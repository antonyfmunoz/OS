"""SQLite-backed approval persistence for cross-process durability.

Provides SQLiteApprovalBackend that stores approval state in a local
SQLite database. WAL mode enables concurrent read access from multiple
processes (CLI, runtime, future API).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Protocol

from umh.execution.approval import ApprovalRequest, ApprovalStatus

_DEFAULT_DB_PATH = "/opt/OS/data/runtime/approvals.sqlite"


class ApprovalBackend(Protocol):
    """Storage backend protocol for approval requests."""

    def save(self, req: ApprovalRequest) -> None: ...
    def update_status(self, approval_id: str, status: ApprovalStatus) -> None: ...
    def update_actor(self, approval_id: str, field: str, actor_id: str) -> None: ...
    def get(self, approval_id: str) -> ApprovalRequest | None: ...
    def list_all(self) -> list[ApprovalRequest]: ...
    def list_by_status(self, status: ApprovalStatus) -> list[ApprovalRequest]: ...
    def get_counters(self) -> dict[str, int]: ...
    def increment_counter(self, counter: str) -> None: ...
    def reset(self) -> None: ...


class InMemoryApprovalBackend:
    """In-memory backend for testing. No persistence."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._counters: dict[str, int] = {"consumed": 0, "denied": 0, "expired": 0}

    def save(self, req: ApprovalRequest) -> None:
        self._requests[req.id] = req

    def update_status(self, approval_id: str, status: ApprovalStatus) -> None:
        if approval_id in self._requests:
            self._requests[approval_id].status = status

    def update_actor(self, approval_id: str, field: str, actor_id: str) -> None:
        req = self._requests.get(approval_id)
        if req is not None and field in ("requested_by", "approved_by"):
            setattr(req, field, actor_id)

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._requests.get(approval_id)

    def list_all(self) -> list[ApprovalRequest]:
        return list(self._requests.values())

    def list_by_status(self, status: ApprovalStatus) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == status]

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def increment_counter(self, counter: str) -> None:
        self._counters[counter] = self._counters.get(counter, 0) + 1

    def reset(self) -> None:
        self._requests.clear()
        self._counters = {"consumed": 0, "denied": 0, "expired": 0}


class SQLiteApprovalBackend:
    """SQLite-backed approval storage for cross-process durability."""

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    capability_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL DEFAULT 'high',
                    inputs_summary TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    updated_at TEXT NOT NULL,
                    requested_by TEXT NOT NULL DEFAULT '',
                    approved_by TEXT NOT NULL DEFAULT ''
                )
            """)
            # Migrate existing tables missing new columns
            existing = {row[1] for row in conn.execute("PRAGMA table_info(approvals)").fetchall()}
            if "requested_by" not in existing:
                conn.execute(
                    "ALTER TABLE approvals ADD COLUMN requested_by TEXT NOT NULL DEFAULT ''"
                )
            if "approved_by" not in existing:
                conn.execute(
                    "ALTER TABLE approvals ADD COLUMN approved_by TEXT NOT NULL DEFAULT ''"
                )

            conn.execute("""
                CREATE TABLE IF NOT EXISTS approval_counters (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute(
                "INSERT OR IGNORE INTO approval_counters (name, value) VALUES ('consumed', 0)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO approval_counters (name, value) VALUES ('denied', 0)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO approval_counters (name, value) VALUES ('expired', 0)"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_request(self, row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            id=row["id"],
            execution_id=row["execution_id"],
            operation=row["operation"],
            capability_type=row["capability_type"],
            risk_level=row["risk_level"],
            inputs_summary=row["inputs_summary"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            status=ApprovalStatus(row["status"]),
            requested_by=row["requested_by"],
            approved_by=row["approved_by"],
        )

    def save(self, req: ApprovalRequest) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO approvals
                       (id, execution_id, operation, capability_type, risk_level,
                        inputs_summary, created_at, expires_at, status, updated_at,
                        requested_by, approved_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        req.id,
                        req.execution_id,
                        req.operation,
                        req.capability_type,
                        req.risk_level,
                        req.inputs_summary,
                        req.created_at,
                        req.expires_at,
                        req.status.value,
                        now,
                        req.requested_by,
                        req.approved_by,
                    ),
                )
                conn.commit()

    def update_status(self, approval_id: str, status: ApprovalStatus) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE approvals SET status = ?, updated_at = ? WHERE id = ?",
                    (status.value, now, approval_id),
                )
                conn.commit()

    def update_actor(self, approval_id: str, field: str, actor_id: str) -> None:
        if field not in ("requested_by", "approved_by"):
            return
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE approvals SET {field} = ?, updated_at = ? WHERE id = ?",
                    (actor_id, now, approval_id),
                )
                conn.commit()

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM approvals WHERE id = ?", (approval_id,)
                ).fetchone()
                if row is None:
                    return None
                return self._row_to_request(row)

    def list_all(self) -> list[ApprovalRequest]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute("SELECT * FROM approvals ORDER BY created_at DESC").fetchall()
                return [self._row_to_request(r) for r in rows]

    def list_by_status(self, status: ApprovalStatus) -> list[ApprovalRequest]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM approvals WHERE status = ? ORDER BY created_at DESC",
                    (status.value,),
                ).fetchall()
                return [self._row_to_request(r) for r in rows]

    def get_counters(self) -> dict[str, int]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute("SELECT name, value FROM approval_counters").fetchall()
                return {row["name"]: row["value"] for row in rows}

    def increment_counter(self, counter: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE approval_counters SET value = value + 1 WHERE name = ?",
                    (counter,),
                )
                conn.commit()

    def reset(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM approvals")
                conn.execute("UPDATE approval_counters SET value = 0")
                conn.commit()
