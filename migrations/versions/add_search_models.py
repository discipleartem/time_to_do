"""Add SearchIndex and SavedSearch models for advanced search

Revision ID: add_search_models
Revises: add_share_link_model
Create Date: 2026-02-04 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_search_models"
down_revision: str | None = "add_share_link_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create searchabletype enum
    searchabletype_enum = postgresql.ENUM(
        "task", "project", "sprint", "comment", name="searchabletype", create_type=True
    )
    searchabletype_enum.create(op.get_bind())

    # Create search_index table
    op.create_table(
        "search_index",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=False),
        sa.Column("entity_type", searchabletype_enum, nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("search_metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["sprints.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["comments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_search_index_entity_type"),
        "search_index",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_search_index_entity_id"), "search_index", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_search_index_project_id"), "search_index", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_search_index_user_id"), "search_index", ["user_id"], unique=False
    )

    # Create saved_searches table
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("filters", sa.Text(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_saved_searches_user_id"), "saved_searches", ["user_id"], unique=False
    )

    # Add saved_searches relationship to users table
    # Note: This requires updating the User model, but we'll handle that in the application code


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f("ix_saved_searches_user_id"), table_name="saved_searches")
    op.drop_table("saved_searches")

    op.drop_index(op.f("ix_search_index_user_id"), table_name="search_index")
    op.drop_index(op.f("ix_search_index_project_id"), table_name="search_index")
    op.drop_index(op.f("ix_search_index_entity_id"), table_name="search_index")
    op.drop_index(op.f("ix_search_index_entity_type"), table_name="search_index")
    op.drop_table("search_index")

    # Drop enum
    searchabletype_enum = postgresql.ENUM(
        "task", "project", "sprint", "comment", name="searchabletype", create_type=True
    )
    searchabletype_enum.drop(op.get_bind())
