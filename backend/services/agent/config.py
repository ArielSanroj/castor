"""
Configuration for the Electoral Intelligence Agent.
All thresholds and intervals are configurable via environment variables.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


class AgentAction(str, Enum):
    """Actions the agent can take."""
    CREATE_INCIDENT = "create_incident"
    DISPATCH_SLA_ALERT = "dispatch_sla_alert"
    CLASSIFY_CPACA = "classify_cpaca"
    CALCULATE_NULLITY_VIABILITY = "calculate_nullity_viability"
    TRACK_DEADLINE = "track_deadline"
    GENERATE_HOURLY_BRIEF = "generate_hourly_brief"
    UPDATE_RISK_SCORES = "update_risk_scores"
    ESCALATE_TO_LEGAL = "escalate_to_legal"
    RECOMMEND_NULLITY = "recommend_nullity"
    GENERATE_EVIDENCE_PACKAGE = "generate_evidence_package"
    MASS_INCIDENT_CREATION = "mass_incident_creation"
    CONTACT_WITNESS = "contact_witness"
    SUGGEST_RECOUNT = "suggest_recount"
    PRIORITIZE_REVIEWS = "prioritize_reviews"
    DEPLOY_WITNESSES = "deploy_witnesses"


class HITLRequirement(str, Enum):
    """Whether an action requires human-in-the-loop approval."""
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi_automatic"
    RECOMMENDATION = "recommendation"


@dataclass
class RuleConfig:
    """Configuration for an agent decision rule."""
    name: str
    condition: str
    action: AgentAction
    hitl_required: HITLRequirement = HITLRequirement.AUTOMATIC
    description: str = ""


@dataclass
class AgentConfig:
    """Configuration for the Electoral Intelligence Agent."""

    # Polling intervals (seconds)
    E14_POLL_INTERVAL: int = int(os.getenv('AGENT_E14_POLL_INTERVAL', '30'))
    INCIDENT_POLL_INTERVAL: int = int(os.getenv('AGENT_INCIDENT_POLL_INTERVAL', '15'))
    KPI_POLL_INTERVAL: int = int(os.getenv('AGENT_KPI_POLL_INTERVAL', '60'))
    DEADLINE_POLL_INTERVAL: int = int(os.getenv('AGENT_DEADLINE_POLL_INTERVAL', '60'))

    # Detection thresholds
    OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv('AGENT_OCR_CONFIDENCE_THRESHOLD', '0.70'))
    ANOMALY_SCORE_THRESHOLD: float = float(os.getenv('AGENT_ANOMALY_SCORE_THRESHOLD', '0.80'))
    NULLITY_VIABILITY_THRESHOLD: float = float(os.getenv('AGENT_NULLITY_VIABILITY_THRESHOLD', '0.70'))
    ARITHMETIC_DELTA_THRESHOLD: int = int(os.getenv('AGENT_ARITHMETIC_DELTA_THRESHOLD', '1'))

    # Geographic clustering
    GEOGRAPHIC_CLUSTER_THRESHOLD: int = int(os.getenv('AGENT_GEOGRAPHIC_CLUSTER_THRESHOLD', '5'))
    GEOGRAPHIC_CLUSTER_WINDOW_MINUTES: int = int(os.getenv('AGENT_GEOGRAPHIC_CLUSTER_WINDOW_MINUTES', '60'))

    # SLA warnings (minutes before breach)
    SLA_WARNING_P0: int = int(os.getenv('AGENT_SLA_WARNING_P0', '5'))
    SLA_WARNING_P1: int = int(os.getenv('AGENT_SLA_WARNING_P1', '10'))
    SLA_WARNING_P2: int = int(os.getenv('AGENT_SLA_WARNING_P2', '15'))

    # Legal deadlines (hours)
    ART_223_WARNING_HOURS: int = int(os.getenv('AGENT_ART_223_WARNING_HOURS', '12'))
    RECOUNT_WARNING_DAYS: int = int(os.getenv('AGENT_RECOUNT_WARNING_DAYS', '2'))
    NULLITY_WARNING_DAYS: int = int(os.getenv('AGENT_NULLITY_WARNING_DAYS', '7'))

    # HITL settings
    HITL_AUTO_ESCALATE_AFTER_MINUTES: int = int(os.getenv('AGENT_HITL_AUTO_ESCALATE_MINUTES', '30'))
    HITL_MAX_PENDING: int = int(os.getenv('AGENT_HITL_MAX_PENDING', '100'))

    # Briefing settings
    BRIEFING_INTERVAL_MINUTES: int = int(os.getenv('AGENT_BRIEFING_INTERVAL_MINUTES', '60'))
    BRIEFING_MAX_LATENCY_MINUTES: int = int(os.getenv('AGENT_BRIEFING_MAX_LATENCY_MINUTES', '2'))

    # Feature flags
    AUTO_INCIDENT_CREATION: bool = os.getenv('AGENT_AUTO_INCIDENT_CREATION', 'true').lower() == 'true'
    AUTO_LEGAL_CLASSIFICATION: bool = os.getenv('AGENT_AUTO_LEGAL_CLASSIFICATION', 'true').lower() == 'true'
    AUTO_RISK_SCORING: bool = os.getenv('AGENT_AUTO_RISK_SCORING', 'true').lower() == 'true'
    LLM_BRIEFINGS_ENABLED: bool = os.getenv('AGENT_LLM_BRIEFINGS_ENABLED', 'true').lower() == 'true'

    # Redis keys
    REDIS_STATE_KEY: str = "agent:state"
    REDIS_METRICS_KEY: str = "agent:metrics"
    REDIS_HITL_QUEUE_KEY: str = "agent:hitl:queue"
    REDIS_ACTIONS_LOG_KEY: str = "agent:actions:log"

    # Decision rules
    rules: List[RuleConfig] = field(default_factory=list)

    def __post_init__(self):
        """Initialize default rules after dataclass creation."""
        if not self.rules:
            self.rules = self._get_default_rules()

    def _get_default_rules(self) -> List[RuleConfig]:
        """Get default decision rules for the agent."""
        return [
            # Contienda Electoral rules
            RuleConfig(
                name="auto_incident_arithmetic",
                condition="anomaly.type == ARITHMETIC_MISMATCH AND anomaly.delta > ARITHMETIC_DELTA_THRESHOLD",
                action=AgentAction.CREATE_INCIDENT,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Auto-create P0 incident for arithmetic mismatches"
            ),
            RuleConfig(
                name="auto_incident_low_ocr",
                condition="form.ocr_confidence < OCR_CONFIDENCE_THRESHOLD",
                action=AgentAction.CREATE_INCIDENT,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Auto-create P1 incident for low OCR confidence"
            ),
            RuleConfig(
                name="sla_warning_p0",
                condition="incident.severity == P0 AND sla_remaining < SLA_WARNING_P0",
                action=AgentAction.DISPATCH_SLA_ALERT,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Dispatch critical alert when P0 SLA is about to breach"
            ),
            RuleConfig(
                name="sla_warning_p1",
                condition="incident.severity == P1 AND sla_remaining < SLA_WARNING_P1",
                action=AgentAction.DISPATCH_SLA_ALERT,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Dispatch warning when P1 SLA is about to breach"
            ),
            RuleConfig(
                name="escalate_to_legal",
                condition="incident.severity == P0 AND incident.age > HITL_AUTO_ESCALATE_AFTER_MINUTES AND NOT resolved",
                action=AgentAction.ESCALATE_TO_LEGAL,
                hitl_required=HITLRequirement.SEMI_AUTOMATIC,
                description="Escalate unresolved P0 incidents to legal team"
            ),

            # Litigio Electoral rules
            RuleConfig(
                name="art_223_deadline",
                condition="cpaca_article == 223 AND deadline_hours < ART_223_WARNING_HOURS",
                action=AgentAction.DISPATCH_SLA_ALERT,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Alert on Art. 223 deadline approaching"
            ),
            RuleConfig(
                name="nullity_recommendation",
                condition="nullity_viability > NULLITY_VIABILITY_THRESHOLD AND affected_votes > 500",
                action=AgentAction.RECOMMEND_NULLITY,
                hitl_required=HITLRequirement.SEMI_AUTOMATIC,
                description="Recommend nullity action when viability is high"
            ),
            RuleConfig(
                name="geographic_cluster",
                condition="anomalies_in_municipality > GEOGRAPHIC_CLUSTER_THRESHOLD AND time_window < GEOGRAPHIC_CLUSTER_WINDOW_MINUTES",
                action=AgentAction.CREATE_INCIDENT,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Create cluster alert for geographic anomaly concentration"
            ),

            # Auto-classification
            RuleConfig(
                name="auto_classify_cpaca",
                condition="incident.created AND NOT incident.cpaca_classified",
                action=AgentAction.CLASSIFY_CPACA,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Auto-classify incidents by CPACA article"
            ),

            # Briefings
            RuleConfig(
                name="hourly_briefing",
                condition="time_since_last_briefing > BRIEFING_INTERVAL_MINUTES",
                action=AgentAction.GENERATE_HOURLY_BRIEF,
                hitl_required=HITLRequirement.AUTOMATIC,
                description="Generate hourly intelligence briefing"
            ),
        ]

    def get_sla_warning_minutes(self, severity: str) -> int:
        """Get SLA warning threshold for a given severity."""
        thresholds = {
            'P0': self.SLA_WARNING_P0,
            'P1': self.SLA_WARNING_P1,
            'P2': self.SLA_WARNING_P2,
            'P3': 30,  # Default
        }
        return thresholds.get(severity, 30)


# Singleton instance
_config_instance: AgentConfig = None


def get_agent_config() -> AgentConfig:
    """Get singleton agent configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = AgentConfig()
    return _config_instance
