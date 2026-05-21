"""UMH Identity — structured actor identity with scoped permissions.

Every API action is attributable to an identity. Identities have scoped
permissions that determine what they can do through the control plane.

Scopes:
    execute          — POST /execute
    approvals:read   — GET /approvals, GET /approvals/{id}
    approvals:write  — POST /approvals/{id}/approve, POST /approvals/{id}/deny
    metrics:read     — GET /metrics
    admin            — all operations + identity management
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

_DEFAULT_DB_PATH = "/opt/OS/data/runtime/identities.sqlite"

VALID_SCOPES = frozenset(
    {
        "execute",
        "approvals:read",
        "approvals:write",
        "metrics:read",
        "memory:read",
        "memory:write",
        "admin",
    }
)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


@dataclass
class Identity:
    id: str
    name: str
    api_key_hash: str
    scopes: list[str]
    created_at: str
    status: str = "active"

    def has_scope(self, scope: str) -> bool:
        if "admin" in self.scopes:
            return True
        return scope in self.scopes

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "scopes": self.scopes,
            "created_at": self.created_at,
            "status": self.status,
        }


class IdentityStore:
    """SQLite-backed identity store."""

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    api_key_hash TEXT NOT NULL UNIQUE,
                    scopes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_identity(self, row: sqlite3.Row) -> Identity:
        scopes_str = row["scopes"]
        scopes = [s.strip() for s in scopes_str.split(",") if s.strip()] if scopes_str else []
        return Identity(
            id=row["id"],
            name=row["name"],
            api_key_hash=row["api_key_hash"],
            scopes=scopes,
            created_at=row["created_at"],
            status=row["status"],
        )

    def create_identity(
        self,
        name: str,
        scopes: list[str],
    ) -> tuple[Identity, str]:
        """Create a new identity. Returns (identity, raw_api_key)."""
        for s in scopes:
            if s not in VALID_SCOPES:
                raise ValueError(f"Invalid scope: {s}")

        raw_key = f"umh_{secrets.token_hex(24)}"
        key_hash = hash_key(raw_key)
        identity_id = f"id_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        scopes_str = ",".join(scopes)

        identity = Identity(
            id=identity_id,
            name=name,
            api_key_hash=key_hash,
            scopes=scopes,
            created_at=now,
        )

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO identities (id, name, api_key_hash, scopes, created_at, status)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (identity_id, name, key_hash, scopes_str, now, "active"),
                )
                conn.commit()

        return identity, raw_key

    def authenticate(self, raw_key: str) -> Identity | None:
        """Authenticate by raw API key. Returns Identity or None."""
        key_hash = hash_key(raw_key)
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM identities WHERE api_key_hash = ? AND status = 'active'",
                    (key_hash,),
                ).fetchone()
                if row is None:
                    return None
                return self._row_to_identity(row)

    def get(self, identity_id: str) -> Identity | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM identities WHERE id = ?", (identity_id,)
                ).fetchone()
                if row is None:
                    return None
                return self._row_to_identity(row)

    def list_identities(self) -> list[Identity]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute("SELECT * FROM identities ORDER BY created_at DESC").fetchall()
                return [self._row_to_identity(r) for r in rows]

    def get_by_name(self, name: str) -> Identity | None:
        """Look up an active identity by name."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM identities WHERE name = ? AND status = 'active'",
                    (name,),
                ).fetchone()
                if row is None:
                    return None
                return self._row_to_identity(row)

    def get_or_create(
        self,
        name: str,
        scopes: list[str] | None = None,
    ) -> tuple[Identity, str | None]:
        """Return existing identity by name, or create one.

        Returns (identity, raw_api_key_or_None).  raw_api_key is only
        returned when a new identity is created.
        """
        existing = self.get_by_name(name)
        if existing is not None:
            return existing, None
        return self.create_identity(name, scopes or ["execute"])

    def disable_identity(self, identity_id: str) -> bool:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE identities SET status = 'disabled' WHERE id = ?",
                    (identity_id,),
                )
                conn.commit()
                return cursor.rowcount > 0

    def reset(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM identities")
                conn.commit()


class InMemoryIdentityStore:
    """In-memory identity store for testing."""

    def __init__(self) -> None:
        self._identities: dict[str, Identity] = {}
        self._key_map: dict[str, str] = {}

    def create_identity(
        self,
        name: str,
        scopes: list[str],
    ) -> tuple[Identity, str]:
        for s in scopes:
            if s not in VALID_SCOPES:
                raise ValueError(f"Invalid scope: {s}")

        raw_key = f"umh_{secrets.token_hex(24)}"
        key_hash = hash_key(raw_key)
        identity_id = f"id_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        identity = Identity(
            id=identity_id,
            name=name,
            api_key_hash=key_hash,
            scopes=scopes,
            created_at=now,
        )
        self._identities[identity_id] = identity
        self._key_map[key_hash] = identity_id
        return identity, raw_key

    def authenticate(self, raw_key: str) -> Identity | None:
        key_hash = hash_key(raw_key)
        identity_id = self._key_map.get(key_hash)
        if identity_id is None:
            return None
        identity = self._identities.get(identity_id)
        if identity is None or identity.status != "active":
            return None
        return identity

    def get(self, identity_id: str) -> Identity | None:
        return self._identities.get(identity_id)

    def list_identities(self) -> list[Identity]:
        return list(self._identities.values())

    def get_by_name(self, name: str) -> Identity | None:
        for identity in self._identities.values():
            if identity.name == name and identity.status == "active":
                return identity
        return None

    def get_or_create(
        self,
        name: str,
        scopes: list[str] | None = None,
    ) -> tuple[Identity, str | None]:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing, None
        return self.create_identity(name, scopes or ["execute"])

    def disable_identity(self, identity_id: str) -> bool:
        identity = self._identities.get(identity_id)
        if identity is None:
            return False
        identity.status = "disabled"
        return True

    def reset(self) -> None:
        self._identities.clear()
        self._key_map.clear()


_store: IdentityStore | InMemoryIdentityStore | None = None
_store_lock = threading.Lock()


def get_identity_store() -> IdentityStore | InMemoryIdentityStore:
    """Return the process-global identity store (lazy-initialized)."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                if (
                    os.environ.get("PYTEST_CURRENT_TEST")
                    or os.environ.get("UMH_IDENTITY_BACKEND") == "memory"
                ):
                    _store = InMemoryIdentityStore()
                else:
                    _store = IdentityStore()
    return _store


def reset_identity_store(store=None) -> None:
    """Replace the global store (useful for tests)."""
    global _store
    with _store_lock:
        _store = store
