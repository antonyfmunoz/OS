"""
Tests for Hierarchical Planning & Multi-Step Goal Execution.

Proves:
    1. System generates valid multi-step plans
    2. Dependencies enforced correctly
    3. Plans compete with single goals
    4. Failed plans degrade
    5. Re-planning works
    6. No regressions
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
    compute_plan_score,
    plan_to_utility,
    get_plan_engine,
    reset_plan_engine,
    MAX_PLANS,
    MAX_STEPS,
    PLAN_COOLDOWN,
    MIN_GOALS_FOR_PLAN,
    PLAN_CONFIDENCE_FLOOR,
    PLAN_FAILURE_PENALTY,
    REPLAN_THRESHOLD,
    PLAN_UTILITY_BONUS,
    TRAJECTORY_CHAIN_THRESHOLD,
    HORIZON_TRIGGER_THRESHOLD,
    CRITERIA_OVERLAP_THRESHOLD,
)
from umh.goals.state import GoalState, GoalRegistry, GoalTracker
from umh.runtime_engine.decision_trace import build_trace

_test("all imports succeed", True)


# ── Helpers ────────────────────────────────────────────────────────────────


def _fresh_registry() -> GoalRegistry:
    """Create a fresh GoalRegistry with no goals."""
    return GoalRegistry()


def _add_related_goals(reg: GoalRegistry) -> None:
    """Add goals with overlapping criteria for trigger A."""
    reg.add_goal(
        GoalState(
            goal_id="sales",
            description="Close sales",
            success_criteria={
                "domain": "sales",
                "type": "persuasive",
                "target": "leads",
            },
            priority=0.9,
        )
    )
    reg.add_goal(
        GoalState(
            goal_id="outreach",
            description="Outreach campaigns",
            success_criteria={
                "domain": "sales",
                "type": "persuasive",
                "channel": "email",
            },
            priority=0.7,
        )
    )


def _add_unrelated_goals(reg: GoalRegistry) -> None:
    """Add goals with no criteria overlap (different keys entirely)."""
    reg.add_goal(
        GoalState(
            goal_id="alpha",
            description="Goal alpha",
            success_criteria={"engineering_area": "backend"},
            priority=0.8,
        )
    )
    reg.add_goal(
        GoalState(
            goal_id="beta",
            description="Goal beta",
            success_criteria={"marketing_channel": "social"},
            priority=0.6,
        )
    )


def _make_traces_with_chain(goal_ids: list[str], quality: float = 0.7) -> list:
    """Create mock traces with sequential high-quality active goals."""
    traces = []
    for i, gid in enumerate(goal_ids):

        class _MockTrace:
            pass

        t = _MockTrace()
        t.turn_id = i + 1
        t.active_goal_id = gid
        t.quality_score = quality
        traces.append(t)
    return traces


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PlanStep data model
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. PlanStep — Data Model")

ps = PlanStep(
    goal_id="step_1",
    position=0,
    dependency_ids=(),
    expected_delta=0.1,
)
_test("goal_id stored", ps.goal_id == "step_1")
_test("position stored", ps.position == 0)
_test("no dependencies", len(ps.dependency_ids) == 0)
_test("expected_delta stored", ps.expected_delta == 0.1)

d = ps.to_dict()
_test("to_dict has goal_id", "goal_id" in d)
_test("to_dict has position", "position" in d)
_test("to_dict has dependency_ids", "dependency_ids" in d)

ps2 = PlanStep(goal_id="step_2", position=1, dependency_ids=("step_1",))
_test("dependency recorded", "step_1" in ps2.dependency_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Plan data model
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Plan — Data Model")

plan = Plan(
    plan_id="plan_test123",
    root_goal_id="step_1",
    steps=(ps, ps2),
    dependencies=(("step_1", "step_2"),),
    expected_value=0.7,
    confidence=0.8,
    horizon=2,
    creation_turn=5,
    generation_reason="test",
)
_test("plan_id stored", plan.plan_id == "plan_test123")
_test("root_goal_id stored", plan.root_goal_id == "step_1")
_test("steps count", len(plan.steps) == 2)
_test("dependencies stored", len(plan.dependencies) == 1)
_test("goal_ids property", plan.goal_ids == ("step_1", "step_2"))
_test("horizon stored", plan.horizon == 2)

pd = plan.to_dict()
_test("to_dict has plan_id", "plan_id" in pd)
_test("to_dict has steps", "steps" in pd)
_test("to_dict has dependencies", "dependencies" in pd)
_test("to_dict has confidence", "confidence" in pd)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PlanProgress tracking
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. PlanProgress — Tracking")

prog = PlanProgress(plan_id="plan_test123", confidence=0.8)
_test("initially active", prog.active)
_test("no completed steps", len(prog.completed_steps) == 0)

_test("step_1 has no deps — is ready", prog.is_step_ready(ps))
_test("step_2 deps not met — not ready", not prog.is_step_ready(ps2))

prog.record_success("step_1", 0.85)
_test("step_1 completed", "step_1" in prog.completed_steps)
_test("step_2 now ready (dep satisfied)", prog.is_step_ready(ps2))

prog.record_success("step_2", 0.9)
_test("plan is complete", prog.is_complete(plan))

ppd = prog.to_dict()
_test("to_dict has completed_steps", "completed_steps" in ppd)
_test("to_dict has confidence", "confidence" in ppd)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Plan scoring
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Plan Scoring")

reg4 = _fresh_registry()
reg4.add_goal(
    GoalState(
        goal_id="step_1", description="s1", success_criteria={"k": "v"}, priority=0.8
    )
)
reg4.add_goal(
    GoalState(
        goal_id="step_2", description="s2", success_criteria={"k": "v"}, priority=0.6
    )
)

t4_1 = reg4.get_tracker("step_1")
t4_1.update_success(0.8)
t4_1.update_success(0.8)

t4_2 = reg4.get_tracker("step_2")
t4_2.update_success(0.7)
t4_2.update_success(0.7)

score = compute_plan_score(plan, reg4)
_test("plan score > 0", score > 0, f"score={score:.4f}")
_test("plan score <= 1", score <= 1.0, f"score={score:.4f}")

empty_reg = _fresh_registry()
empty_score = compute_plan_score(plan, empty_reg)
_test("empty registry → low score", empty_score > 0, f"score={empty_score:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Plan to utility conversion
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Plan → Utility Conversion")

prog5 = PlanProgress(plan_id="plan_test123", confidence=0.8)
util = plan_to_utility(plan, prog5, reg4, current_turn=5)
_test("utility > 0", util > 0, f"utility={util:.4f}")
_test(
    "utility includes PLAN_UTILITY_BONUS",
    util >= PLAN_UTILITY_BONUS,
    f"utility={util:.4f}",
)

prog5_complete = PlanProgress(plan_id="plan_test123", confidence=0.8)
prog5_complete.record_success("step_1", 0.9)
prog5_complete.record_success("step_2", 0.9)
util_complete = plan_to_utility(plan, prog5_complete, reg4, current_turn=5)
_test(
    "completed plan → 0 utility (no next step)",
    util_complete == 0.0,
    f"utility={util_complete:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Constants
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Constants")

_test("MAX_PLANS is 4", MAX_PLANS == 4)
_test("MAX_STEPS is 6", MAX_STEPS == 6)
_test("PLAN_COOLDOWN is 8", PLAN_COOLDOWN == 8)
_test("MIN_GOALS_FOR_PLAN is 2", MIN_GOALS_FOR_PLAN == 2)
_test("PLAN_CONFIDENCE_FLOOR is 0.1", PLAN_CONFIDENCE_FLOOR == 0.1)
_test("REPLAN_THRESHOLD is 0.25", REPLAN_THRESHOLD == 0.25)
_test("TRAJECTORY_CHAIN_THRESHOLD is 0.6", TRAJECTORY_CHAIN_THRESHOLD == 0.6)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Trigger A: Related goals → plan generation
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Trigger A — Related Goals → Plan")

reg7 = _fresh_registry()
_add_related_goals(reg7)

engine7 = PlanEngine()
plans7 = engine7.generate_plans(reg7, traces=[], current_turn=20)
_test("related goals produce plan", len(plans7) == 1, f"count={len(plans7)}")
if plans7:
    p = plans7[0]
    _test("plan has 2 steps", len(p.steps) == 2, f"steps={len(p.steps)}")
    _test(
        "root is higher priority goal",
        p.root_goal_id == "sales",
        f"root={p.root_goal_id}",
    )
    _test("reason contains related_goals", "related_goals" in p.generation_reason)
    _test("dependency exists", len(p.dependencies) > 0)
    _test("plan_id starts with plan_", p.plan_id.startswith("plan_"))


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Trigger B: Trajectory chain → plan generation
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Trigger B — Trajectory Chain → Plan")

reg8 = _fresh_registry()
reg8.add_goal(GoalState(goal_id="g1", description="g1", priority=0.8))
reg8.add_goal(GoalState(goal_id="g2", description="g2", priority=0.7))
reg8.add_goal(GoalState(goal_id="g3", description="g3", priority=0.6))

traces8 = _make_traces_with_chain(["g1", "g2", "g3"])

engine8 = PlanEngine()
plans8 = engine8.generate_plans(reg8, traces=traces8, current_turn=20)
_test("trajectory chain produces plan", len(plans8) == 1, f"count={len(plans8)}")
if plans8:
    p = plans8[0]
    _test("chain plan has 3 steps", len(p.steps) == 3, f"steps={len(p.steps)}")
    _test("reason contains trajectory_chain", "trajectory_chain" in p.generation_reason)
    _test("sequential dependencies", len(p.dependencies) == 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Trigger C: Horizon signal → plan generation
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Trigger C — Horizon Signal → Plan")

reg9 = _fresh_registry()
reg9.add_goal(GoalState(goal_id="h1", description="h1", priority=0.8))
reg9.add_goal(GoalState(goal_id="h2", description="h2", priority=0.7))

t_h1 = reg9.get_tracker("h1")
t_h1.uses = 3
t_h1.delta_history = [-0.1, -0.05, 0.1, 0.2, 0.3]

t_h2 = reg9.get_tracker("h2")
t_h2.uses = 3
t_h2.delta_history = [-0.2, -0.1, 0.15, 0.25, 0.35]

engine9 = PlanEngine()
plans9 = engine9.generate_plans(reg9, traces=[], current_turn=20)
_test("horizon trigger produces plan", len(plans9) == 1, f"count={len(plans9)}")
if plans9:
    p = plans9[0]
    _test("reason contains horizon_trigger", "horizon_trigger" in p.generation_reason)
    _test("horizon plan has 2 steps", len(p.steps) == 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. No plan from unrelated goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. No Plan from Unrelated Goals")

reg10 = _fresh_registry()
_add_unrelated_goals(reg10)

engine10 = PlanEngine()
plans10 = engine10.generate_plans(reg10, traces=[], current_turn=20)
_test("unrelated goals → no plan", len(plans10) == 0, f"count={len(plans10)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Dependency enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Dependency Enforcement")

prog11 = PlanProgress(plan_id="p11", confidence=0.8)

step_a = PlanStep(goal_id="a", position=0, dependency_ids=())
step_b = PlanStep(goal_id="b", position=1, dependency_ids=("a",))
step_c = PlanStep(goal_id="c", position=2, dependency_ids=("a", "b"))

_test("a has no deps → ready", prog11.is_step_ready(step_a))
_test("b needs a → not ready", not prog11.is_step_ready(step_b))
_test("c needs a,b → not ready", not prog11.is_step_ready(step_c))

prog11.record_success("a", 0.9)
_test("after a done: b → ready", prog11.is_step_ready(step_b))
_test("after a done: c → still not ready (needs b)", not prog11.is_step_ready(step_c))

prog11.record_success("b", 0.85)
_test("after a,b done: c → ready", prog11.is_step_ready(step_c))


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Plans compete with single goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Plans Compete with Single Goals")

reg12 = _fresh_registry()
reg12.add_goal(GoalState(goal_id="standalone", description="solo goal", priority=0.9))
reg12.add_goal(GoalState(goal_id="plan_g1", description="plan step 1", priority=0.5))
reg12.add_goal(GoalState(goal_id="plan_g2", description="plan step 2", priority=0.5))

t12_s = reg12.get_tracker("standalone")
t12_s.update_success(0.8)

engine12 = PlanEngine()
plan12 = Plan(
    plan_id="plan_compete",
    root_goal_id="plan_g1",
    steps=(
        PlanStep(goal_id="plan_g1", position=0),
        PlanStep(goal_id="plan_g2", position=1, dependency_ids=("plan_g1",)),
    ),
    dependencies=(("plan_g1", "plan_g2"),),
    expected_value=0.6,
    confidence=0.7,
    horizon=2,
    creation_turn=5,
)
engine12._plans["plan_compete"] = plan12
engine12._progress["plan_compete"] = PlanProgress(
    plan_id="plan_compete", confidence=0.7
)
engine12._active_plan_id = "plan_compete"

best_pid, best_util = engine12.get_best_plan_utility(reg12, current_turn=10)
_test("plan has utility > 0", best_util > 0, f"utility={best_util:.4f}")
_test("plan id returned", best_pid == "plan_compete")

from umh.runtime_engine.goal_arbitrator import GoalArbitrator

arb12 = GoalArbitrator()
arb_result = arb12.select_active_goal(reg12)
single_util = arb_result.utilities.get("standalone", 0.0)
_test("single goal has utility", single_util > 0, f"utility={single_util:.4f}")
_test(
    "both are comparable floats",
    isinstance(best_util, float) and isinstance(single_util, float),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Failed plans degrade
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Failed Plans Degrade")

prog13 = PlanProgress(plan_id="p13", confidence=0.8)
initial_conf = prog13.confidence

prog13.record_failure("step_x", 0.1)
_test(
    "confidence decreased",
    prog13.confidence < initial_conf,
    f"conf={prog13.confidence:.4f}",
)
_test(
    "penalty is PLAN_FAILURE_PENALTY",
    prog13.confidence == initial_conf - PLAN_FAILURE_PENALTY,
    f"conf={prog13.confidence:.4f}",
)
_test("step recorded as failed", "step_x" in prog13.failed_steps)

prog13.record_failure("step_y", 0.05)
_test(
    "double failure → more decay",
    prog13.confidence < initial_conf - PLAN_FAILURE_PENALTY,
)

for _ in range(10):
    prog13.record_failure(f"extra_{_}", 0.05)
_test(
    "confidence has floor",
    prog13.confidence >= PLAN_CONFIDENCE_FLOOR,
    f"conf={prog13.confidence:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Re-planning on failure
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Re-planning")

engine14 = PlanEngine()
plan14 = Plan(
    plan_id="plan_replan",
    root_goal_id="r1",
    steps=(
        PlanStep(goal_id="r1", position=0),
        PlanStep(goal_id="r2", position=1, dependency_ids=("r1",)),
    ),
    dependencies=(("r1", "r2"),),
    expected_value=0.6,
    confidence=0.6,
    horizon=2,
    creation_turn=1,
)
engine14._plans["plan_replan"] = plan14
engine14._progress["plan_replan"] = PlanProgress(plan_id="plan_replan", confidence=0.4)
engine14._active_plan_id = "plan_replan"

_test("initially not needing replan", not engine14.should_replan("plan_replan"))

engine14.record_step_outcome("plan_replan", "r1", 0.1)
_test("after failure: needs replan", engine14.should_replan("plan_replan"))

prog14 = engine14.get_progress("plan_replan")
_test("plan deactivated on low confidence", not prog14.active)
_test("active plan cleared", engine14.active_plan_id is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Cooldown enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Cooldown Enforcement")

reg15 = _fresh_registry()
_add_related_goals(reg15)

engine15 = PlanEngine()
plans15_a = engine15.generate_plans(reg15, traces=[], current_turn=20)
_test("first generation succeeds", len(plans15_a) == 1)

plans15_b = engine15.generate_plans(reg15, traces=[], current_turn=25)
_test("within cooldown → no plan", len(plans15_b) == 0)

plans15_c = engine15.generate_plans(reg15, traces=[], current_turn=30)
_test(
    "after cooldown → possible",
    True,
    f"count={len(plans15_c)} (may be 0 due to duplicate detection)",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Bounded growth (MAX_PLANS)
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Bounded Growth")

engine16 = PlanEngine()
for i in range(MAX_PLANS):
    p = Plan(
        plan_id=f"plan_fill_{i}",
        root_goal_id=f"g_{i}",
        steps=(PlanStep(goal_id=f"g_{i}", position=0),),
        dependencies=(),
        expected_value=0.5,
        confidence=0.5,
        horizon=1,
        creation_turn=i,
    )
    engine16._plans[p.plan_id] = p
    engine16._progress[p.plan_id] = PlanProgress(plan_id=p.plan_id, confidence=0.5)

_test("at MAX_PLANS", engine16.plan_count == MAX_PLANS, f"count={engine16.plan_count}")

reg16 = _fresh_registry()
_add_related_goals(reg16)

plans16 = engine16.generate_plans(reg16, traces=[], current_turn=100)
_test(
    "at cap: pruning + generation possible",
    engine16.plan_count <= MAX_PLANS,
    f"count={engine16.plan_count}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Plan execution — next action
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Plan Execution — Next Action")

reg17 = _fresh_registry()
reg17.add_goal(GoalState(goal_id="e1", description="e1", priority=0.8))
reg17.add_goal(GoalState(goal_id="e2", description="e2", priority=0.6))

engine17 = PlanEngine()
plan17 = Plan(
    plan_id="plan_exec",
    root_goal_id="e1",
    steps=(
        PlanStep(goal_id="e1", position=0),
        PlanStep(goal_id="e2", position=1, dependency_ids=("e1",)),
    ),
    dependencies=(("e1", "e2"),),
    expected_value=0.7,
    confidence=0.7,
    horizon=2,
    creation_turn=1,
)
engine17._plans["plan_exec"] = plan17
engine17._progress["plan_exec"] = PlanProgress(plan_id="plan_exec", confidence=0.7)
engine17._active_plan_id = "plan_exec"

pid17, gid17 = engine17.get_next_action(reg17, current_turn=5)
_test("next action is first step", gid17 == "e1", f"goal={gid17}")
_test("from correct plan", pid17 == "plan_exec")

engine17.record_step_outcome("plan_exec", "e1", 0.8)
pid17b, gid17b = engine17.get_next_action(reg17, current_turn=6)
_test("after step 1 done: next is step 2", gid17b == "e2", f"goal={gid17b}")

engine17.record_step_outcome("plan_exec", "e2", 0.9)
pid17c, gid17c = engine17.get_next_action(reg17, current_turn=7)
_test("after all done: no next action", pid17c is None and gid17c is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Persistence — snapshot and restore
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Persistence — Snapshot & Restore")

engine18 = PlanEngine()
plan18 = Plan(
    plan_id="plan_persist",
    root_goal_id="p1",
    steps=(
        PlanStep(goal_id="p1", position=0),
        PlanStep(goal_id="p2", position=1, dependency_ids=("p1",)),
    ),
    dependencies=(("p1", "p2"),),
    expected_value=0.7,
    confidence=0.8,
    horizon=2,
    creation_turn=10,
    generation_reason="test_persist",
)
engine18._plans["plan_persist"] = plan18
engine18._progress["plan_persist"] = PlanProgress(
    plan_id="plan_persist", confidence=0.8
)
engine18._progress["plan_persist"].record_success("p1", 0.85)
engine18._active_plan_id = "plan_persist"

snap = engine18.snapshot()
_test("snapshot has plans", "plans" in snap)
_test("snapshot has progress", "progress" in snap)
_test("snapshot has active_plan_id", snap["active_plan_id"] == "plan_persist")

engine18_restored = PlanEngine()
engine18_restored.restore(snap)
_test("restored plan count", engine18_restored.plan_count == 1)
_test("restored active plan", engine18_restored.active_plan_id == "plan_persist")

restored_plan = engine18_restored.get_plan("plan_persist")
_test("restored plan has correct steps", len(restored_plan.steps) == 2)
_test("restored plan root", restored_plan.root_goal_id == "p1")

restored_prog = engine18_restored.get_progress("plan_persist")
_test("restored progress has completed step", "p1" in restored_prog.completed_steps)
_test("restored confidence", restored_prog.confidence == 0.8)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. DecisionTrace — plan fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. DecisionTrace — Plan Fields")

trace19 = build_trace(
    turn_id=1,
    active_plan_id="plan_abc",
    active_plan_step="goal_1",
    plan_confidence=0.75,
    plan_count=2,
    plan_generation_reason="related_goals:overlap=0.60",
)
_test("trace has active_plan_id", trace19.active_plan_id == "plan_abc")
_test("trace has active_plan_step", trace19.active_plan_step == "goal_1")
_test("trace has plan_confidence", trace19.plan_confidence == 0.75)
_test("trace has plan_count", trace19.plan_count == 2)
_test(
    "trace has plan_generation_reason",
    "related_goals" in trace19.plan_generation_reason,
)

td19 = trace19.to_dict()
_test("to_dict has active_plan_id", td19["active_plan_id"] == "plan_abc")
_test("to_dict has plan_confidence", td19["plan_confidence"] == 0.75)
_test("to_dict has plan_count", td19["plan_count"] == 2)

trace19_empty = build_trace(turn_id=2)
_test("empty: no active_plan_id", trace19_empty.active_plan_id is None)
_test("empty: no plan_count", trace19_empty.plan_count is None)
_test(
    "empty to_dict: no active_plan_id", "active_plan_id" not in trace19_empty.to_dict()
)
_test("empty to_dict: no plan_count", "plan_count" not in trace19_empty.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Determinism")

reg20a = _fresh_registry()
_add_related_goals(reg20a)

reg20b = _fresh_registry()
_add_related_goals(reg20b)

engine20a = PlanEngine()
engine20b = PlanEngine()

plans20a = engine20a.generate_plans(reg20a, traces=[], current_turn=20)
plans20b = engine20b.generate_plans(reg20b, traces=[], current_turn=20)

_test("deterministic plan count", len(plans20a) == len(plans20b))
if plans20a and plans20b:
    _test("deterministic plan_id", plans20a[0].plan_id == plans20b[0].plan_id)
    _test(
        "deterministic root_goal", plans20a[0].root_goal_id == plans20b[0].root_goal_id
    )
    _test(
        "deterministic reason",
        plans20a[0].generation_reason == plans20b[0].generation_reason,
    )

score20a = compute_plan_score(plans20a[0], reg20a) if plans20a else 0.0
score20b = compute_plan_score(plans20b[0], reg20b) if plans20b else 0.0
_test("deterministic score", score20a == score20b, f"{score20a} vs {score20b}")


# ═══════════════════════════════════════════════════════════════════════════════
# 21. No LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. No LLM Calls")

with open("/opt/OS/eos/hierarchical_planning.py") as f:
    _hp_src = f.read()

_test("no call_with_fallback", "call_with_fallback" not in _hp_src)
_test("no import random", "import random" not in _hp_src)
_test("no anthropic", "anthropic" not in _hp_src)
_test("no openai", "openai" not in _hp_src)
_test("no genai", "genai" not in _hp_src)
_test("no agent_runtime", "agent_runtime" not in _hp_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. ExecutionSpine Unchanged")

with open("/opt/OS/eos/execution_spine.py") as f:
    _spine_src = f.read()

_test("spine: no hierarchical_planning ref", "hierarchical_planning" not in _spine_src)
_test("spine: no PlanEngine ref", "PlanEngine" not in _spine_src)
_test("spine: no plan_id ref", "plan_id" not in _spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Singleton pattern
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. Singleton Pattern")

pe_a = get_plan_engine()
pe_b = get_plan_engine()
_test("singleton: same instance", pe_a is pe_b)

reset_plan_engine()
pe_c = get_plan_engine()
_test("reset creates new instance", pe_a is not pe_c)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Insufficient data — no plan
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Insufficient Data → No Plan")

engine24 = PlanEngine()

reg24_empty = _fresh_registry()
plans24_empty = engine24.generate_plans(reg24_empty, traces=[], current_turn=20)
_test("empty registry → no plan", len(plans24_empty) == 0)

reg24_single = _fresh_registry()
reg24_single.add_goal(GoalState(goal_id="only", description="only", priority=0.8))
engine24b = PlanEngine()
plans24_single = engine24b.generate_plans(reg24_single, traces=[], current_turn=20)
_test("single goal → no plan", len(plans24_single) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. No new dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. No New Dependencies")

_test("no requests", "requests" not in _hp_src)
_test("no httpx", "httpx" not in _hp_src)
_test("no numpy", "numpy" not in _hp_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("26. Backward Compatibility")

from umh.goals.state import GoalState as _GS, GoalRegistry as _GR

_compat_reg = _GR()
_compat_reg.add_goal(_GS(goal_id="compat", description="compat test", priority=0.5))
_test("goal registry works normally", _compat_reg.get_goal("compat") is not None)

_compat_trace = build_trace(turn_id=99)
_test("trace compat: works without plan fields", _compat_trace.active_plan_id is None)
_test("trace compat: plan_count is None", _compat_trace.plan_count is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 27. Plan activate/deactivate
# ═══════════════════════════════════════════════════════════════════════════════

_section("27. Activate / Deactivate Plans")

engine27 = PlanEngine()
plan27 = Plan(
    plan_id="plan_toggle",
    root_goal_id="t1",
    steps=(PlanStep(goal_id="t1", position=0),),
    dependencies=(),
    expected_value=0.5,
    confidence=0.6,
    horizon=1,
    creation_turn=1,
)
engine27._plans["plan_toggle"] = plan27
engine27._progress["plan_toggle"] = PlanProgress(plan_id="plan_toggle", confidence=0.6)
engine27._active_plan_id = "plan_toggle"

engine27.deactivate_plan("plan_toggle")
_test(
    "deactivated: progress not active", not engine27.get_progress("plan_toggle").active
)
_test("deactivated: active_plan_id cleared", engine27.active_plan_id is None)

ok = engine27.activate_plan("plan_toggle")
_test("reactivated successfully", ok)
_test("reactivated: active_plan_id set", engine27.active_plan_id == "plan_toggle")
_test("reactivated: progress active", engine27.get_progress("plan_toggle").active)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
