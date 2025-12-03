import pytest
from unittest.mock import MagicMock, patch
from src.storage.dlq import DLQHandler
from src.core.models import DeadLetterEntry
from src.config import settings
from sqlalchemy import create_engine, text

class TestDLQ:
    
    @pytest.fixture
    def dlq_handler(self):
        with patch('src.storage.dlq.create_engine'), \
             patch('src.storage.dlq.sessionmaker'), \
             patch.object(DLQHandler, '_ensure_table_exists'):
            return DLQHandler()

    @patch('src.storage.dlq.create_engine')
    @patch('src.storage.dlq.sessionmaker')
    def test_push_to_dlq(self, mock_sessionmaker, mock_create_engine):
        """Verify that a failed task is correctly pushed to Postgres DLQ (Mocked)."""
        
        # Setup mocks
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_sessionmaker.return_value = mock_session
        mock_db_session = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db_session
        
        # Re-init handler with mocks active
        handler = DLQHandler()
        
        # Mock data
        task_name = "test_task"
        payload = {"arg1": "value1"}
        error = ValueError("Simulated failure")
        retry_count = 3
        
        # Push to DLQ
        handler.push(task_name, payload, error, retry_count)
        
        # Verify insert was called
        # We check if session.execute was called
        assert mock_db_session.execute.called
        args, _ = mock_db_session.execute.call_args
        query = args[0]
        params = args[1]
        
        assert "INSERT INTO dead_letter_entries" in str(query)
        assert params['task_name'] == task_name
        assert params['error_message'] == "Simulated failure"
        assert params['retry_count'] == 3
        assert params['payload'] == payload

    def test_dlq_resilience(self, dlq_handler):
        """Verify DLQ handles DB errors gracefully (logs critical error but doesn't crash app logic if possible)."""
        # This is harder to test with real DB, but we can mock the session to raise exception
        with patch.object(dlq_handler, 'Session') as mock_session:
            mock_session.side_effect = Exception("DB Down")
            
            # Should raise DLQError
            with pytest.raises(Exception) as excinfo:
                dlq_handler.push("task", {}, ValueError("error"), 1)
            
            assert "Failed to write to DLQ" in str(excinfo.value)
