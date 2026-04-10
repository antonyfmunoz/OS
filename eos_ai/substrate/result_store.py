"""
ResultStore — durable index of ingested ActionResults.

Sits between the station drainer (producer) and ritual reconciliation /
operator inspection (consumers).

Design rules:
  - Dual-layer: an in-memory dict acts as a cache; the authoritative copy
    lives in `substrate.storage.get_storage()` under a single KV key
    (`station_results`). This mirrors the RitualRegistry persistence
    pattern so we inherit Neon-with-JSON-fallback for free.
  - Process-wide singleton via `get_result_store()`. A fresh process
    rehydrates from storage on first access, so ingested results survive
    across process boundaries and ritual reconciliation can happen in a
    later process than the one that drained.
  - Idempotent upsert keyed by `action_id`. Draining the same result
    twice is a no-op overwrite. Last-write-wins on conflict.
  - Bounded. A retention cap (`_MAX_ROWS`) keeps the stored payload from
    growing without limit; on overflow the oldest rows (by `ingested_at`)
    are dropped. This is a simple, additive guardrail, not compaction.
  - Thread-safe. The drainer and reconcile helpers may be invoked from
    different threads; all mutating ops take an RLock.
  - Best-effort persistence. If a flush fails (Neon blip, disk full)
    the in-memory state remains correct and we log rather than raise —
    the store is a view, and losing it is recoverable via re-drain.
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


_STORAGE_KEY = "station_results"
_MAX_ROWS = 500  # bounded retention; oldest-by-ingested_at dropped on overflow
_MAX_AGE_DAYS = 14  # complementary age-based retention; 0 disables


def _log(msg: str) -> None:
    print(f"[substrate.result_store] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IngestedResult:
    action_id: str
    node_id: str
    status: str  # mirrors ActionStatus.value
    detail: Optional[str] = None
    returned_at: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    ingested_at: str = field(default_factory=_utcnow)
    kind: Optional[str] = None  # action kind if known (best-effort)

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "IngestedResult":
        return cls(
            action_id=str(d.get("action_id", "")),
            node_id=str(d.get("node_id", "")),
            status=str(d.get("status", "")),
            detail=d.get("detail"),
            returned_at=d.get("returned_at"),
            data=d.get("data") or {},
            ingested_at=d.get("ingested_at") or _utcnow(),
            kind=d.get("kind"),
        )

    @property
    def is_fallback(self) -> bool:
        """True if the daemon signaled a graceful-degradation path was used."""
        return bool(self.data.get("fallback") or self.data.get("dry_run"))


class ResultStore:
    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._by_action: dict[str, IngestedResult] = {}
        self._loaded = False
        if autoload:
            self._load()

    # ─── Persistence ─────────────────────────────────────────────────────
    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from eos_ai.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default={}) or {}
            except Exception as e:
                _log(f"load failed ({e}); starting empty")
                raw = {}
            if isinstance(raw, dict):
                rows = raw.get("rows") if "rows" in raw else raw
            else:
                rows = {}
            if isinstance(rows, dict):
                for aid, row in rows.items():
                    if not isinstance(row, dict):
                        continue
                    try:
                        self._by_action[str(aid)] = IngestedResult.from_dict(row)
                    except Exception:
                        continue
            self._loaded = True

    def _flush(self) -> None:
        # Caller holds the lock.
        try:
            from eos_ai.substrate.storage import get_storage

            payload = {
                "rows": {aid: r.as_dict() for aid, r in self._by_action.items()},
                "updated_at": _utcnow(),
            }
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:
            _log(f"flush failed: {e}")

    def _enforce_retention(self) -> None:
        # Caller holds the lock.
        # 1) Age sweep (complementary, cheap). Drop rows older than cutoff.
        if _MAX_AGE_DAYS and _MAX_AGE_DAYS > 0:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=_MAX_AGE_DAYS)
            ).isoformat()
            stale = [
                aid
                for aid, r in self._by_action.items()
                if (r.ingested_at or "") and r.ingested_at < cutoff
            ]
            for aid in stale:
                self._by_action.pop(aid, None)
        # 2) Count cap.
        if len(self._by_action) <= _MAX_ROWS:
            return
        ordered = sorted(
            self._by_action.items(),
            key=lambda kv: kv[1].ingested_at or "",
        )
        drop = len(self._by_action) - _MAX_ROWS
        for aid, _ in ordered[:drop]:
            self._by_action.pop(aid, None)

    # ─── Public API ──────────────────────────────────────────────────────
    def put(self, result: IngestedResult) -> None:
        with self._lock:
            self._by_action[result.action_id] = result
            self._enforce_retention()
            self._flush()

    def get(self, action_id: str) -> Optional[IngestedResult]:
        with self._lock:
            return self._by_action.get(action_id)

    def get_many(self, action_ids: list[str]) -> dict[str, IngestedResult]:
        with self._lock:
            return {
                aid: self._by_action[aid]
                for aid in action_ids
                if aid in self._by_action
            }

    def by_node(self, node_id: str) -> list[IngestedResult]:
        with self._lock:
            return [r for r in self._by_action.values() if r.node_id == node_id]

    def by_status(self, status: str) -> list[IngestedResult]:
        needle = (status or "").lower()
        with self._lock:
            return [
                r
                for r in self._by_action.values()
                if (r.status or "").lower() == needle
            ]

    def all(self) -> list[IngestedResult]:
        with self._lock:
            return list(self._by_action.values())

    def latest(self, limit: int = 20) -> list[IngestedResult]:
        with self._lock:
            ordered = sorted(
                self._by_action.values(),
                key=lambda r: r.ingested_at or "",
                reverse=True,
            )
            return ordered[: max(0, int(limit))]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._by_action)
            by_status: dict[str, int] = {}
            fallbacks = 0
            for r in self._by_action.values():
                s = (r.status or "unknown").lower()
                by_status[s] = by_status.get(s, 0) + 1
                if r.is_fallback:
                    fallbacks += 1
            return {
                "total": total,
                "by_status": by_status,
                "fallbacks": fallbacks,
                "cap": _MAX_ROWS,
            }

    def clear(self) -> None:
        """Test helper. Drops in-memory rows AND the durable payload."""
        with self._lock:
            self._by_action.clear()
            self._flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_action)


_store_singleton: Optional[ResultStore] = None
_store_singleton_lock = threading.Lock()


def get_result_store() -> ResultStore:
    global _store_singleton
    if _store_singleton is None:
        with _store_singleton_lock:
            if _store_singleton is None:
                _store_singleton = ResultStore()
    return _store_singleton


def reset_result_store_for_tests() -> None:
    """Drop the singleton. Next `get_result_store()` rehydrates from storage."""
    global _store_singleton
    with _store_singleton_lock:
        _store_singleton = None
