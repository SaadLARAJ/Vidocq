"""
Watchlist system for continuous entity monitoring.
Enables automated periodic scanning and alerting on entity changes.
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__)


class AlertType(Enum):
    NEWS = "news"
    SANCTIONS = "sanctions"
    OWNERSHIP_CHANGE = "ownership_change"
    SCANDAL = "scandal"
    GEOPOLITICAL = "geopolitical"
    RISK_SCORE_CHANGE = "risk_score_change"


class ScanFrequency(Enum):
    REALTIME = "realtime"      # Every 15 minutes
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class WatchlistEntry:
    entity_name: str
    entity_type: str  # ORGANIZATION, PERSON, COUNTRY
    alert_types: List[str]
    frequency: str
    created_at: str
    last_scan: Optional[str] = None
    next_scan: Optional[str] = None
    status: str = "active"
    owner_id: str = "default"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass  
class Alert:
    alert_id: str
    entity_name: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    summary: str
    source: str
    source_url: Optional[str]
    detected_at: str
    acknowledged: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


class WatchlistManager:
    """Manages entity watchlist and generates alerts on changes."""
    
    def __init__(self):
        self._watchlist: Dict[str, WatchlistEntry] = {}
        self._alerts: List[Alert] = []
        self._entity_snapshots: Dict[str, Dict] = {}  # Previous state for comparison
        
        # Try to connect to Redis for persistence
        try:
            import redis
            self.redis = redis.from_url(settings.REDIS_URL)
            self.redis.ping()
            self._load_from_redis()
            logger.info("watchlist_redis_connected")
        except Exception as e:
            logger.warning("watchlist_redis_unavailable", error=str(e))
            self.redis = None
    
    def _entity_key(self, entity_name: str) -> str:
        return hashlib.md5(entity_name.lower().encode()).hexdigest()
    
    def _load_from_redis(self):
        """Load watchlist from Redis on startup."""
        if not self.redis:
            return
        try:
            data = self.redis.get("watchlist:entries")
            if data:
                entries = json.loads(data)
                for key, entry_data in entries.items():
                    self._watchlist[key] = WatchlistEntry(**entry_data)
            
            alerts_data = self.redis.get("watchlist:alerts")
            if alerts_data:
                alerts = json.loads(alerts_data)
                self._alerts = [Alert(**a) for a in alerts]
        except Exception as e:
            logger.error("watchlist_load_failed", error=str(e))
    
    def _save_to_redis(self):
        """Persist watchlist to Redis."""
        if not self.redis:
            return
        try:
            entries = {k: v.to_dict() for k, v in self._watchlist.items()}
            self.redis.set("watchlist:entries", json.dumps(entries))
            
            alerts = [a.to_dict() for a in self._alerts[-1000:]]  # Keep last 1000
            self.redis.set("watchlist:alerts", json.dumps(alerts))
        except Exception as e:
            logger.error("watchlist_save_failed", error=str(e))
    
    def add_entity(
        self,
        entity_name: str,
        entity_type: str = "ORGANIZATION",
        alert_types: List[str] = None,
        frequency: str = "daily",
        owner_id: str = "default"
    ) -> WatchlistEntry:
        """Add an entity to the watchlist."""
        if alert_types is None:
            alert_types = ["news", "sanctions", "ownership_change", "scandal"]
        
        now = datetime.utcnow()
        next_scan = self._calculate_next_scan(frequency, now)
        
        entry = WatchlistEntry(
            entity_name=entity_name,
            entity_type=entity_type,
            alert_types=alert_types,
            frequency=frequency,
            created_at=now.isoformat(),
            next_scan=next_scan.isoformat(),
            owner_id=owner_id
        )
        
        key = self._entity_key(entity_name)
        self._watchlist[key] = entry
        self._save_to_redis()
        
        logger.info("watchlist_entity_added", entity=entity_name, frequency=frequency)
        return entry
    
    def remove_entity(self, entity_name: str) -> bool:
        """Remove an entity from the watchlist."""
        key = self._entity_key(entity_name)
        if key in self._watchlist:
            del self._watchlist[key]
            self._save_to_redis()
            logger.info("watchlist_entity_removed", entity=entity_name)
            return True
        return False
    
    def get_watchlist(self, owner_id: str = None) -> List[WatchlistEntry]:
        """Get all watched entities, optionally filtered by owner."""
        entries = list(self._watchlist.values())
        if owner_id:
            entries = [e for e in entries if e.owner_id == owner_id]
        return entries
    
    def get_pending_scans(self) -> List[WatchlistEntry]:
        """Get entities that need to be scanned now."""
        now = datetime.utcnow()
        pending = []
        
        for entry in self._watchlist.values():
            if entry.status != "active":
                continue
            if entry.next_scan:
                next_scan = datetime.fromisoformat(entry.next_scan)
                if now >= next_scan:
                    pending.append(entry)
        
        return pending
    
    def record_scan(self, entity_name: str, new_state: Dict) -> List[Alert]:
        """Record a scan and detect changes from previous state."""
        key = self._entity_key(entity_name)
        entry = self._watchlist.get(key)
        
        if not entry:
            return []
        
        now = datetime.utcnow()
        alerts = []
        
        # Compare with previous snapshot
        previous_state = self._entity_snapshots.get(key, {})
        if previous_state:
            alerts = self._detect_changes(entry, previous_state, new_state)
        
        # Update state
        self._entity_snapshots[key] = new_state
        entry.last_scan = now.isoformat()
        entry.next_scan = self._calculate_next_scan(entry.frequency, now).isoformat()
        
        self._save_to_redis()
        
        return alerts
    
    def _detect_changes(
        self, 
        entry: WatchlistEntry, 
        old_state: Dict, 
        new_state: Dict
    ) -> List[Alert]:
        """Detect significant changes between states and generate alerts."""
        alerts = []
        now = datetime.utcnow()
        
        # Check for risk score change
        if "risk_score_change" in entry.alert_types:
            old_score = old_state.get("risk_score", 0)
            new_score = new_state.get("risk_score", 0)
            if abs(new_score - old_score) >= 15:
                severity = "HIGH" if new_score > old_score else "MEDIUM"
                alert = Alert(
                    alert_id=f"alert_{hashlib.md5(f'{entry.entity_name}{now}'.encode()).hexdigest()[:12]}",
                    entity_name=entry.entity_name,
                    alert_type="RISK_SCORE_CHANGE",
                    severity=severity,
                    summary=f"Risk score changed from {old_score:.1f} to {new_score:.1f}",
                    source="Vidocq Risk Scoring",
                    source_url=None,
                    detected_at=now.isoformat()
                )
                alerts.append(alert)
        
        # Check for new relations/owners
        if "ownership_change" in entry.alert_types:
            old_owners = set(old_state.get("owners", []))
            new_owners = set(new_state.get("owners", []))
            new_detected = new_owners - old_owners
            
            for owner in new_detected:
                alert = Alert(
                    alert_id=f"alert_{hashlib.md5(f'{entry.entity_name}{owner}{now}'.encode()).hexdigest()[:12]}",
                    entity_name=entry.entity_name,
                    alert_type="OWNERSHIP_CHANGE",
                    severity="HIGH",
                    summary=f"New beneficial owner detected: {owner}",
                    source="Vidocq Graph Analysis",
                    source_url=None,
                    detected_at=now.isoformat()
                )
                alerts.append(alert)
        
        # Check for new sanctions flags
        if "sanctions" in entry.alert_types:
            old_sanctions = old_state.get("sanctions_flags", [])
            new_sanctions = new_state.get("sanctions_flags", [])
            new_flags = set(new_sanctions) - set(old_sanctions)
            
            for flag in new_flags:
                alert = Alert(
                    alert_id=f"alert_{hashlib.md5(f'{entry.entity_name}{flag}{now}'.encode()).hexdigest()[:12]}",
                    entity_name=entry.entity_name,
                    alert_type="SANCTIONS",
                    severity="CRITICAL",
                    summary=f"Sanctions risk detected: {flag}",
                    source="Vidocq Sanctions Monitor",
                    source_url=None,
                    detected_at=now.isoformat()
                )
                alerts.append(alert)
        
        # Store alerts
        self._alerts.extend(alerts)
        self._save_to_redis()
        
        return alerts
    
    def _calculate_next_scan(self, frequency: str, from_time: datetime) -> datetime:
        """Calculate next scan time based on frequency."""
        if frequency == "realtime":
            return from_time + timedelta(minutes=15)
        elif frequency == "hourly":
            return from_time + timedelta(hours=1)
        elif frequency == "daily":
            return from_time + timedelta(days=1)
        elif frequency == "weekly":
            return from_time + timedelta(weeks=1)
        else:
            return from_time + timedelta(days=1)
    
    def get_alerts(
        self, 
        entity_name: str = None,
        unacknowledged_only: bool = False,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts, optionally filtered."""
        alerts = self._alerts.copy()
        
        if entity_name:
            alerts = [a for a in alerts if a.entity_name.lower() == entity_name.lower()]
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        # Sort by date descending
        alerts.sort(key=lambda x: x.detected_at, reverse=True)
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self._save_to_redis()
                return True
        return False
    
    def get_stats(self) -> Dict:
        """Get watchlist statistics."""
        entries = list(self._watchlist.values())
        return {
            "total_watched": len(entries),
            "by_type": {
                "ORGANIZATION": sum(1 for e in entries if e.entity_type == "ORGANIZATION"),
                "PERSON": sum(1 for e in entries if e.entity_type == "PERSON"),
                "COUNTRY": sum(1 for e in entries if e.entity_type == "COUNTRY")
            },
            "by_frequency": {
                "realtime": sum(1 for e in entries if e.frequency == "realtime"),
                "daily": sum(1 for e in entries if e.frequency == "daily"),
                "weekly": sum(1 for e in entries if e.frequency == "weekly")
            },
            "pending_scans": len(self.get_pending_scans()),
            "total_alerts": len(self._alerts),
            "unacknowledged_alerts": sum(1 for a in self._alerts if not a.acknowledged)
        }


# Singleton
_watchlist_instance = None


def get_watchlist_manager() -> WatchlistManager:
    """Get or create the watchlist manager singleton."""
    global _watchlist_instance
    if _watchlist_instance is None:
        _watchlist_instance = WatchlistManager()
    return _watchlist_instance
