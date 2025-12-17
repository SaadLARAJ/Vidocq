"""
VIDOCQ - Chain of Custody / Provenance Tracking
Full audit trail for every piece of intelligence.

"Track not just WHAT, but HOW it got here."

Features:
1. Complete pipeline trace
2. Transformation history
3. Source verification chain
4. Audit-ready export
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import hashlib
import uuid

from src.core.logging import get_logger

logger = get_logger(__name__)


class ProvenanceStep(str, Enum):
    """Types of provenance steps"""
    DISCOVERY = "DISCOVERY"           # Found the source
    INGESTION = "INGESTION"           # Downloaded/fetched content
    EXTRACTION = "EXTRACTION"         # LLM extracted entities/claims
    ENRICHMENT = "ENRICHMENT"         # Added external data
    VERIFICATION = "VERIFICATION"     # Cross-checked
    SCORING = "SCORING"               # Confidence scored
    HUMAN_REVIEW = "HUMAN_REVIEW"     # Human validated
    STORAGE = "STORAGE"               # Saved to database
    TRANSFORMATION = "TRANSFORMATION" # Modified/merged


class ProvenanceRecord(BaseModel):
    """Single step in the chain of custody"""
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_type: ProvenanceStep
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # What was processed
    input_hash: Optional[str] = None      # Hash of input data
    output_hash: Optional[str] = None     # Hash of output data
    
    # Processing details
    processor: str                         # Module/function that processed
    processor_version: str = "1.0"
    parameters: Dict[str, Any] = {}        # Parameters used
    
    # Context
    parent_context: Optional[str] = None   # Investigation context
    source_url: Optional[str] = None
    
    # Results
    items_in: int = 0                      # Items received
    items_out: int = 0                     # Items produced
    items_filtered: int = 0                # Items removed
    
    # Notes
    notes: Optional[str] = None
    warnings: List[str] = []


class ChainOfCustody(BaseModel):
    """Complete provenance chain for a piece of intelligence"""
    custody_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # What this chain is about
    subject: str                           # Entity or claim this tracks
    subject_type: str = "CLAIM"            # ENTITY, CLAIM, RELATION
    
    # The chain
    chain: List[ProvenanceRecord] = []
    
    # Final state
    current_hash: Optional[str] = None
    is_verified: bool = False
    verification_level: int = 0            # 0-5 scale
    
    # Audit metadata
    last_accessed: Optional[datetime] = None
    access_count: int = 0


class ProvenanceTracker:
    """
    Tracks full chain of custody for all intelligence.
    
    Every transformation, extraction, and modification is logged.
    Enables complete audit trail from raw source to final claim.
    """
    
    def __init__(self):
        self._chains: Dict[str, ChainOfCustody] = {}
    
    def start_chain(
        self,
        subject: str,
        subject_type: str = "CLAIM",
        source_url: Optional[str] = None,
        parent_context: Optional[str] = None
    ) -> ChainOfCustody:
        """
        Start a new chain of custody for a subject.
        """
        chain = ChainOfCustody(
            subject=subject,
            subject_type=subject_type
        )
        
        # Add discovery step
        discovery = ProvenanceRecord(
            step_type=ProvenanceStep.DISCOVERY,
            processor="ProvenanceTracker.start_chain",
            source_url=source_url,
            parent_context=parent_context,
            notes=f"Chain started for {subject_type}: {subject}"
        )
        
        chain.chain.append(discovery)
        self._chains[chain.custody_id] = chain
        
        logger.info(
            "provenance_chain_started",
            custody_id=chain.custody_id,
            subject=subject
        )
        
        return chain
    
    def add_step(
        self,
        custody_id: str,
        step_type: ProvenanceStep,
        processor: str,
        input_data: Any = None,
        output_data: Any = None,
        parameters: Dict[str, Any] = None,
        items_in: int = 0,
        items_out: int = 0,
        items_filtered: int = 0,
        notes: str = None,
        warnings: List[str] = None
    ) -> ProvenanceRecord:
        """
        Add a step to an existing chain.
        """
        chain = self._chains.get(custody_id)
        if not chain:
            raise ValueError(f"Chain {custody_id} not found")
        
        # Hash inputs/outputs for integrity
        input_hash = self._hash_data(input_data) if input_data else None
        output_hash = self._hash_data(output_data) if output_data else None
        
        record = ProvenanceRecord(
            step_type=step_type,
            processor=processor,
            input_hash=input_hash,
            output_hash=output_hash,
            parameters=parameters or {},
            items_in=items_in,
            items_out=items_out,
            items_filtered=items_filtered,
            notes=notes,
            warnings=warnings or []
        )
        
        chain.chain.append(record)
        chain.current_hash = output_hash
        
        logger.debug(
            "provenance_step_added",
            custody_id=custody_id,
            step=step_type.value,
            processor=processor
        )
        
        return record
    
    def mark_verified(
        self,
        custody_id: str,
        verifier: str,
        level: int = 1,
        notes: str = None
    ):
        """
        Mark a chain as human-verified.
        
        Verification levels:
        1 = Reviewed by analyst
        2 = Cross-checked with second source
        3 = Confirmed by subject matter expert
        4 = Validated by external authority
        5 = Legally verified (court, official record)
        """
        chain = self._chains.get(custody_id)
        if not chain:
            raise ValueError(f"Chain {custody_id} not found")
        
        # Add verification step
        self.add_step(
            custody_id=custody_id,
            step_type=ProvenanceStep.HUMAN_REVIEW,
            processor=verifier,
            notes=notes or f"Verified at level {level}",
            parameters={"verification_level": level}
        )
        
        chain.is_verified = True
        chain.verification_level = max(chain.verification_level, level)
        
        logger.info(
            "provenance_verified",
            custody_id=custody_id,
            level=level,
            verifier=verifier
        )
    
    def get_chain(self, custody_id: str) -> Optional[ChainOfCustody]:
        """Get a chain by ID."""
        chain = self._chains.get(custody_id)
        if chain:
            chain.last_accessed = datetime.now(timezone.utc)
            chain.access_count += 1
        return chain
    
    def export_for_audit(self, custody_id: str) -> Dict[str, Any]:
        """
        Export chain in audit-ready format.
        
        Returns a complete, human-readable audit trail.
        """
        chain = self.get_chain(custody_id)
        if not chain:
            return {"error": "Chain not found"}
        
        return {
            "custody_id": chain.custody_id,
            "subject": chain.subject,
            "subject_type": chain.subject_type,
            "created_at": chain.created_at.isoformat(),
            "is_verified": chain.is_verified,
            "verification_level": chain.verification_level,
            "total_steps": len(chain.chain),
            "current_integrity_hash": chain.current_hash,
            "audit_trail": [
                {
                    "step": i + 1,
                    "type": step.step_type.value,
                    "timestamp": step.timestamp.isoformat(),
                    "processor": step.processor,
                    "items_in": step.items_in,
                    "items_out": step.items_out,
                    "items_filtered": step.items_filtered,
                    "input_hash": step.input_hash,
                    "output_hash": step.output_hash,
                    "notes": step.notes,
                    "warnings": step.warnings
                }
                for i, step in enumerate(chain.chain)
            ]
        }
    
    def verify_integrity(self, custody_id: str) -> Dict[str, Any]:
        """
        Verify the integrity of a chain.
        
        Checks that hashes form a valid chain.
        """
        chain = self.get_chain(custody_id)
        if not chain:
            return {"valid": False, "error": "Chain not found"}
        
        issues = []
        
        # Check for gaps in chain
        for i, step in enumerate(chain.chain):
            if i > 0:
                prev = chain.chain[i - 1]
                # Output of previous should match input of current (if both exist)
                if prev.output_hash and step.input_hash:
                    if prev.output_hash != step.input_hash:
                        issues.append(f"Hash mismatch at step {i + 1}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "steps_checked": len(chain.chain),
            "verification_level": chain.verification_level
        }
    
    def _hash_data(self, data: Any) -> str:
        """Create a hash of data for integrity tracking."""
        if isinstance(data, str):
            content = data
        elif isinstance(data, dict):
            import json
            content = json.dumps(data, sort_keys=True, default=str)
        elif isinstance(data, list):
            import json
            content = json.dumps(data, sort_keys=True, default=str)
        else:
            content = str(data)
        
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# Singleton for global access
PROVENANCE = ProvenanceTracker()


def track_provenance(
    subject: str,
    step_type: ProvenanceStep,
    processor: str,
    **kwargs
) -> str:
    """
    Quick provenance tracking decorator/function.
    
    Returns custody_id for the chain.
    """
    # Check if there's an existing chain for this subject
    chain = PROVENANCE.start_chain(subject=subject, **kwargs)
    
    PROVENANCE.add_step(
        custody_id=chain.custody_id,
        step_type=step_type,
        processor=processor,
        **kwargs
    )
    
    return chain.custody_id
