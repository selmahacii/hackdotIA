"""Groq Cloud AI integration client and mock client for tests."""

import logging
import time

import httpx

from app.config import settings
from app.integrations.nvidia_client import (
    AIClientError,
    AIClientParseError,
    AIClientTimeoutError,
    AIResponse,
    BaseAIClient,
    parse_ai_json_content,
)
from app.schemas.ai_analysis import AIEnrichmentResult

logger = logging.getLogger(__name__)


class GroqClient(BaseAIClient):
    """Production client for Groq Cloud OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.base_url = (base_url if base_url is not None else settings.GROQ_BASE_URL).rstrip("/")
        self.model = model if model is not None else settings.GROQ_MODEL
        self.timeout = timeout if timeout is not None else float(settings.GROQ_TIMEOUT_SECONDS)
        self.max_tokens = max_tokens if max_tokens is not None else settings.GROQ_MAX_TOKENS
        self.temperature = temperature if temperature is not None else settings.GROQ_TEMPERATURE

    async def analyze(self, system_prompt: str, user_prompt: str) -> AIResponse:
        if not self.api_key:
            raise AIClientError("GROQ_API_KEY is not configured")

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
            logger.warning("Groq API request timed out after %d ms", elapsed_ms)
            raise AIClientTimeoutError(f"Groq API timed out after {self.timeout}s") from exc
        except httpx.HTTPStatusError as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "Groq API returned HTTP error %d: %s", exc.response.status_code, exc.response.text
            )
            raise AIClientError(f"Groq API error HTTP {exc.response.status_code}") from exc
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Unexpected error contacting Groq API: %s", exc)
            raise AIClientError(f"Groq API network/client error: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Extract content
        try:
            choices = raw_json.get("choices", [])
            if not choices:
                raise AIClientParseError("Groq API returned empty choices")
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise AIClientParseError("Groq API returned empty message content")
        except (AttributeError, KeyError, IndexError) as exc:
            raise AIClientParseError(f"Malformed Groq API response structure: {exc}") from exc

        parsed_data = parse_ai_json_content(content)
        try:
            result = AIEnrichmentResult.model_validate(parsed_data)
        except Exception as exc:
            logger.warning("Failed to validate AIEnrichmentResult schema from Groq: %s", exc)
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
        """Execute a conversational completion call to Groq Cloud."""
        if not self.api_key:
            raise AIClientError("GROQ_API_KEY is not configured")

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
            "max_tokens": max_tokens if max_tokens is not None else 1024,
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
            logger.warning("Groq API chat request timed out after %d ms", elapsed_ms)
            raise AIClientTimeoutError(f"Groq API timed out after {self.timeout}s") from exc
        except httpx.HTTPStatusError as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "Groq API chat returned HTTP error %d: %s", exc.response.status_code, exc.response.text
            )
            raise AIClientError(f"Groq API error HTTP {exc.response.status_code}") from exc
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Unexpected error contacting Groq API chat: %s", exc)
            raise AIClientError(f"Groq API network/client error: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        try:
            choices = raw_json.get("choices", [])
            if not choices:
                raise AIClientParseError("Groq API returned empty choices")
            content = choices[0].get("message", {}).get("content", "")
        except (AttributeError, KeyError, IndexError) as exc:
            raise AIClientParseError(f"Malformed Groq API response: {exc}") from exc

        return content, elapsed_ms, self.model


class FakeGroqClient(BaseAIClient):
    """Mock client for testing without external Groq network dependencies."""

    def __init__(
        self,
        canned_result: AIEnrichmentResult | None = None,
        simulate_timeout: bool = False,
        simulate_http_status: int | None = None,
        simulate_invalid_json: bool = False,
        simulate_exception: Exception | None = None,
        model_name: str = "openai/gpt-oss-20b",
        latency_ms: int = 35,
    ) -> None:
        self.canned_result = canned_result or AIEnrichmentResult(
            summary="Kinematic anomaly detected: sudden deceleration spike followed by stationary state.",
            observations=[
                "Accelerometer magnitude peaked at 3.42g",
                "Stationary state observed for >3s",
            ],
            context="Compatible with postural impact sequence requiring caregiver confirmation",
            confidence=0.89,
            data_quality="OPTIMAL",
            possible_factors=["Rapid posture transition", "Impact pattern"],
            recommended_checks=["Verify resident mobility and consciousness", "Inspect room floor"],
            limitations=[
                "Kinematic inference without direct visual telemetry; human verification required"
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
            raise AIClientTimeoutError("Fake Groq timeout simulated")
        if self.simulate_http_status is not None:
            raise AIClientError(f"Fake Groq API error HTTP {self.simulate_http_status}")
        if self.simulate_exception is not None:
            raise self.simulate_exception
        if self.simulate_invalid_json:
            raise AIClientParseError("Fake invalid JSON payload from Groq")

        return AIResponse(
            result=self.canned_result,
            raw_response={"mock": True, "provider": "groq", "call_count": self.call_count},
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
            "D'après les relevés des capteurs (MAX30102 et MPU6050), les constantes vitales montrent une stabilité globale. "
            "Les alertes récentes correspondent à des variations physiologiques ou cinématiques nécessitant une simple vérification de confort par l'équipe soignante.",
            self.latency_ms,
            self.model_name,
        )

