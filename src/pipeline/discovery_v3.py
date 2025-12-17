"""
Discovery Engine v3 - Advanced Multilingual OSINT Search
Designed to find "needles in haystacks" with:
- Polyglot queries (EN, FR, DE, ZH, RU, AR, ES)
- Multiple search strategies (suppliers, ownership, scandals, leaks)
- Source quality filtering
- Anti-evasion techniques
"""
import time
import random
import json
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Optional, Tuple
import google.generativeai as genai
from duckduckgo_search import DDGS
from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__)

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class DiscoveryEngineV3:
    """
    Advanced OSINT Discovery Engine with:
    - Multilingual search (7 languages)
    - Multiple search strategies
    - Source quality scoring
    - Anti-evasion techniques
    """

    # Noise domains to skip (Pure spam/irrelevant)
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
        # Google generic pages (support, products, not OSINT)
        "support.google.com", "google.com/maps", "maps.google.com",
        "accounts.google.com", "myaccount.google.com",
        # Note: Wikipedia REMOVED - it's a good seed source for entity extraction
        # Generic social/forum noise (allowed in WEAK_SIGNAL for leads)
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
        # Forums and generic Q&A
        "quora.com", "answers.com", "ask.com",
        # Translation sites
        "translate.google.com", "deepl.com",
    }



    # Weak Signal domains (Rumors, Leaks, Opinions - Low confidence but high value for leads)
    WEAK_SIGNAL_DOMAINS = {
        "reddit.com": 0.30, "twitter.com": 0.25, "x.com": 0.25,
        "quora.com": 0.20, "telegram.me": 0.35, "t.me": 0.35,
        "facebook.com": 0.20, "linkedin.com": 0.40,  # Profiles are useful
        "pastebin.com": 0.40, "4chan.org": 0.20,
    }

    # High-value source domains
    HIGH_VALUE_DOMAINS = {
        "reuters.com": 0.95, "bloomberg.com": 0.95, "ft.com": 0.92,
        "wsj.com": 0.92, "nytimes.com": 0.90, "theguardian.com": 0.88,
        "bbc.com": 0.88, "apnews.com": 0.95, "afp.com": 0.93,
        # Corporate
        "sec.gov": 0.98, "companieshouse.gov.uk": 0.95,
        "opencorporates.com": 0.90, "dnb.com": 0.88,
        # Defense/Aerospace
        "janes.com": 0.95, "defensenews.com": 0.90, "flightglobal.com": 0.88,
        "ainonline.com": 0.85, "aviationweek.com": 0.88,
        # Leaks/Investigations
        "icij.org": 0.92, "occrp.org": 0.92, "bellingcat.com": 0.90,
        # French sources
        "lesechos.fr": 0.90, "latribune.fr": 0.85, "usinenouvelle.com": 0.88,
        "societe.com": 0.92, "pappers.fr": 0.90, "infogreffe.fr": 0.95,
        # German sources  
        "handelsblatt.com": 0.90, "bundesanzeiger.de": 0.95,
        # Chinese sources
        "scmp.com": 0.85, "caixin.com": 0.82, "xinhuanet.com": 0.75,
        # Japan / India
        "nikkei.com": 0.90, "japantimes.co.jp": 0.88,
        "economictimes.indiatimes.com": 0.88, "business-standard.com": 0.85,
        # Russia (Intelligence value despite bias)
        "rbc.ru": 0.85, "kommersant.ru": 0.85, "tass.com": 0.70, "themoscowtimes.com": 0.88,
        # Middle East
        "aljazeera.com": 0.85, "arabianbusiness.com": 0.85, "thenationalnews.com": 0.82,
        # Africa
        "jeuneafrique.com": 0.88, "allafrica.com": 0.82, "dailymaverick.co.za": 0.85,
        # LatAm
        "mercopress.com": 0.85, "folha.uol.com.br": 0.85, "infobae.com": 0.82,
        # Maritime / Crypto / Tech (Sector specific)
        "marinetraffic.com": 0.92, "vesselfinder.com": 0.90, "lloydslist.com": 0.95,
        "chainalysis.com": 0.92, "elliptic.co": 0.90, "techcrunch.com": 0.85,
        # General Knowledge
        "wikipedia.org": 0.60,
    }

    # Search strategy templates
    SEARCH_STRATEGIES = {
        "suppliers": {
            "en": ["{entity} suppliers manufacturers components", "{entity} supply chain tier-1 tier-2"],
            "fr": ["{entity} fournisseurs fabricants composants", "{entity} chaîne approvisionnement sous-traitants"],
            "de": ["{entity} Lieferanten Hersteller Komponenten", "{entity} Zulieferer Lieferkette"],
            "zh": ["{entity} 供应商 制造商 零部件", "{entity} 供应链"],
            "ru": ["{entity} поставщики производители", "{entity} цепочка поставок"],
        },
        "ownership": {
            "en": ["{entity} ownership shareholders beneficial owner", "{entity} parent company subsidiary holding"],
            "fr": ["{entity} actionnariat propriétaire bénéficiaire effectif", "{entity} filiale société mère holding"],
            "de": ["{entity} Eigentümer Aktionäre Gesellschafter", "{entity} Tochtergesellschaft Muttergesellschaft"],
            "zh": ["{entity} 股东 所有权 母公司", "{entity} 子公司 控股"],
        },
        "sanctions": {
            "en": ["{entity} sanctions embargo blacklist OFAC", "{entity} export controls ITAR EAR"],
            "fr": ["{entity} sanctions embargo liste noire", "{entity} contrôle exportation"],
            "de": ["{entity} Sanktionen Embargo Schwarze Liste", "{entity} Exportkontrolle"],
            "ru": ["{entity} санкции эмбарго черный список"],
        },
        "scandals": {
            "en": ["{entity} scandal investigation fraud corruption", "{entity} lawsuit litigation legal proceedings"],
            "fr": ["{entity} scandale enquête fraude corruption", "{entity} procès litige juridique"],
            "de": ["{entity} Skandal Untersuchung Betrug Korruption"],
        },
        "leaks": {
            "en": ["{entity} Panama Papers Paradise Papers leaked documents", "{entity} offshore shell company tax haven"],
            "fr": ["{entity} Panama Papers documents fuités offshore", "{entity} paradis fiscal société écran"],
        },
        "contracts": {
            "en": ["{entity} contract awarded government procurement", "{entity} tender bid RFP"],
            "fr": ["{entity} contrat attribué marché public appel d'offres"],
            "de": ["{entity} Auftrag Vergabe öffentliche Ausschreibung"],
        },
        "shipping": {
            "en": ["{entity} shipment bill of lading maritime traffic port", "{entity} vessel owner cargo"],
            "fr": ["{entity} expédition fret maritime port navire", "{entity} connaissement cargaison"],
            "ru": ["{entity} груз перевозка порт судно"],
            "zh": ["{entity} 装运 提单 海运 港口"],
        },
        "commodities": {
            "en": ["{entity} mining concession extraction rights", "{entity} oil gas exploration license"],
            "fr": ["{entity} concession minière droits extraction", "{entity} perms exploration pétrole gaz"],
            "es": ["{entity} concesión minera derechos extracción", "{entity} petróleo gas"],
        },
    }

    # Languages to try based on entity origin
    LANGUAGE_HINTS = {
        # Company name patterns -> likely languages to search
        "thales": ["fr", "en"],
        "safran": ["fr", "en"],
        "airbus": ["fr", "de", "en"],
        "dassault": ["fr", "en"],
        "rheinmetall": ["de", "en"],
        "leonardo": ["it", "en"],
        "bae": ["en"],
        "lockheed": ["en"],
        "boeing": ["en"],
        "huawei": ["zh", "en"],
        "alibaba": ["zh", "en"],
        "gazprom": ["ru", "en"],
        "rosneft": ["ru", "en"],
        "rosatom": ["ru", "en"],
    }

    def __init__(self, use_cache: bool = True, max_workers: int = 4, aggressive: bool = True):
        self.max_depth = 3
        self.max_results = 8  # More results per query
        self.max_workers = max_workers
        self.aggressive = aggressive  # Use all languages and strategies
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Cache
        self.cache = None
        if use_cache:
            try:
                from src.storage.cache import get_discovery_cache
                self.cache = get_discovery_cache()
            except Exception as e:
                logger.warning("cache_init_failed", error=str(e))

    def _detect_entity_context(self, entity_name: str) -> Dict:
        """
        Detect entity context using LLM for targeted search.
        Uses robust JSON parsing to handle dirty LLM outputs.
        """
        try:
            prompt = f"""Analyze this entity for OSINT investigation: "{entity_name}"

Determine:
1. Entity type: COMPANY, PRODUCT, PERSON, or GOVERNMENT
2. Industry: DEFENSE, AEROSPACE, ENERGY, FINANCE, TECH, OTHER
3. Likely countries of origin/operation (ISO 2-letter codes)
4. Known parent company (if subsidiary)
5. Key search terms in original language

Return ONLY valid JSON:
{{"type": "COMPANY", "industry": "DEFENSE", "countries": ["FR", "DE"], "parent": "Thales Group", "native_terms": ["radar", "système d'armes"]}}
"""
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # 1. Try clean Parse
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            # 2. Markdown Cleanup
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            
            # 3. Regex Extraction (Non-greedy)
            match = re.search(r'\{.*?\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            
            logger.warning("json_parse_failed_raw", text=text[:100])
                
        except Exception as e:
            logger.warning("context_detection_failed", entity=entity_name, error=str(e))
        
        return {"type": "UNKNOWN", "industry": "OTHER", "countries": ["US"], "parent": None, "native_terms": []}

    def _get_languages_for_entity(self, entity_name: str, context: Dict) -> List[str]:
        """Determine which languages to search in."""
        languages = ["en"]  # Always include English
        
        # From context detection
        countries = context.get("countries", [])
        country_to_lang = {
            "FR": "fr", "DE": "de", "CN": "zh", "RU": "ru", 
            "ES": "es", "AR": "ar", "IT": "it", "JP": "ja"
        }
        for country in countries:
            if country in country_to_lang:
                lang = country_to_lang[country]
                if lang not in languages:
                    languages.append(lang)
        
        # From entity name hints
        entity_lower = entity_name.lower()
        for hint, langs in self.LANGUAGE_HINTS.items():
            if hint in entity_lower:
                for lang in langs:
                    if lang not in languages:
                        languages.append(lang)
        
        return languages[:4]  # Max 4 languages

    def _generate_queries(self, entity_name: str, context: Dict) -> List[str]:
        """Generate comprehensive multilingual queries."""
        queries = []
        languages = self._get_languages_for_entity(entity_name, context)
        
        # Determine relevant strategies based on context
        industry = context.get("industry", "OTHER")
        strategies_to_use = ["suppliers", "ownership", "scandals"]
        
        if industry in ["DEFENSE", "AEROSPACE"]:
            strategies_to_use.extend(["sanctions", "contracts"])
        if industry in ["FINANCE", "ENERGY"]:
            strategies_to_use.extend(["sanctions", "leaks"])
        
        # Generate queries for each strategy and language
        for strategy in strategies_to_use:
            strategy_templates = self.SEARCH_STRATEGIES.get(strategy, {})
            for lang in languages:
                templates = strategy_templates.get(lang, strategy_templates.get("en", []))
                for template in templates[:2]:  # Max 2 per strategy/language
                    query = template.format(entity=entity_name)
                    queries.append(query)
        
        # Add native terms from context
        native_terms = context.get("native_terms", [])
        for term in native_terms[:3]:
            queries.append(f"{entity_name} {term}")
        
        # Add parent company queries
        if context.get("parent"):
            parent = context["parent"]
            queries.append(f"{entity_name} {parent} subsidiary")
            queries.append(f"{parent} {entity_name} supply chain")
        
        # Deduplicate and limit
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower().strip()
            if q_lower not in seen and len(q) > 5:
                seen.add(q_lower)
                unique_queries.append(q)
        
        logger.info("queries_generated", entity=entity_name, count=len(unique_queries), languages=languages)
        return unique_queries[:25]  # Max 25 queries

    def _is_noise_url(self, url: str) -> bool:
        """Check if URL is from a noise domain."""
        url_lower = url.lower()
        for domain in self.NOISE_DOMAINS:
            if domain in url_lower:
                return True
        return False

    def _score_url(self, url: str) -> float:
        """Score URL based on domain quality."""
        url_lower = url.lower()
        
        # High value checking
        for domain, score in self.HIGH_VALUE_DOMAINS.items():
            if domain in url_lower:
                return score
                
        # Weak signal checking
        for domain, score in self.WEAK_SIGNAL_DOMAINS.items():
            if domain in url_lower:
                return score
                
        return 0.5  # Default score (Unknown sources)

    def _execute_search(self, query: str) -> List[Dict]:
        """Execute single search with caching and filtering."""
        # Check cache
        if self.cache:
            cached = self.cache.get_cached_search(query)
            if cached:
                return cached

        results = []
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=self.max_results))
                for r in raw_results:
                    url = r.get("href")
                    if url and not self._is_noise_url(url):
                        results.append({
                            "href": url,
                            "title": r.get("title", ""),
                            "body": r.get("body", ""),
                            "score": self._score_url(url)
                        })
            
            # Cache results
            if self.cache and results:
                self.cache.cache_search_results(query, results)
            
            logger.info("search_executed", query=query[:60], count=len(results))
            
        except Exception as e:
            logger.warning("search_failed", query=query[:60], error=str(e))
        
        return results

    def _execute_search_with_delay(self, query: str) -> List[Dict]:
        """Search with optimized anti-bot delay."""
        # Reduced delay (0.5s - 1.5s) to avoid blocking threads too long
        time.sleep(random.uniform(0.5, 1.5))
        return self._execute_search(query)

    def _parallel_search(self, queries: List[str]) -> List[Dict]:
        """Execute searches in parallel, return scored results."""
        all_results = []
        seen_urls = set()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_query = {
                executor.submit(self._execute_search_with_delay, q): q 
                for q in queries
            }
            
            for future in as_completed(future_to_query):
                try:
                    results = future.result()
                    for r in results:
                        url = r.get("href")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)
                except Exception as e:
                    logger.warning("parallel_search_error", error=str(e))
        
        # Sort by score (best sources first)
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results

    def discover(self, entity_name: str, depth: int = 0, max_urls: int = 50) -> Dict:
        """
        Main discovery method with advanced multilingual search.
        
        Returns:
            Dict with discovered URLs ranked by quality + coverage analysis
        """
        if depth >= self.max_depth:
            return {"entity": entity_name, "urls": [], "max_depth": True}
        
        # Check cache
        if self.cache:
            history = self.cache.get_entity_history(entity_name)
            if history and history.get("urls"):
                logger.info("entity_cache_hit", entity=entity_name)
                return {"entity": entity_name, "urls": history["urls"], "cached": True}
        
        logger.info("discovery_v3_started", entity=entity_name, depth=depth)
        
        # 1. Detect entity context
        context = self._detect_entity_context(entity_name)
        
        # 2. Generate comprehensive queries
        queries = self._generate_queries(entity_name, context)
        
        # 3. Execute parallel searches with strategy tracking
        results = self._parallel_search(queries)
        
        # 4. Coverage Analysis - Track what we found and what's missing
        coverage_report = None
        try:
            from src.pipeline.coverage_analysis import CoverageAnalyzer
            
            analyzer = CoverageAnalyzer()
            
            # Group results by strategy for coverage analysis
            strategy_results = {}
            strategy_queries = {}
            
            for strategy_name, templates in self.SEARCH_STRATEGIES.items():
                strategy_results[strategy_name] = []
                strategy_queries[strategy_name] = []
                
                # Find queries that belong to this strategy
                for q in queries:
                    for lang, lang_templates in templates.items():
                        for template in lang_templates:
                            if template.replace("{entity}", "").strip() in q:
                                strategy_queries[strategy_name].append(q)
                                break
                
                # Find results matching this strategy's queries
                for r in results:
                    # Simple heuristic: if result URL hasn't been assigned yet
                    if r not in strategy_results[strategy_name]:
                        strategy_results[strategy_name].append(r)
            
            # Record searches
            languages = self._get_languages_for_entity(entity_name, context)
            for strategy, strat_results in strategy_results.items():
                for lang in languages:
                    strat_queries = strategy_queries.get(strategy, [])
                    if strat_queries:
                        analyzer.record_search(
                            strategy=strategy,
                            query=strat_queries[0] if strat_queries else f"{entity_name} {strategy}",
                            language=lang,
                            results=strat_results[:10]
                        )
            
            coverage_report = analyzer.analyze(entity_name)
            
            # Log coverage issues
            if coverage_report.critical_gaps:
                logger.warning(
                    "coverage_critical_gaps",
                    entity=entity_name,
                    gaps=coverage_report.critical_gaps
                )
            
        except Exception as e:
            logger.warning("coverage_analysis_failed", error=str(e))
        
        # 5. Extract best URLs
        urls = [r["href"] for r in results[:max_urls]]
        
        # 6. Filter already processed URLs
        if self.cache:
            new_urls = []
            for url in urls:
                if not self.cache.is_url_processed(url):
                    new_urls.append(url)
                    self.cache.mark_url_processed(url)
            urls = new_urls
        
        logger.info("discovery_v3_complete", 
                   entity=entity_name, 
                   urls=len(urls),
                   context=context.get("industry"),
                   languages=self._get_languages_for_entity(entity_name, context),
                   coverage_score=coverage_report.coverage_score if coverage_report else None)
        
        # Store in cache
        if self.cache:
            self.cache.store_entity_history(entity_name, {
                "urls": urls,
                "context": context,
                "query_count": len(queries)
            })
        
        result = {
            "entity": entity_name,
            "urls": urls,
            "context": context,
            "queries_executed": len(queries),
            "high_value_sources": len([r for r in results if r.get("score", 0) >= 0.85])
        }
        
        # Add coverage analysis if available
        if coverage_report:
            result["coverage"] = {
                "score": coverage_report.coverage_score,
                "gaps": coverage_report.gap_strategies,
                "critical_gaps": coverage_report.critical_gaps,
                "recommendations": coverage_report.recommendations,
                "suspicious": coverage_report.suspicious_gaps
            }
        
        return result


# Backward compatibility alias
DiscoveryEngine = DiscoveryEngineV3
