"""
EOS platform decision log — persists routing and delegation decisions.

Uses the substrate storage layer for persistence (same JSON/Neon dual-layer).
This is platform-level decision logging — it does NOT replace substrate
memory or perception records.

Design rules:
- Bounded — max 200 records, FIFO pruning on oldest.
- Best-effort persistence — failures log, never raise.
- Survives restarts via substrate storage.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


_STORAGE_KEY = "eos_platform_decisions"
_MAX_RECORDS = 200


def _log(msg: str) -> None:
    print(f"[platform.eos.decision_log] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"eosd_{uuid.uuid4().hex[:12]}"


# ─── Model ───────────────────────────────────────────────────────────────────


@dataclass
class EOSDecisionRecord:
    """A single platform-level routing/delegation decision."""

    decision_id: str
    source_intent_id: str
    primary_role: str
    delegated_role: Optional[str]
    summary: str
    created_task_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "source_intent_id": self.source_intent_id,
            "primary_role": self.primary_role,
            "delegated_role": self.delegated_role,
            "summary": self.summary,
            "created_task_ids": self.created_task_ids,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EOSDecisionRecord":
        return cls(
            decision_id=d["decision_id"],
            source_intent_id=d["source_intent_id"],
            primary_role=d["primary_role"],
            delegated_role=d.get("delegated_role"),
            summary=d["summary"],
            created_task_ids=d.get("created_task_ids", []),
            created_at=d.get("created_at", _utcnow()),
        )


# ─── Store ───────────────────────────────────────────────────────────────────


class DecisionLog:
    """
    Thread-safe, bounded decision log backed by substrate storage.

    Singleton via DecisionLog.default().
    """

    _default: Optional["DecisionLog"] = None

    def __init__(self) -> None:
        self._records: dict[str, EOSDecisionRecord] = {}
        self._lock = threading.RLock()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            from eos_ai.substrate.storage import get_storage

            raw = get_storage().get(_STORAGE_KEY, default={})
            if isinstance(raw, dict):
                for k, v in raw.items():
                    try:
                        self._records[k] = EOSDecisionRecord.from_dict(v)
                    except Exception:
                        pass
        except Exception as exc:
            _log(f"load failed: {exc}")
        self._loaded = True

    def _flush(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage

            get_storage().put(
                _STORAGE_KEY,
                {k: v.to_dict() for k, v in self._records.items()},
            )
        except Exception as exc:
            _log(f"flush failed: {exc}")

    def _prune(self) -> None:
        if len(self._records) <= _MAX_RECORDS:
            return
        sorted_keys = sorted(
            self._records.keys(),
            key=lambda k: self._records[k].created_at,
        )
        excess = len(self._records) - _MAX_RECORDS
        for k in sorted_keys[:excess]:
            del self._records[k]

    def record(self, decision: EOSDecisionRecord) -> None:
        """Persist a decision record."""
        with self._lock:
            self._ensure_loaded()
            self._records[decision.decision_id] = decision
            self._prune()
            self._flush()

    def get(self, decision_id: str) -> Optional[EOSDecisionRecord]:
        """Retrieve a decision by ID."""
        with self._lock:
            self._ensure_loaded()
            return self._records.get(decision_id)

    def recent(self, limit: int = 20) -> list[EOSDecisionRecord]:
        """Return most recent decisions, newest first."""
        with self._lock:
            self._ensure_loaded()
            items = sorted(
                self._records.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )
            return items[:limit]

    def all(self) -> list[EOSDecisionRecord]:
        """Return all decisions."""
        with self._lock:
            self._ensure_loaded()
            return list(self._records.values())

    @classmethod
    def default(cls) -> "DecisionLog":
        """Return process-wide singleton."""
        if cls._default is None:
            cls._default = cls()
        return cls._default

    @classmethod
    def reset_for_tests(cls) -> None:
        """Test hook — drop the singleton."""
        cls._default = None
