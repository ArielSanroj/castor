"""
User repository for database operations.
Handles user creation, authentication, and retrieval.
"""
import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash

from models.database import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db_base):
        """Initialize with database base."""
        self._db = db_base

    def create_user(
        self,
        email: str,
        password: str,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        campaign_role: Optional[str] = None,
        candidate_position: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        whatsapp_opt_in: bool = False
    ) -> Optional[User]:
        """Create a new user."""
        session = self._db.get_session()
        try:
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                logger.warning(f"User with email {email} already exists")
                return None

            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                campaign_role=campaign_role,
                candidate_position=candidate_position,
                whatsapp_number=whatsapp_number,
                whatsapp_opt_in=whatsapp_opt_in
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            logger.info(f"User created: {user.id}")
            return user

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating user: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user and return user if valid."""
        session = self._db.get_session()
        try:
            user = session.query(User).filter(User.email == email).first()
            if user and check_password_hash(user.password_hash, password) and user.is_active:
                return user
            return None
        except Exception as e:
            logger.error(f"Error authenticating user: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        session = self._db.get_session()
        try:
            return session.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        session = self._db.get_session()
        try:
            return session.query(User).filter(User.email == email).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}", exc_info=True)
            return None
        finally:
            session.close()
