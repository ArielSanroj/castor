"""
Lead repository for database operations.
Handles lead (demo requests) CRUD operations.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from models.database import Lead

logger = logging.getLogger(__name__)


class LeadRepository:
    """Repository for lead database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

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
    ) -> Optional[Lead]:
        """Create a new lead (demo request)."""
        session = self._db.get_session()
        try:
            existing_lead = session.query(Lead).filter(Lead.email == email).first()
            if existing_lead:
                logger.warning(f"Lead with email {email} already exists")
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

            session.add(lead)
            session.commit()
            session.refresh(lead)

            logger.info(f"Lead created: {lead.id} - {lead.email}")
            return lead

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating lead: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        session = self._db.get_session()
        try:
            return session.query(Lead).filter(Lead.id == lead_id).first()
        except Exception as e:
            logger.error(f"Error getting lead: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email."""
        session = self._db.get_session()
        try:
            return session.query(Lead).filter(Lead.email == email).first()
        except Exception as e:
            logger.error(f"Error getting lead by email: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_leads(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Lead]:
        """Get leads with optional filters."""
        session = self._db.get_session()
        try:
            query = session.query(Lead)

            if status:
                query = query.filter(Lead.status == status)

            if candidacy_type:
                query = query.filter(Lead.candidacy_type == candidacy_type)

            return query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting leads: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def update_lead_status(
        self,
        lead_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update lead status."""
        session = self._db.get_session()
        try:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                logger.warning(f"Lead {lead_id} not found")
                return False

            lead.status = status
            if notes:
                lead.notes = notes

            session.commit()
            logger.info(f"Lead {lead_id} status updated to {status}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating lead status: {e}", exc_info=True)
            return False
        finally:
            session.close()

    def count_leads(
        self,
        status: Optional[str] = None,
        candidacy_type: Optional[str] = None
    ) -> int:
        """Count leads with optional filters."""
        session = self._db.get_session()
        try:
            query = session.query(Lead)

            if status:
                query = query.filter(Lead.status == status)

            if candidacy_type:
                query = query.filter(Lead.candidacy_type == candidacy_type)

            return query.count()
        except Exception as e:
            logger.error(f"Error counting leads: {e}", exc_info=True)
            return 0
        finally:
            session.close()
