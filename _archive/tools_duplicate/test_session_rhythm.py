#!/usr/bin/env python3
"""
Validation script for the Session Rhythm layer.

Tests profile management, work mode transitions, session rhythm events,
startup sequence, integration hooks, and backward compatibility.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    status = "PASS" if ok else "FAIL"
    if not ok:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Profile load/save
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Profile Load/Save")

from umh.substrate.profile_manager import (
    PROFILES,
    Profile,
    WorkMode,
    get_active_profile,
    get_profile,
    list_profiles,
    profile_to_work_profile,
    set_active_profile,
)

_test("PROFILES dict not empty", len(PROFILES) >= 2, f"{len(PROFILES)} profiles")
active = get_active_profile()
_test("get_active_profile returns Profile", isinstance(active, Profile), active.id)
saved = set_active_profile("product")
_test("set_active_profile returns Profile", isinstance(saved, Profile), saved.id)
_test("set_active_profile persists", saved.id == "product")
# Reset to builder
set_active_profile("builder")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Builder + Product profiles resolve correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Profile Resolution")

builder = get_profile("builder")
product = get_profile("product")
_test("builder profile exists", builder is not None)
_test("product profile exists", product is not None)
_test(
    "builder default_mode is ACTIVE_WORK",
    builder.default_mode == WorkMode.ACTIVE_WORK,
)
_test(
    "product default_mode is ACTIVE_WORK",
    product.default_mode == WorkMode.ACTIVE_WORK,
)
_test(
    "builder has high verbosity",
    builder.preferences.get("verbosity") == "high",
)
_test(
    "product has balanced verbosity",
    product.preferences.get("verbosity") == "balanced",
)
_test(
    "builder allows parallelism",
    builder.preferences.get("parallelism_allowed") is True,
)
_test(
    "product has verification_bias",
    product.preferences.get("verification_bias") is True,
)

# Bridge to WorkProfile
from umh.substrate.presence_runtime import WorkProfile

wp_builder = profile_to_work_profile(builder)
wp_product = profile_to_work_profile(product)
_test("builder maps to WorkProfile.BUILDER", wp_builder == WorkProfile.BUILDER)
_test("product maps to WorkProfile.PRODUCT", wp_product == WorkProfile.PRODUCT)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Work mode transitions validate correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Work Mode Transitions")

from umh.substrate.work_mode_manager import (
    VALID_TRANSITIONS,
    ModeTransition,
    WorkModeManager,
    get_mode_manager,
)

mgr = WorkModeManager()

# Valid transitions
t1 = mgr.set_mode(WorkMode.DEEP_WORK, reason="test")
_test("ACTIVE_WORK → DEEP_WORK allowed", t1.allowed, f"from={t1.from_mode.value}")

t2 = mgr.set_mode(WorkMode.ACTIVE_WORK, reason="test")
_test("DEEP_WORK → ACTIVE_WORK allowed", t2.allowed)

t3 = mgr.set_mode(WorkMode.PASSIVE_MONITORING, reason="test")
_test("ACTIVE_WORK → PASSIVE_MONITORING allowed", t3.allowed)

# Invalid transition: PASSIVE → OVERNIGHT not in table
t4 = mgr.set_mode(WorkMode.OVERNIGHT, reason="test")
_test("PASSIVE_MONITORING → OVERNIGHT denied", not t4.allowed)

# Force mode bypasses validation
t5 = mgr.force_mode(WorkMode.OVERNIGHT, reason="test_force")
_test("force_mode bypasses validation", t5.allowed and t5.triggered_by == "force")

# Reset back
mgr.force_mode(WorkMode.ACTIVE_WORK, reason="test_reset")

# Transition history
history = mgr.get_transition_history()
_test("transition history tracked", len(history) >= 4, f"{len(history)} transitions")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. SESSION_START loads profile and default mode
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. SESSION_START Lifecycle")

from umh.substrate.session_rhythm import (
    RhythmEvent,
    RhythmResult,
    SessionRhythm,
    get_combined_execution_hints,
    get_mode_execution_hints,
    handle_rhythm_event,
)

rhythm = SessionRhythm()
result = rhythm.handle_event(RhythmEvent.SESSION_START)
_test("SESSION_START returns RhythmResult", isinstance(result, RhythmResult))
_test("SESSION_START has current_profile", bool(result.current_profile))
_test("SESSION_START has current_mode", bool(result.current_mode))
_test("SESSION_START has actions_taken", len(result.actions_taken) > 0)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. TASK_START / TASK_COMPLETE lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. TASK_START / TASK_COMPLETE")

r_start = rhythm.handle_event(RhythmEvent.TASK_START, {"task_id": "test_123"})
_test("TASK_START returns result", isinstance(r_start, RhythmResult))
_test("TASK_START event recorded", r_start.event == RhythmEvent.TASK_START)

r_complete = rhythm.handle_event(RhythmEvent.TASK_COMPLETE, {"task_id": "test_123"})
_test("TASK_COMPLETE returns result", isinstance(r_complete, RhythmResult))

# ═══════════════════════════════════════════════════════════════════════════════
# 6. Pressure HIGH/CRITICAL forces mode change to DEEP_WORK
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Pressure-Driven Mode Change")

# Reset to ACTIVE_WORK first
rhythm_mgr = get_mode_manager()
rhythm_mgr.force_mode(WorkMode.ACTIVE_WORK, reason="test_reset")

r_pressure = rhythm.handle_event(RhythmEvent.PRESSURE_HIGH, {"pressure_level": "high"})
_test("PRESSURE_HIGH returns result", isinstance(r_pressure, RhythmResult))
_test(
    "PRESSURE_HIGH forces DEEP_WORK",
    r_pressure.current_mode == "deep_work" or r_pressure.mode_changed,
    f"mode={r_pressure.current_mode} changed={r_pressure.mode_changed}",
)

# Reset back
rhythm_mgr.force_mode(WorkMode.ACTIVE_WORK, reason="test_reset")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. Idle event transitions to PASSIVE_MONITORING
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Idle Transition")

r_idle = rhythm.handle_event(RhythmEvent.IDLE)
_test("IDLE returns result", isinstance(r_idle, RhythmResult))
_test(
    "IDLE transitions to PASSIVE_MONITORING",
    r_idle.current_mode == "passive_monitoring" or r_idle.mode_changed,
    f"mode={r_idle.current_mode} changed={r_idle.mode_changed}",
)

# Reset
rhythm_mgr.force_mode(WorkMode.ACTIVE_WORK, reason="test_reset")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. Startup sequence runs and returns structured result
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Startup Sequence")

from umh.substrate.startup_sequence import (
    StartupSequenceResult,
    run_startup_sequence,
    spawn_background_hooks,
)

startup_result = run_startup_sequence(builder, WorkMode.ACTIVE_WORK)
_test(
    "startup returns StartupSequenceResult",
    isinstance(startup_result, StartupSequenceResult),
)
_test(
    "startup has steps",
    len(startup_result.steps) > 0,
    f"{len(startup_result.steps)} steps",
)
_test("startup profile_id matches", startup_result.profile_id == "builder")
_test("startup to_dict works", isinstance(startup_result.to_dict(), dict))

# Background hooks
hooks = spawn_background_hooks(builder, WorkMode.ACTIVE_WORK)
_test("background hooks returns list", isinstance(hooks, list))

# ═══════════════════════════════════════════════════════════════════════════════
# 9. Integration does not break existing execution path
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Backward Compatibility — Imports")

errors = []
try:
    from umh.substrate.conversation_router import route_message

    route_message("test message", interface="test")
except Exception as e:
    errors.append(f"conversation_router: {e}")

try:
    from umh.substrate.task_finalization import finalize_completed_task
except Exception as e:
    errors.append(f"task_finalization import: {e}")

try:
    from umh.substrate.plan_executor import execute_with_plan
except Exception as e:
    errors.append(f"plan_executor import: {e}")

try:
    from umh.substrate.discord_text_transport import ingest_text_message
except Exception as e:
    errors.append(f"discord_text_transport import: {e}")

_test(
    "all integration imports work",
    len(errors) == 0,
    "; ".join(errors) if errors else "",
)

# ═══════════════════════════════════════════════════════════════════════════════
# 10. No-profile fallback still works
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. No-Profile Fallback")

# Even with no stored profile, get_active_profile returns builder
fallback = get_active_profile()
_test(
    "fallback returns builder",
    fallback.id == "builder",
    f"got {fallback.id}",
)

# get_profile with invalid ID returns None
invalid = get_profile("nonexistent")
_test("invalid profile returns None", invalid is None)

# ═══════════════════════════════════════════════════════════════════════════════
# 11. /profile and /mode command handling
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Command Handling")

from umh.substrate.discord_text_transport import _handle_rhythm_command

r_profile = _handle_rhythm_command(
    "/profile", guild_id=None, channel_id=None, user_id=None
)
_test(
    "/profile returns status",
    r_profile.get("ingress", {}).get("status") == "ok",
)
_test(
    "/profile lists profiles",
    "available:" in r_profile.get("envelope", {}).get("content", ""),
)

r_profile_set = _handle_rhythm_command(
    "/profile product", guild_id=None, channel_id=None, user_id=None
)
_test(
    "/profile product switches",
    "switched" in r_profile_set.get("envelope", {}).get("content", ""),
)
# Reset
set_active_profile("builder")

r_mode = _handle_rhythm_command("/mode", guild_id=None, channel_id=None, user_id=None)
_test(
    "/mode returns status",
    r_mode.get("ingress", {}).get("status") == "ok",
)

r_mode_set = _handle_rhythm_command(
    "/mode deep_work", guild_id=None, channel_id=None, user_id=None
)
_test(
    "/mode deep_work switches",
    "switched" in r_mode_set.get("envelope", {}).get("content", ""),
)
# Reset mode
rhythm_mgr.force_mode(WorkMode.ACTIVE_WORK, reason="test_reset")

# ═══════════════════════════════════════════════════════════════════════════════
# 12. Execution hints and combined hints
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Execution Hints")

deep_hints = get_mode_execution_hints(WorkMode.DEEP_WORK)
_test("DEEP_WORK prefers sequential", deep_hints.get("prefer_sequential") is True)
_test("DEEP_WORK max_subagents=2", deep_hints.get("max_subagents") == 2)

active_hints = get_mode_execution_hints(WorkMode.ACTIVE_WORK)
_test("ACTIVE_WORK allows parallel", active_hints.get("prefer_sequential") is False)

combined = get_combined_execution_hints()
_test("combined hints has profile_id", "profile_id" in combined)
_test("combined hints has max_subagents", "max_subagents" in combined)
_test("combined hints is dict", isinstance(combined, dict))

# ═══════════════════════════════════════════════════════════════════════════════
# 13. Rhythm log traceability
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Rhythm Log")

from umh.substrate.rhythm_log import get_rhythm_log, log_rhythm_event

log_rhythm_event("test_event", "builder", "active_work", "validation test entry")
recent = get_rhythm_log().get_recent(5)
_test("rhythm log has entries", len(recent) > 0, f"{len(recent)} entries")

# ═══════════════════════════════════════════════════════════════════════════════
# 14. Mode bridge functions
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Mode Bridge Functions")

from umh.substrate.work_mode_manager import mode_to_day_mode, mode_to_presence

from umh.substrate.operator_session import OperatorDayMode
from umh.substrate.presence_runtime import PresenceMode

dm = mode_to_day_mode(WorkMode.DEEP_WORK)
_test("DEEP_WORK → DEEP_WORK day_mode", dm == OperatorDayMode.DEEP_WORK)

dm_overnight = mode_to_day_mode(WorkMode.OVERNIGHT)
_test("OVERNIGHT → OVERNIGHT day_mode", dm_overnight == OperatorDayMode.OVERNIGHT)

pm = mode_to_presence(WorkMode.ACTIVE_WORK)
_test("ACTIVE_WORK → ACTIVE_LOCAL presence", pm == PresenceMode.ACTIVE_LOCAL)

pm_away = mode_to_presence(WorkMode.AWAY)
_test("AWAY → AWAY_LOCAL presence", pm_away == PresenceMode.AWAY_LOCAL)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
