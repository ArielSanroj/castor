"""
Configuration module for E-14 Service.
Handles electoral form processing, OCR, and ingestion.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration class for E-14 Service."""

    # Service identification
    SERVICE_NAME: str = "e14-service"
    SERVICE_PORT: int = int(os.getenv('E14_SERVICE_PORT', '5002'))

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
    DATABASE_URL: Optional[str] = os.getenv('E14_DATABASE_URL', 'postgresql://castor:castor_dev@localhost:5432/e14_db')
    SQLALCHEMY_DATABASE_URI: Optional[str] = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = DEBUG

    # Database Pool
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    DB_POOL_TIMEOUT: int = int(os.getenv('DB_POOL_TIMEOUT', '30'))

    # Redis
    REDIS_URL: Optional[str] = os.getenv('REDIS_URL', 'redis://localhost:6379/1')

    # Anthropic Claude (for Vision OCR)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL: str = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
    CLAUDE_VISION_MODEL: str = os.getenv('CLAUDE_VISION_MODEL', 'claude-sonnet-4-20250514')

    # E-14 OCR Settings
    E14_OCR_MAX_PAGES: int = int(os.getenv('E14_OCR_MAX_PAGES', '20'))
    E14_OCR_TIMEOUT: int = int(os.getenv('E14_OCR_TIMEOUT', '120'))
    E14_OCR_DPI: int = int(os.getenv('E14_OCR_DPI', '150'))

    # E-14 Cost Limits
    E14_COST_PER_PROCESS: float = float(os.getenv('E14_COST_PER_PROCESS', '0.10'))
    E14_HOURLY_COST_LIMIT: float = float(os.getenv('E14_HOURLY_COST_LIMIT', '2.00'))
    E14_DAILY_COST_LIMIT: float = float(os.getenv('E14_DAILY_COST_LIMIT', '5.00'))
    E14_MAX_FILE_SIZE_MB: int = int(os.getenv('E14_MAX_FILE_SIZE_MB', '10'))
    E14_MAX_PAGES: int = int(os.getenv('E14_MAX_PAGES', '20'))

    # Scraping
    REGISTRADURIA_BASE_URL: str = os.getenv('REGISTRADURIA_BASE_URL', 'https://www.registraduria.gov.co')
    SCRAPER_TIMEOUT: int = int(os.getenv('SCRAPER_TIMEOUT', '30'))
    SCRAPER_RETRY_ATTEMPTS: int = int(os.getenv('SCRAPER_RETRY_ATTEMPTS', '3'))

    # Pipeline Settings
    PIPELINE_DOWNLOAD_WORKERS: int = int(os.getenv('PIPELINE_DOWNLOAD_WORKERS', '4'))
    PIPELINE_OCR_WORKERS: int = int(os.getenv('PIPELINE_OCR_WORKERS', '2'))
    PIPELINE_VALIDATION_WORKERS: int = int(os.getenv('PIPELINE_VALIDATION_WORKERS', '4'))

    # Rate Limiting
    RATE_LIMIT_STORAGE_URI: str = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')

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

        if not cls.ANTHROPIC_API_KEY:
            import logging
            logging.warning("ANTHROPIC_API_KEY not set - OCR will not work")

        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

    @classmethod
    def validate(cls) -> bool:
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required in production")
        return True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    ANTHROPIC_API_KEY = 'test-key'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
