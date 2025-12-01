from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.schemas.core import (
    CoreAnalysisResult,
    SentimentOverview,
    TopicAnalysis,
    PeakEvent,
    ChartData,
)
from app.services.narrative_metrics_service import NarrativeMetricsService

logger = logging.getLogger(__name__)


class AnalysisCorePipeline:
    """
    Core pipeline reused by media and campaign products.
    Reuses existing services to avoid behavior changes.
    """

    def __init__(
        self,
        twitter_service,
        sentiment_service,
        trending_service,
        topic_classifier_service,
        chart_service,
        db_service=None,
    ):
        self.twitter_service = twitter_service
        self.sentiment_service = sentiment_service
        self.trending_service = trending_service
        self.topic_classifier_service = topic_classifier_service
        self.chart_service = chart_service
        self.db_service = db_service
        self.narrative_metrics = NarrativeMetricsService()

    def run_core_pipeline(
        self,
        *,
        location: str,
        topic: Optional[str],
        candidate_name: Optional[str],
        politician: Optional[str],
        max_tweets: int,
        time_window_days: int,
        language: str = "es",
    ) -> CoreAnalysisResult:
        now = datetime.utcnow()
        time_from = now - timedelta(days=time_window_days)
        time_to = now

        trending_topic = None
        try:
            trending_topic = self.trending_service.get_trending_for_speech(
                location=location,
                candidate_name=candidate_name or "el candidato",
            )
        except Exception as exc:
            logger.warning(f"Trending service unavailable: {exc}")

        raw_query = self._build_query(
            location=location,
            topic=topic,
            candidate_name=candidate_name,
            politician=politician,
            language=language,
        )

        tweets = self.twitter_service.search_by_pnd_topic(
            topic=topic or "todos",
            location=location,
            candidate_name=candidate_name,
            politician=politician,
            max_results=max_tweets,
        )

        if not tweets:
            empty_sentiment = SentimentOverview(
                positive=0.0, neutral=0.0, negative=0.0
            )
            empty_chart = ChartData(
                by_topic_sentiment={},
                volume_over_time={},
                sentiment_overall={},
                peaks_over_time={},
            )
            return CoreAnalysisResult(
                tweets_analyzed=0,
                location=location,
                topic=topic,
                time_window_from=time_from,
                time_window_to=time_to,
                sentiment_overview=empty_sentiment,
                topics=[],
                peaks=[],
                chart_data=empty_chart,
                trending_topic=trending_topic.get("topic") if (trending_topic and isinstance(trending_topic, dict)) else None,
                raw_query=raw_query,
            )

        tweets_with_sentiment = self.sentiment_service.analyze_tweets(tweets)

        topics_analysis = self.topic_classifier_service.classify_tweets_by_pnd_topic(
            tweets_with_sentiment,
            theme=topic or "Todos",
        )

        sentiment_overview = self._build_sentiment_overview(tweets_with_sentiment)

        peaks: List[PeakEvent] = []

        chart_data = self.chart_service.generate_charts(
            topics_analysis=topics_analysis,
            sentiment_overview=sentiment_overview,
            tweets=tweets_with_sentiment,
            peaks=peaks,
        )

        # Calculate narrative metrics if candidate_name is provided
        narrative_metrics_result = None
        if candidate_name:
            try:
                sentiment_scores = [
                    {
                        "positive": t.get("sentiment", {}).get("positive", 0.0),
                        "negative": t.get("sentiment", {}).get("negative", 0.0),
                        "neutral": t.get("sentiment", {}).get("neutral", 0.0)
                    }
                    for t in tweets_with_sentiment
                ]
                narrative_metrics_result = self.narrative_metrics.calculate_all_metrics(
                    tweets=tweets_with_sentiment,
                    sentiment_scores=sentiment_scores,
                    candidate_name=candidate_name,
                    topic=topic
                )
            except Exception as exc:
                logger.warning(f"Could not calculate narrative metrics: {exc}")

        core_result = CoreAnalysisResult(
            tweets_analyzed=len(tweets_with_sentiment),
            location=location,
            topic=topic,
            time_window_from=time_from,
            time_window_to=time_to,
            sentiment_overview=sentiment_overview,
            topics=topics_analysis,
            peaks=peaks,
            chart_data=chart_data,
            trending_topic=trending_topic.get("topic") if (trending_topic and isinstance(trending_topic, dict)) else None,
            raw_query=raw_query,
        )
        
        # Attach narrative metrics to result (will be used by forecast endpoints)
        if narrative_metrics_result:
            core_result.narrative_metrics = narrative_metrics_result  # type: ignore

        if self.db_service is not None:
            try:
                # Persist in a minimal, non-breaking way
                self.db_service.save_analysis_core(core_result)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.debug(f"Skipping DB persistence for core analysis: {exc}")

        return core_result

    def _build_query(
        self,
        *,
        location: str,
        topic: Optional[str],
        candidate_name: Optional[str],
        politician: Optional[str],
        language: str,
    ) -> str:
        parts = []

        if location:
            parts.append(location)

        if topic:
            topic_query = self.topic_classifier_service.build_topic_query(topic)
            if topic_query:
                parts.append(f"({topic_query})")

        if candidate_name:
            parts.append(candidate_name)

        if politician:
            parts.append(politician)

        if language:
            parts.append(f"lang:{language}")

        return " ".join(parts)

    def _build_sentiment_overview(self, tweets: List[Dict[str, Any]]) -> SentimentOverview:
        total = len(tweets)
        if total == 0:
            return SentimentOverview(positive=0.0, neutral=0.0, negative=0.0)

        pos = sum(1 for t in tweets if t.get("dominant_sentiment") == "positivo")
        neu = sum(1 for t in tweets if t.get("dominant_sentiment") == "neutral")
        neg = sum(1 for t in tweets if t.get("dominant_sentiment") == "negativo")

        return SentimentOverview(
            positive=pos / total,
            neutral=neu / total,
            negative=neg / total,
        )
