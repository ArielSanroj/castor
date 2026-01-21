"""
Local LLM provider implementation (Ollama, LM Studio, etc.).
"""
import json
import logging
from typing import Any, Dict, List, Optional

import requests

from .base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM implementation using Ollama-compatible API."""

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Local LLM provider."""
        from config import Config

        self.base_url = getattr(Config, 'LOCAL_LLM_URL', self.DEFAULT_BASE_URL)
        self.default_config = config or LLMConfig(
            model=getattr(Config, 'LOCAL_LLM_MODEL', self.DEFAULT_MODEL),
            temperature=0.7,
            timeout_seconds=120
        )
        self._check_availability()
        logger.info(f"LocalLLMProvider initialized with model: {self.default_config.model}")

    def _check_availability(self) -> None:
        """Check if local LLM server is running."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            self._available = response.status_code == 200
            if self._available:
                logger.info(f"Local LLM server available at {self.base_url}")
            else:
                logger.warning(f"Local LLM server returned status {response.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Local LLM server not available: {e}")
            self._available = False

    def complete(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> LLMResponse:
        """Generate a completion using local LLM."""
        if not self._available:
            raise RuntimeError("LocalLLMProvider is not available")

        cfg = config or self.default_config

        # Convert to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        payload = {
            "model": cfg.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": cfg.temperature
            }
        }

        if cfg.max_tokens:
            payload["options"]["num_predict"] = cfg.max_tokens

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=cfg.timeout_seconds
            )
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            return LLMResponse(
                content=content,
                model=cfg.model,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                },
                raw_response=data
            )
        except requests.RequestException as e:
            logger.error(f"Local LLM API error: {e}", exc_info=True)
            raise RuntimeError(f"Local LLM request failed: {e}")

    def complete_json(
        self,
        messages: List[LLMMessage],
        config: Optional[LLMConfig] = None
    ) -> Dict[str, Any]:
        """Generate a JSON completion using local LLM."""
        # Add JSON instruction to system message
        enhanced_messages = []
        has_system = False

        for msg in messages:
            if msg.role == "system":
                has_system = True
                enhanced_messages.append(LLMMessage(
                    role="system",
                    content=msg.content + "\n\nIMPORTANTE: Responde UNICAMENTE con JSON valido, sin texto adicional, sin explicaciones, sin markdown."
                ))
            else:
                enhanced_messages.append(msg)

        if not has_system:
            enhanced_messages.insert(0, LLMMessage(
                role="system",
                content="Responde UNICAMENTE con JSON valido, sin texto adicional, sin explicaciones, sin markdown."
            ))

        response = self.complete(enhanced_messages, config)

        # Clean response
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
            logger.error(f"Failed to parse JSON response from local LLM: {e}")
            logger.debug(f"Raw response: {response.content}")
            raise ValueError(f"Invalid JSON response from local LLM: {e}")

    def is_available(self) -> bool:
        """Check if local LLM is available."""
        self._check_availability()
        return self._available

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "local"

    def list_models(self) -> List[str]:
        """List available models in local LLM server."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except requests.RequestException as e:
            logger.warning(f"Failed to list local models: {e}")
            return []
