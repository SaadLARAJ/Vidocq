"""
ShadowMap Entreprise v4.0 - Exceptions personnalisées

Exceptions spécifiques au domaine pour une gestion et une journalisation précises des erreurs.
Toutes les exceptions incluent un contexte pour la journalisation structurée et le débogage.
"""

from typing import Any, Optional


class ShadowMapException(Exception):
    """
    Exception de base pour toutes les erreurs spécifiques à ShadowMap.

    Toutes les exceptions personnalisées en héritent pour une capture facile
    et une gestion unifiée des erreurs.
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialise l'exception avec un message et un contexte optionnel.

        Args:
            message: Message d'erreur lisible par l'homme.
            context: Contexte supplémentaire pour la journalisation/le débogage.
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Représentation en chaîne de caractères avec le contexte."""
        if self.context:
            return f"{self.message} | Contexte: {self.context}"
        return self.message


# =============================================================================
# ERREURS DE CONFIGURATION
# =============================================================================

class ConfigurationError(ShadowMapException):
    """Levée lorsque la configuration est invalide ou manquante."""
    pass


class MissingCredentialError(ConfigurationError):
    """Levée lorsque les informations d'identification requises (clés API, mots de passe) sont manquantes."""
    pass


# =============================================================================
# ERREURS DE VALIDATION DES DONNÉES
# =============================================================================

class ValidationError(ShadowMapException):
    """Levée lorsque la validation des données échoue."""
    pass


class InvalidEntityTypeError(ValidationError):
    """Levée lorsque le type d'entité n'est pas dans ALLOWED_ENTITY_TYPES."""
    pass


class InvalidRelationTypeError(ValidationError):
    """Levée lorsque le type de relation n'est pas dans ALLOWED_RELATIONS."""
    pass


class OntologyViolationError(ValidationError):
    """
    Levée lorsqu'une relation viole les contraintes de type.

    Exemple : EMPLOYS(PERSON, ORGANIZATION) est invalide.
    Forme valide : EMPLOYS(ORGANIZATION, PERSON)
    """
    pass


# =============================================================================
# ERREURS DE STOCKAGE
# =============================================================================

class StorageError(ShadowMapException):
    """Classe de base pour les erreurs liées au stockage."""
    pass


class Neo4jConnectionError(StorageError):
    """Levée lorsque la connexion à Neo4j échoue."""
    pass


class PostgresConnectionError(StorageError):
    """Levée lorsque la connexion à PostgreSQL échoue."""
    pass


class RedisConnectionError(StorageError):
    """Levée lorsque la connexion à Redis échoue."""
    pass


class QdrantConnectionError(StorageError):
    """Levée lorsque la connexion à Qdrant échoue."""
    pass


class TransactionError(StorageError):
    """Levée lorsqu'une transaction de base de données échoue."""
    pass


# =============================================================================
# ERREURS D'EXTRACTION
# =============================================================================

class ExtractionError(ShadowMapException):
    """Classe de base pour les erreurs liées à l'extraction."""
    pass


class ParsingError(ExtractionError):
    """Levée lorsque l'analyse du document échoue."""
    pass


class LLMExtractionError(ExtractionError):
    """Levée lorsque l'extraction par le LLM échoue ou renvoie des données invalides."""
    pass


class EmbeddingError(ExtractionError):
    """Levée lorsque la génération de plongements de texte échoue."""
    pass


# =============================================================================
# ERREURS DE RÉSOLUTION D'ENTITÉS
# =============================================================================

class ResolutionError(ShadowMapException):
    """Classe de base pour les erreurs de résolution d'entités."""
    pass


class SimilarityCalculationError(ResolutionError):
    """Levée lorsque le calcul de similarité échoue."""
    pass


class MergeConflictError(ResolutionError):
    """Levée lorsque la fusion d'entités crée des conflits."""
    pass


# =============================================================================
# ERREURS D'INGESTION
# =============================================================================

class IngestionError(ShadowMapException):
    """Classe de base pour les erreurs liées à l'ingestion."""
    pass


class SourceUnreachableError(IngestionError):
    """Levée lorsque l'URL de la source ne peut pas être récupérée."""
    pass


class RateLimitExceededError(IngestionError):
    """Levée lorsque la limite de débit est atteinte."""
    pass


class DocumentTooLargeError(IngestionError):
    """Levée lorsque le document dépasse MAX_DOCUMENT_SIZE."""
    pass


class UnsupportedFormatError(IngestionError):
    """Levée lorsque le format du document n'est pas pris en charge."""
    pass


# =============================================================================
# ERREURS DE TÂCHE
# =============================================================================

class TaskError(ShadowMapException):
    """Classe de base pour les erreurs de tâches Celery."""
    pass


class TaskRetryExhaustedError(TaskError):
    """Levée lorsqu'une tâche épuise toutes les tentatives et va dans la DLQ."""
    pass


class TaskTimeoutError(TaskError):
    """Levée lorsqu'une tâche dépasse la limite de temps."""
    pass


# =============================================================================
# ERREURS D'API
# =============================================================================

class APIError(ShadowMapException):
    """Classe de base pour les erreurs liées à l'API."""
    pass


class AuthenticationError(APIError):
    """Levée lorsque l'authentification de l'API échoue."""
    pass


class AuthorizationError(APIError):
    """Levée lorsque l'utilisateur n'a pas la permission pour l'opération."""
    pass


class ResourceNotFoundError(APIError):
    """Levée lorsque la ressource demandée n'existe pas."""
    pass


class InvalidRequestError(APIError):
    """Levée lorsque la requête API est malformée."""
    pass
