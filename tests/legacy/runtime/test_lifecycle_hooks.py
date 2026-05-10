"""Tests for lifecycle hooks — verify hooks fire on session state transitions."""

import sys
sys.path.insert(0, "/opt/OS")

from umh.runtime_loop.lifecycle_hooks import register_hook, reset_hooks
from umh.runtime_loop.session_registry import SessionRegistry


def _make_registry() -> SessionRegistry:
    return SessionRegistry()


def test_on_open_fires_on_register():
    reset_hooks()
    fired = []
    register_hook("on_open", lambda s: fired.append(("open", s.session_id)))

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch1")
    assert len(fired) == 1
    assert fired[0] == ("open", rec.session_id)


def test_on_open_fires_on_resolve_or_create_new():
    reset_hooks()
    fired = []
    register_hook("on_open", lambda s: fired.append(s.session_id))

    reg = _make_registry()
    rec = reg.resolve_or_create("test", "builder", "n1", "ch_new")
    assert len(fired) == 1
    assert fired[0] == rec.session_id


def test_on_active_fires_on_idle_to_active():
    reset_hooks()
    fired = []
    register_hook("on_active", lambda s: fired.append(("active", s.session_id)))

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch2")
    reg.set_status(rec.session_id, "idle")
    reg.set_status(rec.session_id, "active")

    assert len(fired) == 1
    assert fired[0] == ("active", rec.session_id)


def test_on_active_fires_via_resolve_or_create():
    reset_hooks()
    fired = []
    register_hook("on_active", lambda s: fired.append(s.session_id))

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch3")
    reg.set_status(rec.session_id, "idle")
    reg.resolve_or_create("test", "builder", "n1", "ch3")

    assert len(fired) == 1


def test_on_idle_fires():
    reset_hooks()
    fired = []
    register_hook("on_idle", lambda s: fired.append(("idle", s.session_id)))

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch4")
    reg.set_status(rec.session_id, "idle")

    assert len(fired) == 1
    assert fired[0] == ("idle", rec.session_id)


def test_on_close_fires():
    reset_hooks()
    fired = []
    register_hook("on_close", lambda s: fired.append(("close", s.session_id)))

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch5")
    reg.close_session(rec.session_id)

    assert len(fired) == 1
    assert fired[0] == ("close", rec.session_id)


def test_hook_failure_does_not_break_lifecycle():
    reset_hooks()
    register_hook("on_open", lambda s: 1 / 0)

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch6")
    assert rec is not None
    assert rec.status == "active"


def test_no_hook_on_same_status():
    reset_hooks()
    fired = []
    register_hook("on_active", lambda s: fired.append(1))

    reg = _make_registry()
    rec = reg.register_session("test", "builder", "n1", "ch7")
    reg.set_status(rec.session_id, "active")

    assert len(fired) == 0


def test_reset_hooks():
    reset_hooks()
    fired = []
    register_hook("on_open", lambda s: fired.append(1))
    reset_hooks()

    reg = _make_registry()
    reg.register_session("test", "builder", "n1", "ch8")
    assert len(fired) == 0


if __name__ == "__main__":
    test_on_open_fires_on_register()
    test_on_open_fires_on_resolve_or_create_new()
    test_on_active_fires_on_idle_to_active()
    test_on_active_fires_via_resolve_or_create()
    test_on_idle_fires()
    test_on_close_fires()
    test_hook_failure_does_not_break_lifecycle()
    test_no_hook_on_same_status()
    test_reset_hooks()
    print("all lifecycle hook tests passed")
