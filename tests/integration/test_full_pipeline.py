import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.api.main import app
from src.ingestion.tasks import ingest_url

client = TestClient(app)

class TestFullPipeline:
    
    @patch('src.ingestion.tasks.ingest_url.delay')
    def test_ingest_endpoint(self, mock_delay):
        """Verify /ingest endpoint triggers Celery task."""
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_delay.return_value = mock_task
        
        response = client.post(
            "/api/v1/ingest",
            json={"url": "https://example.com/article", "source_domain": "example.com"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"task_id": "task-123", "status": "processing"}
        mock_delay.assert_called_once()

    @patch('src.storage.vector.VectorStore.search_similar')
    def test_search_endpoint(self, mock_search):
        """Verify /search endpoint returns results."""
        mock_search.return_value = [{"id": "1", "score": 0.9, "payload": {}}]
        
        response = client.post(
            "/api/v1/search",
            json={"query": "test query", "limit": 5}
        )
        
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_status_endpoint(self):
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
