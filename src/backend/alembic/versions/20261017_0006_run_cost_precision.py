"""run cost precision (Jev costs ~1e-5 USD per email)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("runs", "cost_usd", type_=sa.Numeric(16, 9), existing_type=sa.Numeric(12, 6))


def downgrade() -> None:
    op.alter_column("runs", "cost_usd", type_=sa.Numeric(12, 6), existing_type=sa.Numeric(16, 9))
