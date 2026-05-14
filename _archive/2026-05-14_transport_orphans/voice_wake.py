"""
Voice wake — local station input layer for wake word, clap trigger, and
voice/TTS mode state.

Purpose
-------
Provides a singleton state model for the station's voice activation
surface: which triggers are enabled, whether TTS is on, what mode the
station is in, and what last activated it.

This is *configuration and current-status* — not event history. For the
bounded event ring buffer of individual wake/clap activations, see
wake_producer.py.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path (gateway/cognitive_loop/model_router/agent_runtime/
  primitives) is never imported.
- Singleton state. One VoiceWakeState per process, persisted via substrate
  storage under key ``voice_wake_state``.
- Best-effort. All public functions catch and log; never raise into callers.
- Thread-safe. RLock on all shared state.
- Reversible. Removing this file leaves the substrate exactly as it was.
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "voice_wake_state"


def _log(msg: str) -> None:
    print(f"[substrate.voice_wake] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Enums ───────────────────────────────────────────────────────────────────


class WakeTrigger(str, Enum):
    """Source that triggered the last wake activation."""

    WAKE_WORD = "wake_word"
    CLAP = "clap"
    MANUAL = "manual"
    DISCORD = "discord"
    UNKNOWN = "unknown"


class StationMode(str, Enum):
    """Current station voice-input mode."""

    INACTIVE = "inactive"
    LISTENING = "listening"
    ACTIVE = "active"
    MUTED = "muted"


# ─── Dataclass ───────────────────────────────────────────────────────────────


@dataclass
class VoiceWakeState:
    """Singleton configuration + status for the station voice wake layer."""

    is_listening: bool = False
    wake_enabled: bool = False
    clap_enabled: bool = False
    tts_enabled: bool = False
    last_trigger: Optional[WakeTrigger] = None
    last_trigger_at: Optional[str] = None
    last_phrase: Optional[str] = None
    station_mode: StationMode = StationMode.INACTIVE
    updated_at: str = field(default_factory=_utcnow)

    @classmethod
    def new(cls) -> VoiceWakeState:
        """Create a fresh default state."""
        return cls()

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON storage."""
        return {
            "is_listening": self.is_listening,
            "wake_enabled": self.wake_enabled,
            "clap_enabled": self.clap_enabled,
            "tts_enabled": self.tts_enabled,
            "last_trigger": self.last_trigger.value if self.last_trigger else None,
            "last_trigger_at": self.last_trigger_at,
            "last_phrase": self.last_phrase,
            "station_mode": self.station_mode.value,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> VoiceWakeState:
        """Deserialize from a plain dict. Tolerant of missing/bad keys."""
        # last_trigger enum
        last_trigger: Optional[WakeTrigger] = None
        raw_trigger = d.get("last_trigger")
        if raw_trigger is not None:
            try:
                last_trigger = WakeTrigger(raw_trigger)
            except (ValueError, KeyError):
                last_trigger = WakeTrigger.UNKNOWN

        # station_mode enum
        try:
            station_mode = StationMode(d.get("station_mode", "inactive"))
        except (ValueError, KeyError):
            station_mode = StationMode.INACTIVE

        return cls(
            is_listening=bool(d.get("is_listening", False)),
            wake_enabled=bool(d.get("wake_enabled", False)),
            clap_enabled=bool(d.get("clap_enabled", False)),
            tts_enabled=bool(d.get("tts_enabled", False)),
            last_trigger=last_trigger,
            last_trigger_at=d.get("last_trigger_at"),
            last_phrase=d.get("last_phrase"),
            station_mode=station_mode,
            updated_at=str(d.get("updated_at") or _utcnow()),
        )


# ─── Store ───────────────────────────────────────────────────────────────────


class VoiceWakeStore:
    """Durable, thread-safe singleton store for VoiceWakeState.

    Stores a SINGLE VoiceWakeState (not a collection) under the
    ``voice_wake_state`` key in substrate storage. Dual-layer: in-memory
    for speed, flushed to durable storage on every mutation.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._state: Optional[VoiceWakeState] = None
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from runtime.transport.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting with defaults")
                raw = None
            if isinstance(raw, dict):
                try:
                    self._state = VoiceWakeState.from_dict(raw)
                except Exception:
                    self._state = VoiceWakeState.new()
            else:
                self._state = VoiceWakeState.new()
            self._loaded = True

    def _flush(self) -> None:
        try:
            from runtime.transport.storage import get_storage

            if self._state is not None:
                get_storage().put(_STORAGE_KEY, self._state.to_dict())
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    # — public api —————————————————————————————————————————————

    def get(self) -> VoiceWakeState:
        """Return current state, creating a default if none exists."""
        with self._lock:
            if self._state is None:
                self._state = VoiceWakeState.new()
            return self._state

    def put(self, state: VoiceWakeState) -> None:
        """Update the state, stamp updated_at, and persist."""
        with self._lock:
            state.updated_at = _utcnow()
            self._state = state
            self._flush()

    # — singleton ——————————————————————————————————————————————

    @classmethod
    def default(cls) -> VoiceWakeStore:
        """Return the process-wide singleton store."""
        global _default
        if _default is None:
            with _default_lock:
                if _default is None:
                    _default = cls()
        return _default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Test hook — drop the singleton so the next default() re-resolves."""
        global _default
        with _default_lock:
            _default = None


_default: Optional[VoiceWakeStore] = None
_default_lock = threading.Lock()


# ─── Wake detection adapter interfaces ───────────────────────────────────────


class WakeWordAdapter:
    """Interface for wake word detection.

    Override detect() to integrate with a real wake word engine
    (e.g., Porcupine, Vosk, etc). Default stub always returns (False, None).
    """

    def detect(self, audio_chunk: bytes) -> tuple[bool, Optional[str]]:
        """Return (detected, phrase) from audio chunk."""
        return False, None


class ClapAdapter:
    """Interface for clap detection.

    Override detect() to integrate with a real audio analyzer.
    Default stub always returns False.
    """

    def detect(self, audio_chunk: bytes) -> bool:
        """Return True if clap detected in audio chunk."""
        return False


# ─── Control functions ───────────────────────────────────────────────────────


def enable_wake() -> VoiceWakeState:
    """Enable wake word listening. Returns updated state."""
    store = VoiceWakeStore.default()
    state = store.get()
    state.wake_enabled = True
    state.is_listening = True
    state.station_mode = StationMode.LISTENING
    store.put(state)
    _log("wake word listening enabled")
    return state


def disable_wake() -> VoiceWakeState:
    """Disable wake word listening. Returns updated state."""
    store = VoiceWakeStore.default()
    state = store.get()
    state.wake_enabled = False
    if not state.clap_enabled:
        state.is_listening = False
        state.station_mode = StationMode.INACTIVE
    store.put(state)
    _log("wake word listening disabled")
    return state


def enable_clap() -> VoiceWakeState:
    """Enable clap detection. Returns updated state."""
    store = VoiceWakeStore.default()
    state = store.get()
    state.clap_enabled = True
    state.is_listening = True
    state.station_mode = StationMode.LISTENING
    store.put(state)
    _log("clap detection enabled")
    return state


def disable_clap() -> VoiceWakeState:
    """Disable clap detection. Returns updated state."""
    store = VoiceWakeStore.default()
    state = store.get()
    state.clap_enabled = False
    if not state.wake_enabled:
        state.is_listening = False
        state.station_mode = StationMode.INACTIVE
    store.put(state)
    _log("clap detection disabled")
    return state


def enable_tts() -> VoiceWakeState:
    """Enable text-to-speech output. Returns updated state."""
    store = VoiceWakeStore.default()
    state = store.get()
    state.tts_enabled = True
    store.put(state)
    _log("TTS enabled")
    return state


def disable_tts() -> VoiceWakeState:
    """Disable text-to-speech output. Returns updated state."""
    store = VoiceWakeStore.default()
    state = store.get()
    state.tts_enabled = False
    store.put(state)
    _log("TTS disabled")
    return state


def register_trigger(
    trigger: WakeTrigger, *, phrase: Optional[str] = None
) -> VoiceWakeState:
    """Register that a wake/clap/manual trigger has fired.

    Updates last_trigger, last_trigger_at, last_phrase, and sets
    station_mode to ACTIVE. Returns updated state.
    """
    store = VoiceWakeStore.default()
    state = store.get()
    state.last_trigger = trigger
    state.last_trigger_at = _utcnow()
    state.last_phrase = phrase
    state.station_mode = StationMode.ACTIVE
    store.put(state)
    _log(f"trigger registered: {trigger.value} phrase={phrase!r}")
    return state


def get_voice_wake_summary() -> dict:
    """Get summary suitable for open_day/close_day integration.

    Returns a compact dict with the current wake/clap/tts settings,
    station mode, and last trigger information.
    """
    store = VoiceWakeStore.default()
    state = store.get()
    return {
        "wake_enabled": state.wake_enabled,
        "clap_enabled": state.clap_enabled,
        "tts_enabled": state.tts_enabled,
        "station_mode": state.station_mode.value,
        "last_trigger": state.last_trigger.value if state.last_trigger else None,
        "last_trigger_at": state.last_trigger_at,
    }


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "WakeTrigger",
    "StationMode",
    "VoiceWakeState",
    "VoiceWakeStore",
    "WakeWordAdapter",
    "ClapAdapter",
    "enable_wake",
    "disable_wake",
    "enable_clap",
    "disable_clap",
    "enable_tts",
    "disable_tts",
    "register_trigger",
    "get_voice_wake_summary",
]
