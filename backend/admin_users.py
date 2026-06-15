"""Small admin script for local user cleanup and inspection."""
from __future__ import annotations

import argparse

from sqlalchemy import func, select

from database import SessionLocal
from models import Task, User


def list_users() -> int:
    with SessionLocal() as db:
        rows = db.execute(
            select(
                User.id,
                User.username,
                User.created_at,
                func.count(Task.id).label("task_count"),
            )
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
        ).all()

    if not rows:
        print("No users found.")
        return 0

    for row in rows:
        created_at = row.created_at.isoformat(sep=" ", timespec="seconds")
        print(f"id={row.id} username={row.username} created_at={created_at} tasks={row.task_count}")
    return 0


def delete_user(username: str) -> int:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user is None:
            print(f"User not found: {username}")
            return 1

        deleted_tasks = db.query(Task).filter(Task.user_id == user.id).delete(synchronize_session=False)
        db.delete(user)
        db.commit()

    print(f"Deleted user '{username}' and {deleted_tasks} related tasks.")
    return 0


def purge_users(confirmed: bool) -> int:
    if not confirmed:
        print("Refusing to purge without --yes.")
        return 1

    with SessionLocal() as db:
        deleted_tasks = db.query(Task).delete(synchronize_session=False)
        deleted_users = db.query(User).delete(synchronize_session=False)
        db.commit()

    print(f"Deleted {deleted_users} users and {deleted_tasks} tasks.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or clean local Focus Task users.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List local users and task counts.")

    delete_parser = subparsers.add_parser("delete", help="Delete one user and their tasks.")
    delete_parser.add_argument("--username", required=True, help="Username to delete.")

    purge_parser = subparsers.add_parser("purge", help="Delete every user and task.")
    purge_parser.add_argument("--yes", action="store_true", help="Confirm destructive purge.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list":
        return list_users()
    if args.command == "delete":
        return delete_user(args.username)
    if args.command == "purge":
        return purge_users(args.yes)

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
