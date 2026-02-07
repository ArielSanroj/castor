"""
Incident Monitor.
Monitors incidents for SLA breaches and escalation needs.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class IncidentMonitor:
    """
    Monitors incidents for SLA compliance and escalation triggers.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        on_sla_warning: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_escalation_needed: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the incident monitor.

        Args:
            config: Agent configuration
            on_sla_warning: Callback when SLA warning is triggered
            on_escalation_needed: Callback when escalation is needed
        """
        self.config = config or get_agent_config()
        self._on_sla_warning = on_sla_warning
        self._on_escalation_needed = on_escalation_needed
        self._last_poll_time: Optional[datetime] = None
        self._warned_incidents: Dict[int, datetime] = {}  # incident_id -> last warned time

        logger.info("IncidentMonitor initialized")

    async def poll(self, incidents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Poll incidents and check for SLA/escalation issues.

        Args:
            incidents: List of active incidents

        Returns:
            Dictionary with 'sla_warnings' and 'escalations' lists
        """
        self._last_poll_time = datetime.utcnow()
        results = {
            'sla_warnings': [],
            'escalations': [],
        }

        for incident in incidents:
            # Skip resolved incidents
            status = incident.get('status', 'OPEN')
            if status in ('RESOLVED', 'FALSE_POSITIVE'):
                continue

            # Check SLA
            sla_warning = self._check_sla(incident)
            if sla_warning:
                results['sla_warnings'].append(sla_warning)
                if self._on_sla_warning:
                    self._on_sla_warning(sla_warning)

            # Check escalation
            escalation = self._check_escalation(incident)
            if escalation:
                results['escalations'].append(escalation)
                if self._on_escalation_needed:
                    self._on_escalation_needed(escalation)

        logger.debug(
            f"IncidentMonitor poll: {len(incidents)} incidents, "
            f"{len(results['sla_warnings'])} SLA warnings, "
            f"{len(results['escalations'])} escalations"
        )

        return results

    def check_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check a single incident for issues.

        Args:
            incident: Incident data

        Returns:
            Dictionary with any warnings/issues found
        """
        result = {}

        sla_warning = self._check_sla(incident)
        if sla_warning:
            result['sla_warning'] = sla_warning

        escalation = self._check_escalation(incident)
        if escalation:
            result['escalation_needed'] = escalation

        return result

    def _check_sla(self, incident: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if SLA warning should be issued."""
        incident_id = incident.get('id')
        severity = incident.get('severity', 'P3')
        sla_deadline_str = incident.get('sla_deadline')

        if not sla_deadline_str:
            return None

        # Parse deadline
        if isinstance(sla_deadline_str, str):
            sla_deadline = datetime.fromisoformat(sla_deadline_str.replace('Z', '+00:00'))
        else:
            sla_deadline = sla_deadline_str

        # Calculate remaining time
        now = datetime.utcnow()
        if sla_deadline.tzinfo:
            now = now.replace(tzinfo=sla_deadline.tzinfo)

        remaining = (sla_deadline - now).total_seconds() / 60
        warning_threshold = self.config.get_sla_warning_minutes(severity)

        if remaining <= 0:
            # SLA breached
            return self._create_sla_warning(incident, remaining, 'BREACHED')
        elif remaining < warning_threshold:
            # Check if we've already warned recently (within 5 minutes)
            last_warned = self._warned_incidents.get(incident_id)
            if last_warned and (now - last_warned).total_seconds() < 300:
                return None

            self._warned_incidents[incident_id] = now
            return self._create_sla_warning(incident, remaining, 'WARNING')

        return None

    def _create_sla_warning(
        self,
        incident: Dict[str, Any],
        remaining_minutes: float,
        warning_type: str
    ) -> Dict[str, Any]:
        """Create SLA warning object."""
        return {
            'incident_id': incident.get('id'),
            'severity': incident.get('severity'),
            'incident_type': incident.get('incident_type'),
            'mesa_id': incident.get('mesa_id'),
            'sla_remaining_minutes': max(0, remaining_minutes),
            'warning_type': warning_type,
            'assigned_to': incident.get('assigned_to'),
            'detected_at': datetime.utcnow().isoformat(),
        }

    def _check_escalation(self, incident: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if incident should be escalated."""
        severity = incident.get('severity', 'P3')
        status = incident.get('status', 'OPEN')
        escalated = incident.get('escalated_to_legal', False)

        # Only escalate P0 incidents
        if severity != 'P0':
            return None

        # Skip if already escalated
        if status == 'ESCALATED' or escalated:
            return None

        # Check age
        created_at_str = incident.get('created_at')
        if not created_at_str:
            return None

        if isinstance(created_at_str, str):
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        else:
            created_at = created_at_str

        now = datetime.utcnow()
        if created_at.tzinfo:
            now = now.replace(tzinfo=created_at.tzinfo)

        age_minutes = (now - created_at).total_seconds() / 60

        if age_minutes > self.config.HITL_AUTO_ESCALATE_AFTER_MINUTES:
            return {
                'incident_id': incident.get('id'),
                'severity': severity,
                'incident_type': incident.get('incident_type'),
                'mesa_id': incident.get('mesa_id'),
                'age_minutes': age_minutes,
                'reason': 'P0 incident unresolved beyond threshold',
                'detected_at': datetime.utcnow().isoformat(),
            }

        return None

    def cleanup_warned_cache(self, max_age_hours: int = 24) -> int:
        """
        Clean up old entries from warned incidents cache.

        Args:
            max_age_hours: Maximum age of cache entries

        Returns:
            Number of entries removed
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        old_count = len(self._warned_incidents)

        self._warned_incidents = {
            k: v for k, v in self._warned_incidents.items()
            if v > cutoff
        }

        removed = old_count - len(self._warned_incidents)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old SLA warning entries")

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            'last_poll_time': self._last_poll_time.isoformat() if self._last_poll_time else None,
            'warned_incidents_count': len(self._warned_incidents),
            'poll_interval_seconds': self.config.INCIDENT_POLL_INTERVAL,
        }
