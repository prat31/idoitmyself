"""inboxes, inbox credentials and tags

Revision ID: 0001
Revises:
Create Date: 2026-10-17
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


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    inbox_provider.create(op.get_bind(), checkfirst=True)

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


def downgrade() -> None:
    op.drop_table("inbox_tags")
    op.drop_index("uq_tags_name_lower", table_name="tags")
    op.drop_table("tags")
    op.drop_table("inbox_credentials")
    op.drop_table("inboxes")
    inbox_provider.drop(op.get_bind(), checkfirst=True)
