"""SQLite-backed persistent memory store for UMH.

Mirrors the task_store.py pattern: WAL mode, thread-safe singleton,
environment-configurable DB path.

Memories survive process restarts and provide keyword search across
content and tags.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field

from umh.core.clock import iso_now

_DEFAULT_DB_PATH = "/opt/OS/data/runtime/memory.sqlite"

VALID_MEMORY_TYPES = frozenset({"task", "summary", "insight", "system"})


@dataclass
class Memory:
    """A single memory entry."""

    id: str
    type: str
    content: str
    metadata: dict | None = None
    tags: list[str] = field(default_factory=list)
    created_at: str = ""


class MemoryPersistentStore:
    """SQLite-backed memory storage with keyword search."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.environ.get("UMH_MEMORY_DB_PATH", _DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        metadata = json.loads(row["metadata"]) if row["metadata"] else None
        tags = json.loads(row["tags"]) if row["tags"] else []
        return Memory(
            id=row["id"],
            type=row["type"],
            content=row["content"],
            metadata=metadata,
            tags=tags,
            created_at=row["created_at"],
        )

    def save_memory(
        self,
        type: str,
        content: str,
        metadata: dict | None = None,
        tags: list[str] | None = None,
    ) -> Memory:
        """Create and persist a new memory."""
        if type not in VALID_MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory type '{type}'. Must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))}"
            )
        memory = Memory(
            id=str(uuid.uuid4()),
            type=type,
            content=content,
            metadata=metadata,
            tags=tags or [],
            created_at=iso_now(),
        )
        metadata_json = json.dumps(memory.metadata) if memory.metadata else None
        tags_json = json.dumps(memory.tags)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO memories (id, type, content, metadata, tags, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        memory.id,
                        memory.type,
                        memory.content,
                        metadata_json,
                        tags_json,
                        memory.created_at,
                    ),
                )
                conn.commit()
        return memory

    def get_memory(self, memory_id: str) -> Memory | None:
        """Retrieve a memory by ID."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
                if row is None:
                    return None
                return self._row_to_memory(row)

    def list_memories(self, type: str | None = None, limit: int = 50) -> list[Memory]:
        """List memories, optionally filtered by type, most recent first."""
        with self._lock:
            with self._connect() as conn:
                if type is not None:
                    rows = conn.execute(
                        "SELECT * FROM memories WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                        (type, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                return [self._row_to_memory(r) for r in rows]

    def search_memories(self, query: str, limit: int = 10) -> list[Memory]:
        """Keyword search across content and tags columns."""
        pattern = f"%{query}%"
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE content LIKE ? OR tags LIKE ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (pattern, pattern, limit),
                ).fetchall()
                return [self._row_to_memory(r) for r in rows]

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if deleted."""
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.commit()
                return cursor.rowcount > 0

    def count_memories(self) -> int:
        """Return total number of stored memories."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) as cnt FROM memories").fetchone()
                return row["cnt"]


_store: MemoryPersistentStore | None = None
_store_lock = threading.Lock()


def get_memory_store() -> MemoryPersistentStore:
    """Get the singleton persistent memory store."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = MemoryPersistentStore()
    return _store


def reset_memory_store() -> None:
    """Clear the singleton (for testing)."""
    global _store
    with _store_lock:
        _store = None
