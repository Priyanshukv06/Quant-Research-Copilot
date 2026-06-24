"""
LLM Provider abstraction layer.

Primary: NVIDIA NIM (DiffusionGemma 26B-A4B)
Fallback: Ollama (local models) or other NVIDIA NIM models

Uses the OpenAI-compatible API format that NVIDIA NIM supports.
"""
import json
import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Unified LLM provider that tries NVIDIA NIM first, then falls back to Ollama.
    Uses raw HTTP requests for maximum compatibility with NVIDIA NIM's API.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=120.0)
        self.primary_model = settings.NVIDIA_MODEL
        self.fallback_model = settings.GROQ_MODEL

    async def close(self):
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def _call_nvidia_nim(
        self,
        messages: list[dict],
        temperature: float = settings.TEMPERATURE,
        max_tokens: int = settings.MAX_TOKENS,
        model: Optional[str] = None,
        enable_thinking: bool = False,
    ) -> str:
        """Call NVIDIA NIM API (OpenAI-compatible format)."""
        payload = {
            "model": model or self.primary_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": settings.TOP_P,
            "stream": False,
        }

        # Enable thinking mode for DiffusionGemma
        if enable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": True}

        headers = {
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        response = await self._client.post(
            f"{settings.NVIDIA_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        logger.info(
            f"NVIDIA NIM response: model={model or self.primary_model}, "
            f"tokens_used={data.get('usage', {}).get('total_tokens', '?')}"
        )
        return content

    async def _call_groq(
        self,
        messages: list[dict],
        temperature: float = settings.TEMPERATURE,
        max_tokens: int = settings.MAX_TOKENS,
        model: Optional[str] = None,
    ) -> str:
        """Call Groq Cloud API (OpenAI-compatible format)."""
        payload = {
            "model": model or self.fallback_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        response = await self._client.post(
            f"{settings.GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        logger.info(f"Groq response: model={model or self.fallback_model}")
        return content

    async def generate(
        self,
        messages: list[dict],
        temperature: float = settings.TEMPERATURE,
        max_tokens: int = settings.MAX_TOKENS,
        enable_thinking: bool = False,
    ) -> str:
        """
        Generate a response using the LLM with automatic fallback.
        
        Tries NVIDIA NIM first, falls back to Groq on failure.
        """
        # Try NVIDIA NIM first
        try:
            return await self._call_nvidia_nim(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
            )
        except Exception as e:
            logger.warning(f"NVIDIA NIM failed: {e}. Falling back to Groq.")

        # Fallback to Groq
        try:
            return await self._call_groq(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"Groq also failed: {e}")
            raise RuntimeError(
                "All LLM providers failed. Ensure NVIDIA NIM or GROQ API keys are valid."
            ) from e

    async def generate_json(
        self,
        messages: list[dict],
        temperature: float = 0.1,  # Low temp for structured output
        max_tokens: int = settings.MAX_TOKENS,
    ) -> dict:
        """
        Generate a response and parse it as JSON.
        
        Uses low temperature for deterministic structured output.
        Handles cases where the LLM wraps JSON in markdown code blocks.
        """
        raw = await self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=False,  # Thinking mode can pollute JSON
        )

        # Clean up common LLM artifacts around JSON
        cleaned = raw.strip()

        # Handle <think>...</think> blocks from reasoning models
        if "<think>" in cleaned:
            think_end = cleaned.rfind("</think>")
            if think_end != -1:
                cleaned = cleaned[think_end + len("</think>"):].strip()

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
            raise ValueError(f"LLM did not return valid JSON: {e}") from e


# Singleton instance
llm = LLMProvider()
