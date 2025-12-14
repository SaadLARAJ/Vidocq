"""
ShadowMap Retry Logic & Dead Letter Queue
Handles failed tasks with configurable retry and error tracking.
"""

from celery import Task
from datetime import datetime
from typing import Optional, Dict, Any
from src.core.logging import get_logger

logger = get_logger(__name__)


class BaseTaskWithRetry(Task):
    """
    Base Celery task with automatic retry logic and dead letter queue.
    
    Features:
    - Automatic retry with exponential backoff
    - Maximum retry limit
    - Dead letter queue for permanently failed tasks
    - Error logging and tracking
    """
    
    # Retry configuration
    autoretry_for = (Exception,)
    retry_backoff = True           # Exponential backoff
    retry_backoff_max = 600        # Max 10 minutes between retries
    retry_jitter = True            # Add randomness to avoid thundering herd
    max_retries = 3                # Maximum retry attempts
    
    # Track failures
    abstract = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Called when task fails after all retries.
        Sends to Dead Letter Queue for manual review.
        """
        logger.error(
            "task_permanently_failed",
            task_id=task_id,
            task_name=self.name,
            error_type=type(exc).__name__,
            error_message=str(exc),
            args=str(args)[:500],
            retry_count=self.request.retries
        )
        
        # Save to dead letter queue
        self._save_to_dlq(task_id, exc, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Called when task is retrying.
        Logs retry attempt for monitoring.
        """
        logger.warning(
            "task_retrying",
            task_id=task_id,
            task_name=self.name,
            retry_number=self.request.retries + 1,
            max_retries=self.max_retries,
            error=str(exc)[:200]
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """
        Called when task succeeds.
        Logs success for monitoring.
        """
        if self.request.retries > 0:
            logger.info(
                "task_succeeded_after_retry",
                task_id=task_id,
                task_name=self.name,
                retries_needed=self.request.retries
            )
    
    def _save_to_dlq(self, task_id, exc, args, kwargs, einfo):
        """
        Save failed task to Dead Letter Queue for manual review.
        In production, this would save to PostgreSQL or a dedicated queue.
        """
        dlq_entry = {
            "task_id": task_id,
            "task_name": self.name,
            "args": str(args)[:1000],
            "kwargs": str(kwargs)[:1000],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "stack_trace": str(einfo)[:2000] if einfo else None,
            "retry_count": self.request.retries,
            "failed_at": datetime.utcnow().isoformat()
        }
        
        # Log for now (in production, save to DB)
        logger.error("dead_letter_queue_entry", **dlq_entry)
        
        # Could also save to file for debugging
        try:
            import json
            from pathlib import Path
            
            dlq_dir = Path("logs/dead_letter_queue")
            dlq_dir.mkdir(parents=True, exist_ok=True)
            
            dlq_file = dlq_dir / f"{task_id}.json"
            with open(dlq_file, "w") as f:
                json.dump(dlq_entry, f, indent=2, default=str)
                
        except Exception as e:
            logger.warning("dlq_file_save_failed", error=str(e))


class RateLimitedTask(BaseTaskWithRetry):
    """
    Task with rate limiting to avoid API throttling.
    Use for tasks that call external APIs.
    """
    
    # Rate limit: 10 tasks per minute
    rate_limit = '10/m'
    
    # Additional retry for rate limit errors
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 120  # Max 2 minutes for rate limits


# Utility functions for task management

def get_dlq_entries() -> list:
    """
    Retrieve all Dead Letter Queue entries.
    """
    from pathlib import Path
    import json
    
    dlq_dir = Path("logs/dead_letter_queue")
    if not dlq_dir.exists():
        return []
    
    entries = []
    for file in dlq_dir.glob("*.json"):
        try:
            with open(file) as f:
                entries.append(json.load(f))
        except Exception:
            pass
    
    return sorted(entries, key=lambda x: x.get("failed_at", ""), reverse=True)


def retry_dlq_entry(task_id: str) -> bool:
    """
    Retry a task from the Dead Letter Queue.
    """
    from pathlib import Path
    import json
    
    dlq_file = Path(f"logs/dead_letter_queue/{task_id}.json")
    if not dlq_file.exists():
        return False
    
    try:
        with open(dlq_file) as f:
            entry = json.load(f)
        
        # Re-queue the task (simplified - would need actual task routing)
        logger.info("dlq_task_requeued", task_id=task_id, task_name=entry.get("task_name"))
        
        # Remove from DLQ
        dlq_file.unlink()
        return True
        
    except Exception as e:
        logger.error("dlq_retry_failed", task_id=task_id, error=str(e))
        return False


def clear_dlq() -> int:
    """
    Clear all Dead Letter Queue entries.
    Returns number of entries cleared.
    """
    from pathlib import Path
    
    dlq_dir = Path("logs/dead_letter_queue")
    if not dlq_dir.exists():
        return 0
    
    count = 0
    for file in dlq_dir.glob("*.json"):
        try:
            file.unlink()
            count += 1
        except Exception:
            pass
    
    return count
