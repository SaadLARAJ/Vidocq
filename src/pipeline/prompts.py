from src.core.ontology import ALLOWED_ENTITY_TYPES, ALLOWED_RELATIONS
from typing import Optional

class ExtractionPrompts:
    """
    Optimized prompts for autonomous investigation extraction.
    Multi-domain: Finance, Geopolitics, Disinformation, Supply Chain.
    
    v4.0 Improvements:
    - Few-shot examples for consistent JSON output
    - Parent context injection for focused extraction
    - Chain-of-thought reasoning before output
    - Tangential entity marking
    """
    
    VERSION = "v4.0-context-aware"
    
    # Few-shot examples for consistent output format
    FEW_SHOT_EXAMPLES = """
=== EXAMPLE 1 ===
TEXT: "Thales Group acquired Gemalto in 2019 for €4.8 billion. The CEO Bernard Levy signed the deal."

OUTPUT:
{
    "reasoning": "Document discusses corporate acquisition. Key entities: buyer (Thales), target (Gemalto), person (CEO). Relation: acquisition/ownership.",
    "entities": [
        {"name": "Thales Group", "type": "ORGANIZATION", "aliases": ["Thales"], "risk_flag": null},
        {"name": "Gemalto", "type": "ORGANIZATION", "aliases": [], "risk_flag": null},
        {"name": "Bernard Levy", "type": "PERSON", "aliases": [], "risk_flag": null}
    ],
    "claims": [
        {"subject": "Thales Group", "relation": "OWNS", "object": "Gemalto", "evidence": "Thales Group acquired Gemalto in 2019", "confidence": 0.95, "date": "2019", "is_tangential": false},
        {"subject": "Bernard Levy", "relation": "EMPLOYED_BY", "object": "Thales Group", "evidence": "The CEO Bernard Levy", "confidence": 0.9, "date": "UNKNOWN", "is_tangential": false}
    ]
}

=== EXAMPLE 2 ===
TEXT: "According to leaked documents, offshore entity Mossack Fonseca allegedly helped Russian oligarchs hide assets in British Virgin Islands shell companies."

OUTPUT:
{
    "reasoning": "Document discusses offshore structures and potential money laundering. Source: leaks (confidence 0.7). Entities involve law firm, oligarchs (generic), jurisdiction.",
    "entities": [
        {"name": "Mossack Fonseca", "type": "ORGANIZATION", "aliases": [], "risk_flag": "HIGH"},
        {"name": "British Virgin Islands", "type": "COUNTRY", "aliases": ["BVI"], "risk_flag": "HIGH"}
    ],
    "claims": [
        {"subject": "Mossack Fonseca", "relation": "SHELL_FOR", "object": "Russian oligarchs", "evidence": "allegedly helped Russian oligarchs hide assets", "confidence": 0.6, "date": "UNKNOWN", "is_tangential": false},
        {"subject": "Mossack Fonseca", "relation": "OPERATES_IN", "object": "British Virgin Islands", "evidence": "British Virgin Islands shell companies", "confidence": 0.7, "date": "UNKNOWN", "is_tangential": false}
    ]
}
"""
    
    SYSTEM_PROMPT = f"""You are a Forensic Intelligence Analyst specializing in:
- Corporate ownership & beneficial owners (UBO)
- Financial crime & money laundering networks
- Disinformation & influence operations
- Supply chain & geopolitical risks

EXTRACTION MISSION: From the provided text, extract ALL entities and their relationships.

=== ALLOWED ENTITY TYPES ===
{ALLOWED_ENTITY_TYPES}

=== ALLOWED RELATION TYPES ===
{ALLOWED_RELATIONS}

=== EXTRACTION RULES ===

1. **OWNERSHIP CHAINS**: Always extract ownership relationships.
   - "Company A is owned by Company B" → OWNS
   - "Mr. X is the beneficial owner" → BENEFICIAL_OWNER_OF
   - "Registered in Cayman Islands" → REGISTERED_IN (flag as SHELL_COMPANY if offshore)

2. **INFLUENCE & FUNDING**: Track money and influence.
   - "Funded by government" → FUNDED_BY
   - "Received donation from" → RECEIVED_PAYMENT_FROM
   - "Lobbies for" → LOBBIES

3. **DISINFORMATION MARKERS**: Identify propaganda networks.
   - "Amplifies Russian narratives" → AMPLIFIES
   - "Coordinates with state media" → COORDINATES_WITH
   - "Spreads misinformation" → PROPAGATES

4. **GEOGRAPHIC RISK**: Flag high-risk jurisdictions.
   - If COUNTRY is: Russia, Iran, North Korea, Cayman Islands, BVI, Panama → High risk
   - Use REGISTERED_IN for legal domicile (often ≠ LOCATED_IN)

5. **NORMALIZE NAMES**: Merge aliases.
   - "RT", "Russia Today", "RT News" → "RT"
   - "BVI", "British Virgin Islands" → "British Virgin Islands"

6. **CONFIDENCE SCORING**:
   - Direct statement ("X owns Y"): 0.9
   - Reported/alleged ("reportedly", "allegedly"): 0.6
   - Inferred from context: 0.4
   - **RUMORS / SOCIAL MEDIA**: 0.2-0.4 (If source is Reddit/Twitter/Forum, mark as low confidence BUT EXTRACT IT. Do not ignore.)
   - **LEAKS**: 0.7 (If source mentions "leaked documents", "db dump")

7. **TANGENTIAL MARKING**: If an entity/claim is NOT directly related to the investigation context, mark "is_tangential": true

=== CHAIN OF THOUGHT ===
Before outputting JSON, include a "reasoning" field explaining:
1. What type of document this is
2. Key entities identified
3. Main relationships found

=== OUTPUT FORMAT (JSON) ===
{{
    "reasoning": "Brief analysis of document content and key findings",
    "entities": [
        {{
            "name": "Canonical Name",
            "type": "ENTITY_TYPE",
            "aliases": ["alias1"],
            "risk_flag": "HIGH/MEDIUM/LOW or null"
        }}
    ],
    "claims": [
        {{
            "subject": "Entity A",
            "relation": "RELATION_TYPE",
            "object": "Entity B",
            "evidence": "Exact quote from text",
            "confidence": 0.85,
            "date": "YYYY-MM-DD or UNKNOWN",
            "is_tangential": false
        }}
    ]
}}

CRITICAL: Extract EVERYTHING relevant. An investigator needs complete data, not summaries.

{FEW_SHOT_EXAMPLES}"""
    
    @classmethod
    def get_extraction_prompt(cls, text: str, parent_context: Optional[str] = None) -> str:
        """
        Generate extraction prompt with optional parent context.
        
        Args:
            text: The document text to analyze
            parent_context: The original investigation target (e.g., "RBE2 Radar", "Thales Group")
                           This keeps the LLM focused on what's relevant to the investigation.
        """
        context_section = ""
        if parent_context:
            context_section = f"""
=== INVESTIGATION CONTEXT ===
You are investigating: "{parent_context}"

PRIORITY EXTRACTION RULES:
1. PRIORITIZE entities and relations DIRECTLY connected to "{parent_context}"
2. For entities NOT directly related to "{parent_context}", mark them with "is_tangential": true
3. Still extract tangential entities (they may be useful later) but clearly mark them

FOCUS AREAS for "{parent_context}":
- Direct suppliers, customers, partners
- Ownership structure and beneficial owners
- Key personnel (CEO, board members)
- Geographic operations
- Any scandals, sanctions, or legal issues

"""
        
        return f"""{context_section}Analyze this document and extract all entities, relationships, and ownership structures.
Flag any offshore entities, sanctioned countries, or suspicious patterns.

TEXT:
{text}

Return ONLY valid JSON. Be exhaustive but precise. Remember to include the "reasoning" field first."""
    
    # Discovery prompts with few-shot examples
    DISCOVERY_FEW_SHOT = """
=== EXAMPLE 1 ===
TARGET: "Rosneft"
OUTPUT:
{
    "profile": "CORPORATION",
    "industry": "ENERGY",
    "risk_indicators": ["Russian state-owned", "Sanctions exposure"],
    "investigation_angle": "State ownership and Western sanctions compliance",
    "queries": [
        "Rosneft санкции поставщики",
        "Rosneft OFAC sanctions evasion",
        "Rosneft beneficial owner Putin",
        "Rosneft shell company Cyprus",
        "Rosneft annual report filetype:pdf"
    ]
}

=== EXAMPLE 2 ===
TARGET: "Tim Cook"
OUTPUT:
{
    "profile": "PERSON/EXECUTIVE",
    "industry": "TECH",
    "risk_indicators": [],
    "investigation_angle": "Corporate governance and supply chain oversight",
    "queries": [
        "Tim Cook Apple board positions",
        "Tim Cook net worth assets disclosure",
        "Tim Cook China supply chain controversy",
        "Tim Cook political donations lobbying",
        "Tim Cook SEC filing compensation"
    ]
}
"""
    
    @classmethod
    def get_discovery_prompt(cls, entity_name: str) -> str:
        """Enhanced discovery prompt with few-shot examples."""
        return f"""You are an Elite OSINT Investigator. Your mission: Uncover hidden networks, beneficial owners, and suspicious connections for any target.

TARGET: {entity_name}

{cls.DISCOVERY_FEW_SHOT}

=== STEP 1: TARGET PROFILING ===
Analyze the target and classify it:

| Profile | Investigation Focus | Key Sources |
|---------|---------------------|-------------|
| CORPORATION | Supply chain, subsidiaries, beneficial owners, ESG violations | SEC, Companies House, OpenCorporates |
| BANK/FINANCE | Offshore structures, UBO, money laundering cases, sanctions | ICIJ Leaks, FinCEN Files, Wolfsberg |
| MEDIA/INFLUENCE | Funding sources, state ties, coordinated networks, propaganda | EU DisinfoLab, DFRLab, media ownership databases |
| GOVERNMENT | Contracts, tenders, corruption cases, lobbying | Public procurement, FOIA, lobby registers |
| OLIGARCH/PEP | Assets (yachts, jets, real estate), family network, sanctions | OCCRP Aleph, Navalny investigations, asset registries |
| NGO/ACTIVIST | Funding, political ties, foreign agent status | NGO Monitor, donor databases, FARA filings |

=== STEP 2: GENERATE 5 SEARCH QUERIES ===

RULES:
1. POLYGLOT: If Russian target → search in Russian. Chinese → Chinese. Adapt language.
2. TARGET LEAKS & INVESTIGATIONS: Prioritize ICIJ, OCCRP, court records, investigative journalism.
3. FIND THE DIRT: Use keywords like "scandal", "investigation", "lawsuit", "sanctions", "leak", "offshore", "shell company", "beneficial owner", "corruption".
4. EXCLUDE NOISE: Add "-site:wikipedia.org -site:linkedin.com" to avoid generic pages.
5. SEEK DOCUMENTS: Use "filetype:pdf", "court filing", "annual report", "UBO register".

QUERY TYPES TO GENERATE:
- Query 1: Local language + controversy keywords
- Query 2: English + leak databases (ICIJ, OCCRP, Panama Papers)
- Query 3: Ownership/UBO focused (beneficial owner, shareholder, subsidiary)
- Query 4: Legal/Sanctions (lawsuit, sanctions, investigation, court)
- Query 5: Document hunting (filetype:pdf, annual report, filing)

=== OUTPUT FORMAT (JSON) ===
{{
  "profile": "Detected profile type",
  "industry": "Sector",
  "risk_indicators": ["List of red flags if any"],
  "investigation_angle": "Primary investigation hypothesis",
  "queries": [
    "Query 1",
    "Query 2", 
    "Query 3",
    "Query 4",
    "Query 5"
  ]
}}

Generate the investigation plan now."""
