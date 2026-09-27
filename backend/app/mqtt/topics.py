import re
from typing import Literal

from app.config import settings

MessageType = Literal["telemetry", "status", "health"]
ALLOWED_MESSAGE_TYPES: set[str] = {"telemetry", "status", "health"}


def get_topic_filter(prefix: str | None = None) -> list[str]:
    p = prefix or settings.MQTT_TOPIC_PREFIX
    return [
        f"{p}/+/telemetry",
        f"{p}/+/status",
        f"{p}/+/health",
    ]


def parse_topic(topic: str, prefix: str | None = None) -> tuple[str, MessageType] | None:
    """
    Parses an MQTT topic matching '{prefix}/{device_uid}/{message_type}'.
    Returns (device_uid, message_type) or None if invalid.
    """
    p = re.escape(prefix or settings.MQTT_TOPIC_PREFIX)
    pattern = rf"^{p}/([^/]+)/(telemetry|status|health)$"
    match = re.match(pattern, topic)
    if not match:
        return None
    device_uid, msg_type = match.groups()
    return device_uid, msg_type  # type: ignore[return-value]


def build_topic(device_uid: str, message_type: MessageType, prefix: str | None = None) -> str:
    p = prefix or settings.MQTT_TOPIC_PREFIX
    return f"{p}/{device_uid}/{message_type}"
