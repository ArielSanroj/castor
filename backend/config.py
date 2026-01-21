"""
Configuration module for CASTOR ELECCIONES backend.
Handles environment variables and application settings.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration class."""

    # Flask - SECURITY: SECRET_KEY must be set in production
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING: bool = False

    # Security validation
    _SECRET_KEY_MIN_LENGTH: int = 32
    
    # Server
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5001'))
    
    # CORS
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))  # 1 hour
    
    # Twitter API (Tweepy)
    TWITTER_BEARER_TOKEN: Optional[str] = os.getenv('TWITTER_BEARER_TOKEN')
    TWITTER_API_KEY: Optional[str] = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET: Optional[str] = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN: Optional[str] = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    TWITTER_TIMEOUT_SECONDS: int = int(os.getenv('TWITTER_TIMEOUT_SECONDS', '15'))

    # Twitter Free Tier Limits (100 posts/month)
    TWITTER_MIN_RESULTS: int = int(os.getenv('TWITTER_MIN_RESULTS', '10'))
    TWITTER_MAX_RESULTS_PER_REQUEST: int = int(os.getenv('TWITTER_MAX_RESULTS_PER_REQUEST', '15'))
    TWITTER_MONTHLY_LIMIT: int = int(os.getenv('TWITTER_MONTHLY_LIMIT', '100'))
    TWITTER_DAILY_REQUEST_LIMIT: int = int(os.getenv('TWITTER_DAILY_REQUEST_LIMIT', '3'))
    
    # LLM Provider Selection (openai, claude, local)
    LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'openai')

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o')
    OPENAI_EMBEDDING_MODEL: str = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
    OPENAI_TIMEOUT_SECONDS: int = int(os.getenv('OPENAI_TIMEOUT_SECONDS', '60'))  # Increased for long content generation

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL: str = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')

    # Local LLM (Ollama)
    LOCAL_LLM_URL: str = os.getenv('LOCAL_LLM_URL', 'http://localhost:11434')
    LOCAL_LLM_MODEL: str = os.getenv('LOCAL_LLM_MODEL', 'llama3.2')
    
    # Database (PostgreSQL)
    DATABASE_URL: Optional[str] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/castor_elecciones')
    SQLALCHEMY_DATABASE_URI: Optional[str] = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = DEBUG

    # Database Pool Configuration
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    DB_POOL_TIMEOUT: int = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    
    # BETO Model
    BETO_MODEL_PATH: str = os.getenv('BETO_MODEL_PATH', 'dccuchile/bert-base-spanish-wwm-uncased')
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))
    RATE_LIMIT_STORAGE_URI: str = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')
    
    # Caching
    CACHE_MAX_SIZE: int = int(os.getenv('CACHE_MAX_SIZE', '64'))
    SENTIMENT_CACHE_TTL: int = int(os.getenv('SENTIMENT_CACHE_TTL', '900'))
    OPENAI_CACHE_TTL: int = int(os.getenv('OPENAI_CACHE_TTL', '1800'))
    TRENDING_CACHE_TTL: int = int(os.getenv('TRENDING_CACHE_TTL', '600'))
    TRENDING_CACHE_STALE_TTL: int = int(os.getenv('TRENDING_CACHE_STALE_TTL', '300'))
    
    # Caching (Optimizado para Twitter Free tier - 100 posts/mes)
    REDIS_URL: Optional[str] = os.getenv('REDIS_URL')  # e.g., 'redis://localhost:6379/0'
    CACHE_TTL_TWITTER: int = int(os.getenv('CACHE_TTL_TWITTER', '86400'))  # 24 hours (agresivo para conservar rate limit)
    CACHE_TTL_SENTIMENT: int = int(os.getenv('CACHE_TTL_SENTIMENT', '86400'))  # 24 hours
    CACHE_TTL_OPENAI: int = int(os.getenv('CACHE_TTL_OPENAI', '43200'))  # 12 hours
    CACHE_TTL_TRENDING: int = int(os.getenv('CACHE_TTL_TRENDING', '21600'))  # 6 hours
    
    # Twitter Free Tier Limits (100 posts per month)
    TWITTER_MAX_TWEETS_PER_REQUEST: int = int(os.getenv('TWITTER_MAX_TWEETS_PER_REQUEST', '15'))  # Máximo por análisis
    TWITTER_DAILY_TWEET_LIMIT: int = int(os.getenv('TWITTER_DAILY_TWEET_LIMIT', '3'))  # ~100/30 días = 3 por día
    TWITTER_MONTHLY_LIMIT: int = 100  # Free tier limit
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE')
    
    # PND Topics (Plan Nacional de Desarrollo 2022-2026)
    PND_TOPICS: list = [
        'Seguridad',
        'Infraestructura',
        'Gobernanza y Transparencia',
        'Educación',
        'Salud',
        'Igualdad y Equidad',
        'Paz y Reinserción',
        'Economía y Empleo',
        'Medio Ambiente y Cambio Climático',
        'Alimentación'
    ]
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration is present.

        Returns:
            True if validation passes

        Raises:
            ValueError: If required configuration is missing
        """
        # SECURITY: Validate SECRET_KEY
        if not cls.SECRET_KEY:
            # Generate a temporary key for development only
            import secrets
            cls.SECRET_KEY = secrets.token_hex(32)
            import logging
            logging.warning("SECRET_KEY not set - generated temporary key. Set SECRET_KEY in production!")

        # Core required variables
        required_vars = [
            'DATABASE_URL',
        ]

        # External API keys (may be optional in dev, but recommended)
        api_keys = [
            'TWITTER_BEARER_TOKEN',
            'OPENAI_API_KEY',
        ]

        missing_required = [var for var in required_vars if not getattr(cls, var, None)]
        missing_api_keys = [var for var in api_keys if not getattr(cls, var, None)]

        if missing_required:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_required)}")

        if missing_api_keys:
            raise ValueError(f"Missing API keys (may cause service failures): {', '.join(missing_api_keys)}")

        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    @classmethod
    def validate(cls) -> bool:
        """
        Stricter validation for production environment.
        Fails hard if any secrets are missing.
        """
        # SECURITY: Validate SECRET_KEY length and presence
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < cls._SECRET_KEY_MIN_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be set to a secure value (min {cls._SECRET_KEY_MIN_LENGTH} chars) in production"
            )

        # Validate JWT_SECRET_KEY
        if not cls.JWT_SECRET_KEY or len(cls.JWT_SECRET_KEY) < cls._SECRET_KEY_MIN_LENGTH:
            raise ValueError("JWT_SECRET_KEY must be set in production (min 32 chars)")

        # Validate all required secrets
        required_secrets = [
            'TWITTER_BEARER_TOKEN',
            'OPENAI_API_KEY',
            'DATABASE_URL',
        ]

        missing_secrets = [var for var in required_secrets if not getattr(cls, var, None)]
        if missing_secrets:
            raise ValueError(f"Missing required secrets in production: {', '.join(missing_secrets)}")

        return True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    TWITTER_BEARER_TOKEN = 'test-token'
    OPENAI_API_KEY = 'test-key'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
