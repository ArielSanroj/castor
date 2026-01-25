"""
High-level LLM Service for CASTOR ELECCIONES.
Uses the LLM abstraction layer to provide campaign-specific functionality.

This service can work with any LLM provider (OpenAI, Claude, Local)
by using the unified interface.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from services.llm import get_llm, LLMConfig, LLMMessage, LLMProvider, BaseLLMProvider
from utils.cache import TTLCache
from config import Config

logger = logging.getLogger(__name__)


class LLMService:
    """
    High-level service for LLM interactions in CASTOR.

    Provides campaign-specific methods that work with any LLM provider.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        """
        Initialize LLM Service.

        Args:
            provider: Specific provider to use, or None for default
        """
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
        """
        Generate executive summary from analysis context.

        Args:
            location: Location analyzed
            analysis_context: Formatted analysis context
            candidate_name: Optional candidate name

        Returns:
            Dict with overview, key_findings, recommendations
        """
        cache_key = f"exec_summary:{location.lower()}:{(candidate_name or '').lower()}"
        cached = self._content_cache.get(cache_key)
        if cached:
            return cached

        messages = [
            LLMMessage(
                role="system",
                content="Eres un experto en analisis politico y estrategia electoral. Responde siempre en espanol y formato JSON valido."
            ),
            LLMMessage(
                role="user",
                content=f"""Eres CASTOR ELECCIONES, una herramienta de inteligencia artificial para campanas electorales.

Analiza los siguientes datos de sentimiento ciudadano en {location} y genera un resumen ejecutivo profesional.

Datos analizados:
{analysis_context}

Candidato: {candidate_name or 'el candidato'}

Genera un resumen ejecutivo en espanol con:
1. Una vision general (2-3 parrafos) del clima politico actual
2. Los 3-5 hallazgos clave mas importantes
3. Las 3-5 recomendaciones estrategicas prioritarias

Formato de respuesta JSON:
{{
    "overview": "texto del resumen general",
    "key_findings": ["hallazgo 1", "hallazgo 2", ...],
    "recommendations": ["recomendacion 1", "recomendacion 2", ...]
}}"""
            )
        ]

        try:
            config = LLMConfig(
                model=self._get_model(),
                temperature=0.7
            )
            result = self.llm.complete_json(messages, config)
            self._content_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}", exc_info=True)
            return {
                "overview": f"Analisis de sentimiento ciudadano en {location}.",
                "key_findings": ["Analisis completado con datos disponibles"],
                "recommendations": ["Continuar monitoreo de redes sociales"]
            }

    def generate_strategic_plan(
        self,
        location: str,
        analysis_context: str,
        candidate_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate strategic plan from analysis context.

        Args:
            location: Location analyzed
            analysis_context: Formatted analysis context
            candidate_name: Optional candidate name

        Returns:
            Dict with objectives, actions, timeline, expected_impact
        """
        messages = [
            LLMMessage(
                role="system",
                content="Eres un estratega politico experto. Responde en espanol y formato JSON valido."
            ),
            LLMMessage(
                role="user",
                content=f"""Eres CASTOR ELECCIONES. Genera un plan estrategico electoral profesional.

Ubicacion: {location}
Candidato: {candidate_name or 'el candidato'}

Datos de analisis:
{analysis_context}

Genera un plan estrategico en espanol con:
1. 3-5 objetivos estrategicos claros y medibles
2. Acciones concretas para cada objetivo
3. Timeline propuesto (corto, mediano, largo plazo)
4. Impacto esperado

Formato JSON:
{{
    "objectives": ["objetivo 1", ...],
    "actions": [{{"action": "...", "priority": "alta/media/baja", "topic": "..."}}, ...],
    "timeline": "descripcion del timeline",
    "expected_impact": "descripcion del impacto esperado"
}}"""
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.7)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating strategic plan: {e}", exc_info=True)
            return {
                "objectives": ["Mejorar comunicacion con ciudadanos"],
                "actions": [{"action": "Monitoreo continuo", "priority": "alta", "topic": "General"}],
                "timeline": "3-6 meses",
                "expected_impact": "Mejora en engagement"
            }

    def generate_speech(
        self,
        location: str,
        candidate_name: str,
        analysis_context: str,
        trending_topic: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized speech for candidate.

        Args:
            location: Location
            candidate_name: Candidate name
            analysis_context: Formatted analysis context
            trending_topic: Optional trending topic data

        Returns:
            Dict with title, content, key_points, duration_minutes
        """
        trending_context = ""
        if trending_topic:
            trending_context = f"""
TEMA TRENDING DEL MOMENTO:
- Tema: {trending_topic.get('topic', 'N/A')}
- Engagement: {trending_topic.get('engagement_score', 0):.0f}
- Sentimiento: {trending_topic.get('sentiment_positive', 0):.2%} positivo

IMPORTANTE: El discurso DEBE mencionar este tema trending.
"""

        messages = [
            LLMMessage(
                role="system",
                content="Eres un escritor de discursos politicos experto. Escribe en espanol, tono profesional pero cercano."
            ),
            LLMMessage(
                role="user",
                content=f"""Genera un discurso electoral profesional.

Candidato: {candidate_name}
Ubicacion: {location}

Datos de analisis:
{analysis_context}
{trending_context}

Genera un discurso completo en espanol que:
- Sea inspirador y conecte emocionalmente
- Mencione las necesidades reales identificadas
- Incluya propuestas concretas
- Sea apropiado para 5-10 minutos

Formato JSON:
{{
    "title": "Titulo del discurso",
    "content": "Texto completo del discurso",
    "key_points": ["punto 1", "punto 2", ...],
    "duration_minutes": 7
}}"""
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.8)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            return {
                "title": f"Discurso para {location}",
                "content": f"Queridos ciudadanos de {location}...",
                "key_points": ["Compromiso con la comunidad"],
                "duration_minutes": 5
            }

    def generate_media_summary(
        self,
        stats_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate neutral media summary.

        Args:
            stats_context: Statistics and context data

        Returns:
            Dict with overview, key_stats, key_findings
        """
        messages = [
            LLMMessage(
                role="system",
                content="Eres un analista de datos para un medio de comunicacion. Resumes conversacion en X/Twitter de forma descriptiva, neutral y no partidista."
            ),
            LLMMessage(
                role="user",
                content=f"""Genera un JSON con la forma:
{{"overview": "...", "key_stats": ["..."], "key_findings": ["..."]}}

Solo descripcion de lo que ocurrio, sin recomendaciones.

Datos:
{json.dumps(stats_context, ensure_ascii=False, indent=2)}"""
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.4)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating media summary: {e}", exc_info=True)
            return {
                "overview": "Resumen no disponible.",
                "key_stats": [],
                "key_findings": []
            }

    def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Chat with LLM as campaign assistant.

        Args:
            message: User message
            context: Optional context dictionary

        Returns:
            AI response
        """
        system_prompt = """Eres CASTOR ELECCIONES, un asistente de IA especializado en campanas electorales en Colombia.

Tu funcion es ayudar con:
- Estrategias electorales
- Ideas de discursos
- Analisis de sentimiento
- Consejos de campana

Responde siempre en espanol, de manera profesional pero cercana."""

        user_prompt = message
        if context:
            user_prompt += f"\n\nContexto adicional: {json.dumps(context, ensure_ascii=False)}"

        try:
            return self.llm.chat(user_prompt, system_prompt)
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
        topics_str = ", ".join(topics) if topics else "tema general"
        goals_str = ", ".join(goals) if goals else "claridad narrativa"
        constraints_str = ", ".join(constraints) if constraints else "evitar ataques personales"

        messages = [
            LLMMessage(
                role="system",
                content="Eres un asesor de comunicacion politica. Genera borradores para revision humana, sin automatizar publicaciones."
            ),
            LLMMessage(
                role="user",
                content=f"""Genera borradores sugeridos para un humano.

Contexto:
- Ubicacion: {location}
- Temas: {topics_str}
- Perfil: nombre={profile.get('name', 'candidato')}, rol={profile.get('role', 'candidato')}, tono={profile.get('tone', 'profesional')}
- Valores: {", ".join(profile.get('values', ['transparencia']))}
- Lineas rojas: {", ".join(profile.get('red_lines', ['desinformacion']))}
- Objetivos: {goals_str}
- Restricciones: {constraints_str}
- Contexto: {source_summary or "no disponible"}

Entrega 2-4 borradores tipo post y 1-2 tipo comentario.

Formato JSON:
{{
  "guidance": "nota breve de uso responsable",
  "drafts": [
    {{
      "kind": "post",
      "intent": "informar",
      "draft": "texto...",
      "rationale": "por que ayuda",
      "risk_level": "bajo",
      "best_time": "manana o tarde"
    }}
  ]
}}"""
            )
        ]

        try:
            config = LLMConfig(model=self._get_model(), temperature=0.6)
            return self.llm.complete_json(messages, config)
        except Exception as e:
            logger.error(f"Error generating advisor recommendations: {e}", exc_info=True)
            return {
                "guidance": "Revisar antes de publicar.",
                "drafts": [{
                    "kind": "post",
                    "intent": "informar",
                    "draft": f"Hoy el tema {topics_str} concentra la conversacion.",
                    "rationale": "Mantiene tono institucional.",
                    "risk_level": "bajo",
                    "best_time": "tarde"
                }]
            }

    def _get_model(self) -> str:
        """Get the model name for the current provider."""
        if self._provider_type == LLMProvider.CLAUDE:
            return Config.CLAUDE_MODEL
        elif self._provider_type == LLMProvider.LOCAL:
            return Config.LOCAL_LLM_MODEL
        return Config.OPENAI_MODEL


# Singleton instance for convenience
_llm_service: Optional[LLMService] = None


def get_llm_service(provider: Optional[LLMProvider] = None) -> LLMService:
    """
    Get or create LLM service instance.

    Args:
        provider: Specific provider to use

    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None or provider is not None:
        _llm_service = LLMService(provider)
    return _llm_service
