"""initial schema

Revision ID: 20261014_01
Revises:
Create Date: 2026-10-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20261014_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owner",
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_owner_username"), "owner", ["username"], unique=True)

    op.create_table(
        "ingestionjob",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestionjob_kind"), "ingestionjob", ["kind"], unique=False)
    op.create_index(op.f("ix_ingestionjob_status"), "ingestionjob", ["status"], unique=False)

    op.create_table(
        "repository",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("forks", sa.Integer(), nullable=False),
        sa.Column("open_issues", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["owner.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_full_name"), "repository", ["full_name"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_repository_full_name"), table_name="repository")
    op.drop_table("repository")
    op.drop_index(op.f("ix_ingestionjob_status"), table_name="ingestionjob")
    op.drop_index(op.f("ix_ingestionjob_kind"), table_name="ingestionjob")
    op.drop_table("ingestionjob")
    op.drop_index(op.f("ix_owner_username"), table_name="owner")
    op.drop_table("owner")
