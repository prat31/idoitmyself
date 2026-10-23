"""run name

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill existing runs, then require a name going forward.
    op.add_column("runs", sa.Column("name", sa.String(100), nullable=False, server_default="Ad hoc run"))
    op.alter_column("runs", "name", server_default=None)


def downgrade() -> None:
    op.drop_column("runs", "name")
