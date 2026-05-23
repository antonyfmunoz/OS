"""
Operator state — bounded unified state model for the workstation operator.

Purpose
-------
Until now the substrate had four parallel signals living in four stores:

  - wake events    (WakeProducerHistory)
  - voice sessions (VoiceSessionStore)
  - rituals        (RitualRegistry)
  - readiness      (StationReadiness, derived per call)

Each is correct on its own, but there was no single answer to:

  "What state is this operator in right now, and why?"

This module provides that answer. It is intentionally small:

  - one bounded dataclass (OperatorState) per node
  - one dual-layer store (in-mem + substrate.storage), mirroring
    VoiceSessionStore exactly
  - a tiny per-node ring buffer of recent transitions for explainability
  - no orchestration, no rules engine, no autonomous behavior

The transition logic and wiring live in operator_transitions.py. This file
only owns the *shape* and *persistence* of the state.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path (gateway/cognitive_loop/model_router/agent_runtime/
  primitives) is never imported.
- Bounded. Closed enum of states. Bounded transition history per node.
- Best-effort. All public methods catch and log; never raise into callers.
- Deterministic. Storage layout is a single keyed JSON blob.
- Reversible. Removing this file (and the additive call sites) leaves the
  substrate exactly as it was.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "operator_state"
_MAX_NODES = 100  # bounded retention; oldest-by-updated_at dropped on overflow
_MAX_TRANSITIONS_PER_NODE = 25  # ring buffer per node


def _log(msg: str) -> None:
    print(f"[substrate.operator_state] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "os") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Models ───────────────────────────────────────────────────────────────────


class OperatorMode(str, Enum):
    """Bounded operator modes.

    IDLE         — node is registered but no active session/ritual
    STARTING     — wake/clap received, transitioning into ACTIVE
    ACTIVE       — voice session active, operator present
    FOCUSED      — operator in a scoped scene (e.g. operator_mode) with a ritual
    CLOSING      — close_day in progress
    UNAVAILABLE  — readiness reports the node as unreachable
    """

    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    FOCUSED = "focused"
    CLOSING = "closing"
    UNAVAILABLE = "unavailable"


@dataclass
class OperatorTransition:
    """A single bounded transition record. Audit-only, no behavior."""

    transition_id: str
    node_id: str
    from_mode: Optional[str]
    to_mode: str
    trigger: str  # short tag: "wake_word", "clap", "voice_started", "ritual_open", ...
    reason: str
    occurred_at: str
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OperatorTransition":
        return cls(
            transition_id=str(d.get("transition_id") or _new_id("ot")),
            node_id=str(d.get("node_id", "")),
            from_mode=d.get("from_mode"),
            to_mode=str(d.get("to_mode", OperatorMode.IDLE.value)),
            trigger=str(d.get("trigger", "")),
            reason=str(d.get("reason", "")),
            occurred_at=str(d.get("occurred_at") or _utcnow()),
            metadata=dict(d.get("metadata") or {}),
        )


@dataclass
class OperatorState:
    """Unified bounded operator state for a single node.

    All fields except `node_id` are optional: the state is monotonically
    enriched as wake/voice/ritual/readiness signals flow in.
    """

    node_id: str
    mode: OperatorMode = OperatorMode.IDLE

    # Voice presence
    active_voice_session_id: Optional[str] = None
    active_voice_role: Optional[str] = None
    last_voice_turn_at: Optional[str] = None

    # Wake events
    last_wake_event_id: Optional[str] = None
    last_wake_kind: Optional[str] = None  # "wake_word" | "clap"
    last_wake_action: Optional[str] = None  # "start_voice_session" | ...
    last_wake_at: Optional[str] = None

    # Ritual lifecycle
    current_ritual_id: Optional[str] = None
    current_ritual_kind: Optional[str] = None  # "open_day" | "close_day"
    current_ritual_state: Optional[str] = None  # "pending" → "completed"

    # Scene / readiness
    current_scene: Optional[str] = None
    scene_decision_reason: Optional[str] = None
    readiness_classification: Optional[str] = None  # READY|DEGRADED|UNAVAILABLE
    readiness_age_s: Optional[float] = None

    # Lifecycle
    updated_at: str = field(default_factory=_utcnow)
    snapshot_id: str = field(default_factory=lambda: _new_id("os"))
    transitions: list[OperatorTransition] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # — derived helpers —————————————————————————————————————————————

    @property
    def is_active(self) -> bool:
        return self.mode in (
            OperatorMode.ACTIVE,
            OperatorMode.FOCUSED,
            OperatorMode.STARTING,
        )

    @property
    def last_transition(self) -> Optional[OperatorTransition]:
        return self.transitions[-1] if self.transitions else None

    # — mutation —————————————————————————————————————————————————

    def append_transition(self, transition: OperatorTransition) -> None:
        self.transitions.append(transition)
        if len(self.transitions) > _MAX_TRANSITIONS_PER_NODE:
            drop = len(self.transitions) - _MAX_TRANSITIONS_PER_NODE
            self.transitions = self.transitions[drop:]
        self.updated_at = transition.occurred_at

    # — serialization —————————————————————————————————————————————

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "mode": self.mode.value,
            "active_voice_session_id": self.active_voice_session_id,
            "active_voice_role": self.active_voice_role,
            "last_voice_turn_at": self.last_voice_turn_at,
            "last_wake_event_id": self.last_wake_event_id,
            "last_wake_kind": self.last_wake_kind,
            "last_wake_action": self.last_wake_action,
            "last_wake_at": self.last_wake_at,
            "current_ritual_id": self.current_ritual_id,
            "current_ritual_kind": self.current_ritual_kind,
            "current_ritual_state": self.current_ritual_state,
            "current_scene": self.current_scene,
            "scene_decision_reason": self.scene_decision_reason,
            "readiness_classification": self.readiness_classification,
            "readiness_age_s": self.readiness_age_s,
            "updated_at": self.updated_at,
            "snapshot_id": self.snapshot_id,
            "transitions": [t.as_dict() for t in self.transitions],
            "metadata": dict(self.metadata),
            # convenience denormals for operator reports
            "is_active": self.is_active,
            "last_transition": (
                self.last_transition.as_dict() if self.last_transition else None
            ),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OperatorState":
        try:
            mode = OperatorMode(d.get("mode", "idle"))
        except Exception:
            mode = OperatorMode.IDLE
        transitions_raw = d.get("transitions") or []
        transitions: list[OperatorTransition] = []
        if isinstance(transitions_raw, list):
            for t in transitions_raw:
                if isinstance(t, dict):
                    try:
                        transitions.append(OperatorTransition.from_dict(t))
                    except Exception:
                        continue
        return cls(
            node_id=str(d.get("node_id", "")),
            mode=mode,
            active_voice_session_id=d.get("active_voice_session_id"),
            active_voice_role=d.get("active_voice_role"),
            last_voice_turn_at=d.get("last_voice_turn_at"),
            last_wake_event_id=d.get("last_wake_event_id"),
            last_wake_kind=d.get("last_wake_kind"),
            last_wake_action=d.get("last_wake_action"),
            last_wake_at=d.get("last_wake_at"),
            current_ritual_id=d.get("current_ritual_id"),
            current_ritual_kind=d.get("current_ritual_kind"),
            current_ritual_state=d.get("current_ritual_state"),
            current_scene=d.get("current_scene"),
            scene_decision_reason=d.get("scene_decision_reason"),
            readiness_classification=d.get("readiness_classification"),
            readiness_age_s=d.get("readiness_age_s"),
            updated_at=str(d.get("updated_at") or _utcnow()),
            snapshot_id=str(d.get("snapshot_id") or _new_id("os")),
            transitions=transitions,
            metadata=dict(d.get("metadata") or {}),
        )


# ─── Store ────────────────────────────────────────────────────────────────────


class OperatorStateStore:
    """Durable, bounded, thread-safe index of OperatorStates by node_id.

    Mirrors VoiceSessionStore: dual-layer (in-mem + substrate storage), singleton
    via `get_operator_state_store()`. Best-effort persistence — flush failures
    log and the in-memory state remains correct.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._by_node: dict[str, OperatorState] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence —————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from substrate.execution.transport.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default={}) or {}
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = {}
            rows = raw.get("rows") if isinstance(raw, dict) and "rows" in raw else raw
            if isinstance(rows, dict):
                for node_id, row in rows.items():
                    if not isinstance(row, dict):
                        continue
                    try:
                        self._by_node[str(node_id)] = OperatorState.from_dict(row)
                    except Exception:
                        continue
            self._loaded = True

    def _flush(self) -> None:
        try:
            from substrate.execution.transport.storage import get_storage

            payload = {
                "rows": {nid: s.as_dict() for nid, s in self._by_node.items()},
                "updated_at": _utcnow(),
            }
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _enforce_retention(self) -> None:
        if len(self._by_node) <= _MAX_NODES:
            return
        ordered = sorted(
            self._by_node.items(),
            key=lambda kv: kv[1].updated_at or "",
        )
        drop = len(self._by_node) - _MAX_NODES
        for nid, _ in ordered[:drop]:
            self._by_node.pop(nid, None)

    # — public api —————————————————————————————————————————————

    def get_or_create(self, node_id: str) -> OperatorState:
        with self._lock:
            state = self._by_node.get(node_id)
            if state is None:
                state = OperatorState(node_id=node_id)
                self._by_node[node_id] = state
            return state

    def get(self, node_id: str) -> Optional[OperatorState]:
        with self._lock:
            return self._by_node.get(node_id)

    def put(self, state: OperatorState) -> None:
        with self._lock:
            state.updated_at = _utcnow()
            self._by_node[state.node_id] = state
            self._enforce_retention()
            self._flush()

    def all(self) -> list[OperatorState]:
        with self._lock:
            return list(self._by_node.values())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._by_node)
            by_mode: dict[str, int] = {}
            for s in self._by_node.values():
                k = s.mode.value
                by_mode[k] = by_mode.get(k, 0) + 1
            return {
                "total": total,
                "by_mode": by_mode,
                "cap": _MAX_NODES,
                "max_transitions_per_node": _MAX_TRANSITIONS_PER_NODE,
            }

    def clear(self) -> None:
        """Test helper. Drops in-memory rows AND the durable payload."""
        with self._lock:
            self._by_node.clear()
            self._flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_node)


_store_singleton: Optional[OperatorStateStore] = None
_store_singleton_lock = threading.Lock()


def get_operator_state_store() -> OperatorStateStore:
    global _store_singleton
    if _store_singleton is None:
        with _store_singleton_lock:
            if _store_singleton is None:
                _store_singleton = OperatorStateStore()
    return _store_singleton


def reset_operator_state_store_for_tests() -> None:
    global _store_singleton
    with _store_singleton_lock:
        _store_singleton = None


__all__ = [
    "OperatorMode",
    "OperatorTransition",
    "OperatorState",
    "OperatorStateStore",
    "get_operator_state_store",
    "reset_operator_state_store_for_tests",
]
