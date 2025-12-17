"""
VIDOCQ - Bayesian Belief Fusion
Multi-source intelligence fusion using Bayesian probability.

"Don't just average scores. Compute real probability."

Instead of: (0.8 + 0.6 + 0.4) / 3 = 0.6 (meaningless)
We compute: P(claim|sources) using Bayes' theorem

Features:
1. Source reliability as prior probability
2. Evidence strength as likelihood
3. Proper probabilistic fusion
4. Confidence intervals
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from dataclasses import dataclass
import math

from src.core.logging import get_logger
from src.brain.source_analyst import SourceIntelligence, SourceOrigin

logger = get_logger(__name__)


@dataclass
class SourceEvidence:
    """Evidence from a single source"""
    source_url: str
    supports_claim: bool          # True = confirms, False = denies
    confidence: float             # Source's stated confidence (0-1)
    source_reliability: float     # Source trustworthiness (0-1)
    origin: SourceOrigin = SourceOrigin.UNKNOWN


class BayesianFusionResult(BaseModel):
    """Result of Bayesian multi-source fusion"""
    posterior_probability: float = Field(ge=0, le=1, description="Final probability")
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    
    # Source breakdown
    supporting_sources: int = 0
    contradicting_sources: int = 0
    total_sources: int = 0
    
    # Quality metrics
    source_agreement: float = Field(ge=0, le=1, description="How much sources agree")
    evidence_strength: float = Field(ge=0, le=1, description="Overall evidence quality")
    
    # Interpretation
    verdict: str = "UNCERTAIN"
    reasoning: str = ""


class BayesianFusion:
    """
    Bayesian multi-source intelligence fusion.
    
    Uses Bayes' theorem to combine evidence from multiple sources
    into a single probability estimate.
    
    P(H|E1,E2,...) = P(E1,E2,...|H) * P(H) / P(E1,E2,...)
    
    Assumptions:
    - Sources are conditionally independent
    - Source reliability is known/estimated
    """
    
    # Default prior probability (no evidence)
    DEFAULT_PRIOR = 0.5
    
    # Reliability thresholds
    HIGH_RELIABILITY_THRESHOLD = 0.8
    LOW_RELIABILITY_THRESHOLD = 0.4
    
    def __init__(self):
        self.source_intel = SourceIntelligence()
    
    def fuse(
        self,
        evidences: List[SourceEvidence],
        prior: float = None
    ) -> BayesianFusionResult:
        """
        Fuse multiple source evidences using Bayesian inference.
        
        Args:
            evidences: List of evidence from different sources
            prior: Prior probability P(H) before seeing evidence
            
        Returns:
            BayesianFusionResult with posterior probability
        """
        if not evidences:
            return BayesianFusionResult(
                posterior_probability=prior or self.DEFAULT_PRIOR,
                verdict="NO_EVIDENCE",
                reasoning="No evidence provided"
            )
        
        # Start with prior
        prior_prob = prior if prior is not None else self.DEFAULT_PRIOR
        
        # Use log-odds for numerical stability
        log_odds = math.log(prior_prob / (1 - prior_prob + 1e-10))
        
        supporting = 0
        contradicting = 0
        reliability_sum = 0
        
        for evidence in evidences:
            # Likelihood ratio: P(E|H) / P(E|¬H)
            # Based on source reliability and whether it supports the claim
            
            rel = evidence.source_reliability
            conf = evidence.confidence
            
            # Effective evidence strength
            strength = rel * conf
            
            if evidence.supports_claim:
                # P(E|H) high, P(E|¬H) low
                likelihood_ratio = (0.5 + strength * 0.5) / (0.5 - strength * 0.4 + 0.1)
                supporting += 1
            else:
                # P(E|H) low, P(E|¬H) high
                likelihood_ratio = (0.5 - strength * 0.4 + 0.1) / (0.5 + strength * 0.5)
                contradicting += 1
            
            # Update log-odds
            log_odds += math.log(likelihood_ratio + 1e-10)
            reliability_sum += rel
        
        # Convert back to probability
        posterior = 1 / (1 + math.exp(-log_odds))
        posterior = max(0.01, min(0.99, posterior))  # Clamp
        
        # Calculate confidence interval (simple heuristic)
        n = len(evidences)
        avg_reliability = reliability_sum / n if n > 0 else 0.5
        interval_width = 0.3 * (1 - avg_reliability) * (1 / math.sqrt(n))
        
        lower = max(0, posterior - interval_width)
        upper = min(1, posterior + interval_width)
        
        # Source agreement
        if n > 1:
            agreement = 1 - (min(supporting, contradicting) / max(supporting, contradicting, 1))
        else:
            agreement = 1.0
        
        # Evidence strength
        evidence_strength = avg_reliability * (n / (n + 2))  # Bayesian-ish shrinkage
        
        # Verdict
        verdict, reasoning = self._interpret(
            posterior, supporting, contradicting, agreement, n
        )
        
        result = BayesianFusionResult(
            posterior_probability=posterior,
            confidence_interval=(lower, upper),
            supporting_sources=supporting,
            contradicting_sources=contradicting,
            total_sources=n,
            source_agreement=agreement,
            evidence_strength=evidence_strength,
            verdict=verdict,
            reasoning=reasoning
        )
        
        logger.debug(
            "bayesian_fusion_complete",
            posterior=posterior,
            sources=n,
            verdict=verdict
        )
        
        return result
    
    def fuse_claims(
        self,
        claims: List[Dict[str, Any]],
        claim_key: str = "claim"
    ) -> Dict[str, BayesianFusionResult]:
        """
        Fuse claims grouped by content.
        
        Groups similar claims and fuses their sources.
        
        Returns:
            Dict mapping claim content to fusion result
        """
        # Group claims by content
        claim_groups: Dict[str, List[SourceEvidence]] = {}
        
        for claim in claims:
            content = claim.get(claim_key, str(claim))
            source_url = claim.get("source_url", "")
            confidence = claim.get("confidence", 0.5)
            
            # Get source reliability
            if source_url:
                analysis = self.source_intel.analyze_source(source_url)
                reliability = analysis.trust_score
                origin = analysis.origin
            else:
                reliability = 0.5
                origin = SourceOrigin.UNKNOWN
            
            evidence = SourceEvidence(
                source_url=source_url,
                supports_claim=True,  # Claim existence = support
                confidence=confidence,
                source_reliability=reliability,
                origin=origin
            )
            
            if content not in claim_groups:
                claim_groups[content] = []
            claim_groups[content].append(evidence)
        
        # Fuse each group
        results = {}
        for content, evidences in claim_groups.items():
            results[content] = self.fuse(evidences)
        
        return results
    
    def _interpret(
        self,
        posterior: float,
        supporting: int,
        contradicting: int,
        agreement: float,
        total: int
    ) -> Tuple[str, str]:
        """Generate human-readable interpretation."""
        
        if total == 0:
            return "NO_EVIDENCE", "No evidence to analyze"
        
        if posterior >= 0.9:
            verdict = "HIGHLY_LIKELY"
            base = "Strong evidence supports this claim"
        elif posterior >= 0.75:
            verdict = "LIKELY"
            base = "Evidence supports this claim"
        elif posterior >= 0.6:
            verdict = "PROBABLE"
            base = "More evidence for than against"
        elif posterior >= 0.4:
            verdict = "UNCERTAIN"
            base = "Evidence is mixed or insufficient"
        elif posterior >= 0.25:
            verdict = "UNLIKELY"
            base = "Evidence suggests claim is false"
        else:
            verdict = "HIGHLY_UNLIKELY"
            base = "Strong evidence against this claim"
        
        # Add source context
        if contradicting > 0 and supporting > 0:
            base += f" ({supporting} sources support, {contradicting} contradict)"
            if agreement < 0.5:
                base += ". WARNING: High disagreement between sources."
        elif contradicting == 0:
            base += f" ({supporting} source{'s' if supporting > 1 else ''}, no contradiction)"
        
        return verdict, base
    
    def compute_corroboration_strength(
        self,
        evidences: List[SourceEvidence]
    ) -> float:
        """
        Compute how strong the corroboration is.
        
        Multiple independent, reliable sources = strong
        Single unreliable source = weak
        """
        if not evidences:
            return 0.0
        
        n = len(evidences)
        reliability_sum = sum(e.source_reliability for e in evidences)
        avg_reliability = reliability_sum / n
        
        # Check independence (simple: different domains)
        domains = set()
        for e in evidences:
            if e.source_url:
                try:
                    domain = e.source_url.split("/")[2]
                    domains.add(domain)
                except:
                    pass
        
        independence = len(domains) / max(n, 1)
        
        # Corroboration = f(sources, reliability, independence)
        # More sources, more reliable, more independent = stronger
        strength = (
            min(1.0, n / 5) *        # Up to 5 sources matters
            avg_reliability *         # Reliability
            (0.5 + 0.5 * independence) # Independence bonus
        )
        
        return min(1.0, strength)


# Singleton instance
FUSION = BayesianFusion()


def bayesian_fuse(
    claims: List[Dict[str, Any]],
    claim_key: str = "claim"
) -> Dict[str, BayesianFusionResult]:
    """
    Convenience function for Bayesian fusion.
    
    Usage:
        results = bayesian_fuse(claims)
        for claim, fusion in results.items():
            print(f"{claim}: {fusion.verdict} ({fusion.posterior_probability:.2f})")
    """
    return FUSION.fuse_claims(claims, claim_key)


def fuse_evidence(
    evidences: List[SourceEvidence],
    prior: float = 0.5
) -> BayesianFusionResult:
    """Convenience function for direct evidence fusion."""
    return FUSION.fuse(evidences, prior)
