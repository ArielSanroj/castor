"""
HTTP Client with retry, timeout, and circuit breaker.
Base class for inter-service communication.
"""
import httpx
import logging
from typing import Optional, Dict, Any
from functools import wraps
import time

from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)


class ServiceClient:
    """
    Base HTTP client for inter-service communication.

    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker to prevent cascade failures
    - Timeout configuration
    - Request/response logging

    Usage:
        client = ServiceClient(
            base_url="http://e14-service:5002",
            service_name="e14-service"
        )
        response = client.post("/v1/process", json={"url": "..."})
    """

    def __init__(
        self,
        base_url: str,
        service_name: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_failure_threshold: int = 5,
        circuit_reset_timeout: int = 60
    ):
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": f"castor-service-client/1.0"}
        )

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            reset_timeout=circuit_reset_timeout,
            expected_exceptions=(httpx.RequestError, httpx.HTTPStatusError)
        )

    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if request should be retried."""
        if attempt >= self.max_retries:
            return False

        # Retry on connection errors, timeouts
        if isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout)):
            return True

        # Retry on 5xx errors
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code >= 500

        return False

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        return min(2 ** attempt, 30)  # Max 30 seconds

    def _make_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retries."""
        url = f"{self.base_url}{path}"
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"[{self.service_name}] {method} {path} (attempt {attempt + 1})"
                )

                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()

                logger.debug(
                    f"[{self.service_name}] {method} {path} -> {response.status_code}"
                )
                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                logger.warning(
                    f"[{self.service_name}] {method} {path} failed: {e}"
                )

                if self._should_retry(e, attempt):
                    backoff = self._calculate_backoff(attempt)
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    break

        raise last_exception

    def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """Make request with circuit breaker protection."""
        try:
            return self.circuit_breaker.call(
                self._make_request, method, path, **kwargs
            )
        except CircuitBreakerOpen as e:
            logger.error(f"[{self.service_name}] Circuit breaker open: {e}")
            raise ServiceUnavailable(self.service_name, str(e))

    def get(self, path: str, **kwargs) -> httpx.Response:
        """GET request."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        """POST request."""
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        """PUT request."""
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE request."""
        return self.request("DELETE", path, **kwargs)

    def health_check(self) -> dict:
        """Check if service is healthy."""
        try:
            response = self.get("/api/health/live")
            return {
                "status": "healthy",
                "service": self.service_name,
                "circuit_breaker": self.circuit_breaker.get_state()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": self.service_name,
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.get_state()
            }

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ServiceUnavailable(Exception):
    """Raised when a service is unavailable."""
    def __init__(self, service_name: str, reason: str):
        self.service_name = service_name
        self.reason = reason
        super().__init__(f"Service '{service_name}' unavailable: {reason}")
