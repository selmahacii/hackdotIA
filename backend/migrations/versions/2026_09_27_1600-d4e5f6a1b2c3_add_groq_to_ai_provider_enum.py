"""add_groq_to_ai_provider_enum

Revision ID: d4e5f6a1b2c3
Revises: c3f2d1e0a4b5
Create Date: 2026-09-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a1b2c3'
down_revision: Union[str, None] = 'c3f2d1e0a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add GROQ to ai_provider_enum
    op.execute("ALTER TYPE ai_provider_enum ADD VALUE IF NOT EXISTS 'GROQ'")


def downgrade() -> None:
    pass
