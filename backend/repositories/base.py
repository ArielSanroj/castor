"""
Base Repository Pattern implementation.
Implements Fowler's Repository Pattern for database abstraction.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

# Generic type for entity
T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository.

    Provides a unified interface for data access operations,
    allowing easy swapping of database implementations.
    """

    def __init__(self, session: Session, model_class: Type[T]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy session
            model_class: The model class this repository manages
        """
        self._session = session
        self._model_class = model_class

    @property
    def session(self) -> Session:
        """Get current session."""
        return self._session

    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """
        Get entity by ID.

        Args:
            entity_id: The entity identifier

        Returns:
            Entity or None if not found
        """
        try:
            return self._session.query(self._model_class).filter(
                self._model_class.id == entity_id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self._model_class.__name__} by id: {e}")
            return None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        try:
            return (
                self._session.query(self._model_class)
                .offset(offset)
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self._model_class.__name__}: {e}")
            return []

    def add(self, entity: T) -> T:
        """
        Add entity to session.

        Args:
            entity: Entity to add

        Returns:
            Added entity
        """
        self._session.add(entity)
        return entity

    def add_all(self, entities: List[T]) -> List[T]:
        """
        Add multiple entities to session.

        Args:
            entities: List of entities to add

        Returns:
            Added entities
        """
        self._session.add_all(entities)
        return entities

    def delete(self, entity: T) -> None:
        """
        Delete entity from session.

        Args:
            entity: Entity to delete
        """
        self._session.delete(entity)

    def delete_by_id(self, entity_id: Any) -> bool:
        """
        Delete entity by ID.

        Args:
            entity_id: The entity identifier

        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(entity_id)
        if entity:
            self.delete(entity)
            return True
        return False

    def count(self) -> int:
        """
        Count all entities.

        Returns:
            Total count
        """
        try:
            return self._session.query(self._model_class).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self._model_class.__name__}: {e}")
            return 0

    def exists(self, entity_id: Any) -> bool:
        """
        Check if entity exists.

        Args:
            entity_id: The entity identifier

        Returns:
            True if exists
        """
        try:
            return (
                self._session.query(self._model_class.id)
                .filter(self._model_class.id == entity_id)
                .first()
            ) is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self._model_class.__name__}: {e}")
            return False
