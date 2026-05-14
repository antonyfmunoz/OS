"""
Substrate storage — minimal persistence for NodeRegistry and RitualRegistry.

Design rules:
  - Keep the schema TINY. One key/value surface, JSON blobs as values.
  - Safe default: JSON file at /opt/OS/runtime/.substrate_state.json.
    Always writable, zero migration risk.
  - Optional upgrade: Neon-backed key/value using the existing get_conn() +
    RLS pattern. Creates a single `substrate_state` table on first use.
  - On any Neon failure the storage silently falls back to JSON with a clear
    log line. We never block the substrate on DB availability.

This is intentionally not a generic ORM. It exists only to let the substrate
registries (nodes, rituals) survive across processes without dragging in a
migration framework.

Usage:
    from runtime.transport.storage import get_storage

    st = get_storage()
    st.put("nodes", {"vps-primary": {...}})
    data = st.get("nodes", default={})
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional, Protocol
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


_JSON_PATH = Path(_ROOT) / "runtime" / ".substrate_state.json"


def _log(msg: str) -> None:
    # Single point of logging so we can swap in a proper logger later.
    print(f"[substrate.storage] {msg}", file=sys.stderr)


# ─── Interface ────────────────────────────────────────────────────────────────

class SubstrateStorage(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def put(self, key: str, value: Any) -> None: ...
    def all_keys(self) -> list[str]: ...


# ─── JSON file implementation (safe default) ─────────────────────────────────

class JSONFileStorage:
    """
    Thread-safe JSON file KV store. All values must be JSON-serializable.

    File layout: {"<key>": <value>, ...}
    Writes are atomic via os.replace on a tempfile sibling.
    """

    def __init__(self, path: Path = _JSON_PATH) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_all({})

    def _read_all(self) -> dict:
        try:
            with self._path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            _log(f"read failed ({e}); resetting to empty state")
            return {}

    def _write_all(self, data: dict) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, default=str)
        os.replace(tmp, self._path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._read_all().get(key, default)

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._read_all()
            data[key] = value
            self._write_all(data)

    def all_keys(self) -> list[str]:
        with self._lock:
            return list(self._read_all().keys())


# ─── Neon implementation (opportunistic upgrade) ─────────────────────────────

_NEON_DDL = """
CREATE TABLE IF NOT EXISTS substrate_state (
    org_id  uuid        NOT NULL,
    key     text        NOT NULL,
    value   jsonb       NOT NULL,
    updated timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, key)
);
"""


class NeonStorage:
    """
    Neon-backed KV using the existing RLS-scoped get_conn() pattern.

    The table is created on first successful connect. On ANY failure, the
    wrapping get_storage() call falls back to JSONFileStorage. This avoids
    a hard dependency on DB health during a session start.

    Note: substrate_state is intentionally scoped by org_id so the RLS
    discipline is preserved — the value is only a plain JSONB blob, fine-
    grained RLS on substrate internals is not worth the complexity today.
    """

    def __init__(self) -> None:
        from state.storage.db import get_conn, ORG_ID  # import here so module-level fails are caught
        self._get_conn = get_conn
        self._org_id = ORG_ID
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._get_conn(self._org_id) as cur:
            cur.execute(_NEON_DDL)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            with self._get_conn(self._org_id) as cur:
                cur.execute(
                    "SELECT value FROM substrate_state WHERE org_id=%s AND key=%s",
                    (self._org_id, key),
                )
                row = cur.fetchone()
                if row is None:
                    return default
                return row["value"]
        except Exception as e:
            _log(f"Neon get({key}) failed: {e}")
            return default

    def put(self, key: str, value: Any) -> None:
        try:
            with self._get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO substrate_state (org_id, key, value, updated)
                    VALUES (%s, %s, %s::jsonb, now())
                    ON CONFLICT (org_id, key) DO UPDATE
                        SET value = EXCLUDED.value, updated = now()
                    """,
                    (self._org_id, key, json.dumps(value, default=str)),
                )
        except Exception as e:
            _log(f"Neon put({key}) failed: {e}")

    def all_keys(self) -> list[str]:
        try:
            with self._get_conn(self._org_id) as cur:
                cur.execute("SELECT key FROM substrate_state WHERE org_id=%s", (self._org_id,))
                return [r["key"] for r in cur.fetchall()]
        except Exception as e:
            _log(f"Neon all_keys failed: {e}")
            return []


# ─── Factory ──────────────────────────────────────────────────────────────────

_storage_singleton: Optional[SubstrateStorage] = None


def get_storage(prefer: str = "auto") -> SubstrateStorage:
    """
    Return a process-wide storage singleton.

    prefer:
      "auto" (default) — try Neon, fall back to JSON
      "json"           — always JSON file
      "neon"           — always Neon (raises on failure)
    """
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    if prefer == "json":
        _storage_singleton = JSONFileStorage()
        return _storage_singleton

    if prefer == "neon":
        _storage_singleton = NeonStorage()
        return _storage_singleton

    # auto
    try:
        _storage_singleton = NeonStorage()
        _log("using Neon storage")
    except Exception as e:
        _log(f"Neon unavailable ({e}); using JSON file storage at {_JSON_PATH}")
        _storage_singleton = JSONFileStorage()
    return _storage_singleton


def reset_storage_for_tests() -> None:
    """Test hook — drop the singleton so the next get_storage() re-resolves."""
    global _storage_singleton
    _storage_singleton = None
