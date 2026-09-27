"""Seed script for database initialization.

Creates default users for all 5 RBAC roles and initial resident & device records.
"""

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import DeviceStatus, UserRole
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")

DEFAULT_USERS = [
    {
        "email": "superadmin@smartelderly.local",
        "username": "superadmin",
        "full_name": "Super Administrator",
        "password": "SuperAdmin123!",
        "role": UserRole.SUPERADMIN,
    },
    {
        "email": "admin@smartelderly.local",
        "username": "admin",
        "full_name": "Facility Administrator",
        "password": "Admin123!",
        "role": UserRole.ADMIN,
    },
    {
        "email": "caregiver@smartelderly.local",
        "username": "caregiver",
        "full_name": "Lead Caregiver Sarah",
        "password": "Caregiver123!",
        "role": UserRole.CAREGIVER,
    },
    {
        "email": "operator@smartelderly.local",
        "username": "operator",
        "full_name": "Monitoring Operator Marc",
        "password": "Operator123!",
        "role": UserRole.OPERATOR,
    },
    {
        "email": "readonly@smartelderly.local",
        "username": "readonly",
        "full_name": "Auditor ReadOnly",
        "password": "ReadOnly123!",
        "role": UserRole.READ_ONLY,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # 1. Seed or check Elderly residents
        elderly_stmt = select(ElderlyPerson)
        res = await session.execute(elderly_stmt)
        existing_elderly = list(res.scalars().all())

        if not existing_elderly:
            logger.info("Seeding initial Elderly residents...")
            e1 = ElderlyPerson(
                id=uuid.uuid4(),
                first_name="Jeanne",
                last_name="Dupont",
                date_of_birth=date(1938, 4, 12),
                phone="+33 6 12 34 56 78",
                emergency_contact_name="Michel Dupont (Fils)",
                emergency_contact_phone="+33 6 98 76 54 32",
                is_active=True,
            )
            e2 = ElderlyPerson(
                id=uuid.uuid4(),
                first_name="Robert",
                last_name="Martin",
                date_of_birth=date(1942, 9, 23),
                phone="+33 6 22 33 44 55",
                emergency_contact_name="Claire Martin (Fille)",
                emergency_contact_phone="+33 6 88 77 66 55",
                is_active=True,
            )
            session.add_all([e1, e2])
            await session.flush()
            existing_elderly = [e1, e2]
            logger.info("Created 2 residents: %s and %s", e1.first_name, e2.first_name)

            # 2. Seed Devices for them
            d1 = Device(
                id=uuid.uuid4(),
                elderly_id=e1.id,
                device_uid="ESP32-SENS-001",
                name="Bracelet Capteurs Jeanne",
                status=DeviceStatus.ONLINE,
                firmware_version="1.2.0-esp6.1",
                battery_level=88.5,
                wifi_rssi=-54,
                capabilities={"sensors": ["MPU6050", "MAX30102", "DHT11", "GPS"]},
                last_seen_at=datetime.now(UTC),
            )
            d2 = Device(
                id=uuid.uuid4(),
                elderly_id=e2.id,
                device_uid="ESP32-SENS-002",
                name="Bracelet Capteurs Robert",
                status=DeviceStatus.ONLINE,
                firmware_version="1.2.0-esp6.1",
                battery_level=94.0,
                wifi_rssi=-62,
                capabilities={"sensors": ["MPU6050", "MAX30102", "DHT11", "GPS"]},
                last_seen_at=datetime.now(UTC),
            )
            session.add_all([d1, d2])
            await session.flush()
            logger.info("Created 2 devices for residents.")

        # Assign first resident to the default caregiver
        assigned_resident_ids = [str(existing_elderly[0].id)] if existing_elderly else []

        # 3. Seed Users
        for udata in DEFAULT_USERS:
            stmt = select(User).where(User.username == udata["username"])
            user_res = await session.execute(stmt)
            existing_user = user_res.scalars().first()

            assigned = assigned_resident_ids if udata["role"] == UserRole.CAREGIVER else []

            if existing_user is None:
                new_user = User(
                    email=udata["email"],
                    username=udata["username"],
                    full_name=udata["full_name"],
                    hashed_password=hash_password(udata["password"]),
                    role=udata["role"],
                    is_active=True,
                    assigned_elderly_ids=assigned,
                )
                session.add(new_user)
                logger.info("Created user: %s (%s)", udata["username"], udata["role"].value)
            else:
                # Update role and assigned_elderly_ids if needed
                existing_user.role = udata["role"]
                if udata["role"] == UserRole.CAREGIVER and not existing_user.assigned_elderly_ids:
                    existing_user.assigned_elderly_ids = assigned
                logger.info("User %s already exists.", udata["username"])

        await session.commit()
        logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
