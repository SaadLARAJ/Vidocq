"""
VIDOCQ - Unified Intelligence Scoring System
Multi-factor confidence scoring inspired by CIA ACH methodology.

Factors:
1. LLM extraction confidence
2. Source trustworthiness (from SourceIntelligence)
3. Corroboration (multiple sources confirming)
4. Mission relevance
5. Contradiction penalty
6. Narrative war detection (NEW)
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

from src.core.logging import get_logger
from src.brain.source_analyst import SourceIntelligence, SourceOrigin

logger = get_logger(__name__)


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of how final score was computed"""
    llm_confidence: float = Field(ge=0, le=1, description="Raw LLM extraction confidence")
    source_trust: float = Field(ge=0, le=1, description="Source credibility from SourceIntelligence")
    corroboration_bonus: float = Field(ge=0, le=0.25, description="Bonus for multiple confirmations")
    mission_relevance: float = Field(ge=0, le=1, description="Relevance to current mission")
    contradiction_penalty: float = Field(ge=0, le=0.4, description="Penalty if contradicted")
    tangential_penalty: float = Field(ge=0, le=0.2, description="Penalty for off-topic entities")
    narrative_war_flag: bool = Field(default=False, description="True if claim is part of a narrative conflict")
    final_score: float = Field(ge=0, le=1, description="Computed final score")
    
    # Weights used
    weights: Dict[str, float] = {}


class VisibilityZone(str, Enum):
    """CIA-style visibility zones"""
    GREEN = "CONFIRMED"      # Score >= 0.75
    ORANGE = "UNVERIFIED"    # 0.45 <= Score < 0.75
    GREY = "QUARANTINE"      # Score < 0.45
    CONTESTED = "CONTESTED"  # Narrative war detected


class UnifiedScorer:
    """
    Multi-factor confidence scoring system.
    
    Inspired by Analysis of Competing Hypotheses (ACH) methodology.
    Combines multiple signals into a single trustworthiness score.
    
    v2.0: Integrated ContradictionDetector for narrative war detection.
    """
    
    # Configurable weights (sum to 1.0)
    WEIGHTS = {
        "llm": 0.25,
        "source": 0.30,
        "corroboration": 0.20,
        "relevance": 0.25
    }
    
    # Score thresholds for visibility zones
    THRESHOLD_CONFIRMED = 0.75
    THRESHOLD_UNVERIFIED = 0.45
    
    def __init__(self):
        self.source_intel = SourceIntelligence()
        self._contradiction_detector = None  # Lazy load
    
    @property
    def contradiction_detector(self):
        """Lazy load contradiction detector to avoid circular imports"""
        if self._contradiction_detector is None:
            try:
                from src.brain.contradiction_detector import ContradictionDetector
                self._contradiction_detector = ContradictionDetector()
            except Exception as e:
                logger.warning("contradiction_detector_unavailable", error=str(e))
        return self._contradiction_detector
    
    def compute_score(
        self,
        llm_confidence: float,
        source_url: str,
        corroboration_count: int = 1,
        mission_relevance: float = 0.5,
        is_contradiction: bool = False,
        is_tangential: bool = False,
        source_content: Optional[str] = None,
        narrative_war: bool = False
    ) -> ScoreBreakdown:
        """
        Compute unified confidence score for a claim.
        
        Args:
            llm_confidence: Raw confidence from LLM extraction (0-1)
            source_url: URL of the source document
            corroboration_count: How many sources confirm this claim
            mission_relevance: How relevant to current investigation (0-1)
            is_contradiction: Whether this claim contradicts existing data
            is_tangential: Whether entity is tangential to investigation
            source_content: Optional content for language detection
            narrative_war: Whether this claim is part of a narrative conflict
            
        Returns:
            ScoreBreakdown with all components and final score
        """
        # 1. Analyze source
        source_analysis = self.source_intel.analyze_source(source_url, source_content)
        source_trust = source_analysis.trust_score
        
        # Apply origin-based adjustments
        if source_analysis.origin == SourceOrigin.HOSTILE:
            source_trust *= 0.7  # Hostile sources get 30% trust reduction
        elif source_analysis.origin == SourceOrigin.UNKNOWN:
            source_trust *= 0.8  # Unknown sources get 20% reduction
        
        # 2. Compute corroboration bonus (capped at 0.25)
        corroboration_bonus = min((corroboration_count - 1) * 0.08, 0.25)
        
        # 3. Compute base score
        base_score = (
            llm_confidence * self.WEIGHTS["llm"] +
            source_trust * self.WEIGHTS["source"] +
            corroboration_bonus * self.WEIGHTS["corroboration"] +
            mission_relevance * self.WEIGHTS["relevance"]
        )
        
        # 4. Apply penalties
        contradiction_penalty = 0.0
        tangential_penalty = 0.0
        
        if is_contradiction:
            contradiction_penalty = 0.35
            base_score *= (1 - contradiction_penalty)
            
        if is_tangential:
            tangential_penalty = 0.15
            base_score *= (1 - tangential_penalty)
        
        # 5. Narrative war penalty (don't trust contested claims as much)
        if narrative_war:
            base_score *= 0.8  # 20% reduction for contested claims
        
        # 6. Clamp final score
        final_score = max(0.0, min(1.0, base_score))
        
        breakdown = ScoreBreakdown(
            llm_confidence=llm_confidence,
            source_trust=source_trust,
            corroboration_bonus=corroboration_bonus,
            mission_relevance=mission_relevance,
            contradiction_penalty=contradiction_penalty,
            tangential_penalty=tangential_penalty,
            narrative_war_flag=narrative_war,
            final_score=final_score,
            weights=self.WEIGHTS
        )
        
        logger.debug(
            "score_computed",
            final=final_score,
            source=source_url[:50],
            llm=llm_confidence,
            trust=source_trust,
            narrative_war=narrative_war
        )
        
        return breakdown
    
    def get_visibility_zone(self, score: float, narrative_war: bool = False) -> VisibilityZone:
        """Determine visibility zone based on score and narrative status"""
        if narrative_war:
            return VisibilityZone.CONTESTED
        elif score >= self.THRESHOLD_CONFIRMED:
            return VisibilityZone.GREEN
        elif score >= self.THRESHOLD_UNVERIFIED:
            return VisibilityZone.ORANGE
        else:
            return VisibilityZone.GREY
    
    async def detect_contradictions(
        self,
        target: str,
        claims: List[Dict[str, Any]],
        source_urls: List[str]
    ) -> Dict[str, Any]:
        """
        Run contradiction detection on a batch of claims.
        
        Returns contradiction report with narrative wars detected.
        """
        if not self.contradiction_detector:
            return {"narrative_wars": 0, "conflicts": []}
        
        try:
            report = await self.contradiction_detector.analyze(
                target=target,
                claims=claims,
                source_urls=source_urls
            )
            
            return {
                "narrative_wars": report.narrative_wars_detected,
                "conflicts": [c.model_dump() for c in report.conflicts],
                "alignment": report.overall_narrative_alignment,
                "propaganda_indicators": report.propaganda_indicators,
                "recommendation": report.recommendation
            }
        except Exception as e:
            logger.warning("contradiction_detection_failed", error=str(e))
            return {"narrative_wars": 0, "conflicts": [], "error": str(e)}
    
    def score_batch(
        self,
        claims: List[Dict[str, Any]],
        source_url: str,
        mission_relevance: float = 0.5,
        contested_topics: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Score a batch of claims and add visibility status.
        
        Each claim dict should have:
        - confidence: LLM confidence (optional, default 0.5)
        - is_tangential: bool (optional)
        - topic: str (optional, for narrative war detection)
        
        Args:
            contested_topics: List of topics that are under narrative war
        
        Returns claims with added:
        - unified_score: float
        - visibility_status: str
        - score_breakdown: dict
        """
        contested_topics = contested_topics or []
        scored_claims = []
        
        for claim in claims:
            llm_conf = claim.get("confidence", claim.get("confidence_score", 0.5))
            is_tangential = claim.get("is_tangential", False)
            topic = claim.get("topic", "")
            
            # Check if this claim's topic is contested
            is_contested = any(ct.lower() in topic.lower() for ct in contested_topics)
            
            breakdown = self.compute_score(
                llm_confidence=llm_conf,
                source_url=source_url,
                mission_relevance=mission_relevance,
                is_tangential=is_tangential,
                narrative_war=is_contested
            )
            
            claim["unified_score"] = breakdown.final_score
            claim["visibility_status"] = self.get_visibility_zone(
                breakdown.final_score, 
                narrative_war=breakdown.narrative_war_flag
            ).value
            claim["score_breakdown"] = {
                "source_trust": breakdown.source_trust,
                "corroboration": breakdown.corroboration_bonus,
                "relevance": breakdown.mission_relevance,
                "narrative_war": breakdown.narrative_war_flag
            }
            
            scored_claims.append(claim)
        
        return scored_claims


# Singleton for easy access
SCORER = UnifiedScorer()


def compute_unified_score(
    llm_confidence: float,
    source_url: str,
    corroboration_count: int = 1,
    mission_relevance: float = 0.5,
    is_contradiction: bool = False,
    is_tangential: bool = False,
    narrative_war: bool = False
) -> float:
    """
    Convenience function for computing unified score.
    Returns just the final score float.
    """
    breakdown = SCORER.compute_score(
        llm_confidence=llm_confidence,
        source_url=source_url,
        corroboration_count=corroboration_count,
        mission_relevance=mission_relevance,
        is_contradiction=is_contradiction,
        is_tangential=is_tangential,
        narrative_war=narrative_war
    )
    return breakdown.final_score


async def score_with_contradiction_check(
    target: str,
    claims: List[Dict[str, Any]],
    source_urls: List[str],
    mission_relevance: float = 0.5
) -> Dict[str, Any]:
    """
    Full scoring pipeline with automatic contradiction detection.
    
    1. Run contradiction detection
    2. Identify contested topics
    3. Score all claims with narrative war flags
    
    Returns:
        Dict with scored_claims and contradiction_report
    """
    # Step 1: Detect contradictions
    contradiction_report = await SCORER.detect_contradictions(
        target=target,
        claims=claims,
        source_urls=source_urls
    )
    
    # Step 2: Extract contested topics
    contested_topics = [
        c.get("topic", "") 
        for c in contradiction_report.get("conflicts", [])
    ]
    
    # Step 3: Score with narrative awareness
    # Need to transform claims for scoring
    claim_dicts = []
    for claim in claims:
        if hasattr(claim, 'model_dump'):
            claim_dicts.append(claim.model_dump())
        elif isinstance(claim, dict):
            claim_dicts.append(claim)
        else:
            claim_dicts.append({"claim": str(claim)})
    
    scored = SCORER.score_batch(
        claims=claim_dicts,
        source_url=source_urls[0] if source_urls else "",
        mission_relevance=mission_relevance,
        contested_topics=contested_topics
    )
    
    return {
        "scored_claims": scored,
        "contradiction_report": contradiction_report,
        "contested_topics": contested_topics
    }

