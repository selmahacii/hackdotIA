"""Admin API endpoints for user management and system metrics."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.core.security import hash_password
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import AlertStatus, DeviceStatus, UserRole
from app.models.measurement import Measurement
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> dict:
    """List users with pagination and role filters (Admin and Superadmin only)."""
    user_repo = UserRepository(session)
    users, total = await user_repo.list_users(
        skip=skip, limit=limit, role=role, is_active=is_active
    )

    items = [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_active": u.is_active,
            "assigned_elderly_ids": u.assigned_elderly_ids,
            "created_at": u.created_at.isoformat(),
            "updated_at": u.updated_at.isoformat(),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]

    return {
        "items": items,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Create a new user account (Admin and Superadmin only)."""
    # Only SUPERADMIN can create SUPERADMIN
    if user_in.role == UserRole.SUPERADMIN and current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un Superadmin peut créer un compte Superadmin",
        )

    user_repo = UserRepository(session)

    # Check for existing email or username
    existing_email = await user_repo.get_by_email(user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une adresse email identique existe déjà",
        )

    existing_username = await user_repo.get_by_username(user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un nom d'utilisateur identique existe déjà",
        )

    hashed = hash_password(user_in.password)
    user = await user_repo.create_user(user_in, hashed)
    await session.commit()

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "assigned_elderly_ids": user.assigned_elderly_ids,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Retrieve user details by ID."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )

    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "assigned_elderly_ids": user.assigned_elderly_ids,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Update user information (Admin and Superadmin only)."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )

    # Only SUPERADMIN can modify a SUPERADMIN or promote to SUPERADMIN
    if (
        user.role == UserRole.SUPERADMIN or user_in.role == UserRole.SUPERADMIN
    ) and current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un Superadmin peut modifier le rôle Superadmin",
        )

    hashed: str | None = None
    if user_in.password:
        hashed = hash_password(user_in.password)

    updated_user = await user_repo.update_user(user, user_in, hashed_password=hashed)
    await session.commit()

    return {
        "id": str(updated_user.id),
        "username": updated_user.username,
        "email": updated_user.email,
        "full_name": updated_user.full_name,
        "role": (
            updated_user.role.value
            if hasattr(updated_user.role, "value")
            else str(updated_user.role)
        ),
        "is_active": updated_user.is_active,
        "assigned_elderly_ids": updated_user.assigned_elderly_ids,
        "created_at": updated_user.created_at.isoformat(),
        "updated_at": updated_user.updated_at.isoformat(),
        "last_login_at": (
            updated_user.last_login_at.isoformat() if updated_user.last_login_at else None
        ),
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["SUPERADMIN"]))],
) -> None:
    """Delete a user account (Superadmin only)."""
    if str(user_id) == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer son propre compte administrateur",
        )

    user_repo = UserRepository(session)
    deleted = await user_repo.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé",
        )
    await session.commit()


@router.get("/stats")
async def get_admin_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> dict:
    """Retrieve system and tenant statistics."""
    # Count users
    total_users_res = await session.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    # User role distribution
    roles_res = await session.execute(select(User.role, func.count(User.id)).group_by(User.role))
    role_dist = {str(r[0].value if hasattr(r[0], "value") else r[0]): r[1] for r in roles_res.all()}

    # Residents count
    elderly_count_res = await session.execute(select(func.count(ElderlyPerson.id)))
    elderly_count = elderly_count_res.scalar() or 0

    # Devices count
    devices_count_res = await session.execute(select(func.count(Device.id)))
    devices_count = devices_count_res.scalar() or 0

    # Online devices count
    online_devices_res = await session.execute(
        select(func.count(Device.id)).where(Device.status == DeviceStatus.ONLINE)
    )
    online_devices = online_devices_res.scalar() or 0

    # Alerts count
    open_alerts_res = await session.execute(
        select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN)
    )
    open_alerts = open_alerts_res.scalar() or 0

    # Total measurements
    measurements_count_res = await session.execute(select(func.count(Measurement.id)))
    total_measurements = measurements_count_res.scalar() or 0

    return {
        "users": {
            "total": total_users,
            "by_role": role_dist,
        },
        "residents": elderly_count,
        "devices": {
            "total": devices_count,
            "online": online_devices,
            "offline": devices_count - online_devices,
        },
        "alerts": {
            "open": open_alerts,
        },
        "measurements": {
            "total": total_measurements,
        },
        "system_status": "OPERATIONAL",
    }
