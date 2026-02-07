"""
Electoral Intelligence Agent - Agente de Inteligencia Electoral.

Monitorea dashboards de Contienda Electoral y Litigio Electoral,
detecta anomalias, patrones y situaciones criticas, y toma acciones
que generan valor medible.
"""
from services.agent.electoral_intelligence_agent import ElectoralIntelligenceAgent
from services.agent.config import AgentConfig
from services.agent.state import AgentState

__all__ = ['ElectoralIntelligenceAgent', 'AgentConfig', 'AgentState']
