"""add confirmed to orderstatus enum

Revision ID: 9b1f3a7d5e2c
Revises: 0704715c226c
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9b1f3a7d5e2c'
down_revision: Union[str, Sequence[str], None] = '0704715c226c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE orderstatus ADD VALUE 'confirmed'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres does not support removing a value from an enum type.
    pass
