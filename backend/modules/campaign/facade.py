"""
Campaign Module Facade.

Provides content generation and strategic planning for campaigns.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CampaignModule:
    """
    Facade for campaign operations.

    Provides content generation, strategic planning, and advisor features.
    Uses the LLM abstraction layer for provider flexibility.

    Usage:
        module = CampaignModule()
        summary = module.generate_executive_summary(
            location="Bogota",
            context="...",
            candidate_name="Juan"
        )
    """

    def __init__(self, llm_provider: Optional[str] = None):
        """
        Initialize campaign module.

        Args:
            llm_provider: Optional LLM provider override ('openai', 'claude', 'local')
        """
        self._llm_service = None
        self._llm_provider = llm_provider

    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from services.llm_service import LLMService
                from services.llm import LLMProvider

                provider = None
                if self._llm_provider:
                    provider_map = {
                        'openai': LLMProvider.OPENAI,
                        'claude': LLMProvider.CLAUDE,
                        'local': LLMProvider.LOCAL,
                    }
                    provider = provider_map.get(self._llm_provider)

                self._llm_service = LLMService(provider)
            except Exception as e:
                logger.error(f"Failed to initialize LLM service: {e}")
        return self._llm_service

    def generate_executive_summary(
        self,
        location: str,
        analysis_context: str,
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate executive summary.

        Args:
            location: Location analyzed
            analysis_context: Formatted analysis context
            candidate_name: Optional candidate name

        Returns:
            Dict with overview, key_findings, recommendations
        """
        llm = self._get_llm_service()
        if not llm:
            return self._fallback_summary(location)

        return llm.generate_executive_summary(
            location=location,
            analysis_context=analysis_context,
            candidate_name=candidate_name
        )

    def generate_strategic_plan(
        self,
        location: str,
        analysis_context: str,
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate strategic plan.

        Args:
            location: Location analyzed
            analysis_context: Formatted analysis context
            candidate_name: Optional candidate name

        Returns:
            Dict with objectives, actions, timeline, expected_impact
        """
        llm = self._get_llm_service()
        if not llm:
            return self._fallback_plan()

        return llm.generate_strategic_plan(
            location=location,
            analysis_context=analysis_context,
            candidate_name=candidate_name
        )

    def generate_speech(
        self,
        location: str,
        candidate_name: str,
        analysis_context: str,
        trending_topic: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized speech.

        Args:
            location: Location
            candidate_name: Candidate name
            analysis_context: Formatted analysis context
            trending_topic: Optional trending topic data

        Returns:
            Dict with title, content, key_points, duration_minutes
        """
        llm = self._get_llm_service()
        if not llm:
            return self._fallback_speech(location, candidate_name)

        return llm.generate_speech(
            location=location,
            candidate_name=candidate_name,
            analysis_context=analysis_context,
            trending_topic=trending_topic
        )

    def generate_advisor_recommendations(
        self,
        location: str,
        topics: List[str],
        profile: Dict[str, Any],
        goals: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        source_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate advisor draft recommendations.

        Args:
            location: Location
            topics: Topics to address
            profile: Candidate profile
            goals: Campaign goals
            constraints: Constraints to respect
            source_summary: Optional context summary

        Returns:
            Dict with guidance and drafts
        """
        llm = self._get_llm_service()
        if not llm:
            return self._fallback_advisor(topics)

        return llm.generate_advisor_recommendations(
            location=location,
            topics=topics,
            profile=profile,
            goals=goals or [],
            constraints=constraints or [],
            source_summary=source_summary
        )

    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Chat with campaign assistant.

        Args:
            message: User message
            context: Optional context

        Returns:
            Assistant response
        """
        llm = self._get_llm_service()
        if not llm:
            return "Lo siento, el asistente no esta disponible."

        return llm.chat(message, context)

    # Fallback methods
    def _fallback_summary(self, location: str) -> Dict[str, Any]:
        return {
            "overview": f"Analisis de sentimiento ciudadano en {location}.",
            "key_findings": ["Analisis completado"],
            "recommendations": ["Continuar monitoreo"]
        }

    def _fallback_plan(self) -> Dict[str, Any]:
        return {
            "objectives": ["Mejorar comunicacion"],
            "actions": [{"action": "Monitoreo", "priority": "alta", "topic": "General"}],
            "timeline": "3-6 meses",
            "expected_impact": "Mejora en engagement"
        }

    def _fallback_speech(self, location: str, candidate_name: str) -> Dict[str, Any]:
        return {
            "title": f"Discurso para {location}",
            "content": f"Queridos ciudadanos de {location}...",
            "key_points": ["Compromiso con la comunidad"],
            "duration_minutes": 5
        }

    def _fallback_advisor(self, topics: List[str]) -> Dict[str, Any]:
        return {
            "guidance": "Revisar antes de publicar.",
            "drafts": [{
                "kind": "post",
                "intent": "informar",
                "draft": f"El tema {', '.join(topics)} es relevante.",
                "rationale": "Tono institucional.",
                "risk_level": "bajo",
                "best_time": "tarde"
            }]
        }
