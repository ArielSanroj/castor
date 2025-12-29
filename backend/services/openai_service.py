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
from models.schemas import (
    ExecutiveSummary,
    StrategicPlan,
    Speech,
    PNDTopicAnalysis
)
from app.schemas.core import CoreAnalysisResult
from app.schemas.media import MediaAnalysisSummary
from app.schemas.advisor import AdvisorRequest, AdvisorResponse, AdvisorDraft
from app.schemas.campaign import (
    CampaignAnalysisRequest as NewCampaignRequest,
    ExecutiveSummary as NewExecutiveSummary,
    StrategicPlan as NewStrategicPlan,
    Speech as NewSpeech,
)
from utils.cache import TTLCache

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
        logger.info(f"OpenAIService initialized with model: {self.model}")
    
    @exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exceptions=(openai.APIError, openai.APITimeoutError, openai.RateLimitError)
    )
    def _call_openai_api(self, call_func: Callable) -> Any:
        """
        Execute OpenAI API call with circuit breaker and retry logic.
        
        Args:
            call_func: Function that makes the OpenAI API call
            
        Returns:
            API response
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            Exception: Original exception from API call
        """
        try:
            return self._circuit_breaker.call(call_func)
        except CircuitBreakerOpenError:
            logger.error("OpenAI circuit breaker is OPEN, rejecting request")
            raise
        except (openai.APIError, openai.APITimeoutError, openai.RateLimitError) as e:
            logger.warning(f"OpenAI API error: {e}")
            raise
    
    def generate_executive_summary(
        self,
        location: str,
        topic_analyses: List[PNDTopicAnalysis],
        candidate_name: Optional[str] = None
    ) -> ExecutiveSummary:
        """
        Generate executive summary from topic analyses.
        
        Args:
            location: Location analyzed
            topic_analyses: List of topic analyses
            candidate_name: Optional candidate name
            
        Returns:
            ExecutiveSummary object
        """
        analysis_hash = self._build_analysis_hash(topic_analyses)
        cache_key, cached = self._cache_lookup(
            'exec_summary',
            [location.lower(), (candidate_name or '').lower(), analysis_hash]
        )
        if cached:
            return ExecutiveSummary(**cached)
        
        try:
            # Build context from analyses
            context = self._build_analysis_context(topic_analyses)
            
            prompt = f"""Eres CASTOR ELECCIONES, una herramienta de inteligencia artificial para campañas electorales.

Analiza los siguientes datos de sentimiento ciudadano en {location} y genera un resumen ejecutivo profesional.

Datos analizados:
{context}

Candidato: {candidate_name or 'el candidato'}

Genera un resumen ejecutivo en español con:
1. Una visión general (2-3 párrafos) del clima político actual
2. Los 3-5 hallazgos clave más importantes
3. Las 3-5 recomendaciones estratégicas prioritarias

Formato de respuesta JSON:
{{
    "overview": "texto del resumen general",
    "key_findings": ["hallazgo 1", "hallazgo 2", ...],
    "recommendations": ["recomendación 1", "recomendación 2", ...]
}}"""

            def _make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un experto en análisis político y estrategia electoral. Responde siempre en español y formato JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
            
            response = self._call_openai_api(_make_api_call)
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            summary = ExecutiveSummary(
                overview=result.get('overview', ''),
                key_findings=result.get('key_findings', []),
                recommendations=result.get('recommendations', [])
            )
            self._content_cache.set(cache_key, summary.dict())
            return summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}", exc_info=True)
            # Return fallback summary
            return ExecutiveSummary(
                overview=f"Análisis de sentimiento ciudadano en {location} basado en datos de redes sociales.",
                key_findings=[
                    "Análisis completado con datos disponibles",
                    "Se requiere más información para insights profundos"
                ],
                recommendations=[
                    "Continuar monitoreo de redes sociales",
                    "Ampliar búsqueda de datos"
                ]
            )
    
    def generate_strategic_plan(
        self,
        location: str,
        topic_analyses: List[PNDTopicAnalysis],
        candidate_name: Optional[str] = None
    ) -> StrategicPlan:
        """
        Generate strategic plan from analyses.
        
        Args:
            location: Location analyzed
            topic_analyses: List of topic analyses
            candidate_name: Optional candidate name
            
        Returns:
            StrategicPlan object
        """
        analysis_hash = self._build_analysis_hash(topic_analyses)
        cache_key, cached = self._cache_lookup(
            'strategic_plan',
            [location.lower(), (candidate_name or '').lower(), analysis_hash]
        )
        if cached:
            return StrategicPlan(**cached)
        
        try:
            context = self._build_analysis_context(topic_analyses)
            
            prompt = f"""Eres CASTOR ELECCIONES. Genera un plan estratégico electoral profesional.

Ubicación: {location}
Candidato: {candidate_name or 'el candidato'}

Datos de análisis:
{context}

Genera un plan estratégico en español con:
1. 3-5 objetivos estratégicos claros y medibles
2. Acciones concretas para cada objetivo (formato: {{"action": "descripción", "priority": "alta/media/baja", "topic": "tema PND"}})
3. Timeline propuesto (corto, mediano, largo plazo)
4. Impacto esperado

Formato JSON:
{{
    "objectives": ["objetivo 1", ...],
    "actions": [{{"action": "...", "priority": "...", "topic": "..."}}, ...],
    "timeline": "descripción del timeline",
    "expected_impact": "descripción del impacto esperado"
}}"""

            def _make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un estratega político experto. Responde en español y formato JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
            
            response = self._call_openai_api(_make_api_call)
            
            import json
            result = json.loads(response.choices[0].message.content)
            
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
        """
        Generate personalized speech for candidate based on trending topics.
        
        Args:
            location: Location
            topic_analyses: List of topic analyses
            candidate_name: Candidate name
            trending_topic: Optional trending topic data (what's hot right now)
            
        Returns:
            Speech object
        """
        analysis_hash = self._build_analysis_hash(topic_analyses)
        trending_hash = self._hash_payload(trending_topic) if trending_topic else "none"
        cache_key, cached = self._cache_lookup(
            'speech',
            [location.lower(), candidate_name.lower(), analysis_hash, trending_hash]
        )
        if cached:
            return Speech(**cached)
        
        try:
            context = self._build_analysis_context(topic_analyses)
            
            # Add trending topic context if available
            trending_context = ""
            if trending_topic:
                trending_context = f"""
TEMA TRENDING DEL MOMENTO (lo que la gente está discutiendo AHORA):
- Tema: {trending_topic.get('topic', 'N/A')}
- Engagement: {trending_topic.get('engagement_score', 0):.0f} interacciones
- Sentimiento: {trending_topic.get('sentiment_positive', 0):.2%} positivo
- Menciones: {trending_topic.get('tweet_count', 0)} tweets recientes

IMPORTANTE: El discurso DEBE mencionar y posicionarse sobre este tema trending para conectar con lo que la gente está pensando AHORA.
"""
            
            prompt = f"""Eres CASTOR ELECCIONES. Genera un discurso electoral profesional y personalizado basado en lo que está trending AHORA.

Candidato: {candidate_name}
Ubicación: {location}

Datos de análisis:
{context}
{trending_context}

Genera un discurso completo en español que:
- Sea inspirador y conecte emocionalmente
- Mencione las necesidades reales identificadas
- INCLUYA Y SE POSICIONE sobre el tema trending del momento (esto es CRÍTICO)
- Conecte el tema trending con las propuestas del candidato
- Incluya propuestas concretas alineadas con el PND
- Sea apropiado para un discurso público (5-10 minutos)
- Incluya puntos clave destacados
- Use lenguaje que resuene con lo que la gente está diciendo ahora mismo

Formato JSON:
{{
    "title": "Título del discurso",
    "content": "Texto completo del discurso (mínimo 500 palabras)",
    "key_points": ["punto 1", "punto 2", ...],
    "duration_minutes": 7
}}"""

            def _make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un escritor de discursos políticos experto. Escribe en español, tono profesional pero cercano."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    response_format={"type": "json_object"}
                )
            
            response = self._call_openai_api(_make_api_call)
            
            import json
            result = json.loads(response.choices[0].message.content)
            
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
        return Speech(
            title=f"Discurso para {location}",
            content=f"Queridos ciudadanos de {location}, hoy hablamos de nuestras necesidades y propuestas...",
            key_points=["Compromiso con la comunidad", "Trabajo conjunto"],
            duration_minutes=5
        )

    # ------------------------------------------------------------------
    # New product-specific helpers
    # ------------------------------------------------------------------
    def generate_media_summary(self, core_result: CoreAnalysisResult) -> Dict[str, Any]:
        """
        Generate a neutral, descriptive summary for media product.
        """
        stats_context = {
            "tweets_analyzed": core_result.tweets_analyzed,
            "location": core_result.location,
            "topic": core_result.topic,
            "sentiment_overview": core_result.sentiment_overview.dict(),
            "topics": [t.dict() for t in core_result.topics],
            "time_window_from": core_result.time_window_from.isoformat(),
            "time_window_to": core_result.time_window_to.isoformat(),
            "trending_topic": core_result.trending_topic,
        }

        system_prompt = (
            "Eres un analista de datos para un medio de comunicación. "
            "Resumes conversación en X/Twitter de forma descriptiva, neutral y no partidista. "
            "No des recomendaciones de acción ni lenguaje prescriptivo."
        )
        user_prompt = (
            "Genera un JSON con la forma "
            '{"overview": "...", "key_stats": ["..."], "key_findings": ["..."]} '
            "solo con descripción de lo que ocurrió.\n"
            f"Datos:\n{json.dumps(stats_context, ensure_ascii=False, indent=2)}"
        )

        try:
            def _make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    response_format={"type": "json_object"},
                )
            
            response = self._call_openai_api(_make_api_call)
            result = json.loads(response.choices[0].message.content)
            summary = MediaAnalysisSummary(**result)
            return summary.dict()
        except Exception as exc:
            logger.error(f"Error generating media summary: {exc}", exc_info=True)
            fallback = MediaAnalysisSummary(
                overview="Resumen no disponible por el momento.",
                key_stats=[],
                key_findings=[],
            )
            return fallback.dict()

    # The following adapters are placeholders to align with new schemas.
    # They intentionally raise until you supply prompts/logic.
    def generate_executive_summary_new(
        self,
        core_result: CoreAnalysisResult,
        request: NewCampaignRequest,
    ) -> NewExecutiveSummary:
        raise NotImplementedError("Implementa generate_executive_summary_new según tu lógica")

    def generate_strategic_plan_new(
        self,
        core_result: CoreAnalysisResult,
        request: NewCampaignRequest,
    ) -> NewStrategicPlan:
        raise NotImplementedError("Implementa generate_strategic_plan_new según tu lógica")

    def generate_speech_new(
        self,
        core_result: CoreAnalysisResult,
        request: NewCampaignRequest,
    ) -> NewSpeech:
        raise NotImplementedError("Implementa generate_speech_new según tu lógica")
    
    def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Chat with GPT-4o as campaign assistant.
        
        Args:
            message: User message
            context: Optional context dictionary
            
        Returns:
            AI response
        """
        try:
            system_prompt = """Eres CASTOR ELECCIONES, un asistente de inteligencia artificial especializado en campañas electorales en Colombia.

Tu función es ayudar a candidatos y equipos de campaña con:
- Estrategias electorales
- Ideas de discursos
- Análisis de sentimiento
- Consejos de campaña
- Propuestas alineadas con el Plan Nacional de Desarrollo

Responde siempre en español, de manera profesional pero cercana."""

            user_prompt = message
            if context:
                user_prompt += f"\n\nContexto adicional: {context}"

            def _make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
            
            response = self._call_openai_api(_make_api_call)
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo."
    
    def _build_analysis_context(self, topic_analyses: List[PNDTopicAnalysis]) -> str:
        """Build context string from topic analyses."""
        context_parts = []
        for analysis in topic_analyses:
            sentiment = analysis.sentiment
            context_parts.append(
                f"Tema: {analysis.topic}\n"
                f"Sentimiento - Positivo: {sentiment.positive:.2%}, "
                f"Negativo: {sentiment.negative:.2%}, "
                f"Neutral: {sentiment.neutral:.2%}\n"
                f"Tweets analizados: {analysis.tweet_count}\n"
                f"Insights: {', '.join(analysis.key_insights[:3])}\n"
            )
        return "\n".join(context_parts)

    def generate_advisor_recommendations(self, req: AdvisorRequest) -> AdvisorResponse:
        """
        Generate human-in-the-loop draft suggestions (no auto-posting).
        """
        profile = req.candidate_profile
        topics = ", ".join(req.topics) if req.topics else "tema general"
        goals = ", ".join(req.goals) if req.goals else "claridad narrativa"
        constraints = ", ".join(req.constraints) if req.constraints else "evitar ataques personales"

        prompt = f"""Eres CASTOR Advisor. Debes entregar borradores sugeridos para un humano, NO autopublicar.
Responde en JSON valido y en espanol.

Contexto:
- Ubicacion: {req.location}
- Temas: {topics}
- Perfil: nombre={profile.name or "candidato"}, rol={profile.role or "candidato"}, tono={profile.tone}
- Valores: {", ".join(profile.values) or "transparencia, bienestar"}
- Lineas rojas: {", ".join(profile.red_lines) or "desinformacion, ataques"}
- Objetivos: {goals}
- Restricciones: {constraints}
- Resumen de contexto (si aplica): {req.source_summary or "no disponible"}

Entrega:
- 2-4 borradores tipo post y 1-2 borradores tipo comentario.
- Cada borrador incluye: kind, intent, draft, rationale, risk_level, best_time.
- Evita lenguaje de odio, desinformacion o ataques.
- Enfatiza datos publicos y tono institucional.

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
}}
"""

        try:
            def _make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un asesor de comunicacion politica. Genera borradores para revision humana, sin automatizar publicaciones."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    response_format={"type": "json_object"}
                )

            response = self._call_openai_api(_make_api_call)
            result = json.loads(response.choices[0].message.content)

            drafts = []
            for item in result.get("drafts", []):
                drafts.append(AdvisorDraft(
                    kind=item.get("kind", "post"),
                    intent=item.get("intent", "informar"),
                    draft=item.get("draft", ""),
                    rationale=item.get("rationale", ""),
                    risk_level=item.get("risk_level", "bajo"),
                    best_time=item.get("best_time")
                ))

            guidance = result.get("guidance", "Revisar y aprobar manualmente antes de publicar.")
            return AdvisorResponse(
                success=True,
                approval_required=True,
                guidance=guidance,
                drafts=drafts
            )
        except Exception as e:
            logger.error("Error generating advisor recommendations: %s", e, exc_info=True)
            fallback = [
                AdvisorDraft(
                    kind="post",
                    intent="informar",
                    draft=(
                        f"Hoy el tema {topics} concentra la conversacion en {req.location}. "
                        "Seguiremos informando con datos verificables."
                    ),
                    rationale="Mantiene tono institucional y reconoce el tema dominante.",
                    risk_level="bajo",
                    best_time="tarde"
                )
            ]
            return AdvisorResponse(
                success=True,
                approval_required=True,
                guidance="Borradores generados automaticamente. Revisar antes de publicar.",
                drafts=fallback
            )

    def _cache_lookup(self, namespace: str, parts: List[str]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Build cache key and return stored value if available."""
        key = f"{namespace}:{'|'.join(parts)}"
        return key, self._content_cache.get(key)
    
    def _hash_payload(self, payload: Any) -> str:
        """Return deterministic hash of JSON-serializable payload."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    
    def _build_analysis_hash(self, topic_analyses: List[PNDTopicAnalysis]) -> str:
        """Hash PND topic analyses for caching."""
        payload = [
            analysis.dict() if hasattr(analysis, 'dict') else analysis
            for analysis in topic_analyses
        ]
        return self._hash_payload(payload)
