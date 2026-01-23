"""
Infraestructura Topic Strategy.
Handles infrastructure-related political analysis.
"""
from typing import List, Dict, Any, Optional
from app.interfaces.topic_strategy import (
    TopicConfig,
    PNDTopic,
    TopicStrategyFactory,
)
from .base_strategy import BaseTopicStrategy


@TopicStrategyFactory.register(PNDTopic.INFRAESTRUCTURA)
class InfraestructuraStrategy(BaseTopicStrategy):
    """Strategy for Infraestructura topic analysis."""

    def __init__(self):
        super().__init__()
        self._config = TopicConfig(
            name="infraestructura",
            display_name="Infraestructura",
            keywords=[
                "infraestructura", "vías", "carreteras", "transporte", "obras",
                "puentes", "aeropuertos", "metro", "transmilenio", "movilidad",
                "tráfico", "huecos", "pavimentación", "acueducto", "alcantarillado",
                "servicios públicos", "energía", "gas"
            ],
            hashtags=[
                "#infraestructura", "#movilidad", "#obras",
                "#transporte", "#vías"
            ],
            related_topics=["Economía y Empleo", "Medio Ambiente"],
            sentiment_weight=1.0,
            priority=7
        )

    @property
    def topic(self) -> PNDTopic:
        return PNDTopic.INFRAESTRUCTURA

    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Infrastructure-specific sentiment interpretation."""
        base = super().interpret_sentiment(sentiment_scores, context)

        negative = sentiment_scores.get("negative", 0)

        if negative > 0.5:
            base["interpretation"] = (
                "Fuerte insatisfacción con infraestructura. "
                "Demanda de inversión y mantenimiento."
            )
            base["infrastructure_state"] = "deficiente"
        elif negative > 0.3:
            base["interpretation"] = (
                "Quejas moderadas sobre infraestructura. "
                "Oportunidad para propuestas de mejora."
            )
            base["infrastructure_state"] = "regular"
        else:
            base["interpretation"] = (
                "Percepción aceptable de infraestructura. "
                "Enfoque en mantenimiento y expansión."
            )
            base["infrastructure_state"] = "aceptable"

        return base

    def generate_insights(
        self,
        tweets: List[Dict[str, Any]],
        aggregated_sentiment: Dict[str, float]
    ) -> List[str]:
        """Generate infrastructure-specific insights."""
        insights = super().generate_insights(tweets, aggregated_sentiment)

        if not tweets:
            return insights

        # Analyze for specific infrastructure concerns
        roads_keywords = ["vía", "carretera", "hueco", "pavimento"]
        transport_keywords = ["transporte", "bus", "metro", "tráfico", "movilidad"]
        utilities_keywords = ["agua", "luz", "energía", "gas", "acueducto"]

        total = len(tweets)

        roads_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in roads_keywords)
        )
        transport_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in transport_keywords)
        )
        utilities_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in utilities_keywords)
        )

        if roads_count > total * 0.25:
            insights.append(
                f"El estado de las vías es preocupación principal ({roads_count} menciones)"
            )
        if transport_count > total * 0.2:
            insights.append(
                f"El transporte público es tema relevante ({transport_count} menciones)"
            )
        if utilities_count > total * 0.15:
            insights.append(
                f"Los servicios públicos generan discusión ({utilities_count} menciones)"
            )

        return insights

    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """Generate infrastructure-specific recommendations."""
        recommendations = []
        candidate = candidate_name or "el candidato"
        negative = sentiment.get("negative", 0)

        if negative > 0.5:
            recommendations.extend([
                f"Proponer plan de inversión en infraestructura para {location}",
                "Comprometerse con mantenimiento vial permanente",
                "Plantear mejora del transporte público",
                "Proponer modernización de servicios públicos"
            ])
        elif negative > 0.3:
            recommendations.extend([
                "Proponer proyectos de infraestructura con cronogramas",
                "Destacar propuestas de movilidad sostenible",
                "Plantear alianzas público-privadas para obras"
            ])
        else:
            recommendations.extend([
                "Comunicar avances en obras de infraestructura",
                "Proponer expansión de servicios a zonas desatendidas",
                "Destacar proyectos emblemáticos completados"
            ])

        return recommendations
