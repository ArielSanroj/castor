"""
OpenAI API service for content generation.
Handles GPT-4o interactions for reports, speeches, and chat.
"""
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import openai

from config import Config
from utils.circuit_breaker import (
    get_openai_circuit_breaker,
    exponential_backoff,
    CircuitBreakerOpenError
)
from models.schemas import ExecutiveSummary, StrategicPlan, Speech, PNDTopicAnalysis
from app.schemas.core import CoreAnalysisResult
from app.schemas.media import MediaAnalysisSummary
from app.schemas.advisor import AdvisorRequest, AdvisorResponse
from utils.cache import TTLCache
from .openai_prompts import (
    POLITICAL_ANALYST_SYSTEM,
    POLITICAL_STRATEGIST_SYSTEM,
    SPEECH_WRITER_SYSTEM,
    MEDIA_ANALYST_SYSTEM,
    CAMPAIGN_ASSISTANT_SYSTEM,
    build_executive_summary_prompt,
    build_strategic_plan_prompt,
    build_speech_prompt,
    build_trending_context,
    build_media_summary_prompt
)
from .openai_advisor import AdvisorGenerator

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API interactions."""

    def __init__(self):
        """Initialize OpenAI client."""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            timeout=Config.OPENAI_TIMEOUT_SECONDS
        )
        self.model = Config.OPENAI_MODEL
        self._content_cache = TTLCache(
            ttl_seconds=Config.OPENAI_CACHE_TTL,
            max_size=Config.CACHE_MAX_SIZE
        )
        self._circuit_breaker = get_openai_circuit_breaker()
        self._advisor = AdvisorGenerator(self._make_json_completion)
        logger.info(f"OpenAIService initialized with model: {self.model}")

    @exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exceptions=(openai.APIError, openai.APITimeoutError, openai.RateLimitError)
    )
    def _call_openai_api(self, call_func: Callable) -> Any:
        """Execute OpenAI API call with circuit breaker and retry logic."""
        try:
            return self._circuit_breaker.call(call_func)
        except CircuitBreakerOpenError:
            logger.error("OpenAI circuit breaker is OPEN, rejecting request")
            raise
        except (openai.APIError, openai.APITimeoutError, openai.RateLimitError) as e:
            logger.warning(f"OpenAI API error: {e}")
            raise

    def _make_json_completion(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Make OpenAI API call expecting JSON response."""
        def _make_api_call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )

        response = self._call_openai_api(_make_api_call)
        return json.loads(response.choices[0].message.content)

    def _make_text_completion(self, system: str, prompt: str, temperature: float = 0.7) -> str:
        """Make OpenAI API call expecting text response."""
        def _make_api_call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )

        response = self._call_openai_api(_make_api_call)
        return response.choices[0].message.content

    def generate_executive_summary(
        self,
        location: str,
        topic_analyses: List[PNDTopicAnalysis],
        candidate_name: Optional[str] = None
    ) -> ExecutiveSummary:
        """Generate executive summary from topic analyses."""
        cache_key, cached = self._check_cache('exec_summary', location, candidate_name, topic_analyses)
        if cached:
            return ExecutiveSummary(**cached)

        try:
            context = self._build_analysis_context(topic_analyses)
            prompt = build_executive_summary_prompt(location, context, candidate_name)
            result = self._make_json_completion(POLITICAL_ANALYST_SYSTEM, prompt)

            summary = ExecutiveSummary(
                overview=result.get('overview', ''),
                key_findings=result.get('key_findings', []),
                recommendations=result.get('recommendations', [])
            )
            self._content_cache.set(cache_key, summary.dict())
            return summary

        except Exception as e:
            logger.error(f"Error generating executive summary: {e}", exc_info=True)
            return self._fallback_executive_summary(location)

    def _fallback_executive_summary(self, location: str) -> ExecutiveSummary:
        """Return fallback executive summary on error."""
        return ExecutiveSummary(
            overview=f"Análisis de sentimiento ciudadano en {location} basado en datos de redes sociales.",
            key_findings=["Análisis completado con datos disponibles", "Se requiere más información para insights profundos"],
            recommendations=["Continuar monitoreo de redes sociales", "Ampliar búsqueda de datos"]
        )

    def generate_strategic_plan(
        self,
        location: str,
        topic_analyses: List[PNDTopicAnalysis],
        candidate_name: Optional[str] = None
    ) -> StrategicPlan:
        """Generate strategic plan from analyses."""
        cache_key, cached = self._check_cache('strategic_plan', location, candidate_name, topic_analyses)
        if cached:
            return StrategicPlan(**cached)

        try:
            context = self._build_analysis_context(topic_analyses)
            prompt = build_strategic_plan_prompt(location, context, candidate_name)
            result = self._make_json_completion(POLITICAL_STRATEGIST_SYSTEM, prompt)

            plan = StrategicPlan(
                objectives=result.get('objectives', []),
                actions=result.get('actions', []),
                timeline=result.get('timeline', '3-6 meses'),
                expected_impact=result.get('expected_impact', 'Mejora en percepción ciudadana')
            )
            self._content_cache.set(cache_key, plan.dict())
            return plan

        except Exception as e:
            logger.error(f"Error generating strategic plan: {e}", exc_info=True)
            return self._fallback_strategic_plan()

    def _fallback_strategic_plan(self) -> StrategicPlan:
        """Return fallback strategic plan on error."""
        return StrategicPlan(
            objectives=["Mejorar comunicación con ciudadanos", "Aumentar presencia en redes"],
            actions=[{"action": "Monitoreo continuo", "priority": "alta", "topic": "General"}],
            timeline="3-6 meses",
            expected_impact="Mejora en engagement"
        )

    def generate_speech(
        self,
        location: str,
        topic_analyses: List[PNDTopicAnalysis],
        candidate_name: str,
        trending_topic: Optional[Dict[str, Any]] = None
    ) -> Speech:
        """Generate personalized speech for candidate based on trending topics."""
        cache_key, cached = self._check_speech_cache(location, candidate_name, topic_analyses, trending_topic)
        if cached:
            return Speech(**cached)

        try:
            context = self._build_analysis_context(topic_analyses)
            trending_context = build_trending_context(trending_topic)
            prompt = build_speech_prompt(location, context, candidate_name, trending_context)
            result = self._make_json_completion(SPEECH_WRITER_SYSTEM, prompt, temperature=0.8)

            generated_speech = Speech(
                title=result.get('title', f'Discurso para {location}'),
                content=result.get('content', ''),
                key_points=result.get('key_points', []),
                duration_minutes=result.get('duration_minutes', 7)
            )
            self._content_cache.set(cache_key, generated_speech.dict())
            return generated_speech

        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            return self._fallback_speech(location)

    def _fallback_speech(self, location: str) -> Speech:
        """Return fallback speech on error."""
        return Speech(
            title=f"Discurso para {location}",
            content=f"Queridos ciudadanos de {location}, hoy hablamos de nuestras necesidades y propuestas...",
            key_points=["Compromiso con la comunidad", "Trabajo conjunto"],
            duration_minutes=5
        )

    def generate_media_summary(self, core_result: CoreAnalysisResult) -> Dict[str, Any]:
        """Generate a neutral, descriptive summary for media product."""
        stats_context = self._build_media_stats_context(core_result)
        prompt = build_media_summary_prompt(stats_context)

        try:
            result = self._make_json_completion(MEDIA_ANALYST_SYSTEM, prompt, temperature=0.4)
            return MediaAnalysisSummary(**result).dict()
        except Exception as exc:
            logger.error(f"Error generating media summary: {exc}", exc_info=True)
            return MediaAnalysisSummary(overview="Resumen no disponible.", key_stats=[], key_findings=[]).dict()

    def _build_media_stats_context(self, core_result: CoreAnalysisResult) -> Dict[str, Any]:
        """Build stats context for media summary."""
        return {
            "tweets_analyzed": core_result.tweets_analyzed,
            "location": core_result.location,
            "topic": core_result.topic,
            "sentiment_overview": core_result.sentiment_overview.dict(),
            "topics": [t.dict() for t in core_result.topics],
            "time_window_from": core_result.time_window_from.isoformat(),
            "time_window_to": core_result.time_window_to.isoformat(),
            "trending_topic": core_result.trending_topic,
        }

    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Chat with GPT-4o as campaign assistant."""
        try:
            user_prompt = message + (f"\n\nContexto adicional: {context}" if context else "")
            return self._make_text_completion(CAMPAIGN_ASSISTANT_SYSTEM, user_prompt)
        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."

    def generate_advisor_recommendations(self, req: AdvisorRequest) -> AdvisorResponse:
        """Generate human-in-the-loop draft suggestions (no auto-posting)."""
        return self._advisor.generate_recommendations(req)

    def _build_analysis_context(self, topic_analyses: List[PNDTopicAnalysis]) -> str:
        """Build context string from topic analyses."""
        parts = []
        for analysis in topic_analyses:
            sentiment = analysis.sentiment
            parts.append(
                f"Tema: {analysis.topic}\n"
                f"Sentimiento - Positivo: {sentiment.positive:.2%}, Negativo: {sentiment.negative:.2%}, Neutral: {sentiment.neutral:.2%}\n"
                f"Tweets analizados: {analysis.tweet_count}\n"
                f"Insights: {', '.join(analysis.key_insights[:3])}\n"
            )
        return "\n".join(parts)

    def _check_cache(self, namespace: str, location: str, candidate: Optional[str], analyses: List[PNDTopicAnalysis]) -> Tuple[str, Optional[Dict]]:
        """Check cache for content."""
        analysis_hash = self._build_analysis_hash(analyses)
        key = f"{namespace}:{location.lower()}|{(candidate or '').lower()}|{analysis_hash}"
        return key, self._content_cache.get(key)

    def _check_speech_cache(self, location: str, candidate: str, analyses: List[PNDTopicAnalysis], trending: Optional[Dict]) -> Tuple[str, Optional[Dict]]:
        """Check cache for speech content."""
        analysis_hash = self._build_analysis_hash(analyses)
        trending_hash = self._hash_payload(trending) if trending else "none"
        key = f"speech:{location.lower()}|{candidate.lower()}|{analysis_hash}|{trending_hash}"
        return key, self._content_cache.get(key)

    def _hash_payload(self, payload: Any) -> str:
        """Return deterministic hash of JSON-serializable payload."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def _build_analysis_hash(self, topic_analyses: List[PNDTopicAnalysis]) -> str:
        """Hash PND topic analyses for caching."""
        payload = [analysis.dict() if hasattr(analysis, 'dict') else analysis for analysis in topic_analyses]
        return self._hash_payload(payload)
