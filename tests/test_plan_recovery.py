"""
Test suite: Plan Recovery + Orphan Attribution + Persistence Hardening + Observability.

Validates the four planner stability gaps:
    A. Step recovery (retry / skip / deactivate)
    B. Orphan attribution fallback (direct → active_goal → blended → fallback)
    C. Persistence hardening (bounded, safe restore, stale pruning)
    D. Plan observability (trace fields for recovery state)

No LLM calls. No randomness. Deterministic assertions only.
"""

import sys

sys.path.insert(0, "/opt/OS")

_pass = 0
_fail = 0
_total = 0


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _test(label: str, condition: bool, detail: str = "") -> None:
    global _pass, _fail, _total
    _total += 1
    if condition:
        _pass += 1
        extra = f" -- {detail}" if detail else ""
        print(f"  [PASS] {label}{extra}")
    else:
        _fail += 1
        extra = f" -- {detail}" if detail else ""
        print(f"  [FAIL] {label}{extra}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports")

try:
    from umh.runtime_engine.hierarchical_planning import (
        Plan,
        PlanEngine,
        PlanProgress,
        PlanStep,
        StepRecoveryState,
        MAX_STEP_RETRIES,
        RETRY_COOLDOWN,
        MAX_FAILURE_STREAK,
        PLAN_STALE_TURNS,
        MAX_PLANS,
        MAX_STEPS,
        REPLAN_THRESHOLD,
        get_plan_engine,
        reset_plan_engine,
        _valid_step_ordering,
    )
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
    from umh.runtime_engine.persistence import (
        save_plans,
        load_plans,
        _reset_buffer_for_tests,
    )

    _test("all imports succeed", True)
except Exception as e:
    _test("all imports succeed", False, str(e))
    print(f"FATAL: {e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants exist
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Constants")

_test("MAX_STEP_RETRIES = 2", MAX_STEP_RETRIES == 2)
_test("RETRY_COOLDOWN = 1", RETRY_COOLDOWN == 1)
_test("MAX_FAILURE_STREAK = 2", MAX_FAILURE_STREAK == 2)
_test("PLAN_STALE_TURNS = 10", PLAN_STALE_TURNS == 10)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. StepRecoveryState basics
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. StepRecoveryState")

_rec = StepRecoveryState()
_test("default status is pending", _rec.status == "pending")
_test("default retry_count is 0", _rec.retry_count == 0)
_test("default failure_streak is 0", _rec.failure_streak == 0)

_rec_d = _rec.to_dict()
_test("to_dict has status", _rec_d["status"] == "pending")
_test("to_dict has retry_count", _rec_d["retry_count"] == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PlanProgress with recovery
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. PlanProgress recovery integration")

_prog = PlanProgress(plan_id="test")
_r = _prog.get_recovery("g1")
_test("get_recovery creates state", isinstance(_r, StepRecoveryState))
_test("same object on second call", _prog.get_recovery("g1") is _r)

_pd = _prog.to_dict()
_test("step_recovery in to_dict", "step_recovery" in _pd)
_test("skipped_steps in to_dict", "skipped_steps" in _pd)
_test("last_activity_turn in to_dict", "last_activity_turn" in _pd)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Step recovery — retry on first failure
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Step retry on first failure")

reset_plan_engine()

_plan_retry = Plan(
    plan_id="retry_plan",
    root_goal_id="rg1",
    steps=(
        PlanStep(goal_id="rg1", position=0),
        PlanStep(goal_id="rg2", position=1, dependency_ids=("rg1",)),
    ),
    dependencies=(("rg1", "rg2"),),
    expected_value=0.7,
    confidence=0.8,
    horizon=2,
    creation_turn=0,
)

_pe = PlanEngine()
_pe._plans["retry_plan"] = _plan_retry
_pe._progress["retry_plan"] = PlanProgress(plan_id="retry_plan", confidence=0.8)
_pe._active_plan_id = "retry_plan"

# First failure: should become retry_pending
_pe.record_step_outcome("retry_plan", "rg1", 0.1, current_turn=1)
_rp = _pe.get_progress("retry_plan")
_rec_rg1 = _rp.get_recovery("rg1")
_test("first failure → retry_pending", _rec_rg1.status == "retry_pending")
_test("retry_count = 1", _rec_rg1.retry_count == 1)
_test("failure_streak = 1", _rec_rg1.failure_streak == 1)
_test("plan still active after first failure", _rp.active)

# During cooldown, step should not be ready
from umh.runtime_engine.hierarchical_planning import _get_next_ready_step

_next = _get_next_ready_step(_plan_retry, _rp, current_turn=1)
_test("during cooldown: step not ready", _next is None)

# After cooldown, step should be ready again
_next = _get_next_ready_step(_plan_retry, _rp, current_turn=2)
_test("after cooldown: step is ready", _next is not None and _next.goal_id == "rg1")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Step recovery — retry limit enforced → blocking step deactivates plan
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Retry limit → blocking step → plan deactivated")

reset_plan_engine()

_plan_block = Plan(
    plan_id="block_plan",
    root_goal_id="bg1",
    steps=(
        PlanStep(goal_id="bg1", position=0),
        PlanStep(goal_id="bg2", position=1, dependency_ids=("bg1",)),
    ),
    dependencies=(("bg1", "bg2"),),
    expected_value=0.7,
    confidence=0.9,
    horizon=2,
    creation_turn=0,
)

_pe2 = PlanEngine()
_pe2._plans["block_plan"] = _plan_block
_pe2._progress["block_plan"] = PlanProgress(plan_id="block_plan", confidence=0.9)
_pe2._active_plan_id = "block_plan"

# First failure
_pe2.record_step_outcome("block_plan", "bg1", 0.1, current_turn=1)
_rp2 = _pe2.get_progress("block_plan")
_test("first fail: retry_pending", _rp2.get_recovery("bg1").status == "retry_pending")

# Second failure (exceeds MAX_STEP_RETRIES=2, meets MAX_FAILURE_STREAK=2)
_pe2.record_step_outcome("block_plan", "bg1", 0.05, current_turn=3)
_rec2 = _rp2.get_recovery("bg1")
_test("retry_count = 2", _rec2.retry_count == 2)
_test("failure_streak = 2", _rec2.failure_streak == 2)
_test("status = failed_final (blocking)", _rec2.status == "failed_final")
_test("plan deactivated (blocking step)", not _rp2.active)
_test("bg1 in failed_steps", "bg1" in _rp2.failed_steps)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Step recovery — non-blocking step gets skipped
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Non-blocking step → skipped")

reset_plan_engine()

_plan_skip = Plan(
    plan_id="skip_plan",
    root_goal_id="sg1",
    steps=(
        PlanStep(goal_id="sg1", position=0),
        PlanStep(goal_id="sg2", position=1),  # no dependency on sg1
    ),
    dependencies=(),
    expected_value=0.7,
    confidence=0.9,
    horizon=2,
    creation_turn=0,
)

_pe3 = PlanEngine()
_pe3._plans["skip_plan"] = _plan_skip
_pe3._progress["skip_plan"] = PlanProgress(plan_id="skip_plan", confidence=0.9)
_pe3._active_plan_id = "skip_plan"

# Fail sg1 twice to exceed retries
_pe3.record_step_outcome("skip_plan", "sg1", 0.1, current_turn=1)
_pe3.record_step_outcome("skip_plan", "sg1", 0.05, current_turn=3)

_rp3 = _pe3.get_progress("skip_plan")
_rec3 = _rp3.get_recovery("sg1")
_test("non-blocking: status = skipped", _rec3.status == "skipped")
_test("sg1 in skipped_steps", "sg1" in _rp3.skipped_steps)
_test("sg1 NOT in failed_steps", "sg1" not in _rp3.failed_steps)
_test("plan still active (non-blocking skip)", _rp3.active)

# sg2 should still be reachable
_next3 = _get_next_ready_step(_plan_skip, _rp3, current_turn=4)
_test("sg2 reachable after sg1 skipped", _next3 is not None and _next3.goal_id == "sg2")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Step recovery — success resets failure state
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Success resets failure state")

reset_plan_engine()

_pe4 = PlanEngine()
_plan_reset = Plan(
    plan_id="reset_plan",
    root_goal_id="rr1",
    steps=(PlanStep(goal_id="rr1", position=0),),
    dependencies=(),
    expected_value=0.7,
    confidence=0.8,
    horizon=1,
    creation_turn=0,
)
_pe4._plans["reset_plan"] = _plan_reset
_pe4._progress["reset_plan"] = PlanProgress(plan_id="reset_plan", confidence=0.8)

# Fail once
_pe4.record_step_outcome("reset_plan", "rr1", 0.1, current_turn=1)
_rp4 = _pe4.get_progress("reset_plan")
_test("after fail: retry_pending", _rp4.get_recovery("rr1").status == "retry_pending")

# Succeed
_pe4.record_step_outcome("reset_plan", "rr1", 0.8, current_turn=3)
_rec4 = _rp4.get_recovery("rr1")
_test("after success: status = completed", _rec4.status == "completed")
_test("after success: failure_streak = 0", _rec4.failure_streak == 0)
_test("rr1 in completed_steps", "rr1" in _rp4.completed_steps)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. _is_step_blocking
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Blocking detection")

_pe5 = PlanEngine()
_plan_dep = Plan(
    plan_id="dep_plan",
    root_goal_id="d1",
    steps=(
        PlanStep(goal_id="d1", position=0),
        PlanStep(goal_id="d2", position=1, dependency_ids=("d1",)),
        PlanStep(goal_id="d3", position=2),  # independent
    ),
    dependencies=(("d1", "d2"),),
    expected_value=0.7,
    confidence=0.8,
    horizon=3,
    creation_turn=0,
)

_test("d1 is blocking (d2 depends on it)", _pe5._is_step_blocking(_plan_dep, "d1"))
_test("d3 is NOT blocking", not _pe5._is_step_blocking(_plan_dep, "d3"))
_test("d2 is NOT blocking", not _pe5._is_step_blocking(_plan_dep, "d2"))


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Orphan attribution fallback — direct source
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Attribution source: direct")

_trace_direct = build_trace(
    turn_id=1,
    plan_step_goal_id="g1",
    plan_step_attributed_score=0.85,
    plan_step_attribution_source="direct",
)
_test(
    "attribution_source = direct",
    _trace_direct.plan_step_attribution_source == "direct",
)
_td = _trace_direct.to_dict()
_test(
    "in dict: plan_step_attribution_source",
    _td.get("plan_step_attribution_source") == "direct",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Orphan attribution fallback — active_goal source
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Attribution source: active_goal")

_trace_active = build_trace(
    turn_id=2,
    plan_step_goal_id="g2",
    plan_step_attributed_score=0.7,
    plan_step_attribution_source="active_goal",
)
_test(
    "attribution_source = active_goal",
    _trace_active.plan_step_attribution_source == "active_goal",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Orphan attribution fallback — blended source
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Attribution source: blended")

_trace_blend = build_trace(
    turn_id=3,
    plan_step_goal_id="g3",
    plan_step_attributed_score=0.65,
    plan_step_attribution_source="blended",
)
_test(
    "attribution_source = blended",
    _trace_blend.plan_step_attribution_source == "blended",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Orphan attribution fallback — neutral fallback
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Attribution source: fallback")

_trace_fb = build_trace(
    turn_id=4,
    plan_step_goal_id="orphan_g",
    plan_step_attributed_score=0.0,
    plan_step_attribution_source="fallback",
)
_test(
    "attribution_source = fallback",
    _trace_fb.plan_step_attribution_source == "fallback",
)
_test("fallback score = 0.0", _trace_fb.plan_step_attributed_score == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. DecisionTrace observability fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Observability fields on trace")

_trace_obs = build_trace(
    turn_id=5,
    active_plan_id="p1",
    active_plan_step="g1",
    plan_confidence=0.75,
    plan_count=2,
    plan_step_goal_id="g1",
    plan_step_attributed_score=0.8,
    plan_step_attribution_source="direct",
    plan_step_status="retry_pending",
    plan_step_retry_count=1,
    plan_step_failure_streak=1,
)

_test("active_plan_id on trace", _trace_obs.active_plan_id == "p1")
_test("active_plan_step on trace", _trace_obs.active_plan_step == "g1")
_test("plan_step_status on trace", _trace_obs.plan_step_status == "retry_pending")
_test("plan_step_retry_count on trace", _trace_obs.plan_step_retry_count == 1)
_test("plan_step_failure_streak on trace", _trace_obs.plan_step_failure_streak == 1)
_test(
    "plan_step_attribution_source on trace",
    _trace_obs.plan_step_attribution_source == "direct",
)

_od = _trace_obs.to_dict()
_test("plan_step_status in dict", _od.get("plan_step_status") == "retry_pending")
_test("plan_step_retry_count in dict", _od.get("plan_step_retry_count") == 1)
_test("plan_step_failure_streak in dict", _od.get("plan_step_failure_streak") == 1)
_test(
    "plan_step_attribution_source in dict",
    _od.get("plan_step_attribution_source") == "direct",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. No observability fields when no plan active
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. No fields when no plan")

_trace_none = build_trace(turn_id=6)
_test("plan_step_status is None", _trace_none.plan_step_status is None)
_test("plan_step_retry_count is None", _trace_none.plan_step_retry_count is None)
_test("plan_step_failure_streak is None", _trace_none.plan_step_failure_streak is None)
_test(
    "plan_step_attribution_source is None",
    _trace_none.plan_step_attribution_source is None,
)

_nd = _trace_none.to_dict()
_test("plan_step_status not in dict", "plan_step_status" not in _nd)
_test("plan_step_retry_count not in dict", "plan_step_retry_count" not in _nd)
_test(
    "plan_step_attribution_source not in dict",
    "plan_step_attribution_source" not in _nd,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Persistence hardening — MAX_STEPS enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Persistence: MAX_STEPS enforcement")

reset_plan_engine()
_pe_h = PlanEngine()

_too_many_steps = {
    "plans": {
        "big_plan": {
            "plan_id": "big_plan",
            "root_goal_id": "s0",
            "steps": [
                {
                    "goal_id": f"s{i}",
                    "position": i,
                    "dependency_ids": [f"s{i - 1}"] if i > 0 else [],
                }
                for i in range(MAX_STEPS + 3)
            ],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": MAX_STEPS + 3,
            "creation_turn": 0,
        }
    },
    "progress": {
        "big_plan": {
            "plan_id": "big_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
        }
    },
    "active_plan_id": "big_plan",
    "last_generation_turn": 0,
}

_pe_h.restore(_too_many_steps)
_test("plan with too many steps dropped", "big_plan" not in _pe_h._plans)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Persistence hardening — corrupted plan dropped
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Corrupted plan dropped")

reset_plan_engine()
_pe_c = PlanEngine()

_corrupt = {
    "plans": {
        "good_plan": {
            "plan_id": "good_plan",
            "root_goal_id": "g1",
            "steps": [{"goal_id": "g1", "position": 0}],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 1,
            "creation_turn": 0,
        },
        "bad_plan": {
            "plan_id": "bad_plan",
            "root_goal_id": "x1",
            # missing "steps" key — should cause corruption
        },
    },
    "progress": {
        "good_plan": {
            "plan_id": "good_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
        },
        "bad_plan": {
            "plan_id": "bad_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
        },
    },
    "active_plan_id": "good_plan",
    "last_generation_turn": 0,
}

_pe_c.restore(_corrupt)
_test("good plan survives", "good_plan" in _pe_c._plans)
_test("bad plan dropped", "bad_plan" not in _pe_c._plans)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Persistence hardening — impossible step ordering
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Impossible step ordering dropped")

reset_plan_engine()
_pe_o = PlanEngine()

# Step at position 0 depends on step at position 1 (backward dependency)
_cycle = {
    "plans": {
        "cycle_plan": {
            "plan_id": "cycle_plan",
            "root_goal_id": "c1",
            "steps": [
                {"goal_id": "c1", "position": 0, "dependency_ids": ["c2"]},
                {"goal_id": "c2", "position": 1},
            ],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 2,
            "creation_turn": 0,
        }
    },
    "progress": {
        "cycle_plan": {
            "plan_id": "cycle_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
        }
    },
    "active_plan_id": "cycle_plan",
    "last_generation_turn": 0,
}

_pe_o.restore(_cycle)
_test("cycle plan dropped", "cycle_plan" not in _pe_o._plans)
_test("active_plan_id cleared", _pe_o._active_plan_id is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Persistence hardening — stale plan pruned
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Stale plan pruned")

reset_plan_engine()
_pe_s = PlanEngine()

_stale = {
    "plans": {
        "stale_plan": {
            "plan_id": "stale_plan",
            "root_goal_id": "sp1",
            "steps": [{"goal_id": "sp1", "position": 0}],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 1,
            "creation_turn": 0,
        },
        "fresh_plan": {
            "plan_id": "fresh_plan",
            "root_goal_id": "fp1",
            "steps": [{"goal_id": "fp1", "position": 0}],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 1,
            "creation_turn": 0,
        },
    },
    "progress": {
        "stale_plan": {
            "plan_id": "stale_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
            "last_activity_turn": 0,
        },
        "fresh_plan": {
            "plan_id": "fresh_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
            "last_activity_turn": 18,
        },
    },
    "active_plan_id": "fresh_plan",
    "last_generation_turn": 0,
}

_pe_s.restore(_stale, current_turn=20)
_test("stale plan pruned", "stale_plan" not in _pe_s._plans)
_test("fresh plan survives", "fresh_plan" in _pe_s._plans)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Persistence hardening — MAX_PLANS cap on restore
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. MAX_PLANS cap on restore")

reset_plan_engine()
_pe_cap = PlanEngine()

_many = {"plans": {}, "progress": {}, "active_plan_id": None, "last_generation_turn": 0}
for i in range(MAX_PLANS + 3):
    pid = f"cap_plan_{i}"
    _many["plans"][pid] = {
        "plan_id": pid,
        "root_goal_id": f"cg{i}",
        "steps": [{"goal_id": f"cg{i}", "position": 0}],
        "dependencies": [],
        "expected_value": 0.5,
        "confidence": 0.5,
        "horizon": 1,
        "creation_turn": 0,
    }
    _many["progress"][pid] = {
        "plan_id": pid,
        "completed_steps": [],
        "failed_steps": [],
        "step_scores": {},
        "confidence": 0.3 + i * 0.1,
        "active": True,
        "last_activity_turn": 10,
    }

_pe_cap.restore(_many)
_test(
    f"at most MAX_PLANS={MAX_PLANS}",
    len(_pe_cap._plans) <= MAX_PLANS,
    f"got {len(_pe_cap._plans)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Persistence hardening — completed plan pruned
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Completed plan pruned")

reset_plan_engine()
_pe_comp = PlanEngine()

_completed = {
    "plans": {
        "done_plan": {
            "plan_id": "done_plan",
            "root_goal_id": "dp1",
            "steps": [{"goal_id": "dp1", "position": 0}],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 1,
            "creation_turn": 0,
        }
    },
    "progress": {
        "done_plan": {
            "plan_id": "done_plan",
            "completed_steps": ["dp1"],
            "failed_steps": [],
            "step_scores": {"dp1": 0.9},
            "confidence": 0.5,
            "active": True,
            "last_activity_turn": 5,
        }
    },
    "active_plan_id": "done_plan",
    "last_generation_turn": 0,
}

_pe_comp.restore(_completed)
_test("completed plan pruned", "done_plan" not in _pe_comp._plans)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Recovery state round-trips through persistence
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Recovery state persistence round-trip")

reset_plan_engine()
_reset_buffer_for_tests()

_pe_rt = PlanEngine(persist=True)
_plan_rt = Plan(
    plan_id="rt_plan",
    root_goal_id="rtg1",
    steps=(
        PlanStep(goal_id="rtg1", position=0),
        PlanStep(goal_id="rtg2", position=1, dependency_ids=("rtg1",)),
    ),
    dependencies=(("rtg1", "rtg2"),),
    expected_value=0.7,
    confidence=0.8,
    horizon=2,
    creation_turn=0,
)
_pe_rt._plans["rt_plan"] = _plan_rt
_pe_rt._progress["rt_plan"] = PlanProgress(plan_id="rt_plan", confidence=0.8)
_pe_rt._active_plan_id = "rt_plan"

# Fail rtg1 once → retry_pending
_pe_rt.record_step_outcome("rt_plan", "rtg1", 0.1, current_turn=1)
_pe_rt._maybe_persist()

from umh.runtime_engine.persistence import flush as _flush, _buffer

_flush()

# Create new engine and load persisted state
reset_plan_engine()
_pe_rt2 = PlanEngine(persist=True)

_rp_rt2 = _pe_rt2.get_progress("rt_plan")
if _rp_rt2 is not None:
    _rec_rt2 = _rp_rt2.step_recovery.get("rtg1")
    _test("recovery state persisted", _rec_rt2 is not None)
    if _rec_rt2:
        _test(
            "retry_count preserved",
            _rec_rt2.retry_count == 1,
            f"got {_rec_rt2.retry_count}",
        )
        _test(
            "status preserved",
            _rec_rt2.status == "retry_pending",
            f"got {_rec_rt2.status}",
        )
        _test("failure_streak preserved", _rec_rt2.failure_streak == 1)
else:
    _test("recovery state persisted", False, "progress not loaded")
    _test("retry_count preserved", False)
    _test("status preserved", False)
    _test("failure_streak preserved", False)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. _valid_step_ordering
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Step ordering validation")

_valid = (
    PlanStep(goal_id="a", position=0),
    PlanStep(goal_id="b", position=1, dependency_ids=("a",)),
)
_test("valid ordering passes", _valid_step_ordering(_valid))

_invalid = (
    PlanStep(goal_id="a", position=0, dependency_ids=("b",)),
    PlanStep(goal_id="b", position=1),
)
_test("backward dependency fails", not _valid_step_ordering(_invalid))

_self_dep = (PlanStep(goal_id="a", position=0, dependency_ids=("a",)),)
_test("self-dependency fails", not _valid_step_ordering(_self_dep))


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Missing dependency in step → plan dropped
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. Missing dependency drops plan")

reset_plan_engine()
_pe_md = PlanEngine()

_missing_dep = {
    "plans": {
        "md_plan": {
            "plan_id": "md_plan",
            "root_goal_id": "m1",
            "steps": [
                {"goal_id": "m1", "position": 0},
                {"goal_id": "m2", "position": 1, "dependency_ids": ["nonexistent"]},
            ],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 2,
            "creation_turn": 0,
        }
    },
    "progress": {
        "md_plan": {
            "plan_id": "md_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
        }
    },
    "active_plan_id": "md_plan",
    "last_generation_turn": 0,
}

_pe_md.restore(_missing_dep)
_test("plan with missing dependency dropped", "md_plan" not in _pe_md._plans)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Plan completion with skipped steps
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Plan completion with skipped steps")

reset_plan_engine()

_plan_skip_complete = Plan(
    plan_id="sc_plan",
    root_goal_id="sc1",
    steps=(
        PlanStep(goal_id="sc1", position=0),
        PlanStep(goal_id="sc2", position=1),  # no dependency
    ),
    dependencies=(),
    expected_value=0.7,
    confidence=0.8,
    horizon=2,
    creation_turn=0,
)

_pe_sc = PlanEngine()
_pe_sc._plans["sc_plan"] = _plan_skip_complete
_pe_sc._progress["sc_plan"] = PlanProgress(plan_id="sc_plan", confidence=0.8)
_pe_sc._active_plan_id = "sc_plan"

# Skip sc1, complete sc2
_rp_sc = _pe_sc.get_progress("sc_plan")
_rp_sc.skipped_steps.append("sc1")
_rp_sc.get_recovery("sc1").status = "skipped"

_pe_sc.record_step_outcome("sc_plan", "sc2", 0.9, current_turn=5)

_test(
    "plan complete with 1 skipped + 1 completed",
    _rp_sc.is_complete(_plan_skip_complete),
)
_test("plan deactivated after completion", not _rp_sc.active)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Determinism: same inputs → same recovery state
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. Determinism")

_results = []
for _ in range(3):
    reset_plan_engine()
    _pe_det = PlanEngine()
    _plan_det = Plan(
        plan_id="det_plan",
        root_goal_id="dg1",
        steps=(
            PlanStep(goal_id="dg1", position=0),
            PlanStep(goal_id="dg2", position=1, dependency_ids=("dg1",)),
        ),
        dependencies=(("dg1", "dg2"),),
        expected_value=0.7,
        confidence=0.8,
        horizon=2,
        creation_turn=0,
    )
    _pe_det._plans["det_plan"] = _plan_det
    _pe_det._progress["det_plan"] = PlanProgress(plan_id="det_plan", confidence=0.8)
    _pe_det._active_plan_id = "det_plan"

    _pe_det.record_step_outcome("det_plan", "dg1", 0.1, current_turn=1)
    _pe_det.record_step_outcome("det_plan", "dg1", 0.05, current_turn=3)

    _snap = _pe_det.get_progress("det_plan").to_dict()
    _results.append(_snap)

_test("3 runs produce identical state", _results[0] == _results[1] == _results[2])


# ═══════════════════════════════════════════════════════════════════════════════
# 26. No LLM calls in modified modules
# ═══════════════════════════════════════════════════════════════════════════════

_section("26. No LLM calls")

import ast

for _mod_path in [
    "/opt/OS/eos/hierarchical_planning.py",
    "/opt/OS/eos/persistence.py",
]:
    with open(_mod_path) as f:
        _src = f.read()
    _test(
        f"no call_with_fallback in {_mod_path.split('/')[-1]}",
        "call_with_fallback" not in _src,
    )
    _test(
        f"no anthropic in {_mod_path.split('/')[-1]}",
        "anthropic" not in _src.lower()
        or "anthropic" in _src.lower().split("co-authored")[0] == False,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 27. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("27. ExecutionSpine unchanged")

import hashlib

with open("/opt/OS/eos/execution_spine.py", "rb") as f:
    _spine_hash = hashlib.md5(f.read()).hexdigest()

_test(
    "spine hash unchanged",
    _spine_hash == "9b98f166681cb5747a240a1cdc44f96f",
    f"hash={_spine_hash}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 28. Backward compatibility — old progress format loads
# ═══════════════════════════════════════════════════════════════════════════════

_section("28. Backward compat: old progress format")

reset_plan_engine()
_pe_bc = PlanEngine()

_old_format = {
    "plans": {
        "old_plan": {
            "plan_id": "old_plan",
            "root_goal_id": "og1",
            "steps": [{"goal_id": "og1", "position": 0}],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 1,
            "creation_turn": 0,
        }
    },
    "progress": {
        "old_plan": {
            "plan_id": "old_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": True,
            # no skipped_steps, step_recovery, last_activity_turn
        }
    },
    "active_plan_id": "old_plan",
    "last_generation_turn": 0,
}

_pe_bc.restore(_old_format)
_test("old format loads", "old_plan" in _pe_bc._plans)
_rp_bc = _pe_bc.get_progress("old_plan")
_test("skipped_steps defaults to []", _rp_bc.skipped_steps == [])
_test("step_recovery defaults to {}", _rp_bc.step_recovery == {})
_test("last_activity_turn defaults to 0", _rp_bc.last_activity_turn == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 29. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("29. No new external dependencies")

_allowed = {"__future__", "hashlib", "logging", "math", "dataclasses", "typing"}
with open("/opt/OS/eos/hierarchical_planning.py") as f:
    _tree = ast.parse(f.read())
_imports = set()
for node in ast.walk(_tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            _imports.add(alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        if node.module and not node.module.startswith("umh.runtime_engine."):
            _imports.add(node.module.split(".")[0])

_test(
    "no new external imports in hierarchical_planning",
    _imports.issubset(_allowed),
    f"found: {sorted(_imports)}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 30. Inactive plan pruned on restore
# ═══════════════════════════════════════════════════════════════════════════════

_section("30. Inactive plan pruned")

reset_plan_engine()
_pe_ip = PlanEngine()

_inactive = {
    "plans": {
        "inactive_plan": {
            "plan_id": "inactive_plan",
            "root_goal_id": "ip1",
            "steps": [{"goal_id": "ip1", "position": 0}],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.5,
            "horizon": 1,
            "creation_turn": 0,
        }
    },
    "progress": {
        "inactive_plan": {
            "plan_id": "inactive_plan",
            "completed_steps": [],
            "failed_steps": [],
            "step_scores": {},
            "confidence": 0.5,
            "active": False,
        }
    },
    "active_plan_id": "inactive_plan",
    "last_generation_turn": 0,
}

_pe_ip.restore(_inactive)
_test("inactive plan pruned", "inactive_plan" not in _pe_ip._plans)
_test("active_plan_id cleared after prune", _pe_ip._active_plan_id is None)


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  TOTAL: {_total} assertions | PASS: {_pass} | FAIL: {_fail}")
print(f"{'═' * 60}")

sys.exit(0 if _fail == 0 else 1)
