"""
Circuit Breaker pattern implementation.
Prevents cascade failures when external services are down.
"""
import time
import logging
from functools import wraps
from enum import Enum
from typing import Callable, Optional, Any
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, reject requests immediately (fail fast)
    - HALF_OPEN: Testing recovery, allow one request through

    Usage:
        @circuit_breaker(failure_threshold=5, reset_timeout=60)
        def call_external_service():
            return requests.get("http://external-service/api")
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.expected_exceptions = expected_exceptions

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.lock = Lock()

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit state."""
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if reset timeout has passed
                if self.last_failure_time and \
                   time.time() - self.last_failure_time >= self.reset_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                return True

            return False

    def _on_success(self):
        """Handle successful request."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def _on_failure(self):
        """Handle failed request."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker OPEN - service still failing")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker OPEN - {self.failure_count} failures"
                )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if not self._should_allow_request():
            raise CircuitBreakerOpen(
                f"Circuit breaker is OPEN. Retry after {self.reset_timeout}s"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise

    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout
        }


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


def circuit_breaker(
    failure_threshold: int = 5,
    reset_timeout: int = 60,
    expected_exceptions: tuple = (Exception,)
):
    """
    Decorator for circuit breaker pattern.

    Args:
        failure_threshold: Number of failures before opening circuit
        reset_timeout: Seconds to wait before trying again
        expected_exceptions: Exceptions that count as failures

    Usage:
        @circuit_breaker(failure_threshold=5, reset_timeout=60)
        def call_service():
            return requests.get("http://service/api")
    """
    cb = CircuitBreaker(
        failure_threshold=failure_threshold,
        reset_timeout=reset_timeout,
        expected_exceptions=expected_exceptions
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)

        # Attach circuit breaker instance for inspection
        wrapper.circuit_breaker = cb
        return wrapper

    return decorator
