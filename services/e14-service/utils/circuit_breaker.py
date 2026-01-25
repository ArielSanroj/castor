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
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit Breaker implementation."""

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
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if self.last_failure_time and \
                   time.time() - self.last_failure_time >= self.reset_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            return True

    def _on_success(self):
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0

    def _on_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitState.HALF_OPEN or \
               self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self._should_allow_request():
            raise CircuitBreakerOpen(f"Circuit breaker is OPEN")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions:
            self._on_failure()
            raise

    def get_state(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold
        }


class CircuitBreakerOpen(Exception):
    pass


def circuit_breaker(failure_threshold: int = 5, reset_timeout: int = 60, expected_exceptions: tuple = (Exception,)):
    cb = CircuitBreaker(failure_threshold, reset_timeout, expected_exceptions)
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        wrapper.circuit_breaker = cb
        return wrapper
    return decorator
