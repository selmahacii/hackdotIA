import asyncio
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import settings
from app.core.logging import logger
from app.db.session import engine
from app.mqtt import mqtt_consumer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Lifespan startup
    logger.info(f"Starting {settings.PROJECT_NAME} in Phase 0 mode...")
    logger.info(f"Configured CORS origins: {settings.cors_origins_list}")
    # Database connection test on startup (non-fatal if down, /ready will reflect state)
    try:
        async with engine.connect():
            logger.info("Database engine connected successfully.")
    except Exception as e:
        logger.warning(f"Database connection not yet established at startup: {e}")

    # Start background MQTT Consumer
    await mqtt_consumer.start()

    yield

    # Lifespan shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    await mqtt_consumer.stop()
    await engine.dispose()
    logger.info("Database engine disposed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "ready": f"{settings.API_V1_STR}/ready",
    }
