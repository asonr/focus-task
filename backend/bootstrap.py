"""Startup bootstrap helpers."""
from sqlalchemy.orm import Session

from auth import hash_password
import config
from models import User


def bootstrap_admin_user(db: Session) -> None:
    """Create the initial admin only for a completely empty user table."""
    username = config.BOOTSTRAP_ADMIN_USERNAME.strip()
    password = config.BOOTSTRAP_ADMIN_PASSWORD

    if not username or not password:
        return
    if len(password) < config.PASSWORD_MIN_LENGTH:
        raise RuntimeError("FOCUS_TASK_BOOTSTRAP_ADMIN_PASSWORD is shorter than FOCUS_TASK_PASSWORD_MIN_LENGTH")
    if db.query(User.id).first() is not None:
        return

    db.add(
        User(
            username=username,
            hashed_password=hash_password(password),
            is_admin=True,
            disabled=False,
        )
    )
    db.commit()
