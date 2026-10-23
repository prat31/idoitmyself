"""labels

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LABEL_COLORS = ("gray", "red", "orange", "amber", "green", "teal", "blue", "violet", "pink")


def upgrade() -> None:
    op.create_table(
        "labels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_labels"),
        sa.CheckConstraint(
            f"color IN ({', '.join(repr(c) for c in LABEL_COLORS)})", name="ck_labels_color_in_palette"
        ),
    )
    op.create_index("uq_labels_name_lower", "labels", [sa.text("lower(name)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_labels_name_lower", table_name="labels")
    op.drop_table("labels")
