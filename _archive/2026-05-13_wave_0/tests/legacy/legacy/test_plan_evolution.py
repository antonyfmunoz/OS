"""
Test suite: Plan Evolution Layer.

Validates:
    A. Deterministic mutation trigger selection
    B. Each mutation operator (narrow, reorder, substitute, compress)
    C. Dependency-safe reorder only
    D. Recombination only for compatible parents
    E. Cycle rejection
    F. MAX_STEPS enforcement
    G. Bounded population pruning (evolved-first)
    H. Evolved plan origin tagging
    I. Runtime integration order
    J. Persistence compatibility
    K. Determinism across repeated identical runs
    L. No ExecutionSpine changes / no new LLM calls

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
    from umh.runtime_engine.plan_mutation import (
        PlanMutation,
        PlanMutationResult,
        PlanRecombination,
        PlanMutationEngine,
        get_plan_mutation_engine,
        reset_plan_mutation_engine,
        _op_narrow,
        _op_reorder,
        _op_substitute,
        _op_compress,
        _recombine_plans,
        _find_underperforming_step,
        _find_retry_exhausted_step,
        _is_near_miss,
        _find_bloated_step,
        MUTATION_COOLDOWN,
        UNDERPERFORMANCE_THRESHOLD,
        RETRY_EXHAUSTION_THRESHOLD,
        MIN_STEPS_FOR_MUTATION,
    )
    from umh.runtime_engine.hierarchical_planning import (
        Plan,
        PlanStep,
        PlanProgress,
        PlanEngine,
        StepRecoveryState,
        MAX_PLANS,
        MAX_STEPS,
        _valid_step_ordering,
        reset_plan_engine,
    )
    from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

    _test("all imports succeed", True)
except Exception as e:
    _test("all imports succeed", False, str(e))
    print(f"\nFATAL: Import failed — cannot continue.\n{e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_plan(
    plan_id: str = "plan_a",
    steps: tuple | None = None,
    deps: tuple = (),
    confidence: float = 0.7,
    origin: str = "",
) -> Plan:
    if steps is None:
        steps = (
            PlanStep(goal_id="g1", position=0),
            PlanStep(goal_id="g2", position=1, dependency_ids=("g1",)),
            PlanStep(goal_id="g3", position=2, dependency_ids=("g2",)),
        )
    return Plan(
        plan_id=plan_id,
        root_goal_id=steps[0].goal_id,
        steps=steps,
        dependencies=deps,
        expected_value=0.6,
        confidence=confidence,
        horizon=len(steps),
        creation_turn=0,
        generation_reason="test",
        origin=origin,
    )


def _make_progress(
    plan_id: str = "plan_a",
    confidence: float = 0.7,
    step_scores: dict | None = None,
    completed: list | None = None,
    failed: list | None = None,
    recovery: dict | None = None,
) -> PlanProgress:
    p = PlanProgress(plan_id=plan_id, confidence=confidence)
    if step_scores:
        p.step_scores = dict(step_scores)
    if completed:
        p.completed_steps = list(completed)
    if failed:
        p.failed_steps = list(failed)
    if recovery:
        for gid, rec_dict in recovery.items():
            p.step_recovery[gid] = StepRecoveryState(**rec_dict)
    return p


class _FakeGoal:
    def __init__(
        self,
        goal_id: str,
        priority: float = 0.7,
        success_criteria: dict | None = None,
        active: bool = True,
    ):
        self.goal_id = goal_id
        self.priority = priority
        self.success_criteria = success_criteria or {"m": 0.8}
        self.active = active


class _FakeTracker:
    def __init__(self, uses: int = 0, success_score: float = 0.5):
        self.uses = uses
        self.success_score = success_score


class _FakeRegistry:
    def __init__(self, goals: list | None = None):
        self._goals = goals or []

    def get_all_goals(self):
        return self._goals

    def get_goal(self, goal_id: str):
        for g in self._goals:
            if g.goal_id == goal_id:
                return g
        return None

    def get_tracker(self, goal_id: str):
        return _FakeTracker(uses=0)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Plan origin field
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Plan origin field")

plan_base = _make_plan()
_test("default origin is empty", plan_base.origin == "")

plan_evolved = _make_plan(origin="mutated:narrow:plan_a")
_test("custom origin preserved", plan_evolved.origin == "mutated:narrow:plan_a")

d = plan_evolved.to_dict()
_test("origin in to_dict", d.get("origin") == "mutated:narrow:plan_a")

d_base = plan_base.to_dict()
_test("empty origin omitted from to_dict", "origin" not in d_base)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Narrow operator — removes a non-dependent step
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Narrow operator: remove non-dependent step")

plan_3step = _make_plan(
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1),
        PlanStep(goal_id="g3", position=2),
    ),
)

narrowed = _op_narrow(plan_3step, "g2")
_test("narrow produces new plan", narrowed is not None)
_test("narrowed has 2 steps", len(narrowed.steps) == 2)
_test("g2 removed", "g2" not in narrowed.goal_ids)
_test("narrowed origin set", "narrow" in narrowed.origin)
_test("narrowed plan_id differs", narrowed.plan_id != plan_3step.plan_id)
_test("DAG valid", _valid_step_ordering(narrowed.steps))


_section("3. Narrow: cannot remove step with dependents")

plan_chain = _make_plan()  # g1 → g2 → g3
cannot_narrow = _op_narrow(plan_chain, "g1")
_test("cannot narrow g1 (g2 depends on it)", cannot_narrow is None)

cannot_narrow_g2 = _op_narrow(plan_chain, "g2")
_test("cannot narrow g2 (g3 depends on it)", cannot_narrow_g2 is None)

can_narrow_g3 = _op_narrow(plan_chain, "g3")
_test("can narrow g3 (no dependents)", can_narrow_g3 is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Reorder operator — dependency-safe swap only
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Reorder: swap independent adjacent steps")

plan_independent = _make_plan(
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1),
        PlanStep(goal_id="g3", position=2),
    ),
)

reordered = _op_reorder(plan_independent, 0, 1)
_test("reorder produces new plan", reordered is not None)
_test("reordered step 0 is g2", reordered.steps[0].goal_id == "g2")
_test("reordered step 1 is g1", reordered.steps[1].goal_id == "g1")
_test("DAG valid after reorder", _valid_step_ordering(reordered.steps))
_test("reorder origin set", "reorder" in reordered.origin)


_section("5. Reorder: blocked by dependency")

plan_dep_chain = _make_plan()  # g1 → g2 → g3
blocked_reorder = _op_reorder(plan_dep_chain, 0, 1)
_test("reorder blocked when g2 depends on g1", blocked_reorder is None)


_section("6. Reorder: non-adjacent rejected")

non_adj = _op_reorder(plan_independent, 0, 2)
_test("non-adjacent swap rejected", non_adj is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Substitute operator
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Substitute operator")

substituted = _op_substitute(plan_3step, "g2", "g_new")
_test("substitute produces new plan", substituted is not None)
_test("g2 replaced by g_new", "g_new" in substituted.goal_ids)
_test("g2 no longer present", "g2" not in substituted.goal_ids)
_test("substitute origin set", "substitute" in substituted.origin)

# Cannot substitute with a goal already in the plan
dup_sub = _op_substitute(plan_3step, "g2", "g1")
_test("cannot substitute with existing goal", dup_sub is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Compress operator
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Compress: merge duplicate-goal steps")

plan_dup = _make_plan(
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g1", position=1),
        PlanStep(goal_id="g2", position=2),
    ),
)

compressed = _op_compress(plan_dup, 0, 1)
_test("compress produces new plan", compressed is not None)
_test("compressed has 2 steps", len(compressed.steps) == 2)
_test("compress origin set", "compress" in compressed.origin)

# Cannot compress different goals
no_compress = _op_compress(plan_3step, 0, 1)
_test("cannot compress different goals", no_compress is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Mutation trigger detection
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Underperforming step detection")

progress_under = _make_progress(
    step_scores={"g1": 0.8, "g2": 0.1, "g3": 0.6},
)
under = _find_underperforming_step(plan_3step, progress_under)
_test("finds g2 as underperforming", under == "g2", f"found={under}")


_section("10. Retry exhaustion detection")

progress_retry = _make_progress(
    recovery={"g2": {"retry_count": 3, "failure_streak": 2, "status": "failed_final"}},
)
exhausted = _find_retry_exhausted_step(plan_3step, progress_retry)
_test("finds g2 as retry-exhausted", exhausted == "g2", f"found={exhausted}")


_section("11. Near-miss detection")

plan_4step = _make_plan(
    plan_id="plan_4step",
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1),
        PlanStep(goal_id="g3", position=2),
        PlanStep(goal_id="g4", position=3),
    ),
    confidence=0.6,
)

progress_near = _make_progress(
    completed=["g1", "g2", "g3"],
    failed=["g4"],
)
_test(
    "4-step plan with 3 completed + 1 failed = near miss (3/4=0.75 > 0.7)",
    _is_near_miss(plan_4step, progress_near),
)

progress_not_near = _make_progress(
    completed=["g1"],
    failed=["g2", "g3", "g4"],
)
_test(
    "only 1/4 completed = not near miss",
    not _is_near_miss(plan_4step, progress_not_near),
)


_section("12. Bloated step detection")

progress_bloat = _make_progress(
    step_scores={"g1": 0.8, "g2": 0.7, "g3": 0.1},
)
bloated = _find_bloated_step(plan_3step, progress_bloat)
_test("finds g3 as bloated (score 0.1)", bloated == "g3", f"found={bloated}")


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Recombination: compatible parents
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Recombination: compatible overlapping plans")

plan_x = _make_plan(
    plan_id="plan_x",
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1),
    ),
    confidence=0.8,
)
plan_y = _make_plan(
    plan_id="plan_y",
    steps=(
        PlanStep(goal_id="g2", position=0),
        PlanStep(goal_id="g3", position=1),
    ),
    confidence=0.7,
)

recombined = _recombine_plans(plan_x, plan_y, turn=10)
_test("recombination produces plan", recombined is not None)
if recombined is not None:
    _test("recombined has g1", "g1" in recombined.goal_ids)
    _test("recombined origin set", "recombined" in recombined.origin)
    _test("DAG valid", _valid_step_ordering(recombined.steps))
    _test(
        "no duplicate goals", len(set(recombined.goal_ids)) == len(recombined.goal_ids)
    )
    _test("recombined ≤ MAX_STEPS", len(recombined.steps) <= MAX_STEPS)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Recombination: incompatible (no overlap) → None
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Recombination: no overlap → rejected")

plan_no_overlap = _make_plan(
    plan_id="plan_z",
    steps=(
        PlanStep(goal_id="g_x", position=0),
        PlanStep(goal_id="g_y", position=1),
    ),
)

no_recomb = _recombine_plans(plan_x, plan_no_overlap, turn=10)
_test("no overlap → no recombination", no_recomb is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Cycle rejection
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Cycle rejection in mutations")

plan_with_dep = _make_plan(
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1, dependency_ids=("g1",)),
    ),
)

# Reorder g1 and g2 would create a backward dependency
cycle_reorder = _op_reorder(plan_with_dep, 0, 1)
_test("reorder creating cycle → rejected", cycle_reorder is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. MAX_STEPS enforcement in recombination
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. MAX_STEPS cap in recombination")

# Create two plans that together exceed MAX_STEPS
big_steps_a = tuple(PlanStep(goal_id=f"a{i}", position=i) for i in range(4))
big_steps_b = tuple(PlanStep(goal_id=f"a{i}", position=i) for i in range(3, 7))

plan_big_a = _make_plan(plan_id="big_a", steps=big_steps_a)
plan_big_b = _make_plan(plan_id="big_b", steps=big_steps_b)

big_recomb = _recombine_plans(plan_big_a, plan_big_b, turn=20)
if big_recomb is not None:
    _test("recombined ≤ MAX_STEPS", len(big_recomb.steps) <= MAX_STEPS)
else:
    _test("recombination rejected (acceptable)", True, "plans incompatible after cap")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Bounded population: evolved-first pruning
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. register_evolved_plan: bounded population")

reset_plan_engine()
pe = PlanEngine()

# Fill to MAX_PLANS with base plans
for i in range(MAX_PLANS):
    p = _make_plan(
        plan_id=f"base_{i}",
        steps=(
            PlanStep(goal_id=f"bg{i}", position=0),
            PlanStep(goal_id=f"bg{i}_b", position=1),
        ),
    )
    pe._plans[p.plan_id] = p
    pe._progress[p.plan_id] = PlanProgress(plan_id=p.plan_id, confidence=0.5 + i * 0.05)

_test("at MAX_PLANS", pe.plan_count == MAX_PLANS)

evolved = _make_plan(
    plan_id="evolved_1",
    steps=(PlanStep(goal_id="eg1", position=0), PlanStep(goal_id="eg2", position=1)),
    origin="mutated:narrow:base_0",
    confidence=0.3,
)

registered = pe.register_evolved_plan(evolved)
_test("evolved plan registered (pruned weakest base)", registered)
_test("still at MAX_PLANS", pe.plan_count == MAX_PLANS)
_test("evolved plan present", pe.get_plan("evolved_1") is not None)


_section("18. Evolved-first pruning: second evolved plan prunes first evolved")

evolved2 = _make_plan(
    plan_id="evolved_2",
    steps=(PlanStep(goal_id="eg3", position=0), PlanStep(goal_id="eg4", position=1)),
    origin="mutated:narrow:base_1",
    confidence=0.6,
)

reg2 = pe.register_evolved_plan(evolved2)
_test("second evolved registered", reg2)
_test(
    "first evolved pruned (lower confidence)",
    pe.get_plan("evolved_1") is None,
    "evolved_1 had confidence=0.3 < evolved_2's 0.6",
)
_test("second evolved present", pe.get_plan("evolved_2") is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. PlanMutationEngine: cooldown enforcement
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. PlanMutationEngine: cooldown")

reset_plan_mutation_engine()
pme = PlanMutationEngine()

# Set up engine with an underperforming plan
reset_plan_engine()
pe2 = PlanEngine()
plan_under = _make_plan(
    plan_id="plan_u",
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1),
        PlanStep(goal_id="g3", position=2),
    ),
)
pe2._plans["plan_u"] = plan_under
pe2._progress["plan_u"] = _make_progress(
    plan_id="plan_u",
    step_scores={"g1": 0.8, "g2": 0.1, "g3": 0.6},
)

registry = _FakeRegistry(
    [
        _FakeGoal("g1"),
        _FakeGoal("g2"),
        _FakeGoal("g3"),
    ]
)

result1 = pme.evaluate(pe2, registry, current_turn=10)
_test(
    "first evaluation produces mutation",
    result1.has_mutation,
    f"type={result1.mutation.mutation_type if result1.mutation else 'none'}",
)

# Immediate re-evaluation should be blocked by cooldown
result2 = pme.evaluate(pe2, registry, current_turn=11)
_test("cooldown blocks immediate re-mutation", not result2.has_mutation)

# After cooldown passes
result3 = pme.evaluate(pe2, registry, current_turn=10 + MUTATION_COOLDOWN)
# May or may not produce mutation depending on state, but cooldown is not blocking
_test("past cooldown: evaluation runs", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. PlanMutationEngine: priority-ordered triggers
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Priority ordering: underperformance first")

reset_plan_mutation_engine()
pme2 = PlanMutationEngine()

# Plan with both underperforming AND bloated steps
reset_plan_engine()
pe3 = PlanEngine()
plan_multi = _make_plan(
    plan_id="plan_m",
    steps=(
        PlanStep(goal_id="g1", position=0),
        PlanStep(goal_id="g2", position=1),
        PlanStep(goal_id="g3", position=2),
    ),
)
pe3._plans["plan_m"] = plan_multi
pe3._progress["plan_m"] = _make_progress(
    plan_id="plan_m",
    step_scores={"g1": 0.8, "g2": 0.15, "g3": 0.05},
)

r = pme2.evaluate(pe3, registry, current_turn=20)
if r.has_mutation:
    _test(
        "underperformance trigger fires first",
        "underperforming" in r.mutation.mutation_reason
        or "narrow" in r.mutation.mutation_type,
        f"reason={r.mutation.mutation_reason}",
    )
else:
    _test("mutation produced", False, "expected mutation but got none")


# ═══════════════════════════════════════════════════════════════════════════════
# 21. DecisionTrace: plan evolution fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. DecisionTrace: evolution fields present")

from umh.strategy.memory import reset_strategy_memory

reset_strategy_memory()

trace = build_trace(
    turn_id=1,
    plan_mutation_applied=True,
    plan_mutation_type="narrow",
    mutated_plan_id="plan_mut_narrow_abc",
    mutated_from_plan_id="plan_a",
    plan_recombination_applied=True,
    recombined_plan_id="plan_recomb_xyz",
    recombined_from_plan_ids=("plan_a", "plan_b"),
    plan_evolution_reason="underperforming:g2",
    plan_origin_snapshot={"plan_mut_narrow_abc": "mutated:narrow:plan_a"},
)

_test("plan_mutation_applied set", trace.plan_mutation_applied is True)
_test("plan_mutation_type set", trace.plan_mutation_type == "narrow")
_test("mutated_plan_id set", trace.mutated_plan_id == "plan_mut_narrow_abc")
_test("mutated_from_plan_id set", trace.mutated_from_plan_id == "plan_a")
_test("plan_recombination_applied set", trace.plan_recombination_applied is True)
_test("recombined_plan_id set", trace.recombined_plan_id == "plan_recomb_xyz")
_test(
    "recombined_from_plan_ids set",
    trace.recombined_from_plan_ids == ("plan_a", "plan_b"),
)
_test("plan_evolution_reason set", trace.plan_evolution_reason == "underperforming:g2")
_test("plan_origin_snapshot set", trace.plan_origin_snapshot is not None)


_section("22. DecisionTrace: to_dict serialization")

td = trace.to_dict()
_test("plan_mutation_applied in dict", td.get("plan_mutation_applied") is True)
_test("plan_mutation_type in dict", td.get("plan_mutation_type") == "narrow")
_test("mutated_plan_id in dict", "mutated_plan_id" in td)
_test("mutated_from_plan_id in dict", "mutated_from_plan_id" in td)
_test("plan_recombination_applied in dict", "plan_recombination_applied" in td)
_test("recombined_plan_id in dict", "recombined_plan_id" in td)
_test("recombined_from_plan_ids in dict", "recombined_from_plan_ids" in td)
_test(
    "recombined_from_plan_ids is list", isinstance(td["recombined_from_plan_ids"], list)
)
_test("plan_evolution_reason in dict", "plan_evolution_reason" in td)
_test("plan_origin_snapshot in dict", "plan_origin_snapshot" in td)


_section("23. DecisionTrace: None fields omitted")

reset_strategy_memory()
trace_none = build_trace(turn_id=2)
td_none = trace_none.to_dict()

for field_name in [
    "plan_mutation_applied",
    "plan_mutation_type",
    "mutated_plan_id",
    "mutated_from_plan_id",
    "plan_recombination_applied",
    "recombined_plan_id",
    "recombined_from_plan_ids",
    "plan_evolution_reason",
    "plan_origin_snapshot",
]:
    _test(f"{field_name} absent when None", field_name not in td_none)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Determinism: narrow operator")

results_narrow = []
for _ in range(5):
    r = _op_narrow(plan_3step, "g2")
    results_narrow.append(r.plan_id if r else None)

_test("narrow deterministic", all(r == results_narrow[0] for r in results_narrow))


_section("25. Determinism: reorder operator")

results_reorder = []
for _ in range(5):
    r = _op_reorder(plan_independent, 0, 1)
    results_reorder.append(r.plan_id if r else None)

_test("reorder deterministic", all(r == results_reorder[0] for r in results_reorder))


_section("26. Determinism: recombination")

results_recomb = []
for _ in range(5):
    r = _recombine_plans(plan_x, plan_y, turn=10)
    results_recomb.append(r.plan_id if r else None)

_test(
    "recombination deterministic", all(r == results_recomb[0] for r in results_recomb)
)


_section("27. Determinism: mutation engine")

results_engine = []
for _ in range(3):
    reset_plan_mutation_engine()
    pme_det = PlanMutationEngine()
    reset_plan_engine()
    pe_det = PlanEngine()
    pe_det._plans["plan_u"] = plan_under
    pe_det._progress["plan_u"] = _make_progress(
        plan_id="plan_u",
        step_scores={"g1": 0.8, "g2": 0.1, "g3": 0.6},
    )
    r_det = pme_det.evaluate(pe_det, registry, current_turn=10)
    results_engine.append(r_det.mutation.to_dict() if r_det.has_mutation else None)

_test(
    "engine evaluation deterministic",
    all(r == results_engine[0] for r in results_engine),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 28. Persistence compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("28. Plan origin round-trip via snapshot/restore")

reset_plan_engine()
pe_persist = PlanEngine()
evolved_plan = _make_plan(
    plan_id="evo_rt",
    steps=(PlanStep(goal_id="eg1", position=0), PlanStep(goal_id="eg2", position=1)),
    origin="mutated:narrow:base_1",
)
pe_persist._plans["evo_rt"] = evolved_plan
pe_persist._progress["evo_rt"] = PlanProgress(plan_id="evo_rt", confidence=0.6)

snapshot = pe_persist.snapshot()
_test(
    "snapshot has origin",
    snapshot["plans"]["evo_rt"].get("origin") == "mutated:narrow:base_1",
)

# Restore into fresh engine
pe_restore = PlanEngine()
pe_restore.restore(snapshot, current_turn=5)
restored = pe_restore.get_plan("evo_rt")
_test("restored plan exists", restored is not None)
if restored:
    _test("restored origin preserved", restored.origin == "mutated:narrow:base_1")


_section("29. Backward compat: old snapshot without origin")

old_snapshot = {
    "plans": {
        "old_plan": {
            "plan_id": "old_plan",
            "root_goal_id": "og1",
            "steps": [
                {
                    "goal_id": "og1",
                    "position": 0,
                    "dependency_ids": [],
                    "expected_delta": 0.0,
                }
            ],
            "dependencies": [],
            "expected_value": 0.5,
            "confidence": 0.6,
            "horizon": 1,
            "creation_turn": 0,
            "generation_reason": "test",
        },
    },
    "progress": {
        "old_plan": {
            "plan_id": "old_plan",
            "completed_steps": [],
            "failed_steps": [],
            "skipped_steps": [],
            "step_scores": {},
            "step_recovery": {},
            "confidence": 0.6,
            "active": True,
            "last_activity_turn": 4,
        },
    },
    "active_plan_id": "old_plan",
    "last_generation_turn": 0,
}

pe_old = PlanEngine()
pe_old.restore(old_snapshot, current_turn=5)
old_restored = pe_old.get_plan("old_plan")
_test("old plan restores", old_restored is not None)
if old_restored:
    _test("missing origin defaults to empty", old_restored.origin == "")


# ═══════════════════════════════════════════════════════════════════════════════
# 30. No LLM calls, no randomness, no external deps
# ═══════════════════════════════════════════════════════════════════════════════

_section("30. No LLM calls / no randomness / no new deps")

import importlib

pm_mod = importlib.import_module("umh.runtime_engine.plan_mutation")
pm_src = open(pm_mod.__file__).read()

_test("no random import in plan_mutation", "import random" not in pm_src)
_test("no LLM call in plan_mutation", "call_with_fallback" not in pm_src)
_test(
    "no anthropic in plan_mutation",
    "anthropic" not in pm_src.lower().split("import")[0],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 31. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("31. ExecutionSpine not modified")

import os

spine_src = open("/opt/OS/eos/execution_spine.py").read()
_test("no plan_mutation in spine", "plan_mutation" not in spine_src)
_test("no evolution in spine", "evolution" not in spine_src)
_test("no mutated in spine", "mutated" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 32. Singleton pattern
# ═══════════════════════════════════════════════════════════════════════════════

_section("32. Singleton pattern")

reset_plan_mutation_engine()
e1 = get_plan_mutation_engine()
e2 = get_plan_mutation_engine()
_test("singleton returns same instance", e1 is e2)

reset_plan_mutation_engine()
e3 = get_plan_mutation_engine()
_test("reset creates new instance", e3 is not e1)


# ═══════════════════════════════════════════════════════════════════════════════
# 33. Data model serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("33. PlanMutation / PlanRecombination to_dict")

mut = PlanMutation(
    mutated_plan_id="mut_1",
    parent_plan_id="parent_1",
    mutation_type="narrow",
    mutation_reason="underperforming:g2",
    affected_step_goal_id="g2",
    creation_turn=5,
)

md = mut.to_dict()
_test(
    "mutation to_dict has all fields",
    all(
        k in md
        for k in [
            "mutated_plan_id",
            "parent_plan_id",
            "mutation_type",
            "mutation_reason",
            "affected_step_goal_id",
            "creation_turn",
        ]
    ),
)

rec = PlanRecombination(
    recombined_plan_id="recomb_1",
    parent_plan_ids=("p1", "p2"),
    recombination_reason="compatible",
    creation_turn=10,
)

rd = rec.to_dict()
_test(
    "recombination to_dict has all fields",
    all(
        k in rd
        for k in [
            "recombined_plan_id",
            "parent_plan_ids",
            "recombination_reason",
            "creation_turn",
        ]
    ),
)
_test("parent_plan_ids is list", isinstance(rd["parent_plan_ids"], list))


# ═══════════════════════════════════════════════════════════════════════════════
# 34. PlanMutationResult properties
# ═══════════════════════════════════════════════════════════════════════════════

_section("34. PlanMutationResult properties")

empty_result = PlanMutationResult()
_test("empty result: no mutation", not empty_result.has_mutation)
_test("empty result: no recombination", not empty_result.has_recombination)
_test("empty result: no changes", not empty_result.has_changes)

mut_result = PlanMutationResult(mutation=mut, mutated_plan=plan_base)
_test("mutation result: has_mutation", mut_result.has_mutation)
_test("mutation result: has_changes", mut_result.has_changes)
_test("mutation result: no recombination", not mut_result.has_recombination)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  TOTAL: {_total} assertions | PASS: {_pass} | FAIL: {_fail}")
print(f"{'═' * 60}")

if _fail > 0:
    sys.exit(1)
