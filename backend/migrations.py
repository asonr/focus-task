"""Small SQLite migrations for local installs."""
from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        user_tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchall()
        if user_tables:
            user_columns = conn.execute(text("PRAGMA table_info('users')")).mappings().all()
            user_column_names = {column["name"] for column in user_columns}
            if "is_admin" not in user_column_names:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
                conn.execute(text("UPDATE users SET is_admin = 1 WHERE lower(username) = 'admin'"))
                conn.execute(text("UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)"))
            if "disabled" not in user_column_names:
                conn.execute(text("ALTER TABLE users ADD COLUMN disabled BOOLEAN NOT NULL DEFAULT 0"))

        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")).fetchall()
        if not tables:
            return

        task_columns = conn.execute(text("PRAGMA table_info('tasks')")).mappings().all()
        task_column_names = {column["name"] for column in task_columns}
        schedule_columns = {
            "start_at": "VARCHAR(20) NOT NULL DEFAULT ''",
            "notify_on_start": "BOOLEAN NOT NULL DEFAULT 1",
            "notify_on_due": "BOOLEAN NOT NULL DEFAULT 1",
            "notify_on_overdue": "BOOLEAN NOT NULL DEFAULT 1",
        }
        for column_name, definition in schedule_columns.items():
            if column_name not in task_column_names:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {column_name} {definition}"))

        indexes = conn.execute(text("PRAGMA index_list('tasks')")).mappings().all()
        has_global_client_unique = False
        has_user_client_unique = False
        for index in indexes:
            if not index["unique"]:
                continue
            columns = conn.execute(text(f"PRAGMA index_info('{index['name']}')")).mappings().all()
            column_names = [column["name"] for column in columns]
            if column_names == ["client_id"]:
                has_global_client_unique = True
                break
            if column_names == ["user_id", "client_id"]:
                has_user_client_unique = True

        if not has_global_client_unique:
            if not has_user_client_unique:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_tasks_user_client ON tasks (user_id, client_id)"))
            return

        conn.execute(text("ALTER TABLE tasks RENAME TO tasks_old"))
        conn.execute(text("""
            CREATE TABLE tasks (
                id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                client_id VARCHAR(36) NOT NULL,
                quadrant INTEGER NOT NULL,
                title VARCHAR(500) NOT NULL,
                notes TEXT NOT NULL,
                done BOOLEAN NOT NULL,
                start_at VARCHAR(20) NOT NULL,
                due VARCHAR(20) NOT NULL,
                tag VARCHAR(100) NOT NULL,
                repeat VARCHAR(20) NOT NULL,
                notify_on_start BOOLEAN NOT NULL,
                notify_on_due BOOLEAN NOT NULL,
                notify_on_overdue BOOLEAN NOT NULL,
                show_in_focus BOOLEAN NOT NULL,
                sort_order FLOAT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                done_at VARCHAR(30) NOT NULL,
                deleted BOOLEAN NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT uq_tasks_user_client UNIQUE (user_id, client_id)
            )
        """))
        conn.execute(text("""
            INSERT INTO tasks (
                id, user_id, client_id, quadrant, title, notes, done, start_at, due, tag, repeat,
                notify_on_start, notify_on_due, notify_on_overdue, show_in_focus,
                sort_order, created_at, updated_at, done_at, deleted
            )
            SELECT
                id, user_id, client_id, quadrant, title, notes, done, start_at, due, tag, repeat,
                notify_on_start, notify_on_due, notify_on_overdue, show_in_focus,
                sort_order, created_at, updated_at, done_at, deleted
            FROM tasks_old
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_id ON tasks (id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_user_id ON tasks (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_client_id ON tasks (client_id)"))
        conn.execute(text("DROP TABLE tasks_old"))
