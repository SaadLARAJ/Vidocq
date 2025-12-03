"""
ShadowMap Enterprise v4.0 - Data Models

All data models use Pydantic v2 for strict validation and serialization.
Every model includes complete type hints and field descriptions.

Models follow the Reification Pattern - relations are first-class objects
with their own properties (confidence, provenance, timestamps).
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceDocument(BaseModel):
    """
    Source document ingested into the system.

    Represents any raw input: news articles, PDFs, tweets, reports, etc.
    Each document receives a reliability score based on its source domain.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this source document"
    )
    url: Optional[HttpUrl] = Field(
        default=None,
        description="Original URL if available (None for uploaded files)"
    )
    raw_content: str = Field(
        description="Original unprocessed content (HTML, markdown, plain text)"
    )
    cleaned_content: Optional[str] = Field(
        default=None,
        description="Cleaned content after HTML stripping and normalization"
    )
    source_domain: str = Field(
        description="Domain of the source (e.g., 'reuters.com', 'telegram')"
    )
    document_type: Literal["article", "pdf", "tweet", "telegram_post", "report"] = Field(
        default="article",
        description="Type of source document"
    )
    ingested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when document was ingested"
    )
    reliability_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Source reliability score from SourceReliabilityRegistry"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata (author, publish_date, tags, etc.)"
    )

    @field_validator("source_domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """Normalize domain to lowercase for consistent lookups."""
        return v.lower().strip()


class EntityNode(BaseModel):
    """
    Entity node in the knowledge graph.

    Represents a unique real-world entity (person, organization, location, etc.)
    after entity resolution. Multiple mentions are deduplicated into one canonical entity.
    """

    id: str = Field(
        description="Deterministic UUID based on canonical_name + entity_type hash"
    )
    canonical_name: str = Field(
        description="Canonical (preferred) name for this entity"
    )
    entity_type: Literal[
        "PERSON",
        "ORGANIZATION",
        "LOCATION",
        "EVENT",
        "CRYPTO_WALLET",
        "DOCUMENT"
    ] = Field(
        description="Type of entity from closed ontology"
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names and spellings for this entity"
    )
    first_seen: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when entity was first extracted"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last update to this entity"
    )
    vector_id: Optional[str] = Field(
        default=None,
        description="ID in Qdrant vector database for similarity search"
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Additional attributes (nationality, industry, coordinates, etc.)"
    )

    @field_validator("canonical_name")
    @classmethod
    def validate_canonical_name(cls, v: str) -> str:
        """Ensure canonical name is not empty."""
        if not v or not v.strip():
            raise ValueError("canonical_name cannot be empty")
        return v.strip()


class Claim(BaseModel):
    """
    A claim representing a relationship between two entities.

    Implements the Reification Pattern: relationships are objects, not just edges.
    Each claim carries full provenance, confidence scoring, and audit metadata.

    This is the core unit of knowledge in ShadowMap - every fact is traceable
    back to its source and extraction method.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this claim"
    )
    source_id: UUID = Field(
        description="ID of the SourceDocument this claim was extracted from"
    )
    source_url: str = Field(
        description="URL of the source document for audit trail"
    )
    subject_id: str = Field(
        description="Entity ID of the subject (source of the relationship)"
    )
    relation_type: str = Field(
        description="Type of relationship (must be in ALLOWED_RELATIONS)"
    )
    object_id: str = Field(
        description="Entity ID of the object (target of the relationship)"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score calculated via ConfidenceCalculator"
    )
    evidence_snippet: str = Field(
        description="Text snippet from source that supports this claim"
    )
    extraction_model: str = Field(
        description="Model/method used for extraction (e.g., 'gpt-4o-2024-05-13')"
    )
    prompt_version: str = Field(
        description="Version of the extraction prompt (e.g., 'v1.2')"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when claim was extracted"
    )
    corroboration_count: int = Field(
        default=1,
        ge=1,
        description="Number of independent sources corroborating this claim"
    )
    status: Literal["pending_review", "verified", "disputed", "archived"] = Field(
        default="pending_review",
        description="Review status of this claim"
    )

    @field_validator("evidence_snippet")
    @classmethod
    def validate_evidence(cls, v: str) -> str:
        """Ensure evidence snippet is not empty."""
        if not v or not v.strip():
            raise ValueError("evidence_snippet cannot be empty")
        return v.strip()


class AmbiguousMatch(BaseModel):
    """
    Ambiguous entity resolution case requiring Human-In-The-Loop (HITL) review.

    When two entities have similarity scores in the ambiguous range
    (HITL_MINIMUM_SCORE <= score < MERGE_THRESHOLD), they are queued
    for manual analyst review.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this ambiguous match"
    )
    candidate_a_id: str = Field(
        description="Entity ID of first candidate"
    )
    candidate_b_id: str = Field(
        description="Entity ID of second candidate"
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Computed similarity score between candidates"
    )
    evidence_context: list[str] = Field(
        default_factory=list,
        description="Context snippets where each entity appears"
    )
    entity_type: str = Field(
        description="Type of entities being compared"
    )
    status: Literal["PENDING", "MERGED", "REJECTED"] = Field(
        default="PENDING",
        description="Resolution status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when match was identified"
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when analyst reviewed this match"
    )
    reviewed_by: Optional[str] = Field(
        default=None,
        description="Analyst ID who reviewed this match"
    )
    review_notes: Optional[str] = Field(
        default=None,
        description="Notes from analyst review"
    )

    @field_validator("similarity_score")
    @classmethod
    def validate_similarity(cls, v: float) -> float:
        """Ensure similarity score is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"similarity_score must be between 0.0 and 1.0, got {v}")
        return v


class DeadLetterEntry(BaseModel):
    """
    Failed task stored in Dead Letter Queue (DLQ).

    Any task that fails after MAX_RETRIES attempts is stored here for
    manual investigation. NOTHING DISAPPEARS - all failures are auditable.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this DLQ entry"
    )
    task_name: str = Field(
        description="Name of the failed Celery task"
    )
    task_id: str = Field(
        description="Celery task ID for correlation"
    )
    payload: dict = Field(
        description="Original task payload (arguments)"
    )
    error_type: str = Field(
        description="Exception class name (e.g., 'ConnectionError')"
    )
    error_message: str = Field(
        description="Human-readable error message"
    )
    stack_trace: str = Field(
        description="Full stack trace for debugging"
    )
    retry_count: int = Field(
        ge=0,
        description="Number of retry attempts before DLQ"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when task first failed"
    )
    last_retry_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last retry attempt"
    )
    manually_resolved: bool = Field(
        default=False,
        description="Whether this was manually resolved by an operator"
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        description="Notes on how this failure was resolved"
    )


class ExtractionResult(BaseModel):
    """
    Result of entity/relation extraction from a document chunk.

    Returned by the extraction pipeline before storage in the graph.
    """

    entities: list[EntityNode] = Field(
        default_factory=list,
        description="Entities extracted from the chunk"
    )
    claims: list[Claim] = Field(
        default_factory=list,
        description="Claims (relations) extracted from the chunk"
    )
    extraction_metadata: dict[str, str | float | int] = Field(
        default_factory=dict,
        description="Metadata about the extraction (model, latency, token count, etc.)"
    )


class ResolutionDecision(BaseModel):
    """
    Entity resolution decision record.

    Tracks all entity merge/reject decisions for audit and model training.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this decision"
    )
    entity_a_id: str = Field(
        description="First entity ID in comparison"
    )
    entity_b_id: str = Field(
        description="Second entity ID in comparison"
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Computed similarity score"
    )
    decision: Literal["auto_merged", "manual_merged", "rejected", "pending"] = Field(
        description="Resolution decision"
    )
    decided_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of decision"
    )
    decided_by: Literal["system", "analyst"] = Field(
        description="Who made the decision"
    )
    analyst_id: Optional[str] = Field(
        default=None,
        description="ID of analyst if manual decision"
    )
