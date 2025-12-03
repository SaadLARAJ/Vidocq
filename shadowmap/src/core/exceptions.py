class ShadowMapError(Exception):
    """Base exception for ShadowMap Enterprise."""
    pass

class IngestionError(ShadowMapError):
    """Base for ingestion related errors."""
    pass

class SourceUnreachableError(IngestionError):
    """Raised when a source cannot be reached after retries."""
    pass

class ParsingError(IngestionError):
    """Raised when content parsing fails."""
    pass

class StorageError(ShadowMapError):
    """Base for storage related errors."""
    pass

class DLQError(StorageError):
    """Raised when writing to DLQ fails."""
    pass

class ConfigurationError(ShadowMapError):
    """Raised when configuration is invalid."""
    pass
