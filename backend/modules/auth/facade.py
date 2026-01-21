"""
Auth Module Facade.

Provides authentication and user management operations.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuthModule:
    """
    Facade for authentication operations.

    Provides user registration, authentication, and management.
    Uses the Repository Pattern for database abstraction.

    Usage:
        module = AuthModule()
        user = module.register(
            email="test@example.com",
            password="secret123"
        )
        token = module.login("test@example.com", "secret123")
    """

    def __init__(self):
        """Initialize auth module."""
        pass

    def register(
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
    ) -> Optional[Dict[str, Any]]:
        """
        Register a new user.

        Args:
            email: User email
            password: User password
            phone: Optional phone number
            first_name: Optional first name
            last_name: Optional last name
            campaign_role: Optional campaign role
            candidate_position: Optional candidate position
            whatsapp_number: Optional WhatsApp number
            whatsapp_opt_in: WhatsApp opt-in status

        Returns:
            User dict if successful, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                user = uow.users.create(
                    email=email,
                    password=password,
                    phone=phone,
                    first_name=first_name,
                    last_name=last_name,
                    campaign_role=campaign_role,
                    candidate_position=candidate_position,
                    whatsapp_number=whatsapp_number,
                    whatsapp_opt_in=whatsapp_opt_in
                )

                if not user:
                    return None

                uow.commit()

                return {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }

        except Exception as e:
            logger.error(f"Registration failed: {e}", exc_info=True)
            return None

    def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user.

        Args:
            email: User email
            password: User password

        Returns:
            User dict if successful, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                user = uow.users.authenticate(email, password)

                if not user:
                    return None

                return {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }

        except Exception as e:
            logger.error(f"Authentication failed: {e}", exc_info=True)
            return None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User dict if found, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                user = uow.users.get_by_id(user_id)

                if not user:
                    return None

                return {
                    "id": str(user.id),
                    "email": user.email,
                    "phone": user.phone,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "campaign_role": user.campaign_role,
                    "candidate_position": user.candidate_position,
                    "whatsapp_number": user.whatsapp_number,
                    "whatsapp_opt_in": user.whatsapp_opt_in
                }

        except Exception as e:
            logger.error(f"Get user failed: {e}", exc_info=True)
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User dict if found, None otherwise
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                user = uow.users.get_by_email(email)

                if not user:
                    return None

                return {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }

        except Exception as e:
            logger.error(f"Get user by email failed: {e}", exc_info=True)
            return None

    def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update user password.

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            True if successful
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                result = uow.users.update_password(user_id, new_password)
                if result:
                    uow.commit()
                return result

        except Exception as e:
            logger.error(f"Update password failed: {e}", exc_info=True)
            return False

    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            from repositories import unit_of_work

            with unit_of_work() as uow:
                result = uow.users.deactivate(user_id)
                if result:
                    uow.commit()
                return result

        except Exception as e:
            logger.error(f"Deactivate user failed: {e}", exc_info=True)
            return False
