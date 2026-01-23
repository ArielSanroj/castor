"""
Sentiment Analyzer Interface.
Abstracts sentiment analysis implementations.

SOLID Principles:
- SRP: Only handles sentiment analysis
- ISP: Minimal interface for sentiment operations
- DIP: Services depend on this abstraction
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class SentimentType(Enum):
    """Sentiment classification types."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Standardized sentiment analysis result."""
    positive: float
    negative: float
    neutral: float
    confidence: float = 1.0
    dominant: SentimentType = SentimentType.NEUTRAL

    def __post_init__(self):
        """Calculate dominant sentiment after initialization."""
        scores = {
            SentimentType.POSITIVE: self.positive,
            SentimentType.NEGATIVE: self.negative,
            SentimentType.NEUTRAL: self.neutral
        }
        self.dominant = max(scores, key=scores.get)
        self.confidence = max(self.positive, self.negative, self.neutral)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "confidence": self.confidence,
            "dominant": self.dominant.value
        }

    @classmethod
    def neutral_default(cls) -> "SentimentResult":
        """Return a neutral default result."""
        return cls(positive=0.33, negative=0.33, neutral=0.34)


class ISentimentAnalyzer(ABC):
    """
    Interface for sentiment analysis.

    Implementations:
    - BETOSentimentAnalyzer (Spanish BERT model)
    - OpenAISentimentAnalyzer (GPT-based)
    - HuggingFaceSentimentAnalyzer (Various models)

    Usage:
        analyzer: ISentimentAnalyzer = BETOSentimentAnalyzer()
        result = analyzer.analyze("Este producto es excelente")
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used."""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        pass

    @abstractmethod
    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text.

        Args:
            text: Text to analyze

        Returns:
            SentimentResult with scores
        """
        pass

    @abstractmethod
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts (batch processing).

        Args:
            texts: List of texts to analyze

        Returns:
            List of SentimentResult objects
        """
        pass

    def analyze_with_context(
        self,
        text: str,
        context: Optional[str] = None
    ) -> SentimentResult:
        """
        Analyze sentiment with additional context.
        Default implementation ignores context.

        Args:
            text: Text to analyze
            context: Optional context for better analysis

        Returns:
            SentimentResult with scores
        """
        return self.analyze(text)

    @abstractmethod
    def aggregate(self, results: List[SentimentResult]) -> SentimentResult:
        """
        Aggregate multiple sentiment results into one.

        Args:
            results: List of SentimentResult objects

        Returns:
            Aggregated SentimentResult
        """
        pass

    def is_available(self) -> bool:
        """Check if analyzer is available and model is loaded."""
        return True
