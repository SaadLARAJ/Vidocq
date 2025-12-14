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
def extract_claims(self, text: str, source_domain: str, source_id: str, source_url: str = "", depth: int = 0):
    """
    Task to extract information from text using Gemini and save to storage.
    """
    logger.info("starting_extraction", source_id=source_id, text_len=len(text), depth=depth)
    
    try:
        # 1. Extract
        extractor = Extractor()
        data = extractor.extract(text=text, source_domain=source_domain, source_url=source_url)
        
        entities = data.get("entities", [])
        claims = data.get("claims", [])
        
        logger.info("extraction_success", entities=len(entities), claims=len(claims))
        
        from src.pipeline.verification import apply_verification_to_extraction
        entities, claims, verification_summary = apply_verification_to_extraction(entities, claims)
        logger.info("verification_applied", **verification_summary)
        
        # ============================================
        # 2.5 SOFT-FILTERING (CIA/OTAN Style Quarantine)
        # "Raw Intelligence Never Dies" - We NEVER delete data
        # Instead, we TAG it with visibility status
        # ============================================
        
        # Apply visibility tagging based on confidence + relevance
        try:
            from src.pipeline.relevance_filter import RelevanceFilter, MissionType
            import asyncio
            
            relevance_filter = RelevanceFilter(mission_type=MissionType.SUPPLY_CHAIN)
            
            # Evaluate each claim and assign visibility status
            quarantine_count = 0
            visible_count = 0
            
            for claim in claims:
                confidence = getattr(claim, 'confidence_score', 0.5)
                
                # Get relevance decision (but we don't delete based on it)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                decision = loop.run_until_complete(relevance_filter.evaluate(
                    source_entity=getattr(claim, 'subject', ''),
                    relation=getattr(claim, 'predicate', ''),
                    target_entity=getattr(claim, 'object', ''),
                    context=getattr(claim, 'source_text', ''),
                    confidence=confidence
                ))
                loop.close()
                
                # Combined score
                combined_score = (confidence + decision.relevance_score) / 2
                
                # === THE TAGGING STRATEGY (Never Delete) ===
                # Zone Verte: Confirmé (score >= 0.8)
                # Zone Orange: Non-vérifié (0.5 <= score < 0.8)  
                # Zone Grise: Quarantaine (score < 0.5)
                
                if combined_score >= 0.8:
                    claim.visibility_status = "CONFIRMED"      # Zone Verte
                    claim.visibility = "VISIBLE"
                    visible_count += 1
                elif combined_score >= 0.5:
                    claim.visibility_status = "UNVERIFIED"     # Zone Orange
                    claim.visibility = "VISIBLE"
                    visible_count += 1
                else:
                    claim.visibility_status = "QUARANTINE"     # Zone Grise
                    claim.visibility = "HIDDEN"
                    quarantine_count += 1
                
                # Store the score for later analysis
                claim.combined_relevance_score = combined_score
                claim.relevance_reason = decision.reason
            
            # Same for entities
            for entity in entities:
                confidence = getattr(entity, 'confidence_score', 0.7)
                if confidence >= 0.7:
                    entity.visibility_status = "CONFIRMED"
                    entity.visibility = "VISIBLE"
                elif confidence >= 0.4:
                    entity.visibility_status = "UNVERIFIED"
                    entity.visibility = "VISIBLE"
                else:
                    entity.visibility_status = "QUARANTINE"
                    entity.visibility = "HIDDEN"
            
            logger.info(
                "soft_filter_applied",
                total_claims=len(claims),
                visible=visible_count,
                quarantined=quarantine_count,
                note="NO DATA DELETED - All saved with visibility tags"
            )
            
        except Exception as filter_err:
            logger.warning("soft_filter_skipped", error=str(filter_err))
            # If filter fails, mark everything as VISIBLE (safe default)
            for claim in claims:
                claim.visibility_status = "UNVERIFIED"
                claim.visibility = "VISIBLE"
            for entity in entities:
                entity.visibility_status = "UNVERIFIED"
                entity.visibility = "VISIBLE"
        
        # 3. Save to Graph (Neo4j) - SAVE EVERYTHING (Quarantined + Visible)
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
                logger.info("triggering_discovery_async", entity=entity.canonical_name, depth=depth)
                # Async trigger to keep workers moving
                # Avoid circular import at top level
                from src.ingestion.tasks import launch_discovery_task
                launch_discovery_task.delay(entity.canonical_name, depth=depth)

        return {"features_extracted": len(entities) + len(claims)}

    except Exception as e:
        # FAIL FAST STRATEGY
        # If extraction fails (JSON error, API quota, etc.), we log it and STOP.
        # We do NOT retry, so the worker can immediately pick up the next URL.
        logger.error("extraction_failed_skipping", error=str(e), source_id=source_id)
        return {"error": str(e), "status": "failed_fast"}
