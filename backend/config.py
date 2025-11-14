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
    
    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING: bool = False
    
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
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o')
    
    # Database (PostgreSQL)
    DATABASE_URL: Optional[str] = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/castor_elecciones')
    SQLALCHEMY_DATABASE_URI: Optional[str] = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = DEBUG
    
    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_FROM: str = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+34637909472')
    TWILIO_CONTENT_SID: str = os.getenv('TWILIO_CONTENT_SID', 'HX899df0cc78b682c1a96c5bc83c5b4d3b')
    
    # BETO Model
    BETO_MODEL_PATH: str = os.getenv('BETO_MODEL_PATH', 'dccuchile/bert-base-spanish-wwm-uncased')
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))
    
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
        """Validate that all required configuration is present."""
        required_vars = [
            'TWITTER_BEARER_TOKEN',
            'OPENAI_API_KEY',
            'DATABASE_URL'
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var, None)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
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
        """Stricter validation for production."""
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY must be set in production")
        return super().validate()


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

