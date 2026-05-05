"""
Replay Validation — dual-mode replay engine with mutation drift detection.

Two replay modes protect the event log as both executable and verifiable truth:

  FAST REPLAY   — applies recorded mutations from the log directly.
                  Used for runtime recovery. O(n) in log length.

  VERIFY REPLAY — re-executes primitives, recomputes mutations,
                  compares mutation_hash against the log record.
                  Detects logic drift / silent corruption.

Verification runs selectively:
  - on deploy
  - at checkpoint boundaries
  - on sampled sessions
  - on failure recovery

On drift detection the session is halted and replayed from last
checkpoint in verify mode. Persistent mismatch marks the session invalid.

No external dependencies. Pure data operations + hashing.
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# ─── Logging ────────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.replay_validation]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr, flush=True)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ─── Core Data Models ───────────────────────────────────────────────────────


class MutationOp(str, Enum):
    """State mutation operations."""

    SET = "SET"
    DELETE = "DELETE"
    INCREMENT = "INCREMENT"


@dataclass(frozen=True)
class StateMutation:
    """Explicit record of a single state change.

    Carried inside every EventLogEntry so replay can reconstruct
    state without re-executing primitives.

    Attributes:
        key: State store key being mutated.
        operation: SET, DELETE, or INCREMENT.
        value: New value (SET) or delta (INCREMENT). None for DELETE.
        previous_value: Value before mutation. None if unknown or first write.
    """

    key: str
    operation: MutationOp
    value: Any = None
    previous_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "operation": self.operation.value,
            "value": self.value,
            "previous_value": self.previous_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateMutation":
        return cls(
            key=data["key"],
            operation=MutationOp(data["operation"]),
            value=data.get("value"),
            previous_value=data.get("previous_value"),
        )


def compute_mutation_hash(mutations: list[StateMutation]) -> str:
    """Deterministic SHA-256 hash of a mutation list.

    The canonical form is a JSON array sorted by key, with
    deterministic serialization. This is the integrity seal:
    if recomputed mutations produce a different hash, the log
    has drifted from the actual primitive logic.

    Returns:
        First 16 hex chars of SHA-256 digest.
    """
    canonical = json.dumps(
        [m.to_dict() for m in sorted(mutations, key=lambda m: m.key)],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ─── Event Log Entry ────────────────────────────────────────────────────────


@dataclass
class EventLogEntry:
    """Single entry in the append-only event log.

    This wraps the raw Event with sequence ordering, explicit mutations,
    and a mutation hash for verification.

    Attributes:
        sequence_number: Monotonic, gap-free, assigned by log writer.
        event_id: UUID from the event spine.
        event_type: Canonical event type string.
        causal_event_id: Which event caused this one.
        correlation_id: Workflow thread.
        source: Originating subsystem.
        source_session: Specific session.
        event_time: When the event occurred (ISO8601 UTC).
        log_time: When the entry was written to the log (ISO8601 UTC).
        payload: Event-specific data.
        state_mutations: Explicit state changes this event caused.
        mutation_hash: SHA-256 hash of state_mutations for verification.
        metadata: Envelope metadata (node_id, execution_id, etc).
    """

    sequence_number: int
    event_id: str
    event_type: str
    correlation_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    state_mutations: list[StateMutation] = field(default_factory=list)
    mutation_hash: str = ""
    causal_event_id: Optional[str] = None
    source: str = ""
    source_session: str = ""
    event_time: str = field(default_factory=_now_iso)
    log_time: str = field(default_factory=_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mutation_hash and self.state_mutations:
            self.mutation_hash = compute_mutation_hash(self.state_mutations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_number": self.sequence_number,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "causal_event_id": self.causal_event_id,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "source_session": self.source_session,
            "event_time": self.event_time,
            "log_time": self.log_time,
            "payload": self.payload,
            "state_mutations": [m.to_dict() for m in self.state_mutations],
            "mutation_hash": self.mutation_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventLogEntry":
        mutations = [
            StateMutation.from_dict(m) for m in data.get("state_mutations", [])
        ]
        return cls(
            sequence_number=data["sequence_number"],
            event_id=data["event_id"],
            event_type=data["event_type"],
            causal_event_id=data.get("causal_event_id"),
            correlation_id=data.get("correlation_id", ""),
            source=data.get("source", ""),
            source_session=data.get("source_session", ""),
            event_time=data.get("event_time", ""),
            log_time=data.get("log_time", ""),
            payload=data.get("payload", {}),
            state_mutations=mutations,
            mutation_hash=data.get("mutation_hash", ""),
            metadata=data.get("metadata", {}),
        )


# ─── Append-Only Event Log ─────────────────────────────────────────────────


class EventLog:
    """Append-only event log — the source of truth.

    Single writer (control plane). Thread-safe.
    Never mutates existing entries.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._next_seq = 0
        self._boot()

    def _boot(self) -> None:
        """Scan log to find the next sequence number."""
        import os

        if not os.path.exists(self._path):
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            return
        last_seq = -1
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        seq = entry.get("sequence_number", -1)
                        if seq > last_seq:
                            last_seq = seq
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass
        self._next_seq = last_seq + 1

    def append(
        self,
        event_id: str,
        event_type: str,
        mutations: list[StateMutation],
        *,
        correlation_id: str = "",
        causal_event_id: Optional[str] = None,
        source: str = "",
        source_session: str = "",
        payload: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> EventLogEntry:
        """Append an event with its state mutations.

        Returns the created EventLogEntry with assigned sequence_number.
        Raises on I/O failure (caller must handle).
        """
        with self._lock:
            entry = EventLogEntry(
                sequence_number=self._next_seq,
                event_id=event_id,
                event_type=event_type,
                causal_event_id=causal_event_id,
                correlation_id=correlation_id,
                source=source,
                source_session=source_session,
                event_time=_now_iso(),
                log_time=_now_iso(),
                payload=payload or {},
                state_mutations=mutations,
                metadata=metadata or {},
            )
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
                f.flush()
            self._next_seq += 1
            return entry

    def read_from(
        self, sequence_number: int = 0, limit: int = 10_000
    ) -> list[EventLogEntry]:
        """Read entries starting from a sequence number."""
        entries: list[EventLogEntry] = []
        with self._lock:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        seq = data.get("sequence_number", -1)
                        if seq >= sequence_number:
                            entries.append(EventLogEntry.from_dict(data))
                            if len(entries) >= limit:
                                break
                        # Entries before our start are skipped
                        # but we still scan because the file is ordered
                        # and we cannot seek by line in JSONL
                    # fallthrough: EOF reached
                    pass
            except FileNotFoundError:
                pass
        return entries

    def read_range(self, start: int, end: int) -> list[EventLogEntry]:
        """Read entries in [start, end) sequence range."""
        return [
            e
            for e in self.read_from(start, limit=end - start + 1)
            if e.sequence_number < end
        ]

    def last_sequence(self) -> int:
        """Return the last assigned sequence number, or -1 if empty."""
        with self._lock:
            return self._next_seq - 1


# ─── Replay Modes ───────────────────────────────────────────────────────────


class ReplayMode(str, Enum):
    """Replay strategy."""

    FAST = "fast"
    VERIFY = "verify"


@dataclass
class DriftRecord:
    """Single mutation drift detection record.

    Attributes:
        event_id: The event where drift was detected.
        sequence_number: Log position of the divergence.
        expected_hash: mutation_hash from the log.
        actual_hash: Recomputed mutation_hash from primitives.
        expected_mutations: Mutations recorded in log.
        actual_mutations: Mutations recomputed by primitive.
    """

    event_id: str
    sequence_number: int
    expected_hash: str
    actual_hash: str
    expected_mutations: list[dict[str, Any]] = field(default_factory=list)
    actual_mutations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "sequence_number": self.sequence_number,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "expected_mutations": self.expected_mutations,
            "actual_mutations": self.actual_mutations,
        }


@dataclass
class ReplayResult:
    """Outcome of a replay operation.

    Attributes:
        mode: Which replay mode was used.
        state: Final state after replay.
        entries_processed: Number of log entries replayed.
        from_sequence: Starting sequence number.
        to_sequence: Ending sequence number (inclusive).
        drift_records: List of detected mutation drifts (verify mode only).
        duration_ms: Wall-clock time for replay.
        valid: True if no drift detected (always True for fast mode).
        halted_at: Sequence number where replay was halted due to drift.
    """

    mode: ReplayMode
    state: dict[str, Any] = field(default_factory=dict)
    entries_processed: int = 0
    from_sequence: int = 0
    to_sequence: int = -1
    drift_records: list[DriftRecord] = field(default_factory=list)
    duration_ms: float = 0.0
    valid: bool = True
    halted_at: Optional[int] = None

    @property
    def mutation_mismatch_count(self) -> int:
        return len(self.drift_records)

    @property
    def first_divergence_event_id(self) -> Optional[str]:
        if self.drift_records:
            return self.drift_records[0].event_id
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "entries_processed": self.entries_processed,
            "from_sequence": self.from_sequence,
            "to_sequence": self.to_sequence,
            "mutation_mismatch_count": self.mutation_mismatch_count,
            "first_divergence_event_id": self.first_divergence_event_id,
            "duration_ms": round(self.duration_ms, 3),
            "valid": self.valid,
            "halted_at": self.halted_at,
            "drift_records": [d.to_dict() for d in self.drift_records],
        }


# ─── State Projection (apply mutations to state) ───────────────────────────


def apply_mutations(state: dict[str, Any], mutations: list[StateMutation]) -> None:
    """Apply a list of mutations to a state dict in place.

    This is the core projection function. Given any state snapshot
    and a list of mutations, it produces the next state. Deterministic.
    """
    for m in mutations:
        if m.operation == MutationOp.SET:
            state[m.key] = m.value
        elif m.operation == MutationOp.DELETE:
            state.pop(m.key, None)
        elif m.operation == MutationOp.INCREMENT:
            current = state.get(m.key, 0)
            state[m.key] = current + (m.value or 0)


# ─── Primitive Re-executor Type ─────────────────────────────────────────────

# A PrimitiveReExecutor is a callable that, given an EventLogEntry and
# the current state, re-runs the primitive logic and returns the
# mutations that SHOULD have been produced.
#
# In verify mode, the replay engine calls this for each entry,
# then compares the recomputed mutations against the log record.
#
# Signature: (entry, current_state) -> list[StateMutation]

PrimitiveReExecutor = Callable[[EventLogEntry, dict[str, Any]], list[StateMutation]]


# ─── Replay Engine ──────────────────────────────────────────────────────────


def replay_fast(
    log: EventLog,
    *,
    from_seq: int = 0,
    to_seq: Optional[int] = None,
    initial_state: Optional[dict[str, Any]] = None,
) -> ReplayResult:
    """Fast replay — apply mutations from log. O(n) in entries.

    Does NOT re-execute primitives.
    Does NOT emit events.
    Does NOT dispatch to execution plane.
    Deterministic: same log -> same state, always.

    Args:
        log: The event log to replay from.
        from_seq: Starting sequence number (inclusive).
        to_seq: Ending sequence number (inclusive). None = end of log.
        initial_state: Starting state (e.g. from checkpoint). Default empty.

    Returns:
        ReplayResult with the reconstructed state.
    """
    start_time = time.monotonic()
    state = dict(initial_state) if initial_state else {}
    effective_to = to_seq if to_seq is not None else log.last_sequence()

    entries = log.read_from(from_seq)
    processed = 0

    for entry in entries:
        if to_seq is not None and entry.sequence_number > to_seq:
            break
        apply_mutations(state, entry.state_mutations)
        processed += 1

    elapsed = (time.monotonic() - start_time) * 1000

    _log(
        f"fast replay: {processed} entries "
        f"[{from_seq}..{effective_to}] in {elapsed:.1f}ms"
    )

    return ReplayResult(
        mode=ReplayMode.FAST,
        state=state,
        entries_processed=processed,
        from_sequence=from_seq,
        to_sequence=effective_to,
        duration_ms=elapsed,
        valid=True,
    )


def replay_verify(
    log: EventLog,
    re_executor: PrimitiveReExecutor,
    *,
    from_seq: int = 0,
    to_seq: Optional[int] = None,
    initial_state: Optional[dict[str, Any]] = None,
    halt_on_drift: bool = True,
) -> ReplayResult:
    """Verify replay — re-execute primitives and compare mutation hashes.

    For each entry:
    1. Call re_executor to get what the primitive SHOULD produce.
    2. Compute mutation_hash from the recomputed mutations.
    3. Compare against the mutation_hash in the log entry.
    4. If mismatch: record a DriftRecord.

    The log mutations are still applied to state (they are the record
    of what actually happened). Drift records indicate where the
    primitive logic has diverged from what was recorded.

    Args:
        log: The event log to replay.
        re_executor: Callable that re-runs primitive logic.
        from_seq: Starting sequence number.
        to_seq: Ending sequence number. None = end of log.
        initial_state: Starting state from checkpoint.
        halt_on_drift: If True, stop at first drift. Default True.

    Returns:
        ReplayResult with drift records.
    """
    start_time = time.monotonic()
    state = dict(initial_state) if initial_state else {}
    effective_to = to_seq if to_seq is not None else log.last_sequence()
    drift_records: list[DriftRecord] = []
    processed = 0

    entries = log.read_from(from_seq)

    for entry in entries:
        if to_seq is not None and entry.sequence_number > to_seq:
            break

        # Re-execute primitive to get expected mutations
        try:
            recomputed = re_executor(entry, state)
        except Exception as exc:
            _log(
                f"re-executor failed at seq={entry.sequence_number} "
                f"event={entry.event_id}: {exc}"
            )
            recomputed = []

        recomputed_hash = compute_mutation_hash(recomputed) if recomputed else ""
        recorded_hash = entry.mutation_hash

        # Compare hashes
        if recomputed_hash != recorded_hash:
            drift = DriftRecord(
                event_id=entry.event_id,
                sequence_number=entry.sequence_number,
                expected_hash=recorded_hash,
                actual_hash=recomputed_hash,
                expected_mutations=[m.to_dict() for m in entry.state_mutations],
                actual_mutations=[m.to_dict() for m in recomputed],
            )
            drift_records.append(drift)
            _log(
                f"DRIFT at seq={entry.sequence_number} "
                f"event={entry.event_id}: "
                f"expected={recorded_hash} actual={recomputed_hash}"
            )

            if halt_on_drift:
                elapsed = (time.monotonic() - start_time) * 1000
                return ReplayResult(
                    mode=ReplayMode.VERIFY,
                    state=state,
                    entries_processed=processed,
                    from_sequence=from_seq,
                    to_sequence=effective_to,
                    drift_records=drift_records,
                    duration_ms=elapsed,
                    valid=False,
                    halted_at=entry.sequence_number,
                )

        # Apply the LOGGED mutations (what actually happened)
        apply_mutations(state, entry.state_mutations)
        processed += 1

    elapsed = (time.monotonic() - start_time) * 1000
    valid = len(drift_records) == 0

    _log(
        f"verify replay: {processed} entries "
        f"[{from_seq}..{effective_to}] in {elapsed:.1f}ms — "
        f"{'VALID' if valid else f'{len(drift_records)} drifts'}"
    )

    return ReplayResult(
        mode=ReplayMode.VERIFY,
        state=state,
        entries_processed=processed,
        from_sequence=from_seq,
        to_sequence=effective_to,
        drift_records=drift_records,
        duration_ms=elapsed,
        valid=valid,
    )


# ─── Checkpoint ─────────────────────────────────────────────────────────────


@dataclass
class Checkpoint:
    """Execution checkpoint — snapshot of state at a known-good point.

    Attributes:
        checkpoint_id: Unique identifier.
        sequence_number: Log position this checkpoint covers through.
        state_snapshot: Full state store contents at this point.
        in_flight: Execution IDs dispatched but not yet completed.
        completed_keys: Idempotency keys in the completed set.
        verify_hash: SHA-256 of canonical state snapshot.
        session_id: Session this checkpoint belongs to.
        created_at: When the checkpoint was taken.
    """

    checkpoint_id: str
    sequence_number: int
    state_snapshot: dict[str, Any]
    in_flight: list[str] = field(default_factory=list)
    completed_keys: list[str] = field(default_factory=list)
    verify_hash: str = ""
    session_id: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if not self.verify_hash:
            self.verify_hash = _state_hash(self.state_snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "sequence_number": self.sequence_number,
            "state_snapshot": self.state_snapshot,
            "in_flight": self.in_flight,
            "completed_keys": self.completed_keys,
            "verify_hash": self.verify_hash,
            "session_id": self.session_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            sequence_number=data["sequence_number"],
            state_snapshot=data.get("state_snapshot", {}),
            in_flight=data.get("in_flight", []),
            completed_keys=data.get("completed_keys", []),
            verify_hash=data.get("verify_hash", ""),
            session_id=data.get("session_id"),
            created_at=data.get("created_at", ""),
        )


def _state_hash(state: dict[str, Any]) -> str:
    """SHA-256 hash of canonical JSON state snapshot."""
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


class CheckpointStore:
    """JSONL-backed checkpoint persistence.

    File: /opt/OS/logs/harness_checkpoints.jsonl
    Append-only. Load latest by scanning.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        import os

        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> None:
        """Append a checkpoint to the store."""
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(checkpoint.to_dict()) + "\n")
                f.flush()

    def load_latest(self, session_id: Optional[str] = None) -> Optional[Checkpoint]:
        """Load the most recent checkpoint, optionally filtered by session.

        Scans the entire file (checkpoints are infrequent, file is small).
        """
        latest: Optional[dict[str, Any]] = None
        with self._lock:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if session_id and data.get("session_id") != session_id:
                            continue
                        # Higher sequence_number = more recent
                        if latest is None or data.get(
                            "sequence_number", -1
                        ) > latest.get("sequence_number", -1):
                            latest = data
            except FileNotFoundError:
                return None
        return Checkpoint.from_dict(latest) if latest else None

    def load_all(self) -> list[Checkpoint]:
        """Load all checkpoints (for audit/cleanup)."""
        checkpoints: list[Checkpoint] = []
        with self._lock:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            checkpoints.append(Checkpoint.from_dict(data))
                        except (json.JSONDecodeError, KeyError):
                            pass
            except FileNotFoundError:
                pass
        return checkpoints


# ─── Verification Policy ────────────────────────────────────────────────────


class VerificationTrigger(str, Enum):
    """When to run verify replay instead of fast replay."""

    DEPLOY = "deploy"
    CHECKPOINT_BOUNDARY = "checkpoint_boundary"
    SAMPLED_SESSION = "sampled_session"
    FAILURE_RECOVERY = "failure_recovery"
    MANUAL = "manual"


@dataclass
class VerificationPolicy:
    """Controls when verification runs.

    Attributes:
        sample_rate: Fraction of sessions to verify (0.0 to 1.0).
        verify_on_deploy: Always verify after deployment.
        verify_on_checkpoint: Verify at checkpoint boundaries.
        verify_on_recovery: Verify during failure recovery.
        max_verify_entries: Cap on entries per verify pass (cost control).
    """

    sample_rate: float = 0.1
    verify_on_deploy: bool = True
    verify_on_checkpoint: bool = True
    verify_on_recovery: bool = True
    max_verify_entries: int = 500

    def should_verify(self, trigger: VerificationTrigger) -> bool:
        """Decide whether to run verify replay for a given trigger."""
        if trigger == VerificationTrigger.DEPLOY:
            return self.verify_on_deploy
        if trigger == VerificationTrigger.CHECKPOINT_BOUNDARY:
            return self.verify_on_checkpoint
        if trigger == VerificationTrigger.FAILURE_RECOVERY:
            return self.verify_on_recovery
        if trigger == VerificationTrigger.SAMPLED_SESSION:
            import random

            return random.random() < self.sample_rate
        if trigger == VerificationTrigger.MANUAL:
            return True
        return False


# ─── Drift Detection + Events ──────────────────────────────────────────────


@dataclass
class DriftEvent:
    """Emitted when mutation drift is detected.

    This is the structured signal that triggers recovery.
    Integrate with the event spine by creating an Event with
    this payload.
    """

    session_id: str
    first_divergence_seq: int
    first_divergence_event_id: str
    mismatch_count: int
    trigger: VerificationTrigger
    replay_result_summary: dict[str, Any]
    detected_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": "mutation_drift_detected",
            "session_id": self.session_id,
            "first_divergence_seq": self.first_divergence_seq,
            "first_divergence_event_id": self.first_divergence_event_id,
            "mismatch_count": self.mismatch_count,
            "trigger": self.trigger.value,
            "replay_result_summary": self.replay_result_summary,
            "detected_at": self.detected_at,
        }


# ─── Recovery Strategy ──────────────────────────────────────────────────────


class SessionValidity(str, Enum):
    """Session state after drift recovery attempt."""

    VALID = "valid"
    RECOVERED = "recovered"
    INVALID = "invalid"


@dataclass
class RecoveryResult:
    """Outcome of a drift recovery attempt.

    Attributes:
        session_id: The session that was recovered.
        validity: Final session state.
        checkpoint_used: Which checkpoint was the recovery base.
        fast_replay: Result of fast replay from checkpoint.
        verify_replay: Result of verify replay from checkpoint.
        halted: Whether new execution was halted for this session.
        detail: Additional recovery context.
    """

    session_id: str
    validity: SessionValidity
    checkpoint_used: Optional[Checkpoint] = None
    fast_replay: Optional[ReplayResult] = None
    verify_replay: Optional[ReplayResult] = None
    halted: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "session_id": self.session_id,
            "validity": self.validity.value,
            "halted": self.halted,
            "detail": self.detail,
        }
        if self.checkpoint_used:
            result["checkpoint_seq"] = self.checkpoint_used.sequence_number
        if self.fast_replay:
            result["fast_replay"] = self.fast_replay.to_dict()
        if self.verify_replay:
            result["verify_replay"] = self.verify_replay.to_dict()
        return result


def recover_from_drift(
    log: EventLog,
    checkpoint_store: CheckpointStore,
    re_executor: PrimitiveReExecutor,
    session_id: str,
) -> RecoveryResult:
    """Execute the recovery strategy on drift detection.

    Steps:
    1. Halt new execution for session.
    2. Load latest checkpoint.
    3. Replay from checkpoint in verify mode.
    4. If mismatch persists, mark session invalid.
    5. If clean, mark session recovered.

    Args:
        log: The event log.
        checkpoint_store: Checkpoint persistence.
        re_executor: Primitive re-execution callable.
        session_id: The affected session.

    Returns:
        RecoveryResult describing the outcome.
    """
    _log(f"recovery: starting for session={session_id}")

    # Step 1: Load checkpoint
    checkpoint = checkpoint_store.load_latest(session_id=session_id)

    if checkpoint is None:
        _log(f"recovery: no checkpoint for session={session_id}, full verify")
        from_seq = 0
        initial_state: dict[str, Any] = {}
    else:
        _log(
            f"recovery: using checkpoint at seq={checkpoint.sequence_number} "
            f"for session={session_id}"
        )
        from_seq = checkpoint.sequence_number + 1
        initial_state = dict(checkpoint.state_snapshot)

    # Step 2: Verify replay from checkpoint
    verify_result = replay_verify(
        log,
        re_executor,
        from_seq=from_seq,
        initial_state=initial_state,
        halt_on_drift=False,  # scan all entries to get full drift picture
    )

    if verify_result.valid:
        _log(f"recovery: session={session_id} is CLEAN after verify replay")
        return RecoveryResult(
            session_id=session_id,
            validity=SessionValidity.RECOVERED,
            checkpoint_used=checkpoint,
            verify_replay=verify_result,
            halted=False,
            detail="Verify replay from checkpoint found no drift",
        )

    # Mismatch persists — session is invalid
    _log(
        f"recovery: session={session_id} INVALID — "
        f"{verify_result.mutation_mismatch_count} drifts persist"
    )
    return RecoveryResult(
        session_id=session_id,
        validity=SessionValidity.INVALID,
        checkpoint_used=checkpoint,
        verify_replay=verify_result,
        halted=True,
        detail=(
            f"Persistent drift: {verify_result.mutation_mismatch_count} mismatches "
            f"starting at event {verify_result.first_divergence_event_id}"
        ),
    )


# ─── Convenience: Take Checkpoint ──────────────────────────────────────────


def take_checkpoint(
    log: EventLog,
    checkpoint_store: CheckpointStore,
    state: dict[str, Any],
    *,
    in_flight: Optional[list[str]] = None,
    completed_keys: Optional[list[str]] = None,
    session_id: Optional[str] = None,
) -> Checkpoint:
    """Capture a checkpoint at the current log position.

    Args:
        log: The event log (reads last_sequence).
        checkpoint_store: Where to persist the checkpoint.
        state: Current state snapshot to preserve.
        in_flight: Execution IDs not yet completed.
        completed_keys: Idempotency keys already processed.
        session_id: Session scope for the checkpoint.

    Returns:
        The persisted Checkpoint.
    """
    import uuid

    cp = Checkpoint(
        checkpoint_id=uuid.uuid4().hex,
        sequence_number=log.last_sequence(),
        state_snapshot=dict(state),
        in_flight=list(in_flight or []),
        completed_keys=list(completed_keys or []),
        session_id=session_id,
    )
    checkpoint_store.save(cp)
    _log(
        f"checkpoint: id={cp.checkpoint_id[:8]} "
        f"seq={cp.sequence_number} session={session_id}"
    )
    return cp


# ─── Exports ────────────────────────────────────────────────────────────────

__all__ = [
    # Core models
    "MutationOp",
    "StateMutation",
    "compute_mutation_hash",
    "EventLogEntry",
    # Event log
    "EventLog",
    # Replay
    "ReplayMode",
    "DriftRecord",
    "ReplayResult",
    "apply_mutations",
    "PrimitiveReExecutor",
    "replay_fast",
    "replay_verify",
    # Checkpoint
    "Checkpoint",
    "CheckpointStore",
    "take_checkpoint",
    # Verification policy
    "VerificationTrigger",
    "VerificationPolicy",
    # Drift detection
    "DriftEvent",
    # Recovery
    "SessionValidity",
    "RecoveryResult",
    "recover_from_drift",
]
