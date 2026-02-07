"""
Actuators for the Electoral Intelligence Agent.
These components execute actions decided by the agent.
"""
from services.agent.actuators.incident_creator import IncidentCreator
from services.agent.actuators.alert_dispatcher import AlertDispatcher
from services.agent.actuators.report_generator import ReportGenerator
from services.agent.actuators.hitl_escalator import HITLEscalator

__all__ = ['IncidentCreator', 'AlertDispatcher', 'ReportGenerator', 'HITLEscalator']
