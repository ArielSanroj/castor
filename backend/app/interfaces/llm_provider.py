"""
LLM Provider Interface.
Abstracts LLM implementations (OpenAI, Claude, Local) for vendor independence.

SOLID Principles:
- ISP: Segregated interface for LLM operations only
- DIP: High-level modules depend on this abstraction, not concrete implementations
- OCP: New LLM providers can be added without modifying existing code
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"


@dataclass
class LLMResponse:
    """Standardized LLM response across all providers."""
    content: str
    model: str
    provider: LLMProvider
    tokens_used: int = 0
    finish_reason: str = "stop"
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "tokens_used": self.tokens_used,
            "finish_reason": self.finish_reason
        }


class ILLMProvider(ABC):
    """
    Interface for LLM providers.

    Implementations:
    - OpenAIProvider (GPT-4o, GPT-4-turbo)
    - ClaudeProvider (Claude 3.5 Sonnet)
    - LocalProvider (Ollama/Llama)

    Usage:
        provider: ILLMProvider = OpenAIProvider()
        response = provider.generate("Analyze this text")
    """

    @property
    @abstractmethod
    def provider_name(self) -> LLMProvider:
        """Get the provider type."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the current model name."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> LLMResponse:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            temperature: Creativity (0.0-1.0)
            max_tokens: Maximum response length

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output.

        Args:
            prompt: User prompt
            schema: Expected JSON schema/structure
            system_prompt: Optional system instructions

        Returns:
            Parsed JSON dictionary
        """
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate text embedding vector.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is available and configured."""
        return True

    def get_context_window(self) -> int:
        """Get maximum context window size in tokens."""
        return 4096  # Default, override in implementations
