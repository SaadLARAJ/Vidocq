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
def extract_claims(self, text: str, source_domain: str, source_id: str, source_url: str = "", depth: int = 0, parent_context: str = None):
    """
    Task to extract information from text using Gemini and save to storage.
    
    Args:
        parent_context: The original search term to maintain context in recursive discovery.
                       E.g., if searching for 'RBE2 Radar', child entities will be searched
                       with context 'RBE2 Radar' to stay focused.
    """
    logger.info("starting_extraction", source_id=source_id, text_len=len(text), depth=depth)
    
    try:
        # 1. Extract with parent context for focused extraction
        extractor = Extractor()
        data = extractor.extract(
            text=text, 
            source_domain=source_domain, 
            source_url=source_url,
            parent_context=parent_context  # Now passed through!
        )
        
        entities = data.get("entities", [])
        claims = data.get("claims", [])
        
        logger.info("extraction_success", entities=len(entities), claims=len(claims))
        
        from src.pipeline.verification import apply_verification_to_extraction
        entities, claims, verification_summary = apply_verification_to_extraction(entities, claims)
        logger.info("verification_applied", **verification_summary)
        
        # ============================================
        # 2.5 UNIFIED SCORING (CIA/OTAN Style Intelligence Grading)
        # Multi-factor scoring: LLM confidence + Source trust + Relevance
        # "Raw Intelligence Never Dies" - We NEVER delete data
        # ============================================
        
        try:
            from src.core.unified_scoring import UnifiedScorer, VisibilityZone
            from src.pipeline.relevance_filter import RelevanceFilter, MissionType
            import asyncio
            
            scorer = UnifiedScorer()
            relevance_filter = RelevanceFilter(mission_type=MissionType.SUPPLY_CHAIN)
            
            quarantine_count = 0
            visible_count = 0
            
            for claim in claims:
                llm_confidence = getattr(claim, 'confidence_score', 0.5)
                is_tangential = getattr(claim, 'is_tangential', False)
                
                # Get relevance decision
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                decision = loop.run_until_complete(relevance_filter.evaluate(
                    source_entity=getattr(claim, 'subject_id', ''),
                    relation=getattr(claim, 'relation_type', ''),
                    target_entity=getattr(claim, 'object_id', ''),
                    context=getattr(claim, 'evidence_snippet', ''),
                    confidence=llm_confidence
                ))
                loop.close()
                
                # Compute unified score using multi-factor system
                breakdown = scorer.compute_score(
                    llm_confidence=llm_confidence,
                    source_url=source_url or source_domain,
                    mission_relevance=decision.relevance_score,
                    is_tangential=is_tangential,
                    corroboration_count=1  # Will be updated when we find matching claims
                )
                
                # Assign visibility zone
                visibility = scorer.get_visibility_zone(breakdown.final_score)
                claim.visibility_status = visibility.value
                claim.unified_score = breakdown.final_score
                claim.score_breakdown = {
                    "llm": breakdown.llm_confidence,
                    "source_trust": breakdown.source_trust,
                    "relevance": breakdown.mission_relevance,
                    "corroboration": breakdown.corroboration_bonus
                }
                
                if visibility == VisibilityZone.GREY:
                    quarantine_count += 1
                else:
                    visible_count += 1
            
            # Score entities
            for entity in entities:
                confidence = getattr(entity, 'confidence_score', 0.7)
                is_tangential = getattr(entity, 'is_tangential', False)
                
                breakdown = scorer.compute_score(
                    llm_confidence=confidence,
                    source_url=source_url or source_domain,
                    mission_relevance=0.7 if not is_tangential else 0.3,
                    is_tangential=is_tangential
                )
                
                entity.visibility_status = scorer.get_visibility_zone(breakdown.final_score).value
                entity.unified_score = breakdown.final_score
            
            logger.info(
                "unified_scoring_applied",
                total_claims=len(claims),
                visible=visible_count,
                quarantined=quarantine_count,
                scorer_version="UnifiedScorer v1.0",
                note="NO DATA DELETED - All saved with visibility tags"
            )
            
        except Exception as filter_err:
            logger.warning("unified_scoring_skipped", error=str(filter_err))
            # If scoring fails, mark everything as UNVERIFIED (safe default)
            for claim in claims:
                claim.visibility_status = "UNVERIFIED"
            for entity in entities:
                entity.visibility_status = "UNVERIFIED"
        
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
        # Only trigger if we haven't reached max depth AND entity is high-quality
        from src.pipeline.discovery import DiscoveryEngine
        discovery = DiscoveryEngine()
        
        # NOISE ENTITY FILTER - Prevent garbage from spawning new searches
        NOISE_ENTITY_KEYWORDS = {
            "school", "university", "college", "class", "grade", "math", "science",
            "secondary", "primary", "tutorial", "course", "homework", "quiz",
            "triangle", "matrix", "vector", "theorem", "chapter", "exercise",
            "user", "admin", "login", "password", "username", "profile",
            "facebook", "twitter", "instagram", "youtube", "tiktok", "reddit",
            "forum", "comment", "reply", "answer", "question", "brainly"
        }
        
        for entity in entities:
            if entity.entity_type == "ORGANIZATION":
                # Check if entity name contains noise keywords
                name_lower = entity.canonical_name.lower()
                is_noise = any(noise in name_lower for noise in NOISE_ENTITY_KEYWORDS)
                
                if is_noise:
                    logger.info("discovery_skipped_noise_entity", entity=entity.canonical_name, reason="noise_keywords")
                    continue
                    
                # Check minimum confidence before triggering discovery
                confidence = getattr(entity, 'confidence_score', 0.5)
                if confidence < 0.4:
                    logger.info("discovery_skipped_low_confidence", entity=entity.canonical_name, confidence=confidence)
                    continue
                
                logger.info("triggering_discovery_async", entity=entity.canonical_name, depth=depth, context=parent_context)
                # Async trigger to keep workers moving
                # Avoid circular import at top level
                from src.ingestion.tasks import launch_discovery_task
                launch_discovery_task.delay(entity.canonical_name, depth=depth, parent_context=parent_context)

        return {"features_extracted": len(entities) + len(claims)}

    except Exception as e:
        # FAIL FAST STRATEGY
        # If extraction fails (JSON error, API quota, etc.), we log it and STOP.
        # We do NOT retry, so the worker can immediately pick up the next URL.
        logger.error("extraction_failed_skipping", error=str(e), source_id=source_id)
        return {"error": str(e), "status": "failed_fast"}

