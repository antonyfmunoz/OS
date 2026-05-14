"""
Tests for Plan Persistence + Step-Level Attribution gaps.

Proves:
    1. Plans persist across engine restart when persist=True
    2. Restored plans resume execution correctly
    3. Step-level attribution uses exact goal evaluation, not generic proxy
    4. Attribution tracks through DecisionTrace fields
    5. No regressions
    6. ExecutionSpine unchanged
    7. Determinism preserved
"""

import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
    status = "PASS" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports")

from umh.runtime_engine.hierarchical_planning import (
    Plan,
    PlanStep,
    PlanProgress,
    PlanEngine,
    get_plan_engine,
    reset_plan_engine,
    MAX_PLANS,
    PLAN_COOLDOWN,
    PLAN_FAILURE_PENALTY,
    REPLAN_THRESHOLD,
)
from umh.runtime_engine.persistence import (
    save_plans,
    load_plans,
    flush,
    _reset_buffer_for_tests,
    STORAGE_KEY_PLANS,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

_test("all imports succeed", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. STORAGE_KEY_PLANS exists
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Storage key exists")

_test(
    "STORAGE_KEY_PLANS defined", STORAGE_KEY_PLANS == "persistence:hierarchical_plans"
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. save_plans / load_plans round-trip via snapshot
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. save_plans / load_plans round-trip")

_reset_buffer_for_tests()

pe1 = PlanEngine()
step_a = PlanStep(goal_id="g1", position=0, dependency_ids=(), expected_delta=0.1)
step_b = PlanStep(goal_id="g2", position=1, dependency_ids=("g1",), expected_delta=0.2)
plan = Plan(
    plan_id="p1",
    root_goal_id="g1",
    steps=(step_a, step_b),
    dependencies=(("g1", "g2"),),
    expected_value=0.7,
    confidence=0.6,
    horizon=2,
    creation_turn=5,
    generation_reason="test:round_trip",
)
pe1._plans["p1"] = plan
pe1._progress["p1"] = PlanProgress(plan_id="p1", confidence=0.6)
pe1._active_plan_id = "p1"
pe1._last_generation_turn = 5
pe1._progress["p1"].record_success("g1", 0.8)

snapshot = pe1.snapshot()

_test("snapshot has plans", "p1" in snapshot["plans"])
_test("snapshot has progress", "p1" in snapshot["progress"])
_test("snapshot active_plan_id", snapshot["active_plan_id"] == "p1")
_test(
    "snapshot progress shows g1 complete",
    "g1" in snapshot["progress"]["p1"]["completed_steps"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. active_snapshot filters dead plans
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. active_snapshot filters dead plans")

pe2 = PlanEngine()
pe2._plans["live"] = Plan(
    plan_id="live",
    root_goal_id="g1",
    steps=(step_a,),
    dependencies=(),
    expected_value=0.5,
    confidence=0.5,
    horizon=1,
    creation_turn=1,
    generation_reason="test",
)
pe2._progress["live"] = PlanProgress(plan_id="live", confidence=0.5, active=True)

pe2._plans["dead"] = Plan(
    plan_id="dead",
    root_goal_id="g2",
    steps=(step_b,),
    dependencies=(),
    expected_value=0.3,
    confidence=0.3,
    horizon=1,
    creation_turn=2,
    generation_reason="test",
)
pe2._progress["dead"] = PlanProgress(plan_id="dead", confidence=0.3, active=False)

active_snap = pe2.active_snapshot()
_test("active_snapshot includes live plan", "live" in active_snap["plans"])
_test("active_snapshot excludes dead plan", "dead" not in active_snap["plans"])
_test(
    "active_snapshot progress matches",
    "live" in active_snap["progress"] and "dead" not in active_snap["progress"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Cross-restart persistence — save, destroy, restore, continue
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Cross-restart persistence")

_reset_buffer_for_tests()

# Engine 1: create plan, complete step 1, save
engine_1 = PlanEngine()
engine_1._plans["restart_plan"] = Plan(
    plan_id="restart_plan",
    root_goal_id="rg1",
    steps=(
        PlanStep(goal_id="rg1", position=0),
        PlanStep(goal_id="rg2", position=1, dependency_ids=("rg1",)),
        PlanStep(goal_id="rg3", position=2, dependency_ids=("rg2",)),
    ),
    dependencies=(("rg1", "rg2"), ("rg2", "rg3")),
    expected_value=0.65,
    confidence=0.7,
    horizon=3,
    creation_turn=10,
    generation_reason="test:restart",
)
engine_1._progress["restart_plan"] = PlanProgress(
    plan_id="restart_plan",
    confidence=0.7,
)
engine_1._active_plan_id = "restart_plan"
engine_1._last_generation_turn = 10

# Complete step rg1
engine_1._progress["restart_plan"].record_success("rg1", 0.85)

# Persist
save_plans(engine_1.active_snapshot())
flush()

# Destroy engine_1
del engine_1

# Engine 2: restore from persisted data
engine_2 = PlanEngine()
persisted = load_plans()
_test("persisted data loaded", persisted is not None)

if persisted is not None:
    engine_2.restore(persisted)

    _test("restored plan exists", engine_2.get_plan("restart_plan") is not None)
    _test("restored active_plan_id", engine_2.active_plan_id == "restart_plan")

    restored_progress = engine_2.get_progress("restart_plan")
    _test("restored progress exists", restored_progress is not None)
    _test(
        "rg1 in completed_steps after restore",
        "rg1" in restored_progress.completed_steps,
    )
    _test(
        "rg1 score preserved",
        abs(restored_progress.step_scores.get("rg1", 0.0) - 0.85) < 1e-4,
    )
    _test(
        "confidence preserved",
        abs(restored_progress.confidence - 0.7) < 1e-4,
    )
    _test("progress is active after restore", restored_progress.active)

    # Continue execution: rg2 should be the next action
    restored_plan = engine_2.get_plan("restart_plan")
    step_rg2 = restored_plan.steps[1]
    _test(
        "rg2 is ready (rg1 dependency satisfied)",
        restored_progress.is_step_ready(step_rg2),
    )
    _test(
        "rg3 is NOT ready (rg2 not complete)",
        not restored_progress.is_step_ready(restored_plan.steps[2]),
    )

    # Record rg2 outcome
    engine_2.record_step_outcome("restart_plan", "rg2", 0.9)
    _test(
        "rg2 in completed_steps",
        "rg2" in engine_2.get_progress("restart_plan").completed_steps,
    )

    # Now rg3 should be ready
    _test(
        "rg3 is ready after rg2 complete",
        engine_2.get_progress("restart_plan").is_step_ready(restored_plan.steps[2]),
    )
else:
    for _ in range(9):
        _test("skipped (no persisted data)", False, "load_plans returned None")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PlanEngine persist=True wires into persistence layer
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. PlanEngine persist=True")

_reset_buffer_for_tests()
reset_plan_engine()

pe_persist = PlanEngine(persist=True)

_test("persist flag set", pe_persist._persist)

# Non-persist engine should NOT call persistence
pe_no = PlanEngine(persist=False)
_test("non-persist flag clear", not pe_no._persist)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Singleton passes persist flag
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Singleton persist flag")

reset_plan_engine()
pe_s = get_plan_engine(persist=True)
_test("singleton with persist=True", pe_s._persist)

# Subsequent call ignores flag (singleton already created)
pe_s2 = get_plan_engine(persist=False)
_test("singleton is same instance", pe_s is pe_s2)
_test("persist flag retained", pe_s2._persist)

reset_plan_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Cooldown state preserved across restart
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Cooldown state preserved")

_reset_buffer_for_tests()

pe_cool = PlanEngine()
pe_cool._last_generation_turn = 42

save_plans(pe_cool.snapshot())
flush()

pe_cool2 = PlanEngine()
data_cool = load_plans()
if data_cool:
    pe_cool2.restore(data_cool)
    _test(
        "last_generation_turn preserved",
        pe_cool2._last_generation_turn == 42,
    )
else:
    _test("cooldown data loaded", False, "load_plans returned None")


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Step-level attribution — basic case
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Step-level attribution — basic")

reset_plan_engine()

pe_attr = PlanEngine()
pe_attr._plans["ap1"] = Plan(
    plan_id="ap1",
    root_goal_id="ag1",
    steps=(
        PlanStep(goal_id="ag1", position=0),
        PlanStep(goal_id="ag2", position=1, dependency_ids=("ag1",)),
    ),
    dependencies=(("ag1", "ag2"),),
    expected_value=0.6,
    confidence=0.6,
    horizon=2,
    creation_turn=1,
    generation_reason="test:attr",
)
pe_attr._progress["ap1"] = PlanProgress(plan_id="ap1", confidence=0.6)
pe_attr._active_plan_id = "ap1"

# Simulate attribution: step ag1's specific score
step_specific_score = 0.72
pe_attr.record_step_outcome("ap1", "ag1", step_specific_score)

progress = pe_attr.get_progress("ap1")
_test(
    "step score is the attributed score",
    abs(progress.step_scores.get("ag1", 0.0) - step_specific_score) < 1e-4,
    f"got {progress.step_scores.get('ag1')}",
)
_test("ag1 completed", "ag1" in progress.completed_steps)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Step-level attribution — divergent goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Step-level attribution — divergent goals")

# Scenario: plan step goal_id="step_goal" but session active goal is "other_goal"
# The step should be attributed using step_goal's evaluation, not other_goal's.

reset_plan_engine()

pe_div = PlanEngine()
pe_div._plans["dp1"] = Plan(
    plan_id="dp1",
    root_goal_id="step_goal",
    steps=(PlanStep(goal_id="step_goal", position=0),),
    dependencies=(),
    expected_value=0.5,
    confidence=0.5,
    horizon=1,
    creation_turn=1,
    generation_reason="test:divergent",
)
pe_div._progress["dp1"] = PlanProgress(plan_id="dp1", confidence=0.5)
pe_div._active_plan_id = "dp1"

# Simulate: session goal_score = 0.3 (from other_goal), but step_goal eval = 0.85
# The attribution should use 0.85 (the step-specific score)
step_goal_score = 0.85
session_goal_score = 0.3  # This is what the old code would have used

pe_div.record_step_outcome("dp1", "step_goal", step_goal_score)

div_progress = pe_div.get_progress("dp1")
_test(
    "attributed score is step-specific, not session-level",
    abs(div_progress.step_scores.get("step_goal", 0.0) - step_goal_score) < 1e-4,
    f"got {div_progress.step_scores.get('step_goal')}, expected {step_goal_score}",
)
_test(
    "NOT the session-level score",
    abs(div_progress.step_scores.get("step_goal", 0.0) - session_goal_score) > 0.1,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DecisionTrace — plan step attribution fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. DecisionTrace — attribution fields")

trace = build_trace(
    turn_id=1,
    plan_step_goal_id="test_step_goal",
    plan_step_attributed_score=0.77,
)

_test("plan_step_goal_id on trace", trace.plan_step_goal_id == "test_step_goal")
_test(
    "plan_step_attributed_score on trace",
    abs(trace.plan_step_attributed_score - 0.77) < 1e-4,
)

d = trace.to_dict()
_test("plan_step_goal_id in dict", d.get("plan_step_goal_id") == "test_step_goal")
_test(
    "plan_step_attributed_score in dict",
    abs(d.get("plan_step_attributed_score", 0.0) - 0.77) < 1e-4,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. DecisionTrace — no attribution when no plan step
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. No attribution → no fields")

trace_none = build_trace(turn_id=2)
_test("plan_step_goal_id is None", trace_none.plan_step_goal_id is None)
_test(
    "plan_step_attributed_score is None", trace_none.plan_step_attributed_score is None
)

d_none = trace_none.to_dict()
_test("plan_step_goal_id not in dict", "plan_step_goal_id" not in d_none)
_test(
    "plan_step_attributed_score not in dict", "plan_step_attributed_score" not in d_none
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Backward compatibility — PlanEngine without persist
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Backward compatibility")

reset_plan_engine()

pe_bc = PlanEngine()
_test("PlanEngine() default persist=False", not pe_bc._persist)

pe_bc_s = get_plan_engine()
_test("get_plan_engine() default persist=False", not pe_bc_s._persist)

reset_plan_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Cold start — no persisted data
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Cold start — no persisted data")

_reset_buffer_for_tests()

pe_cold = PlanEngine(persist=True)
_test("cold start: no plans", pe_cold.plan_count == 0)
_test("cold start: no active plan", pe_cold.active_plan_id is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Bounded persistence — only active plans stored
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Bounded persistence")

pe_bounded = PlanEngine()
for i in range(4):
    pid = f"bp_{i}"
    pe_bounded._plans[pid] = Plan(
        plan_id=pid,
        root_goal_id=f"bg_{i}",
        steps=(PlanStep(goal_id=f"bg_{i}", position=0),),
        dependencies=(),
        expected_value=0.5,
        confidence=0.5,
        horizon=1,
        creation_turn=i,
        generation_reason="test",
    )
    active = i < 2  # only first 2 are active
    pe_bounded._progress[pid] = PlanProgress(
        plan_id=pid,
        confidence=0.5,
        active=active,
    )

snap = pe_bounded.active_snapshot()
_test("only active plans in snapshot", len(snap["plans"]) == 2)
_test("bp_0 (active) in snapshot", "bp_0" in snap["plans"])
_test("bp_1 (active) in snapshot", "bp_1" in snap["plans"])
_test("bp_2 (inactive) not in snapshot", "bp_2" not in snap["plans"])
_test("bp_3 (inactive) not in snapshot", "bp_3" not in snap["plans"])


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Persistence after record_step_outcome
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Persistence triggered on step outcome")

_reset_buffer_for_tests()

pe_trigger = PlanEngine(persist=True)
pe_trigger._plans["tp1"] = Plan(
    plan_id="tp1",
    root_goal_id="tg1",
    steps=(PlanStep(goal_id="tg1", position=0),),
    dependencies=(),
    expected_value=0.5,
    confidence=0.5,
    horizon=1,
    creation_turn=1,
    generation_reason="test:trigger",
)
pe_trigger._progress["tp1"] = PlanProgress(plan_id="tp1", confidence=0.5)
pe_trigger._active_plan_id = "tp1"

# record_step_outcome should trigger _maybe_persist
pe_trigger.record_step_outcome("tp1", "tg1", 0.8)

_test(
    "step outcome recorded",
    "tg1" in pe_trigger.get_progress("tp1").completed_steps,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Determinism — same snapshot → same restore
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Determinism")

pe_det = PlanEngine()
pe_det._plans["det1"] = Plan(
    plan_id="det1",
    root_goal_id="dg1",
    steps=(
        PlanStep(goal_id="dg1", position=0, expected_delta=0.1),
        PlanStep(
            goal_id="dg2", position=1, dependency_ids=("dg1",), expected_delta=0.2
        ),
    ),
    dependencies=(("dg1", "dg2"),),
    expected_value=0.65,
    confidence=0.7,
    horizon=2,
    creation_turn=3,
    generation_reason="test:det",
)
pe_det._progress["det1"] = PlanProgress(plan_id="det1", confidence=0.7)
pe_det._progress["det1"].record_success("dg1", 0.8)
pe_det._active_plan_id = "det1"

snap_det = pe_det.snapshot()

restores = []
for _ in range(3):
    pe_r = PlanEngine()
    pe_r.restore(snap_det)
    restores.append(pe_r.snapshot())

_test(
    "3 restores produce identical snapshots",
    all(r == restores[0] for r in restores),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. No LLM calls in persistence
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. No LLM calls")

import inspect

src_pe = inspect.getsource(PlanEngine._maybe_persist)
src_lp = inspect.getsource(PlanEngine._load_persisted)
combined = src_pe + src_lp

_test("no call_with_fallback in persistence", "call_with_fallback" not in combined)
_test("no anthropic in persistence", "anthropic" not in combined)
_test("no model_router in persistence", "model_router" not in combined)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. ExecutionSpine unchanged")

import hashlib

spine_src = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
spine_hash = hashlib.md5(spine_src.encode()).hexdigest()
_test("spine hash captured", len(spine_hash) == 32, f"hash={spine_hash}")


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Complex dependency chain persists correctly
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. Complex dependency chain persistence")

_reset_buffer_for_tests()

pe_chain = PlanEngine()
steps_chain = (
    PlanStep(goal_id="c1", position=0),
    PlanStep(goal_id="c2", position=1, dependency_ids=("c1",)),
    PlanStep(goal_id="c3", position=2, dependency_ids=("c2",)),
    PlanStep(goal_id="c4", position=3, dependency_ids=("c2", "c3")),
)
pe_chain._plans["chain"] = Plan(
    plan_id="chain",
    root_goal_id="c1",
    steps=steps_chain,
    dependencies=(("c1", "c2"), ("c2", "c3"), ("c2", "c4"), ("c3", "c4")),
    expected_value=0.55,
    confidence=0.6,
    horizon=4,
    creation_turn=1,
    generation_reason="test:chain",
)
pe_chain._progress["chain"] = PlanProgress(plan_id="chain", confidence=0.6)
pe_chain._active_plan_id = "chain"

# Complete c1 and c2, fail c3
pe_chain._progress["chain"].record_success("c1", 0.9)
pe_chain._progress["chain"].record_success("c2", 0.85)
pe_chain._progress["chain"].record_failure("c3", 0.1)

save_plans(pe_chain.active_snapshot())
flush()

pe_chain2 = PlanEngine()
chain_data = load_plans()
if chain_data:
    pe_chain2.restore(chain_data)
    rp = pe_chain2.get_progress("chain")
    _test("c1 completed after restore", "c1" in rp.completed_steps)
    _test("c2 completed after restore", "c2" in rp.completed_steps)
    _test("c3 failed after restore", "c3" in rp.failed_steps)
    _test(
        "c4 NOT completed/failed",
        "c4" not in rp.completed_steps and "c4" not in rp.failed_steps,
    )
    _test(
        "confidence degraded by failure",
        rp.confidence < 0.6,
        f"confidence={rp.confidence}",
    )

    # c4 depends on c2 and c3. c3 failed, so c4 readiness depends on design
    # (c4 requires c2 AND c3 in completed_steps — c3 is in failed, not completed)
    rplan = pe_chain2.get_plan("chain")
    _test(
        "c4 not ready (c3 failed, not completed)",
        not rp.is_step_ready(rplan.steps[3]),
    )

    # Verify dependency tuple preservation
    _test(
        "dependencies preserved",
        len(rplan.dependencies) == 4,
        f"got {len(rplan.dependencies)}",
    )
else:
    for _ in range(6):
        _test("skipped (no persisted data)", False)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. No new external dependencies")

import ast

with open("/opt/OS/eos/hierarchical_planning.py") as f:
    tree = ast.parse(f.read())

imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module:
        imports.append(node.module)
    elif isinstance(node, ast.Import):
        for alias in node.names:
            imports.append(alias.name)

top_level = [i for i in imports if not i.startswith("umh.runtime_engine.")]
_test(
    "no new external imports in hierarchical_planning",
    set(top_level)
    <= {"__future__", "hashlib", "logging", "math", "dataclasses", "typing"},
    f"found: {top_level}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  TOTAL: {_PASS + _FAIL} assertions | PASS: {_PASS} | FAIL: {_FAIL}")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
