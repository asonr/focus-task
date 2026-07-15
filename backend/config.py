"""Runtime configuration."""
import os
import secrets


DATABASE_URL = os.getenv("FOCUS_TASK_DATABASE_URL", "sqlite:///./todo.db")
SECRET_KEY = os.getenv("FOCUS_TASK_SECRET_KEY", "dev-" + secrets.token_urlsafe(32))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("FOCUS_TASK_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))
PASSWORD_MIN_LENGTH = int(os.getenv("FOCUS_TASK_PASSWORD_MIN_LENGTH", "8"))
BOOTSTRAP_ADMIN_USERNAME = os.getenv("FOCUS_TASK_BOOTSTRAP_ADMIN_USERNAME", "admin")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("FOCUS_TASK_BOOTSTRAP_ADMIN_PASSWORD", "")
