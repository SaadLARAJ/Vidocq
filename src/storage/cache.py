"""
Redis-based caching for discovery operations.
"""
import json
import hashlib
import redis
from typing import List, Dict, Optional, Set
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class DiscoveryCache:
    """Caching layer for discovery operations with TTL and deduplication."""
    
    def __init__(self, ttl_hours: int = 24):
        self.ttl = ttl_hours * 3600  # Convert to seconds
        try:
            self.client = redis.from_url(settings.REDIS_URL)
            self.client.ping()
            self.enabled = True
            logger.info("discovery_cache_connected", redis_url=settings.REDIS_URL)
        except Exception as e:
            logger.warning("discovery_cache_disabled", error=str(e))
            self.client = None
            self.enabled = False
    
    def _hash_query(self, query: str) -> str:
        """Generate a unique hash for a search query."""
        return f"search:{hashlib.md5(query.lower().encode()).hexdigest()}"
    
    def _url_key(self, url: str) -> str:
        """Generate a unique key for a URL."""
        return f"url:{hashlib.md5(url.encode()).hexdigest()}"
    
    def _entity_key(self, entity_name: str) -> str:
        """Generate a unique key for an entity investigation."""
        return f"entity:{hashlib.md5(entity_name.lower().encode()).hexdigest()}"
    
    # --- Search Results Caching ---
    
    def get_cached_search(self, query: str) -> Optional[List[Dict]]:
        """
        Check if search results are cached.
        Returns None if not cached or cache disabled.
        """
        if not self.enabled:
            return None
        
        try:
            key = self._hash_query(query)
            cached = self.client.get(key)
            if cached:
                logger.info("cache_hit_search", query=query[:50])
                return json.loads(cached)
        except Exception as e:
            logger.warning("cache_read_error", error=str(e))
        
        return None
    
    def cache_search_results(self, query: str, results: List[Dict]):
        """Store search results in cache with TTL."""
        if not self.enabled or not results:
            return
        
        try:
            key = self._hash_query(query)
            self.client.setex(key, self.ttl, json.dumps(results))
            logger.info("cache_stored_search", query=query[:50], count=len(results))
        except Exception as e:
            logger.warning("cache_write_error", error=str(e))
    
    # --- URL Deduplication ---
    
    def is_url_processed(self, url: str) -> bool:
        """Check if a URL has already been ingested."""
        if not self.enabled:
            return False
        
        try:
            return self.client.exists(self._url_key(url)) > 0
        except Exception:
            return False
    
    def mark_url_processed(self, url: str, source_entity: str = "unknown"):
        """Mark a URL as processed to avoid re-ingestion."""
        if not self.enabled:
            return
        
        try:
            key = self._url_key(url)
            self.client.setex(key, self.ttl * 7, json.dumps({  # 7x TTL for URLs
                "url": url,
                "source": source_entity,
                "processed": True
            }))
        except Exception as e:
            logger.warning("cache_mark_url_error", error=str(e))
    
    def filter_new_urls(self, urls: Set[str]) -> Set[str]:
        """Filter out already-processed URLs from a set."""
        if not self.enabled:
            return urls
        
        return {url for url in urls if not self.is_url_processed(url)}
    
    # --- Entity Investigation History ---
    
    def get_entity_history(self, entity_name: str) -> Optional[Dict]:
        """Get previous investigation data for an entity."""
        if not self.enabled:
            return None
        
        try:
            key = self._entity_key(entity_name)
            cached = self.client.get(key)
            if cached:
                logger.info("cache_hit_entity", entity=entity_name)
                return json.loads(cached)
        except Exception:
            pass
        
        return None
    
    def store_entity_investigation(self, entity_name: str, data: Dict):
        """Store investigation results for an entity."""
        if not self.enabled:
            return
        
        try:
            key = self._entity_key(entity_name)
            # Merge with existing data if present
            existing = self.get_entity_history(entity_name) or {}
            existing.update(data)
            existing["last_updated"] = str(__import__("datetime").datetime.utcnow())
            
            self.client.setex(key, self.ttl * 30, json.dumps(existing))  # 30 days for entities
        except Exception as e:
            logger.warning("cache_store_entity_error", error=str(e))
    
    # Alias for backward compatibility with discovery_v3.py
    def store_entity_history(self, entity_name: str, data: Dict):
        """Alias for store_entity_investigation."""
        self.store_entity_investigation(entity_name, data)

    
    # --- Statistics ---
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            info = self.client.info("keyspace")
            return {
                "enabled": True,
                "ttl_hours": self.ttl // 3600,
                "keyspace": info
            }
        except Exception:
            return {"enabled": True, "error": "stats_unavailable"}


# Singleton instance
_cache_instance = None


def get_discovery_cache() -> DiscoveryCache:
    """Get or create the singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DiscoveryCache()
    return _cache_instance
