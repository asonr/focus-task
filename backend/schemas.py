"""Pydantic schemas for request/response validation."""
from datetime import datetime
from pydantic import BaseModel, Field

from config import PASSWORD_MIN_LENGTH


# ─── Auth ───
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=100)


class UserLogin(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    disabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserOut(UserOut):
    task_count: int = 0


class UserAdminUpdate(BaseModel):
    is_admin: bool | None = None
    disabled: bool | None = None


class UserPasswordReset(BaseModel):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ─── Task ───
class TaskCreate(BaseModel):
    client_id: str
    quadrant: int = Field(1, ge=1, le=4)
    title: str = Field("", max_length=500)
    notes: str = ""
    done: bool = False
    start_at: str = ""
    due: str = ""
    tag: str = ""
    repeat: str = "none"
    notify_on_start: bool = True
    notify_on_due: bool = True
    notify_on_overdue: bool = True
    show_in_focus: bool = False
    sort_order: float = 0
    done_at: str = ""


class TaskUpdate(BaseModel):
    quadrant: int | None = Field(None, ge=1, le=4)
    title: str | None = Field(None, max_length=500)
    notes: str | None = None
    done: bool | None = None
    start_at: str | None = None
    due: str | None = None
    tag: str | None = None
    repeat: str | None = None
    notify_on_start: bool | None = None
    notify_on_due: bool | None = None
    notify_on_overdue: bool | None = None
    show_in_focus: bool | None = None
    sort_order: float | None = None
    done_at: str | None = None
    deleted: bool | None = None


class TaskSyncIn(TaskCreate):
    deleted: bool = False


class TaskOut(BaseModel):
    id: int
    client_id: str
    quadrant: int
    title: str
    notes: str
    done: bool
    start_at: str
    due: str
    tag: str
    repeat: str
    notify_on_start: bool
    notify_on_due: bool
    notify_on_overdue: bool
    show_in_focus: bool
    sort_order: float
    done_at: str
    deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskReorderItem(BaseModel):
    client_id: str
    sort_order: float


class TaskReorder(BaseModel):
    items: list[TaskReorderItem]


# ─── Sync ───
class SyncPush(BaseModel):
    tasks: list[TaskSyncIn]


class SyncPull(BaseModel):
    since: datetime | None = None
