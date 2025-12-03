from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.core.models import EntityNode, AmbiguousMatch
from src.core.logging import get_logger

logger = get_logger(__name__)

class ResolutionQueue:
    """Manages the queue of ambiguous matches requiring human review."""
    
    def __init__(self):
        self.engine = create_engine(settings.POSTGRES_DSN)
        self.Session = sessionmaker(bind=self.engine)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Idempotent table creation."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ambiguous_matches (
            id UUID PRIMARY KEY,
            candidate_a_id TEXT NOT NULL,
            candidate_b_id TEXT NOT NULL,
            similarity_score FLOAT NOT NULL,
            evidence_context JSONB,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            reviewed_at TIMESTAMP WITHOUT TIME ZONE
        );
        """
        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()

    def add(self, incoming: EntityNode, existing: EntityNode, score: float):
        """Add an ambiguous match to the queue."""
        match_entry = AmbiguousMatch(
            candidate_a_id=incoming.id,
            candidate_b_id=existing.id,
            similarity_score=score,
            evidence_context=["Context placeholder"] # In real app, pass context
        )
        
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        INSERT INTO ambiguous_matches 
                        (id, candidate_a_id, candidate_b_id, similarity_score, evidence_context, status, created_at)
                        VALUES (:id, :candidate_a_id, :candidate_b_id, :similarity_score, :evidence_context, :status, :created_at)
                    """),
                    match_entry.model_dump(mode='json')
                )
                session.commit()
            logger.info("added_to_hitl_queue", match_id=str(match_entry.id), score=score)
        except Exception as e:
            logger.error("failed_to_queue_match", error=str(e))
