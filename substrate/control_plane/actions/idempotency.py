"""Filesystem sentinel store for Control Plane idempotency.

One JSON file per key at /opt/OS/logs/idempotency/<sha1(key)>.json.

The core contract is exactly one successful execution per key within
its TTL window. Single-host, low-concurrency, no lock manager — we
use O_EXCL atomic file creation as the mutual-exclusion primitive.

This module imports NOTHING from other core.action_system modules.
It is a leaf dependency, called only from substrate.control_plane.py.

Sentinel schema:
    {
      "key": "<caller-supplied string>",
      "action_id": "<uuid of the associated Action>",
      "status": "in_flight" | "executed" | "failed" | "deferred",
      "created_at": "<ISO utc>",
      "completed_at": "<ISO utc or null>",
      "ttl_seconds": <int; 0 means never expires>
    }

Status transitions (written by control_plane.py):
    (none) --claim--> in_flight
    in_flight --complete_executed--> executed
    in_flight --complete_failed--> failed
    in_flight --complete_deferred--> deferred
    deferred --complete_executed--> executed     (via resume path)
    deferred --complete_failed--> failed         (via resume path)

Gotchas:
    - SHA-1 is filesystem-safe digesting, NOT cryptographic security.
    - Keys containing colons / slashes would break naïve path joins;
      hashing sidesteps that. Original key is preserved in the JSON
      body for operator readability.
    - `claim()` uses O_CREAT|O_EXCL|O_WRONLY. The OS guarantees exactly
      one caller wins the create. Loser sees FileExistsError and
      should re-read the existing sentinel to decide what to do.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


IDEMPOTENCY_DIR = f"{_ROOT}/logs/idempotency"

VALID_STATUSES: tuple[str, ...] = ("in_flight", "executed", "failed", "deferred")


def _hash_key(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _path_for(key: str) -> str:
    os.makedirs(IDEMPOTENCY_DIR, exist_ok=True)
    return os.path.join(IDEMPOTENCY_DIR, f"{_hash_key(key)}.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Sentinel:
    key: str
    action_id: str
    status: str
    created_at: str
    completed_at: str | None = None
    ttl_seconds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_expired(self, *, now: datetime | None = None) -> bool:
        if self.ttl_seconds <= 0:
            return False
        try:
            created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        ref = now or datetime.now(timezone.utc)
        return (ref - created) >= timedelta(seconds=self.ttl_seconds)


def read(key: str) -> Sentinel | None:
    """Return the current sentinel for a key, or None if absent."""
    path = _path_for(key)
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return Sentinel(
        key=data.get("key", key),
        action_id=data.get("action_id", ""),
        status=data.get("status", ""),
        created_at=data.get("created_at", ""),
        completed_at=data.get("completed_at"),
        ttl_seconds=int(data.get("ttl_seconds", 0)),
    )


def _write(sentinel: Sentinel) -> str:
    """Unconditionally overwrite the sentinel file. Returns the path."""
    path = _path_for(sentinel.key)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sentinel.to_dict(), f, indent=2)
    os.replace(tmp, path)
    return path


def claim(key: str, action_id: str, ttl_seconds: int = 0) -> tuple[bool, Sentinel]:
    """Attempt to atomically claim `key` for `action_id`.

    Returns (won, sentinel):
      - (True,  new_sentinel)       — we created it; caller proceeds.
      - (False, existing_sentinel)  — someone else holds it; caller inspects status.

    Uses O_CREAT|O_EXCL for the race-free branch. No locks, no DB.
    """
    path = _path_for(key)
    new = Sentinel(
        key=key,
        action_id=action_id,
        status="in_flight",
        created_at=_now_iso(),
        completed_at=None,
        ttl_seconds=int(ttl_seconds or 0),
    )
    payload = json.dumps(new.to_dict(), indent=2).encode("utf-8")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        existing = read(key)
        # If the file exists but is unreadable/corrupt, treat as holding
        # an empty sentinel — the control_plane will force-overwrite.
        if existing is None:
            existing = Sentinel(
                key=key,
                action_id="",
                status="in_flight",
                created_at="",
                completed_at=None,
                ttl_seconds=0,
            )
        return (False, existing)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
    except Exception:
        # Best-effort cleanup of a half-written sentinel.
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        raise
    return (True, new)


def force_claim(key: str, action_id: str, ttl_seconds: int = 0) -> Sentinel:
    """Overwrite any existing sentinel for `key` with a fresh in_flight claim.

    Used by the control_plane when the prior sentinel is expired, failed,
    or points at a deferred action whose file has been dropped.
    """
    new = Sentinel(
        key=key,
        action_id=action_id,
        status="in_flight",
        created_at=_now_iso(),
        completed_at=None,
        ttl_seconds=int(ttl_seconds or 0),
    )
    _write(new)
    return new


def complete(key: str, status: str) -> Sentinel | None:
    """Update the sentinel for `key` to a terminal or intermediate status.

    Valid statuses: executed | failed | deferred.
    Returns the updated sentinel, or None if the sentinel is missing.
    """
    if status not in ("executed", "failed", "deferred"):
        raise ValueError(f"invalid completion status {status!r}")
    current = read(key)
    if current is None:
        return None
    current.status = status
    if status in ("executed", "failed"):
        current.completed_at = _now_iso()
    _write(current)
    return current


def clear(key: str) -> bool:
    """Delete the sentinel for `key`. Returns True if removed."""
    path = _path_for(key)
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False


def list_all() -> list[Sentinel]:
    """Return every sentinel on disk. Sorted by created_at descending."""
    if not os.path.isdir(IDEMPOTENCY_DIR):
        return []
    out: list[Sentinel] = []
    for name in os.listdir(IDEMPOTENCY_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(IDEMPOTENCY_DIR, name)
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        out.append(
            Sentinel(
                key=data.get("key", ""),
                action_id=data.get("action_id", ""),
                status=data.get("status", ""),
                created_at=data.get("created_at", ""),
                completed_at=data.get("completed_at"),
                ttl_seconds=int(data.get("ttl_seconds", 0)),
            )
        )
    out.sort(key=lambda s: s.created_at, reverse=True)
    return out


def find(key_or_sha: str) -> Sentinel | None:
    """Look up a sentinel by raw key OR by its sha1 filename prefix.

    Operators use both forms — the full key when they know it, and the
    sha prefix when copy-pasting from `list`.
    """
    direct = read(key_or_sha)
    if direct is not None:
        return direct
    # Try as hex prefix.
    if not os.path.isdir(IDEMPOTENCY_DIR):
        return None
    for name in os.listdir(IDEMPOTENCY_DIR):
        if name.endswith(".json") and name.startswith(key_or_sha):
            path = os.path.join(IDEMPOTENCY_DIR, name)
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                return None
            return Sentinel(
                key=data.get("key", ""),
                action_id=data.get("action_id", ""),
                status=data.get("status", ""),
                created_at=data.get("created_at", ""),
                completed_at=data.get("completed_at"),
                ttl_seconds=int(data.get("ttl_seconds", 0)),
            )
    return None


def prune_expired() -> list[str]:
    """Remove every expired sentinel. Returns list of cleared keys."""
    cleared: list[str] = []
    for s in list_all():
        if s.is_expired():
            if clear(s.key):
                cleared.append(s.key)
    return cleared


__all__ = [
    "IDEMPOTENCY_DIR",
    "VALID_STATUSES",
    "Sentinel",
    "read",
    "claim",
    "force_claim",
    "complete",
    "clear",
    "list_all",
    "find",
    "prune_expired",
]
