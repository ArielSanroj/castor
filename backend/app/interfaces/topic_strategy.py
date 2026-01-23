"""
Topic Strategy Interface.
Implements Strategy Pattern for PND topic handling.

SOLID Principles:
- OCP: New topics can be added without modifying existing code
- SRP: Each strategy handles one topic's logic
- LSP: All strategies are interchangeable

Strategy Pattern Benefits:
- Eliminates if/else chains for topic handling
- Easy to add new topics
- Each topic's logic is encapsulated
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type
from enum import Enum


class PNDTopic(Enum):
    """Plan Nacional de Desarrollo topics."""
    SEGURIDAD = "Seguridad"
    EDUCACION = "Educación"
    SALUD = "Salud"
    ECONOMIA = "Economía y Empleo"
    INFRAESTRUCTURA = "Infraestructura"
    GOBERNANZA = "Gobernanza y Transparencia"
    IGUALDAD = "Igualdad y Equidad"
    PAZ = "Paz y Reinserción"
    AMBIENTE = "Medio Ambiente y Cambio Climático"
    ALIMENTACION = "Alimentación"
    TODOS = "Todos"


@dataclass
class TopicConfig:
    """Configuration for a PND topic strategy."""
    name: str
    display_name: str
    keywords: List[str]
    hashtags: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    sentiment_weight: float = 1.0  # Weight for sentiment aggregation
    priority: int = 5  # 1-10, higher = more important


class ITopicStrategy(ABC):
    """
    Interface for topic-specific analysis strategies.

    Each topic has its own:
    - Keywords for search
    - Analysis focus areas
    - Sentiment interpretation
    - Recommendation generation

    Usage:
        strategy = TopicStrategyFactory.get_strategy(PNDTopic.SEGURIDAD)
        keywords = strategy.get_search_keywords()
        analysis = strategy.analyze_tweets(tweets)
    """

    @property
    @abstractmethod
    def topic(self) -> PNDTopic:
        """Get the topic this strategy handles."""
        pass

    @property
    @abstractmethod
    def config(self) -> TopicConfig:
        """Get topic configuration."""
        pass

    @abstractmethod
    def get_search_keywords(self, location: Optional[str] = None) -> str:
        """
        Get search keywords for this topic.

        Args:
            location: Optional location to customize keywords

        Returns:
            Search query string with keywords
        """
        pass

    @abstractmethod
    def get_hashtags(self) -> List[str]:
        """Get relevant hashtags for this topic."""
        pass

    @abstractmethod
    def classify_tweet(self, tweet_text: str) -> float:
        """
        Classify how relevant a tweet is to this topic.

        Args:
            tweet_text: Tweet text to classify

        Returns:
            Relevance score 0.0-1.0
        """
        pass

    @abstractmethod
    def interpret_sentiment(
        self,
        sentiment_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Interpret sentiment scores in topic-specific context.

        Args:
            sentiment_scores: Raw sentiment scores
            context: Optional context (location, candidate, etc.)

        Returns:
            Interpreted sentiment with topic-specific insights
        """
        pass

    @abstractmethod
    def generate_insights(
        self,
        tweets: List[Dict[str, Any]],
        aggregated_sentiment: Dict[str, float]
    ) -> List[str]:
        """
        Generate topic-specific insights from analyzed tweets.

        Args:
            tweets: Analyzed tweets with sentiment
            aggregated_sentiment: Overall sentiment scores

        Returns:
            List of insight strings
        """
        pass

    @abstractmethod
    def get_recommendations(
        self,
        sentiment: Dict[str, float],
        location: str,
        candidate_name: Optional[str] = None
    ) -> List[str]:
        """
        Generate topic-specific recommendations.

        Args:
            sentiment: Sentiment analysis results
            location: Analysis location
            candidate_name: Optional candidate name

        Returns:
            List of recommendation strings
        """
        pass


class TopicStrategyFactory:
    """
    Factory for creating topic strategies.
    Implements Factory Pattern for strategy instantiation.
    """

    _strategies: Dict[PNDTopic, Type[ITopicStrategy]] = {}

    @classmethod
    def register(cls, topic: PNDTopic):
        """
        Decorator to register a strategy for a topic.

        Usage:
            @TopicStrategyFactory.register(PNDTopic.SEGURIDAD)
            class SeguridadStrategy(ITopicStrategy):
                ...
        """
        def decorator(strategy_class: Type[ITopicStrategy]):
            cls._strategies[topic] = strategy_class
            return strategy_class
        return decorator

    @classmethod
    def get_strategy(cls, topic: PNDTopic) -> ITopicStrategy:
        """
        Get strategy instance for a topic.

        Args:
            topic: PND topic

        Returns:
            Strategy instance

        Raises:
            ValueError: If no strategy registered for topic
        """
        if topic not in cls._strategies:
            raise ValueError(f"No strategy registered for topic: {topic.value}")
        return cls._strategies[topic]()

    @classmethod
    def get_all_strategies(cls) -> List[ITopicStrategy]:
        """Get instances of all registered strategies."""
        return [strategy() for strategy in cls._strategies.values()]

    @classmethod
    def get_registered_topics(cls) -> List[PNDTopic]:
        """Get list of topics with registered strategies."""
        return list(cls._strategies.keys())

    @classmethod
    def has_strategy(cls, topic: PNDTopic) -> bool:
        """Check if a strategy is registered for a topic."""
        return topic in cls._strategies
