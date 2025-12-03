import traceback
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.core.models import DeadLetterEntry
from src.core.logging import get_logger
from src.core.exceptions import DLQError

logger = get_logger(__name__)

class DLQHandler:
    """Handles writing failed tasks to the Dead Letter Queue in Postgres."""
    
    def __init__(self):
        self.engine = create_engine(settings.POSTGRES_DSN)
        self.Session = sessionmaker(bind=self.engine)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Idempotent table creation for DLQ."""
        # Note: In production, use Alembic migrations. This is for Phase 1 validation.
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS dead_letter_entries (
            id UUID PRIMARY KEY,
            task_name TEXT NOT NULL,
            payload JSONB NOT NULL,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            stack_trace TEXT NOT NULL,
            retry_count INTEGER NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
        );
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_table_sql))
                conn.commit()
        except Exception as e:
            logger.error("dlq_table_creation_failed", error=str(e))
            raise DLQError(f"Failed to ensure DLQ table exists: {e}")

    def push(self, task_name: str, payload: dict, error: Exception, retry_count: int):
        """
        Push a failed task to the DLQ.
        
        Args:
            task_name: Name of the Celery task.
            payload: Arguments passed to the task.
            error: The exception that caused the failure.
            retry_count: Number of times retried.
        """
        entry = DeadLetterEntry(
            task_name=task_name,
            payload=payload,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            retry_count=retry_count
        )
        
        try:
            with self.Session() as session:
                # Raw SQL insert to avoid full ORM overhead for simple insert
                session.execute(
                    text("""
                        INSERT INTO dead_letter_entries 
                        (id, task_name, payload, error_type, error_message, stack_trace, retry_count, created_at)
                        VALUES (:id, :task_name, :payload, :error_type, :error_message, :stack_trace, :retry_count, :created_at)
                    """),
                    entry.model_dump(mode='json')
                )
                session.commit()
            
            logger.error(
                "task_moved_to_dlq", 
                task_name=task_name, 
                error=str(error), 
                dlq_id=str(entry.id)
            )
            
        except Exception as e:
            logger.critical("dlq_write_failed", original_error=str(error), dlq_error=str(e))
            # If DLQ fails, we are in a very bad state. Log to stderr/file as last resort.
            raise DLQError(f"Failed to write to DLQ: {e}")

_dlq_instance = None

def get_dlq():
    """Singleton accessor for DLQHandler."""
    global _dlq_instance
    if _dlq_instance is None:
        _dlq_instance = DLQHandler()
    return _dlq_instance
