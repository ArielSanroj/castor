"""
Analysis Module Facade.

Provides a clean interface for analysis operations.
Internally uses existing services but exposes a stable public API.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import (
    AnalysisRequest,
    AnalysisResult,
    SentimentResult,
    TopicResult,
    ChartDataPoint,
)

logger = logging.getLogger(__name__)


class AnalysisModule:
    """
    Facade for analysis operations.

    This class provides a stable public interface for analysis operations.
    Internally it delegates to the existing services.

    Usage:
        module = AnalysisModule()
        result = module.analyze(AnalysisRequest(
            location="Bogota",
            topic="Seguridad"
        ))
    """

    def __init__(self):
        """Initialize analysis module."""
        self._pipeline = None
        self._twitter_service = None
        self._sentiment_service = None

    def _get_pipeline(self):
        """Lazy load analysis pipeline."""
        if self._pipeline is None:
            try:
                from app.services.analysis_core import AnalysisCorePipeline
                self._pipeline = AnalysisCorePipeline()
            except Exception as e:
                logger.error(f"Failed to initialize pipeline: {e}")
        return self._pipeline

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Perform analysis based on request.

        Args:
            request: Analysis request parameters

        Returns:
            AnalysisResult with analysis data
        """
        pipeline = self._get_pipeline()

        if not pipeline:
            return AnalysisResult(
                success=False,
                location=request.location,
                topic=request.topic,
                tweets_analyzed=0,
                sentiment_overview=SentimentResult(0.33, 0.33, 0.34),
                topics=[],
                chart_data=[],
                peaks=[],
                trending_topic=None,
                time_window_from=datetime.now(),
                time_window_to=datetime.now(),
                error="Analysis pipeline not available"
            )

        try:
            core_result = pipeline.run_core_pipeline(
                location=request.location,
                topic=request.topic,
                candidate_name=request.candidate_name,
                politician=request.politician,
                max_tweets=request.max_tweets,
                time_window_days=request.time_window_days,
                language=request.language
            )

            # Convert to module models
            sentiment_overview = SentimentResult(
                positive=core_result.sentiment_overview.positive,
                negative=core_result.sentiment_overview.negative,
                neutral=core_result.sentiment_overview.neutral
            )

            topics = [
                TopicResult(
                    topic=t.topic,
                    sentiment=SentimentResult(
                        positive=t.sentiment.positive,
                        negative=t.sentiment.negative,
                        neutral=t.sentiment.neutral
                    ),
                    tweet_count=t.tweet_count,
                    key_insights=t.key_insights if hasattr(t, 'key_insights') else [],
                    sample_tweets=t.sample_tweets if hasattr(t, 'sample_tweets') else []
                )
                for t in core_result.topics
            ]

            chart_data = [
                ChartDataPoint(
                    date=c.date if hasattr(c, 'date') else c.get('date', ''),
                    positive=c.positive if hasattr(c, 'positive') else c.get('positive', 0),
                    negative=c.negative if hasattr(c, 'negative') else c.get('negative', 0),
                    neutral=c.neutral if hasattr(c, 'neutral') else c.get('neutral', 0)
                )
                for c in core_result.chart_data
            ]

            return AnalysisResult(
                success=True,
                location=core_result.location,
                topic=core_result.topic,
                tweets_analyzed=core_result.tweets_analyzed,
                sentiment_overview=sentiment_overview,
                topics=topics,
                chart_data=chart_data,
                peaks=core_result.peaks,
                trending_topic=core_result.trending_topic,
                time_window_from=core_result.time_window_from,
                time_window_to=core_result.time_window_to,
                raw_query=core_result.raw_query
            )

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return AnalysisResult(
                success=False,
                location=request.location,
                topic=request.topic,
                tweets_analyzed=0,
                sentiment_overview=SentimentResult(0.33, 0.33, 0.34),
                topics=[],
                chart_data=[],
                peaks=[],
                trending_topic=None,
                time_window_from=datetime.now(),
                time_window_to=datetime.now(),
                error=str(e)
            )

    def get_sentiment(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of sentiment results
        """
        try:
            from services.sentiment_service import SentimentService
            service = SentimentService()
            results = []

            for text in texts:
                sentiment = service.analyze_sentiment(text)
                results.append(SentimentResult(
                    positive=sentiment.get('positive', 0.33),
                    negative=sentiment.get('negative', 0.33),
                    neutral=sentiment.get('neutral', 0.34)
                ))

            return results

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return [SentimentResult(0.33, 0.33, 0.34) for _ in texts]

    def classify_topic(self, text: str) -> str:
        """
        Classify text into PND topic.

        Args:
            text: Text to classify

        Returns:
            Topic classification
        """
        try:
            from services.topic_classifier_service import TopicClassifierService
            classifier = TopicClassifierService()
            return classifier.classify(text)
        except Exception as e:
            logger.error(f"Topic classification failed: {e}")
            return "General"
