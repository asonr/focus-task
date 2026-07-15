"""Admin user management router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_admin_user, hash_password
from database import get_db
from models import Task, User
from schemas import AdminUserOut, UserAdminUpdate, UserPasswordReset

router = APIRouter(prefix="/api/users", tags=["users"])


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.is_admin == True, User.disabled == False).count()


def _get_target_user(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[AdminUserOut])
def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    rows = (
        db.query(User, func.count(Task.id).label("task_count"))
        .outerjoin(Task, Task.user_id == User.id)
        .group_by(User.id)
        .order_by(User.id)
        .all()
    )
    return [
        AdminUserOut(
            id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            disabled=user.disabled,
            created_at=user.created_at,
            task_count=task_count,
        )
        for user, task_count in rows
    ]


@router.patch("/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    body: UserAdminUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = _get_target_user(user_id, db)
    update_data = body.model_dump(exclude_unset=True)

    if user.id == current_user.id and update_data.get("disabled") is True:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    if user.id == current_user.id and update_data.get("is_admin") is False:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin privileges")

    would_be_active_admin = user.is_admin and not user.disabled
    next_is_admin = update_data.get("is_admin", user.is_admin)
    next_disabled = update_data.get("disabled", user.disabled)
    would_remove_active_admin = would_be_active_admin and (not next_is_admin or next_disabled)
    if would_remove_active_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="At least one active admin is required")

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    task_count = db.query(Task).filter(Task.user_id == user.id).count()
    return AdminUserOut(
        id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        disabled=user.disabled,
        created_at=user.created_at,
        task_count=task_count,
    )


@router.post("/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    body: UserPasswordReset,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = _get_target_user(user_id, db)
    user.hashed_password = hash_password(body.password)
    db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = _get_target_user(user_id, db)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if user.is_admin and not user.disabled and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="At least one active admin is required")

    deleted_tasks = db.query(Task).filter(Task.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"ok": True, "deleted_tasks": deleted_tasks}
