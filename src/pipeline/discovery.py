import time
import random
import json
import google.generativeai as genai
from typing import List, Dict
from duckduckgo_search import DDGS
from src.core.logging import get_logger
from src.ingestion.tasks import ingest_url
from src.config import settings

logger = get_logger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

class DiscoveryEngine:
    """
    Real-world OSINT Discovery Engine.
    Uses DuckDuckGo to hunt for "Shadow Documents" (CMRT, Slavery Statements).
    Now POLYGLOT: Uses Gemini to generate queries in the local language of the entity.
    """

    def __init__(self):
        self.ddgs = DDGS()
        self.max_depth = 2  # Limit depth to avoid Kevin Bacon effect (noise)
        self.max_results = 5 # More results = richer graph
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def generate_multilingual_queries(self, entity_name: str) -> List[str]:
        """
        Uses LLM to profile target and generate investigation-specific search queries.
        Autonomous investigation agent - adapts strategy based on target type.
        """
        try:

            prompt = f"""You are an Elite OSINT Investigator. Your mission: Uncover hidden networks, beneficial owners, and suspicious connections for any target.

TARGET: {entity_name}

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
            
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Robust Parsing Logic
            # 1. Clean Markdown
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            text = text.strip()

            parsed_data = {}
            queries = []
            
            import json
            import ast
            import re

            # 2. Try Standard JSON
            try:
                parsed_data = json.loads(text)
            except:
                # 3. Try Python Eval (for single quotes)
                try:
                    parsed_data = ast.literal_eval(text)
                    logger.info("llm_query_fallback_ast", method="ast.literal_eval")
                except:
                    # 4. Regex Fallback
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        try:
                            parsed_data = ast.literal_eval(match.group(0))
                        except:
                            parsed_data = {}
            
            # Extract queries from the new dict format
            if isinstance(parsed_data, dict):
                queries = parsed_data.get("queries", [])
                profile = parsed_data.get("profile", "Unknown")
                reasoning = parsed_data.get("reasoning", "None")
                logger.info("dynamic_domain_analysis", entity=entity_name, profile=profile, reasoning=reasoning)
            elif isinstance(parsed_data, list):
                # Fallback if LLM ignores instructions and returns just a list
                queries = parsed_data
            
            # 5. Validation
            if not isinstance(queries, list):
                logger.warning("llm_query_invalid_format", received=str(queries)[:100])
                queries = []
            
            # 6. Ensure strings
            queries = [str(q) for q in queries if isinstance(q, str)]

            if not queries:
                raise ValueError("No valid queries generated")
            
            return queries

        except Exception as e:
            logger.error("llm_query_generation_failed", error=str(e))
            # Fallback to English - Broader queries
            return [
                f"{entity_name} major suppliers list",
                f"{entity_name} subsidiaries list",
                f"{entity_name} corruption scandal"
            ]

    def discover_and_loop(self, entity_name: str, current_depth: int = 0):
        """
        Main entry point for recursive discovery.
        """
        if current_depth >= self.max_depth:
            logger.info("max_depth_reached", entity=entity_name, depth=current_depth)
            return

        # FILTER: Ignore generic/noise entities
        DENY_LIST = {
            "PDF", "Word", "Excel", "Powerpoint", "Microsoft Office", "LibreOffice", "Google Docs", 
            "Adobe Acrobat Reader", "Notepad++", "Windows", "Keep",
            "Facebook", "Twitter", "Instagram", "WhatsApp", "YouTube", "LinkedIn", "Viadeo",
            "Copains d'avant", "Journal des femmes", "Journal Du Net", "Linternaute", "CCM Benchmark",
            "Login", "Subscribe", "Home", "Contact", "About Us", "Privacy Policy", "Cookie Policy"
        }
        
        if entity_name in DENY_LIST or len(entity_name) < 3:
             logger.info("discovery_skipped_denylist", entity=entity_name)
             return

        logger.info("starting_discovery_hunt", entity=entity_name, depth=current_depth)

        # 1. Generate Hunter Queries (Polyglot)
        queries = self.generate_multilingual_queries(entity_name)

        found_urls = set()

        # 2. Execute Search
        for query in queries:
            try:
                # Random sleep for OpSec (avoid bot detection)
                time.sleep(random.uniform(2.0, 5.0))
                
                logger.info("executing_search", query=query)
                results = self.ddgs.text(query, max_results=self.max_results)
                
                if results:
                    for res in results:
                        url = res.get('href')
                        if url:
                            found_urls.add(url)
                            
            except Exception as e:
                logger.error("discovery_search_failed", query=query, error=str(e))

        # 3. Recursive Ingestion Trigger
        logger.info("discovery_complete", entity=entity_name, urls_found=len(found_urls))
        
        for url in found_urls:
            # In a real scenario, we would check Redis here to avoid re-ingesting
            # if not redis_client.exists(url): ...
            
            logger.info("triggering_ingestion", url=url, parent_entity=entity_name)
            
            # Trigger the ingestion task with incremented depth
            ingest_url.delay(url, f"discovery_hunt_{entity_name}", depth=current_depth + 1)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/pipeline/discovery.py <Entity Name>")
        print("Example: python src/pipeline/discovery.py 'Airbus'")
        sys.exit(1)

    entity = sys.argv[1]
    print(f"🚀 Launching Discovery Hunt for: {entity}")
    
    engine = DiscoveryEngine()
    engine.discover_and_loop(entity, 0)
