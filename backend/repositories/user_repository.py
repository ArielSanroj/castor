"""
User Repository.
Handles all user-related data access operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash

from models.database import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""

    def __init__(self, session: Session):
        """Initialize user repository."""
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User or None
        """
        return (
            self._session.query(User)
            .filter(User.email == email)
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
            self._session.query(User.id)
            .filter(User.email == email)
            .first()
        ) is not None

    def create(
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
        """
        Create a new user.

        Args:
            email: User email
            password: Plain text password (will be hashed)
            phone: Optional phone number
            first_name: Optional first name
            last_name: Optional last name
            campaign_role: Optional campaign role
            candidate_position: Optional candidate position
            whatsapp_number: Optional WhatsApp number
            whatsapp_opt_in: WhatsApp opt-in status

        Returns:
            Created user or None if email exists
        """
        if self.email_exists(email):
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

        self.add(user)
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user by email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise
        """
        user = self.get_by_email(email)
        if user and check_password_hash(user.password_hash, password) and user.is_active:
            return user
        return None

    def get_active_users(self, limit: int = 100) -> list:
        """
        Get all active users.

        Args:
            limit: Maximum number of users

        Returns:
            List of active users
        """
        return (
            self._session.query(User)
            .filter(User.is_active == True)
            .limit(limit)
            .all()
        )

    def deactivate(self, user_id: str) -> bool:
        """
        Deactivate user account.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            return True
        return False

    def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update user password.

        Args:
            user_id: User ID
            new_password: New plain text password

        Returns:
            True if successful
        """
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = generate_password_hash(new_password)
            return True
        return False
