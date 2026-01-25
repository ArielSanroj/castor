"""
Service clients for E-14 Service.
Handles communication with Core Service and other microservices.
"""
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from utils.http_client import ServiceClient, ServiceUnavailable

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    """Result of token validation."""
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[list] = None
    error: Optional[str] = None


class CoreServiceClient(ServiceClient):
    """
    Client for Core Service communication.

    Handles:
    - JWT token validation
    - User information retrieval
    - Authentication checks
    """

    def __init__(self, base_url: Optional[str] = None):
        url = base_url or os.getenv("CORE_SERVICE_URL", "http://localhost:5001")
        super().__init__(
            base_url=url,
            service_name="core-service",
            timeout=10.0,
            max_retries=2,
            circuit_failure_threshold=5,
            circuit_reset_timeout=30
        )

    def validate_token(self, token: str) -> TokenValidationResult:
        """
        Validate JWT token with Core Service.

        Args:
            token: JWT access token

        Returns:
            TokenValidationResult with user info if valid
        """
        try:
            response = self.post(
                "/internal/validate-token",
                json={"token": token}
            )
            data = response.json()

            if data.get("valid"):
                return TokenValidationResult(
                    valid=True,
                    user_id=data.get("user_id"),
                    email=data.get("email"),
                    roles=data.get("roles", ["user"])
                )
            else:
                return TokenValidationResult(
                    valid=False,
                    error=data.get("error", "Invalid token")
                )

        except ServiceUnavailable as e:
            logger.error(f"Core service unavailable for token validation: {e}")
            return TokenValidationResult(
                valid=False,
                error="Authentication service unavailable"
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return TokenValidationResult(
                valid=False,
                error=str(e)
            )

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Core Service.

        Args:
            user_id: User ID

        Returns:
            User dict or None if not found
        """
        try:
            response = self.get(f"/internal/user/{user_id}")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None


# Singleton instance
_core_client: Optional[CoreServiceClient] = None


def get_core_client() -> CoreServiceClient:
    """Get or create Core Service client singleton."""
    global _core_client
    if _core_client is None:
        _core_client = CoreServiceClient()
    return _core_client
