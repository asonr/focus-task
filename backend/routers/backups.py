"""User data exports and administrator SQLite disaster-recovery snapshots."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import config
from auth import get_current_admin_user, get_current_user
from database import engine, get_db
from models import Task, User
from schemas import TaskBackup, UserBackup, UserBackupImport, UserBackupImportResult
from time_utils import utc_now

router = APIRouter(prefix="/api/backups", tags=["backups"])

_TASK_FIELDS = (
    "client_id", "quadrant", "title", "notes", "done", "start_at", "due", "tag", "repeat",
    "notify_on_start", "notify_on_due", "notify_on_overdue", "show_in_focus", "sort_order",
    "done_at", "deleted",
)


def _task_backup(task: Task) -> TaskBackup:
    return TaskBackup(**{field: getattr(task, field) for field in _TASK_FIELDS}, created_at=task.created_at, updated_at=task.updated_at)


def _apply_backup(task: Task, backup: TaskBackup) -> None:
    for field in _TASK_FIELDS:
        setattr(task, field, getattr(backup, field))
    if backup.created_at is not None:
        task.created_at = backup.created_at
    task.updated_at = backup.updated_at or utc_now()


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.get("/user", response_model=UserBackup)
def export_user_backup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.user_id == current_user.id).order_by(Task.created_at).all()
    return UserBackup(
        exported_at=utc_now(),
        username=current_user.username,
        tasks=[_task_backup(task) for task in tasks],
    )


@router.post("/user/import", response_model=UserBackupImportResult)
def import_user_backup(
    body: UserBackupImport,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = {
        task.client_id: task
        for task in db.query(Task).filter(Task.user_id == current_user.id).all()
    }
    created = updated = skipped = removed = 0

    if body.mode == "replace":
        removed = db.query(Task).filter(Task.user_id == current_user.id).delete(synchronize_session=False)
        existing = {}

    for backup_task in body.backup.tasks:
        task = existing.get(backup_task.client_id)
        if task is None:
            task = Task(user_id=current_user.id, client_id=backup_task.client_id)
            _apply_backup(task, backup_task)
            db.add(task)
            created += 1
            continue

        if _as_utc(backup_task.updated_at) < _as_utc(task.updated_at):
            skipped += 1
            continue
        _apply_backup(task, backup_task)
        updated += 1

    db.commit()
    return UserBackupImportResult(created=created, updated=updated, skipped=skipped, removed=removed)


def _database_path() -> Path:
    url = make_url(config.DATABASE_URL)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise HTTPException(status_code=501, detail="Server snapshots require a file-based SQLite database")
    return Path(url.database).resolve()


def _backup_dir() -> Path:
    path = Path(config.BACKUP_DIR).expanduser() if config.BACKUP_DIR else _database_path().parent / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _snapshot_name(prefix: str = "focus-task") -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.db"


def _prune_snapshots() -> None:
    keep = max(1, config.BACKUP_RETENTION_COUNT)
    snapshots = sorted(_backup_dir().glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    for expired in snapshots[keep:]:
        expired.unlink(missing_ok=True)


def _create_snapshot(prefix: str = "focus-task") -> Path:
    target = _backup_dir() / _snapshot_name(prefix)
    source = sqlite3.connect(str(_database_path()))
    destination = sqlite3.connect(str(target))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    _prune_snapshots()
    return target


def _snapshot_path(name: str) -> Path:
    if Path(name).name != name or not name.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid snapshot name")
    path = _backup_dir() / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return path


def _snapshot_info(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
    }


@router.get("/server")
def list_server_snapshots(current_user: User = Depends(get_current_admin_user)):
    _ = current_user
    snapshots = sorted(_backup_dir().glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [_snapshot_info(path) for path in snapshots]


@router.post("/server", status_code=status.HTTP_201_CREATED)
def create_server_snapshot(current_user: User = Depends(get_current_admin_user)):
    _ = current_user
    return _snapshot_info(_create_snapshot())


@router.get("/server/{name}")
def download_server_snapshot(name: str, current_user: User = Depends(get_current_admin_user)):
    _ = current_user
    path = _snapshot_path(name)
    return FileResponse(path, media_type="application/vnd.sqlite3", filename=path.name)


@router.delete("/server/{name}")
def delete_server_snapshot(name: str, current_user: User = Depends(get_current_admin_user)):
    _ = current_user
    _snapshot_path(name).unlink()
    return {"ok": True}


def _validate_database(path: Path) -> None:
    try:
        connection = sqlite3.connect(str(path))
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid SQLite database") from exc
    if not integrity or integrity[0] != "ok" or not {"users", "tasks"}.issubset(tables):
        raise HTTPException(status_code=400, detail="Backup database is incomplete or corrupted")


@router.put("/server/restore")
async def restore_server_snapshot(request: Request, current_user: User = Depends(get_current_admin_user)):
    _ = current_user
    content_length = int(request.headers.get("content-length", "0") or 0)
    if content_length > config.BACKUP_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Backup file is too large")
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Backup file is empty")
    if len(payload) > config.BACKUP_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Backup file is too large")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir=_backup_dir()) as uploaded:
        uploaded.write(payload)
        uploaded_path = Path(uploaded.name)

    try:
        _validate_database(uploaded_path)
        safety_snapshot = _create_snapshot("before-restore")
        source = sqlite3.connect(str(uploaded_path))
        destination = engine.raw_connection()
        try:
            source.backup(destination.driver_connection)
            destination.commit()
        finally:
            destination.close()
            source.close()
    finally:
        uploaded_path.unlink(missing_ok=True)

    return {"ok": True, "safety_snapshot": safety_snapshot.name}
