"""
Data Repository Interfaces.
Abstracts data persistence layer for database independence.

SOLID Principles:
- ISP: Segregated interfaces for different entity types
- DIP: Services depend on repository abstractions
- SRP: Each repository handles one entity type

Repository Pattern Benefits:
- Database agnostic (PostgreSQL, MySQL, MongoDB)
- Testable (easy to mock)
- Centralized data access logic
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TypeVar, Generic
from datetime import datetime


T = TypeVar('T')


@dataclass
class PaginationParams:
    """Pagination parameters for list queries."""
    page: int = 1
    per_page: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"  # "asc" or "desc"


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result."""
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class IDataRepository(ABC):
    """
    Base repository interface with common CRUD operations.
    """

    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def get_all(self, pagination: Optional[PaginationParams] = None) -> PaginatedResult:
        """Get all entities with optional pagination."""
        pass

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new entity."""
        pass

    @abstractmethod
    def update(self, entity_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update existing entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        pass

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        pass


class IUserRepository(ABC):
    """
    User-specific repository interface.
    Extends base operations with user-specific methods.
    """

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        pass

    @abstractmethod
    def create(
        self,
        email: str,
        password_hash: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Create new user."""
        pass

    @abstractmethod
    def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user data."""
        pass

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Delete user."""
        pass

    @abstractmethod
    def verify_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials and return user if valid."""
        pass

    @abstractmethod
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        pass


class IAnalysisRepository(ABC):
    """
    Analysis-specific repository interface.
    Handles political analysis data persistence.
    """

    @abstractmethod
    def save_analysis(
        self,
        user_id: str,
        location: str,
        theme: str,
        analysis_data: Dict[str, Any],
        candidate_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Save analysis result."""
        pass

    @abstractmethod
    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis by ID."""
        pass

    @abstractmethod
    def get_user_analyses(
        self,
        user_id: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult:
        """Get all analyses for a user."""
        pass

    @abstractmethod
    def get_analyses_by_location(
        self,
        location: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult:
        """Get all analyses for a location."""
        pass

    @abstractmethod
    def get_recent_analyses(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent analyses within specified days."""
        pass

    @abstractmethod
    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete analysis by ID."""
        pass


class ITrendingRepository(ABC):
    """
    Trending topics repository interface.
    """

    @abstractmethod
    def save_trending(
        self,
        location: str,
        topics: List[Dict[str, Any]],
        detected_at: Optional[datetime] = None
    ) -> bool:
        """Save trending topics for a location."""
        pass

    @abstractmethod
    def get_trending(
        self,
        location: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get trending topics for a location."""
        pass

    @abstractmethod
    def get_trending_history(
        self,
        location: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get trending topics history."""
        pass


class ILeadRepository(ABC):
    """
    Lead/demo request repository interface.
    """

    @abstractmethod
    def create_lead(
        self,
        name: str,
        email: str,
        phone: str,
        interest: str,
        location: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Create new lead."""
        pass

    @abstractmethod
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get lead by ID."""
        pass

    @abstractmethod
    def get_leads(
        self,
        status: Optional[str] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult:
        """Get leads with optional status filter."""
        pass

    @abstractmethod
    def update_lead_status(self, lead_id: str, status: str) -> bool:
        """Update lead status."""
        pass

    @abstractmethod
    def count_leads(self, status: Optional[str] = None) -> int:
        """Count leads with optional status filter."""
        pass
