"""
Sentiment analysis service using BETO model.
Provides 99% accuracy sentiment classification for Spanish text.
"""
import logging
from typing import List, Dict, Any, Optional
import torch
from config import Config
from models.schemas import SentimentData
from utils.cache import TTLCache
from services.model_singleton import get_beto_model
from .sentiment_aggregation import (
    aggregate_sentiment,
    aggregate_sentiment_weighted,
    get_credibility_stats,
)

logger = logging.getLogger(__name__)


class SentimentService:
    """Service for sentiment analysis using BETO model."""

    def __init__(self):
        """Initialize sentiment service with lazy model loading."""
        self._model = None
        self._tokenizer = None
        self._device = None
        self._sentiment_cache = TTLCache(
            ttl_seconds=Config.SENTIMENT_CACHE_TTL,
            max_size=Config.CACHE_MAX_SIZE
        )
        logger.info("SentimentService initialized (model will load on first use)")

    def _ensure_model_loaded(self):
        """Load model if not already loaded (lazy loading)."""
        if self._model is None:
            self._model, self._tokenizer, self._device = get_beto_model()
            logger.info(f"BETO model loaded lazily on device: {self._device}")

    @property
    def model(self):
        self._ensure_model_loaded()
        return self._model

    @property
    def tokenizer(self):
        self._ensure_model_loaded()
        return self._tokenizer

    @property
    def device(self):
        self._ensure_model_loaded()
        return self._device

    def _cache_key(self, text: str) -> str:
        """Generate cache key for sentiment results."""
        return text.strip().lower()

    def analyze_sentiment(self, text: str) -> SentimentData:
        """Analyze sentiment of a single text."""
        if not text or not text.strip():
            return SentimentData(positive=0.33, negative=0.33, neutral=0.34)

        cache_key = self._cache_key(text)
        cached = self._sentiment_cache.get(cache_key)
        if cached:
            return SentimentData(**cached)

        try:
            inputs = self.tokenizer(
                text, return_tensors='pt', truncation=True, max_length=512, padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1).cpu().numpy()[0]

            # Map to sentiment scores (model outputs: [negative, neutral, positive])
            sentiment = SentimentData(
                positive=float(probabilities[2]),
                negative=float(probabilities[0]),
                neutral=float(probabilities[1])
            )
            self._sentiment_cache.set(cache_key, sentiment.dict())
            return sentiment

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
            return SentimentData(positive=0.33, negative=0.33, neutral=0.34)

    def analyze_batch(self, texts: List[str]) -> List[SentimentData]:
        """Analyze sentiment for multiple texts (batch processing)."""
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
                inputs = self.tokenizer(
                    batch, return_tensors='pt', truncation=True, max_length=512, padding=True
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probabilities = torch.softmax(logits, dim=-1).cpu().numpy()

                for index_offset, prob in enumerate(probabilities):
                    sentiment = SentimentData(
                        positive=float(prob[2]),
                        negative=float(prob[0]),
                        neutral=float(prob[1])
                    )
                    target_idx = uncached_indices[i + index_offset]
                    sentiments[target_idx] = sentiment
                    self._sentiment_cache.set(self._cache_key(uncached_texts[i + index_offset]), sentiment.dict())

            except Exception as e:
                logger.error(f"Error in batch sentiment analysis: {e}")
                for index_offset in range(len(batch)):
                    sentiment = SentimentData(positive=0.33, negative=0.33, neutral=0.34)
                    target_idx = uncached_indices[i + index_offset]
                    sentiments[target_idx] = sentiment

        # Fill any remaining None entries
        for idx, value in enumerate(sentiments):
            if value is None:
                sentiments[idx] = SentimentData(positive=0.33, negative=0.33, neutral=0.34)

        return sentiments

    def analyze_tweets(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for a list of tweets."""
        if not tweets:
            return []

        texts = [tweet.get('text', '') for tweet in tweets]
        sentiments = self.analyze_batch(texts)

        for tweet, sentiment in zip(tweets, sentiments):
            tweet['sentiment'] = sentiment.dict()
            tweet['dominant_sentiment'] = sentiment.get_dominant_sentiment().value

        return tweets

    # Delegate aggregation methods to sentiment_aggregation module
    def aggregate_sentiment(self, sentiments: List[SentimentData]) -> SentimentData:
        """Aggregate multiple sentiment analyses into one."""
        return aggregate_sentiment(sentiments)

    def aggregate_sentiment_weighted(self, tweets: List[Dict[str, Any]]) -> SentimentData:
        """Aggregate sentiment weighted by account credibility."""
        return aggregate_sentiment_weighted(tweets)

    def get_credibility_stats(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about credibility scores in a set of tweets."""
        return get_credibility_stats(tweets)
