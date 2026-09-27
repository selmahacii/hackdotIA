from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.ai_analysis import router as ai_analysis_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.devices import router as devices_router
from app.api.v1.elderly import router as elderly_router
from app.api.v1.health import router as health_router
from app.api.v1.measurements import router as measurements_router
from app.api.v1.sensors import router as sensors_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(elderly_router)
api_router.include_router(devices_router)
api_router.include_router(alerts_router)
api_router.include_router(measurements_router)
api_router.include_router(sensors_router)
api_router.include_router(dashboard_router)
api_router.include_router(ai_analysis_router)

__all__ = ["api_router"]
