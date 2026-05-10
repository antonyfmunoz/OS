"""
Runtime state rehydration from checkpoint + event replay.

Phase 2 of the event-sourced runtime: makes the durable event log and
checkpoint system the SOURCE OF TRUTH for runtime state.

Hydration protocol:
  1. Load the latest checkpoint (if any) into RuntimeStateStore.
  2. Determine replay start sequence (checkpoint seq + 1, or 0).
  3. Replay events from the event log, applying state_mutations.
  4. Optionally verify mutation_hash integrity per event.
  5. Compute a final state hash for the hydrated store.

Design rules:
- Purely additive — does not modify event log or checkpoints.
- Deterministic — same log + checkpoint = same state.
- Non-fatal drift detection — collects all drift, does not abort.
- Thread-safe inputs — all runtimes are already thread-safe.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from umh.substrate.checkpoint_runtime import CheckpointRuntime
from umh.substrate.event_log_runtime import (
    EventLogRuntime,
    compute_mutation_hash,
)
from umh.substrate.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.runtime_rehydration]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Result dataclass ──────────────────────────────────────────────────


@dataclass
class RuntimeRehydrationResult:
    """Outcome of a runtime state hydration from checkpoint + replay."""

    checkpoint_loaded: bool
    checkpoint_sequence: int | None
    events_replayed: int
    final_state_hash: str
    drift_detected: bool
    drift_details: list[dict[str, Any]] = field(default_factory=list)


# ─── Core hydration function ───────────────────────────────────────────


def hydrate_runtime_state(
    event_log_runtime: EventLogRuntime,
    checkpoint_runtime: CheckpointRuntime,
    runtime_state_store: RuntimeStateStore,
    session_name: str | None = None,
    verify: bool = True,
) -> RuntimeRehydrationResult:
    """Reconstruct runtime state from checkpoint + event replay.

    Steps:
      1. Load latest checkpoint and restore its snapshot into the store.
      2. Determine replay start: checkpoint.sequence_number + 1, or 0.
      3. Stream events from the log, filter by session_name if provided,
         and apply state_mutations into the store.
      4. If verify=True, recompute mutation_hash per event and compare
         against the stored hash. Drift events are collected (non-fatal).
      5. Compute a final state hash from the hydrated store.

    Args:
        event_log_runtime: The durable event log to replay from.
        checkpoint_runtime: The checkpoint store to load snapshots from.
        runtime_state_store: The in-memory store to hydrate.
        session_name: If provided, only replay events for this session.
        verify: If True, verify mutation_hash integrity during replay.

    Returns:
        RuntimeRehydrationResult with hydration outcome and drift info.
    """
    # ── Step 1: Load latest checkpoint ──────────────────────────────
    checkpoint = checkpoint_runtime.load_latest_checkpoint()
    checkpoint_loaded = checkpoint is not None
    checkpoint_sequence: int | None = None

    if checkpoint is not None:
        checkpoint_sequence = checkpoint.sequence_number
        runtime_state_store.load_snapshot(checkpoint.state_snapshot)
        _log(
            f"checkpoint loaded: seq={checkpoint_sequence} "
            f"hash={checkpoint.snapshot_hash[:16]}"
        )
    else:
        runtime_state_store.reset()
        _log("no checkpoint found — cold start from seq 0")

    # ── Step 2: Determine replay start sequence ─────────────────────
    replay_start: int = (
        (checkpoint_sequence + 1) if checkpoint_sequence is not None else 0
    )

    # ── Step 3 + 4: Replay events with optional verification ────────
    all_events = event_log_runtime.read_all()
    events_replayed = 0
    drift_details: list[dict[str, Any]] = []

    for event in all_events:
        # Skip events before the replay window
        if event.sequence_number < replay_start:
            continue

        # Filter by session if requested
        if session_name is not None and event.session_name != session_name:
            continue

        # Apply state mutations
        if event.state_mutations:
            runtime_state_store.apply_event_envelope(event)

        events_replayed += 1

        # Verify mutation_hash integrity
        if verify and event.state_mutations:
            expected_hash = compute_mutation_hash(event.state_mutations)
            if event.mutation_hash and event.mutation_hash != expected_hash:
                drift_entry = {
                    "sequence_number": event.sequence_number,
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "stored_hash": event.mutation_hash,
                    "computed_hash": expected_hash,
                }
                drift_details.append(drift_entry)
                _log(
                    f"DRIFT at seq={event.sequence_number}: "
                    f"stored={event.mutation_hash[:16]} "
                    f"computed={expected_hash[:16]}"
                )

    # ── Step 5: Compute final state hash ────────────────────────────
    final_state_hash = runtime_state_store.compute_state_hash()

    _log(
        f"hydration complete: checkpoint={'yes' if checkpoint_loaded else 'no'} "
        f"replayed={events_replayed} drift={len(drift_details)} "
        f"hash={final_state_hash}"
    )

    return RuntimeRehydrationResult(
        checkpoint_loaded=checkpoint_loaded,
        checkpoint_sequence=checkpoint_sequence,
        events_replayed=events_replayed,
        final_state_hash=final_state_hash,
        drift_detected=len(drift_details) > 0,
        drift_details=drift_details,
    )
