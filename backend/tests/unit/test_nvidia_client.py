"""Unit tests for NVIDIA AI Client, JSON parser, and FakeNVIDIAClient."""

import pytest

from app.integrations.nvidia_client import (
    AIClientError,
    AIClientParseError,
    AIClientTimeoutError,
    FakeNVIDIAClient,
    NVIDIAClient,
    parse_ai_json_content,
)
from app.schemas.ai_analysis import AIEnrichmentResult


def test_parse_ai_json_content_plain() -> None:
    raw = '{"summary": "Test summary", "confidence": 0.95}'
    data = parse_ai_json_content(raw)
    assert data["summary"] == "Test summary"
    assert data["confidence"] == 0.95


def test_parse_ai_json_content_markdown_fence() -> None:
    raw = """```json
    {
        "summary": "Impact detected",
        "observations": ["3.4g spike"],
        "confidence": 0.85
    }
    ```"""
    data = parse_ai_json_content(raw)
    assert data["summary"] == "Impact detected"
    assert data["observations"] == ["3.4g spike"]


def test_parse_ai_json_content_surrounding_prose() -> None:
    raw = """Here is the structured analysis requested:
    {
        "summary": "Elevated heart rate",
        "confidence": 0.78
    }
    Please let me know if you need more details."""
    data = parse_ai_json_content(raw)
    assert data["summary"] == "Elevated heart rate"
    assert data["confidence"] == 0.78


def test_parse_ai_json_content_invalid() -> None:
    raw = "Not a json payload at all"
    with pytest.raises(AIClientParseError):
        parse_ai_json_content(raw)


def test_parse_ai_json_content_array() -> None:
    raw = '["item1", "item2"]'
    with pytest.raises(AIClientParseError):
        parse_ai_json_content(raw)


@pytest.mark.asyncio
async def test_fake_nvidia_client_success() -> None:
    client = FakeNVIDIAClient()
    resp = await client.analyze(system_prompt="sys", user_prompt="user")

    assert client.call_count == 1
    assert client.last_system_prompt == "sys"
    assert client.last_user_prompt == "user"
    assert isinstance(resp.result, AIEnrichmentResult)
    assert resp.result.confidence > 0.0
    assert resp.model_name == "meta/llama-3.1-8b-instruct"
    assert resp.latency_ms > 0


@pytest.mark.asyncio
async def test_fake_nvidia_client_timeout() -> None:
    client = FakeNVIDIAClient(simulate_timeout=True)
    with pytest.raises(AIClientTimeoutError):
        await client.analyze("sys", "user")
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_fake_nvidia_client_http_error() -> None:
    client = FakeNVIDIAClient(simulate_http_status=429)
    with pytest.raises(AIClientError) as exc_info:
        await client.analyze("sys", "user")
    assert "429" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fake_nvidia_client_invalid_json() -> None:
    client = FakeNVIDIAClient(simulate_invalid_json=True)
    with pytest.raises(AIClientParseError):
        await client.analyze("sys", "user")


@pytest.mark.asyncio
async def test_nvidia_client_missing_api_key() -> None:
    client = NVIDIAClient(api_key="")
    with pytest.raises(AIClientError) as exc_info:
        await client.analyze("sys", "user")
    assert "NVIDIA_API_KEY is not configured" in str(exc_info.value)
