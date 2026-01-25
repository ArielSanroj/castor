"""
Service clients for Dashboard IA Service.
Handles communication with Core Service and E-14 Service.
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
    """Client for Core Service communication."""

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
        """Validate JWT token with Core Service."""
        try:
            response = self.post("/internal/validate-token", json={"token": token})
            data = response.json()

            if data.get("valid"):
                return TokenValidationResult(
                    valid=True,
                    user_id=data.get("user_id"),
                    email=data.get("email"),
                    roles=data.get("roles", ["user"])
                )
            return TokenValidationResult(valid=False, error=data.get("error"))

        except ServiceUnavailable as e:
            logger.error(f"Core service unavailable: {e}")
            return TokenValidationResult(valid=False, error="Auth service unavailable")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return TokenValidationResult(valid=False, error=str(e))

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from Core Service."""
        try:
            response = self.get(f"/internal/user/{user_id}")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None


class E14ServiceClient(ServiceClient):
    """Client for E-14 Service communication."""

    def __init__(self, base_url: Optional[str] = None):
        url = base_url or os.getenv("E14_SERVICE_URL", "http://localhost:5002")
        super().__init__(
            base_url=url,
            service_name="e14-service",
            timeout=120.0,  # Longer timeout for OCR
            max_retries=1,
            circuit_failure_threshold=3,
            circuit_reset_timeout=60
        )

    def process_e14(self, pdf_url: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """Process E-14 form through OCR service."""
        try:
            payload = {"url": pdf_url}
            if options:
                payload.update(options)

            response = self.post("/api/v1/e14/process", json=payload)
            return response.json()

        except ServiceUnavailable as e:
            logger.error(f"E14 service unavailable: {e}")
            return {"ok": False, "error": "E14 service unavailable"}
        except Exception as e:
            logger.error(f"E14 processing error: {e}")
            return {"ok": False, "error": str(e)}

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        try:
            response = self.get("/api/v1/pipeline/status")
            return response.json()
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return {"status": "unknown", "error": str(e)}


# Singleton instances
_core_client: Optional[CoreServiceClient] = None
_e14_client: Optional[E14ServiceClient] = None


def get_core_client() -> CoreServiceClient:
    """Get or create Core Service client singleton."""
    global _core_client
    if _core_client is None:
        _core_client = CoreServiceClient()
    return _core_client


def get_e14_client() -> E14ServiceClient:
    """Get or create E14 Service client singleton."""
    global _e14_client
    if _e14_client is None:
        _e14_client = E14ServiceClient()
    return _e14_client
