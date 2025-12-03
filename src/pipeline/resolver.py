from typing import List, Optional, Tuple
from src.config import settings
from src.core.models import EntityNode, AmbiguousMatch
from src.core.logging import get_logger
from src.pipeline.queue import ResolutionQueue

logger = get_logger(__name__)

class EntityResolver:
    """
    Handles Entity Resolution (ER).
    Decides whether to Merge, Queue (HITL), or Create new entity.
    """
    
    def __init__(self):
        self.queue = ResolutionQueue()

    def resolve(self, incoming_entity: EntityNode, candidates: List[EntityNode]) -> str:
        """
        Resolve an incoming entity against a list of candidates.
        
        Returns:
            str: 'MERGED', 'QUEUED', or 'CREATED'
        """
        best_match, score = self._find_best_match(incoming_entity, candidates)
        
        threshold = settings.MERGE_THRESHOLDS.get(
            incoming_entity.entity_type, 
            settings.MERGE_THRESHOLDS["DEFAULT"]
        )
        
        logger.info(
            "resolving_entity", 
            entity=incoming_entity.canonical_name, 
            best_match=best_match.canonical_name if best_match else None, 
            score=score,
            threshold=threshold
        )

        # Case 1: High confidence -> Auto Merge
        if score >= threshold:
            self._merge(incoming_entity, best_match)
            return "MERGED"
            
        # Case 2: Ambiguous -> HITL Queue
        elif score >= settings.HITL_MIN_SCORE:
            self.queue.add(incoming_entity, best_match, score)
            return "QUEUED"
            
        # Case 3: Low confidence -> Create New
        else:
            self._create(incoming_entity)
            return "CREATED"

    def _find_best_match(self, entity: EntityNode, candidates: List[EntityNode]) -> Tuple[Optional[EntityNode], float]:
        """
        Find the best matching candidate and its score.
        Simple implementation: Exact name match = 1.0, else 0.0.
        Real implementation would use Vector Similarity + Levenshtein.
        """
        if not candidates:
            return None, 0.0
            
        best_candidate = None
        best_score = 0.0
        
        for candidate in candidates:
            # Mock similarity logic
            sim = self._calculate_similarity(entity, candidate)
            if sim > best_score:
                best_score = sim
                best_candidate = candidate
                
        return best_candidate, best_score

    def _calculate_similarity(self, a: EntityNode, b: EntityNode) -> float:
        """Mock similarity calculator."""
        if a.canonical_name == b.canonical_name:
            return 1.0
        # Simulate ambiguity for testing
        if a.canonical_name == "Jean Dupont" and b.canonical_name == "Jean Dupont (Lyon)":
            return 0.85
        return 0.0

    def _merge(self, incoming: EntityNode, existing: EntityNode):
        logger.info("merging_entities", incoming=incoming.id, existing=existing.id)
        # Logic to update Neo4j would go here

    def _create(self, entity: EntityNode):
        logger.info("creating_new_entity", entity=entity.id)
        # Logic to insert into Neo4j would go here
