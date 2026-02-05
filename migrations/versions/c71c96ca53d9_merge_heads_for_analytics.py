"""Merge heads for analytics

Revision ID: c71c96ca53d9
Revises: add_files_table, add_search_models
Create Date: 2026-02-05 08:43:15.020848

"""

# revision identifiers, used by Alembic.
revision = "c71c96ca53d9"
down_revision = ("add_files_table", "add_search_models")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema"""
    pass


def downgrade() -> None:
    """Downgrade database schema"""
    pass
