"""
VIDOCQ BRAIN - Geo-Sourced Reporter
Generates intelligence reports structured by geographic origin of sources.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from src.brain.core_logic import VidocqBrain, TargetProfile, TargetType, PredictiveAlert
from src.brain.source_analyst import SourceIntelligence, SourceOrigin, SourceAnalysis
from src.pipeline.analyst import GraphAnalyst
from src.core.logging import get_logger
from src.config import settings

import google.generativeai as genai

logger = get_logger(__name__)


class GeoSourcedReport(BaseModel):
    """Complete geo-sourced intelligence report"""
    title: str
    target: str
    target_type: str
    generated_at: datetime
    
    # Sections
    executive_summary: str
    western_perspective: str
    hostile_perspective: str
    local_perspective: str
    risk_assessment: str
    recommendations: List[str]
    
    # Metadata
    source_breakdown: Dict[str, int]
    alerts: List[Dict]
    confidence_score: float


class GeoSourcedReporter:
    """
    Generates intelligence reports that separate information by source origin.
    
    This allows decision-makers to see:
    - What WESTERN sources say (US, EU perspective)
    - What HOSTILE sources say (RU, CN perspective)
    - What LOCAL sources say (on-the-ground info)
    - Where the narratives DIVERGE (information warfare)
    """
    
    def __init__(self):
        self.brain = VidocqBrain()
        self.source_intel = SourceIntelligence()
        self.graph_analyst = GraphAnalyst()
        
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self.model = None
    
    async def generate_report(
        self,
        target: str,
        include_analysis: bool = True
    ) -> GeoSourcedReport:
        """
        Generate a complete geo-sourced intelligence report.
        """
        logger.info("generating_geosourced_report", target=target)
        
        # Step 1: Get brain analysis
        brain_analysis = await self.brain.analyze(target)
        profile = TargetProfile(**brain_analysis["profile"])
        alerts = brain_analysis["alerts"]
        
        # Step 2: Get graph data and cluster sources
        graph_data = self._get_graph_data_with_sources(target)
        source_clusters = self._cluster_sources(graph_data.get("sources", []))
        
        # Step 3: Generate section by section
        if self.model and include_analysis:
            sections = await self._generate_sections(
                target=target,
                profile=profile,
                graph_data=graph_data,
                source_clusters=source_clusters
            )
        else:
            sections = self._generate_fallback_sections(
                target=target,
                profile=profile,
                source_clusters=source_clusters
            )
        
        # Step 4: Build final report
        report = GeoSourcedReport(
            title=f"Intelligence Report: {target}",
            target=target,
            target_type=profile.target_type.value,
            generated_at=datetime.utcnow(),
            executive_summary=sections["summary"],
            western_perspective=sections["western"],
            hostile_perspective=sections["hostile"],
            local_perspective=sections["local"],
            risk_assessment=sections["risk"],
            recommendations=sections["recommendations"],
            source_breakdown={
                origin.value: len(sources) 
                for origin, sources in source_clusters.items()
            },
            alerts=alerts,
            confidence_score=self._calculate_confidence(source_clusters)
        )
        
        logger.info("geosourced_report_complete", target=target)
        return report
    
    def _get_graph_data_with_sources(self, target: str) -> Dict[str, Any]:
        """Retrieve graph data including source URLs"""
        try:
            from src.storage.graph import GraphStore
            graph = GraphStore()
            
            query = """
            MATCH (e:Entity)-[r]->(connected:Entity)
            WHERE toLower(e.canonical_name) CONTAINS toLower($target)
               OR toLower(e.id) CONTAINS toLower($target)
            RETURN e.canonical_name as entity,
                   type(r) as relation,
                   connected.canonical_name as connected_entity,
                   r.source_url as source_url,
                   r.confidence_score as confidence
            LIMIT 50
            """
            
            with graph.driver.session() as session:
                result = session.run(query, target=target)
                records = list(result)
            
            relations = []
            sources = []
            
            for record in records:
                relations.append({
                    "entity": record["entity"],
                    "relation": record["relation"],
                    "connected": record["connected_entity"],
                    "confidence": record["confidence"]
                })
                if record["source_url"]:
                    sources.append(record["source_url"])
            
            return {
                "relations": relations,
                "sources": list(set(sources)),
                "entity_count": len(set(r["entity"] for r in relations)),
                "relation_count": len(relations)
            }
            
        except Exception as e:
            logger.error("graph_data_retrieval_failed", error=str(e))
            return {"relations": [], "sources": []}
    
    def _cluster_sources(
        self, 
        source_urls: List[str]
    ) -> Dict[SourceOrigin, List[SourceAnalysis]]:
        """Cluster source URLs by geographic origin"""
        return self.source_intel.cluster_by_origin(source_urls)
    
    async def _generate_sections(
        self,
        target: str,
        profile: TargetProfile,
        graph_data: Dict[str, Any],
        source_clusters: Dict[SourceOrigin, List[SourceAnalysis]]
    ) -> Dict[str, Any]:
        """Generate report sections using LLM"""
        
        # Build context for LLM
        context = self._build_context(target, profile, graph_data, source_clusters)
        
        prompt = f"""Tu es un analyste de renseignement stratégique senior.
Génère un rapport d'intelligence basé sur ces données.

CIBLE: {target}
TYPE: {profile.target_type.value}
SECTEUR: {profile.probable_sector or "Non déterminé"}

DONNÉES DU GRAPHE:
{context}

RÉPARTITION DES SOURCES:
- Sources OCCIDENTALES (US/EU): {len(source_clusters.get(SourceOrigin.WESTERN, []))}
- Sources HOSTILES (RU/CN): {len(source_clusters.get(SourceOrigin.HOSTILE, []))}
- Sources NEUTRES: {len(source_clusters.get(SourceOrigin.NEUTRAL, []))}

Génère un JSON avec ces sections:
{{
    "summary": "Synthèse exécutive en 3-4 phrases",
    "western": "Ce que disent les sources occidentales (ou 'Pas de données' si aucune)",
    "hostile": "Ce que disent les sources hostiles (ou 'Pas de données' si aucune)",
    "local": "Informations de terrain/locales",
    "risk": "Évaluation des risques principaux",
    "recommendations": ["Liste", "de", "recommandations"]
}}

RÈGLES:
- Reste factuel, cite les sources
- Signale les CONTRADICTIONS entre blocs géographiques
- Identifie les signaux de PROPAGANDE ou DÉSINFORMATION"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 2000}
            )
            
            import json
            text = response.text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
            
        except Exception as e:
            logger.error("section_generation_failed", error=str(e))
            return self._generate_fallback_sections(target, profile, source_clusters)
    
    def _generate_fallback_sections(
        self,
        target: str,
        profile: TargetProfile,
        source_clusters: Dict[SourceOrigin, List[SourceAnalysis]]
    ) -> Dict[str, Any]:
        """Generate sections without LLM"""
        
        western_count = len(source_clusters.get(SourceOrigin.WESTERN, []))
        hostile_count = len(source_clusters.get(SourceOrigin.HOSTILE, []))
        
        return {
            "summary": f"Investigation de {target} ({profile.target_type.value}). "
                      f"Données collectées depuis {western_count + hostile_count} sources.",
            "western": f"{western_count} sources occidentales analysées." 
                      if western_count else "Pas de données occidentales.",
            "hostile": f"{hostile_count} sources potentiellement hostiles détectées."
                      if hostile_count else "Pas de données hostiles.",
            "local": "Analyse locale non disponible sans données terrain.",
            "risk": "Évaluation des risques en attente d'analyse approfondie.",
            "recommendations": [
                "Approfondir l'investigation avec des sources primaires",
                "Croiser les informations entre blocs géographiques",
                "Surveiller l'évolution dans le temps"
            ]
        }
    
    def _build_context(
        self,
        target: str,
        profile: TargetProfile,
        graph_data: Dict[str, Any],
        source_clusters: Dict[SourceOrigin, List[SourceAnalysis]]
    ) -> str:
        """Build context string for LLM"""
        lines = []
        
        # Relations found
        relations = graph_data.get("relations", [])[:20]
        if relations:
            lines.append("RELATIONS DÉCOUVERTES:")
            for r in relations:
                lines.append(f"- {r['entity']} --[{r['relation']}]--> {r['connected']}")
        
        # Known risks from profile
        if profile.known_risk_flags:
            lines.append("\nRISQUES CONNUS:")
            for flag in profile.known_risk_flags[:5]:
                lines.append(f"- {flag}")
        
        # Source examples by origin
        for origin in [SourceOrigin.WESTERN, SourceOrigin.HOSTILE]:
            sources = source_clusters.get(origin, [])[:3]
            if sources:
                lines.append(f"\nEXEMPLES SOURCES {origin.value}:")
                for s in sources:
                    lines.append(f"- {s.domain} (confiance: {s.trust_score:.1f})")
        
        return "\n".join(lines)
    
    def _calculate_confidence(
        self,
        source_clusters: Dict[SourceOrigin, List[SourceAnalysis]]
    ) -> float:
        """Calculate overall report confidence based on source diversity"""
        western = len(source_clusters.get(SourceOrigin.WESTERN, []))
        hostile = len(source_clusters.get(SourceOrigin.HOSTILE, []))
        neutral = len(source_clusters.get(SourceOrigin.NEUTRAL, []))
        total = western + hostile + neutral
        
        if total == 0:
            return 0.1
        
        # More diverse sources = higher confidence
        diversity_score = min(1.0, (western > 0) * 0.3 + (hostile > 0) * 0.2 + (neutral > 0) * 0.2)
        
        # More sources = higher confidence (diminishing returns)
        volume_score = min(0.3, total / 100)
        
        return min(1.0, diversity_score + volume_score + 0.2)
    
    def export_to_markdown(self, report: GeoSourcedReport) -> str:
        """Export report to Markdown format"""
        md = f"""# {report.title}

**Type de cible**: {report.target_type}  
**Généré le**: {report.generated_at.strftime('%Y-%m-%d %H:%M')}  
**Score de confiance**: {report.confidence_score:.0%}

---

## Synthèse Exécutive

{report.executive_summary}

---

## Analyse par Origine des Sources

### 🇺🇸🇪🇺 Perspective Occidentale

{report.western_perspective}

### 🇷🇺🇨🇳 Perspective Adversaire

{report.hostile_perspective}

### 🏠 Informations Locales

{report.local_perspective}

---

## Évaluation des Risques

{report.risk_assessment}

---

## Recommandations

"""
        for i, rec in enumerate(report.recommendations, 1):
            md += f"{i}. {rec}\n"
        
        md += f"""
---

## Répartition des Sources

| Origine | Nombre |
|---------|--------|
"""
        for origin, count in report.source_breakdown.items():
            md += f"| {origin} | {count} |\n"
        
        if report.alerts:
            md += "\n---\n\n## Alertes\n\n"
            for alert in report.alerts:
                level = alert.get("risk_level", "UNKNOWN")
                emoji = "🔴" if level == "HIGH" else "🟡" if level == "MEDIUM" else "🟢"
                md += f"- {emoji} **{alert.get('alert_type', 'Alert')}**: {alert.get('message', '')}\n"
        
        md += "\n---\n\n*Rapport généré par VIDOCQ - Intelligence Autonome*"
        
        return md
