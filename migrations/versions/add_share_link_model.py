"""Add ShareLink model for external sharing

Revision ID: add_share_link_model
Revises: 1b658662bd77
Create Date: 2026-02-04 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_share_link_model"
down_revision: str | None = "1b658662bd77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create ENUM types
    shareabletype_enum = postgresql.ENUM(
        "project", "task", "sprint", name="shareabletype", create_type=True
    )
    shareabletype_enum.create(op.get_bind())

    sharepermission_enum = postgresql.ENUM(
        "view", "comment", name="sharepermission", create_type=True
    )
    sharepermission_enum.create(op.get_bind())

    # Create share_links table
    op.create_table(
        "share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("shareable_type", shareabletype_enum, nullable=False),
        sa.Column("shareable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission", sharepermission_enum, nullable=False),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_views", sa.Integer(), nullable=True),
        sa.Column("current_views", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_share_links_token"), "share_links", ["token"], unique=False
    )


def downgrade() -> None:
    # Drop table
    op.drop_index(op.f("ix_share_links_token"), table_name="share_links")
    op.drop_table("share_links")

    # Drop ENUM types
    sharepermission_enum = postgresql.ENUM(name="sharepermission")
    sharepermission_enum.drop(op.get_bind())

    shareabletype_enum = postgresql.ENUM(name="shareabletype")
    shareabletype_enum.drop(op.get_bind())
