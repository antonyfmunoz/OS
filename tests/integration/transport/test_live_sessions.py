"""Smoke tests for eos_ai.substrate.live_sessions.

Validates:
  1.  test_live_session_create        — LiveSession.new() creates with correct defaults
  2.  test_live_session_roundtrip     — to_dict/from_dict roundtrip
  3.  test_create_and_start           — create_live_session + start_live_session lifecycle
  4.  test_pause_resume               — pause → resume transitions
  5.  test_end_session                — end_live_session sets ENDED + summary
  6.  test_fail_session               — fail_live_session sets FAILED + error
  7.  test_attach_task                — attach_task_to_live_session deduplicates
  8.  test_attach_pipeline            — attach_pipeline_to_live_session works and persists
  9.  test_detach                     — detach removes, idempotent on missing
 10.  test_persistence                — session survives singleton reset
 11.  test_active_filter              — active() returns only non-terminal
 12.  test_is_terminal                — is_terminal for ENDED and FAILED
 13.  test_summary                    — get_live_session_summary returns expected keys

Run directly:
    python3 tests/substrate/test_live_sessions.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.live_sessions import (  # noqa: E402
    LiveSession,
    LiveSessionState,
    LiveSessionStore,
    LiveSessionType,
    attach_pipeline_to_live_session,
    attach_task_to_live_session,
    create_live_session,
    detach_pipeline_from_live_session,
    detach_task_from_live_session,
    end_live_session,
    fail_live_session,
    get_live_session_summary,
    pause_live_session,
    resume_live_session,
    start_live_session,
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
    """Reset all singletons and clear storage keys between tests."""
    try:
        from eos_ai.substrate.storage import get_storage

        get_storage().put("live_sessions", None)
    except Exception:  # noqa: BLE001
        pass
    LiveSessionStore.reset_default_for_tests()


# ─── Test 1: LiveSession.new() defaults ────────────────────────────────────


def test_live_session_create() -> None:
    print("\n── Test 1: LiveSession.new() creates with correct defaults ──")

    _reset_all()

    session = LiveSession.new("Test", LiveSessionType.VOICE)

    _report(
        "live_session_id starts with lsess_",
        session.live_session_id.startswith("lsess_"),
        f"got {session.live_session_id!r}",
    )
    _report(
        "state is CREATED",
        session.state == LiveSessionState.CREATED,
        f"got {session.state.value}",
    )
    _report(
        "title is 'Test'",
        session.title == "Test",
        f"got {session.title!r}",
    )
    _report(
        "session_type is VOICE",
        session.session_type == LiveSessionType.VOICE,
        f"got {session.session_type.value}",
    )
    _report(
        "primary_agent_role defaults to 'general'",
        session.primary_agent_role == "general",
        f"got {session.primary_agent_role!r}",
    )
    _report(
        "attached_task_ids is empty list",
        session.attached_task_ids == [],
        f"got {session.attached_task_ids!r}",
    )
    _report(
        "attached_pipeline_ids is empty list",
        session.attached_pipeline_ids == [],
        f"got {session.attached_pipeline_ids!r}",
    )


# ─── Test 2: to_dict / from_dict roundtrip ─────────────────────────────────


def test_live_session_roundtrip() -> None:
    print("\n── Test 2: to_dict / from_dict roundtrip ──")

    _reset_all()

    original = LiveSession.new(
        "Roundtrip",
        LiveSessionType.MEETING,
        primary_agent_role="strategist",
        participant_agent_roles=["analyst", "scribe"],
        attached_day_session_id="ds_round",
    )
    original.attached_task_ids = ["task_aaa"]
    original.attached_pipeline_ids = ["pipe_bbb"]
    original.summary = "test summary"
    original.last_event = "test event"

    d = original.to_dict()
    restored = LiveSession.from_dict(d)

    _report(
        "live_session_id survives",
        restored.live_session_id == original.live_session_id,
        f"got {restored.live_session_id!r}",
    )
    _report(
        "title survives",
        restored.title == original.title,
        f"got {restored.title!r}",
    )
    _report(
        "session_type survives",
        restored.session_type == original.session_type,
        f"got {restored.session_type.value}",
    )
    _report(
        "state survives",
        restored.state == original.state,
        f"got {restored.state.value}",
    )
    _report(
        "primary_agent_role survives",
        restored.primary_agent_role == original.primary_agent_role,
        f"got {restored.primary_agent_role!r}",
    )
    _report(
        "participant_agent_roles survives",
        restored.participant_agent_roles == original.participant_agent_roles,
        f"got {restored.participant_agent_roles!r}",
    )
    _report(
        "attached_day_session_id survives",
        restored.attached_day_session_id == original.attached_day_session_id,
        f"got {restored.attached_day_session_id!r}",
    )
    _report(
        "attached_task_ids survives",
        restored.attached_task_ids == original.attached_task_ids,
        f"got {restored.attached_task_ids!r}",
    )
    _report(
        "attached_pipeline_ids survives",
        restored.attached_pipeline_ids == original.attached_pipeline_ids,
        f"got {restored.attached_pipeline_ids!r}",
    )
    _report(
        "summary survives",
        restored.summary == original.summary,
        f"got {restored.summary!r}",
    )
    _report(
        "last_event survives",
        restored.last_event == original.last_event,
        f"got {restored.last_event!r}",
    )


# ─── Test 3: create + start lifecycle ──────────────────────────────────────


def test_create_and_start() -> None:
    print("\n── Test 3: create_live_session + start_live_session lifecycle ──")

    _reset_all()

    session = create_live_session("Sprint Planning", LiveSessionType.MEETING)

    _report(
        "state is CREATED after create",
        session.state == LiveSessionState.CREATED,
        f"got {session.state.value}",
    )
    _report(
        "live_session_id starts with lsess_",
        session.live_session_id.startswith("lsess_"),
        f"got {session.live_session_id!r}",
    )

    started = start_live_session(session.live_session_id)

    _report(
        "state is ACTIVE after start",
        started.state == LiveSessionState.ACTIVE,
        f"got {started.state.value}",
    )
    _report(
        "last_event is 'started'",
        started.last_event == "started",
        f"got {started.last_event!r}",
    )
    _report(
        "persisted in store",
        LiveSessionStore.default().get(session.live_session_id) is not None,
    )


# ─── Test 4: pause → resume ───────────────────────────────────────────────


def test_pause_resume() -> None:
    print("\n── Test 4: pause → resume transitions ──")

    _reset_all()

    session = create_live_session("Voice Call", LiveSessionType.VOICE)
    start_live_session(session.live_session_id)

    paused = pause_live_session(session.live_session_id)

    _report(
        "state is PAUSED after pause",
        paused.state == LiveSessionState.PAUSED,
        f"got {paused.state.value}",
    )
    _report(
        "last_event is 'paused'",
        paused.last_event == "paused",
        f"got {paused.last_event!r}",
    )

    resumed = resume_live_session(session.live_session_id)

    _report(
        "state is ACTIVE after resume",
        resumed.state == LiveSessionState.ACTIVE,
        f"got {resumed.state.value}",
    )
    _report(
        "last_event is 'resumed'",
        resumed.last_event == "resumed",
        f"got {resumed.last_event!r}",
    )


# ─── Test 5: end session ──────────────────────────────────────────────────


def test_end_session() -> None:
    print("\n── Test 5: end_live_session sets ENDED + summary ──")

    _reset_all()

    session = create_live_session("Standup", LiveSessionType.MEETING)
    start_live_session(session.live_session_id)

    ended = end_live_session(session.live_session_id, summary="Done")

    _report(
        "state is ENDED",
        ended.state == LiveSessionState.ENDED,
        f"got {ended.state.value}",
    )
    _report(
        "summary is 'Done'",
        ended.summary == "Done",
        f"got {ended.summary!r}",
    )
    _report(
        "last_event is 'ended'",
        ended.last_event == "ended",
        f"got {ended.last_event!r}",
    )


# ─── Test 6: fail session ─────────────────────────────────────────────────


def test_fail_session() -> None:
    print("\n── Test 6: fail_live_session sets FAILED + error ──")

    _reset_all()

    session = create_live_session("Discord VC", LiveSessionType.DISCORD_VOICE)
    start_live_session(session.live_session_id)

    failed = fail_live_session(session.live_session_id, error="Connection lost")

    _report(
        "state is FAILED",
        failed.state == LiveSessionState.FAILED,
        f"got {failed.state.value}",
    )
    _report(
        "last_event contains 'Connection lost'",
        failed.last_event is not None and "Connection lost" in failed.last_event,
        f"got {failed.last_event!r}",
    )


# ─── Test 7: attach task (with dedup) ─────────────────────────────────────


def test_attach_task() -> None:
    print("\n── Test 7: attach_task_to_live_session deduplicates ──")

    _reset_all()

    session = create_live_session("Work Session", LiveSessionType.LOCAL)

    updated = attach_task_to_live_session(session.live_session_id, "task_abc123")

    _report(
        "task_id in attached_task_ids",
        "task_abc123" in updated.attached_task_ids,
        f"got {updated.attached_task_ids!r}",
    )

    # Attach same task again — should not duplicate
    updated2 = attach_task_to_live_session(session.live_session_id, "task_abc123")

    _report(
        "dedup: still only 1 entry after second attach",
        updated2.attached_task_ids.count("task_abc123") == 1,
        f"count = {updated2.attached_task_ids.count('task_abc123')}",
    )


# ─── Test 8: attach pipeline ──────────────────────────────────────────────


def test_attach_pipeline() -> None:
    print("\n── Test 8: attach_pipeline_to_live_session works and persists ──")

    _reset_all()

    session = create_live_session("Pipeline Session", LiveSessionType.LOCAL)

    updated = attach_pipeline_to_live_session(session.live_session_id, "pipe_xyz")

    _report(
        "pipeline_id in attached_pipeline_ids",
        "pipe_xyz" in updated.attached_pipeline_ids,
        f"got {updated.attached_pipeline_ids!r}",
    )

    # Verify persistence via store
    reloaded = LiveSessionStore.default().get(session.live_session_id)
    _report(
        "persisted in store",
        reloaded is not None and "pipe_xyz" in reloaded.attached_pipeline_ids,
        f"got {reloaded.attached_pipeline_ids if reloaded else 'None'}",
    )


# ─── Test 9: detach (idempotent) ──────────────────────────────────────────


def test_detach() -> None:
    print("\n── Test 9: detach removes, idempotent on missing ──")

    _reset_all()

    session = create_live_session("Detach Test", LiveSessionType.LOCAL)
    attach_task_to_live_session(session.live_session_id, "task_detach1")

    detached = detach_task_from_live_session(session.live_session_id, "task_detach1")

    _report(
        "task removed after detach",
        "task_detach1" not in detached.attached_task_ids,
        f"got {detached.attached_task_ids!r}",
    )

    # Detach again — should not raise
    try:
        detached2 = detach_task_from_live_session(
            session.live_session_id, "task_detach1"
        )
        _report(
            "idempotent: second detach does not raise",
            True,
        )
        _report(
            "still empty after second detach",
            "task_detach1" not in detached2.attached_task_ids,
            f"got {detached2.attached_task_ids!r}",
        )
    except Exception as e:
        _report("idempotent: second detach does not raise", False, f"raised {e!r}")

    # Also test pipeline detach idempotency
    try:
        detach_pipeline_from_live_session(session.live_session_id, "pipe_nonexistent")
        _report(
            "idempotent: detach missing pipeline does not raise",
            True,
        )
    except Exception as e:
        _report(
            "idempotent: detach missing pipeline does not raise",
            False,
            f"raised {e!r}",
        )


# ─── Test 10: persistence across singleton reset ──────────────────────────


def test_persistence() -> None:
    print("\n── Test 10: session survives singleton reset ──")

    _reset_all()

    session = create_live_session("Persist Me", LiveSessionType.GOOGLE_MEET)
    sid = session.live_session_id

    # Reset singleton (simulates process restart)
    LiveSessionStore.reset_default_for_tests()

    # Reload from storage
    reloaded = LiveSessionStore.default().get(sid)

    _report(
        "session reloads after singleton reset",
        reloaded is not None,
        "got None" if reloaded is None else "",
    )
    if reloaded is not None:
        _report(
            "live_session_id survives",
            reloaded.live_session_id == sid,
            f"expected {sid!r}, got {reloaded.live_session_id!r}",
        )
        _report(
            "title survives",
            reloaded.title == "Persist Me",
            f"got {reloaded.title!r}",
        )
        _report(
            "session_type survives",
            reloaded.session_type == LiveSessionType.GOOGLE_MEET,
            f"got {reloaded.session_type.value}",
        )
        _report(
            "state survives",
            reloaded.state == LiveSessionState.CREATED,
            f"got {reloaded.state.value}",
        )


# ─── Test 11: active() filter ─────────────────────────────────────────────


def test_active_filter() -> None:
    print("\n── Test 11: active() returns only non-terminal ──")

    _reset_all()

    s1 = create_live_session("Active One", LiveSessionType.VOICE)
    start_live_session(s1.live_session_id)

    s2 = create_live_session("Ended One", LiveSessionType.VOICE)
    start_live_session(s2.live_session_id)
    end_live_session(s2.live_session_id, summary="Finished")

    active = LiveSessionStore.default().active()

    _report(
        "active() returns 1 session",
        len(active) == 1,
        f"got {len(active)}",
    )
    _report(
        "active session is s1",
        len(active) == 1 and active[0].live_session_id == s1.live_session_id,
        f"got {active[0].live_session_id if active else 'empty'}",
    )


# ─── Test 12: is_terminal ─────────────────────────────────────────────────


def test_is_terminal() -> None:
    print("\n── Test 12: is_terminal for ENDED and FAILED ──")

    _reset_all()

    ended = LiveSession.new("Ended", LiveSessionType.LOCAL)
    ended.state = LiveSessionState.ENDED

    failed = LiveSession.new("Failed", LiveSessionType.LOCAL)
    failed.state = LiveSessionState.FAILED

    active = LiveSession.new("Active", LiveSessionType.LOCAL)
    active.state = LiveSessionState.ACTIVE

    created = LiveSession.new("Created", LiveSessionType.LOCAL)
    # state defaults to CREATED

    paused = LiveSession.new("Paused", LiveSessionType.LOCAL)
    paused.state = LiveSessionState.PAUSED

    _report("ENDED is terminal", ended.is_terminal() is True)
    _report("FAILED is terminal", failed.is_terminal() is True)
    _report("ACTIVE is not terminal", active.is_terminal() is False)
    _report("CREATED is not terminal", created.is_terminal() is False)
    _report("PAUSED is not terminal", paused.is_terminal() is False)


# ─── Test 13: get_live_session_summary ─────────────────────────────────────


def test_summary() -> None:
    print("\n── Test 13: get_live_session_summary returns expected keys ──")

    _reset_all()

    # Create sessions in various states
    s1 = create_live_session("Active", LiveSessionType.VOICE)
    start_live_session(s1.live_session_id)

    s2 = create_live_session("Paused", LiveSessionType.MEETING)
    start_live_session(s2.live_session_id)
    pause_live_session(s2.live_session_id)

    s3 = create_live_session("Ended", LiveSessionType.LOCAL)
    start_live_session(s3.live_session_id)
    end_live_session(s3.live_session_id, summary="All done")

    summary = get_live_session_summary()

    expected_keys = {
        "active_live_sessions",
        "paused_live_sessions",
        "waiting_live_sessions",
        "total_active",
        "recent_ended",
    }

    _report(
        "all expected keys present",
        expected_keys.issubset(set(summary.keys())),
        f"got keys: {list(summary.keys())}",
    )
    _report(
        "active_live_sessions == 1",
        summary["active_live_sessions"] == 1,
        f"got {summary['active_live_sessions']}",
    )
    _report(
        "paused_live_sessions == 1",
        summary["paused_live_sessions"] == 1,
        f"got {summary['paused_live_sessions']}",
    )
    _report(
        "waiting_live_sessions == 0",
        summary["waiting_live_sessions"] == 0,
        f"got {summary['waiting_live_sessions']}",
    )
    _report(
        "total_active == 2 (non-terminal)",
        summary["total_active"] == 2,
        f"got {summary['total_active']}",
    )
    _report(
        "recent_ended == 1",
        summary["recent_ended"] == 1,
        f"got {summary['recent_ended']}",
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Live Sessions Smoke Tests")
    print("=" * 60)

    test_live_session_create()
    test_live_session_roundtrip()
    test_create_and_start()
    test_pause_resume()
    test_end_session()
    test_fail_session()
    test_attach_task()
    test_attach_pipeline()
    test_detach()
    test_persistence()
    test_active_filter()
    test_is_terminal()
    test_summary()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
