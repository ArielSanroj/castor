"""
Twitter API service using Tweepy.
Handles tweet search and data extraction.
"""
import logging
import tweepy
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

from config import Config
from utils.cache import get_cache_key, get, set
from utils.twitter_rate_tracker import (
    can_make_twitter_request,
    record_twitter_usage,
    get_twitter_usage_stats
)
from utils.circuit_breaker import (
    get_twitter_circuit_breaker,
    exponential_backoff,
    CircuitBreakerOpenError
)
from utils.bot_detector import get_bot_detector
from .twitter_keywords import get_topic_keywords

logger = logging.getLogger(__name__)

# Twitter API constants
TWITTER_MIN_RESULTS = 10
TWITTER_MAX_PER_REQUEST = 100


class TwitterService:
    """Service for interacting with Twitter API."""

    def __init__(self):
        """Initialize Twitter API client."""
        if not Config.TWITTER_BEARER_TOKEN:
            raise ValueError("TWITTER_BEARER_TOKEN not configured")

        self.client = self._create_client()
        self._circuit_breaker = get_twitter_circuit_breaker()
        logger.info("TwitterService initialized")

    def _create_client(self) -> tweepy.Client:
        """Create and configure Tweepy client."""
        client_kwargs = {
            'bearer_token': Config.TWITTER_BEARER_TOKEN,
            'consumer_key': Config.TWITTER_API_KEY,
            'consumer_secret': Config.TWITTER_API_SECRET,
            'access_token': Config.TWITTER_ACCESS_TOKEN,
            'access_token_secret': Config.TWITTER_ACCESS_TOKEN_SECRET,
            'wait_on_rate_limit': True,
        }

        if self._supports_timeout():
            client_kwargs['timeout'] = Config.TWITTER_TIMEOUT_SECONDS

        return tweepy.Client(**client_kwargs)

    def _supports_timeout(self) -> bool:
        """Check if tweepy version supports timeout parameter."""
        try:
            import inspect
            params = inspect.signature(tweepy.Client.__init__).parameters
            return 'timeout' in params
        except Exception:
            return False

    @exponential_backoff(
        max_retries=3,
        initial_delay=2.0,
        max_delay=60.0,
        exceptions=(tweepy.TooManyRequests, tweepy.BadRequest, tweepy.Unauthorized, Exception)
    )
    def _call_twitter_api(self, call_func):
        """Execute Twitter API call with circuit breaker and retry logic."""
        try:
            return self._circuit_breaker.call(call_func)
        except CircuitBreakerOpenError:
            logger.error("Twitter circuit breaker is OPEN, rejecting request")
            raise
        except (tweepy.TooManyRequests, tweepy.BadRequest, tweepy.Unauthorized) as e:
            logger.warning(f"Twitter API error: {e}")
            raise

    def _check_rate_limits(self, max_results: int) -> Tuple[bool, int, int]:
        """Check rate limits and calculate adjusted request size."""
        daily_limit = Config.TWITTER_DAILY_TWEET_LIMIT

        if daily_limit < TWITTER_MIN_RESULTS:
            return self._handle_low_daily_limit(daily_limit, max_results)

        adjusted_max = min(max_results, daily_limit)
        can_proceed, reason = can_make_twitter_request(adjusted_max)

        if not can_proceed:
            logger.warning(f"Twitter rate limit check failed: {reason}")
            return False, 0, 0

        return True, adjusted_max, adjusted_max

    def _handle_low_daily_limit(self, daily_limit: int, max_results: int) -> Tuple[bool, int, int]:
        """Handle case where daily limit is below Twitter minimum."""
        logger.info(f"Daily limit ({daily_limit}) below Twitter minimum ({TWITTER_MIN_RESULTS})")

        can_proceed, reason = can_make_twitter_request(TWITTER_MIN_RESULTS)

        if not can_proceed:
            stats = get_twitter_usage_stats()
            remaining = stats["today"]["remaining"]

            if remaining <= 0:
                logger.warning(f"Twitter rate limit check failed: {reason}")
                return False, 0, 0

            logger.warning(f"Quota ({remaining}) less than minimum, attempting anyway")

        actual_limit = min(daily_limit, max_results)
        return True, TWITTER_MIN_RESULTS, actual_limit

    def _build_search_query(self, query: str, location: Optional[str], lang: str) -> str:
        """Build Twitter search query string."""
        if location:
            return f"{location} {query} lang:{lang} -is:retweet"
        return f"{query} lang:{lang} -is:retweet"

    def _parse_user_data(self, user) -> Dict[str, Any]:
        """Parse user object into dictionary."""
        return {
            'id': user.id,
            'username': user.username,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'description': user.description,
            'location': user.location,
            'profile_image_url': user.profile_image_url,
            'verified': getattr(user, 'verified', False),
            'followers_count': user.public_metrics.get('followers_count', 0) if user.public_metrics else 0,
            'following_count': user.public_metrics.get('following_count', 0) if user.public_metrics else 0,
            'tweet_count': user.public_metrics.get('tweet_count', 0) if user.public_metrics else 0,
        }

    def _parse_tweet_data(self, tweet, author_data: Dict, lang: str) -> Dict[str, Any]:
        """Parse tweet object into dictionary."""
        return {
            'id': tweet.id,
            'text': tweet.text,
            'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
            'author_id': tweet.author_id,
            'author': author_data,
            'public_metrics': tweet.public_metrics,
            'lang': tweet.lang or lang
        }

    def _extract_users_from_response(self, response) -> Dict[str, Dict]:
        """Extract user data from API response includes."""
        users_by_id = {}

        if not hasattr(response, 'includes') or not response.includes:
            return users_by_id

        if 'users' not in response.includes:
            return users_by_id

        for user in response.includes['users']:
            users_by_id[user.id] = self._parse_user_data(user)

        return users_by_id

    def _fetch_single_page(self, search_query: str, start_time: str, current_max: int, pagination_token: Optional[str]):
        """Fetch a single page of tweets from API."""
        def _make_api_call():
            return self.client.search_recent_tweets(
                query=search_query,
                max_results=current_max,
                start_time=start_time,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'geo'],
                user_fields=['created_at', 'description', 'location', 'profile_image_url',
                            'public_metrics', 'verified', 'username'],
                expansions=['author_id'],
                next_token=pagination_token
            )
        return self._call_twitter_api(_make_api_call)

    def _fetch_tweets_paginated(self, search_query: str, max_results: int, days_back: int, lang: str) -> List[Dict[str, Any]]:
        """Fetch tweets with pagination."""
        start_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
        tweets = []
        pagination_token = None

        while len(tweets) < max_results:
            remaining = max_results - len(tweets)
            current_max = min(remaining, TWITTER_MAX_PER_REQUEST)

            try:
                response = self._fetch_single_page(search_query, start_time, current_max, pagination_token)

                if not response.data:
                    break

                users_by_id = self._extract_users_from_response(response)

                for tweet in response.data:
                    author_data = users_by_id.get(tweet.author_id, {})
                    tweets.append(self._parse_tweet_data(tweet, author_data, lang))

                pagination_token = response.meta.get('next_token') if hasattr(response, 'meta') and response.meta else None
                if not pagination_token:
                    break

            except tweepy.TooManyRequests:
                logger.warning("Rate limit reached, stopping pagination")
                break
            except tweepy.BadRequest as e:
                logger.error(f"Bad request: {e}")
                break
            except Exception as e:
                logger.error(f"Error searching tweets: {e}")
                break

        return tweets

    def _apply_bot_filter(self, tweets: List[Dict]) -> List[Dict]:
        """Apply bot detection and filter tweets."""
        if not tweets:
            return tweets

        bot_detector = get_bot_detector()
        filtered_tweets, bot_stats = bot_detector.filter_and_score_tweets(tweets)

        logger.info(f"Bot filter: {len(tweets)} -> {len(filtered_tweets)} (filtered {bot_stats['hard_filtered']} bots)")

        return filtered_tweets

    def _search_tweets_impl(self, query: str, location: Optional[str] = None, max_results: int = 100, lang: str = 'es', days_back: int = 7) -> List[Dict[str, Any]]:
        """Search for tweets matching the query."""
        can_proceed, adjusted_max, actual_limit = self._check_rate_limits(max_results)
        if not can_proceed:
            return []

        max_results = max(adjusted_max, TWITTER_MIN_RESULTS)

        try:
            search_query = self._build_search_query(query, location, lang)
            tweets = self._fetch_tweets_paginated(search_query, max_results, days_back, lang)

            if not tweets:
                logger.info(f"No tweets found for query: {query}")
                return []

            tweets_to_use = tweets[:actual_limit]
            record_twitter_usage(len(tweets_to_use))

            filtered_tweets = self._apply_bot_filter(tweets_to_use)

            logger.info(f"Retrieved {len(filtered_tweets)} tweets for query: {query}")
            return filtered_tweets

        except Exception as e:
            logger.error(f"Error in search_tweets: {e}", exc_info=True)
            return []

    def search_tweets(self, query: str, location: Optional[str] = None, max_results: int = 100, lang: str = 'es', days_back: int = 7) -> List[Dict[str, Any]]:
        """Search for tweets with caching."""
        cache_key = get_cache_key("twitter_search", query, location, max_results, lang, days_back)
        cached_result = get(cache_key)

        if cached_result is not None:
            logger.debug(f"Cache hit for Twitter search: {query}")
            return cached_result

        result = self._search_tweets_impl(query, location, max_results, lang, days_back)
        set(cache_key, result, Config.CACHE_TTL_TWITTER)

        return result

    def search_by_pnd_topic(self, topic: str, location: str, candidate_name: Optional[str] = None, politician: Optional[str] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """Search tweets for a specific PND topic."""
        keywords = get_topic_keywords(topic)
        query_parts = [keywords]

        if candidate_name:
            query_parts.append(candidate_name)

        if politician:
            query_parts.append(f"@{politician.replace('@', '')}")

        query = " OR ".join(query_parts)

        return self.search_tweets(query=query, location=location, max_results=max_results)

    def get_tweet_metrics(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific tweet."""
        try:
            def _make_api_call():
                return self.client.get_tweet(tweet_id, tweet_fields=['public_metrics'])

            tweet = self._call_twitter_api(_make_api_call)
            return tweet.data.public_metrics if tweet.data else None
        except Exception as e:
            logger.error(f"Error getting tweet metrics: {e}")
            return None