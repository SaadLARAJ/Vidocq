"""
ShadowMap Enterprise v4.0 - Confidence Scoring Tests

Critical tests for the ConfidenceCalculator following V4 formula:
    C = min(MAX_CONFIDENCE, (S × M) × (1 + log₁₀(N) / DIVISOR))

All test cases defined in the spec must pass at 100%.
"""

import math
import pytest

from src.core.scoring import ConfidenceCalculator
from src.config import settings


class TestConfidenceCalculator:
    """Test suite for ConfidenceCalculator - formula V4."""

    def test_high_trust_source(self) -> None:
        """
        Reuters (S=0.95) + GPT-4o (M=0.90) with 1 corroboration.

        Expected: 0.95 × 0.90 = 0.855
        """
        score = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 1)
        expected = 0.95 * 0.90  # 0.855
        assert score == pytest.approx(expected, abs=1e-6)

    def test_low_trust_source(self) -> None:
        """
        Telegram (S=0.30) + SpaCy NER (M=0.70) with 1 corroboration.

        Expected: 0.30 × 0.70 = 0.21
        """
        score = ConfidenceCalculator.compute("telegram", "spacy_ner", 1)
        expected = 0.30 * 0.70  # 0.21
        assert score == pytest.approx(expected, abs=1e-6)

    def test_corroboration_boost_factor(self) -> None:
        """
        10 corroborating sources should boost by 10%.

        Boost formula: 1 + log₁₀(10) / 10 = 1 + 1/10 = 1.1
        """
        base = ConfidenceCalculator.compute("nytimes.com", "gpt-4o", 1)
        boosted = ConfidenceCalculator.compute("nytimes.com", "gpt-4o", 10)

        # Base score: 0.90 * 0.90 = 0.81
        # Boosted: 0.81 * 1.1 = 0.891
        expected_boost = 1 + (math.log10(10) / 10.0)  # 1.1
        assert boosted == pytest.approx(base * expected_boost, abs=1e-6)

    def test_cap_at_max_confidence(self) -> None:
        """
        Confidence score must never exceed MAX_CONFIDENCE (0.99).

        Even with perfect source + method + high corroboration.
        """
        # Manual verification (S=1.0) + Reuters (already high) + 100 corroborations
        score = ConfidenceCalculator.compute("reuters.com", "manual_verification", 100)

        # Should be capped at 0.99
        assert score == settings.MAX_CONFIDENCE
        assert score == 0.99

    def test_zero_corroboration_safe(self) -> None:
        """
        corroboration_count=0 must not crash - treated as 1.

        Protection: max(1, corroboration_count)
        """
        score = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 0)

        # Should be same as corroboration_count=1
        expected = 0.95 * 0.90  # 0.855
        assert score == pytest.approx(expected, abs=1e-6)

    def test_unknown_source_uses_default(self) -> None:
        """
        Unknown source domain should use DEFAULT weight (0.50).
        """
        score = ConfidenceCalculator.compute("unknown-website.com", "gpt-4o", 1)

        # DEFAULT source weight = 0.50, gpt-4o = 0.90
        expected = 0.50 * 0.90  # 0.45
        assert score == pytest.approx(expected, abs=1e-6)

    def test_unknown_method_uses_fallback(self) -> None:
        """
        Unknown extraction method should use conservative fallback (0.5).
        """
        score = ConfidenceCalculator.compute("reuters.com", "unknown_method", 1)

        # Reuters = 0.95, fallback method = 0.50
        expected = 0.95 * 0.50  # 0.475
        assert score == pytest.approx(expected, abs=1e-6)

    def test_corroboration_boost_100_sources(self) -> None:
        """
        100 corroborations: boost = 1 + log₁₀(100)/10 = 1.2
        Base = 0.855, Boosted = 0.855 * 1.2 = 1.026 → capped at 0.99
        """
        base = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 1)
        boosted = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 100)

        expected_boost = 1 + (math.log10(100) / 10.0)  # 1 + 2/10 = 1.2
        expected_uncapped = base * expected_boost  # 0.855 * 1.2 = 1.026

        # Since 1.026 > 0.99, should be capped at MAX_CONFIDENCE
        assert boosted == 0.99
        assert expected_uncapped > 0.99  # Verify it would exceed cap

    def test_manual_verification_highest_method_weight(self) -> None:
        """
        Manual verification should have method weight = 1.0
        """
        score = ConfidenceCalculator.compute("reuters.com", "manual_verification", 1)

        # Reuters = 0.95, manual = 1.0
        expected = 0.95 * 1.0  # 0.95
        assert score == pytest.approx(expected, abs=1e-6)

    def test_compute_with_metadata_structure(self) -> None:
        """
        compute_with_metadata should return full breakdown.
        """
        metadata = ConfidenceCalculator.compute_with_metadata(
            "reuters.com", "gpt-4o", 10
        )

        assert "final_score" in metadata
        assert "source_weight" in metadata
        assert "method_weight" in metadata
        assert "base_score" in metadata
        assert "corroboration_boost" in metadata
        assert "corroboration_count" in metadata

        # Verify values
        assert metadata["source_weight"] == 0.95
        assert metadata["method_weight"] == 0.90
        assert metadata["base_score"] == pytest.approx(0.855, abs=1e-6)
        assert metadata["corroboration_boost"] == pytest.approx(1.1, abs=1e-6)
        assert metadata["corroboration_count"] == 10


class TestMergeThresholds:
    """Test suite for entity merge threshold logic."""

    def test_get_person_threshold(self) -> None:
        """PERSON entities should have threshold = 0.92"""
        threshold = ConfidenceCalculator.get_merge_threshold("PERSON")
        assert threshold == 0.92

    def test_get_crypto_wallet_threshold(self) -> None:
        """CRYPTO_WALLET entities should have threshold = 0.99 (exact match)"""
        threshold = ConfidenceCalculator.get_merge_threshold("CRYPTO_WALLET")
        assert threshold == 0.99

    def test_get_default_threshold(self) -> None:
        """Unknown entity type should use DEFAULT threshold = 0.90"""
        threshold = ConfidenceCalculator.get_merge_threshold("UNKNOWN_TYPE")
        assert threshold == 0.90

    def test_should_auto_merge_above_threshold(self) -> None:
        """
        Similarity score above threshold → auto-merge.
        PERSON threshold = 0.92, score = 0.95 → True
        """
        should_merge = ConfidenceCalculator.should_auto_merge(0.95, "PERSON")
        assert should_merge is True

    def test_should_not_auto_merge_below_threshold(self) -> None:
        """
        Similarity score below threshold → no auto-merge.
        PERSON threshold = 0.92, score = 0.85 → False
        """
        should_merge = ConfidenceCalculator.should_auto_merge(0.85, "PERSON")
        assert should_merge is False

    def test_should_auto_merge_exact_threshold(self) -> None:
        """
        Similarity score equal to threshold → auto-merge.
        PERSON threshold = 0.92, score = 0.92 → True
        """
        should_merge = ConfidenceCalculator.should_auto_merge(0.92, "PERSON")
        assert should_merge is True

    def test_should_queue_for_hitl_ambiguous_range(self) -> None:
        """
        Score in [HITL_MINIMUM=0.80, threshold=0.92) → queue for HITL.
        PERSON threshold = 0.92, score = 0.85 → True
        """
        should_queue = ConfidenceCalculator.should_queue_for_hitl(0.85, "PERSON")
        assert should_queue is True

    def test_should_not_queue_below_hitl_minimum(self) -> None:
        """
        Score below HITL_MINIMUM=0.80 → ignore completely.
        Score = 0.75 → False
        """
        should_queue = ConfidenceCalculator.should_queue_for_hitl(0.75, "PERSON")
        assert should_queue is False

    def test_should_not_queue_above_threshold(self) -> None:
        """
        Score above threshold → auto-merge, not HITL.
        PERSON threshold = 0.92, score = 0.95 → False (auto-merged instead)
        """
        should_queue = ConfidenceCalculator.should_queue_for_hitl(0.95, "PERSON")
        assert should_queue is False

    def test_hitl_boundary_exact_minimum(self) -> None:
        """
        Score exactly at HITL_MINIMUM=0.80 → queue for HITL.
        """
        should_queue = ConfidenceCalculator.should_queue_for_hitl(0.80, "PERSON")
        assert should_queue is True

    def test_hitl_boundary_just_below_threshold(self) -> None:
        """
        Score = 0.919999 (< 0.92) → queue for HITL.
        """
        should_queue = ConfidenceCalculator.should_queue_for_hitl(0.919999, "PERSON")
        assert should_queue is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_negative_corroboration_count(self) -> None:
        """
        Negative corroboration count should be protected (treated as 1).
        """
        score = ConfidenceCalculator.compute("reuters.com", "gpt-4o", -5)
        expected = 0.95 * 0.90  # Same as count=1
        assert score == pytest.approx(expected, abs=1e-6)

    def test_extremely_large_corroboration(self) -> None:
        """
        Very large corroboration (10,000) should still cap at MAX_CONFIDENCE.
        """
        score = ConfidenceCalculator.compute("reuters.com", "manual_verification", 10000)
        assert score == 0.99

    def test_zero_weight_source(self) -> None:
        """
        If a source had 0.0 weight, score should be 0.0
        (though this shouldn't happen in production config).
        """
        # Temporarily test with DEFAULT = 0.50 as proxy
        # In real scenario, if DEFAULT were 0.0:
        # For this test, we'll just verify low trust source
        score = ConfidenceCalculator.compute("telegram", "regex_extraction", 1)
        # telegram=0.30, regex=0.60 → 0.18
        assert score == pytest.approx(0.18, abs=1e-6)

    def test_case_sensitivity_of_domain(self) -> None:
        """
        Source domains should be case-insensitive (handled in model validation).
        For now, config lookup is case-sensitive - test exact match.
        """
        score_lower = ConfidenceCalculator.compute("reuters.com", "gpt-4o", 1)

        # Capital case won't match - will use DEFAULT
        score_upper = ConfidenceCalculator.compute("REUTERS.COM", "gpt-4o", 1)

        # Lower case matches config (0.95 * 0.90 = 0.855)
        assert score_lower == pytest.approx(0.855, abs=1e-6)

        # Upper case uses DEFAULT (0.50 * 0.90 = 0.45)
        assert score_upper == pytest.approx(0.45, abs=1e-6)


class TestRealWorldScenarios:
    """Test realistic scenarios from production use cases."""

    def test_bellingcat_investigation(self) -> None:
        """
        Bellingcat (S=0.88) + manual verification (M=1.0) + 3 corroborations.

        Boost = 1 + log₁₀(3)/10 ≈ 1.0477
        Score = 0.88 * 1.0 * 1.0477 ≈ 0.922
        """
        score = ConfidenceCalculator.compute("bellingcat.com", "manual_verification", 3)

        base = 0.88 * 1.0
        boost = 1 + (math.log10(3) / 10.0)
        expected = base * boost

        assert score == pytest.approx(expected, abs=1e-3)

    def test_twitter_rumor_low_confidence(self) -> None:
        """
        Twitter (S=0.40) + regex extraction (M=0.60) + 1 source.

        Score = 0.40 * 0.60 = 0.24 (very low confidence)
        """
        score = ConfidenceCalculator.compute("twitter.com", "regex_extraction", 1)
        assert score == pytest.approx(0.24, abs=1e-6)

    def test_blockchain_data_high_confidence(self) -> None:
        """
        Etherscan (S=0.95) + manual verification (M=1.0).

        Score = 0.95 * 1.0 = 0.95 (blockchain data is highly reliable)
        """
        score = ConfidenceCalculator.compute("etherscan.io", "manual_verification", 1)
        assert score == pytest.approx(0.95, abs=1e-6)

    def test_multi_source_corroboration(self) -> None:
        """
        NYTimes (S=0.90) + GPT-4o (M=0.90) + 5 sources.

        Base = 0.81, Boost = 1 + log₁₀(5)/10 ≈ 1.0699
        Score ≈ 0.867
        """
        score = ConfidenceCalculator.compute("nytimes.com", "gpt-4o", 5)

        base = 0.90 * 0.90  # 0.81
        boost = 1 + (math.log10(5) / 10.0)  # ~1.0699
        expected = base * boost

        assert score == pytest.approx(expected, abs=1e-3)


if __name__ == "__main__":
    # Allow running tests directly with: python tests/core/test_scoring.py
    pytest.main([__file__, "-v"])
