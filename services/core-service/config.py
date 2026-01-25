"""
Configuration module for Core Service.
Handles authentication, users, and shared infrastructure.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration class for Core Service."""

    # Service identification
    SERVICE_NAME: str = "core-service"
    SERVICE_PORT: int = int(os.getenv('CORE_SERVICE_PORT', '5001'))

    # Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY', '')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING: bool = False

    # Server
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = SERVICE_PORT

    # CORS
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5002,http://localhost:5003').split(',')

    # JWT
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
    JWT_REFRESH_TOKEN_EXPIRES: int = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '604800'))

    # Database (PostgreSQL)
    DATABASE_URL: Optional[str] = os.getenv('CORE_DATABASE_URL', os.getenv('DATABASE_URL', 'postgresql://castor:castor_dev@localhost:5432/core_db'))
    SQLALCHEMY_DATABASE_URI: Optional[str] = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = DEBUG

    # Database Pool
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '10'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    DB_POOL_TIMEOUT: int = int(os.getenv('DB_POOL_TIMEOUT', '30'))

    # Redis
    REDIS_URL: Optional[str] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = os.getenv('RATE_LIMIT_DEFAULT', '100/hour')
    RATE_LIMIT_AUTH: str = os.getenv('RATE_LIMIT_AUTH', '20/minute')
    RATE_LIMIT_STORAGE_URI: str = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE')

    # Security
    _SECRET_KEY_MIN_LENGTH: int = 32

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if not cls.SECRET_KEY:
            import secrets
            cls.SECRET_KEY = secrets.token_hex(32)
            cls.JWT_SECRET_KEY = cls.SECRET_KEY
            import logging
            logging.warning("SECRET_KEY not set - generated temporary key")

        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

    @classmethod
    def validate(cls) -> bool:
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < cls._SECRET_KEY_MIN_LENGTH:
            raise ValueError("SECRET_KEY must be set in production (min 32 chars)")
        if not cls.JWT_SECRET_KEY or len(cls.JWT_SECRET_KEY) < cls._SECRET_KEY_MIN_LENGTH:
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
