"""
Salud Topic Strategy.
Handles health-related political analysis.
"""
from typing import List, Dict, Any, Optional
from app.interfaces.topic_strategy import (
    TopicConfig,
    PNDTopic,
    TopicStrategyFactory,
)
from .base_strategy import BaseTopicStrategy


@TopicStrategyFactory.register(PNDTopic.SALUD)
class SaludStrategy(BaseTopicStrategy):
    """Strategy for Salud (Health) topic analysis."""

    def __init__(self):
        super().__init__()
        self._config = TopicConfig(
            name="salud",
            display_name="Salud",
            keywords=[
                "salud", "hospitales", "médicos", "EPS", "medicamentos",
                "clínicas", "urgencias", "citas médicas", "enfermeros",
                "vacunación", "atención", "pacientes", "sistema de salud",
                "IPS", "tutelas", "crisis salud"
            ],
            hashtags=[
                "#salud", "#saludpública", "#eps",
                "#derechoalasalud", "#hospitales"
            ],
            related_topics=["Igualdad y Equidad", "Economía y Empleo"],
            sentiment_weight=1.2,
            priority=9
        )

    @property
    def topic(self) -> PNDTopic:
        return PNDTopic.SALUD

    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Health-specific sentiment interpretation."""
        base = super().interpret_sentiment(sentiment_scores, context)

        negative = sentiment_scores.get("negative", 0)

        if negative > 0.5:
            base["interpretation"] = (
                "Crisis de confianza en el sistema de salud. "
                "Demanda urgente de soluciones estructurales."
            )
            base["crisis_level"] = "alto"
        elif negative > 0.3:
            base["interpretation"] = (
                "Insatisfacción moderada con servicios de salud. "
                "Oportunidad para propuestas de mejora."
            )
            base["crisis_level"] = "medio"
        else:
            base["interpretation"] = (
                "Percepción estable del sistema de salud. "
                "Mantener enfoque en prevención y acceso."
            )
            base["crisis_level"] = "bajo"

        return base

    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """Generate health-specific recommendations."""
        recommendations = []
        candidate = candidate_name or "el candidato"
        negative = sentiment.get("negative", 0)

        if negative > 0.5:
            recommendations.extend([
                f"Proponer reforma al sistema de salud para {location}",
                "Comprometerse con reducción de tiempos de espera en citas",
                "Plantear fortalecimiento de red hospitalaria pública",
                "Proponer regulación de precios de medicamentos"
            ])
        elif negative > 0.3:
            recommendations.extend([
                "Proponer mejora de infraestructura hospitalaria",
                "Destacar propuestas de salud preventiva",
                "Plantear aumento de cobertura en zonas rurales"
            ])
        else:
            recommendations.extend([
                "Comunicar indicadores positivos de salud",
                "Proponer consolidación de programas exitosos",
                "Destacar avances en vacunación y prevención"
            ])

        return recommendations
