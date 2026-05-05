"""
Execution-level completion awareness for the run lifecycle.

Separates "output finished" from "execution finished" by tracking whether
the underlying tmux session / CC process is still active after logical
completion.  This prevents clear from firing while a zombie shell lingers
or a late webhook arrives.

Execution state is orthogonal to logical lifecycle (RunStatus).  A run
can be logically FINALIZED but execution still ACTIVE (CC process alive,
output still growing).

State machine:
  ACTIVE → DRAINING → COMPLETE

Design rules (substrate conventions):
- Additive only.  No hot-path imports.
- Deterministic.  No LLM calls.
- Thread-safe.  All state behind locks.
- In-memory.  No persistence.
- Composable with run_lifecycle — does not modify RunStatus enum.

Public API:
  - RunExecutionState (enum)
  - ExecutionTracker (per-run tracker)
  - mark_execution_activity(source_session) -> None
  - mark_execution_draining(source_session) -> None
  - mark_execution_complete(source_session, stalled=False) -> None
  - get_execution_state(source_session) -> RunExecutionState | None
  - is_execution_complete(source_session) -> bool
  - is_execution_stalled(source_session, stall_timeout_s=5.0) -> bool
  - reset_execution(source_session) -> None
  - reset_for_tests() -> None
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


_LOG_PREFIX = "[substrate.run_execution]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Execution state enum ────────────────────────────────────────────────────


class RunExecutionState(str, Enum):
    """Physical execution state of a run's underlying process."""

    ACTIVE = "active"
    DRAINING = "draining"
    COMPLETE = "complete"


# ─── Per-run execution tracker ───────────────────────────────────────────────


@dataclass
class ExecutionTracker:
    """Tracks physical execution state for a single run.

    Created when a run starts.  Updated by watcher (output growth),
    finalization (draining), and completion detection (complete).
    """

    source_session: str
    state: RunExecutionState = RunExecutionState.ACTIVE
    last_activity_ts: float = field(default_factory=time.monotonic)
    draining_since: float = 0.0
    completed_at: float = 0.0
    stalled: bool = False

    def mark_activity(self) -> None:
        """Record that real output activity was detected."""
        self.last_activity_ts = time.monotonic()

    def mark_draining(self) -> None:
        """Transition to DRAINING (finalization succeeded, waiting for execution end)."""
        if self.state == RunExecutionState.ACTIVE:
            self.state = RunExecutionState.DRAINING
            self.draining_since = time.monotonic()
            _log(f"execution_draining_started: session={self.source_session}")

    def mark_complete(self, *, stalled: bool = False) -> None:
        """Transition to COMPLETE (execution truly finished)."""
        if self.state != RunExecutionState.COMPLETE:
            self.state = RunExecutionState.COMPLETE
            self.completed_at = time.monotonic()
            self.stalled = stalled
            event = "execution_stalled_detected" if stalled else "execution_complete"
            _log(f"{event}: session={self.source_session} stalled={stalled}")

    def is_stalled(self, stall_timeout_s: float = 5.0) -> bool:
        """Check if execution appears stalled (no activity beyond timeout)."""
        if self.state == RunExecutionState.COMPLETE:
            return self.stalled
        elapsed = time.monotonic() - self.last_activity_ts
        return elapsed > stall_timeout_s

    def to_dict(self) -> dict:
        now = time.monotonic()
        return {
            "source_session": self.source_session,
            "state": self.state.value,
            "seconds_since_activity": round(now - self.last_activity_ts, 2),
            "stalled": self.stalled,
            "draining_since": self.draining_since or None,
            "completed_at": self.completed_at or None,
        }


# ─── Execution manager (singleton) ──────────────────────────────────────────


class _ExecutionManager:
    """Thread-safe singleton managing per-session execution trackers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trackers: dict[str, ExecutionTracker] = {}

    def get_or_create(self, source_session: str) -> ExecutionTracker:
        """Get existing tracker or create a new one."""
        with self._lock:
            if source_session not in self._trackers:
                self._trackers[source_session] = ExecutionTracker(
                    source_session=source_session,
                )
            return self._trackers[source_session]

    def mark_activity(self, source_session: str) -> None:
        """Record output activity for a session."""
        with self._lock:
            tracker = self._trackers.get(source_session)
            if tracker and tracker.state != RunExecutionState.COMPLETE:
                tracker.mark_activity()

    def mark_draining(self, source_session: str) -> None:
        """Transition session execution to DRAINING."""
        with self._lock:
            tracker = self._trackers.get(source_session)
            if tracker:
                tracker.mark_draining()

    def mark_complete(self, source_session: str, *, stalled: bool = False) -> None:
        """Transition session execution to COMPLETE."""
        with self._lock:
            tracker = self._trackers.get(source_session)
            if tracker:
                tracker.mark_complete(stalled=stalled)

    def get_state(self, source_session: str) -> Optional[RunExecutionState]:
        """Get current execution state for a session."""
        with self._lock:
            tracker = self._trackers.get(source_session)
            return tracker.state if tracker else None

    def is_complete(self, source_session: str) -> bool:
        """Check if execution is complete for a session."""
        with self._lock:
            tracker = self._trackers.get(source_session)
            if tracker is None:
                return True  # no tracker = nothing running
            return tracker.state == RunExecutionState.COMPLETE

    def is_stalled(self, source_session: str, stall_timeout_s: float = 5.0) -> bool:
        """Check if execution is stalled for a session."""
        with self._lock:
            tracker = self._trackers.get(source_session)
            if tracker is None:
                return False
            return tracker.is_stalled(stall_timeout_s)

    def reset(self, source_session: str) -> None:
        """Reset execution tracker for a session (after clear)."""
        with self._lock:
            self._trackers.pop(source_session, None)

    def reset_for_tests(self) -> None:
        """Test helper — clear all trackers."""
        with self._lock:
            self._trackers.clear()

    def get_tracker(self, source_session: str) -> Optional[ExecutionTracker]:
        """Get tracker instance (for diagnostics)."""
        with self._lock:
            return self._trackers.get(source_session)


# ─── Module-level singleton ──────────────────────────────────────────────────

_manager = _ExecutionManager()


# ─── Public API ──────────────────────────────────────────────────────────────


def init_execution_tracker(source_session: str) -> ExecutionTracker:
    """Initialize execution tracking for a new run."""
    tracker = _manager.get_or_create(source_session)
    _log(f"execution_tracker_initialized: session={source_session}")
    return tracker


def mark_execution_activity(source_session: str) -> None:
    """Record that real output activity was detected for a session.

    Called by session_watcher whenever output grows.
    """
    _manager.mark_activity(source_session)


def mark_execution_draining(source_session: str) -> None:
    """Transition execution to DRAINING after finalization succeeds.

    Called by task_finalization after canonical artifact is published.
    """
    _manager.mark_draining(source_session)


def mark_execution_complete(source_session: str, *, stalled: bool = False) -> None:
    """Transition execution to COMPLETE.

    Called when execution is truly finished (process exited, output
    stable, or stall timeout exceeded).
    """
    _manager.mark_complete(source_session, stalled=stalled)


def get_execution_state(
    source_session: str,
) -> Optional[RunExecutionState]:
    """Get current execution state for a session."""
    return _manager.get_state(source_session)


def is_execution_complete(source_session: str) -> bool:
    """Check if execution is complete for a session."""
    return _manager.is_complete(source_session)


def is_execution_stalled(source_session: str, stall_timeout_s: float = 5.0) -> bool:
    """Check if execution appears stalled (no recent activity)."""
    return _manager.is_stalled(source_session, stall_timeout_s)


def reset_execution(source_session: str) -> None:
    """Reset execution tracking for a session (called after clear)."""
    _manager.reset(source_session)


def get_execution_tracker(
    source_session: str,
) -> Optional[ExecutionTracker]:
    """Get tracker instance for diagnostics."""
    return _manager.get_tracker(source_session)


def reset_for_tests() -> None:
    """Test helper — clear all state."""
    _manager.reset_for_tests()


__all__ = [
    "RunExecutionState",
    "ExecutionTracker",
    "init_execution_tracker",
    "mark_execution_activity",
    "mark_execution_draining",
    "mark_execution_complete",
    "get_execution_state",
    "is_execution_complete",
    "is_execution_stalled",
    "reset_execution",
    "get_execution_tracker",
    "reset_for_tests",
]
