"""
RAG Content Formatters for CASTOR ELECCIONES.
Functions to format analysis data for indexing.
"""
from typing import Any, Dict, List


def format_executive_summary(summary: Dict, location: str, date: str) -> str:
    """Format executive summary for indexing."""
    parts = [f"RESUMEN EJECUTIVO - Análisis de {location} ({date}):"]

    if summary.get("overview"):
        parts.append(f"Visión general: {summary['overview']}")

    findings = summary.get("key_findings", [])
    if findings:
        parts.append("Hallazgos clave:")
        for f in findings[:5]:
            parts.append(f"- {f}")

    recommendations = summary.get("recommendations", [])
    if recommendations:
        parts.append("Recomendaciones estratégicas:")
        for r in recommendations[:5]:
            parts.append(f"- {r}")

    return "\n".join(parts)


def format_topic(topic: Dict, location: str, date: str) -> str:
    """Format topic analysis for indexing."""
    topic_name = topic.get("topic", "Sin nombre")
    parts = [f"ANÁLISIS DE TEMA: {topic_name} en {location} ({date})"]

    sentiment = topic.get("sentiment", {})
    if sentiment:
        pos = sentiment.get("positive", 0) * 100
        neg = sentiment.get("negative", 0) * 100
        neu = sentiment.get("neutral", 0) * 100
        parts.append(f"Sentimiento: {pos:.1f}% positivo, {neu:.1f}% neutral, {neg:.1f}% negativo")

    count = topic.get("tweet_count", 0)
    if count:
        parts.append(f"Menciones analizadas: {count}")

    insights = topic.get("key_insights", [])
    if insights:
        parts.append("Insights principales:")
        for insight in insights[:5]:
            parts.append(f"- {insight}")

    return "\n".join(parts)


def format_sentiment(sentiment: Dict, location: str, date: str) -> str:
    """Format sentiment overview."""
    pos = sentiment.get("positive", 0) * 100
    neg = sentiment.get("negative", 0) * 100
    neu = sentiment.get("neutral", 0) * 100

    tone = "Favorable" if pos > neg + 10 else "Crítico" if neg > pos + 10 else "Mixto"

    interpretation = (
        'La percepción ciudadana es mayormente favorable' if pos > 50
        else 'Existen preocupaciones significativas en la ciudadanía' if neg > 40
        else 'La opinión está dividida'
    )

    return f"""ANÁLISIS DE SENTIMIENTO GENERAL - {location} ({date}):
Sentimiento positivo: {pos:.1f}%
Sentimiento neutral: {neu:.1f}%
Sentimiento negativo: {neg:.1f}%
Tono general de la conversación: {tone}
Interpretación: {interpretation}"""


def format_strategic_plan(plan: Dict, location: str, date: str) -> str:
    """Format strategic plan."""
    parts = [f"PLAN ESTRATÉGICO - {location} ({date}):"]

    objectives = plan.get("objectives", [])
    if objectives:
        parts.append("Objetivos estratégicos:")
        for obj in objectives[:5]:
            parts.append(f"- {obj}")

    actions = plan.get("actions", [])
    if actions:
        parts.append("Acciones recomendadas:")
        for action in actions[:5]:
            if isinstance(action, dict):
                parts.append(f"- {action.get('action', action)} (Prioridad: {action.get('priority', 'media')})")
            else:
                parts.append(f"- {action}")

    if plan.get("timeline"):
        parts.append(f"Timeline sugerido: {plan['timeline']}")

    if plan.get("expected_impact"):
        parts.append(f"Impacto esperado: {plan['expected_impact']}")

    return "\n".join(parts)


def format_speech(speech: Dict, location: str, date: str) -> str:
    """Format speech content."""
    parts = [f"DISCURSO GENERADO - {location} ({date}):"]

    if speech.get("title"):
        parts.append(f"Título: {speech['title']}")

    key_points = speech.get("key_points", [])
    if key_points:
        parts.append("Puntos clave del discurso:")
        for point in key_points[:5]:
            parts.append(f"- {point}")

    content = speech.get("content", "")
    if content:
        preview = content[:500] + "..." if len(content) > 500 else content
        parts.append(f"Extracto: {preview}")

    return "\n".join(parts)


def format_metadata(meta: Dict, location: str, date: str) -> str:
    """Format analysis metadata."""
    parts = [f"DATOS DEL ANÁLISIS - {location} ({date}):"]

    if meta.get("tweets_analyzed"):
        parts.append(f"Tweets analizados: {meta['tweets_analyzed']}")

    if meta.get("theme"):
        parts.append(f"Tema principal: {meta['theme']}")

    if meta.get("trending_topic"):
        parts.append(f"Tema trending: {meta['trending_topic']}")

    if meta.get("trending_engagement"):
        parts.append(f"Engagement del trending: {meta['trending_engagement']}")

    return "\n".join(parts)


def format_tweets_chunk(
    tweets: List[Dict],
    topic: str,
    location: str,
    date: str,
    candidate: str = ""
) -> str:
    """Format a chunk of tweets for indexing."""
    stats = _calculate_tweet_stats(tweets)
    header = _build_tweets_header(topic, location, date, candidate, stats)
    content = _format_tweet_content(tweets)

    return "\n".join(header + content)


def _calculate_tweet_stats(tweets: List[Dict]) -> Dict[str, int]:
    """Calculate sentiment statistics for tweets."""
    pos_count = sum(1 for t in tweets if 'positiv' in (t.get('sentiment_label') or '').lower())
    neg_count = sum(1 for t in tweets if 'negativ' in (t.get('sentiment_label') or '').lower())
    neu_count = len(tweets) - pos_count - neg_count

    return {'pos': pos_count, 'neg': neg_count, 'neu': neu_count, 'total': len(tweets)}


def _build_tweets_header(
    topic: str,
    location: str,
    date: str,
    candidate: str,
    stats: Dict[str, int]
) -> List[str]:
    """Build header for tweets chunk."""
    header = [
        f"TWEETS SOBRE {topic.upper()} - {location} ({date})",
        f"Candidato/Tema: {candidate}" if candidate else "",
        f"Total tweets: {stats['total']} | Positivos: {stats['pos']} | Negativos: {stats['neg']} | Neutrales: {stats['neu']}",
        "",
        "Opiniones de ciudadanos:"
    ]
    return header


def _format_tweet_content(tweets: List[Dict]) -> List[str]:
    """Format individual tweets."""
    content = []
    for t in tweets:
        author = t.get('author_username', 'usuario')
        text = t.get('content', '')[:280]
        sentiment = t.get('sentiment_label', 'neutral')
        engagement = t.get('retweet_count', 0) + t.get('like_count', 0)

        content.append(f"- @{author} [{sentiment}]: \"{text}\"")
        if engagement > 10:
            content.append(f"  (Engagement: {engagement})")

    return content
