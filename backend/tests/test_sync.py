import tempfile
import unittest
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth import hash_password
from database import Base, get_db
from main import app
from models import User


class SyncApiTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "test.db"
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
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
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


if __name__ == "__main__":
    unittest.main()
