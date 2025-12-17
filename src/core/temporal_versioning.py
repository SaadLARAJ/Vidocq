"""
VIDOCQ - Temporal Fact Versioning
Tracks fact evolution over time in Neo4j.

"Facts change. Track the evolution, not just the current state."

Features:
1. Version facts/relations with timestamps
2. Track changes over time
3. Query historical states
4. Detect fact flip-flops (potential manipulation)
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from src.core.logging import get_logger

logger = get_logger(__name__)


class FactStatus(str, Enum):
    """Status of a fact version"""
    ACTIVE = "ACTIVE"           # Current version
    SUPERSEDED = "SUPERSEDED"   # Replaced by newer version
    RETRACTED = "RETRACTED"     # Explicitly retracted
    CONTESTED = "CONTESTED"     # Under dispute


class FactVersion(BaseModel):
    """A versioned fact/relation"""
    fact_id: str
    version: int = 1
    
    # Core fact data
    subject: str
    relation: str
    object: str
    
    # Temporal data
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None  # None = still valid
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Provenance
    source_url: str
    source_date: Optional[datetime] = None
    confidence: float = 0.5
    
    # Status
    status: FactStatus = FactStatus.ACTIVE
    superseded_by: Optional[str] = None  # fact_id of newer version
    
    # Change tracking
    change_reason: Optional[str] = None  # Why this version differs


class TemporalFactStore:
    """
    Manages temporal versioning of facts in Neo4j.
    
    Schema additions:
    - Each Claim gets `valid_from`, `valid_until`, `version` properties
    - SUPERSEDES relationship links versions
    - FactHistory nodes track all changes
    """
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    async def store_fact_version(self, fact: FactVersion) -> str:
        """
        Store a new fact version.
        
        If a previous version exists for the same subject-relation-object,
        marks it as superseded.
        """
        query = """
        // Check for existing active fact
        OPTIONAL MATCH (existing:Claim {
            subject: $subject,
            relation: $relation,
            object: $object,
            status: 'ACTIVE'
        })
        
        // Create new version
        CREATE (new:Claim {
            fact_id: $fact_id,
            version: $version,
            subject: $subject,
            relation: $relation,
            object: $object,
            valid_from: datetime($valid_from),
            valid_until: CASE WHEN $valid_until IS NULL THEN null ELSE datetime($valid_until) END,
            recorded_at: datetime($recorded_at),
            source_url: $source_url,
            source_date: CASE WHEN $source_date IS NULL THEN null ELSE datetime($source_date) END,
            confidence: $confidence,
            status: $status
        })
        
        // If existing, create supersedes relationship
        FOREACH (e IN CASE WHEN existing IS NOT NULL THEN [existing] ELSE [] END |
            SET e.status = 'SUPERSEDED',
                e.superseded_by = $fact_id,
                e.valid_until = datetime($recorded_at)
            CREATE (new)-[:SUPERSEDES]->(e)
        )
        
        RETURN new.fact_id as fact_id
        """
        
        params = {
            "fact_id": fact.fact_id,
            "version": fact.version,
            "subject": fact.subject,
            "relation": fact.relation,
            "object": fact.object,
            "valid_from": fact.valid_from.isoformat(),
            "valid_until": fact.valid_until.isoformat() if fact.valid_until else None,
            "recorded_at": fact.recorded_at.isoformat(),
            "source_url": fact.source_url,
            "source_date": fact.source_date.isoformat() if fact.source_date else None,
            "confidence": fact.confidence,
            "status": fact.status.value
        }
        
        async with self.driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            
            logger.info(
                "fact_version_stored",
                fact_id=fact.fact_id,
                version=fact.version,
                subject=fact.subject
            )
            
            return record["fact_id"]
    
    async def get_fact_history(
        self,
        subject: str,
        relation: str,
        object: str
    ) -> List[FactVersion]:
        """
        Get complete history of a fact's evolution.
        
        Returns all versions in chronological order.
        """
        query = """
        MATCH (c:Claim {
            subject: $subject,
            relation: $relation,
            object: $object
        })
        RETURN c
        ORDER BY c.version ASC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "subject": subject,
                "relation": relation,
                "object": object
            })
            
            versions = []
            async for record in result:
                node = record["c"]
                versions.append(FactVersion(
                    fact_id=node["fact_id"],
                    version=node["version"],
                    subject=node["subject"],
                    relation=node["relation"],
                    object=node["object"],
                    valid_from=node["valid_from"],
                    valid_until=node.get("valid_until"),
                    recorded_at=node["recorded_at"],
                    source_url=node["source_url"],
                    confidence=node["confidence"],
                    status=FactStatus(node["status"])
                ))
            
            return versions
    
    async def get_fact_at_time(
        self,
        subject: str,
        relation: str,
        object: str,
        point_in_time: datetime
    ) -> Optional[FactVersion]:
        """
        Get the fact version that was active at a specific point in time.
        """
        query = """
        MATCH (c:Claim {
            subject: $subject,
            relation: $relation,
            object: $object
        })
        WHERE c.valid_from <= datetime($point_in_time)
          AND (c.valid_until IS NULL OR c.valid_until > datetime($point_in_time))
        RETURN c
        LIMIT 1
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "subject": subject,
                "relation": relation,
                "object": object,
                "point_in_time": point_in_time.isoformat()
            })
            
            record = await result.single()
            if record:
                node = record["c"]
                return FactVersion(
                    fact_id=node["fact_id"],
                    version=node["version"],
                    subject=node["subject"],
                    relation=node["relation"],
                    object=node["object"],
                    valid_from=node["valid_from"],
                    confidence=node["confidence"],
                    status=FactStatus(node["status"])
                )
            return None
    
    async def detect_flip_flops(
        self,
        subject: str,
        min_flips: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Detect facts that have changed multiple times (potential manipulation).
        
        Returns facts where the value has flipped back and forth.
        """
        query = """
        MATCH (c:Claim {subject: $subject})
        WITH c.relation as relation, c.object as object, 
             collect(c) as versions
        WHERE size(versions) >= $min_flips
        RETURN relation, object, size(versions) as change_count,
               [v in versions | {
                   version: v.version,
                   recorded_at: v.recorded_at,
                   status: v.status
               }] as history
        ORDER BY change_count DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "subject": subject,
                "min_flips": min_flips
            })
            
            flip_flops = []
            async for record in result:
                flip_flops.append({
                    "relation": record["relation"],
                    "object": record["object"],
                    "change_count": record["change_count"],
                    "history": record["history"],
                    "warning": "POTENTIAL MANIPULATION" if record["change_count"] >= 3 else "MONITOR"
                })
            
            if flip_flops:
                logger.warning(
                    "fact_flip_flops_detected",
                    subject=subject,
                    count=len(flip_flops)
                )
            
            return flip_flops
    
    async def retract_fact(
        self,
        fact_id: str,
        reason: str
    ) -> bool:
        """
        Retract a fact (mark as no longer valid).
        """
        query = """
        MATCH (c:Claim {fact_id: $fact_id})
        SET c.status = 'RETRACTED',
            c.valid_until = datetime(),
            c.retraction_reason = $reason
        RETURN c.fact_id as fact_id
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "fact_id": fact_id,
                "reason": reason
            })
            
            record = await result.single()
            if record:
                logger.info(
                    "fact_retracted",
                    fact_id=fact_id,
                    reason=reason
                )
                return True
            return False


def generate_fact_id(subject: str, relation: str, object: str, version: int = 1) -> str:
    """Generate a unique fact ID."""
    import hashlib
    content = f"{subject}::{relation}::{object}::v{version}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def create_fact_version(
    subject: str,
    relation: str,
    object: str,
    source_url: str,
    confidence: float = 0.5,
    source_date: Optional[datetime] = None,
    version: int = 1
) -> FactVersion:
    """
    Convenience function to create a fact version.
    """
    fact_id = generate_fact_id(subject, relation, object, version)
    
    return FactVersion(
        fact_id=fact_id,
        version=version,
        subject=subject,
        relation=relation,
        object=object,
        source_url=source_url,
        source_date=source_date,
        confidence=confidence
    )
