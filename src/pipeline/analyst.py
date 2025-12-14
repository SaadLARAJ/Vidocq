"""
ShadowMap Graph Analyst - Intelligence Report Generator
Transforms raw Neo4j graph data into factual, unbiased intelligence reports.
"""

import json
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from src.storage.graph import GraphStore
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class GraphAnalyst:
    """
    Autonomous Graph Analyst Agent.
    Reads Neo4j graph data and produces factual intelligence reports.
    Multi-domain: Supply Chain, Geopolitics, Finance, Influence Networks.
    """
    
    # Universal Intelligence Analyst Prompt - Multi-Domain
    ANALYST_PROMPT = """ROLE: You are a Senior Intelligence Analyst. Your mission is to analyze a knowledge graph and produce professional, factual intelligence reports.

CAPABILITIES:
- You may use your GENERAL KNOWLEDGE to contextualize entities (e.g., "China is a major manufacturing hub", "This bank was involved in X scandal in 2020").
- You MUST clearly distinguish between:
  * FACTS FROM THE GRAPH (use: "The data shows...")
  * GENERAL KNOWLEDGE (use: "It is publicly known that...")
  * INFERENCES (use: "This suggests..." or "This may indicate...")

ANALYSIS DOMAINS (adapt based on entity types detected):
- SUPPLY CHAIN: Manufacturing dependencies, supplier risks, logistics bottlenecks
- GEOPOLITICS: Country risk, sanctions, territorial disputes, diplomatic relations
- FINANCE: Ownership structures, offshore entities, regulatory issues
- INFLUENCE NETWORKS: Media ownership, political connections, lobbying

STRICT RULES:
1. OBJECTIVITY: Base your analysis on the graph data. Enrich with public knowledge, but label it clearly.
2. RISK IDENTIFICATION: Flag high-risk nodes (sanctioned countries, legal disputes, single-source dependencies).
3. CLUSTERS & GAPS: Identify connected groups AND missing connections that would be expected.
4. CONFIDENCE WEIGHTING: Use the confidence scores. "90% confidence" ≠ "50% confidence".
5. NO SPECULATION: Never invent relationships that don't exist in the data.
6. PROFESSIONAL TONE: Write for a senior decision-maker. Be concise, direct, actionable.

OUTPUT FORMAT (Markdown):
1. **Executive Summary** - 3 key findings (bullet points)
2. **Entity Landscape** - Table of key actors with type and risk level
3. **Network Analysis** - Clusters, key connectors, isolated nodes
4. **Risk Assessment** - Critical dependencies, geopolitical exposure, data gaps
5. **Intelligence Gaps** - What's missing? What should be investigated next?

---

**GRAPH DATA**

{graph_data}

---

Generate the intelligence report now. Be factual, be useful, be brief."""

    def __init__(self):
        self.graph_store = GraphStore()
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    def fetch_graph_data(self, entity_filter: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        """
        Fetch all entities and relationships from Neo4j.
        Returns structured data for analysis.
        """
        # Query for entities
        entity_query = """
        MATCH (e:Entity)
        RETURN e.id as id, e.canonical_name as name, labels(e) as types, 
               e.entity_type as primary_type
        LIMIT $limit
        """
        
        # Query for relationships with confidence scores
        rel_query = """
        MATCH (s:Entity)-[r]->(t:Entity)
        RETURN s.canonical_name as source, 
               type(r) as relation, 
               t.canonical_name as target,
               r.confidence_score as confidence,
               r.evidence_snippet as evidence
        LIMIT $limit
        """
        
        entities = []
        relationships = []
        
        try:
            with self.graph_store.driver.session() as session:
                # Fetch entities
                result = session.run(entity_query, limit=limit)
                for record in result:
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["primary_type"] or "UNKNOWN"
                    })
                
                # Fetch relationships
                result = session.run(rel_query, limit=limit)
                for record in result:
                    confidence = record["confidence"]
                    if confidence is None:
                        confidence = 0.5  # Default medium confidence
                    
                    relationships.append({
                        "source": record["source"],
                        "relation": record["relation"],
                        "target": record["target"],
                        "confidence": round(float(confidence) * 100),  # Convert to percentage
                        "evidence": record["evidence"] or ""
                    })
                    
        except Exception as e:
            logger.error("graph_fetch_failed", error=str(e))
            raise
        
        return {
            "entities": entities,
            "relationships": relationships,
            "stats": {
                "entity_count": len(entities),
                "relationship_count": len(relationships)
            }
        }
    
    def format_graph_for_prompt(self, graph_data: Dict[str, Any]) -> str:
        """
        Convert graph data to human-readable format for the LLM.
        """
        lines = []
        
        # Format relationships
        for rel in graph_data["relationships"]:
            conf_str = f"{rel['confidence']}%"
            line = f"{rel['source']} -> [{rel['relation']}] -> {rel['target']} | Confidence: {conf_str}"
            lines.append(line)
        
        # Add stats
        stats = graph_data["stats"]
        lines.append("")
        lines.append(f"--- STATISTICS ---")
        lines.append(f"Total Entities: {stats['entity_count']}")
        lines.append(f"Total Relationships: {stats['relationship_count']}")
        
        # Add entity type breakdown
        type_counts = {}
        for ent in graph_data["entities"]:
            t = ent["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        
        lines.append("Entity Types:")
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - {t}: {count}")
        
        return "\n".join(lines)
    
    def generate_report(self, entity_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point: Fetch graph data and generate intelligence report.
        """
        logger.info("starting_graph_analysis", filter=entity_filter)
        
        # 1. Fetch data from Neo4j
        graph_data = self.fetch_graph_data(entity_filter=entity_filter)
        
        if graph_data["stats"]["entity_count"] == 0:
            return {
                "status": "empty",
                "report": "# No Data Available\n\nThe knowledge graph is empty. Please run discovery on target entities first.",
                "stats": graph_data["stats"]
            }
        
        # 2. Format for LLM
        formatted_data = self.format_graph_for_prompt(graph_data)
        
        # 3. Generate report with Gemini
        prompt = self.ANALYST_PROMPT.replace("{graph_data}", formatted_data)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,  # Low temp for factual reporting
                    "top_p": 0.9,
                    "max_output_tokens": 4096
                }
            )
            
            report = response.text.strip()
            
            logger.info("report_generated", 
                       entity_count=graph_data["stats"]["entity_count"],
                       relationship_count=graph_data["stats"]["relationship_count"])
            
            return {
                "status": "success",
                "report": report,
                "stats": graph_data["stats"],
                "raw_data": {
                    "entities": graph_data["entities"][:20],  # Preview
                    "relationships": graph_data["relationships"][:20]
                }
            }
            
        except Exception as e:
            logger.error("report_generation_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "stats": graph_data["stats"]
            }
    
    def export_graph_csv(self) -> str:
        """
        Export graph data as CSV for manual analysis.
        """
        graph_data = self.fetch_graph_data(limit=1000)
        
        lines = ["source,relation,target,confidence"]
        for rel in graph_data["relationships"]:
            line = f'"{rel["source"]}","{rel["relation"]}","{rel["target"]}",{rel["confidence"]}'
            lines.append(line)
        
        return "\n".join(lines)


# CLI Entry Point
if __name__ == "__main__":
    import sys
    
    print("ShadowMap Graph Analyst")
    print("=" * 50)
    
    analyst = GraphAnalyst()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--export":
        csv = analyst.export_graph_csv()
        print(csv)
    else:
        result = analyst.generate_report()
        print(result["report"])
