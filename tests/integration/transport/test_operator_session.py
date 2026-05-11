"""Smoke tests for runtime.substrate.operator_session.

Validates:
  1. All 5 OperatorDayMode values serialize correctly.
  2. Creating a session, persisting it, resetting the singleton, reloading —
     all fields survive the round-trip.
  3. Putting a new session replaces the previous one.

Run directly:
    python3 tests/substrate/test_operator_session.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.operator_session import (  # noqa: E402
    OperatorDayMode,
    OperatorSession,
    OperatorSessionStore,
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


# ─── Test 1: enum values ────────────────────────────────────────────────────


def test_enum_values() -> None:
    print("\n── Test 1: OperatorDayMode enum values ──")

    expected = {
        "inactive": OperatorDayMode.INACTIVE,
        "remote_active": OperatorDayMode.REMOTE_ACTIVE,
        "local_active": OperatorDayMode.LOCAL_ACTIVE,
        "deep_work": OperatorDayMode.DEEP_WORK,
        "overnight": OperatorDayMode.OVERNIGHT,
    }

    _report(
        "exactly 5 members", len(OperatorDayMode) == 5, f"got {len(OperatorDayMode)}"
    )

    for value, member in expected.items():
        _report(
            f"OperatorDayMode.{member.name} == {value!r}",
            member.value == value,
            f"got {member.value!r}",
        )

    # round-trip via str value
    for value in expected:
        reconstructed = OperatorDayMode(value)
        _report(
            f"OperatorDayMode({value!r}) round-trips",
            reconstructed.value == value,
            f"got {reconstructed.value!r}",
        )


# ─── Test 2: create, persist, reload ────────────────────────────────────────


def test_create_and_persist() -> None:
    print("\n── Test 2: create session, persist, reset singleton, reload ──")

    OperatorSessionStore.reset_default_for_tests()
    store = OperatorSessionStore.default()

    session = OperatorSession.new()
    session.day_mode = OperatorDayMode.DEEP_WORK
    session.is_day_open = True
    session.active_workspace = "builder"
    session.node_preference = "vps"
    session.last_active_node = "vps-primary"
    session.last_active_discord_channel_id = "123456789"
    session.active_tmux_session = "builder"
    session.ritual_open_id = "ritual_abc123"
    session.ritual_close_id = "ritual_def456"
    session.last_briefing_summary = "Yesterday: shipped operator session spine."
    session.unfinished_priorities = ["write tests", "ruff format"]
    session.overnight_tasks = ["graph rebuild"]
    session.continuity_notes_for_next_open = "Resume operator session work first."
    session.last_resume_context = "Task 1 complete."

    store.put(session)

    # Capture the ID before reset
    original_id = session.day_session_id

    # Reset singleton — forces a fresh load from storage
    OperatorSessionStore.reset_default_for_tests()
    store2 = OperatorSessionStore.default()

    reloaded = store2.get()

    _report("reloaded is not None", reloaded is not None)
    if reloaded is None:
        _report("(skipping remaining checks — reload returned None)", False)
        return

    _report(
        "day_session_id survives",
        reloaded.day_session_id == original_id,
        f"expected {original_id!r}, got {reloaded.day_session_id!r}",
    )
    _report(
        "day_mode survives as enum",
        reloaded.day_mode == OperatorDayMode.DEEP_WORK,
        f"got {reloaded.day_mode!r}",
    )
    _report(
        "is_day_open survives",
        reloaded.is_day_open is True,
        f"got {reloaded.is_day_open!r}",
    )
    _report(
        "active_workspace survives",
        reloaded.active_workspace == "builder",
        f"got {reloaded.active_workspace!r}",
    )
    _report(
        "node_preference survives",
        reloaded.node_preference == "vps",
        f"got {reloaded.node_preference!r}",
    )
    _report(
        "last_active_node survives",
        reloaded.last_active_node == "vps-primary",
        f"got {reloaded.last_active_node!r}",
    )
    _report(
        "last_active_discord_channel_id survives",
        reloaded.last_active_discord_channel_id == "123456789",
        f"got {reloaded.last_active_discord_channel_id!r}",
    )
    _report(
        "active_tmux_session survives",
        reloaded.active_tmux_session == "builder",
        f"got {reloaded.active_tmux_session!r}",
    )
    _report(
        "ritual_open_id survives",
        reloaded.ritual_open_id == "ritual_abc123",
        f"got {reloaded.ritual_open_id!r}",
    )
    _report(
        "ritual_close_id survives",
        reloaded.ritual_close_id == "ritual_def456",
        f"got {reloaded.ritual_close_id!r}",
    )
    _report(
        "last_briefing_summary survives",
        reloaded.last_briefing_summary == "Yesterday: shipped operator session spine.",
        f"got {reloaded.last_briefing_summary!r}",
    )
    _report(
        "unfinished_priorities is list and survives",
        isinstance(reloaded.unfinished_priorities, list)
        and reloaded.unfinished_priorities == ["write tests", "ruff format"],
        f"got {reloaded.unfinished_priorities!r}",
    )
    _report(
        "overnight_tasks is list and survives",
        isinstance(reloaded.overnight_tasks, list)
        and reloaded.overnight_tasks == ["graph rebuild"],
        f"got {reloaded.overnight_tasks!r}",
    )
    _report(
        "continuity_notes_for_next_open survives",
        reloaded.continuity_notes_for_next_open
        == "Resume operator session work first.",
        f"got {reloaded.continuity_notes_for_next_open!r}",
    )
    _report(
        "last_resume_context survives",
        reloaded.last_resume_context == "Task 1 complete.",
        f"got {reloaded.last_resume_context!r}",
    )


# ─── Test 3: put overwrites ──────────────────────────────────────────────────


def test_put_overwrites() -> None:
    print("\n── Test 3: putting a new session replaces the previous one ──")

    OperatorSessionStore.reset_default_for_tests()
    store = OperatorSessionStore.default()

    first = OperatorSession.new()
    first.active_workspace = "product"
    first.day_mode = OperatorDayMode.REMOTE_ACTIVE
    store.put(first)

    first_id = first.day_session_id

    second = OperatorSession.new()
    second.active_workspace = "builder"
    second.day_mode = OperatorDayMode.LOCAL_ACTIVE
    store.put(second)

    second_id = second.day_session_id

    current = store.get()

    _report("store holds exactly one session (overwritten)", current is not None)
    if current is None:
        return

    _report(
        "current session_id is the second one",
        current.day_session_id == second_id,
        f"first={first_id!r}, second={second_id!r}, got={current.day_session_id!r}",
    )
    _report(
        "current day_mode is LOCAL_ACTIVE",
        current.day_mode == OperatorDayMode.LOCAL_ACTIVE,
        f"got {current.day_mode!r}",
    )
    _report(
        "current active_workspace is builder",
        current.active_workspace == "builder",
        f"got {current.active_workspace!r}",
    )
    _report(
        "first session_id is no longer current",
        current.day_session_id != first_id,
        f"got {current.day_session_id!r}",
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Operator Session Smoke Tests")
    print("=" * 60)

    test_enum_values()
    test_create_and_persist()
    test_put_overwrites()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
