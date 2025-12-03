"""
ShadowMap Entreprise v4.0 - Gestion de la configuration

Toutes les valeurs de configuration, seuils et poids sont centralisés ici.
ZÉRO nombre magique autorisé dans la logique métier.

Les variables d'environnement surchargent les valeurs par défaut via Pydantic Settings.
"""

from typing import Dict, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration centralisée pour ShadowMap Entreprise.

    Tous les seuils, poids et paramètres opérationnels sont définis ici
    pour éviter les nombres magiques dans le code et permettre un ajustement facile.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # =========================================================================
    # ENVIRONNEMENT & DÉPLOIEMENT
    # =========================================================================
    ENVIRONMENT: Literal["development", "staging", "production"] = "production"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # =========================================================================
    # CONNEXIONS AUX BASES DE DONNÉES
    # =========================================================================
    NEO4J_URI: str = Field(
        default="bolt://localhost:7687",
        description="URI de connexion Bolt pour Neo4j"
    )
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = Field(
        default="shadowmap_secure_2024",
        description="Mot de passe d'authentification Neo4j"
    )
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_TRANSACTION_RETRY_TIME: int = 30  # secondes
    NEO4J_CONNECTION_TIMEOUT: int = 30  # secondes

    POSTGRES_DSN: str = Field(
        default="postgresql://shadowmap:shadowmap_pg_2024@localhost:5432/shadowmap_audit",
        description="Chaîne de connexion PostgreSQL pour la piste d'audit et la DLQ"
    )

    REDIS_URL: str = Field(
        default="redis://:shadowmap_redis_2024@localhost:6379/0",
        description="URL de connexion Redis pour le broker Celery et le cache"
    )

    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Point de terminaison HTTP de la base de données vectorielle Qdrant"
    )
    QDRANT_COLLECTION_NAME: str = "shadowmap_entities"
    QDRANT_VECTOR_SIZE: int = 768  # plongements all-MiniLM-L6-v2

    # =========================================================================
    # POIDS DE FIABILITÉ DES SOURCES (0.0 - 1.0)
    # =========================================================================
    SOURCE_WEIGHTS: Dict[str, float] = {
        # Niveau 1 : Agences de presse de haute confiance
        "reuters.com": 0.95,
        "apnews.com": 0.95,
        "bbc.com": 0.93,
        "nytimes.com": 0.90,
        "washingtonpost.com": 0.90,
        "theguardian.com": 0.88,
        "wsj.com": 0.90,
        "ft.com": 0.92,

        # Niveau 2 : Sources régionales réputées
        "cnn.com": 0.80,
        "aljazeera.com": 0.82,
        "dw.com": 0.85,
        "france24.com": 0.83,

        # Niveau 3 : Sources de renseignement spécialisées
        "bellingcat.com": 0.88,
        "occrp.org": 0.90,
        "icij.org": 0.92,

        # Niveau 4 : Médias sociaux / Faible confiance
        "twitter.com": 0.40,
        "x.com": 0.40,
        "telegram": 0.30,
        "reddit.com": 0.35,

        # Niveau 5 : Sources Blockchain
        "etherscan.io": 0.95,
        "blockchain.com": 0.93,

        # Défaut pour les sources inconnues
        "DEFAULT": 0.50
    }

    # =========================================================================
    # POIDS DE CONFIANCE DES MÉTHODES D'EXTRACTION (0.0 - 1.0)
    # =========================================================================
    METHOD_WEIGHTS: Dict[str, float] = {
        "manual_verification": 1.00,  # Vérifié par un humain
        "gpt-4o": 0.90,               # GPT-4 Omni
        "gpt-4-turbo": 0.88,
        "gpt-4": 0.85,
        "claude-3-opus": 0.90,
        "claude-3-sonnet": 0.85,
        "spacy_ner": 0.70,            # Ligne de base SpaCy NER
        "regex_extraction": 0.60,     # Correspondance de motifs
        "heuristic": 0.50,            # Heuristiques basées sur des règles
    }

    # =========================================================================
    # SEUILS DE RÉSOLUTION D'ENTITÉS
    # =========================================================================
    MERGE_THRESHOLDS: Dict[str, float] = {
        "PERSON": 0.92,         # Seuil élevé pour la fusion de personnes (éviter les faux positifs)
        "ORGANIZATION": 0.88,   # Les organisations peuvent avoir des noms similaires
        "LOCATION": 0.95,       # Les lieux sont bien définis
        "EVENT": 0.85,          # Les événements peuvent être décrits différemment
        "CRYPTO_WALLET": 0.99,  # Les portefeuilles doivent correspondre exactement
        "DOCUMENT": 0.90,
        "DEFAULT": 0.90
    }

    # Score de similarité minimum pour déclencher une revue HITL
    HITL_MINIMUM_SCORE: float = 0.80

    # En dessous de ce score, aucune considération de fusion
    IGNORE_SIMILARITY_BELOW: float = 0.70

    # =========================================================================
    # PARAMÈTRES DE CALCUL DE LA CONFIANCE
    # =========================================================================
    # Score de confiance maximal atteignable (jamais 1.0 pour indiquer l'incertitude)
    MAX_CONFIDENCE: float = 0.99

    # Formule de boost de corroboration : 1 + log10(N) / CORROBORATION_DIVISOR
    CORROBORATION_DIVISOR: float = 10.0

    # =========================================================================
    # CONFIGURATION DES TÂCHES CELERY
    # =========================================================================
    CELERY_BROKER_URL: str = Field(
        default="redis://:shadowmap_redis_2024@localhost:6379/0",
        description="Broker de messages Celery"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://:shadowmap_redis_2024@localhost:6379/1",
        description="Backend de résultats Celery"
    )
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 600  # Limite stricte de 10 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 540  # Limite souple de 9 minutes

    # Configuration des nouvelles tentatives
    CELERY_MAX_RETRIES: int = 3
    CELERY_RETRY_BACKOFF: bool = True
    CELERY_RETRY_BACKOFF_MAX: int = 600  # secondes
    CELERY_RETRY_JITTER: bool = True

    # =========================================================================
    # CONFIGURATION DE LA FILE DE MESSAGES MORTS (DLQ)
    # =========================================================================
    DLQ_RETENTION_DAYS: int = 90
    DLQ_AUTO_RETRY_ENABLED: bool = False  # Examen manuel requis

    # =========================================================================
    # CONFIGURATION OPSEC & FURTIVITÉ
    # =========================================================================
    # Plage de gigue du délai de requête (secondes)
    REQUEST_DELAY_MIN: float = 1.5
    REQUEST_DELAY_MAX: float = 4.0

    # Délai d'attente de connexion pour les requêtes HTTP
    HTTP_TIMEOUT: int = 30

    # Nombre maximum de requêtes simultanées par domaine
    MAX_CONCURRENT_REQUESTS_PER_DOMAIN: int = 2

    # Rotation des User-Agents activée
    ROTATE_USER_AGENTS: bool = True

    # =========================================================================
    # EXTRACTION & ANALYSE
    # =========================================================================
    # Taille des morceaux sémantiques pour les documents longs
    CHUNK_SIZE: int = 1000  # tokens
    CHUNK_OVERLAP: int = 200  # tokens

    # Taille maximale du document à traiter (octets)
    MAX_DOCUMENT_SIZE: int = 10 * 1024 * 1024  # 10 Mo

    # Taille du lot d'extraction LLM
    LLM_BATCH_SIZE: int = 5

    # =========================================================================
    # VERSIONNAGE DES PROMPTS
    # =========================================================================
    CURRENT_EXTRACTION_PROMPT_VERSION: str = "v1.2"

    # =========================================================================
    # CONFIGURATION DE L'API
    # =========================================================================
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    API_RELOAD: bool = False  # True uniquement en développement

    # Limitation de débit
    API_RATE_LIMIT_PER_MINUTE: int = 60

    # =========================================================================
    # CONFIGURATION D'OPENAI
    # =========================================================================
    OPENAI_API_KEY: str = Field(
        default="",
        description="Clé API OpenAI pour l'extraction GPT-4"
    )
    OPENAI_MODEL: str = "gpt-4o-2024-05-13"
    OPENAI_TEMPERATURE: float = 0.1  # Température basse pour une extraction déterministe
    OPENAI_MAX_TOKENS: int = 2000

    # =========================================================================
    # CONFIGURATION DU MODÈLE DE PLONGEMENTS
    # =========================================================================
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32

    # =========================================================================
    # VALIDATEURS
    # =========================================================================
    @field_validator("SOURCE_WEIGHTS")
    @classmethod
    def validate_source_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """S'assure que tous les poids des sources sont dans la plage valide [0.0, 1.0]."""
        for source, weight in v.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Le poids de la source pour '{source}' doit être entre 0.0 et 1.0, obtenu {weight}")
        return v

    @field_validator("METHOD_WEIGHTS")
    @classmethod
    def validate_method_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """S'assure que tous les poids des méthodes sont dans la plage valide [0.0, 1.0]."""
        for method, weight in v.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Le poids de la méthode pour '{method}' doit être entre 0.0 et 1.0, obtenu {weight}")
        return v

    @field_validator("MERGE_THRESHOLDS")
    @classmethod
    def validate_merge_thresholds(cls, v: Dict[str, float]) -> Dict[str, float]:
        """S'assure que tous les seuils de fusion sont dans la plage valide [0.0, 1.0]."""
        for entity_type, threshold in v.items():
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"Le seuil de fusion pour '{entity_type}' doit être entre 0.0 et 1.0, obtenu {threshold}")
        return v

    @field_validator("MAX_CONFIDENCE")
    @classmethod
    def validate_max_confidence(cls, v: float) -> float:
        """S'assure que la confiance maximale est inférieure à 1.0 (jamais 100% certain)."""
        if not 0.0 < v < 1.0:
            raise ValueError(f"MAX_CONFIDENCE doit être entre 0.0 et 1.0 (exclusif), obtenu {v}")
        return v


# Instance globale des paramètres
settings = Settings()
