"""
Database base service with session management.
Provides core database functionality for repository modules.
"""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import Config
from models.database import Base

logger = logging.getLogger(__name__)


class DatabaseBase:
    """Base class for database operations with session management."""

    def __init__(self):
        """Initialize database connection."""
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL not configured")

        if Config.DATABASE_URL.startswith("sqlite"):
            self.engine = create_engine(
                Config.DATABASE_URL,
                connect_args={"check_same_thread": False}
            )
            logger.info("DatabaseBase initialized with SQLite")
        else:
            self.engine = create_engine(
                Config.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=Config.DB_POOL_SIZE,
                max_overflow=Config.DB_MAX_OVERFLOW,
                pool_timeout=Config.DB_POOL_TIMEOUT
            )
            logger.info(f"DatabaseBase initialized (pool_size={Config.DB_POOL_SIZE})")

        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def init_db(self):
        """Initialize database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created")
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            raise

    def get_session(self) -> Session:
        """Get database session (legacy - prefer session_scope for new code)."""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        Usage:
            with db_service.session_scope() as session:
                session.add(obj)
                # auto-commits on success, auto-rollbacks on exception
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
