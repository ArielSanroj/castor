from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SentimentOverview(BaseModel):
    """Overview of sentiment distribution."""
    positive: float = 0.0
    neutral: float = 0.0
    negative: float = 0.0


class TopicAnalysis(BaseModel):
    """Analysis of a single topic."""
    topic: str = ""
    tweet_count: int = 0
    sentiment: Dict[str, float] = Field(default_factory=lambda: {
        "positive": 0.33,
        "neutral": 0.34,
        "negative": 0.33
    })
    keywords: List[str] = Field(default_factory=list)
    sample_tweets: List[str] = Field(default_factory=list)


class PeakEvent(BaseModel):
    """Represents a peak event in the timeline."""
    timestamp: datetime
    volume: int = 0
    description: str = ""
    dominant_sentiment: Optional[str] = None


class ChartData(BaseModel):
    """Chart data for frontend visualization."""
    by_topic_sentiment: Dict[str, Any] = Field(default_factory=dict)
    volume_over_time: Dict[str, Any] = Field(default_factory=dict)
    sentiment_overall: Dict[str, Any] = Field(default_factory=dict)
    peaks_over_time: Dict[str, Any] = Field(default_factory=dict)


class TweetData(BaseModel):
    """Tweet data for frontend display."""
    tweet_id: str = ""
    author_username: str = ""
    author_name: Optional[str] = None
    content: str = ""
    sentiment_label: Optional[str] = None
    pnd_topic: Optional[str] = None
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0


class CoreAnalysisResult(BaseModel):
    """Result from core analysis pipeline."""
    tweets_analyzed: int = 0
    location: str = ""
    topic: Optional[str] = None
    time_window_from: datetime
    time_window_to: datetime
    sentiment_overview: SentimentOverview
    topics: List[Any] = Field(default_factory=list)
    peaks: List[PeakEvent] = Field(default_factory=list)
    chart_data: ChartData
    tweets_data: List[TweetData] = Field(default_factory=list)
    trending_topic: Optional[str] = None
    raw_query: Optional[str] = None
    narrative_metrics: Optional[Dict[str, Any]] = None
