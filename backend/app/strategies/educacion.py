"""
Educación Topic Strategy.
Handles education-related political analysis.
"""
from typing import List, Dict, Any, Optional
from app.interfaces.topic_strategy import (
    TopicConfig,
    PNDTopic,
    TopicStrategyFactory,
)
from .base_strategy import BaseTopicStrategy


@TopicStrategyFactory.register(PNDTopic.EDUCACION)
class EducacionStrategy(BaseTopicStrategy):
    """Strategy for Educación (Education) topic analysis."""

    def __init__(self):
        super().__init__()
        self._config = TopicConfig(
            name="educacion",
            display_name="Educación",
            keywords=[
                "educación", "colegios", "universidad", "estudiantes", "maestros",
                "profesores", "escuelas", "becas", "ICETEX", "SENA",
                "matrícula", "deserción", "calidad educativa", "infraestructura escolar",
                "alimentación escolar", "PAE", "jornada única"
            ],
            hashtags=[
                "#educación", "#maestros", "#estudiantes",
                "#universidadpública", "#educaciónpública"
            ],
            related_topics=["Igualdad y Equidad", "Economía y Empleo"],
            sentiment_weight=1.1,
            priority=8
        )

    @property
    def topic(self) -> PNDTopic:
        return PNDTopic.EDUCACION

    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Education-specific sentiment interpretation."""
        base = super().interpret_sentiment(sentiment_scores, context)

        negative = sentiment_scores.get("negative", 0)
        positive = sentiment_scores.get("positive", 0)

        if negative > 0.5:
            base["interpretation"] = (
                "Fuerte insatisfacción con el sistema educativo. "
                "Demanda de mejoras en calidad y acceso."
            )
            base["opportunity"] = "propuestas_concretas"
        elif positive > negative:
            base["interpretation"] = (
                "Valoración positiva de iniciativas educativas. "
                "Oportunidad para fortalecer propuestas."
            )
            base["opportunity"] = "consolidar_mensaje"
        else:
            base["interpretation"] = (
                "Opiniones mixtas sobre educación. "
                "Necesidad de diferenciar propuestas."
            )
            base["opportunity"] = "diferenciacion"

        return base

    def generate_insights(
        self,
        tweets: List[Dict[str, Any]],
        aggregated_sentiment: Dict[str, float]
    ) -> List[str]:
        """Generate education-specific insights."""
        insights = super().generate_insights(tweets, aggregated_sentiment)

        if not tweets:
            return insights

        # Analyze for specific education concerns
        access_keywords = ["matrícula", "cupo", "acceso", "gratuidad"]
        quality_keywords = ["calidad", "nivel", "excelencia", "ranking"]
        infrastructure_keywords = ["infraestructura", "colegio", "sede", "dotación"]
        teacher_keywords = ["maestro", "profesor", "docente", "salario"]

        total = len(tweets)

        access_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in access_keywords)
        )
        quality_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in quality_keywords)
        )
        teacher_count = sum(
            1 for t in tweets
            if any(kw in t.get("text", "").lower() for kw in teacher_keywords)
        )

        if access_count > total * 0.2:
            insights.append(
                f"El acceso a educación es una preocupación central ({access_count} menciones)"
            )
        if quality_count > total * 0.15:
            insights.append(
                f"La calidad educativa es tema de debate ({quality_count} menciones)"
            )
        if teacher_count > total * 0.15:
            insights.append(
                f"Los docentes son actores relevantes en la conversación ({teacher_count} menciones)"
            )

        return insights

    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """Generate education-specific recommendations."""
        recommendations = []
        candidate = candidate_name or "el candidato"
        negative = sentiment.get("negative", 0)

        if negative > 0.5:
            recommendations.extend([
                f"Proponer plan de mejora educativa con metas medibles para {location}",
                "Comprometerse con aumento de inversión en educación",
                "Proponer programa de becas y subsidios estudiantiles",
                "Plantear mejora de condiciones laborales docentes"
            ])
        elif negative > 0.3:
            recommendations.extend([
                f"Visitar instituciones educativas en {location}",
                "Proponer alianzas público-privadas para educación",
                "Destacar propuestas de educación técnica y vocacional"
            ])
        else:
            recommendations.extend([
                "Comunicar avances en indicadores educativos",
                "Proponer consolidación de programas exitosos",
                "Destacar historias de éxito educativo local"
            ])

        return recommendations
