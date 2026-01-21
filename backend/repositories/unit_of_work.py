"""
Unit of Work Pattern implementation.
Manages database transactions and repository access.
"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import Config
from .user_repository import UserRepository
from .analysis_repository import AnalysisRepository
from .lead_repository import LeadRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work for managing transactions and repository access.

    Provides transactional boundary for a set of operations.
    All repositories share the same session within a unit of work.

    Usage:
        with UnitOfWork() as uow:
            user = uow.users.create(email="...", password="...")
            uow.commit()
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Unit of Work.

        Args:
            session: Optional pre-existing session
        """
        self._session = session
        self._owns_session = session is None

        # Repositories (lazy initialized)
        self._users: Optional[UserRepository] = None
        self._analyses: Optional[AnalysisRepository] = None
        self._leads: Optional[LeadRepository] = None

    @property
    def session(self) -> Session:
        """Get or create session."""
        if self._session is None:
            self._session = _session_factory()
        return self._session

    @property
    def users(self) -> UserRepository:
        """Get User repository."""
        if self._users is None:
            self._users = UserRepository(self.session)
        return self._users

    @property
    def analyses(self) -> AnalysisRepository:
        """Get Analysis repository."""
        if self._analyses is None:
            self._analyses = AnalysisRepository(self.session)
        return self._analyses

    @property
    def leads(self) -> LeadRepository:
        """Get Lead repository."""
        if self._leads is None:
            self._leads = LeadRepository(self.session)
        return self._leads

    def commit(self) -> None:
        """Commit current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.session.rollback()

    def flush(self) -> None:
        """Flush pending changes to database."""
        self.session.flush()

    def __enter__(self) -> 'UnitOfWork':
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if exc_type is not None:
            self.rollback()
        if self._owns_session and self._session is not None:
            self._session.close()


# Session factory (singleton pattern)
_engine = None
_SessionFactory = None


def _get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            Config.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=Config.DB_POOL_SIZE,
            max_overflow=Config.DB_MAX_OVERFLOW,
            pool_timeout=Config.DB_POOL_TIMEOUT
        )
    return _engine


def _session_factory() -> Session:
    """Create a new session."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=_get_engine(),
            autocommit=False,
            autoflush=False
        )
    return _SessionFactory()


@contextmanager
def unit_of_work() -> Generator[UnitOfWork, None, None]:
    """
    Context manager for Unit of Work.

    Usage:
        with unit_of_work() as uow:
            user = uow.users.create(email="...", password="...")
            uow.commit()

    Yields:
        UnitOfWork instance
    """
    uow = UnitOfWork()
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
    finally:
        if uow._owns_session and uow._session is not None:
            uow._session.close()


def get_unit_of_work() -> UnitOfWork:
    """
    Get a new Unit of Work instance.

    For simple operations that don't need context manager.

    Returns:
        UnitOfWork instance
    """
    return UnitOfWork()
