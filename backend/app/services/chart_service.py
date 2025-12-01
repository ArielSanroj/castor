from __future__ import annotations

from typing import List, Dict, Any

from app.schemas.core import ChartData, TopicAnalysis
from models.schemas import PNDTopicAnalysis, SentimentData
from utils.chart_generator import ChartGenerator


class ChartService:
    """
    Adapter that reuses ChartGenerator to build Chart.js configs.
    """

    def generate_charts(
        self,
        topics_analysis: List[TopicAnalysis],
        sentiment_overview,
        tweets,
        peaks,
    ) -> ChartData:
        # Convert to legacy schema expected by ChartGenerator
        legacy_topics: List[PNDTopicAnalysis] = []
        for topic in topics_analysis:
            legacy_topics.append(
                PNDTopicAnalysis(
                    topic=topic.topic,
                    sentiment=SentimentData(
                        positive=topic.sentiment.positive,
                        negative=topic.sentiment.negative,
                        neutral=topic.sentiment.neutral,
                    ),
                    tweet_count=topic.tweet_count,
                    key_insights=[],
                    sample_tweets=[],
                )
            )

        legacy_chart = ChartGenerator.generate_sentiment_chart(legacy_topics)
        by_topic_sentiment = {
            "type": legacy_chart.type,
            "data": {
                "labels": legacy_chart.labels,
                "datasets": legacy_chart.datasets,
            },
            "options": legacy_chart.options,
        }

        return ChartData(
            by_topic_sentiment=by_topic_sentiment,
            volume_over_time={},
            sentiment_overall={},
            peaks_over_time={},
        )
