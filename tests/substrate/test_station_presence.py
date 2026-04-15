"""Smoke tests for eos_ai.substrate.station_presence.

Validates:
  1.  test_default_state           — fresh presence has expected defaults
  2.  test_set_presence_mode       — mode changes correctly
  3.  test_mark_local_available    — local_available toggles
  4.  test_mark_local_unavailable  — local_available goes False
  5.  test_update_station_presence — partial update preserves other fields
  6.  test_persistence             — survives singleton reset
  7.  test_get_station_summary     — summary returns expected keys
  8.  test_roundtrip               — to_dict/from_dict roundtrip

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
    """Reset singleton and underlying storage so each test starts clean."""
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("station_presence", None)
    except Exception:  # noqa: BLE001
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
