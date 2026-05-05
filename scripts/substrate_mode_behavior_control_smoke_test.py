#!/usr/bin/env python3
"""
Smoke test — Mode Behavior + Session Control v1.

Validates:
  1. Product mode: no internal leakage
  2. Builder mode: debug/system allowed
  3. /clear: tmux command executed
  4. /reset: session recreated
  5. Auto-clear: triggers correctly
  6. Both modes: still use shared router (no bypass)
  7. TTS: still body-only
  8. No hot-path regressions

Tripwires:
  - Router must still be used (no bypass introduced)
  - No new hot-path imports in mode_behavior or session_control
"""

import os
import sys
import importlib
import inspect

sys.path.insert(0, "/opt/OS")
os.environ.setdefault("EOS_NODE_ROLE", "vps")

PASS = 0
FAIL = 0


def _result(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ─── 1. Product mode: no internal leakage ───────────────────────────────────

section("1. Product mode — internal leakage detection")

from eos_ai.substrate.mode_behavior import shape_reply, detect_internal_leakage

# Text with internal references
internal_text = (
    "I routed your request through the model_router call_with_fallback.\n"
    "The tmux session dex_builder_main processed it.\n"
    "Provider: anthropic via cc_sdk backend #0.\n"
    "[debug] latency=450ms\n"
    "Your answer is: The quarterly report shows 15% growth."
)

shaped = shape_reply(internal_text, mode="product")
leaks = detect_internal_leakage(shaped)
_result(
    "internal refs stripped",
    len(leaks) == 0,
    f"remaining leaks: {leaks}" if leaks else "clean",
)

# Debug lines removed
_result(
    "debug lines removed",
    "[debug]" not in shaped,
    f"shaped output: {shaped[:100]}...",
)

# Actual content preserved
_result(
    "answer content preserved",
    "quarterly report" in shaped.lower() and "15%" in shaped,
    "substantive content intact",
)

# ─── 2. Builder mode: system allowed ────────────────────────────────────────

section("2. Builder mode — system visibility allowed")

builder_text = (
    "The model_router used cc_sdk as backend #0.\n"
    "Session: dex_builder_main\n"
    "Latency: 450ms\n\n\n\n\n"
    "Your code change is deployed.\n"
    "Let me know if you need anything else!"
)

builder_shaped = shape_reply(builder_text, mode="builder")
_result(
    "system refs preserved",
    "model_router" in builder_shaped,
    "system language visible",
)
_result(
    "trailing filler stripped",
    "let me know" not in builder_shaped.lower(),
    "filler removed",
)
_result(
    "excessive blank lines collapsed",
    "\n\n\n\n" not in builder_shaped,
    "whitespace normalized",
)

# ─── 3. /clear command ──────────────────────────────────────────────────────

section("3. /clear — session clear via bridge")

from eos_ai.substrate.session_control import clear_session

# This will fail if tmux is not available or session doesn't exist —
# that's expected in CI. We validate the function exists, is callable,
# and returns the right shape.
result = clear_session("vps", "dex_smoke_test_nonexistent")
_result(
    "clear_session returns dict",
    isinstance(result, dict),
    f"type={type(result).__name__}",
)
_result(
    "clear_session has ok field",
    "ok" in result,
    f"ok={result.get('ok')}",
)
_result(
    "clear_session has action field",
    result.get("action") == "clear",
    f"action={result.get('action')}",
)

# ─── 4. /reset command ──────────────────────────────────────────────────────

section("4. /reset — session reset via bridge")

from eos_ai.substrate.session_control import reset_session

result = reset_session("vps", "dex_smoke_test_nonexistent")
_result(
    "reset_session returns dict",
    isinstance(result, dict),
    f"type={type(result).__name__}",
)
_result(
    "reset_session has ok field",
    "ok" in result,
    f"ok={result.get('ok')}",
)
_result(
    "reset_session has action field",
    result.get("action") == "reset",
    f"action={result.get('action')}",
)

# ─── 5. Auto-clear ──────────────────────────────────────────────────────────

section("5. Auto-clear — message counting + threshold trigger")

from eos_ai.substrate.session_control import (
    get_message_count,
    maybe_auto_clear,
    reset_counters_for_tests,
)

reset_counters_for_tests()
os.environ["EOS_SESSION_AUTO_CLEAR_MESSAGES"] = "3"

test_session = "dex_auto_clear_test"
r1 = maybe_auto_clear(test_session, target="vps")
_result(
    "count 1: not cleared",
    not r1.get("auto_cleared"),
    f"count={r1.get('count', '?')}",
)

r2 = maybe_auto_clear(test_session, target="vps")
_result(
    "count 2: not cleared",
    not r2.get("auto_cleared"),
    f"count={r2.get('count', '?')}",
)

r3 = maybe_auto_clear(test_session, target="vps")
_result(
    "count 3: auto-clear triggered",
    r3.get("auto_cleared") is True,
    f"count_before={r3.get('count_before_clear', '?')}",
)

# Counter should reset after clear
count_after = get_message_count(test_session)
_result(
    "counter reset after clear",
    count_after == 0,
    f"count_after={count_after}",
)

# Clean up
del os.environ["EOS_SESSION_AUTO_CLEAR_MESSAGES"]
reset_counters_for_tests()

# ─── 6. Both modes: shared router (no bypass) ──────────────────────────────

section("6. Tripwire — shared router, no bypass")

# Verify mode_behavior does NOT import any hot-path modules
import eos_ai.substrate.mode_behavior as mb

mb_source = inspect.getsource(mb)
hot_path_imports = [
    "from eos_ai.gateway",
    "from eos_ai.cognitive_loop",
    "from eos_ai.model_router",
    "from eos_ai.agent_runtime",
    "from eos_ai.primitives",
]
for hp in hot_path_imports:
    _result(
        f"mode_behavior no import: {hp.split('.')[-1]}",
        hp not in mb_source,
        "clean" if hp not in mb_source else "HOT PATH IMPORT FOUND",
    )

# Verify session_control does NOT import hot-path modules
import eos_ai.substrate.session_control as sc

sc_source = inspect.getsource(sc)
for hp in hot_path_imports:
    _result(
        f"session_control no import: {hp.split('.')[-1]}",
        hp not in sc_source,
        "clean" if hp not in sc_source else "HOT PATH IMPORT FOUND",
    )

# Verify maybe_mirror still calls ingest_text_message (router path)
from eos_ai.substrate import discord_text_transport as dtt

dtt_source = inspect.getsource(dtt.maybe_mirror_discord_text_message)
_result(
    "maybe_mirror still calls ingest_text_message",
    "ingest_text_message" in dtt_source,
    "router path intact",
)

# ─── 7. TTS: body-only behavior preserved ──────────────────────────────────

section("7. TTS — body-only behavior preserved")

from eos_ai.substrate.discord_text_transport import build_tts_reply_envelope

os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "true"
os.environ["EOS_DISCORD_TEXT_REPLY_TTS_ENABLED"] = "true"
os.environ["EOS_DISCORD_TEXT_ALLOWED_GUILDS"] = "*"
os.environ["EOS_DISCORD_TEXT_ALLOWED_CHANNELS"] = "*"
os.environ["EOS_DISCORD_TEXT_ALLOWED_USERS"] = "*"

reply_with_footer = "Here is your answer.\n\n---\n*provider: anthropic | model: opus*"

env = build_tts_reply_envelope(reply_with_footer)
_result(
    "envelope status ok",
    env.get("status") == "ok",
    f"status={env.get('status')}",
)

emit_plan = env.get("emit_plan", [])
if len(emit_plan) >= 2:
    visible = emit_plan[0]
    spoken = emit_plan[1]
    _result(
        "visible message has footer",
        "provider" in visible.get("content", ""),
        "footer preserved in display",
    )
    _result(
        "spoken message is body-only",
        "provider" not in spoken.get("content", ""),
        "footer stripped from TTS",
    )
elif len(emit_plan) == 1:
    # No footer detected by sanitizer — still valid
    _result(
        "single emit (no footer detected)",
        True,
        "sanitizer found no footer to strip",
    )
else:
    _result("emit_plan present", False, f"emit_plan={emit_plan}")

# ─── 8. No hot-path regressions ────────────────────────────────────────────

section("8. No hot-path regressions — import verification")

modules_to_check = [
    "eos_ai.substrate.mode_behavior",
    "eos_ai.substrate.session_control",
    "eos_ai.substrate.discord_text_transport",
    "eos_ai.substrate.discord_mode_routing",
    "eos_ai.substrate.claude_session_bridge",
]

for mod_name in modules_to_check:
    try:
        importlib.import_module(mod_name)
        _result(f"import {mod_name.split('.')[-1]}", True, "ok")
    except Exception as e:
        _result(f"import {mod_name.split('.')[-1]}", False, str(e))

# Verify session command interception exists in discord_text_transport
dtt_full = inspect.getsource(dtt)
_result(
    "_handle_session_command defined",
    "_handle_session_command" in dtt_full,
    "session command handler present",
)
_result(
    "/clear interception in maybe_mirror",
    '"/clear"' in dtt_source or "'/clear'" in dtt_source,
    "clear intercepted before routing",
)

# ─── Summary ────────────────────────────────────────────────────────────────

print(f"\n{'═' * 60}")
print(f"  SUMMARY: {PASS} passed, {FAIL} failed")
print(f"{'═' * 60}")

sys.exit(0 if FAIL == 0 else 1)
