"""
Tests for service classes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.twitter_service import TwitterService
from services.sentiment_service import SentimentService
from services.openai_service import OpenAIService
from services.database_service import DatabaseService
from models.schemas import SentimentData, PNDTopicAnalysis


class TestTwitterService:
    """Tests for TwitterService."""
    
    @patch('services.twitter_service.tweepy.Client')
    def test_init(self, mock_client):
        """Test TwitterService initialization."""
        with patch('services.twitter_service.Config') as mock_config:
            mock_config.TWITTER_BEARER_TOKEN = 'test_token'
            mock_config.TWITTER_API_KEY = None
            mock_config.TWITTER_API_SECRET = None
            mock_config.TWITTER_ACCESS_TOKEN = None
            mock_config.TWITTER_ACCESS_TOKEN_SECRET = None
            
            service = TwitterService()
            assert service.client is not None
    
    @patch('services.twitter_service.tweepy.Client')
    def test_search_tweets_cached(self, mock_client):
        """Test that search_tweets uses cache."""
        with patch('services.twitter_service.Config') as mock_config, \
             patch('services.twitter_service.get') as mock_get, \
             patch('services.twitter_service.set') as mock_set:
            
            mock_config.TWITTER_BEARER_TOKEN = 'test_token'
            mock_config.CACHE_TTL_TWITTER = 1800
            
            # Mock cache hit
            mock_get.return_value = [{'id': '1', 'text': 'cached tweet'}]
            
            service = TwitterService()
            result = service.search_tweets('test query')
            
            assert result == [{'id': '1', 'text': 'cached tweet'}]
            mock_get.assert_called_once()


class TestSentimentService:
    """Tests for SentimentService."""
    
    @patch('services.sentiment_service.AutoTokenizer')
    @patch('services.sentiment_service.AutoModelForSequenceClassification')
    def test_analyze_sentiment(self, mock_model_class, mock_tokenizer_class):
        """Test sentiment analysis."""
        # Mock model and tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer
        mock_tokenizer_class.from_pretrained = Mock(return_value=mock_tokenizer)
        
        mock_model = Mock()
        mock_output = Mock()
        mock_output.logits = Mock()
        mock_output.logits.cpu.return_value.numpy.return_value = [[0.2, 0.3, 0.5]]  # [negative, neutral, positive]
        mock_model.return_value = mock_output
        mock_model.eval = Mock()
        mock_model_class.from_pretrained = Mock(return_value=mock_model)
        
        with patch('services.sentiment_service.Config') as mock_config:
            mock_config.BETO_MODEL_PATH = 'test/model'
            
            service = SentimentService()
            result = service.analyze_sentiment("Test text")
            
            assert isinstance(result, SentimentData)
            assert result.positive > 0
            assert result.negative > 0
            assert result.neutral > 0
    
    def test_aggregate_sentiment(self):
        """Test sentiment aggregation."""
        service = SentimentService()
        
        sentiments = [
            SentimentData(positive=0.6, negative=0.2, neutral=0.2),
            SentimentData(positive=0.4, negative=0.3, neutral=0.3),
        ]
        
        result = service.aggregate_sentiment(sentiments)
        
        assert isinstance(result, SentimentData)
        assert 0.4 < result.positive < 0.6
        assert result.positive + result.negative + result.neutral > 0.9  # Should be normalized


class TestOpenAIService:
    """Tests for OpenAIService."""
    
    @patch('services.openai_service.openai.OpenAI')
    def test_init(self, mock_openai):
        """Test OpenAIService initialization."""
        with patch('services.openai_service.Config') as mock_config:
            mock_config.OPENAI_API_KEY = 'test_key'
            mock_config.OPENAI_MODEL = 'gpt-4o'
            
            service = OpenAIService()
            assert service.client is not None
            assert service.model == 'gpt-4o'
    
    @patch('services.openai_service.openai.OpenAI')
    def test_generate_executive_summary(self, mock_openai):
        """Test executive summary generation."""
        # Mock OpenAI client
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"overview": "Test", "key_findings": [], "recommendations": []}'
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client_instance
        
        with patch('services.openai_service.Config') as mock_config:
            mock_config.OPENAI_API_KEY = 'test_key'
            mock_config.OPENAI_MODEL = 'gpt-4o'
            
            service = OpenAIService()
            topic_analyses = [
                PNDTopicAnalysis(
                    topic="Seguridad",
                    sentiment=SentimentData(positive=0.5, negative=0.3, neutral=0.2),
                    tweet_count=100,
                    key_insights=[],
                    sample_tweets=[]
                )
            ]
            
            result = service.generate_executive_summary(
                location="Bogotá",
                topic_analyses=topic_analyses
            )
            
            assert result.overview == "Test"
            assert isinstance(result.key_findings, list)


class TestDatabaseService:
    """Tests for DatabaseService."""
    
    @patch('services.database_service.create_engine')
    @patch('services.database_service.sessionmaker')
    def test_init(self, mock_sessionmaker, mock_engine):
        """Test DatabaseService initialization."""
        with patch('services.database_service.Config') as mock_config:
            mock_config.DATABASE_URL = 'postgresql://test'
            
            service = DatabaseService()
            assert service.engine is not None
            assert service.SessionLocal is not None
    
    @patch('services.database_service.create_engine')
    @patch('services.database_service.sessionmaker')
    def test_create_user(self, mock_sessionmaker, mock_engine):
        """Test user creation."""
        # Mock session
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing user
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        mock_session.close = Mock()
        
        mock_sessionmaker.return_value = mock_session
        
        with patch('services.database_service.Config') as mock_config:
            mock_config.DATABASE_URL = 'postgresql://test'
            
            service = DatabaseService()
            service.SessionLocal = Mock(return_value=mock_session)
            
            user = service.create_user(
                email='test@example.com',
                password='password123'
            )
            
            assert user is not None
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

