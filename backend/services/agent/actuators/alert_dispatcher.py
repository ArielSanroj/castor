"""
Alert Dispatcher.
Dispatches alerts via various channels (dashboard, websocket, etc).
"""
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    DASHBOARD = "DASHBOARD"
    WEBSOCKET = "WEBSOCKET"
    LOG = "LOG"


class AlertUrgency(str, Enum):
    """Alert urgency levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertType(str, Enum):
    """Types of alerts."""
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"
    DEADLINE_WARNING = "DEADLINE_WARNING"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    CLUSTER_DETECTED = "CLUSTER_DETECTED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    HITL_REQUIRED = "HITL_REQUIRED"
    SYSTEM_ALERT = "SYSTEM_ALERT"


@dataclass
class Alert:
    """An alert to be dispatched."""
    alert_id: str
    alert_type: AlertType
    urgency: AlertUrgency
    title: str
    message: str
    target_id: Optional[str]  # Incident ID, mesa ID, etc.
    target_type: Optional[str]  # incident, mesa, deadline
    data: Dict[str, Any]
    created_at: datetime
    channels: List[AlertChannel]
    dispatched: bool = False
    dispatched_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.value,
            'urgency': self.urgency.value,
            'title': self.title,
            'message': self.message,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'channels': [c.value for c in self.channels],
            'dispatched': self.dispatched,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
        }


class AlertDispatcher:
    """
    Dispatches alerts to various channels.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        websocket_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the alert dispatcher.

        Args:
            config: Agent configuration
            websocket_callback: Callback for WebSocket dispatch
        """
        self.config = config or get_agent_config()
        self._websocket_callback = websocket_callback

        self._alert_counter = 0
        self._alerts_dispatched = 0
        self._recent_alerts: List[Alert] = []
        self._max_recent = 100

        logger.info("AlertDispatcher initialized")

    async def dispatch_sla_alert(
        self,
        incident_id: int,
        severity: str,
        sla_remaining_minutes: float,
        assigned_to: Optional[str] = None
    ) -> Alert:
        """
        Dispatch an SLA warning or breach alert.

        Args:
            incident_id: Incident ID
            severity: Incident severity (P0, P1, etc)
            sla_remaining_minutes: Minutes remaining on SLA
            assigned_to: User assigned to the incident

        Returns:
            Dispatched alert
        """
        is_breach = sla_remaining_minutes <= 0
        alert_type = AlertType.SLA_BREACH if is_breach else AlertType.SLA_WARNING

        urgency = AlertUrgency.CRITICAL if is_breach or severity == 'P0' else AlertUrgency.HIGH

        if is_breach:
            title = f"SLA INCUMPLIDO - Incidente {severity} #{incident_id}"
            message = f"El SLA del incidente #{incident_id} ({severity}) ha sido incumplido."
        else:
            title = f"Alerta SLA - Incidente {severity} #{incident_id}"
            message = f"Quedan {sla_remaining_minutes:.0f} minutos para el SLA del incidente #{incident_id}."

        if assigned_to:
            message += f" Asignado a: {assigned_to}"
        else:
            message += " SIN ASIGNAR"

        alert = await self._create_and_dispatch(
            alert_type=alert_type,
            urgency=urgency,
            title=title,
            message=message,
            target_id=str(incident_id),
            target_type='incident',
            data={
                'incident_id': incident_id,
                'severity': severity,
                'sla_remaining_minutes': sla_remaining_minutes,
                'assigned_to': assigned_to,
                'is_breach': is_breach,
            },
        )

        return alert

    async def dispatch_deadline_alert(
        self,
        deadline_id: str,
        deadline_type: str,
        hours_remaining: float,
        incident_id: Optional[int] = None,
        cpaca_article: Optional[int] = None
    ) -> Alert:
        """
        Dispatch a deadline warning or expiration alert.

        Args:
            deadline_id: Deadline ID
            deadline_type: Type of deadline
            hours_remaining: Hours remaining
            incident_id: Related incident ID
            cpaca_article: CPACA article number

        Returns:
            Dispatched alert
        """
        is_expired = hours_remaining <= 0
        alert_type = AlertType.DEADLINE_EXPIRED if is_expired else AlertType.DEADLINE_WARNING

        if hours_remaining < 6:
            urgency = AlertUrgency.CRITICAL
        elif hours_remaining < 24:
            urgency = AlertUrgency.HIGH
        else:
            urgency = AlertUrgency.MEDIUM

        article_str = f" (Art. {cpaca_article})" if cpaca_article else ""

        if is_expired:
            title = f"PLAZO VENCIDO - {deadline_type}{article_str}"
            message = f"El plazo {deadline_type}{article_str} ha vencido."
        else:
            title = f"Alerta de Plazo - {deadline_type}{article_str}"
            if hours_remaining < 24:
                message = f"Quedan {hours_remaining:.0f} horas para el plazo {deadline_type}{article_str}."
            else:
                days = hours_remaining / 24
                message = f"Quedan {days:.1f} días para el plazo {deadline_type}{article_str}."

        if incident_id:
            message += f" Incidente relacionado: #{incident_id}"

        alert = await self._create_and_dispatch(
            alert_type=alert_type,
            urgency=urgency,
            title=title,
            message=message,
            target_id=deadline_id,
            target_type='deadline',
            data={
                'deadline_id': deadline_id,
                'deadline_type': deadline_type,
                'hours_remaining': hours_remaining,
                'incident_id': incident_id,
                'cpaca_article': cpaca_article,
                'is_expired': is_expired,
            },
        )

        return alert

    async def dispatch_anomaly_alert(
        self,
        anomaly: Dict[str, Any]
    ) -> Alert:
        """
        Dispatch an anomaly detection alert.

        Args:
            anomaly: Anomaly data

        Returns:
            Dispatched alert
        """
        anomaly_type = anomaly.get('type', 'UNKNOWN')
        mesa_id = anomaly.get('mesa_id', '')
        severity = anomaly.get('severity', 'MEDIUM')

        urgency_map = {
            'CRITICAL': AlertUrgency.CRITICAL,
            'HIGH': AlertUrgency.HIGH,
            'MEDIUM': AlertUrgency.MEDIUM,
            'LOW': AlertUrgency.LOW,
        }
        urgency = urgency_map.get(severity, AlertUrgency.MEDIUM)

        title = f"Anomalía Detectada - {anomaly_type}"
        message = anomaly.get('description', f"Anomalía tipo {anomaly_type} detectada en mesa {mesa_id}")

        alert = await self._create_and_dispatch(
            alert_type=AlertType.ANOMALY_DETECTED,
            urgency=urgency,
            title=title,
            message=message,
            target_id=mesa_id,
            target_type='mesa',
            data=anomaly,
        )

        return alert

    async def dispatch_cluster_alert(
        self,
        municipality_code: str,
        anomaly_count: int,
        affected_mesas: List[str]
    ) -> Alert:
        """
        Dispatch a geographic cluster alert.

        Args:
            municipality_code: Municipality code
            anomaly_count: Number of anomalies in cluster
            affected_mesas: List of affected mesa IDs

        Returns:
            Dispatched alert
        """
        title = f"CLUSTER GEOGRÁFICO - Municipio {municipality_code}"
        message = f"Se detectaron {anomaly_count} anomalías en el municipio {municipality_code}. Requiere investigación inmediata."

        alert = await self._create_and_dispatch(
            alert_type=AlertType.CLUSTER_DETECTED,
            urgency=AlertUrgency.CRITICAL,
            title=title,
            message=message,
            target_id=municipality_code,
            target_type='municipality',
            data={
                'municipality_code': municipality_code,
                'anomaly_count': anomaly_count,
                'affected_mesas': affected_mesas[:20],  # Limit
            },
        )

        return alert

    async def dispatch_hitl_alert(
        self,
        request_id: str,
        action_type: str,
        description: str,
        priority: str
    ) -> Alert:
        """
        Dispatch a HITL approval required alert.

        Args:
            request_id: HITL request ID
            action_type: Type of action requiring approval
            description: Description of the action
            priority: Priority level

        Returns:
            Dispatched alert
        """
        urgency = AlertUrgency.CRITICAL if priority == 'P0' else AlertUrgency.HIGH

        title = f"Aprobación Requerida - {action_type}"
        message = f"Se requiere aprobación humana para: {description}"

        alert = await self._create_and_dispatch(
            alert_type=AlertType.HITL_REQUIRED,
            urgency=urgency,
            title=title,
            message=message,
            target_id=request_id,
            target_type='hitl_request',
            data={
                'request_id': request_id,
                'action_type': action_type,
                'priority': priority,
            },
        )

        return alert

    async def _create_and_dispatch(
        self,
        alert_type: AlertType,
        urgency: AlertUrgency,
        title: str,
        message: str,
        target_id: Optional[str],
        target_type: Optional[str],
        data: Dict[str, Any]
    ) -> Alert:
        """Create and dispatch an alert."""
        self._alert_counter += 1

        # Determine channels based on urgency
        channels = [AlertChannel.DASHBOARD, AlertChannel.LOG]
        if urgency in (AlertUrgency.CRITICAL, AlertUrgency.HIGH):
            channels.append(AlertChannel.WEBSOCKET)

        alert = Alert(
            alert_id=f"ALR-{self._alert_counter:08d}",
            alert_type=alert_type,
            urgency=urgency,
            title=title,
            message=message,
            target_id=target_id,
            target_type=target_type,
            data=data,
            created_at=datetime.utcnow(),
            channels=channels,
        )

        # Dispatch to channels
        await self._dispatch_to_channels(alert)

        return alert

    async def _dispatch_to_channels(self, alert: Alert) -> None:
        """Dispatch alert to configured channels."""
        for channel in alert.channels:
            try:
                if channel == AlertChannel.LOG:
                    self._dispatch_to_log(alert)
                elif channel == AlertChannel.WEBSOCKET:
                    await self._dispatch_to_websocket(alert)
                elif channel == AlertChannel.DASHBOARD:
                    self._dispatch_to_dashboard(alert)
            except Exception as e:
                logger.error(f"Error dispatching to {channel}: {e}")

        alert.dispatched = True
        alert.dispatched_at = datetime.utcnow()
        self._alerts_dispatched += 1

        # Store in recent alerts
        self._recent_alerts.append(alert)
        if len(self._recent_alerts) > self._max_recent:
            self._recent_alerts = self._recent_alerts[-self._max_recent:]

    def _dispatch_to_log(self, alert: Alert) -> None:
        """Dispatch alert to log."""
        log_level = {
            AlertUrgency.CRITICAL: logging.CRITICAL,
            AlertUrgency.HIGH: logging.ERROR,
            AlertUrgency.MEDIUM: logging.WARNING,
            AlertUrgency.LOW: logging.INFO,
            AlertUrgency.INFO: logging.INFO,
        }.get(alert.urgency, logging.INFO)

        logger.log(log_level, f"[{alert.alert_type.value}] {alert.title}: {alert.message}")

    async def _dispatch_to_websocket(self, alert: Alert) -> None:
        """Dispatch alert via WebSocket."""
        if self._websocket_callback:
            try:
                self._websocket_callback(alert.to_dict())
            except Exception as e:
                logger.error(f"WebSocket dispatch failed: {e}")

    def _dispatch_to_dashboard(self, alert: Alert) -> None:
        """
        Dispatch alert to dashboard.
        In production, this would push to a notification queue.
        """
        # The alert is stored in recent_alerts which can be queried by the dashboard
        pass

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return [a.to_dict() for a in self._recent_alerts[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        return {
            'alerts_dispatched': self._alerts_dispatched,
            'recent_count': len(self._recent_alerts),
        }
