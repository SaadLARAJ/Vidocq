# tests/core/test_scoring.py

import pytest
from src.core.scoring import ConfidenceCalculator

class TestConfidenceCalculator:
    
    def test_high_trust_source(self):
        """Reuters + GPT-4o = score élevé."""
        score = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 1)
        assert score == pytest.approx(0.855)  # 0.95 * 0.90

    def test_low_trust_source(self):
        """Telegram + SpaCy = score faible."""
        score = ConfidenceCalculator.compute("telegram", "spacy_ner", 1)
        assert score == pytest.approx(0.21)  # 0.30 * 0.70

    def test_corroboration_boost(self):
        """10 sources = boost de 10%."""
        base = ConfidenceCalculator.compute("nytimes.com", "gpt-4o", 1)
        boosted = ConfidenceCalculator.compute("nytimes.com", "gpt-4o", 10)
        assert boosted == pytest.approx(base * 1.1)

    def test_cap_at_99(self):
        """Jamais > 0.99."""
        score = ConfidenceCalculator.compute("reuters.com", "manual_verification", 100)
        assert score == 0.99

    def test_zero_corroboration_safe(self):
        """corroboration_count=0 ne crash pas."""
        score = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 0)
        assert score == pytest.approx(0.855)  # Traité comme 1
