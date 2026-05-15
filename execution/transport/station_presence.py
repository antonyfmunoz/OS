"""
Station presence — unified station posture and availability state.

Combines node availability, wake/clap/tts flags, control mode, and
operator presence mode into a single queryable singleton.  This is the
"where is the operator and what's available" question answered in one
place.

Distinct from:
  - OperatorDayMode (operator_session.py) — daily lifecycle posture
  - StationMode (voice_wake.py) — voice input FSM
  - LocalControlMode (local_control.py) — trust level for machine control

StationPresence is a *read model* that aggregates these for consumers
who need a single snapshot without importing 4 modules.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only.  Hot path never imported.
- Singleton state via StationPresenceStore.
- Best-effort.  All public functions catch and log; never raise.
- Thread-safe.  RLock on all shared state.
- Persisted via substrate storage under key ``station_presence``.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "station_presence"


def _log(msg: str) -> None:
    print(f"[substrate.station_presence] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"sp_{uuid.uuid4().hex[:12]}"


# ─── Enums ───────────────────────────────────────────────────────────────────


class StationPresenceMode(str, Enum):
    """High-level operator station posture.

    AWAY       — operator not at any station
    REMOTE     — operating via mobile/remote device only
    LOCAL      — at the primary local workstation
    DEEP_WORK  — focus block; suppress non-critical notifications
    OVERNIGHT  — day closed; autonomous execution mode
    """

    AWAY = "away"
    REMOTE = "remote"
    LOCAL = "local"
    DEEP_WORK = "deep_work"
    OVERNIGHT = "overnight"


# ─── Dataclass ───────────────────────────────────────────────────────────────


@dataclass
class StationPresence:
    """Unified station presence snapshot.

    Aggregates posture mode, node availability, and wake/clap/tts flags
    into a single persistent object.
    """

    presence_id: str
    mode: StationPresenceMode = StationPresenceMode.AWAY
    local_available: bool = False
    vps_available: bool = True
    wake_enabled: bool = False
    clap_enabled: bool = False
    tts_enabled: bool = False
    last_trigger_type: Optional[str] = None
    last_trigger_at: Optional[str] = None
    updated_at: str = field(default_factory=_utcnow)

    @classmethod
    def new(cls) -> StationPresence:
        """Create a fresh default presence."""
        return cls(presence_id=_new_id())

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON storage."""
        return {
            "presence_id": self.presence_id,
            "mode": self.mode.value,
            "local_available": self.local_available,
            "vps_available": self.vps_available,
            "wake_enabled": self.wake_enabled,
            "clap_enabled": self.clap_enabled,
            "tts_enabled": self.tts_enabled,
            "last_trigger_type": self.last_trigger_type,
            "last_trigger_at": self.last_trigger_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StationPresence:
        """Deserialize from a plain dict.  Tolerant of missing/bad keys."""
        try:
            mode = StationPresenceMode(d.get("mode", "away"))
        except (ValueError, KeyError):
            mode = StationPresenceMode.AWAY

        return cls(
            presence_id=str(d.get("presence_id") or _new_id()),
            mode=mode,
            local_available=bool(d.get("local_available", False)),
            vps_available=bool(d.get("vps_available", True)),
            wake_enabled=bool(d.get("wake_enabled", False)),
            clap_enabled=bool(d.get("clap_enabled", False)),
            tts_enabled=bool(d.get("tts_enabled", False)),
            last_trigger_type=d.get("last_trigger_type"),
            last_trigger_at=d.get("last_trigger_at"),
            updated_at=str(d.get("updated_at") or _utcnow()),
        )


# ─── Store ───────────────────────────────────────────────────────────────────


class StationPresenceStore:
    """Durable, thread-safe singleton store for StationPresence.

    Stores a SINGLE StationPresence (not a collection) under the
    ``station_presence`` key in substrate storage.  Dual-layer: in-memory
    for speed, flushed to durable storage on every mutation.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._state: Optional[StationPresence] = None
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from execution.transport.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting with defaults")
                raw = None
            if isinstance(raw, dict):
                try:
                    self._state = StationPresence.from_dict(raw)
                except Exception:
                    self._state = StationPresence.new()
            else:
                self._state = StationPresence.new()
            self._loaded = True

    def _flush(self) -> None:
        try:
            from execution.transport.storage import get_storage

            if self._state is not None:
                get_storage().put(_STORAGE_KEY, self._state.to_dict())
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    # — public api —————————————————————————————————————————————

    def get(self) -> StationPresence:
        """Return current state, creating a default if none exists."""
        with self._lock:
            if self._state is None:
                self._state = StationPresence.new()
            return self._state

    def put(self, state: StationPresence) -> None:
        """Update the state, stamp updated_at, and persist."""
        with self._lock:
            state.updated_at = _utcnow()
            self._state = state
            self._flush()

    # — singleton ——————————————————————————————————————————————

    _default: Optional["StationPresenceStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> StationPresenceStore:
        """Return the process-wide singleton store."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Test hook — drop the singleton so the next default() re-resolves."""
        with cls._default_lock:
            cls._default = None


# ─── Control functions ───────────────────────────────────────────────────────


def get_station_presence() -> StationPresence:
    """Return the current station presence."""
    return StationPresenceStore.default().get()


def update_station_presence(
    *,
    mode: Optional[StationPresenceMode] = None,
    local_available: Optional[bool] = None,
    vps_available: Optional[bool] = None,
    wake_enabled: Optional[bool] = None,
    clap_enabled: Optional[bool] = None,
    tts_enabled: Optional[bool] = None,
    last_trigger_type: Optional[str] = None,
    last_trigger_at: Optional[str] = None,
) -> StationPresence:
    """Partial update — only supplied fields are changed."""
    store = StationPresenceStore.default()
    state = store.get()
    if mode is not None:
        state.mode = mode
    if local_available is not None:
        state.local_available = local_available
    if vps_available is not None:
        state.vps_available = vps_available
    if wake_enabled is not None:
        state.wake_enabled = wake_enabled
    if clap_enabled is not None:
        state.clap_enabled = clap_enabled
    if tts_enabled is not None:
        state.tts_enabled = tts_enabled
    if last_trigger_type is not None:
        state.last_trigger_type = last_trigger_type
    if last_trigger_at is not None:
        state.last_trigger_at = last_trigger_at
    store.put(state)
    return state


def set_presence_mode(mode: StationPresenceMode) -> StationPresence:
    """Set the station presence mode."""
    return update_station_presence(mode=mode)


def mark_local_available() -> StationPresence:
    """Mark the local station as available."""
    return update_station_presence(local_available=True)


def mark_local_unavailable() -> StationPresence:
    """Mark the local station as unavailable."""
    return update_station_presence(local_available=False)


def get_station_summary() -> dict:
    """Get unified station summary for open_day/close_day integration.

    Reads from station_presence for posture, and best-effort reads
    from local_control for control_mode.

    Returns:
        {
            "presence_mode": str,
            "local_available": bool,
            "vps_available": bool,
            "wake_enabled": bool,
            "clap_enabled": bool,
            "tts_enabled": bool,
            "control_mode": str,
            "last_trigger_type": str | None,
            "last_trigger_at": str | None,
        }
    """
    state = get_station_presence()

    control_mode = "passive"
    try:
        from execution.transport.local_control import LocalControlStore

        control_mode = LocalControlStore.default().get_mode().value
    except Exception:  # noqa: BLE001
        pass

    return {
        "presence_mode": state.mode.value,
        "local_available": state.local_available,
        "vps_available": state.vps_available,
        "wake_enabled": state.wake_enabled,
        "clap_enabled": state.clap_enabled,
        "tts_enabled": state.tts_enabled,
        "control_mode": control_mode,
        "last_trigger_type": state.last_trigger_type,
        "last_trigger_at": state.last_trigger_at,
    }


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "StationPresenceMode",
    "StationPresence",
    "StationPresenceStore",
    "get_station_presence",
    "update_station_presence",
    "set_presence_mode",
    "mark_local_available",
    "mark_local_unavailable",
    "get_station_summary",
]
