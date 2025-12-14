"""
VIDOCQ BRAIN - Contradiction Detector
Detects narrative warfare by showing CONFLICTS instead of averaging scores.

"Ne lisse pas le score. Affiche le conflit : Guerre Narrative détectée."

Features:
- Detect when Western and Eastern sources disagree
- Show the conflict explicitly, not a meaningless average
- Highlight propaganda patterns
- Score by bloc credibility, not overall average
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum

from src.brain.source_analyst import SourceIntelligence, SourceOrigin, SourceAnalysis
from src.core.logging import get_logger

logger = get_logger(__name__)


class NarrativeStance(str, Enum):
    """Position on a narrative"""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    CONFLICTED = "CONFLICTED"


class NarrativeConflict(BaseModel):
    """A detected conflict between information blocs"""
    topic: str
    western_stance: NarrativeStance
    western_claim: str
    western_sources: List[str]
    hostile_stance: NarrativeStance
    hostile_claim: str
    hostile_sources: List[str]
    conflict_severity: float = Field(ge=0, le=1)
    likely_truth: Optional[str] = None
    analysis: str


class ContradictionReport(BaseModel):
    """Complete contradiction analysis report"""
    target: str
    narrative_wars_detected: int
    conflicts: List[NarrativeConflict]
    overall_narrative_alignment: float = Field(ge=0, le=1, description="1=full agreement, 0=total contradiction")
    dominant_narrative: Optional[str] = None
    propaganda_indicators: List[str] = []
    recommendation: str


class ContradictionDetector:
    """
    Detects narrative warfare between information blocs.
    
    Instead of averaging confidence scores (which produces meaningless gray),
    this module explicitly shows WHERE sources disagree.
    
    "Reuters says WHITE (0.9), RT says BLACK (0.2)"
    → OLD: Average = 0.55 (meaningless gray)
    → NEW: "NARRATIVE WAR DETECTED. Western sources claim X, Eastern sources claim Y."
    """
    
    def __init__(self):
        self.source_intel = SourceIntelligence()
        
        # Keywords that indicate stance on common topics
        self.stance_indicators = {
            "positive": [
                "success", "growth", "profit", "partnership", "agreement",
                "legitimate", "approved", "cleared", "innocent", "legal"
            ],
            "negative": [
                "failure", "decline", "loss", "conflict", "violation",
                "sanctions", "corrupt", "illegal", "fraud", "crime"
            ]
        }
        
        # Known propaganda patterns by source origin
        self.propaganda_patterns = {
            SourceOrigin.HOSTILE: [
                "state-controlled media",
                "known disinformation outlet",
                "no independent verification"
            ],
            SourceOrigin.WESTERN: [
                "government-aligned narrative",
                "limited sourcing"
            ]
        }
    
    async def analyze(
        self,
        target: str,
        claims: List[Dict[str, Any]],
        source_urls: List[str]
    ) -> ContradictionReport:
        """
        Analyze claims for narrative contradictions.
        
        Claims should be a list of:
        {
            "claim": "The company is profitable",
            "source_url": "https://...",
            "confidence": 0.8
        }
        """
        logger.info("contradiction_analysis_started", target=target)
        
        # Step 1: Cluster sources by origin
        source_analyses = {url: self.source_intel.analyze_source(url) for url in source_urls}
        
        western_sources = [
            url for url, analysis in source_analyses.items() 
            if analysis.origin == SourceOrigin.WESTERN
        ]
        hostile_sources = [
            url for url, analysis in source_analyses.items() 
            if analysis.origin == SourceOrigin.HOSTILE
        ]
        
        # Step 2: Cluster claims by source origin
        western_claims = [c for c in claims if c.get("source_url") in western_sources]
        hostile_claims = [c for c in claims if c.get("source_url") in hostile_sources]
        
        # Step 3: Detect conflicts
        conflicts = self._detect_conflicts(target, western_claims, hostile_claims)
        
        # Step 4: Detect propaganda patterns
        propaganda_indicators = self._detect_propaganda(source_analyses)
        
        # Step 5: Calculate overall alignment
        if conflicts:
            alignment = 1 - (sum(c.conflict_severity for c in conflicts) / len(conflicts))
        else:
            alignment = 1.0
        
        # Step 6: Determine dominant narrative
        dominant = self._determine_dominant_narrative(western_claims, hostile_claims)
        
        # Step 7: Generate recommendation
        recommendation = self._generate_recommendation(conflicts, alignment, propaganda_indicators)
        
        report = ContradictionReport(
            target=target,
            narrative_wars_detected=len(conflicts),
            conflicts=conflicts,
            overall_narrative_alignment=alignment,
            dominant_narrative=dominant,
            propaganda_indicators=propaganda_indicators,
            recommendation=recommendation
        )
        
        logger.info(
            "contradiction_analysis_complete",
            target=target,
            conflicts=len(conflicts),
            alignment=alignment
        )
        
        return report
    
    def _detect_conflicts(
        self,
        target: str,
        western_claims: List[Dict],
        hostile_claims: List[Dict]
    ) -> List[NarrativeConflict]:
        """Detect where Western and Hostile sources disagree."""
        
        conflicts = []
        
        # Extract topics from claims
        western_topics = self._extract_topics(western_claims)
        hostile_topics = self._extract_topics(hostile_claims)
        
        # Find common topics
        common_topics = set(western_topics.keys()) & set(hostile_topics.keys())
        
        for topic in common_topics:
            western_stance = self._determine_stance(western_topics[topic])
            hostile_stance = self._determine_stance(hostile_topics[topic])
            
            # Check if stances conflict
            if self._stances_conflict(western_stance, hostile_stance):
                conflict = NarrativeConflict(
                    topic=topic,
                    western_stance=western_stance,
                    western_claim=self._summarize_claims(western_topics[topic]),
                    western_sources=[c.get("source_url", "") for c in western_topics[topic][:3]],
                    hostile_stance=hostile_stance,
                    hostile_claim=self._summarize_claims(hostile_topics[topic]),
                    hostile_sources=[c.get("source_url", "") for c in hostile_topics[topic][:3]],
                    conflict_severity=self._calculate_conflict_severity(western_stance, hostile_stance),
                    likely_truth=self._assess_likely_truth(western_topics[topic], hostile_topics[topic]),
                    analysis=self._generate_conflict_analysis(topic, western_stance, hostile_stance)
                )
                conflicts.append(conflict)
        
        # Also check for one-sided narratives (only one side mentions something)
        western_only = set(western_topics.keys()) - set(hostile_topics.keys())
        hostile_only = set(hostile_topics.keys()) - set(western_topics.keys())
        
        # One-sided negative claims are suspicious
        for topic in western_only:
            stance = self._determine_stance(western_topics[topic])
            if stance == NarrativeStance.NEGATIVE:
                conflicts.append(NarrativeConflict(
                    topic=topic,
                    western_stance=stance,
                    western_claim=self._summarize_claims(western_topics[topic]),
                    western_sources=[c.get("source_url", "") for c in western_topics[topic][:3]],
                    hostile_stance=NarrativeStance.NEUTRAL,
                    hostile_claim="Aucune mention de ce sujet",
                    hostile_sources=[],
                    conflict_severity=0.5,
                    analysis="Narrative occidentale unilatérale. Vérifier indépendamment."
                ))
        
        return conflicts
    
    def _extract_topics(self, claims: List[Dict]) -> Dict[str, List[Dict]]:
        """Group claims by topic."""
        topics = {}
        
        # Simple topic extraction based on keywords
        topic_keywords = {
            "financial": ["profit", "loss", "revenue", "billion", "million", "stock"],
            "legal": ["sanction", "court", "lawsuit", "illegal", "regulation", "compliance"],
            "political": ["government", "minister", "election", "policy", "diplomatic"],
            "ownership": ["acquisition", "shareholder", "owner", "buy", "sell", "stake"],
            "operational": ["factory", "production", "supply", "employee", "operation"]
        }
        
        for claim in claims:
            claim_text = claim.get("claim", "").lower()
            assigned = False
            
            for topic, keywords in topic_keywords.items():
                if any(kw in claim_text for kw in keywords):
                    if topic not in topics:
                        topics[topic] = []
                    topics[topic].append(claim)
                    assigned = True
                    break
            
            if not assigned:
                if "general" not in topics:
                    topics["general"] = []
                topics["general"].append(claim)
        
        return topics
    
    def _determine_stance(self, claims: List[Dict]) -> NarrativeStance:
        """Determine overall stance from a list of claims."""
        
        positive_count = 0
        negative_count = 0
        
        for claim in claims:
            text = claim.get("claim", "").lower()
            
            if any(word in text for word in self.stance_indicators["positive"]):
                positive_count += 1
            if any(word in text for word in self.stance_indicators["negative"]):
                negative_count += 1
        
        if positive_count > negative_count * 2:
            return NarrativeStance.POSITIVE
        elif negative_count > positive_count * 2:
            return NarrativeStance.NEGATIVE
        elif positive_count > 0 and negative_count > 0:
            return NarrativeStance.CONFLICTED
        else:
            return NarrativeStance.NEUTRAL
    
    def _stances_conflict(self, stance1: NarrativeStance, stance2: NarrativeStance) -> bool:
        """Check if two stances are contradictory."""
        conflicts = [
            (NarrativeStance.POSITIVE, NarrativeStance.NEGATIVE),
            (NarrativeStance.NEGATIVE, NarrativeStance.POSITIVE)
        ]
        return (stance1, stance2) in conflicts
    
    def _calculate_conflict_severity(self, stance1: NarrativeStance, stance2: NarrativeStance) -> float:
        """Calculate how severe the conflict is."""
        if stance1 == NarrativeStance.POSITIVE and stance2 == NarrativeStance.NEGATIVE:
            return 0.9
        elif stance1 == NarrativeStance.NEGATIVE and stance2 == NarrativeStance.POSITIVE:
            return 0.9
        elif NarrativeStance.CONFLICTED in (stance1, stance2):
            return 0.5
        else:
            return 0.3
    
    def _summarize_claims(self, claims: List[Dict]) -> str:
        """Summarize multiple claims into one sentence."""
        if not claims:
            return "Aucune donnée"
        
        # Take the first claim as representative
        first = claims[0].get("claim", "")[:200]
        if len(claims) > 1:
            return f"{first} (+{len(claims)-1} autres)"
        return first
    
    def _assess_likely_truth(self, western_claims: List, hostile_claims: List) -> Optional[str]:
        """Assess which narrative is more likely true based on source credibility."""
        
        # Calculate weighted credibility
        western_credibility = sum(c.get("confidence", 0.5) for c in western_claims) / max(len(western_claims), 1)
        hostile_credibility = sum(c.get("confidence", 0.5) for c in hostile_claims) / max(len(hostile_claims), 1)
        
        # Apply source bias discount (state media gets penalty)
        hostile_credibility *= 0.7  # Discount for potential propaganda
        
        if western_credibility > hostile_credibility * 1.5:
            return "Narrative occidentale plus crédible (sources indépendantes majoritaires)"
        elif hostile_credibility > western_credibility * 1.5:
            return "ATTENTION: Narrative adverse dominante malgré biais de source"
        else:
            return "Vérité indéterminable - sources en conflit direct"
    
    def _generate_conflict_analysis(
        self, 
        topic: str, 
        western_stance: NarrativeStance, 
        hostile_stance: NarrativeStance
    ) -> str:
        """Generate human-readable conflict analysis."""
        return (
            f"GUERRE NARRATIVE sur '{topic}': "
            f"Sources occidentales: {western_stance.value}. "
            f"Sources adverses: {hostile_stance.value}. "
            f"Contradiction directe détectée."
        )
    
    def _detect_propaganda(self, source_analyses: Dict[str, SourceAnalysis]) -> List[str]:
        """Detect propaganda patterns in sources."""
        indicators = []
        
        hostile_count = sum(
            1 for s in source_analyses.values() 
            if s.origin == SourceOrigin.HOSTILE
        )
        
        if hostile_count > 0:
            indicators.append(f"{hostile_count} sources de médias d'État/adverses détectées")
        
        # Check for low-trust sources
        low_trust = [
            s.domain for s in source_analyses.values() 
            if s.trust_score < 0.4
        ]
        
        if low_trust:
            indicators.append(f"Sources à faible crédibilité: {', '.join(low_trust[:3])}")
        
        return indicators
    
    def _determine_dominant_narrative(
        self, 
        western_claims: List, 
        hostile_claims: List
    ) -> Optional[str]:
        """Determine which narrative dominates by volume and credibility."""
        
        if len(western_claims) > len(hostile_claims) * 2:
            return "Narrative occidentale dominante (volume supérieur)"
        elif len(hostile_claims) > len(western_claims) * 2:
            return "ALERTE: Narrative adverse dominante"
        else:
            return "Narratives équilibrées - conflit ouvert"
    
    def _generate_recommendation(
        self,
        conflicts: List[NarrativeConflict],
        alignment: float,
        propaganda_indicators: List[str]
    ) -> str:
        """Generate actionable recommendation."""
        
        if len(conflicts) >= 3:
            return (
                "GUERRE INFORMATIONNELLE ACTIVE. Ne pas se fier aux sources médiatiques. "
                "Requiert vérification par sources primaires (documents officiels, témoins directs)."
            )
        elif len(conflicts) >= 1 and alignment < 0.5:
            return (
                "Contradictions significatives détectées. Croiser systématiquement avec "
                "des sources neutres (Reuters, AP, documents officiels)."
            )
        elif propaganda_indicators:
            return (
                "Présence de sources de propagande. Privilégier les sources vérifiées "
                "et indépendantes pour toute décision basée sur ces informations."
            )
        else:
            return "Consensus narratif acceptable. Niveau de confiance standard."
