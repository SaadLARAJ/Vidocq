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
    backend=settings.REDIS_URL
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
def ingest_url(self, url: str, source_domain: str):
    """
    Ingest a URL: Fetch -> Parse -> Chunk -> (Next: Extract).
    """
    logger.info("starting_ingestion", url=url)
    
    # 1. Fetch with Stealth
    with StealthSession() as session:
        response = session.get(url)
        html_content = response.text

    # 2. Parse
    clean_text = ContentParser.parse_html(html_content)
    
    # 3. Create SourceDocument model
    doc = SourceDocument(
        url=url,
        raw_content=html_content,
        cleaned_content=clean_text,
        source_domain=source_domain,
        reliability_score=settings.SOURCE_WEIGHTS.get(source_domain, 0.5)
    )
    
    # 4. Chunk
    chunker = SemanticChunker()
    chunks = chunker.chunk(clean_text)
    
    logger.info("ingestion_complete", url=url, chunks_count=len(chunks))
    
    # TODO: Trigger extraction task for each chunk
    # for chunk in chunks:
    #     extract_claims.delay(chunk, doc.id)
    
    return {"doc_id": str(doc.id), "chunks": len(chunks)}
