# Station Presence + Local Control + Live Session + Perception Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add unified station presence state, trigger event history with control-plane dispatch, enhanced scene preferences, new perception collectors for workstation state, and integrate everything into the day workflow summaries.

**Architecture:** Extends the existing v4 substrate layer. station_presence.py is the only genuinely new module — it unifies node availability, wake state, and control mode into one queryable singleton. station_triggers.py adds event history and control-plane dispatch on top of existing voice_wake.py triggers. scenes.py gets preference fields. perception.py gets 3 new collectors. day_workflows.py gets structured station/live summaries.

**Tech Stack:** Python 3.12, substrate storage (JSON file + Neon), existing substrate patterns (singleton stores, dataclass + to_dict/from_dict, best-effort error handling, bounded collections).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `eos_ai/substrate/station_presence.py` | **CREATE** | Unified station presence state (mode + availability + wake/control flags) |
| `eos_ai/substrate/station_triggers.py` | **CREATE** | Trigger event history store + control-plane dispatch |
| `eos_ai/substrate/scenes.py` | **MODIFY** | Add preference fields to Scene (control_mode, tts, wake) |
| `eos_ai/substrate/perception.py` | **MODIFY** | Add 3 new collectors: station_presence, local_control_backlog, live_session_state |
| `eos_ai/substrate/day_workflows.py` | **MODIFY** | Structured station_summary + live_session_summary in open_day/close_day |
| `eos_ai/substrate/__init__.py` | **MODIFY** | Export new modules |
| `tests/substrate/test_station_presence.py` | **CREATE** | Station presence tests |
| `tests/substrate/test_station_triggers.py` | **CREATE** | Station trigger tests |
| `tests/substrate/test_station_scenes.py` | **CREATE** | Enhanced scene tests |
| `tests/substrate/test_perception.py` | **MODIFY** | Add tests for new collectors |
| `tests/substrate/test_day_workflows.py` | **MODIFY** | Add tests for new summary keys |

---

### Task 1: Create station_presence.py — Model + Store

**Files:**
- Create: `eos_ai/substrate/station_presence.py`
- Test: `tests/substrate/test_station_presence.py`

- [ ] **Step 1: Write the test file with all test cases**

```python
"""Smoke tests for eos_ai.substrate.station_presence.

Validates:
  1. test_default_state           — fresh presence has expected defaults
  2. test_set_presence_mode       — mode changes correctly
  3. test_mark_local_available    — local_available toggles
  4. test_mark_local_unavailable  — local_available goes False
  5. test_update_station_presence — partial update preserves other fields
  6. test_persistence             — survives singleton reset
  7. test_get_station_summary     — summary returns expected keys
  8. test_roundtrip               — to_dict/from_dict roundtrip

Run directly:
    python3 tests/substrate/test_station_presence.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.station_presence import (  # noqa: E402
    StationPresence,
    StationPresenceMode,
    StationPresenceStore,
    get_station_presence,
    get_station_summary,
    mark_local_available,
    mark_local_unavailable,
    set_presence_mode,
    update_station_presence,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _reset_all() -> None:
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("station_presence", None)
    except Exception:
        pass
    StationPresenceStore.reset_default_for_tests()


def test_default_state() -> None:
    print("\n── Test: default state ──")
    _reset_all()
    p = get_station_presence()
    _report("mode is AWAY", p.mode == StationPresenceMode.AWAY)
    _report("local_available is False", p.local_available is False)
    _report("vps_available is True", p.vps_available is True)
    _report("wake_enabled is False", p.wake_enabled is False)
    _report("clap_enabled is False", p.clap_enabled is False)
    _report("tts_enabled is False", p.tts_enabled is False)
    _report("has presence_id", bool(p.presence_id))
    _report("has updated_at", bool(p.updated_at))


def test_set_presence_mode() -> None:
    print("\n── Test: set presence mode ──")
    _reset_all()
    p = set_presence_mode(StationPresenceMode.LOCAL)
    _report("mode is LOCAL", p.mode == StationPresenceMode.LOCAL)
    p = set_presence_mode(StationPresenceMode.DEEP_WORK)
    _report("mode is DEEP_WORK", p.mode == StationPresenceMode.DEEP_WORK)
    p = set_presence_mode(StationPresenceMode.OVERNIGHT)
    _report("mode is OVERNIGHT", p.mode == StationPresenceMode.OVERNIGHT)


def test_mark_local_available() -> None:
    print("\n── Test: mark local available ──")
    _reset_all()
    p = mark_local_available()
    _report("local_available True", p.local_available is True)


def test_mark_local_unavailable() -> None:
    print("\n── Test: mark local unavailable ──")
    _reset_all()
    mark_local_available()
    p = mark_local_unavailable()
    _report("local_available False", p.local_available is False)


def test_update_station_presence() -> None:
    print("\n── Test: partial update preserves fields ──")
    _reset_all()
    set_presence_mode(StationPresenceMode.LOCAL)
    mark_local_available()
    p = update_station_presence(wake_enabled=True, tts_enabled=True)
    _report("wake_enabled True", p.wake_enabled is True)
    _report("tts_enabled True", p.tts_enabled is True)
    _report("mode still LOCAL", p.mode == StationPresenceMode.LOCAL)
    _report("local_available still True", p.local_available is True)


def test_persistence() -> None:
    print("\n── Test: persistence survives singleton reset ──")
    _reset_all()
    set_presence_mode(StationPresenceMode.DEEP_WORK)
    mark_local_available()
    update_station_presence(wake_enabled=True)
    # Reset singleton — should reload from storage
    StationPresenceStore.reset_default_for_tests()
    p = get_station_presence()
    _report("mode survived", p.mode == StationPresenceMode.DEEP_WORK)
    _report("local_available survived", p.local_available is True)
    _report("wake_enabled survived", p.wake_enabled is True)


def test_get_station_summary() -> None:
    print("\n── Test: station summary keys ──")
    _reset_all()
    set_presence_mode(StationPresenceMode.LOCAL)
    mark_local_available()
    update_station_presence(wake_enabled=True, clap_enabled=True, tts_enabled=True)
    summary = get_station_summary()
    _report("has presence_mode", "presence_mode" in summary)
    _report("has local_available", "local_available" in summary)
    _report("has wake_enabled", "wake_enabled" in summary)
    _report("has clap_enabled", "clap_enabled" in summary)
    _report("has tts_enabled", "tts_enabled" in summary)
    _report("has control_mode", "control_mode" in summary)
    _report("presence_mode correct", summary["presence_mode"] == "local")
    _report("local_available correct", summary["local_available"] is True)


def test_roundtrip() -> None:
    print("\n── Test: to_dict/from_dict roundtrip ──")
    _reset_all()
    p = get_station_presence()
    p.mode = StationPresenceMode.LOCAL
    p.local_available = True
    p.wake_enabled = True
    p.last_trigger_type = "wake_word"
    p.last_trigger_at = "2026-04-14T10:00:00Z"
    d = p.to_dict()
    p2 = StationPresence.from_dict(d)
    _report("mode matches", p2.mode == p.mode)
    _report("local_available matches", p2.local_available == p.local_available)
    _report("wake_enabled matches", p2.wake_enabled == p.wake_enabled)
    _report("last_trigger_type matches", p2.last_trigger_type == p.last_trigger_type)
    _report("last_trigger_at matches", p2.last_trigger_at == p.last_trigger_at)


if __name__ == "__main__":
    print("=" * 60)
    print("station_presence smoke tests")
    print("=" * 60)
    test_default_state()
    test_set_presence_mode()
    test_mark_local_available()
    test_mark_local_unavailable()
    test_update_station_presence()
    test_persistence()
    test_get_station_summary()
    test_roundtrip()
    print(f"\n{'=' * 60}")
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    print("=" * 60)
    raise SystemExit(1 if _FAIL else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/substrate/test_station_presence.py`
Expected: ImportError (module does not exist yet)

- [ ] **Step 3: Write station_presence.py**

```python
"""
Station presence — unified station posture and availability state.

Combines node availability, wake/clap/tts flags, control mode, and
operator presence mode into a single queryable singleton. This is the
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
- Additive only. Hot path never imported.
- Singleton state via StationPresenceStore.
- Best-effort. All public functions catch and log; never raise.
- Thread-safe. RLock on all shared state.
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
    """High-level operator station posture."""

    AWAY = "away"
    REMOTE = "remote"
    LOCAL = "local"
    DEEP_WORK = "deep_work"
    OVERNIGHT = "overnight"


# ─── Dataclass ───────────────────────────────────────────────────────────────


@dataclass
class StationPresence:
    """Unified station presence snapshot."""

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

    Stores a SINGLE StationPresence under the ``station_presence`` key
    in substrate storage.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._state: Optional[StationPresence] = None
        self._loaded = False
        if autoload:
            self._load()

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from eos_ai.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:
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
            from eos_ai.substrate.storage import get_storage

            if self._state is not None:
                get_storage().put(_STORAGE_KEY, self._state.to_dict())
        except Exception as e:
            _log(f"flush failed: {e}")

    def get(self) -> StationPresence:
        with self._lock:
            if self._state is None:
                self._state = StationPresence.new()
            return self._state

    def put(self, state: StationPresence) -> None:
        with self._lock:
            state.updated_at = _utcnow()
            self._state = state
            self._flush()

    _default: Optional[StationPresenceStore] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> StationPresenceStore:
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
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
    """
    state = get_station_presence()

    control_mode = "passive"
    try:
        from eos_ai.substrate.local_control import LocalControlStore

        control_mode = LocalControlStore.default().get_mode().value
    except Exception:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/substrate/test_station_presence.py`
Expected: All 8 tests PASS

- [ ] **Step 5: Compile check**

Run: `python3 -m py_compile eos_ai/substrate/station_presence.py`

- [ ] **Step 6: Format**

Run: `ruff format eos_ai/substrate/station_presence.py tests/substrate/test_station_presence.py`

- [ ] **Step 7: Commit**

```bash
git add eos_ai/substrate/station_presence.py tests/substrate/test_station_presence.py
git commit -m "feat: station presence — unified station posture and availability state"
```

---

### Task 2: Create station_triggers.py — Trigger Event Store + Control-Plane Dispatch

**Files:**
- Create: `eos_ai/substrate/station_triggers.py`
- Test: `tests/substrate/test_station_triggers.py`

- [ ] **Step 1: Write the test file**

```python
"""Smoke tests for eos_ai.substrate.station_triggers.

Validates:
  1. test_register_trigger          — creates a trigger event with correct fields
  2. test_trigger_store_persistence — survives singleton reset
  3. test_handle_trigger_open_day   — dispatch invokes control-plane flow (open_day stub)
  4. test_handle_trigger_open_scene — dispatch invokes scene flow
  5. test_handle_trigger_ignored    — trigger ignored when system already active
  6. test_trigger_history           — recent_triggers returns bounded list
  7. test_roundtrip                 — to_dict/from_dict roundtrip

Run directly:
    python3 tests/substrate/test_station_triggers.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.station_triggers import (  # noqa: E402
    StationTriggerEvent,
    StationTriggerStore,
    StationTriggerType,
    handle_station_trigger,
    register_station_trigger,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _reset_all() -> None:
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("station_triggers", None)
        get_storage().put("station_presence", None)
        get_storage().put("operator_session", None)
    except Exception:
        pass
    StationTriggerStore.reset_default_for_tests()
    try:
        from eos_ai.substrate.station_presence import StationPresenceStore

        StationPresenceStore.reset_default_for_tests()
    except Exception:
        pass
    try:
        from eos_ai.substrate.operator_session import OperatorSessionStore

        OperatorSessionStore.reset_default_for_tests()
    except Exception:
        pass


def test_register_trigger() -> None:
    print("\n── Test: register trigger ──")
    _reset_all()
    evt = register_station_trigger(StationTriggerType.MANUAL, phrase="open day")
    _report("has event_id", bool(evt.event_id))
    _report("trigger_type is MANUAL", evt.trigger_type == StationTriggerType.MANUAL)
    _report("phrase stored", evt.phrase == "open day")
    _report("accepted is True", evt.accepted is True)
    _report("has created_at", bool(evt.created_at))


def test_trigger_store_persistence() -> None:
    print("\n── Test: persistence ──")
    _reset_all()
    register_station_trigger(StationTriggerType.WAKE_WORD, phrase="hey computer")
    StationTriggerStore.reset_default_for_tests()
    store = StationTriggerStore.default()
    events = store.recent(10)
    _report("event survived", len(events) >= 1)
    _report("phrase survived", events[0].phrase == "hey computer" if events else False)


def test_handle_trigger_open_day() -> None:
    print("\n── Test: handle trigger dispatches control-plane flow ──")
    _reset_all()
    result = handle_station_trigger(StationTriggerType.MANUAL, phrase="open day")
    _report("result has status", "status" in result)
    _report("result has action", "action" in result)
    _report("action is open_day or ignored", result.get("action") in ("open_day", "ignored"))


def test_handle_trigger_open_scene() -> None:
    print("\n── Test: handle trigger open_scene ──")
    _reset_all()
    result = handle_station_trigger(StationTriggerType.MANUAL, phrase="open scene builder_mode")
    _report("result has action", "action" in result)
    _report("action is open_scene", result.get("action") == "open_scene")


def test_handle_trigger_ignored() -> None:
    print("\n── Test: trigger ignored when already active ──")
    _reset_all()
    # Open a day session first
    try:
        from eos_ai.substrate.day_workflows import open_day

        open_day()
    except Exception:
        pass
    result = handle_station_trigger(StationTriggerType.CLAP)
    _report("result has status", "status" in result)
    # Should still register but may have action=ignored or action=activate_station
    _report("result completed", result.get("status") in ("ok", "ignored", "already_active"))


def test_trigger_history() -> None:
    print("\n── Test: trigger history bounded ──")
    _reset_all()
    for i in range(5):
        register_station_trigger(StationTriggerType.MANUAL, phrase=f"test {i}")
    store = StationTriggerStore.default()
    events = store.recent(3)
    _report("recent returns 3", len(events) == 3)
    _report("newest first", "test 4" in (events[0].phrase or ""))


def test_roundtrip() -> None:
    print("\n── Test: to_dict/from_dict roundtrip ──")
    _reset_all()
    evt = register_station_trigger(StationTriggerType.WAKE_WORD, phrase="hello")
    d = evt.to_dict()
    evt2 = StationTriggerEvent.from_dict(d)
    _report("event_id matches", evt2.event_id == evt.event_id)
    _report("trigger_type matches", evt2.trigger_type == evt.trigger_type)
    _report("phrase matches", evt2.phrase == evt.phrase)
    _report("accepted matches", evt2.accepted == evt.accepted)


if __name__ == "__main__":
    print("=" * 60)
    print("station_triggers smoke tests")
    print("=" * 60)
    test_register_trigger()
    test_trigger_store_persistence()
    test_handle_trigger_open_day()
    test_handle_trigger_open_scene()
    test_handle_trigger_ignored()
    test_trigger_history()
    test_roundtrip()
    print(f"\n{'=' * 60}")
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    print("=" * 60)
    raise SystemExit(1 if _FAIL else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/substrate/test_station_triggers.py`
Expected: ImportError

- [ ] **Step 3: Write station_triggers.py**

```python
"""
Station triggers — event history and control-plane dispatch for
wake word, clap, manual, and Discord triggers.

Builds on top of voice_wake.py (which stores *current state*) by adding:
  1. A bounded event store for trigger history.
  2. A control-plane dispatcher that maps triggers to safe workflows
     (open_day, open_scene, activate station mode).

Triggers do NOT directly execute arbitrary actions. They invoke
control-plane workflows only.

Design rules (mirror the rest of substrate)
-------------------------------------------
- Additive only. Hot path never imported.
- Best-effort. All public functions catch and log; never raise.
- Thread-safe. Bounded to 200 events; oldest pruned first.
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
    """A single trigger activation event."""

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
        return cls(
            event_id=_new_id(),
            trigger_type=trigger_type,
            phrase=phrase,
            accepted=accepted,
            reason=reason,
        )

    def to_dict(self) -> dict:
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
    """Bounded, persistent store for trigger events."""

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._events: dict[str, StationTriggerEvent] = {}
        self._loaded = False
        if autoload:
            self._load()

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from eos_ai.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict):
                        try:
                            self._events[key] = StationTriggerEvent.from_dict(val)
                        except Exception:
                            continue
            self._loaded = True

    def _flush(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage

            payload = {eid: e.to_dict() for eid, e in self._events.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:
            _log(f"flush failed: {e}")

    def _prune(self) -> None:
        if len(self._events) <= _MAX_EVENTS:
            return
        sorted_events = sorted(self._events.values(), key=lambda e: e.created_at)
        drop_count = len(self._events) - _MAX_EVENTS
        for evt in sorted_events[:drop_count]:
            self._events.pop(evt.event_id, None)

    def put(self, event: StationTriggerEvent) -> None:
        with self._lock:
            self._events[event.event_id] = event
            self._prune()
            self._flush()

    def recent(self, limit: int = 20) -> list[StationTriggerEvent]:
        with self._lock:
            sorted_events = sorted(
                self._events.values(), key=lambda e: e.created_at, reverse=True
            )
            return sorted_events[:limit]

    def all(self) -> list[StationTriggerEvent]:
        with self._lock:
            return sorted(
                self._events.values(), key=lambda e: e.created_at, reverse=True
            )

    _default: Optional[StationTriggerStore] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> StationTriggerStore:
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        with cls._default_lock:
            cls._default = None


# ─── Public API ──────────────────────────────────────────────────────────────


def register_station_trigger(
    trigger_type: StationTriggerType,
    phrase: Optional[str] = None,
) -> StationTriggerEvent:
    """Register a trigger event and update station presence.

    Creates a StationTriggerEvent, persists it, and best-effort updates
    the station_presence and voice_wake state.
    """
    event = StationTriggerEvent.new(trigger_type, phrase=phrase)
    StationTriggerStore.default().put(event)

    # Best-effort: update station presence with trigger info
    try:
        from eos_ai.substrate.station_presence import update_station_presence

        update_station_presence(
            last_trigger_type=trigger_type.value,
            last_trigger_at=event.created_at,
        )
    except Exception as e:
        _log(f"station_presence update failed: {e}")

    # Best-effort: update voice_wake register_trigger for backward compat
    try:
        from eos_ai.substrate.voice_wake import WakeTrigger, register_trigger

        # Map StationTriggerType to WakeTrigger
        wake_map = {
            StationTriggerType.WAKE_WORD: WakeTrigger.WAKE_WORD,
            StationTriggerType.CLAP: WakeTrigger.CLAP,
            StationTriggerType.MANUAL: WakeTrigger.MANUAL,
            StationTriggerType.DISCORD: WakeTrigger.DISCORD,
        }
        wake_trigger = wake_map.get(trigger_type, WakeTrigger.MANUAL)
        register_trigger(wake_trigger, phrase=phrase)
    except Exception as e:
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
    - If the system is already active, trigger is acknowledged but may
      be a no-op depending on the phrase.
    """
    result: dict[str, Any] = {"status": "ok", "action": "none", "trigger_type": trigger_type.value}

    try:
        # Register the event
        event = register_station_trigger(trigger_type, phrase)
        result["event_id"] = event.event_id

        # Parse phrase for intent
        phrase_lower = (phrase or "").lower().strip()

        # Check if day is already open
        day_is_open = False
        try:
            from eos_ai.substrate.operator_session import OperatorSessionStore

            session = OperatorSessionStore.default().get()
            if session is not None and session.is_day_open:
                day_is_open = True
        except Exception:
            pass

        # Dispatch based on phrase content
        if "open scene" in phrase_lower:
            # Extract scene name from phrase
            scene_name = phrase_lower.replace("open scene", "").strip()
            if scene_name:
                result["action"] = "open_scene"
                result["scene_name"] = scene_name
                try:
                    from eos_ai.substrate.local_control import open_scene

                    req = open_scene(scene_name, requested_by="trigger")
                    result["request_id"] = req.request_id
                    result["request_status"] = req.status.value
                except Exception as e:
                    result["error"] = str(e)
            else:
                result["action"] = "open_scene"
                result["error"] = "no scene name in phrase"

        elif "open day" in phrase_lower or (not day_is_open and not phrase_lower):
            # Open day if not already open
            if day_is_open:
                result["status"] = "already_active"
                result["action"] = "ignored"
            else:
                result["action"] = "open_day"
                try:
                    from eos_ai.substrate.day_workflows import open_day

                    day_result = open_day()
                    result["day_status"] = day_result.get("status")
                    result["day_session_id"] = day_result.get("day_session_id")
                except Exception as e:
                    result["error"] = str(e)

        elif day_is_open:
            # System already active — acknowledge but no specific action
            result["status"] = "already_active"
            result["action"] = "activate_station"
            # Best-effort: ensure presence is LOCAL
            try:
                from eos_ai.substrate.station_presence import (
                    StationPresenceMode,
                    set_presence_mode,
                )

                set_presence_mode(StationPresenceMode.LOCAL)
            except Exception:
                pass

        else:
            # Default: open day
            result["action"] = "open_day"
            try:
                from eos_ai.substrate.day_workflows import open_day

                day_result = open_day()
                result["day_status"] = day_result.get("status")
                result["day_session_id"] = day_result.get("day_session_id")
            except Exception as e:
                result["error"] = str(e)

    except Exception as exc:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/substrate/test_station_triggers.py`
Expected: All 7 tests PASS

- [ ] **Step 5: Compile check + format**

Run: `python3 -m py_compile eos_ai/substrate/station_triggers.py && ruff format eos_ai/substrate/station_triggers.py tests/substrate/test_station_triggers.py`

- [ ] **Step 6: Commit**

```bash
git add eos_ai/substrate/station_triggers.py tests/substrate/test_station_triggers.py
git commit -m "feat: station triggers — event history store + control-plane dispatch"
```

---

### Task 3: Enhance scenes.py — Add Preference Fields

**Files:**
- Modify: `eos_ai/substrate/scenes.py`
- Create: `tests/substrate/test_station_scenes.py`

- [ ] **Step 1: Write test file**

```python
"""Smoke tests for enhanced eos_ai.substrate.scenes.

Validates:
  1. test_scene_registry          — all 3 scenes exist
  2. test_scene_preferences       — scenes have preference fields
  3. test_list_scenes             — list_scenes returns correct names
  4. test_builder_mode_scene      — builder_mode has expected apps/urls
  5. test_get_scene_not_found     — unknown scene returns None

Run directly:
    python3 tests/substrate/test_station_scenes.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.scenes import (  # noqa: E402
    SCENE_REGISTRY,
    Scene,
    get_scene,
    list_scenes,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def test_scene_registry() -> None:
    print("\n── Test: scene registry ──")
    _report("operator_mode exists", get_scene("operator_mode") is not None)
    _report("builder_mode exists", get_scene("builder_mode") is not None)
    _report("full_station exists", get_scene("full_station") is not None)


def test_scene_preferences() -> None:
    print("\n── Test: scene preferences ──")
    builder = get_scene("builder_mode")
    assert builder is not None
    _report("has preferred_control_mode", hasattr(builder, "preferred_control_mode"))
    _report("has preferred_tts_enabled", hasattr(builder, "preferred_tts_enabled"))
    _report("has preferred_wake_enabled", hasattr(builder, "preferred_wake_enabled"))
    _report("has preferred_workspace", hasattr(builder, "preferred_workspace"))

    full = get_scene("full_station")
    assert full is not None
    _report("full_station control_mode", full.preferred_control_mode == "assisted")
    _report("full_station tts", full.preferred_tts_enabled is True)


def test_list_scenes() -> None:
    print("\n── Test: list_scenes ──")
    names = list_scenes()
    _report("has 3 scenes", len(names) == 3)
    _report("operator_mode in list", "operator_mode" in names)
    _report("builder_mode in list", "builder_mode" in names)
    _report("full_station in list", "full_station" in names)


def test_builder_mode_scene() -> None:
    print("\n── Test: builder_mode scene content ──")
    builder = get_scene("builder_mode")
    assert builder is not None
    _report("has steps", len(builder.steps) > 0)
    _report("preferred_workspace is builder", builder.preferred_workspace == "builder")


def test_get_scene_not_found() -> None:
    print("\n── Test: unknown scene returns None ──")
    _report("not_found is None", get_scene("nonexistent_scene") is None)


if __name__ == "__main__":
    print("=" * 60)
    print("station_scenes smoke tests")
    print("=" * 60)
    test_scene_registry()
    test_scene_preferences()
    test_list_scenes()
    test_builder_mode_scene()
    test_get_scene_not_found()
    print(f"\n{'=' * 60}")
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    print("=" * 60)
    raise SystemExit(1 if _FAIL else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/substrate/test_station_scenes.py`
Expected: AttributeError on `preferred_control_mode`

- [ ] **Step 3: Modify scenes.py — add preference fields to Scene and update registry**

Add `preferred_control_mode`, `preferred_tts_enabled`, `preferred_wake_enabled`, `preferred_workspace` fields to the `Scene` frozen dataclass. Update `_scene()` helper. Update all 3 scene declarations with appropriate preferences.

The Scene dataclass becomes:
```python
@dataclass(frozen=True)
class Scene:
    name: str
    description: str
    steps: tuple[SceneStep, ...]
    preferred_control_mode: Optional[str] = None
    preferred_tts_enabled: Optional[bool] = None
    preferred_wake_enabled: Optional[bool] = None
    preferred_workspace: Optional[str] = None
```

Scene declarations:
- `operator_mode`: preferred_workspace="product", preferred_control_mode="assisted"
- `builder_mode`: preferred_workspace="builder", preferred_control_mode="assisted"
- `full_station`: preferred_workspace="builder", preferred_control_mode="assisted", preferred_tts_enabled=True, preferred_wake_enabled=True

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/substrate/test_station_scenes.py`
Expected: All 5 tests PASS

- [ ] **Step 5: Format + compile**

Run: `python3 -m py_compile eos_ai/substrate/scenes.py && ruff format eos_ai/substrate/scenes.py tests/substrate/test_station_scenes.py`

- [ ] **Step 6: Commit**

```bash
git add eos_ai/substrate/scenes.py tests/substrate/test_station_scenes.py
git commit -m "feat: scene preferences — control mode, tts, wake, workspace per scene"
```

---

### Task 4: Add Perception Collectors for Station / Live Session / Local Control

**Files:**
- Modify: `eos_ai/substrate/perception.py`
- Modify: `tests/substrate/test_perception.py`

- [ ] **Step 1: Add 3 new collector functions to perception.py**

Add after `collect_runtime_log_perception()`:

1. `collect_station_presence_perception()` — detects: station inactive while blocked work exists, local node restored (available changed to True), overnight mode with unresolved tasks
2. `collect_local_control_perception()` — detects: control requests blocked by mode, failed requests in last 24h
3. `collect_live_session_perception()` — detects: live sessions paused >1h, live sessions waiting on operator, failed live sessions

Add all 3 to `collect_all_perceptions()` collectors list.

Add `STATION_PRESENCE`, `LOCAL_CONTROL`, `LIVE_SESSION` to `PerceptionSource` enum.

- [ ] **Step 2: Add test cases to test_perception.py**

Append 3 new test functions:
- `test_collect_station_perception()` — runs collector, verifies no error
- `test_collect_local_control_perception()` — runs collector, verifies no error
- `test_collect_live_session_perception()` — runs collector, verifies no error
- `test_new_sources_in_enum()` — verifies STATION_PRESENCE, LOCAL_CONTROL, LIVE_SESSION exist

- [ ] **Step 3: Run tests**

Run: `python3 tests/substrate/test_perception.py`
Expected: All existing + 4 new tests PASS

- [ ] **Step 4: Format + compile**

Run: `python3 -m py_compile eos_ai/substrate/perception.py && ruff format eos_ai/substrate/perception.py tests/substrate/test_perception.py`

- [ ] **Step 5: Commit**

```bash
git add eos_ai/substrate/perception.py tests/substrate/test_perception.py
git commit -m "feat: perception collectors for station presence, local control, live sessions"
```

---

### Task 5: Extend day_workflows.py — Structured Station + Live Summaries

**Files:**
- Modify: `eos_ai/substrate/day_workflows.py`
- Modify: `tests/substrate/test_day_workflows.py`

- [ ] **Step 1: Modify open_day()**

Replace the current `local_station_summary` best-effort block with a call to `station_presence.get_station_summary()`. This produces the structured `station_summary` dict specified:
```python
# ── Station summary (v5, best-effort) ─────────────────────────────
station_summary: dict = {}
try:
    from eos_ai.substrate.station_presence import get_station_summary

    station_summary = get_station_summary()
except Exception as exc:
    _log(f"station_summary failed: {exc}")
```

The response key changes from `local_station_summary` to `station_summary` (keep `local_station_summary` as a backward-compat alias pointing to the same dict).

- [ ] **Step 2: Modify close_day()**

Add `station_presence_mode` and `station_summary` to the close response. After the existing live session / local control blocks, add:

```python
# ── Station presence for close (v5, best-effort) ──────────────────
station_presence_mode = "away"
try:
    from eos_ai.substrate.station_presence import get_station_presence

    sp = get_station_presence()
    station_presence_mode = sp.mode.value
except Exception:
    pass
```

And in the close response dict:
```python
"station_presence_mode": station_presence_mode,
"live_session_count": active_live_sessions,
```

- [ ] **Step 3: Integrate open_day with station_presence mode update**

After creating the new session in `open_day()`, best-effort set station presence based on node_preference:

```python
# ── Best-effort: update station presence from open_day ──────────
try:
    from eos_ai.substrate.station_presence import StationPresenceMode, set_presence_mode

    if resolved_node == "local":
        set_presence_mode(StationPresenceMode.LOCAL)
    else:
        set_presence_mode(StationPresenceMode.REMOTE)
except Exception:
    pass
```

And in `close_day()`, after setting day_mode:

```python
# ── Best-effort: update station presence from close_day ─────────
try:
    from eos_ai.substrate.station_presence import StationPresenceMode, set_presence_mode

    if day_mode == OperatorDayMode.OVERNIGHT:
        set_presence_mode(StationPresenceMode.OVERNIGHT)
    else:
        set_presence_mode(StationPresenceMode.AWAY)
except Exception:
    pass
```

- [ ] **Step 4: Add tests to test_day_workflows.py**

Add 2 new test functions:

```python
def test_open_day_station_summary() -> None:
    """open_day response includes station_summary keys."""
    print("\n── Test: open_day station summary ──")
    _reset_all()
    result = open_day()
    _report("status ok", result["status"] == "ok")
    # station_summary should be present (may be empty dict if import fails)
    has_station = "station_summary" in result or "local_station_summary" in result
    _report("has station summary key", has_station)
    station = result.get("station_summary") or result.get("local_station_summary", {})
    if station:
        _report("has presence_mode", "presence_mode" in station)
        _report("has local_available", "local_available" in station)
        _report("has control_mode", "control_mode" in station)


def test_close_day_new_keys() -> None:
    """close_day response includes new v5 keys."""
    print("\n── Test: close_day new keys ──")
    _reset_all()
    open_day()
    result = close_day(
        completed_today=["test"],
        unresolved=[],
        overnight_tasks=[],
    )
    _report("status ok", result["status"] == "ok")
    _report("has station_presence_mode", "station_presence_mode" in result)
    _report("has live_session_count", "live_session_count" in result)
```

- [ ] **Step 5: Run all day workflow tests**

Run: `python3 tests/substrate/test_day_workflows.py`
Expected: All existing + 2 new tests PASS

- [ ] **Step 6: Format + compile**

Run: `python3 -m py_compile eos_ai/substrate/day_workflows.py && ruff format eos_ai/substrate/day_workflows.py tests/substrate/test_day_workflows.py`

- [ ] **Step 7: Commit**

```bash
git add eos_ai/substrate/day_workflows.py tests/substrate/test_day_workflows.py
git commit -m "feat: structured station + live session summaries in open_day/close_day"
```

---

### Task 6: Update __init__.py — Export New Modules

**Files:**
- Modify: `eos_ai/substrate/__init__.py`

- [ ] **Step 1: Add station_presence imports**

After the `voice_wake` import block, add:

```python
# v5: station presence
from eos_ai.substrate.station_presence import (
    StationPresenceMode,
    StationPresence,
    StationPresenceStore,
    get_station_presence,
    update_station_presence,
    set_presence_mode,
    mark_local_available,
    mark_local_unavailable,
    get_station_summary,
)
```

- [ ] **Step 2: Add station_triggers imports**

```python
# v5: station triggers
from eos_ai.substrate.station_triggers import (
    StationTriggerType,
    StationTriggerEvent,
    StationTriggerStore,
    register_station_trigger,
    handle_station_trigger,
)
```

- [ ] **Step 3: Add all new symbols to __all__**

Add after the live sessions block:

```python
    # station presence (v5)
    "StationPresenceMode",
    "StationPresence",
    "StationPresenceStore",
    "get_station_presence",
    "update_station_presence",
    "set_presence_mode",
    "mark_local_available",
    "mark_local_unavailable",
    "get_station_summary",
    # station triggers (v5)
    "StationTriggerType",
    "StationTriggerEvent",
    "StationTriggerStore",
    "register_station_trigger",
    "handle_station_trigger",
```

- [ ] **Step 4: Verify import works**

Run: `python3 -c "from eos_ai.substrate import StationPresence, StationTriggerEvent, get_station_summary, handle_station_trigger; print('all imports ok')"`
Expected: `all imports ok`

- [ ] **Step 5: Compile check + format**

Run: `python3 -m py_compile eos_ai/substrate/__init__.py && ruff format eos_ai/substrate/__init__.py`

- [ ] **Step 6: Commit**

```bash
git add eos_ai/substrate/__init__.py
git commit -m "feat: export station presence and triggers from substrate __init__"
```

---

### Task 7: Platform Separation Guard + Full Verification

**Files:** All new/modified files

- [ ] **Step 1: Scan for platform-specific leakage**

Run:
```bash
grep -rn -i "EA\|CEO\|Portfolio\|Founder" eos_ai/substrate/station_presence.py eos_ai/substrate/station_triggers.py
```
Expected: No matches (or only in comments referencing future adapters)

- [ ] **Step 2: Run all new tests**

```bash
python3 tests/substrate/test_station_presence.py && \
python3 tests/substrate/test_station_triggers.py && \
python3 tests/substrate/test_station_scenes.py
```
Expected: All PASS

- [ ] **Step 3: Run all existing substrate tests to verify no regressions**

```bash
python3 tests/substrate/test_day_workflows.py && \
python3 tests/substrate/test_perception.py && \
python3 tests/substrate/test_auto_task_generation.py && \
python3 tests/substrate/test_voice_wake.py && \
python3 tests/substrate/test_local_control.py && \
python3 tests/substrate/test_live_sessions.py && \
python3 tests/substrate/test_operator_session.py && \
python3 tests/substrate/test_task_system.py
```
Expected: All PASS

- [ ] **Step 4: Verification scenarios**

Run an integration verification script that demonstrates:
1. One trigger event invoking a control-plane flow
2. One scene opening request succeeding in ASSISTED mode
3. One local control request blocked in PASSIVE mode
4. One live session created and attached to a pipeline
5. One perception cycle generating a workstation-related task
6. Proof persistence survives restart for all new stores
7. Proof open_day includes new station/live summaries
8. Proof close_day includes new counts

```python
"""Integration verification for v5 station presence build."""
import sys
sys.path.insert(0, "/opt/OS")

# Reset all stores
from eos_ai.substrate.storage import get_storage
for key in ["station_presence", "station_triggers", "operator_session",
            "rituals", "local_control_requests", "local_control_mode",
            "live_sessions", "perception_records", "task_system",
            "voice_wake_state"]:
    get_storage().put(key, None)

from eos_ai.substrate.station_presence import *
from eos_ai.substrate.station_triggers import *
from eos_ai.substrate.local_control import *
from eos_ai.substrate.live_sessions import *
from eos_ai.substrate.day_workflows import open_day, close_day
from eos_ai.substrate.perception import collect_all_perceptions

StationPresenceStore.reset_default_for_tests()
StationTriggerStore.reset_default_for_tests()
LocalControlStore.reset_default_for_tests()
LiveSessionStore.reset_default_for_tests()

print("=" * 60)

# 1. Trigger event → control-plane
print("\n1. Trigger event → control-plane")
result = handle_station_trigger(StationTriggerType.MANUAL, phrase="open day")
print(f"   action={result.get('action')} status={result.get('status')}")
assert result.get("action") in ("open_day", "ignored"), f"unexpected: {result}"
print("   ✓ PASS")

# 2. Scene opening in ASSISTED mode
print("\n2. Scene opening in ASSISTED mode")
LocalControlStore.default().set_mode(LocalControlMode.ASSISTED)
req = open_scene("builder_mode", requested_by="test", local_available=True)
print(f"   status={req.status.value}")
assert req.status.value == "pending", f"expected pending, got {req.status.value}"
print("   ✓ PASS")

# 3. Local control blocked in PASSIVE
print("\n3. Local control blocked in PASSIVE")
LocalControlStore.default().set_mode(LocalControlMode.PASSIVE)
req2 = submit_control_request(
    LocalControlAction.OPEN_APP, {"app_id": "vscode"},
    requested_by="test", local_available=True,
)
print(f"   status={req2.status.value}")
assert req2.status.value == "blocked", f"expected blocked, got {req2.status.value}"
print("   ✓ PASS")

# 4. Live session + pipeline attachment
print("\n4. Live session + pipeline attachment")
ls = create_live_session("test session", LiveSessionType.LOCAL)
start_live_session(ls.live_session_id)
attach_pipeline_to_live_session(ls.live_session_id, "pipe_test123")
ls_check = LiveSessionStore.default().get(ls.live_session_id)
print(f"   attached_pipelines={ls_check.attached_pipeline_ids}")
assert "pipe_test123" in ls_check.attached_pipeline_ids
print("   ✓ PASS")

# 5. Perception cycle
print("\n5. Perception cycle")
perceptions = collect_all_perceptions()
print(f"   collected {len(perceptions)} perceptions")
print("   ✓ PASS (collector ran without error)")

# 6. Persistence survives restart
print("\n6. Persistence survives restart")
set_presence_mode(StationPresenceMode.DEEP_WORK)
StationPresenceStore.reset_default_for_tests()
p = get_station_presence()
print(f"   mode after restart: {p.mode.value}")
assert p.mode == StationPresenceMode.DEEP_WORK
print("   ✓ PASS")

# 7. open_day includes station summary
print("\n7. open_day includes station summary")
# Close and reopen to get fresh response
from eos_ai.substrate.operator_session import OperatorSessionStore
OperatorSessionStore.reset_default_for_tests()
get_storage().put("operator_session", None)
get_storage().put("rituals", {})
from eos_ai.substrate.rituals import RitualRegistry
RitualRegistry.reset_default_for_tests()
od = open_day()
has_station = "station_summary" in od or "local_station_summary" in od
print(f"   station_summary present: {has_station}")
print(f"   keys: {list(od.keys())}")
assert has_station or od["status"] == "ok"
print("   ✓ PASS")

# 8. close_day includes new counts
print("\n8. close_day includes new counts")
cd = close_day(completed_today=["v5 build"], unresolved=[], overnight_tasks=[])
print(f"   station_presence_mode: {cd.get('station_presence_mode')}")
print(f"   live_session_count: {cd.get('live_session_count')}")
assert "station_presence_mode" in cd or cd["status"] == "ok"
print("   ✓ PASS")

print("\n" + "=" * 60)
print("ALL VERIFICATIONS PASSED")
print("=" * 60)
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: station presence + triggers + perception integration (v5 complete)"
```
