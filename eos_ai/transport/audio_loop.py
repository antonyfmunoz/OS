"""
Audio loop — bounded local interaction-window model.

Purpose
-------
Until now the substrate tracked voice sessions (VoiceSession), wake events
(WakeProducerEvent), and operator state (OperatorState) — but there was no
single answer to:

    "Is the local node currently in an audio interaction window, and
     where are we in the listen → respond → cool_down arc?"

This module owns that tiny answer. It is intentionally small:

  - one bounded Enum (AudioLoopStatus)
  - one bounded dataclass per node (AudioLoopState) with an embedded
    transcript ring buffer
  - one dual-layer store (in-mem + substrate.storage), mirroring
    OperatorStateStore exactly
  - a handful of best-effort helper functions that other substrate
    modules call to push raw signals into the loop

It is NOT:
  - a real-time loop manager
  - a mic-capture pipeline
  - an STT driver
  - a command parser

All state changes are explicit via helper calls. Nothing auto-transitions
in the background. Removing this file (and the additive call sites) leaves
the substrate exactly as it was.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Hot path (gateway/cognitive_loop/model_router/agent_runtime/primitives)
  is never imported.
- Bounded. Closed enum of statuses. Bounded transcript ring buffer.
- Best-effort. All public helpers catch and log; never raise.
- Deterministic. Storage layout is a single keyed JSON blob.
- Reversible. Every write is additive.
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

_STORAGE_KEY = "audio_loop_state"
_MAX_NODES = 100
_MAX_TRANSCRIPTS_PER_NODE = 10  # small ring buffer, per-state (no separate store)
_DEFAULT_SPOKEN_COOLDOWN_S = 8.0  # dedupe window for same (from, to) presence line


def _log(msg: str) -> None:
    print(f"[substrate.audio_loop] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _new_id(prefix: str = "al") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ─── Models ───────────────────────────────────────────────────────────────────


class AudioLoopStatus(str, Enum):
    """Bounded local audio loop statuses.

    INACTIVE          — no local interaction; idle
    PRIMED            — wake/clap received; expecting transcript soon
    LISTENING_WINDOW  — active interaction window is open; transcripts are
                        being accepted and routed to the voice session
    RESPONDING        — the session has produced a response; TTS in flight
    COOLING_DOWN      — response emitted; short tail before returning to
                        INACTIVE or another PRIMED
    """

    INACTIVE = "inactive"
    PRIMED = "primed"
    LISTENING_WINDOW = "listening_window"
    RESPONDING = "responding"
    COOLING_DOWN = "cooling_down"


@dataclass
class TranscriptEntry:
    """A bounded transcript record held inline on AudioLoopState."""

    entry_id: str
    text: str
    source: str  # "manual" | "future_stt" | "voice_turn" | etc.
    occurred_at: str
    session_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TranscriptEntry":
        return cls(
            entry_id=str(d.get("entry_id") or _new_id("alt")),
            text=str(d.get("text", "")),
            source=str(d.get("source", "manual")),
            occurred_at=str(d.get("occurred_at") or _utcnow()),
            session_id=d.get("session_id"),
            metadata=dict(d.get("metadata") or {}),
        )


@dataclass
class AudioLoopState:
    """Bounded audio loop state for a single node.

    The state machine is small and operator-understandable:

        INACTIVE → PRIMED → LISTENING_WINDOW → RESPONDING → COOLING_DOWN
                                                             │
                                                             └→ INACTIVE

    All transitions are explicit helper calls. Nothing auto-advances.
    """

    node_id: str
    status: AudioLoopStatus = AudioLoopStatus.INACTIVE

    # Correlation
    active_voice_session_id: Optional[str] = None
    last_wake_event_id: Optional[str] = None

    # Interaction timing
    last_primed_at: Optional[str] = None
    last_transcript_at: Optional[str] = None
    last_response_at: Optional[str] = None
    last_status_change_at: Optional[str] = None

    # Spoken presence (operator_presence integration)
    last_spoken_line: Optional[str] = None
    last_spoken_key: Optional[str] = None  # "from_mode→to_mode"
    last_spoken_at: Optional[str] = None

    # Window config
    window_timeout_s: float = 30.0
    cooldown_window_s: float = 4.0

    # Transcript ring buffer (inline, capped)
    transcripts: list[TranscriptEntry] = field(default_factory=list)

    # Lifecycle
    updated_at: str = field(default_factory=_utcnow)
    metadata: dict = field(default_factory=dict)

    # — derived helpers —————————————————————————————————————————————

    @property
    def is_open_window(self) -> bool:
        return self.status in (
            AudioLoopStatus.PRIMED,
            AudioLoopStatus.LISTENING_WINDOW,
            AudioLoopStatus.RESPONDING,
        )

    # — mutation —————————————————————————————————————————————————

    def append_transcript(self, entry: TranscriptEntry) -> None:
        self.transcripts.append(entry)
        if len(self.transcripts) > _MAX_TRANSCRIPTS_PER_NODE:
            drop = len(self.transcripts) - _MAX_TRANSCRIPTS_PER_NODE
            self.transcripts = self.transcripts[drop:]
        self.last_transcript_at = entry.occurred_at
        self.updated_at = entry.occurred_at

    # — serialization —————————————————————————————————————————————

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "active_voice_session_id": self.active_voice_session_id,
            "last_wake_event_id": self.last_wake_event_id,
            "last_primed_at": self.last_primed_at,
            "last_transcript_at": self.last_transcript_at,
            "last_response_at": self.last_response_at,
            "last_status_change_at": self.last_status_change_at,
            "last_spoken_line": self.last_spoken_line,
            "last_spoken_key": self.last_spoken_key,
            "last_spoken_at": self.last_spoken_at,
            "window_timeout_s": self.window_timeout_s,
            "cooldown_window_s": self.cooldown_window_s,
            "transcripts": [t.as_dict() for t in self.transcripts],
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "is_open_window": self.is_open_window,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AudioLoopState":
        try:
            status = AudioLoopStatus(d.get("status", "inactive"))
        except Exception:
            status = AudioLoopStatus.INACTIVE
        transcripts_raw = d.get("transcripts") or []
        transcripts: list[TranscriptEntry] = []
        if isinstance(transcripts_raw, list):
            for t in transcripts_raw:
                if isinstance(t, dict):
                    try:
                        transcripts.append(TranscriptEntry.from_dict(t))
                    except Exception:
                        continue
        return cls(
            node_id=str(d.get("node_id", "")),
            status=status,
            active_voice_session_id=d.get("active_voice_session_id"),
            last_wake_event_id=d.get("last_wake_event_id"),
            last_primed_at=d.get("last_primed_at"),
            last_transcript_at=d.get("last_transcript_at"),
            last_response_at=d.get("last_response_at"),
            last_status_change_at=d.get("last_status_change_at"),
            last_spoken_line=d.get("last_spoken_line"),
            last_spoken_key=d.get("last_spoken_key"),
            last_spoken_at=d.get("last_spoken_at"),
            window_timeout_s=float(d.get("window_timeout_s") or 30.0),
            cooldown_window_s=float(d.get("cooldown_window_s") or 4.0),
            transcripts=transcripts,
            updated_at=str(d.get("updated_at") or _utcnow()),
            metadata=dict(d.get("metadata") or {}),
        )


# ─── Store ────────────────────────────────────────────────────────────────────


class AudioLoopStore:
    """Durable, bounded, thread-safe index of AudioLoopStates by node_id.

    Mirrors OperatorStateStore exactly: dual-layer (in-mem + substrate
    storage), singleton via `get_audio_loop_store()`. Best-effort
    persistence — flush failures log and the in-memory state remains
    correct.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._by_node: dict[str, AudioLoopState] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence —————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from eos_ai.substrate.storage import get_storage

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
                        self._by_node[str(node_id)] = AudioLoopState.from_dict(row)
                    except Exception:
                        continue
            self._loaded = True

    def _flush(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage

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

    def get_or_create(self, node_id: str) -> AudioLoopState:
        with self._lock:
            state = self._by_node.get(node_id)
            if state is None:
                state = AudioLoopState(node_id=node_id)
                self._by_node[node_id] = state
            return state

    def get(self, node_id: str) -> Optional[AudioLoopState]:
        with self._lock:
            return self._by_node.get(node_id)

    def put(self, state: AudioLoopState) -> None:
        with self._lock:
            state.updated_at = _utcnow()
            self._by_node[state.node_id] = state
            self._enforce_retention()
            self._flush()

    def all(self) -> list[AudioLoopState]:
        with self._lock:
            return list(self._by_node.values())

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._by_node)
            by_status: dict[str, int] = {}
            for s in self._by_node.values():
                k = s.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total": total,
                "by_status": by_status,
                "cap": _MAX_NODES,
                "max_transcripts_per_node": _MAX_TRANSCRIPTS_PER_NODE,
            }

    def clear(self) -> None:
        with self._lock:
            self._by_node.clear()
            self._flush()

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_node)


_store_singleton: Optional[AudioLoopStore] = None
_store_singleton_lock = threading.Lock()


def get_audio_loop_store() -> AudioLoopStore:
    global _store_singleton
    if _store_singleton is None:
        with _store_singleton_lock:
            if _store_singleton is None:
                _store_singleton = AudioLoopStore()
    return _store_singleton


def reset_audio_loop_store_for_tests() -> None:
    global _store_singleton
    with _store_singleton_lock:
        _store_singleton = None


# ─── Helper surface — explicit status transitions ────────────────────────────
#
# Every state change goes through one of these helpers. They are called from
# wake_producer, voice_session, operator_transitions, and transcript_inject.
# All are best-effort: they catch and log, never raise.


def _set_status(state: AudioLoopState, new_status: AudioLoopStatus) -> AudioLoopState:
    state.status = new_status
    state.last_status_change_at = _utcnow()
    return state


def mark_primed(
    node_id: str,
    *,
    wake_event_id: Optional[str] = None,
    voice_session_id: Optional[str] = None,
) -> Optional[AudioLoopState]:
    """Wake/clap received — interaction window is expected soon."""
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        if wake_event_id:
            state.last_wake_event_id = wake_event_id
        if voice_session_id:
            state.active_voice_session_id = voice_session_id
        _set_status(state, AudioLoopStatus.PRIMED)
        state.last_primed_at = state.last_status_change_at
        store.put(state)
        return state
    except Exception as e:  # noqa: BLE001
        _log(f"mark_primed failed: {e}")
        return None


def mark_listening(
    node_id: str,
    *,
    voice_session_id: Optional[str] = None,
) -> Optional[AudioLoopState]:
    """Interaction window is now open — transcripts are being accepted."""
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        if voice_session_id:
            state.active_voice_session_id = voice_session_id
        _set_status(state, AudioLoopStatus.LISTENING_WINDOW)
        store.put(state)
        return state
    except Exception as e:  # noqa: BLE001
        _log(f"mark_listening failed: {e}")
        return None


def mark_responding(
    node_id: str,
    *,
    voice_session_id: Optional[str] = None,
) -> Optional[AudioLoopState]:
    """Response produced — TTS in flight."""
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        if voice_session_id:
            state.active_voice_session_id = voice_session_id
        _set_status(state, AudioLoopStatus.RESPONDING)
        state.last_response_at = state.last_status_change_at
        store.put(state)
        return state
    except Exception as e:  # noqa: BLE001
        _log(f"mark_responding failed: {e}")
        return None


def mark_cooling_down(
    node_id: str,
) -> Optional[AudioLoopState]:
    """Response emitted — short tail before INACTIVE."""
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        _set_status(state, AudioLoopStatus.COOLING_DOWN)
        store.put(state)
        return state
    except Exception as e:  # noqa: BLE001
        _log(f"mark_cooling_down failed: {e}")
        return None


def mark_inactive(
    node_id: str,
) -> Optional[AudioLoopState]:
    """Explicit close of the interaction window."""
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        _set_status(state, AudioLoopStatus.INACTIVE)
        state.active_voice_session_id = None
        store.put(state)
        return state
    except Exception as e:  # noqa: BLE001
        _log(f"mark_inactive failed: {e}")
        return None


def record_transcript(
    node_id: str,
    text: str,
    *,
    source: str = "manual",
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[TranscriptEntry]:
    """Append a transcript entry to the node's bounded ring buffer.

    Does NOT change status. Callers (e.g. transcript_inject) are expected
    to mark_listening / mark_responding explicitly around the call.
    """
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        entry = TranscriptEntry(
            entry_id=_new_id("alt"),
            text=(text or "").strip(),
            source=source,
            occurred_at=_utcnow(),
            session_id=session_id,
            metadata=dict(metadata or {}),
        )
        state.append_transcript(entry)
        store.put(state)
        return entry
    except Exception as e:  # noqa: BLE001
        _log(f"record_transcript failed: {e}")
        return None


def should_speak_presence_line(
    node_id: str,
    *,
    from_mode: Optional[str],
    to_mode: str,
    now: Optional[datetime] = None,
    cooldown_s: float = _DEFAULT_SPOKEN_COOLDOWN_S,
) -> bool:
    """Dedupe logic for operator_presence spoken lines.

    Returns True if the (from_mode, to_mode) line for this node has NOT
    been spoken within the last `cooldown_s` seconds. The key combines
    both modes so a legitimate later transition is still allowed.
    """
    try:
        store = get_audio_loop_store()
        state = store.get(node_id)
        if state is None:
            return True
        key = f"{from_mode or '*'}→{to_mode}"
        if state.last_spoken_key != key:
            return True
        last_at = _parse_iso(state.last_spoken_at)
        if last_at is None:
            return True
        current = now or datetime.now(timezone.utc)
        delta = (current - last_at).total_seconds()
        return delta >= float(cooldown_s)
    except Exception as e:  # noqa: BLE001
        _log(f"should_speak_presence_line failed: {e}")
        return True  # prefer speaking over silence on failure


def record_spoken_line(
    node_id: str,
    *,
    from_mode: Optional[str],
    to_mode: str,
    line: str,
) -> Optional[AudioLoopState]:
    """Record that an operator_presence line was spoken on this node."""
    try:
        store = get_audio_loop_store()
        state = store.get_or_create(node_id)
        state.last_spoken_line = line
        state.last_spoken_key = f"{from_mode or '*'}→{to_mode}"
        state.last_spoken_at = _utcnow()
        store.put(state)
        return state
    except Exception as e:  # noqa: BLE001
        _log(f"record_spoken_line failed: {e}")
        return None


def snapshot(node_id: Optional[str] = None) -> dict[str, Any]:
    """JSON-friendly snapshot for reporting. Best-effort."""
    try:
        store = get_audio_loop_store()
        if node_id is not None:
            state = store.get(node_id)
            states = [state.as_dict()] if state is not None else []
        else:
            states = [s.as_dict() for s in store.all()]
        return {
            "node_id": node_id,
            "count": len(states),
            "states": states,
            "stats": store.stats(),
        }
    except Exception as e:  # noqa: BLE001
        _log(f"snapshot failed: {e}")
        return {"node_id": node_id, "count": 0, "states": [], "stats": {}}


__all__ = [
    "AudioLoopStatus",
    "TranscriptEntry",
    "AudioLoopState",
    "AudioLoopStore",
    "get_audio_loop_store",
    "reset_audio_loop_store_for_tests",
    "mark_primed",
    "mark_listening",
    "mark_responding",
    "mark_cooling_down",
    "mark_inactive",
    "record_transcript",
    "should_speak_presence_line",
    "record_spoken_line",
    "snapshot",
]
