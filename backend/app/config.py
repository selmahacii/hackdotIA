from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "Smart Elderly Monitoring System"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://elderly:elderly@localhost:5433/elderly"

    # JWT Security
    JWT_SECRET: str = "CHANGE_ME"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # MQTT
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USER: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_KEEPALIVE: int = 60
    MQTT_RECONNECT_DELAY: float = 2.0
    MQTT_MAX_RECONNECT_DELAY: float = 30.0
    MQTT_TOPIC_PREFIX: str = "elderly"
    MQTT_QOS: int = 1
    MQTT_CLEAN_SESSION: bool = True

    # AI (NVIDIA API / OpenAI compatible)
    AI_PROVIDER: str = "nvidia"
    AI_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    AI_MODEL: str = "meta/llama-3.1-8b-instruct"
    NVIDIA_API_KEY: str = ""
    AI_TIMEOUT_S: float = 10.0

    # Groq Official Configuration
    GROQ_ENABLED: bool = True
    GROQ_API_KEY: str | None = None
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_TIMEOUT_SECONDS: float = 15.0
    GROQ_MAX_TOKENS: int = 500
    GROQ_TEMPERATURE: float = 0.1

    # NVIDIA Configuration (maintained for backwards compatibility)
    NVIDIA_ENABLED: bool = False
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "meta/llama-3.1-8b-instruct"
    NVIDIA_TIMEOUT_SECONDS: float = 10.0
    NVIDIA_MAX_TOKENS: int = 500
    NVIDIA_TEMPERATURE: float = 0.1

    # Sensor Health & Processing Thresholds
    SENSOR_MAX30102_ABSENCE_THRESHOLD_S: float = 60.0
    SENSOR_DHT11_MIN_INTERVAL_S: float = 2.0
    SENSOR_DHT11_FROZEN_DURATION_S: float = 300.0
    SENSOR_MPU6050_FLATLINE_SAMPLES: int = 5
    SENSOR_GPS_NO_FIX_DURATION_S: float = 180.0
    DEVICE_OFFLINE_THRESHOLD_S: float = 60.0
    BATTERY_WARNING_THRESHOLD: float = 20.0
    BATTERY_CRITICAL_THRESHOLD: float = 10.0

    # CORS
    CORS_ORIGINS: str | list[str] = (
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
