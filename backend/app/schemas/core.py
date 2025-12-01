from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SentimentOverview(BaseModel):
    positive: float = Field(..., ge=0.0, le=1.0)
    neutral: float = Field(..., ge=0.0, le=1.0)
    negative: float = Field(..., ge=0.0, le=1.0)


class TopicAnalysis(BaseModel):
    topic: str
    tweet_count: int = Field(..., ge=0)
    sentiment: SentimentOverview
    sample_terms: Optional[List[str]] = None
    sample_tweets_ids: Optional[List[str]] = None


class PeakEvent(BaseModel):
    timestamp: datetime
    label: Optional[str] = None
    approx_volume: int = Field(..., ge=0)


class ChartData(BaseModel):
    """
    Chart.js compatible configs.
    """
    by_topic_sentiment: Dict[str, Any]
    volume_over_time: Dict[str, Any]
    sentiment_overall: Optional[Dict[str, Any]] = None
    peaks_over_time: Optional[Dict[str, Any]] = None


class CoreAnalysisResult(BaseModel):
    """
    Core analysis output shared by media and campaign products.
    """
    tweets_analyzed: int = Field(..., ge=0)
    location: str
    topic: Optional[str] = None

    time_window_from: datetime
    time_window_to: datetime

    sentiment_overview: SentimentOverview
    topics: List[TopicAnalysis]
    peaks: List[PeakEvent]
    chart_data: ChartData

    trending_topic: Optional[str] = None
    raw_query: Optional[str] = None
    narrative_metrics: Optional[Dict[str, Any]] = None  # Added for IVN and narrative indices
