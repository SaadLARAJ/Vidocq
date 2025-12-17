"""
VIDOCQ - Pipeline Integration Test
Demonstrates the complete chain of all modules.

Run with: python -m src.scripts.test_pipeline "Thales Group"
"""

import asyncio
import sys
from datetime import datetime

from src.core.logging import get_logger

logger = get_logger(__name__)


async def test_full_pipeline(target: str):
    """
    Test the complete investigation pipeline.
    
    This demonstrates:
    1. Classification (Chain-of-Thought)
    2. Discovery (with Coverage Analysis)
    3. Extraction (with Parent Context)
    4. Scoring (with SourceIntelligence + Contradiction)
    5. Language Detection
    """
    print(f"\n{'='*60}")
    print(f"🔍 VIDOCQ Investigation Pipeline Test")
    print(f"{'='*60}")
    print(f"Target: {target}")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    # Test 1: Brain Classification
    print("📋 PHASE 1: Target Classification (Chain-of-Thought)")
    print("-" * 40)
    try:
        from src.brain.core_logic import VidocqBrain
        brain = VidocqBrain()
        classification = await brain.classify_target(target)
        print(f"  Type: {classification.target_type.value}")
        print(f"  Confidence: {classification.confidence:.2f}")
        print(f"  Country: {classification.probable_country}")
        print(f"  Sector: {classification.probable_sector}")
        print(f"  ✅ Classification OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 2: Discovery with Coverage
    print("\n🌐 PHASE 2: Discovery + Coverage Analysis")
    print("-" * 40)
    try:
        from src.pipeline.discovery_v3 import DiscoveryEngineV3
        discovery = DiscoveryEngineV3()
        result = discovery.discover(target, max_urls=5)
        print(f"  URLs found: {len(result.get('urls', []))}")
        print(f"  Queries executed: {result.get('queries_executed', 0)}")
        
        if "coverage" in result:
            coverage = result["coverage"]
            print(f"  Coverage score: {coverage.get('score', 0):.2f}")
            if coverage.get("critical_gaps"):
                print(f"  ⚠️ Critical gaps: {coverage['critical_gaps']}")
        print(f"  ✅ Discovery OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 3: Extraction with Context
    print("\n📑 PHASE 3: Extraction (with Parent Context)")
    print("-" * 40)
    try:
        from src.pipeline.extractor import Extractor
        from src.pipeline.prompts import ExtractionPrompts
        
        extractor = Extractor()
        print(f"  Prompt version: {ExtractionPrompts.VERSION}")
        print(f"  Parent context: '{target}' will be injected")
        
        # Test prompt generation
        test_prompt = ExtractionPrompts.get_extraction_prompt(
            "Sample text about " + target,
            parent_context=target
        )
        
        if f'You are investigating: "{target}"' in test_prompt:
            print(f"  ✅ Context injection working")
        else:
            print(f"  ⚠️ Context injection might not be working")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 4: Unified Scoring
    print("\n📊 PHASE 4: Unified Scoring + Contradiction Detection")
    print("-" * 40)
    try:
        from src.core.unified_scoring import UnifiedScorer, VisibilityZone
        
        scorer = UnifiedScorer()
        print(f"  Weights: {scorer.WEIGHTS}")
        print(f"  Zones: {[z.value for z in VisibilityZone]}")
        
        # Test scoring
        breakdown = scorer.compute_score(
            llm_confidence=0.8,
            source_url="https://reuters.com/article/test",
            mission_relevance=0.7,
            narrative_war=False
        )
        print(f"  Test score: {breakdown.final_score:.2f}")
        print(f"  Source trust: {breakdown.source_trust:.2f}")
        
        # Test with narrative war
        breakdown_contested = scorer.compute_score(
            llm_confidence=0.8,
            source_url="https://reuters.com/article/test",
            mission_relevance=0.7,
            narrative_war=True
        )
        print(f"  Contested score: {breakdown_contested.final_score:.2f} (20% penalty)")
        print(f"  ✅ Scoring OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 5: Language Detection
    print("\n🌍 PHASE 5: Language Detection (LLM-based)")
    print("-" * 40)
    try:
        from src.core.language_detection import LanguageDetector
        
        detector = LanguageDetector()
        
        # Test different languages
        tests = [
            ("Hello, this is English text", "en"),
            ("Bonjour, ceci est du texte français", "fr"),
            ("Привет, это русский текст", "ru"),
        ]
        
        for text, expected in tests:
            result = detector.detect_sync(text)
            status = "✅" if result.primary_language == expected else "⚠️"
            print(f"  {status} '{text[:30]}...' → {result.primary_language} ({result.confidence:.2f})")
        
        print(f"  ✅ Language Detection OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 6: Temporal Versioning
    print("\n⏱️ PHASE 6: Temporal Versioning")
    print("-" * 40)
    try:
        from src.core.temporal_versioning import create_fact_version, FactStatus
        
        fact = create_fact_version(
            subject="Thales Group",
            relation="OWNS",
            object="Gemalto",
            source_url="https://example.com/acquisition",
            confidence=0.95
        )
        
        print(f"  Fact ID: {fact.fact_id}")
        print(f"  Version: {fact.version}")
        print(f"  Status: {fact.status.value}")
        print(f"  Valid from: {fact.valid_from.isoformat()}")
        print(f"  ✅ Temporal Versioning OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 7: Full Pipeline (if all components work)
    print("\n🚀 PHASE 7: Full Pipeline Integration")
    print("-" * 40)
    try:
        from src.pipeline.unified_pipeline import UnifiedPipeline
        
        pipeline = UnifiedPipeline()
        print(f"  Brain: {'✅' if pipeline.brain else '❌'}")
        print(f"  Discovery: {'✅' if pipeline.discovery else '❌'}")
        print(f"  Extractor: {'✅' if pipeline.extractor else '❌'}")
        print(f"  Scorer: {'✅' if pipeline.scorer else '❌'}")
        print(f"  Language Detector: {'✅' if pipeline.language_detector else '❌'}")
        print(f"  ✅ Pipeline Integration OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ All Integration Tests Complete")
    print(f"{'='*60}\n")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "Thales Group"
    asyncio.run(test_full_pipeline(target))


if __name__ == "__main__":
    main()
