from celery import Celery, Task
from celery.signals import task_failure
from src.config import settings
from src.core.logging import get_logger
from src.storage.dlq import get_dlq
from src.ingestion.stealth import StealthSession
from src.ingestion.parser import ContentParser
from src.ingestion.chunking import SemanticChunker
from src.core.models import SourceDocument
from src.core.exceptions import IngestionError

logger = get_logger(__name__)

# Celery App Configuration
celery_app = Celery(
    "shadowmap",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['src.pipeline.tasks']
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.ingestion.tasks.ingest_url": "parse_queue",
    }
)

class BaseTask(Task):
    """Base task with DLQ support on failure."""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("task_failed", task_id=task_id, error=str(exc))
        # If it's the last retry, push to DLQ
        if self.request.retries >= self.max_retries:
            logger.warning("max_retries_exceeded_pushing_to_dlq", task_id=task_id)
            get_dlq().push(
                task_name=self.name,
                payload={"args": args, "kwargs": kwargs},
                error=exc,
                retry_count=self.request.retries
            )
        super().on_failure(exc, task_id, args, kwargs, einfo)

@celery_app.task(
    bind=True,
    base=BaseTask,
    autoretry_for=(IngestionError,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3
)
def ingest_url(self, url: str, source_domain: str, depth: int = 0, entity_name: str = None):
    """
    Ingest a URL: Fetch -> Parse -> Check Relevance -> Chunk -> (Next: Extract).
    
    If entity_name is provided, the page content is checked for relevance.
    Pages that don't mention the entity are skipped to avoid garbage processing.
    """
    logger.info("starting_ingestion", url=url)
    
    # 1. Fetch with Stealth
    with StealthSession() as session:
        response = session.get(url)
        content_type = response.headers.get("Content-Type", "").lower()
        
        if "pdf" in content_type:
            from src.ingestion.pdf_parser import PDFParser
            html_content = PDFParser.parse_pdf(response.content)
            logger.info("pdf_ingestion", url=url, type="pdf")
        else:
            html_content = response.text

    # 2. Parse
    clean_text = ContentParser.parse_html(html_content)
    
    # 3. RELEVANCE CHECK - Skip pages that don't mention the entity
    if entity_name and clean_text:
        # Split entity into keywords and check if ANY are present
        keywords = [kw.lower().strip() for kw in entity_name.split() if len(kw) > 2]
        text_lower = clean_text.lower()
        
        # Check if at least one significant keyword appears in the page
        keyword_found = any(kw in text_lower for kw in keywords)
        
        if not keyword_found:
            logger.info("page_skipped_not_relevant", url=url, entity=entity_name, 
                       keywords=keywords[:5], text_preview=text_lower[:100])
            return {"doc_id": None, "chunks": 0, "skipped": "not_relevant"}
    
    # 4. Create SourceDocument model
    doc = SourceDocument(
        url=url,
        raw_content=html_content,
        cleaned_content=clean_text,
        source_domain=source_domain,
        reliability_score=settings.SOURCE_WEIGHTS.get(source_domain, 0.5)
    )
    
    # 5. Chunk
    chunker = SemanticChunker()
    chunks = chunker.chunk(clean_text)
    
    logger.info("ingestion_complete", url=url, chunks_count=len(chunks))
    
    # Trigger extraction task for each chunk
    # Pass entity_name as parent_context so child discoveries stay focused
    from src.pipeline.tasks import extract_claims
    for chunk in chunks:
        extract_claims.delay(text=chunk, source_domain=source_domain, source_id=str(doc.id), source_url=url, depth=depth, parent_context=entity_name)
    
    return {"doc_id": str(doc.id), "chunks": len(chunks)}

@celery_app.task(bind=True, base=BaseTask)
def launch_discovery_task(self, entity_name: str, depth: int = 0, use_v3: bool = True, parent_context: str = None):
    """
    Launch the Discovery Engine in a background worker.
    
    Args:
        entity_name: Entity to investigate
        depth: Current recursion depth
        use_v3: Use V3 engine (multilingual, context-aware) - DEFAULT
        parent_context: Original search context to keep searches focused
                       E.g., searching "Thales" with context "RBE2 Radar" → "Thales RBE2 Radar"
    """
    # Build contextual search term - combine entity with parent context if present
    search_term = entity_name
    if parent_context and parent_context.lower() not in entity_name.lower():
        search_term = f"{entity_name} {parent_context}"
    
    logger.info("celery_discovery_started", entity=entity_name, v3=use_v3, search_term=search_term, context=parent_context)
    
    # V3 is the default - better context detection, multilingual, noise filtering
    if use_v3:
        try:
            from src.pipeline.discovery_v3 import DiscoveryEngineV3
            from src.ingestion.tasks import ingest_url
            
            engine = DiscoveryEngineV3(use_cache=True, aggressive=True)
            # Use contextual search term for discovery
            result = engine.discover(search_term, depth=depth, max_urls=30)
            
            # Trigger ingestion for discovered URLs
            # Use parent_context (or entity if no context) for relevance check
            relevance_context = parent_context if parent_context else entity_name
            urls = result.get("urls", [])
            for url in urls:
                ingest_url.delay(url, f"discovery_v3_{entity_name}", depth=depth + 1, entity_name=relevance_context)
            
            return {
                "status": "completed", 
                "entity": entity_name,
                "search_term": search_term,
                "parent_context": parent_context,
                "urls_found": len(urls),
                "context": result.get("context", {}),
                "cached": result.get("cached", False)
            }
        except Exception as e:
            logger.warning("discovery_v3_failed_fallback_v2", error=str(e))
    
    # Fallback to V2
    from src.pipeline.discovery_v2 import DiscoveryEngineV2
    engine = DiscoveryEngineV2(use_cache=True)
    result = engine.discover_and_ingest(entity_name, depth)
    return {
        "status": "completed", 
        "entity": entity_name,
        "urls_found": result.get("url_count", 0),
        "cached": result.get("cached", False)
    }


@celery_app.task(bind=True, base=BaseTask)
def launch_discovery_v2_task(self, entity_name: str, depth: int = 0):
    """
    Launch the enhanced Discovery Engine v2 (with caching) in a background worker.
    Kept for backward compatibility.
    """
    logger.info("celery_discovery_v2_started", entity=entity_name)
    
    from src.pipeline.discovery_v2 import DiscoveryEngineV2
    engine = DiscoveryEngineV2(use_cache=True)
    result = engine.discover_and_ingest(entity_name, depth)
    
    return {
        "status": "completed", 
        "entity": entity_name,
        "urls_found": result.get("url_count", 0),
        "cached": result.get("cached", False)
    }

