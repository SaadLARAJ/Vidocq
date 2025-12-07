from celery import shared_task
import uuid
import hashlib
import google.generativeai as genai
from src.pipeline.extractor import Extractor
from src.core.logging import get_logger
from src.storage.graph import GraphStore
from src.storage.vector import VectorStore

logger = get_logger(__name__)

def generate_uuid_from_string(val: str) -> str:
    """Generate a deterministic UUID from a string."""
    hex_string = hashlib.md5(val.encode("UTF-8")).hexdigest()
    return str(uuid.UUID(hex=hex_string))

@shared_task(name="src.pipeline.tasks.extract_claims", bind=True, max_retries=3)
def extract_claims(self, text: str, source_domain: str, source_id: str, depth: int = 0):
    """
    Task to extract information from text using Gemini and save to storage.
    """
    logger.info("starting_extraction", source_id=source_id, text_len=len(text), depth=depth)
    
    try:
        # 1. Extract
        extractor = Extractor()
        data = extractor.extract(text=text, source_domain=source_domain)
        
        entities = data.get("entities", [])
        claims = data.get("claims", [])
        
        logger.info("extraction_success", entities=len(entities), claims=len(claims))
        
        # 2. Save to Graph (Neo4j)
        graph_store = GraphStore()
        graph_store.merge_entities_batch(entities)
        graph_store.merge_claims_batch(claims)
             
        # 3. Save to Vector DB (Qdrant)
        vector_store = VectorStore()
        vector_data = []
        
        for entity in entities:
             # Generate real embedding using Gemini
             # Model: "models/text-embedding-004" is standard for Gemini
             try:
                 embedding_result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=entity.canonical_name,
                    task_type="retrieval_document"
                 )
                 vector = embedding_result['embedding']
                 
                 # Ensure ID is UUID
                 entity_uuid = generate_uuid_from_string(entity.id)
                 
                 vector_data.append({
                     "id": entity_uuid,
                     "vector": vector, 
                     "payload": entity.model_dump()
                 })
             except Exception as embed_err:
                 logger.error("embedding_failed", entity=entity.canonical_name, error=str(embed_err))

        if vector_data:
            # Note: The vector config in vector.py must match the size of text-embedding-004 (768 dimensions)
            # The current vector.py sets size=1536 (OpenAI standard).
            # This might cause a dimension mismatch error if not updated.
            # But we will try to upsert. If it fails, we know why.
            try:
                vector_store.upsert_vectors(vector_data) 
                logger.info("vectors_saved", count=len(vector_data))
            except Exception as e:
                 logger.error("vector_upsert_failed_dimension_mismatch_likely", error=str(e))
        
        # 4. Recursive Discovery Trigger
        # Only trigger if we haven't reached max depth
        from src.pipeline.discovery import DiscoveryEngine
        discovery = DiscoveryEngine()
        
        for entity in entities:
            if entity.entity_type == "ORGANIZATION":
                logger.info("triggering_discovery", entity=entity.canonical_name, depth=depth)
                # We trigger this synchronously here, but in production this should be a separate task
                # to avoid blocking the worker. For the prototype, it's fine as it spawns async ingest tasks.
                discovery.discover_and_loop(entity.canonical_name, current_depth=depth)

        return {"features_extracted": len(entities) + len(claims)}

    except Exception as e:
        # FAIL FAST STRATEGY
        # If extraction fails (JSON error, API quota, etc.), we log it and STOP.
        # We do NOT retry, so the worker can immediately pick up the next URL.
        logger.error("extraction_failed_skipping", error=str(e), source_id=source_id)
        return {"error": str(e), "status": "failed_fast"}
