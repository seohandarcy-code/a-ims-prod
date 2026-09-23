"""add allowed_users (SSO access control)

Revision ID: 0002_add_allowed_users
Revises: 0001_initial
Create Date: 2026-09-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_allowed_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allowed_users",
        sa.Column("sso_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("team", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("allowed_users")
