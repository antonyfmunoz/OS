"""
In-memory runtime state store with deterministic mutation application.

This module mirrors the canonical runtime state that would be rebuilt
from event replay. For Phase 1, it is a simple dict-backed store.
Future phases will hydrate it from the event log at startup.

Supported mutation operations:
- SET:            state[key] = value
- INCREMENT:      state[key] += value (default 1)
- APPEND_UNIQUE:  append value to list at key if not already present
- REMOVE:         delete key from state

Invariants:
- apply_mutations() is deterministic: same mutations in same order
  produce the same state, regardless of when they are applied.
- Unknown operations raise ValueError (fail loud, not silent).
- snapshot() returns a deep copy — mutations to the copy do not
  affect the store.
- load_snapshot() replaces the entire store atomically.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import threading
from typing import Any

_LOG_PREFIX = "[substrate.runtime_state_store]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Mutation operations ─────────────────────────────────────────────────

_VALID_OPS = frozenset({"SET", "INCREMENT", "APPEND_UNIQUE", "REMOVE"})


class WriteEnforcementViolation(RuntimeError):
    """Raised when a write is attempted outside the scheduler in enforced mode."""


class RuntimeStateStore:
    """In-memory key-value state store with deterministic mutation support.

    Thread-safe via threading.Lock. All public methods acquire the lock.

    Write enforcement:
        When _enforce_scheduler is True, only calls from within a
        scheduler_write_context() block may apply mutations or set values.
        All other writes raise WriteEnforcementViolation. This ensures
        the scheduler is the sole authority for state mutations in
        EVENT_PRIMARY mode.
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._enforce_scheduler: bool = False
        self._scheduler_writing: bool = False

    def enable_write_enforcement(self) -> None:
        """Enable write enforcement. Only scheduler_write_context() may write."""
        with self._lock:
            self._enforce_scheduler = True
            _log("write enforcement ENABLED — only scheduler may mutate state")

    def disable_write_enforcement(self) -> None:
        """Disable write enforcement. Any caller may write."""
        with self._lock:
            self._enforce_scheduler = False
            _log("write enforcement DISABLED")

    def scheduler_write_context(self) -> "_SchedulerWriteContext":
        """Context manager granting write access to the scheduler.

        Usage:
            with store.scheduler_write_context():
                store.apply_mutations(mutations)
        """
        return _SchedulerWriteContext(self)

    def _check_write_allowed(self, operation: str = "write") -> None:
        """Raise if write enforcement is active and caller is not the scheduler."""
        if self._enforce_scheduler and not self._scheduler_writing:
            raise WriteEnforcementViolation(
                f"State {operation} rejected: write enforcement is active. "
                f"Only scheduler may mutate state in EVENT_PRIMARY mode."
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the store. Reads are always allowed."""
        with self._lock:
            return copy.deepcopy(self._state.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Set a value in the store."""
        with self._lock:
            self._check_write_allowed("SET")
            self._state[key] = value

    def apply_mutations(self, state_mutations: list[dict]) -> None:
        """Apply a list of mutations deterministically.

        Each mutation is a dict with at minimum:
            {"op": "SET|INCREMENT|APPEND_UNIQUE|REMOVE", "key": "...", "value": ...}

        value is optional for REMOVE.
        value defaults to 1 for INCREMENT.

        Raises ValueError on unknown op — fail loud.
        """
        with self._lock:
            self._check_write_allowed("apply_mutations")
            for mutation in state_mutations:
                op = mutation.get("op", "")
                key = mutation.get("key", "")
                value = mutation.get("value")

                if op not in _VALID_OPS:
                    raise ValueError(
                        f"Unknown mutation op: {op!r}. Valid ops: {sorted(_VALID_OPS)}"
                    )

                if op == "SET":
                    self._state[key] = value

                elif op == "INCREMENT":
                    increment_by = value if value is not None else 1
                    current = self._state.get(key, 0)
                    self._state[key] = current + increment_by

                elif op == "APPEND_UNIQUE":
                    current = self._state.get(key, [])
                    if not isinstance(current, list):
                        current = [current]
                    if value not in current:
                        current.append(value)
                    self._state[key] = current

                elif op == "REMOVE":
                    self._state.pop(key, None)

    def snapshot(self) -> dict[str, Any]:
        """Return a deep copy of the entire state."""
        with self._lock:
            return copy.deepcopy(self._state)

    def load_snapshot(self, snapshot_dict: dict[str, Any]) -> None:
        """Replace the entire state atomically from a snapshot."""
        with self._lock:
            self._check_write_allowed("load_snapshot")
            self._state = copy.deepcopy(snapshot_dict)

    def reset(self) -> None:
        """Clear all state. Also resets enforcement."""
        with self._lock:
            self._state.clear()
            self._enforce_scheduler = False
            self._scheduler_writing = False

    def keys(self) -> list[str]:
        """Return all keys in the store."""
        with self._lock:
            return list(self._state.keys())

    def apply_event_envelope(self, event_envelope: Any) -> None:
        """Extract state_mutations from an EventEnvelope and apply them.

        Accepts any object with a ``state_mutations`` attribute that is a
        list[dict].  No-ops when the list is empty.
        """
        mutations: list[dict] = getattr(event_envelope, "state_mutations", [])
        if mutations:
            self.apply_mutations(mutations)

    def compute_state_hash(self) -> str:
        """SHA-256 prefix of the canonical JSON representation of the store.

        Returns the first 16 hex characters (64 bits) of the hash.
        Deterministic: identical state always produces the same hash.
        """
        with self._lock:
            canonical = json.dumps(
                self._state, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @property
    def write_enforcement_active(self) -> bool:
        """Whether write enforcement is currently active."""
        with self._lock:
            return self._enforce_scheduler


class _SchedulerWriteContext:
    """Context manager that temporarily grants scheduler write access.

    Used by the EventScheduler to apply mutations while enforcement is active.
    NOT reentrant — nested usage is safe but meaningless.
    """

    def __init__(self, store: RuntimeStateStore) -> None:
        self._store = store

    def __enter__(self) -> RuntimeStateStore:
        with self._store._lock:
            self._store._scheduler_writing = True
        return self._store

    def __exit__(self, *exc: Any) -> None:
        with self._store._lock:
            self._store._scheduler_writing = False
