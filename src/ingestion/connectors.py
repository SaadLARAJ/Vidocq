"""
ShadowMap Premium Data Connectors
Ready for production but disabled by default.
Enable via ENABLE_PREMIUM_SOURCES=true in .env
"""

import httpx
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from src.core.sources import data_sources
from src.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# BASE CONNECTOR
# =============================================================================

class BaseConnector(ABC):
    """Abstract base class for all data source connectors."""
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if this connector is enabled."""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Execute a search query."""
        pass


# =============================================================================
# SEARCH ENGINE CONNECTORS
# =============================================================================

class SerpApiConnector(BaseConnector):
    """
    SerpApi - Google Search without blocking.
    Cost: $50/month for 5000 searches.
    Docs: https://serpapi.com/
    """
    
    def __init__(self):
        self.api_key = data_sources.SERPAPI_API_KEY
        self.base_url = "https://serpapi.com/search"
    
    def is_enabled(self) -> bool:
        return data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_SERPAPI and self.api_key
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            logger.debug("SerpApi disabled, skipping")
            return []
        
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": limit
            }
            
            with httpx.Client(timeout=30) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for item in data.get("organic_results", [])[:limit]:
                results.append({
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                    "source": "serpapi"
                })
            
            logger.info("serpapi_search_complete", query=query, results=len(results))
            return results
            
        except Exception as e:
            logger.error("serpapi_error", error=str(e))
            return []


# =============================================================================
# CORPORATE REGISTRY CONNECTORS
# =============================================================================

class OpenCorporatesConnector(BaseConnector):
    """
    OpenCorporates - Global company registry.
    Cost: $500/month for API access.
    Docs: https://api.opencorporates.com/
    """
    
    def __init__(self):
        self.api_key = data_sources.OPENCORPORATES_API_KEY
        self.base_url = "https://api.opencorporates.com/v0.4"
    
    def is_enabled(self) -> bool:
        return data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_OPENCORPORATES and self.api_key
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            logger.debug("OpenCorporates disabled, skipping")
            return []
        
        try:
            url = f"{self.base_url}/companies/search"
            params = {
                "q": query,
                "api_token": self.api_key,
                "per_page": limit
            }
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for company in data.get("results", {}).get("companies", []):
                c = company.get("company", {})
                results.append({
                    "name": c.get("name"),
                    "jurisdiction": c.get("jurisdiction_code"),
                    "company_number": c.get("company_number"),
                    "status": c.get("current_status"),
                    "incorporation_date": c.get("incorporation_date"),
                    "registered_address": c.get("registered_address_in_full"),
                    "opencorporates_url": c.get("opencorporates_url"),
                    "source": "opencorporates"
                })
            
            logger.info("opencorporates_search_complete", query=query, results=len(results))
            return results
            
        except Exception as e:
            logger.error("opencorporates_error", error=str(e))
            return []
    
    def get_company_officers(self, jurisdiction: str, company_number: str) -> List[Dict]:
        """Get directors/officers of a company - useful for UBO tracing."""
        if not self.is_enabled():
            return []
        
        try:
            url = f"{self.base_url}/companies/{jurisdiction}/{company_number}/officers"
            params = {"api_token": self.api_key}
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return data.get("results", {}).get("officers", [])
            
        except Exception as e:
            logger.error("opencorporates_officers_error", error=str(e))
            return []


class GLEIFConnector(BaseConnector):
    """
    GLEIF - Legal Entity Identifier (LEI) database.
    FREE with rate limits.
    Docs: https://www.gleif.org/en/lei-data/gleif-api
    """
    
    def __init__(self):
        self.base_url = data_sources.GLEIF_API_URL
    
    def is_enabled(self) -> bool:
        return data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_GLEIF
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            logger.debug("GLEIF disabled, skipping")
            return []
        
        try:
            url = f"{self.base_url}/lei-records"
            params = {
                "filter[fulltext]": query,
                "page[size]": limit
            }
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for record in data.get("data", []):
                attrs = record.get("attributes", {})
                entity = attrs.get("entity", {})
                results.append({
                    "lei": attrs.get("lei"),
                    "name": entity.get("legalName", {}).get("name"),
                    "jurisdiction": entity.get("jurisdiction"),
                    "status": attrs.get("registration", {}).get("status"),
                    "legal_form": entity.get("legalForm", {}).get("id"),
                    "headquarters": entity.get("headquartersAddress", {}),
                    "source": "gleif"
                })
            
            logger.info("gleif_search_complete", query=query, results=len(results))
            return results
            
        except Exception as e:
            logger.error("gleif_error", error=str(e))
            return []


# =============================================================================
# INVESTIGATION & SANCTIONS CONNECTORS
# =============================================================================

class OCCRPAlephConnector(BaseConnector):
    """
    OCCRP Aleph - Investigative journalism database.
    FREE but requires approved account.
    Contains: Offshore Leaks, court records, corporate registries.
    Docs: https://aleph.occrp.org/
    """
    
    def __init__(self):
        self.api_key = data_sources.OCCRP_ALEPH_API_KEY
        self.base_url = data_sources.OCCRP_ALEPH_URL
    
    def is_enabled(self) -> bool:
        return data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_OCCRP_ALEPH and self.api_key
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            logger.debug("OCCRP Aleph disabled, skipping")
            return []
        
        try:
            url = f"{self.base_url}/entities"
            headers = {"Authorization": f"ApiKey {self.api_key}"}
            params = {"q": query, "limit": limit}
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for entity in data.get("results", []):
                results.append({
                    "id": entity.get("id"),
                    "name": entity.get("properties", {}).get("name", [None])[0],
                    "schema": entity.get("schema"),
                    "datasets": entity.get("datasets"),
                    "source": "occrp_aleph"
                })
            
            logger.info("occrp_search_complete", query=query, results=len(results))
            return results
            
        except Exception as e:
            logger.error("occrp_error", error=str(e))
            return []


class OpenSanctionsConnector(BaseConnector):
    """
    OpenSanctions - Sanctions, PEPs, and criminals database.
    FREE and open source.
    Contains: OFAC, EU, UN sanctions lists + PEP data.
    Docs: https://www.opensanctions.org/docs/api/
    """
    
    def __init__(self):
        self.base_url = data_sources.OPENSANCTIONS_API_URL
    
    def is_enabled(self) -> bool:
        return data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_OPENSANCTIONS
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            logger.debug("OpenSanctions disabled, skipping")
            return []
        
        try:
            url = f"{self.base_url}/search/default"
            params = {"q": query, "limit": limit}
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for entity in data.get("results", []):
                results.append({
                    "id": entity.get("id"),
                    "name": entity.get("caption"),
                    "schema": entity.get("schema"),
                    "datasets": entity.get("datasets"),
                    "first_seen": entity.get("first_seen"),
                    "last_seen": entity.get("last_seen"),
                    "is_sanctioned": "sanctions" in str(entity.get("datasets", [])).lower(),
                    "source": "opensanctions"
                })
            
            logger.info("opensanctions_search_complete", query=query, results=len(results))
            return results
            
        except Exception as e:
            logger.error("opensanctions_error", error=str(e))
            return []


class WikidataConnector(BaseConnector):
    """
    Wikidata - Structured knowledge base.
    FREE and unlimited.
    Useful for: Entity disambiguation, basic facts, relationships.
    """
    
    def __init__(self):
        self.sparql_url = data_sources.WIKIDATA_SPARQL_URL
    
    def is_enabled(self) -> bool:
        return data_sources.ENABLE_PREMIUM_SOURCES and data_sources.USE_WIKIDATA
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            logger.debug("Wikidata disabled, skipping")
            return []
        
        try:
            # Use Wikidata's search API (simpler than SPARQL for basic search)
            url = "https://www.wikidata.org/w/api.php"
            params = {
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": limit,
                "format": "json"
            }
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for entity in data.get("search", []):
                results.append({
                    "id": entity.get("id"),
                    "name": entity.get("label"),
                    "description": entity.get("description"),
                    "wikidata_url": f"https://www.wikidata.org/wiki/{entity.get('id')}",
                    "source": "wikidata"
                })
            
            logger.info("wikidata_search_complete", query=query, results=len(results))
            return results
            
        except Exception as e:
            logger.error("wikidata_error", error=str(e))
            return []


# =============================================================================
# UNIFIED MULTI-SOURCE SEARCH
# =============================================================================

class MultiSourceSearch:
    """
    Aggregates results from all enabled data sources.
    Use this in discovery.py when ENABLE_PREMIUM_SOURCES=true.
    """
    
    def __init__(self):
        self.connectors = [
            SerpApiConnector(),
            OpenCorporatesConnector(),
            GLEIFConnector(),
            OCCRPAlephConnector(),
            OpenSanctionsConnector(),
            WikidataConnector(),
        ]
    
    def search_all(self, query: str, limit_per_source: int = 5) -> Dict[str, List[Dict]]:
        """
        Search across all enabled sources.
        Returns results grouped by source.
        """
        results = {}
        
        for connector in self.connectors:
            if connector.is_enabled():
                source_name = connector.__class__.__name__.replace("Connector", "")
                results[source_name] = connector.search(query, limit=limit_per_source)
        
        # Log summary
        total = sum(len(r) for r in results.values())
        logger.info("multi_source_search_complete", 
                   query=query, 
                   sources=len(results), 
                   total_results=total)
        
        return results
    
    def get_enabled_sources(self) -> List[str]:
        """List all currently enabled sources."""
        return [
            c.__class__.__name__.replace("Connector", "")
            for c in self.connectors
            if c.is_enabled()
        ]


# =============================================================================
# SANCTIONS SCREENING UTILITY
# =============================================================================

def screen_entity_sanctions(entity_name: str) -> Dict[str, Any]:
    """
    Quick sanctions screening for an entity.
    Returns risk assessment.
    """
    connector = OpenSanctionsConnector()
    
    if not connector.is_enabled():
        return {
            "screened": False,
            "reason": "OpenSanctions not enabled",
            "is_sanctioned": None
        }
    
    results = connector.search(entity_name, limit=5)
    
    if not results:
        return {
            "screened": True,
            "is_sanctioned": False,
            "matches": []
        }
    
    # Check for sanctions matches
    sanctioned_matches = [r for r in results if r.get("is_sanctioned")]
    
    return {
        "screened": True,
        "is_sanctioned": len(sanctioned_matches) > 0,
        "matches": results,
        "risk_level": "HIGH" if sanctioned_matches else "LOW"
    }
