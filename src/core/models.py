from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID, uuid4

# Import the single source of truth for ontology
from src.core.ontology import ALLOWED_ENTITY_TYPES, ALLOWED_RELATIONS

class SourceDocument(BaseModel):
    """Document source ingéré (Article, PDF, Tweet)."""
    id: UUID = Field(default_factory=uuid4)
    url: Optional[HttpUrl] = None
    raw_content: str
    cleaned_content: Optional[str] = None
    source_domain: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    reliability_score: float = Field(description="Calculé via SourceReliabilityRegistry")

class EntityNode(BaseModel):
    """Entité unique dans le graphe."""
    id: str = Field(description="UUID déterministe basé sur canonical_name + type")
    canonical_name: str
    # Use the imported list to define allowed types
    entity_type: Literal[*ALLOWED_ENTITY_TYPES]
    aliases: List[str] = []
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    vector_id: Optional[str] = Field(default=None, description="ID dans Qdrant")

class Claim(BaseModel):
    """
    Affirmation extraite avec provenance complète.
    Modèle de Réification — une relation est un OBJET, pas juste un trait.
    """
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    source_url: str
    subject_id: str
    # Use the imported list to define allowed relations
    relation_type: Literal[*ALLOWED_RELATIONS]
    object_id: str
    confidence_score: float = Field(description="Calculé via ConfidenceCalculator")
    evidence_snippet: str = Field(description="Extrait de texte prouvant le lien")
    extraction_model: str  # ex: "gpt-4o-2024-05-13"
    prompt_version: str    # ex: "v1.2"
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

class AmbiguousMatch(BaseModel):
    """Cas d'Entity Resolution ambigu pour review HITL."""
    id: UUID = Field(default_factory=uuid4)
    candidate_a_id: str
    candidate_b_id: str
    similarity_score: float
    evidence_context: List[str]  # Contextes où ils apparaissent
    status: Literal["PENDING", "MERGED", "REJECTED"] = "PENDING"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None

class DeadLetterEntry(BaseModel):
    """Tâche échouée stockée pour analyse."""
    id: UUID = Field(default_factory=uuid4)
    task_name: str
    payload: dict
    error_type: str
    error_message: str
    stack_trace: str
    retry_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
