"""
VIDOCQ - Coverage Analysis Module
Detects information gaps and missing critical data.

"What we DIDN'T find is sometimes more important than what we found."

Features:
1. Track search coverage by strategy
2. Identify critical gaps (e.g., no ownership info found)
3. Generate coverage reports
4. Flag suspicious absences
"""

from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from src.core.logging import get_logger

logger = get_logger(__name__)


class CoverageStatus(str, Enum):
    """Coverage status for each search strategy"""
    COVERED = "COVERED"           # Results found
    PARTIAL = "PARTIAL"           # Some results, but below threshold
    GAP = "GAP"                   # No meaningful results
    CRITICAL_GAP = "CRITICAL_GAP" # No results on critical strategy


class StrategyCoverage(BaseModel):
    """Coverage analysis for a single strategy"""
    strategy: str
    queries_executed: int = 0
    total_results: int = 0
    high_value_results: int = 0  # From trusted sources
    status: CoverageStatus = CoverageStatus.GAP
    languages_searched: List[str] = []
    sample_queries: List[str] = []


class CoverageReport(BaseModel):
    """Full coverage analysis for an entity"""
    entity: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Strategy breakdown
    strategies_analyzed: List[StrategyCoverage] = []
    
    # Summary metrics
    total_strategies: int = 0
    covered_strategies: int = 0
    gap_strategies: int = 0
    critical_gaps: List[str] = []
    
    # Coverage score (0-1)
    coverage_score: float = 0.0
    
    # Recommendations
    recommendations: List[str] = []
    
    # Suspicious patterns
    suspicious_gaps: List[str] = []


class CoverageAnalyzer:
    """
    Analyzes search coverage to detect information gaps.
    
    Identifies:
    - Strategies with no results (potential data gaps)
    - Critical missing information (ownership, sanctions, etc.)
    - Suspicious absences that warrant further investigation
    """
    
    # Critical strategies that should ALWAYS have results for valid entities
    CRITICAL_STRATEGIES = {
        "ownership": "No ownership information found - suspicious for any company",
        "suppliers": "No supply chain data - unusual for manufacturing entities",
        "scandals": "Zero controversy results could indicate limited coverage OR clean record"
    }
    
    # Minimum results to consider a strategy "covered"
    MIN_RESULTS_THRESHOLD = 2
    
    def __init__(self):
        self.results_by_strategy: Dict[str, List[Dict]] = {}
        self.queries_by_strategy: Dict[str, List[str]] = {}
        self.languages_by_strategy: Dict[str, Set[str]] = {}
    
    def record_search(
        self,
        strategy: str,
        query: str,
        language: str,
        results: List[Dict]
    ):
        """Record search results for analysis"""
        if strategy not in self.results_by_strategy:
            self.results_by_strategy[strategy] = []
            self.queries_by_strategy[strategy] = []
            self.languages_by_strategy[strategy] = set()
        
        self.results_by_strategy[strategy].extend(results)
        self.queries_by_strategy[strategy].append(query)
        self.languages_by_strategy[strategy].add(language)
    
    def analyze(self, entity: str) -> CoverageReport:
        """
        Analyze coverage and generate report.
        
        Returns:
            CoverageReport with gaps, recommendations, and suspicious patterns
        """
        report = CoverageReport(entity=entity)
        
        strategies = []
        covered_count = 0
        gap_count = 0
        critical_gaps = []
        suspicious = []
        recommendations = []
        
        # Analyze each strategy
        all_strategies = set(self.results_by_strategy.keys()) | set(self.CRITICAL_STRATEGIES.keys())
        
        for strategy in all_strategies:
            results = self.results_by_strategy.get(strategy, [])
            queries = self.queries_by_strategy.get(strategy, [])
            languages = self.languages_by_strategy.get(strategy, set())
            
            # Count high-value results (from trusted sources)
            high_value = sum(1 for r in results if r.get("score", 0) >= 0.85)
            
            # Determine status
            if len(results) >= self.MIN_RESULTS_THRESHOLD:
                status = CoverageStatus.COVERED
                covered_count += 1
            elif len(results) > 0:
                status = CoverageStatus.PARTIAL
            elif strategy in self.CRITICAL_STRATEGIES:
                status = CoverageStatus.CRITICAL_GAP
                critical_gaps.append(strategy)
                gap_count += 1
                
                # Add to suspicious if it's a critical gap
                suspicious.append(
                    f"CRITICAL: {strategy.upper()} - {self.CRITICAL_STRATEGIES[strategy]}"
                )
            else:
                status = CoverageStatus.GAP
                gap_count += 1
            
            coverage = StrategyCoverage(
                strategy=strategy,
                queries_executed=len(queries),
                total_results=len(results),
                high_value_results=high_value,
                status=status,
                languages_searched=list(languages),
                sample_queries=queries[:3]  # Keep first 3 as samples
            )
            strategies.append(coverage)
        
        # Generate recommendations
        if critical_gaps:
            recommendations.append(
                f"🔴 CRITICAL GAPS: {', '.join(critical_gaps)} - Manual investigation required"
            )
        
        if gap_count > len(all_strategies) / 2:
            recommendations.append(
                "⚠️ More than 50% of strategies returned no results. "
                "Consider: 1) Try alternative entity names 2) Check if entity is obscure 3) Expand language coverage"
            )
        
        # Check for language gaps
        all_languages = set()
        for langs in self.languages_by_strategy.values():
            all_languages.update(langs)
        
        if "en" in all_languages and len(all_languages) == 1:
            recommendations.append(
                "🌐 Only English searches performed. Consider adding local language queries."
            )
        
        # Compute coverage score
        total = len(all_strategies)
        if total > 0:
            coverage_score = covered_count / total
        else:
            coverage_score = 0.0
        
        # Build report
        report.strategies_analyzed = strategies
        report.total_strategies = total
        report.covered_strategies = covered_count
        report.gap_strategies = gap_count
        report.critical_gaps = critical_gaps
        report.coverage_score = coverage_score
        report.recommendations = recommendations
        report.suspicious_gaps = suspicious
        
        logger.info(
            "coverage_analysis_complete",
            entity=entity,
            score=coverage_score,
            gaps=gap_count,
            critical=len(critical_gaps)
        )
        
        return report
    
    def reset(self):
        """Reset for new entity analysis"""
        self.results_by_strategy = {}
        self.queries_by_strategy = {}
        self.languages_by_strategy = {}


def analyze_search_coverage(
    entity: str,
    search_results: Dict[str, List[Dict]],
    queries_executed: Dict[str, List[str]]
) -> CoverageReport:
    """
    Convenience function to analyze search coverage.
    
    Args:
        entity: Entity name being investigated
        search_results: Dict of strategy -> list of results
        queries_executed: Dict of strategy -> list of queries used
        
    Returns:
        CoverageReport with analysis
    """
    analyzer = CoverageAnalyzer()
    
    for strategy, results in search_results.items():
        queries = queries_executed.get(strategy, [])
        # Infer language from query (simple heuristic)
        for i, query in enumerate(queries):
            lang = "en"  # Default
            if any(c in query for c in "абвгдежзи"):
                lang = "ru"
            elif any(c in query for c in "中国的是"):
                lang = "zh"
            elif any(w in query.lower() for w in ["fournisseur", "société", "entreprise"]):
                lang = "fr"
            elif any(w in query.lower() for w in ["lieferant", "unternehmen"]):
                lang = "de"
            
            # Record with subset of results for this query
            result_slice = results[i:i+5] if i < len(results) else []
            analyzer.record_search(strategy, query, lang, result_slice)
    
    return analyzer.analyze(entity)
