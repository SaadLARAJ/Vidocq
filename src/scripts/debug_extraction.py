import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.pipeline.extractor import Extractor
from src.config import settings

def test_extraction():
    print(f"Testing Extraction with Model: {settings.GEMINI_MODEL}")
    
    # Sample text representing the domain
    text = """
    Apple Inc. designs the iPhone in California.
    The device is manufactured by Foxconn, which is located in China.
    Pegatron also assembles units in India.
    Tim Cook is the CEO of Apple.
    Consumer Reports published a review criticizing the battery life.
    """
    
    extractor = Extractor()
    
    print("Sending text to Gemini...")
    try:
        result = extractor.extract(text, source_domain="test.com")
        
        print("\n--- EXTRACTION RESULT ---")
        entities = result.get("entities", [])
        claims = result.get("claims", [])
        
        print(f"Entities Found: {len(entities)}")
        for e in entities:
            print(f" - {e.canonical_name} ({e.entity_type}) [ID: {e.id}]")
            
        print(f"\nClaims Found: {len(claims)}")
        for c in claims:
            print(f" - {c.subject_id} --[{c.relation_type}]--> {c.object_id}")
            print(f"   Evidence: {c.evidence_snippet}")
            
    except Exception as e:
        print(f"Error during extraction: {e}")

if __name__ == "__main__":
    test_extraction()
