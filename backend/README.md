# Backend Notes

## Docker

The backend can run in Docker with the root compose file:

`docker compose up -d --build focus-task-api`

The container stores SQLite data in `/data/todo.db` through a named Docker volume. Full deployment notes are in `docs/docker-deploy.md`.

## Database migrations

The backend now uses Alembic for schema changes.

- Create or update the local schema with:
  `alembic upgrade head`
- Generate a new migration after model changes:
  `alembic revision --autogenerate -m "describe change"`

Latest task scheduling fields include `start_at`, `due` with minute precision, and per-task notification flags.

## Legacy SQLite upgrade

Older local databases that still use the global `tasks.client_id` unique constraint can be upgraded once with:

`python3 run_legacy_migration.py`

The startup script can run that helper before boot if needed:

`FOCUS_TASK_RUN_LEGACY_MIGRATION=1 ./start.sh`

## Local admin script

For local user cleanup and inspection:

- List users:
  `python3 admin_users.py list`
- Delete one user and their tasks:
  `python3 admin_users.py delete --username alice`
- Delete all users and tasks:
  `python3 admin_users.py purge --yes`
