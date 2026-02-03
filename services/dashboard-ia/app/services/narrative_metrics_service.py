"""
Narrative Metrics Service for calculating campaign communication metrics.
Provides ICCE, SOV, SNA, and Momentum calculations.
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NarrativeMetricsService:
    """
    Service for calculating narrative/communication metrics.

    Metrics:
    - ICCE: Indice de Comunicacion y Confianza Electoral (0-100)
    - SOV: Share of Voice - percentage of conversation
    - SNA: Sentiment Net Average (-100 to 100)
    - Momentum: Trend direction indicator
    """

    def calculate_all_metrics(
        self,
        tweets: List[Dict[str, Any]],
        sentiment_scores: List[Dict[str, float]],
        candidate_name: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate all narrative metrics from tweet data.

        Args:
            tweets: List of tweet dictionaries
            sentiment_scores: List of sentiment score dicts with positive/negative/neutral
            candidate_name: Optional candidate name for filtering
            topic: Optional topic for context

        Returns:
            Dictionary with icce, sov, sna, momentum metrics
        """
        if not tweets or not sentiment_scores:
            return {
                "icce": 50.0,
                "sov": 0.0,
                "sna": 0.0,
                "momentum": 0.0,
                "tweet_count": 0
            }

        try:
            # Calculate SNA (Sentiment Net Average)
            total_positive = sum(s.get("positive", 0.0) for s in sentiment_scores)
            total_negative = sum(s.get("negative", 0.0) for s in sentiment_scores)
            total_neutral = sum(s.get("neutral", 0.0) for s in sentiment_scores)

            total_sentiment = total_positive + total_negative + total_neutral
            if total_sentiment > 0:
                avg_positive = total_positive / len(sentiment_scores)
                avg_negative = total_negative / len(sentiment_scores)
                sna = (avg_positive - avg_negative) * 100
            else:
                sna = 0.0

            # Calculate SOV (Share of Voice) - simplified
            # In a real implementation, this would compare against competitor mentions
            sov = min(100.0, len(tweets) / 10.0)  # Simplified: 10 tweets = 100% SOV

            # Calculate ICCE (Indice de Comunicacion y Confianza Electoral)
            # Based on sentiment, volume, and engagement
            engagement_total = sum(
                t.get("retweet_count", 0) + t.get("like_count", 0) + t.get("reply_count", 0)
                for t in tweets
            )
            avg_engagement = engagement_total / len(tweets) if tweets else 0

            # ICCE formula: base 50 + sentiment contribution + engagement bonus
            sentiment_contribution = sna * 0.3  # 30% weight
            engagement_bonus = min(15, avg_engagement / 10)  # Max 15 points from engagement
            volume_bonus = min(10, len(tweets) / 20)  # Max 10 points from volume

            icce = max(0, min(100, 50 + sentiment_contribution + engagement_bonus + volume_bonus))

            # Calculate Momentum (trend indicator)
            # Simplified: based on recent sentiment trend
            if len(sentiment_scores) >= 2:
                recent_scores = sentiment_scores[-5:] if len(sentiment_scores) >= 5 else sentiment_scores
                old_scores = sentiment_scores[:5] if len(sentiment_scores) >= 5 else []

                if old_scores:
                    recent_avg = sum(s.get("positive", 0) - s.get("negative", 0) for s in recent_scores) / len(recent_scores)
                    old_avg = sum(s.get("positive", 0) - s.get("negative", 0) for s in old_scores) / len(old_scores)
                    momentum = (recent_avg - old_avg) * 50
                else:
                    momentum = 0.0
            else:
                momentum = 0.0

            return {
                "icce": round(icce, 1),
                "sov": round(sov, 1),
                "sna": round(sna, 1),
                "momentum": round(momentum, 1),
                "tweet_count": len(tweets),
                "avg_engagement": round(avg_engagement, 1),
                "sentiment_distribution": {
                    "positive": round(total_positive / len(sentiment_scores), 3) if sentiment_scores else 0,
                    "negative": round(total_negative / len(sentiment_scores), 3) if sentiment_scores else 0,
                    "neutral": round(total_neutral / len(sentiment_scores), 3) if sentiment_scores else 0
                }
            }

        except Exception as e:
            logger.error(f"Error calculating narrative metrics: {e}")
            return {
                "icce": 50.0,
                "sov": 0.0,
                "sna": 0.0,
                "momentum": 0.0,
                "tweet_count": len(tweets),
                "error": str(e)
            }
