"""
Event Store — append-only JSONL persistence for the event spine.

Simple flat-file store.  Events are appended on creation, updated
in-place (rewrite) on status change.  No database dependency.

File: logs/event_spine.jsonl

Thread-safe via a file lock.  Designed for moderate throughput
(tens of events per second, not thousands).
"""

from __future__ import annotations

import json
import os
import sys
import threading
from typing import Any, Optional

from umh.substrate.event_spine import Event, EventStatus

# ─── Config ─────────────────────────────────────────────────────────────────

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_DEFAULT_STORE_PATH = os.path.join(_REPO_ROOT, "logs", "event_spine.jsonl")

_LOG_PREFIX = "[substrate.event_store]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── EventStore ─────────────────────────────────────────────────────────────


class EventStore:
    """Append-only JSONL event store with in-place status updates.

    All operations are thread-safe.  The store file is created on
    first write if it doesn't exist.
    """

    def __init__(self, path: str = _DEFAULT_STORE_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    @property
    def path(self) -> str:
        return self._path

    def append(self, event: Event) -> None:
        """Append an event to the store."""
        with self._lock:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event.serialize()) + "\n")
            except Exception as exc:
                _log(f"append failed: {exc}")

    def update_status(
        self,
        event_id: str,
        new_status: EventStatus,
        extra_fields: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Update an event's status (and optional extra payload fields).

        Rewrites the entire file — acceptable for moderate event volume.
        Returns True if the event was found and updated.
        """
        with self._lock:
            return self._update_locked(event_id, new_status, extra_fields)

    def _update_locked(
        self,
        event_id: str,
        new_status: EventStatus,
        extra_fields: Optional[dict[str, Any]],
    ) -> bool:
        items = self._read_all_locked()
        found = False
        for item in items:
            if item.get("event_id") == event_id:
                item["status"] = new_status.value
                from umh.substrate.event_spine import _now_iso

                item["updated_at"] = _now_iso()
                if extra_fields:
                    item["payload"] = {**item.get("payload", {}), **extra_fields}
                found = True
                break

        if found:
            self._write_all_locked(items)
        return found

    def get(self, event_id: str) -> Optional[Event]:
        """Retrieve a single event by ID."""
        with self._lock:
            for item in self._read_all_locked():
                if item.get("event_id") == event_id:
                    try:
                        return Event.deserialize(item)
                    except Exception:
                        return None
        return None

    def get_by_correlation(self, correlation_id: str) -> list[Event]:
        """Retrieve all events sharing a correlation ID."""
        results: list[Event] = []
        with self._lock:
            for item in self._read_all_locked():
                if item.get("correlation_id") == correlation_id:
                    try:
                        results.append(Event.deserialize(item))
                    except Exception:
                        pass
        return results

    def read_recent(self, limit: int = 50) -> list[Event]:
        """Read the most recent N events (newest last)."""
        with self._lock:
            items = self._read_all_locked()

        events: list[Event] = []
        for item in items[-limit:]:
            try:
                events.append(Event.deserialize(item))
            except Exception:
                pass
        return events

    def has_completed_reply(self, correlation_id: str, *, role: str = "") -> bool:
        """Check if a completed reply_complete event exists for a (correlation, role).

        Role-aware dedup: each operating context (ea_product, builder) gets its
        own final-reply slot.  Product replies never suppress Builder replies
        and vice versa.  When role is empty, falls back to correlation-only check
        for backward compatibility.
        """
        with self._lock:
            for item in self._read_all_locked():
                if (
                    item.get("correlation_id") == correlation_id
                    and item.get("event_type") == "reply_complete"
                    and item.get("status") == "completed"
                ):
                    # If role filtering is active, only match same role
                    if role and item.get("role", "") != role:
                        continue
                    return True
        return False

    def compact(self, max_age_hours: int = 24) -> int:
        """Remove events older than max_age_hours. Returns removed count."""
        import time

        cutoff = time.time() - (max_age_hours * 3600)
        with self._lock:
            items = self._read_all_locked()
            keep: list[dict[str, Any]] = []
            removed = 0
            for item in items:
                created = item.get("created_at", "")
                try:
                    ts = time.mktime(time.strptime(created[:19], "%Y-%m-%dT%H:%M:%S"))
                except (ValueError, TypeError):
                    ts = time.time()
                if ts < cutoff:
                    removed += 1
                else:
                    keep.append(item)
            if removed:
                self._write_all_locked(keep)
        return removed

    # ─── Internal I/O ───────────────────────────────────────────────────

    def _read_all_locked(self) -> list[dict[str, Any]]:
        """Read all entries. Must hold self._lock."""
        items: list[dict[str, Any]] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            items.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except FileNotFoundError:
            pass
        return items

    def _write_all_locked(self, items: list[dict[str, Any]]) -> None:
        """Rewrite entire store. Must hold self._lock."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item) + "\n")
        except Exception as exc:
            _log(f"write failed: {exc}")


# ─── Module-level singleton ─────────────────────────────────────────────────

_store = EventStore()


def get_event_store() -> EventStore:
    """Get the module-level event store singleton."""
    return _store


__all__ = [
    "EventStore",
    "get_event_store",
]
