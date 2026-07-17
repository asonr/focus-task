import tempfile
import unittest
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from auth import hash_password
from bootstrap import bootstrap_admin_user
import config
from database import Base, get_db
from main import app
from models import User
from routers import backups as backups_router
from migrations import run_migrations


class SyncApiTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "test.db"
        self.original_database_url = config.DATABASE_URL
        self.original_backup_dir = config.BACKUP_DIR
        config.DATABASE_URL = f"sqlite:///{db_path}"
        config.BACKUP_DIR = str(Path(self.tmpdir.name) / "backups")
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.TestingSessionLocal = TestingSessionLocal
        self.original_backup_engine = backups_router.engine
        backups_router.engine = engine
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        config.DATABASE_URL = self.original_database_url
        config.BACKUP_DIR = self.original_backup_dir
        backups_router.engine = self.original_backup_engine
        self.tmpdir.cleanup()

    def auth_headers(self, username="alice"):
        password = "password123"
        self.client.post("/api/auth/register", json={"username": username, "password": password})
        res = self.client.post("/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(res.status_code, 200)
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def task_payload(self, client_id="task-1", **overrides):
        payload = {
            "client_id": client_id,
            "quadrant": 1,
            "title": "Write test",
            "notes": "",
            "done": False,
            "start_at": "",
            "due": "",
            "tag": "",
            "repeat": "none",
            "notify_on_start": True,
            "notify_on_due": True,
            "notify_on_overdue": True,
            "show_in_focus": False,
            "sort_order": 0,
            "done_at": "",
        }
        payload.update(overrides)
        return payload

    def test_sync_push_accepts_deleted_tombstone(self):
        headers = self.auth_headers()
        create_res = self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload()]},
            headers=headers,
        )
        self.assertEqual(create_res.status_code, 200)
        self.assertFalse(create_res.json()[0]["deleted"])

        delete_res = self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(deleted=True)]},
            headers=headers,
        )
        self.assertEqual(delete_res.status_code, 200)
        self.assertTrue(delete_res.json()[0]["deleted"])

        list_res = self.client.get("/api/tasks?include_deleted=true", headers=headers)
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.json()), 1)
        self.assertTrue(list_res.json()[0]["deleted"])

    def test_sync_pull_returns_deleted_changes_since_cursor(self):
        headers = self.auth_headers()
        create_res = self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload()]},
            headers=headers,
        )
        cursor = create_res.json()[0]["updated_at"]

        delete_res = self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(deleted=True)]},
            headers=headers,
        )
        self.assertGreaterEqual(delete_res.json()[0]["updated_at"], cursor)

        pull_res = self.client.post("/api/tasks/sync/pull", json={"since": cursor}, headers=headers)
        self.assertEqual(pull_res.status_code, 200)
        self.assertEqual(len(pull_res.json()), 1)
        self.assertTrue(pull_res.json()[0]["deleted"])

    def test_client_ids_are_scoped_per_user(self):
        alice_headers = self.auth_headers("alice")
        bob_headers = self.auth_headers("bob")

        alice_res = self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="shared-client-id", title="Alice")]},
            headers=alice_headers,
        )
        bob_res = self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="shared-client-id", title="Bob")]},
            headers=bob_headers,
        )

        self.assertEqual(alice_res.status_code, 200)
        self.assertEqual(bob_res.status_code, 200)
        self.assertEqual(alice_res.json()[0]["title"], "Alice")
        self.assertEqual(bob_res.json()[0]["title"], "Bob")

    def test_user_backup_export_and_merge_are_scoped_to_current_user(self):
        alice_headers = self.auth_headers("alice")
        bob_headers = self.auth_headers("bob")
        self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="alice-task", title="Alice")]},
            headers=alice_headers,
        )
        self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="bob-task", title="Bob")]},
            headers=bob_headers,
        )

        export_res = self.client.get("/api/backups/user", headers=alice_headers)
        self.assertEqual(export_res.status_code, 200)
        backup = export_res.json()
        self.assertEqual(backup["format"], "focus-task-backup")
        self.assertEqual(backup["version"], 1)
        self.assertEqual([task["client_id"] for task in backup["tasks"]], ["alice-task"])

        backup["tasks"].append(self.task_payload(client_id="imported-task", title="Imported"))
        import_res = self.client.post(
            "/api/backups/user/import",
            json={"mode": "merge", "backup": backup},
            headers=alice_headers,
        )
        self.assertEqual(import_res.status_code, 200)
        self.assertEqual(import_res.json()["created"], 1)

        alice_tasks = self.client.get("/api/tasks?include_deleted=true", headers=alice_headers).json()
        bob_tasks = self.client.get("/api/tasks?include_deleted=true", headers=bob_headers).json()
        self.assertEqual({task["client_id"] for task in alice_tasks}, {"alice-task", "imported-task"})
        self.assertEqual({task["client_id"] for task in bob_tasks}, {"bob-task"})

    def test_user_backup_replace_removes_only_current_users_tasks(self):
        alice_headers = self.auth_headers("alice")
        bob_headers = self.auth_headers("bob")
        self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="old-alice")]},
            headers=alice_headers,
        )
        self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="bob-task")]},
            headers=bob_headers,
        )
        backup = {
            "format": "focus-task-backup",
            "version": 1,
            "exported_at": "2026-07-17T00:00:00Z",
            "username": "alice",
            "tasks": [self.task_payload(client_id="restored-alice", title="Restored")],
        }

        replace_res = self.client.post(
            "/api/backups/user/import",
            json={"mode": "replace", "backup": backup},
            headers=alice_headers,
        )
        self.assertEqual(replace_res.status_code, 200)
        self.assertEqual(replace_res.json()["removed"], 1)
        alice_tasks = self.client.get("/api/tasks?include_deleted=true", headers=alice_headers).json()
        bob_tasks = self.client.get("/api/tasks?include_deleted=true", headers=bob_headers).json()
        self.assertEqual([task["client_id"] for task in alice_tasks], ["restored-alice"])
        self.assertEqual([task["client_id"] for task in bob_tasks], ["bob-task"])

    def test_regular_user_cannot_manage_server_snapshots(self):
        self.auth_headers("admin")
        bob_headers = self.auth_headers("bob")
        res = self.client.get("/api/backups/server", headers=bob_headers)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_create_download_and_delete_server_snapshot(self):
        admin_headers = self.auth_headers("admin")
        create_res = self.client.post("/api/backups/server", headers=admin_headers)
        self.assertEqual(create_res.status_code, 201)
        snapshot = create_res.json()
        self.assertTrue(snapshot["name"].endswith(".db"))
        self.assertGreater(snapshot["size"], 0)

        list_res = self.client.get("/api/backups/server", headers=admin_headers)
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual([item["name"] for item in list_res.json()], [snapshot["name"]])

        download_res = self.client.get(f"/api/backups/server/{snapshot['name']}", headers=admin_headers)
        self.assertEqual(download_res.status_code, 200)
        self.assertGreater(len(download_res.content), 0)

        delete_res = self.client.delete(f"/api/backups/server/{snapshot['name']}", headers=admin_headers)
        self.assertEqual(delete_res.status_code, 200)
        self.assertEqual(self.client.get("/api/backups/server", headers=admin_headers).json(), [])

    def test_admin_restore_rolls_back_database_and_creates_safety_snapshot(self):
        admin_headers = self.auth_headers("admin")
        create_res = self.client.post("/api/backups/server", headers=admin_headers)
        snapshot_name = create_res.json()["name"]
        snapshot_bytes = self.client.get(f"/api/backups/server/{snapshot_name}", headers=admin_headers).content

        self.client.post(
            "/api/tasks/sync/push",
            json={"tasks": [self.task_payload(client_id="after-snapshot")]},
            headers=admin_headers,
        )
        self.assertEqual(len(self.client.get("/api/tasks", headers=admin_headers).json()), 1)

        restore_res = self.client.put(
            "/api/backups/server/restore",
            content=snapshot_bytes,
            headers={**admin_headers, "Content-Type": "application/vnd.sqlite3"},
        )
        self.assertEqual(restore_res.status_code, 200)
        self.assertTrue(restore_res.json()["safety_snapshot"].startswith("before-restore-"))
        self.assertEqual(self.client.get("/api/tasks", headers=admin_headers).json(), [])
        snapshots = self.client.get("/api/backups/server", headers=admin_headers).json()
        self.assertEqual(len(snapshots), 2)

    def test_login_accepts_legacy_short_password_accounts(self):
        with self.TestingSessionLocal() as db:
            user = User(username="legacy-admin", hashed_password=hash_password("12345"))
            db.add(user)
            db.commit()

        res = self.client.post("/api/auth/login", json={"username": "legacy-admin", "password": "12345"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.json())

    def test_sync_round_trip_preserves_schedule_and_notification_fields(self):
        headers = self.auth_headers()
        create_res = self.client.post(
            "/api/tasks/sync/push",
            json={
                "tasks": [
                    self.task_payload(
                        client_id="task-with-times",
                        start_at="2026-06-12T09:30",
                        due="2026-06-12T18:00",
                        notify_on_start=True,
                        notify_on_due=False,
                        notify_on_overdue=True,
                    )
                ]
            },
            headers=headers,
        )
        self.assertEqual(create_res.status_code, 200)
        created = create_res.json()[0]
        self.assertEqual(created["start_at"], "2026-06-12T09:30")
        self.assertEqual(created["due"], "2026-06-12T18:00")
        self.assertTrue(created["notify_on_start"])
        self.assertFalse(created["notify_on_due"])
        self.assertTrue(created["notify_on_overdue"])

        pull_res = self.client.post("/api/tasks/sync/pull", json={}, headers=headers)
        self.assertEqual(pull_res.status_code, 200)
        task = pull_res.json()[0]
        self.assertEqual(task["start_at"], "2026-06-12T09:30")
        self.assertEqual(task["due"], "2026-06-12T18:00")

    def test_reorder_updates_sort_order_and_timestamp(self):
        headers = self.auth_headers()
        create_res = self.client.post(
            "/api/tasks/sync/push",
            json={
                "tasks": [
                    self.task_payload(client_id="task-a", title="A", sort_order=0),
                    self.task_payload(client_id="task-b", title="B", sort_order=1),
                ]
            },
            headers=headers,
        )
        self.assertEqual(create_res.status_code, 200)
        original_updated_at = {task["client_id"]: task["updated_at"] for task in create_res.json()}

        reorder_res = self.client.post(
            "/api/tasks/reorder",
            json={
                "items": [
                    {"client_id": "task-b", "sort_order": 0},
                    {"client_id": "task-a", "sort_order": 1},
                ]
            },
            headers=headers,
        )
        self.assertEqual(reorder_res.status_code, 200)

        list_res = self.client.get("/api/tasks?include_deleted=true", headers=headers)
        self.assertEqual(list_res.status_code, 200)
        tasks = {task["client_id"]: task for task in list_res.json()}
        self.assertEqual(tasks["task-b"]["sort_order"], 0)
        self.assertEqual(tasks["task-a"]["sort_order"], 1)
        self.assertGreaterEqual(tasks["task-b"]["updated_at"], original_updated_at["task-b"])
        self.assertGreaterEqual(tasks["task-a"]["updated_at"], original_updated_at["task-a"])

    def test_admin_can_list_users_and_regular_user_cannot(self):
        admin_headers = self.auth_headers("admin")
        bob_headers = self.auth_headers("bob")

        admin_res = self.client.get("/api/users", headers=admin_headers)
        self.assertEqual(admin_res.status_code, 200)
        users = {user["username"]: user for user in admin_res.json()}
        self.assertTrue(users["admin"]["is_admin"])
        self.assertFalse(users["bob"]["is_admin"])

        bob_res = self.client.get("/api/users", headers=bob_headers)
        self.assertEqual(bob_res.status_code, 403)

    def test_admin_can_disable_reset_password_and_delete_user(self):
        admin_headers = self.auth_headers("admin")
        self.auth_headers("bob")

        users_res = self.client.get("/api/users", headers=admin_headers)
        bob = next(user for user in users_res.json() if user["username"] == "bob")

        disable_res = self.client.patch(
            f"/api/users/{bob['id']}",
            json={"disabled": True},
            headers=admin_headers,
        )
        self.assertEqual(disable_res.status_code, 200)
        self.assertTrue(disable_res.json()["disabled"])

        disabled_login = self.client.post("/api/auth/login", json={"username": "bob", "password": "password123"})
        self.assertEqual(disabled_login.status_code, 403)

        reset_res = self.client.post(
            f"/api/users/{bob['id']}/reset-password",
            json={"password": "newpassword123"},
            headers=admin_headers,
        )
        self.assertEqual(reset_res.status_code, 200)

        enable_res = self.client.patch(
            f"/api/users/{bob['id']}",
            json={"disabled": False},
            headers=admin_headers,
        )
        self.assertEqual(enable_res.status_code, 200)

        new_login = self.client.post("/api/auth/login", json={"username": "bob", "password": "newpassword123"})
        self.assertEqual(new_login.status_code, 200)

        delete_res = self.client.delete(f"/api/users/{bob['id']}", headers=admin_headers)
        self.assertEqual(delete_res.status_code, 200)

        users_after = self.client.get("/api/users", headers=admin_headers)
        self.assertNotIn("bob", {user["username"] for user in users_after.json()})

    def test_admin_cannot_disable_or_delete_self(self):
        admin_headers = self.auth_headers("admin")
        users_res = self.client.get("/api/users", headers=admin_headers)
        admin = next(user for user in users_res.json() if user["username"] == "admin")

        disable_res = self.client.patch(
            f"/api/users/{admin['id']}",
            json={"disabled": True},
            headers=admin_headers,
        )
        self.assertEqual(disable_res.status_code, 400)

        delete_res = self.client.delete(f"/api/users/{admin['id']}", headers=admin_headers)
        self.assertEqual(delete_res.status_code, 400)

    def test_bootstrap_admin_user_creates_initial_admin_only_once(self):
        original_username = config.BOOTSTRAP_ADMIN_USERNAME
        original_password = config.BOOTSTRAP_ADMIN_PASSWORD
        config.BOOTSTRAP_ADMIN_USERNAME = "admin"
        config.BOOTSTRAP_ADMIN_PASSWORD = "admin123"
        try:
            with self.TestingSessionLocal() as db:
                bootstrap_admin_user(db)
                bootstrap_admin_user(db)
                users = db.query(User).all()
                self.assertEqual(len(users), 1)
                self.assertEqual(users[0].username, "admin")
                self.assertTrue(users[0].is_admin)
                self.assertFalse(users[0].disabled)
        finally:
            config.BOOTSTRAP_ADMIN_USERNAME = original_username
            config.BOOTSTRAP_ADMIN_PASSWORD = original_password

    def test_legacy_migration_adds_schedule_and_notification_columns(self):
        legacy_path = Path(self.tmpdir.name) / "legacy.db"
        legacy_engine = create_engine(f"sqlite:///{legacy_path}")
        with legacy_engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    client_id VARCHAR(36) NOT NULL UNIQUE,
                    quadrant INTEGER NOT NULL DEFAULT 1,
                    title VARCHAR(500) NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    done BOOLEAN NOT NULL DEFAULT 0,
                    due VARCHAR(20) NOT NULL DEFAULT '',
                    tag VARCHAR(100) NOT NULL DEFAULT '',
                    repeat VARCHAR(20) NOT NULL DEFAULT 'none',
                    show_in_focus BOOLEAN NOT NULL DEFAULT 0,
                    sort_order FLOAT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    done_at VARCHAR(30) NOT NULL DEFAULT '',
                    deleted BOOLEAN NOT NULL DEFAULT 0
                )
            """))

        run_migrations(legacy_engine)
        columns = {column["name"] for column in inspect(legacy_engine).get_columns("tasks")}
        self.assertTrue({
            "start_at", "notify_on_start", "notify_on_due", "notify_on_overdue"
        }.issubset(columns))
        unique_constraints = inspect(legacy_engine).get_unique_constraints("tasks")
        unique_indexes = inspect(legacy_engine).get_indexes("tasks")
        unique_column_sets = {
            tuple(item["column_names"])
            for item in [*unique_constraints, *unique_indexes]
            if item.get("unique", True)
        }
        self.assertIn(("user_id", "client_id"), unique_column_sets)
        legacy_engine.dispose()


if __name__ == "__main__":
    unittest.main()
