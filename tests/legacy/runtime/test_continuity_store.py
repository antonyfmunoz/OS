"""Tests for session continuity — artifact persistence across session boundaries."""

import sys
sys.path.insert(0, "/opt/OS")

import io
import contextlib
import time

from umh.runtime_loop.continuity_store import ContinuityStore, get_continuity_store
from umh.runtime_loop.lifecycle_hooks import reset_hooks
from umh.runtime_loop.lifecycle_behaviors import install
from umh.runtime_loop.session_registry import SessionRegistry


def _capture_stderr(fn):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        fn()
    return buf.getvalue()


def test_store_save_and_load():
    store = ContinuityStore()
    store.save("ch1", {"session_id": "s1", "duration_s": 10.0})
    result = store.load("ch1")
    assert result is not None
    assert result["session_id"] == "s1"


def test_store_load_missing():
    store = ContinuityStore()
    assert store.load("nonexistent") is None


def test_store_overwrite():
    store = ContinuityStore()
    store.save("ch1", {"v": 1})
    store.save("ch1", {"v": 2})
    assert store.load("ch1")["v"] == 2


def test_store_clear():
    store = ContinuityStore()
    store.save("ch1", {"v": 1})
    store.clear("ch1")
    assert store.load("ch1") is None


def test_different_channels_isolated():
    store = ContinuityStore()
    store.save("ch_a", {"from": "a"})
    store.save("ch_b", {"from": "b"})
    assert store.load("ch_a")["from"] == "a"
    assert store.load("ch_b")["from"] == "b"


def test_close_saves_continuity_artifact():
    reset_hooks()
    install()
    store = get_continuity_store()

    reg = SessionRegistry()
    rec = reg.register_session("test", "builder", "n1", "ch_cont_1")
    reg.close_session(rec.session_id)

    artifact = store.load("ch_cont_1")
    assert artifact is not None
    assert artifact["session_id"] == rec.session_id
    assert artifact["mode"] == "builder"
    assert artifact["node"] == "n1"
    assert "duration_s" in artifact
    assert "ended_at" in artifact
    assert "surface_count" in artifact
    assert "last_activity_ts" in artifact


def test_open_loads_previous_artifact():
    reset_hooks()
    install()
    store = get_continuity_store()

    reg = SessionRegistry()

    rec1 = reg.register_session("test", "builder", "n1", "ch_cont_2")
    reg.close_session(rec1.session_id)

    saved = store.load("ch_cont_2")
    assert saved is not None

    output = _capture_stderr(
        lambda: reg.register_session("test2", "builder", "n1", "ch_cont_2")
    )
    assert "resume_decision" in output
    assert rec1.session_id in output


def test_open_without_previous_no_resume():
    reset_hooks()
    install()

    reg = SessionRegistry()
    output = _capture_stderr(
        lambda: reg.register_session("fresh", "builder", "n1", "ch_fresh")
    )
    assert "resume_decision" not in output
    assert "session_opened" in output


def test_full_cycle_does_not_break_lifecycle():
    reset_hooks()
    install()

    reg = SessionRegistry()
    rec1 = reg.register_session("s1", "builder", "n1", "ch_cycle")
    assert rec1.status == "active"

    closed = reg.close_session(rec1.session_id)
    assert closed.status == "closed"

    rec2 = reg.register_session("s2", "builder", "n1", "ch_cycle")
    assert rec2.status == "active"
    assert rec2.session_id != rec1.session_id


def test_snapshot():
    store = ContinuityStore()
    store.save("ch1", {"v": 1})
    store.save("ch2", {"v": 2})
    snap = store.snapshot()
    assert snap["channel_count"] == 2
    assert set(snap["channels"]) == {"ch1", "ch2"}


if __name__ == "__main__":
    test_store_save_and_load()
    test_store_load_missing()
    test_store_overwrite()
    test_store_clear()
    test_different_channels_isolated()
    test_close_saves_continuity_artifact()
    test_open_loads_previous_artifact()
    test_open_without_previous_no_resume()
    test_full_cycle_does_not_break_lifecycle()
    test_snapshot()
    print("all continuity store tests passed")
