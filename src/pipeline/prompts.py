from src.core.ontology import ALLOWED_ENTITY_TYPES, ALLOWED_RELATIONS

class ExtractionPrompts:
    """Centralized repository for versioned LLM prompts."""
    
    VERSION = "v1.3-hybrid"  # Updated version to reflect the new strategy
    
    SYSTEM_PROMPT = f"""
    You are an expert Intelligence Analyst for a defense agency.
    Your task is to extract structured knowledge from the provided text, following these rules with extreme precision.
    
    STRICT RULES:
    1. ENTITY NORMALIZATION (CRITICAL): Merge all aliases to a single, simple Canonical Name.
       - Example: "Apple", "Apple Inc.", "Apple Corp" -> MUST all be "Apple".
       - Example: "Foxconn Technology", "Hon Hai Precision Industry" -> MUST all be "Foxconn".

    2. GEOGRAPHICAL EXTRACTION (MANDATORY): You MUST extract specific locations as `CITY` or `COUNTRY` types. You MUST use relations like `LOCATED_IN`, `OPERATES_IN`, or `MANUFACTURES_IN` to link an `ORGANIZATION` to a `CITY` or `COUNTRY`.

    3. RELATION NUANCE (MANDATORY): Use the most precise relation from the allowed list. If a relationship is reported, rumored, or planned (not confirmed), you MUST use a nuanced verb.
       - Example: If the text says "Apple might source from Y", use `POTENTIALLY_SUPPLIES`, not `SUPPLIES`.
       - Example: For confirmed facts like "Apple's factory is in Zhengzhou", use `MANUFACTURES_IN`.

    4. STRICT TYPING: The 'relation' (for claims) and 'type' (for entities) fields MUST be an exact match from the allowed lists. Do not invent new types.
       - Allowed Entity Types: {ALLOWED_ENTITY_TYPES}
       - Allowed Relation Types: {ALLOWED_RELATIONS}

    5. EVIDENCE (CRITICAL): The 'evidence' field MUST contain the exact, unaltered natural language sentence from the text that proves the relationship.

    6. NO SENTENCES AS NODES: Entity names MUST be concise concepts (max 5 words), not full sentences.
       - BAD: "Since iOS 10.2.1, Apple has instituted a policy..." -> This is not an entity.
       - GOOD: "Performance Management Policy"

    7. DO NOT EXTRACT AUTHORS: Do not extract journalists, reporters, or the author of the text as having a relationship (e.g., `EMPLOYS`) with a company they are writing about.

    8. EXHAUSTIVE EXTRACTION: Extract EVERY valid entity and relation from the text. Do not summarize or skip information that fits the rules.

    9. DEEP REASONING: Connect entities by reasoning across the entire document. If an organization is mentioned in paragraph 1 and its factory location is mentioned in paragraph 10, you must still create the `MANUFACTURES_IN` link.

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
                "evidence": "Exact text snippet from the source document that proves the claim."
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
