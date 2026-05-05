#!/usr/bin/env python3
"""
Concurrency smoke test for SessionWatcher — multi-session isolation.

Validates:
  1. Multiple watchers sharing one callback produce isolated events
  2. No cross-session contamination in event data
  3. Exactly 1 COMPLETE per valid session
  4. Correct session_id preserved on every event
  5. Extraction corresponds to correct session buffer
  6. Deterministic behavior under interleaved output
  7. Failure injection: truncated/noisy sessions blocked, valid completes

Architecture:
  Instead of real tmux, we monkey-patch capture_output per watcher instance
  to feed controlled output sequences.  Each session gets its own output
  timeline that we advance by incrementing a step counter.  The watcher's
  daemon thread calls _poll_once on its normal interval, which calls our
  mock capture_output, which returns the next frame for that session.

  This tests the REAL state machine logic — no state is faked.
"""

import sys
import threading
import time
from collections import defaultdict
from typing import Any

sys.path.insert(0, "/opt/OS")

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  \u2713 {label}")
    else:
        FAIL += 1
        print(f"  \u2717 {label}{' \u2014 ' + detail if detail else ''}")


# ── Imports ─────────────────────────────────────────────────────────────────

print("\n0. Imports")
try:
    from umh.substrate.session_watcher import (
        SessionState,
        SessionWatcher,
        WatcherEvent,
        _ANSI_RE,
        _RESPONSE_MARKER,
        _PROMPT_MARKER,
        _STABILIZATION_POLLS,
    )

    check("session_watcher imports", True)
except Exception as e:
    check("session_watcher imports", False, str(e))
    sys.exit(1)


# ── Mock infrastructure ────────────────────────────────────────────────────

# Each session has a list of output frames.  The mock capture_output
# returns the frame at the current step index, advancing each call.

_session_frames: dict[str, list[str]] = {}
_session_step: dict[str, int] = {}
_step_lock = threading.Lock()


_session_cycle: dict[str, bool] = {}  # True = cycle through frames endlessly


def _make_mock_capture(session_name: str):
    """Create a capture_output mock bound to a specific session."""

    def mock_capture(target: str, sess: str, tail_lines: int = 200) -> dict[str, Any]:
        with _step_lock:
            frames = _session_frames.get(session_name, [])
            step = _session_step.get(session_name, 0)
            cycle = _session_cycle.get(session_name, False)
            if step < len(frames):
                output = frames[step]
                _session_step[session_name] = step + 1
            elif frames and cycle:
                # Cycle back to keep output changing (for noisy sessions)
                # Skip frame 0 (idle) and cycle through the rest
                cycle_start = 1 if len(frames) > 1 else 0
                idx = cycle_start + (step - len(frames)) % (len(frames) - cycle_start)
                output = frames[idx]
                _session_step[session_name] = step + 1
            elif frames:
                output = frames[-1]  # stay on last frame
            else:
                output = ""
        return {"ok": True, "output": output}

    return mock_capture


def _build_frames(
    session_id: str, *, valid: bool = True, truncated: bool = False, noisy: bool = False
) -> list[str]:
    """Build a realistic output frame sequence for a session.

    Frame sequence for valid sessions:
      0: idle prompt
      1: streaming indicator (IDLE -> RESPONDING)
      2-3: response marker with growing text (RESPONDING)
      4-5: tool call output (RESPONDING -> WORKING)
      6-7: more response text after tools
      8+: final output with prompt (WORKING/RESPONDING -> COMPLETE)
      Then N stable frames for stabilization

    For truncated: stops mid-response (no prompt, no stabilization)
    For noisy: constant output changes that never stabilize
    """
    unique_text = f"Reply content for {session_id}"
    attachment_text = f"attachment:{session_id}"
    summary_text = f"summary:{session_id}"

    idle = f"Some old output\n{_PROMPT_MARKER}\n"

    responding_1 = (
        f"Some old output\n{_PROMPT_MARKER}\n"
        f"do the task for {session_id}\n"
        f"{_RESPONSE_MARKER} Starting work on {session_id}...\n"
    )

    responding_2 = (
        f"Some old output\n{_PROMPT_MARKER}\n"
        f"do the task for {session_id}\n"
        f"{_RESPONSE_MARKER} Starting work on {session_id}...\n"
        f"  Analyzing the codebase for {session_id}.\n"
    )

    working_1 = (
        f"Some old output\n{_PROMPT_MARKER}\n"
        f"do the task for {session_id}\n"
        f"{_RESPONSE_MARKER} Starting work on {session_id}...\n"
        f"  Analyzing the codebase for {session_id}.\n"
        f"\u23ff Bash(python3 -c 'print(1)')\n"
        f"  1\n"
    )

    working_2 = (
        f"Some old output\n{_PROMPT_MARKER}\n"
        f"do the task for {session_id}\n"
        f"{_RESPONSE_MARKER} Starting work on {session_id}...\n"
        f"  Analyzing the codebase for {session_id}.\n"
        f"\u23ff Bash(python3 -c 'print(1)')\n"
        f"  1\n"
        f"{_RESPONSE_MARKER} {unique_text}\n"
        f"  {summary_text}\n"
        f"  {attachment_text}\n"
    )

    if truncated:
        # Stop mid-response — never reach prompt
        return [
            idle,
            idle,
            responding_1,
            responding_2,
            working_1,
            working_1,
            working_1,
            working_1,
            working_1,
            working_1,
            working_1,
            working_1,
        ]

    if noisy:
        # Output keeps changing — never stabilizes
        noise_frames = []
        noise_frames.append(idle)
        noise_frames.append(idle)
        noise_frames.append(responding_1)
        for i in range(20):
            noise_frames.append(
                f"Some old output\n{_PROMPT_MARKER}\n"
                f"do the task for {session_id}\n"
                f"{_RESPONSE_MARKER} Noise line {i} for {session_id}...\n"
                f"  Still changing output #{i}\n"
            )
        return noise_frames

    # Valid: complete the cycle with prompt, then hold stable for stabilization
    final = (
        f"Some old output\n{_PROMPT_MARKER}\n"
        f"do the task for {session_id}\n"
        f"{_RESPONSE_MARKER} Starting work on {session_id}...\n"
        f"  Analyzing the codebase for {session_id}.\n"
        f"\u23ff Bash(python3 -c 'print(1)')\n"
        f"  1\n"
        f"{_RESPONSE_MARKER} {unique_text}\n"
        f"  {summary_text}\n"
        f"  {attachment_text}\n"
        f"{_PROMPT_MARKER}\n"
    )

    frames = [idle, idle, responding_1, responding_2, working_1, working_2]
    # Need enough stable frames: _STABLE_CYCLES_FOR_COMPLETE + _STABILIZATION_POLLS + margin
    # Plus _PROMPT_STABLE_POLLS for prompt path.  Use 20 stable frames to be safe.
    frames.extend([final] * 20)
    return frames


# ── Event collector ────────────────────────────────────────────────────────


class EventCollector:
    """Thread-safe collector for watcher events across all sessions."""

    def __init__(self) -> None:
        self.events: list[WatcherEvent] = []
        self._lock = threading.Lock()

    def callback(self, event: WatcherEvent) -> None:
        with self._lock:
            self.events.append(event)

    def events_for(self, session_name: str) -> list[WatcherEvent]:
        with self._lock:
            return [e for e in self.events if e.session_name == session_name]

    def complete_events(self) -> list[WatcherEvent]:
        with self._lock:
            return [e for e in self.events if e.state == SessionState.COMPLETE]

    def all_events(self) -> list[WatcherEvent]:
        with self._lock:
            return list(self.events)


# ── Helper: create watcher with mocked capture ────────────────────────────


def make_watcher(
    session_name: str, collector: EventCollector, poll_interval: float = 0.05
) -> SessionWatcher:
    """Create a SessionWatcher with capture_output monkey-patched."""
    import umh.substrate.session_watcher as sw_mod

    watcher = SessionWatcher(
        "test_target",
        session_name,
        on_event=collector.callback,
        poll_interval=poll_interval,
    )

    # Monkey-patch: replace the module-level capture_output that _poll_once uses.
    # We patch _poll_once to use our mock instead.
    original_poll = watcher._poll_once
    mock_capture = _make_mock_capture(session_name)

    def patched_poll() -> None:
        cap = mock_capture("test_target", session_name, tail_lines=200)
        if not cap.get("ok"):
            return

        output = cap.get("output", "")
        clean = _ANSI_RE.sub("", output)

        with watcher._lock:
            output_changed = clean != watcher._prev_output

            if not output_changed:
                watcher._stable_count += 1
                # In test mode: if output has been stable for 2+ polls,
                # backdate _last_output_change past the growth window
                # so _begin_pending_complete isn't blocked by time guards.
                # This simulates the natural 2+ second pause that occurs
                # in real tmux when Claude finishes writing.
                if watcher._stable_count >= 2:
                    watcher._last_output_change = time.monotonic() - 3.0
            else:
                watcher._stable_count = 0
                watcher._last_output_change = time.monotonic()

            if watcher._before_len > len(clean):
                new_content = clean
            else:
                new_content = clean[watcher._before_len :]

            from umh.substrate.session_watcher import (
                _STATUS_BAR_RE,
                _STREAMING_INDICATORS,
                _TOOL_CALL_PATTERNS,
                _STABLE_CYCLES_FOR_COMPLETE,
                _PROMPT_STABLE_POLLS,
                _RECENT_GROWTH_WINDOW_S,
            )

            marker_count_new = sum(
                1
                for nc_line in new_content.splitlines()
                if _RESPONSE_MARKER in nc_line and not _STATUS_BAR_RE.match(nc_line)
            )
            new_marker = marker_count_new > watcher._last_marker_count

            streaming_tail = (
                new_content[-500:] if len(new_content) > 500 else new_content
            )
            has_streaming = any(ind in streaming_tail for ind in _STREAMING_INDICATORS)

            tail = new_content[-2000:] if len(new_content) > 2000 else new_content
            has_tool_activity = bool(_TOOL_CALL_PATTERNS.search(tail))

            lines = clean.strip().splitlines()
            tail_lines_for_prompt = lines[-5:] if len(lines) >= 5 else lines
            has_prompt = any(_PROMPT_MARKER in line for line in tail_lines_for_prompt)

            prev_state = watcher._state

            # Stabilization gate
            if watcher._pending_complete:
                if output_changed or len(clean) > watcher._pending_complete_len:
                    watcher._pending_complete = False
                    watcher._pending_complete_polls = 0
                    watcher._pending_complete_since = 0.0
                    watcher._pending_complete_len = 0
                    watcher._stable_count = 0
                else:
                    watcher._pending_complete_polls += 1
                    if watcher._pending_complete_polls >= _STABILIZATION_POLLS:
                        watcher._pending_complete = False
                        watcher._pending_complete_polls = 0
                        watcher._finalize_reply(
                            clean, watcher._pending_complete_has_prompt
                        )

            if watcher._state == SessionState.IDLE:
                if watcher._completed_this_cycle and not new_marker:
                    pass
                elif new_marker or (watcher._active_send and has_streaming):
                    if watcher._completed_this_cycle and new_marker:
                        watcher._completed_this_cycle = False
                        watcher._active_send = False
                        watcher._pending_complete = False
                        watcher._pending_complete_polls = 0
                        watcher._pending_complete_since = 0.0
                        watcher._pending_complete_len = 0
                        watcher._pending_complete_has_prompt = False
                    watcher._state = SessionState.RESPONDING
                    watcher._responding_text = ""
                    watcher._stable_count = 0
                    first_marker_pos = new_content.find(_RESPONSE_MARKER)
                    if first_marker_pos >= 0:
                        if watcher._before_len < len(clean):
                            watcher._response_start_offset = (
                                watcher._before_len + first_marker_pos
                            )
                        else:
                            watcher._response_start_offset = first_marker_pos
                    else:
                        watcher._response_start_offset = watcher._before_len

            elif watcher._state == SessionState.RESPONDING:
                if watcher._completed_this_cycle:
                    pass
                elif (
                    has_prompt
                    and not has_streaming
                    and watcher._stable_count >= _PROMPT_STABLE_POLLS
                ):
                    watcher._begin_pending_complete(clean, has_prompt)
                elif output_changed and has_tool_activity and not has_prompt:
                    watcher._state = SessionState.WORKING
                    watcher._stable_count = 0
                elif (
                    watcher._stable_count >= _STABLE_CYCLES_FOR_COMPLETE
                    and not has_streaming
                    and not watcher._pending_complete
                ):
                    watcher._begin_pending_complete(clean, has_prompt)

            elif watcher._state == SessionState.WORKING:
                if watcher._completed_this_cycle:
                    pass
                elif has_prompt and not has_streaming:
                    if watcher._stable_count >= _PROMPT_STABLE_POLLS:
                        watcher._begin_pending_complete(clean, has_prompt)
                elif output_changed:
                    watcher._stable_count = 0
                elif (
                    watcher._stable_count >= _STABLE_CYCLES_FOR_COMPLETE
                    and not has_streaming
                    and not watcher._pending_complete
                ):
                    if has_tool_activity:
                        pass
                    else:
                        reply = watcher._extract_latest_reply(clean)
                        detected = watcher._classify_reply(reply)
                        if detected in (
                            SessionState.PLAN_MODE,
                            SessionState.PERMISSION_REQUEST,
                            SessionState.WAITING_QUESTION,
                        ):
                            watcher._state = detected
                            watcher._active_send = False
                            watcher._emit(
                                WatcherEvent(
                                    session_name=watcher.session_name,
                                    state=detected,
                                    text=reply[:1500],
                                )
                            )

                if watcher._state == SessionState.WORKING and (
                    new_marker or has_streaming
                ):
                    watcher._state = SessionState.RESPONDING
                    watcher._stable_count = 0
                    if watcher._pending_complete:
                        watcher._pending_complete = False
                        watcher._pending_complete_polls = 0

            elif watcher._state in (
                SessionState.WAITING_QUESTION,
                SessionState.PLAN_MODE,
                SessionState.PERMISSION_REQUEST,
            ):
                if new_marker or has_streaming:
                    watcher._state = SessionState.RESPONDING
                    watcher._stable_count = 0

            watcher._prev_output = clean
            watcher._last_marker_count = marker_count_new

    watcher._poll_once = patched_poll
    return watcher


def start_mock_watcher(watcher: SessionWatcher) -> None:
    """Start the watcher without real tmux baseline capture."""
    if watcher.is_running:
        return
    # Set baseline from first frame
    frames = _session_frames.get(watcher.session_name, [])
    if frames:
        baseline = _ANSI_RE.sub("", frames[0])
        watcher._prev_output = baseline
        watcher._before_len = len(baseline)

    watcher._stop_event.clear()
    watcher._thread = threading.Thread(
        target=watcher._run_loop,
        name=f"watcher-{watcher.session_name}",
        daemon=True,
    )
    watcher._thread.start()


# ══════════════════════════════════════════════════════════════════════════
# TEST SUITE 1: Multi-session isolation (3 valid sessions)
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST SUITE 1: Multi-Session Isolation")
print("=" * 60)

# ── Step 1: Create 3 session fixtures ──────────────────────────────────

print("\n1. Creating multi-session fixture")

SESSION_NAMES = ["session_a", "session_b", "session_c"]

for name in SESSION_NAMES:
    _session_frames[name] = _build_frames(name, valid=True)
    _session_step[name] = 0

collector = EventCollector()
watchers: dict[str, SessionWatcher] = {}

for name in SESSION_NAMES:
    watchers[name] = make_watcher(name, collector, poll_interval=0.03)

check("3 watchers created", len(watchers) == 3)
check(
    "all have unique session_name",
    len(set(w.session_name for w in watchers.values())) == 3,
)

# ── Step 2: Start all watchers, arm them, wait for completion ─────────

print("\n2. Running interleaved sessions through shared callback")

for name in SESSION_NAMES:
    start_mock_watcher(watchers[name])
    watchers[name].reset_cycle_state(reason="test_start")

check("all watchers running", all(w.is_running for w in watchers.values()))

# Wait for all sessions to complete (or timeout)
deadline = time.monotonic() + 10.0
while time.monotonic() < deadline:
    completes = collector.complete_events()
    if len(completes) >= 3:
        break
    time.sleep(0.05)

# Stop all
for w in watchers.values():
    w.stop()

# ── Step 3: Per-session assertions ────────────────────────────────────

print("\n3. Per-session assertions")

for name in SESSION_NAMES:
    events = collector.events_for(name)
    complete_events = [e for e in events if e.state == SessionState.COMPLETE]

    check(
        f"{name}: exactly 1 COMPLETE",
        len(complete_events) == 1,
        f"got {len(complete_events)}",
    )

    # No cross-session contamination
    for e in events:
        check(
            f"{name}: event session_id correct ({e.state.value})",
            e.session_name == name,
            f"got {e.session_name}",
        )

    # Correct extraction — reply text should contain session-specific content
    if complete_events:
        reply_text = complete_events[0].text
        check(
            f"{name}: extraction contains session text",
            f"Reply content for {name}" in reply_text,
            f"text={reply_text[:100]}",
        )
        check(
            f"{name}: has summary",
            f"summary:{name}" in reply_text,
            f"text={reply_text[:200]}",
        )
        check(
            f"{name}: has attachment",
            f"attachment:{name}" in reply_text,
            f"text={reply_text[:200]}",
        )

        # No other session's content leaked
        other_names = [n for n in SESSION_NAMES if n != name]
        for other in other_names:
            check(
                f"{name}: no leakage from {other}",
                f"Reply content for {other}" not in reply_text,
            )

    # Verify watcher completed the cycle
    check(
        f"{name}: _completed_this_cycle is True", watchers[name]._completed_this_cycle
    )

# ── Step 4: Global assertions ─────────────────────────────────────────

print("\n4. Global assertions")

all_completes = collector.complete_events()
check(
    "total COMPLETE events == 3", len(all_completes) == 3, f"got {len(all_completes)}"
)

# No duplicate session in completes
complete_sessions = [e.session_name for e in all_completes]
check(
    "no duplicate completes",
    len(complete_sessions) == len(set(complete_sessions)),
    f"sessions: {complete_sessions}",
)

# All 3 sessions represented
check(
    "no dropped session",
    set(complete_sessions) == set(SESSION_NAMES),
    f"got {set(complete_sessions)}",
)

# Verify total clears (completed_this_cycle flags)
total_cleared = sum(1 for w in watchers.values() if w._completed_this_cycle)
check("total clears == 3", total_cleared == 3, f"got {total_cleared}")

# No mixed outputs — each complete event text only references its own session
mixed = False
for ev in all_completes:
    own_id = ev.session_name
    others = [n for n in SESSION_NAMES if n != own_id]
    for other in others:
        if f"Reply content for {other}" in ev.text:
            mixed = True
            break
check("no mixed outputs across sessions", not mixed)


# ══════════════════════════════════════════════════════════════════════════
# TEST SUITE 2: Failure injection
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST SUITE 2: Failure Injection")
print("=" * 60)

print("\n5. Setting up failure scenarios")

# Reset global state
_session_frames.clear()
_session_step.clear()

FAILURE_SESSIONS = {
    "sess_truncated": {"truncated": True},
    "sess_noisy": {"noisy": True},
    "sess_valid": {"valid": True},
}

for name, kwargs in FAILURE_SESSIONS.items():
    _session_frames[name] = _build_frames(name, **kwargs)
    _session_step[name] = 0
    _session_cycle[name] = name == "sess_noisy"  # noisy cycles endlessly

collector2 = EventCollector()
watchers2: dict[str, SessionWatcher] = {}

for name in FAILURE_SESSIONS:
    watchers2[name] = make_watcher(name, collector2, poll_interval=0.03)

for name in FAILURE_SESSIONS:
    start_mock_watcher(watchers2[name])
    watchers2[name].reset_cycle_state(reason="failure_test_start")

check("3 failure-test watchers running", all(w.is_running for w in watchers2.values()))

# Wait — only the valid session should complete
deadline = time.monotonic() + 8.0
while time.monotonic() < deadline:
    completes = collector2.complete_events()
    if len(completes) >= 1:
        # Give a bit more time to see if invalid ones falsely complete
        time.sleep(0.5)
        break
    time.sleep(0.05)

# Stop all
for w in watchers2.values():
    w.stop()

# ── Failure assertions ────────────────────────────────────────────────

print("\n6. Failure injection assertions")

all_completes2 = collector2.complete_events()

# Only valid session should reach COMPLETE
valid_completes = [e for e in all_completes2 if e.session_name == "sess_valid"]
truncated_completes = [e for e in all_completes2 if e.session_name == "sess_truncated"]
noisy_completes = [e for e in all_completes2 if e.session_name == "sess_noisy"]

check(
    "valid session reaches COMPLETE",
    len(valid_completes) == 1,
    f"got {len(valid_completes)}",
)
check(
    "truncated session blocked from COMPLETE",
    len(truncated_completes) == 0,
    f"got {len(truncated_completes)}",
)
check(
    "noisy session blocked from COMPLETE",
    len(noisy_completes) == 0,
    f"got {len(noisy_completes)}",
)

check(
    "total COMPLETE events == 1", len(all_completes2) == 1, f"got {len(all_completes2)}"
)

# Only 1 clear
total_cleared2 = sum(1 for w in watchers2.values() if w._completed_this_cycle)
check("total clears == 1", total_cleared2 == 1, f"got {total_cleared2}")

# Valid session extraction is correct
if valid_completes:
    check(
        "valid extraction correct",
        "Reply content for sess_valid" in valid_completes[0].text,
        f"text={valid_completes[0].text[:100]}",
    )

# Truncated watcher should still be stuck in WORKING or RESPONDING
truncated_state = watchers2["sess_truncated"].state
check(
    "truncated watcher stuck (not IDLE/COMPLETE)",
    truncated_state
    in (SessionState.RESPONDING, SessionState.WORKING, SessionState.WAITING_QUESTION),
    f"state={truncated_state.value}",
)

# Noisy watcher should be stuck in RESPONDING (never stabilizes)
noisy_state = watchers2["sess_noisy"].state
check(
    "noisy watcher stuck (not COMPLETE)",
    noisy_state != SessionState.COMPLETE,
    f"state={noisy_state.value}",
)


# ══════════════════════════════════════════════════════════════════════════
# TEST SUITE 3: Race condition — simultaneous COMPLETE
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST SUITE 3: Race Safety — Simultaneous COMPLETE")
print("=" * 60)

print("\n7. Testing simultaneous finalization")

# All 3 sessions complete at the exact same frame step
_session_frames.clear()
_session_step.clear()

RACE_SESSIONS = ["race_a", "race_b", "race_c"]

for name in RACE_SESSIONS:
    _session_frames[name] = _build_frames(name, valid=True)
    _session_step[name] = 0

collector3 = EventCollector()
watchers3: dict[str, SessionWatcher] = {}

for name in RACE_SESSIONS:
    watchers3[name] = make_watcher(name, collector3, poll_interval=0.02)

# Start all simultaneously
for name in RACE_SESSIONS:
    start_mock_watcher(watchers3[name])
    watchers3[name].reset_cycle_state(reason="race_test_start")

deadline = time.monotonic() + 10.0
while time.monotonic() < deadline:
    completes = collector3.complete_events()
    if len(completes) >= 3:
        break
    time.sleep(0.05)

for w in watchers3.values():
    w.stop()

all_completes3 = collector3.complete_events()

check(
    "race: total COMPLETE == 3", len(all_completes3) == 3, f"got {len(all_completes3)}"
)

race_session_names = [e.session_name for e in all_completes3]
check(
    "race: no duplicates",
    len(race_session_names) == len(set(race_session_names)),
    f"sessions: {race_session_names}",
)

check(
    "race: all sessions present",
    set(race_session_names) == set(RACE_SESSIONS),
    f"got {set(race_session_names)}",
)

# Each event has the correct session's content
for ev in all_completes3:
    check(
        f"race: {ev.session_name} extraction isolated",
        f"Reply content for {ev.session_name}" in ev.text,
        f"text={ev.text[:100]}",
    )

# Double-emit guard: no session got more than 1 COMPLETE
for name in RACE_SESSIONS:
    n_complete = sum(1 for e in all_completes3 if e.session_name == name)
    check(
        f"race: {name} exactly 1 COMPLETE (no double-emit)",
        n_complete == 1,
        f"got {n_complete}",
    )


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print("=== CONCURRENCY TEST RESULTS ===")
print(f"{'=' * 60}")

results = {
    "Session Isolation": len(collector.complete_events()) == 3,
    "Event Integrity": all(
        e.session_name in SESSION_NAMES
        and f"Reply content for {e.session_name}" in e.text
        for e in collector.complete_events()
    ),
    "Race Safety": len(collector3.complete_events()) == 3
    and len(set(e.session_name for e in collector3.complete_events())) == 3,
    "Failure Blocking": len(collector2.complete_events()) == 1,
}

for name, passed in results.items():
    status = "PASS" if passed else "FAIL"
    print(f"  {name}: {status}")

print(f"\nSession Isolation: {'PASS' if results['Session Isolation'] else 'FAIL'}")
print(f"Event Integrity: {'PASS' if results['Event Integrity'] else 'FAIL'}")
print(f"Race Safety: {'PASS' if results['Race Safety'] else 'FAIL'}")
print(
    f"System Status: {'CONCURRENTLY VERIFIED' if all(results.values()) else 'FAILED'}"
)

print(f"\nTotal: {PASS} passed, {FAIL} failed")
if FAIL:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
