"""
Service interfaces for CASTOR.
Following SOLID principles - Dependency Inversion (DIP) and Interface Segregation (ISP).
"""
from .llm_provider import ILLMProvider, LLMResponse
from .sentiment_analyzer import ISentimentAnalyzer
from .data_repository import IDataRepository, IAnalysisRepository, IUserRepository
from .topic_strategy import ITopicStrategy, TopicStrategyFactory

__all__ = [
    'ILLMProvider',
    'LLMResponse',
    'ISentimentAnalyzer',
    'IDataRepository',
    'IAnalysisRepository',
    'IUserRepository',
    'ITopicStrategy',
    'TopicStrategyFactory',
]
