"""
Decision Engine for the Electoral Intelligence Agent.
Evaluates rules and determines which actions to take.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from services.agent.config import (
    AgentConfig,
    AgentAction,
    HITLRequirement,
    RuleConfig,
    get_agent_config
)

logger = logging.getLogger(__name__)


@dataclass
class RuleMatch:
    """Result of a rule evaluation."""
    rule: RuleConfig
    matched: bool
    action: AgentAction
    hitl_required: HITLRequirement
    context: Dict[str, Any]
    priority: str = "P2"


@dataclass
class Decision:
    """A decision made by the engine."""
    action: AgentAction
    hitl_required: HITLRequirement
    priority: str
    rule_name: str
    context: Dict[str, Any]
    rationale: str


class DecisionEngine:
    """
    Evaluates rules and makes decisions for the agent.
    Uses a simple rule-based system with threshold evaluation.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the decision engine.

        Args:
            config: Agent configuration (uses singleton if None)
        """
        self.config = config or get_agent_config()
        self._rule_evaluators = self._build_evaluators()
        logger.info(f"DecisionEngine initialized with {len(self.config.rules)} rules")

    def evaluate_e14_form(self, form_data: Dict[str, Any]) -> List[Decision]:
        """
        Evaluate an E-14 form and return decisions.

        Args:
            form_data: E-14 form data with OCR results and validations

        Returns:
            List of decisions to execute
        """
        decisions = []
        context = self._build_e14_context(form_data)

        # Check arithmetic mismatch
        if self._check_arithmetic_mismatch(context):
            decisions.append(Decision(
                action=AgentAction.CREATE_INCIDENT,
                hitl_required=HITLRequirement.AUTOMATIC,
                priority="P0",
                rule_name="auto_incident_arithmetic",
                context={
                    'incident_type': 'ARITHMETIC_FAIL',
                    'mesa_id': context.get('mesa_id'),
                    'delta': context.get('arithmetic_delta'),
                    'expected': context.get('expected_total'),
                    'actual': context.get('actual_total'),
                },
                rationale=f"Arithmetic mismatch detected: delta={context.get('arithmetic_delta')}"
            ))

        # Check low OCR confidence
        if self._check_low_ocr_confidence(context):
            decisions.append(Decision(
                action=AgentAction.CREATE_INCIDENT,
                hitl_required=HITLRequirement.AUTOMATIC,
                priority="P1",
                rule_name="auto_incident_low_ocr",
                context={
                    'incident_type': 'OCR_LOW_CONF',
                    'mesa_id': context.get('mesa_id'),
                    'ocr_confidence': context.get('ocr_confidence'),
                    'low_confidence_fields': context.get('low_confidence_fields', []),
                },
                rationale=f"Low OCR confidence: {context.get('ocr_confidence'):.2%}"
            ))

        # Auto-classify CPACA if incident would be created
        if decisions:
            decisions.append(Decision(
                action=AgentAction.CLASSIFY_CPACA,
                hitl_required=HITLRequirement.AUTOMATIC,
                priority="P2",
                rule_name="auto_classify_cpaca",
                context={'mesa_id': context.get('mesa_id')},
                rationale="Auto-classify for legal tracking"
            ))

        return decisions

    def evaluate_incident(self, incident: Dict[str, Any]) -> List[Decision]:
        """
        Evaluate an incident and return decisions.

        Args:
            incident: Incident data

        Returns:
            List of decisions to execute
        """
        decisions = []
        context = self._build_incident_context(incident)

        # Check SLA warning
        sla_decision = self._check_sla_warning(context)
        if sla_decision:
            decisions.append(sla_decision)

        # Check escalation need
        escalation_decision = self._check_escalation_needed(context)
        if escalation_decision:
            decisions.append(escalation_decision)

        # Check nullity viability for legal incidents
        if context.get('escalated_to_legal'):
            nullity_decision = self._check_nullity_viability(context)
            if nullity_decision:
                decisions.append(nullity_decision)

        return decisions

    def evaluate_deadline(self, deadline_data: Dict[str, Any]) -> List[Decision]:
        """
        Evaluate a legal deadline and return decisions.

        Args:
            deadline_data: Deadline information

        Returns:
            List of decisions to execute
        """
        decisions = []
        context = self._build_deadline_context(deadline_data)

        # Check Art. 223 deadline
        if context.get('cpaca_article') == 223:
            hours_remaining = context.get('hours_remaining', 999)
            if hours_remaining < self.config.ART_223_WARNING_HOURS:
                decisions.append(Decision(
                    action=AgentAction.DISPATCH_SLA_ALERT,
                    hitl_required=HITLRequirement.AUTOMATIC,
                    priority="P0",
                    rule_name="art_223_deadline",
                    context={
                        'deadline_type': 'ART_223',
                        'hours_remaining': hours_remaining,
                        'incident_id': context.get('incident_id'),
                    },
                    rationale=f"Art. 223 deadline in {hours_remaining}h"
                ))

        # Check recount deadline
        if context.get('deadline_type') == 'RECOUNT':
            days_remaining = context.get('days_remaining', 999)
            if days_remaining < self.config.RECOUNT_WARNING_DAYS:
                decisions.append(Decision(
                    action=AgentAction.DISPATCH_SLA_ALERT,
                    hitl_required=HITLRequirement.AUTOMATIC,
                    priority="P1",
                    rule_name="recount_deadline",
                    context={
                        'deadline_type': 'RECOUNT',
                        'days_remaining': days_remaining,
                        'incident_id': context.get('incident_id'),
                    },
                    rationale=f"Recount deadline in {days_remaining} days"
                ))

        # Check nullity deadline
        if context.get('deadline_type') == 'NULLITY':
            days_remaining = context.get('days_remaining', 999)
            if days_remaining < self.config.NULLITY_WARNING_DAYS:
                decisions.append(Decision(
                    action=AgentAction.DISPATCH_SLA_ALERT,
                    hitl_required=HITLRequirement.AUTOMATIC,
                    priority="P1",
                    rule_name="nullity_deadline",
                    context={
                        'deadline_type': 'NULLITY',
                        'days_remaining': days_remaining,
                        'incident_id': context.get('incident_id'),
                    },
                    rationale=f"Nullity deadline in {days_remaining} days"
                ))

        return decisions

    def evaluate_geographic_cluster(
        self,
        municipality_code: str,
        anomalies: List[Dict[str, Any]],
        time_window_minutes: int = 60
    ) -> List[Decision]:
        """
        Evaluate geographic clustering of anomalies.

        Args:
            municipality_code: Municipality code
            anomalies: List of anomalies in the municipality
            time_window_minutes: Time window to consider

        Returns:
            List of decisions to execute
        """
        decisions = []

        # Filter recent anomalies
        cutoff = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_anomalies = [
            a for a in anomalies
            if datetime.fromisoformat(a.get('created_at', '2000-01-01')) > cutoff
        ]

        if len(recent_anomalies) >= self.config.GEOGRAPHIC_CLUSTER_THRESHOLD:
            decisions.append(Decision(
                action=AgentAction.CREATE_INCIDENT,
                hitl_required=HITLRequirement.AUTOMATIC,
                priority="P0",
                rule_name="geographic_cluster",
                context={
                    'incident_type': 'GEOGRAPHIC_CLUSTER',
                    'municipality_code': municipality_code,
                    'anomaly_count': len(recent_anomalies),
                    'time_window_minutes': time_window_minutes,
                    'anomaly_ids': [a.get('id') for a in recent_anomalies],
                },
                rationale=f"Geographic cluster: {len(recent_anomalies)} anomalies in {time_window_minutes}min"
            ))

            # Flag high risk
            decisions.append(Decision(
                action=AgentAction.UPDATE_RISK_SCORES,
                hitl_required=HITLRequirement.AUTOMATIC,
                priority="P1",
                rule_name="geographic_cluster",
                context={
                    'municipality_code': municipality_code,
                    'risk_level': 'HIGH',
                    'reason': 'geographic_cluster',
                },
                rationale="Update risk score due to geographic cluster"
            ))

        return decisions

    def should_generate_briefing(self, last_briefing_at: Optional[datetime]) -> bool:
        """
        Check if a new briefing should be generated.

        Args:
            last_briefing_at: Timestamp of last briefing

        Returns:
            True if new briefing should be generated
        """
        if not self.config.LLM_BRIEFINGS_ENABLED:
            return False

        if last_briefing_at is None:
            return True

        elapsed = (datetime.utcnow() - last_briefing_at).total_seconds() / 60
        return elapsed >= self.config.BRIEFING_INTERVAL_MINUTES

    # ============================================================
    # Private Helper Methods
    # ============================================================

    def _build_e14_context(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build context from E-14 form data."""
        header = form_data.get('document_header_extracted', {})
        validations = form_data.get('validations', [])

        # Calculate arithmetic delta
        total_computed = 0
        total_reported = 0
        for tally in form_data.get('normalized_tallies', []):
            if isinstance(tally, dict) and 'party_total' in tally:
                total_computed += tally.get('party_total', 0)

        # Get OCR confidence
        ocr_fields = form_data.get('ocr_fields', [])
        confidences = [f.get('confidence', 1.0) for f in ocr_fields if f.get('confidence')]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
        low_conf_fields = [f for f in ocr_fields if f.get('confidence', 1.0) < self.config.OCR_CONFIDENCE_THRESHOLD]

        # Check for arithmetic failures in validations
        arithmetic_delta = 0
        for v in validations:
            if v.get('rule_key') == 'ARITHMETIC_SUM' and not v.get('passed'):
                details = v.get('details', {})
                arithmetic_delta = abs(details.get('expected', 0) - details.get('actual', 0))

        return {
            'mesa_id': header.get('mesa_id') or f"{header.get('dept_code', '00')}-{header.get('muni_code', '000')}-{header.get('zone_code', '00')}-{header.get('station_code', '00')}-{header.get('table_number', 0):03d}",
            'dept_code': header.get('dept_code'),
            'muni_code': header.get('muni_code'),
            'ocr_confidence': avg_confidence,
            'low_confidence_fields': [f.get('field_key') for f in low_conf_fields],
            'arithmetic_delta': arithmetic_delta,
            'total_computed': total_computed,
            'validations_failed': [v for v in validations if not v.get('passed')],
        }

    def _build_incident_context(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Build context from incident data."""
        created_at = incident.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        sla_deadline = incident.get('sla_deadline')
        if isinstance(sla_deadline, str):
            sla_deadline = datetime.fromisoformat(sla_deadline)

        age_minutes = 0
        if created_at:
            age_minutes = (datetime.utcnow() - created_at).total_seconds() / 60

        sla_remaining = 999
        if sla_deadline:
            sla_remaining = (sla_deadline - datetime.utcnow()).total_seconds() / 60

        return {
            'incident_id': incident.get('id'),
            'incident_type': incident.get('incident_type'),
            'severity': incident.get('severity'),
            'status': incident.get('status'),
            'age_minutes': age_minutes,
            'sla_remaining_minutes': max(0, sla_remaining),
            'assigned_to': incident.get('assigned_to'),
            'escalated_to_legal': incident.get('escalated_to_legal', False),
            'delta_value': incident.get('delta_value'),
            'mesa_id': incident.get('mesa_id'),
        }

    def _build_deadline_context(self, deadline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build context from deadline data."""
        deadline = deadline_data.get('deadline')
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)

        hours_remaining = 999
        days_remaining = 999
        if deadline:
            delta = deadline - datetime.utcnow()
            hours_remaining = delta.total_seconds() / 3600
            days_remaining = delta.days

        return {
            'incident_id': deadline_data.get('incident_id'),
            'deadline_type': deadline_data.get('deadline_type'),
            'cpaca_article': deadline_data.get('cpaca_article'),
            'hours_remaining': hours_remaining,
            'days_remaining': days_remaining,
        }

    def _check_arithmetic_mismatch(self, context: Dict[str, Any]) -> bool:
        """Check if arithmetic mismatch exceeds threshold."""
        delta = context.get('arithmetic_delta', 0)
        return delta > self.config.ARITHMETIC_DELTA_THRESHOLD

    def _check_low_ocr_confidence(self, context: Dict[str, Any]) -> bool:
        """Check if OCR confidence is below threshold."""
        confidence = context.get('ocr_confidence', 1.0)
        return confidence < self.config.OCR_CONFIDENCE_THRESHOLD

    def _check_sla_warning(self, context: Dict[str, Any]) -> Optional[Decision]:
        """Check if SLA warning should be issued."""
        severity = context.get('severity', 'P3')
        sla_remaining = context.get('sla_remaining_minutes', 999)
        status = context.get('status', 'OPEN')

        # Skip if already resolved
        if status in ('RESOLVED', 'FALSE_POSITIVE'):
            return None

        warning_threshold = self.config.get_sla_warning_minutes(severity)

        if sla_remaining < warning_threshold:
            priority = "P0" if severity == "P0" else "P1"
            return Decision(
                action=AgentAction.DISPATCH_SLA_ALERT,
                hitl_required=HITLRequirement.AUTOMATIC,
                priority=priority,
                rule_name=f"sla_warning_{severity.lower()}",
                context={
                    'incident_id': context.get('incident_id'),
                    'severity': severity,
                    'sla_remaining_minutes': sla_remaining,
                },
                rationale=f"SLA breach imminent: {sla_remaining:.0f}min remaining"
            )

        return None

    def _check_escalation_needed(self, context: Dict[str, Any]) -> Optional[Decision]:
        """Check if incident should be escalated."""
        severity = context.get('severity', 'P3')
        age_minutes = context.get('age_minutes', 0)
        status = context.get('status', 'OPEN')
        escalated = context.get('escalated_to_legal', False)

        # Only escalate P0 incidents
        if severity != 'P0':
            return None

        # Skip if already resolved or escalated
        if status in ('RESOLVED', 'FALSE_POSITIVE', 'ESCALATED') or escalated:
            return None

        if age_minutes > self.config.HITL_AUTO_ESCALATE_AFTER_MINUTES:
            return Decision(
                action=AgentAction.ESCALATE_TO_LEGAL,
                hitl_required=HITLRequirement.SEMI_AUTOMATIC,
                priority="P0",
                rule_name="escalate_to_legal",
                context={
                    'incident_id': context.get('incident_id'),
                    'age_minutes': age_minutes,
                    'severity': severity,
                },
                rationale=f"P0 incident unresolved for {age_minutes:.0f}min"
            )

        return None

    def _check_nullity_viability(self, context: Dict[str, Any]) -> Optional[Decision]:
        """Check if nullity recommendation should be made."""
        # This would normally calculate viability based on legal criteria
        # For now, check if delta is significant
        delta = context.get('delta_value', 0)
        if delta and delta > 500:
            return Decision(
                action=AgentAction.RECOMMEND_NULLITY,
                hitl_required=HITLRequirement.SEMI_AUTOMATIC,
                priority="P1",
                rule_name="nullity_recommendation",
                context={
                    'incident_id': context.get('incident_id'),
                    'affected_votes': delta,
                },
                rationale=f"High vote impact: {delta} votes affected"
            )
        return None

    def _build_evaluators(self) -> Dict[str, callable]:
        """Build rule evaluator functions."""
        # For simple threshold-based rules, we use the check methods above
        # More complex rules could be added here
        return {}
