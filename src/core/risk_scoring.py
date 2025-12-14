"""
Multi-dimensional risk scoring for supply chain entities.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.core.logging import get_logger

logger = get_logger(__name__)


class RiskLevel(Enum):
    """Risk classification levels."""
    CRITICAL = "CRITICAL"   # Score >= 80
    HIGH = "HIGH"           # Score 60-79
    MEDIUM = "MEDIUM"       # Score 40-59
    LOW = "LOW"             # Score 20-39
    MINIMAL = "MINIMAL"     # Score < 20


@dataclass
class RiskScore:
    """Comprehensive risk score for an entity."""
    entity_id: str
    entity_name: str
    
    # Individual scores (0-100)
    concentration_score: float      # Dépendance à un seul fournisseur
    geopolitical_score: float       # Risque géopolitique du pays
    depth_score: float              # Profondeur N-tier (visibilité)
    sanctions_score: float          # Risque de sanctions
    esg_score: float                # Risque ESG (environnement, social)
    
    # Computed
    overall_score: float
    risk_level: RiskLevel
    
    # Details
    risk_factors: List[str]
    recommendations: List[str]


# Geopolitical Risk Database (simplified)
GEOPOLITICAL_RISK = {
    # Critical Risk Countries (Score 90-100)
    "RUSSIA": 95, "NORTH KOREA": 100, "IRAN": 90, "SYRIA": 95, "BELARUS": 85,
    "VENEZUELA": 80, "CUBA": 75, "MYANMAR": 85,
    
    # High Risk (Score 60-79)
    "CHINA": 70, "PAKISTAN": 65, "EGYPT": 55, "TURKEY": 50,
    "SAUDI ARABIA": 55, "UAE": 45, "VIETNAM": 40, "INDIA": 35,
    
    # Medium Risk (Score 30-49)
    "BRAZIL": 35, "MEXICO": 40, "ARGENTINA": 35, "SOUTH AFRICA": 40,
    "INDONESIA": 35, "THAILAND": 30, "MALAYSIA": 25, "PHILIPPINES": 35,
    
    # Low Risk (Score 10-29)
    "TAIWAN": 60,  # High due to China tension, not internal risk
    "SOUTH KOREA": 20, "JAPAN": 15, "ISRAEL": 45,
    "POLAND": 15, "CZECH REPUBLIC": 10, "HUNGARY": 25,
    
    # Minimal Risk (Score < 10)
    "USA": 10, "UK": 8, "GERMANY": 5, "FRANCE": 5, "NETHERLANDS": 5,
    "SWITZERLAND": 3, "CANADA": 8, "AUSTRALIA": 8, "SWEDEN": 3,
    "NORWAY": 3, "FINLAND": 3, "DENMARK": 3, "SINGAPORE": 10,
    
    # Default
    "UNKNOWN": 50
}

# Sanctions Lists Indicators
SANCTIONS_KEYWORDS = [
    "OFAC", "SDN", "sanctions", "sanctionné", "blacklist",
    "embargo", "restricted", "denied party", "BIS Entity List"
]

# ESG Risk Indicators
ESG_KEYWORDS = {
    "environmental": ["pollution", "toxic", "environmental violation", "EPA fine", "carbon"],
    "social": ["forced labor", "child labor", "slavery", "exploitation", "Uyghur"],
    "governance": ["corruption", "bribery", "fraud", "money laundering", "scandal"]
}


class RiskScorer:
    """
    Multi-dimensional risk scoring engine.
    Analyzes entities and their relationships to compute risk scores.
    """
    
    def __init__(self, graph_store=None):
        self.graph_store = graph_store
    
    def score_entity(self, entity_id: str, entity_name: str, 
                     relationships: List[Dict] = None,
                     locations: List[str] = None,
                     claims: List[Dict] = None) -> RiskScore:
        """
        Compute comprehensive risk score for an entity.
        
        Args:
            entity_id: Unique identifier
            entity_name: Display name
            relationships: List of relationships (suppliers, partners, etc.)
            locations: Countries/cities associated with entity
            claims: Extracted claims about the entity
        
        Returns:
            RiskScore with detailed breakdown
        """
        relationships = relationships or []
        locations = locations or []
        claims = claims or []
        
        risk_factors = []
        recommendations = []
        
        # 1. CONCENTRATION SCORE (Supply Chain Dependency)
        concentration = self._calculate_concentration(relationships)
        if concentration > 70:
            risk_factors.append(f"High supplier concentration ({concentration:.0f}%)")
            recommendations.append("Diversify supplier base to reduce single-point-of-failure risk")
        
        # 2. GEOPOLITICAL SCORE
        geo_score, geo_factors = self._calculate_geopolitical(locations)
        risk_factors.extend(geo_factors)
        if geo_score > 60:
            recommendations.append("Conduct enhanced due diligence on high-risk geography suppliers")
        
        # 3. DEPTH SCORE (N-Tier Visibility)
        depth_score = self._calculate_depth_visibility(relationships)
        if depth_score > 50:
            risk_factors.append("Limited visibility beyond Tier-1 suppliers")
            recommendations.append("Map deeper supply chain tiers (Tier 2+)")
        
        # 4. SANCTIONS SCORE
        sanctions_score, sanction_flags = self._check_sanctions_exposure(claims, entity_name)
        risk_factors.extend(sanction_flags)
        if sanctions_score > 50:
            recommendations.append("Immediate sanctions compliance review required")
        
        # 5. ESG SCORE
        esg_score, esg_flags = self._calculate_esg_risk(claims)
        risk_factors.extend(esg_flags)
        if esg_score > 40:
            recommendations.append("ESG audit recommended for flagged suppliers")
        
        # OVERALL SCORE (Weighted Average)
        weights = {
            "concentration": 0.20,
            "geopolitical": 0.25,
            "depth": 0.15,
            "sanctions": 0.25,
            "esg": 0.15
        }
        
        overall = (
            concentration * weights["concentration"] +
            geo_score * weights["geopolitical"] +
            depth_score * weights["depth"] +
            sanctions_score * weights["sanctions"] +
            esg_score * weights["esg"]
        )
        
        # Determine Risk Level
        if overall >= 80:
            level = RiskLevel.CRITICAL
        elif overall >= 60:
            level = RiskLevel.HIGH
        elif overall >= 40:
            level = RiskLevel.MEDIUM
        elif overall >= 20:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.MINIMAL
        
        return RiskScore(
            entity_id=entity_id,
            entity_name=entity_name,
            concentration_score=concentration,
            geopolitical_score=geo_score,
            depth_score=depth_score,
            sanctions_score=sanctions_score,
            esg_score=esg_score,
            overall_score=overall,
            risk_level=level,
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _calculate_concentration(self, relationships: List[Dict]) -> float:
        """
        Calculate supplier concentration risk.
        High score = too dependent on few suppliers.
        """
        if not relationships:
            return 50.0  # No data = medium risk
        
        # Count suppliers by type
        supplier_counts = {}
        for rel in relationships:
            rel_type = rel.get("type", "UNKNOWN")
            if rel_type in ["SUPPLIES", "COMPONENT_OF", "MANUFACTURES"]:
                supplier = rel.get("target", "unknown")
                supplier_counts[supplier] = supplier_counts.get(supplier, 0) + 1
        
        if not supplier_counts:
            return 30.0
        
        total = sum(supplier_counts.values())
        max_single = max(supplier_counts.values())
        
        # If single supplier > 50% of relationships = high concentration
        concentration_ratio = (max_single / total) * 100 if total > 0 else 0
        
        # Fewer unique suppliers = higher risk
        diversity_penalty = max(0, 100 - len(supplier_counts) * 10)
        
        return min(100, (concentration_ratio + diversity_penalty) / 2)
    
    def _calculate_geopolitical(self, locations: List[str]) -> Tuple[float, List[str]]:
        """Calculate geopolitical risk based on locations."""
        if not locations:
            return 40.0, ["No location data available"]
        
        factors = []
        scores = []
        
        for loc in locations:
            loc_upper = loc.upper().strip()
            score = GEOPOLITICAL_RISK.get(loc_upper, GEOPOLITICAL_RISK["UNKNOWN"])
            scores.append(score)
            
            if score >= 70:
                factors.append(f"High-risk country exposure: {loc}")
            elif score >= 50:
                factors.append(f"Elevated risk country: {loc}")
        
        # Worst-case dominates (max score has 60% weight, average 40%)
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            final = max_score * 0.6 + avg_score * 0.4
            return final, factors
        
        return 40.0, factors
    
    def _calculate_depth_visibility(self, relationships: List[Dict]) -> float:
        """
        Calculate N-tier visibility risk.
        Higher score = less visibility into deep supply chain.
        """
        if not relationships:
            return 70.0  # No relationships known = poor visibility
        
        # Count depth levels
        depths = [rel.get("depth", 1) for rel in relationships]
        max_depth = max(depths) if depths else 1
        avg_depth = sum(depths) / len(depths) if depths else 1
        
        # More depth = better visibility = lower risk
        depth_bonus = min(max_depth * 15, 60)
        
        return max(10, 100 - depth_bonus - len(relationships) * 2)
    
    def _check_sanctions_exposure(self, claims: List[Dict], entity_name: str) -> Tuple[float, List[str]]:
        """Check for sanctions-related red flags."""
        flags = []
        score = 0
        
        # Check entity name against known patterns
        name_lower = entity_name.lower()
        if any(kw in name_lower for kw in ["gazprom", "rosneft", "sberbank"]):
            score += 50
            flags.append(f"Entity name matches known sanctioned patterns: {entity_name}")
        
        # Check claims for sanctions keywords
        for claim in claims:
            evidence = claim.get("evidence", "").lower()
            for keyword in SANCTIONS_KEYWORDS:
                if keyword.lower() in evidence:
                    score += 20
                    flags.append(f"Sanctions-related keyword detected: {keyword}")
                    break
        
        return min(100, score), flags
    
    def _calculate_esg_risk(self, claims: List[Dict]) -> Tuple[float, List[str]]:
        """Calculate ESG risk from claims evidence."""
        flags = []
        total_score = 0
        
        for claim in claims:
            evidence = claim.get("evidence", "").lower()
            
            for category, keywords in ESG_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in evidence:
                        total_score += 15
                        flags.append(f"ESG {category} risk: {kw}")
                        break
        
        return min(100, total_score), flags
    
    def score_supply_chain(self, root_entity: str) -> Dict:
        """
        Score entire supply chain from a root entity.
        Returns aggregate risk and per-supplier breakdown.
        """
        if not self.graph_store:
            return {"error": "Graph store not configured"}
        
        # Query supply chain from Neo4j
        query = """
        MATCH (root:Entity {name: $entity})-[r*1..3]->(supplier:Entity)
        RETURN supplier.name as name, supplier.id as id, 
               labels(supplier) as labels, length(r) as depth
        """
        
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, entity=root_entity)
                suppliers = [dict(record) for record in result]
        except Exception as e:
            logger.error("supply_chain_query_failed", error=str(e))
            return {"error": str(e)}
        
        # Score each supplier
        scores = []
        for supplier in suppliers:
            score = self.score_entity(
                entity_id=supplier.get("id", "unknown"),
                entity_name=supplier.get("name", "Unknown"),
                relationships=[{"depth": supplier.get("depth", 1)}]
            )
            scores.append({
                "entity": supplier.get("name"),
                "depth": supplier.get("depth"),
                "score": score.overall_score,
                "level": score.risk_level.value,
                "factors": score.risk_factors[:3]  # Top 3 factors
            })
        
        # Aggregate
        if scores:
            avg_score = sum(s["score"] for s in scores) / len(scores)
            max_score = max(s["score"] for s in scores)
            critical_count = sum(1 for s in scores if s["level"] == "CRITICAL")
        else:
            avg_score = 0
            max_score = 0
            critical_count = 0
        
        return {
            "root_entity": root_entity,
            "supplier_count": len(scores),
            "average_risk": avg_score,
            "max_risk": max_score,
            "critical_suppliers": critical_count,
            "suppliers": sorted(scores, key=lambda x: x["score"], reverse=True)
        }


# Singleton
_scorer_instance = None


def get_risk_scorer(graph_store=None) -> RiskScorer:
    """Get or create the risk scorer singleton."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = RiskScorer(graph_store)
    return _scorer_instance
