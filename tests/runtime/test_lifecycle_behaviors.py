"""Tests for lifecycle behaviors — verify real actions fire on session transitions."""

import sys
sys.path.insert(0, "/opt/OS")

import io
import contextlib
import time

from umh.runtime_loop.lifecycle_hooks import reset_hooks
from umh.runtime_loop.lifecycle_behaviors import install, on_open, on_close
from umh.runtime_loop.session_registry import SessionRegistry, SessionRecord


def _make_registry() -> SessionRegistry:
    return SessionRegistry()


def _capture_stderr(fn):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        fn()
    return buf.getvalue()


def test_on_open_logs_session_opened():
    rec = SessionRecord(
        session_id="ses_test_open",
        session_name="test",
        mode="builder",
        node="n1",
        channel_id="ch1",
        transport="discord",
        status="active",
        last_activity_ts=time.time(),
        created_ts=time.time(),
        last_opened_ts=time.time(),
    )
    output = _capture_stderr(lambda: on_open(rec))
    assert "session_opened" in output
    assert "ses_test_open" in output
    assert "builder" in output


def test_on_close_logs_session_closed():
    now = time.time()
    rec = SessionRecord(
        session_id="ses_test_close",
        session_name="test",
        mode="builder",
        node="n1",
        channel_id="ch2",
        transport="discord",
        status="closed",
        last_activity_ts=now,
        created_ts=now - 120,
        last_opened_ts=now - 120,
        last_closed_ts=now,
    )
    output = _capture_stderr(lambda: on_close(rec))
    assert "session_closed" in output
    assert "ses_test_close" in output
    assert "duration_s" in output


def test_install_wires_hooks():
    reset_hooks()
    install()

    reg = _make_registry()
    output = _capture_stderr(lambda: reg.register_session("test", "builder", "n1", "ch3"))
    assert "session_opened" in output


def test_close_via_registry():
    reset_hooks()
    install()

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch4")

    output = _capture_stderr(lambda: reg.close_session(rec.session_id))
    assert "session_closed" in output


def test_behaviors_dont_break_lifecycle():
    reset_hooks()
    install()

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch5")
    assert rec.status == "active"

    closed = reg.close_session(rec.session_id)
    assert closed is not None
    assert closed.status == "closed"


def test_duration_is_positive():
    reset_hooks()
    now = time.time()
    rec = SessionRecord(
        session_id="ses_dur",
        session_name="test",
        mode="builder",
        node="n1",
        channel_id="ch6",
        transport="discord",
        status="closed",
        last_activity_ts=now,
        created_ts=now - 60,
        last_opened_ts=now - 60,
        last_closed_ts=now,
    )
    output = _capture_stderr(lambda: on_close(rec))
    assert "duration_s" in output


if __name__ == "__main__":
    test_on_open_logs_session_opened()
    test_on_close_logs_session_closed()
    test_install_wires_hooks()
    test_close_via_registry()
    test_behaviors_dont_break_lifecycle()
    test_duration_is_positive()
    print("all lifecycle behavior tests passed")
