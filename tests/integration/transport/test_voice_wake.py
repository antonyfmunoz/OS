"""Smoke tests for eos_ai.substrate.voice_wake.

Validates:
  1.  test_default_state          — fresh state has expected defaults
  2.  test_enable_wake            — enable_wake sets correct fields
  3.  test_disable_wake           — disable_wake sets correct fields
  4.  test_enable_disable_clap    — clap enable/disable toggles correctly
  5.  test_register_trigger       — trigger registration updates state
  6.  test_tts_toggle             — enable/disable TTS
  7.  test_persistence            — state survives singleton reset
  8.  test_wake_summary           — get_voice_wake_summary returns expected keys
  9.  test_mode_transitions       — station_mode changes correctly through enable/disable/trigger
 10.  test_adapters               — stub adapters return safe defaults

Run directly:
    python3 tests/substrate/test_voice_wake.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.voice_wake import (  # noqa: E402
    ClapAdapter,
    StationMode,
    VoiceWakeState,
    VoiceWakeStore,
    WakeTrigger,
    WakeWordAdapter,
    disable_clap,
    disable_tts,
    disable_wake,
    enable_clap,
    enable_tts,
    enable_wake,
    get_voice_wake_summary,
    register_trigger,
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

        get_storage().put("voice_wake_state", None)
    except Exception:  # noqa: BLE001
        pass
    VoiceWakeStore.reset_default_for_tests()


# ─── Test 1: default state ─────────────────────────────────────────────────


def test_default_state() -> None:
    print("\n── Test 1: default state ──")

    _reset_all()

    state = VoiceWakeStore.default().get()

    _report(
        "wake_enabled is False",
        state.wake_enabled is False,
        f"got {state.wake_enabled!r}",
    )
    _report(
        "clap_enabled is False",
        state.clap_enabled is False,
        f"got {state.clap_enabled!r}",
    )
    _report(
        "tts_enabled is False",
        state.tts_enabled is False,
        f"got {state.tts_enabled!r}",
    )
    _report(
        "station_mode is INACTIVE",
        state.station_mode == StationMode.INACTIVE,
        f"got {state.station_mode!r}",
    )


# ─── Test 2: enable wake ───────────────────────────────────────────────────


def test_enable_wake() -> None:
    print("\n── Test 2: enable wake ──")

    _reset_all()

    state = enable_wake()

    _report(
        "wake_enabled is True",
        state.wake_enabled is True,
        f"got {state.wake_enabled!r}",
    )
    _report(
        "is_listening is True",
        state.is_listening is True,
        f"got {state.is_listening!r}",
    )
    _report(
        "station_mode is LISTENING",
        state.station_mode == StationMode.LISTENING,
        f"got {state.station_mode!r}",
    )


# ─── Test 3: disable wake ──────────────────────────────────────────────────


def test_disable_wake() -> None:
    print("\n── Test 3: disable wake ──")

    _reset_all()

    enable_wake()
    state = disable_wake()

    _report(
        "wake_enabled is False",
        state.wake_enabled is False,
        f"got {state.wake_enabled!r}",
    )
    _report(
        "station_mode is INACTIVE",
        state.station_mode == StationMode.INACTIVE,
        f"got {state.station_mode!r}",
    )


# ─── Test 4: enable/disable clap ───────────────────────────────────────────


def test_enable_disable_clap() -> None:
    print("\n── Test 4: enable/disable clap ──")

    _reset_all()

    # Enable clap alone
    state = enable_clap()
    _report(
        "clap_enabled is True",
        state.clap_enabled is True,
        f"got {state.clap_enabled!r}",
    )

    # Enable wake, then disable clap — mode stays LISTENING (wake still on)
    enable_wake()
    state = disable_clap()
    _report(
        "clap_enabled is False after disable",
        state.clap_enabled is False,
        f"got {state.clap_enabled!r}",
    )
    _report(
        "station_mode stays LISTENING (wake still enabled)",
        state.station_mode == StationMode.LISTENING,
        f"got {state.station_mode!r}",
    )


# ─── Test 5: register trigger ──────────────────────────────────────────────


def test_register_trigger() -> None:
    print("\n── Test 5: register trigger ──")

    _reset_all()

    state = register_trigger(WakeTrigger.MANUAL, phrase="hey os")

    _report(
        "last_trigger is MANUAL",
        state.last_trigger == WakeTrigger.MANUAL,
        f"got {state.last_trigger!r}",
    )
    _report(
        "last_phrase is 'hey os'",
        state.last_phrase == "hey os",
        f"got {state.last_phrase!r}",
    )
    _report(
        "station_mode is ACTIVE",
        state.station_mode == StationMode.ACTIVE,
        f"got {state.station_mode!r}",
    )
    _report(
        "last_trigger_at is not None",
        state.last_trigger_at is not None,
        f"got {state.last_trigger_at!r}",
    )


# ─── Test 6: TTS toggle ────────────────────────────────────────────────────


def test_tts_toggle() -> None:
    print("\n── Test 6: TTS toggle ──")

    _reset_all()

    state = enable_tts()
    _report(
        "tts_enabled is True after enable",
        state.tts_enabled is True,
        f"got {state.tts_enabled!r}",
    )

    state = disable_tts()
    _report(
        "tts_enabled is False after disable",
        state.tts_enabled is False,
        f"got {state.tts_enabled!r}",
    )


# ─── Test 7: persistence ───────────────────────────────────────────────────


def test_persistence() -> None:
    print("\n── Test 7: persistence (state survives singleton reset) ──")

    _reset_all()

    enable_wake()

    # Reset singleton only (not storage) — state should reload from storage
    VoiceWakeStore.reset_default_for_tests()

    state = VoiceWakeStore.default().get()
    _report(
        "wake_enabled persisted as True",
        state.wake_enabled is True,
        f"got {state.wake_enabled!r}",
    )


# ─── Test 8: wake summary ──────────────────────────────────────────────────


def test_wake_summary() -> None:
    print("\n── Test 8: wake summary ──")

    _reset_all()

    summary = get_voice_wake_summary()

    expected_keys = {
        "wake_enabled",
        "clap_enabled",
        "tts_enabled",
        "station_mode",
        "last_trigger",
        "last_trigger_at",
    }
    _report(
        "summary has expected keys",
        set(summary.keys()) == expected_keys,
        f"got {set(summary.keys())!r}",
    )
    _report(
        "summary is a dict",
        isinstance(summary, dict),
        f"got {type(summary).__name__}",
    )


# ─── Test 9: mode transitions ──────────────────────────────────────────────


def test_mode_transitions() -> None:
    print("\n── Test 9: mode transitions ──")

    _reset_all()

    # Start INACTIVE
    state = VoiceWakeStore.default().get()
    _report(
        "starts INACTIVE",
        state.station_mode == StationMode.INACTIVE,
        f"got {state.station_mode!r}",
    )

    # enable_wake → LISTENING
    state = enable_wake()
    _report(
        "enable_wake → LISTENING",
        state.station_mode == StationMode.LISTENING,
        f"got {state.station_mode!r}",
    )

    # register_trigger → ACTIVE
    state = register_trigger(WakeTrigger.WAKE_WORD, phrase="hey os")
    _report(
        "register_trigger → ACTIVE",
        state.station_mode == StationMode.ACTIVE,
        f"got {state.station_mode!r}",
    )

    # disable_wake → INACTIVE (clap not enabled)
    state = disable_wake()
    _report(
        "disable_wake → INACTIVE",
        state.station_mode == StationMode.INACTIVE,
        f"got {state.station_mode!r}",
    )


# ─── Test 10: adapters ─────────────────────────────────────────────────────


def test_adapters() -> None:
    print("\n── Test 10: stub adapters ──")

    wake_result = WakeWordAdapter().detect(b"audio")
    _report(
        "WakeWordAdapter returns (False, None)",
        wake_result == (False, None),
        f"got {wake_result!r}",
    )

    clap_result = ClapAdapter().detect(b"audio")
    _report(
        "ClapAdapter returns False",
        clap_result is False,
        f"got {clap_result!r}",
    )


# ─── Runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("voice_wake smoke tests")
    print("=" * 60)

    test_default_state()
    test_enable_wake()
    test_disable_wake()
    test_enable_disable_clap()
    test_register_trigger()
    test_tts_toggle()
    test_persistence()
    test_wake_summary()
    test_mode_transitions()
    test_adapters()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    print("=" * 60)

    raise SystemExit(_FAIL)
