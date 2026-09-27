"""Alerts API endpoints with RBAC, caregiver isolation, ack, and resolve actions."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    AuthenticatedUser,
    check_alert_caregiver_access,
    get_current_user,
    get_db,
    require_roles,
)
from app.models.alert import Alert
from app.models.enums import AlertSeverity, AlertStatus, AlertType

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    elderly_id: uuid.UUID | None = None,
    severity: AlertSeverity | None = None,
    alert_status: AlertStatus | None = None,
    alert_type: AlertType | None = None,
) -> dict:
    """List alerts with pagination, filtering, and caregiver isolation."""
    stmt = select(Alert).options(
        selectinload(Alert.elderly),
        selectinload(Alert.device),
        selectinload(Alert.ai_analyses),
    )

    if elderly_id:
        stmt = stmt.where(Alert.elderly_id == elderly_id)
    elif current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        stmt = stmt.where(Alert.elderly_id.in_(current_user.assigned_elderly_ids))

    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if alert_status:
        stmt = stmt.where(Alert.status == alert_status)
    if alert_type:
        stmt = stmt.where(Alert.alert_type == alert_type)

    stmt = stmt.order_by(Alert.occurred_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    alerts = result.scalars().all()

    items = []
    for a in alerts:
        latest_ai = a.ai_analyses[-1] if a.ai_analyses else None
        items.append(
            {
                "id": str(a.id),
                "elderly_id": str(a.elderly_id),
                "elderly_name": (
                    f"{a.elderly.first_name} {a.elderly.last_name}" if a.elderly else None
                ),
                "device_id": str(a.device_id) if a.device_id else None,
                "device_name": a.device.name if a.device else None,
                "alert_type": (
                    a.alert_type.value if hasattr(a.alert_type, "value") else str(a.alert_type)
                ),
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "title": a.title,
                "description": a.description,
                "source": a.source.value if hasattr(a.source, "value") else str(a.source),
                "occurred_at": a.occurred_at.isoformat(),
                "occurrence_count": a.occurrence_count,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "acknowledged_by": a.acknowledged_by,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "has_ai_analysis": latest_ai is not None,
                "ai_status": (
                    (
                        latest_ai.status.value
                        if hasattr(latest_ai.status, "value")
                        else str(latest_ai.status)
                    )
                    if latest_ai
                    else None
                ),
                "ai_summary": latest_ai.possible_event if latest_ai else None,
            }
        )

    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.get("/{alert_id}")
async def get_alert_detail(
    alert_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    """Get complete alert detail including deterministic context and AI analysis."""
    stmt = (
        select(Alert)
        .options(
            selectinload(Alert.elderly),
            selectinload(Alert.device),
            selectinload(Alert.ai_analyses),
        )
        .where(Alert.id == alert_id)
    )
    result = await session.execute(stmt)
    alert = result.scalars().first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte non trouvée",
        )

    check_alert_caregiver_access(alert, current_user)

    ai_list = [
        {
            "id": str(ai.id),
            "provider": ai.provider.value if hasattr(ai.provider, "value") else str(ai.provider),
            "status": ai.status.value if hasattr(ai.status, "value") else str(ai.status),
            "risk_level": ai.risk_level,
            "anomaly_detected": ai.anomaly_detected,
            "possible_event": ai.possible_event,
            "explanation": ai.explanation,
            "recommended_action": ai.recommended_action,
            "confidence": ai.confidence,
            "model_name": ai.model_name,
            "latency_ms": ai.latency_ms,
            "created_at": ai.created_at.isoformat(),
            "completed_at": ai.completed_at.isoformat() if ai.completed_at else None,
        }
        for ai in alert.ai_analyses
    ]

    return {
        "id": str(alert.id),
        "elderly_id": str(alert.elderly_id),
        "elderly_name": (
            f"{alert.elderly.first_name} {alert.elderly.last_name}" if alert.elderly else None
        ),
        "device_id": str(alert.device_id) if alert.device_id else None,
        "device_uid": alert.device.device_uid if alert.device else None,
        "device_name": alert.device.name if alert.device else None,
        "alert_type": (
            alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type)
        ),
        "severity": (
            alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        ),
        "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status),
        "title": alert.title,
        "description": alert.description,
        "source": alert.source.value if hasattr(alert.source, "value") else str(alert.source),
        "occurred_at": alert.occurred_at.isoformat(),
        "occurrence_count": alert.occurrence_count,
        "context": alert.context,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "acknowledged_by": alert.acknowledged_by,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "ai_analyses": ai_list,
    }


@router.post("/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_roles(["ADMIN", "SUPERADMIN", "CAREGIVER", "OPERATOR"])),
    ],
) -> dict:
    """Acknowledge an alert."""
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalars().first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte non trouvée",
        )

    check_alert_caregiver_access(alert, current_user)

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(UTC)
    alert.acknowledged_by = current_user.username
    await session.commit()
    await session.refresh(alert)

    return {
        "id": str(alert.id),
        "status": alert.status.value,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "acknowledged_by": alert.acknowledged_by,
    }


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_roles(["ADMIN", "SUPERADMIN", "CAREGIVER", "OPERATOR"])),
    ],
) -> dict:
    """Mark an alert as resolved."""
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalars().first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerte non trouvée",
        )

    check_alert_caregiver_access(alert, current_user)

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(alert)

    return {
        "id": str(alert.id),
        "status": alert.status.value,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }
