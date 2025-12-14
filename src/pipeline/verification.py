"""
ShadowMap Verification Agent (Agent Critique)
Double-checks extracted entities against trusted sources.
Reduces hallucinations by validating LLM extractions.
"""

import httpx
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.core.logging import get_logger
from src.core.sources import data_sources

logger = get_logger(__name__)


class VerificationStatus(Enum):
    """Verification result status."""
    VERIFIED = "VERIFIED"           # Found in trusted source
    PARTIALLY_VERIFIED = "PARTIAL"  # Found but with differences
    UNVERIFIED = "UNVERIFIED"       # Not found in any source
    SANCTIONED = "SANCTIONED"       # Found in sanctions list (HIGH RISK)
    SKIPPED = "SKIPPED"             # Verification disabled


@dataclass
class VerificationResult:
    """Result of entity verification."""
    entity_name: str
    status: VerificationStatus
    confidence_adjustment: float  # Multiplier: 1.0 = no change, 0.5 = halved
    sources_checked: List[str]
    matches_found: List[Dict[str, Any]]
    risk_flags: List[str]
    verification_notes: str


class VerificationAgent:
    """
    The "Agent Critique" - Validates extracted entities.
    
    Workflow:
    1. Check entity in Wikidata (existence + basic facts)
    2. Check entity in OpenSanctions (risk screening)
    3. Adjust confidence score based on findings
    4. Flag unverified entities as LOW_CONFIDENCE
    """
    
    def __init__(self):
        self.timeout = 10  # seconds per API call
        self.min_confidence_threshold = 0.3  # Below this = likely hallucination
    
    def verify_entity(self, entity_name: str, entity_type: str) -> VerificationResult:
        """
        Verify a single entity against all available sources.
        Returns verification result with confidence adjustment.
        """
        sources_checked = []
        matches_found = []
        risk_flags = []
        
        # Track verification status
        wikidata_match = None
        sanctions_match = None
        
        # === CHECK 1: Wikidata (Existence Validation) ===
        if data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_WIKIDATA:
            wikidata_match = self._check_wikidata(entity_name)
            sources_checked.append("Wikidata")
            if wikidata_match:
                matches_found.append({"source": "Wikidata", **wikidata_match})
        
        # === CHECK 2: OpenSanctions (Risk Screening) ===
        if data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_OPENSANCTIONS:
            sanctions_match = self._check_opensanctions(entity_name)
            sources_checked.append("OpenSanctions")
            if sanctions_match:
                matches_found.append({"source": "OpenSanctions", **sanctions_match})
                if sanctions_match.get("is_sanctioned"):
                    risk_flags.append("SANCTIONED_ENTITY")
        
        # === FALLBACK: Quick Google verification via Gemini ===
        if not sources_checked:
            # If no premium sources enabled, use LLM to verify
            llm_check = self._quick_llm_verify(entity_name, entity_type)
            sources_checked.append("LLM_QuickCheck")
            if llm_check["exists"]:
                matches_found.append({"source": "LLM", **llm_check})
        
        # === DETERMINE STATUS & CONFIDENCE ADJUSTMENT ===
        return self._compute_result(
            entity_name=entity_name,
            entity_type=entity_type,
            sources_checked=sources_checked,
            matches_found=matches_found,
            risk_flags=risk_flags,
            wikidata_match=wikidata_match,
            sanctions_match=sanctions_match
        )
    
    def _check_wikidata(self, entity_name: str) -> Optional[Dict]:
        """Check if entity exists in Wikidata."""
        try:
            url = "https://www.wikidata.org/w/api.php"
            params = {
                "action": "wbsearchentities",
                "search": entity_name,
                "language": "en",
                "limit": 3,
                "format": "json"
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = data.get("search", [])
            if results:
                best = results[0]
                return {
                    "wikidata_id": best.get("id"),
                    "label": best.get("label"),
                    "description": best.get("description"),
                    "match_score": 1.0 if best.get("label", "").lower() == entity_name.lower() else 0.7
                }
            return None
            
        except Exception as e:
            logger.warning("wikidata_check_failed", entity=entity_name, error=str(e))
            return None
    
    def _check_opensanctions(self, entity_name: str) -> Optional[Dict]:
        """Check if entity is in sanctions/PEP lists."""
        try:
            url = f"{data_sources.OPENSANCTIONS_API_URL}/search/default"
            params = {"q": entity_name, "limit": 3}
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = data.get("results", [])
            if results:
                best = results[0]
                datasets = best.get("datasets", [])
                is_sanctioned = any("sanction" in d.lower() for d in datasets)
                
                return {
                    "opensanctions_id": best.get("id"),
                    "caption": best.get("caption"),
                    "schema": best.get("schema"),
                    "datasets": datasets,
                    "is_sanctioned": is_sanctioned,
                    "is_pep": any("pep" in d.lower() for d in datasets)
                }
            return None
            
        except Exception as e:
            logger.warning("opensanctions_check_failed", entity=entity_name, error=str(e))
            return None
    
    def _quick_llm_verify(self, entity_name: str, entity_type: str) -> Dict:
        """
        Use Gemini for quick existence check.
        Only used when premium sources are disabled.
        """
        try:
            import google.generativeai as genai
            from src.config import settings
            
            if not settings.GEMINI_API_KEY:
                return {"exists": False, "reason": "No API key"}
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            prompt = f"""Quick fact check: Is "{entity_name}" a real {entity_type}?
Answer ONLY with JSON: {{"exists": true/false, "confidence": 0.0-1.0, "note": "brief reason"}}"""
            
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 100}
            )
            
            text = response.text.strip()
            if text.startswith("```"): text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
            
            import json
            result = json.loads(text)
            return result
            
        except Exception as e:
            logger.warning("llm_verify_failed", entity=entity_name, error=str(e))
            return {"exists": False, "reason": str(e)}
    
    def _compute_result(
        self,
        entity_name: str,
        entity_type: str,
        sources_checked: List[str],
        matches_found: List[Dict],
        risk_flags: List[str],
        wikidata_match: Optional[Dict],
        sanctions_match: Optional[Dict]
    ) -> VerificationResult:
        """Compute final verification status and confidence adjustment."""
        
        # No sources checked = skip
        if not sources_checked:
            return VerificationResult(
                entity_name=entity_name,
                status=VerificationStatus.SKIPPED,
                confidence_adjustment=1.0,
                sources_checked=[],
                matches_found=[],
                risk_flags=[],
                verification_notes="Verification disabled"
            )
        
        # Sanctioned entity = HIGH RISK but VERIFIED
        if sanctions_match and sanctions_match.get("is_sanctioned"):
            return VerificationResult(
                entity_name=entity_name,
                status=VerificationStatus.SANCTIONED,
                confidence_adjustment=1.2,  # Boost confidence (it's real!)
                sources_checked=sources_checked,
                matches_found=matches_found,
                risk_flags=["SANCTIONED_ENTITY", "HIGH_RISK"],
                verification_notes=f"Entity found in sanctions database: {sanctions_match.get('datasets')}"
            )
        
        # Found in Wikidata = VERIFIED
        if wikidata_match:
            adjustment = wikidata_match.get("match_score", 0.8)
            return VerificationResult(
                entity_name=entity_name,
                status=VerificationStatus.VERIFIED,
                confidence_adjustment=1.0 + (adjustment * 0.2),  # Slight boost
                sources_checked=sources_checked,
                matches_found=matches_found,
                risk_flags=risk_flags,
                verification_notes=f"Verified via Wikidata: {wikidata_match.get('description', 'N/A')}"
            )
        
        # Found in OpenSanctions but not sanctioned = PEP or known entity
        if sanctions_match:
            return VerificationResult(
                entity_name=entity_name,
                status=VerificationStatus.PARTIALLY_VERIFIED,
                confidence_adjustment=1.0,
                sources_checked=sources_checked,
                matches_found=matches_found,
                risk_flags=risk_flags if risk_flags else ["PEP_OR_KNOWN_ENTITY"],
                verification_notes=f"Found in OpenSanctions (not sanctioned): {sanctions_match.get('schema')}"
            )
        
        # Not found anywhere = UNVERIFIED (potential hallucination)
        return VerificationResult(
            entity_name=entity_name,
            status=VerificationStatus.UNVERIFIED,
            confidence_adjustment=0.5,  # Halve confidence
            sources_checked=sources_checked,
            matches_found=[],
            risk_flags=["UNVERIFIED", "LOW_CONFIDENCE"],
            verification_notes="Entity not found in any trusted source. May be hallucination or niche entity."
        )
    
    def verify_batch(self, entities: List[Dict[str, str]]) -> List[VerificationResult]:
        """
        Verify multiple entities.
        Input: [{"name": "Entity Name", "type": "ORGANIZATION"}, ...]
        """
        results = []
        for entity in entities:
            result = self.verify_entity(
                entity_name=entity.get("name", ""),
                entity_type=entity.get("type", "UNKNOWN")
            )
            results.append(result)
            logger.info(
                "entity_verified",
                name=entity.get("name"),
                status=result.status.value,
                adjustment=result.confidence_adjustment
            )
        
        return results


# === INTEGRATION HELPER ===

def apply_verification_to_extraction(
    entities: List[Any],
    claims: List[Any]
) -> Tuple[List[Any], List[Any], Dict[str, Any]]:
    """
    Apply verification to extraction results.
    Adjusts confidence scores and flags unverified entities.
    
    Returns: (updated_entities, updated_claims, verification_summary)
    """
    agent = VerificationAgent()
    
    # Convert entities to verification format
    entity_list = [{"name": e.canonical_name, "type": e.entity_type} for e in entities]
    
    # Run verification
    results = agent.verify_batch(entity_list)
    
    # Build lookup for confidence adjustments
    adjustments = {r.entity_name: r for r in results}
    
    # Update entity confidence (if they have a confidence attribute)
    verified_count = 0
    unverified_count = 0
    sanctioned_count = 0
    
    for entity in entities:
        result = adjustments.get(entity.canonical_name)
        if result:
            if result.status == VerificationStatus.VERIFIED:
                verified_count += 1
            elif result.status == VerificationStatus.UNVERIFIED:
                unverified_count += 1
                # Add flag to entity (if possible)
                if hasattr(entity, 'aliases'):
                    entity.aliases.append("UNVERIFIED")
            elif result.status == VerificationStatus.SANCTIONED:
                sanctioned_count += 1
                if hasattr(entity, 'aliases'):
                    entity.aliases.append("SANCTIONED")
    
    # Update claim confidence scores
    for claim in claims:
        # Get subject and object verification results
        subj_result = adjustments.get(claim.subject_id.split(":")[0])
        obj_result = adjustments.get(claim.object_id.split(":")[0])
        
        # Apply adjustments
        if subj_result:
            claim.confidence_score *= subj_result.confidence_adjustment
        if obj_result:
            claim.confidence_score *= obj_result.confidence_adjustment
        
        # Cap at 1.0
        claim.confidence_score = min(1.0, claim.confidence_score)
    
    summary = {
        "total_entities": len(entities),
        "verified": verified_count,
        "unverified": unverified_count,
        "sanctioned": sanctioned_count,
        "verification_rate": verified_count / len(entities) if entities else 0
    }
    
    logger.info("verification_complete", **summary)
    
    return entities, claims, summary
