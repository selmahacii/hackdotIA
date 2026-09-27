"""Unit tests for Groq AI Client, FakeGroqClient, and AI service integration."""

import pytest

from app.integrations.groq_client import FakeGroqClient, GroqClient
from app.integrations.nvidia_client import (
    AIClientError,
    AIClientParseError,
    AIClientTimeoutError,
)
from app.schemas.ai_analysis import AIEnrichmentResult


def test_groq_client_missing_api_key() -> None:
    client = GroqClient(api_key="")
    with pytest.raises(AIClientError) as exc_info:
        import asyncio

        asyncio.run(client.analyze("sys", "user"))
    assert "GROQ_API_KEY is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fake_groq_client_success() -> None:
    client = FakeGroqClient()
    resp = await client.analyze(system_prompt="sys prompt", user_prompt="user prompt")

    assert client.call_count == 1
    assert client.last_system_prompt == "sys prompt"
    assert client.last_user_prompt == "user prompt"
    assert isinstance(resp.result, AIEnrichmentResult)
    assert resp.result.confidence > 0.0
    assert resp.model_name == "openai/gpt-oss-20b"
    assert resp.latency_ms > 0
    assert "Kinematic anomaly" in resp.result.summary


@pytest.mark.asyncio
async def test_fake_groq_client_timeout() -> None:
    client = FakeGroqClient(simulate_timeout=True)
    with pytest.raises(AIClientTimeoutError):
        await client.analyze("sys", "user")
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_fake_groq_client_http_error() -> None:
    client = FakeGroqClient(simulate_http_status=429)
    with pytest.raises(AIClientError) as exc_info:
        await client.analyze("sys", "user")
    assert "429" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fake_groq_client_invalid_json() -> None:
    client = FakeGroqClient(simulate_invalid_json=True)
    with pytest.raises(AIClientParseError):
        await client.analyze("sys", "user")
