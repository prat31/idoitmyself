"""initial schema: inboxes, tags, labels, filters (+ scope), scans (+ ad hoc filters), emails

Revision ID: 0001
Revises:
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

inbox_provider = postgresql.ENUM("gmail", name="inbox_provider", create_type=False)
filter_status = postgresql.ENUM("active", "inactive", name="filter_status", create_type=False)
scan_kind = postgresql.ENUM("scheduled", "adhoc", name="scan_kind", create_type=False)
scan_status = postgresql.ENUM(
    "queued", "running", "completed", "failed", "cancelled", name="scan_status", create_type=False
)
ENUMS = (inbox_provider, filter_status, scan_kind, scan_status)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _counter(name: str) -> sa.Column:
    return sa.Column(name, sa.Integer(), server_default=sa.text("0"), nullable=False)


def upgrade() -> None:
    for enum in ENUMS:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "inboxes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", inbox_provider, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email_address", sa.String(320), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_inboxes"),
        sa.UniqueConstraint("provider", "email_address", name="uq_inboxes_provider_email_address"),
    )

    op.create_table(
        "inbox_credentials",
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name="fk_inbox_credentials_inbox_id_inboxes", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("inbox_id", name="pk_inbox_credentials"),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_tags"),
    )
    op.create_index("uq_tags_name_lower", "tags", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "inbox_tags",
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name="fk_inbox_tags_inbox_id_inboxes", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name="fk_inbox_tags_tag_id_tags", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("inbox_id", "tag_id", name="pk_inbox_tags"),
    )

    op.create_table(
        "labels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), server_default=sa.text("'gray'"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "name <> '' AND name = btrim(regexp_replace(lower(name), '[^[:alnum:]]+', '_', 'g'), '_')",
            name="ck_labels_name_normalized",
        ),
        sa.CheckConstraint(
            "color IN ('gray', 'red', 'orange', 'amber', 'green', 'teal', 'blue', 'violet', 'pink')",
            name="ck_labels_color_in_palette",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_labels"),
        sa.UniqueConstraint("name", name="uq_labels_name"),
    )

    op.create_table(
        "filters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("label_id", sa.UUID(), nullable=False),
        sa.Column("rule", postgresql.JSONB(), nullable=False),
        sa.Column("status", filter_status, nullable=False),
        sa.Column(
            "status_changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name="fk_filters_label_id_labels", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_filters"),
    )
    op.create_index("ix_filters_label_id", "filters", ["label_id"])
    op.create_index("ix_filters_status", "filters", ["status"])

    # A filter's scope: whole mailbox types and/or individual inboxes.
    op.create_table(
        "filter_mailbox_types",
        sa.Column("filter_id", sa.UUID(), nullable=False),
        sa.Column("mailbox_type", inbox_provider, nullable=False),
        sa.ForeignKeyConstraint(
            ["filter_id"],
            ["filters.id"],
            name="fk_filter_mailbox_types_filter_id_filters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("filter_id", "mailbox_type", name="pk_filter_mailbox_types"),
    )
    op.create_table(
        "filter_inboxes",
        sa.Column("filter_id", sa.UUID(), nullable=False),
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["filter_id"], ["filters.id"], name="fk_filter_inboxes_filter_id_filters", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name="fk_filter_inboxes_inbox_id_inboxes", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("filter_id", "inbox_id", name="pk_filter_inboxes"),
    )

    op.create_table(
        "scans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("kind", scan_kind, nullable=False),
        sa.Column("status", scan_status, nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        _counter("emails_found"),
        _counter("emails_processed"),
        _counter("emails_skipped"),
        _counter("emails_failed"),
        _counter("emails_matched"),
        _counter("labels_applied"),
        _counter("retries"),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name="fk_scans_inbox_id_inboxes", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scans"),
    )
    op.create_index("ix_scans_inbox_id", "scans", ["inbox_id"])
    op.create_index("ix_scans_status", "scans", ["status"])

    # The filters an ad hoc scan runs.
    op.create_table(
        "scan_filters",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("filter_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="fk_scan_filters_scan_id_scans", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["filter_id"], ["filters.id"], name="fk_scan_filters_filter_id_filters", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("scan_id", "filter_id", name="pk_scan_filters"),
    )

    op.create_table(
        "inbox_sync",
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("scanned_until", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name="fk_inbox_sync_inbox_id_inboxes", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("inbox_id", name="pk_inbox_sync"),
    )

    op.create_table(
        "emails",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=False),
        sa.Column("provider_thread_id", sa.String(255), nullable=True),
        sa.Column("internet_message_id", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_address", sa.Text(), nullable=True),
        sa.Column("to_addresses", sa.Text(), nullable=True),
        sa.Column("cc_addresses", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["inbox_id"], ["inboxes.id"], name="fk_emails_inbox_id_inboxes", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="fk_emails_scan_id_scans", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_emails"),
        sa.UniqueConstraint("inbox_id", "provider_message_id", name="uq_emails_inbox_id_provider_message_id"),
    )
    op.create_index("ix_emails_inbox_id", "emails", ["inbox_id"])
    op.create_index("ix_emails_inbox_id_sent_at", "emails", ["inbox_id", "sent_at"])

    op.create_table(
        "email_labels",
        sa.Column("email_id", sa.UUID(), nullable=False),
        sa.Column("label_id", sa.UUID(), nullable=False),
        sa.Column("filter_id", sa.UUID(), nullable=True),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.id"], name="fk_email_labels_email_id_emails", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name="fk_email_labels_label_id_labels", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["filter_id"], ["filters.id"], name="fk_email_labels_filter_id_filters", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name="fk_email_labels_scan_id_scans", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("email_id", "label_id", name="pk_email_labels"),
    )
    op.create_index("ix_email_labels_label_id", "email_labels", ["label_id"])
    op.create_index("ix_email_labels_filter_id", "email_labels", ["filter_id"])


def downgrade() -> None:
    for table in (
        "email_labels",
        "emails",
        "inbox_sync",
        "scan_filters",
        "scans",
        "filter_inboxes",
        "filter_mailbox_types",
        "filters",
        "labels",
        "inbox_tags",
        "tags",
        "inbox_credentials",
        "inboxes",
    ):
        op.drop_table(table)
    for enum in reversed(ENUMS):
        enum.drop(op.get_bind(), checkfirst=True)
