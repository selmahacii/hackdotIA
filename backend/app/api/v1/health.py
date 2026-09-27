from typing import Any

from fastapi import APIRouter, Response, status

from app.db.session import check_database_connection
from app.mqtt.client import get_mqtt_status

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check(response: Response) -> dict[str, Any]:
    db_ok = await check_database_connection()
    mqtt_info = get_mqtt_status()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not ready",
            "database": "disconnected",
            "mqtt": mqtt_info["status"],
        }
    return {
        "status": "ready",
        "database": "connected",
        "mqtt": mqtt_info["status"],
    }
