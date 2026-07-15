"""SQLAlchemy models."""
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, DateTime, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from time_utils import utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_tasks_user_client"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    quadrant: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    start_at: Mapped[str] = mapped_column(String(20), default="")
    due: Mapped[str] = mapped_column(String(20), default="")
    tag: Mapped[str] = mapped_column(String(100), default="")
    repeat: Mapped[str] = mapped_column(String(20), default="none")
    notify_on_start: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_due: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_overdue: Mapped[bool] = mapped_column(Boolean, default=True)
    show_in_focus: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    done_at: Mapped[str] = mapped_column(String(30), default="")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
