import pytest
from unittest.mock import MagicMock, patch
from src.storage.graph import GraphStore
from src.core.models import EntityNode
import time

class TestGraphPerformance:
    
    @patch('src.storage.graph.GraphDatabase')
    def test_batch_insert_performance(self, mock_graph_db):
        """
        Verify batch insert logic handles large lists efficiently.
        Since we mock the DB, we mainly verify the UNWIND query structure and data passing.
        """
        # Setup Mock
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        store = GraphStore()
        
        # Generate 1000 entities
        entities = [
            EntityNode(
                id=f"ent_{i}", 
                canonical_name=f"Entity {i}", 
                entity_type="PERSON"
            ) for i in range(1000)
        ]
        
        start_time = time.time()
        store.merge_entities_batch(entities)
        end_time = time.time()
        
        # Verify call
        assert mock_session.run.called
        args, kwargs = mock_session.run.call_args
        query = args[0]
        params = kwargs
        
        assert "UNWIND $entities AS entity" in query
        assert len(params['entities']) == 1000
        
        print(f"Batch processing time (mocked): {end_time - start_time:.4f}s")
