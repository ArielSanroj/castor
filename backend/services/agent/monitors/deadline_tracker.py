"""
Deadline Tracker.
Tracks legal deadlines for CPACA articles and electoral processes.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class DeadlineType(str, Enum):
    """Types of legal deadlines."""
    ART_223 = "ART_223"  # 48 hours for electoral irregularities
    ART_224 = "ART_224"  # Nullity request
    ART_225 = "ART_225"  # Recounting request
    ART_226 = "ART_226"  # Appeals
    RECOUNT = "RECOUNT"  # General recount deadline (5 days)
    NULLITY = "NULLITY"  # General nullity deadline (30 days)
    EVIDENCE = "EVIDENCE"  # Evidence submission deadline


@dataclass
class TrackedDeadline:
    """A deadline being tracked."""
    deadline_id: str
    deadline_type: DeadlineType
    incident_id: Optional[int]
    mesa_id: Optional[str]
    cpaca_article: Optional[int]
    created_at: datetime
    deadline: datetime
    description: str
    status: str = "active"  # active, warned, expired, completed
    last_warning_at: Optional[datetime] = None
    warning_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['deadline_type'] = self.deadline_type.value
        data['created_at'] = self.created_at.isoformat()
        data['deadline'] = self.deadline.isoformat()
        if self.last_warning_at:
            data['last_warning_at'] = self.last_warning_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackedDeadline':
        """Create from dictionary."""
        data['deadline_type'] = DeadlineType(data['deadline_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['deadline'] = datetime.fromisoformat(data['deadline'])
        if data.get('last_warning_at'):
            data['last_warning_at'] = datetime.fromisoformat(data['last_warning_at'])
        return cls(**data)


# Standard deadline durations
DEADLINE_DURATIONS = {
    DeadlineType.ART_223: timedelta(hours=48),
    DeadlineType.ART_224: timedelta(days=30),
    DeadlineType.ART_225: timedelta(days=5),
    DeadlineType.ART_226: timedelta(days=10),
    DeadlineType.RECOUNT: timedelta(days=5),
    DeadlineType.NULLITY: timedelta(days=30),
    DeadlineType.EVIDENCE: timedelta(days=3),
}


class DeadlineTracker:
    """
    Tracks legal deadlines and sends warnings.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        on_deadline_warning: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_deadline_expired: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the deadline tracker.

        Args:
            config: Agent configuration
            on_deadline_warning: Callback when deadline warning is triggered
            on_deadline_expired: Callback when deadline expires
        """
        self.config = config or get_agent_config()
        self._on_warning = on_deadline_warning
        self._on_expired = on_deadline_expired
        self._deadlines: Dict[str, TrackedDeadline] = {}
        self._last_poll_time: Optional[datetime] = None
        self._deadline_counter = 0

        logger.info("DeadlineTracker initialized")

    def add_deadline(
        self,
        deadline_type: DeadlineType,
        incident_id: Optional[int] = None,
        mesa_id: Optional[str] = None,
        cpaca_article: Optional[int] = None,
        description: str = "",
        custom_deadline: Optional[datetime] = None
    ) -> TrackedDeadline:
        """
        Add a new deadline to track.

        Args:
            deadline_type: Type of deadline
            incident_id: Related incident ID
            mesa_id: Related mesa ID
            cpaca_article: CPACA article number
            description: Description of the deadline
            custom_deadline: Custom deadline time (uses standard if None)

        Returns:
            Created TrackedDeadline
        """
        self._deadline_counter += 1
        deadline_id = f"DL-{self._deadline_counter:06d}"

        now = datetime.utcnow()
        if custom_deadline:
            deadline = custom_deadline
        else:
            duration = DEADLINE_DURATIONS.get(deadline_type, timedelta(days=7))
            deadline = now + duration

        tracked = TrackedDeadline(
            deadline_id=deadline_id,
            deadline_type=deadline_type,
            incident_id=incident_id,
            mesa_id=mesa_id,
            cpaca_article=cpaca_article,
            created_at=now,
            deadline=deadline,
            description=description or f"Deadline for {deadline_type.value}",
        )

        self._deadlines[deadline_id] = tracked
        logger.info(f"Added deadline {deadline_id}: {deadline_type.value} expires {deadline.isoformat()}")

        return tracked

    def add_cpaca_deadline(
        self,
        article: int,
        incident_id: Optional[int] = None,
        mesa_id: Optional[str] = None,
        description: str = ""
    ) -> TrackedDeadline:
        """
        Add a CPACA article deadline.

        Args:
            article: CPACA article number (223, 224, 225, 226)
            incident_id: Related incident ID
            mesa_id: Related mesa ID
            description: Description

        Returns:
            Created TrackedDeadline
        """
        article_map = {
            223: DeadlineType.ART_223,
            224: DeadlineType.ART_224,
            225: DeadlineType.ART_225,
            226: DeadlineType.ART_226,
        }

        deadline_type = article_map.get(article, DeadlineType.ART_223)

        return self.add_deadline(
            deadline_type=deadline_type,
            incident_id=incident_id,
            mesa_id=mesa_id,
            cpaca_article=article,
            description=description or f"Plazo Art. {article} CPACA",
        )

    async def poll(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Check all deadlines for warnings or expirations.

        Returns:
            Dictionary with 'warnings' and 'expirations' lists
        """
        self._last_poll_time = datetime.utcnow()
        results = {
            'warnings': [],
            'expirations': [],
        }

        now = datetime.utcnow()

        for deadline in list(self._deadlines.values()):
            if deadline.status not in ('active', 'warned'):
                continue

            # Check if expired
            if now >= deadline.deadline:
                expiration = self._handle_expiration(deadline)
                results['expirations'].append(expiration)
                continue

            # Check if warning needed
            warning = self._check_warning(deadline, now)
            if warning:
                results['warnings'].append(warning)

        logger.debug(
            f"DeadlineTracker poll: {len(self._deadlines)} deadlines, "
            f"{len(results['warnings'])} warnings, {len(results['expirations'])} expirations"
        )

        return results

    def _check_warning(self, deadline: TrackedDeadline, now: datetime) -> Optional[Dict[str, Any]]:
        """Check if warning should be issued for deadline."""
        remaining = deadline.deadline - now
        hours_remaining = remaining.total_seconds() / 3600
        days_remaining = remaining.days

        # Determine warning threshold based on type
        should_warn = False
        urgency = 'low'

        if deadline.deadline_type in (DeadlineType.ART_223,):
            # 48-hour deadline: warn at 12 hours
            if hours_remaining < self.config.ART_223_WARNING_HOURS:
                should_warn = True
                urgency = 'critical' if hours_remaining < 6 else 'high'
        elif deadline.deadline_type in (DeadlineType.ART_225, DeadlineType.RECOUNT):
            # 5-day deadline: warn at 2 days
            if days_remaining < self.config.RECOUNT_WARNING_DAYS:
                should_warn = True
                urgency = 'high' if days_remaining < 1 else 'medium'
        elif deadline.deadline_type in (DeadlineType.ART_224, DeadlineType.NULLITY):
            # 30-day deadline: warn at 7 days
            if days_remaining < self.config.NULLITY_WARNING_DAYS:
                should_warn = True
                urgency = 'high' if days_remaining < 3 else 'medium'
        else:
            # Default: warn at 1 day
            if days_remaining < 1:
                should_warn = True
                urgency = 'medium'

        if not should_warn:
            return None

        # Avoid duplicate warnings (min 1 hour between warnings)
        if deadline.last_warning_at:
            since_last = (now - deadline.last_warning_at).total_seconds() / 3600
            if since_last < 1:
                return None

        # Update deadline state
        deadline.status = 'warned'
        deadline.last_warning_at = now
        deadline.warning_count += 1

        warning = {
            'deadline_id': deadline.deadline_id,
            'deadline_type': deadline.deadline_type.value,
            'incident_id': deadline.incident_id,
            'mesa_id': deadline.mesa_id,
            'cpaca_article': deadline.cpaca_article,
            'hours_remaining': hours_remaining,
            'days_remaining': days_remaining,
            'urgency': urgency,
            'description': deadline.description,
            'deadline': deadline.deadline.isoformat(),
            'warning_count': deadline.warning_count,
            'detected_at': now.isoformat(),
        }

        if self._on_warning:
            self._on_warning(warning)

        return warning

    def _handle_expiration(self, deadline: TrackedDeadline) -> Dict[str, Any]:
        """Handle an expired deadline."""
        deadline.status = 'expired'

        expiration = {
            'deadline_id': deadline.deadline_id,
            'deadline_type': deadline.deadline_type.value,
            'incident_id': deadline.incident_id,
            'mesa_id': deadline.mesa_id,
            'cpaca_article': deadline.cpaca_article,
            'description': deadline.description,
            'deadline': deadline.deadline.isoformat(),
            'expired_at': datetime.utcnow().isoformat(),
        }

        if self._on_expired:
            self._on_expired(expiration)

        logger.warning(f"Deadline expired: {deadline.deadline_id} ({deadline.deadline_type.value})")

        return expiration

    def complete_deadline(self, deadline_id: str) -> bool:
        """
        Mark a deadline as completed.

        Args:
            deadline_id: Deadline ID

        Returns:
            True if found and completed
        """
        if deadline_id in self._deadlines:
            self._deadlines[deadline_id].status = 'completed'
            logger.info(f"Deadline completed: {deadline_id}")
            return True
        return False

    def get_deadline(self, deadline_id: str) -> Optional[TrackedDeadline]:
        """Get a deadline by ID."""
        return self._deadlines.get(deadline_id)

    def get_active_deadlines(self) -> List[TrackedDeadline]:
        """Get all active deadlines."""
        return [d for d in self._deadlines.values() if d.status in ('active', 'warned')]

    def get_deadlines_for_incident(self, incident_id: int) -> List[TrackedDeadline]:
        """Get all deadlines for an incident."""
        return [d for d in self._deadlines.values() if d.incident_id == incident_id]

    def cleanup_old_deadlines(self, max_age_days: int = 30) -> int:
        """
        Remove old completed/expired deadlines.

        Args:
            max_age_days: Maximum age of deadlines to keep

        Returns:
            Number of deadlines removed
        """
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        old_count = len(self._deadlines)

        self._deadlines = {
            k: v for k, v in self._deadlines.items()
            if v.status in ('active', 'warned') or v.deadline > cutoff
        }

        removed = old_count - len(self._deadlines)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old deadlines")

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        by_status = {'active': 0, 'warned': 0, 'expired': 0, 'completed': 0}
        by_type = {}

        for deadline in self._deadlines.values():
            by_status[deadline.status] = by_status.get(deadline.status, 0) + 1
            by_type[deadline.deadline_type.value] = by_type.get(deadline.deadline_type.value, 0) + 1

        return {
            'last_poll_time': self._last_poll_time.isoformat() if self._last_poll_time else None,
            'total_deadlines': len(self._deadlines),
            'by_status': by_status,
            'by_type': by_type,
            'poll_interval_seconds': self.config.DEADLINE_POLL_INTERVAL,
        }
