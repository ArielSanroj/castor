"""
Twitter API service using Tweepy.
Handles tweet search and data extraction.
"""
import logging
import tweepy
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from config import Config

logger = logging.getLogger(__name__)


class TwitterService:
    """Service for interacting with Twitter API."""
    
    def __init__(self):
        """Initialize Twitter API client."""
        if not Config.TWITTER_BEARER_TOKEN:
            raise ValueError("TWITTER_BEARER_TOKEN not configured")
        
        self.client = tweepy.Client(
            bearer_token=Config.TWITTER_BEARER_TOKEN,
            consumer_key=Config.TWITTER_API_KEY,
            consumer_secret=Config.TWITTER_API_SECRET,
            access_token=Config.TWITTER_ACCESS_TOKEN,
            access_token_secret=Config.TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        logger.info("TwitterService initialized")
    
    def search_tweets(
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
        try:
            # Build query string
            search_query = f"{query} lang:{lang}"
            if location:
                search_query += f" -is:retweet place:{location}"
            
            # Calculate date range
            start_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            
            # Search tweets
            tweets = []
            pagination_token = None
            
            while len(tweets) < max_results:
                remaining = max_results - len(tweets)
                current_max = min(remaining, 100)  # API limit per request
                
                try:
                    response = self.client.search_recent_tweets(
                        query=search_query,
                        max_results=current_max,
                        start_time=start_time,
                        tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'geo'],
                        next_token=pagination_token
                    )
                    
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
            
            logger.info(f"Retrieved {len(tweets)} tweets for query: {query}")
            return tweets[:max_results]
            
        except Exception as e:
            logger.error(f"Error in search_tweets: {e}", exc_info=True)
            return []
    
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
            tweet = self.client.get_tweet(
                tweet_id,
                tweet_fields=['public_metrics']
            )
            return tweet.data.public_metrics if tweet.data else None
        except Exception as e:
            logger.error(f"Error getting tweet metrics: {e}")
            return None

