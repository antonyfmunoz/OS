"""
Action Tracker — VPS-side pending action lifecycle management.

Centralized registry for tracking SafeAction state transitions across
the entire dispatch → acknowledge → complete/expire/fail lifecycle.
Replaces the fragmented per-node tracking in StationContract._inflight.

Every action dispatched through the substrate passes through this tracker,
giving the VPS global visibility into:
  - What actions are pending/dispatched/acknowledged/completed/expired/failed
  - Per-node action counts and states
  - Stale actions that need cleanup on reconnect
  - Full action lifecycle for traceability

Design rules (mirror substrate conventions):
- Singleton via get_action_tracker().
- Thread-safe via RLock.
- Dual-layer: in-memory for speed + substrate storage for durability.
- Bounded: configurable retention cap + TTL-based expiry sweep.
- Additive: does not modify SafeAction or ActionResult schemas.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ─── Constants ─────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.action_tracker]"
_STORAGE_KEY = "action_tracker"
MAX_TRACKED_ACTIONS = 500
MAX_AGE_HOURS = 48.0


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utcnow_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


# ─── Action Lifecycle State ────────────────────────────────────────────────


class TrackedState(str, Enum):
    """Lifecycle states for a tracked action.

    Valid transitions:
      PENDING → DISPATCHED → ACKNOWLEDGED → COMPLETED
      PENDING → DISPATCHED → ACKNOWLEDGED → FAILED
      PENDING → DISPATCHED → COMPLETED  (ACK skipped — legacy path)
      PENDING → DISPATCHED → FAILED
      PENDING → DISPATCHED → EXPIRED
      PENDING → EXPIRED
      * → EXPIRED  (TTL sweep can expire from any non-terminal state)
    """

    PENDING = "pending"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


# Terminal states — no further transitions allowed.
_TERMINAL_STATES = frozenset(
    {TrackedState.COMPLETED, TrackedState.EXPIRED, TrackedState.FAILED}
)

# Valid transitions from each state.
_VALID_TRANSITIONS: dict[TrackedState, frozenset[TrackedState]] = {
    TrackedState.PENDING: frozenset({TrackedState.DISPATCHED, TrackedState.EXPIRED}),
    TrackedState.DISPATCHED: frozenset(
        {
            TrackedState.ACKNOWLEDGED,
            TrackedState.COMPLETED,
            TrackedState.EXPIRED,
            TrackedState.FAILED,
        }
    ),
    TrackedState.ACKNOWLEDGED: frozenset(
        {TrackedState.COMPLETED, TrackedState.EXPIRED, TrackedState.FAILED}
    ),
    TrackedState.COMPLETED: frozenset(),
    TrackedState.EXPIRED: frozenset(),
    TrackedState.FAILED: frozenset(),
}


# ─── Tracked Action Record ─────────────────────────────────────────────────


@dataclass
class TrackedAction:
    """A single action's lifecycle record on the VPS side."""

    action_id: str
    kind: str  # ActionKind.value
    target_node_id: str
    issued_by: Optional[str] = None
    state: TrackedState = TrackedState.PENDING
    issued_at: str = field(default_factory=_utcnow)
    ttl_seconds: int = 3600
    dispatched_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    completed_at: Optional[str] = None
    expired_at: Optional[str] = None
    failed_at: Optional[str] = None
    detail: Optional[str] = None
    result_data: dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    def is_expired_by_ttl(self) -> bool:
        """Check if this action's TTL has elapsed."""
        try:
            issued_ts = datetime.fromisoformat(self.issued_at).timestamp()
            return (_utcnow_ts() - issued_ts) > self.ttl_seconds
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind,
            "target_node_id": self.target_node_id,
            "issued_by": self.issued_by,
            "state": self.state.value,
            "issued_at": self.issued_at,
            "ttl_seconds": self.ttl_seconds,
            "dispatched_at": self.dispatched_at,
            "acknowledged_at": self.acknowledged_at,
            "completed_at": self.completed_at,
            "expired_at": self.expired_at,
            "failed_at": self.failed_at,
            "detail": self.detail,
            "result_data": self.result_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackedAction":
        return cls(
            action_id=data["action_id"],
            kind=data.get("kind", "unknown"),
            target_node_id=data.get("target_node_id", "unknown"),
            issued_by=data.get("issued_by"),
            state=TrackedState(data.get("state", "pending")),
            issued_at=data.get("issued_at", _utcnow()),
            ttl_seconds=data.get("ttl_seconds", 3600),
            dispatched_at=data.get("dispatched_at"),
            acknowledged_at=data.get("acknowledged_at"),
            completed_at=data.get("completed_at"),
            expired_at=data.get("expired_at"),
            failed_at=data.get("failed_at"),
            detail=data.get("detail"),
            result_data=data.get("result_data", {}),
        )


# ─── State Transition ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class TransitionResult:
    """Result of a state transition attempt."""

    success: bool
    previous_state: TrackedState
    new_state: TrackedState
    action_id: str
    reason: str = ""


# ─── Action Tracker ────────────────────────────────────────────────────────


class ActionTracker:
    """VPS-side centralized action lifecycle tracker.

    Thread-safe. Dual-layer persistence (in-memory + substrate storage).
    Bounded by MAX_TRACKED_ACTIONS with oldest-terminal eviction.
    """

    def __init__(self, *, persist: bool = True) -> None:
        self._actions: dict[str, TrackedAction] = {}
        self._lock = threading.RLock()
        self._persist = persist
        if persist:
            self._load()

    # ─── Persistence ─────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            from umh.substrate.storage import get_storage

            raw = get_storage().get(_STORAGE_KEY, default={}) or {}
            for action_id, data in raw.items():
                try:
                    self._actions[action_id] = TrackedAction.from_dict(data)
                except Exception:
                    pass
        except Exception as e:
            _log(f"load failed ({e}); starting empty")

    def _flush(self) -> None:
        if not self._persist:
            return
        try:
            from umh.substrate.storage import get_storage

            payload = {aid: a.to_dict() for aid, a in self._actions.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:
            _log(f"flush failed ({e}); in-memory only")

    # ─── Core Operations ─────────────────────────────────────────────────

    def track(
        self,
        action_id: str,
        kind: str,
        target_node_id: str,
        *,
        issued_by: Optional[str] = None,
        issued_at: Optional[str] = None,
        ttl_seconds: int = 3600,
    ) -> TrackedAction:
        """Begin tracking a new action. Called when action is created/dispatched."""
        with self._lock:
            tracked = TrackedAction(
                action_id=action_id,
                kind=kind,
                target_node_id=target_node_id,
                issued_by=issued_by,
                issued_at=issued_at or _utcnow(),
                ttl_seconds=ttl_seconds,
            )
            self._actions[action_id] = tracked
            self._maybe_evict()
            self._flush()
            self._emit_event("action_dispatched", tracked)
            return tracked

    def transition(
        self,
        action_id: str,
        new_state: TrackedState,
        *,
        detail: Optional[str] = None,
        result_data: Optional[dict[str, Any]] = None,
    ) -> TransitionResult:
        """Attempt a state transition for a tracked action.

        Validates the transition is legal. Updates timestamps and detail.
        Returns TransitionResult indicating success/failure.
        """
        with self._lock:
            tracked = self._actions.get(action_id)
            if tracked is None:
                return TransitionResult(
                    success=False,
                    previous_state=TrackedState.PENDING,
                    new_state=new_state,
                    action_id=action_id,
                    reason=f"action_id {action_id} not tracked",
                )

            previous = tracked.state
            valid_next = _VALID_TRANSITIONS.get(previous, frozenset())

            if new_state not in valid_next:
                return TransitionResult(
                    success=False,
                    previous_state=previous,
                    new_state=new_state,
                    action_id=action_id,
                    reason=f"invalid transition {previous.value}→{new_state.value}",
                )

            # Apply transition
            tracked.state = new_state
            now = _utcnow()

            if new_state == TrackedState.DISPATCHED:
                tracked.dispatched_at = now
            elif new_state == TrackedState.ACKNOWLEDGED:
                tracked.acknowledged_at = now
            elif new_state == TrackedState.COMPLETED:
                tracked.completed_at = now
            elif new_state == TrackedState.EXPIRED:
                tracked.expired_at = now
            elif new_state == TrackedState.FAILED:
                tracked.failed_at = now

            if detail is not None:
                tracked.detail = detail
            if result_data is not None:
                tracked.result_data = result_data

            self._flush()

            # Emit lifecycle event
            event_name = f"action_{new_state.value}"
            self._emit_event(event_name, tracked)

            return TransitionResult(
                success=True,
                previous_state=previous,
                new_state=new_state,
                action_id=action_id,
            )

    def mark_dispatched(
        self, action_id: str, *, detail: Optional[str] = None
    ) -> TransitionResult:
        """Convenience: PENDING → DISPATCHED."""
        return self.transition(action_id, TrackedState.DISPATCHED, detail=detail)

    def mark_acknowledged(
        self, action_id: str, *, detail: Optional[str] = None
    ) -> TransitionResult:
        """Convenience: DISPATCHED → ACKNOWLEDGED."""
        return self.transition(action_id, TrackedState.ACKNOWLEDGED, detail=detail)

    def mark_completed(
        self,
        action_id: str,
        *,
        detail: Optional[str] = None,
        result_data: Optional[dict[str, Any]] = None,
    ) -> TransitionResult:
        """Convenience: ACKNOWLEDGED/DISPATCHED → COMPLETED."""
        return self.transition(
            action_id,
            TrackedState.COMPLETED,
            detail=detail,
            result_data=result_data,
        )

    def mark_failed(
        self, action_id: str, *, detail: Optional[str] = None
    ) -> TransitionResult:
        """Convenience: any non-terminal → FAILED."""
        return self.transition(action_id, TrackedState.FAILED, detail=detail)

    def mark_expired(
        self, action_id: str, *, detail: Optional[str] = None
    ) -> TransitionResult:
        """Convenience: any non-terminal → EXPIRED."""
        return self.transition(action_id, TrackedState.EXPIRED, detail=detail)

    # ─── Queries ─────────────────────────────────────────────────────────

    def get(self, action_id: str) -> Optional[TrackedAction]:
        with self._lock:
            return self._actions.get(action_id)

    def by_node(self, node_id: str) -> list[TrackedAction]:
        with self._lock:
            return [a for a in self._actions.values() if a.target_node_id == node_id]

    def by_state(self, state: TrackedState) -> list[TrackedAction]:
        with self._lock:
            return [a for a in self._actions.values() if a.state == state]

    def pending_for_node(self, node_id: str) -> list[TrackedAction]:
        """Actions that are pending or dispatched (not yet completed) for a node."""
        with self._lock:
            return [
                a
                for a in self._actions.values()
                if a.target_node_id == node_id
                and a.state
                in (
                    TrackedState.PENDING,
                    TrackedState.DISPATCHED,
                    TrackedState.ACKNOWLEDGED,
                )
            ]

    def is_pending(self, action_id: str) -> bool:
        with self._lock:
            a = self._actions.get(action_id)
            return a is not None and not a.is_terminal()

    def stats(self) -> dict[str, Any]:
        """Summary statistics for observability."""
        with self._lock:
            counts: dict[str, int] = {}
            per_node: dict[str, int] = {}
            for a in self._actions.values():
                counts[a.state.value] = counts.get(a.state.value, 0) + 1
                if not a.is_terminal():
                    per_node[a.target_node_id] = per_node.get(a.target_node_id, 0) + 1
            return {
                "total_tracked": len(self._actions),
                "by_state": counts,
                "active_per_node": per_node,
            }

    # ─── Reconnect Support ───────────────────────────────────────────────

    def expire_stale_for_node(self, node_id: str) -> list[str]:
        """Expire all non-terminal actions for a node whose TTL has elapsed.

        Called during reconnect to clean up stale actions that can't be
        executed anymore. Returns list of expired action_ids.
        """
        expired_ids: list[str] = []
        with self._lock:
            for a in list(self._actions.values()):
                if a.target_node_id != node_id:
                    continue
                if a.is_terminal():
                    continue
                if a.is_expired_by_ttl():
                    a.state = TrackedState.EXPIRED
                    a.expired_at = _utcnow()
                    a.detail = "expired on reconnect: TTL elapsed while node offline"
                    expired_ids.append(a.action_id)
                    self._emit_event("action_expired", a)

            if expired_ids:
                self._flush()
                _log(
                    f"expired {len(expired_ids)} stale action(s) "
                    f"for node {node_id} on reconnect"
                )
        return expired_ids

    def get_valid_pending_for_node(self, node_id: str) -> list[TrackedAction]:
        """Get non-expired pending actions for a node.

        Called during reconnect to identify actions that are still valid
        and could be re-dispatched.
        """
        with self._lock:
            return [
                a
                for a in self._actions.values()
                if a.target_node_id == node_id
                and not a.is_terminal()
                and not a.is_expired_by_ttl()
            ]

    # ─── Housekeeping ────────────────────────────────────────────────────

    def sweep_expired(self) -> list[str]:
        """Sweep all tracked actions and expire any whose TTL has elapsed.

        Called periodically (e.g., on heartbeat) to keep state clean.
        Returns list of newly expired action_ids.
        """
        expired_ids: list[str] = []
        with self._lock:
            for a in list(self._actions.values()):
                if a.is_terminal():
                    continue
                if a.is_expired_by_ttl():
                    a.state = TrackedState.EXPIRED
                    a.expired_at = _utcnow()
                    a.detail = "expired: TTL elapsed"
                    expired_ids.append(a.action_id)
                    self._emit_event("action_expired", a)

            if expired_ids:
                self._flush()
        return expired_ids

    def _maybe_evict(self) -> None:
        """Evict oldest terminal actions if over capacity. Must hold lock."""
        if len(self._actions) <= MAX_TRACKED_ACTIONS:
            return

        # Sort terminal actions by completion/expiry time, evict oldest
        terminals = [a for a in self._actions.values() if a.is_terminal()]
        terminals.sort(
            key=lambda a: a.completed_at or a.expired_at or a.failed_at or ""
        )

        to_remove = len(self._actions) - MAX_TRACKED_ACTIONS
        for a in terminals[:to_remove]:
            self._actions.pop(a.action_id, None)

    # ─── Event Emission ──────────────────────────────────────────────────

    def _emit_event(self, event_name: str, tracked: TrackedAction) -> None:
        """Emit a structured lifecycle event. Best-effort."""
        try:
            from umh.substrate.workstation_log import log_event

            log_event(
                event_name,
                {
                    "action_id": tracked.action_id,
                    "kind": tracked.kind,
                    "node_id": tracked.target_node_id,
                    "state": tracked.state.value,
                    "issued_by": tracked.issued_by,
                    "detail": tracked.detail,
                },
                to_stderr=False,
            )
        except Exception:
            pass


# ─── Module-level singleton ────────────────────────────────────────────────

_tracker: Optional[ActionTracker] = None
_tracker_lock = threading.Lock()


def get_action_tracker() -> ActionTracker:
    """Get the process-wide action tracker singleton."""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = ActionTracker()
    return _tracker


def reset_tracker_for_tests() -> None:
    """Reset the singleton for test isolation."""
    global _tracker
    _tracker = None


__all__ = [
    "TrackedState",
    "TrackedAction",
    "TransitionResult",
    "ActionTracker",
    "get_action_tracker",
    "reset_tracker_for_tests",
]
