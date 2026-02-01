"""
High-level LLM Service for CASTOR ELECCIONES.
Uses the LLM abstraction layer to provide campaign-specific functionality.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from services.llm import get_llm, LLMConfig, LLMMessage, LLMProvider, BaseLLMProvider
from utils.cache import TTLCache
from config import Config
from .llm_prompts import (
    POLITICAL_ANALYST_SYSTEM,
    POLITICAL_STRATEGIST_SYSTEM,
    SPEECH_WRITER_SYSTEM,
    MEDIA_ANALYST_SYSTEM,
    CAMPAIGN_ASSISTANT_SYSTEM,
    ADVISOR_SYSTEM,
    build_executive_summary_prompt,
    build_strategic_plan_prompt,
    build_speech_prompt,
    build_trending_context,
    build_media_summary_prompt,
    build_advisor_prompt,
    get_executive_summary_fallback,
    get_strategic_plan_fallback,
    get_speech_fallback,
    get_media_summary_fallback,
    get_advisor_fallback,
)

logger = logging.getLogger(__name__)


class LLMService:
    """High-level service for LLM interactions in CASTOR."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        """Initialize LLM Service."""
        self._provider_type = provider
        self._llm: Optional[BaseLLMProvider] = None
        self._content_cache = TTLCache(
            ttl_seconds=Config.OPENAI_CACHE_TTL,
            max_size=Config.CACHE_MAX_SIZE
        )

    @property
    def llm(self) -> BaseLLMProvider:
        """Lazy initialization of LLM provider."""
        if self._llm is None:
            self._llm = get_llm(self._provider_type)
        return self._llm

    def generate_executive_summary(
        self,
        location: str,
        analysis_context: str,
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate executive summary from analysis context."""
        cache_key = f"exec_summary:{location.lower()}:{(candidate_name or '').lower()}"
        cached = self._content_cache.get(cache_key)
        if cached:
            return cached

        messages = [
            LLMMessage(role="system", content=POLITICAL_ANALYST_SYSTEM),
            LLMMessage(
                role="user",
                content=build_executive_summary_prompt(location, analysis_context, candidate_name)
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.7)
            result = self.llm.complete_json(messages, config)
            self._content_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}", exc_info=True)
            return get_executive_summary_fallback(location)

    def generate_strategic_plan(
        self,
        location: str,
        analysis_context: str,
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate strategic plan from analysis context."""
        messages = [
            LLMMessage(role="system", content=POLITICAL_STRATEGIST_SYSTEM),
            LLMMessage(
                role="user",
                content=build_strategic_plan_prompt(location, analysis_context, candidate_name)
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.7)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating strategic plan: {e}", exc_info=True)
            return get_strategic_plan_fallback()

    def generate_speech(
        self,
        location: str,
        candidate_name: str,
        analysis_context: str,
        trending_topic: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate personalized speech for candidate."""
        trending_context = build_trending_context(trending_topic)

        messages = [
            LLMMessage(role="system", content=SPEECH_WRITER_SYSTEM),
            LLMMessage(
                role="user",
                content=build_speech_prompt(location, candidate_name, analysis_context, trending_context)
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.8)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            return get_speech_fallback(location)

    def generate_media_summary(self, stats_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate neutral media summary."""
        messages = [
            LLMMessage(role="system", content=MEDIA_ANALYST_SYSTEM),
            LLMMessage(role="user", content=build_media_summary_prompt(stats_context))
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.4)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating media summary: {e}", exc_info=True)
            return get_media_summary_fallback()

    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Chat with LLM as campaign assistant."""
        user_prompt = message
        if context:
            user_prompt += f"\n\nContexto adicional: {json.dumps(context, ensure_ascii=False)}"

        try:
            return self.llm.chat(user_prompt, CAMPAIGN_ASSISTANT_SYSTEM)
        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return "Lo siento, hubo un error procesando tu mensaje."

    def generate_advisor_recommendations(
        self,
        location: str,
        topics: List[str],
        profile: Dict[str, Any],
        goals: List[str],
        constraints: List[str],
        source_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate advisor draft recommendations."""
        topics_str = ", ".join(topics) if topics else "tema general"
        goals_str = ", ".join(goals) if goals else "claridad narrativa"
        constraints_str = ", ".join(constraints) if constraints else "evitar ataques personales"

        messages = [
            LLMMessage(role="system", content=ADVISOR_SYSTEM),
            LLMMessage(
                role="user",
                content=build_advisor_prompt(
                    location, topics_str, profile, goals_str, constraints_str, source_summary
                )
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.6)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating advisor recommendations: {e}", exc_info=True)
            return get_advisor_fallback(topics_str)

    def _get_model(self) -> str:
        """Get the model name for the current provider."""
        if self._provider_type == LLMProvider.CLAUDE:
            return Config.CLAUDE_MODEL
        elif self._provider_type == LLMProvider.LOCAL:
            return Config.LOCAL_LLM_MODEL
        return Config.OPENAI_MODEL


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service(provider: Optional[LLMProvider] = None) -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None or provider is not None:
        _llm_service = LLMService(provider)
    return _llm_service
