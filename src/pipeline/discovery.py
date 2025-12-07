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
        self.max_depth = 2  # Strict limit for demo/prototype
        self.max_results = 2 # Keep it focused
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def generate_multilingual_queries(self, entity_name: str) -> List[str]:
        """
        Uses LLM to detect entity origin and generate localized search queries.
        """
        try:
            prompt = f"""
            You are an expert OSINT investigator. 
            For the entity '{entity_name}', generate 3 highly specific Google search queries to find its suppliers and supply chain documents.
            
            RULES:
            1. Detect the probable nationality of the entity.
            2. If the entity is Chinese, write queries in Simplified Chinese (e.g., '... 供应商名单').
            3. If the entity is Russian, write queries in Russian (e.g., '... поставщики').
            4. If the entity is French, write queries in French.
            5. Otherwise, use English.
            6. Target "Conflict Minerals Reports", "Supplier Lists", and "Tenders".
            
            OUTPUT FORMAT:
            Return ONLY a raw JSON list of strings. No markdown, no code blocks.
            Example: ["query1", "query2", "query3"]
            """
            
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up potential markdown formatting
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            queries = json.loads(text)
            
            # Log the detection (inferring from the first query characters or just generic log)
            logger.info("generated_multilingual_queries", entity=entity_name, queries=queries)
            return queries

        except Exception as e:
            logger.error("llm_query_generation_failed", error=str(e))
            # Fallback to English
            return [
                f"{entity_name} supplier list filetype:pdf",
                f"{entity_name} conflict minerals report",
                f"{entity_name} tier 2 suppliers"
            ]

    def discover_and_loop(self, entity_name: str, current_depth: int = 0):
        """
        Main entry point for recursive discovery.
        """
        if current_depth >= self.max_depth:
            logger.info("max_depth_reached", entity=entity_name, depth=current_depth)
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
    # Manual Test
    engine = DiscoveryEngine()
    # Test with a Russian entity to verify Polyglot behavior
    engine.discover_and_loop("VSMPO-AVISMA", 0)
