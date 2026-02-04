"""Add sender_id to notifications

Revision ID: 1b658662bd77
Revises: 344c745e1f4b
Create Date: 2026-02-04 05:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b658662bd77"
down_revision: str | None = "344c745e1f4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add sender_id column to notifications table"""
    # Add sender_id column
    op.add_column(
        "notifications",
        sa.Column(
            "sender_id", sa.Uuid(), nullable=True, comment="ID отправителя уведомления"
        ),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_notifications_sender_id_users",
        "notifications",
        "users",
        ["sender_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index
    op.create_index(
        "ix_notifications_sender_id", "notifications", ["sender_id"], unique=False
    )


def downgrade() -> None:
    """Remove sender_id column from notifications table"""
    # Drop index
    op.drop_index("ix_notifications_sender_id", table_name="notifications")

    # Drop foreign key
    op.drop_constraint(
        "fk_notifications_sender_id_users",
        table_name="notifications",
        type_="foreignkey",
    )

    # Drop column
    op.drop_column("notifications", "sender_id")
