"""
Abstract base class for LLM providers.
Implements Fowler's pattern for reducing vendor lock-in.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"


@dataclass
class LLMMessage:
    """Unified message format for LLM interactions."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Unified response format from LLM providers."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout_seconds: int = 60
    json_mode: bool = False


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM implementations must implement these methods to ensure
    interchangeability between providers (OpenAI, Claude, Local).
    """

    @abstractmethod
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM provider with configuration."""
        pass

    @abstractmethod
    def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of messages in the conversation
            config: Optional config override for this request

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
    def complete_json(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """
        Generate a JSON completion from the LLM.

        Args:
            messages: List of messages in the conversation
            config: Optional config override for this request

        Returns:
            Parsed JSON dictionary
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is properly configured and available."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for logging/identification."""
        pass

    def chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        Simple chat interface for quick interactions.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt

        Returns:
            The assistant's response
        """
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=user_message))

        response = self.complete(messages)
        return response.content
