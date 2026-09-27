from enum import Enum


class DeviceStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class AlertType(str, Enum):
    FALL_SUSPECTED = "FALL_SUSPECTED"
    HEART_RATE_ANOMALY = "HEART_RATE_ANOMALY"
    SPO2_ANOMALY = "SPO2_ANOMALY"
    TEMPERATURE_ANOMALY = "TEMPERATURE_ANOMALY"
    SENSOR_HEALTH = "SENSOR_HEALTH"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    GPS_UNAVAILABLE = "GPS_UNAVAILABLE"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertSource(str, Enum):
    RULE_ENGINE = "RULE_ENGINE"
    SENSOR_HEALTH = "SENSOR_HEALTH"
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"


class AIProvider(str, Enum):
    NVIDIA = "NVIDIA"
    FALLBACK_RULES = "FALLBACK_RULES"
    NONE = "NONE"


class AIAnalysisStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FALLBACK = "FALLBACK"


class SensorHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    NO_CONTACT = "NO_CONTACT"
    SUSPECT = "SUSPECT"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
