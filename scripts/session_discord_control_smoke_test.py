#!/usr/bin/env python3
"""Smoke tests for the interactive Discord control layer.

Tests: state detection patterns, event formatting, button views,
channel routing, option extraction, timeout config, and watcher
activity tracking.

Run: python3 scripts/session_discord_control_smoke_test.py
"""

import os
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'), override=True)

# Must import AFTER load_dotenv so module-level os.getenv picks up values
from runtime.substrate.session_watcher import (  # noqa: E402
    SessionState,
    SessionWatcher,
    WatcherEvent,
    _PLAN_PATTERNS,
    _PERMISSION_PATTERNS,
    _QUESTION_PATTERNS,
)
from runtime.substrate.session_discord_bridge import (
    LAYER_VERSION,
    PlanApprovalView,
    PermissionView,
    QuestionOptionView,
    format_event,
    _extract_options,
    _resolve_channel_id,
    _BUTTON_TIMEOUT,
    _BUILDER_SESSION,
    _PRODUCT_SESSION,
)


passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


# ─── Layer version ──────────────────────────────────────────────────────────

print("\n=== Layer version ===")
check("bridge version is v2", LAYER_VERSION == "v2")

# ─── Button timeout config ──────────────────────────────────────────────────

print("\n=== Button timeout ===")
check("timeout is 60s", _BUTTON_TIMEOUT == 60.0)

plan_view = PlanApprovalView("test")
check("PlanApprovalView timeout = 60s", plan_view.timeout == 60.0)

perm_view = PermissionView("test")
check("PermissionView timeout = 60s", perm_view.timeout == 60.0)

q_view = QuestionOptionView("test", [("1. A", "1"), ("2. B", "2")])
check("QuestionOptionView timeout = 60s", q_view.timeout == 60.0)

# ─── View button counts ─────────────────────────────────────────────────────

print("\n=== View button counts ===")
check(
    "PlanApprovalView has 3 buttons (approve/reject/edit)", len(plan_view.children) == 3
)
check("PermissionView has 2 buttons (allow/deny)", len(perm_view.children) == 2)

q2 = QuestionOptionView("t", [("1. A", "1"), ("2. B", "2"), ("3. C", "3")])
check("QuestionOptionView 3 options → 3 buttons", len(q2.children) == 3)

q4 = QuestionOptionView(
    "t",
    [
        ("1. A", "1"),
        ("2. B", "2"),
        ("3. C", "3"),
        ("4. D", "4"),
        ("5. E", "5"),
    ],
)
check("QuestionOptionView caps at 4 buttons", len(q4.children) == 4)

# ─── View responded flag ────────────────────────────────────────────────────

print("\n=== Responded flag ===")
check("PlanApprovalView starts unresponded", not plan_view.responded)
check("PermissionView starts unresponded", not perm_view.responded)
check("QuestionOptionView starts unresponded", not q_view.responded)

# ─── Plan patterns ──────────────────────────────────────────────────────────

print("\n=== Plan pattern detection ===")
plan_texts = [
    "Here is my plan for the refactor:",
    "Do you want me to proceed with this?",
    "Shall I proceed?",
    "Want me to go ahead?",
    "Please approve this plan.",
    "Entering plan mode...",
]
for txt in plan_texts:
    matched = any(p.search(txt) for p in _PLAN_PATTERNS)
    check(f"plan: '{txt[:40]}'", matched)

# ─── Permission patterns ────────────────────────────────────────────────────

print("\n=== Permission pattern detection ===")
perm_texts = [
    "Allow this tool to execute?",
    "The agent needs permission to continue.",
    "Bash(rm -rf /tmp/old)",
    "Allow once",
    "Allow always",
    "[Y]es / [N]o",
    "Do you want to allow this action?",
]
for txt in perm_texts:
    matched = any(p.search(txt) for p in _PERMISSION_PATTERNS)
    check(f"perm: '{txt[:40]}'", matched)

# ─── Question patterns ──────────────────────────────────────────────────────

print("\n=== Question pattern detection ===")
q_texts = [
    "What should I name this file?",
    "Which one do you prefer?",
    "Could you clarify what you mean?",
    "Please choose from the following:",
]
for txt in q_texts:
    matched = any(p.search(txt) for p in _QUESTION_PATTERNS)
    check(f"question: '{txt[:40]}'", matched)

# ─── Option extraction ──────────────────────────────────────────────────────

print("\n=== Option extraction ===")
opts = _extract_options("Pick one:\n1. First\n2. Second\n3. Third")
check("extracts 3 options", len(opts) == 3)
check("first option label", opts[0][0] == "1. First")
check("first option value", opts[0][1] == "1")

opts_none = _extract_options("What should I name this?")
check("no options in plain question", len(opts_none) == 0)

opts_one = _extract_options("Only one:\n1. Single")
check("single option = no buttons (need 2+)", len(opts_one) == 0)

opts_five = _extract_options("1. A\n2. B\n3. C\n4. D\n5. E")
check("5 options = no buttons (max 4)", len(opts_five) == 0)

opts_paren = _extract_options("1) Alpha\n2) Beta")
check("parenthesis style options work", len(opts_paren) == 2)

# ─── format_event ────────────────────────────────────────────────────────────

print("\n=== format_event ===")

# Plan mode
evt_plan = WatcherEvent(
    "dex_builder_main", SessionState.PLAN_MODE, "Here is my plan: do stuff"
)
fmt_plan = format_event(evt_plan)
check("plan: has content", fmt_plan["content"] is not None)
check("plan: has view", fmt_plan["view"] is not None)
check("plan: view is PlanApprovalView", isinstance(fmt_plan["view"], PlanApprovalView))

# Permission
evt_perm = WatcherEvent(
    "dex_builder_main", SessionState.PERMISSION_REQUEST, "Allow Bash(ls)?"
)
fmt_perm = format_event(evt_perm)
check("perm: has content", fmt_perm["content"] is not None)
check("perm: view is PermissionView", isinstance(fmt_perm["view"], PermissionView))

# Question with options
evt_q_opts = WatcherEvent(
    "dex_builder_main", SessionState.WAITING_QUESTION, "Which?\n1. Alpha\n2. Beta"
)
fmt_q_opts = format_event(evt_q_opts)
check("question+opts: has view", fmt_q_opts["view"] is not None)
check(
    "question+opts: view is QuestionOptionView",
    isinstance(fmt_q_opts["view"], QuestionOptionView),
)

# Question without options
evt_q_plain = WatcherEvent(
    "dex_builder_main", SessionState.WAITING_QUESTION, "What name?"
)
fmt_q_plain = format_event(evt_q_plain)
check("question plain: no view", fmt_q_plain["view"] is None)
check("question plain: has !answer hint", "!answer" in fmt_q_plain["content"])

# Idle
evt_idle = WatcherEvent("dex_builder_main", SessionState.IDLE, "done")
fmt_idle = format_event(evt_idle)
check("idle: no content", fmt_idle["content"] is None)

# ─── Channel routing ────────────────────────────────────────────────────────

print("\n=== Channel routing ===")
builder_id = _resolve_channel_id(_BUILDER_SESSION)
product_id = _resolve_channel_id(_PRODUCT_SESSION)
unknown_id = _resolve_channel_id("unknown_session")

check("builder session resolves to int", isinstance(builder_id, int))
check("product session resolves to int", isinstance(product_id, int))
check("unknown session resolves to None", unknown_id is None)
check("builder != product", builder_id != product_id)

# ─── Watcher activity tracking ──────────────────────────────────────────────

print("\n=== Watcher activity tracking ===")
w = SessionWatcher("vps", "test_tracking")
check("last_activity is float", isinstance(w.last_activity, float))
check("last_reply_preview starts empty", w.last_reply_preview == "")

# Simulate emit
before = time.time()
w._emit(WatcherEvent("test_tracking", SessionState.IDLE, "hello world reply"))
check("last_activity updated after emit", w.last_activity >= before)
check("last_reply_preview populated", "hello world" in w.last_reply_preview)

# ─── Classify reply (watcher internal) ──────────────────────────────────────

print("\n=== Classify reply ===")
w2 = SessionWatcher("vps", "test_classify")

check(
    "permission classified",
    w2._classify_reply("Allow this tool") == SessionState.PERMISSION_REQUEST,
)
check(
    "plan classified", w2._classify_reply("Here is my plan") == SessionState.PLAN_MODE
)
check(
    "question classified",
    w2._classify_reply("line1\nline2\nwhat do you think?")
    == SessionState.WAITING_QUESTION,
)
check(
    "normal classified as idle",
    w2._classify_reply("All done, changes applied.") == SessionState.IDLE,
)

# Permission takes precedence over plan
check(
    "permission > plan precedence",
    w2._classify_reply("Allow this tool in my plan") == SessionState.PERMISSION_REQUEST,
)

# ─── Summary ────────────────────────────────────────────────────────────────

print(f"\n{'=' * 50}")
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed:
    sys.exit(1)
else:
    print("All smoke tests passed.")
    sys.exit(0)
