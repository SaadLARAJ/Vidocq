"""
VIDOCQ BRAIN - Negative Space Analysis
Detects what's MISSING - The most suspicious signal.

"Ce qui n'est pas là est plus suspect que ce qui est là."

Features:
- Digital footprint gaps (no LinkedIn, no history)
- Domain age analysis (site created yesterday)
- Publication gaps (expert without papers)
- Photo absence detection
- Historical erasure detection
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import httpx
import re

from src.core.logging import get_logger

logger = get_logger(__name__)


class SuspicionLevel(str, Enum):
    """Level of suspicion from negative space analysis"""
    CRITICAL = "CRITICAL"    # Multiple major red flags
    HIGH = "HIGH"            # Clear anomalies
    MEDIUM = "MEDIUM"        # Some gaps worth investigating
    LOW = "LOW"              # Minor gaps, probably normal
    CLEAN = "CLEAN"          # Normal digital footprint


class VoidAnomaly(BaseModel):
    """A detected absence/void that is suspicious"""
    anomaly_type: str
    description: str
    severity: SuspicionLevel
    expected: str
    found: str
    investigation_hint: str


class NegativeSpaceReport(BaseModel):
    """Complete negative space analysis report"""
    target: str
    target_type: str
    overall_suspicion: SuspicionLevel
    void_score: float = Field(ge=0, le=1, description="0=normal, 1=highly suspicious")
    anomalies: List[VoidAnomaly] = []
    profile_completeness: float = Field(ge=0, le=1)
    historical_depth: Optional[int] = None  # Years of traceable history
    summary: str
    recommendation: str


class NegativeSpaceAnalyzer:
    """
    The "Ghost Detector" - Analyzes what's MISSING.
    
    Principles:
    1. Real people/companies leave digital traces
    2. The ABSENCE of expected traces is suspicious
    3. "Too clean" profiles are red flags
    4. Sudden appearance (no history) = synthetic identity risk
    """
    
    def __init__(self):
        self.timeout = 10
        
        # Expected digital footprint by entity type
        self.expected_footprints = {
            "PERSON": {
                "linkedin": {"weight": 0.3, "desc": "Professional network presence"},
                "academic": {"weight": 0.2, "desc": "Publications, patents, degrees"},
                "news_mentions": {"weight": 0.15, "desc": "Media mentions"},
                "social_media": {"weight": 0.1, "desc": "Twitter/X, Facebook presence"},
                "photo_availability": {"weight": 0.15, "desc": "Identifiable photos"},
                "historical_traces": {"weight": 0.1, "desc": "Pre-2020 activity"}
            },
            "COMPANY": {
                "official_registry": {"weight": 0.25, "desc": "Company registration records"},
                "domain_age": {"weight": 0.2, "desc": "Website existence duration"},
                "employee_traces": {"weight": 0.15, "desc": "Visible employees on LinkedIn"},
                "financial_filings": {"weight": 0.15, "desc": "Published accounts"},
                "press_coverage": {"weight": 0.1, "desc": "Media mentions"},
                "physical_presence": {"weight": 0.15, "desc": "Verifiable address/office"}
            },
            "STATE": {
                "official_sources": {"weight": 0.3, "desc": "Government publications"},
                "international_data": {"weight": 0.25, "desc": "UN/World Bank data"},
                "diplomatic_traces": {"weight": 0.2, "desc": "Embassy, treaties"},
                "economic_data": {"weight": 0.25, "desc": "Trade, GDP statistics"}
            }
        }
    
    async def analyze(
        self, 
        target: str, 
        target_type: str,
        existing_data: Optional[Dict] = None
    ) -> NegativeSpaceReport:
        """
        Run complete negative space analysis.
        Detects suspicious absences in digital footprint.
        """
        logger.info("negative_space_analysis_started", target=target, type=target_type)
        
        anomalies = []
        footprint_scores = {}
        
        # Get expected footprints for this entity type
        expected = self.expected_footprints.get(
            target_type.upper(), 
            self.expected_footprints["COMPANY"]
        )
        
        # Analyze each expected footprint
        for footprint_type, config in expected.items():
            score, anomaly = await self._check_footprint(
                target=target,
                footprint_type=footprint_type,
                target_type=target_type,
                existing_data=existing_data
            )
            
            footprint_scores[footprint_type] = score
            if anomaly:
                anomalies.append(anomaly)
        
        # Check for historical erasure patterns
        erasure_anomaly = await self._detect_erasure_patterns(target, target_type)
        if erasure_anomaly:
            anomalies.append(erasure_anomaly)
        
        # Check for "too clean" syndrome
        clean_anomaly = self._detect_too_clean(target, anomalies, footprint_scores)
        if clean_anomaly:
            anomalies.append(clean_anomaly)
        
        # Calculate overall scores
        void_score = self._calculate_void_score(anomalies, footprint_scores, expected)
        profile_completeness = sum(footprint_scores.values()) / len(footprint_scores) if footprint_scores else 0.5
        overall_suspicion = self._determine_suspicion_level(void_score, anomalies)
        
        # Estimate historical depth
        historical_depth = self._estimate_historical_depth(existing_data)
        
        # Generate summary and recommendation
        summary, recommendation = self._generate_insights(
            target, target_type, anomalies, void_score, overall_suspicion
        )
        
        report = NegativeSpaceReport(
            target=target,
            target_type=target_type,
            overall_suspicion=overall_suspicion,
            void_score=void_score,
            anomalies=anomalies,
            profile_completeness=profile_completeness,
            historical_depth=historical_depth,
            summary=summary,
            recommendation=recommendation
        )
        
        logger.info(
            "negative_space_analysis_complete",
            target=target,
            suspicion=overall_suspicion.value,
            anomaly_count=len(anomalies)
        )
        
        return report
    
    async def _check_footprint(
        self,
        target: str,
        footprint_type: str,
        target_type: str,
        existing_data: Optional[Dict]
    ) -> Tuple[float, Optional[VoidAnomaly]]:
        """Check a specific footprint type for anomalies."""
        
        # Simulate footprint checking (in production, use real APIs)
        # For now, use heuristics based on existing data
        
        if footprint_type == "linkedin":
            return self._check_linkedin_presence(target, existing_data)
        
        elif footprint_type == "domain_age":
            return self._check_domain_age(target, existing_data)
        
        elif footprint_type == "historical_traces":
            return self._check_historical_traces(target, existing_data)
        
        elif footprint_type == "academic":
            return self._check_academic_presence(target, existing_data)
        
        elif footprint_type == "photo_availability":
            return self._check_photo_availability(target, existing_data)
        
        # Default: assume present (score 0.7)
        return 0.7, None
    
    def _check_linkedin_presence(
        self, 
        target: str, 
        existing_data: Optional[Dict]
    ) -> Tuple[float, Optional[VoidAnomaly]]:
        """Check for LinkedIn presence."""
        
        # Check if we found LinkedIn in our sources
        sources = existing_data.get("sources", []) if existing_data else []
        has_linkedin = any("linkedin" in s.lower() for s in sources)
        
        if has_linkedin:
            return 0.9, None
        
        # No LinkedIn for a person is suspicious
        return 0.2, VoidAnomaly(
            anomaly_type="MISSING_LINKEDIN",
            description=f"Aucun profil LinkedIn trouvé pour {target}",
            severity=SuspicionLevel.MEDIUM,
            expected="Profil LinkedIn professionnel",
            found="Aucun profil détecté",
            investigation_hint="Vérifier manuellement LinkedIn, possible profil caché ou inexistant"
        )
    
    def _check_domain_age(
        self, 
        target: str, 
        existing_data: Optional[Dict]
    ) -> Tuple[float, Optional[VoidAnomaly]]:
        """Check domain age for companies."""
        
        # In production: use WHOIS API
        # For now: heuristic based on company name patterns
        
        suspicious_patterns = ["2023", "2024", "new", "startup"]
        target_lower = target.lower()
        
        if any(p in target_lower for p in suspicious_patterns):
            return 0.3, VoidAnomaly(
                anomaly_type="YOUNG_ENTITY",
                description=f"Entité potentiellement récente: {target}",
                severity=SuspicionLevel.LOW,
                expected="Historique de plusieurs années",
                found="Indices de création récente",
                investigation_hint="Vérifier la date de création au registre du commerce"
            )
        
        return 0.7, None
    
    def _check_historical_traces(
        self, 
        target: str, 
        existing_data: Optional[Dict]
    ) -> Tuple[float, Optional[VoidAnomaly]]:
        """Check for pre-2020 digital traces."""
        
        # Look for date patterns in collected data
        sources = existing_data.get("sources", []) if existing_data else []
        
        # Check if any source mentions dates before 2020
        old_patterns = ["2019", "2018", "2017", "2016", "2015", "2010", "2000"]
        has_old_traces = any(
            any(p in str(s) for p in old_patterns) 
            for s in sources
        )
        
        if not has_old_traces and len(sources) > 0:
            return 0.3, VoidAnomaly(
                anomaly_type="NO_HISTORICAL_FOOTPRINT",
                description=f"Aucune trace antérieure à 2020 pour {target}",
                severity=SuspicionLevel.HIGH,
                expected="Historique numérique sur plusieurs années",
                found="Traces uniquement récentes (post-2020)",
                investigation_hint="ALERTE: Possible identité synthétique ou entité écran. Vérifier les archives."
            )
        
        return 0.8, None
    
    def _check_academic_presence(
        self, 
        target: str, 
        existing_data: Optional[Dict]
    ) -> Tuple[float, Optional[VoidAnomaly]]:
        """Check for academic/publication presence."""
        
        # Check for academic source patterns
        sources = existing_data.get("sources", []) if existing_data else []
        academic_domains = ["scholar", "researchgate", "academia", "arxiv", "ieee", "pubmed"]
        
        has_academic = any(
            any(d in s.lower() for d in academic_domains)
            for s in sources
        )
        
        # Only flag if target claims expertise
        expertise_keywords = ["dr", "phd", "professor", "expert", "scientist", "researcher"]
        claims_expertise = any(k in target.lower() for k in expertise_keywords)
        
        if claims_expertise and not has_academic:
            return 0.2, VoidAnomaly(
                anomaly_type="CLAIMED_EXPERTISE_NO_PUBLICATIONS",
                description=f"Expertise revendiquée sans publications: {target}",
                severity=SuspicionLevel.HIGH,
                expected="Publications académiques, brevets, citations",
                found="Aucune trace académique malgré titre d'expert",
                investigation_hint="ALERTE: Potentiel faux expert. Vérifier les diplômes et publications."
            )
        
        return 0.7, None
    
    def _check_photo_availability(
        self, 
        target: str, 
        existing_data: Optional[Dict]
    ) -> Tuple[float, Optional[VoidAnomaly]]:
        """Check for identifiable photos."""
        
        # In production: use image search APIs
        # For now: heuristic
        
        sources = existing_data.get("sources", []) if existing_data else []
        image_patterns = ["photo", "image", "portrait", "picture", "jpg", "png"]
        
        has_images = any(
            any(p in str(s).lower() for p in image_patterns)
            for s in sources
        )
        
        if not has_images:
            return 0.4, VoidAnomaly(
                anomaly_type="NO_IDENTIFIABLE_PHOTOS",
                description=f"Aucune photo identifiable pour {target}",
                severity=SuspicionLevel.MEDIUM,
                expected="Photos professionnelles, événements, presse",
                found="Absence totale d'image identifiable",
                investigation_hint="Personne évitant les photos = signal de profil caché ou synthétique"
            )
        
        return 0.8, None
    
    async def _detect_erasure_patterns(
        self, 
        target: str, 
        target_type: str
    ) -> Optional[VoidAnomaly]:
        """Detect patterns suggesting deliberate erasure of traces."""
        
        # In production: compare with Wayback Machine, track deletions
        # For now: placeholder for the concept
        
        # This would check:
        # - Pages that existed but were deleted
        # - LinkedIn profiles that were deactivated
        # - News articles that were taken down
        # - Court records that were sealed
        
        return None  # No erasure detected in demo
    
    def _detect_too_clean(
        self, 
        target: str,
        anomalies: List[VoidAnomaly],
        footprint_scores: Dict[str, float]
    ) -> Optional[VoidAnomaly]:
        """Detect suspiciously clean/perfect profiles."""
        
        # If NO anomalies and NO negative info, that itself is suspicious
        if len(anomalies) == 0 and all(s > 0.9 for s in footprint_scores.values()):
            return VoidAnomaly(
                anomaly_type="SUSPICIOUSLY_CLEAN",
                description=f"Profil anormalement propre: {target}",
                severity=SuspicionLevel.MEDIUM,
                expected="Quelques imperfections normales",
                found="Profil parfait sans aucune aspérité",
                investigation_hint="Un profil TROP parfait peut être manufacturé. Creuser les détails."
            )
        
        return None
    
    def _calculate_void_score(
        self,
        anomalies: List[VoidAnomaly],
        footprint_scores: Dict[str, float],
        expected: Dict
    ) -> float:
        """Calculate overall void/suspicion score."""
        
        # Start with inverse of average footprint presence
        if footprint_scores:
            base_score = 1 - (sum(footprint_scores.values()) / len(footprint_scores))
        else:
            base_score = 0.5
        
        # Add penalty for each anomaly
        anomaly_penalties = {
            SuspicionLevel.CRITICAL: 0.3,
            SuspicionLevel.HIGH: 0.2,
            SuspicionLevel.MEDIUM: 0.1,
            SuspicionLevel.LOW: 0.05
        }
        
        for anomaly in anomalies:
            base_score += anomaly_penalties.get(anomaly.severity, 0.05)
        
        return min(1.0, max(0.0, base_score))
    
    def _determine_suspicion_level(
        self, 
        void_score: float, 
        anomalies: List[VoidAnomaly]
    ) -> SuspicionLevel:
        """Determine overall suspicion level."""
        
        critical_count = sum(1 for a in anomalies if a.severity == SuspicionLevel.CRITICAL)
        high_count = sum(1 for a in anomalies if a.severity == SuspicionLevel.HIGH)
        
        if critical_count > 0 or void_score > 0.8:
            return SuspicionLevel.CRITICAL
        elif high_count >= 2 or void_score > 0.6:
            return SuspicionLevel.HIGH
        elif high_count == 1 or void_score > 0.4:
            return SuspicionLevel.MEDIUM
        elif void_score > 0.2:
            return SuspicionLevel.LOW
        else:
            return SuspicionLevel.CLEAN
    
    def _estimate_historical_depth(self, existing_data: Optional[Dict]) -> Optional[int]:
        """Estimate how many years of traceable history exist."""
        
        if not existing_data:
            return None
        
        # Look for year patterns in data
        all_text = str(existing_data)
        years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', all_text)
        
        if years:
            oldest = min(int(y) for y in years)
            return datetime.now().year - oldest
        
        return None
    
    def _generate_insights(
        self,
        target: str,
        target_type: str,
        anomalies: List[VoidAnomaly],
        void_score: float,
        suspicion: SuspicionLevel
    ) -> Tuple[str, str]:
        """Generate human-readable summary and recommendation."""
        
        if suspicion == SuspicionLevel.CRITICAL:
            summary = f"ALERTE CRITIQUE: {target} présente des anomalies majeures dans son empreinte numérique. Plusieurs signaux indiquent une possible identité synthétique, entité écran, ou couverture de renseignement."
            recommendation = "Investigation approfondie OBLIGATOIRE. Vérifier manuellement l'existence physique, les registres officiels, et croiser avec des sources humaines."
        
        elif suspicion == SuspicionLevel.HIGH:
            summary = f"SUSPICION ÉLEVÉE: {target} a des lacunes significatives dans son historique numérique. L'absence de traces attendues est anormale pour ce type d'entité."
            recommendation = "Audit approfondi recommandé avant toute collaboration. Demander des preuves documentaires directes."
        
        elif suspicion == SuspicionLevel.MEDIUM:
            summary = f"ATTENTION: {target} présente quelques lacunes dans son empreinte numérique qui méritent investigation."
            recommendation = "Vérification standard recommandée. Les lacunes peuvent avoir des explications légitimes."
        
        elif suspicion == SuspicionLevel.LOW:
            summary = f"FAIBLE RISQUE: {target} a une empreinte numérique globalement normale avec quelques points mineurs à clarifier."
            recommendation = "Procédure standard. Aucune action urgente requise."
        
        else:
            summary = f"PROFIL NORMAL: {target} présente une empreinte numérique cohérente avec son profil."
            recommendation = "Aucune anomalie détectée. Continuer la surveillance standard."
        
        return summary, recommendation
