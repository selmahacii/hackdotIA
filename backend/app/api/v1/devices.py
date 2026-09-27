"""Devices API endpoints with RBAC and caregiver tenant isolation."""

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
    require_roles,
)
from app.models.device import Device
from app.models.enums import DeviceStatus
from app.repositories.device import DeviceRepository
from app.schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    elderly_id: uuid.UUID | None = None,
    device_status: DeviceStatus | None = None,
) -> list[Device]:
    """List IoT devices. Caregivers only see devices for assigned elderly residents."""
    stmt = select(Device)

    if elderly_id:
        check_elderly_caregiver_access(elderly_id, current_user)
        stmt = stmt.where(Device.elderly_id == elderly_id)
    elif current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        stmt = stmt.where(Device.elderly_id.in_(current_user.assigned_elderly_ids))

    if device_status:
        stmt = stmt.where(Device.status == device_status)

    stmt = stmt.order_by(Device.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device_by_id(
    device_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> Device:
    """Get device details by ID."""
    repo = DeviceRepository(session)
    device = await repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appareil non trouvé",
        )

    check_elderly_caregiver_access(device.elderly_id, current_user)
    return device


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_in: DeviceCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> Device:
    """Register a new device (Admin & Superadmin only)."""
    repo = DeviceRepository(session)
    existing = await repo.get_by_uid(device_in.device_uid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un appareil avec l'UID '{device_in.device_uid}' existe déjà",
        )

    device = Device(
        device_uid=device_in.device_uid,
        elderly_id=device_in.elderly_id,
        name=device_in.name,
        status=device_in.status,
        firmware_version=device_in.firmware_version,
        battery_level=device_in.battery_level,
        wifi_rssi=device_in.wifi_rssi,
        capabilities=device_in.capabilities,
    )
    created = await repo.create(device)
    await session.commit()
    return created


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: uuid.UUID,
    device_in: DeviceUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN", "OPERATOR"]))
    ],
) -> Device:
    """Update device configuration or status."""
    repo = DeviceRepository(session)
    device = await repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appareil non trouvé",
        )

    for field, val in device_in.model_dump(exclude_unset=True).items():
        setattr(device, field, val)

    await session.commit()
    await session.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> None:
    """Delete a device registration."""
    repo = DeviceRepository(session)
    deleted = await repo.delete(device_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appareil non trouvé",
        )
    await session.commit()
