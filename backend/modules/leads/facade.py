"""
Leads Module Facade.

Provides lead management and CRM operations.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LeadsModule:
    """
    Facade for lead management operations.

    Provides lead creation, querying, and status management.
    Uses the Repository Pattern for database abstraction.

    Usage:
        module = LeadsModule()
        lead = module.create_lead(
            first_name="Juan",
            last_name="Perez",
            email="juan@example.com",
            phone="+573001234567",
            interest="Demo solicitation",
            location="Bogota"
        )
    """

    def __init__(self):
        """Initialize leads module."""
        pass

    def create_lead(
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
    ) -> Optional[Dict[str, Any]]:
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
            Lead dict if successful, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                lead = uow.leads.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    interest=interest,
                    location=location,
                    candidacy_type=candidacy_type,
                    status=status,
                    notes=notes,
                    metadata=metadata
                )

                if not lead:
                    return None

                uow.commit()

                return {
                    "id": str(lead.id),
                    "email": lead.email,
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "status": lead.status
                }

        except Exception as e:
            logger.error(f"Create lead failed: {e}", exc_info=True)
            return None

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Get lead by ID.

        Args:
            lead_id: Lead ID

        Returns:
            Lead dict if found, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                lead = uow.leads.get_by_id(lead_id)

                if not lead:
                    return None

                return self._lead_to_dict(lead)

        except Exception as e:
            logger.error(f"Get lead failed: {e}", exc_info=True)
            return None

    def get_lead_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get lead by email.

        Args:
            email: Lead email

        Returns:
            Lead dict if found, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                lead = uow.leads.get_by_email(email)

                if not lead:
                    return None

                return self._lead_to_dict(lead)

        except Exception as e:
            logger.error(f"Get lead by email failed: {e}", exc_info=True)
            return None

    def get_leads(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get leads with optional filters.

        Args:
            status: Optional status filter
            candidacy_type: Optional candidacy type filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of lead dicts
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                leads = uow.leads.get_filtered(
                    status=status,
                    candidacy_type=candidacy_type,
                    limit=limit,
                    offset=offset
                )

                return [self._lead_to_dict(lead) for lead in leads]

        except Exception as e:
            logger.error(f"Get leads failed: {e}", exc_info=True)
            return []

    def update_status(
        self,
        lead_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update lead status.

        Args:
            lead_id: Lead ID
            status: New status
            notes: Optional notes

        Returns:
            True if successful
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                result = uow.leads.update_status(lead_id, status, notes)
                if result:
                    uow.commit()
                return result

        except Exception as e:
            logger.error(f"Update lead status failed: {e}", exc_info=True)
            return False

    def count_leads(
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
            Count of leads
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                return uow.leads.count_filtered(
                    status=status,
                    candidacy_type=candidacy_type
                )

        except Exception as e:
            logger.error(f"Count leads failed: {e}", exc_info=True)
            return 0

    def _lead_to_dict(self, lead) -> Dict[str, Any]:
        """Convert lead entity to dictionary."""
        return {
            "id": str(lead.id),
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "phone": lead.phone,
            "interest": lead.interest,
            "location": lead.location,
            "candidacy_type": lead.candidacy_type,
            "status": lead.status,
            "notes": lead.notes,
            "created_at": lead.created_at.isoformat() if lead.created_at else None
        }
