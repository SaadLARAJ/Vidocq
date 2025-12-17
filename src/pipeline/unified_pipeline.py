"""
VIDOCQ - Unified Intelligence Pipeline v2.0
Master orchestration that chains ALL modules together.

"One pipeline to rule them all."

INTEGRATED MODULES:
1. VidocqBrain (Classification with CoT)
2. DiscoveryEngineV3 (Search + Coverage Analysis)
3. Extractor (with Parent Context)
4. EvolvingOntology (Type inference + inheritance)
5. LanguageDetector (LLM-based)
6. UnifiedScorer (SourceIntelligence + Contradiction)
7. BayesianFusion (Multi-source probability)
8. ProvenanceTracker (Chain of custody)
9. TemporalFactStore (Fact versioning)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import asyncio

from src.core.logging import get_logger

logger = get_logger(__name__)


class InvestigationResult(BaseModel):
    """Complete result of an investigation pipeline run"""
    target: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    # Provenance
    custody_id: Optional[str] = None  # Chain of custody ID
    
    # Discovery phase
    discovery_results: Dict[str, Any] = {}
    coverage_analysis: Dict[str, Any] = {}
    urls_discovered: int = 0
    
    # Extraction phase
    entities_extracted: int = 0
    claims_extracted: int = 0
    extraction_context: Optional[str] = None
    
    # Ontology
    entity_types_inferred: Dict[str, str] = {}  # entity -> inferred type
    high_risk_entities: List[str] = []
    
    # Scoring phase
    scoring_summary: Dict[str, Any] = {}
    contradiction_report: Dict[str, Any] = {}
    contested_topics: List[str] = []
    
    # Bayesian Fusion
    bayesian_summary: Dict[str, Any] = {}
    fused_claims: Dict[str, float] = {}  # claim -> posterior probability
    
    # Classification
    target_classification: Dict[str, Any] = {}
    
    # Language analysis
    languages_detected: List[str] = []
    
    # Status breakdown
    confirmed_claims: int = 0
    unverified_claims: int = 0
    quarantined_claims: int = 0
    contested_claims: int = 0
    
    # Temporal versioning
    facts_versioned: int = 0
    
    # Recommendations
    recommendations: List[str] = []
    critical_gaps: List[str] = []
    
    # Audit
    provenance_export: Dict[str, Any] = {}


class UnifiedPipelineV2:
    """
    Master orchestration for the complete intelligence pipeline v2.0.
    
    Chains together ALL modules:
    
    ┌─────────────────────────────────────────────────────────────────┐
    │                    UNIFIED PIPELINE v2.0                        │
    ├─────────────────────────────────────────────────────────────────┤
    │  1. PROVENANCE      → Start chain of custody                    │
    │  2. CLASSIFICATION  → VidocqBrain (CoT + few-shot)             │
    │  3. DISCOVERY       → DiscoveryV3 + Coverage Analysis           │
    │  4. INGESTION       → Fetch + Language Detection                │
    │  5. EXTRACTION      → Extractor (with parent_context)           │
    │  6. ONTOLOGY        → Type inference + risk detection           │
    │  7. SCORING         → UnifiedScorer + Contradiction             │
    │  8. FUSION          → Bayesian multi-source fusion              │
    │  9. VERSIONING      → Temporal fact versioning                  │
    │ 10. STORAGE         → Neo4j + Qdrant                            │
    └─────────────────────────────────────────────────────────────────┘
    """
    
    VERSION = "2.0"
    
    def __init__(self):
        # Lazy-loaded modules
        self._brain = None
        self._discovery = None
        self._extractor = None
        self._scorer = None
        self._language_detector = None
        self._provenance = None
        self._ontology = None
        self._fusion = None
    
    # ==================== LAZY LOADERS ====================
    
    @property
    def brain(self):
        if self._brain is None:
            from src.brain.core_logic import VidocqBrain
            self._brain = VidocqBrain()
        return self._brain
    
    @property
    def discovery(self):
        if self._discovery is None:
            from src.pipeline.discovery_v3 import DiscoveryEngineV3
            self._discovery = DiscoveryEngineV3()
        return self._discovery
    
    @property
    def extractor(self):
        if self._extractor is None:
            from src.pipeline.extractor import Extractor
            self._extractor = Extractor()
        return self._extractor
    
    @property
    def scorer(self):
        if self._scorer is None:
            from src.core.unified_scoring import UnifiedScorer
            self._scorer = UnifiedScorer()
        return self._scorer
    
    @property
    def language_detector(self):
        if self._language_detector is None:
            from src.core.language_detection import LanguageDetector
            self._language_detector = LanguageDetector()
        return self._language_detector
    
    @property
    def provenance(self):
        if self._provenance is None:
            from src.core.provenance import ProvenanceTracker
            self._provenance = ProvenanceTracker()
        return self._provenance
    
    @property
    def ontology(self):
        if self._ontology is None:
            from src.core.evolving_ontology import EntityHierarchy
            self._ontology = EntityHierarchy()
        return self._ontology
    
    @property
    def fusion(self):
        if self._fusion is None:
            from src.core.bayesian_fusion import BayesianFusion
            self._fusion = BayesianFusion()
        return self._fusion
    
    # ==================== MAIN PIPELINE ====================
    
    async def investigate(
        self,
        target: str,
        max_urls: int = 20,
        max_depth: int = 1
    ) -> InvestigationResult:
        """
        Run complete investigation pipeline on a target.
        
        Full flow with ALL modules integrated.
        """
        result = InvestigationResult(target=target)
        
        try:
            # =====================
            # PHASE 1: PROVENANCE - Start Chain of Custody
            # =====================
            logger.info("pipeline_v2_phase_1_provenance", target=target)
            
            from src.core.provenance import ProvenanceStep
            
            chain = self.provenance.start_chain(
                subject=target,
                subject_type="INVESTIGATION",
                parent_context=target
            )
            result.custody_id = chain.custody_id
            
            # =====================
            # PHASE 2: CLASSIFICATION (CoT + Few-shot)
            # =====================
            logger.info("pipeline_v2_phase_2_classification", target=target)
            
            classification = await self.brain.classify_target(target)
            result.target_classification = {
                "type": classification.target_type.value,
                "confidence": classification.confidence,
                "country": classification.probable_country,
                "sector": classification.probable_sector,
                "strategy": classification.search_strategy
            }
            
            # Log to provenance
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.EXTRACTION,
                processor="VidocqBrain.classify_target",
                parameters={"model": "gemini", "cot_enabled": True},
                items_out=1,
                notes=f"Classified as {classification.target_type.value}"
            )
            
            # =====================
            # PHASE 3: DISCOVERY + COVERAGE
            # =====================
            logger.info("pipeline_v2_phase_3_discovery", target=target)
            
            discovery_result = self.discovery.discover(
                entity_name=target,
                max_urls=max_urls
            )
            
            result.discovery_results = discovery_result
            result.urls_discovered = len(discovery_result.get("urls", []))
            
            if "coverage" in discovery_result:
                result.coverage_analysis = discovery_result["coverage"]
                result.critical_gaps = discovery_result["coverage"].get("critical_gaps", [])
                result.recommendations.extend(
                    discovery_result["coverage"].get("recommendations", [])
                )
            
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.DISCOVERY,
                processor="DiscoveryEngineV3.discover",
                items_out=result.urls_discovered,
                parameters={"max_urls": max_urls},
                notes=f"Coverage score: {result.coverage_analysis.get('score', 'N/A')}"
            )
            
            # =====================
            # PHASE 4: EXTRACTION (with context) + LANGUAGE DETECTION
            # =====================
            logger.info("pipeline_v2_phase_4_extraction", target=target)
            
            all_entities = []
            all_claims = []
            all_source_urls = []
            detected_languages = set()
            claims_for_fusion = []
            
            for url in discovery_result.get("urls", [])[:max_urls]:
                try:
                    from src.pipeline.ingestion import fetch_and_clean
                    text = await fetch_and_clean(url)
                    
                    if not text or len(text) < 100:
                        continue
                    
                    # LANGUAGE DETECTION
                    lang_result = await self.language_detector.detect(text[:1000])
                    detected_languages.add(lang_result.primary_language)
                    
                    # EXTRACTION with parent context
                    extraction = self.extractor.extract(
                        text=text,
                        source_domain=url.split("/")[2] if "/" in url else url,
                        source_url=url,
                        parent_context=target  # CONTEXT PROPAGATION
                    )
                    
                    entities = extraction.get("entities", [])
                    claims = extraction.get("claims", [])
                    
                    # Prepare for Bayesian fusion
                    for claim in claims:
                        claims_for_fusion.append({
                            "claim": claim.get("evidence", str(claim)),
                            "source_url": url,
                            "confidence": claim.get("confidence", 0.5),
                            "is_tangential": claim.get("is_tangential", False)
                        })
                    
                    all_entities.extend(entities)
                    all_claims.extend(claims)
                    all_source_urls.append(url)
                    
                except Exception as e:
                    logger.warning("extraction_failed", url=url, error=str(e))
                    continue
            
            result.entities_extracted = len(all_entities)
            result.claims_extracted = len(all_claims)
            result.extraction_context = target
            result.languages_detected = list(detected_languages)
            
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.EXTRACTION,
                processor="Extractor.extract",
                items_in=len(all_source_urls),
                items_out=len(all_claims),
                parameters={"parent_context": target},
                notes=f"Languages: {', '.join(detected_languages)}"
            )
            
            # =====================
            # PHASE 5: ONTOLOGY - Type Inference + Risk Detection
            # =====================
            logger.info("pipeline_v2_phase_5_ontology", target=target)
            
            for entity in all_entities:
                entity_name = entity.get("name", "")
                entity_data = {
                    "name": entity_name,
                    "type": entity.get("type", "ENTITY"),
                    "properties": entity
                }
                
                # Infer most specific type
                inferred_type = self.ontology.infer_type(entity_data)
                result.entity_types_inferred[entity_name] = inferred_type
                
                # Check for high-risk entities
                risks = self.ontology.get_risk_indicators(inferred_type)
                if risks:
                    result.high_risk_entities.append(f"{entity_name} ({inferred_type})")
            
            if result.high_risk_entities:
                result.recommendations.append(
                    f"🔴 {len(result.high_risk_entities)} entités à haut risque détectées: {', '.join(result.high_risk_entities[:3])}"
                )
            
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.ENRICHMENT,
                processor="EvolvingOntology.infer_type",
                items_in=len(all_entities),
                items_out=len(result.high_risk_entities),
                notes=f"High-risk: {len(result.high_risk_entities)}"
            )
            
            # =====================
            # PHASE 6: SCORING + CONTRADICTION DETECTION
            # =====================
            logger.info("pipeline_v2_phase_6_scoring", target=target)
            
            if all_claims:
                from src.core.unified_scoring import score_with_contradiction_check
                
                scoring_result = await score_with_contradiction_check(
                    target=target,
                    claims=claims_for_fusion,
                    source_urls=all_source_urls,
                    mission_relevance=0.7
                )
                
                result.contradiction_report = scoring_result.get("contradiction_report", {})
                result.contested_topics = scoring_result.get("contested_topics", [])
                
                for claim in scoring_result.get("scored_claims", []):
                    status = claim.get("visibility_status", "UNVERIFIED")
                    if status == "CONFIRMED":
                        result.confirmed_claims += 1
                    elif status == "UNVERIFIED":
                        result.unverified_claims += 1
                    elif status == "QUARANTINE":
                        result.quarantined_claims += 1
                    elif status == "CONTESTED":
                        result.contested_claims += 1
                
                result.scoring_summary = {
                    "total_claims": len(all_claims),
                    "confirmed": result.confirmed_claims,
                    "unverified": result.unverified_claims,
                    "quarantined": result.quarantined_claims,
                    "contested": result.contested_claims,
                    "narrative_wars": result.contradiction_report.get("narrative_wars", 0)
                }
            
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.SCORING,
                processor="UnifiedScorer + ContradictionDetector",
                items_in=len(all_claims),
                parameters={"weights": self.scorer.WEIGHTS},
                notes=f"Contested: {result.contested_claims}"
            )
            
            # =====================
            # PHASE 7: BAYESIAN FUSION
            # =====================
            logger.info("pipeline_v2_phase_7_fusion", target=target)
            
            if claims_for_fusion:
                fusion_results = self.fusion.fuse_claims(claims_for_fusion)
                
                highly_likely = 0
                uncertain = 0
                
                for claim_text, fusion_result in fusion_results.items():
                    result.fused_claims[claim_text[:100]] = fusion_result.posterior_probability
                    
                    if fusion_result.verdict in ["HIGHLY_LIKELY", "LIKELY"]:
                        highly_likely += 1
                    elif fusion_result.verdict == "UNCERTAIN":
                        uncertain += 1
                
                result.bayesian_summary = {
                    "total_fused": len(fusion_results),
                    "highly_likely": highly_likely,
                    "uncertain": uncertain,
                    "method": "Bayesian log-odds fusion"
                }
                
                if uncertain > len(fusion_results) * 0.5:
                    result.recommendations.append(
                        f"⚠️ {uncertain}/{len(fusion_results)} claims ont une probabilité incertaine. Plus de sources nécessaires."
                    )
            
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.VERIFICATION,
                processor="BayesianFusion.fuse_claims",
                items_in=len(claims_for_fusion),
                items_out=len(result.fused_claims),
                notes=f"Method: Bayesian log-odds"
            )
            
            # =====================
            # PHASE 8: TEMPORAL VERSIONING
            # =====================
            logger.info("pipeline_v2_phase_8_versioning", target=target)
            
            try:
                from src.core.temporal_versioning import create_fact_version
                
                for claim in all_claims[:10]:  # Version top 10 claims
                    if isinstance(claim, dict):
                        subject = claim.get("subject", target)
                        relation = claim.get("relation", "RELATED_TO")
                        obj = claim.get("object", "")
                        
                        if subject and obj:
                            fact = create_fact_version(
                                subject=subject,
                                relation=relation,
                                object=obj,
                                source_url=claim.get("source_url", ""),
                                confidence=claim.get("confidence", 0.5)
                            )
                            result.facts_versioned += 1
                
            except Exception as e:
                logger.warning("versioning_skipped", error=str(e))
            
            self.provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.STORAGE,
                processor="TemporalFactStore",
                items_out=result.facts_versioned,
                notes=f"Facts versioned: {result.facts_versioned}"
            )
            
            # =====================
            # PHASE 9: GENERATE RECOMMENDATIONS
            # =====================
            logger.info("pipeline_v2_phase_9_recommendations", target=target)
            
            if result.contradiction_report.get("narrative_wars", 0) > 0:
                result.recommendations.append(
                    f"⚠️ GUERRE NARRATIVE: {result.contradiction_report.get('narrative_wars')} conflits. "
                    f"Recommandation: {result.contradiction_report.get('recommendation', 'Vérifier manuellement')}"
                )
            
            if result.critical_gaps:
                result.recommendations.append(
                    f"🔴 GAPS CRITIQUES: {', '.join(result.critical_gaps)}. Investigation manuelle requise."
                )
            
            if len(result.languages_detected) > 1:
                result.recommendations.append(
                    f"🌐 Sources multilingues: {', '.join(result.languages_detected)}. Vérifier cohérence."
                )
            
            # =====================
            # PHASE 10: FINALIZE PROVENANCE
            # =====================
            result.provenance_export = self.provenance.export_for_audit(chain.custody_id)
            result.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                "pipeline_v2_complete",
                target=target,
                entities=result.entities_extracted,
                claims=result.claims_extracted,
                bayesian_fused=len(result.fused_claims),
                high_risk=len(result.high_risk_entities),
                recommendations=len(result.recommendations),
                provenance_steps=len(result.provenance_export.get("audit_trail", []))
            )
            
        except Exception as e:
            logger.error("pipeline_v2_failed", target=target, error=str(e))
            result.recommendations.append(f"❌ ERREUR PIPELINE: {str(e)}")
            
            # Still export provenance even on failure
            if result.custody_id:
                result.provenance_export = self.provenance.export_for_audit(result.custody_id)
        
        return result


# Singleton instance
PIPELINE = UnifiedPipelineV2()


async def investigate(target: str, max_urls: int = 20) -> InvestigationResult:
    """
    Convenience function to run a full investigation.
    
    Usage:
        result = await investigate("Thales Group")
        
        # All modules used:
        print(result.bayesian_summary)      # Bayesian fusion
        print(result.provenance_export)     # Chain of custody
        print(result.entity_types_inferred) # Ontology
        print(result.scoring_summary)       # Unified scoring
        print(result.coverage_analysis)     # Coverage gaps
    """
    return await PIPELINE.investigate(target, max_urls=max_urls)


def investigate_sync(target: str, max_urls: int = 20) -> InvestigationResult:
    """Synchronous wrapper for investigate."""
    return asyncio.run(investigate(target, max_urls=max_urls))

