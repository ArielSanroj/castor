"""
Response helpers for standardized API responses.
Provides DRY utilities for common response patterns.
"""
import logging
from functools import wraps
from threading import Lock
from typing import Any, Dict, Optional, Tuple, Callable
from flask import jsonify, Response

logger = logging.getLogger(__name__)


# =============================================================================
# STANDARDIZED RESPONSE FUNCTIONS
# =============================================================================

def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200
) -> Tuple[Response, int]:
    """
    Create a standardized success response.

    Args:
        data: Response payload data
        message: Optional success message
        status_code: HTTP status code (default 200)

    Returns:
        Tuple of (jsonify response, status code)
    """
    response = {"success": True}

    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data

    if message:
        response["message"] = message

    return jsonify(response), status_code


def error_response(
    error: str,
    status_code: int = 400,
    details: Optional[Dict] = None
) -> Tuple[Response, int]:
    """
    Create a standardized error response.

    Args:
        error: Error message for the client
        status_code: HTTP status code (default 400)
        details: Optional additional error details (NOT exception info)

    Returns:
        Tuple of (jsonify response, status code)
    """
    response = {
        "success": False,
        "error": error
    }

    if details:
        response["details"] = details

    return jsonify(response), status_code


def validation_error(field: str, message: str) -> Tuple[Response, int]:
    """Create a validation error response."""
    return error_response(
        error=f"Validation error: {message}",
        status_code=400,
        details={"field": field}
    )


def not_found_error(resource: str) -> Tuple[Response, int]:
    """Create a not found error response."""
    return error_response(
        error=f"{resource} not found",
        status_code=404
    )


def internal_error(exception: Exception, context: str = "") -> Tuple[Response, int]:
    """
    Create an internal server error response.
    Logs the full exception but returns sanitized message to client.

    Args:
        exception: The caught exception
        context: Additional context for logging

    Returns:
        Sanitized error response (no exception details exposed)
    """
    logger.error(f"Internal error in {context}: {exception}", exc_info=True)
    return error_response(
        error="Internal server error. Please try again later.",
        status_code=500
    )


# =============================================================================
# REQUEST VALIDATION HELPERS
# =============================================================================

def require_field(payload: Dict, field: str, field_type: type = str) -> Tuple[Any, Optional[Tuple[Response, int]]]:
    """
    Validate that a required field exists and has the correct type.

    Args:
        payload: Request payload dict
        field: Field name to validate
        field_type: Expected type (default str)

    Returns:
        Tuple of (value, None) if valid, or (None, error_response) if invalid
    """
    value = payload.get(field)

    if value is None:
        return None, error_response(f"{field} is required", 400)

    if field_type == str and isinstance(value, str):
        value = value.strip()
        if not value:
            return None, error_response(f"{field} cannot be empty", 400)

    if not isinstance(value, field_type):
        return None, error_response(f"{field} must be of type {field_type.__name__}", 400)

    return value, None


def validate_range(
    value: int,
    min_val: int,
    max_val: int,
    field_name: str
) -> Optional[Tuple[Response, int]]:
    """
    Validate that a numeric value is within a range.

    Returns:
        None if valid, error response if invalid
    """
    if value < min_val or value > max_val:
        return error_response(
            f"{field_name} must be between {min_val} and {max_val}",
            400
        )
    return None


# =============================================================================
# THREAD-SAFE SERVICE INITIALIZATION
# =============================================================================

class ThreadSafeServiceFactory:
    """
    Thread-safe lazy initialization of services.
    Uses double-checked locking pattern.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._locks: Dict[str, Lock] = {}
        self._global_lock = Lock()

    def get_or_create(self, name: str, factory: Callable[[], Any]) -> Any:
        """
        Get existing service or create new one thread-safely.

        Args:
            name: Service identifier
            factory: Callable that creates the service

        Returns:
            The service instance
        """
        # Fast path - service already exists
        if name in self._services:
            return self._services[name]

        # Slow path - need to potentially create service
        with self._global_lock:
            # Get or create lock for this service
            if name not in self._locks:
                self._locks[name] = Lock()

        with self._locks[name]:
            # Double-check after acquiring lock
            if name not in self._services:
                self._services[name] = factory()
            return self._services[name]

    def clear(self, name: Optional[str] = None):
        """Clear service(s) from cache."""
        with self._global_lock:
            if name:
                self._services.pop(name, None)
            else:
                self._services.clear()


# Global service factory instance
service_factory = ThreadSafeServiceFactory()


# =============================================================================
# DECORATORS
# =============================================================================

def handle_exceptions(context: str = ""):
    """
    Decorator to handle exceptions consistently.
    Logs full exception but returns sanitized response.

    Args:
        context: Context string for logging
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return internal_error(e, context or func.__name__)
        return wrapper
    return decorator


def require_json(func: Callable):
    """Decorator to require JSON body in request."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request
        if not request.is_json:
            return error_response("Content-Type must be application/json", 415)
        return func(*args, **kwargs)
    return wrapper
