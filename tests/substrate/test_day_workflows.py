"""Smoke tests for eos_ai.substrate.day_workflows.

Validates:
  1. test_open_day_fresh        — first open_day with no prior session returns ok + empty briefing
  2. test_already_open          — calling open_day when already open returns already_open
  3. test_close_day             — close_day updates session, returns summary with active_workspace and node_preference
  4. test_not_open              — close_day with no open session returns not_open
  5. test_continuity_carries_forward — after close + open, new briefing contains prior continuity
  6. test_restart_safe          — session spine survives singleton reset
  7. test_ritual_created        — both workflows create rituals in RitualRegistry, all COMPLETED

Run directly:
    python3 tests/substrate/test_day_workflows.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.day_workflows import close_day, open_day  # noqa: E402
from eos_ai.substrate.operator_session import (  # noqa: E402
    OperatorDayMode,
    OperatorSessionStore,
)
from eos_ai.substrate.rituals import RitualRegistry, RitualState  # noqa: E402

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
    """Reset both OperatorSessionStore and RitualRegistry singletons.

    Also clears the underlying storage key so the next singleton creation
    starts with a blank slate — not a session left open by a prior test.
    """
    # Clear session storage before tearing down singletons so the next
    # OperatorSessionStore.default() does not reload a stale open session.
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("operator_session", None)
        get_storage().put("rituals", {})
    except Exception:  # noqa: BLE001
        pass
    OperatorSessionStore.reset_default_for_tests()
    RitualRegistry.reset_default_for_tests()


# ─── Test 1: open_day fresh ─────────────────────────────────────────────────


def test_open_day_fresh() -> None:
    print("\n── Test 1: open_day fresh (no prior session) ──")

    _reset_all()

    result = open_day(
        workspace="builder",
        node_preference="local",
        discord_channel_id=None,
    )

    _report(
        "status is ok", result.get("status") == "ok", f"got {result.get('status')!r}"
    )
    _report(
        "day_session_id present",
        isinstance(result.get("day_session_id"), str)
        and result["day_session_id"].startswith("ds_"),
        f"got {result.get('day_session_id')!r}",
    )
    _report(
        "briefing key present",
        "briefing" in result,
        f"keys: {list(result.keys())}",
    )
    briefing = result.get("briefing", {})
    _report(
        "briefing.where_we_left_off is None (no prior session)",
        briefing.get("where_we_left_off") is None,
        f"got {briefing.get('where_we_left_off')!r}",
    )
    _report(
        "briefing.unfinished_priorities is empty list",
        briefing.get("unfinished_priorities") == [],
        f"got {briefing.get('unfinished_priorities')!r}",
    )
    _report(
        "briefing.overnight_tasks is empty list",
        briefing.get("overnight_tasks") == [],
        f"got {briefing.get('overnight_tasks')!r}",
    )
    _report(
        "briefing.recommended_first_action is None",
        briefing.get("recommended_first_action") is None,
        f"got {briefing.get('recommended_first_action')!r}",
    )
    _report(
        "day_mode is local_active (node_preference=local)",
        result.get("day_mode") == OperatorDayMode.LOCAL_ACTIVE.value,
        f"got {result.get('day_mode')!r}",
    )
    _report(
        "active_workspace is builder",
        result.get("active_workspace") == "builder",
        f"got {result.get('active_workspace')!r}",
    )
    _report("opened_at is set", result.get("opened_at") is not None)


# ─── Test 2: already open ────────────────────────────────────────────────────


def test_already_open() -> None:
    print("\n── Test 2: open_day when already open returns already_open ──")

    _reset_all()

    # First open
    first = open_day(
        workspace="builder", node_preference="local", discord_channel_id=None
    )
    first_id = first.get("day_session_id")

    # Second open — should be idempotent
    result = open_day(
        workspace="builder", node_preference="local", discord_channel_id=None
    )

    _report(
        "status is already_open",
        result.get("status") == "already_open",
        f"got {result.get('status')!r}",
    )
    _report(
        "day_session_id unchanged",
        result.get("day_session_id") == first_id,
        f"first={first_id!r}, got={result.get('day_session_id')!r}",
    )
    _report("day_mode present", "day_mode" in result)
    _report("active_workspace present", "active_workspace" in result)
    _report("opened_at present", "opened_at" in result)


# ─── Test 3: close_day ───────────────────────────────────────────────────────


def test_close_day() -> None:
    print("\n── Test 3: close_day updates session ──")

    _reset_all()

    open_day(workspace="builder", node_preference="auto", discord_channel_id="ch_abc")

    result = close_day(
        completed_today=["wrote tests", "shipped day_workflows"],
        unresolved=["update wiki"],
        overnight_tasks=["graph rebuild"],
        continuity_notes="Resume wiki update tomorrow.",
        resume_context="Task 2 complete.",
        discord_channel_id="ch_abc",
    )

    _report(
        "status is ok", result.get("status") == "ok", f"got {result.get('status')!r}"
    )
    _report(
        "day_session_id present",
        isinstance(result.get("day_session_id"), str)
        and result["day_session_id"].startswith("ds_"),
    )
    _report("closed_at present", result.get("closed_at") is not None)
    summary = result.get("summary", {})
    _report(
        "summary.completed_today matches",
        summary.get("completed_today") == ["wrote tests", "shipped day_workflows"],
        f"got {summary.get('completed_today')!r}",
    )
    _report(
        "summary.unresolved matches",
        summary.get("unresolved") == ["update wiki"],
        f"got {summary.get('unresolved')!r}",
    )
    _report(
        "summary.overnight_tasks matches",
        summary.get("overnight_tasks") == ["graph rebuild"],
        f"got {summary.get('overnight_tasks')!r}",
    )
    _report(
        "summary.day_mode is overnight (overnight_tasks present)",
        summary.get("day_mode") == OperatorDayMode.OVERNIGHT.value,
        f"got {summary.get('day_mode')!r}",
    )
    _report(
        "summary.active_workspace present for observability",
        "active_workspace" in summary,
        f"keys: {list(summary.keys())}",
    )
    _report(
        "summary.node_preference present for observability",
        "node_preference" in summary,
        f"keys: {list(summary.keys())}",
    )

    # Confirm session is now closed
    session = OperatorSessionStore.default().get()
    _report(
        "session is_day_open is False after close",
        session is not None and session.is_day_open is False,
        f"got {session.is_day_open if session else 'None'}",
    )


# ─── Test 4: not open ───────────────────────────────────────────────────────


def test_not_open() -> None:
    print("\n── Test 4: close_day with no open session returns not_open ──")

    _reset_all()

    result = close_day(
        completed_today=[],
        unresolved=[],
        overnight_tasks=[],
        continuity_notes=None,
        resume_context=None,
        discord_channel_id=None,
    )

    _report(
        "status is not_open",
        result.get("status") == "not_open",
        f"got {result.get('status')!r}",
    )


# ─── Test 5: continuity carries forward ─────────────────────────────────────


def test_continuity_carries_forward() -> None:
    print("\n── Test 5: continuity carries forward after close + open ──")

    _reset_all()

    # Open day 1
    open_day(workspace="builder", node_preference="local", discord_channel_id=None)

    # Close with continuity
    close_day(
        completed_today=["shipped substrate"],
        unresolved=["write wiki", "update graph"],
        overnight_tasks=["neon sync"],
        continuity_notes="Left off at day_workflows implementation.",
        resume_context="Task 2 in progress.",
        discord_channel_id=None,
    )

    # Open day 2 — should inherit prior continuity
    result = open_day(
        workspace="builder", node_preference="vps", discord_channel_id=None
    )

    briefing = result.get("briefing", {})

    _report(
        "status is ok", result.get("status") == "ok", f"got {result.get('status')!r}"
    )
    _report(
        "where_we_left_off carries forward",
        briefing.get("where_we_left_off")
        == "Left off at day_workflows implementation.",
        f"got {briefing.get('where_we_left_off')!r}",
    )
    _report(
        "unfinished_priorities carries forward",
        briefing.get("unfinished_priorities") == ["write wiki", "update graph"],
        f"got {briefing.get('unfinished_priorities')!r}",
    )
    _report(
        "overnight_tasks carries forward",
        briefing.get("overnight_tasks") == ["neon sync"],
        f"got {briefing.get('overnight_tasks')!r}",
    )
    _report(
        "recommended_first_action is first unfinished priority",
        briefing.get("recommended_first_action") == "write wiki",
        f"got {briefing.get('recommended_first_action')!r}",
    )
    _report(
        "resume_context carries forward",
        briefing.get("resume_context") == "Task 2 in progress.",
        f"got {briefing.get('resume_context')!r}",
    )
    # New day session — different ID from prior
    _report(
        "new day_session_id created",
        result.get("day_session_id") is not None,
    )


# ─── Test 6: restart safe ────────────────────────────────────────────────────


def test_restart_safe() -> None:
    print("\n── Test 6: session spine survives singleton reset ──")

    _reset_all()

    open_result = open_day(
        workspace="builder", node_preference="local", discord_channel_id=None
    )
    original_id = open_result.get("day_session_id")

    # Reset singletons (simulate process restart)
    OperatorSessionStore.reset_default_for_tests()

    # Reload — storage should still hold the session
    reloaded = OperatorSessionStore.default().get()

    _report(
        "session reloads after singleton reset",
        reloaded is not None,
        "got None" if reloaded is None else "",
    )
    if reloaded is not None:
        _report(
            "day_session_id survives reset",
            reloaded.day_session_id == original_id,
            f"expected {original_id!r}, got {reloaded.day_session_id!r}",
        )
        _report(
            "is_day_open survives reset",
            reloaded.is_day_open is True,
            f"got {reloaded.is_day_open!r}",
        )


# ─── Test 7: rituals created ─────────────────────────────────────────────────


def test_ritual_created() -> None:
    print("\n── Test 7: both workflows create rituals in RitualRegistry ──")

    _reset_all()

    open_result = open_day(
        workspace="builder", node_preference="local", discord_channel_id=None
    )
    open_ritual_id = open_result.get("ritual_id")

    close_result = close_day(
        completed_today=["test"],
        unresolved=[],
        overnight_tasks=[],
        continuity_notes=None,
        resume_context=None,
        discord_channel_id=None,
    )
    close_ritual_id = close_result.get("ritual_id")

    registry = RitualRegistry.default()
    history = registry.history()

    _report(
        "open_day ritual_id is returned",
        open_ritual_id is not None,
        f"got {open_ritual_id!r}",
    )
    _report(
        "close_day ritual_id is returned",
        close_ritual_id is not None,
        f"got {close_ritual_id!r}",
    )
    _report(
        "at least 2 rituals in history",
        len(history) >= 2,
        f"got {len(history)}",
    )

    if open_ritual_id:
        open_ritual = registry.get(open_ritual_id)
        _report(
            "open_day ritual state is COMPLETED",
            open_ritual is not None and open_ritual.state == RitualState.COMPLETED,
            f"got {open_ritual.state if open_ritual else 'None'}",
        )

    if close_ritual_id:
        close_ritual = registry.get(close_ritual_id)
        _report(
            "close_day ritual state is COMPLETED",
            close_ritual is not None and close_ritual.state == RitualState.COMPLETED,
            f"got {close_ritual.state if close_ritual else 'None'}",
        )


# ─── Test 8: open_day station summary ──────────────────────────────────────


def test_open_day_station_summary() -> None:
    print("\n── Test 8: open_day station summary ──")
    _reset_all()
    # Also reset station_presence
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("station_presence", None)
    except Exception:  # noqa: BLE001
        pass
    try:
        from eos_ai.substrate.station_presence import StationPresenceStore

        StationPresenceStore.reset_default_for_tests()
    except Exception:  # noqa: BLE001
        pass

    result = open_day(workspace="builder", node_preference="local")
    _report("status ok", result["status"] == "ok")
    has_station = "station_summary" in result or "local_station_summary" in result
    _report("has station summary key", has_station)
    station = result.get("station_summary") or result.get("local_station_summary", {})
    if station:
        _report("has presence_mode", "presence_mode" in station)
        _report("has local_available", "local_available" in station)
        _report("has control_mode", "control_mode" in station)
        _report("has wake_enabled", "wake_enabled" in station)
        _report("has tts_enabled", "tts_enabled" in station)


# ─── Test 9: close_day new keys ───────────────────────────────────────────


def test_close_day_new_keys() -> None:
    print("\n── Test 9: close_day new keys ──")
    _reset_all()
    # Also reset station_presence
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("station_presence", None)
    except Exception:  # noqa: BLE001
        pass
    try:
        from eos_ai.substrate.station_presence import StationPresenceStore

        StationPresenceStore.reset_default_for_tests()
    except Exception:  # noqa: BLE001
        pass

    open_day()
    result = close_day(
        completed_today=["test"],
        unresolved=[],
        overnight_tasks=[],
    )
    _report("status ok", result["status"] == "ok")
    _report("has station_presence_mode", "station_presence_mode" in result)
    _report("has live_session_count", "live_session_count" in result)
    _report(
        "station_presence_mode is away (no overnight tasks)",
        result.get("station_presence_mode") == "away",
        f"got {result.get('station_presence_mode')!r}",
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Day Workflows Smoke Tests")
    print("=" * 60)

    test_open_day_fresh()
    test_already_open()
    test_close_day()
    test_not_open()
    test_continuity_carries_forward()
    test_restart_safe()
    test_ritual_created()
    test_open_day_station_summary()
    test_close_day_new_keys()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
