"""
Trending topics detection service.
Detects what's trending in real-time to inform campaign speeches.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import re
from services.twitter_service import TwitterService
from services.sentiment_service import SentimentService
from services.database_service import DatabaseService
from models.database import TrendingTopic

logger = logging.getLogger(__name__)


class TrendingService:
    """Service for detecting and analyzing trending topics."""
    
    def __init__(self):
        """Initialize trending service."""
        self.twitter_service = TwitterService()
        self.sentiment_service = SentimentService()
        self.db_service = DatabaseService()
        logger.info("TrendingService initialized")
    
    def detect_trending_topics(
        self,
        location: str,
        hours_back: int = 24,
        min_tweets: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Detect trending topics in a location.
        
        Args:
            location: Location to analyze
            hours_back: Hours to look back
            min_tweets: Minimum tweets to consider trending
            
        Returns:
            List of trending topics with metadata
        """
        try:
            logger.info(f"Detecting trending topics for {location}")
            
            # Search for recent tweets in location
            # Use broad queries to capture trending topics
            queries = [
                f"{location}",
                f"{location} OR {location.lower()}",
                f"#{location.replace(' ', '')}"
            ]
            
            all_tweets = []
            for query in queries:
                tweets = self.twitter_service.search_tweets(
                    query=query,
                    location=location,
                    max_results=200,
                    days_back=1
                )
                all_tweets.extend(tweets)
            
            # Remove duplicates
            seen_ids = set()
            unique_tweets = []
            for tweet in all_tweets:
                if tweet['id'] not in seen_ids:
                    seen_ids.add(tweet['id'])
                    unique_tweets.append(tweet)
            
            logger.info(f"Found {len(unique_tweets)} unique tweets")
            
            # Extract keywords and hashtags
            keywords = self._extract_keywords(unique_tweets)
            hashtags = self._extract_hashtags(unique_tweets)
            
            # Group tweets by topic
            topics = self._group_tweets_by_topic(unique_tweets, keywords, hashtags)
            
            # Analyze sentiment for each topic
            trending_topics = []
            for topic_name, topic_tweets in topics.items():
                if len(topic_tweets) < min_tweets:
                    continue
                
                # Calculate engagement score
                engagement = sum(
                    t.get('public_metrics', {}).get('like_count', 0) +
                    t.get('public_metrics', {}).get('retweet_count', 0) * 2 +
                    t.get('public_metrics', {}).get('reply_count', 0)
                    for t in topic_tweets
                )
                
                # Analyze sentiment
                texts = [t['text'] for t in topic_tweets]
                sentiments = self.sentiment_service.analyze_batch(texts)
                aggregated = self.sentiment_service.aggregate_sentiment(sentiments)
                
                # Get sample tweets
                sorted_tweets = sorted(
                    topic_tweets,
                    key=lambda x: (
                        x.get('public_metrics', {}).get('retweet_count', 0) +
                        x.get('public_metrics', {}).get('like_count', 0)
                    ),
                    reverse=True
                )
                sample_tweets = [t['text'][:200] for t in sorted_tweets[:5]]
                
                trending_topic = {
                    'topic': topic_name,
                    'location': location,
                    'tweet_count': len(topic_tweets),
                    'engagement_score': engagement,
                    'sentiment_positive': aggregated.positive,
                    'sentiment_negative': aggregated.negative,
                    'sentiment_neutral': aggregated.neutral,
                    'keywords': list(keywords.get(topic_name, [])),
                    'sample_tweets': sample_tweets,
                    'detected_at': datetime.utcnow(),
                    'is_active': True
                }
                
                # Save to database
                topic_id = self.db_service.save_trending_topic(trending_topic)
                if topic_id:
                    trending_topic['id'] = topic_id
                
                trending_topics.append(trending_topic)
            
            # Sort by engagement score
            trending_topics.sort(key=lambda x: x['engagement_score'], reverse=True)
            
            logger.info(f"Detected {len(trending_topics)} trending topics")
            return trending_topics[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Error detecting trending topics: {e}", exc_info=True)
            return []
    
    def _extract_keywords(self, tweets: List[Dict[str, Any]]) -> Counter:
        """Extract keywords from tweets."""
        # Common stopwords in Spanish
        stopwords = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se',
            'no', 'haber', 'por', 'con', 'su', 'para', 'como', 'estar',
            'tener', 'le', 'lo', 'todo', 'pero', 'más', 'hacer', 'o',
            'poder', 'decir', 'este', 'ir', 'otro', 'ese', 'la', 'si',
            'me', 'ya', 'ver', 'porque', 'dar', 'cuando', 'él', 'muy',
            'sin', 'vez', 'mucho', 'saber', 'qué', 'sobre', 'mi', 'alguno'
        }
        
        all_words = []
        for tweet in tweets:
            text = tweet.get('text', '').lower()
            # Remove URLs, mentions, hashtags
            text = re.sub(r'http\S+|@\w+|#\w+', '', text)
            # Extract words
            words = re.findall(r'\b[a-záéíóúñ]+\b', text)
            # Filter stopwords and short words
            words = [w for w in words if len(w) > 3 and w not in stopwords]
            all_words.extend(words)
        
        return Counter(all_words)
    
    def _extract_hashtags(self, tweets: List[Dict[str, Any]]) -> Counter:
        """Extract hashtags from tweets."""
        all_hashtags = []
        for tweet in tweets:
            text = tweet.get('text', '')
            hashtags = re.findall(r'#(\w+)', text)
            all_hashtags.extend([h.lower() for h in hashtags])
        
        return Counter(all_hashtags)
    
    def _group_tweets_by_topic(
        self,
        tweets: List[Dict[str, Any]],
        keywords: Counter,
        hashtags: Counter
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group tweets by topic."""
        # Get top keywords and hashtags
        top_keywords = [word for word, count in keywords.most_common(20)]
        top_hashtags = [tag for tag, count in hashtags.most_common(10)]
        
        topics = {}
        
        for tweet in tweets:
            text = tweet.get('text', '').lower()
            
            # Check hashtags first (more reliable)
            tweet_hashtags = [h.lower() for h in re.findall(r'#(\w+)', tweet.get('text', ''))]
            matching_hashtag = None
            for hashtag in top_hashtags:
                if hashtag in tweet_hashtags:
                    matching_hashtag = hashtag
                    break
            
            if matching_hashtag:
                topic_name = f"#{matching_hashtag}"
                if topic_name not in topics:
                    topics[topic_name] = []
                topics[topic_name].append(tweet)
                continue
            
            # Check keywords
            matching_keywords = [kw for kw in top_keywords if kw in text]
            if matching_keywords:
                # Use the most specific keyword
                topic_name = matching_keywords[0]
                if topic_name not in topics:
                    topics[topic_name] = []
                topics[topic_name].append(tweet)
            else:
                # Default topic
                if 'general' not in topics:
                    topics['general'] = []
                topics['general'].append(tweet)
        
        return topics
    
    def get_trending_for_speech(
        self,
        location: str,
        candidate_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most relevant trending topic for creating a speech.
        
        Args:
            location: Location
            candidate_name: Candidate name
            
        Returns:
            Trending topic data optimized for speech creation
        """
        trending_topics = self.detect_trending_topics(location, hours_back=12)
        
        if not trending_topics:
            return None
        
        # Select topic with highest engagement and positive sentiment
        best_topic = max(
            trending_topics,
            key=lambda x: x['engagement_score'] * (x['sentiment_positive'] + 0.5 * x['sentiment_neutral'])
        )
        
        return best_topic

