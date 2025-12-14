"""
VIDOCQ BRAIN - Supply Chain Wargaming
Simulate catastrophic scenarios and propagate shock waves through the graph.

"Que se passe-t-il si Taiwan est bloqué demain?"

Features:
- What-if scenario simulation
- Shock wave propagation through supply chain
- Impact assessment on dependent entities
- Risk cascade visualization
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum

from src.storage.graph import GraphStore
from src.core.logging import get_logger

logger = get_logger(__name__)


class ScenarioType(str, Enum):
    """Types of catastrophic scenarios"""
    EMBARGO = "EMBARGO"               # Trade embargo on a country
    SUPPLIER_FAILURE = "SUPPLIER_FAILURE"  # Key supplier goes bankrupt
    CONFLICT = "CONFLICT"             # Military conflict
    SANCTION = "SANCTION"             # New sanctions imposed
    NATURAL_DISASTER = "NATURAL_DISASTER"  # Earthquake, flood, etc.
    CYBER_ATTACK = "CYBER_ATTACK"     # Critical infrastructure attack
    NATIONALIZATION = "NATIONALIZATION"  # Foreign assets seized


class ImpactLevel(str, Enum):
    """Level of impact from scenario"""
    CATASTROPHIC = "CATASTROPHIC"  # Complete failure
    SEVERE = "SEVERE"              # Major disruption
    MODERATE = "MODERATE"          # Significant impact
    MINOR = "MINOR"                # Some impact
    NEGLIGIBLE = "NEGLIGIBLE"      # Minimal impact


class AffectedEntity(BaseModel):
    """An entity affected by the scenario"""
    entity_id: str
    entity_name: str
    entity_type: str
    impact_level: ImpactLevel
    impact_delay_days: int  # How many days until impact hits
    dependency_chain: List[str]  # Path from trigger to this entity
    mitigation_possible: bool
    mitigation_options: List[str] = []


class WargameScenario(BaseModel):
    """A complete wargame scenario simulation"""
    scenario_id: str
    scenario_type: ScenarioType
    trigger_entity: str
    trigger_description: str
    simulation_date: datetime
    
    # Results
    affected_entities: List[AffectedEntity]
    total_affected: int
    cascade_depth: int  # How many levels of supply chain affected
    estimated_recovery_days: int
    
    # Analysis
    critical_nodes: List[str]  # Single points of failure
    recommended_actions: List[str]
    summary: str


class SupplyChainWargamer:
    """
    The Digital Twin of Chaos.
    
    Simulates catastrophic scenarios by propagating shock waves through
    the knowledge graph. Answers: "What happens if X fails?"
    
    Use cases:
    - "What if Taiwan is blockaded?" → Shows all dependencies on TSMC
    - "What if Supplier X goes bankrupt?" → Shows cascade effects
    - "What if Russia cuts gas?" → Shows energy dependencies
    """
    
    def __init__(self):
        self.graph_store = GraphStore()
        
        # Impact propagation rules
        self.propagation_rules = {
            "SUPPLIES": 0.9,           # Supplier failure = 90% impact
            "DEPENDS_ON": 0.85,        # Dependency = 85% impact
            "OWNED_BY": 0.7,           # Ownership = 70% impact
            "PARTNERS_WITH": 0.4,      # Partnership = 40% impact
            "LOCATED_IN": 0.6,         # Location = 60% impact for geo scenarios
            "BENEFICIAL_OWNER_OF": 0.5 # UBO = 50% impact
        }
        
        # Recovery time estimates by impact type
        self.recovery_estimates = {
            ImpactLevel.CATASTROPHIC: 365,
            ImpactLevel.SEVERE: 180,
            ImpactLevel.MODERATE: 90,
            ImpactLevel.MINOR: 30,
            ImpactLevel.NEGLIGIBLE: 7
        }
    
    async def simulate(
        self,
        trigger_entity: str,
        scenario_type: ScenarioType,
        description: Optional[str] = None
    ) -> WargameScenario:
        """
        Run a wargame simulation.
        
        Args:
            trigger_entity: The entity that fails/is blocked (e.g., "Taiwan", "TSMC")
            scenario_type: Type of scenario (EMBARGO, SUPPLIER_FAILURE, etc.)
            description: Optional description of the scenario
        """
        logger.info(
            "wargame_simulation_started",
            trigger=trigger_entity,
            scenario=scenario_type.value
        )
        
        scenario_id = f"WG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Step 1: Find the trigger entity in the graph
        trigger_id = await self._find_entity(trigger_entity)
        
        # Step 2: Propagate shock wave through graph
        affected_entities = await self._propagate_shock(
            trigger_id=trigger_id,
            trigger_name=trigger_entity,
            scenario_type=scenario_type
        )
        
        # Step 3: Identify critical nodes (single points of failure)
        critical_nodes = self._identify_critical_nodes(affected_entities)
        
        # Step 4: Calculate cascade depth
        max_depth = max(
            (len(e.dependency_chain) for e in affected_entities),
            default=0
        )
        
        # Step 5: Estimate recovery time
        recovery_days = self._estimate_recovery(affected_entities)
        
        # Step 6: Generate recommendations
        recommendations = self._generate_recommendations(
            scenario_type, affected_entities, critical_nodes
        )
        
        # Step 7: Generate summary
        summary = self._generate_summary(
            trigger_entity, scenario_type, affected_entities, max_depth
        )
        
        scenario = WargameScenario(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            trigger_entity=trigger_entity,
            trigger_description=description or f"{scenario_type.value} affecting {trigger_entity}",
            simulation_date=datetime.utcnow(),
            affected_entities=affected_entities,
            total_affected=len(affected_entities),
            cascade_depth=max_depth,
            estimated_recovery_days=recovery_days,
            critical_nodes=critical_nodes,
            recommended_actions=recommendations,
            summary=summary
        )
        
        logger.info(
            "wargame_simulation_complete",
            trigger=trigger_entity,
            affected=len(affected_entities),
            depth=max_depth
        )
        
        return scenario
    
    async def _find_entity(self, entity_name: str) -> Optional[str]:
        """Find entity ID in graph."""
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.canonical_name) CONTAINS toLower($name)
           OR toLower(e.id) CONTAINS toLower($name)
        RETURN e.id as id
        LIMIT 1
        """
        
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, name=entity_name)
                record = result.single()
                return record["id"] if record else None
        except Exception as e:
            logger.error("entity_lookup_failed", error=str(e))
            return None
    
    async def _propagate_shock(
        self,
        trigger_id: Optional[str],
        trigger_name: str,
        scenario_type: ScenarioType,
        max_depth: int = 5
    ) -> List[AffectedEntity]:
        """
        Propagate shock wave through the graph.
        Uses BFS to find all downstream affected entities.
        """
        affected = []
        visited: Set[str] = set()
        
        # Query to find all connected entities
        query = """
        MATCH (source:Entity)-[r]->(target:Entity)
        WHERE source.id = $source_id OR source.canonical_name CONTAINS $source_name
        RETURN target.id as target_id,
               target.canonical_name as target_name,
               labels(target)[1] as target_type,
               type(r) as relation_type,
               source.canonical_name as source_name
        """
        
        # BFS queue: (entity_id, entity_name, depth, chain, cumulative_impact)
        queue = [(trigger_id, trigger_name, 0, [trigger_name], 1.0)]
        
        try:
            with self.graph_store.driver.session() as session:
                while queue and len(affected) < 100:  # Limit to 100 entities
                    current_id, current_name, depth, chain, impact = queue.pop(0)
                    
                    if depth >= max_depth:
                        continue
                    
                    if current_name in visited:
                        continue
                    visited.add(current_name)
                    
                    # Find downstream entities
                    result = session.run(
                        query, 
                        source_id=current_id or "",
                        source_name=current_name
                    )
                    
                    for record in result:
                        target_name = record["target_name"]
                        target_type = record["target_type"] or "Entity"
                        relation_type = record["relation_type"]
                        
                        if target_name in visited:
                            continue
                        
                        # Calculate propagated impact
                        propagation_factor = self.propagation_rules.get(relation_type, 0.3)
                        new_impact = impact * propagation_factor
                        
                        # Determine impact level
                        impact_level = self._calculate_impact_level(new_impact, scenario_type)
                        
                        # Create affected entity
                        new_chain = chain + [target_name]
                        
                        entity = AffectedEntity(
                            entity_id=record["target_id"],
                            entity_name=target_name,
                            entity_type=target_type,
                            impact_level=impact_level,
                            impact_delay_days=depth * 30,  # ~30 days per tier
                            dependency_chain=new_chain,
                            mitigation_possible=impact_level not in [ImpactLevel.CATASTROPHIC],
                            mitigation_options=self._suggest_mitigations(
                                target_type, relation_type, impact_level
                            )
                        )
                        
                        affected.append(entity)
                        
                        # Add to queue for further propagation
                        queue.append((
                            record["target_id"],
                            target_name,
                            depth + 1,
                            new_chain,
                            new_impact
                        ))
        
        except Exception as e:
            logger.error("shock_propagation_failed", error=str(e))
        
        return affected
    
    def _calculate_impact_level(
        self, 
        impact_score: float, 
        scenario_type: ScenarioType
    ) -> ImpactLevel:
        """Calculate impact level from propagated score."""
        
        # Adjust thresholds based on scenario severity
        severity_multiplier = {
            ScenarioType.CONFLICT: 1.2,
            ScenarioType.EMBARGO: 1.1,
            ScenarioType.SANCTION: 1.0,
            ScenarioType.SUPPLIER_FAILURE: 0.9,
            ScenarioType.NATURAL_DISASTER: 0.8,
            ScenarioType.CYBER_ATTACK: 0.7,
            ScenarioType.NATIONALIZATION: 1.0
        }.get(scenario_type, 1.0)
        
        adjusted_score = impact_score * severity_multiplier
        
        if adjusted_score > 0.8:
            return ImpactLevel.CATASTROPHIC
        elif adjusted_score > 0.6:
            return ImpactLevel.SEVERE
        elif adjusted_score > 0.4:
            return ImpactLevel.MODERATE
        elif adjusted_score > 0.2:
            return ImpactLevel.MINOR
        else:
            return ImpactLevel.NEGLIGIBLE
    
    def _suggest_mitigations(
        self,
        entity_type: str,
        relation_type: str,
        impact_level: ImpactLevel
    ) -> List[str]:
        """Suggest mitigation options based on impact type."""
        
        mitigations = []
        
        if relation_type == "SUPPLIES":
            mitigations.extend([
                "Identifier des fournisseurs alternatifs",
                "Constituer un stock de sécurité (3-6 mois)",
                "Négocier des clauses de force majeure"
            ])
        
        if entity_type == "COUNTRY":
            mitigations.extend([
                "Diversifier géographiquement la chaîne",
                "Relocaliser les opérations critiques"
            ])
        
        if impact_level in [ImpactLevel.CATASTROPHIC, ImpactLevel.SEVERE]:
            mitigations.append("Mettre en place un plan de continuité d'activité (PCA)")
        
        return mitigations[:3]  # Limit to 3 options
    
    def _identify_critical_nodes(
        self, 
        affected: List[AffectedEntity]
    ) -> List[str]:
        """Identify single points of failure."""
        
        critical = []
        
        # Entities with catastrophic impact
        for entity in affected:
            if entity.impact_level == ImpactLevel.CATASTROPHIC:
                critical.append(entity.entity_name)
        
        # Entities that appear in multiple chains (bottlenecks)
        chain_appearances = {}
        for entity in affected:
            for node in entity.dependency_chain[:-1]:  # Exclude the entity itself
                chain_appearances[node] = chain_appearances.get(node, 0) + 1
        
        for node, count in chain_appearances.items():
            if count >= 3 and node not in critical:
                critical.append(node)
        
        return critical[:10]  # Top 10 critical nodes
    
    def _estimate_recovery(self, affected: List[AffectedEntity]) -> int:
        """Estimate total recovery time in days."""
        
        if not affected:
            return 0
        
        # Take the worst case
        worst_impact = max(
            (e.impact_level for e in affected),
            key=lambda x: list(ImpactLevel).index(x),
            default=ImpactLevel.MINOR
        )
        
        return self.recovery_estimates.get(worst_impact, 90)
    
    def _generate_recommendations(
        self,
        scenario_type: ScenarioType,
        affected: List[AffectedEntity],
        critical_nodes: List[str]
    ) -> List[str]:
        """Generate strategic recommendations."""
        
        recommendations = []
        
        catastrophic_count = sum(
            1 for e in affected 
            if e.impact_level == ImpactLevel.CATASTROPHIC
        )
        
        if catastrophic_count > 0:
            recommendations.append(
                f"URGENT: {catastrophic_count} entités à risque catastrophique. "
                f"Initier immédiatement une diversification."
            )
        
        if critical_nodes:
            recommendations.append(
                f"Points de défaillance uniques identifiés: {', '.join(critical_nodes[:3])}. "
                f"Créer des redondances."
            )
        
        if scenario_type in [ScenarioType.EMBARGO, ScenarioType.CONFLICT]:
            recommendations.append(
                "Recommandation géopolitique: Réduire l'exposition aux zones à risque. "
                "Envisager le nearshoring."
            )
        
        recommendations.append(
            "Mettre à jour le registre des risques avec ce scénario simulé."
        )
        
        return recommendations
    
    def _generate_summary(
        self,
        trigger: str,
        scenario_type: ScenarioType,
        affected: List[AffectedEntity],
        max_depth: int
    ) -> str:
        """Generate executive summary."""
        
        catastrophic = sum(1 for e in affected if e.impact_level == ImpactLevel.CATASTROPHIC)
        severe = sum(1 for e in affected if e.impact_level == ImpactLevel.SEVERE)
        
        return (
            f"SIMULATION: {scenario_type.value} sur {trigger}. "
            f"Impact propagé sur {len(affected)} entités en {max_depth} niveaux de cascade. "
            f"Impacts critiques: {catastrophic}. Impacts sévères: {severe}. "
            f"{'ACTION IMMÉDIATE REQUISE.' if catastrophic > 0 else 'Surveillance recommandée.'}"
        )
