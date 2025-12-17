"""
Enhanced OSINT Discovery Engine with caching and parallel execution.
"""
import time
import random
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Optional
import google.generativeai as genai
from duckduckgo_search import DDGS
from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class DiscoveryEngineV2:
    """OSINT Discovery Engine with caching and parallel query execution."""

    # Entities to always skip (noise)
    DENY_LIST = {
        "PDF", "Word", "Excel", "Powerpoint", "Microsoft Office", "LibreOffice",
        "Adobe Acrobat Reader", "Notepad++", "Windows", "Keep", "Google Docs",
        "Facebook", "Twitter", "Instagram", "WhatsApp", "YouTube", "LinkedIn",
        "Login", "Subscribe", "Home", "Contact", "About Us", "Privacy Policy",
        "Cookie Policy", "Terms of Service", "N/A", "Unknown", "TBD"
    }
    
    # Noise domains to filter out (shared with V3)
    NOISE_DOMAINS = {
        # Educational Q&A sites (major source of pollution)
        "brainly.com", "brainly.in", "brainly.ph", "brainly.lat",
        "chegg.com", "coursehero.com", "studymode.com", "studocu.com",
        "numerade.com", "bartleby.com", "transtutors.com", "homeworklib.com",
        "toppr.com", "byjus.com", "doubtnut.com", "vedantu.com",
        # E-commerce (not intelligence sources)
        "amazon.com", "amazon.fr", "amazon.de", "amazon.co.uk",
        "ebay.com", "aliexpress.com", "alibaba.com", "wish.com",
        # Login pages and auth
        "login.", "signin.", "signup.", "auth.", "account.",
        "myaccount.microsoft.com", "account.microsoft.com",
        # Wikipedia (too generic)
        "wikipedia.org", "wikidata.org", "wikimedia.org",
        # Generic social/forum noise
        "pinterest.com", "tumblr.com", "blogger.com",
        # File sharing/hosting
        "scribd.com", "slideshare.net", "docsity.com", "docplayer.net",
        # Video/Media platforms (no extractable intelligence)
        "youtube.com", "music.youtube.com", "youtu.be",
        "vimeo.com", "dailymotion.com", "twitch.tv",
        # App stores
        "play.google.com", "apps.apple.com", "microsoft.com/store",
        # School/Education portals
        "monlycee.net", "pronote.net", "ecole-directe.fr",
    }
    
    def _is_noise_url(self, url: str) -> bool:
        """Check if URL is from a noise domain."""
        url_lower = url.lower()
        for domain in self.NOISE_DOMAINS:
            if domain in url_lower:
                return True
        return False

    def __init__(self, use_cache: bool = True, max_workers: int = 3):
        self.max_depth = 3          # Increased for better coverage
        self.max_results = 5        # Per query
        self.max_workers = max_workers
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Initialize cache
        self.cache = None
        if use_cache:
            try:
                from src.storage.cache import get_discovery_cache
                self.cache = get_discovery_cache()
            except Exception as e:
                logger.warning("cache_init_failed", error=str(e))

    def _should_skip(self, entity_name: str) -> bool:
        """Check if entity should be skipped."""
        if not entity_name or len(entity_name) < 3:
            return True
        return entity_name.upper().strip() in self.DENY_LIST

    def _execute_search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Execute a single search with caching.
        Returns list of results with 'href' and 'title' keys.
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get_cached_search(query)
            if cached:
                return cached

        results = []
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                results = [
                    {"href": r.get("href"), "title": r.get("title", ""), "body": r.get("body", "")}
                    for r in raw_results if r.get("href")
                ]
            
            # Cache results
            if self.cache and results:
                self.cache.cache_search_results(query, results)
                
            logger.info("search_executed", query=query[:60], count=len(results))
            
        except Exception as e:
            logger.warning("search_failed", query=query[:60], error=str(e))
        
        return results

    def _execute_parallel_searches(self, queries: List[str]) -> Set[str]:
        """
        Execute multiple searches in parallel.
        Returns set of unique URLs found.
        """
        found_urls = set()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all queries
            future_to_query = {
                executor.submit(self._execute_search_with_delay, q): q 
                for q in queries
            }
            
            # Collect results
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    results = future.result()
                    for r in results:
                        if r.get("href"):
                            found_urls.add(r["href"])
                except Exception as e:
                    logger.warning("parallel_search_error", query=query[:60], error=str(e))
        
        return found_urls

    def _execute_search_with_delay(self, query: str) -> List[Dict]:
        """Execute search with random delay (anti-bot)."""
        time.sleep(random.uniform(1.0, 2.5))
        return self._execute_search(query, self.max_results)

    def generate_investigation_queries(self, entity_name: str) -> List[str]:
        """
        Generate smart investigation queries using LLM.
        Falls back to simple queries if LLM fails.
        """
        try:
            prompt = f"""You are an Expert OSINT Investigator. Generate 5 search queries to investigate: "{entity_name}"

RULES:
1. Detect language/nationality → Use appropriate language for queries
2. Target: suppliers, subsidiaries, scandals, sanctions, ownership
3. Mix: some broad queries + some specific document queries
4. NO site: operators, NO excessive quotation marks
5. Keep queries simple and likely to return results

OUTPUT: Raw JSON array of 5 strings only.
Example: ["query1", "query2", "query3", "query4", "query5"]
"""
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            # Parse
            import re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                queries = json.loads(match.group(0))
                if isinstance(queries, list) and len(queries) > 0:
                    queries = [str(q) for q in queries if isinstance(q, str)]
                    if queries:
                        logger.info("llm_queries_generated", entity=entity_name, count=len(queries))
                        return queries
            
            raise ValueError("Failed to parse LLM response")
            
        except Exception as e:
            logger.warning("llm_query_fallback", entity=entity_name, error=str(e))
            return self._get_fallback_queries(entity_name)

    def _get_fallback_queries(self, entity_name: str) -> List[str]:
        """Simple fallback queries when LLM fails."""
        return [
            entity_name,
            f"{entity_name} company",
            f"{entity_name} suppliers",
            f"{entity_name} subsidiaries",
            f"{entity_name} news"
        ]

    def discover(self, entity_name: str, depth: int = 0) -> Dict:
        """
        Main discovery method.
        
        Args:
            entity_name: Entity to investigate
            depth: Current recursion depth
            
        Returns:
            Dict with discovered URLs and metadata
        """
        # Validation
        if self._should_skip(entity_name):
            logger.info("discovery_skipped", entity=entity_name, reason="deny_list_or_invalid")
            return {"entity": entity_name, "urls": [], "skipped": True}
        
        if depth >= self.max_depth:
            logger.info("max_depth_reached", entity=entity_name, depth=depth)
            return {"entity": entity_name, "urls": [], "max_depth": True}
        
        # Check if entity was recently investigated
        if self.cache:
            history = self.cache.get_entity_history(entity_name)
            if history and history.get("urls"):
                logger.info("entity_cache_hit", entity=entity_name)
                return {"entity": entity_name, "urls": history["urls"], "cached": True}
        
        logger.info("discovery_started", entity=entity_name, depth=depth)
        
        # Generate queries
        queries = self.generate_investigation_queries(entity_name)
        
        # Execute searches in parallel
        found_urls = self._execute_parallel_searches(queries)
        
        # If no results, try fallback queries
        if not found_urls:
            logger.warning("primary_search_empty_trying_fallback", entity=entity_name)
            fallback_queries = self._get_fallback_queries(entity_name)
            found_urls = self._execute_parallel_searches(fallback_queries)
        
        # Filter already-processed URLs
        if self.cache:
            new_urls = self.cache.filter_new_urls(found_urls)
            logger.info("urls_filtered", total=len(found_urls), new=len(new_urls))
        else:
            new_urls = found_urls
        
        # Store entity investigation
        if self.cache and new_urls:
            self.cache.store_entity_investigation(entity_name, {
                "urls": list(new_urls),
                "depth": depth,
                "query_count": len(queries)
            })
        
        logger.info("discovery_complete", entity=entity_name, urls=len(new_urls))
        
        return {
            "entity": entity_name,
            "depth": depth,
            "queries_used": len(queries),
            "urls": list(new_urls),
            "url_count": len(new_urls)
        }

    def discover_and_ingest(self, entity_name: str, depth: int = 0):
        """
        Discover URLs and trigger ingestion tasks.
        This is the main entry point for the Celery worker.
        """
        result = self.discover(entity_name, depth)
        
        if result.get("skipped") or result.get("max_depth") or result.get("cached"):
            return result
        
        urls = result.get("urls", [])
        
        # Trigger ingestion for each URL (with noise filtering)
        from src.ingestion.tasks import ingest_url
        
        ingested_count = 0
        skipped_count = 0
        
        for url in urls:
            # Skip noise domains
            if self._is_noise_url(url):
                logger.info("ingestion_skipped_noise_domain", url=url, entity=entity_name)
                skipped_count += 1
                continue
                
            if self.cache:
                self.cache.mark_url_processed(url, entity_name)
            
            logger.info("triggering_ingestion", url=url, entity=entity_name)
            ingest_url.delay(url, f"discovery_{entity_name}", depth=depth + 1, entity_name=entity_name)
            ingested_count += 1
        
        result["ingested"] = ingested_count
        result["skipped_noise"] = skipped_count
        
        return result


# Backward compatibility wrapper
class DiscoveryEngine(DiscoveryEngineV2):
    """Alias for backward compatibility."""
    
    def discover_and_loop(self, entity_name: str, current_depth: int = 0):
        """Backward compatible method name."""
        return self.discover_and_ingest(entity_name, current_depth)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.discovery_v2 <Entity Name>")
        print("Example: python -m src.pipeline.discovery_v2 'Airbus'")
        sys.exit(1)

    entity = sys.argv[1]
    print(f"🚀 Launching Discovery Hunt for: {entity}")
    
    engine = DiscoveryEngineV2(use_cache=True)
    result = engine.discover(entity, depth=0)
    
    print(f"\n📊 Results:")
    print(f"  URLs found: {result.get('url_count', 0)}")
    print(f"  Queries used: {result.get('queries_used', 0)}")
    if result.get("urls"):
        print(f"\n🔗 Top URLs:")
        for url in list(result["urls"])[:5]:
            print(f"  - {url}")
