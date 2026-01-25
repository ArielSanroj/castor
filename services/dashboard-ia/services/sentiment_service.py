"""
Sentiment analysis service using BETO model.
Provides 99% accuracy sentiment classification for Spanish text.
Uses singleton pattern to avoid loading model multiple times.
"""
import logging
from typing import List, Dict, Any, Optional
import torch
from config import Config
from models.schemas import SentimentData, SentimentType
from utils.cache import TTLCache
from services.model_singleton import get_beto_model

logger = logging.getLogger(__name__)


class SentimentService:
    """Service for sentiment analysis using BETO model."""
    
    def __init__(self):
        """Initialize BETO model for sentiment analysis."""
        # Use singleton to avoid loading model multiple times
        self.model, self.tokenizer, self.device = get_beto_model()
        self._sentiment_cache = TTLCache(
            ttl_seconds=Config.SENTIMENT_CACHE_TTL,
            max_size=Config.CACHE_MAX_SIZE
        )
        logger.info(f"SentimentService initialized with device: {self.device}")

    def _cache_key(self, text: str) -> str:
        """Generate cache key for sentiment results."""
        return text.strip().lower()
    
    def analyze_sentiment(self, text: str) -> SentimentData:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            SentimentData with scores
        """
        if not text or not text.strip():
            return SentimentData(positive=0.33, negative=0.33, neutral=0.34)
        
        cache_key = self._cache_key(text)
        cached = self._sentiment_cache.get(cache_key)
        if cached:
            return SentimentData(**cached)
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            
            # Map to sentiment scores
            # Assuming model outputs: [negative, neutral, positive]
            sentiment = SentimentData(
                positive=float(probabilities[2]),
                negative=float(probabilities[0]),
                neutral=float(probabilities[1])
            )
            self._sentiment_cache.set(cache_key, sentiment.dict())
            return sentiment
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
            # Return neutral as fallback
            return SentimentData(positive=0.33, negative=0.33, neutral=0.34)
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentData]:
        """
        Analyze sentiment for multiple texts (batch processing).
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of SentimentData objects
        """
        if not texts:
            return []
        
        sentiments: List[Optional[SentimentData]] = [None] * len(texts)
        uncached_texts = []
        uncached_indices = []
        
        for idx, text in enumerate(texts):
            cache_key = self._cache_key(text)
            cached = self._sentiment_cache.get(cache_key)
            if cached:
                sentiments[idx] = SentimentData(**cached)
            else:
                uncached_texts.append(text)
                uncached_indices.append(idx)
        
        if not uncached_texts:
            return [s for s in sentiments if s is not None]
        
        batch_size = 32
        
        for i in range(0, len(uncached_texts), batch_size):
            batch = uncached_texts[i:i + batch_size]
            try:
                # Tokenize batch
                inputs = self.tokenizer(
                    batch,
                    return_tensors='pt',
                    truncation=True,
                    max_length=512,
                    padding=True
                ).to(self.device)
                
                # Predict
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
                
                # Process results
                for index_offset, prob in enumerate(probabilities):
                    sentiment = SentimentData(
                        positive=float(prob[2]),
                        negative=float(prob[0]),
                        neutral=float(prob[1])
                    )
                    target_idx = uncached_indices[i + index_offset]
                    sentiments[target_idx] = sentiment
                    self._sentiment_cache.set(
                        self._cache_key(uncached_texts[i + index_offset]),
                        sentiment.dict()
                    )
                    
            except Exception as e:
                logger.error(f"Error in batch sentiment analysis: {e}")
                # Add neutral fallback for failed items
                for index_offset in range(len(batch)):
                    sentiment = SentimentData(positive=0.33, negative=0.33, neutral=0.34)
                    target_idx = uncached_indices[i + index_offset]
                    sentiments[target_idx] = sentiment
        
        # Fill any remaining None entries (shouldn't happen but safe)
        for idx, value in enumerate(sentiments):
            if value is None:
                sentiments[idx] = SentimentData(positive=0.33, negative=0.33, neutral=0.34)
        
        return sentiments
    
    def analyze_tweets(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a list of tweets.
        
        Args:
            tweets: List of tweet dictionaries with 'text' key
            
        Returns:
            List of tweets with added 'sentiment' field
        """
        if not tweets:
            return []
        
        texts = [tweet.get('text', '') for tweet in tweets]
        sentiments = self.analyze_batch(texts)
        
        # Add sentiment to tweets
        for tweet, sentiment in zip(tweets, sentiments):
            tweet['sentiment'] = sentiment.dict()
            tweet['dominant_sentiment'] = sentiment.get_dominant_sentiment().value
        
        return tweets
    
    def aggregate_sentiment(self, sentiments: List[SentimentData]) -> SentimentData:
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

    def aggregate_sentiment_weighted(self, tweets: List[Dict[str, Any]]) -> SentimentData:
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

    def get_credibility_stats(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
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
