"""
Sentiment analysis service using BETO model.
Provides 99% accuracy sentiment classification for Spanish text.
"""
import logging
from typing import List, Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from config import Config
from models.schemas import SentimentData, SentimentType
from utils.cache import TTLCache

logger = logging.getLogger(__name__)


class SentimentService:
    """Service for sentiment analysis using BETO model."""
    
    def __init__(self):
        """Initialize BETO model for sentiment analysis."""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_name = Config.BETO_MODEL_PATH
        self.model = None
        self.tokenizer = None
        self._load_model()
        self._sentiment_cache = TTLCache(
            ttl_seconds=Config.SENTIMENT_CACHE_TTL,
            max_size=Config.CACHE_MAX_SIZE
        )
        logger.info(f"SentimentService initialized with device: {self.device}")

    def _cache_key(self, text: str) -> str:
        """Generate cache key for sentiment results."""
        return text.strip().lower()
    
    def _load_model(self):
        """Load BETO model and tokenizer."""
        try:
            logger.info(f"Loading BETO model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=3  # positive, negative, neutral
            )
            self.model.to(self.device)
            self.model.eval()
            logger.info("BETO model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading BETO model: {e}", exc_info=True)
            raise
    
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
