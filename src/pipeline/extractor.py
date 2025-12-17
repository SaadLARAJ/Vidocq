import os
import json
from typing import List, Dict, Any, Optional
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
    
    v4.0: Now supports parent_context for focused extraction.
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

    def extract(
        self, 
        text: str, 
        source_domain: str, 
        source_url: str = "",
        parent_context: Optional[str] = None
    ) -> Dict[str, List[Any]]:
        """
        Extract entities and claims from text using Gemini.
        
        Args:
            text: The document text to extract from.
            source_domain: The domain of the source for credibility scoring.
            source_url: The URL of the original document for traceability.
            parent_context: The original investigation target (e.g., "RBE2 Radar").
                           This focuses the LLM on relevant entities.
        """
        logger.info("extracting_knowledge", model=self.model_name, text_len=len(text), context=parent_context)
        
        if not self.api_key:
             # Fallback to simulation if no key provided (or raise error)
             logger.warning("No API key. Using simulation mode.")
             return self._simulate_inference(text, source_domain)

        try:
            # Construct prompt with parent context
            system_instruction = ExtractionPrompts.SYSTEM_PROMPT
            user_prompt = ExtractionPrompts.get_extraction_prompt(text, parent_context=parent_context)
            
            # Gemini call with LOW temperature for factual extraction
            # max_output_tokens prevents runaway 7000-line JSON responses
            response = self.model.generate_content(
                f"{system_instruction}\n\n{user_prompt}",
                generation_config={
                    "temperature": 0.1, 
                    "top_p": 0.9,
                    "max_output_tokens": 4096  # ~3000 words max, forces concise output
                }
            )
            
            # Nettoyage de la réponse brute de Gemini
            raw_text = response.text.strip()
            
            # Si Gemini a mis des balises Markdown ```json ... ```, on les enlève
            # Clean raw text
            text = response.text.strip()
            
            # Markdown code block cleanup
            if "```" in text:
                try:
                    text = text.split("```json")[1].split("```")[0].strip()
                except IndexError:
                    try:
                        text = text.split("```")[1].strip()
                    except IndexError:
                        pass # Keep original text if split fails

            # Remove invalid escape sequences that confuse json.loads
            # e.g. "C:\Path" -> "C:\\Path" or worse "\s" -> "\\s"
            # This is a brute force fix for common LLM path/regex hallucinations
            text = text.replace("\\s", "\\\\s").replace("\\_", "\\\\_")
                
            # Attempt parsing
            try:
                extracted_data = json.loads(text)
            except json.JSONDecodeError:
                # Fallback 1: Dirty Regex extraction (Non-greedy)
                import re
                try:
                    # Look for { ... } structure
                    # Python re does not support recursion (?R), so we use a simple greedy match 
                    # from first { to last }
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        json_cand = match.group(0)
                        # Attempt to fix common errors like trailing commas
                        json_cand = re.sub(r',\s*}', '}', json_cand)
                        json_cand = re.sub(r',\s*]', ']', json_cand)
                        extracted_data = json.loads(json_cand)
                    else:
                        raise ValueError("No JSON object found via regex")
                except Exception as e:
                    logger.error("extraction_json_hard_fail", error=str(e), raw_preview=text[:200])
                    # Return empty structure instead of crashing
                    extracted_data = {"entities": [], "claims": []}
            
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
                
                # VALIDATION: Blacklist Filter
                IGNORE_TERMS = [
                    # Navigation Web
                    "portal", "login", "signup", "contact us", "privacy policy", "terms of use",
                    "sitemap", "search", "menu", "skip to content", "advertisement",
                    # Wiki-ismes
                    "see also", "edit", "history", "external links", "references", 
                    "bibliography", "citation needed", "stub", "category:",
                    # Concepts génériques
                    "new factory", "the company", "a supplier", "strategic partner",
                    "annual report", "pdf document", "press release", "image", "chart", 
                    "asic team", "document", "pdf", "jpg", "png"
                ]

                if len(ename) < 3 or ename.isdigit() or "%" in ename:
                    continue
                
                if any(bad in ename.lower() for bad in IGNORE_TERMS):
                    logger.info("entity_filtered_blacklist", name=ename)
                    continue

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
                    # Specific rules for confidence: use LLM score if available, else calc
                    llm_conf = claim_data.get('confidence')
                    if llm_conf is not None and isinstance(llm_conf, (int, float)):
                        score = float(llm_conf)
                    else:
                        score = ConfidenceCalculator.compute(
                            source_domain=source_domain,
                            method=self.model_name,
                            corroboration_count=1
                        )
                    
                    claim = Claim(
                        source_id=claim_data.get("source_id", "00000000-0000-0000-0000-000000000000"),
                        source_url=source_url or source_domain,  # Use actual URL for traceability
                        subject_id=subj_id,
                        relation_type=claim_data.get('relation', 'RELATED_TO'),
                        object_id=obj_id,
                        confidence_score=score,
                        evidence_snippet=claim_data.get('evidence', ''),
                        context=claim_data.get('context'),
                        date=claim_data.get('date'),
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
