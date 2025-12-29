from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from .core import SentimentOverview, TopicAnalysis, PeakEvent, ChartData


class MediaAnalysisRequest(BaseModel):
    """
    Request body for /api/media/analyze
    """
    location: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ciudad/país. Ej: 'Colombia' o 'Bogotá'"
    )
    topic: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Tema general o eje PND (Seguridad, Salud, Educación, etc.)",
    )
    candidate_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nombre de persona mencionada, si aplica.",
    )
    politician: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Usuario de X/Twitter. Ej: '@juanperez'",
    )
    max_tweets: int = Field(
        default=15,
        ge=1,  # Permitir desde 1 tweet (para respetar límite diario de 3)
        le=20,  # Máximo estricto para Free tier
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
        pattern="^[a-z]{2}$",
        description="Idioma. Por defecto 'es'.",
    )
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: Optional[str]) -> Optional[str]:
        """Validate topic against allowed PND topics."""
        if v is None:
            return None
        
        from config import Config
        
        # Normalize topic
        topic_lower = v.strip().lower()
        
        # Check if it's a valid PND topic (case-insensitive)
        valid_topics = [t.lower() for t in Config.PND_TOPICS]
        
        if topic_lower not in valid_topics:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Custom topic '{v}' not in standard PND topics")
            # Still allow it for media analysis
        
        return v.strip() if v else None
    
    @field_validator('max_tweets')
    @classmethod
    def validate_max_tweets(cls, v: int) -> int:
        """Validate max_tweets against Free tier limits."""
        from config import Config
        
        # Strict enforcement for media endpoint (Free tier)
        daily_limit = Config.TWITTER_DAILY_TWEET_LIMIT
        
        if v > daily_limit:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"max_tweets={v} exceeds daily limit ({daily_limit}) for Free tier. "
                f"Request may fail or consume monthly quota."
            )
        
        # Hard limit for media endpoint
        if v > 20:
            raise ValueError(
                f"max_tweets={v} exceeds maximum allowed (20) for Free tier. "
                f"Use campaign endpoint for higher limits."
            )
        
        return v
    
    @field_validator('politician')
    @classmethod
    def validate_politician(cls, v: Optional[str]) -> Optional[str]:
        """Normalize politician Twitter handle."""
        if v is None:
            return None
        
        v = v.strip()
        # Remove @ if present (will be added when needed)
        if v.startswith('@'):
            v = v[1:]
        
        # Basic validation
        if len(v) == 0:
            return None
        
        if len(v) > 15:  # Twitter username max length
            raise ValueError("Twitter handle too long (max 15 characters)")
        
        return v


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
