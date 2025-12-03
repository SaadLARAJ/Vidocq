from typing import List, Dict, Any
from src.core.logging import get_logger
from src.core.models import Claim, EntityNode
from src.pipeline.prompts import ExtractionPrompts
from src.core.scoring import ConfidenceCalculator

logger = get_logger(__name__)

class Extractor:
    """
    Hybrid extraction engine.
    For Phase 2, we implement the structure. 
    In a real scenario, this would call OpenAI/Anthropic APIs.
    """
    
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.prompt_version = ExtractionPrompts.VERSION

    def extract(self, text: str, source_domain: str) -> Dict[str, List[Any]]:
        """
        Extract entities and claims from text.
        """
        logger.info("extracting_knowledge", model=self.model_name, text_len=len(text))
        
        # TODO: Integrate OpenAI/Anthropic client here
        # Currently using simulation for dev environment
        extracted_data = self._simulate_inference(text)
        
        entities = []
        claims = []
        
        # Process Entities
        for ent_data in extracted_data.get("entities", []):
            entity = EntityNode(
                id=f"{ent_data['name']}:{ent_data['type']}", # Simple ID gen for now
                canonical_name=ent_data['name'],
                entity_type=ent_data['type'],
                aliases=ent_data.get("aliases", [])
            )
            entities.append(entity)
            
        # Process Claims
        for claim_data in extracted_data.get("claims", []):
            # Calculate confidence
            score = ConfidenceCalculator.compute(
                source_domain=source_domain,
                method=self.model_name,
                corroboration_count=1
            )
            
            claim = Claim(
                source_id=claim_data.get("source_id", "00000000-0000-0000-0000-000000000000"), # Placeholder
                source_url="http://placeholder.url", # Placeholder
                subject_id=claim_data['subject'],
                relation_type=claim_data['relation'],
                object_id=claim_data['object'],
                confidence_score=score,
                evidence_snippet=claim_data['evidence'],
                extraction_model=self.model_name,
                prompt_version=self.prompt_version
            )
            claims.append(claim)
            
        return {"entities": entities, "claims": claims}

    def _simulate_inference(self, text: str) -> Dict[str, Any]:
        """
        Simulate LLM output for local development/testing.
        Returns deterministic results for known entities to verify pipeline integrity.
        """
        # Dev heuristic: if text contains known entities, extract them
        if "Jean Dupont" in text:
            return {
                "entities": [
                    {"name": "Jean Dupont", "type": "PERSON", "aliases": ["J. Dupont"]}
                ],
                "claims": []
            }
        return {"entities": [], "claims": []}
