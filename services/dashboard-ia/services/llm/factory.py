"""
LLM Provider Factory.
Implements strategy pattern for switching between LLM providers.
"""
import logging
from typing import Dict, Optional, Type

from .base import BaseLLMProvider, LLMConfig, LLMProvider

logger = logging.getLogger(__name__)

# Registry of provider implementations
_PROVIDER_REGISTRY: Dict[LLMProvider, Type[BaseLLMProvider]] = {}


def register_provider(provider_type: LLMProvider):
    """Decorator to register a provider implementation."""
    def decorator(cls: Type[BaseLLMProvider]):
        _PROVIDER_REGISTRY[provider_type] = cls
        return cls
    return decorator


# Register providers
def _register_providers():
    """Register all available providers."""
    from .openai_provider import OpenAIProvider
    from .claude_provider import ClaudeProvider
    from .local_provider import LocalLLMProvider

    _PROVIDER_REGISTRY[LLMProvider.OPENAI] = OpenAIProvider
    _PROVIDER_REGISTRY[LLMProvider.CLAUDE] = ClaudeProvider
    _PROVIDER_REGISTRY[LLMProvider.LOCAL] = LocalLLMProvider


class LLMFactory:
    """
    Factory for creating and managing LLM providers.

    Usage:
        # Get default provider (from config)
        llm = LLMFactory.get_provider()

        # Get specific provider
        llm = LLMFactory.get_provider(LLMProvider.CLAUDE)

        # Use the provider
        response = llm.chat("Hola, como estas?")
    """

    _instances: Dict[LLMProvider, BaseLLMProvider] = {}
    _default_provider: Optional[LLMProvider] = None

    @classmethod
    def get_provider(
        cls,
        provider_type: Optional[LLMProvider] = None,
        config: Optional[LLMConfig] = None,
        force_new: bool = False
    ) -> BaseLLMProvider:
        """
        Get or create an LLM provider instance.

        Args:
            provider_type: The provider to use (defaults to configured provider)
            config: Optional configuration override
            force_new: If True, create a new instance even if one exists

        Returns:
            BaseLLMProvider instance
        """
        # Ensure providers are registered
        if not _PROVIDER_REGISTRY:
            _register_providers()

        # Determine which provider to use
        if provider_type is None:
            provider_type = cls._get_default_provider()

        # Return cached instance if available
        if not force_new and provider_type in cls._instances:
            return cls._instances[provider_type]

        # Create new instance
        provider_class = _PROVIDER_REGISTRY.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_type}")

        try:
            instance = provider_class(config)
            cls._instances[provider_type] = instance
            logger.info(f"Created LLM provider: {provider_type.value}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create {provider_type.value} provider: {e}")
            raise

    @classmethod
    def _get_default_provider(cls) -> LLMProvider:
        """Get the default provider from configuration."""
        if cls._default_provider:
            return cls._default_provider

        from config import Config
        provider_name = getattr(Config, 'LLM_PROVIDER', 'openai').lower()

        provider_map = {
            'openai': LLMProvider.OPENAI,
            'claude': LLMProvider.CLAUDE,
            'anthropic': LLMProvider.CLAUDE,
            'local': LLMProvider.LOCAL,
            'ollama': LLMProvider.LOCAL,
        }

        cls._default_provider = provider_map.get(provider_name, LLMProvider.OPENAI)
        return cls._default_provider

    @classmethod
    def set_default_provider(cls, provider_type: LLMProvider) -> None:
        """Set the default provider."""
        cls._default_provider = provider_type
        logger.info(f"Default LLM provider set to: {provider_type.value}")

    @classmethod
    def get_available_providers(cls) -> Dict[LLMProvider, bool]:
        """Check which providers are available."""
        if not _PROVIDER_REGISTRY:
            _register_providers()

        available = {}
        for provider_type, provider_class in _PROVIDER_REGISTRY.items():
            try:
                instance = provider_class()
                available[provider_type] = instance.is_available()
            except Exception:
                available[provider_type] = False

        return available

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached provider instances."""
        cls._instances.clear()
        logger.info("Cleared all LLM provider instances")


# Convenience function
def get_llm(
    provider: Optional[LLMProvider] = None,
    config: Optional[LLMConfig] = None
) -> BaseLLMProvider:
    """
    Get an LLM provider instance.

    This is the main entry point for using LLM providers.

    Examples:
        # Use default provider
        llm = get_llm()
        response = llm.chat("Hola!")

        # Use specific provider
        llm = get_llm(LLMProvider.CLAUDE)

        # With custom config
        config = LLMConfig(model="gpt-4o", temperature=0.5)
        llm = get_llm(LLMProvider.OPENAI, config)
    """
    return LLMFactory.get_provider(provider, config)
