"""
VIDOCQ BRAIN - The Universal Radar
Intelligent Core for Autonomous Investigation

Components:
- core_logic.py: Target classification, memory, prediction
- source_analyst.py: Geographic origin classification
- reporter.py: Geo-sourced intelligence reports
- negative_space.py: Ghost detection (suspicious absences)
- contradiction_detector.py: Narrative warfare detection
- wargaming.py: Catastrophe simulation
"""

from src.brain.core_logic import (
    VidocqBrain,
    TargetType,
    TargetProfile,
    RiskLevel,
    PredictiveAlert
)

from src.brain.source_analyst import (
    SourceIntelligence,
    SourceOrigin,
    SourceAnalysis
)

from src.brain.reporter import (
    GeoSourcedReporter,
    GeoSourcedReport
)

from src.brain.negative_space import (
    NegativeSpaceAnalyzer,
    NegativeSpaceReport,
    VoidAnomaly,
    SuspicionLevel
)

from src.brain.contradiction_detector import (
    ContradictionDetector,
    ContradictionReport,
    NarrativeConflict,
    NarrativeStance
)

from src.brain.wargaming import (
    SupplyChainWargamer,
    WargameScenario,
    ScenarioType,
    ImpactLevel,
    AffectedEntity
)

__all__ = [
    # Core Logic
    "VidocqBrain",
    "TargetType",
    "TargetProfile",
    "RiskLevel",
    "PredictiveAlert",
    
    # Source Intelligence
    "SourceIntelligence",
    "SourceOrigin",
    "SourceAnalysis",
    
    # Reporter
    "GeoSourcedReporter",
    "GeoSourcedReport",
    
    # Negative Space (Ghost Detector)
    "NegativeSpaceAnalyzer",
    "NegativeSpaceReport",
    "VoidAnomaly",
    "SuspicionLevel",
    
    # Contradiction Detector (Narrative Warfare)
    "ContradictionDetector",
    "ContradictionReport",
    "NarrativeConflict",
    "NarrativeStance",
    
    # Wargaming (Catastrophe Simulation)
    "SupplyChainWargamer",
    "WargameScenario",
    "ScenarioType",
    "ImpactLevel",
    "AffectedEntity"
]

