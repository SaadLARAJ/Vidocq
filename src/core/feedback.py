"""
VIDOCQ - Feedback & Continuous Learning System
Collects analyst corrections for future model training.

"Chaque clic de l'analyste rend l'IA plus intelligente."

Features:
- Store corrections (relation fixes, entity merges)
- Store validations (confirmed accurate)
- Export training data for fine-tuning
- Track learning metrics
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum
import json
import os

from src.storage.graph import GraphStore
from src.core.logging import get_logger

logger = get_logger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback an analyst can provide"""
    VALIDATE = "VALIDATE"           # Confirm relation is correct
    CORRECT_RELATION = "CORRECT_RELATION"  # Fix relation type
    DELETE_RELATION = "DELETE_RELATION"    # Remove false relation
    MERGE_ENTITIES = "MERGE_ENTITIES"      # Two entities are the same
    ADD_CONTEXT = "ADD_CONTEXT"    # Add missing context
    FLAG_NOISE = "FLAG_NOISE"      # Mark as noise/irrelevant


class FeedbackEntry(BaseModel):
    """A single feedback entry from an analyst"""
    feedback_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # What is being corrected
    entity_id: Optional[str] = None
    relation_id: Optional[str] = None
    source_entity: Optional[str] = None
    target_entity: Optional[str] = None
    original_relation: Optional[str] = None
    
    # The feedback
    feedback_type: FeedbackType
    correct_value: Optional[str] = None  # New relation type, merged entity, etc.
    analyst_note: Optional[str] = None
    
    # For training
    original_context: Optional[str] = None  # The source text
    is_used_for_training: bool = False


class TrainingExample(BaseModel):
    """Formatted example for model fine-tuning"""
    input_text: str
    expected_output: Dict[str, Any]
    source: str = "analyst_feedback"


class FeedbackStore:
    """
    Stores and manages analyst feedback for continuous learning.
    
    Data is stored in:
    1. JSON file (for persistence and export)
    2. Neo4j (for graph updates)
    
    When enough feedback accumulates, it can be exported
    as training data for model fine-tuning.
    """
    
    FEEDBACK_FILE = "data/feedback/corrections.jsonl"
    TRAINING_FILE = "data/feedback/training_data.jsonl"
    MIN_EXAMPLES_FOR_TRAINING = 100
    
    def __init__(self):
        self.graph_store = GraphStore()
        self._ensure_directories()
        self.feedback_count = self._count_feedback()
    
    def _ensure_directories(self):
        """Ensure feedback directories exist"""
        os.makedirs("data/feedback", exist_ok=True)
    
    def _count_feedback(self) -> int:
        """Count existing feedback entries"""
        if not os.path.exists(self.FEEDBACK_FILE):
            return 0
        with open(self.FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    
    async def add_feedback(self, feedback: FeedbackEntry) -> Dict[str, Any]:
        """
        Add a new feedback entry.
        
        1. Store in JSON for persistence
        2. Optionally apply to graph immediately
        3. Increment training counter
        """
        logger.info(
            "feedback_received",
            type=feedback.feedback_type.value,
            entity=feedback.entity_id or feedback.source_entity
        )
        
        # Store in JSONL file
        with open(self.FEEDBACK_FILE, 'a', encoding='utf-8') as f:
            f.write(feedback.model_dump_json() + '\n')
        
        self.feedback_count += 1
        
        # Apply correction to graph if it's a correction
        if feedback.feedback_type == FeedbackType.CORRECT_RELATION:
            await self._apply_relation_correction(feedback)
        elif feedback.feedback_type == FeedbackType.DELETE_RELATION:
            await self._apply_deletion(feedback)
        elif feedback.feedback_type == FeedbackType.VALIDATE:
            await self._apply_validation(feedback)
        elif feedback.feedback_type == FeedbackType.FLAG_NOISE:
            await self._apply_noise_flag(feedback)
        
        # Check if ready for training
        ready_for_training = self.feedback_count >= self.MIN_EXAMPLES_FOR_TRAINING
        
        return {
            "status": "feedback_recorded",
            "feedback_id": feedback.feedback_id,
            "total_feedback": self.feedback_count,
            "ready_for_training": ready_for_training,
            "training_threshold": self.MIN_EXAMPLES_FOR_TRAINING
        }
    
    async def _apply_relation_correction(self, feedback: FeedbackEntry):
        """Apply relation type correction to Neo4j"""
        if not feedback.source_entity or not feedback.target_entity:
            return
        
        query = """
        MATCH (s:Entity)-[r]->(t:Entity)
        WHERE s.canonical_name = $source AND t.canonical_name = $target
        DELETE r
        CREATE (s)-[new_r:$new_type {
            corrected: true,
            correction_date: datetime(),
            original_type: $original
        }]->(t)
        """
        
        try:
            with self.graph_store.driver.session() as session:
                # Neo4j doesn't allow parameterized relationship types
                # So we need a workaround
                session.run("""
                    MATCH (s:Entity)-[r]->(t:Entity)
                    WHERE s.canonical_name = $source AND t.canonical_name = $target
                    SET r.corrected = true,
                        r.correction_date = datetime(),
                        r.corrected_to = $new_type
                """, 
                    source=feedback.source_entity,
                    target=feedback.target_entity,
                    new_type=feedback.correct_value
                )
                logger.info("relation_corrected", 
                    source=feedback.source_entity,
                    target=feedback.target_entity,
                    new_type=feedback.correct_value
                )
        except Exception as e:
            logger.error("correction_failed", error=str(e))
    
    async def _apply_deletion(self, feedback: FeedbackEntry):
        """Mark relation as deleted (soft delete)"""
        if not feedback.source_entity or not feedback.target_entity:
            return
        
        try:
            with self.graph_store.driver.session() as session:
                session.run("""
                    MATCH (s:Entity)-[r]->(t:Entity)
                    WHERE s.canonical_name = $source AND t.canonical_name = $target
                    SET r.deleted = true,
                        r.deletion_date = datetime(),
                        r.visibility = 'HIDDEN'
                """,
                    source=feedback.source_entity,
                    target=feedback.target_entity
                )
                logger.info("relation_soft_deleted",
                    source=feedback.source_entity,
                    target=feedback.target_entity
                )
        except Exception as e:
            logger.error("deletion_failed", error=str(e))
    
    async def _apply_validation(self, feedback: FeedbackEntry):
        """Mark relation as validated (confirmed accurate)"""
        if not feedback.source_entity or not feedback.target_entity:
            return
        
        try:
            with self.graph_store.driver.session() as session:
                session.run("""
                    MATCH (s:Entity)-[r]->(t:Entity)
                    WHERE s.canonical_name = $source AND t.canonical_name = $target
                    SET r.validated = true,
                        r.validation_date = datetime(),
                        r.visibility_status = 'CONFIRMED',
                        r.confidence_score = 1.0
                """,
                    source=feedback.source_entity,
                    target=feedback.target_entity
                )
                logger.info("relation_validated",
                    source=feedback.source_entity,
                    target=feedback.target_entity
                )
        except Exception as e:
            logger.error("validation_failed", error=str(e))
    
    async def _apply_noise_flag(self, feedback: FeedbackEntry):
        """Flag as noise - move to permanent quarantine"""
        if not feedback.entity_id and not feedback.source_entity:
            return
        
        entity = feedback.entity_id or feedback.source_entity
        
        try:
            with self.graph_store.driver.session() as session:
                session.run("""
                    MATCH (e:Entity)
                    WHERE e.id = $entity OR e.canonical_name = $entity
                    SET e.is_noise = true,
                        e.visibility_status = 'NOISE',
                        e.visibility = 'HIDDEN'
                """, entity=entity)
                logger.info("entity_flagged_noise", entity=entity)
        except Exception as e:
            logger.error("noise_flag_failed", error=str(e))
    
    def export_training_data(self) -> List[TrainingExample]:
        """
        Export feedback as training examples for fine-tuning.
        
        Format suitable for Mistral/LLaMA fine-tuning.
        """
        if not os.path.exists(self.FEEDBACK_FILE):
            return []
        
        examples = []
        
        with open(self.FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                entry = FeedbackEntry.model_validate_json(line)
                
                # Only use corrections, not validations (for training)
                if entry.feedback_type in [
                    FeedbackType.CORRECT_RELATION,
                    FeedbackType.DELETE_RELATION,
                    FeedbackType.FLAG_NOISE
                ]:
                    example = TrainingExample(
                        input_text=entry.original_context or f"{entry.source_entity} {entry.original_relation} {entry.target_entity}",
                        expected_output={
                            "entities": [entry.source_entity, entry.target_entity],
                            "relation": entry.correct_value or "NONE",
                            "is_noise": entry.feedback_type == FeedbackType.FLAG_NOISE
                        }
                    )
                    examples.append(example)
        
        # Write to training file
        with open(self.TRAINING_FILE, 'w', encoding='utf-8') as f:
            for ex in examples:
                f.write(ex.model_dump_json() + '\n')
        
        logger.info("training_data_exported", count=len(examples))
        return examples
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        if not os.path.exists(self.FEEDBACK_FILE):
            return {
                "total_feedback": 0,
                "by_type": {},
                "ready_for_training": False
            }
        
        by_type = {}
        with open(self.FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                entry = FeedbackEntry.model_validate_json(line)
                by_type[entry.feedback_type.value] = by_type.get(entry.feedback_type.value, 0) + 1
        
        total = sum(by_type.values())
        
        return {
            "total_feedback": total,
            "by_type": by_type,
            "ready_for_training": total >= self.MIN_EXAMPLES_FOR_TRAINING,
            "training_threshold": self.MIN_EXAMPLES_FOR_TRAINING,
            "progress_percent": min(100, total / self.MIN_EXAMPLES_FOR_TRAINING * 100)
        }
