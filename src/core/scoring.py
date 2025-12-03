"""
ShadowMap Enterprise v4.0 - Confidence Scoring Engine

Implements deterministic confidence calculation using the V4 formula:
    C = min(MAX_CONFIDENCE, (S × M) × (1 + log₁₀(N) / DIVISOR))

Where:
    S = Source reliability weight (0.0 - 1.0)
    M = Method confidence weight (0.0 - 1.0)
    N = Corroboration count (>= 1, protected against zero)
    MAX_CONFIDENCE = 0.99 (never claim 100% certainty)
    DIVISOR = 10.0 (corroboration boost scaling factor)

All weights and thresholds come from src.config - ZERO magic numbers.
"""

import math
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class ConfidenceCalculator:
    """
    Deterministic confidence score calculator for claims and entity links.

    This class implements the V4 confidence formula with rigorous mathematical
    protections and full audit trail via structured logging.
    """

    @staticmethod
    def compute(
        source_domain: str,
        method: str,
        corroboration_count: int = 1,
    ) -> float:
        """
        Calculate confidence score for a claim or entity extraction.

        Args:
            source_domain: Domain of the source (e.g., "reuters.com", "twitter.com")
            method: Extraction method used (e.g., "gpt-4o", "spacy_ner")
            corroboration_count: Number of independent sources corroborating this claim.
                                 Must be >= 1. If 0 is passed, treated as 1.

        Returns:
            Confidence score between 0.0 and MAX_CONFIDENCE (0.99)

        Example:
            >>> calc = ConfidenceCalculator()
            >>> calc.compute("reuters.com", "gpt-4o", 1)
            0.855  # 0.95 * 0.90 = 0.855

            >>> calc.compute("reuters.com", "gpt-4o", 10)
            0.9405  # 0.855 * (1 + log10(10)/10) = 0.855 * 1.1 = 0.9405

            >>> calc.compute("telegram", "spacy_ner", 1)
            0.21  # 0.30 * 0.70 = 0.21
        """
        # Retrieve source reliability weight
        source_weight = settings.SOURCE_WEIGHTS.get(
            source_domain,
            settings.SOURCE_WEIGHTS["DEFAULT"]
        )

        # Retrieve method confidence weight
        method_weight = settings.METHOD_WEIGHTS.get(method)
        if method_weight is None:
            logger.warning(
                "unknown_extraction_method",
                method=method,
                source_domain=source_domain,
                fallback_weight=0.5,
            )
            method_weight = 0.5  # Conservative fallback

        # Calculate base score (S × M)
        base_score = source_weight * method_weight

        # Mathematical protection: corroboration count must be >= 1
        safe_corroboration_count = max(1, corroboration_count)

        if corroboration_count < 1:
            logger.warning(
                "invalid_corroboration_count",
                original_count=corroboration_count,
                corrected_to=safe_corroboration_count,
                source_domain=source_domain,
                method=method,
            )

        # Calculate corroboration boost: 1 + log₁₀(N) / DIVISOR
        corroboration_boost = 1.0 + (
            math.log10(safe_corroboration_count) / settings.CORROBORATION_DIVISOR
        )

        # Apply boost and cap at MAX_CONFIDENCE
        final_score = min(
            settings.MAX_CONFIDENCE,
            base_score * corroboration_boost
        )

        logger.debug(
            "confidence_calculated",
            source_domain=source_domain,
            source_weight=source_weight,
            method=method,
            method_weight=method_weight,
            corroboration_count=corroboration_count,
            base_score=base_score,
            corroboration_boost=corroboration_boost,
            final_score=final_score,
        )

        return final_score

    @staticmethod
    def compute_with_metadata(
        source_domain: str,
        method: str,
        corroboration_count: int = 1,
    ) -> dict[str, float]:
        """
        Calculate confidence score with full metadata breakdown.

        Useful for auditing, debugging, and explaining confidence scores
        to analysts via the HITL interface.

        Args:
            source_domain: Domain of the source
            method: Extraction method used
            corroboration_count: Number of corroborating sources

        Returns:
            Dictionary containing:
                - final_score: The computed confidence
                - source_weight: S component
                - method_weight: M component
                - base_score: S × M
                - corroboration_boost: 1 + log₁₀(N)/10
                - corroboration_count: Actual count used

        Example:
            >>> calc = ConfidenceCalculator()
            >>> calc.compute_with_metadata("reuters.com", "gpt-4o", 10)
            {
                "final_score": 0.9405,
                "source_weight": 0.95,
                "method_weight": 0.90,
                "base_score": 0.855,
                "corroboration_boost": 1.1,
                "corroboration_count": 10
            }
        """
        source_weight = settings.SOURCE_WEIGHTS.get(
            source_domain,
            settings.SOURCE_WEIGHTS["DEFAULT"]
        )
        method_weight = settings.METHOD_WEIGHTS.get(method, 0.5)
        base_score = source_weight * method_weight
        safe_count = max(1, corroboration_count)
        boost = 1.0 + (math.log10(safe_count) / settings.CORROBORATION_DIVISOR)
        final = min(settings.MAX_CONFIDENCE, base_score * boost)

        return {
            "final_score": final,
            "source_weight": source_weight,
            "method_weight": method_weight,
            "base_score": base_score,
            "corroboration_boost": boost,
            "corroboration_count": safe_count,
        }

    @staticmethod
    def get_merge_threshold(entity_type: str) -> float:
        """
        Retrieve the similarity threshold for entity merging.

        Args:
            entity_type: Type of entity (e.g., "PERSON", "ORGANIZATION")

        Returns:
            Similarity threshold (0.0 - 1.0) above which entities auto-merge

        Example:
            >>> ConfidenceCalculator.get_merge_threshold("PERSON")
            0.92
            >>> ConfidenceCalculator.get_merge_threshold("CRYPTO_WALLET")
            0.99
        """
        return settings.MERGE_THRESHOLDS.get(
            entity_type,
            settings.MERGE_THRESHOLDS["DEFAULT"]
        )

    @staticmethod
    def should_auto_merge(similarity_score: float, entity_type: str) -> bool:
        """
        Determine if two entities should be automatically merged.

        Args:
            similarity_score: Computed similarity (0.0 - 1.0)
            entity_type: Type of entity being compared

        Returns:
            True if score exceeds threshold for auto-merge, False otherwise

        Example:
            >>> ConfidenceCalculator.should_auto_merge(0.95, "PERSON")
            True  # 0.95 > 0.92 threshold
            >>> ConfidenceCalculator.should_auto_merge(0.85, "PERSON")
            False  # 0.85 < 0.92 threshold
        """
        threshold = ConfidenceCalculator.get_merge_threshold(entity_type)
        return similarity_score >= threshold

    @staticmethod
    def should_queue_for_hitl(similarity_score: float, entity_type: str) -> bool:
        """
        Determine if an ambiguous entity pair should go to HITL queue.

        Args:
            similarity_score: Computed similarity (0.0 - 1.0)
            entity_type: Type of entity being compared

        Returns:
            True if score is in ambiguous range [HITL_MINIMUM, threshold), False otherwise

        Example:
            >>> ConfidenceCalculator.should_queue_for_hitl(0.85, "PERSON")
            True  # 0.80 <= 0.85 < 0.92
            >>> ConfidenceCalculator.should_queue_for_hitl(0.75, "PERSON")
            False  # 0.75 < 0.80 minimum
        """
        threshold = ConfidenceCalculator.get_merge_threshold(entity_type)
        return (
            settings.HITL_MINIMUM_SCORE <= similarity_score < threshold
        )
