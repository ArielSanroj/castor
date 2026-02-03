"""
Response helpers and service factory utilities.
Provides thread-safe lazy initialization of services.
"""
import threading
from typing import Dict, Any, Type, TypeVar

T = TypeVar('T')


class ServiceFactory:
    """
    Thread-safe factory for creating and caching service instances.
    Implements lazy initialization pattern.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get_or_create(self, name: str, service_class: Type[T], *args, **kwargs) -> T:
        """
        Get existing service instance or create a new one.

        Args:
            name: Unique identifier for the service
            service_class: Class to instantiate if not exists
            *args, **kwargs: Arguments for service instantiation

        Returns:
            Service instance
        """
        if name not in self._services:
            with self._lock:
                # Double-check locking pattern
                if name not in self._services:
                    self._services[name] = service_class(*args, **kwargs)
        return self._services[name]

    def clear(self, name: str = None):
        """
        Clear cached service(s).

        Args:
            name: Optional service name to clear. If None, clears all.
        """
        with self._lock:
            if name is None:
                self._services.clear()
            elif name in self._services:
                del self._services[name]


# Global service factory instance
service_factory = ServiceFactory()


def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> tuple:
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code

    Returns:
        Tuple of (response dict, status code)
    """
    response = {
        "success": True,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    return response, status_code


def error_response(message: str, status_code: int = 400, errors: list = None) -> tuple:
    """
    Create a standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code
        errors: List of specific errors

    Returns:
        Tuple of (response dict, status code)
    """
    response = {
        "success": False,
        "error": message,
    }
    if errors:
        response["errors"] = errors
    return response, status_code
