"""
OpenAI LLM provider implementation.
"""
import json
import logging
from typing import Any, Callable, Dict, List, Optional

import openai

from config import Config
from utils.circuit_breaker import (
    get_openai_circuit_breaker,
    exponential_backoff,
    CircuitBreakerOpenError
)
from .base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT implementation of BaseLLMProvider."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize OpenAI provider."""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            timeout=Config.OPENAI_TIMEOUT_SECONDS
        )
        self.default_config = config or LLMConfig(
            model=Config.OPENAI_MODEL,
            temperature=0.7,
            timeout_seconds=Config.OPENAI_TIMEOUT_SECONDS
        )
        self._circuit_breaker = get_openai_circuit_breaker()
        logger.info(f"OpenAIProvider initialized with model: {self.default_config.model}")

    @exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exceptions=(openai.APIError, openai.APITimeoutError, openai.RateLimitError)
    )
    def _call_api(self, call_func: Callable) -> Any:
        """Execute API call with circuit breaker and retry logic."""
        try:
            return self._circuit_breaker.call(call_func)
        except CircuitBreakerOpenError:
            logger.error("OpenAI circuit breaker is OPEN, rejecting request")
            raise
        except (openai.APIError, openai.APITimeoutError, openai.RateLimitError) as e:
            logger.warning(f"OpenAI API error: {e}")
            raise

    def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a completion using OpenAI."""
        cfg = config or self.default_config

        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        def _make_call():
            kwargs = {
                "model": cfg.model,
                "messages": openai_messages,
                "temperature": cfg.temperature,
            }
            if cfg.max_tokens:
                kwargs["max_tokens"] = cfg.max_tokens
            if cfg.json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            return self.client.chat.completions.create(**kwargs)

        response = self._call_api(_make_call)
        choice = response.choices[0]

        return LLMResponse(
            content=choice.message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None,
            raw_response=response
        )

    def complete_json(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """Generate a JSON completion using OpenAI."""
        cfg = config or self.default_config
        json_config = LLMConfig(
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            timeout_seconds=cfg.timeout_seconds,
            json_mode=True
        )

        response = self.complete(messages, json_config)

        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")

    def is_available(self) -> bool:
        """Check if OpenAI is configured and available."""
        return bool(Config.OPENAI_API_KEY)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openai"
