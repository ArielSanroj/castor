from __future__ import annotations

from typing import Dict, List, Optional

from app.schemas.core import TopicAnalysis, SentimentOverview


class TopicClassifierService:
    """
    Wrapper that reuses existing topic classification helpers.
    """

    def __init__(self):
        # Deferred imports to avoid circular deps
        from app.routes.analysis import _classify_tweets_by_topic, _get_topic_keywords

        self._classify = _classify_tweets_by_topic
        self._get_keywords = _get_topic_keywords

    def build_topic_query(self, topic: Optional[str]) -> Optional[str]:
        if not topic:
            return None
        return self._get_keywords(topic)

    def classify_tweets_by_pnd_topic(
        self,
        tweets: List[Dict],
        theme: Optional[str],
    ) -> List[TopicAnalysis]:
        """
        Reuse the existing classifier and adapt to TopicAnalysis.
        """
        theme_value = theme or "Todos"
        legacy_results = self._classify(tweets, theme_value)

        topic_analyses: List[TopicAnalysis] = []
        for result in legacy_results:
            sentiment = result.sentiment
            topic_analyses.append(
                TopicAnalysis(
                    topic=result.topic,
                    tweet_count=result.tweet_count,
                    sentiment=SentimentOverview(
                        positive=sentiment.positive,
                        neutral=sentiment.neutral,
                        negative=sentiment.negative,
                    ),
                    sample_terms=None,
                    sample_tweets_ids=None,
                )
            )
        return topic_analyses
