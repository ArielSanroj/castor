"""
KPI Monitor.
Calculates and tracks agent performance KPIs.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from services.agent.config import AgentConfig, get_agent_config
from services.agent.state import AgentState, AgentMetrics

logger = logging.getLogger(__name__)


@dataclass
class KPISnapshot:
    """Snapshot of KPIs at a point in time."""
    timestamp: datetime

    # OKR 1: Data Integrity
    detection_rate_arithmetic: float = 0.0  # Target: 95%
    mtti_seconds: float = 0.0  # Mean time to incident (Target: <30s)
    p0p1_analysis_coverage: float = 0.0  # Target: 99%
    false_positive_rate_ocr: float = 0.0  # Target: <5%

    # OKR 2: Legal Response
    cpaca_classification_time_seconds: float = 0.0  # Target: <60s
    evidence_package_time_seconds: float = 0.0  # Target: <300s
    nullity_correlation: float = 0.0  # Target: >80%
    deadline_alert_accuracy: float = 0.0  # Target: 100%

    # OKR 3: Proactive Decisions
    briefing_latency_seconds: float = 0.0  # Target: <120s
    risk_prediction_accuracy: float = 0.0  # Target: >75%
    recommendation_satisfaction: float = 0.0  # Target: >90%
    manual_effort_reduction: float = 0.0  # Target: 60%

    # Agent operational KPIs
    agent_uptime: float = 0.0  # Target: >99.5%
    agent_actions_per_hour: float = 0.0
    agent_hitl_escalation_rate: float = 0.0  # Target: <20%
    agent_recommendation_acceptance: float = 0.0  # Target: >75%

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class KPIMonitor:
    """
    Monitors and calculates agent KPIs.
    Tracks performance against OKR targets.
    """

    # OKR Targets
    TARGETS = {
        'detection_rate_arithmetic': 0.95,
        'mtti_seconds': 30.0,
        'p0p1_analysis_coverage': 0.99,
        'false_positive_rate_ocr': 0.05,
        'cpaca_classification_time_seconds': 60.0,
        'evidence_package_time_seconds': 300.0,
        'nullity_correlation': 0.80,
        'deadline_alert_accuracy': 1.0,
        'briefing_latency_seconds': 120.0,
        'risk_prediction_accuracy': 0.75,
        'recommendation_satisfaction': 0.90,
        'manual_effort_reduction': 0.60,
        'agent_uptime': 0.995,
        'agent_hitl_escalation_rate': 0.20,
        'agent_recommendation_acceptance': 0.75,
    }

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        state: Optional[AgentState] = None
    ):
        """
        Initialize the KPI monitor.

        Args:
            config: Agent configuration
            state: Agent state manager
        """
        self.config = config or get_agent_config()
        self._state = state
        self._snapshots: List[KPISnapshot] = []
        self._max_snapshots = 1000
        self._last_calculation_time: Optional[datetime] = None

        # Rolling counters for calculations
        self._counters: Dict[str, Any] = {
            'arithmetic_detected': 0,
            'arithmetic_total': 0,
            'incidents_created': 0,
            'incident_creation_times': [],
            'p0p1_analyzed': 0,
            'p0p1_total': 0,
            'false_positives': 0,
            'total_classifications': 0,
            'classification_times': [],
            'evidence_times': [],
            'deadline_alerts_correct': 0,
            'deadline_alerts_total': 0,
            'briefing_times': [],
            'hitl_escalated': 0,
            'hitl_total': 0,
            'recommendations_accepted': 0,
            'recommendations_total': 0,
        }

        logger.info("KPIMonitor initialized")

    def calculate_kpis(self) -> KPISnapshot:
        """
        Calculate current KPIs.

        Returns:
            KPISnapshot with current values
        """
        now = datetime.utcnow()
        self._last_calculation_time = now

        snapshot = KPISnapshot(timestamp=now)

        # OKR 1: Data Integrity
        if self._counters['arithmetic_total'] > 0:
            snapshot.detection_rate_arithmetic = (
                self._counters['arithmetic_detected'] / self._counters['arithmetic_total']
            )

        if self._counters['incident_creation_times']:
            snapshot.mtti_seconds = sum(self._counters['incident_creation_times']) / len(
                self._counters['incident_creation_times']
            )

        if self._counters['p0p1_total'] > 0:
            snapshot.p0p1_analysis_coverage = (
                self._counters['p0p1_analyzed'] / self._counters['p0p1_total']
            )

        if self._counters['total_classifications'] > 0:
            snapshot.false_positive_rate_ocr = (
                self._counters['false_positives'] / self._counters['total_classifications']
            )

        # OKR 2: Legal Response
        if self._counters['classification_times']:
            snapshot.cpaca_classification_time_seconds = sum(
                self._counters['classification_times']
            ) / len(self._counters['classification_times'])

        if self._counters['evidence_times']:
            snapshot.evidence_package_time_seconds = sum(
                self._counters['evidence_times']
            ) / len(self._counters['evidence_times'])

        if self._counters['deadline_alerts_total'] > 0:
            snapshot.deadline_alert_accuracy = (
                self._counters['deadline_alerts_correct'] / self._counters['deadline_alerts_total']
            )

        # OKR 3: Proactive Decisions
        if self._counters['briefing_times']:
            snapshot.briefing_latency_seconds = sum(
                self._counters['briefing_times']
            ) / len(self._counters['briefing_times'])

        # Agent operational
        if self._state:
            metrics = self._state.get_metrics()
            started_at = self._state.get_started_at()
            if started_at:
                expected_uptime = (now - started_at).total_seconds()
                if expected_uptime > 0:
                    snapshot.agent_uptime = metrics.uptime_seconds / expected_uptime

            # Calculate actions per hour
            actions_last_hour = len(self._state.get_actions_since(now - timedelta(hours=1)))
            snapshot.agent_actions_per_hour = float(actions_last_hour)

        if self._counters['hitl_total'] > 0:
            snapshot.agent_hitl_escalation_rate = (
                self._counters['hitl_escalated'] / self._counters['hitl_total']
            )

        if self._counters['recommendations_total'] > 0:
            snapshot.agent_recommendation_acceptance = (
                self._counters['recommendations_accepted'] / self._counters['recommendations_total']
            )

        # Store snapshot
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

        return snapshot

    def record_arithmetic_detection(self, detected: bool) -> None:
        """Record arithmetic anomaly detection result."""
        self._counters['arithmetic_total'] += 1
        if detected:
            self._counters['arithmetic_detected'] += 1

    def record_incident_creation(self, creation_time_seconds: float) -> None:
        """Record incident creation time."""
        self._counters['incidents_created'] += 1
        self._counters['incident_creation_times'].append(creation_time_seconds)
        # Keep only last 100 times
        if len(self._counters['incident_creation_times']) > 100:
            self._counters['incident_creation_times'] = self._counters['incident_creation_times'][-100:]

    def record_p0p1_analysis(self, analyzed: bool) -> None:
        """Record P0/P1 incident analysis."""
        self._counters['p0p1_total'] += 1
        if analyzed:
            self._counters['p0p1_analyzed'] += 1

    def record_classification(self, is_false_positive: bool) -> None:
        """Record classification result."""
        self._counters['total_classifications'] += 1
        if is_false_positive:
            self._counters['false_positives'] += 1

    def record_cpaca_classification(self, time_seconds: float) -> None:
        """Record CPACA classification time."""
        self._counters['classification_times'].append(time_seconds)
        if len(self._counters['classification_times']) > 100:
            self._counters['classification_times'] = self._counters['classification_times'][-100:]

    def record_evidence_package(self, time_seconds: float) -> None:
        """Record evidence package generation time."""
        self._counters['evidence_times'].append(time_seconds)
        if len(self._counters['evidence_times']) > 100:
            self._counters['evidence_times'] = self._counters['evidence_times'][-100:]

    def record_deadline_alert(self, correct: bool) -> None:
        """Record deadline alert accuracy."""
        self._counters['deadline_alerts_total'] += 1
        if correct:
            self._counters['deadline_alerts_correct'] += 1

    def record_briefing(self, latency_seconds: float) -> None:
        """Record briefing generation time."""
        self._counters['briefing_times'].append(latency_seconds)
        if len(self._counters['briefing_times']) > 100:
            self._counters['briefing_times'] = self._counters['briefing_times'][-100:]

    def record_hitl_decision(self, escalated: bool) -> None:
        """Record HITL decision."""
        self._counters['hitl_total'] += 1
        if escalated:
            self._counters['hitl_escalated'] += 1

    def record_recommendation(self, accepted: bool) -> None:
        """Record recommendation acceptance."""
        self._counters['recommendations_total'] += 1
        if accepted:
            self._counters['recommendations_accepted'] += 1

    def get_target_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of each KPI against its target.

        Returns:
            Dictionary with KPI name -> {value, target, on_target, gap}
        """
        snapshot = self.calculate_kpis()
        status = {}

        for kpi_name, target in self.TARGETS.items():
            value = getattr(snapshot, kpi_name, 0.0)

            # For some KPIs, lower is better
            lower_is_better = kpi_name in (
                'mtti_seconds',
                'false_positive_rate_ocr',
                'cpaca_classification_time_seconds',
                'evidence_package_time_seconds',
                'briefing_latency_seconds',
                'agent_hitl_escalation_rate',
            )

            if lower_is_better:
                on_target = value <= target
                gap = target - value
            else:
                on_target = value >= target
                gap = value - target

            status[kpi_name] = {
                'value': value,
                'target': target,
                'on_target': on_target,
                'gap': gap,
                'gap_percent': (gap / target * 100) if target != 0 else 0,
            }

        return status

    def get_recent_snapshots(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Get recent KPI snapshots."""
        return [s.to_dict() for s in self._snapshots[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            'last_calculation_time': self._last_calculation_time.isoformat() if self._last_calculation_time else None,
            'snapshots_count': len(self._snapshots),
            'counters': {k: v if not isinstance(v, list) else len(v) for k, v in self._counters.items()},
        }

    def reset_counters(self) -> None:
        """Reset all counters (e.g., for a new election cycle)."""
        for key in self._counters:
            if isinstance(self._counters[key], list):
                self._counters[key] = []
            else:
                self._counters[key] = 0
        logger.info("KPI counters reset")
