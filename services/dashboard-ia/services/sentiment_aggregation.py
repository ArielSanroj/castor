"""
Sentiment Aggregation utilities for CASTOR ELECCIONES.
Provides aggregation and statistics for sentiment data.
"""
from typing import Any, Dict, List
from models.schemas import SentimentData


def aggregate_sentiment(sentiments: List[SentimentData]) -> SentimentData:
    """
    Aggregate multiple sentiment analyses into one.

    Args:
        sentiments: List of SentimentData objects

    Returns:
        Aggregated SentimentData
    """
    if not sentiments:
        return SentimentData(positive=0.33, negative=0.33, neutral=0.34)

    total = len(sentiments)
    avg_positive = sum(s.positive for s in sentiments) / total
    avg_negative = sum(s.negative for s in sentiments) / total
    avg_neutral = sum(s.neutral for s in sentiments) / total

    # Normalize to ensure they sum to 1
    total_score = avg_positive + avg_negative + avg_neutral
    if total_score > 0:
        return SentimentData(
            positive=avg_positive / total_score,
            negative=avg_negative / total_score,
            neutral=avg_neutral / total_score
        )

    return SentimentData(positive=0.33, negative=0.33, neutral=0.34)


def aggregate_sentiment_weighted(tweets: List[Dict[str, Any]]) -> SentimentData:
    """
    Aggregate sentiment weighted by account credibility.
    More credible accounts have more influence on the final score.

    Args:
        tweets: List of tweet dicts with 'sentiment' and '_credibility' fields

    Returns:
        Weighted aggregated SentimentData
    """
    if not tweets:
        return SentimentData(positive=0.33, negative=0.33, neutral=0.34)

    weighted_positive = 0.0
    weighted_negative = 0.0
    weighted_neutral = 0.0
    total_weight = 0.0

    for tweet in tweets:
        sentiment = tweet.get('sentiment', {})
        credibility = tweet.get('_credibility', {})

        # Get credibility weight (default 0.5 if not available)
        weight = credibility.get('score', 0.5) if isinstance(credibility, dict) else 0.5

        # Accumulate weighted sentiments
        weighted_positive += sentiment.get('positive', 0.33) * weight
        weighted_negative += sentiment.get('negative', 0.33) * weight
        weighted_neutral += sentiment.get('neutral', 0.34) * weight
        total_weight += weight

    if total_weight == 0:
        return SentimentData(positive=0.33, negative=0.33, neutral=0.34)

    # Calculate weighted averages
    avg_positive = weighted_positive / total_weight
    avg_negative = weighted_negative / total_weight
    avg_neutral = weighted_neutral / total_weight

    # Normalize to ensure they sum to 1
    total_score = avg_positive + avg_negative + avg_neutral
    if total_score > 0:
        return SentimentData(
            positive=avg_positive / total_score,
            negative=avg_negative / total_score,
            neutral=avg_neutral / total_score
        )

    return SentimentData(positive=0.33, negative=0.33, neutral=0.34)


def get_credibility_stats(tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about credibility scores in a set of tweets.

    Args:
        tweets: List of tweets with _credibility field

    Returns:
        Dict with credibility statistics
    """
    if not tweets:
        return {'count': 0, 'avg_credibility': 0.0, 'high_credibility': 0, 'low_credibility': 0}

    scores = []
    high_cred = 0
    low_cred = 0

    for tweet in tweets:
        cred = tweet.get('_credibility', {})
        score = cred.get('score', 0.5) if isinstance(cred, dict) else 0.5
        scores.append(score)

        if score >= 0.7:
            high_cred += 1
        elif score < 0.4:
            low_cred += 1

    return {
        'count': len(tweets),
        'avg_credibility': sum(scores) / len(scores) if scores else 0.0,
        'high_credibility_count': high_cred,
        'low_credibility_count': low_cred,
        'high_credibility_pct': (high_cred / len(tweets)) * 100 if tweets else 0,
        'low_credibility_pct': (low_cred / len(tweets)) * 100 if tweets else 0
    }
