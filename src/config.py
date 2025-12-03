from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict

class Settings(BaseSettings):
    # Infrastructure
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "shadowmap_entities"
    
    POSTGRES_DSN: str = "postgresql://shadowmap:shadowmap@localhost:5432/shadowmap_audit"
    
    REDIS_URL: str = "redis://localhost:6379/0"

    # Scoring Weights
    SOURCE_WEIGHTS: Dict[str, float] = {
        "reuters.com": 0.95,
        "apnews.com": 0.95,
        "nytimes.com": 0.90,
        "bbc.com": 0.90,
        "telegram": 0.30,
        "twitter.com": 0.40,
        "x.com": 0.40,
        "DEFAULT": 0.50
    }
    
    METHOD_WEIGHTS: Dict[str, float] = {
        "gpt-4o": 0.90,
        "gpt-4-turbo": 0.85,
        "spacy_ner": 0.70,
        "regex": 0.60,
        "manual_verification": 1.0
    }

    # Entity Resolution Thresholds
    MERGE_THRESHOLDS: Dict[str, float] = {
        "PERSON": 0.92,
        "ORGANIZATION": 0.90,
        "LOCATION": 0.95,
        "EVENT": 0.85,
        "CRYPTO_WALLET": 1.0, # Exact match only
        "DEFAULT": 0.90
    }
    
    HITL_MIN_SCORE: float = 0.80

    # OpSec
    JITTER_MIN: float = 1.5
    JITTER_MAX: float = 4.0

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
