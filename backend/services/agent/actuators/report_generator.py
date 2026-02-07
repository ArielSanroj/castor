"""
Report Generator.
Generates intelligence briefings and reports using LLM.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from services.agent.config import AgentConfig, get_agent_config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates intelligence briefings and reports.
    Uses LLM for narrative generation when available.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        openai_service=None
    ):
        """
        Initialize the report generator.

        Args:
            config: Agent configuration
            openai_service: OpenAI service for LLM generation
        """
        self.config = config or get_agent_config()
        self._openai_service = openai_service
        self._reports_generated = 0

        logger.info("ReportGenerator initialized")

    async def generate_hourly_briefing(
        self,
        metrics: Dict[str, Any],
        recent_actions: List[Dict[str, Any]],
        pending_hitl: List[Dict[str, Any]],
        high_risk_areas: List[Dict[str, Any]],
        recent_incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an hourly intelligence briefing.

        Args:
            metrics: Agent metrics
            recent_actions: Recent agent actions
            pending_hitl: Pending HITL requests
            high_risk_areas: High-risk areas
            recent_incidents: Recent incidents

        Returns:
            Briefing report
        """
        start_time = datetime.utcnow()

        briefing = {
            'type': 'HOURLY_BRIEFING',
            'generated_at': start_time.isoformat(),
            'period': 'last_hour',
            'sections': {},
        }

        # Executive summary section
        briefing['sections']['executive_summary'] = self._generate_executive_summary(
            metrics, recent_actions, high_risk_areas
        )

        # Metrics section
        briefing['sections']['metrics'] = {
            'anomalies_detected': metrics.get('anomalies_detected_last_hour', 0),
            'incidents_created': metrics.get('incidents_auto_created', 0),
            'alerts_sent': metrics.get('deadline_alerts_sent', 0),
            'hitl_pending': len(pending_hitl),
            'agent_uptime': f"{metrics.get('uptime_seconds', 0) / 3600:.1f}h",
        }

        # High risk areas section
        briefing['sections']['high_risk_areas'] = [
            {
                'area_code': area.get('area_code'),
                'area_name': area.get('area_name'),
                'risk_level': area.get('risk_level'),
                'score': area.get('score'),
                'anomaly_count': area.get('anomaly_count'),
            }
            for area in high_risk_areas[:5]
        ]

        # Recent actions section
        briefing['sections']['recent_actions'] = [
            {
                'action_type': action.get('action_type'),
                'timestamp': action.get('timestamp'),
                'target_id': action.get('target_id'),
                'result': action.get('result'),
            }
            for action in recent_actions[:10]
        ]

        # Pending approvals section
        briefing['sections']['pending_approvals'] = [
            {
                'request_id': req.get('request_id'),
                'action_type': req.get('action_type'),
                'priority': req.get('priority'),
                'title': req.get('title'),
            }
            for req in pending_hitl[:5]
        ]

        # Generate narrative if LLM is available
        if self.config.LLM_BRIEFINGS_ENABLED and self._openai_service:
            narrative = await self._generate_narrative_llm(briefing)
        else:
            narrative = self._generate_narrative_simple(briefing)

        briefing['narrative'] = narrative

        # Calculate latency
        latency = (datetime.utcnow() - start_time).total_seconds()
        briefing['generation_latency_seconds'] = latency

        self._reports_generated += 1

        logger.info(f"Generated hourly briefing in {latency:.2f}s")
        return briefing

    async def generate_incident_report(
        self,
        incident: Dict[str, Any],
        legal_classification: Optional[Dict[str, Any]] = None,
        related_anomalies: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed incident report.

        Args:
            incident: Incident data
            legal_classification: Legal classification if available
            related_anomalies: Related anomalies

        Returns:
            Incident report
        """
        report = {
            'type': 'INCIDENT_REPORT',
            'generated_at': datetime.utcnow().isoformat(),
            'incident_id': incident.get('id'),
            'sections': {},
        }

        # Incident details
        report['sections']['incident'] = {
            'id': incident.get('id'),
            'type': incident.get('incident_type'),
            'severity': incident.get('severity'),
            'status': incident.get('status'),
            'mesa_id': incident.get('mesa_id'),
            'description': incident.get('description'),
            'created_at': incident.get('created_at'),
            'sla_deadline': incident.get('sla_deadline'),
        }

        # Legal classification
        if legal_classification:
            report['sections']['legal'] = {
                'cpaca_article': legal_classification.get('primary_article'),
                'causals': legal_classification.get('causals', []),
                'nullity_viability': legal_classification.get('nullity_viability'),
                'deadline': legal_classification.get('deadline'),
                'recommended_actions': legal_classification.get('recommended_actions', []),
            }

        # Related anomalies
        if related_anomalies:
            report['sections']['related_anomalies'] = [
                {
                    'anomaly_id': a.get('anomaly_id'),
                    'type': a.get('type'),
                    'description': a.get('description'),
                }
                for a in related_anomalies[:5]
            ]

        # Evidence requirements
        if legal_classification:
            report['sections']['evidence_requirements'] = legal_classification.get(
                'evidence_requirements', []
            )

        self._reports_generated += 1
        return report

    async def generate_evidence_package(
        self,
        incident: Dict[str, Any],
        legal_classification: Dict[str, Any],
        form_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an evidence package for legal proceedings.

        Args:
            incident: Incident data
            legal_classification: Legal classification
            form_data: E-14 form data if available

        Returns:
            Evidence package
        """
        start_time = datetime.utcnow()

        package = {
            'type': 'EVIDENCE_PACKAGE',
            'generated_at': start_time.isoformat(),
            'incident_id': incident.get('id'),
            'cpaca_article': legal_classification.get('primary_article'),
            'sections': {},
        }

        # Case summary
        package['sections']['case_summary'] = {
            'incident_type': incident.get('incident_type'),
            'mesa_id': incident.get('mesa_id'),
            'detected_at': incident.get('created_at'),
            'nullity_viability': legal_classification.get('nullity_viability'),
            'causals': legal_classification.get('causals', []),
        }

        # Timeline of events
        package['sections']['timeline'] = [
            {
                'timestamp': incident.get('created_at'),
                'event': 'Anomalía detectada',
                'details': incident.get('description'),
            },
        ]

        if incident.get('assigned_at'):
            package['sections']['timeline'].append({
                'timestamp': incident.get('assigned_at'),
                'event': 'Incidente asignado',
                'details': f"Asignado a: {incident.get('assigned_to')}",
            })

        # Evidence items
        package['sections']['evidence'] = []

        # Add E-14 form evidence
        if form_data:
            package['sections']['evidence'].append({
                'evidence_type': 'E14_FORM',
                'description': 'Acta de escrutinio E-14',
                'mesa_id': form_data.get('document_header_extracted', {}).get('mesa_id'),
                'extracted_data': {
                    'ocr_confidence': form_data.get('overall_confidence'),
                    'validations_failed': len([
                        v for v in form_data.get('validations', [])
                        if not v.get('passed')
                    ]),
                },
            })

        # Add incident evidence
        package['sections']['evidence'].append({
            'evidence_type': 'INCIDENT_RECORD',
            'description': 'Registro del incidente',
            'incident_id': incident.get('id'),
            'delta_value': incident.get('delta_value'),
            'ocr_confidence': incident.get('ocr_confidence'),
        })

        # Legal basis
        package['sections']['legal_basis'] = {
            'primary_article': legal_classification.get('primary_article'),
            'secondary_articles': legal_classification.get('secondary_articles', []),
            'causals': legal_classification.get('causals', []),
            'viability_factors': legal_classification.get('viability_factors', {}),
        }

        # Recommended actions
        package['sections']['recommended_actions'] = legal_classification.get(
            'recommended_actions', []
        )

        # Evidence requirements checklist
        requirements = legal_classification.get('evidence_requirements', [])
        package['sections']['evidence_checklist'] = [
            {'requirement': req, 'status': 'PENDING'}
            for req in requirements
        ]

        # Calculate latency
        latency = (datetime.utcnow() - start_time).total_seconds()
        package['generation_latency_seconds'] = latency

        self._reports_generated += 1

        logger.info(f"Generated evidence package for incident {incident.get('id')} in {latency:.2f}s")
        return package

    def _generate_executive_summary(
        self,
        metrics: Dict[str, Any],
        recent_actions: List[Dict[str, Any]],
        high_risk_areas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate executive summary section."""
        anomalies = metrics.get('anomalies_detected_last_hour', 0)
        incidents = metrics.get('incidents_auto_created', 0)
        high_risk_count = len(high_risk_areas)

        # Determine overall status
        if high_risk_count > 3 or anomalies > 20:
            status = 'ALERTA'
            color = 'red'
        elif high_risk_count > 0 or anomalies > 10:
            status = 'PRECAUCIÓN'
            color = 'yellow'
        else:
            status = 'NORMAL'
            color = 'green'

        return {
            'status': status,
            'status_color': color,
            'key_metrics': {
                'anomalies_last_hour': anomalies,
                'incidents_created': incidents,
                'high_risk_areas': high_risk_count,
            },
            'highlights': self._generate_highlights(metrics, high_risk_areas),
        }

    def _generate_highlights(
        self,
        metrics: Dict[str, Any],
        high_risk_areas: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate highlight points."""
        highlights = []

        anomalies = metrics.get('anomalies_detected_last_hour', 0)
        if anomalies > 0:
            highlights.append(f"Se detectaron {anomalies} anomalías en la última hora")

        if high_risk_areas:
            areas = ", ".join(a.get('area_name', a.get('area_code', ''))[:20] for a in high_risk_areas[:3])
            highlights.append(f"Áreas de alto riesgo: {areas}")

        hitl_pending = metrics.get('hitl_pending', 0)
        if hitl_pending > 0:
            highlights.append(f"{hitl_pending} acciones pendientes de aprobación humana")

        if not highlights:
            highlights.append("Operación normal sin eventos significativos")

        return highlights

    async def _generate_narrative_llm(self, briefing: Dict[str, Any]) -> str:
        """Generate narrative using LLM."""
        if not self._openai_service:
            return self._generate_narrative_simple(briefing)

        try:
            metrics = briefing['sections'].get('metrics', {})
            high_risk = briefing['sections'].get('high_risk_areas', [])
            pending = briefing['sections'].get('pending_approvals', [])

            prompt = f"""Genera un briefing ejecutivo de inteligencia electoral en español para el War Room.

Datos del período:
- Anomalías detectadas: {metrics.get('anomalies_detected', 0)}
- Incidentes creados: {metrics.get('incidents_created', 0)}
- Alertas enviadas: {metrics.get('alerts_sent', 0)}
- Aprobaciones pendientes: {len(pending)}
- Áreas de alto riesgo: {len(high_risk)}

Genera un resumen ejecutivo de 2-3 párrafos conciso y profesional."""

            response = self._openai_service.chat(prompt)
            return response
        except Exception as e:
            logger.error(f"LLM narrative generation failed: {e}")
            return self._generate_narrative_simple(briefing)

    def _generate_narrative_simple(self, briefing: Dict[str, Any]) -> str:
        """Generate simple narrative without LLM."""
        metrics = briefing['sections'].get('metrics', {})
        summary = briefing['sections'].get('executive_summary', {})
        high_risk = briefing['sections'].get('high_risk_areas', [])

        status = summary.get('status', 'NORMAL')
        anomalies = metrics.get('anomalies_detected', 0)
        incidents = metrics.get('incidents_created', 0)
        hitl_pending = metrics.get('hitl_pending', 0)

        narrative = f"BRIEFING DE INTELIGENCIA ELECTORAL - {briefing.get('generated_at', '')}\n\n"
        narrative += f"Estado general: {status}\n\n"

        narrative += f"En el último período se detectaron {anomalies} anomalías y "
        narrative += f"se crearon {incidents} incidentes automáticamente. "

        if high_risk:
            areas = ", ".join(a.get('area_name', a.get('area_code', '')) for a in high_risk[:3])
            narrative += f"Se identificaron {len(high_risk)} áreas de alto riesgo: {areas}. "

        if hitl_pending > 0:
            narrative += f"\n\nHay {hitl_pending} acciones pendientes de aprobación humana que requieren atención."
        else:
            narrative += "\n\nNo hay acciones pendientes de aprobación."

        return narrative

    def get_stats(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            'reports_generated': self._reports_generated,
            'llm_enabled': self._openai_service is not None,
        }
