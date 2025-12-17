"""
VIDOCQ - Executive Intelligence Brief Generator
Auto-generate Palantir-style intelligence reports.

"From raw data to boardroom-ready intelligence."

Generates:
1. Executive Summary (1 page)
2. Key Findings with confidence levels
3. Risk Matrix
4. Network Visualization Data
5. Actionable Recommendations
6. Appendix with sources
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum

from src.core.logging import get_logger

logger = get_logger(__name__)


class ReportFormat(str, Enum):
    EXECUTIVE_BRIEF = "EXECUTIVE_BRIEF"  # 1-2 pages for C-suite
    DETAILED_ANALYSIS = "DETAILED_ANALYSIS"  # Full report
    RISK_ASSESSMENT = "RISK_ASSESSMENT"  # Focus on risks
    DUE_DILIGENCE = "DUE_DILIGENCE"  # M&A style
    COMPLIANCE = "COMPLIANCE"  # Regulatory focus


class IntelligenceBrief(BaseModel):
    """Auto-generated intelligence report"""
    
    # Header
    title: str
    classification: str = "INTERNAL USE ONLY"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    format: ReportFormat = ReportFormat.EXECUTIVE_BRIEF
    
    # Target
    target: str
    target_type: str = ""
    
    # Executive Summary
    executive_summary: str = ""
    key_finding: str = ""  # Single most important finding
    
    # Confidence Assessment
    overall_confidence: float = 0.0
    data_quality: str = "MEDIUM"
    source_count: int = 0
    
    # Key Findings (max 5)
    key_findings: List[Dict[str, Any]] = []
    
    # Risk Matrix
    risk_matrix: Dict[str, Any] = {}
    
    # Network Summary
    network_summary: Dict[str, Any] = {}
    
    # Recommendations
    recommendations: List[str] = []
    immediate_actions: List[str] = []
    
    # Sources
    primary_sources: List[str] = []
    source_breakdown: Dict[str, int] = {}
    
    # Metadata
    analysis_time_seconds: float = 0.0
    modules_used: List[str] = []
    
    # Markdown Report
    markdown_report: str = ""


class BriefGenerator:
    """
    Generates executive intelligence briefs from pipeline results.
    
    Transforms raw investigation data into Palantir-style reports.
    """
    
    CLASSIFICATION_LABELS = {
        "COMPANY": "Corporate Entity",
        "PERSON": "Individual",
        "STATE": "State Actor",
        "ORGANIZATION": "Organization"
    }
    
    def generate(
        self,
        target: str,
        investigation_result: Dict[str, Any],
        format: ReportFormat = ReportFormat.EXECUTIVE_BRIEF
    ) -> IntelligenceBrief:
        """
        Generate an intelligence brief from investigation results.
        """
        brief = IntelligenceBrief(
            title=f"Intelligence Brief: {target}",
            target=target,
            format=format
        )
        
        try:
            # Extract classification
            classification = investigation_result.get("classification", {})
            brief.target_type = self.CLASSIFICATION_LABELS.get(
                classification.get("type", "UNKNOWN"),
                "Unknown Entity"
            )
            
            # Extract metrics
            scoring = investigation_result.get("scoring", {})
            brief.overall_confidence = scoring.get("confirmed", 0) / max(scoring.get("total_claims", 1), 1)
            brief.source_count = investigation_result.get("discovery", {}).get("urls_discovered", 0)
            
            # Determine data quality
            brief.data_quality = self._assess_data_quality(investigation_result)
            
            # Generate key finding
            brief.key_finding = self._generate_key_finding(investigation_result)
            
            # Generate executive summary
            brief.executive_summary = self._generate_executive_summary(target, investigation_result)
            
            # Extract key findings
            brief.key_findings = self._extract_key_findings(investigation_result)
            
            # Build risk matrix
            brief.risk_matrix = self._build_risk_matrix(investigation_result)
            
            # Network summary
            brief.network_summary = self._build_network_summary(investigation_result)
            
            # Recommendations
            brief.recommendations = investigation_result.get("recommendations", [])
            brief.immediate_actions = self._generate_immediate_actions(investigation_result)
            
            # Sources
            brief.source_breakdown = {
                "confirmed": scoring.get("confirmed", 0),
                "unverified": scoring.get("unverified", 0),
                "contested": scoring.get("contested", 0)
            }
            
            # Modules used
            brief.modules_used = self._get_modules_used(investigation_result)
            
            # Generate markdown
            brief.markdown_report = self._generate_markdown(brief)
            
            logger.info("brief_generated", target=target, format=format.value)
            
        except Exception as e:
            logger.error("brief_generation_failed", error=str(e))
            brief.executive_summary = f"Brief generation failed: {str(e)}"
        
        return brief
    
    def _assess_data_quality(self, result: Dict) -> str:
        """Assess overall data quality."""
        scoring = result.get("scoring", {})
        total = scoring.get("total_claims", 0)
        confirmed = scoring.get("confirmed", 0)
        
        if total == 0:
            return "INSUFFICIENT"
        
        ratio = confirmed / total
        
        if ratio > 0.5:
            return "HIGH"
        elif ratio > 0.2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_key_finding(self, result: Dict) -> str:
        """Generate the single most important finding."""
        # Check for narrative wars first
        contradiction = result.get("contradiction", {})
        if contradiction.get("narrative_wars", 0) > 0:
            return f"⚠️ NARRATIVE CONFLICT DETECTED: Contradictory information from different source blocs"
        
        # Check for high-risk entities
        ontology = result.get("ontology", {})
        high_risk = ontology.get("high_risk_entities", [])
        if high_risk:
            return f"🔴 HIGH-RISK ENTITIES: {len(high_risk)} entities flagged for enhanced scrutiny"
        
        # Check for critical gaps
        discovery = result.get("discovery", {})
        gaps = discovery.get("critical_gaps", [])
        if gaps:
            return f"📋 INFORMATION GAPS: Missing critical data on {', '.join(gaps[:2])}"
        
        # Default
        scoring = result.get("scoring", {})
        confirmed = scoring.get("confirmed", 0)
        return f"✅ {confirmed} verified claims extracted from {result.get('discovery', {}).get('urls_discovered', 0)} sources"
    
    def _generate_executive_summary(self, target: str, result: Dict) -> str:
        """Generate executive summary paragraph."""
        classification = result.get("classification", {})
        scoring = result.get("scoring", {})
        discovery = result.get("discovery", {})
        bayesian = result.get("bayesian_fusion", {})
        
        parts = [
            f"This brief presents intelligence on **{target}**, ",
            f"classified as a **{classification.get('type', 'entity')}** ",
            f"({classification.get('sector', 'sector unknown')}). "
        ]
        
        parts.append(
            f"Analysis covered **{discovery.get('urls_discovered', 0)} sources** "
            f"across **{len(result.get('extraction', {}).get('languages_detected', []))} languages**. "
        )
        
        parts.append(
            f"Extraction yielded **{scoring.get('total_claims', 0)} claims**, "
            f"of which **{scoring.get('confirmed', 0)}** are verified. "
        )
        
        if bayesian.get("highly_likely", 0) > 0:
            parts.append(
                f"Bayesian fusion identified **{bayesian.get('highly_likely')} high-confidence claims**. "
            )
        
        if scoring.get("contested", 0) > 0:
            parts.append(
                f"⚠️ **{scoring.get('contested')} claims are contested** between conflicting sources. "
            )
        
        return "".join(parts)
    
    def _extract_key_findings(self, result: Dict) -> List[Dict[str, Any]]:
        """Extract top 5 key findings."""
        findings = []
        
        # Finding 1: Entity Classification
        classification = result.get("classification", {})
        if classification:
            findings.append({
                "category": "Classification",
                "finding": f"{classification.get('type', 'Unknown')} in {classification.get('sector', 'unknown sector')}",
                "confidence": classification.get("confidence", 0.5),
                "importance": "HIGH"
            })
        
        # Finding 2: High Risk Entities
        ontology = result.get("ontology", {})
        if ontology.get("high_risk_entities"):
            findings.append({
                "category": "Risk Detection",
                "finding": f"{len(ontology['high_risk_entities'])} high-risk entities in network",
                "entities": ontology["high_risk_entities"][:3],
                "confidence": 0.8,
                "importance": "CRITICAL"
            })
        
        # Finding 3: Narrative Conflicts
        contradiction = result.get("contradiction", {})
        if contradiction.get("narrative_wars", 0) > 0:
            findings.append({
                "category": "Information Warfare",
                "finding": f"{contradiction['narrative_wars']} narrative conflicts detected",
                "topics": contradiction.get("contested_topics", [])[:3],
                "confidence": 0.7,
                "importance": "HIGH"
            })
        
        # Finding 4: Coverage Gaps
        discovery = result.get("discovery", {})
        if discovery.get("critical_gaps"):
            findings.append({
                "category": "Intelligence Gaps",
                "finding": f"Missing information on: {', '.join(discovery['critical_gaps'][:3])}",
                "confidence": 0.9,
                "importance": "MEDIUM"
            })
        
        # Finding 5: Bayesian Summary
        bayesian = result.get("bayesian_fusion", {})
        if bayesian:
            findings.append({
                "category": "Evidence Assessment",
                "finding": f"{bayesian.get('highly_likely', 0)}/{bayesian.get('total_fused', 0)} claims are highly likely true",
                "method": bayesian.get("method", "Bayesian fusion"),
                "confidence": 0.85,
                "importance": "MEDIUM"
            })
        
        return findings[:5]
    
    def _build_risk_matrix(self, result: Dict) -> Dict[str, Any]:
        """Build risk matrix."""
        ontology = result.get("ontology", {})
        contradiction = result.get("contradiction", {})
        
        return {
            "dimensions": {
                "operational": {
                    "level": "MEDIUM",
                    "factors": ["Geographic concentration", "Single-source dependencies"]
                },
                "reputational": {
                    "level": "HIGH" if contradiction.get("narrative_wars", 0) > 0 else "LOW",
                    "factors": ["Media coverage divergence", "Contested narratives"]
                },
                "regulatory": {
                    "level": "MEDIUM",
                    "factors": ["Jurisdiction exposure", "Compliance requirements"]
                },
                "financial": {
                    "level": "MEDIUM" if ontology.get("high_risk_entities") else "LOW",
                    "factors": ["Shell company exposure", "Offshore structures"]
                }
            },
            "overall_level": "HIGH" if (
                contradiction.get("narrative_wars", 0) > 0 or 
                len(ontology.get("high_risk_entities", [])) > 2
            ) else "MEDIUM"
        }
    
    def _build_network_summary(self, result: Dict) -> Dict[str, Any]:
        """Build network summary."""
        extraction = result.get("extraction", {})
        ontology = result.get("ontology", {})
        
        return {
            "total_entities": extraction.get("entities_extracted", 0),
            "entity_types": ontology.get("entity_types", {}),
            "high_risk_count": len(ontology.get("high_risk_entities", [])),
            "connections_mapped": extraction.get("claims_extracted", 0)
        }
    
    def _generate_immediate_actions(self, result: Dict) -> List[str]:
        """Generate immediate action items."""
        actions = []
        
        contradiction = result.get("contradiction", {})
        if contradiction.get("narrative_wars", 0) > 0:
            actions.append("Convene source evaluation meeting within 48 hours")
        
        ontology = result.get("ontology", {})
        if ontology.get("high_risk_entities"):
            actions.append("Initiate enhanced due diligence on flagged entities")
        
        discovery = result.get("discovery", {})
        if discovery.get("critical_gaps"):
            actions.append(f"Task analysts to fill gaps: {', '.join(discovery['critical_gaps'][:2])}")
        
        if not actions:
            actions.append("Continue standard monitoring")
        
        return actions
    
    def _get_modules_used(self, result: Dict) -> List[str]:
        """List modules used in analysis."""
        modules = ["VidocqBrain", "DiscoveryV3", "Extractor"]
        
        if result.get("bayesian_fusion"):
            modules.append("BayesianFusion")
        
        if result.get("contradiction"):
            modules.append("ContradictionDetector")
        
        if result.get("ontology"):
            modules.append("EvolvingOntology")
        
        if result.get("provenance"):
            modules.append("ProvenanceTracker")
        
        return modules
    
    def _generate_markdown(self, brief: IntelligenceBrief) -> str:
        """Generate full markdown report."""
        lines = [
            f"# {brief.title}",
            "",
            f"**Classification:** {brief.classification}",
            f"**Generated:** {brief.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Target Type:** {brief.target_type}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            brief.executive_summary,
            "",
            f"> **KEY FINDING:** {brief.key_finding}",
            "",
            "---",
            "",
            "## Data Quality Assessment",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Overall Confidence | {brief.overall_confidence*100:.0f}% |",
            f"| Data Quality | {brief.data_quality} |",
            f"| Sources Analyzed | {brief.source_count} |",
            "",
            "---",
            "",
            "## Key Findings",
            "",
        ]
        
        for i, finding in enumerate(brief.key_findings, 1):
            importance_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(finding.get("importance"), "⚪")
            lines.append(f"### {i}. {finding.get('category', 'Finding')}")
            lines.append(f"{importance_emoji} **{finding.get('finding', '')}**")
            lines.append(f"*Confidence: {finding.get('confidence', 0)*100:.0f}%*")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            "## Risk Matrix",
            "",
            f"**Overall Risk Level:** {brief.risk_matrix.get('overall_level', 'MEDIUM')}",
            "",
            "| Dimension | Level | Key Factors |",
            "|-----------|-------|-------------|",
        ])
        
        for dim, data in brief.risk_matrix.get("dimensions", {}).items():
            factors = ", ".join(data.get("factors", [])[:2])
            lines.append(f"| {dim.title()} | {data.get('level', 'MEDIUM')} | {factors} |")
        
        lines.extend([
            "",
            "---",
            "",
            "## Immediate Actions Required",
            "",
        ])
        
        for action in brief.immediate_actions:
            lines.append(f"- [ ] {action}")
        
        lines.extend([
            "",
            "---",
            "",
            "## Recommendations",
            "",
        ])
        
        for rec in brief.recommendations:
            lines.append(f"- {rec}")
        
        lines.extend([
            "",
            "---",
            "",
            "## Methodology",
            "",
            f"This report was generated using the **VIDOCQ Unified Pipeline v2.0**.",
            "",
            f"**Modules Used:** {', '.join(brief.modules_used)}",
            "",
            "---",
            "",
            f"*Report ID: {brief.target}-{brief.generated_at.strftime('%Y%m%d%H%M')}*",
        ])
        
        return "\n".join(lines)


# Convenience function
def generate_brief(
    target: str,
    investigation_result: Dict[str, Any],
    format: ReportFormat = ReportFormat.EXECUTIVE_BRIEF
) -> IntelligenceBrief:
    """Generate an executive intelligence brief."""
    generator = BriefGenerator()
    return generator.generate(target, investigation_result, format)
