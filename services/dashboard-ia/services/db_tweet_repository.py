"""
Tweet repository for database operations.
Handles tweet storage and retrieval.
"""
import logging
from typing import Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError

from models.database import Tweet

logger = logging.getLogger(__name__)


class TweetRepository:
    """Repository for tweet database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

    def save_tweets(self, api_call_id: str, tweets_data: List[Dict[str, Any]]) -> int:
        """Save multiple tweets to database. Returns count of tweets saved."""
        session = self._db.get_session()
        saved_count = 0
        try:
            for tweet_data in tweets_data:
                tweet = self._create_tweet_from_data(api_call_id, tweet_data)
                session.add(tweet)
                saved_count += 1

            session.commit()
            logger.info(f"Saved {saved_count} tweets for API call {api_call_id}")
            return saved_count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving tweets: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    def _create_tweet_from_data(self, api_call_id: str, data: Dict[str, Any]) -> Tweet:
        """Create Tweet object from dictionary data."""
        return Tweet(
            api_call_id=api_call_id,
            tweet_id=data.get('tweet_id', ''),
            author_id=data.get('author_id'),
            author_username=data.get('author_username'),
            author_name=data.get('author_name'),
            author_verified=data.get('author_verified', False),
            author_followers_count=data.get('author_followers_count', 0),
            content=data.get('content', ''),
            content_cleaned=data.get('content_cleaned'),
            tweet_created_at=data.get('tweet_created_at'),
            language=data.get('language'),
            source=data.get('source'),
            retweet_count=data.get('retweet_count', 0),
            like_count=data.get('like_count', 0),
            reply_count=data.get('reply_count', 0),
            quote_count=data.get('quote_count', 0),
            impression_count=data.get('impression_count', 0),
            is_retweet=data.get('is_retweet', False),
            is_reply=data.get('is_reply', False),
            is_quote=data.get('is_quote', False),
            replied_to_tweet_id=data.get('replied_to_tweet_id'),
            quoted_tweet_id=data.get('quoted_tweet_id'),
            hashtags=data.get('hashtags', []),
            mentions=data.get('mentions', []),
            urls=data.get('urls', []),
            geo_country=data.get('geo_country'),
            geo_city=data.get('geo_city'),
            geo_coordinates=data.get('geo_coordinates'),
            sentiment_positive=data.get('sentiment_positive', 0.0),
            sentiment_negative=data.get('sentiment_negative', 0.0),
            sentiment_neutral=data.get('sentiment_neutral', 0.0),
            sentiment_label=data.get('sentiment_label'),
            sentiment_confidence=data.get('sentiment_confidence', 0.0),
            pnd_topic=data.get('pnd_topic'),
            pnd_confidence=data.get('pnd_confidence', 0.0),
            pnd_secondary_topic=data.get('pnd_secondary_topic'),
            is_potential_bot=data.get('is_potential_bot', False),
            bot_score=data.get('bot_score', 0.0)
        )

    def get_tweets_by_api_call(
        self,
        api_call_id: str,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get tweets for a specific API call."""
        session = self._db.get_session()
        try:
            tweets = (
                session.query(Tweet)
                .filter(Tweet.api_call_id == api_call_id)
                .order_by(Tweet.tweet_created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [self._tweet_to_dict(t) for t in tweets]
        except Exception as e:
            logger.error(f"Error getting tweets: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def _tweet_to_dict(self, tweet: Tweet) -> Dict[str, Any]:
        """Convert Tweet object to dictionary."""
        return {
            'tweet_id': tweet.tweet_id,
            'author_username': tweet.author_username,
            'author_name': tweet.author_name,
            'content': tweet.content,
            'tweet_created_at': tweet.tweet_created_at.isoformat() if tweet.tweet_created_at else None,
            'retweet_count': tweet.retweet_count,
            'like_count': tweet.like_count,
            'reply_count': tweet.reply_count,
            'sentiment_label': tweet.sentiment_label,
            'pnd_topic': tweet.pnd_topic
        }
