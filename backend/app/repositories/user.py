from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(func.lower(User.username) == username.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> tuple[Sequence[User], int]:
        query = select(User)
        count_query = select(func.count(User.id))

        if role is not None:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.scalars().all()

        return items, total

    async def create_user(self, user_in: UserCreate, hashed_password: str) -> User:
        user = User(
            email=user_in.email.strip().lower(),
            username=user_in.username.strip(),
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=user_in.role,
            is_active=user_in.is_active,
            assigned_elderly_ids=[str(eid) for eid in user_in.assigned_elderly_ids],
        )
        return await self.create(user)

    async def update_user(
        self,
        user: User,
        user_in: UserUpdate,
        hashed_password: str | None = None,
    ) -> User:
        if user_in.email is not None:
            user.email = user_in.email.strip().lower()
        if user_in.username is not None:
            user.username = user_in.username.strip()
        if user_in.full_name is not None:
            user.full_name = user_in.full_name
        if user_in.role is not None:
            user.role = user_in.role
        if user_in.is_active is not None:
            user.is_active = user_in.is_active
        if hashed_password is not None:
            user.hashed_password = hashed_password
        if user_in.assigned_elderly_ids is not None:
            user.assigned_elderly_ids = [str(eid) for eid in user_in.assigned_elderly_ids]
        user.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()
