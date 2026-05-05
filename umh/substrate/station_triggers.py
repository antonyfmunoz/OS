"""
Station triggers — event history and control-plane dispatch for
wake word, clap, manual, and Discord triggers.

Builds on top of voice_wake.py (which stores *current state*) by adding:
  1. A bounded event store for trigger history.
  2. A control-plane dispatcher that maps triggers to safe workflows
     (open_day, open_scene, activate station mode).

Triggers do NOT directly execute arbitrary actions.  They invoke
control-plane workflows only.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only.  Hot path never imported.
- Best-effort.  All public functions catch and log; never raise.
- Thread-safe.  Bounded to 200 events; oldest pruned first.
- Persisted via substrate storage under key ``station_triggers``.
"""

from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "station_triggers"
_MAX_EVENTS = 200


def _log(msg: str) -> None:
    print(f"[substrate.station_triggers] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"trig_{uuid.uuid4().hex[:12]}"


# ─── Enums ───────────────────────────────────────────────────────────────────


class StationTriggerType(str, Enum):
    """Source of the station trigger."""

    WAKE_WORD = "wake_word"
    CLAP = "clap"
    MANUAL = "manual"
    DISCORD = "discord"


# ─── Dataclass ───────────────────────────────────────────────────────────────


@dataclass
class StationTriggerEvent:
    """A single trigger activation event with lifecycle tracking."""

    event_id: str
    trigger_type: StationTriggerType
    phrase: Optional[str] = None
    created_at: str = field(default_factory=_utcnow)
    accepted: bool = True
    reason: Optional[str] = None

    @classmethod
    def new(
        cls,
        trigger_type: StationTriggerType,
        *,
        phrase: Optional[str] = None,
        accepted: bool = True,
        reason: Optional[str] = None,
    ) -> StationTriggerEvent:
        """Create a new trigger event with generated ID."""
        return cls(
            event_id=_new_id(),
            trigger_type=trigger_type,
            phrase=phrase,
            accepted=accepted,
            reason=reason,
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON storage."""
        return {
            "event_id": self.event_id,
            "trigger_type": self.trigger_type.value,
            "phrase": self.phrase,
            "created_at": self.created_at,
            "accepted": self.accepted,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StationTriggerEvent:
        """Deserialize from a dict.  Tolerant of missing/bad keys."""
        try:
            trigger_type = StationTriggerType(d.get("trigger_type", "manual"))
        except (ValueError, KeyError):
            trigger_type = StationTriggerType.MANUAL

        return cls(
            event_id=str(d.get("event_id") or _new_id()),
            trigger_type=trigger_type,
            phrase=d.get("phrase"),
            created_at=str(d.get("created_at") or _utcnow()),
            accepted=bool(d.get("accepted", True)),
            reason=d.get("reason"),
        )


# ─── Store ───────────────────────────────────────────────────────────────────


class StationTriggerStore:
    """Bounded, persistent event store for station triggers.

    Dual-layer: in-memory dict + substrate.storage.  Thread-safe singleton.
    Bounded to _MAX_EVENTS entries; oldest events pruned first.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._events: dict[str, StationTriggerEvent] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ————————————————————————————————————————————

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from umh.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict):
                        try:
                            self._events[key] = StationTriggerEvent.from_dict(val)
                        except Exception:  # noqa: BLE001
                            continue
            self._loaded = True

    def _flush(self) -> None:
        try:
            from umh.substrate.storage import get_storage

            payload = {eid: e.to_dict() for eid, e in self._events.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _prune(self) -> None:
        """Drop oldest events when over _MAX_EVENTS.  Caller holds lock."""
        if len(self._events) <= _MAX_EVENTS:
            return
        sorted_events = sorted(self._events.values(), key=lambda e: e.created_at)
        drop_count = len(self._events) - _MAX_EVENTS
        for evt in sorted_events[:drop_count]:
            self._events.pop(evt.event_id, None)

    # — public api —————————————————————————————————————————————

    def put(self, event: StationTriggerEvent) -> None:
        """Persist an event.  Prunes if over capacity."""
        with self._lock:
            self._events[event.event_id] = event
            self._prune()
            self._flush()

    def recent(self, limit: int = 20) -> list[StationTriggerEvent]:
        """Return the most recent N events, newest first."""
        with self._lock:
            sorted_events = sorted(
                self._events.values(), key=lambda e: e.created_at, reverse=True
            )
            return sorted_events[:limit]

    def all(self) -> list[StationTriggerEvent]:
        """Return all events, newest first."""
        with self._lock:
            return sorted(
                self._events.values(), key=lambda e: e.created_at, reverse=True
            )

    # — singleton ——————————————————————————————————————————————

    _default: Optional["StationTriggerStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> StationTriggerStore:
        """Return the process-wide singleton store."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Test hook — drop the singleton."""
        with cls._default_lock:
            cls._default = None


# ─── Public API ──────────────────────────────────────────────────────────────


def register_station_trigger(
    trigger_type: StationTriggerType,
    phrase: Optional[str] = None,
) -> StationTriggerEvent:
    """Register a trigger event and update station presence.

    Creates a StationTriggerEvent, persists it, and best-effort updates
    the station_presence and voice_wake state for backward compatibility.
    """
    event = StationTriggerEvent.new(trigger_type, phrase=phrase)
    StationTriggerStore.default().put(event)

    # Best-effort: update station presence with trigger info
    try:
        from umh.substrate.station_presence import update_station_presence

        update_station_presence(
            last_trigger_type=trigger_type.value,
            last_trigger_at=event.created_at,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"station_presence update failed: {e}")

    # Best-effort: update voice_wake for backward compat
    try:
        from umh.substrate.voice_wake import WakeTrigger, register_trigger

        wake_map = {
            StationTriggerType.WAKE_WORD: WakeTrigger.WAKE_WORD,
            StationTriggerType.CLAP: WakeTrigger.CLAP,
            StationTriggerType.MANUAL: WakeTrigger.MANUAL,
            StationTriggerType.DISCORD: WakeTrigger.DISCORD,
        }
        wake_trigger = wake_map.get(trigger_type, WakeTrigger.MANUAL)
        register_trigger(wake_trigger, phrase=phrase)
    except Exception as e:  # noqa: BLE001
        _log(f"voice_wake register_trigger failed: {e}")

    _log(f"trigger registered: {trigger_type.value} phrase={phrase!r}")
    return event


def handle_station_trigger(
    trigger_type: StationTriggerType,
    phrase: Optional[str] = None,
) -> dict[str, Any]:
    """Handle a trigger by dispatching to the appropriate control-plane flow.

    Rules for v1:
    - Triggers call control-plane workflows only.
    - Supported actions: open_day, open_scene, activate_station.
    - If the system is already active, trigger is acknowledged but
      may be a no-op depending on the phrase.
    - No arbitrary action execution.
    """
    result: dict[str, Any] = {
        "status": "ok",
        "action": "none",
        "trigger_type": trigger_type.value,
    }

    try:
        # Register the event
        event = register_station_trigger(trigger_type, phrase)
        result["event_id"] = event.event_id

        # Parse phrase for intent
        phrase_lower = (phrase or "").lower().strip()

        # Check if day is already open
        day_is_open = False
        try:
            from umh.substrate.operator_session import OperatorSessionStore

            session = OperatorSessionStore.default().get()
            if session is not None and session.is_day_open:
                day_is_open = True
        except Exception:  # noqa: BLE001
            pass

        # Dispatch based on phrase content
        if "open scene" in phrase_lower:
            scene_name = phrase_lower.replace("open scene", "").strip()
            result["action"] = "open_scene"
            if scene_name:
                result["scene_name"] = scene_name
                try:
                    from umh.substrate.local_control import open_scene

                    req = open_scene(scene_name, requested_by="trigger")
                    result["request_id"] = req.request_id
                    result["request_status"] = req.status.value
                except Exception as e:  # noqa: BLE001
                    result["error"] = str(e)
            else:
                result["error"] = "no scene name in phrase"

        elif "open day" in phrase_lower or (not day_is_open and not phrase_lower):
            if day_is_open:
                result["status"] = "already_active"
                result["action"] = "ignored"
            else:
                result["action"] = "open_day"
                try:
                    from umh.substrate.day_workflows import open_day

                    day_result = open_day()
                    result["day_status"] = day_result.get("status")
                    result["day_session_id"] = day_result.get("day_session_id")
                except Exception as e:  # noqa: BLE001
                    result["error"] = str(e)

        elif day_is_open:
            # System already active — acknowledge, ensure LOCAL presence
            result["status"] = "already_active"
            result["action"] = "activate_station"
            try:
                from umh.substrate.station_presence import (
                    StationPresenceMode,
                    set_presence_mode,
                )

                set_presence_mode(StationPresenceMode.LOCAL)
            except Exception:  # noqa: BLE001
                pass

        else:
            # Default: open day
            result["action"] = "open_day"
            try:
                from umh.substrate.day_workflows import open_day

                day_result = open_day()
                result["day_status"] = day_result.get("status")
                result["day_session_id"] = day_result.get("day_session_id")
            except Exception as e:  # noqa: BLE001
                result["error"] = str(e)

    except Exception as exc:  # noqa: BLE001
        _log(f"handle_station_trigger error: {exc}")
        result["status"] = "error"
        result["error"] = str(exc)

    return result


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "StationTriggerType",
    "StationTriggerEvent",
    "StationTriggerStore",
    "register_station_trigger",
    "handle_station_trigger",
]
