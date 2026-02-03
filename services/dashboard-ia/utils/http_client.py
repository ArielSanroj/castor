"""
HTTP Client with retry, timeout, and circuit breaker.
Base class for inter-service communication.
"""
import httpx
import logging
from typing import Optional
import time

from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base HTTP client for inter-service communication."""

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
            recovery_timeout=circuit_reset_timeout,
            expected_exception=Exception  # Catches all exceptions
        )

    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        if isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout)):
            return True
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code >= 500
        return False

    def _calculate_backoff(self, attempt: int) -> float:
        return min(2 ** attempt, 30)

    def _make_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                if self._should_retry(e, attempt):
                    time.sleep(self._calculate_backoff(attempt))
                else:
                    break

        raise last_exception

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            return self.circuit_breaker.call(self._make_request, method, path, **kwargs)
        except CircuitBreakerOpen as e:
            raise ServiceUnavailable(self.service_name, str(e))

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def close(self):
        self.client.close()


class ServiceUnavailable(Exception):
    def __init__(self, service_name: str, reason: str):
        self.service_name = service_name
        self.reason = reason
        super().__init__(f"Service '{service_name}' unavailable: {reason}")
