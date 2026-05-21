"""Continuity store — in-memory artifact cache keyed by channel_id.

Stores the last session's closing artifact so the next session on the
same channel can resume with context. No persistence — survives only
within a single process lifetime.
"""

from __future__ import annotations

import threading
from typing import Any


class ContinuityStore:
    """Thread-safe in-memory store for session continuity artifacts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._artifacts: dict[str, dict[str, Any]] = {}

    def save(self, channel_id: str, artifact: dict[str, Any]) -> None:
        with self._lock:
            self._artifacts[channel_id] = artifact

    def load(self, channel_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._artifacts.get(channel_id)

    def clear(self, channel_id: str) -> None:
        with self._lock:
            self._artifacts.pop(channel_id, None)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"channel_count": len(self._artifacts), "channels": list(self._artifacts.keys())}


_SINGLETON: ContinuityStore | None = None
_SINGLETON_LOCK = threading.Lock()


def get_continuity_store() -> ContinuityStore:
    """Return the process-wide continuity store singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                _SINGLETON = ContinuityStore()
    return _SINGLETON
