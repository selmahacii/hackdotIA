"""External integration clients for Smart Elderly Monitoring System."""

from app.integrations.groq_client import FakeGroqClient, GroqClient
from app.integrations.nvidia_client import (
    AIClientError,
    AIClientParseError,
    AIClientTimeoutError,
    AIResponse,
    BaseAIClient,
    FakeNVIDIAClient,
    NVIDIAClient,
    parse_ai_json_content,
)

__all__ = [
    "AIClientError",
    "AIClientParseError",
    "AIClientTimeoutError",
    "AIResponse",
    "BaseAIClient",
    "FakeGroqClient",
    "FakeNVIDIAClient",
    "GroqClient",
    "NVIDIAClient",
    "parse_ai_json_content",
]
