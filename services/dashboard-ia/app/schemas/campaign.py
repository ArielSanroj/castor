from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from .core import SentimentOverview, TopicAnalysis, ChartData


class CampaignAnalysisRequest(BaseModel):
    """
    Request body for /api/campaign/analyze
    """
    location: str = Field(..., min_length=1, max_length=200, description="Location to analyze")
    theme: str = Field(..., min_length=1, max_length=100, description="PND theme or topic")
    candidate_name: Optional[str] = Field(None, max_length=200, description="Candidate name")
    politician: Optional[str] = Field(None, max_length=100, description="Twitter handle (e.g., @username)")
    max_tweets: int = Field(
        default=120,
        ge=10,
        le=2000,
        description="Maximum tweets to analyze (10-2000). Higher values consume more quota."
    )
    language: str = Field(default="es", pattern="^[a-z]{2}$", description="Language code (ISO 639-1)")
    
    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme against allowed PND topics."""
        from config import Config
        
        # Normalize theme
        theme_lower = v.strip().lower()
        
        # Check if it's a valid PND topic (case-insensitive)
        valid_themes = [t.lower() for t in Config.PND_TOPICS]
        valid_themes.extend(['todos los temas', 'todos', 'all', 'all topics'])
        
        if theme_lower not in valid_themes:
            # Allow custom themes but warn/log
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Custom theme '{v}' not in standard PND topics")
            # Still allow it, but could be restricted in production
        
        return v.strip()
    
    @field_validator('max_tweets')
    @classmethod
    def validate_max_tweets(cls, v: int) -> int:
        """Validate max_tweets against quota limits."""
        from config import Config
        
        # Enforce daily limit for Twitter Free tier
        daily_limit = Config.TWITTER_DAILY_TWEET_LIMIT
        if v > daily_limit * 10:  # Allow some flexibility but warn
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"max_tweets={v} exceeds recommended daily limit ({daily_limit}). "
                f"This may consume monthly quota quickly."
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


class ExecutiveSummary(BaseModel):
    overview: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class StrategicAction(BaseModel):
    description: str
    priority: str
    estimated_timeline: Optional[str] = None
    expected_impact: Optional[str] = None


class StrategicObjective(BaseModel):
    name: str
    description: Optional[str] = None
    actions: List[StrategicAction] = Field(default_factory=list)


class StrategicPlan(BaseModel):
    objectives: List[StrategicObjective] = Field(default_factory=list)
    timeline: Optional[Dict[str, Any]] = None
    overall_expected_impact: Optional[str] = None


class Speech(BaseModel):
    title: str
    key_points: List[str] = Field(default_factory=list)
    content: str
    duration_minutes: Optional[int] = None
    trending_topic: Optional[str] = None


class CampaignMetadata(BaseModel):
    tweets_analyzed: int
    location: str
    theme: str
    candidate_name: Optional[str] = None
    politician: Optional[str] = None
    generated_at: datetime
    trending_topic: Optional[str] = None
    raw_query: Optional[str] = None


class CampaignAnalysisResponse(BaseModel):
    success: bool = True

    executive_summary: ExecutiveSummary
    topic_analyses: List[TopicAnalysis]
    strategic_plan: StrategicPlan
    speech: Speech
    chart_data: ChartData

    metadata: CampaignMetadata
