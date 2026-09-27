import pytest
from httpx import AsyncClient

from app.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient) -> None:
    from app.config import settings

    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.PROJECT_NAME
    assert data["health"] == "/api/v1/health"
    assert data["ready"] == "/api/v1/ready"


def test_password_hashing() -> None:
    plain = "Secr3tP@ssw0rd!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_decoding() -> None:
    payload = {"sub": "elderly_caregiver_1", "role": "caregiver"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "elderly_caregiver_1"
    assert decoded["role"] == "caregiver"
    assert "exp" in decoded


def test_settings_cors_parsing() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000")
    origins = settings.cors_origins_list
    assert origins == ["http://localhost:3000", "http://127.0.0.1:3000"]
