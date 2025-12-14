"""
ShadowMap Data Sources Configuration
Premium APIs ready but disabled by default (using DuckDuckGo for demo).
Enable when scaling to production.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataSourcesConfig(BaseSettings):
    """
    Configuration for external data sources.
    Set ENABLE_PREMIUM_SOURCES=true in .env to activate paid APIs.
    """
    
    # === MASTER SWITCH ===
    ENABLE_PREMIUM_SOURCES: bool = False  # Keep False for demo, True for production
    
    # === SEARCH ENGINES ===
    # DuckDuckGo (FREE - Default for demo)
    USE_DUCKDUCKGO: bool = True
    
    # SerpApi (PAID - Google results without blocking)
    # $50/month for 5000 searches
    SERPAPI_API_KEY: Optional[str] = None
    USE_SERPAPI: bool = False
    
    # BrightData / Oxylabs (PAID - Proxy + SERP)
    # Enterprise pricing
    BRIGHTDATA_API_KEY: Optional[str] = None
    USE_BRIGHTDATA: bool = False
    
    # === CORPORATE REGISTRIES ===
    # OpenCorporates (PAID - Company data worldwide)
    # $500/month for API access
    OPENCORPORATES_API_KEY: Optional[str] = None
    USE_OPENCORPORATES: bool = False
    
    # GLEIF (FREE with rate limits - LEI data for financial entities)
    # Legal Entity Identifiers
    USE_GLEIF: bool = False
    GLEIF_API_URL: str = "https://api.gleif.org/api/v1"
    
    # Companies House UK (FREE with API key)
    COMPANIES_HOUSE_API_KEY: Optional[str] = None
    USE_COMPANIES_HOUSE: bool = False
    
    # === LEAK DATABASES & INVESTIGATIONS ===
    # OCCRP Aleph (FREE - Investigative journalism database)
    # Requires account approval
    OCCRP_ALEPH_API_KEY: Optional[str] = None
    USE_OCCRP_ALEPH: bool = False
    OCCRP_ALEPH_URL: str = "https://aleph.occrp.org/api/2"
    
    # === SANCTIONS & RISK ===
    # OpenSanctions (FREE - Sanctions, PEPs, criminals)
    USE_OPENSANCTIONS: bool = False
    OPENSANCTIONS_API_URL: str = "https://api.opensanctions.org"
    
    # === KNOWLEDGE GRAPHS ===
    # Wikidata (FREE - Structured entity data)
    USE_WIKIDATA: bool = False
    WIKIDATA_SPARQL_URL: str = "https://query.wikidata.org/sparql"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Singleton instance
data_sources = DataSourcesConfig()


# === PRICING SUMMARY FOR INVESTORS ===
"""
MONTHLY COST BREAKDOWN (Production Mode):

| Source         | Cost/Month | Value                           |
|----------------|------------|--------------------------------|
| DuckDuckGo     | FREE       | Demo only, rate limited        |
| SerpApi        | $50        | 5000 Google searches           |
| OpenCorporates | $500       | Unlimited company lookups      |
| GLEIF          | FREE       | Financial entity LEIs          |
| OCCRP Aleph    | FREE       | Investigative data             |
| OpenSanctions  | FREE       | Sanctions screening            |
| BrightData     | $500+      | Proxy + anti-blocking          |

TOTAL MINIMUM: ~$600/month for production-grade data
TOTAL ENTERPRISE: ~$2000/month with proxy infrastructure

ROI: One due diligence report sells $5,000-$50,000
"""
