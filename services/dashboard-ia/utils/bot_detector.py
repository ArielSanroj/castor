"""
Bot detection and credibility scoring for Twitter accounts.
Combines hard filters (obvious bots) with soft scoring (credibility weighting).
"""
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class BotDetector:
    """
    Hybrid bot detection system:
    1. Hard filters: Remove obvious bots/spam
    2. Soft scoring: Weight remaining accounts by credibility
    """

    # Hard filter thresholds (accounts that fail these are excluded)
    MIN_ACCOUNT_AGE_DAYS = 7
    MIN_FOLLOWERS = 1
    MAX_NUMERIC_CHARS_IN_USERNAME = 6

    # Scoring weights
    SCORE_WEIGHTS = {
        'verified': 0.25,
        'followers_high': 0.15,      # >1000 followers
        'followers_medium': 0.10,    # >100 followers
        'account_age_year': 0.15,    # >1 year old
        'account_age_month': 0.08,   # >1 month old
        'has_bio': 0.08,
        'has_profile_image': 0.07,
        'has_location': 0.05,
        'reasonable_ratio': 0.07,    # followers/following ratio reasonable
    }

    PENALTY_WEIGHTS = {
        'no_bio': -0.10,
        'default_profile': -0.15,
        'suspicious_username': -0.12,
        'new_account': -0.15,        # <30 days
        'no_followers': -0.20,
        'extreme_tweet_rate': -0.15, # >100 tweets/day average
        'follow_ratio_extreme': -0.10,  # following >> followers
    }

    def __init__(self):
        """Initialize bot detector."""
        self._stats = {
            'total_processed': 0,
            'hard_filtered': 0,
            'low_credibility': 0,
            'high_credibility': 0
        }

    def is_obvious_bot(self, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Hard filter: Detect obvious bots that should be excluded entirely.

        Args:
            user_data: Twitter user object with account info

        Returns:
            Tuple of (is_bot, reason)
        """
        if not user_data:
            return True, "no_user_data"

        # Check account age
        created_at = user_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass

            if isinstance(created_at, datetime):
                now = datetime.now(timezone.utc)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                account_age = (now - created_at).days

                if account_age < self.MIN_ACCOUNT_AGE_DAYS:
                    return True, f"account_too_new_{account_age}d"

        # Check followers
        followers = user_data.get('followers_count', 0) or 0
        if followers < self.MIN_FOLLOWERS:
            return True, "no_followers"

        # Check username for bot patterns
        username = user_data.get('username', '') or ''

        # Too many numbers in username (e.g., user29384756)
        numeric_count = sum(c.isdigit() for c in username)
        if numeric_count > self.MAX_NUMERIC_CHARS_IN_USERNAME:
            return True, "suspicious_username_numbers"

        # Bot-like username patterns
        bot_patterns = [
            r'^[a-z]+\d{6,}$',           # word + many numbers
            r'^\d+[a-z]+\d+$',           # number + word + number
            r'^[A-Z][a-z]+\d{5,}$',      # Name12345678
            r'bot|spam|fake|test',        # obvious bot words (case insensitive)
        ]

        for pattern in bot_patterns:
            if re.search(pattern, username, re.IGNORECASE):
                return True, f"suspicious_username_pattern"

        # Check for default/empty profile indicators
        profile_image = user_data.get('profile_image_url', '') or ''
        if 'default_profile' in profile_image.lower():
            # Only filter if combined with other suspicious signals
            if followers < 10 and not user_data.get('description'):
                return True, "default_profile_no_engagement"

        return False, "passed"

    def calculate_credibility_score(self, user_data: Dict[str, Any]) -> float:
        """
        Calculate credibility score for a Twitter account (0.0 - 1.0).
        Higher score = more credible/human-like account.

        Args:
            user_data: Twitter user object with account info

        Returns:
            Credibility score between 0.0 and 1.0
        """
        if not user_data:
            return 0.3  # Default low score for missing data

        score = 0.5  # Base score

        # Positive signals
        if user_data.get('verified', False):
            score += self.SCORE_WEIGHTS['verified']

        followers = user_data.get('followers_count', 0) or 0
        if followers >= 1000:
            score += self.SCORE_WEIGHTS['followers_high']
        elif followers >= 100:
            score += self.SCORE_WEIGHTS['followers_medium']

        # Account age
        created_at = user_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    created_at = None

            if isinstance(created_at, datetime):
                now = datetime.now(timezone.utc)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                account_age_days = (now - created_at).days

                if account_age_days >= 365:
                    score += self.SCORE_WEIGHTS['account_age_year']
                elif account_age_days >= 30:
                    score += self.SCORE_WEIGHTS['account_age_month']
                elif account_age_days < 30:
                    score += self.PENALTY_WEIGHTS['new_account']

        # Profile completeness
        if user_data.get('description'):
            score += self.SCORE_WEIGHTS['has_bio']
        else:
            score += self.PENALTY_WEIGHTS['no_bio']

        profile_image = user_data.get('profile_image_url', '') or ''
        if profile_image and 'default_profile' not in profile_image.lower():
            score += self.SCORE_WEIGHTS['has_profile_image']
        else:
            score += self.PENALTY_WEIGHTS['default_profile']

        if user_data.get('location'):
            score += self.SCORE_WEIGHTS['has_location']

        # Follower/following ratio
        following = user_data.get('following_count', 0) or 0
        if followers > 0 and following > 0:
            ratio = followers / following
            if 0.1 <= ratio <= 10:
                score += self.SCORE_WEIGHTS['reasonable_ratio']
            elif following > followers * 10:  # Following way more than followers
                score += self.PENALTY_WEIGHTS['follow_ratio_extreme']

        # Tweet rate (if available)
        tweet_count = user_data.get('tweet_count', 0) or 0
        if created_at and isinstance(created_at, datetime):
            account_age_days = max((datetime.now(timezone.utc) - created_at).days, 1)
            tweets_per_day = tweet_count / account_age_days
            if tweets_per_day > 100:
                score += self.PENALTY_WEIGHTS['extreme_tweet_rate']

        # Clamp score between 0.1 and 1.0
        return max(0.1, min(1.0, score))

    def process_tweet(self, tweet: Dict[str, Any]) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Process a tweet and its author for bot detection.

        Args:
            tweet: Tweet object with author info

        Returns:
            Tuple of (should_include, credibility_score, enriched_tweet)
        """
        self._stats['total_processed'] += 1

        # Extract user data from tweet
        user_data = tweet.get('author', {}) or tweet.get('user', {}) or {}

        # If user data is nested under 'data'
        if 'data' in user_data:
            user_data = user_data['data']

        # Hard filter check
        is_bot, reason = self.is_obvious_bot(user_data)
        if is_bot:
            self._stats['hard_filtered'] += 1
            logger.debug(f"Filtered bot: {user_data.get('username', 'unknown')} - {reason}")
            return False, 0.0, tweet

        # Calculate credibility score
        credibility = self.calculate_credibility_score(user_data)

        # Track stats
        if credibility < 0.4:
            self._stats['low_credibility'] += 1
        elif credibility > 0.7:
            self._stats['high_credibility'] += 1

        # Enrich tweet with credibility info
        enriched_tweet = tweet.copy()
        enriched_tweet['_credibility'] = {
            'score': credibility,
            'account_age_signal': 'old' if user_data.get('created_at') else 'unknown',
            'followers': user_data.get('followers_count', 0),
            'verified': user_data.get('verified', False)
        }

        return True, credibility, enriched_tweet

    def filter_and_score_tweets(
        self,
        tweets: list,
        min_credibility: float = 0.0
    ) -> Tuple[list, Dict[str, Any]]:
        """
        Filter out bots and score remaining tweets.

        Args:
            tweets: List of tweet objects
            min_credibility: Minimum credibility score to include (0.0-1.0)

        Returns:
            Tuple of (filtered_tweets, stats)
        """
        filtered_tweets = []

        for tweet in tweets:
            should_include, credibility, enriched_tweet = self.process_tweet(tweet)

            if should_include and credibility >= min_credibility:
                filtered_tweets.append(enriched_tweet)

        stats = {
            **self._stats,
            'included': len(filtered_tweets),
            'filtered_total': len(tweets) - len(filtered_tweets),
            'filter_rate': (len(tweets) - len(filtered_tweets)) / max(len(tweets), 1)
        }

        logger.info(
            f"Bot detection: {len(filtered_tweets)}/{len(tweets)} tweets passed "
            f"({stats['hard_filtered']} hard filtered, "
            f"{stats['low_credibility']} low credibility)"
        )

        return filtered_tweets, stats

    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return self._stats.copy()

    def reset_stats(self):
        """Reset detection statistics."""
        self._stats = {
            'total_processed': 0,
            'hard_filtered': 0,
            'low_credibility': 0,
            'high_credibility': 0
        }


# Singleton instance
_bot_detector: Optional[BotDetector] = None


def get_bot_detector() -> BotDetector:
    """Get singleton bot detector instance."""
    global _bot_detector
    if _bot_detector is None:
        _bot_detector = BotDetector()
    return _bot_detector


def calculate_weighted_sentiment(
    sentiment: Dict[str, float],
    credibility: float
) -> Dict[str, float]:
    """
    Weight sentiment scores by account credibility.
    More credible accounts have more influence on aggregated sentiment.

    Args:
        sentiment: Dict with positive, negative, neutral scores
        credibility: Account credibility score (0.0-1.0)

    Returns:
        Dict with weighted sentiment and weight
    """
    return {
        'positive': sentiment.get('positive', 0.0),
        'negative': sentiment.get('negative', 0.0),
        'neutral': sentiment.get('neutral', 0.0),
        'weight': credibility
    }
