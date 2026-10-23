"""label evaluations (skip already-evaluated email/label pairs), run reclassify + emails_skipped

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "label_evaluations",
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("label_id", sa.UUID(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("condition_hash", sa.String(64), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.id"], name=op.f("fk_label_evaluations_email_id_emails"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name=op.f("fk_label_evaluations_label_id_labels"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_label_evaluations_run_id_runs"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("email_id", "label_id", name=op.f("pk_label_evaluations")),
    )
    op.create_index(op.f("ix_label_evaluations_label_id"), "label_evaluations", ["label_id"])
    op.add_column(
        "runs", sa.Column("reclassify", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column(
        "runs", sa.Column("emails_skipped", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )

    # Backfill the positive answers we already have, fingerprinted with the condition the run asked
    # (same hash as app.models.email.condition_hash). Negative answers were never stored before this
    # migration, so those pairs are evaluated once more on their next run.
    op.execute(
        """
        INSERT INTO label_evaluations (email_id, label_id, probability, condition_hash, run_id, evaluated_at)
        SELECT el.email_id, el.label_id, el.probability,
               encode(sha256(convert_to(rl.filter_condition, 'UTF8')), 'hex'), el.run_id, el.updated_at
        FROM email_labels el
        JOIN run_labels rl ON rl.run_id = el.run_id AND rl.label_id = el.label_id
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("runs", "emails_skipped")
    op.drop_column("runs", "reclassify")
    op.drop_index(op.f("ix_label_evaluations_label_id"), table_name="label_evaluations")
    op.drop_table("label_evaluations")
