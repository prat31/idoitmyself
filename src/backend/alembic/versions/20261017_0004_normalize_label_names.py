"""normalize label names (lowercase, non-alphanumeric runs -> "_")

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Mirrors app.schemas.label.normalize_label_name. Fails on the unique index if two existing
    # names normalize to the same value (resolve those by hand first).
    op.execute("UPDATE labels SET name = btrim(regexp_replace(lower(name), '[^[:alnum:]]+', '_', 'g'), '_')")
    op.create_check_constraint(
        op.f("ck_labels_name_normalized"),
        "labels",
        "name <> '' AND name = btrim(regexp_replace(lower(name), '[^[:alnum:]]+', '_', 'g'), '_')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_labels_name_normalized"), "labels", type_="check")
