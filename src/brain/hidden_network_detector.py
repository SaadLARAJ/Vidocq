"""
VIDOCQ - Hidden Network Detector
Detects suspicious patterns that humans would miss.

"The most dangerous connections are the ones you don't see."

Advanced Graph Analytics:
1. Circular Ownership Detection (A → B → C → A)
2. Shell Company Cluster Detection
3. Unusual Intermediary Patterns
4. "Too Clean" Profile Detection
5. Suspicious Timing Patterns
6. Hidden Influence Networks
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field
from dataclasses import dataclass
from collections import defaultdict
import math

from src.core.logging import get_logger

logger = get_logger(__name__)


class SuspiciousPattern(BaseModel):
    """A detected suspicious pattern"""
    pattern_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: float = Field(ge=0, le=1)
    entities_involved: List[str]
    description: str
    evidence: List[str] = []
    investigation_hint: str = ""


class NetworkAnalysisResult(BaseModel):
    """Result of hidden network analysis"""
    target: str
    patterns_detected: int = 0
    risk_score: float = Field(ge=0, le=100, default=0)
    
    suspicious_patterns: List[SuspiciousPattern] = []
    
    # Network metrics
    centrality_score: float = 0.0  # How central is target in network
    cluster_coefficient: float = 0.0  # How clustered are connections
    
    # Specific detections
    circular_ownership: List[List[str]] = []  # Cycles found
    shell_company_clusters: List[List[str]] = []
    hidden_intermediaries: List[str] = []
    
    # Summary
    risk_level: str = "LOW"
    summary: str = ""
    recommendations: List[str] = []


class HiddenNetworkDetector:
    """
    Detects hidden patterns and suspicious networks in the knowledge graph.
    
    Uses graph algorithms to find:
    - Circular ownership (money laundering indicator)
    - Shell company clusters (tax evasion indicator)
    - Unusual intermediaries (corruption indicator)
    - Suspiciously sparse profiles (synthetic identity)
    """
    
    # Patterns that indicate shell companies
    SHELL_INDICATORS = [
        "registered agent",
        "nominee",
        "offshore",
        "trust",
        "holding",
        "investment vehicle",
        "SPV",
        "special purpose"
    ]
    
    # High-risk jurisdictions for shells
    SHELL_JURISDICTIONS = [
        "CAYMAN ISLANDS", "BRITISH VIRGIN ISLANDS", "BVI",
        "PANAMA", "JERSEY", "GUERNSEY", "ISLE OF MAN",
        "DELAWARE", "NEVADA", "LUXEMBOURG", "LIECHTENSTEIN",
        "SEYCHELLES", "MAURITIUS", "CYPRUS", "MALTA"
    ]
    
    def __init__(self, graph_store=None):
        self.graph_store = graph_store
    
    async def analyze(self, target: str) -> NetworkAnalysisResult:
        """
        Run complete hidden network analysis on a target.
        """
        result = NetworkAnalysisResult(target=target)
        
        try:
            # Get the network around the target
            network = await self._get_network(target, max_depth=4)
            
            if not network["nodes"]:
                result.summary = "No network data found for target"
                return result
            
            # Run all detection algorithms
            patterns = []
            
            # 1. Circular Ownership Detection
            cycles = self._detect_cycles(network, target)
            for cycle in cycles:
                patterns.append(SuspiciousPattern(
                    pattern_type="CIRCULAR_OWNERSHIP",
                    severity="CRITICAL",
                    confidence=0.9,
                    entities_involved=cycle,
                    description=f"Circular ownership detected: {' → '.join(cycle)}",
                    evidence=[f"Ownership chain forms a loop"],
                    investigation_hint="Check for round-tripping of funds or tax evasion"
                ))
            result.circular_ownership = cycles
            
            # 2. Shell Company Cluster Detection
            shell_clusters = self._detect_shell_clusters(network)
            for cluster in shell_clusters:
                patterns.append(SuspiciousPattern(
                    pattern_type="SHELL_CLUSTER",
                    severity="HIGH",
                    confidence=0.8,
                    entities_involved=cluster,
                    description=f"Shell company cluster: {len(cluster)} entities in offshore jurisdictions",
                    evidence=[f"Multiple entities in typical shell jurisdictions"],
                    investigation_hint="Trace beneficial ownership through the cluster"
                ))
            result.shell_company_clusters = shell_clusters
            
            # 3. Hidden Intermediary Detection
            intermediaries = self._detect_hidden_intermediaries(network, target)
            for inter in intermediaries:
                patterns.append(SuspiciousPattern(
                    pattern_type="HIDDEN_INTERMEDIARY",
                    severity="MEDIUM",
                    confidence=0.7,
                    entities_involved=[inter["entity"]],
                    description=f"Unusual intermediary: {inter['entity']} connects {inter['connects']} entities",
                    evidence=inter.get("reasons", []),
                    investigation_hint="Check if intermediary is known to target"
                ))
            result.hidden_intermediaries = [i["entity"] for i in intermediaries]
            
            # 4. Too Clean Profile Detection
            clean_profiles = self._detect_too_clean_profiles(network)
            for profile in clean_profiles:
                patterns.append(SuspiciousPattern(
                    pattern_type="SYNTHETIC_IDENTITY_RISK",
                    severity="MEDIUM",
                    confidence=0.6,
                    entities_involved=[profile["entity"]],
                    description=f"Suspiciously sparse profile: {profile['entity']}",
                    evidence=profile.get("missing", []),
                    investigation_hint="Verify identity through primary sources"
                ))
            
            # 5. Timing Pattern Detection
            timing_anomalies = self._detect_timing_patterns(network)
            for anomaly in timing_anomalies:
                patterns.append(SuspiciousPattern(
                    pattern_type="SUSPICIOUS_TIMING",
                    severity="MEDIUM",
                    confidence=anomaly.get("confidence", 0.6),
                    entities_involved=anomaly.get("entities", []),
                    description=anomaly["description"],
                    evidence=anomaly.get("evidence", []),
                    investigation_hint="Check for coordinated actions"
                ))
            
            # 6. Calculate network metrics
            result.centrality_score = self._calculate_centrality(network, target)
            result.cluster_coefficient = self._calculate_clustering(network, target)
            
            # Store patterns
            result.suspicious_patterns = patterns
            result.patterns_detected = len(patterns)
            
            # Calculate overall risk score
            result.risk_score = self._calculate_risk_score(patterns)
            result.risk_level = self._get_risk_level(result.risk_score)
            
            # Generate summary
            result.summary = self._generate_summary(result)
            result.recommendations = self._generate_recommendations(result)
            
            logger.info(
                "hidden_network_analysis_complete",
                target=target,
                patterns=len(patterns),
                risk_score=result.risk_score
            )
            
        except Exception as e:
            logger.error("hidden_network_analysis_failed", error=str(e))
            result.summary = f"Analysis failed: {str(e)}"
        
        return result
    
    async def _get_network(self, target: str, max_depth: int = 3) -> Dict[str, Any]:
        """Get network data from graph store."""
        if not self.graph_store:
            # Return mock data for testing
            return self._get_mock_network(target)
        
        query = """
        MATCH path = (start:Entity {canonical_name: $target})-[*1..4]-(connected:Entity)
        UNWIND relationships(path) as rel
        WITH DISTINCT startNode(rel) as source, endNode(rel) as target, type(rel) as rel_type, rel
        RETURN 
            source.canonical_name as source,
            source.type as source_type,
            source.country as source_country,
            target.canonical_name as target,
            target.type as target_type,
            target.country as target_country,
            rel_type,
            rel.created_at as rel_date
        LIMIT 500
        """
        
        try:
            with self.graph_store.driver.session() as session:
                result = session.run(query, {"target": target})
                
                nodes = {}
                edges = []
                
                for record in result:
                    source = record["source"]
                    target_node = record["target"]
                    
                    nodes[source] = {
                        "name": source,
                        "type": record["source_type"],
                        "country": record["source_country"]
                    }
                    nodes[target_node] = {
                        "name": target_node,
                        "type": record["target_type"],
                        "country": record["target_country"]
                    }
                    
                    edges.append({
                        "source": source,
                        "target": target_node,
                        "type": record["rel_type"],
                        "date": record["rel_date"]
                    })
                
                return {"nodes": nodes, "edges": edges}
                
        except Exception as e:
            logger.warning("network_query_failed", error=str(e))
            return {"nodes": {}, "edges": []}
    
    def _get_mock_network(self, target: str) -> Dict[str, Any]:
        """Generate mock network for testing."""
        return {
            "nodes": {
                target: {"name": target, "type": "COMPANY", "country": "FRANCE"},
                "Subsidiary A": {"name": "Subsidiary A", "type": "COMPANY", "country": "LUXEMBOURG"},
                "Holding B": {"name": "Holding B", "type": "COMPANY", "country": "CAYMAN ISLANDS"},
                "Director X": {"name": "Director X", "type": "PERSON", "country": None},
            },
            "edges": [
                {"source": target, "target": "Subsidiary A", "type": "OWNS", "date": None},
                {"source": "Subsidiary A", "target": "Holding B", "type": "OWNED_BY", "date": None},
                {"source": "Director X", "target": "Holding B", "type": "DIRECTS", "date": None},
            ]
        }
    
    def _detect_cycles(self, network: Dict, start: str) -> List[List[str]]:
        """Detect circular ownership patterns using DFS."""
        cycles = []
        
        # Build adjacency list for OWNS relations
        adj = defaultdict(list)
        for edge in network["edges"]:
            if edge["type"] in ["OWNS", "CONTROLS", "BENEFICIAL_OWNER"]:
                adj[edge["source"]].append(edge["target"])
        
        # DFS to find cycles
        def find_cycles(node: str, path: List[str], visited: Set[str]):
            if node in visited:
                # Found a cycle
                if node in path:
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    if len(cycle) >= 3:  # Minimum 3 entities for meaningful cycle
                        cycles.append(cycle)
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in adj[node]:
                find_cycles(neighbor, path.copy(), visited.copy())
        
        find_cycles(start, [], set())
        
        return cycles
    
    def _detect_shell_clusters(self, network: Dict) -> List[List[str]]:
        """Detect clusters of shell companies."""
        clusters = []
        shell_candidates = []
        
        for name, props in network["nodes"].items():
            country = (props.get("country") or "").upper()
            name_lower = name.lower()
            
            is_shell = False
            
            # Check jurisdiction
            if any(j in country for j in self.SHELL_JURISDICTIONS):
                is_shell = True
            
            # Check name patterns
            if any(ind in name_lower for ind in self.SHELL_INDICATORS):
                is_shell = True
            
            if is_shell:
                shell_candidates.append(name)
        
        # Group connected shells into clusters
        if len(shell_candidates) >= 2:
            # Simple: if 2+ shells are connected, it's a cluster
            shell_set = set(shell_candidates)
            connected_shells = []
            
            for edge in network["edges"]:
                if edge["source"] in shell_set and edge["target"] in shell_set:
                    connected_shells.extend([edge["source"], edge["target"]])
            
            if connected_shells:
                clusters.append(list(set(connected_shells)))
        
        return clusters
    
    def _detect_hidden_intermediaries(self, network: Dict, target: str) -> List[Dict]:
        """Detect entities that serve as unusual intermediaries."""
        intermediaries = []
        
        # Count connections per entity
        connection_count = defaultdict(int)
        for edge in network["edges"]:
            connection_count[edge["source"]] += 1
            connection_count[edge["target"]] += 1
        
        # Find entities with high betweenness (many connections but not the target)
        for entity, count in connection_count.items():
            if entity == target:
                continue
            
            if count >= 3:  # Connected to 3+ entities
                node = network["nodes"].get(entity, {})
                
                # Check if this seems like a legitimate intermediary
                reasons = []
                
                if node.get("type") == "PERSON":
                    reasons.append("Person connecting multiple organizations")
                
                country = (node.get("country") or "").upper()
                if any(j in country for j in self.SHELL_JURISDICTIONS):
                    reasons.append(f"Located in {country}")
                
                if reasons:
                    intermediaries.append({
                        "entity": entity,
                        "connects": count,
                        "reasons": reasons
                    })
        
        return intermediaries
    
    def _detect_too_clean_profiles(self, network: Dict) -> List[Dict]:
        """Detect profiles that are suspiciously sparse."""
        clean_profiles = []
        
        for name, props in network["nodes"].items():
            missing = []
            
            if not props.get("country"):
                missing.append("No country information")
            
            if props.get("type") == "PERSON":
                # Persons should have more info
                missing.append("Limited personal information")
            
            # Check connection count
            connections = sum(
                1 for e in network["edges"] 
                if e["source"] == name or e["target"] == name
            )
            
            if connections == 1:
                missing.append("Only one connection (isolated)")
            
            if len(missing) >= 2:
                clean_profiles.append({
                    "entity": name,
                    "missing": missing
                })
        
        return clean_profiles
    
    def _detect_timing_patterns(self, network: Dict) -> List[Dict]:
        """Detect suspicious timing patterns in entity creation/relations."""
        anomalies = []
        
        # Check for entities created around same time
        dates = []
        for edge in network["edges"]:
            if edge.get("date"):
                dates.append((edge["date"], edge["source"], edge["target"]))
        
        if len(dates) >= 3:
            # If multiple relations created same day = coordinated
            from collections import Counter
            date_counts = Counter(d[0] for d in dates if d[0])
            
            for date, count in date_counts.items():
                if count >= 3:
                    entities = set()
                    for d in dates:
                        if d[0] == date:
                            entities.add(d[1])
                            entities.add(d[2])
                    
                    anomalies.append({
                        "description": f"{count} relations created on same day",
                        "confidence": min(0.9, 0.5 + count * 0.1),
                        "entities": list(entities),
                        "evidence": [f"All created on {date}"]
                    })
        
        return anomalies
    
    def _calculate_centrality(self, network: Dict, target: str) -> float:
        """Calculate how central the target is in the network."""
        if not network["edges"]:
            return 0.0
        
        # Simple degree centrality
        connections = sum(
            1 for e in network["edges"] 
            if e["source"] == target or e["target"] == target
        )
        
        max_possible = len(network["nodes"]) - 1
        if max_possible == 0:
            return 0.0
        
        return min(1.0, connections / max_possible)
    
    def _calculate_clustering(self, network: Dict, target: str) -> float:
        """Calculate local clustering coefficient."""
        # Get neighbors of target
        neighbors = set()
        for edge in network["edges"]:
            if edge["source"] == target:
                neighbors.add(edge["target"])
            elif edge["target"] == target:
                neighbors.add(edge["source"])
        
        if len(neighbors) < 2:
            return 0.0
        
        # Count edges between neighbors
        neighbor_edges = 0
        for edge in network["edges"]:
            if edge["source"] in neighbors and edge["target"] in neighbors:
                neighbor_edges += 1
        
        # Max possible edges between neighbors
        max_edges = len(neighbors) * (len(neighbors) - 1) / 2
        
        return neighbor_edges / max_edges if max_edges > 0 else 0.0
    
    def _calculate_risk_score(self, patterns: List[SuspiciousPattern]) -> float:
        """Calculate overall risk score from patterns."""
        if not patterns:
            return 0.0
        
        severity_weights = {
            "CRITICAL": 40,
            "HIGH": 25,
            "MEDIUM": 15,
            "LOW": 5
        }
        
        score = 0
        for pattern in patterns:
            weight = severity_weights.get(pattern.severity, 10)
            score += weight * pattern.confidence
        
        return min(100, score)
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to level."""
        if score >= 75:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 25:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_summary(self, result: NetworkAnalysisResult) -> str:
        """Generate human-readable summary."""
        if result.patterns_detected == 0:
            return f"No suspicious patterns detected for {result.target}"
        
        parts = [f"Analysis of {result.target}: "]
        
        if result.circular_ownership:
            parts.append(f"⚠️ {len(result.circular_ownership)} circular ownership pattern(s). ")
        
        if result.shell_company_clusters:
            parts.append(f"🏢 {len(result.shell_company_clusters)} shell company cluster(s). ")
        
        if result.hidden_intermediaries:
            parts.append(f"👤 {len(result.hidden_intermediaries)} suspicious intermediary(ies). ")
        
        parts.append(f"Overall risk: {result.risk_level} ({result.risk_score:.0f}/100)")
        
        return "".join(parts)
    
    def _generate_recommendations(self, result: NetworkAnalysisResult) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        
        if result.circular_ownership:
            recs.append("🔴 CRITICAL: Investigate circular ownership for potential money laundering")
        
        if result.shell_company_clusters:
            recs.append("🟠 HIGH: Trace beneficial ownership through shell company cluster")
        
        if result.hidden_intermediaries:
            recs.append("🟡 MEDIUM: Verify legitimacy of intermediary entities")
        
        if result.risk_score >= 50:
            recs.append("📋 Recommend enhanced due diligence before any business relationship")
        
        if not recs:
            recs.append("✅ No immediate action required, standard monitoring sufficient")
        
        return recs


# Convenience function
async def detect_hidden_networks(target: str, graph_store=None) -> NetworkAnalysisResult:
    """Quick analysis for hidden networks."""
    detector = HiddenNetworkDetector(graph_store)
    return await detector.analyze(target)
