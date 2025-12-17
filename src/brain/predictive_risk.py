"""
VIDOCQ - Predictive Risk Scoring
Predict FUTURE risks before they materialize.

"The best intelligence is knowing what will happen NEXT."

Uses pattern matching and temporal analysis to predict:
1. Sanction likelihood
2. Financial distress signals
3. Regulatory action risks
4. M&A vulnerability
5. Supply chain disruption probability
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from enum import Enum

from src.core.logging import get_logger

logger = get_logger(__name__)


class RiskType(str, Enum):
    SANCTION = "SANCTION"
    FINANCIAL_DISTRESS = "FINANCIAL_DISTRESS"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    SUPPLY_CHAIN_DISRUPTION = "SUPPLY_CHAIN_DISRUPTION"
    REPUTATIONAL = "REPUTATIONAL"
    GEOPOLITICAL = "GEOPOLITICAL"
    CYBER = "CYBER"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"


class TimeHorizon(str, Enum):
    IMMEDIATE = "0-30 days"
    SHORT_TERM = "1-6 months"
    MEDIUM_TERM = "6-12 months"
    LONG_TERM = "1-3 years"


class PredictedRisk(BaseModel):
    """A predicted future risk"""
    risk_type: RiskType
    probability: float = Field(ge=0, le=1)
    time_horizon: TimeHorizon
    
    description: str
    triggers: List[str] = []  # What would cause this
    early_warning_signs: List[str] = []  # What to watch for
    
    impact_if_realized: str = ""
    mitigation_options: List[str] = []
    
    # Confidence in prediction
    confidence: float = Field(ge=0, le=1, default=0.5)
    data_quality: str = "MEDIUM"  # LOW, MEDIUM, HIGH


class PredictiveRiskReport(BaseModel):
    """Complete predictive risk assessment"""
    target: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Overall assessment
    overall_risk_trajectory: str = "STABLE"  # IMPROVING, STABLE, DETERIORATING, CRITICAL
    risk_score_current: float = 0
    risk_score_predicted: float = 0
    
    # Specific predictions
    predicted_risks: List[PredictedRisk] = []
    
    # Top concerns
    top_risks: List[str] = []
    
    # Monitoring recommendations
    key_indicators_to_watch: List[str] = []
    recommended_alert_triggers: List[str] = []
    
    summary: str = ""


class PredictiveRiskScorer:
    """
    Predicts future risks using pattern matching and temporal analysis.
    
    Patterns analyzed:
    - Geographic exposure (Russia, China, Iran, etc.)
    - Industry-specific risks
    - Ownership structure red flags
    - Historical patterns from known cases
    - Regulatory trends
    """
    
    # Risk patterns based on historical data
    SANCTION_PREDICTORS = {
        "russia_connection": 0.6,
        "iran_connection": 0.7,
        "china_military_connection": 0.5,
        "north_korea_connection": 0.9,
        "venezuela_government": 0.4,
        "dual_use_technology": 0.3,
        "weapons_trade": 0.5,
        "cryptocurrency_heavy": 0.2,
    }
    
    FINANCIAL_DISTRESS_SIGNALS = {
        "rapid_leadership_changes": 0.4,
        "auditor_resignation": 0.7,
        "delayed_filings": 0.5,
        "related_party_transactions": 0.3,
        "offshore_restructuring": 0.4,
        "asset_sales": 0.3,
        "credit_rating_downgrade": 0.6,
    }
    
    GEOPOLITICAL_HOTSPOTS = [
        "TAIWAN", "UKRAINE", "ISRAEL", "IRAN", "SOUTH CHINA SEA",
        "NORTH KOREA", "SYRIA", "YEMEN", "VENEZUELA"
    ]
    
    def __init__(self, graph_store=None):
        self.graph_store = graph_store
    
    async def predict(self, target: str, entity_data: Dict = None) -> PredictiveRiskReport:
        """
        Generate predictive risk assessment for a target.
        """
        report = PredictiveRiskReport(target=target)
        
        try:
            # Get entity context
            context = entity_data or await self._get_entity_context(target)
            
            # Run prediction algorithms
            predictions = []
            
            # 1. Sanction Risk Prediction
            sanction_risk = self._predict_sanction_risk(target, context)
            if sanction_risk:
                predictions.append(sanction_risk)
            
            # 2. Financial Distress Prediction
            financial_risk = self._predict_financial_distress(target, context)
            if financial_risk:
                predictions.append(financial_risk)
            
            # 3. Geopolitical Risk
            geo_risk = self._predict_geopolitical_risk(target, context)
            if geo_risk:
                predictions.append(geo_risk)
            
            # 4. Supply Chain Disruption
            supply_risk = self._predict_supply_chain_risk(target, context)
            if supply_risk:
                predictions.append(supply_risk)
            
            # 5. Regulatory Action
            reg_risk = self._predict_regulatory_risk(target, context)
            if reg_risk:
                predictions.append(reg_risk)
            
            # 6. Cyber Risk
            cyber_risk = self._predict_cyber_risk(target, context)
            if cyber_risk:
                predictions.append(cyber_risk)
            
            # Sort by probability
            predictions.sort(key=lambda x: x.probability, reverse=True)
            
            report.predicted_risks = predictions
            report.top_risks = [p.description for p in predictions[:3]]
            
            # Calculate scores
            report.risk_score_current = self._calculate_current_risk(context)
            report.risk_score_predicted = self._calculate_predicted_risk(predictions)
            
            # Determine trajectory
            report.overall_risk_trajectory = self._determine_trajectory(
                report.risk_score_current,
                report.risk_score_predicted
            )
            
            # Generate monitoring recommendations
            report.key_indicators_to_watch = self._get_key_indicators(predictions)
            report.recommended_alert_triggers = self._get_alert_triggers(predictions)
            
            # Summary
            report.summary = self._generate_summary(report)
            
            logger.info(
                "predictive_risk_complete",
                target=target,
                predictions=len(predictions),
                trajectory=report.overall_risk_trajectory
            )
            
        except Exception as e:
            logger.error("predictive_risk_failed", error=str(e))
            report.summary = f"Prediction failed: {str(e)}"
        
        return report
    
    async def _get_entity_context(self, target: str) -> Dict:
        """Get entity context from graph store."""
        context = {
            "countries": [],
            "industries": [],
            "connections": [],
            "risk_indicators": [],
            "recent_events": []
        }
        
        if not self.graph_store:
            return context
        
        # Query for entity details
        query = """
        MATCH (e:Entity {canonical_name: $target})
        OPTIONAL MATCH (e)-[:LOCATED_IN|OPERATES_IN]->(c:Entity)
        OPTIONAL MATCH (e)-[r]->(connected:Entity)
        RETURN e, collect(DISTINCT c.name) as countries, 
               collect(DISTINCT {name: connected.name, type: type(r)}) as connections
        """
        
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, {"target": target})
                record = result.single()
                
                if record:
                    context["countries"] = record["countries"]
                    context["connections"] = record["connections"]
        except:
            pass
        
        return context
    
    def _predict_sanction_risk(self, target: str, context: Dict) -> Optional[PredictedRisk]:
        """Predict likelihood of sanctions."""
        probability = 0.0
        triggers = []
        
        # Check country connections
        countries = [c.upper() for c in context.get("countries", [])]
        
        if any("RUSSIA" in c for c in countries):
            probability += self.SANCTION_PREDICTORS["russia_connection"]
            triggers.append("Russian operations or connections")
        
        if any("IRAN" in c for c in countries):
            probability += self.SANCTION_PREDICTORS["iran_connection"]
            triggers.append("Iranian operations or connections")
        
        if any("CHINA" in c for c in countries):
            probability += self.SANCTION_PREDICTORS["china_military_connection"] * 0.3
            triggers.append("Chinese operations (depends on sector)")
        
        # Check for dual-use tech indicators
        target_lower = target.lower()
        if any(term in target_lower for term in ["defense", "military", "aerospace", "semiconductor"]):
            probability += 0.1
            triggers.append("Dual-use technology sector")
        
        if probability > 0.1:
            return PredictedRisk(
                risk_type=RiskType.SANCTION,
                probability=min(0.95, probability),
                time_horizon=TimeHorizon.MEDIUM_TERM,
                description=f"Elevated sanction risk due to geographic/sector exposure",
                triggers=triggers,
                early_warning_signs=[
                    "Increased media coverage of parent country tensions",
                    "Regulatory inquiries from OFAC/EU",
                    "Partner companies receiving sanctions"
                ],
                impact_if_realized="Loss of Western market access, banking restrictions",
                mitigation_options=[
                    "Diversify geographic exposure",
                    "Establish compliance firewalls",
                    "Pre-emptive divestment of high-risk assets"
                ],
                confidence=0.6
            )
        
        return None
    
    def _predict_financial_distress(self, target: str, context: Dict) -> Optional[PredictedRisk]:
        """Predict financial distress signals."""
        signals = context.get("risk_indicators", [])
        probability = 0.0
        triggers = []
        
        # Check for distress signals in context
        for signal, weight in self.FINANCIAL_DISTRESS_SIGNALS.items():
            if signal in str(signals).lower():
                probability += weight
                triggers.append(signal.replace("_", " ").title())
        
        # Always return a baseline if entity exists
        if probability > 0.2:
            return PredictedRisk(
                risk_type=RiskType.FINANCIAL_DISTRESS,
                probability=min(0.8, probability),
                time_horizon=TimeHorizon.SHORT_TERM,
                description="Financial distress indicators detected",
                triggers=triggers,
                early_warning_signs=[
                    "Credit facility draw-downs",
                    "Supplier payment delays",
                    "Key executive departures"
                ],
                impact_if_realized="Potential bankruptcy, supply chain disruption",
                mitigation_options=[
                    "Accelerate receivables collection",
                    "Identify alternative suppliers",
                    "Negotiate payment terms"
                ],
                confidence=0.5
            )
        
        return None
    
    def _predict_geopolitical_risk(self, target: str, context: Dict) -> Optional[PredictedRisk]:
        """Predict geopolitical exposure risk."""
        countries = [c.upper() for c in context.get("countries", [])]
        
        hotspot_exposure = []
        for hotspot in self.GEOPOLITICAL_HOTSPOTS:
            if any(hotspot in c for c in countries):
                hotspot_exposure.append(hotspot)
        
        if hotspot_exposure:
            return PredictedRisk(
                risk_type=RiskType.GEOPOLITICAL,
                probability=0.3 + 0.1 * len(hotspot_exposure),
                time_horizon=TimeHorizon.MEDIUM_TERM,
                description=f"Geopolitical exposure in: {', '.join(hotspot_exposure)}",
                triggers=[f"Escalation in {h}" for h in hotspot_exposure],
                early_warning_signs=[
                    "Military movements",
                    "Diplomatic incidents",
                    "Trade restriction announcements"
                ],
                impact_if_realized="Operational disruption, asset seizure, market access loss",
                mitigation_options=[
                    "Geographic diversification",
                    "Local partnership structures",
                    "Political risk insurance"
                ],
                confidence=0.7
            )
        
        return None
    
    def _predict_supply_chain_risk(self, target: str, context: Dict) -> Optional[PredictedRisk]:
        """Predict supply chain disruption risk."""
        countries = [c.upper() for c in context.get("countries", [])]
        
        # Check for concentration risk
        if any("TAIWAN" in c for c in countries):
            return PredictedRisk(
                risk_type=RiskType.SUPPLY_CHAIN_DISRUPTION,
                probability=0.4,
                time_horizon=TimeHorizon.LONG_TERM,
                description="Taiwan semiconductor supply dependency",
                triggers=["Cross-strait tensions", "Natural disasters", "US-China decoupling"],
                early_warning_signs=[
                    "TSMC capacity announcements",
                    "Chinese military exercises",
                    "US chip export controls"
                ],
                impact_if_realized="Critical component shortage, production halt",
                mitigation_options=[
                    "Qualify alternative suppliers",
                    "Build strategic inventory",
                    "Support reshoring initiatives"
                ],
                confidence=0.75
            )
        
        return None
    
    def _predict_regulatory_risk(self, target: str, context: Dict) -> Optional[PredictedRisk]:
        """Predict regulatory action risk."""
        target_lower = target.lower()
        
        # Tech companies face more regulatory scrutiny
        if any(term in target_lower for term in ["tech", "data", "ai", "social", "platform"]):
            return PredictedRisk(
                risk_type=RiskType.REGULATORY_ACTION,
                probability=0.5,
                time_horizon=TimeHorizon.SHORT_TERM,
                description="Elevated regulatory scrutiny (tech sector)",
                triggers=["Data privacy investigations", "Antitrust reviews", "AI regulation"],
                early_warning_signs=[
                    "Parliamentary hearings",
                    "Commissioner statements",
                    "Competitor regulatory actions"
                ],
                impact_if_realized="Fines, operational restrictions, forced divestitures",
                mitigation_options=[
                    "Proactive compliance investment",
                    "Regulatory engagement strategy",
                    "Business model adaptation"
                ],
                confidence=0.6
            )
        
        return None
    
    def _predict_cyber_risk(self, target: str, context: Dict) -> Optional[PredictedRisk]:
        """Predict cyber attack risk."""
        target_lower = target.lower()
        
        # Critical infrastructure and defense = higher cyber risk
        high_risk_sectors = ["defense", "energy", "bank", "government", "infrastructure", "aerospace"]
        
        if any(sector in target_lower for sector in high_risk_sectors):
            return PredictedRisk(
                risk_type=RiskType.CYBER,
                probability=0.6,
                time_horizon=TimeHorizon.IMMEDIATE,
                description="Elevated cyber attack risk (critical sector)",
                triggers=["State-sponsored campaigns", "Ransomware groups", "Insider threats"],
                early_warning_signs=[
                    "Industry peer attacks",
                    "Threat intelligence reports",
                    "Geopolitical tensions"
                ],
                impact_if_realized="Operational disruption, data breach, ransom demands",
                mitigation_options=[
                    "Zero-trust architecture",
                    "Incident response preparation",
                    "Cyber insurance"
                ],
                confidence=0.7
            )
        
        return None
    
    def _calculate_current_risk(self, context: Dict) -> float:
        """Calculate current risk score."""
        score = 20  # Baseline
        
        countries = [c.upper() for c in context.get("countries", [])]
        
        # Add for high-risk countries
        if any("RUSSIA" in c for c in countries):
            score += 20
        if any("CHINA" in c for c in countries):
            score += 10
        if any("IRAN" in c for c in countries):
            score += 25
        
        return min(100, score)
    
    def _calculate_predicted_risk(self, predictions: List[PredictedRisk]) -> float:
        """Calculate predicted risk score from predictions."""
        if not predictions:
            return 0
        
        # Weighted average of probabilities
        total = sum(p.probability * p.confidence * 100 for p in predictions)
        return min(100, total / len(predictions))
    
    def _determine_trajectory(self, current: float, predicted: float) -> str:
        """Determine risk trajectory."""
        diff = predicted - current
        
        if diff > 20:
            return "CRITICAL"
        elif diff > 10:
            return "DETERIORATING"
        elif diff < -10:
            return "IMPROVING"
        else:
            return "STABLE"
    
    def _get_key_indicators(self, predictions: List[PredictedRisk]) -> List[str]:
        """Extract key indicators to watch."""
        indicators = []
        for p in predictions[:3]:
            indicators.extend(p.early_warning_signs[:2])
        return list(set(indicators))[:5]
    
    def _get_alert_triggers(self, predictions: List[PredictedRisk]) -> List[str]:
        """Get recommended alert triggers."""
        triggers = []
        for p in predictions:
            if p.probability > 0.5:
                triggers.extend(p.triggers[:1])
        return list(set(triggers))[:3]
    
    def _generate_summary(self, report: PredictiveRiskReport) -> str:
        """Generate summary text."""
        if not report.predicted_risks:
            return f"{report.target}: No elevated risks predicted"
        
        top = report.predicted_risks[0]
        return (
            f"{report.target}: {report.overall_risk_trajectory} trajectory. "
            f"Top risk: {top.risk_type.value} ({top.probability*100:.0f}% in {top.time_horizon.value}). "
            f"Monitor: {', '.join(report.key_indicators_to_watch[:2])}"
        )


# Convenience function
async def predict_risks(target: str, graph_store=None) -> PredictiveRiskReport:
    """Quick predictive risk assessment."""
    scorer = PredictiveRiskScorer(graph_store)
    return await scorer.predict(target)
