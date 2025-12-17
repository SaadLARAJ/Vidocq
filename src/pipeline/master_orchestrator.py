"""
VIDOCQ - Master Intelligence Orchestrator
The ULTIMATE integration ensuring ALL modules work together optimally.

"Every module enhances every other module."

SYNERGY MATRIX:
- Ontology → PredictiveRisk (DEFENSE_CONTRACTOR = higher cyber risk)
- Coverage Gaps → PredictiveRisk (missing data = uncertainty)
- Hidden Networks → Brief (shell clusters in report)
- Bayesian → Network Confidence (fused scores)
- All steps → Provenance (complete audit trail)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import asyncio

from src.core.logging import get_logger

logger = get_logger(__name__)


class VidocqResult(BaseModel):
    """Complete VIDOCQ analysis result with full synergy"""
    
    # Metadata
    target: str
    analysis_id: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0
    
    # Chain of Custody
    custody_id: Optional[str] = None
    provenance_steps: int = 0
    
    # Phase 1: Classification
    classification: Dict[str, Any] = {}
    
    # Phase 2: Discovery + Coverage
    urls_discovered: int = 0
    coverage_score: float = 0
    critical_gaps: List[str] = []
    
    # Phase 3: Extraction + Language
    entities_extracted: int = 0
    claims_extracted: int = 0
    languages_detected: List[str] = []
    
    # Phase 4: Ontology
    entity_types: Dict[str, str] = {}
    high_risk_entities: List[str] = []
    
    # Phase 5: Scoring + Contradiction
    scoring_summary: Dict[str, Any] = {}
    narrative_wars: int = 0
    contested_topics: List[str] = []
    
    # Phase 6: Bayesian Fusion
    bayesian_summary: Dict[str, Any] = {}
    high_confidence_claims: int = 0
    
    # Phase 7: Hidden Networks (SYNERGY: uses graph + ontology)
    hidden_networks: Dict[str, Any] = {}
    circular_ownership: List[List[str]] = []
    shell_clusters: List[List[str]] = []
    network_risk_score: float = 0
    
    # Phase 8: Predictive Risk (SYNERGY: uses ontology + gaps)
    predictive_risks: Dict[str, Any] = {}
    risk_trajectory: str = "STABLE"
    top_predicted_risks: List[str] = []
    
    # Phase 9: Temporal Versioning
    facts_versioned: int = 0
    
    # Phase 10: Executive Brief (SYNERGY: uses ALL)
    executive_summary: str = ""
    key_finding: str = ""
    risk_matrix: Dict[str, Any] = {}
    markdown_report: str = ""
    
    # Recommendations (merged from ALL modules)
    all_recommendations: List[str] = []
    immediate_actions: List[str] = []


class MasterOrchestrator:
    """
    Master orchestrator ensuring OPTIMAL integration of ALL modules.
    
    Each module receives context from previous modules to enhance results.
    No feature works in isolation - everything synergizes.
    """
    
    VERSION = "3.0-synergy"
    
    def __init__(self):
        # All modules lazy-loaded
        self._modules = {}
    
    def _get_module(self, name: str):
        """Lazy load modules on demand."""
        if name not in self._modules:
            if name == "brain":
                from src.brain.core_logic import VidocqBrain
                self._modules[name] = VidocqBrain()
            elif name == "discovery":
                from src.pipeline.discovery_v3 import DiscoveryEngineV3
                self._modules[name] = DiscoveryEngineV3()
            elif name == "extractor":
                from src.pipeline.extractor import Extractor
                self._modules[name] = Extractor()
            elif name == "scorer":
                from src.core.unified_scoring import UnifiedScorer
                self._modules[name] = UnifiedScorer()
            elif name == "language":
                from src.core.language_detection import LanguageDetector
                self._modules[name] = LanguageDetector()
            elif name == "provenance":
                from src.core.provenance import ProvenanceTracker
                self._modules[name] = ProvenanceTracker()
            elif name == "ontology":
                from src.core.evolving_ontology import EntityHierarchy
                self._modules[name] = EntityHierarchy()
            elif name == "fusion":
                from src.core.bayesian_fusion import BayesianFusion
                self._modules[name] = BayesianFusion()
            elif name == "networks":
                from src.brain.hidden_network_detector import HiddenNetworkDetector
                self._modules[name] = HiddenNetworkDetector()
            elif name == "risk":
                from src.brain.predictive_risk import PredictiveRiskScorer
                self._modules[name] = PredictiveRiskScorer()
            elif name == "brief":
                from src.brain.brief_generator import BriefGenerator
                self._modules[name] = BriefGenerator()
        return self._modules.get(name)
    
    async def analyze(
        self,
        target: str,
        max_urls: int = 20,
        graph_store=None
    ) -> VidocqResult:
        """
        Run COMPLETE analysis with OPTIMAL synergy between ALL modules.
        """
        result = VidocqResult(
            target=target,
            analysis_id=f"{target.replace(' ', '_')}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        # Shared context that grows as we progress
        context = {
            "target": target,
            "entity_type": None,
            "sector": None,
            "countries": [],
            "high_risk_entities": [],
            "coverage_gaps": [],
            "ontology_types": {},
            "network_patterns": [],
            "claims_for_fusion": []
        }
        
        try:
            from src.core.provenance import ProvenanceStep
            
            # =====================
            # PHASE 1: PROVENANCE START
            # =====================
            logger.info("master_phase_1_provenance", target=target)
            
            provenance = self._get_module("provenance")
            chain = provenance.start_chain(
                subject=target,
                subject_type="MASTER_ANALYSIS",
                parent_context=target
            )
            result.custody_id = chain.custody_id
            
            # =====================
            # PHASE 2: CLASSIFICATION
            # =====================
            logger.info("master_phase_2_classification", target=target)
            
            brain = self._get_module("brain")
            classification = await brain.classify_target(target)
            
            result.classification = {
                "type": classification.target_type.value,
                "confidence": classification.confidence,
                "country": classification.probable_country,
                "sector": classification.probable_sector
            }
            
            # SYNERGY: Store for other modules
            context["entity_type"] = classification.target_type.value
            context["sector"] = classification.probable_sector
            if classification.probable_country:
                context["countries"].append(classification.probable_country)
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.EXTRACTION,
                processor="VidocqBrain.classify_target",
                items_out=1,
                notes=f"Type: {classification.target_type.value}"
            )
            
            # =====================
            # PHASE 3: DISCOVERY + COVERAGE
            # =====================
            logger.info("master_phase_3_discovery", target=target)
            
            discovery = self._get_module("discovery")
            discovery_result = discovery.discover(target, max_urls=max_urls)
            
            result.urls_discovered = len(discovery_result.get("urls", []))
            
            if "coverage" in discovery_result:
                result.coverage_score = discovery_result["coverage"].get("score", 0)
                result.critical_gaps = discovery_result["coverage"].get("critical_gaps", [])
                # SYNERGY: Gaps inform risk prediction
                context["coverage_gaps"] = result.critical_gaps
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.DISCOVERY,
                processor="DiscoveryV3",
                items_out=result.urls_discovered,
                notes=f"Coverage: {result.coverage_score:.2f}"
            )
            
            # =====================
            # PHASE 4: EXTRACTION + LANGUAGE
            # =====================
            logger.info("master_phase_4_extraction", target=target)
            
            extractor = self._get_module("extractor")
            language_detector = self._get_module("language")
            
            all_entities = []
            all_claims = []
            detected_languages = set()
            
            for url in discovery_result.get("urls", [])[:max_urls]:
                try:
                    from src.pipeline.ingestion import fetch_and_clean
                    text = await fetch_and_clean(url)
                    
                    if not text or len(text) < 100:
                        continue
                    
                    # Language detection
                    lang = await language_detector.detect(text[:1000])
                    detected_languages.add(lang.primary_language)
                    
                    # Extraction with context
                    extraction = extractor.extract(
                        text=text,
                        source_domain=url.split("/")[2] if "/" in url else url,
                        source_url=url,
                        parent_context=target
                    )
                    
                    entities = extraction.get("entities", [])
                    claims = extraction.get("claims", [])
                    
                    # Prepare for Bayesian fusion
                    for claim in claims:
                        context["claims_for_fusion"].append({
                            "claim": claim.get("evidence", str(claim)),
                            "source_url": url,
                            "confidence": claim.get("confidence", 0.5)
                        })
                    
                    all_entities.extend(entities)
                    all_claims.extend(claims)
                    
                except Exception as e:
                    continue
            
            result.entities_extracted = len(all_entities)
            result.claims_extracted = len(all_claims)
            result.languages_detected = list(detected_languages)
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.EXTRACTION,
                processor="Extractor",
                items_out=len(all_claims),
                notes=f"Languages: {', '.join(detected_languages)}"
            )
            
            # =====================
            # PHASE 5: ONTOLOGY (SYNERGY: informs risk)
            # =====================
            logger.info("master_phase_5_ontology", target=target)
            
            ontology = self._get_module("ontology")
            
            for entity in all_entities:
                entity_name = entity.get("name", "")
                entity_data = {
                    "name": entity_name,
                    "type": entity.get("type", "ENTITY"),
                    "properties": entity
                }
                
                inferred_type = ontology.infer_type(entity_data)
                result.entity_types[entity_name] = inferred_type
                context["ontology_types"][entity_name] = inferred_type
                
                # Check for high-risk
                risks = ontology.get_risk_indicators(inferred_type)
                if risks:
                    result.high_risk_entities.append(f"{entity_name} ({inferred_type})")
                    context["high_risk_entities"].append(entity_name)
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.ENRICHMENT,
                processor="EvolvingOntology",
                items_out=len(result.high_risk_entities),
                notes=f"High-risk: {len(result.high_risk_entities)}"
            )
            
            # =====================
            # PHASE 6: SCORING + CONTRADICTION
            # =====================
            logger.info("master_phase_6_scoring", target=target)
            
            if all_claims:
                from src.core.unified_scoring import score_with_contradiction_check
                
                scoring_result = await score_with_contradiction_check(
                    target=target,
                    claims=context["claims_for_fusion"],
                    source_urls=[c.get("source_url", "") for c in context["claims_for_fusion"]],
                    mission_relevance=0.7
                )
                
                result.scoring_summary = {
                    "confirmed": scoring_result.get("confirmed", 0),
                    "contested": scoring_result.get("contested", 0),
                    "total": len(all_claims)
                }
                result.narrative_wars = scoring_result.get("contradiction_report", {}).get("narrative_wars", 0)
                result.contested_topics = scoring_result.get("contested_topics", [])
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.SCORING,
                processor="UnifiedScorer + ContradictionDetector",
                notes=f"Narrative wars: {result.narrative_wars}"
            )
            
            # =====================
            # PHASE 7: BAYESIAN FUSION
            # =====================
            logger.info("master_phase_7_fusion", target=target)
            
            if context["claims_for_fusion"]:
                fusion = self._get_module("fusion")
                fusion_results = fusion.fuse_claims(context["claims_for_fusion"])
                
                high_confidence = sum(
                    1 for r in fusion_results.values()
                    if r.verdict in ["HIGHLY_LIKELY", "LIKELY"]
                )
                
                result.bayesian_summary = {
                    "total": len(fusion_results),
                    "high_confidence": high_confidence,
                    "method": "Bayesian log-odds"
                }
                result.high_confidence_claims = high_confidence
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.VERIFICATION,
                processor="BayesianFusion",
                notes=f"High confidence: {result.high_confidence_claims}"
            )
            
            # =====================
            # PHASE 8: HIDDEN NETWORKS (SYNERGY: uses ontology)
            # =====================
            logger.info("master_phase_8_networks", target=target)
            
            networks = self._get_module("networks")
            networks.graph_store = graph_store  # Use real graph if available
            
            network_result = await networks.analyze(target)
            
            result.hidden_networks = {
                "risk_level": network_result.risk_level,
                "patterns": network_result.patterns_detected
            }
            result.circular_ownership = network_result.circular_ownership
            result.shell_clusters = network_result.shell_company_clusters
            result.network_risk_score = network_result.risk_score
            
            # SYNERGY: Add network patterns to context
            context["network_patterns"] = [p.pattern_type for p in network_result.suspicious_patterns]
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.ENRICHMENT,
                processor="HiddenNetworkDetector",
                notes=f"Patterns: {network_result.patterns_detected}"
            )
            
            # =====================
            # PHASE 9: PREDICTIVE RISK (SYNERGY: uses ontology + gaps + networks)
            # =====================
            logger.info("master_phase_9_predictive", target=target)
            
            risk_scorer = self._get_module("risk")
            risk_scorer.graph_store = graph_store
            
            # Build enriched context for prediction
            enriched_context = {
                "countries": context["countries"],
                "entity_type": context["entity_type"],
                "sector": context["sector"],
                "high_risk_entities": context["high_risk_entities"],
                "coverage_gaps": context["coverage_gaps"],  # SYNERGY!
                "ontology_types": context["ontology_types"],  # SYNERGY!
                "network_patterns": context["network_patterns"],  # SYNERGY!
                "shell_clusters": len(result.shell_clusters),  # SYNERGY!
                "circular_ownership": len(result.circular_ownership)  # SYNERGY!
            }
            
            risk_result = await risk_scorer.predict(target, enriched_context)
            
            result.predictive_risks = {
                "trajectory": risk_result.overall_risk_trajectory,
                "current": risk_result.risk_score_current,
                "predicted": risk_result.risk_score_predicted
            }
            result.risk_trajectory = risk_result.overall_risk_trajectory
            result.top_predicted_risks = risk_result.top_risks
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.ENRICHMENT,
                processor="PredictiveRiskScorer",
                notes=f"Trajectory: {risk_result.overall_risk_trajectory}"
            )
            
            # =====================
            # PHASE 10: TEMPORAL VERSIONING
            # =====================
            logger.info("master_phase_10_versioning", target=target)
            
            try:
                from src.core.temporal_versioning import create_fact_version
                
                for claim in all_claims[:10]:
                    if isinstance(claim, dict):
                        subject = claim.get("subject", target)
                        obj = claim.get("object", "")
                        if subject and obj:
                            create_fact_version(
                                subject=subject,
                                relation=claim.get("relation", "RELATED_TO"),
                                object=obj,
                                source_url=claim.get("source_url", ""),
                                confidence=claim.get("confidence", 0.5)
                            )
                            result.facts_versioned += 1
            except:
                pass
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.STORAGE,
                processor="TemporalVersioning",
                items_out=result.facts_versioned
            )
            
            # =====================
            # PHASE 11: EXECUTIVE BRIEF (SYNERGY: uses EVERYTHING)
            # =====================
            logger.info("master_phase_11_brief", target=target)
            
            brief_gen = self._get_module("brief")
            
            # Build comprehensive result dict with ALL data
            full_result = {
                "classification": result.classification,
                "scoring": result.scoring_summary,
                "discovery": {
                    "urls_discovered": result.urls_discovered,
                    "coverage_score": result.coverage_score,
                    "critical_gaps": result.critical_gaps
                },
                "extraction": {
                    "entities_extracted": result.entities_extracted,
                    "claims_extracted": result.claims_extracted,
                    "languages_detected": result.languages_detected
                },
                "ontology": {
                    "entity_types": result.entity_types,
                    "high_risk_entities": result.high_risk_entities
                },
                "contradiction": {
                    "narrative_wars": result.narrative_wars,
                    "contested_topics": result.contested_topics
                },
                "bayesian_fusion": result.bayesian_summary,
                "hidden_networks": {
                    "circular_ownership": result.circular_ownership,
                    "shell_clusters": result.shell_clusters,
                    "risk_score": result.network_risk_score
                },
                "predictive_risks": result.predictive_risks,
                "recommendations": []
            }
            
            from src.brain.brief_generator import ReportFormat
            brief = brief_gen.generate(target, full_result, ReportFormat.EXECUTIVE_BRIEF)
            
            result.executive_summary = brief.executive_summary
            result.key_finding = brief.key_finding
            result.risk_matrix = brief.risk_matrix
            result.markdown_report = brief.markdown_report
            
            provenance.add_step(
                custody_id=chain.custody_id,
                step_type=ProvenanceStep.TRANSFORMATION,
                processor="BriefGenerator",
                notes="Executive brief generated"
            )
            
            # =====================
            # PHASE 12: MERGE RECOMMENDATIONS
            # =====================
            all_recs = set()
            
            # From coverage
            if result.critical_gaps:
                all_recs.add(f"🔴 GAPS: Fill information on {', '.join(result.critical_gaps[:2])}")
            
            # From networks
            if result.circular_ownership:
                all_recs.add("🔴 CRITICAL: Investigate circular ownership patterns")
            if result.shell_clusters:
                all_recs.add("🟠 HIGH: Trace beneficial ownership through shell clusters")
            
            # From narrative wars
            if result.narrative_wars > 0:
                all_recs.add(f"⚠️ NARRATIVE WAR: {result.narrative_wars} conflicts require manual verification")
            
            # From predictive
            if result.risk_trajectory in ["DETERIORATING", "CRITICAL"]:
                all_recs.add(f"📈 RISK TREND: {result.risk_trajectory} - implement monitoring")
            
            # From ontology
            if result.high_risk_entities:
                all_recs.add(f"🏢 {len(result.high_risk_entities)} high-risk entities require enhanced due diligence")
            
            result.all_recommendations = list(all_recs)
            result.immediate_actions = brief.immediate_actions
            
            # Finalize
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            result.provenance_steps = len(provenance.get_chain(chain.custody_id).chain)
            
            logger.info(
                "master_complete",
                target=target,
                duration=result.duration_seconds,
                phases=12,
                recommendations=len(result.all_recommendations)
            )
            
        except Exception as e:
            logger.error("master_failed", error=str(e))
            result.all_recommendations.append(f"❌ ERROR: {str(e)}")
        
        return result


# Singleton
MASTER = MasterOrchestrator()


async def full_analysis(target: str, max_urls: int = 20, graph_store=None) -> VidocqResult:
    """
    Run COMPLETE analysis with FULL SYNERGY.
    
    This is THE function to use for comprehensive intelligence.
    """
    return await MASTER.analyze(target, max_urls, graph_store)


def full_analysis_sync(target: str, max_urls: int = 20) -> VidocqResult:
    """Synchronous wrapper."""
    return asyncio.run(full_analysis(target, max_urls))
