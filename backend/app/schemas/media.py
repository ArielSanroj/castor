from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from .core import SentimentOverview, TopicAnalysis, PeakEvent, ChartData


class MediaAnalysisRequest(BaseModel):
    """
    Request body for /api/media/analyze
    """
    location: str = Field(..., description="Ciudad/país. Ej: 'Colombia' o 'Bogotá'")
    topic: Optional[str] = Field(
        default=None,
        description="Tema general o eje PND (Seguridad, Salud, Educación, etc.)",
    )
    candidate_name: Optional[str] = Field(
        default=None,
        description="Nombre de persona mencionada, si aplica.",
    )
    politician: Optional[str] = Field(
        default=None,
        description="Usuario de X/Twitter. Ej: '@juanperez'",
    )
    max_tweets: int = Field(
        default=15,
        ge=1,  # Permitir desde 1 tweet (para respetar límite diario de 3)
        le=20,
        description="Límite de tweets a analizar (máx 20 para Free tier, recomendado 3/día).",
    )
    time_window_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Rango de días hacia atrás a considerar.",
    )
    language: str = Field(
        default="es",
        description="Idioma. Por defecto 'es'.",
    )


class MediaAnalysisSummary(BaseModel):
    overview: str
    key_stats: List[str] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)


class MediaAnalysisMetadata(BaseModel):
    tweets_analyzed: int
    location: str
    topic: Optional[str] = None
    time_window_from: datetime
    time_window_to: datetime
    trending_topic: Optional[str] = None
    raw_query: Optional[str] = None


class MediaAnalysisResponse(BaseModel):
    success: bool = True
    summary: MediaAnalysisSummary

    sentiment_overview: SentimentOverview
    topics: List[TopicAnalysis]
    peaks: List[PeakEvent]
    chart_data: ChartData

    metadata: MediaAnalysisMetadata
