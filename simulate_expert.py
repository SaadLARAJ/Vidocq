
import sys
import os
import json
import asyncio
from typing import Dict, List

# Add src to path
sys.path.append(os.getcwd())

from src.config import settings
from src.pipeline.discovery_v3 import DiscoveryEngineV3

# Windows Unicode Fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def simulate_expert_search(entity: str):
    print(f"\n=======================================================")
    print(f"🚀  EXPERT SIMULATION: {entity.upper()}")
    print(f"=======================================================")
    
    engine = DiscoveryEngineV3(use_cache=False, aggressive=True)
    
    # 1. Detection Contexte
    print(f"\n[1] 🧠 INTELLIGENCE CONTEXTUELLE")
    print("    Analysing entity profile via Gemini...")
    context = engine._detect_entity_context(entity)
    print(f"    Detected Context: {json.dumps(context, indent=2)}")
    
    # 2. Stratégie Multilingue
    print(f"\n[2] 🌍 STRATEGIE LINGUISTIQUE")
    languages = engine._get_languages_for_entity(entity, context)
    print(f"    Target Languages: {languages}")
    
    # 3. Génération Requêtes
    print(f"\n[3] 🔍 GENERATION REQUETES (Mode Large Panel)")
    queries = engine._generate_queries(entity, context)
    
    print(f"    Generated {len(queries)} specialized queries:")
    for i, q in enumerate(queries):
        print(f"    {i+1:02d}. {q}")
        
    # 4. Sources Prioritaires
    print(f"\n[4] 🎯 CIBLAGE SOURCES (Top Tier)")
    industry = context.get('industry', 'OTHER')
    if industry in ['DEFENSE', 'AEROSPACE']:
        print("    - Jane's Defence Weekly")
        print("    - Defense News")
        print("    - SIPRI Arms Transfers")
    if industry in ['FINANCE', 'ENERGY']:
        print("    - Bloomberg Terminal (simulated)")
        print("    - Offshore Leaks Database")
        print("    - MarineTraffic API")
    if industry == "TECH":
        print("    - TechCrunch")
        print("    - GitHub / StackOverflow")
        
    print(f"\n=======================================================")
    print(f"✅  SIMULATION COMPLETE: Ready for Deep Ingestion")
    print(f"=======================================================")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        entity = sys.argv[1]
    else:
        entity = "Thales Group"
    
    simulate_expert_search(entity)
