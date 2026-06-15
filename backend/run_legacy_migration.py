"""One-off helper for upgrading older SQLite databases before Alembic."""

from database import engine
from migrations import run_migrations


if __name__ == "__main__":
    run_migrations(engine)
