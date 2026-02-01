"""
LLM Prompt Templates for CASTOR ELECCIONES.
System prompts and prompt builders for the LLM service.
"""
import json
from typing import Any, Dict, List, Optional


# System prompts
POLITICAL_ANALYST_SYSTEM = (
    "Eres un experto en analisis politico y estrategia electoral. "
    "Responde siempre en espanol y formato JSON valido."
)

POLITICAL_STRATEGIST_SYSTEM = (
    "Eres un estratega politico experto. "
    "Responde en espanol y formato JSON valido."
)

SPEECH_WRITER_SYSTEM = (
    "Eres un escritor de discursos politicos experto. "
    "Escribe en espanol, tono profesional pero cercano."
)

MEDIA_ANALYST_SYSTEM = (
    "Eres un analista de datos para un medio de comunicacion. "
    "Resumes conversacion en X/Twitter de forma descriptiva, neutral y no partidista."
)

CAMPAIGN_ASSISTANT_SYSTEM = """Eres CASTOR ELECCIONES, un asistente de IA especializado en campanas electorales en Colombia.

Tu funcion es ayudar con:
- Estrategias electorales
- Ideas de discursos
- Analisis de sentimiento
- Consejos de campana

Responde siempre en espanol, de manera profesional pero cercana."""

ADVISOR_SYSTEM = (
    "Eres un asesor de comunicacion politica. "
    "Genera borradores para revision humana, sin automatizar publicaciones."
)


def build_executive_summary_prompt(
    location: str,
    analysis_context: str,
    candidate_name: Optional[str]
) -> str:
    """Build prompt for executive summary generation."""
    return f"""Eres CASTOR ELECCIONES, una herramienta de inteligencia artificial para campanas electorales.

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


def build_strategic_plan_prompt(
    location: str,
    analysis_context: str,
    candidate_name: Optional[str]
) -> str:
    """Build prompt for strategic plan generation."""
    return f"""Eres CASTOR ELECCIONES. Genera un plan estrategico electoral profesional.

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


def build_speech_prompt(
    location: str,
    candidate_name: str,
    analysis_context: str,
    trending_context: str
) -> str:
    """Build prompt for speech generation."""
    return f"""Genera un discurso electoral profesional.

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


def build_trending_context(trending_topic: Optional[Dict[str, Any]]) -> str:
    """Build trending topic context for speech generation."""
    if not trending_topic:
        return ""

    return f"""
TEMA TRENDING DEL MOMENTO:
- Tema: {trending_topic.get('topic', 'N/A')}
- Engagement: {trending_topic.get('engagement_score', 0):.0f}
- Sentimiento: {trending_topic.get('sentiment_positive', 0):.2%} positivo

IMPORTANTE: El discurso DEBE mencionar este tema trending.
"""


def build_media_summary_prompt(stats_context: Dict[str, Any]) -> str:
    """Build prompt for media summary generation."""
    return f"""Genera un JSON con la forma:
{{"overview": "...", "key_stats": ["..."], "key_findings": ["..."]}}

Solo descripcion de lo que ocurrio, sin recomendaciones.

Datos:
{json.dumps(stats_context, ensure_ascii=False, indent=2)}"""


def build_advisor_prompt(
    location: str,
    topics_str: str,
    profile: Dict[str, Any],
    goals_str: str,
    constraints_str: str,
    source_summary: Optional[str]
) -> str:
    """Build prompt for advisor recommendations."""
    return f"""Genera borradores sugeridos para un humano.

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


# Fallback responses
def get_executive_summary_fallback(location: str) -> Dict[str, Any]:
    """Return fallback executive summary."""
    return {
        "overview": f"Analisis de sentimiento ciudadano en {location}.",
        "key_findings": ["Analisis completado con datos disponibles"],
        "recommendations": ["Continuar monitoreo de redes sociales"]
    }


def get_strategic_plan_fallback() -> Dict[str, Any]:
    """Return fallback strategic plan."""
    return {
        "objectives": ["Mejorar comunicacion con ciudadanos"],
        "actions": [{"action": "Monitoreo continuo", "priority": "alta", "topic": "General"}],
        "timeline": "3-6 meses",
        "expected_impact": "Mejora en engagement"
    }


def get_speech_fallback(location: str) -> Dict[str, Any]:
    """Return fallback speech."""
    return {
        "title": f"Discurso para {location}",
        "content": f"Queridos ciudadanos de {location}...",
        "key_points": ["Compromiso con la comunidad"],
        "duration_minutes": 5
    }


def get_media_summary_fallback() -> Dict[str, Any]:
    """Return fallback media summary."""
    return {
        "overview": "Resumen no disponible.",
        "key_stats": [],
        "key_findings": []
    }


def get_advisor_fallback(topics_str: str) -> Dict[str, Any]:
    """Return fallback advisor response."""
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
