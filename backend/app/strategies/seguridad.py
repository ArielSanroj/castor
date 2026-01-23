"""
Seguridad Topic Strategy.
Handles security-related political analysis.
"""
from typing import List, Dict, Any, Optional
from app.interfaces.topic_strategy import (
    TopicConfig,
    PNDTopic,
    TopicStrategyFactory,
)
from .base_strategy import BaseTopicStrategy


@TopicStrategyFactory.register(PNDTopic.SEGURIDAD)
class SeguridadStrategy(BaseTopicStrategy):
    """Strategy for Seguridad (Security) topic analysis."""

    def __init__(self):
        super().__init__()
        self._config = TopicConfig(
            name="seguridad",
            display_name="Seguridad",
            keywords=[
                "seguridad", "delincuencia", "crimen", "policía", "robo",
                "violencia", "homicidio", "inseguridad", "hurto", "atraco",
                "extorsión", "secuestro", "narcotráfico", "bandas", "criminalidad"
            ],
            hashtags=[
                "#seguridad", "#nomasviolencia", "#pazciudadana",
                "#seguridadciudadana", "#colombia"
            ],
            related_topics=["Paz y Reinserción", "Gobernanza y Transparencia"],
            sentiment_weight=1.2,  # High priority topic
            priority=9
        )

    @property
    def topic(self) -> PNDTopic:
        return PNDTopic.SEGURIDAD

    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Security-specific sentiment interpretation."""
        base = super().interpret_sentiment(sentiment_scores, context)

        negative = sentiment_scores.get("negative", 0)
        positive = sentiment_scores.get("positive", 0)

        # Security topic: high negative usually means concern about crime
        if negative > 0.5:
            base["interpretation"] = (
                "Alta preocupación ciudadana por la inseguridad. "
                "Los ciudadanos demandan acciones concretas."
            )
            base["urgency"] = "alta"
        elif negative > positive:
            base["interpretation"] = (
                "Percepción moderada de inseguridad. "
                "Oportunidad para propuestas de prevención."
            )
            base["urgency"] = "media"
        else:
            base["interpretation"] = (
                "Percepción relativamente positiva sobre seguridad. "
                "Mantener y comunicar avances."
            )
            base["urgency"] = "baja"

        return base

    def generate_insights(
        self,
        tweets: List[Dict[str, Any]],
        aggregated_sentiment: Dict[str, float]
    ) -> List[str]:
        """Generate security-specific insights."""
        insights = super().generate_insights(tweets, aggregated_sentiment)

        if not tweets:
            return insights

        # Analyze for specific security concerns
        crime_keywords = ["robo", "hurto", "atraco", "asalto"]
        violence_keywords = ["violencia", "homicidio", "asesinato"]
        drug_keywords = ["narcotráfico", "drogas", "microtráfico"]

        crime_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in crime_keywords)
        )
        violence_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in violence_keywords)
        )
        drug_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in drug_keywords)
        )

        total = len(tweets)
        if crime_count > total * 0.3:
            insights.append(
                f"El robo y hurto son las principales preocupaciones ({crime_count} menciones)"
            )
        if violence_count > total * 0.2:
            insights.append(
                f"La violencia es un tema recurrente ({violence_count} menciones)"
            )
        if drug_count > total * 0.1:
            insights.append(
                f"El narcotráfico aparece en la conversación ({drug_count} menciones)"
            )

        return insights

    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """Generate security-specific recommendations."""
        recommendations = []
        candidate = candidate_name or "el candidato"
        negative = sentiment.get("negative", 0)

        if negative > 0.5:
            recommendations.extend([
                f"Proponer plan de seguridad con métricas concretas para {location}",
                "Comprometerse con aumento de pie de fuerza policial",
                "Plantear estrategias de prevención del delito con comunidad",
                f"Realizar recorridos en zonas críticas de {location} con medios"
            ])
        elif negative > 0.3:
            recommendations.extend([
                f"Destacar propuestas de seguridad ciudadana para {location}",
                "Proponer tecnología para vigilancia (cámaras, apps ciudadanas)",
                "Enfatizar coordinación con Policía y Fiscalía"
            ])
        else:
            recommendations.extend([
                "Comunicar indicadores positivos de seguridad si existen",
                "Proponer consolidación de logros en seguridad",
                f"Mantener presencia en {location} para demostrar cercanía"
            ])

        return recommendations
