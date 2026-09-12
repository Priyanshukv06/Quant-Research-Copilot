"""LLM Provider — thin wrapper around the multi-provider router.

The public API (generate, generate_json) stays identical so no agent code changes.
Internally, all calls are routed through RoutedLLMBackend which handles:
  - 5 providers (Gemini, Groq, Mistral, NVIDIA, OpenRouter)
  - Multiple API keys per provider with round-robin + failover rotation
  - Priority-ordered fallback chain (strongest models first)
  - Provider cooldowns on rate-limit / auth / server errors
"""

import json
import logging
import re

from config import settings
from llm.router import RoutedLLMBackend

logger = logging.getLogger(__name__)

# Regex for cleaning <think> blocks from JSON responses
_THINK_BLOCK = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.I)


class LLMProvider:
    """Unified LLM provider backed by a multi-provider router."""

    def __init__(self):
        self.router = RoutedLLMBackend()
        configured = self.router.configured_providers()
        logger.info(
            "LLM Router initialized with %d providers: %s",
            len(configured), ", ".join(configured) if configured else "(none)"
        )
        available = self.router.available_models()
        if available:
            logger.info(
                "Model chain (%d models): %s",
                len(available),
                " → ".join(f"{m.name}" for m in self.router.chain())
            )

    async def generate(
        self,
        messages: list[dict],
        temperature: float = settings.TEMPERATURE,
        max_tokens: int = settings.MAX_TOKENS,
        enable_thinking: bool = False,  # kept for API compat, now a no-op
    ) -> str:
        """Generate a response using the LLM router with automatic fallback.

        The `enable_thinking` parameter is retained for backward compatibility
        but is now a no-op — the router handles <think> block stripping
        automatically for any reasoning model.
        """
        return await self.router.route(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_json(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = settings.MAX_TOKENS,
    ) -> dict:
        """Generate a response and parse it as JSON.

        Uses low temperature for deterministic structured output.
        Handles cases where the LLM wraps JSON in markdown code blocks.
        """
        raw = await self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Clean up common LLM artifacts around JSON
        cleaned = raw.strip()

        # Handle <think>...</think> blocks from reasoning models
        if "<think>" in cleaned:
            cleaned = _THINK_BLOCK.sub("", cleaned).strip()
            # Handle orphan <think> (unterminated)
            if "<think>" in cleaned.lower():
                think_start = cleaned.lower().find("<think>")
                cleaned = cleaned[:think_start].strip()

        # Remove markdown code fences
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {cleaned[:200]}...")
            # Try to extract JSON from the response
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            # Try array extraction for screener slot-fill responses
            start = cleaned.find("[")
            end = cleaned.rfind("]") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"LLM did not return valid JSON: {e}") from e


# Singleton instance
llm = LLMProvider()
