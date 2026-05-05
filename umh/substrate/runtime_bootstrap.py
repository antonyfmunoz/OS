"""
Singleton access for the event-sourced runtime infrastructure.

Process-local singletons for Phase 1. Each getter lazily initializes
and returns the same instance for the lifetime of the process.

Usage:
    from umh.substrate.runtime_bootstrap import (
        get_event_log_runtime,
        get_checkpoint_runtime,
        get_runtime_state_store,
    )

    log = get_event_log_runtime()
    cp = get_checkpoint_runtime()
    store = get_runtime_state_store()

Integration:
    These are called from run_lifecycle.py at lifecycle boundary events
    (finalization, publication, clear, seal). They are best-effort and
    never block the lifecycle — callers wrap in try/except.
"""

from __future__ import annotations

import threading
from pathlib import Path

from umh.substrate.checkpoint_runtime import CheckpointRuntime
from umh.substrate.event_log_runtime import EventLogRuntime
from umh.substrate.runtime_rehydration import (
    RuntimeRehydrationResult,
    hydrate_runtime_state,
)
from umh.substrate.runtime_state_store import RuntimeStateStore

_lock = threading.Lock()

_event_log: EventLogRuntime | None = None
_checkpoint: CheckpointRuntime | None = None
_state_store: RuntimeStateStore | None = None

# Default paths — overridable for testing via _reset_for_testing()
_log_path: Path | None = None
_checkpoint_dir: Path | None = None


def get_event_log_runtime() -> EventLogRuntime:
    """Return the process-local EventLogRuntime singleton."""
    global _event_log
    if _event_log is None:
        with _lock:
            if _event_log is None:
                _event_log = EventLogRuntime(log_path=_log_path)
    return _event_log


def get_checkpoint_runtime() -> CheckpointRuntime:
    """Return the process-local CheckpointRuntime singleton."""
    global _checkpoint
    if _checkpoint is None:
        with _lock:
            if _checkpoint is None:
                _checkpoint = CheckpointRuntime(checkpoint_dir=_checkpoint_dir)
    return _checkpoint


def get_runtime_state_store() -> RuntimeStateStore:
    """Return the process-local RuntimeStateStore singleton."""
    global _state_store
    if _state_store is None:
        with _lock:
            if _state_store is None:
                _state_store = RuntimeStateStore()
    return _state_store


def initialize_runtime_state(
    session_name: str | None = None,
    verify: bool = True,
) -> tuple[RuntimeStateStore, RuntimeRehydrationResult]:
    """Single entrypoint for hydrated runtime state.

    Instantiates (or reuses) the process-local singletons, then runs
    hydrate_runtime_state() to reconstruct state from the latest
    checkpoint + subsequent event replay.

    Args:
        session_name: If provided, only replay events for this session.
        verify: If True, verify mutation_hash integrity during replay.

    Returns:
        Tuple of (hydrated RuntimeStateStore, RuntimeRehydrationResult).
    """
    store = get_runtime_state_store()
    result = hydrate_runtime_state(
        event_log_runtime=get_event_log_runtime(),
        checkpoint_runtime=get_checkpoint_runtime(),
        runtime_state_store=store,
        session_name=session_name,
        verify=verify,
    )
    return store, result


def _reset_for_testing(
    log_path: Path | None = None,
    checkpoint_dir: Path | None = None,
) -> None:
    """Reset all singletons. FOR TESTING ONLY.

    Optionally override paths to use temp directories.
    """
    global _event_log, _checkpoint, _state_store, _log_path, _checkpoint_dir
    with _lock:
        _event_log = None
        _checkpoint = None
        _state_store = None
        _log_path = log_path
        _checkpoint_dir = checkpoint_dir
