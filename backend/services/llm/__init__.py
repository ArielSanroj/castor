"""
LLM Abstraction Layer.

Provides a unified interface for multiple LLM providers (OpenAI, Claude, Local).
Implements Fowler's pattern for reducing vendor lock-in.

Usage:
    from services.llm import get_llm, LLMProvider

    # Use default provider (from config)
    llm = get_llm()
    response = llm.chat("Hola, como estas?")

    # Use specific provider
    llm = get_llm(LLMProvider.CLAUDE)

    # JSON completion
    messages = [
        LLMMessage(role="system", content="Responde en JSON"),
        LLMMessage(role="user", content="Dame 3 colores")
    ]
    data = llm.complete_json(messages)
"""

from .base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)
from .factory import (
    LLMFactory,
    get_llm,
)
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .local_provider import LocalLLMProvider

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMConfig",
    "LLMMessage",
    "LLMProvider",
    "LLMResponse",
    # Factory
    "LLMFactory",
    "get_llm",
    # Providers
    "OpenAIProvider",
    "ClaudeProvider",
    "LocalLLMProvider",
]
