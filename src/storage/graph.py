from neo4j import GraphDatabase
from typing import List
from src.config import settings
from src.core.models import EntityNode, Claim
from src.core.logging import get_logger
from src.core.exceptions import StorageError

logger = get_logger(__name__)

class GraphStore:
    """
    Neo4j storage handler.
    Enforces batch writes using UNWIND for performance.
    """
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def merge_entities_batch(self, entities: List[EntityNode]):
        """
        Batch upsert entities using UNWIND.
        """
        if not entities:
            return

        query = """
        UNWIND $entities AS entity
        MERGE (e:Entity {id: entity.id})
        ON CREATE SET 
            e.name = entity.canonical_name,
            e.type = entity.entity_type,
            e.aliases = entity.aliases,
            e.first_seen = entity.first_seen,
            e.vector_id = entity.vector_id
        ON MATCH SET
            e.aliases = apoc.coll.toSet(e.aliases + entity.aliases)
        """
        
        # Convert Pydantic models to dicts
        entity_dicts = [e.model_dump(mode='json') for e in entities]
        
        try:
            with self.driver.session() as session:
                session.run(query, entities=entity_dicts)
            logger.info("batch_entities_merged", count=len(entities))
        except Exception as e:
            logger.error("neo4j_batch_error", error=str(e))
            raise StorageError(f"Failed to merge entities batch: {e}")

    def merge_claims_batch(self, claims: List[Claim]):
        """
        Batch upsert claims (relationships) using UNWIND.
        """
        if not claims:
            return

        query = """
        UNWIND $claims AS claim
        MATCH (s:Entity {id: claim.subject_id})
        MATCH (o:Entity {id: claim.object_id})
        MERGE (s)-[r:RELATION {id: claim.id}]->(o)
        ON CREATE SET
            r.type = claim.relation_type,
            r.confidence = claim.confidence_score,
            r.evidence = claim.evidence_snippet,
            r.source_id = claim.source_id,
            r.extracted_at = claim.extracted_at
        """
        
        claim_dicts = [c.model_dump(mode='json') for c in claims]
        
        try:
            with self.driver.session() as session:
                session.run(query, claims=claim_dicts)
            logger.info("batch_claims_merged", count=len(claims))
        except Exception as e:
            logger.error("neo4j_batch_error", error=str(e))
            raise StorageError(f"Failed to merge claims batch: {e}")
