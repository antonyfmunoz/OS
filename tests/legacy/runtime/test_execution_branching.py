"""Tests for execution branching — resume vs fresh changes actual behavior."""

import sys
sys.path.insert(0, "/opt/OS")

import time

from umh.runtime_loop.lifecycle_hooks import reset_hooks
from umh.runtime_loop.lifecycle_behaviors import (
    install,
    get_resume_context,
    _resume_contexts,
)
from umh.runtime_loop.session_registry import SessionRegistry
from umh.runtime_loop.continuity_store import get_continuity_store
from umh.substrate.daily_rituals import OpenDayRequest
from umh.substrate.ritual_execution_driver import (
    execute_resume_day,
    execute_open_day,
)


def _setup():
    reset_hooks()
    _resume_contexts.clear()
    install()
    return SessionRegistry()


def _make_open_request(session_id: str) -> OpenDayRequest:
    return OpenDayRequest(
        request_id="req_test",
        runtime_session_id=session_id,
        entry_transport="discord",
        requested_profile_id="",
        requested_at="2026-04-18T00:00:00Z",
        correlation_id="cor_test",
    )


def _minimal_state() -> dict:
    return {}


def test_execute_resume_day_returns_contract():
    prev = {"session_id": "s_old", "mode": "builder", "duration_s": 60.0}
    req = _make_open_request("ses_new")
    mutations, events, result = execute_resume_day(_minimal_state(), req, prev)

    assert isinstance(mutations, list)
    assert isinstance(events, list)
    assert hasattr(result, "to_dict")
    assert result.plan_id.startswith("resume_")


def test_execute_resume_day_emits_session_resumed():
    prev = {"session_id": "s_old", "mode": "builder", "duration_s": 60.0}
    req = _make_open_request("ses_new")
    _, events, _ = execute_resume_day(_minimal_state(), req, prev)

    event_types = [e.event_type for e in events]
    assert "session_resumed" in event_types
    assert "open_day_started" not in event_types


def test_execute_resume_day_carries_previous_mode():
    prev = {"session_id": "s_old", "mode": "product", "duration_s": 30.0}
    req = _make_open_request("ses_new")
    _, _, result = execute_resume_day(_minimal_state(), req, prev)

    assert result.mode_after == "product"


def test_execute_resume_day_steps():
    prev = {"session_id": "s_old", "mode": "builder", "duration_s": 10.0}
    req = _make_open_request("ses_new")
    _, _, result = execute_resume_day(_minimal_state(), req, prev)

    assert "restore_presence" in result.steps_executed
    assert "restore_mode" in result.steps_executed
    assert "session_resumed" in result.steps_executed


def test_execute_resume_day_emits_completed():
    prev = {"session_id": "s_old", "mode": "builder", "duration_s": 10.0}
    req = _make_open_request("ses_new")
    _, events, _ = execute_resume_day(_minimal_state(), req, prev)

    completed = [e for e in events if e.event_type == "ritual_completed"]
    assert len(completed) == 1
    assert completed[0].metadata["ritual_kind"] == "resume_day"


def test_full_cycle_resume_branch():
    """Close → quick reopen → should branch to execute_resume_day."""
    reg = _setup()

    rec1 = reg.register_session("s1", "builder", "n1", "ch_branch_r")
    reg.close_session(rec1.session_id)

    rec2 = reg.register_session("s2", "builder", "n1", "ch_branch_r")
    ctx = get_resume_context(rec2.session_id)
    assert ctx is not None
    assert ctx["resume_decision"]["strategy"] == "resume"


def test_full_cycle_fresh_branch():
    """Stale artifact → should NOT trigger resume branch."""
    reg = _setup()
    store = get_continuity_store()

    store.save("ch_branch_f", {
        "session_id": "s_ancient",
        "mode": "builder",
        "node": "n1",
        "duration_s": 120.0,
        "last_activity_ts": time.time() - 1000,
        "surface_count": 0,
        "ended_at": time.time() - 600,
    })

    rec = reg.register_session("s_new", "builder", "n1", "ch_branch_f")
    ctx = get_resume_context(rec.session_id)
    assert ctx is not None
    assert ctx["resume_decision"]["strategy"] == "fresh"


def test_no_previous_goes_to_open_day():
    """No continuity → no resume context stashed."""
    reg = _setup()

    rec = reg.register_session("fresh", "builder", "n1", "ch_clean")
    ctx = get_resume_context(rec.session_id)
    assert ctx is None


def test_resume_payload_has_previous_session_id():
    prev = {"session_id": "ses_prev_42", "mode": "builder", "duration_s": 45.0}
    req = _make_open_request("ses_current")
    _, events, _ = execute_resume_day(_minimal_state(), req, prev)

    resumed = [e for e in events if e.event_type == "session_resumed"][0]
    assert resumed.payload["previous_session_id"] == "ses_prev_42"
    assert resumed.payload["previous_duration_s"] == 45.0


def test_open_day_still_works_unchanged():
    """Regression: execute_open_day still returns valid results."""
    req = _make_open_request("ses_fresh")
    mutations, events, result = execute_open_day(_minimal_state(), req)

    event_types = [e.event_type for e in events]
    assert "open_day_started" in event_types
    assert "session_resumed" not in event_types
    assert result.plan_id != ""


if __name__ == "__main__":
    test_execute_resume_day_returns_contract()
    test_execute_resume_day_emits_session_resumed()
    test_execute_resume_day_carries_previous_mode()
    test_execute_resume_day_steps()
    test_execute_resume_day_emits_completed()
    test_full_cycle_resume_branch()
    test_full_cycle_fresh_branch()
    test_no_previous_goes_to_open_day()
    test_resume_payload_has_previous_session_id()
    test_open_day_still_works_unchanged()
    print("all execution branching tests passed")
