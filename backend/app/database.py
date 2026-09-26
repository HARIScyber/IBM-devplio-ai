from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DB_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).resolve().parents[1] / "devpilot.db"))


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT NOT NULL,
            root TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT, repository_id TEXT, action TEXT NOT NULL,
            detail TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, repository_id TEXT NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, status TEXT NOT NULL,
            payload_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)


def save_repository(repo_id: str, name: str, source: str, root: str, metadata: dict[str, Any]) -> None:
    with connection() as db:
        db.execute("INSERT OR REPLACE INTO repositories(id,name,source,root,metadata_json) VALUES(?,?,?,?,?)",
                   (repo_id, name, source, root, json.dumps(metadata)))
        db.execute("INSERT INTO activity(repository_id,action,detail) VALUES(?,?,?)",
                   (repo_id, "Repository analyzed", f"Indexed {metadata.get('file_count', 0)} files from {name}"))


def get_repository(repo_id: str) -> dict[str, Any] | None:
    with connection() as db:
        row = db.execute("SELECT * FROM repositories WHERE id=?", (repo_id,)).fetchone()
    if not row:
        return None
    return {"id": row["id"], "name": row["name"], "source": row["source"],
            "root": row["root"], "created_at": row["created_at"], **json.loads(row["metadata_json"])}


def add_activity(repo_id: str | None, action: str, detail: str) -> None:
    with connection() as db:
        db.execute("INSERT INTO activity(repository_id,action,detail) VALUES(?,?,?)", (repo_id, action, detail))


def recent_activity(limit: int = 30) -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def save_chat(repo_id: str, question: str, answer: str) -> None:
    with connection() as db:
        db.execute("INSERT INTO chat_messages(repository_id,question,answer) VALUES(?,?,?)", (repo_id, question, answer))


def save_workflow(workflow: dict[str, Any]) -> None:
    with connection() as db:
        db.execute(
            "INSERT INTO workflows(id,repository_id,status,payload_json,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, "
            "payload_json=excluded.payload_json, updated_at=excluded.updated_at",
            (workflow["workflow_id"], workflow["repository_id"], workflow["status"],
             json.dumps(workflow), workflow["created_at"], workflow["updated_at"]),
        )


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    with connection() as db:
        row = db.execute("SELECT payload_json FROM workflows WHERE id=?", (workflow_id,)).fetchone()
    return json.loads(row["payload_json"]) if row else None


def recent_workflows(limit: int = 20, repository_id: str | None = None) -> list[dict[str, Any]]:
    with connection() as db:
        if repository_id:
            rows = db.execute("SELECT payload_json FROM workflows WHERE repository_id=? ORDER BY updated_at DESC LIMIT ?", (repository_id, limit)).fetchall()
        else:
            rows = db.execute("SELECT payload_json FROM workflows ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]
