"""
RAG PND Formatters for CASTOR ELECCIONES.
Functions to format PND metrics and snapshots for indexing.
"""
from typing import Any, Dict, List


def format_pnd_summary(
    pnd_metrics: List[Dict],
    location: str,
    date: str,
    candidate: str = ""
) -> str:
    """Format PND metrics summary."""
    parts = [
        f"MÉTRICAS PND COMPLETAS - {location} ({date})",
        f"Candidato: {candidate}" if candidate else "",
        "",
        "Análisis por eje del Plan Nacional de Desarrollo:"
    ]

    for m in pnd_metrics:
        parts.extend(_format_single_pnd_metric(m))

    return "\n".join(parts)


def _format_single_pnd_metric(m: Dict) -> List[str]:
    """Format a single PND metric entry."""
    axis = m.get('pnd_axis_display', m.get('pnd_axis', 'Desconocido'))
    icce = m.get('icce', 0)
    sov = m.get('sov', 0)
    sna = m.get('sna', 0)
    tweets = m.get('tweet_count', 0)
    trend = m.get('trend', 'stable')

    trend_text = "↑ subiendo" if trend == 'up' else "↓ bajando" if trend == 'down' else "→ estable"
    sentiment_text = "positivo" if sna > 10 else "negativo" if sna < -10 else "neutral"

    parts = [
        f"\n{axis}:",
        f"  - ICCE: {icce:.1f}/100 (Fuerza narrativa)",
        f"  - SOV: {sov:.1f}% (Presencia en conversación)",
        f"  - SNA: {sna:+.1f}% (Sentimiento {sentiment_text})",
        f"  - Tweets: {tweets} | Tendencia: {trend_text}"
    ]

    samples = m.get('sample_tweets', [])
    if samples:
        sample_text = samples[0][:100] + "..." if len(samples[0]) > 100 else samples[0]
        parts.append(f"  - Ejemplo: \"{sample_text}\"")

    return parts


def format_pnd_axis(metric: Dict, location: str, date: str, candidate: str = "") -> str:
    """Format single PND axis for indexing."""
    axis = metric.get('pnd_axis_display', metric.get('pnd_axis', 'Desconocido'))
    icce = metric.get('icce', 0)
    sov = metric.get('sov', 0)
    sna = metric.get('sna', 0)

    interpretation = _get_pnd_interpretation(icce, sna, axis)
    recommendation = _get_pnd_recommendation(icce)

    return f"""ANÁLISIS DEL EJE PND: {axis} - {location} ({date})
Candidato: {candidate}

MÉTRICAS:
- ICCE (Índice de Capacidad Electoral): {icce:.1f}/100
- SOV (Share of Voice): {sov:.1f}%
- SNA (Sentimiento Neto Agregado): {sna:+.1f}%
- Tweets analizados: {metric.get('tweet_count', 0)}

INTERPRETACIÓN:
{chr(10).join('• ' + i for i in interpretation)}

RECOMENDACIÓN:
{recommendation}
"""


def _get_pnd_interpretation(icce: float, sna: float, axis: str) -> List[str]:
    """Get interpretation text for PND metrics."""
    interpretation = []

    if icce >= 60:
        interpretation.append(f"El candidato tiene una posición FUERTE en {axis}")
    elif icce < 45:
        interpretation.append(f"El candidato tiene una posición DÉBIL en {axis}, requiere atención")
    else:
        interpretation.append(f"El candidato tiene una posición MODERADA en {axis}")

    interpretation.append(_get_sentiment_interpretation(sna))
    return interpretation


def _get_sentiment_interpretation(sna: float) -> str:
    """Get sentiment interpretation text."""
    if sna > 15:
        return "El sentimiento ciudadano es MUY POSITIVO"
    elif sna > 5:
        return "El sentimiento ciudadano es positivo"
    elif sna < -15:
        return "El sentimiento ciudadano es MUY NEGATIVO, hay críticas fuertes"
    elif sna < -5:
        return "El sentimiento ciudadano es negativo"
    else:
        return "El sentimiento ciudadano es neutral/dividido"


def _get_pnd_recommendation(icce: float) -> str:
    """Get recommendation based on ICCE score."""
    if icce >= 60:
        return 'Mantener y capitalizar esta fortaleza narrativa'
    elif icce < 45:
        return 'Desarrollar propuestas y aumentar presencia en este tema'
    else:
        return 'Incrementar acciones para consolidar posición'


def format_analysis_snapshot(
    snapshot: Dict,
    location: str,
    date: str,
    candidate: str = ""
) -> str:
    """Format analysis snapshot for indexing."""
    metrics = _extract_snapshot_metrics(snapshot)
    levels = _get_snapshot_levels(metrics)
    evaluation = _get_snapshot_evaluation(metrics['icce'], metrics['sna'])

    return _build_snapshot_content(snapshot, metrics, levels, evaluation, location, date, candidate)


def _extract_snapshot_metrics(snapshot: Dict) -> Dict[str, Any]:
    """Extract metrics from snapshot."""
    return {
        'icce': snapshot.get('icce', 50),
        'sov': snapshot.get('sov', 0),
        'sna': snapshot.get('sna', 0),
        'momentum': snapshot.get('momentum', 0),
        'pos': snapshot.get('sentiment_positive', 0.33),
        'neg': snapshot.get('sentiment_negative', 0.33),
        'neu': snapshot.get('sentiment_neutral', 0.34)
    }


def _get_snapshot_levels(metrics: Dict) -> Dict[str, str]:
    """Get level descriptions for snapshot metrics."""
    icce = metrics['icce']
    momentum = metrics['momentum']
    pos = metrics['pos']
    neg = metrics['neg']

    return {
        'icce_level': "alto" if icce >= 60 else "bajo" if icce < 45 else "moderado",
        'momentum_text': "positivo (creciendo)" if momentum > 0.005 else "negativo (decreciendo)" if momentum < -0.005 else "estable",
        'sentiment_text': "favorable" if pos > neg + 0.1 else "desfavorable" if neg > pos + 0.1 else "mixto"
    }


def _build_snapshot_content(
    snapshot: Dict,
    metrics: Dict,
    levels: Dict,
    evaluation: str,
    location: str,
    date: str,
    candidate: str
) -> str:
    """Build snapshot content string."""
    key_findings = snapshot.get('key_findings', [])
    findings_text = chr(10).join('• ' + f for f in key_findings) if key_findings else '• No hay hallazgos específicos'
    trending = ', '.join(snapshot.get('trending_topics', [])) or 'No identificados'

    return f"""RESUMEN EJECUTIVO DE ANÁLISIS - {location} ({date})
Candidato/Tema: {candidate}

INDICADORES CLAVE:
- ICCE (Índice de Capacidad Electoral): {metrics['icce']:.1f}/100 - Nivel {levels['icce_level']}
- SOV (Share of Voice): {metrics['sov']:.1f}% de la conversación
- SNA (Sentimiento Neto): {metrics['sna']:+.1f}%
- Momentum: {metrics['momentum']:+.3f} ({levels['momentum_text']})

DISTRIBUCIÓN DE SENTIMIENTO:
- Positivo: {metrics['pos']*100:.1f}%
- Neutral: {metrics['neu']*100:.1f}%
- Negativo: {metrics['neg']*100:.1f}%
- Balance general: {levels['sentiment_text']}

RESUMEN:
{snapshot.get('executive_summary', f'Análisis de conversación sobre {candidate} en {location}')}

HALLAZGOS CLAVE:
{findings_text}

TEMAS TRENDING:
{trending}

EVALUACIÓN GENERAL:
{evaluation}
"""


def _get_snapshot_evaluation(icce: float, sna: float) -> str:
    """Get evaluation text for snapshot."""
    if icce >= 60 and sna > 0:
        return 'La posición narrativa es sólida, mantener estrategia actual'
    elif icce >= 50:
        return 'La posición narrativa es favorable pero puede mejorar'
    elif icce < 40:
        return 'Se requiere atención urgente a la estrategia de comunicación'
    else:
        return 'Hay oportunidades de mejora en la narrativa'
