"""Database configuration and session management."""
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import DATABASE_URL
from migrations import run_migrations

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    run_startup_migrations()


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _alembic_config() -> Config | None:
    root = _runtime_root()
    ini_path = root / "alembic.ini"
    script_path = root / "alembic"
    if ini_path.is_dir():
        ini_path = ini_path / "alembic.ini"
    if not ini_path.is_file() or not script_path.is_dir():
        return None

    config = Config(str(ini_path))
    config.set_main_option("script_location", str(script_path))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


def _has_table(table_name: str) -> bool:
    return inspect(engine).has_table(table_name)


def run_startup_migrations() -> None:
    config = _alembic_config()

    if config is None:
        run_migrations(engine)
        Base.metadata.create_all(bind=engine)
        return

    has_app_tables = _has_table("users") or _has_table("tasks")
    has_alembic_version = _has_table("alembic_version")

    if has_app_tables and not has_alembic_version:
        run_migrations(engine)
        Base.metadata.create_all(bind=engine)
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")
