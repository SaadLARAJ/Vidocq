import os
import json
from typing import List, Dict, Any
import google.generativeai as genai
from src.core.logging import get_logger
from src.core.models import Claim, EntityNode
from src.pipeline.prompts import ExtractionPrompts
from src.core.scoring import ConfidenceCalculator

logger = get_logger(__name__)

from src.config import settings

class Extractor:
    """
    Hybrid extraction engine using Google Gemini.
    """
    
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = settings.GEMINI_MODEL or model_name
        self.api_key = settings.GEMINI_API_KEY
        self.prompt_version = ExtractionPrompts.VERSION
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            logger.warning("GEMINI_API_KEY not found. Extraction will fail unless in simulation mode.")

    def extract(self, text: str, source_domain: str) -> Dict[str, List[Any]]:
        """
        Extract entities and claims from text using Gemini.
        """
        logger.info("extracting_knowledge", model=self.model_name, text_len=len(text))
        
        if not self.api_key:
             # Fallback to simulation if no key provided (or raise error)
             logger.warning("No API key. Using simulation mode.")
             return self._simulate_inference(text, source_domain)

        try:
            # Construct prompt
            system_instruction = ExtractionPrompts.SYSTEM_PROMPT
            user_prompt = ExtractionPrompts.get_extraction_prompt(text)
            
            # Gemini call
            # We use generation_config to enforce JSON response if possible, 
            # or just prompt engineering. Gemini 1.5 supports response_mime_type="application/json"
            response = self.model.generate_content(
                f"{system_instruction}\n\n{user_prompt}"
            )
            
            # Nettoyage de la réponse brute de Gemini
            raw_text = response.text.strip()
            
            # Si Gemini a mis des balises Markdown ```json ... ```, on les enlève
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "")
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "")
                
            # Maintenant on peut charger le JSON propre
            extracted_data = json.loads(raw_text)
            
            entities = []
            claims = []
            
            # Lookup map for linking claims
            name_to_id = {}
            
            # Process Entities
            for ent_data in extracted_data.get("entities", []):
                # Robustness: key "type" might be missing if LLM hallucinates
                etype = ent_data.get('type', 'UNKNOWN')
                ename = ent_data.get('name', 'Unknown')
                
                eid = f"{ename}:{etype}"
                name_to_id[ename] = eid
                
                entity = EntityNode(
                    id=eid, 
                    canonical_name=ename,
                    entity_type=etype,
                    aliases=ent_data.get("aliases", [])
                )
                entities.append(entity)
                
            # Process Claims
            for claim_data in extracted_data.get("claims", []):
                subj_name = claim_data.get('subject')
                obj_name = claim_data.get('object')
                
                # Resolve IDs
                subj_id = name_to_id.get(subj_name)
                obj_id = name_to_id.get(obj_name)
                
                # Only keep claim if both endpoints are known entities
                if subj_id and obj_id:
                    # Calculate confidence
                    score = ConfidenceCalculator.compute(
                        source_domain=source_domain,
                        method=self.model_name,
                        corroboration_count=1
                    )
                    
                    claim = Claim(
                        source_id=claim_data.get("source_id", "00000000-0000-0000-0000-000000000000"), # Placeholder
                        source_url="http://placeholder.url", # Placeholder
                        subject_id=subj_id,
                        relation_type=claim_data.get('relation', 'RELATED_TO'),
                        object_id=obj_id,
                        confidence_score=score,
                        evidence_snippet=claim_data.get('evidence', ''),
                        extraction_model=self.model_name,
                        prompt_version=self.prompt_version
                    )
                    claims.append(claim)
                else:
                    logger.warning("claim_skipped_missing_entity", subject=subj_name, object=obj_name)
                
            return {"entities": entities, "claims": claims}

        except Exception as e:
            logger.error("extraction_failed", error=str(e))
            return {"entities": [], "claims": []}

    def _simulate_inference(self, text: str, source_domain: str = "") -> Dict[str, Any]:
        """
        Legacy simulation for testing without API keys.
        """
        entities = []
        claims = []
        
        if "Jean Dupont" in text:
            ent = EntityNode(
                id="Jean Dupont:PERSON",
                canonical_name="Jean Dupont",
                entity_type="PERSON",
                aliases=["J. Dupont"]
            )
            entities.append(ent)
            
        return {"entities": entities, "claims": claims}
