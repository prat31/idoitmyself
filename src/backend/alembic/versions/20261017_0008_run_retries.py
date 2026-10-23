"""run discovered_at and retries (broker-side retry of transient failures)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("retries", sa.Integer(), server_default=sa.text("0"), nullable=False))


def downgrade() -> None:
    op.drop_column("runs", "retries")
    op.drop_column("runs", "discovered_at")
