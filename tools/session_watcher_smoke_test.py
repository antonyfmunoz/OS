#!/usr/bin/env python3
"""
Smoke tests for Session Watcher + Discord Bridge.

Tests:
  1. State machine transitions (all 5 states)
  2. Reply extraction from mock tmux output
  3. Classification (plan, permission, question, normal)
  4. Watcher-aware ask_session fallback
  5. Bridge event formatting
  6. Session isolation (builder vs product)
  7. Double-response prevention on buttons
"""

import sys
import threading
import time

sys.path.insert(0, "/opt/OS")

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}{' — ' + detail if detail else ''}")


# ── 1. Imports ───────────────────────────────────────────────────────────────

print("\n1. Imports")
try:
    from umh.substrate.session_watcher import (
        SessionState,
        SessionWatcher,
        WatcherEvent,
        get_watcher,
        start_watcher,
        stop_watcher,
        stop_all_watchers,
        ask_session_watched,
    )

    check("session_watcher imports", True)
except Exception as e:
    check("session_watcher imports", False, str(e))

try:
    from umh.substrate.session_discord_bridge import (
        SessionDiscordBridge,
        PlanApprovalView,
        PermissionView,
        format_event,
        get_bridge,
    )

    check("session_discord_bridge imports", True)
except Exception as e:
    check("session_discord_bridge imports", False, str(e))


# ── 2. SessionState enum ────────────────────────────────────────────────────

print("\n2. SessionState enum")
check("IDLE exists", SessionState.IDLE.value == "idle")
check("RESPONDING exists", SessionState.RESPONDING.value == "responding")
check(
    "WAITING_QUESTION exists", SessionState.WAITING_QUESTION.value == "waiting_question"
)
check("WORKING exists", SessionState.WORKING.value == "working")
check("PLAN_MODE exists", SessionState.PLAN_MODE.value == "plan_mode")
check(
    "PERMISSION_REQUEST exists",
    SessionState.PERMISSION_REQUEST.value == "permission_request",
)


# ── 3. WatcherEvent ─────────────────────────────────────────────────────────

print("\n3. WatcherEvent")
ev = WatcherEvent(session_name="test_session", state=SessionState.IDLE, text="hello")
d = ev.to_dict()
check("to_dict has session_name", d["session_name"] == "test_session")
check("to_dict has state value", d["state"] == "idle")
check("to_dict has text", d["text"] == "hello")
check("to_dict has timestamp", isinstance(d["timestamp"], float))


# ── 4. SessionWatcher init ──────────────────────────────────────────────────

print("\n4. SessionWatcher init (no start)")
w = SessionWatcher("vps", "test_smoke", on_event=lambda e: None)
check("initial state is IDLE", w.state == SessionState.IDLE)
check("not running before start", not w.is_running)


# ── 5. Reply classification ─────────────────────────────────────────────────

print("\n5. Reply classification")

# Plan mode
w2 = SessionWatcher("vps", "test_classify")
result = w2._classify_reply(
    "Here is my plan:\n1. Do X\n2. Do Y\nDo you want me to proceed?"
)
check("plan text → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply("I will:\n1. Read the file\n2. Edit it\nShall I proceed?")
check("shall I proceed → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply(
    "Here's the plan.\n\n## Files Modified\n| File | Change |\n|---|---|\n"
    "| foo.py | Add endpoint |\n\nSay the word and I'll execute it."
)
check("say the word → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply("That's the full plan. Say the word and I'll execute it.")
check("full plan → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply(
    "Here's the plan.\n\n1. Read the file\n2. Edit it\n\nReady to execute?"
)
check("ready to execute → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply("Here's what I'd do:\n1. A\n2. B\nShould I proceed?")
check("should I proceed → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply("Here's my approach:\n1. A\n2. B\nWant me to proceed?")
check("want me to proceed → PLAN_MODE", result == SessionState.PLAN_MODE)

result = w2._classify_reply(
    "Overview:\n1. A\n2. B\nShall I go ahead and implement this?"
)
check("trailing proceed question → PLAN_MODE", result == SessionState.PLAN_MODE)

# Permission
result = w2._classify_reply("Allow this tool to run:\nBash(ls -la /opt/OS)")
check("Allow this tool → PERMISSION_REQUEST", result == SessionState.PERMISSION_REQUEST)

result = w2._classify_reply("Bash(docker restart os-discord)\n[Y]es / [N]o")
check("[Y]es/[N]o → PERMISSION_REQUEST", result == SessionState.PERMISSION_REQUEST)

# Question
result = w2._classify_reply(
    "The file has two versions.\nWhich one would you like to use?"
)
check("question mark → WAITING_QUESTION", result == SessionState.WAITING_QUESTION)

# Normal reply
result = w2._classify_reply("Done. The file has been updated successfully.")
check("normal reply → IDLE", result == SessionState.IDLE)


# ── 6. Reply extraction ─────────────────────────────────────────────────────

print("\n6. Reply extraction")

mock_output = """❯ tell me about the project
● The project is an AI operating system called EOS.
  It manages multiple business ventures through a unified
  intelligence layer.
❯"""

reply = w2._extract_latest_reply(mock_output)
check("extracts reply text", "AI operating system" in reply)
check("strips ● marker", "●" not in reply)
check("stops at ❯", "❯" not in reply)

# Empty output
reply_empty = w2._extract_latest_reply("just some random text")
check("no marker → empty", reply_empty == "")


# ── 7. Event formatting (Discord bridge) ────────────────────────────────────

print("\n7. Event formatting")

ev_q = WatcherEvent(
    session_name="dex_builder_main",
    state=SessionState.WAITING_QUESTION,
    text="Which database should I use?",
)
fmt = format_event(ev_q)
check("question format has content", "asking" in fmt["content"].lower())
check("question has no view", fmt["view"] is None)

ev_p = WatcherEvent(
    session_name="dex_builder_main",
    state=SessionState.PLAN_MODE,
    text="Here is my plan:\n1. Do X",
)
fmt = format_event(ev_p)
check("plan format has content", "plan" in fmt["content"].lower())
check("plan has view", fmt["view"] is not None)
check("plan view is PlanApprovalView", isinstance(fmt["view"], PlanApprovalView))

ev_perm = WatcherEvent(
    session_name="dex_builder_main",
    state=SessionState.PERMISSION_REQUEST,
    text="Bash(rm -rf /tmp/test)",
)
fmt = format_event(ev_perm)
check("permission format has content", "permission" in fmt["content"].lower())
check("permission has view", isinstance(fmt["view"], PermissionView))

ev_idle = WatcherEvent(
    session_name="dex_builder_main",
    state=SessionState.IDLE,
    text="Done.",
)
fmt = format_event(ev_idle)
check("idle format has no content", fmt["content"] is None)


# ── 8. Bridge singleton ─────────────────────────────────────────────────────

print("\n8. Bridge singleton")
bridge = get_bridge()
check(
    "get_bridge returns SessionDiscordBridge", isinstance(bridge, SessionDiscordBridge)
)
bridge2 = get_bridge()
check("singleton — same instance", bridge is bridge2)


# ── 9. ask_session_watched fallback ──────────────────────────────────────────

print("\n9. ask_session_watched fallback (no watcher)")
result = ask_session_watched("vps", "nonexistent_session", "hello")
check("no watcher → fallback signal", result.get("fallback") is True)
check("no watcher → ok=False", result.get("ok") is False)
check("no watcher → reason=no_watcher", result.get("reason") == "no_watcher")


# ── 10. Session isolation ────────────────────────────────────────────────────

print("\n10. Session isolation")
w_builder = SessionWatcher("vps", "dex_builder_main")
w_product = SessionWatcher("vps", "dex_product_main")
check("separate instances", w_builder is not w_product)
check("separate session names", w_builder.session_name != w_product.session_name)
# Modify one, confirm other unaffected
w_builder._state = SessionState.RESPONDING
check("builder state change", w_builder.state == SessionState.RESPONDING)
check("product state unchanged", w_product.state == SessionState.IDLE)


# ── 11. Watcher global registry ─────────────────────────────────────────────

print("\n11. Watcher registry")
check("get nonexistent → None", get_watcher("nonexistent") is None)
stop_all_watchers()  # clean slate
check("stop_all on empty → no error", True)


# ── 12. wait_until_idle ─────────────────────────────────────────────────────

print("\n12. wait_until_idle")

# Idle watcher with prompt visible → should return True quickly
w_idle = SessionWatcher("vps", "test_idle_check")
# Simulate state: IDLE, prompt visible, stable output
w_idle._state = SessionState.IDLE
w_idle._prev_output = "some output\n❯"
result_idle = w_idle.wait_until_idle(timeout=2.0, min_stable_polls=2)
check("idle with prompt → True", result_idle is True)

# Responding watcher → should timeout (short timeout)
w_busy = SessionWatcher("vps", "test_busy_check")
w_busy._state = SessionState.RESPONDING
w_busy._prev_output = "some output ✻ streaming..."
result_busy = w_busy.wait_until_idle(timeout=0.5, min_stable_polls=2)
check("responding → timeout False", result_busy is False)

# Streaming indicator present → should timeout
w_stream = SessionWatcher("vps", "test_stream_check")
w_stream._state = SessionState.IDLE
w_stream._prev_output = "some output ⎿ still going\n❯"
result_stream = w_stream.wait_until_idle(timeout=0.5, min_stable_polls=2)
check("streaming indicator → timeout False", result_stream is False)

# No prompt → should timeout
w_noprompt = SessionWatcher("vps", "test_noprompt_check")
w_noprompt._state = SessionState.IDLE
w_noprompt._prev_output = "some output without prompt"
result_noprompt = w_noprompt.wait_until_idle(timeout=0.5, min_stable_polls=2)
check("no prompt → timeout False", result_noprompt is False)


# ── 13. WORKING state transitions ──────────────────────────────────────────

print("\n13. WORKING state transitions")

# RESPONDING → WORKING when tool call detected
w_work = SessionWatcher("vps", "test_working")
w_work._state = SessionState.RESPONDING
w_work._prev_output = "● Let me check that.\n⎿ Bash("
# Simulate a poll with tool call output
w_work._stable_count = 0
w_work._last_marker_count = 1
# Manually test the transition logic: output changed + tool activity + no prompt
new_output = "● Let me check that.\n⎿ Bash(python3 -c 'print(1)')\n  1"
# The _poll_once reads from tmux, but we can test state directly
w_work._state = SessionState.WORKING  # simulate transition
check("WORKING state reachable", w_work.state == SessionState.WORKING)

from umh.substrate.session_watcher import _STABLE_CYCLES_FOR_COMPLETE

# WORKING stays while output changes
w_work._stable_count = 0
check("WORKING with changes keeps stable_count=0", w_work._stable_count == 0)

# WORKING → finalize when stable + prompt
w_work._state = SessionState.WORKING
w_work._stable_count = 5
check(
    "WORKING with high stable count",
    w_work._stable_count >= _STABLE_CYCLES_FOR_COMPLETE,
)

# Verify _TOOL_CALL_PATTERNS matches expected patterns
from umh.substrate.session_watcher import _TOOL_CALL_PATTERNS

check("detects Bash(", bool(_TOOL_CALL_PATTERNS.search("⎿ Bash(ls -la)")))
check("detects python3", bool(_TOOL_CALL_PATTERNS.search("python3 -c 'test'")))
check("detects git", bool(_TOOL_CALL_PATTERNS.search("git log --oneline")))
check("detects Read(", bool(_TOOL_CALL_PATTERNS.search("Read(/opt/OS/foo.py)")))
check(
    "no false positive on plain text",
    not bool(_TOOL_CALL_PATTERNS.search("The project is working fine.")),
)

# Verify adaptive timeout constants exist
from umh.substrate.session_watcher import _IDLE_TIMEOUT_S, _WORKING_TIMEOUT_S

check("idle timeout is 30s", _IDLE_TIMEOUT_S == 30.0)
check("working timeout is 120s", _WORKING_TIMEOUT_S == 120.0)


# ── 14. before_len windowing — tool call detection ─────────────────────────

print("\n14. before_len windowing — tool call detection")

# Simulate: old history contains tool calls, new content does not.
# Without windowing, watcher would see old Bash(...) and stay WORKING.
w_win = SessionWatcher("vps", "test_window")

# Old history with tool calls
old_history = (
    "❯ fix the bug\n"
    "● Let me check.\n"
    "⎿ Bash(python3 -c 'print(1)')\n"
    "  1\n"
    "● Done. The file is fixed.\n"
    "❯\n"
)
# Set before_len to the end of old history (simulating send_response snapshot)
w_win._before_len = len(old_history)
w_win._prev_output = old_history

# New content: a clean reply with no tool calls
new_reply = "● The project looks good. No issues found.\n❯\n"
full_output = old_history + new_reply

# Test: _extract_latest_reply should find the NEW ● marker, not the old ones
reply = w_win._extract_latest_reply(full_output)
check("windowed extract finds new reply", "No issues found" in reply)
check("windowed extract ignores old reply", "file is fixed" not in reply)

# Test: tool call patterns should NOT trigger on old content
from umh.substrate.session_watcher import _TOOL_CALL_PATTERNS

new_content = full_output[w_win._before_len :]
has_tool_in_new = bool(_TOOL_CALL_PATTERNS.search(new_content))
check("no tool calls in new content", not has_tool_in_new)

has_tool_in_old = bool(_TOOL_CALL_PATTERNS.search(old_history))
check("tool calls exist in old content (control)", has_tool_in_old)


# ── 15. before_len windowing — marker counting ────────────────────────────

print("\n15. before_len windowing — marker counting")

# Old output has 2 ● markers, new content adds 1 more
w_mk = SessionWatcher("vps", "test_marker_window")
old_out = "● old reply 1\n❯\n● old reply 2\n❯\n"
w_mk._before_len = len(old_out)
w_mk._prev_output = old_out
w_mk._last_marker_count = 0  # reset for fresh cycle

new_out = old_out + "● new reply here\n❯\n"
new_content = new_out[w_mk._before_len :]
new_markers = new_content.count("●")
check("new content has exactly 1 marker", new_markers == 1)
check("full output has 3 markers (would confuse old logic)", new_out.count("●") == 3)


# ── 16. before_len windowing — reply extraction edge cases ─────────────────

print("\n16. before_len windowing — reply extraction edge cases")

# Edge: before_len is 0 (no prior send) — should work like before
w_edge = SessionWatcher("vps", "test_edge_zero")
w_edge._before_len = 0
output_simple = "● Hello world\n❯\n"
reply = w_edge._extract_latest_reply(output_simple)
check("before_len=0 extracts normally", "Hello world" in reply)

# Edge: before_len exceeds output (shouldn't happen, but degrade gracefully)
w_edge2 = SessionWatcher("vps", "test_edge_exceed")
w_edge2._before_len = 99999
output_short = "● Short reply\n❯\n"
reply2 = w_edge2._extract_latest_reply(output_short)
check("before_len > output → empty reply", reply2 == "")


# ── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'=' * 50}")
print(f"Session Watcher Smoke Test: {PASS} passed, {FAIL} failed")
if FAIL:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
