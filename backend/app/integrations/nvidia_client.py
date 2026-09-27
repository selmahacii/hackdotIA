"""NVIDIA AI integration client and mock client for tests."""

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.schemas.ai_analysis import AIEnrichmentResult

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Base exception for AI integration errors."""

    pass


class AIClientTimeoutError(AIClientError):
    """Raised when an AI integration request times out."""

    pass


class AIClientParseError(AIClientError):
    """Raised when the AI response cannot be parsed into the expected JSON/Pydantic schema."""

    pass


@dataclass
class AIResponse:
    result: AIEnrichmentResult
    raw_response: dict[str, Any]
    latency_ms: int
    model_name: str


def parse_ai_json_content(content: str) -> dict[str, Any]:
    """Extract and parse JSON object from LLM response text.

    Handles optional markdown code fences like ```json ... ``` or ``` ... ```.
    """
    cleaned = content.strip()
    # Strip markdown code block fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    else:
        # If no fence, find the first '{' and last '}'
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise AIClientParseError(f"Expected JSON object, got {type(data).__name__}")
        return data
    except json.JSONDecodeError as exc:
        raise AIClientParseError(f"Failed to parse JSON from AI response: {exc}") from exc


class BaseAIClient(ABC):
    """Abstract interface for AI enrichment clients."""

    @abstractmethod
    async def analyze(self, system_prompt: str, user_prompt: str) -> AIResponse:
        """Execute prompt against AI provider and return structured AIResponse."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, int, str]:
        """Execute conversational chat and return (reply_text, latency_ms, model_name)."""
        pass


class NVIDIAClient(BaseAIClient):
    """Production client for NVIDIA Cloud Functions / OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.NVIDIA_API_KEY
        self.base_url = (base_url if base_url is not None else settings.NVIDIA_BASE_URL).rstrip("/")
        self.model = model if model is not None else settings.NVIDIA_MODEL
        self.timeout = timeout if timeout is not None else float(settings.NVIDIA_TIMEOUT_SECONDS)
        self.max_tokens = max_tokens if max_tokens is not None else settings.NVIDIA_MAX_TOKENS
        self.temperature = temperature if temperature is not None else settings.NVIDIA_TEMPERATURE

    async def analyze(self, system_prompt: str, user_prompt: str) -> AIResponse:
        if not self.api_key:
            raise AIClientError("NVIDIA_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                raw_json = response.json()
        except httpx.TimeoutException as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning("NVIDIA API request timed out after %d ms", elapsed_ms)
            raise AIClientTimeoutError(f"NVIDIA API timed out after {self.timeout}s") from exc
        except httpx.HTTPStatusError as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "NVIDIA API returned HTTP error %d: %s", exc.response.status_code, exc.response.text
            )
            raise AIClientError(f"NVIDIA API error HTTP {exc.response.status_code}") from exc
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Unexpected error contacting NVIDIA API: %s", exc)
            raise AIClientError(f"NVIDIA API network/client error: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract content
        try:
            choices = raw_json.get("choices", [])
            if not choices:
                raise AIClientParseError("NVIDIA API returned empty choices")
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise AIClientParseError("NVIDIA API returned empty message content")
        except (AttributeError, KeyError, IndexError) as exc:
            raise AIClientParseError(f"Malformed NVIDIA API response structure: {exc}") from exc

        parsed_data = parse_ai_json_content(content)
        try:
            result = AIEnrichmentResult.model_validate(parsed_data)
        except Exception as exc:
            logger.warning("Failed to validate AIEnrichmentResult schema: %s", exc)
            raise AIClientParseError(f"Invalid AIEnrichmentResult schema: {exc}") from exc

        return AIResponse(
            result=result,
            raw_response=raw_json,
            latency_ms=elapsed_ms,
            model_name=self.model,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, int, str]:
        if not self.api_key:
            raise AIClientError("NVIDIA_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": False,
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                raw_json = response.json()
        except httpx.TimeoutException as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            raise AIClientTimeoutError(f"NVIDIA API timed out after {self.timeout}s") from exc
        except Exception as exc:
            raise AIClientError(f"NVIDIA API chat error: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        try:
            choices = raw_json.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
        except Exception as exc:
            raise AIClientParseError(f"Malformed response: {exc}") from exc

        return content, elapsed_ms, self.model


class FakeNVIDIAClient(BaseAIClient):
    """Mock client for testing without external NVIDIA network dependencies."""

    def __init__(
        self,
        canned_result: AIEnrichmentResult | None = None,
        simulate_timeout: bool = False,
        simulate_http_status: int | None = None,
        simulate_invalid_json: bool = False,
        simulate_exception: Exception | None = None,
        model_name: str = "meta/llama-3.1-8b-instruct",
        latency_ms: int = 42,
    ) -> None:
        self.canned_result = canned_result or AIEnrichmentResult(
            summary="Kinematic anomaly detected: sudden deceleration spike followed by stationary state.",
            observations=[
                "Accelerometer magnitude peaked at 3.2g",
                "Stationary state observed for >3s",
            ],
            context="Consistent with slip or fall event in indoor environment",
            confidence=0.88,
            data_quality="OPTIMAL",
            possible_factors=["Sudden postural change", "Physical impact"],
            recommended_checks=["Verify resident consciousness and mobility", "Inspect room floor"],
            limitations=[
                "Inference based solely on wrist/wearable kinematics without visual confirmation"
            ],
        )
        self.simulate_timeout = simulate_timeout
        self.simulate_http_status = simulate_http_status
        self.simulate_invalid_json = simulate_invalid_json
        self.simulate_exception = simulate_exception
        self.model_name = model_name
        self.latency_ms = latency_ms

        self.call_count: int = 0
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    async def analyze(self, system_prompt: str, user_prompt: str) -> AIResponse:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        if self.simulate_timeout:
            raise AIClientTimeoutError("Fake timeout simulated")
        if self.simulate_http_status is not None:
            raise AIClientError(f"Fake NVIDIA API error HTTP {self.simulate_http_status}")
        if self.simulate_exception is not None:
            raise self.simulate_exception
        if self.simulate_invalid_json:
            raise AIClientParseError("Fake invalid JSON payload")

        return AIResponse(
            result=self.canned_result,
            raw_response={"mock": True, "call_count": self.call_count},
            latency_ms=self.latency_ms,
            model_name=self.model_name,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, int, str]:
        self.call_count += 1
        return (
            "D'après les relevés des capteurs, la situation est sous contrôle. Les paramètres vitaux sont stables.",
            self.latency_ms,
            self.model_name,
        )

