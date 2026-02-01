"""
Campaign Agent Prompt Templates for CASTOR ELECCIONES.
Prompts for strategy generation.
"""
from typing import Any, Dict, List


STRATEGY_SYSTEM = (
    "Eres un estratega politico experto. "
    "Responde siempre en espanol y formato JSON valido."
)

SIGNATURE_SYSTEM = "Eres experto en recoleccion de firmas para campanas politicas."


def build_winning_strategies_prompt(
    location: str,
    candidate_name: str,
    trending_summary: str,
    successful_summary: str,
    sentiment_analysis: Dict[str, Any]
) -> str:
    """Build prompt for winning strategies generation."""
    return f"""Eres un experto estratega politico en Colombia. Analiza los siguientes datos y genera estrategias concretas para ganar votos.

UBICACION: {location}
CANDIDATO: {candidate_name}

TEMAS TRENDING (lo que la gente esta discutiendo ahora):
{trending_summary}

ACCIONES EXITOSAS PREVIAS (lo que funciono antes):
{successful_summary}

ANALISIS DE SENTIMIENTO:
- Sentimiento promedio positivo: {sentiment_analysis.get('avg_positive', 0):.2%}
- Sentimiento promedio negativo: {sentiment_analysis.get('avg_negative', 0):.2%}
- Oportunidad: {sentiment_analysis.get('opportunity_score', 0):.2f}

Genera 5 estrategias concretas para ganar votos. Cada estrategia debe incluir:

1. Nombre de la estrategia
2. Descripcion detallada
3. Mensajes clave a comunicar
4. Canales recomendados (redes sociales, eventos, medios, etc.)
5. Timing (cuando ejecutar)
6. Demografia objetivo
7. Votos estimados
8. Nivel de confianza (0-1)
9. Nivel de riesgo (bajo, medio, alto)

Formato JSON:
{{
    "strategies": [
        {{
            "strategy_name": "Nombre",
            "description": "Descripcion",
            "key_messages": ["mensaje 1", "mensaje 2"],
            "channels": ["canal 1", "canal 2"],
            "timing": "cuando ejecutar",
            "target_demographic": "demografia",
            "predicted_votes": 1000,
            "confidence_score": 0.85,
            "risk_level": "medio"
        }}
    ]
}}"""


def build_signature_strategy_prompt(
    location: str,
    current_signatures: int,
    target_signatures: int,
    remaining: int
) -> str:
    """Build prompt for signature collection strategy."""
    return f"""Genera una estrategia para recolectar {remaining} firmas mas en {location}.

Firmas actuales: {current_signatures}
Meta: {target_signatures}
Faltan: {remaining}

Genera estrategia con:
1. Canales de recoleccion (digital, presencial, hibrido)
2. Mensajes persuasivos
3. Incentivos o llamados a la accion
4. Timing y frecuencia
5. Metricas de seguimiento

Formato JSON con estrategia detallada."""


def get_fallback_strategies(location: str) -> List[Dict[str, Any]]:
    """Return fallback strategies on error."""
    return [
        {
            'strategy_name': 'Enfoque en Temas Trending',
            'description': f'Alinear discurso con temas trending en {location}',
            'key_messages': ['Mensaje alineado con preocupaciones ciudadanas'],
            'channels': ['Twitter', 'Facebook', 'Eventos publicos'],
            'timing': 'Inmediato',
            'target_demographic': 'General',
            'predicted_votes': 500,
            'confidence_score': 0.7,
            'risk_level': 'bajo'
        }
    ]


def get_fallback_signature_strategy() -> Dict[str, Any]:
    """Return fallback signature strategy."""
    return {
        'channels': ['Redes sociales', 'Eventos presenciales', 'WhatsApp'],
        'key_messages': ['Tu firma cuenta', 'Juntos por el cambio'],
        'timing': 'Inmediato'
    }
