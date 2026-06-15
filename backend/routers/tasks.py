"""Tasks router — CRUD and sync."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Task
from schemas import TaskCreate, TaskUpdate, TaskOut, TaskReorder, SyncPush, SyncPull
from auth import get_current_user
from time_utils import utc_now

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    include_deleted: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Task).filter(Task.user_id == current_user.id)
    if not include_deleted:
        q = q.filter(Task.deleted == False)
    return q.order_by(Task.sort_order, Task.created_at.desc()).all()


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Task).filter(Task.client_id == body.client_id, Task.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Task with this client_id already exists")
    task = Task(user_id=current_user.id, **body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = utc_now()
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.deleted = True
    task.updated_at = utc_now()
    db.commit()
    return {"ok": True}


@router.post("/reorder")
def reorder_tasks(body: TaskReorder, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for item in body.items:
        task = db.query(Task).filter(
            Task.client_id == item["client_id"],
            Task.user_id == current_user.id,
        ).first()
        if task:
            task.sort_order = item["sort_order"]
    db.commit()
    return {"ok": True}


# ─── Sync endpoints ───
@router.post("/sync/push", response_model=list[TaskOut])
def sync_push(body: SyncPush, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = []
    for task_in in body.tasks:
        existing = db.query(Task).filter(
            Task.client_id == task_in.client_id,
            Task.user_id == current_user.id,
        ).first()
        if existing:
            # Update existing
            for key, value in task_in.model_dump().items():
                setattr(existing, key, value)
            existing.updated_at = utc_now()
            results.append(existing)
        else:
            # Create new
            task = Task(user_id=current_user.id, **task_in.model_dump())
            db.add(task)
            results.append(task)
    db.commit()
    for t in results:
        db.refresh(t)
    return results


@router.post("/sync/pull", response_model=list[TaskOut])
def sync_pull(body: SyncPull, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Task).filter(Task.user_id == current_user.id)
    if body.since:
        q = q.filter(Task.updated_at >= body.since)
    return q.order_by(Task.updated_at.desc()).all()
