"""
Agent state management using Redis.
Tracks agent status, metrics, and action history.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent operational status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AgentMetrics:
    """Real-time metrics for the agent."""
    # Detection metrics
    anomalies_detected_total: int = 0
    anomalies_detected_last_hour: int = 0
    incidents_auto_created: int = 0
    detection_latency_p95_ms: float = 0.0
    false_positive_rate: float = 0.0

    # Legal intelligence metrics
    cpaca_classifications_total: int = 0
    cpaca_classification_accuracy: float = 0.0
    nullity_recommendations: int = 0
    evidence_packages_generated: int = 0
    deadline_alerts_sent: int = 0

    # Operational metrics
    uptime_seconds: int = 0
    actions_total: int = 0
    actions_last_hour: int = 0
    hitl_pending: int = 0
    hitl_escalation_rate: float = 0.0
    recommendation_acceptance_rate: float = 0.0

    # Briefing metrics
    briefings_generated: int = 0
    last_briefing_at: Optional[str] = None
    briefing_latency_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMetrics':
        """Create metrics from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ActionRecord:
    """Record of an agent action."""
    action_id: str
    action_type: str
    timestamp: str
    trigger_rule: str
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    hitl_required: bool = False
    hitl_status: Optional[str] = None  # pending, approved, rejected
    hitl_approved_by: Optional[str] = None
    hitl_approved_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionRecord':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HITLRequest:
    """Human-in-the-loop approval request."""
    request_id: str
    action_type: str
    created_at: str
    expires_at: str
    priority: str  # P0, P1, P2, P3
    title: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    recommended_action: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected, expired
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HITLRequest':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AgentState:
    """
    Manages agent state in Redis.
    Provides persistence and sharing across workers.
    """

    def __init__(self, redis_client=None):
        """
        Initialize agent state manager.

        Args:
            redis_client: Redis client instance (optional, uses in-memory if None)
        """
        self._redis = redis_client
        self._use_memory = redis_client is None

        # In-memory fallback storage
        self._memory_store: Dict[str, Any] = {}

        # Key prefixes
        self._state_key = "agent:state"
        self._metrics_key = "agent:metrics"
        self._actions_key = "agent:actions"
        self._hitl_key = "agent:hitl"
        self._briefings_key = "agent:briefings"

        logger.info(f"AgentState initialized (redis={'enabled' if redis_client else 'disabled'})")

    # ============================================================
    # Status Management
    # ============================================================

    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        data = self._get(self._state_key)
        if data:
            return AgentStatus(data.get('status', AgentStatus.STOPPED.value))
        return AgentStatus.STOPPED

    def set_status(self, status: AgentStatus) -> None:
        """Set agent status."""
        data = self._get(self._state_key) or {}
        data['status'] = status.value
        data['status_updated_at'] = datetime.utcnow().isoformat()
        self._set(self._state_key, data)
        logger.info(f"Agent status changed to: {status.value}")

    def get_started_at(self) -> Optional[datetime]:
        """Get agent start time."""
        data = self._get(self._state_key)
        if data and data.get('started_at'):
            return datetime.fromisoformat(data['started_at'])
        return None

    def set_started_at(self, timestamp: Optional[datetime] = None) -> None:
        """Set agent start time."""
        data = self._get(self._state_key) or {}
        data['started_at'] = (timestamp or datetime.utcnow()).isoformat()
        self._set(self._state_key, data)

    # ============================================================
    # Metrics Management
    # ============================================================

    def get_metrics(self) -> AgentMetrics:
        """Get current agent metrics."""
        data = self._get(self._metrics_key)
        if data:
            return AgentMetrics.from_dict(data)
        return AgentMetrics()

    def update_metrics(self, **kwargs) -> AgentMetrics:
        """Update specific metrics fields."""
        metrics = self.get_metrics()
        for key, value in kwargs.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)
        self._set(self._metrics_key, metrics.to_dict())
        return metrics

    def increment_metric(self, metric_name: str, amount: int = 1) -> int:
        """Increment a numeric metric."""
        metrics = self.get_metrics()
        if hasattr(metrics, metric_name):
            current = getattr(metrics, metric_name)
            new_value = current + amount
            setattr(metrics, metric_name, new_value)
            self._set(self._metrics_key, metrics.to_dict())
            return new_value
        return 0

    def update_uptime(self) -> int:
        """Update uptime based on started_at."""
        started_at = self.get_started_at()
        if started_at and self.get_status() == AgentStatus.RUNNING:
            uptime = int((datetime.utcnow() - started_at).total_seconds())
            self.update_metrics(uptime_seconds=uptime)
            return uptime
        return 0

    # ============================================================
    # Action History
    # ============================================================

    def record_action(self, action: ActionRecord) -> None:
        """Record an agent action."""
        actions = self._get_list(self._actions_key)
        actions.append(action.to_dict())

        # Keep only last 1000 actions
        if len(actions) > 1000:
            actions = actions[-1000:]

        self._set_list(self._actions_key, actions)
        self.increment_metric('actions_total')
        logger.debug(f"Recorded action: {action.action_type}")

    def get_recent_actions(self, limit: int = 50) -> List[ActionRecord]:
        """Get recent actions."""
        actions = self._get_list(self._actions_key)
        return [ActionRecord.from_dict(a) for a in actions[-limit:]]

    def get_actions_since(self, since: datetime) -> List[ActionRecord]:
        """Get actions since a given time."""
        actions = self._get_list(self._actions_key)
        since_iso = since.isoformat()
        return [
            ActionRecord.from_dict(a)
            for a in actions
            if a.get('timestamp', '') >= since_iso
        ]

    # ============================================================
    # HITL Queue Management
    # ============================================================

    def add_hitl_request(self, request: HITLRequest) -> None:
        """Add a HITL approval request."""
        requests = self._get_list(self._hitl_key)
        requests.append(request.to_dict())
        self._set_list(self._hitl_key, requests)
        self.increment_metric('hitl_pending')
        logger.info(f"Added HITL request: {request.request_id}")

    def get_pending_hitl_requests(self) -> List[HITLRequest]:
        """Get all pending HITL requests."""
        requests = self._get_list(self._hitl_key)
        return [
            HITLRequest.from_dict(r)
            for r in requests
            if r.get('status') == 'pending'
        ]

    def get_hitl_request(self, request_id: str) -> Optional[HITLRequest]:
        """Get a specific HITL request by ID."""
        requests = self._get_list(self._hitl_key)
        for r in requests:
            if r.get('request_id') == request_id:
                return HITLRequest.from_dict(r)
        return None

    def update_hitl_request(
        self,
        request_id: str,
        status: str,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> Optional[HITLRequest]:
        """Update a HITL request status."""
        requests = self._get_list(self._hitl_key)
        for i, r in enumerate(requests):
            if r.get('request_id') == request_id:
                r['status'] = status
                r['reviewed_by'] = reviewed_by
                r['reviewed_at'] = datetime.utcnow().isoformat()
                r['review_notes'] = notes
                requests[i] = r
                self._set_list(self._hitl_key, requests)

                if status in ('approved', 'rejected'):
                    self.increment_metric('hitl_pending', -1)

                logger.info(f"HITL request {request_id} {status} by {reviewed_by}")
                return HITLRequest.from_dict(r)
        return None

    # ============================================================
    # Briefings
    # ============================================================

    def store_briefing(self, briefing: Dict[str, Any]) -> None:
        """Store a generated briefing."""
        briefings = self._get_list(self._briefings_key)
        briefing['stored_at'] = datetime.utcnow().isoformat()
        briefings.append(briefing)

        # Keep only last 100 briefings
        if len(briefings) > 100:
            briefings = briefings[-100:]

        self._set_list(self._briefings_key, briefings)
        self.update_metrics(
            briefings_generated=len(briefings),
            last_briefing_at=briefing['stored_at']
        )

    def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        """Get the most recent briefing."""
        briefings = self._get_list(self._briefings_key)
        if briefings:
            return briefings[-1]
        return None

    def get_briefings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent briefings."""
        briefings = self._get_list(self._briefings_key)
        return briefings[-limit:]

    # ============================================================
    # Internal Storage Methods
    # ============================================================

    def _get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from storage."""
        if self._use_memory:
            return self._memory_store.get(key)
        try:
            data = self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get error for {key}: {e}")
        return None

    def _set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set value in storage."""
        if self._use_memory:
            self._memory_store[key] = value
            return
        try:
            data = json.dumps(value)
            if ttl:
                self._redis.setex(key, ttl, data)
            else:
                self._redis.set(key, data)
        except Exception as e:
            logger.error(f"Redis set error for {key}: {e}")

    def _get_list(self, key: str) -> List[Dict[str, Any]]:
        """Get list from storage."""
        data = self._get(key)
        if data and isinstance(data, list):
            return data
        return []

    def _set_list(self, key: str, value: List[Dict[str, Any]]) -> None:
        """Set list in storage."""
        self._set(key, value)

    def clear(self) -> None:
        """Clear all agent state."""
        keys = [
            self._state_key,
            self._metrics_key,
            self._actions_key,
            self._hitl_key,
            self._briefings_key
        ]
        if self._use_memory:
            for key in keys:
                self._memory_store.pop(key, None)
        else:
            for key in keys:
                try:
                    self._redis.delete(key)
                except Exception as e:
                    logger.error(f"Redis delete error for {key}: {e}")
        logger.info("Agent state cleared")
