from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class MQTTMetrics:
    status: str = "disconnected"
    last_connected_at: datetime | None = None
    last_disconnected_at: datetime | None = None
    messages_received: int = 0
    messages_processed: int = 0
    duplicates_detected: int = 0
    validation_errors: int = 0
    unknown_devices: int = 0
    topic_mismatches: int = 0
    connection_attempts: int = 0

    def mark_connecting(self) -> None:
        self.status = "connecting"
        self.connection_attempts += 1

    def mark_connected(self) -> None:
        self.status = "connected"
        self.last_connected_at = datetime.now(UTC)

    def mark_disconnected(self) -> None:
        self.status = "disconnected"
        self.last_disconnected_at = datetime.now(UTC)

    def mark_reconnecting(self) -> None:
        self.status = "reconnecting"
        self.connection_attempts += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "connected": self.status == "connected",
            "last_connected_at": (
                self.last_connected_at.isoformat() if self.last_connected_at else None
            ),
            "last_disconnected_at": (
                self.last_disconnected_at.isoformat() if self.last_disconnected_at else None
            ),
            "messages_received": self.messages_received,
            "messages_processed": self.messages_processed,
            "duplicates_detected": self.duplicates_detected,
            "validation_errors": self.validation_errors,
            "unknown_devices": self.unknown_devices,
            "topic_mismatches": self.topic_mismatches,
            "connection_attempts": self.connection_attempts,
        }


# Global state instance
mqtt_metrics = MQTTMetrics()


def get_mqtt_status() -> dict[str, Any]:
    return mqtt_metrics.to_dict()
