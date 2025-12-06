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
        Batch upsert entities using UNWIND, dynamically setting labels.
        """
        if not entities:
            return

        query = """
        UNWIND $entities AS entity
        // Merge on the generic :Entity label and unique ID
        MERGE (e:Entity {id: entity.id})
        // Set properties on create or update
        SET e += entity.properties
        // Dynamically add the specific label (e.g., :ORGANIZATION, :COUNTRY)
        WITH e, entity.entity_type AS label
        CALL apoc.create.addLabels(e, [label]) YIELD node
        RETURN count(node)
        """
        
        # Convert Pydantic models to dicts, preparing properties for SET
        entity_dicts = []
        for e in entities:
            props = e.model_dump(mode='json', exclude={'id'})
            entity_dicts.append({
                'id': e.id,
                'entity_type': e.entity_type,
                'properties': props
            })
        
        try:
            with self.driver.session() as session:
                session.run(query, entities=entity_dicts)
            logger.info("batch_entities_merged", count=len(entities))
        except Exception as e:
            logger.error("neo4j_batch_error", error=str(e))
            raise StorageError(f"Failed to merge entities batch: {e}")

    def merge_claims_batch(self, claims: List[Claim]):
        """
        Batch upsert claims (relationships) using UNWIND and dynamic relationship types.
        """
        if not claims:
            return

        query = """
        UNWIND $claims AS claim
        MATCH (s:Entity {id: claim.subject_id})
        MATCH (o:Entity {id: claim.object_id})
        // Use apoc.merge.relationship to create a relationship with a dynamic type
        CALL apoc.merge.relationship(s, claim.relation_type, {}, claim.properties, o) YIELD rel
        RETURN count(rel) AS total
        """
        
        # Convert Pydantic models to dicts for APOC
        claim_dicts = []
        for c in claims:
            # Prepare properties, excluding IDs that are used for matching
            props = c.model_dump(mode='json', exclude={'subject_id', 'object_id', 'relation_type'})
            claim_dicts.append({
                'subject_id': c.subject_id,
                'object_id': c.object_id,
                'relation_type': c.relation_type.upper(), # Ensure type is uppercase
                'properties': props
            })
        
        try:
            with self.driver.session() as session:
                session.run(query, claims=claim_dicts)
            logger.info("batch_claims_merged", count=len(claims))
        except Exception as e:
            logger.error("neo4j_batch_error", error=str(e))
            raise StorageError(f"Failed to merge claims batch: {e}")
