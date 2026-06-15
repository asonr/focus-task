"""Small SQLite migrations for local installs."""
from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")).fetchall()
        if not tables:
            return

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
                due VARCHAR(20) NOT NULL,
                tag VARCHAR(100) NOT NULL,
                repeat VARCHAR(20) NOT NULL,
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
                id, user_id, client_id, quadrant, title, notes, done, due, tag, repeat,
                show_in_focus, sort_order, created_at, updated_at, done_at, deleted
            )
            SELECT
                id, user_id, client_id, quadrant, title, notes, done, due, tag, repeat,
                show_in_focus, sort_order, created_at, updated_at, done_at, deleted
            FROM tasks_old
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_id ON tasks (id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_user_id ON tasks (user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_client_id ON tasks (client_id)"))
        conn.execute(text("DROP TABLE tasks_old"))
