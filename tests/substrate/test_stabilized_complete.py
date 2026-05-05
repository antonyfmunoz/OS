"""Tests for stabilized COMPLETE detection in session_watcher.

Validates that the watcher does NOT emit premature COMPLETE when:
  1. Claude pauses between sections of a multi-part report
  2. Output growth resumes after a pause
  3. Only the final, truly-stable output triggers COMPLETE

Also validates clear dedupe in session_control.

Run directly:
    python3 tests/substrate/test_stabilized_complete.py
"""

from __future__ import annotations

import sys
import time
from unittest.mock import patch

sys.path.insert(0, "/opt/OS")

from umh.substrate.session_watcher import (  # noqa: E402
    SessionState,
    SessionWatcher,
    WatcherEvent,
    _PROMPT_MARKER,
    _RESPONSE_MARKER,
    _STABILIZATION_POLLS,
    _STABLE_CYCLES_FOR_COMPLETE,
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


class FakeCapture:
    """Simulates tmux capture_output by returning scripted output sequences."""

    def __init__(self) -> None:
        self.outputs: list[str] = []
        self._idx = 0

    def add(self, text: str) -> None:
        self.outputs.append(text)

    def __call__(self, target: str, session_name: str, **kw: object) -> dict:
        if self._idx < len(self.outputs):
            output = self.outputs[self._idx]
            self._idx += 1
        else:
            # Repeat last output (stable)
            output = self.outputs[-1] if self.outputs else ""
        return {"ok": True, "output": output}


def _make_watcher() -> SessionWatcher:
    """Create a watcher ready for manual polling (no daemon thread)."""
    w = SessionWatcher("test", "test_session")
    w._prev_output = ""
    w._before_len = 0
    w._active_send = True
    w._completed_this_cycle = False
    w._state = SessionState.IDLE
    return w


def _poll(w: SessionWatcher, capture: FakeCapture) -> None:
    """Run one poll cycle with the fake capture."""
    with patch(
        "umh.substrate.session_watcher.capture_output", capture
    ):
        w._poll_once()


# ─── Test 1: Multi-section report with pause ───────────────────────────────


def test_no_premature_complete_on_pause() -> None:
    """Output that pauses between sections must NOT trigger early COMPLETE."""
    print("\n── Test 1: no premature COMPLETE on mid-report pause ──")

    w = _make_watcher()
    cap = FakeCapture()
    events: list[WatcherEvent] = []
    w._on_event = lambda e: events.append(e)

    # Simulate a multi-section report being generated:
    # Phase 1: Section 1 arrives (output growing)
    section1 = f"{_RESPONSE_MARKER} Builder Report\n\n1. Item one\n2. Item two\n3. Item three\n"
    cap.add(section1)  # Poll 0: first output
    _poll(w, cap)
    _report(
        "enters RESPONDING on first marker",
        w._state == SessionState.RESPONDING,
        f"state={w._state.value}",
    )

    # Phase 2: Output grows (still writing)
    section1_ext = section1 + "4. Item four\n5. Item five\n"
    cap.add(section1_ext)  # Poll 1: more output
    _poll(w, cap)
    _report(
        "still RESPONDING while output grows",
        w._state == SessionState.RESPONDING,
        f"state={w._state.value}",
    )

    # Phase 3: Pause begins — output is stable for _STABLE_CYCLES_FOR_COMPLETE cycles
    # This simulates Claude thinking before section 2
    for i in range(_STABLE_CYCLES_FOR_COMPLETE):
        cap.add(section1_ext)  # Same output repeated
        _poll(w, cap)

    _report(
        "pending complete detected (not finalized yet)",
        w._pending_complete is True,
        f"pending={w._pending_complete}, completed={w._completed_this_cycle}",
    )
    _report(
        "NOT yet completed",
        w._completed_this_cycle is False,
        f"completed={w._completed_this_cycle}",
    )

    # Phase 4: New output arrives during stabilization window!
    # This is the critical moment — section 2 starts
    section2 = section1_ext + "\n6. Item six\n7. Item seven\n8. Item eight\n"
    cap.add(section2)
    _poll(w, cap)

    _report(
        "pending complete INVALIDATED by new output",
        w._pending_complete is False,
        f"pending={w._pending_complete}",
    )
    _report(
        "still RESPONDING (not prematurely completed)",
        w._state == SessionState.RESPONDING,
        f"state={w._state.value}",
    )
    _report(
        "no COMPLETE events emitted",
        all(e.state != SessionState.COMPLETE for e in events),
        f"events={[e.state.value for e in events]}",
    )

    # Phase 5: Final output with prompt — truly done
    final_output = section2 + "9. Item nine\n10. Item ten\n\n" + _PROMPT_MARKER
    cap.add(final_output)
    _poll(w, cap)  # Prompt appears, stable_count resets

    # Need _PROMPT_STABLE_POLLS of stability
    for i in range(3):
        cap.add(final_output)
        _poll(w, cap)

    # Then _STABILIZATION_POLLS more for stabilization window
    for i in range(_STABILIZATION_POLLS):
        cap.add(final_output)
        _poll(w, cap)

    complete_events = [e for e in events if e.state == SessionState.COMPLETE]
    _report(
        "COMPLETE emitted exactly once after full stabilization",
        len(complete_events) == 1,
        f"complete_count={len(complete_events)}",
    )
    if complete_events:
        _report(
            "final reply contains all 10 items",
            "Item ten" in complete_events[0].text
            or "10." in complete_events[0].text,
            f"reply_preview={complete_events[0].text[:200]!r}",
        )


# ─── Test 2: Stabilization window confirms genuine completion ──────────────


def test_stable_output_completes_after_window() -> None:
    """Output that is genuinely done should complete after stabilization."""
    print("\n── Test 2: genuinely stable output completes after window ──")

    w = _make_watcher()
    cap = FakeCapture()
    events: list[WatcherEvent] = []
    w._on_event = lambda e: events.append(e)

    # Short, complete response with prompt
    response = (
        f"{_RESPONSE_MARKER} Done. All tasks completed.\n\n" + _PROMPT_MARKER
    )
    cap.add(response)
    _poll(w, cap)  # Enter RESPONDING

    # Stable polls: need _PROMPT_STABLE_POLLS for prompt-first path
    total_polls_needed = _STABILIZATION_POLLS + 3  # generous margin
    for _ in range(total_polls_needed):
        cap.add(response)
        _poll(w, cap)

    complete_events = [e for e in events if e.state == SessionState.COMPLETE]
    _report(
        "COMPLETE fires for genuinely stable output",
        len(complete_events) == 1,
        f"complete_count={len(complete_events)}",
    )


# ─── Test 3: Stability-only path (no prompt) with pause ───────────────────


def test_stability_path_invalidation() -> None:
    """Without a prompt, stability-based COMPLETE must also be stabilized."""
    print("\n── Test 3: stability-only path respects stabilization window ──")

    w = _make_watcher()
    cap = FakeCapture()
    events: list[WatcherEvent] = []
    w._on_event = lambda e: events.append(e)

    # Section 1 arrives
    section1 = f"{_RESPONSE_MARKER} Report heading\n\n1. First thing\n"
    cap.add(section1)
    _poll(w, cap)

    # Pause: stable for _STABLE_CYCLES_FOR_COMPLETE (enters pending complete)
    for _ in range(_STABLE_CYCLES_FOR_COMPLETE):
        cap.add(section1)
        _poll(w, cap)

    _report(
        "pending complete entered without prompt",
        w._pending_complete is True,
        f"pending={w._pending_complete}",
    )

    # Output grows — invalidates the pending
    section2 = section1 + "2. Second thing\n3. Third thing\n"
    cap.add(section2)
    _poll(w, cap)

    _report(
        "pending invalidated",
        w._pending_complete is False,
    )
    _report(
        "no COMPLETE events yet",
        all(e.state != SessionState.COMPLETE for e in events),
    )


# ─── Test 4: Clear dedupe ─────────────────────────────────────────────────


def test_clear_dedupe() -> None:
    """clear_session must block duplicate clears within cooldown window."""
    print("\n── Test 4: clear dedupe in session_control ──")

    from umh.substrate.session_control import (
        _CLEAR_COOLDOWN_S,
        _clear_in_flight,
        _clear_lock,
        clear_session,
    )

    # Reset state
    with _clear_lock:
        _clear_in_flight.clear()

    # First clear: should succeed (mocked send)
    with patch(
        "umh.substrate.claude_session_bridge.send_message",
        return_value={"ok": True},
    ):
        r1 = clear_session("test", "test_session")
    _report("first clear succeeds", r1["ok"] is True)

    # Second clear immediately: should be blocked
    with patch(
        "umh.substrate.claude_session_bridge.send_message",
        return_value={"ok": True},
    ):
        r2 = clear_session("test", "test_session")
    _report(
        "duplicate clear blocked",
        r2["ok"] is False and r2.get("reason") == "duplicate_within_cooldown",
        f"reason={r2.get('reason')}",
    )

    # Reset state
    with _clear_lock:
        _clear_in_flight.clear()


# ─── Test 5: No duplicate COMPLETE events ──────────────────────────────────


def test_no_duplicate_complete() -> None:
    """Only one COMPLETE event per send cycle, even with extended stable output."""
    print("\n── Test 5: no duplicate COMPLETE events ──")

    w = _make_watcher()
    cap = FakeCapture()
    events: list[WatcherEvent] = []
    w._on_event = lambda e: events.append(e)

    response = f"{_RESPONSE_MARKER} Short reply.\n\n" + _PROMPT_MARKER

    # First poll: enter RESPONDING
    cap.add(response)
    _poll(w, cap)

    # Enough polls to trigger pending + stabilization
    for _ in range(10):
        cap.add(response)
        _poll(w, cap)

    complete_events = [e for e in events if e.state == SessionState.COMPLETE]
    _report(
        "exactly one COMPLETE event",
        len(complete_events) == 1,
        f"count={len(complete_events)}",
    )

    # Keep polling after COMPLETE — should NOT produce more
    for _ in range(5):
        cap.add(response)
        _poll(w, cap)

    complete_events = [e for e in events if e.state == SessionState.COMPLETE]
    _report(
        "still exactly one COMPLETE after continued polling",
        len(complete_events) == 1,
        f"count={len(complete_events)}",
    )


# ─── Run all ───────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("Stabilized COMPLETE detection tests")
    print("=" * 60)

    test_no_premature_complete_on_pause()
    test_stable_output_completes_after_window()
    test_stability_path_invalidation()
    test_clear_dedupe()
    test_no_duplicate_complete()

    print(f"\n{'=' * 60}")
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    print(f"{'=' * 60}")

    if _FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
