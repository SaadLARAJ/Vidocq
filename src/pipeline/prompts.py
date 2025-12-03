from src.core.ontology import ALLOWED_ENTITY_TYPES, ALLOWED_RELATIONS

class ExtractionPrompts:
    """Centralized repository for versioned LLM prompts."""
    
    VERSION = "v1.2"
    
    SYSTEM_PROMPT = f"""
    You are an expert Intelligence Analyst for a defense agency.
    Your task is to extract structured knowledge from the provided text.
    
    STRICT RULES:
    1. Extract ONLY entities of types: {ALLOWED_ENTITY_TYPES}
    2. Extract ONLY relations of types: {ALLOWED_RELATIONS}
    3. Output must be valid JSON.
    4. For every claim, provide an exact 'evidence_snippet' from the text.
    5. If a relation is implied but not explicit, do NOT extract it.
    
    JSON STRUCTURE:
    {{
        "entities": [
            {{
                "name": "Canonical Name",
                "type": "ENTITY_TYPE",
                "aliases": ["alias1", "alias2"]
            }}
        ],
        "claims": [
            {{
                "subject": "Entity Name",
                "relation": "RELATION_TYPE",
                "object": "Entity Name",
                "evidence": "Exact text snippet"
            }}
        ]
    }}
    """
    
    @classmethod
    def get_extraction_prompt(cls, text: str) -> str:
        return f"""
        Analyze the following text and extract entities and relations according to the system rules.
        
        TEXT:
        {text}
        """
