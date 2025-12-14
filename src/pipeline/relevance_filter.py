"""
VIDOCQ - Expert Relevance Filter
Mission-Contextual Noise Elimination

"Un lien n'est jamais pertinent dans l'absolu. Il est pertinent par rapport à la mission."

This filter is the critical gatekeeper that transforms a "Scraper" into an "Intelligent Analyst".
It decides what goes into the final graph based on MISSION CONTEXT.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import google.generativeai as genai

from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


class MissionType(str, Enum):
    """Types of investigation missions - determines what's relevant"""
    SUPPLY_CHAIN = "SUPPLY_CHAIN"        # Industrial, logistics, R&D, critical shareholders
    FINANCIAL_CRIME = "FINANCIAL_CRIME"  # Money, holdings, offshore, family, sponsors
    INFLUENCE = "INFLUENCE"              # Media, politics, think tanks, donations
    GEOPOLITICAL = "GEOPOLITICAL"        # Resources, alliances, military, embargos
    GENERAL = "GENERAL"                  # Default: keep most things


class RelevanceDecision(BaseModel):
    """Decision from the relevance filter"""
    is_relevant: bool
    relevance_score: float = Field(ge=0, le=1)
    reason: str
    mission_type: MissionType


class FilterStats(BaseModel):
    """Statistics from filtering session"""
    total_processed: int = 0
    kept: int = 0
    discarded: int = 0
    average_score: float = 0.0
    top_discards: List[str] = []


class RelevanceFilter:
    """
    The Expert Relevance Filter - Mission-Contextual Noise Elimination.
    
    This is the critical gatekeeper between extraction and storage.
    It evaluates every claim/relation against the investigation mission.
    
    Rules:
    - SUPPLY_CHAIN: Keep industrial, logistics, R&D, critical shareholders
                    Discard: sponsors, charity, HR, hobbies
    - FINANCIAL_CRIME: Keep money, holdings, offshore, family, sponsors, art
                       Discard: pure operational/industrial
    - INFLUENCE: Keep media, politics, think tanks, donations
                 Discard: pure supply chain
    """
    
    # Minimum score to keep a relation (high bar for quality)
    MIN_RELEVANCE_SCORE = 0.6
    
    def __init__(self, mission_type: MissionType = MissionType.SUPPLY_CHAIN):
        self.mission_type = mission_type
        self.stats = FilterStats()
        
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self.model = None
            logger.warning("RelevanceFilter initialized without LLM - using rules only")
        
        # Rule-based patterns for fast filtering (no LLM needed)
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize rule-based patterns for fast filtering"""
        
        # Always discard these (noise across all missions)
        self.universal_noise = [
            "privacy policy", "politique de confidentialité",
            "terms of service", "conditions d'utilisation",
            "cookie", "newsletter", "subscribe",
            "contact us", "contactez-nous",
            "all rights reserved", "tous droits réservés",
            "copyright", "legal notice",
            "follow us", "share this", "tweet",
            "advertisement", "publicité",
            "related articles", "articles similaires",
            "comments", "commentaires",
            "login", "register", "signup",
            "search", "recherche",
            "menu", "navigation", "footer", "header"
        ]
        
        # Mission-specific relevance patterns
        self.mission_patterns = {
            MissionType.SUPPLY_CHAIN: {
                "keep": [
                    "supplier", "fournisseur", "supply", "approvisionnement",
                    "manufacturer", "fabricant", "factory", "usine",
                    "component", "composant", "raw material", "matière première",
                    "logistics", "logistique", "shipping", "transport",
                    "customer", "client", "contract", "contrat",
                    "partnership", "partenariat", "joint venture",
                    "subsidiary", "filiale", "acquisition", "merger",
                    "shareholder", "actionnaire", "investor", "investisseur",
                    "production", "manufacturing", "assembly",
                    "technology", "R&D", "patent", "brevet",
                    "export", "import", "trade"
                ],
                "discard": [
                    "sponsor", "sponsorship", "charity", "donation",
                    "hobby", "sport", "football", "ski",
                    "birthday", "wedding", "vacation",
                    "restaurant", "hotel", "travel",
                    "likes", "follows", "retweet"
                ]
            },
            MissionType.FINANCIAL_CRIME: {
                "keep": [
                    "bank", "banque", "account", "compte",
                    "offshore", "shell company", "société écran",
                    "holding", "trust", "foundation", "fondation",
                    "beneficial owner", "bénéficiaire effectif",
                    "money", "argent", "transfer", "virement",
                    "sanction", "OFAC", "SDN", "blacklist",
                    "panama", "cayman", "british virgin",
                    "family", "famille", "spouse", "wife", "husband",
                    "son", "daughter", "fils", "fille",
                    "art", "yacht", "real estate", "immobilier",
                    "luxury", "luxe", "sponsor", "donation",
                    "political", "politique", "contribution",
                    "corruption", "bribe", "fraud", "fraude"
                ],
                "discard": [
                    "factory output", "production volume",
                    "technical specification", "product feature",
                    "employee count", "hiring"
                ]
            },
            MissionType.INFLUENCE: {
                "keep": [
                    "media", "journalist", "press", "presse",
                    "politician", "politique", "minister", "ministre",
                    "parliament", "congress", "sénat", "assemblée",
                    "lobby", "lobbying", "think tank",
                    "NGO", "ONG", "foundation", "fondation",
                    "donation", "contribution", "funding",
                    "speech", "discours", "interview",
                    "social media", "twitter", "facebook",
                    "influence", "campaign", "campaign",
                    "advisor", "conseiller", "consultant"
                ],
                "discard": [
                    "factory", "manufacturing", "component",
                    "logistics", "shipping", "warehouse"
                ]
            },
            MissionType.GEOPOLITICAL: {
                "keep": [
                    "government", "gouvernement", "ministry", "ministère",
                    "military", "defense", "défense", "army", "armée",
                    "alliance", "treaty", "traité", "NATO", "OTAN",
                    "embargo", "sanction", "export control",
                    "resource", "ressource", "oil", "gas", "rare earth",
                    "strategic", "stratégique", "critical",
                    "border", "frontière", "territory", "territoire",
                    "conflict", "war", "guerre"
                ],
                "discard": [
                    "celebrity", "entertainment", "sport",
                    "tourism", "restaurant"
                ]
            }
        }
    
    async def evaluate(
        self,
        source_entity: str,
        relation: str,
        target_entity: str,
        context: Optional[str] = None,
        confidence: float = 0.5
    ) -> RelevanceDecision:
        """
        Evaluate if a relation is relevant to the current mission.
        
        Returns:
            RelevanceDecision with is_relevant, score, and reason
        """
        self.stats.total_processed += 1
        
        # Step 1: Quick rule-based check for universal noise
        combined_text = f"{source_entity} {relation} {target_entity} {context or ''}"
        combined_lower = combined_text.lower()
        
        for noise in self.universal_noise:
            if noise in combined_lower:
                decision = RelevanceDecision(
                    is_relevant=False,
                    relevance_score=0.0,
                    reason=f"Universal noise pattern: '{noise}'",
                    mission_type=self.mission_type
                )
                self.stats.discarded += 1
                self.stats.top_discards.append(f"{source_entity}->{target_entity}")
                return decision
        
        # Step 2: Rule-based mission pattern matching
        patterns = self.mission_patterns.get(self.mission_type, {})
        
        # Check for explicit discard patterns
        for pattern in patterns.get("discard", []):
            if pattern.lower() in combined_lower:
                decision = RelevanceDecision(
                    is_relevant=False,
                    relevance_score=0.2,
                    reason=f"Mission '{self.mission_type.value}' discard pattern: '{pattern}'",
                    mission_type=self.mission_type
                )
                self.stats.discarded += 1
                return decision
        
        # Check for explicit keep patterns (boost score)
        keep_matches = sum(
            1 for pattern in patterns.get("keep", [])
            if pattern.lower() in combined_lower
        )
        
        if keep_matches >= 2:
            # Strong match - definitely keep
            decision = RelevanceDecision(
                is_relevant=True,
                relevance_score=min(0.95, 0.7 + (keep_matches * 0.1)),
                reason=f"Strong match for {self.mission_type.value} ({keep_matches} patterns)",
                mission_type=self.mission_type
            )
            self.stats.kept += 1
            return decision
        
        # Step 3: For ambiguous cases, use LLM if available
        if self.model and keep_matches == 0:
            return await self._llm_evaluate(
                source_entity, relation, target_entity, context
            )
        
        # Step 4: Default decision based on confidence
        if keep_matches >= 1:
            is_relevant = confidence >= self.MIN_RELEVANCE_SCORE
            score = confidence * 0.8 + 0.2  # Slight boost for pattern match
        else:
            is_relevant = confidence >= 0.7  # Higher bar for no pattern match
            score = confidence * 0.6
        
        if is_relevant:
            self.stats.kept += 1
        else:
            self.stats.discarded += 1
        
        return RelevanceDecision(
            is_relevant=is_relevant,
            relevance_score=score,
            reason="Default evaluation based on confidence",
            mission_type=self.mission_type
        )
    
    async def _llm_evaluate(
        self,
        source_entity: str,
        relation: str,
        target_entity: str,
        context: Optional[str]
    ) -> RelevanceDecision:
        """Use LLM for ambiguous cases"""
        
        prompt = f"""RÔLE : Tu es le "Filtre de Pertinence" d'une IA de renseignement.
TA TÂCHE : Évaluer si cette information mérite d'être conservée.

MISSION ACTUELLE : {self.mission_type.value}

INFORMATION À ÉVALUER :
- SOURCE : {source_entity}
- RELATION : {relation}
- CIBLE : {target_entity}
- CONTEXTE : {context or 'Non disponible'}

RÈGLES DE DÉCISION :
- SUPPLY_CHAIN : Garde liens industriels, logistique, R&D, actionnariat. Jette sponsors, charité, hobbies.
- FINANCIAL_CRIME : Garde argent, holdings, offshore, famille, sponsors. Jette opérationnel pur.
- INFLUENCE : Garde médias, politique, think tanks, donations. Jette supply chain pure.
- GEOPOLITICAL : Garde ressources, alliances, militaire, embargos. Jette divertissement.

RÉPONDS UNIQUEMENT par JSON valide :
{{"is_relevant": true/false, "relevance_score": 0.0-1.0, "reason": "Explication courte"}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 200}
            )
            
            import json
            text = response.text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text)
            
            is_relevant = data.get("is_relevant", False)
            score = data.get("relevance_score", 0.5)
            
            # Apply minimum threshold
            if score < self.MIN_RELEVANCE_SCORE:
                is_relevant = False
            
            if is_relevant:
                self.stats.kept += 1
            else:
                self.stats.discarded += 1
            
            return RelevanceDecision(
                is_relevant=is_relevant,
                relevance_score=score,
                reason=data.get("reason", "LLM evaluation"),
                mission_type=self.mission_type
            )
            
        except Exception as e:
            logger.warning("llm_relevance_failed", error=str(e))
            # Default to keeping with moderate score
            self.stats.kept += 1
            return RelevanceDecision(
                is_relevant=True,
                relevance_score=0.6,
                reason="LLM evaluation failed, defaulting to keep",
                mission_type=self.mission_type
            )
    
    async def filter_batch(
        self,
        claims: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], FilterStats]:
        """
        Filter a batch of claims/relations.
        
        Args:
            claims: List of claim dicts with source, target, relation, confidence
        
        Returns:
            Tuple of (filtered_claims, stats)
        """
        filtered = []
        
        for claim in claims:
            decision = await self.evaluate(
                source_entity=claim.get("source", ""),
                relation=claim.get("relation", ""),
                target_entity=claim.get("target", ""),
                context=claim.get("context", ""),
                confidence=claim.get("confidence", 0.5)
            )
            
            if decision.is_relevant:
                claim["relevance_score"] = decision.relevance_score
                claim["relevance_reason"] = decision.reason
                filtered.append(claim)
            else:
                logger.debug(
                    "claim_filtered_out",
                    source=claim.get("source"),
                    target=claim.get("target"),
                    reason=decision.reason
                )
        
        # Update average score
        if self.stats.kept > 0:
            scores = [c.get("relevance_score", 0.5) for c in filtered]
            self.stats.average_score = sum(scores) / len(scores)
        
        # Limit top discards list
        self.stats.top_discards = self.stats.top_discards[-10:]
        
        logger.info(
            "batch_filter_complete",
            total=self.stats.total_processed,
            kept=self.stats.kept,
            discarded=self.stats.discarded,
            avg_score=self.stats.average_score
        )
        
        return filtered, self.stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        return {
            "mission_type": self.mission_type.value,
            "total_processed": self.stats.total_processed,
            "kept": self.stats.kept,
            "discarded": self.stats.discarded,
            "filter_rate": (
                self.stats.discarded / max(self.stats.total_processed, 1) * 100
            ),
            "average_relevance_score": self.stats.average_score,
            "min_threshold": self.MIN_RELEVANCE_SCORE
        }
    
    def reset_stats(self):
        """Reset statistics for new session"""
        self.stats = FilterStats()


# Convenience function for pipeline integration
async def filter_claims(
    claims: List[Dict[str, Any]],
    mission_type: MissionType = MissionType.SUPPLY_CHAIN
) -> List[Dict[str, Any]]:
    """
    Convenience function to filter claims with default settings.
    """
    filter_instance = RelevanceFilter(mission_type=mission_type)
    filtered, _ = await filter_instance.filter_batch(claims)
    return filtered
