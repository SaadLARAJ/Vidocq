"""
VIDOCQ - Ecosystem Learning & Cascade Prediction
Learns the full ecosystem and predicts impacts from events.

"Si grève dans une usine → Qui est impacté en cascade ?"

Features:
1. Validate entire reports (all relations become training data)
2. Learn graph structure for cascade predictions
3. Detect events and predict downstream impacts
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

from src.storage.graph import GraphStore
from src.core.logging import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """Types of events that can trigger cascade analysis"""
    STRIKE = "STRIKE"                    # Grève
    BANKRUPTCY = "BANKRUPTCY"            # Faillite
    SANCTION = "SANCTION"               # Nouvelle sanction
    NATURAL_DISASTER = "NATURAL_DISASTER"  # Catastrophe naturelle
    CYBER_ATTACK = "CYBER_ATTACK"       # Cyberattaque
    ACQUISITION = "ACQUISITION"         # Rachat
    PRODUCTION_STOP = "PRODUCTION_STOP"  # Arrêt de production
    PRICE_SPIKE = "PRICE_SPIKE"         # Flambée des prix
    POLITICAL = "POLITICAL"             # Événement politique
    SUPPLY_SHORTAGE = "SUPPLY_SHORTAGE"  # Pénurie


class CascadeImpact(BaseModel):
    """Impact on a single entity in the cascade"""
    entity: str
    distance: int  # 1 = direct, 2 = tier-2, etc.
    impact_type: str  # SUPPLY_DISRUPTION, PRICE_INCREASE, etc.
    severity: float  # 0.0 to 1.0
    reasoning: str


class CascadePrediction(BaseModel):
    """Full cascade prediction from an event"""
    trigger_event: str
    trigger_entity: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Direct impacts (tier 1)
    direct_impacts: List[CascadeImpact] = []
    
    # Cascade impacts (tier 2+)
    cascade_impacts: List[CascadeImpact] = []
    
    # Critical warnings
    critical_entities: List[str] = []
    
    # Summary
    total_affected: int = 0
    max_cascade_depth: int = 0
    executive_summary: str = ""


class ReportValidation(BaseModel):
    """
    Quality rating of an entire report.
    NOTE: This does NOT automatically validate relations.
    Each relation must be validated individually for learning.
    """
    report_id: str
    target: str
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    validator: str = "analyst"
    
    # Quality assessment (NOT learning)
    quality_score: float = 1.0  # 0.0 to 1.0
    precision_score: float = 1.0  # How precise is the data
    completeness_score: float = 1.0  # How complete is the coverage
    notes: Optional[str] = None
    
    # Stats (read-only, not validated)
    total_entities: int = 0
    total_relations: int = 0
    
    # Individual validations required
    relations_requiring_validation: int = 0


class RelationValidation(BaseModel):
    """
    Individual relation validation for learning.
    THIS is what trains the model - one relation at a time.
    """
    relation_id: str
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # The relation being validated
    source_entity: str
    target_entity: str
    relation_type: str
    
    # Validation decision
    is_correct: bool = True
    corrected_type: Optional[str] = None  # If wrong, what should it be?
    
    # Context for learning
    original_context: Optional[str] = None
    analyst_note: Optional[str] = None


class EcosystemLearner:
    """
    Learns the full ecosystem from validated data.
    
    IMPORTANT: Two types of validation:
    1. Report Quality = Just a rating, no learning
    2. Relation Validation = Individual, THIS is what trains the model
    """
    
    def __init__(self):
        self.graph_store = GraphStore()
    
    async def rate_report(
        self,
        target: str,
        quality_score: float = 1.0,
        precision_score: float = 1.0,
        completeness_score: float = 1.0,
        validator: str = "analyst",
        notes: Optional[str] = None
    ) -> ReportValidation:
        """
        Rate an entire report's quality.
        
        NOTE: This does NOT validate individual relations!
        It just rates the overall quality of the report.
        Use validate_relation() to train the model on individual relations.
        """
        logger.info("rating_report", target=target, quality=quality_score)
        
        # Count entities and relations for stats (read-only)
        total_entities = 0
        total_relations = 0
        unvalidated = 0
        
        try:
            with self.graph_store.driver.session() as session:
                # Count entities
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE toLower(e.canonical_name) CONTAINS toLower($target)
                    RETURN count(e) as count
                """, target=target)
                record = result.single()
                total_entities = record["count"] if record else 0
                
                # Count relations
                result = session.run("""
                    MATCH (e:Entity)-[r]-()
                    WHERE toLower(e.canonical_name) CONTAINS toLower($target)
                    RETURN count(r) as total,
                           sum(CASE WHEN r.validated = true THEN 0 ELSE 1 END) as unvalidated
                """, target=target)
                record = result.single()
                total_relations = record["total"] if record else 0
                unvalidated = record["unvalidated"] if record else 0
                
        except Exception as e:
            logger.error("report_stats_failed", error=str(e))
        
        return ReportValidation(
            report_id=f"report_{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            target=target,
            quality_score=quality_score,
            precision_score=precision_score,
            completeness_score=completeness_score,
            notes=notes,
            total_entities=total_entities,
            total_relations=total_relations,
            relations_requiring_validation=unvalidated
        )
    
    async def validate_relation(
        self,
        source_entity: str,
        target_entity: str,
        relation_type: str,
        is_correct: bool = True,
        corrected_type: Optional[str] = None,
        original_context: Optional[str] = None,
        analyst_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a SINGLE relation - THIS is what trains the model.
        
        Each call:
        1. Marks the relation as validated in Neo4j
        2. Stores as training example
        3. Updates confidence scores
        
        This is intentionally individual - the analyst must confirm each relation.
        """
        logger.info(
            "validating_relation",
            source=source_entity,
            target=target_entity,
            relation=relation_type,
            is_correct=is_correct
        )
        
        # 1. Update Neo4j
        try:
            with self.graph_store.driver.session() as session:
                if is_correct:
                    # Mark as validated
                    session.run("""
                        MATCH (s:Entity)-[r]->(t:Entity)
                        WHERE toLower(s.canonical_name) CONTAINS toLower($source)
                          AND toLower(t.canonical_name) CONTAINS toLower($target)
                        SET r.validated = true,
                            r.validation_date = datetime(),
                            r.confidence_score = 1.0,
                            r.visibility_status = 'CONFIRMED'
                    """, source=source_entity, target=target_entity)
                else:
                    # Mark as corrected (if wrong relation type)
                    session.run("""
                        MATCH (s:Entity)-[r]->(t:Entity)
                        WHERE toLower(s.canonical_name) CONTAINS toLower($source)
                          AND toLower(t.canonical_name) CONTAINS toLower($target)
                        SET r.corrected = true,
                            r.correction_date = datetime(),
                            r.original_type = type(r),
                            r.corrected_to = $corrected_type,
                            r.visibility_status = 'CONFIRMED'
                    """, source=source_entity, target=target_entity, corrected_type=corrected_type)
                    
        except Exception as e:
            logger.error("neo4j_validation_failed", error=str(e))
        
        # 2. Store as training example
        from src.core.feedback import FeedbackStore, FeedbackEntry, FeedbackType
        
        store = FeedbackStore()
        
        if is_correct:
            entry = FeedbackEntry(
                feedback_id=f"rel_{source_entity}_{target_entity}_{datetime.now().strftime('%H%M%S')}",
                source_entity=source_entity,
                target_entity=target_entity,
                original_relation=relation_type,
                feedback_type=FeedbackType.VALIDATE,
                original_context=original_context,
                analyst_note=analyst_note
            )
        else:
            entry = FeedbackEntry(
                feedback_id=f"rel_{source_entity}_{target_entity}_{datetime.now().strftime('%H%M%S')}",
                source_entity=source_entity,
                target_entity=target_entity,
                original_relation=relation_type,
                feedback_type=FeedbackType.CORRECT_RELATION,
                correct_value=corrected_type,
                original_context=original_context,
                analyst_note=analyst_note
            )
        
        result = await store.add_feedback(entry)
        
        return {
            "status": "success",
            "relation": f"{source_entity} → {relation_type} → {target_entity}",
            "action": "validated" if is_correct else f"corrected to {corrected_type}",
            "training_stored": True,
            "feedback_id": entry.feedback_id,
            "total_examples": result.get("total_feedback", 0)
        }
    
    async def get_relations_to_validate(
        self,
        target: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get list of relations that need validation for a target.
        Returns unvalidated relations for the analyst to review.
        """
        query = """
        MATCH (s:Entity)-[r]->(t:Entity)
        WHERE (toLower(s.canonical_name) CONTAINS toLower($target)
               OR toLower(t.canonical_name) CONTAINS toLower($target))
          AND r.validated IS NULL
          AND r.corrected IS NULL
        RETURN s.canonical_name as source,
               type(r) as relation,
               t.canonical_name as target,
               r.confidence_score as confidence,
               r.source_text as context
        LIMIT $limit
        """
        
        relations = []
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, target=target, limit=limit)
                for record in result:
                    relations.append({
                        "source": record["source"],
                        "relation": record["relation"],
                        "target": record["target"],
                        "confidence": record.get("confidence", 0.5),
                        "context": record.get("context", ""),
                        "needs_validation": True
                    })
        except Exception as e:
            logger.error("get_relations_failed", error=str(e))
        
        return relations
    
    async def predict_cascade(
        self,
        trigger_entity: str,
        event_type: EventType,
        max_depth: int = 3
    ) -> CascadePrediction:
        """
        Predict cascade impacts from an event.
        
        Example:
        - Event: "Strike at TSMC"
        - Prediction: Apple, NVIDIA, AMD impacted at tier 1
                      Car manufacturers at tier 2 (via chip shortage)
        """
        logger.info("predicting_cascade", entity=trigger_entity, event=event_type.value)
        
        prediction = CascadePrediction(
            trigger_event=f"{event_type.value} at {trigger_entity}",
            trigger_entity=trigger_entity,
            event_type=event_type
        )
        
        # Query graph for connected entities by depth
        for depth in range(1, max_depth + 1):
            impacts = await self._find_impacts_at_depth(
                trigger_entity, 
                event_type, 
                depth
            )
            
            if depth == 1:
                prediction.direct_impacts.extend(impacts)
            else:
                prediction.cascade_impacts.extend(impacts)
        
        # Find critical entities (high connectivity or marked as critical)
        prediction.critical_entities = await self._find_critical_in_cascade(
            trigger_entity, max_depth
        )
        
        # Calculate totals
        all_impacts = prediction.direct_impacts + prediction.cascade_impacts
        prediction.total_affected = len(all_impacts)
        prediction.max_cascade_depth = max(
            [i.distance for i in all_impacts], default=0
        )
        
        # Generate summary
        prediction.executive_summary = self._generate_summary(prediction)
        
        return prediction
    
    async def _find_impacts_at_depth(
        self,
        trigger: str,
        event_type: EventType,
        depth: int
    ) -> List[CascadeImpact]:
        """Find impacted entities at specific depth"""
        
        # Build dynamic path pattern based on depth
        path_pattern = "-[*" + str(depth) + "]-"
        
        query = f"""
        MATCH (trigger:Entity)-[r*{depth}]-(impacted:Entity)
        WHERE toLower(trigger.canonical_name) CONTAINS toLower($trigger)
        RETURN DISTINCT impacted.canonical_name as entity,
               impacted.sector as sector,
               {depth} as distance
        LIMIT 50
        """
        
        impacts = []
        
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, trigger=trigger)
                
                for record in result:
                    impact_type = self._determine_impact_type(event_type, record.get("sector"))
                    severity = self._calculate_severity(event_type, depth)
                    
                    impacts.append(CascadeImpact(
                        entity=record["entity"],
                        distance=depth,
                        impact_type=impact_type,
                        severity=severity,
                        reasoning=f"Connected at tier {depth} to {trigger}"
                    ))
        
        except Exception as e:
            logger.warning("cascade_query_failed", depth=depth, error=str(e))
        
        return impacts
    
    def _determine_impact_type(self, event_type: EventType, sector: Optional[str]) -> str:
        """Determine type of impact based on event and sector"""
        impact_map = {
            EventType.STRIKE: "SUPPLY_DISRUPTION",
            EventType.BANKRUPTCY: "SUPPLIER_LOSS",
            EventType.SANCTION: "COMPLIANCE_RISK",
            EventType.NATURAL_DISASTER: "FACILITY_DAMAGE",
            EventType.CYBER_ATTACK: "DATA_BREACH",
            EventType.PRODUCTION_STOP: "SHORTAGE",
            EventType.PRICE_SPIKE: "COST_INCREASE",
            EventType.SUPPLY_SHORTAGE: "PRODUCTION_DELAY"
        }
        return impact_map.get(event_type, "UNKNOWN_IMPACT")
    
    def _calculate_severity(self, event_type: EventType, depth: int) -> float:
        """Calculate severity (decreases with distance)"""
        base_severity = {
            EventType.BANKRUPTCY: 0.95,
            EventType.SANCTION: 0.90,
            EventType.STRIKE: 0.70,
            EventType.PRODUCTION_STOP: 0.80,
            EventType.CYBER_ATTACK: 0.85,
            EventType.NATURAL_DISASTER: 0.90
        }.get(event_type, 0.50)
        
        # Severity decreases with distance
        decay = 0.3 * (depth - 1)
        return max(0.1, base_severity - decay)
    
    async def _find_critical_in_cascade(
        self,
        trigger: str,
        max_depth: int
    ) -> List[str]:
        """Find critical entities in the cascade path"""
        
        query = """
        MATCH path = (trigger:Entity)-[*1..3]-(critical:Entity)
        WHERE toLower(trigger.canonical_name) CONTAINS toLower($trigger)
          AND (critical.sector IN ['defense', 'nuclear', 'semiconductor', 'energy']
               OR critical.is_critical = true
               OR critical.visibility_status = 'CONFIRMED')
        RETURN DISTINCT critical.canonical_name as name
        LIMIT 10
        """
        
        critical = []
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, trigger=trigger)
                critical = [record["name"] for record in result if record["name"]]
        except Exception as e:
            logger.warning("critical_query_failed", error=str(e))
        
        return critical
    
    def _generate_summary(self, prediction: CascadePrediction) -> str:
        """Generate executive summary"""
        
        if prediction.total_affected == 0:
            return f"Aucun impact en cascade détecté pour {prediction.trigger_entity}."
        
        severity = "CRITIQUE" if any(i.severity > 0.8 for i in prediction.direct_impacts) else "MODÉRÉ"
        
        summary = f"""ALERTE {severity}: {prediction.event_type.value} chez {prediction.trigger_entity}

IMPACTS DIRECTS ({len(prediction.direct_impacts)}):
{', '.join([i.entity for i in prediction.direct_impacts[:5]])}

CASCADE ({len(prediction.cascade_impacts)} entités):
Profondeur max: {prediction.max_cascade_depth} niveaux

ENTITÉS CRITIQUES AFFECTÉES:
{', '.join(prediction.critical_entities) if prediction.critical_entities else 'Aucune identifiée'}

RECOMMANDATION: Surveiller les sources alternatives et activer les plans de continuité.
"""
        return summary


# Singleton instance
ECOSYSTEM = EcosystemLearner()
