"""
Twitter API service using Tweepy.
Handles tweet search and data extraction.
"""
import logging
import tweepy
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from config import Config
from utils.cache import get_cache_key, get, set
from utils.twitter_rate_tracker import can_make_twitter_request, record_twitter_usage, get_twitter_usage_stats
from utils.circuit_breaker import (
    get_twitter_circuit_breaker,
    exponential_backoff,
    CircuitBreakerOpenError
)

logger = logging.getLogger(__name__)


class TwitterService:
    """Service for interacting with Twitter API."""
    
    def __init__(self):
        """Initialize Twitter API client."""
        if not Config.TWITTER_BEARER_TOKEN:
            raise ValueError("TWITTER_BEARER_TOKEN not configured")
        
        # Build client kwargs - some tweepy versions don't support timeout
        client_kwargs = {
            'bearer_token': Config.TWITTER_BEARER_TOKEN,
            'consumer_key': Config.TWITTER_API_KEY,
            'consumer_secret': Config.TWITTER_API_SECRET,
            'access_token': Config.TWITTER_ACCESS_TOKEN,
            'access_token_secret': Config.TWITTER_ACCESS_TOKEN_SECRET,
            'wait_on_rate_limit': True,
        }

        # Only add timeout if supported by this tweepy version
        try:
            import inspect
            client_init_params = inspect.signature(tweepy.Client.__init__).parameters
            if 'timeout' in client_init_params:
                client_kwargs['timeout'] = Config.TWITTER_TIMEOUT_SECONDS
        except Exception:
            pass  # If we can't check, skip timeout parameter

        self.client = tweepy.Client(**client_kwargs)
        self._circuit_breaker = get_twitter_circuit_breaker()
        logger.info("TwitterService initialized")
    
    @exponential_backoff(
        max_retries=3,
        initial_delay=2.0,
        max_delay=60.0,
        exceptions=(tweepy.TooManyRequests, tweepy.BadRequest, tweepy.Unauthorized, Exception)
    )
    def _call_twitter_api(self, call_func):
        """
        Execute Twitter API call with circuit breaker and retry logic.
        
        Args:
            call_func: Function that makes the Twitter API call
            
        Returns:
            API response
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            Exception: Original exception from API call
        """
        try:
            return self._circuit_breaker.call(call_func)
        except CircuitBreakerOpenError:
            logger.error("Twitter circuit breaker is OPEN, rejecting request")
            raise
        except (tweepy.TooManyRequests, tweepy.BadRequest, tweepy.Unauthorized) as e:
            logger.warning(f"Twitter API error: {e}")
            raise
    
    def _search_tweets_impl(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 100,
        lang: str = 'es',
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Search for tweets matching the query.
        
        Args:
            query: Search query string
            location: Optional location filter
            max_results: Maximum number of results (10-500)
            lang: Language code (default: 'es' for Spanish)
            days_back: Number of days to look back
            
        Returns:
            List of tweet dictionaries
        """
        # Check rate limit before making request (Twitter Free tier: 100 posts/month)
        # Adjust max_results to respect daily limit, but ensure minimum of 10 (Twitter API requirement)
        from config import Config
        daily_limit = Config.TWITTER_DAILY_TWEET_LIMIT
        
        # Twitter API requires min 10 results per request
        TWITTER_MIN_RESULTS = 10
        
        # If daily limit is less than minimum, we need to request minimum but will only use what's available
        if daily_limit < TWITTER_MIN_RESULTS:
            logger.info(f"Daily limit ({daily_limit}) is below Twitter minimum ({TWITTER_MIN_RESULTS}). Will request minimum but only use {daily_limit}.")
            # Check if we have any remaining quota (even if less than minimum)
            can_proceed, reason = can_make_twitter_request(TWITTER_MIN_RESULTS)
            logger.info(f"Rate limit check for {TWITTER_MIN_RESULTS} tweets: can_proceed={can_proceed}, reason={reason}")
            if not can_proceed:
                # If we can't make the minimum request, check if we have ANY quota left
                stats = get_twitter_usage_stats()
                remaining = stats["today"]["remaining"]
                logger.info(f"Checking remaining quota: {remaining} tweets available")
                if remaining <= 0:
                    logger.warning(f"Twitter rate limit check failed: {reason}")
                    return []
                # If we have some quota but less than minimum, log warning but proceed
                logger.warning(f"Daily quota ({remaining}) is less than Twitter minimum ({TWITTER_MIN_RESULTS}), but attempting anyway to verify connection.")
            # Use minimum required by Twitter, but respect the daily limit by only processing that many
            adjusted_max = TWITTER_MIN_RESULTS
            actual_limit = min(daily_limit, max_results)  # We'll only process this many from the results
            logger.info(f"Proceeding with request: adjusted_max={adjusted_max}, actual_limit={actual_limit}")
        else:
            adjusted_max = min(max_results, daily_limit)
            actual_limit = adjusted_max
            can_proceed, reason = can_make_twitter_request(adjusted_max)
            if not can_proceed:
                logger.warning(f"Twitter rate limit check failed: {reason}")
                return []
        
        # Use adjusted max_results for the actual request (must be >= 10)
        max_results = max(adjusted_max, TWITTER_MIN_RESULTS)
        
        try:
            # Build query string
            # Note: place: operator requires paid Twitter API plan
            # Using location as text search instead for Free tier compatibility
            search_query = f"{query} lang:{lang} -is:retweet"
            if location:
                # Include location as text in query instead of place: operator
                search_query = f"{location} {query} lang:{lang} -is:retweet"
            
            # Calculate date range
            start_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            
            # Search tweets
            tweets = []
            pagination_token = None
            
            while len(tweets) < max_results:
                remaining = max_results - len(tweets)
                current_max = min(remaining, 100)  # API limit per request
                
                try:
                    def _make_api_call():
                        return self.client.search_recent_tweets(
                            query=search_query,
                            max_results=current_max,
                            start_time=start_time,
                            tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'geo'],
                            next_token=pagination_token
                        )
                    
                    response = self._call_twitter_api(_make_api_call)
                    
                    if not response.data:
                        break
                    
                    for tweet in response.data:
                        tweets.append({
                            'id': tweet.id,
                            'text': tweet.text,
                            'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                            'author_id': tweet.author_id,
                            'public_metrics': tweet.public_metrics,
                            'lang': tweet.lang or lang
                        })
                    
                    # Check if there are more pages
                    if not hasattr(response, 'meta') or not response.meta.get('next_token'):
                        break
                    
                    pagination_token = response.meta['next_token']
                    
                except tweepy.TooManyRequests:
                    logger.warning("Rate limit reached, waiting...")
                    break
                except tweepy.BadRequest as e:
                    logger.error(f"Bad request: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error searching tweets: {e}")
                    break
            
            # Record usage for rate limiting (only count what we actually use)
            if tweets:
                # If we had to request more than daily limit, only return and count what we use
                tweets_to_use = tweets[:actual_limit]
                record_twitter_usage(len(tweets_to_use))
                logger.info(f"Retrieved {len(tweets)} tweets for query: {query}, using {len(tweets_to_use)}")
                return tweets_to_use
            
            logger.info(f"Retrieved {len(tweets)} tweets for query: {query}")
            return tweets
            
        except Exception as e:
            logger.error(f"Error in search_tweets: {e}", exc_info=True)
            return []
    
    def search_tweets(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 100,
        lang: str = 'es',
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Search for tweets with caching.
        
        Args:
            query: Search query string
            location: Optional location filter
            max_results: Maximum number of results
            lang: Language code
            days_back: Number of days to look back
            
        Returns:
            List of tweet dictionaries
        """
        # Check cache first
        cache_key = get_cache_key("twitter_search", query, location, max_results, lang, days_back)
        cached_result = get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for Twitter search: {query}")
            return cached_result
        
        # Call implementation
        result = self._search_tweets_impl(query, location, max_results, lang, days_back)
        
        # Cache result
        set(cache_key, result, Config.CACHE_TTL_TWITTER)
        return result
    
    def search_by_pnd_topic(
        self,
        topic: str,
        location: str,
        candidate_name: Optional[str] = None,
        politician: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search tweets for a specific PND topic.
        
        Args:
            topic: PND topic name
            location: Location to search
            candidate_name: Optional candidate name
            politician: Optional politician Twitter handle
            max_results: Maximum tweets to retrieve
            
        Returns:
            List of relevant tweets
        """
        # Build keyword query based on topic
        keywords = self._get_topic_keywords(topic)
        query_parts = [keywords]
        
        if candidate_name:
            query_parts.append(candidate_name)
        
        if politician:
            query_parts.append(f"@{politician.replace('@', '')}")
        
        query = " OR ".join(query_parts)
        
        return self.search_tweets(
            query=query,
            location=location,
            max_results=max_results
        )
    
    def _get_topic_keywords(self, topic: str) -> str:
        """Get search keywords for a PND topic."""
        topic_keywords = {
            'Seguridad': 'seguridad OR delincuencia OR crimen OR policía OR robo',
            'Infraestructura': 'infraestructura OR vías OR carreteras OR transporte OR obras',
            'Gobernanza y Transparencia': 'transparencia OR corrupción OR gobernanza OR gobierno',
            'Educación': 'educación OR colegios OR universidad OR estudiantes OR maestros',
            'Salud': 'salud OR hospitales OR médicos OR EPS OR medicamentos',
            'Igualdad y Equidad': 'igualdad OR equidad OR género OR mujeres OR inclusión',
            'Paz y Reinserción': 'paz OR reinserción OR conflicto OR víctimas',
            'Economía y Empleo': 'economía OR empleo OR trabajo OR desempleo OR empresas',
            'Medio Ambiente y Cambio Climático': 'medio ambiente OR cambio climático OR contaminación OR reciclaje',
            'Alimentación': 'alimentación OR comida OR hambre OR seguridad alimentaria OR agricultura'
        }
        
        return topic_keywords.get(topic, topic)
    
    def get_tweet_metrics(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific tweet."""
        try:
            def _make_api_call():
                return self.client.get_tweet(
                    tweet_id,
                    tweet_fields=['public_metrics']
                )
            
            tweet = self._call_twitter_api(_make_api_call)
            return tweet.data.public_metrics if tweet.data else None
        except Exception as e:
            logger.error(f"Error getting tweet metrics: {e}")
            return None
