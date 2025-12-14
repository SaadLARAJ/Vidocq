"""
Cross-client alert system for anonymous risk sharing.
Enables Vidocq clients to benefit from collective intelligence.
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


@dataclass
class CrossClientFlag:
    """A risk flag shared anonymously across clients."""
    entity_hash: str          # Hashed entity name for privacy
    entity_name: str          # Original name (stored but not shared externally)
    flag_type: str            # Type of risk flag
    severity: str             # LOW, MEDIUM, HIGH, CRITICAL
    flagged_at: str
    flagged_by_hash: str      # Anonymous client identifier
    expiry: str               # When flag should be re-evaluated
    details: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_anonymous_dict(self) -> Dict:
        """Return dict without revealing who flagged."""
        return {
            "entity": self.entity_name,
            "flag_type": self.flag_type,
            "severity": self.severity,
            "flagged_at": self.flagged_at,
            "details": self.details,
            "message": "This entity was flagged by another Vidocq user"
        }


class CrossClientAlertSystem:
    """Anonymous risk sharing between Vidocq clients."""
    
    def __init__(self):
        self._flags: Dict[str, List[CrossClientFlag]] = {}  # entity_hash -> flags
        self._client_entities: Dict[str, Set[str]] = {}     # client_id -> entity_hashes they care about
        
        try:
            import redis
            self.redis = redis.from_url(settings.REDIS_URL)
            self.redis.ping()
            self._load_from_redis()
            logger.info("cross_client_alerts_connected")
        except Exception as e:
            logger.warning("cross_client_alerts_redis_unavailable", error=str(e))
            self.redis = None
    
    def _hash_entity(self, entity_name: str) -> str:
        return hashlib.sha256(entity_name.lower().strip().encode()).hexdigest()[:16]
    
    def _hash_client(self, client_id: str) -> str:
        return hashlib.sha256(client_id.encode()).hexdigest()[:12]
    
    def _load_from_redis(self):
        if not self.redis:
            return
        try:
            data = self.redis.get("crossclient:flags")
            if data:
                raw = json.loads(data)
                for entity_hash, flags_data in raw.items():
                    self._flags[entity_hash] = [CrossClientFlag(**f) for f in flags_data]
            
            entities_data = self.redis.get("crossclient:client_entities")
            if entities_data:
                raw = json.loads(entities_data)
                for client_id, entities in raw.items():
                    self._client_entities[client_id] = set(entities)
        except Exception as e:
            logger.error("crossclient_load_failed", error=str(e))
    
    def _save_to_redis(self):
        if not self.redis:
            return
        try:
            flags_data = {k: [f.to_dict() for f in v] for k, v in self._flags.items()}
            self.redis.set("crossclient:flags", json.dumps(flags_data))
            
            entities_data = {k: list(v) for k, v in self._client_entities.items()}
            self.redis.set("crossclient:client_entities", json.dumps(entities_data))
        except Exception as e:
            logger.error("crossclient_save_failed", error=str(e))
    
    def register_entity_interest(self, client_id: str, entity_name: str):
        """Register that a client cares about an entity (e.g., in their supply chain)."""
        entity_hash = self._hash_entity(entity_name)
        
        if client_id not in self._client_entities:
            self._client_entities[client_id] = set()
        
        self._client_entities[client_id].add(entity_hash)
        self._save_to_redis()
        
        logger.info("client_entity_registered", client=client_id[:8], entity_hash=entity_hash)
    
    def flag_entity(
        self,
        client_id: str,
        entity_name: str,
        flag_type: str,
        severity: str = "MEDIUM",
        details: str = "",
        expiry_days: int = 30
    ) -> CrossClientFlag:
        """Flag an entity as risky (shared anonymously with other clients)."""
        entity_hash = self._hash_entity(entity_name)
        client_hash = self._hash_client(client_id)
        now = datetime.utcnow()
        
        flag = CrossClientFlag(
            entity_hash=entity_hash,
            entity_name=entity_name,
            flag_type=flag_type,
            severity=severity,
            flagged_at=now.isoformat(),
            flagged_by_hash=client_hash,
            expiry=(now + timedelta(days=expiry_days)).isoformat(),
            details=details
        )
        
        if entity_hash not in self._flags:
            self._flags[entity_hash] = []
        
        self._flags[entity_hash].append(flag)
        self._save_to_redis()
        
        logger.info("entity_flagged", entity_hash=entity_hash, flag_type=flag_type, severity=severity)
        return flag
    
    def check_entity_flags(self, entity_name: str, exclude_client: str = None) -> List[Dict]:
        """Check if an entity has been flagged by other clients."""
        entity_hash = self._hash_entity(entity_name)
        
        if entity_hash not in self._flags:
            return []
        
        now = datetime.utcnow()
        exclude_client_hash = self._hash_client(exclude_client) if exclude_client else None
        
        active_flags = []
        for flag in self._flags[entity_hash]:
            # Skip expired flags
            if datetime.fromisoformat(flag.expiry) < now:
                continue
            # Skip flags from the same client
            if exclude_client_hash and flag.flagged_by_hash == exclude_client_hash:
                continue
            active_flags.append(flag.to_anonymous_dict())
        
        return active_flags
    
    def get_alerts_for_client(self, client_id: str) -> List[Dict]:
        """Get all active flags for entities a client cares about."""
        if client_id not in self._client_entities:
            return []
        
        alerts = []
        for entity_hash in self._client_entities[client_id]:
            if entity_hash in self._flags:
                for flag in self._flags[entity_hash]:
                    # Skip client's own flags
                    if flag.flagged_by_hash == self._hash_client(client_id):
                        continue
                    # Skip expired
                    if datetime.fromisoformat(flag.expiry) < datetime.utcnow():
                        continue
                    
                    alert = flag.to_anonymous_dict()
                    alert["in_your_network"] = True
                    alerts.append(alert)
        
        return alerts
    
    def get_stats(self) -> Dict:
        """Get cross-client alert system statistics."""
        total_flags = sum(len(f) for f in self._flags.values())
        unique_entities = len(self._flags)
        total_clients = len(self._client_entities)
        
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for flags in self._flags.values():
            for flag in flags:
                if flag.severity in severity_counts:
                    severity_counts[flag.severity] += 1
        
        return {
            "total_flags": total_flags,
            "unique_entities_flagged": unique_entities,
            "participating_clients": total_clients,
            "by_severity": severity_counts
        }


# Singleton
_alert_system_instance = None


def get_cross_client_alerts() -> CrossClientAlertSystem:
    """Get or create the cross-client alert system singleton."""
    global _alert_system_instance
    if _alert_system_instance is None:
        _alert_system_instance = CrossClientAlertSystem()
    return _alert_system_instance
