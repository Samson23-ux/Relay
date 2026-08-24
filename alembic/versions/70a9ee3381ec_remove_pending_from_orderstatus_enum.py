"""remove pending from orderstatus enum

Revision ID: 70a9ee3381ec
Revises: 9b1f3a7d5e2c
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70a9ee3381ec'
down_revision: Union[str, Sequence[str], None] = '9b1f3a7d5e2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres can't drop a single enum value directly, so: move any orders
    # still sitting in 'pending' onto 'processing' (its replacement as the
    # default in-flight status), then recreate the type without 'pending'.
    op.execute("UPDATE orders SET status = 'processing' WHERE status = 'pending'")

    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_old")
    op.execute(
        "CREATE TYPE orderstatus AS ENUM "
        "('processing', 'confirmed', 'delivered', 'cancelled')"
    )
    op.execute(
        "ALTER TABLE orders ALTER COLUMN status TYPE orderstatus "
        "USING status::text::orderstatus"
    )
    op.execute("DROP TYPE orderstatus_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_new")
    op.execute(
        "CREATE TYPE orderstatus AS ENUM "
        "('pending', 'processing', 'confirmed', 'delivered', 'cancelled')"
    )
    op.execute(
        "ALTER TABLE orders ALTER COLUMN status TYPE orderstatus "
        "USING status::text::orderstatus"
    )
    op.execute("DROP TYPE orderstatus_new")
