"""API endpoints for AI Enrichment analysis and WebSocket notifications."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthenticatedUser,
    check_alert_caregiver_access,
    get_db,
    require_roles,
)
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.alert import AlertRepository
from app.schemas.ai_analysis import AIAnalysisResponse
from app.services.ai_analysis import AIAnalysisService
from app.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/alerts/{alert_id}/ai-analysis",
    response_model=AIAnalysisResponse,
    summary="Get AI enrichment analysis for an alert",
    description="Returns the latest AI analysis for an alert. Requires role ADMIN, CAREGIVER, OPERATOR, or READ_ONLY.",
)
async def get_alert_ai_analysis(
    alert_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_roles(["ADMIN", "CAREGIVER", "OPERATOR", "READ_ONLY"])),
    ],
) -> AIAnalysisResponse:
    alert_repo = AlertRepository(db)
    alert = await alert_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    check_alert_caregiver_access(alert, current_user)

    ai_repo = AIAnalysisRepository(db)
    analysis = await ai_repo.get_latest_by_alert_id(alert_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI analysis found for alert {alert_id}",
        )

    return AIAnalysisResponse.model_validate(analysis)


@router.post(
    "/alerts/{alert_id}/ai-analysis",
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger or re-trigger AI analysis for an alert",
    description="Triggers AI enrichment analysis. Requires role ADMIN, CAREGIVER, or OPERATOR.",
)
async def trigger_alert_ai_analysis(
    alert_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_roles(["ADMIN", "CAREGIVER", "OPERATOR"])),
    ],
    force: bool = Query(
        default=False, description="Force re-triggering analysis even if already completed"
    ),
) -> AIAnalysisResponse:
    alert_repo = AlertRepository(db)
    alert = await alert_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    check_alert_caregiver_access(alert, current_user)

    service = AIAnalysisService(db)
    analysis = await service.run_enrichment_for_alert(alert_id, force=force)
    return AIAnalysisResponse.model_validate(analysis)


@router.websocket("/alerts/ws")
async def alerts_websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time WebSocket endpoint for receiving live alerts and AI enrichment notifications."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and receive optional ping messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket exception: %s", exc)
        ws_manager.disconnect(websocket)
