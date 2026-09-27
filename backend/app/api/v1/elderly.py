"""Elderly Residents API endpoints with RBAC and caregiver tenant isolation."""

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
from app.models.elderly import ElderlyPerson
from app.repositories.elderly import ElderlyRepository
from app.schemas.elderly import ElderlyCreate, ElderlyResponse, ElderlyUpdate

router = APIRouter(prefix="/elderly", tags=["elderly"])


@router.get("", response_model=list[ElderlyResponse])
async def list_elderly(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = True,
    search: str | None = Query(default=None, description="Search by name or phone"),
) -> list[ElderlyPerson]:
    """List elderly residents.

    Caregivers only see residents assigned to them (tenant isolation).
    """
    stmt = select(ElderlyPerson)
    if active_only:
        stmt = stmt.where(ElderlyPerson.is_active.is_(True))

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (ElderlyPerson.first_name.ilike(pattern))
            | (ElderlyPerson.last_name.ilike(pattern))
            | (ElderlyPerson.phone.ilike(pattern))
        )

    # Caregiver tenant isolation
    if current_user.role == "CAREGIVER" and current_user.assigned_elderly_ids:
        stmt = stmt.where(ElderlyPerson.id.in_(current_user.assigned_elderly_ids))

    stmt = (
        stmt.order_by(ElderlyPerson.last_name, ElderlyPerson.first_name).offset(skip).limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{elderly_id}", response_model=ElderlyResponse)
async def get_elderly_by_id(
    elderly_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ElderlyPerson:
    """Get single resident detail by ID, with caregiver isolation enforcement."""
    check_elderly_caregiver_access(elderly_id, current_user)

    repo = ElderlyRepository(session)
    elderly = await repo.get_by_id(elderly_id)
    if not elderly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Résident non trouvé",
        )
    return elderly


@router.post("", response_model=ElderlyResponse, status_code=status.HTTP_201_CREATED)
async def create_elderly(
    elderly_in: ElderlyCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> ElderlyPerson:
    """Create a new elderly resident (Admin & Superadmin only)."""
    repo = ElderlyRepository(session)
    elderly = ElderlyPerson(
        first_name=elderly_in.first_name,
        last_name=elderly_in.last_name,
        date_of_birth=elderly_in.date_of_birth,
        phone=elderly_in.phone,
        emergency_contact_name=elderly_in.emergency_contact_name,
        emergency_contact_phone=elderly_in.emergency_contact_phone,
        is_active=elderly_in.is_active,
    )
    created = await repo.create(elderly)
    await session.commit()
    return created


@router.patch("/{elderly_id}", response_model=ElderlyResponse)
async def update_elderly(
    elderly_id: uuid.UUID,
    elderly_in: ElderlyUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> ElderlyPerson:
    """Update elderly resident details (Admin & Superadmin only)."""
    repo = ElderlyRepository(session)
    elderly = await repo.get_by_id(elderly_id)
    if not elderly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Résident non trouvé",
        )

    for field, val in elderly_in.model_dump(exclude_unset=True).items():
        setattr(elderly, field, val)

    await session.commit()
    await session.refresh(elderly)
    return elderly


@router.delete("/{elderly_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_elderly(
    elderly_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[AuthenticatedUser, Depends(require_roles(["ADMIN", "SUPERADMIN"]))],
) -> None:
    """Delete elderly resident (Admin & Superadmin only)."""
    repo = ElderlyRepository(session)
    deleted = await repo.delete(elderly_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Résident non trouvé",
        )
    await session.commit()
