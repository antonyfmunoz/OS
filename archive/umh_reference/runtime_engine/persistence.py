"""
Persistence layer — lightweight cross-restart memory for EOS.

Persists:
    - StrategyMemory stats (EMA scores, wins, uses, global_turn)
    - DirectiveMemory stats
    - GoalTracker state
    - MetaWeightEngine signal performance (EMA, observations)
    - MemoryFabric entries (bounded, append-only log)
    - HierarchicalPlan state
    - Minimal session summaries (quality, confidence, flags — NOT full traces)

Uses the same SubstrateStorage backend as WorldModel (Neon KV with JSON
file fallback). No new tables, no new connections, no migrations.

Write policy: buffered with flush every ``FLUSH_INTERVAL`` updates to
keep the hot path fast. Explicit ``flush()`` on shutdown.

All payloads are versioned (``{"version": N, "data": ...}``) for forward
compatibility. Unknown versions are ignored, missing keys fall back cleanly.
"""

from __future__ import annotations

import atexit
import logging
import threading
from typing import Any

_log = logging.getLogger(__name__)

STORAGE_KEY_STRATEGY = "persistence:strategy_memory"
STORAGE_KEY_DIRECTIVE = "persistence:directive_memory"
STORAGE_KEY_TRACKERS = "persistence:goal_trackers"
STORAGE_KEY_SUMMARIES = "persistence:session_summaries"
STORAGE_KEY_PLANS = "persistence:hierarchical_plans"
STORAGE_KEY_META_WEIGHTS = "persistence:meta_weights"
STORAGE_KEY_MEMORY_FABRIC = "persistence:memory_fabric"
STORAGE_KEY_OBJECTIVE_HISTORY = "persistence:objective_history"
STORAGE_KEY_RUNTIME_STATE = "persistence:runtime_state"
STORAGE_KEY_WORLD_SUBSTRATE = "persistence:world_substrate"

MAX_SUMMARIES = 100
MAX_OBJECTIVE_HISTORY = 200
MAX_RECENT_ACTIONS = 50
FLUSH_INTERVAL = 5
PERSISTENCE_VERSION = 1


class _PersistenceBuffer:
    """Write buffer that batches storage writes to reduce IO pressure.

    The buffer is the single source of truth for in-flight data. Storage
    is only read to seed the summaries list on first access (cold start).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._strategy_dirty = False
        self._strategy_data: dict | None = None
        self._directive_dirty = False
        self._directive_data: dict | None = None
        self._trackers_dirty = False
        self._trackers_data: dict | None = None
        self._summaries_dirty = False
        self._summaries_data: list[dict] | None = None
        self._summaries_seeded = False
        self._plans_dirty = False
        self._plans_data: dict | None = None
        self._meta_weights_dirty = False
        self._meta_weights_data: dict | None = None
        self._memory_fabric_dirty = False
        self._memory_fabric_data: dict | None = None
        self._objective_history_dirty = False
        self._objective_history_data: dict | None = None
        self._runtime_state_dirty = False
        self._runtime_state_data: dict | None = None
        self._world_substrate_dirty = False
        self._world_substrate_data: dict | None = None
        self._update_count = 0

    def mark_strategy(self, data: dict) -> None:
        with self._lock:
            self._strategy_data = data
            self._strategy_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_directive(self, data: dict) -> None:
        with self._lock:
            self._directive_data = data
            self._directive_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_trackers(self, data: dict) -> None:
        with self._lock:
            self._trackers_data = data
            self._trackers_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_meta_weights(self, data: dict) -> None:
        with self._lock:
            self._meta_weights_data = data
            self._meta_weights_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_memory_fabric(self, data: dict) -> None:
        with self._lock:
            self._memory_fabric_data = data
            self._memory_fabric_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_objective_history(self, data: dict) -> None:
        with self._lock:
            self._objective_history_data = data
            self._objective_history_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_runtime_state(self, data: dict) -> None:
        with self._lock:
            self._runtime_state_data = data
            self._runtime_state_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_world_substrate(self, data: dict) -> None:
        with self._lock:
            self._world_substrate_data = data
            self._world_substrate_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def mark_plans(self, data: dict) -> None:
        with self._lock:
            self._plans_data = data
            self._plans_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def append_summary(self, summary: dict) -> None:
        """Append a summary to the in-memory list, seeding from storage on first call."""
        with self._lock:
            if not self._summaries_seeded:
                self._seed_summaries_locked()
            if self._summaries_data is None:
                self._summaries_data = []
            self._summaries_data.append(summary)
            if len(self._summaries_data) > MAX_SUMMARIES:
                self._summaries_data = self._summaries_data[-MAX_SUMMARIES:]
            self._summaries_dirty = True
            self._update_count += 1
            if self._update_count >= FLUSH_INTERVAL:
                self._flush_locked()

    def _seed_summaries_locked(self) -> None:
        """Load existing summaries from storage once. Caller holds the lock."""
        self._summaries_seeded = True
        storage = _get_storage_safe()
        if storage is None:
            return
        try:
            raw = storage.get(STORAGE_KEY_SUMMARIES)
            if isinstance(raw, list):
                self._summaries_data = raw
        except Exception:
            pass

    def get_summaries(self) -> list[dict]:
        """Return the current in-memory summaries list."""
        with self._lock:
            if not self._summaries_seeded:
                self._seed_summaries_locked()
            return list(self._summaries_data or [])

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        """Write all dirty buffers to storage. Caller holds the lock."""
        storage = _get_storage_safe()
        if storage is None:
            return

        if self._strategy_dirty and self._strategy_data is not None:
            try:
                storage.put(STORAGE_KEY_STRATEGY, self._strategy_data)
                self._strategy_dirty = False
            except Exception as e:
                _log.debug("Strategy flush failed: %s", e)

        if self._directive_dirty and self._directive_data is not None:
            try:
                storage.put(STORAGE_KEY_DIRECTIVE, self._directive_data)
                self._directive_dirty = False
            except Exception as e:
                _log.debug("Directive flush failed: %s", e)

        if self._trackers_dirty and self._trackers_data is not None:
            try:
                storage.put(STORAGE_KEY_TRACKERS, self._trackers_data)
                self._trackers_dirty = False
            except Exception as e:
                _log.debug("Trackers flush failed: %s", e)

        if self._summaries_dirty and self._summaries_data is not None:
            try:
                storage.put(STORAGE_KEY_SUMMARIES, self._summaries_data)
                self._summaries_dirty = False
            except Exception as e:
                _log.debug("Summaries flush failed: %s", e)

        if self._plans_dirty and self._plans_data is not None:
            try:
                storage.put(STORAGE_KEY_PLANS, self._plans_data)
                self._plans_dirty = False
            except Exception as e:
                _log.debug("Plans flush failed: %s", e)

        if self._meta_weights_dirty and self._meta_weights_data is not None:
            try:
                storage.put(STORAGE_KEY_META_WEIGHTS, self._meta_weights_data)
                self._meta_weights_dirty = False
            except Exception as e:
                _log.debug("Meta weights flush failed: %s", e)

        if self._memory_fabric_dirty and self._memory_fabric_data is not None:
            try:
                storage.put(STORAGE_KEY_MEMORY_FABRIC, self._memory_fabric_data)
                self._memory_fabric_dirty = False
            except Exception as e:
                _log.debug("Memory fabric flush failed: %s", e)

        if self._objective_history_dirty and self._objective_history_data is not None:
            try:
                storage.put(STORAGE_KEY_OBJECTIVE_HISTORY, self._objective_history_data)
                self._objective_history_dirty = False
            except Exception as e:
                _log.debug("Objective history flush failed: %s", e)

        if self._runtime_state_dirty and self._runtime_state_data is not None:
            try:
                storage.put(STORAGE_KEY_RUNTIME_STATE, self._runtime_state_data)
                self._runtime_state_dirty = False
            except Exception as e:
                _log.debug("Runtime state flush failed: %s", e)

        if self._world_substrate_dirty and self._world_substrate_data is not None:
            try:
                storage.put(STORAGE_KEY_WORLD_SUBSTRATE, self._world_substrate_data)
                self._world_substrate_dirty = False
            except Exception as e:
                _log.debug("World substrate flush failed: %s", e)

        self._update_count = 0


_buffer = _PersistenceBuffer()
atexit.register(_buffer.flush)


def _get_storage_safe() -> Any:
    """Get SubstrateStorage, returning None on failure."""
    try:
        from umh.substrate.storage import get_storage

        return get_storage()
    except Exception as e:
        _log.debug("Storage unavailable: %s", e)
        return None


# ─── Strategy Memory ─────────────────────────────────────────────────────────


def save_strategy_memory(
    strategy_stats: dict[str, dict],
    global_turn: int = 0,
) -> None:
    """Buffer strategy memory for persistence.

    ``strategy_stats`` is the dict from ``StrategyMemory.to_dict()``.
    """
    payload = {
        "strategies": strategy_stats,
        "global_turn": global_turn,
    }
    _buffer.mark_strategy(payload)


def load_strategy_memory() -> dict | None:
    """Load persisted strategy memory, or None if unavailable.

    Returns ``{"strategies": {...}, "global_turn": int}`` or None.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_STRATEGY)
        if data is None:
            return None
        if not isinstance(data, dict) or "strategies" not in data:
            _log.debug("Invalid strategy memory format, ignoring")
            return None
        return data
    except Exception as e:
        _log.debug("Strategy memory load failed: %s", e)
        return None


# ─── Directive Memory ────────────────────────────────────────────────────────


def save_directive_memory(
    directive_stats: dict[str, dict],
    global_turn: int = 0,
) -> None:
    """Buffer directive memory for persistence.

    ``directive_stats`` is the dict from ``DirectiveMemory.to_dict()``.
    """
    payload = {
        "directives": directive_stats,
        "global_turn": global_turn,
    }
    _buffer.mark_directive(payload)


def load_directive_memory() -> dict | None:
    """Load persisted directive memory, or None if unavailable.

    Returns ``{"directives": {...}, "global_turn": int}`` or None.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_DIRECTIVE)
        if data is None:
            return None
        if not isinstance(data, dict) or "directives" not in data:
            _log.debug("Invalid directive memory format, ignoring")
            return None
        return data
    except Exception as e:
        _log.debug("Directive memory load failed: %s", e)
        return None


# ─── Goal Trackers ───────────────────────────────────────────────────────────


def save_goal_trackers(
    tracker_data: dict[str, dict],
    registry_turn: int = 0,
) -> None:
    """Buffer goal tracker state for persistence.

    ``tracker_data`` maps goal_id → GoalTracker.to_dict().
    Only tracker runtime signals are persisted — GoalState objects
    are reconstructed by the caller each session.
    """
    payload = {
        "trackers": tracker_data,
        "registry_turn": registry_turn,
    }
    _buffer.mark_trackers(payload)


def load_goal_trackers() -> dict | None:
    """Load persisted goal tracker state, or None if unavailable.

    Returns ``{"trackers": {...}, "registry_turn": int}`` or None.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_TRACKERS)
        if data is None:
            return None
        if not isinstance(data, dict) or "trackers" not in data:
            _log.debug("Invalid tracker data format, ignoring")
            return None
        return data
    except Exception as e:
        _log.debug("Goal tracker load failed: %s", e)
        return None


# ─── Session Summaries ───────────────────────────────────────────────────────


def append_session_summary(summary: dict) -> None:
    """Append a turn summary and buffer for persistence.

    Maintains a bounded list of the last ``MAX_SUMMARIES`` entries.
    The buffer is the source of truth — storage is only read to seed
    on first access.
    """
    _buffer.append_summary(summary)


def load_recent_summaries(limit: int = 50) -> list[dict]:
    """Load the most recent session summaries.

    Returns up to ``limit`` entries, most recent last. Reads from the
    buffer's in-memory list (which seeds from storage on first access).
    """
    all_summaries = _buffer.get_summaries()
    return all_summaries[-limit:]


# ─── Hierarchical Plans ─────────────────────────────────────────────────────


def save_plans(plan_snapshot: dict) -> None:
    """Buffer hierarchical plan state for persistence.

    ``plan_snapshot`` is the dict from ``PlanEngine.snapshot()``.
    Only active plans are stored — callers should filter before saving.
    """
    _buffer.mark_plans(plan_snapshot)


def load_plans() -> dict | None:
    """Load persisted plan state, or None if unavailable.

    Returns the dict previously passed to ``save_plans()`` or None.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_PLANS)
        if data is None:
            return None
        if not isinstance(data, dict) or "plans" not in data:
            _log.debug("Invalid plan data format, ignoring")
            return None
        return data
    except Exception as e:
        _log.debug("Plan load failed: %s", e)
        return None


# ─── Meta Weights ───────────────────────────────────────────────────────────


def save_meta_weights(snapshot: dict) -> None:
    """Buffer meta weight engine state for persistence.

    ``snapshot`` is the dict from ``MetaWeightEngine.snapshot()``.
    Wrapped with version for forward compatibility.
    """
    payload = {
        "version": PERSISTENCE_VERSION,
        "data": snapshot,
    }
    _buffer.mark_meta_weights(payload)


def load_meta_weights() -> dict | None:
    """Load persisted meta weight state, or None if unavailable.

    Returns the inner ``data`` dict (MetaWeightEngine.snapshot() format)
    or None. Validates version and structure.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_META_WEIGHTS)
        if data is None:
            return None
        if not isinstance(data, dict):
            _log.debug("Invalid meta weights format, ignoring")
            return None
        version = data.get("version", 0)
        if version > PERSISTENCE_VERSION:
            _log.debug(
                "Meta weights version %d > %d, ignoring", version, PERSISTENCE_VERSION
            )
            return None
        inner = data.get("data")
        if not isinstance(inner, dict):
            _log.debug("Invalid meta weights data payload, ignoring")
            return None
        return inner
    except Exception as e:
        _log.debug("Meta weights load failed: %s", e)
        return None


# ─── Memory Fabric ──────────────────────────────────────────────────────────


def save_memory_fabric(snapshot: dict) -> None:
    """Buffer memory fabric state for persistence.

    ``snapshot`` is the dict from ``MemoryFabric.snapshot()``.
    Wrapped with version for forward compatibility.
    """
    payload = {
        "version": PERSISTENCE_VERSION,
        "data": snapshot,
    }
    _buffer.mark_memory_fabric(payload)


def load_memory_fabric() -> dict | None:
    """Load persisted memory fabric state, or None if unavailable.

    Returns the inner ``data`` dict (MemoryFabric.snapshot() format)
    or None. Validates version and structure.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_MEMORY_FABRIC)
        if data is None:
            return None
        if not isinstance(data, dict):
            _log.debug("Invalid memory fabric format, ignoring")
            return None
        version = data.get("version", 0)
        if version > PERSISTENCE_VERSION:
            _log.debug(
                "Memory fabric version %d > %d, ignoring", version, PERSISTENCE_VERSION
            )
            return None
        inner = data.get("data")
        if not isinstance(inner, dict):
            _log.debug("Invalid memory fabric data payload, ignoring")
            return None
        return inner
    except Exception as e:
        _log.debug("Memory fabric load failed: %s", e)
        return None


# ─── Objective History ─────────────────────────────────────────────────────


def save_objective_history(values: list[float]) -> None:
    """Buffer objective history for persistence.

    ``values`` is a bounded list of recent objective_value floats.
    Capped to MAX_OBJECTIVE_HISTORY before wrapping.
    """
    capped = (
        values[-MAX_OBJECTIVE_HISTORY:]
        if len(values) > MAX_OBJECTIVE_HISTORY
        else list(values)
    )
    payload = {
        "version": PERSISTENCE_VERSION,
        "data": {
            "objective_values": capped,
        },
    }
    _buffer.mark_objective_history(payload)


def load_objective_history() -> list[float] | None:
    """Load persisted objective history, or None if unavailable.

    Returns a list of objective_value floats (oldest first), or None.
    Validates version and structure.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_OBJECTIVE_HISTORY)
        if data is None:
            return None
        if not isinstance(data, dict):
            _log.debug("Invalid objective history format, ignoring")
            return None
        version = data.get("version", 0)
        if version > PERSISTENCE_VERSION:
            _log.debug(
                "Objective history version %d > %d, ignoring",
                version,
                PERSISTENCE_VERSION,
            )
            return None
        inner = data.get("data")
        if not isinstance(inner, dict):
            _log.debug("Invalid objective history data payload, ignoring")
            return None
        values = inner.get("objective_values")
        if not isinstance(values, list):
            _log.debug("Invalid objective_values in payload, ignoring")
            return None
        return [float(v) for v in values[-MAX_OBJECTIVE_HISTORY:]]
    except Exception as e:
        _log.debug("Objective history load failed: %s", e)
        return None


# ─── Runtime State ─────────────────────────────────────────────────────────


def save_runtime_state(state: dict) -> None:
    """Buffer runtime behavioral state for persistence.

    Persists derived state needed for restart continuity:
    reward_ema, reward_peak, failure_streak, recent_actions, trap_detector.
    """
    recent = state.get("recent_actions", [])
    if len(recent) > MAX_RECENT_ACTIONS:
        state = dict(state)
        state["recent_actions"] = recent[-MAX_RECENT_ACTIONS:]

    payload = {
        "version": PERSISTENCE_VERSION,
        "data": state,
    }
    _buffer.mark_runtime_state(payload)


def load_runtime_state() -> dict | None:
    """Load persisted runtime behavioral state, or None if unavailable."""
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_RUNTIME_STATE)
        if data is None:
            return None
        if not isinstance(data, dict):
            _log.debug("Invalid runtime state format, ignoring")
            return None
        version = data.get("version", 0)
        if version > PERSISTENCE_VERSION:
            _log.debug(
                "Runtime state version %d > %d, ignoring",
                version,
                PERSISTENCE_VERSION,
            )
            return None
        inner = data.get("data")
        if not isinstance(inner, dict):
            _log.debug("Invalid runtime state data payload, ignoring")
            return None
        return inner
    except Exception as e:
        _log.debug("Runtime state load failed: %s", e)
        return None


# ─── World Substrate ───────────────────────────────────────────────────────


def save_world_substrate(snapshot: dict) -> None:
    """Buffer world substrate state for persistence.

    ``snapshot`` is the dict from ``WorldSubstrate.snapshot()``.
    Already versioned by the engine, passed through as-is.
    """
    _buffer.mark_world_substrate(snapshot)


def load_world_substrate() -> dict | None:
    """Load persisted world substrate state, or None if unavailable.

    Returns the full versioned payload for ``WorldSubstrate.restore()``.
    """
    storage = _get_storage_safe()
    if storage is None:
        return None
    try:
        data = storage.get(STORAGE_KEY_WORLD_SUBSTRATE)
        if data is None:
            return None
        if not isinstance(data, dict):
            _log.debug("Invalid world substrate format, ignoring")
            return None
        return data
    except Exception as e:
        _log.debug("World substrate load failed: %s", e)
        return None


# ─── Persistence Status ─────────────────────────────────────────────────────


def get_persistence_status() -> dict:
    """Return observability snapshot of persistence state.

    Used by DecisionTrace to report persistence health.
    """
    components: list[str] = []
    errors: list[str] = []

    for name, key in [
        ("strategy_memory", STORAGE_KEY_STRATEGY),
        ("directive_memory", STORAGE_KEY_DIRECTIVE),
        ("goal_trackers", STORAGE_KEY_TRACKERS),
        ("meta_weights", STORAGE_KEY_META_WEIGHTS),
        ("memory_fabric", STORAGE_KEY_MEMORY_FABRIC),
        ("objective_history", STORAGE_KEY_OBJECTIVE_HISTORY),
        ("runtime_state", STORAGE_KEY_RUNTIME_STATE),
        ("plans", STORAGE_KEY_PLANS),
        ("world_substrate", STORAGE_KEY_WORLD_SUBSTRATE),
    ]:
        storage = _get_storage_safe()
        if storage is None:
            break
        try:
            data = storage.get(key)
            if data is not None:
                components.append(name)
        except Exception as e:
            errors.append(f"{name}: {e}")

    return {
        "version": PERSISTENCE_VERSION,
        "persisted_components": components,
        "errors": errors[0] if errors else None,
    }


# ─── Flush & Test Hooks ────────────────────────────────────────────────────


def flush() -> None:
    """Force-flush all pending writes to storage."""
    _buffer.flush()


def _reset_buffer_for_tests() -> None:
    """Test hook — reset the buffer state."""
    global _buffer
    _buffer = _PersistenceBuffer()
    atexit.register(_buffer.flush)
