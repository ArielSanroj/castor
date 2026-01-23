"""
Economía y Empleo Topic Strategy.
Handles economy and employment-related political analysis.
"""
from typing import List, Dict, Any, Optional
from app.interfaces.topic_strategy import (
    TopicConfig,
    PNDTopic,
    TopicStrategyFactory,
)
from .base_strategy import BaseTopicStrategy


@TopicStrategyFactory.register(PNDTopic.ECONOMIA)
class EconomiaStrategy(BaseTopicStrategy):
    """Strategy for Economía y Empleo topic analysis."""

    def __init__(self):
        super().__init__()
        self._config = TopicConfig(
            name="economia",
            display_name="Economía y Empleo",
            keywords=[
                "economía", "empleo", "trabajo", "desempleo", "empresas",
                "salario", "inflación", "precios", "costo de vida",
                "emprendimiento", "PYMES", "inversión", "pobreza",
                "informalidad", "pensiones", "reforma laboral"
            ],
            hashtags=[
                "#empleo", "#economía", "#desempleo",
                "#trabajodigno", "#emprendimiento"
            ],
            related_topics=["Educación", "Infraestructura"],
            sentiment_weight=1.3,  # High priority - affects daily life
            priority=10
        )

    @property
    def topic(self) -> PNDTopic:
        return PNDTopic.ECONOMIA

    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Economy-specific sentiment interpretation."""
        base = super().interpret_sentiment(sentiment_scores, context)

        negative = sentiment_scores.get("negative", 0)
        positive = sentiment_scores.get("positive", 0)

        if negative > 0.5:
            base["interpretation"] = (
                "Fuerte preocupación económica ciudadana. "
                "El bolsillo es prioridad del electorado."
            )
            base["economic_mood"] = "pesimista"
        elif positive > negative:
            base["interpretation"] = (
                "Optimismo económico moderado. "
                "Oportunidad para propuestas de crecimiento."
            )
            base["economic_mood"] = "optimista"
        else:
            base["interpretation"] = (
                "Incertidumbre económica. "
                "El electorado busca propuestas concretas."
            )
            base["economic_mood"] = "incierto"

        return base

    def generate_insights(
        self,
        tweets: List[Dict[str, Any]],
        aggregated_sentiment: Dict[str, float]
    ) -> List[str]:
        """Generate economy-specific insights."""
        insights = super().generate_insights(tweets, aggregated_sentiment)

        if not tweets:
            return insights

        # Analyze for specific economic concerns
        employment_keywords = ["empleo", "trabajo", "desempleo", "despido"]
        inflation_keywords = ["inflación", "precios", "caro", "costo"]
        business_keywords = ["empresa", "negocio", "emprendimiento", "pyme"]

        total = len(tweets)

        employment_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in employment_keywords)
        )
        inflation_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in inflation_keywords)
        )
        business_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in business_keywords)
        )

        if employment_count > total * 0.25:
            insights.append(
                f"El empleo es la principal preocupación económica ({employment_count} menciones)"
            )
        if inflation_count > total * 0.2:
            insights.append(
                f"El costo de vida genera preocupación ({inflation_count} menciones)"
            )
        if business_count > total * 0.15:
            insights.append(
                f"El emprendimiento es tema de interés ({business_count} menciones)"
            )

        return insights

    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """Generate economy-specific recommendations."""
        recommendations = []
        candidate = candidate_name or "el candidato"
        negative = sentiment.get("negative", 0)

        if negative > 0.5:
            recommendations.extend([
                f"Proponer plan de generación de empleo con cifras para {location}",
                "Comprometerse con apoyo a PYMES y emprendedores",
                "Plantear subsidios o alivios para familias vulnerables",
                "Proponer incentivos para atracción de inversión"
            ])
        elif negative > 0.3:
            recommendations.extend([
                "Proponer formalización laboral con beneficios",
                "Destacar propuestas de capacitación y reconversión laboral",
                "Plantear alianzas para generación de empleo joven"
            ])
        else:
            recommendations.extend([
                "Comunicar indicadores económicos positivos",
                "Proponer consolidación del crecimiento económico",
                "Destacar casos de éxito empresarial local"
            ])

        return recommendations
