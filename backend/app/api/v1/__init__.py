from fastapi import APIRouter

from app.api.v1.ai_analysis import router as ai_analysis_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(ai_analysis_router, tags=["AI Analysis"])

__all__ = ["api_router"]
