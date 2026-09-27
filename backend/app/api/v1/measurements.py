"""Measurements API endpoints with filtering, historical trend series, and RBAC."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AuthenticatedUser,
    check_elderly_caregiver_access,
    get_current_user,
    get_db,
)
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementResponse

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.get("", response_model=list[MeasurementResponse])
async def list_measurements(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    elderly_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Measurement]:
    """List measurements with pagination and filtering."""
    stmt = select(Measurement)

    if elderly_id:
        check_elderly_caregiver_access(elderly_id, current_user)
        stmt = stmt.where(Measurement.elderly_id == elderly_id)
    elif current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        stmt = stmt.where(Measurement.elderly_id.in_(current_user.assigned_elderly_ids))

    if device_id:
        stmt = stmt.where(Measurement.device_id == device_id)

    stmt = stmt.order_by(Measurement.measured_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/latest", response_model=MeasurementResponse | None)
async def get_latest_measurement(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    elderly_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
) -> Measurement | None:
    """Retrieve the single most recent measurement for a resident or device."""
    if not elderly_id and not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Préciser elderly_id ou device_id",
        )

    stmt = select(Measurement)
    if elderly_id:
        check_elderly_caregiver_access(elderly_id, current_user)
        stmt = stmt.where(Measurement.elderly_id == elderly_id)
    if device_id:
        stmt = stmt.where(Measurement.device_id == device_id)

    stmt = stmt.order_by(Measurement.measured_at.desc()).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first()


@router.get("/history")
async def get_measurement_history(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    elderly_id: uuid.UUID,
    limit: int = Query(60, ge=1, le=500),
) -> list[dict]:
    """Retrieve chronologically ordered time-series points for dashboard charts."""
    check_elderly_caregiver_access(elderly_id, current_user)

    stmt = (
        select(Measurement)
        .where(Measurement.elderly_id == elderly_id)
        .order_by(Measurement.measured_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    measurements = list(result.scalars().all())
    measurements.reverse()  # Chronological order

    return [
        {
            "timestamp": m.measured_at.isoformat(),
            "bpm": m.bpm,
            "spo2": m.spo2,
            "temperature_c": m.temperature_c,
            "humidity_percent": m.humidity_percent,
            "accel_magnitude_g": m.accel_magnitude_g,
            "battery_level": m.battery_level,
            "finger_detected": m.finger_detected,
        }
        for m in measurements
    ]
