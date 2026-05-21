"""
Canonical run lifecycle — single source of truth for run ownership.

This module solves the WORLD-CLASS LIFECYCLE OWNERSHIP BUG:
  Multiple independent paths (watcher, webhook, pseudolive) could each
  detect CC completion and independently finalize + clear the same run.
  The old 5-second cooldown was time-based, not run-scoped.

After this module:
  1. Completion signals are PROPOSALS, not authority
  2. Only ONE source becomes the canonical completion owner per run
  3. Finalization happens AT MOST ONCE per run
  4. Clear happens AT MOST ONCE per run
  5. All proposals, decisions, and rejections are logged for forensics

Design rules (substrate conventions):
- Additive only. No hot-path imports.
- Deterministic. No LLM calls.
- Thread-safe. All state behind locks.
- In-memory with structured logging for forensics.
- Scoped by (source_session, generation) — one CC session runs one task at a time.

Key concepts:
- A "run" is identified by (source_session, generation). Generation is a
  monotonic counter that increments each time a new task is sent to the session.
- Completion proposals arrive from multiple sources (watcher, webhook, pseudolive).
  The FIRST valid proposal becomes the canonical owner.
- Once a run is finalized, no further finalization can occur.
- Once a run is cleared, no further clear can occur.
- Later proposals are recorded but rejected.

Public API:
  - start_run(source_session, ...) -> RunHandle
  - propose_run_completion(source_session, source, payload) -> ProposalResult
  - attempt_canonical_finalization(source_session, source, finalize_fn) -> FinalizationResult
  - request_run_clear(source_session, source) -> ClearDecision
  - get_run_record(source_session) -> RunLifecycleRecord | None
  - get_run_forensics(source_session) -> list[ForensicEntry]
"""

from __future__ import annotations

import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


_LOG_PREFIX = "[substrate.run_lifecycle]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Shadow event scheduler (Phase 3) ─────────────────────────────────
# Lazy singleton. Emitting into this scheduler is best-effort — failure
# never blocks the existing lifecycle. The scheduler runs in shadow mode:
# events flow through it in parallel with the legacy imperative path.

_shadow_scheduler: Any = None
_shadow_scheduler_lock = threading.Lock()


def _get_shadow_scheduler() -> Any:
    """Lazy-init the shadow lifecycle scheduler. Returns None on failure."""
    global _shadow_scheduler
    if _shadow_scheduler is None:
        with _shadow_scheduler_lock:
            if _shadow_scheduler is None:
                try:
                    from umh.substrate.lifecycle_handlers import (
                        create_lifecycle_scheduler,
                    )
                    from umh.substrate.runtime_bootstrap import (
                        get_event_log_runtime,
                        get_runtime_state_store,
                    )

                    _shadow_scheduler = create_lifecycle_scheduler(
                        store=get_runtime_state_store(),
                        event_log=get_event_log_runtime(),
                    )
                except Exception as exc:
                    _log(f"shadow scheduler init failed (non-blocking): {exc}")
                    return None
    return _shadow_scheduler


def _maybe_shadow_emit(
    event_type: str,
    session_name: str,
    source: str,
    run_id: str = "",
    payload: dict | None = None,
    metadata: dict | None = None,
) -> None:
    """Best-effort shadow emission into the event scheduler.

    Called after durable lifecycle events to feed the event-driven path.
    Never raises. Never blocks the lifecycle.
    """
    try:
        scheduler = _get_shadow_scheduler()
        if scheduler is None:
            return

        from umh.substrate.event_scheduler import SchedulerEvent

        scheduler.emit(
            SchedulerEvent(
                event_type=event_type,
                session_name=session_name,
                source=source,
                run_id=run_id,
                payload=payload or {},
                metadata=metadata or {},
            )
        )
    except Exception as exc:
        _log(f"shadow emit failed for {event_type} (non-blocking): {exc}")


def reset_shadow_scheduler_for_testing() -> None:
    """Reset the shadow scheduler singleton. FOR TESTING ONLY."""
    global _shadow_scheduler
    with _shadow_scheduler_lock:
        _shadow_scheduler = None


# ─── Execution mode ──────────────────────────────────────────────────────
# Phase 4: Authority transfer. Controls which path drives lifecycle
# transitions — the legacy imperative path or the event scheduler.
#
# LEGACY:        Legacy path only. Events are NOT emitted to scheduler.
# SHADOW:        Legacy path executes. Events also emitted to scheduler
#                (current Phase 3 behavior).
# EVENT_PRIMARY: Scheduler drives ALL transitions. Legacy is fallback on
#                scheduler failure only.


class ExecutionMode(Enum):
    """Controls which execution path drives lifecycle transitions."""

    LEGACY = "legacy"
    SHADOW = "shadow"
    EVENT_PRIMARY = "event_primary"


_EXECUTION_MODE_OVERRIDE: ExecutionMode | None = None


def get_execution_mode() -> ExecutionMode:
    """Return the current execution mode.

    Resolution order:
      1. Test override (set via set_execution_mode_for_testing)
      2. LIFECYCLE_EXECUTION_MODE env var
      3. Default: SHADOW (Phase 3 current behavior)
    """
    if _EXECUTION_MODE_OVERRIDE is not None:
        return _EXECUTION_MODE_OVERRIDE

    import os

    raw = os.environ.get("LIFECYCLE_EXECUTION_MODE", "shadow").lower()
    try:
        return ExecutionMode(raw)
    except ValueError:
        _log(f"WARNING: unknown LIFECYCLE_EXECUTION_MODE={raw!r}, defaulting to SHADOW")
        return ExecutionMode.SHADOW


def set_execution_mode_for_testing(mode: ExecutionMode | None) -> None:
    """Override execution mode for testing. Pass None to clear."""
    global _EXECUTION_MODE_OVERRIDE
    _EXECUTION_MODE_OVERRIDE = mode


# ─── Run status enum ───────────────────────────────────────────────────────


class RunStatus(Enum):
    """Lifecycle status of a run."""

    RUNNING = "running"
    COMPLETION_PROPOSED = "completion_proposed"
    FINALIZATION_STARTED = "finalization_started"
    FINALIZED = "finalized"
    CLEAR_REQUESTED = "clear_requested"
    CLEARED = "cleared"


class FinalizationStatus(Enum):
    """Sub-status for the finalization step."""

    NOT_STARTED = "not_started"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED_ALREADY_FINALIZED = "blocked_already_finalized"
    BLOCKED_ALREADY_CLEARED = "blocked_already_cleared"
    BLOCKED_NOT_OWNER = "blocked_not_owner"


class ClearStatus(Enum):
    """Sub-status for the clear step."""

    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    SENT = "sent"
    CONFIRMED = "confirmed"
    BLOCKED_NOT_FINALIZED = "blocked_not_finalized"
    BLOCKED_ALREADY_CLEARED = "blocked_already_cleared"
    BLOCKED_FINALIZATION_FAILED = "blocked_finalization_failed"
    BLOCKED_NOT_PUBLISHED = "blocked_not_published"
    BLOCKED_NOT_READY = "blocked_not_ready"
    STALLED_SAFE = "stalled_safe"
    FAILED = "failed"


# ─── Forensic entry ────────────────────────────────────────────────────────


@dataclass
class ForensicEntry:
    """Structured log entry for run lifecycle forensics."""

    timestamp: str
    event: str
    source: str
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "source": self.source,
            "detail": self.detail,
            "metadata": self.metadata,
        }


# ─── Completion proposal ──────────────────────────────────────────────────


@dataclass
class CompletionProposal:
    """A proposal from a source that a run is complete."""

    source: str  # "watcher", "webhook", "pseudolive"
    proposed_at: str = field(default_factory=_utcnow)
    accepted: bool = False
    rejected_reason: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "proposed_at": self.proposed_at,
            "accepted": self.accepted,
            "rejected_reason": self.rejected_reason,
        }


# ─── Run lifecycle record ─────────────────────────────────────────────────


@dataclass
class RunLifecycleRecord:
    """Single source of truth for one run's lifecycle state.

    Scoped by (source_session, generation). One CC session can only have
    one active run at a time. Generation increments with each new task.
    """

    source_session: str
    generation: int
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    task_id: str = ""
    correlation_id: str = ""
    role: str = ""

    # Status
    status: RunStatus = RunStatus.RUNNING
    finalization_status: FinalizationStatus = FinalizationStatus.NOT_STARTED
    clear_status: ClearStatus = ClearStatus.NOT_REQUESTED

    # Ownership
    completion_owner: str = ""  # source that won ownership
    completion_proposals: list[CompletionProposal] = field(default_factory=list)

    # Timestamps
    started_at: str = field(default_factory=_utcnow)
    finalized_at: str = ""
    cleared_at: str = ""

    # Finalization result reference
    finalization_id: str = ""
    finalization_result: dict[str, Any] = field(default_factory=dict)

    # Canonical publication tracking
    canonical_result_id: str = ""
    publication_confirmed: bool = False
    publication_confirmed_at: str = ""

    # Physical clear dispatch lock — atomic exactly-once guard.
    # Set BEFORE tmux send-keys. Blocks all subsequent clear attempts
    # for this run at the physical injection boundary, regardless of
    # which path (webhook, watcher, pseudolive, manual) tries to clear.
    # This is the EARLIEST and STRONGEST clear dedupe signal.
    clear_dispatched: bool = False
    clear_dispatched_at: str = ""
    clear_dispatched_source: str = ""

    # Terminal finalization — irreversible lifecycle seal
    # Once True: ALL propose/finalize/clear/confirm operations are rejected.
    # Survives late events, duplicate webhooks, watcher re-fires.
    terminally_finalized: bool = False
    terminally_finalized_at: str = ""

    # Execution-level state (physical process tracking)
    execution_state: str = "active"  # "active", "draining", "complete"
    execution_last_activity_ts: str = ""
    execution_stalled: bool = False

    # Forensics
    forensics: list[ForensicEntry] = field(default_factory=list)

    # Lifecycle boundary events that get durable event log writes.
    # Only terminal state transitions — not every forensic entry.
    _DURABLE_LOG_EVENTS: frozenset[str] = frozenset(
        {
            "finalization_succeeded",
            "publication_confirmed",
            "clear_requested",
            "clear_confirmed",
            "terminal_seal_applied",
            "run_completion_proposed",
        }
    )

    def _record(
        self,
        event: str,
        source: str,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a forensic entry.

        If the event is a lifecycle boundary event, also append to the
        durable event log (best-effort, never blocks lifecycle).
        """
        entry = ForensicEntry(
            timestamp=_utcnow(),
            event=event,
            source=source,
            detail=detail,
            metadata=metadata or {},
        )
        self.forensics.append(entry)
        _log(
            f"{event}: run={self.run_id} session={self.source_session} "
            f"gen={self.generation} source={source} {detail}"
        )

        # ── Durable event log write (Phase 1 runtime) ────────────────
        if event in self._DURABLE_LOG_EVENTS:
            try:
                from umh.substrate.runtime_bootstrap import (
                    get_event_log_runtime,
                )

                state_mutations = []
                if event == "finalization_succeeded":
                    state_mutations = [
                        {
                            "op": "SET",
                            "key": "finalization_status",
                            "value": "succeeded",
                        },
                        {"op": "SET", "key": "finalized_at", "value": entry.timestamp},
                    ]
                elif event == "publication_confirmed":
                    state_mutations = [
                        {"op": "SET", "key": "publication_confirmed", "value": True},
                        {
                            "op": "SET",
                            "key": "publication_confirmed_at",
                            "value": entry.timestamp,
                        },
                    ]
                elif event == "clear_requested":
                    state_mutations = [
                        {"op": "SET", "key": "clear_status", "value": "requested"},
                    ]
                elif event == "clear_confirmed":
                    state_mutations = [
                        {"op": "SET", "key": "clear_status", "value": "confirmed"},
                        {"op": "SET", "key": "cleared_at", "value": entry.timestamp},
                    ]
                elif event == "terminal_seal_applied":
                    state_mutations = [
                        {"op": "SET", "key": "terminally_finalized", "value": True},
                        {
                            "op": "SET",
                            "key": "terminally_finalized_at",
                            "value": entry.timestamp,
                        },
                    ]

                get_event_log_runtime().append(
                    event_type=event,
                    session_name=self.source_session,
                    source=source,
                    run_id=self.run_id,
                    event_time=entry.timestamp,
                    payload={"detail": detail, **(metadata or {})},
                    state_mutations=state_mutations,
                    metadata={
                        "generation": self.generation,
                        "task_id": self.task_id,
                        "correlation_id": self.correlation_id,
                    },
                )
            except Exception as exc:
                _log(f"WARNING: durable event log write failed for {event}: {exc}")

            # ── Shadow emission into event scheduler (Phase 3) ──────
            _maybe_shadow_emit(
                event_type=event,
                session_name=self.source_session,
                source=source,
                run_id=self.run_id,
                payload={"detail": detail, **(metadata or {})},
                metadata={
                    "generation": self.generation,
                    "task_id": self.task_id,
                    "correlation_id": self.correlation_id,
                },
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_session": self.source_session,
            "generation": self.generation,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "role": self.role,
            "status": self.status.value,
            "finalization_status": self.finalization_status.value,
            "clear_status": self.clear_status.value,
            "completion_owner": self.completion_owner,
            "proposals": [p.to_dict() for p in self.completion_proposals],
            "started_at": self.started_at,
            "finalized_at": self.finalized_at,
            "cleared_at": self.cleared_at,
            "finalization_id": self.finalization_id,
            "canonical_result_id": self.canonical_result_id,
            "publication_confirmed": self.publication_confirmed,
            "publication_confirmed_at": self.publication_confirmed_at,
            "execution_state": self.execution_state,
            "terminally_finalized": self.terminally_finalized,
            "terminally_finalized_at": self.terminally_finalized_at,
            "execution_stalled": self.execution_stalled,
            "forensics_count": len(self.forensics),
        }


# ─── Result types ──────────────────────────────────────────────────────────


@dataclass
class ProposalResult:
    """Outcome of propose_run_completion()."""

    accepted: bool
    is_owner: bool
    run_id: str = ""
    generation: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "is_owner": self.is_owner,
            "run_id": self.run_id,
            "generation": self.generation,
            "reason": self.reason,
        }


@dataclass
class FinalizationDecision:
    """Outcome of attempt_canonical_finalization()."""

    allowed: bool
    run_id: str = ""
    generation: int = 0
    reason: str = ""
    finalization_result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "run_id": self.run_id,
            "generation": self.generation,
            "reason": self.reason,
        }


@dataclass
class ClearDecision:
    """Outcome of request_run_clear()."""

    allowed: bool
    run_id: str = ""
    generation: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "run_id": self.run_id,
            "generation": self.generation,
            "reason": self.reason,
        }


# ─── Run handle (returned from start_run) ─────────────────────────────────


@dataclass
class RunHandle:
    """Lightweight reference to a started run."""

    run_id: str
    source_session: str
    generation: int


# ─── Lifecycle manager (singleton) ─────────────────────────────────────────


class _RunLifecycleManager:
    """Thread-safe singleton managing all run lifecycle records.

    Keyed by source_session. Each session has at most one active run record.
    When a new run starts, the old record is archived and a fresh one is created.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # source_session → current RunLifecycleRecord
        self._active: dict[str, RunLifecycleRecord] = {}
        # source_session → generation counter (monotonic)
        self._generations: dict[str, int] = {}
        # Completed runs archive (bounded ring buffer for forensics)
        self._archive: list[RunLifecycleRecord] = []
        self._max_archive = 50

    def _write_lifecycle_checkpoint(
        self,
        record: RunLifecycleRecord,
        trigger_event: str,
    ) -> None:
        """Best-effort durable checkpoint write at lifecycle boundaries.

        Called after clear_confirmed and terminal_seal_applied to snapshot
        the minimal canonical state. Never raises — failure is logged only.
        """
        try:
            from umh.substrate.runtime_bootstrap import (
                get_checkpoint_runtime,
                get_event_log_runtime,
            )

            seq = get_event_log_runtime().get_last_sequence()
            last_events = get_event_log_runtime().tail(1)
            event_id = last_events[0].event_id if last_events else ""

            snapshot = {
                "session_name": record.source_session,
                "run_id": record.run_id,
                "generation": record.generation,
                "task_id": record.task_id,
                "status": record.status.value,
                "finalization_status": record.finalization_status.value,
                "publication_confirmed": record.publication_confirmed,
                "clear_status": record.clear_status.value,
                "terminally_finalized": record.terminally_finalized,
                "trigger_event": trigger_event,
            }

            get_checkpoint_runtime().write_checkpoint(
                sequence_number=seq,
                event_id=event_id,
                state_snapshot=snapshot,
                completed_keys=[
                    f"{record.source_session}:{record.run_id}:{trigger_event}"
                ],
                metadata={
                    "trigger": trigger_event,
                    "correlation_id": record.correlation_id,
                },
            )
        except Exception as exc:
            _log(f"WARNING: checkpoint write failed for {trigger_event}: {exc}")

    def start_run(
        self,
        source_session: str,
        *,
        task_id: str = "",
        correlation_id: str = "",
        role: str = "",
    ) -> RunHandle:
        """Register a new run for a session. Archives any prior active run."""
        with self._lock:
            # Archive previous run if it exists
            prev = self._active.get(source_session)
            if prev:
                self._archive.append(prev)
                if len(self._archive) > self._max_archive:
                    self._archive = self._archive[-self._max_archive :]

            # Increment generation
            gen = self._generations.get(source_session, 0) + 1
            self._generations[source_session] = gen

            record = RunLifecycleRecord(
                source_session=source_session,
                generation=gen,
                task_id=task_id,
                correlation_id=correlation_id,
                role=role,
            )
            record._record(
                "run_started",
                "lifecycle_manager",
                f"task={task_id} correlation={correlation_id}",
            )
            self._active[source_session] = record

            _log(
                f"run_started: session={source_session} gen={gen} "
                f"run_id={record.run_id} task={task_id}"
            )

        # Initialize execution tracker (outside lock — separate module)
        try:
            from umh.substrate.run_execution import init_execution_tracker

            init_execution_tracker(source_session)
        except Exception as exc:
            _log(f"execution tracker init failed (non-blocking): {exc}")

        # Hydrate runtime state from checkpoint + event replay (best-effort)
        try:
            from umh.substrate.runtime_bootstrap import initialize_runtime_state

            _store, _result = initialize_runtime_state(session_name=source_session)
            _log(
                f"state hydration: checkpoint={_result.checkpoint_loaded} "
                f"replayed={_result.events_replayed} "
                f"drift={_result.drift_detected} "
                f"hash={_result.final_state_hash}"
            )
        except Exception as exc:
            _log(f"state hydration failed (non-blocking): {exc}")

        return RunHandle(
            run_id=record.run_id,
            source_session=source_session,
            generation=gen,
        )

    def propose_completion(
        self,
        source_session: str,
        source: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> ProposalResult:
        """Propose that a run is complete. First valid proposal wins ownership.

        If no active run exists for this session, the proposal is accepted
        and a synthetic run is created (backward compat for paths that don't
        call start_run).
        """
        with self._lock:
            record = self._active.get(source_session)

            # Backward compat: if no run was started, create one now
            if record is None:
                gen = self._generations.get(source_session, 0) + 1
                self._generations[source_session] = gen
                record = RunLifecycleRecord(
                    source_session=source_session,
                    generation=gen,
                )
                record._record(
                    "run_started_synthetic",
                    source,
                    "no prior start_run — created on first proposal",
                )
                self._active[source_session] = record

            proposal = CompletionProposal(
                source=source,
                payload=payload or {},
            )

            # Terminal finalization — hard reject, lifecycle is CLOSED
            if record.terminally_finalized:
                proposal.rejected_reason = "run_terminally_finalized"
                record.completion_proposals.append(proposal)
                record._record(
                    "completion_proposed_rejected",
                    source,
                    "run terminally finalized — lifecycle closed",
                )
                return ProposalResult(
                    accepted=False,
                    is_owner=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="run_terminally_finalized",
                )

            # Already cleared — reject
            if record.status == RunStatus.CLEARED:
                proposal.rejected_reason = "run_already_cleared"
                record.completion_proposals.append(proposal)
                record._record(
                    "completion_proposed_rejected", source, "run already cleared"
                )
                return ProposalResult(
                    accepted=False,
                    is_owner=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="run_already_cleared",
                )

            # Already finalized — reject
            if record.status in (RunStatus.FINALIZED, RunStatus.CLEAR_REQUESTED):
                proposal.rejected_reason = "run_already_finalized"
                record.completion_proposals.append(proposal)
                record._record(
                    "completion_proposed_rejected", source, "run already finalized"
                )
                return ProposalResult(
                    accepted=False,
                    is_owner=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="run_already_finalized",
                )

            # First valid proposal — accept and assign ownership
            if not record.completion_owner:
                proposal.accepted = True
                record.completion_owner = source
                record.status = RunStatus.COMPLETION_PROPOSED
                record.completion_proposals.append(proposal)
                record._record(
                    "completion_owner_assigned",
                    source,
                    f"first proposal — {source} is now owner",
                )
                return ProposalResult(
                    accepted=True,
                    is_owner=True,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="first_proposal_accepted",
                )

            # Owner already assigned
            if record.completion_owner == source:
                # Same source proposing again — accept but not new owner
                proposal.accepted = True
                record.completion_proposals.append(proposal)
                record._record(
                    "completion_proposed_duplicate", source, "same source re-proposing"
                )
                return ProposalResult(
                    accepted=True,
                    is_owner=True,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="owner_re_proposal",
                )

            # Different source — record but reject
            proposal.rejected_reason = f"owner_is_{record.completion_owner}"
            record.completion_proposals.append(proposal)
            record._record(
                "completion_proposed_rejected",
                source,
                f"owner already assigned to {record.completion_owner}",
            )
            return ProposalResult(
                accepted=False,
                is_owner=False,
                run_id=record.run_id,
                generation=record.generation,
                reason=f"owner_is_{record.completion_owner}",
            )

    def attempt_finalization(
        self,
        source_session: str,
        source: str,
        finalize_fn: Callable[[], dict[str, Any]],
    ) -> FinalizationDecision:
        """Attempt canonical finalization. Only the owner may finalize.

        finalize_fn is called OUTSIDE the lock to avoid holding the lock
        during potentially slow I/O. The lock is re-acquired to record
        the outcome.
        """
        # Phase 1: check eligibility under lock
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                return FinalizationDecision(
                    allowed=False,
                    reason="no_active_run",
                )

            # Terminal finalization — hard reject
            if record.terminally_finalized:
                record._record(
                    "finalization_blocked",
                    source,
                    "run terminally finalized — lifecycle closed",
                )
                return FinalizationDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="blocked_terminally_finalized",
                )

            # Already cleared
            if record.status == RunStatus.CLEARED:
                record._record("finalization_blocked", source, "run already cleared")
                return FinalizationDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="blocked_already_cleared",
                )

            # Already finalized
            if record.finalization_status == FinalizationStatus.SUCCEEDED:
                record._record("finalization_blocked", source, "already finalized")
                return FinalizationDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="blocked_already_finalized",
                )

            # Not the owner
            if record.completion_owner and record.completion_owner != source:
                record._record(
                    "finalization_blocked",
                    source,
                    f"not owner (owner={record.completion_owner})",
                )
                return FinalizationDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason=f"blocked_not_owner_{record.completion_owner}",
                )

            # Mark as started
            record.status = RunStatus.FINALIZATION_STARTED
            record.finalization_status = FinalizationStatus.STARTED
            record._record("finalization_started", source)
            run_id = record.run_id
            gen = record.generation

        # Phase 2: execute finalization OUTSIDE lock
        try:
            result = finalize_fn()
        except Exception as exc:
            with self._lock:
                record = self._active.get(source_session)
                if record and record.generation == gen:
                    record.finalization_status = FinalizationStatus.FAILED
                    record._record("finalization_failed", source, str(exc))
            return FinalizationDecision(
                allowed=True,
                run_id=run_id,
                generation=gen,
                reason=f"finalization_exception: {exc}",
            )

        # Phase 3: record outcome under lock
        with self._lock:
            record = self._active.get(source_session)
            if record and record.generation == gen:
                record.finalization_result = result
                fin_success = result.get("success", False)
                if fin_success:
                    record.status = RunStatus.FINALIZED
                    record.finalization_status = FinalizationStatus.SUCCEEDED
                    record.finalized_at = _utcnow()
                    record.finalization_id = result.get("finalization_id", "")
                    record._record(
                        "finalization_succeeded",
                        source,
                        f"fin_id={record.finalization_id}",
                    )
                else:
                    record.finalization_status = FinalizationStatus.FAILED
                    record._record(
                        "finalization_failed",
                        source,
                        f"result_success=False errors={result.get('errors', [])}",
                    )

        return FinalizationDecision(
            allowed=True,
            run_id=run_id,
            generation=gen,
            finalization_result=result,
            reason="finalization_executed",
        )

    def record_publication(
        self,
        source_session: str,
        source: str,
        *,
        result_id: str = "",
    ) -> None:
        """Record that canonical artifact was published for the current run."""
        with self._lock:
            record = self._active.get(source_session)
            if record:
                record.canonical_result_id = result_id
                record.publication_confirmed = True
                record.publication_confirmed_at = _utcnow()
                record._record(
                    "publication_confirmed",
                    source,
                    f"result_id={result_id}",
                )

    def try_mark_clear_dispatched(
        self,
        source_session: str,
        source: str,
    ) -> bool:
        """Atomic exactly-once physical clear dispatch lock.

        This is the FIRST guard checked at the tmux injection boundary.
        If clear_dispatched is already True for this run, returns False
        immediately — the second /clear never reaches tmux.

        Returns:
            True  — first dispatch accepted, flag set atomically
            False — already dispatched, caller must NOT inject /clear
        """
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                _log(
                    f"clear_dispatch_attempt: session={source_session} "
                    f"source={source} result=no_active_run"
                )
                return False

            if record.clear_dispatched:
                record._record(
                    "clear_blocked_already_dispatched",
                    source,
                    f"first_dispatch_by={record.clear_dispatched_source} "
                    f"at={record.clear_dispatched_at}",
                )
                _log(
                    f"clear_blocked_already_dispatched: "
                    f"session={source_session} run={record.run_id} "
                    f"source={source} "
                    f"first_by={record.clear_dispatched_source} "
                    f"at={record.clear_dispatched_at}"
                )
                return False

            # Atomically claim the dispatch slot
            record.clear_dispatched = True
            record.clear_dispatched_at = _utcnow()
            record.clear_dispatched_source = source
            record._record(
                "clear_dispatch_succeeded",
                source,
                f"run={record.run_id} gen={record.generation}",
            )
            _log(
                f"clear_dispatch_succeeded: "
                f"session={source_session} run={record.run_id} "
                f"source={source}"
            )
            return True

    def request_clear(
        self,
        source_session: str,
        source: str,
    ) -> ClearDecision:
        """Request to clear the session for the current run.

        Rules:
          1. Clear only if finalization succeeded
          2. Clear only if session is QUIESCENT or STALLED_AFTER_PUBLICATION
          3. Clear at most once per run
          4. Log exact reason for block/allow

        NOTE: publication_confirmed is NOT required to start clear.
        It is only required for terminal seal (mark_terminal_if_complete).
        """
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                return ClearDecision(
                    allowed=False,
                    reason="no_active_run",
                )

            # Terminal finalization — hard reject
            if record.terminally_finalized:
                record._record(
                    "clear_blocked_terminally_finalized",
                    source,
                    "run terminally finalized — lifecycle closed",
                )
                return ClearDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="blocked_terminally_finalized",
                )

            # Already cleared or clear already requested
            if record.clear_status in (
                ClearStatus.REQUESTED,
                ClearStatus.SENT,
                ClearStatus.CONFIRMED,
                ClearStatus.STALLED_SAFE,
            ):
                record._record("clear_blocked_already_cleared", source)
                return ClearDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason="blocked_already_cleared_for_run",
                )

            # Finalization must have succeeded
            if record.finalization_status != FinalizationStatus.SUCCEEDED:
                reason = f"blocked_not_finalized_{record.finalization_status.value}"
                record._record(
                    "clear_blocked_not_finalized",
                    source,
                    f"fin_status={record.finalization_status.value}",
                )
                return ClearDecision(
                    allowed=False,
                    run_id=record.run_id,
                    generation=record.generation,
                    reason=reason,
                )

            # NOTE: publication_confirmed is NOT required to START clear.
            # It is only required for the terminal seal (mark_terminal_if_complete).
            # Delivery success → finalization succeeded → clear may proceed.

            # NOTE: Session readiness is NOT checked here. Readiness is a
            # physical/timing concern — it belongs in clear_session() where
            # the actual tmux injection happens. request_clear() answers
            # "is this run eligible for clear?" (lifecycle only).
            # clear_session() answers "is it safe to inject right now?"

            # ── All lifecycle gates pass — allow clear ───────────────
            record.clear_status = ClearStatus.REQUESTED
            record._record("clear_requested", source)
            record.status = RunStatus.CLEAR_REQUESTED
            run_id = record.run_id
            gen = record.generation

        return ClearDecision(
            allowed=True,
            run_id=run_id,
            generation=gen,
            reason="clear_allowed",
        )

    def confirm_clear(self, source_session: str, source: str) -> None:
        """Confirm that clear was actually sent to tmux."""
        with self._lock:
            record = self._active.get(source_session)
            if record is None or record.terminally_finalized:
                return  # lifecycle closed — ignore late confirmations
            if record.clear_status == ClearStatus.REQUESTED:
                record.clear_status = ClearStatus.CONFIRMED
                record.status = RunStatus.CLEARED
                record.cleared_at = _utcnow()
                record._record("clear_confirmed", source)
                # ── Durable checkpoint at clear boundary (Phase 1) ────
                self._write_lifecycle_checkpoint(record, "clear_confirmed")

    def mark_clear_sent(self, source_session: str, source: str) -> None:
        """Mark clear as sent (before tmux confirmation)."""
        with self._lock:
            record = self._active.get(source_session)
            if record and record.clear_status == ClearStatus.REQUESTED:
                record.clear_status = ClearStatus.SENT
                record._record("clear_sent", source)

    def mark_clear_failed(
        self, source_session: str, source: str, reason: str = ""
    ) -> None:
        """Mark clear as failed."""
        with self._lock:
            record = self._active.get(source_session)
            if record:
                record.clear_status = ClearStatus.FAILED
                record._record("clear_failed", source, reason)

    def get_record(self, source_session: str) -> Optional[RunLifecycleRecord]:
        """Get the current run record for a session (snapshot)."""
        with self._lock:
            return self._active.get(source_session)

    def get_forensics(self, source_session: str) -> list[dict[str, Any]]:
        """Get forensic entries for the current run."""
        with self._lock:
            record = self._active.get(source_session)
            if record:
                return [e.to_dict() for e in record.forensics]
            return []

    def get_all_records(self) -> dict[str, dict[str, Any]]:
        """Get all active run records (for diagnostics)."""
        with self._lock:
            return {k: v.to_dict() for k, v in self._active.items()}

    def mark_terminal_if_complete(
        self,
        source_session: str,
        source: str,
        *,
        no_clear_policy: bool = False,
    ) -> bool:
        """Seal the run lifecycle ONLY if all completion conditions are met.

        Conditions for sealing:
          - publication_confirmed == True
          AND one of:
            a) clear_status in (CONFIRMED, STALLED_SAFE)  — normal completion
            b) no_clear_policy == True                      — explicit skip

        Returns True if sealed, False if conditions not met or already sealed.
        """
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                return False
            if record.terminally_finalized:
                record._record(
                    "terminal_seal_duplicate",
                    source,
                    "already terminally finalized — ignoring",
                )
                return False

            # Gate: publication must be confirmed
            if not record.publication_confirmed:
                record._record(
                    "terminal_seal_blocked_not_published",
                    source,
                    "publication not confirmed — seal deferred",
                )
                _log(
                    f"terminal_seal_blocked_not_published: "
                    f"run={record.run_id} session={source_session} source={source}"
                )
                return False

            # Gate: clear must be completed OR explicit no-clear policy
            clear_done = record.clear_status in (
                ClearStatus.CONFIRMED,
                ClearStatus.STALLED_SAFE,
            )
            if not clear_done and not no_clear_policy:
                record._record(
                    "terminal_seal_blocked_not_cleared",
                    source,
                    f"clear_status={record.clear_status.value} "
                    f"no_clear_policy={no_clear_policy} — seal deferred",
                )
                _log(
                    f"terminal_seal_blocked_not_cleared: "
                    f"run={record.run_id} session={source_session} "
                    f"clear_status={record.clear_status.value} source={source}"
                )
                return False

            # All conditions met — seal
            record.terminally_finalized = True
            record.terminally_finalized_at = _utcnow()
            seal_path = "clear_completed" if clear_done else "no_clear_policy"
            record._record(
                "terminal_seal_applied",
                source,
                f"lifecycle CLOSED via {seal_path} — "
                f"publication=confirmed clear={record.clear_status.value}",
            )
            _log(
                f"TERMINAL_SEAL: run={record.run_id} session={source_session} "
                f"gen={record.generation} path={seal_path} source={source}"
            )
            # ── Durable checkpoint at terminal seal (Phase 1) ─────
            self._write_lifecycle_checkpoint(record, "terminal_seal_applied")
            return True

    def is_terminally_finalized(self, source_session: str) -> bool:
        """Check if the current run is terminally finalized (lifecycle closed)."""
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                return False
            return record.terminally_finalized

    def is_finalized(self, source_session: str) -> bool:
        """Check if the current run for a session is already finalized."""
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                return False
            return record.finalization_status == FinalizationStatus.SUCCEEDED

    def is_cleared(self, source_session: str) -> bool:
        """Check if the current run for a session is already cleared or clear requested."""
        with self._lock:
            record = self._active.get(source_session)
            if record is None:
                return False
            return record.clear_status in (
                ClearStatus.REQUESTED,
                ClearStatus.SENT,
                ClearStatus.CONFIRMED,
                ClearStatus.STALLED_SAFE,
            )

    def reset_for_tests(self) -> None:
        """Test helper — clear all state."""
        with self._lock:
            self._active.clear()
            self._generations.clear()
            self._archive.clear()


# ─── Module-level singleton ────────────────────────────────────────────────

_manager = _RunLifecycleManager()


# ─── Public API (delegates to singleton) ───────────────────────────────────


def start_run(
    source_session: str,
    *,
    task_id: str = "",
    correlation_id: str = "",
    role: str = "",
) -> RunHandle:
    """Register a new run for a session. Call when sending a task to CC."""
    return _manager.start_run(
        source_session,
        task_id=task_id,
        correlation_id=correlation_id,
        role=role,
    )


def propose_run_completion(
    source_session: str,
    source: str,
    *,
    payload: dict[str, Any] | None = None,
) -> ProposalResult:
    """Propose that the current run is complete. First valid proposal wins.

    When ORCHESTRATION_MODE=active, also emits an operator_intent_requested
    event into the production scheduler so the orchestration layer drives
    the lifecycle progression instead of the legacy self-chaining handlers.
    The legacy proposal is still recorded for ownership semantics.
    """
    result = _manager.propose_completion(source_session, source, payload=payload)

    # ── Orchestration ingress (mode-gated) ─────────────────────────
    if result.accepted:
        try:
            from umh.substrate.orchestration_mode import orchestration_mode_active

            if orchestration_mode_active():
                _emit_orchestration_ingress(
                    intent_type="lifecycle_finalize",
                    goal={"session_name": source_session, **(payload or {})},
                    session_name=source_session,
                    source=source,
                )
        except Exception as exc:
            _log(f"orchestration ingress emission failed (non-blocking): {exc}")

    return result


def _emit_orchestration_ingress(
    intent_type: str,
    goal: dict[str, Any],
    session_name: str,
    source: str,
    priority: int = 100,
) -> None:
    """Emit an orchestration ingress event into the production scheduler.

    Uses the trigger adapter to build the event, then emits into the
    primary scheduler via execution_authority.  Best-effort, never blocks
    the caller.
    """
    from umh.substrate.execution_authority import _get_primary_scheduler
    try:
        from umh.substrate.trigger_adapters import from_operator
    except ImportError:
        pass

    scheduler, _store = _get_primary_scheduler()
    event = from_operator(
        intent_type=intent_type,
        goal=goal,
        priority=priority,
        session_name=session_name,
        operator_id=source,
    )
    scheduler.emit(event)
    _log(
        f"orchestration ingress emitted: type={intent_type} "
        f"session={session_name} source={source}"
    )


def attempt_canonical_finalization(
    source_session: str,
    source: str,
    finalize_fn: Callable[[], dict[str, Any]],
) -> FinalizationDecision:
    """Attempt canonical finalization. Only the owner may finalize.

    When ORCHESTRATION_MODE=active: orchestration drives lifecycle via
    IntentCoordinator plan steps. Return immediately — the coordinator
    will emit finalization events through its workflow.

    In EVENT_PRIMARY mode: scheduler executes finalization, legacy is
    fallback on scheduler failure.
    """
    # ── Orchestration takes over lifecycle progression ──────────────
    try:
        from umh.substrate.orchestration_mode import orchestration_mode_active

        if orchestration_mode_active():
            _log(
                f"orchestration active — deferring finalization to coordinator: "
                f"session={source_session}"
            )
            record = _manager.get_record(source_session)
            return FinalizationDecision(
                allowed=True,
                run_id=record.run_id if record else "",
                reason="orchestration_deferred",
                finalization_result={"orchestration_deferred": True},
            )
    except Exception as exc:
        _log(f"orchestration mode check failed, falling through: {exc}")

    mode = get_execution_mode()

    if mode == ExecutionMode.EVENT_PRIMARY:
        try:
            from umh.substrate.execution_authority import event_primary_finalize

            record = _manager.get_record(source_session)
            run_id = record.run_id if record else ""

            ep_result = event_primary_finalize(
                session_name=source_session,
                source=source,
                finalize_fn=finalize_fn,
                run_id=run_id,
            )
            state = ep_result.final_state
            _log(
                f"EVENT_PRIMARY finalization: session={source_session} "
                f"finalization_status={state.get('finalization_status')} "
                f"hash={ep_result.state_hash}"
            )
            # Translate scheduler state into FinalizationDecision
            fin_status = state.get("finalization_status")
            return FinalizationDecision(
                allowed=fin_status == "succeeded",
                run_id=run_id,
                reason="event_primary_finalization_executed",
                finalization_result=state,
            )
        except Exception as exc:
            _log(
                f"EVENT_PRIMARY finalization FAILED, falling back to LEGACY: "
                f"session={source_session} error={exc}"
            )
            # Fall through to legacy

    return _manager.attempt_finalization(source_session, source, finalize_fn)


def record_run_publication(
    source_session: str,
    source: str,
    *,
    result_id: str = "",
) -> None:
    """Record that canonical artifact was published for the current run.

    When ORCHESTRATION_MODE=active: orchestration handles publication as
    a plan step. Still record in legacy manager for forensics.

    In EVENT_PRIMARY mode: scheduler records publication, legacy is fallback.
    """
    # ── Orchestration handles publication via plan steps ────────────
    try:
        from umh.substrate.orchestration_mode import orchestration_mode_active

        if orchestration_mode_active():
            _log(
                f"orchestration active — publication deferred to coordinator: "
                f"session={source_session}"
            )
            # Still update legacy record for forensics/backward compat
            _manager.record_publication(source_session, source, result_id=result_id)
            return
    except Exception as exc:
        _log(f"orchestration mode check failed, falling through: {exc}")

    mode = get_execution_mode()

    if mode == ExecutionMode.EVENT_PRIMARY:
        try:
            from umh.substrate.execution_authority import (
                event_primary_record_publication,
            )

            record = _manager.get_record(source_session)
            run_id = record.run_id if record else ""

            ep_result = event_primary_record_publication(
                session_name=source_session,
                source=source,
                result_id=result_id,
                run_id=run_id,
            )
            _log(
                f"EVENT_PRIMARY publication: session={source_session} "
                f"publication_confirmed={ep_result.final_state.get('publication_confirmed')} "
                f"hash={ep_result.state_hash}"
            )
            return
        except Exception as exc:
            _log(
                f"EVENT_PRIMARY publication FAILED, falling back to LEGACY: "
                f"session={source_session} error={exc}"
            )

    _manager.record_publication(source_session, source, result_id=result_id)


def try_mark_clear_dispatched(
    source_session: str,
    source: str,
) -> bool:
    """Atomic exactly-once physical clear dispatch lock.

    Call this BEFORE injecting /clear into tmux. Returns True only for
    the first caller per run — all subsequent callers get False and must
    NOT inject /clear. This is the earliest and strongest dedupe signal.
    """
    return _manager.try_mark_clear_dispatched(source_session, source)


def request_run_clear(
    source_session: str,
    source: str,
) -> ClearDecision:
    """Request permission to clear the session for the current run.

    When ORCHESTRATION_MODE=active: orchestration handles clear as a
    plan step. Return allowed=True so caller records the decision.

    In EVENT_PRIMARY mode: scheduler processes clear request, legacy is fallback.
    """
    # ── Orchestration handles clear via plan steps ─────────────────
    try:
        from umh.substrate.orchestration_mode import orchestration_mode_active

        if orchestration_mode_active():
            _log(
                f"orchestration active — clear deferred to coordinator: "
                f"session={source_session}"
            )
            record = _manager.get_record(source_session)
            return ClearDecision(
                allowed=True,
                run_id=record.run_id if record else "",
                reason="orchestration_deferred",
            )
    except Exception as exc:
        _log(f"orchestration mode check failed, falling through: {exc}")

    mode = get_execution_mode()

    if mode == ExecutionMode.EVENT_PRIMARY:
        try:
            from umh.substrate.execution_authority import (
                event_primary_request_clear,
            )

            record = _manager.get_record(source_session)
            run_id = record.run_id if record else ""

            ep_result = event_primary_request_clear(
                session_name=source_session,
                source=source,
                run_id=run_id,
            )
            state = ep_result.final_state
            clear_status = state.get("clear_status", "")
            _log(
                f"EVENT_PRIMARY clear request: session={source_session} "
                f"clear_status={clear_status} hash={ep_result.state_hash}"
            )
            return ClearDecision(
                allowed=clear_status in ("requested", "confirmed"),
                run_id=run_id,
                reason=f"event_primary_clear_{clear_status}",
            )
        except Exception as exc:
            _log(
                f"EVENT_PRIMARY clear request FAILED, falling back to LEGACY: "
                f"session={source_session} error={exc}"
            )

    return _manager.request_clear(source_session, source)


def confirm_run_clear(source_session: str, source: str) -> None:
    """Confirm clear was executed.

    In EVENT_PRIMARY mode: scheduler confirms clear, legacy is fallback.
    """
    mode = get_execution_mode()

    if mode == ExecutionMode.EVENT_PRIMARY:
        try:
            from umh.substrate.execution_authority import (
                event_primary_confirm_clear,
            )

            record = _manager.get_record(source_session)
            run_id = record.run_id if record else ""

            ep_result = event_primary_confirm_clear(
                session_name=source_session,
                source=source,
                run_id=run_id,
            )
            _log(
                f"EVENT_PRIMARY clear confirmed: session={source_session} "
                f"clear_status={ep_result.final_state.get('clear_status')} "
                f"hash={ep_result.state_hash}"
            )
            return
        except Exception as exc:
            _log(
                f"EVENT_PRIMARY clear confirm FAILED, falling back to LEGACY: "
                f"session={source_session} error={exc}"
            )

    _manager.confirm_clear(source_session, source)


def mark_clear_sent(source_session: str, source: str) -> None:
    """Mark clear as sent to tmux."""
    _manager.mark_clear_sent(source_session, source)


def mark_clear_failed(source_session: str, source: str, reason: str = "") -> None:
    """Mark clear as failed."""
    _manager.mark_clear_failed(source_session, source, reason)


def get_run_record(
    source_session: str,
) -> Optional[RunLifecycleRecord]:
    """Get the current run record for a session."""
    return _manager.get_record(source_session)


def get_run_forensics(source_session: str) -> list[dict[str, Any]]:
    """Get forensic log for the current run."""
    return _manager.get_forensics(source_session)


def get_all_run_records() -> dict[str, dict[str, Any]]:
    """Get all active run records."""
    return _manager.get_all_records()


def mark_run_terminal_if_complete(
    source_session: str,
    source: str,
    *,
    no_clear_policy: bool = False,
) -> bool:
    """Seal the run lifecycle IF all completion conditions are met.

    Conditions:
      - publication_confirmed == True
      - clear_completed == True OR no_clear_policy == True

    In EVENT_PRIMARY mode: scheduler applies terminal seal, legacy is fallback.
    """
    mode = get_execution_mode()

    if mode == ExecutionMode.EVENT_PRIMARY:
        try:
            from umh.substrate.execution_authority import (
                event_primary_mark_terminal,
            )

            record = _manager.get_record(source_session)
            run_id = record.run_id if record else ""

            ep_result = event_primary_mark_terminal(
                session_name=source_session,
                source=source,
                no_clear_policy=no_clear_policy,
                run_id=run_id,
            )
            sealed = ep_result.final_state.get("terminally_finalized", False)
            _log(
                f"EVENT_PRIMARY terminal seal: session={source_session} "
                f"sealed={sealed} hash={ep_result.state_hash}"
            )
            return sealed
        except Exception as exc:
            _log(
                f"EVENT_PRIMARY terminal seal FAILED, falling back to LEGACY: "
                f"session={source_session} error={exc}"
            )

    return _manager.mark_terminal_if_complete(
        source_session, source, no_clear_policy=no_clear_policy
    )


def is_run_terminally_finalized(source_session: str) -> bool:
    """Check if the current run's lifecycle is permanently closed."""
    return _manager.is_terminally_finalized(source_session)


def is_run_finalized(source_session: str) -> bool:
    """Check if current run is already finalized."""
    return _manager.is_finalized(source_session)


def is_run_cleared(source_session: str) -> bool:
    """Check if current run is already cleared."""
    return _manager.is_cleared(source_session)


def reset_for_tests() -> None:
    """Test helper."""
    _manager.reset_for_tests()
    reset_shadow_scheduler_for_testing()
    set_execution_mode_for_testing(None)


__all__ = [
    "ExecutionMode",
    "get_execution_mode",
    "set_execution_mode_for_testing",
    "RunStatus",
    "FinalizationStatus",
    "ClearStatus",
    "ForensicEntry",
    "CompletionProposal",
    "RunLifecycleRecord",
    "ProposalResult",
    "FinalizationDecision",
    "ClearDecision",
    "RunHandle",
    "start_run",
    "propose_run_completion",
    "attempt_canonical_finalization",
    "record_run_publication",
    "try_mark_clear_dispatched",
    "request_run_clear",
    "confirm_run_clear",
    "mark_clear_sent",
    "mark_clear_failed",
    "mark_run_terminal_if_complete",
    "is_run_terminally_finalized",
    "get_run_record",
    "get_run_forensics",
    "get_all_run_records",
    "is_run_finalized",
    "is_run_cleared",
    "reset_for_tests",
]
