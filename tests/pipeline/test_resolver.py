import pytest
from unittest.mock import MagicMock, patch
from src.pipeline.resolver import EntityResolver
from src.core.models import EntityNode
from src.config import settings

class TestEntityResolution:
    
    @pytest.fixture
    def resolver(self):
        with patch('src.pipeline.queue.create_engine'), \
             patch('src.pipeline.queue.sessionmaker'), \
             patch('src.pipeline.queue.ResolutionQueue._ensure_table_exists'):
            return EntityResolver()

    def test_exact_match_merges(self, resolver):
        """Noms identiques = fusion automatique."""
        incoming = EntityNode(id="1", canonical_name="Jean Dupont", entity_type="PERSON")
        candidate = EntityNode(id="2", canonical_name="Jean Dupont", entity_type="PERSON")
        
        # Mock similarity to 1.0
        with patch.object(resolver, '_calculate_similarity', return_value=1.0):
            result = resolver.resolve(incoming, [candidate])
            assert result == "MERGED"

    def test_ambiguous_goes_to_queue(self, resolver):
        """Score entre 0.80 et seuil → HITL queue."""
        # Threshold PERSON = 0.92
        incoming = EntityNode(id="1", canonical_name="Jean Dupont", entity_type="PERSON")
        candidate = EntityNode(id="2", canonical_name="Jean Dupont (Lyon)", entity_type="PERSON")
        
        # Mock similarity to 0.85 (Ambiguous)
        with patch.object(resolver, '_calculate_similarity', return_value=0.85):
            with patch.object(resolver.queue, 'add') as mock_add:
                result = resolver.resolve(incoming, [candidate])
                assert result == "QUEUED"
                mock_add.assert_called_once()

    def test_low_score_no_merge(self, resolver):
        """Score < 0.80 = pas de relation."""
        incoming = EntityNode(id="1", canonical_name="Jean Dupont", entity_type="PERSON")
        candidate = EntityNode(id="2", canonical_name="Alice Smith", entity_type="PERSON")
        
        # Mock similarity to 0.10
        with patch.object(resolver, '_calculate_similarity', return_value=0.10):
            result = resolver.resolve(incoming, [candidate])
            assert result == "CREATED"

    def test_threshold_boundary_0_80(self, resolver):
        """Score = 0.80 exactement → queue."""
        incoming = EntityNode(id="1", canonical_name="A", entity_type="PERSON")
        candidate = EntityNode(id="2", canonical_name="B", entity_type="PERSON")
        
        with patch.object(resolver, '_calculate_similarity', return_value=0.80):
            with patch.object(resolver.queue, 'add') as mock_add:
                result = resolver.resolve(incoming, [candidate])
                assert result == "QUEUED"

    def test_threshold_boundary_exact(self, resolver):
        """Score = 0.919999 → queue (< 0.92)."""
        incoming = EntityNode(id="1", canonical_name="A", entity_type="PERSON")
        candidate = EntityNode(id="2", canonical_name="B", entity_type="PERSON")
        
        with patch.object(resolver, '_calculate_similarity', return_value=0.919999):
            with patch.object(resolver.queue, 'add') as mock_add:
                result = resolver.resolve(incoming, [candidate])
                assert result == "QUEUED"
