"""
Claude (Anthropic) LLM provider implementation.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude implementation of BaseLLMProvider."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Claude provider."""
        try:
            import anthropic
            from config import Config

            api_key = getattr(Config, 'ANTHROPIC_API_KEY', None)
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured")

            self.client = anthropic.Anthropic(api_key=api_key)
            self.default_config = config or LLMConfig(
                model=getattr(Config, 'CLAUDE_MODEL', 'claude-3-5-sonnet-20241022'),
                temperature=0.7,
                max_tokens=4096,
                timeout_seconds=60
            )
            self._available = True
            logger.info(f"ClaudeProvider initialized with model: {self.default_config.model}")

        except ImportError:
            logger.warning("anthropic package not installed. ClaudeProvider unavailable.")
            self._available = False
            self.client = None
            self.default_config = config or LLMConfig(model="claude-3-5-sonnet-20241022")
        except ValueError as e:
            logger.warning(f"ClaudeProvider configuration error: {e}")
            self._available = False
            self.client = None
            self.default_config = config or LLMConfig(model="claude-3-5-sonnet-20241022")

    def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a completion using Claude."""
        if not self._available or not self.client:
            raise RuntimeError("ClaudeProvider is not available")

        cfg = config or self.default_config

        # Claude uses a separate system parameter
        system_content = None
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        kwargs = {
            "model": cfg.model,
            "messages": claude_messages,
            "max_tokens": cfg.max_tokens or 4096,
        }

        if system_content:
            kwargs["system"] = system_content

        # Claude doesn't have temperature in the same range, adjust if needed
        if cfg.temperature is not None:
            kwargs["temperature"] = min(cfg.temperature, 1.0)

        try:
            response = self.client.messages.create(**kwargs)

            content = ""
            if response.content:
                content = response.content[0].text

            return LLMResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if response.usage else None,
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise

    def complete_json(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """Generate a JSON completion using Claude."""
        # Claude doesn't have a native JSON mode, so we modify the prompt
        enhanced_messages = []
        for msg in messages:
            if msg.role == "system":
                enhanced_messages.append(LLMMessage(
                    role="system",
                    content=msg.content + "\n\nIMPORTANTE: Responde SOLO con JSON valido, sin texto adicional."
                ))
            else:
                enhanced_messages.append(msg)

        if not any(m.role == "system" for m in enhanced_messages):
            enhanced_messages.insert(0, LLMMessage(
                role="system",
                content="Responde SOLO con JSON valido, sin texto adicional."
            ))

        response = self.complete(enhanced_messages, config)

        # Try to extract JSON from response
        content = response.content.strip()

        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Claude: {e}")
            logger.debug(f"Raw response: {response.content}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")

    def is_available(self) -> bool:
        """Check if Claude is configured and available."""
        return self._available

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "claude"
