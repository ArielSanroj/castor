"""
Analysis Module Models.

Data transfer objects for the analysis module.
These are the public contract for this module.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AnalysisRequest:
    """Request for analysis operation."""
    location: str
    topic: Optional[str] = None
    candidate_name: Optional[str] = None
    politician: Optional[str] = None
    max_tweets: int = 15
    time_window_days: int = 7
    language: str = "es"
    user_id: Optional[str] = None


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    positive: float
    negative: float
    neutral: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral
        }


@dataclass
class TopicResult:
    """Topic analysis result."""
    topic: str
    sentiment: SentimentResult
    tweet_count: int
    key_insights: List[str] = field(default_factory=list)
    sample_tweets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "sentiment": self.sentiment.to_dict(),
            "tweet_count": self.tweet_count,
            "key_insights": self.key_insights,
            "sample_tweets": self.sample_tweets
        }


@dataclass
class ChartDataPoint:
    """Data point for chart visualization."""
    date: str
    positive: int
    negative: int
    neutral: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral
        }


@dataclass
class AnalysisResult:
    """Result of analysis operation."""
    success: bool
    location: str
    topic: Optional[str]
    tweets_analyzed: int
    sentiment_overview: SentimentResult
    topics: List[TopicResult]
    chart_data: List[ChartDataPoint]
    peaks: List[Dict[str, Any]]
    trending_topic: Optional[str]
    time_window_from: datetime
    time_window_to: datetime
    raw_query: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "location": self.location,
            "topic": self.topic,
            "tweets_analyzed": self.tweets_analyzed,
            "sentiment_overview": self.sentiment_overview.to_dict(),
            "topics": [t.to_dict() for t in self.topics],
            "chart_data": [c.to_dict() for c in self.chart_data],
            "peaks": self.peaks,
            "trending_topic": self.trending_topic,
            "time_window_from": self.time_window_from.isoformat(),
            "time_window_to": self.time_window_to.isoformat(),
            "raw_query": self.raw_query,
            "error": self.error
        }
