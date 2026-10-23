"""emails, email labels, runs, label match threshold

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-17 09:02:16.725661
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Enum("adhoc", name="run_kind"), nullable=False),
        sa.Column(
            "status", sa.Enum("queued", "running", "completed", "failed", name="run_status"), nullable=False
        ),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("emails_found", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("emails_processed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("emails_failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("emails_matched", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("labels_applied", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("labels_removed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )
    op.create_index(op.f("ix_runs_status"), "runs", ["status"], unique=False)
    op.create_table(
        "emails",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=False),
        sa.Column("provider_thread_id", sa.String(length=255), nullable=True),
        sa.Column("internet_message_id", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_address", sa.Text(), nullable=True),
        sa.Column("to_addresses", sa.Text(), nullable=True),
        sa.Column("cc_addresses", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("last_run_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name=op.f("fk_emails_inbox_id_inboxes"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["last_run_id"], ["runs.id"], name=op.f("fk_emails_last_run_id_runs"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emails")),
        sa.UniqueConstraint("inbox_id", "provider_message_id", name="uq_emails_inbox_id_provider_message_id"),
    )
    op.create_index(op.f("ix_emails_inbox_id"), "emails", ["inbox_id"], unique=False)
    op.create_index("ix_emails_inbox_id_sent_at", "emails", ["inbox_id", "sent_at"], unique=False)
    op.create_table(
        "run_inboxes",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("inbox_id", sa.UUID(), nullable=True),
        sa.Column("inbox_name", sa.String(length=100), nullable=False),
        sa.Column("email_address", sa.String(length=320), nullable=False),
        sa.Column("emails_found", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name=op.f("fk_run_inboxes_inbox_id_inboxes"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_run_inboxes_run_id_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("run_id", "position", name=op.f("pk_run_inboxes")),
    )
    op.create_table(
        "run_labels",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.UUID(), nullable=True),
        sa.Column("label_name", sa.String(length=50), nullable=False),
        sa.Column("filter_condition", sa.Text(), nullable=False),
        sa.Column("match_threshold", sa.Float(), nullable=False),
        sa.Column("matched", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name=op.f("fk_run_labels_label_id_labels"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_run_labels_run_id_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("run_id", "position", name=op.f("pk_run_labels")),
    )
    op.create_table(
        "email_labels",
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("label_id", sa.UUID(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.id"], name=op.f("fk_email_labels_email_id_emails"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name=op.f("fk_email_labels_label_id_labels"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"], name=op.f("fk_email_labels_run_id_runs"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("email_id", "label_id", name=op.f("pk_email_labels")),
    )
    op.create_index(op.f("ix_email_labels_label_id"), "email_labels", ["label_id"], unique=False)
    op.add_column(
        "labels", sa.Column("match_threshold", sa.Float(), server_default=sa.text("0.5"), nullable=False)
    )
    op.create_check_constraint(
        op.f("ck_labels_match_threshold_range"), "labels", "match_threshold > 0 AND match_threshold < 1"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_labels_match_threshold_range"), "labels", type_="check")
    op.drop_column("labels", "match_threshold")
    op.drop_index(op.f("ix_email_labels_label_id"), table_name="email_labels")
    op.drop_table("email_labels")
    op.drop_table("run_labels")
    op.drop_table("run_inboxes")
    op.drop_index("ix_emails_inbox_id_sent_at", table_name="emails")
    op.drop_index(op.f("ix_emails_inbox_id"), table_name="emails")
    op.drop_table("emails")
    op.drop_index(op.f("ix_runs_status"), table_name="runs")
    op.drop_table("runs")
    sa.Enum(name="run_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="run_kind").drop(op.get_bind(), checkfirst=True)
