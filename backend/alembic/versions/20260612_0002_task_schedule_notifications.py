"""task schedule and notification fields

Revision ID: 20260612_0002
Revises: 20260612_0001
Create Date: 2026-06-12 14:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260612_0002"
down_revision = "20260612_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
      batch_op.add_column(sa.Column("start_at", sa.String(length=20), nullable=False, server_default=""))
      batch_op.add_column(sa.Column("notify_on_start", sa.Boolean(), nullable=False, server_default=sa.true()))
      batch_op.add_column(sa.Column("notify_on_due", sa.Boolean(), nullable=False, server_default=sa.true()))
      batch_op.add_column(sa.Column("notify_on_overdue", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
      batch_op.drop_column("notify_on_overdue")
      batch_op.drop_column("notify_on_due")
      batch_op.drop_column("notify_on_start")
      batch_op.drop_column("start_at")
