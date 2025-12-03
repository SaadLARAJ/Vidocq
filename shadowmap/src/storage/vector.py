from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict, Any
from src.config import settings
from src.core.logging import get_logger
from src.core.exceptions import StorageError

logger = get_logger(__name__)

class VectorStore:
    """
    Qdrant vector storage handler.
    """
    
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists."""
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=1536, # OpenAI embedding size
                        distance=models.Distance.COSINE
                    )
                )
        except Exception as e:
            logger.error("qdrant_init_error", error=str(e))
            # Don't raise here to allow app startup even if Qdrant is flaky, 
            # but in strict mode we might want to.

    def upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """
        Batch upsert vectors.
        vectors list should contain dicts with: id, vector, payload
        """
        if not vectors:
            return

        points = [
            models.PointStruct(
                id=v["id"],
                vector=v["vector"],
                payload=v["payload"]
            ) for v in vectors
        ]
        
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info("batch_vectors_upserted", count=len(vectors))
        except Exception as e:
            logger.error("qdrant_upsert_error", error=str(e))
            raise StorageError(f"Failed to upsert vectors: {e}")

    def search_similar(self, vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit
            )
            return [
                {"id": r.id, "score": r.score, "payload": r.payload} 
                for r in results
            ]
        except Exception as e:
            logger.error("qdrant_search_error", error=str(e))
            return []
