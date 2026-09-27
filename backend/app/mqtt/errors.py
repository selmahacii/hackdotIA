class MQTTError(Exception):
    """Base exception for all MQTT related ingestion errors."""


class TopicMismatchError(MQTTError):
    """Raised when topic device_uid does not match payload device_uid."""

    def __init__(self, topic_uid: str, payload_uid: str) -> None:
        super().__init__(
            f"Topic device_uid '{topic_uid}' does not match payload device_uid '{payload_uid}'"
        )
        self.topic_uid = topic_uid
        self.payload_uid = payload_uid


class UnknownDeviceError(MQTTError):
    """Raised when device_uid does not exist in database."""

    def __init__(self, device_uid: str) -> None:
        super().__init__(f"Device '{device_uid}' is not registered in the system")
        self.device_uid = device_uid


class DuplicateEventError(MQTTError):
    """Raised when event_id has already been processed (idempotence)."""

    def __init__(self, event_id: str) -> None:
        super().__init__(f"Duplicate event_id detected: {event_id}")
        self.event_id = event_id


class InvalidPayloadError(MQTTError):
    """Raised when payload JSON is malformed or violates Pydantic schema."""

    def __init__(self, reason: str, details: object = None) -> None:
        super().__init__(f"Invalid payload: {reason}")
        self.reason = reason
        self.details = details
