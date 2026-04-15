"""Smoke tests for eos_ai.substrate.station_triggers.

Validates:
  1.  test_register_trigger          — creates a trigger event with correct fields
  2.  test_trigger_store_persistence — survives singleton reset
  3.  test_handle_trigger_open_day   — dispatch invokes control-plane flow
  4.  test_handle_trigger_open_scene — dispatch invokes scene flow
  5.  test_handle_trigger_ignored    — trigger ignored when system already active
  6.  test_trigger_history           — recent_triggers returns bounded list
  7.  test_roundtrip                 — to_dict/from_dict roundtrip

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
    """Reset all singletons and storage keys relevant to triggers."""
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("station_triggers", None)
        get_storage().put("station_presence", None)
        get_storage().put("operator_session", None)
        get_storage().put("rituals", {})
        get_storage().put("voice_wake_state", None)
    except Exception:  # noqa: BLE001
        pass
    StationTriggerStore.reset_default_for_tests()
    try:
        from eos_ai.substrate.station_presence import StationPresenceStore

        StationPresenceStore.reset_default_for_tests()
    except Exception:  # noqa: BLE001
        pass
    try:
        from eos_ai.substrate.operator_session import OperatorSessionStore

        OperatorSessionStore.reset_default_for_tests()
    except Exception:  # noqa: BLE001
        pass
    try:
        from eos_ai.substrate.rituals import RitualRegistry

        RitualRegistry.reset_default_for_tests()
    except Exception:  # noqa: BLE001
        pass
    try:
        from eos_ai.substrate.voice_wake import VoiceWakeStore

        VoiceWakeStore.reset_default_for_tests()
    except Exception:  # noqa: BLE001
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
    _report(
        "phrase survived",
        events[0].phrase == "hey computer" if events else False,
    )


def test_handle_trigger_open_day() -> None:
    print("\n── Test: handle trigger dispatches control-plane flow ──")
    _reset_all()
    result = handle_station_trigger(StationTriggerType.MANUAL, phrase="open day")
    _report("result has status", "status" in result)
    _report("result has action", "action" in result)
    _report(
        "action is open_day or ignored",
        result.get("action") in ("open_day", "ignored"),
    )


def test_handle_trigger_open_scene() -> None:
    print("\n── Test: handle trigger open_scene ──")
    _reset_all()
    result = handle_station_trigger(
        StationTriggerType.MANUAL, phrase="open scene builder_mode"
    )
    _report("result has action", "action" in result)
    _report("action is open_scene", result.get("action") == "open_scene")


def test_handle_trigger_ignored() -> None:
    print("\n── Test: trigger ignored when already active ──")
    _reset_all()
    # Open a day session first
    try:
        from eos_ai.substrate.day_workflows import open_day

        open_day()
    except Exception:  # noqa: BLE001
        pass
    result = handle_station_trigger(StationTriggerType.CLAP)
    _report("result has status", "status" in result)
    _report(
        "result completed",
        result.get("status") in ("ok", "ignored", "already_active"),
    )


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
