"""
Lead Repository.
Handles all lead-related data access operations.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from models.database import Lead
from .base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    """Repository for Lead entity operations."""

    def __init__(self, session: Session):
        """Initialize lead repository."""
        super().__init__(session, Lead)

    def get_by_email(self, email: str) -> Optional[Lead]:
        """
        Get lead by email.

        Args:
            email: Lead email

        Returns:
            Lead or None
        """
        return (
            self._session.query(Lead)
            .filter(Lead.email == email)
            .first()
        )

    def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check

        Returns:
            True if exists
        """
        return (
            self._session.query(Lead.id)
            .filter(Lead.email == email)
            .first()
        ) is not None

    def create(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        interest: str,
        location: str,
        candidacy_type: Optional[str] = None,
        status: str = "nuevo",
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Lead]:
        """
        Create a new lead.

        Args:
            first_name: First name
            last_name: Last name
            email: Email address
            phone: Phone number
            interest: Interest/reason
            location: Location
            candidacy_type: Type of candidacy
            status: Lead status
            notes: Optional notes
            metadata: Optional extra metadata

        Returns:
            Created lead or None if email exists
        """
        if self.email_exists(email):
            return None

        lead = Lead(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            interest=interest,
            location=location,
            candidacy_type=candidacy_type,
            status=status,
            notes=notes,
            extra_metadata=metadata or {}
        )

        self.add(lead)
        return lead

    def get_by_status(self, status: str, limit: int = 100, offset: int = 0) -> List[Lead]:
        """
        Get leads by status.

        Args:
            status: Lead status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of leads
        """
        return (
            self._session.query(Lead)
            .filter(Lead.status == status)
            .order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_by_candidacy_type(self, candidacy_type: str, limit: int = 100) -> List[Lead]:
        """
        Get leads by candidacy type.

        Args:
            candidacy_type: Type of candidacy
            limit: Maximum number of results

        Returns:
            List of leads
        """
        return (
            self._session.query(Lead)
            .filter(Lead.candidacy_type == candidacy_type)
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_filtered(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Lead]:
        """
        Get leads with optional filters.

        Args:
            status: Optional status filter
            candidacy_type: Optional candidacy type filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of leads
        """
        query = self._session.query(Lead)

        if status:
            query = query.filter(Lead.status == status)

        if candidacy_type:
            query = query.filter(Lead.candidacy_type == candidacy_type)

        return (
            query
            .order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_status(self, lead_id: str, status: str, notes: Optional[str] = None) -> bool:
        """
        Update lead status.

        Args:
            lead_id: Lead ID
            status: New status
            notes: Optional notes

        Returns:
            True if successful
        """
        lead = self.get_by_id(lead_id)
        if lead:
            lead.status = status
            if notes:
                lead.notes = notes
            return True
        return False

    def count_by_status(self, status: str) -> int:
        """
        Count leads by status.

        Args:
            status: Lead status

        Returns:
            Count
        """
        return (
            self._session.query(Lead)
            .filter(Lead.status == status)
            .count()
        )

    def count_filtered(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None
    ) -> int:
        """
        Count leads with optional filters.

        Args:
            status: Optional status filter
            candidacy_type: Optional candidacy type filter

        Returns:
            Count
        """
        query = self._session.query(Lead)

        if status:
            query = query.filter(Lead.status == status)

        if candidacy_type:
            query = query.filter(Lead.candidacy_type == candidacy_type)

        return query.count()
