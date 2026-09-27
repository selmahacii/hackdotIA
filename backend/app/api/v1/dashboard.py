"""Dashboard API endpoints for aggregate KPIs and telemetry trends."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.config import settings
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import AlertStatus, DeviceStatus
from app.models.measurement import Measurement

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict:
    """Retrieve key performance indicators and summary metrics for the main dashboard."""
    elderly_query = select(func.count(ElderlyPerson.id)).where(ElderlyPerson.is_active.is_(True))
    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        elderly_query = elderly_query.where(ElderlyPerson.id.in_(current_user.assigned_elderly_ids))
    elderly_res = await session.execute(elderly_query)
    residents_count = elderly_res.scalar() or 0

    # 2. Devices count
    dev_query = select(Device)
    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        dev_query = dev_query.where(Device.elderly_id.in_(current_user.assigned_elderly_ids))
    dev_res = await session.execute(dev_query)
    devices = list(dev_res.scalars().all())
    devices_total = len(devices)
    devices_online = sum(1 for d in devices if d.status == DeviceStatus.ONLINE)

    # 3. Open alerts count by severity
    alerts_query = select(Alert).where(Alert.status == AlertStatus.OPEN)
    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        alerts_query = alerts_query.where(Alert.elderly_id.in_(current_user.assigned_elderly_ids))
    alerts_res = await session.execute(alerts_query)
    open_alerts = list(alerts_res.scalars().all())

    severity_counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "INFO": 0,
    }
    for a in open_alerts:
        sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
        if sev in severity_counts:
            severity_counts[sev] += 1

    # 4. Recent alerts (last 5)
    recent_alerts_stmt = (
        select(Alert)
        .options(selectinload(Alert.elderly), selectinload(Alert.ai_analyses))
        .order_by(Alert.occurred_at.desc())
        .limit(5)
    )
    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        recent_alerts_stmt = recent_alerts_stmt.where(
            Alert.elderly_id.in_(current_user.assigned_elderly_ids)
        )
    recent_alerts_res = await session.execute(recent_alerts_stmt)
    recent_alerts = [
        {
            "id": str(a.id),
            "elderly_name": (
                f"{a.elderly.first_name} {a.elderly.last_name}" if a.elderly else "Résident"
            ),
            "title": a.title,
            "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "occurred_at": a.occurred_at.isoformat(),
            "has_ai": len(a.ai_analyses) > 0,
        }
        for a in recent_alerts_res.scalars().all()
    ]

    # 5. Recent measurements for rapid display
    meas_stmt = select(Measurement).order_by(Measurement.measured_at.desc()).limit(10)
    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        meas_stmt = meas_stmt.where(Measurement.elderly_id.in_(current_user.assigned_elderly_ids))
    meas_res = await session.execute(meas_stmt)
    recent_measurements = [
        {
            "id": str(m.id),
            "measured_at": m.measured_at.isoformat(),
            "bpm": m.bpm,
            "spo2": m.spo2,
            "temperature_c": m.temperature_c,
            "accel_magnitude_g": m.accel_magnitude_g,
        }
        for m in meas_res.scalars().all()
    ]

    return {
        "kpi": {
            "residents_count": residents_count,
            "devices_total": devices_total,
            "devices_online": devices_online,
            "devices_offline": devices_total - devices_online,
            "open_alerts_total": len(open_alerts),
            "critical_alerts": severity_counts["CRITICAL"],
            "high_alerts": severity_counts["HIGH"],
            "medium_alerts": severity_counts["MEDIUM"],
            "low_alerts": severity_counts["LOW"],
        },
        "recent_alerts": recent_alerts,
        "recent_measurements": recent_measurements,
        "ai_engine": {
            "groq_enabled": settings.GROQ_ENABLED,
            "groq_model": settings.GROQ_MODEL if settings.GROQ_ENABLED else None,
            "status": "ONLINE" if settings.GROQ_ENABLED else "FALLBACK_RULES",
        },
    }
