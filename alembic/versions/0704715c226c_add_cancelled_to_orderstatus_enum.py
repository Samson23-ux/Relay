"""add cancelled to orderstatus enum

Revision ID: 0704715c226c
Revises: e24cbf4df7ca
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0704715c226c'
down_revision: Union[str, Sequence[str], None] = 'e24cbf4df7ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE orderstatus ADD VALUE 'cancelled'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing a value from an enum type.
    pass
