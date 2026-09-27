"""add_running_and_error_to_ai_analysis

Revision ID: c3f2d1e0a4b5
Revises: becd5d6ea3f2
Create Date: 2026-09-27 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f2d1e0a4b5'
down_revision: Union[str, None] = 'becd5d6ea3f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add RUNNING to ai_analysis_status_enum
    op.execute("ALTER TYPE ai_analysis_status_enum ADD VALUE IF NOT EXISTS 'RUNNING'")
    # Add error column to ai_analysis
    op.add_column('ai_analysis', sa.Column('error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_analysis', 'error')
