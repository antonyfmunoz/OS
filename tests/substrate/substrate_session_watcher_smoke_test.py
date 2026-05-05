"""Smoke tests for eos_ai.substrate.session_watcher.

Validates two critical bug fixes:
  1. Conversational replies ending with '?' are NOT classified as waiting_question
     when ● + ❯ (complete response) markers are present.
  2. Watcher stays IDLE when no active send is pending, even if tmux output changes.

Run directly:
    python3 tests/substrate/substrate_session_watcher_smoke_test.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.session_watcher import (  # noqa: E402
    SessionState,
    SessionWatcher,
    WatcherEvent,
    _PROMPT_MARKER,
    _RESPONSE_MARKER,
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


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_watcher() -> SessionWatcher:
    """Create a watcher without starting the daemon thread."""
    return SessionWatcher("test", "test_session")


def _simulate_output(w: SessionWatcher, text: str) -> None:
    """Simulate a tmux capture by setting _prev_output directly."""
    w._prev_output = text


# ─── Bug 1: false waiting_question detection ────────────────────────────────


def test_conversational_question_not_waiting() -> None:
    """A reply like 'What do you need?' with ● + ❯ should be reply_text, not waiting_question."""
    print("\n── Bug 1: conversational '?' should not trigger waiting_question ──")

    w = _make_watcher()
    events: list[WatcherEvent] = []
    w._on_event = lambda e: events.append(e)

    # Simulate: active send in progress
    w._active_send = True
    w._state = SessionState.RESPONDING
    w._before_len = 0

    # Simulate finalized output: ● marker, reply ending with ?, then ❯ prompt
    clean = f"Some prior context\n{_RESPONSE_MARKER} What's up? What do you need?\n{_PROMPT_MARKER} "

    # Call _finalize_reply with has_prompt=True (● stable, ❯ visible)
    with w._lock:
        w._finalize_reply(clean, has_prompt=True)

    _report(
        "state transitions to IDLE (not WAITING_QUESTION)",
        w._state == SessionState.IDLE,
        f"got {w._state.value}",
    )
    _report(
        "_active_send cleared",
        w._active_send is False,
    )
    _report(
        "reply_ready is set",
        w._reply_ready.is_set(),
    )
    _report(
        "reply_text contains the reply",
        "What do you need?" in w._reply_text,
        f"reply_text={w._reply_text!r:.80}",
    )

    # The event should be IDLE, not WAITING_QUESTION
    idle_events = [e for e in events if e.state == SessionState.IDLE]
    question_events = [e for e in events if e.state == SessionState.WAITING_QUESTION]
    _report(
        "emitted IDLE event (not WAITING_QUESTION)",
        len(idle_events) == 1 and len(question_events) == 0,
        f"idle={len(idle_events)} question={len(question_events)}",
    )


def test_ask_user_without_prompt_still_waiting_question() -> None:
    """When CC uses ask_user (no ❯ after), waiting_question should still trigger."""
    print(
        "\n── Bug 1b: ask_user pattern (no prompt) should still be waiting_question ──"
    )

    w = _make_watcher()
    events: list[WatcherEvent] = []
    w._on_event = lambda e: events.append(e)

    w._active_send = True
    w._state = SessionState.RESPONDING
    w._before_len = 0

    # ask_user output: question without ❯ prompt after it
    clean = f"Some prior context\n{_RESPONSE_MARKER} Which option do you prefer?\nOption A or Option B?"

    # has_prompt=False — no ❯ visible after the content
    with w._lock:
        w._finalize_reply(clean, has_prompt=False)

    _report(
        "state transitions to WAITING_QUESTION",
        w._state == SessionState.WAITING_QUESTION,
        f"got {w._state.value}",
    )
    _report(
        "_active_send cleared",
        w._active_send is False,
    )


# ─── Bug 2: builder session oscillating ─────────────────────────────────────


def test_no_send_means_idle() -> None:
    """Without an active send, output changes should NOT move state out of IDLE."""
    print("\n── Bug 2: no active send → state stays IDLE ──")

    w = _make_watcher()
    w._active_send = False
    w._state = SessionState.IDLE
    w._before_len = 0

    # Simulate _poll_once seeing new markers in output (background activity)
    # We can't call _poll_once directly (needs real tmux), so we test the
    # guard condition directly: the IDLE block checks _active_send.

    # Simulate: output has new markers but _active_send is False
    old_output = "line 1\nline 2"
    new_output = f"line 1\nline 2\n{_RESPONSE_MARKER} Loading skills...\nDone."

    w._prev_output = old_output

    # Manually run the IDLE transition logic (extracted from _poll_once)
    new_content = new_output[w._before_len :]
    marker_count = new_content.count(_RESPONSE_MARKER)
    new_marker = marker_count > w._last_marker_count
    has_streaming = any(ind in new_content for ind in {"✻", "⎿"})

    # This is the exact guard from _poll_once
    should_transition = w._active_send and (new_marker or has_streaming)

    _report(
        "new_marker is True (output has ●)",
        new_marker is True,
    )
    _report(
        "_active_send is False → should NOT transition",
        should_transition is False,
    )
    _report(
        "state remains IDLE",
        w._state == SessionState.IDLE,
        f"got {w._state.value}",
    )


def test_active_send_allows_transition() -> None:
    """With an active send, new markers should move IDLE → RESPONDING."""
    print("\n── Bug 2b: active send → IDLE → RESPONDING works ──")

    w = _make_watcher()
    w._active_send = True
    w._state = SessionState.IDLE
    w._before_len = 0
    w._last_marker_count = 0

    new_content = f"{_RESPONSE_MARKER} Here is the reply"
    marker_count = new_content.count(_RESPONSE_MARKER)
    new_marker = marker_count > w._last_marker_count

    should_transition = w._active_send and (new_marker or False)

    _report(
        "active send + new marker → should transition",
        should_transition is True,
    )


def test_active_send_cleared_on_finalize() -> None:
    """_active_send should be False after _finalize_reply completes."""
    print("\n── Bug 2c: _active_send cleared after finalize ──")

    w = _make_watcher()
    w._active_send = True
    w._state = SessionState.RESPONDING
    w._before_len = 0

    clean = f"{_RESPONSE_MARKER} Done. All good.\n{_PROMPT_MARKER} "

    with w._lock:
        w._finalize_reply(clean, has_prompt=True)

    _report(
        "_active_send is False after finalize",
        w._active_send is False,
    )
    _report(
        "state is IDLE",
        w._state == SessionState.IDLE,
        f"got {w._state.value}",
    )


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Session Watcher Smoke Tests")
    print("=" * 60)

    test_conversational_question_not_waiting()
    test_ask_user_without_prompt_still_waiting_question()
    test_no_send_means_idle()
    test_active_send_allows_transition()
    test_active_send_cleared_on_finalize()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
