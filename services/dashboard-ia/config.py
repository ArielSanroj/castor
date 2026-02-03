"""
Configuration module for Dashboard IA Service.
Handles electoral strategy, Twitter analysis, sentiment, RAG, and forecasting.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration class for Dashboard IA Service."""

    # Service identification
    SERVICE_NAME: str = "dashboard-ia"
    SERVICE_PORT: int = int(os.getenv('DASHBOARD_SERVICE_PORT', '5003'))

    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING: bool = False

    # Server
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = SERVICE_PORT

    # CORS
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5001').split(',')

    # Core Service (for auth validation)
    CORE_SERVICE_URL: str = os.getenv('CORE_SERVICE_URL', 'http://localhost:5001')

    # JWT (for token validation - keys must match Core Service)
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', SECRET_KEY)

    # Database (PostgreSQL)
    DATABASE_URL: Optional[str] = os.getenv('DASHBOARD_DATABASE_URL', 'postgresql://castor:castor_dev@localhost:5432/dashboard_db')
    SQLALCHEMY_DATABASE_URI: Optional[str] = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = DEBUG

    # Database Pool
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    DB_POOL_TIMEOUT: int = int(os.getenv('DB_POOL_TIMEOUT', '30'))

    # Redis
    REDIS_URL: Optional[str] = os.getenv('REDIS_URL', 'redis://localhost:6379/2')

    # Twitter API
    TWITTER_BEARER_TOKEN: Optional[str] = os.getenv('TWITTER_BEARER_TOKEN')
    TWITTER_API_KEY: Optional[str] = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET: Optional[str] = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN: Optional[str] = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    TWITTER_TIMEOUT_SECONDS: int = int(os.getenv('TWITTER_TIMEOUT_SECONDS', '15'))

    # Twitter Limits
    TWITTER_MIN_RESULTS: int = int(os.getenv('TWITTER_MIN_RESULTS', '10'))
    TWITTER_MAX_RESULTS_PER_REQUEST: int = int(os.getenv('TWITTER_MAX_RESULTS_PER_REQUEST', '15'))
    TWITTER_MONTHLY_LIMIT: int = int(os.getenv('TWITTER_MONTHLY_LIMIT', '15000'))
    TWITTER_DAILY_TWEET_LIMIT: int = int(os.getenv('TWITTER_DAILY_TWEET_LIMIT', '500'))
    TWITTER_DAILY_REQUEST_LIMIT: int = int(os.getenv('TWITTER_DAILY_REQUEST_LIMIT', '3'))

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o')
    OPENAI_EMBEDDING_MODEL: str = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
    OPENAI_TIMEOUT_SECONDS: int = int(os.getenv('OPENAI_TIMEOUT_SECONDS', '60'))

    # Anthropic Claude (fallback)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL: str = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')

    # Local LLM (Ollama)
    LOCAL_LLM_URL: str = os.getenv('LOCAL_LLM_URL', 'http://localhost:11434')
    LOCAL_LLM_MODEL: str = os.getenv('LOCAL_LLM_MODEL', 'llama3.2')

    # LLM Provider Selection
    LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'openai')

    # BETO Model (Sentiment)
    BETO_MODEL_PATH: str = os.getenv('BETO_MODEL_PATH', 'dccuchile/bert-base-spanish-wwm-uncased')

    # Caching TTLs
    CACHE_TTL_TWITTER: int = int(os.getenv('CACHE_TTL_TWITTER', '86400'))
    CACHE_TTL_SENTIMENT: int = int(os.getenv('CACHE_TTL_SENTIMENT', '86400'))
    CACHE_TTL_OPENAI: int = int(os.getenv('CACHE_TTL_OPENAI', '43200'))
    CACHE_TTL_TRENDING: int = int(os.getenv('CACHE_TTL_TRENDING', '21600'))
    SENTIMENT_CACHE_TTL: int = int(os.getenv('SENTIMENT_CACHE_TTL', '900'))
    OPENAI_CACHE_TTL: int = int(os.getenv('OPENAI_CACHE_TTL', '1800'))
    TRENDING_CACHE_TTL: int = int(os.getenv('TRENDING_CACHE_TTL', '600'))
    TRENDING_CACHE_STALE_TTL: int = int(os.getenv('TRENDING_CACHE_STALE_TTL', '300'))

    # Cache Settings
    CACHE_MAX_SIZE: int = int(os.getenv('CACHE_MAX_SIZE', '1000'))

    # Twitter Request Limits
    TWITTER_MAX_TWEETS_PER_REQUEST: int = int(os.getenv('TWITTER_MAX_TWEETS_PER_REQUEST', '500'))

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))
    RATE_LIMIT_STORAGE_URI: str = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')

    # PND Topics
    PND_TOPICS: list = [
        'Seguridad',
        'Infraestructura',
        'Gobernanza y Transparencia',
        'Educacion',
        'Salud',
        'Igualdad y Equidad',
        'Paz y Reinsercion',
        'Economia y Empleo',
        'Medio Ambiente y Cambio Climatico',
        'Alimentacion'
    ]

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE')

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.SECRET_KEY:
            import secrets
            cls.SECRET_KEY = secrets.token_hex(32)
            cls.JWT_SECRET_KEY = cls.SECRET_KEY

        missing = []
        if not cls.TWITTER_BEARER_TOKEN:
            missing.append('TWITTER_BEARER_TOKEN')
        if not cls.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')

        if missing:
            import logging
            logging.warning(f"Missing API keys: {', '.join(missing)}")

        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

    @classmethod
    def validate(cls) -> bool:
        required = ['TWITTER_BEARER_TOKEN', 'OPENAI_API_KEY']
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Missing required keys in production: {', '.join(missing)}")
        return True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    TWITTER_BEARER_TOKEN = 'test-token'
    OPENAI_API_KEY = 'test-key'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
