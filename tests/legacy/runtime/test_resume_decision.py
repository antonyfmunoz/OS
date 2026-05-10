"""Tests for resume decision logic — continuity drives session strategy."""

import sys
sys.path.insert(0, "/opt/OS")

import io
import contextlib
import time

from umh.runtime_loop.continuity_store import ContinuityStore, get_continuity_store
from umh.runtime_loop.lifecycle_hooks import reset_hooks
from umh.runtime_loop.lifecycle_behaviors import (
    RESUME_THRESHOLD_S,
    _make_resume_decision,
    get_resume_context,
    install,
    _resume_contexts,
)
from umh.runtime_loop.session_registry import SessionRegistry
from umh.runtime_loop.context import RuntimeContext


def _capture_stderr(fn):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        fn()
    return buf.getvalue()


def _setup():
    reset_hooks()
    _resume_contexts.clear()
    install()
    return SessionRegistry()


def test_decision_resume_when_quick_reopen():
    now = time.time()
    prev = {"ended_at": now - 60, "duration_s": 120.0, "mode": "builder", "session_id": "s_old"}
    decision = _make_resume_decision(prev, now)
    assert decision["strategy"] == "resume"
    assert decision["idle_gap_s"] < RESUME_THRESHOLD_S


def test_decision_fresh_when_long_gap():
    now = time.time()
    prev = {"ended_at": now - 600, "duration_s": 120.0, "mode": "builder", "session_id": "s_old"}
    decision = _make_resume_decision(prev, now)
    assert decision["strategy"] == "fresh"
    assert decision["idle_gap_s"] >= RESUME_THRESHOLD_S


def test_decision_fresh_at_exact_threshold():
    now = time.time()
    prev = {"ended_at": now - RESUME_THRESHOLD_S, "duration_s": 10.0, "mode": "builder", "session_id": "s_old"}
    decision = _make_resume_decision(prev, now)
    assert decision["strategy"] == "fresh"


def test_decision_resume_just_under_threshold():
    now = time.time()
    prev = {"ended_at": now - (RESUME_THRESHOLD_S - 1), "duration_s": 10.0, "mode": "builder", "session_id": "s_old"}
    decision = _make_resume_decision(prev, now)
    assert decision["strategy"] == "resume"


def test_full_cycle_resume():
    reg = _setup()
    store = get_continuity_store()

    rec1 = reg.register_session("s1", "builder", "n1", "ch_resume")
    reg.close_session(rec1.session_id)

    output = _capture_stderr(
        lambda: reg.register_session("s2", "builder", "n1", "ch_resume")
    )
    assert "resume_decision" in output
    assert '"strategy": "resume"' in output or "'strategy': 'resume'" in output


def test_full_cycle_fresh():
    reg = _setup()
    store = get_continuity_store()

    store.save("ch_stale", {
        "session_id": "s_ancient",
        "mode": "builder",
        "node": "n1",
        "duration_s": 60.0,
        "last_activity_ts": time.time() - 1000,
        "surface_count": 0,
        "ended_at": time.time() - 600,
    })

    output = _capture_stderr(
        lambda: reg.register_session("s_new", "builder", "n1", "ch_stale")
    )
    assert "resume_decision" in output
    assert '"strategy": "fresh"' in output or "'strategy': 'fresh'" in output


def test_no_previous_no_decision():
    reg = _setup()

    output = _capture_stderr(
        lambda: reg.register_session("fresh", "builder", "n1", "ch_brand_new")
    )
    assert "resume_decision" not in output
    assert "session_opened" in output


def test_resume_context_stashed():
    reg = _setup()

    rec1 = reg.register_session("s1", "builder", "n1", "ch_stash")
    reg.close_session(rec1.session_id)
    rec2 = reg.register_session("s2", "builder", "n1", "ch_stash")

    ctx = get_resume_context(rec2.session_id)
    assert ctx is not None
    assert ctx["previous_session"]["session_id"] == rec1.session_id
    assert ctx["resume_decision"]["strategy"] == "resume"


def test_runtime_context_has_previous_session():
    ctx = RuntimeContext(
        runtime_session_id="ses_1",
        transport="discord",
        timestamp="2026-04-18T00:00:00Z",
        correlation_id="cor_1",
        previous_session={"session_id": "old", "mode": "builder"},
    )
    assert ctx.previous_session is not None
    assert ctx.previous_session["session_id"] == "old"


def test_runtime_context_none_by_default():
    ctx = RuntimeContext(
        runtime_session_id="ses_2",
        transport="discord",
        timestamp="2026-04-18T00:00:00Z",
        correlation_id="cor_2",
    )
    assert ctx.previous_session is None


def test_decision_carries_metadata():
    now = time.time()
    prev = {
        "ended_at": now - 30,
        "duration_s": 45.5,
        "mode": "product",
        "session_id": "ses_prev_123",
    }
    decision = _make_resume_decision(prev, now)
    assert decision["prev_duration_s"] == 45.5
    assert decision["last_mode"] == "product"
    assert decision["previous_session_id"] == "ses_prev_123"


def test_lifecycle_not_broken_by_decision():
    reg = _setup()

    rec1 = reg.register_session("s1", "builder", "n1", "ch_safe")
    assert rec1.status == "active"

    closed = reg.close_session(rec1.session_id)
    assert closed.status == "closed"

    rec2 = reg.register_session("s2", "builder", "n1", "ch_safe")
    assert rec2.status == "active"
    assert rec2.session_id != rec1.session_id


if __name__ == "__main__":
    test_decision_resume_when_quick_reopen()
    test_decision_fresh_when_long_gap()
    test_decision_fresh_at_exact_threshold()
    test_decision_resume_just_under_threshold()
    test_full_cycle_resume()
    test_full_cycle_fresh()
    test_no_previous_no_decision()
    test_resume_context_stashed()
    test_runtime_context_has_previous_session()
    test_runtime_context_none_by_default()
    test_decision_carries_metadata()
    test_lifecycle_not_broken_by_decision()
    print("all resume decision tests passed")
