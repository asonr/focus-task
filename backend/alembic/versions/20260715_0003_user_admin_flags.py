"""user admin and disabled flags

Revision ID: 20260715_0003
Revises: 20260612_0002
Create Date: 2026-07-15 15:15:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260715_0003"
down_revision = "20260612_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute("UPDATE users SET is_admin = 1 WHERE lower(username) = 'admin'")
    op.execute("UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("disabled")
        batch_op.drop_column("is_admin")
