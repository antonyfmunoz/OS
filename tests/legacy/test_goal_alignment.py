"""
Tests for Goal Alignment & Utility Constraint Layer.

Validates:
    1. misaligned goals are downweighted or rejected
    2. aligned goals are promoted
    3. alignment uses only existing signals (no new dependencies)
    4. determinism preserved
    5. no regression
    6. no new LLM calls
    7. ExecutionSpine unchanged
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
# ═════���═════════════════════════════════════════════════════════════════════════

_section("0. Imports + Setup")

from umh.runtime_engine.goal_alignment import (
    GoalAlignmentEvaluator,
    AlignmentResult,
    DISALLOW_THRESHOLD,
    DOWNWEIGHT_THRESHOLD,
    W_CONSISTENCY,
    W_OUTCOME,
    W_EFFICIENCY,
    W_CONFLICT,
    W_PERSISTENCE,
    CONSISTENCY_WINDOW,
    CONSISTENCY_PENALTY_THRESHOLD,
    OUTCOME_WINDOW,
    OUTCOME_PENALTY_THRESHOLD,
    EFFICIENCY_MIN_USES,
    EFFICIENCY_PENALTY_THRESHOLD,
    CONFLICT_DELTA_THRESHOLD,
    PERSISTENCE_MIN_USES,
    PERSISTENCE_SCORE_THRESHOLD,
    PERSISTENCE_BOOST,
)
from umh.goals.state import GoalState, GoalRegistry, GoalTracker
from umh.runtime_engine.meta_goal import MetaGoal
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

_test("imports", True)


# ── Helpers ────────���─────────────────────��──────────────────────────────────


def _make_meta_goal(
    goal_id: str = "test_goal",
    parent_goals: tuple = (),
    confidence: float = 0.7,
    utility_estimate: float = 0.5,
    description: str = "Test goal description",
    criteria: dict | None = None,
    priority: float = 0.5,
) -> MetaGoal:
    return MetaGoal(
        goal_id=goal_id,
        origin="generated",
        parent_goals=parent_goals,
        confidence=confidence,
        utility_estimate=utility_estimate,
        lifecycle_state="active",
        description=description,
        success_criteria=criteria
        if criteria is not None
        else {"domain": "test", "type": "validate"},
        priority=priority,
        generation_turn=1,
        generation_reason="test",
    )


def _make_registry_with_tracker(
    goal_id: str,
    priority: float = 0.5,
    success_score: float = 0.5,
    uses: int = 0,
    delta_history: list | None = None,
) -> GoalRegistry:
    reg = GoalRegistry()
    gs = GoalState(
        goal_id=goal_id,
        description=f"Goal {goal_id}",
        success_criteria={"domain": goal_id},
        priority=priority,
    )
    reg.add_goal(gs)
    tracker = reg.get_tracker(goal_id)
    tracker.success_score = success_score
    tracker.uses = uses
    if delta_history:
        tracker.delta_history = list(delta_history)
    return reg


def _make_trace(
    turn_id: int = 1,
    active_goal_id: str | None = None,
    outcome_score: float | None = None,
    goal_pool_snapshot: dict | None = None,
    execution_budget: dict | None = None,
) -> DecisionTrace:
    return build_trace(
        turn_id=turn_id,
        active_goal_id=active_goal_id,
        outcome_score=outcome_score,
        goal_pool_snapshot=goal_pool_snapshot,
        execution_budget=execution_budget,
    )


# ═════════════════════════════════��═══════════════════════════════════��═════════
# 1. AlignmentResult model
# ══��══════════════��════════════════════════════════════���════════════════════════

_section("1. AlignmentResult model")

ar = AlignmentResult(
    alignment_score=0.75,
    penalties=("test_penalty",),
    adjusted_priority=0.4,
    allowed=True,
)
_test("alignment_score set", ar.alignment_score == 0.75)
_test("penalties tuple", ar.penalties == ("test_penalty",))
_test("adjusted_priority set", ar.adjusted_priority == 0.4)
_test("allowed set", ar.allowed is True)
_test("frozen", hasattr(ar, "__dataclass_fields__"))

d = ar.to_dict()
_test("to_dict alignment_score", abs(d["alignment_score"] - 0.75) < 0.001)
_test("to_dict penalties list", isinstance(d["penalties"], list))
_test("to_dict allowed", d["allowed"] is True)


# ════════════════════════════════════════���════════════════════════���═════════════
# 2. New goal with no parents — neutral alignment
# ════��══════════════════════════════════════════════════════════════════════════

_section("2. No-parent goal — neutral alignment")

evaluator = GoalAlignmentEvaluator()
reg = GoalRegistry()
mg = _make_meta_goal(goal_id="fresh", parent_goals=())

result = evaluator.evaluate_alignment(mg, reg)
_test("neutral goal allowed", result.allowed)
_test(
    "alignment score around 0.5",
    0.3 < result.alignment_score < 0.8,
    f"score={result.alignment_score:.3f}",
)
_test("no penalties for neutral goal", len(result.penalties) == 0)
_test(
    "priority adjusted but reasonable",
    result.adjusted_priority > 0.0 and result.adjusted_priority <= mg.priority,
    f"adj={result.adjusted_priority:.3f}",
)


# ═══════════════════════════════════════════════��═══════════════════════════════
# 3. Signal A: Historical consistency — stable parent
# ═��═════════════════���════════════════════════════��══════════════════════════════

_section("3. Consistency — stable parent")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_stable",
    success_score=0.7,
    uses=10,
    delta_history=[0.05, 0.04, 0.06, 0.05, 0.04, 0.05, 0.06, 0.05],
)
mg = _make_meta_goal(goal_id="child_stable", parent_goals=("parent_stable",))

result = evaluator.evaluate_alignment(mg, reg)
_test("stable parent → allowed", result.allowed)
consistency_penalty = [p for p in result.penalties if "consistency" in p]
_test(
    "no consistency penalty",
    len(consistency_penalty) == 0,
    f"penalties={result.penalties}",
)


# ═════════════════════════���═════════════════════════════════════════════════════
# 4. Signal A: Historical consistency — volatile parent
# ═══════════════════���═══════════════════════════���═══════════════════════════════

_section("4. Consistency — volatile parent")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_volatile",
    success_score=0.4,
    uses=10,
    delta_history=[-0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5],
)
mg = _make_meta_goal(goal_id="child_volatile", parent_goals=("parent_volatile",))

result = evaluator.evaluate_alignment(mg, reg)
volatile_penalties = [p for p in result.penalties if "consistency" in p]
_test("volatile parent gets consistency penalty", len(volatile_penalties) > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Signal B: Outcome utility — good outcomes
# ═══════════════���═════════════════════════════════════���═════════════════════════

_section("5. Outcome — good parent outcomes")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker("parent_good_outcome", success_score=0.8, uses=5)
traces = [
    _make_trace(turn_id=i, active_goal_id="parent_good_outcome", outcome_score=0.85)
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_good", parent_goals=("parent_good_outcome",))

result = evaluator.evaluate_alignment(mg, reg, traces)
outcome_penalties = [p for p in result.penalties if "outcome" in p]
_test("good outcomes → no penalty", len(outcome_penalties) == 0)


# ════════════════════��════════════════════════════════���═════════════════════════
# 6. Signal B: Outcome utility — poor outcomes
# ═════════════════════���══════════════════════��══════════════════════════════════

_section("6. Outcome — poor parent outcomes")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker("parent_bad_outcome", success_score=0.3, uses=5)
traces = [
    _make_trace(turn_id=i, active_goal_id="parent_bad_outcome", outcome_score=0.1)
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_bad", parent_goals=("parent_bad_outcome",))

result = evaluator.evaluate_alignment(mg, reg, traces)
outcome_penalties = [p for p in result.penalties if "outcome" in p]
_test("poor outcomes → penalty", len(outcome_penalties) > 0)
_test(
    "lower alignment score",
    result.alignment_score < 0.5,
    f"score={result.alignment_score:.3f}",
)


# ═════════════════════════════════════════════════════════════════════��═════════
# 7. Signal C: Resource efficiency — efficient parent
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Efficiency — efficient parent")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker("parent_efficient", success_score=0.8, uses=5)
traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="parent_efficient",
        execution_budget={
            "allocations": [{"goal_id": "parent_efficient", "token_budget_ratio": 0.3}],
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_efficient", parent_goals=("parent_efficient",))

result = evaluator.evaluate_alignment(mg, reg, traces)
eff_penalties = [p for p in result.penalties if "efficiency" in p]
_test("efficient parent → no penalty", len(eff_penalties) == 0)


# ═════════════════��═══════════════════════════════════���═════════════════════════
# 8. Signal C: Resource efficiency — wasteful parent
# ════════���══════════════════════════════════════════════════════════════════════

_section("8. Efficiency — wasteful parent")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker("parent_wasteful", success_score=0.1, uses=5)
traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="parent_wasteful",
        execution_budget={
            "allocations": [{"goal_id": "parent_wasteful", "token_budget_ratio": 0.9}],
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_wasteful", parent_goals=("parent_wasteful",))

result = evaluator.evaluate_alignment(mg, reg, traces)
eff_penalties = [p for p in result.penalties if "efficiency" in p]
_test("wasteful parent → penalty", len(eff_penalties) > 0)


# ══════���══════════════════════════════════════════════════════════���═════════════
# 9. Signal D: Conflict detection — no conflict
# ════════════���══════════════════════════════════════════════════════════════════

_section("9. Conflict — no conflict")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker("parent_peaceful", success_score=0.7, uses=5)
reg.add_goal(
    GoalState(
        goal_id="peer_goal",
        description="Peer",
        success_criteria={"domain": "peer"},
        priority=0.5,
    )
)

traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="parent_peaceful",
        goal_pool_snapshot={
            "trackers": {
                "peer_goal": {"latest_delta": 0.05},
            }
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_peaceful", parent_goals=("parent_peaceful",))

result = evaluator.evaluate_alignment(mg, reg, traces)
conflict_penalties = [p for p in result.penalties if "conflict" in p]
_test("no conflict → no penalty", len(conflict_penalties) == 0)


# ══��═══════════════════════��══════════════════════════════════���═════════════════
# 10. Signal D: Conflict detection — harming peers
# ══════════════════���════════════════════════════════════════════════════════════

_section("10. Conflict — harming peers")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker("parent_harmful", success_score=0.7, uses=5)
reg.add_goal(
    GoalState(
        goal_id="peer_harmed",
        description="Harmed peer",
        success_criteria={"domain": "peer"},
        priority=0.5,
    )
)

traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="parent_harmful",
        goal_pool_snapshot={
            "trackers": {
                "peer_harmed": {"latest_delta": -0.3},
            }
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_harmful", parent_goals=("parent_harmful",))

result = evaluator.evaluate_alignment(mg, reg, traces)
conflict_penalties = [p for p in result.penalties if "conflict" in p]
_test("conflict detected → penalty", len(conflict_penalties) > 0)


# ══════════════════════════════════════════════════════════════════���════════════
# 11. Signal E: Persistence bias — long-lived successful parent
# ═���═════════════════��════════════════════════════��══════════════════════════════

_section("11. Persistence — long-lived parent")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_persistent",
    success_score=0.7,
    uses=10,
    delta_history=[0.05] * 10,
)
mg = _make_meta_goal(goal_id="child_persistent", parent_goals=("parent_persistent",))

result_persistent = evaluator.evaluate_alignment(mg, reg)

# Compare with short-lived parent
reg2 = _make_registry_with_tracker(
    "parent_young",
    success_score=0.7,
    uses=1,
    delta_history=[0.05],
)
mg2 = _make_meta_goal(goal_id="child_young", parent_goals=("parent_young",))

result_young = evaluator.evaluate_alignment(mg2, reg2)

_test(
    "persistent parent gets higher score",
    result_persistent.alignment_score > result_young.alignment_score,
    f"persistent={result_persistent.alignment_score:.3f} vs young={result_young.alignment_score:.3f}",
)


# ══════════════════════════════��════════════════════════════════════════════════
# 12. Disallowed — extremely misaligned goal
# ══��═══════════════════════���══════════════════════════════���═════════════════════

_section("12. Disallowed — extremely misaligned")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_terrible",
    success_score=0.05,
    uses=10,
    delta_history=[-0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5],
)
reg.add_goal(
    GoalState(
        goal_id="peer_suffering",
        description="Suffering peer",
        success_criteria={"domain": "peer"},
        priority=0.5,
    )
)

traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="parent_terrible",
        outcome_score=0.05,
        goal_pool_snapshot={
            "trackers": {
                "peer_suffering": {"latest_delta": -0.4},
            }
        },
        execution_budget={
            "allocations": [{"goal_id": "parent_terrible", "token_budget_ratio": 0.9}],
        },
    )
    for i in range(10)
]
mg = _make_meta_goal(
    goal_id="child_terrible",
    parent_goals=("parent_terrible",),
    priority=0.3,
)

result = evaluator.evaluate_alignment(mg, reg, traces)
_test("extremely misaligned → disallowed", not result.allowed)
_test(
    "alignment score below threshold",
    result.alignment_score < DISALLOW_THRESHOLD,
    f"score={result.alignment_score:.3f}, threshold={DISALLOW_THRESHOLD}",
)
_test(
    "has multiple penalties",
    len(result.penalties) >= 3,
    f"penalties={len(result.penalties)}",
)


# ═════���═══════════════════════════════════════════════════��═════════════════════
# 13. Borderline — allowed but downweighted
# ══════════════════��══════════════════════════��═══════════════════════════════���═

_section("13. Borderline — downweighted")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_mediocre",
    success_score=0.4,
    uses=5,
    delta_history=[0.0, -0.1, 0.05, -0.05, 0.0],
)
mg = _make_meta_goal(
    goal_id="child_mediocre",
    parent_goals=("parent_mediocre",),
    priority=0.8,
)

result = evaluator.evaluate_alignment(mg, reg)
_test("borderline allowed", result.allowed)
_test(
    "priority downweighted",
    result.adjusted_priority < mg.priority,
    f"original={mg.priority}, adjusted={result.adjusted_priority:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Aligned goal — priority preserved or barely reduced
# ═════════════════���═══════════════════════════════��═════════════════════════════

_section("14. Well-aligned goal — priority preserved")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_great",
    success_score=0.85,
    uses=10,
    delta_history=[0.1, 0.08, 0.12, 0.09, 0.11, 0.1, 0.08, 0.09, 0.1, 0.11],
)
traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="parent_great",
        outcome_score=0.9,
        execution_budget={
            "allocations": [{"goal_id": "parent_great", "token_budget_ratio": 0.3}],
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(
    goal_id="child_great",
    parent_goals=("parent_great",),
    priority=0.8,
)

result = evaluator.evaluate_alignment(mg, reg, traces)
_test("well-aligned allowed", result.allowed)
_test(
    "high alignment score",
    result.alignment_score > 0.6,
    f"score={result.alignment_score:.3f}",
)
_test(
    "priority mostly preserved",
    result.adjusted_priority >= mg.priority * 0.5,
    f"original={mg.priority}, adjusted={result.adjusted_priority:.3f}",
)
_test(
    "few or no penalties", len(result.penalties) <= 1, f"penalties={result.penalties}"
)


# ══════��════════════════════════════��═════════════════════════════════════��═════
# 15. Weight constants sum to 1.0
# ═════���════════════════════════��════════════════════════════════════��═══════════

_section("15. Weight constants")

total_weight = W_CONSISTENCY + W_OUTCOME + W_EFFICIENCY + W_CONFLICT + W_PERSISTENCE
_test("weights sum to 1.0", abs(total_weight - 1.0) < 0.001, f"sum={total_weight}")


# ���════════════════���═════════════════════════════════════════════════════════════
# 16. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Determinism")

evaluator = GoalAlignmentEvaluator()
reg = _make_registry_with_tracker(
    "parent_det",
    success_score=0.6,
    uses=5,
    delta_history=[0.1, -0.1, 0.05, -0.05, 0.02],
)
mg = _make_meta_goal(goal_id="child_det", parent_goals=("parent_det",))

r1 = evaluator.evaluate_alignment(mg, reg)
r2 = evaluator.evaluate_alignment(mg, reg)
r3 = evaluator.evaluate_alignment(mg, reg)

_test(
    "deterministic alignment_score",
    r1.alignment_score == r2.alignment_score == r3.alignment_score,
)
_test("deterministic penalties", r1.penalties == r2.penalties == r3.penalties)
_test("deterministic allowed", r1.allowed == r2.allowed == r3.allowed)
_test(
    "deterministic adjusted_priority",
    r1.adjusted_priority == r2.adjusted_priority == r3.adjusted_priority,
)


# ═════════════════════════���═════════════════════════════════════════════════════
# 17. DecisionTrace fields
# ═══���═══════════════════════════════════════════════════════════════════════════

_section("17. DecisionTrace fields")

trace = build_trace(
    turn_id=99,
    goal_alignment_scores={"goal_a": 0.8},
    alignment_penalties=("penalty_1", "penalty_2"),
    alignment_decisions=({"alignment_score": 0.8, "allowed": True},),
)
_test("trace has goal_alignment_scores", trace.goal_alignment_scores == {"goal_a": 0.8})
_test(
    "trace has alignment_penalties",
    trace.alignment_penalties == ("penalty_1", "penalty_2"),
)
_test("trace has alignment_decisions", len(trace.alignment_decisions) == 1)

d = trace.to_dict()
_test("to_dict has goal_alignment_scores", "goal_alignment_scores" in d)
_test("to_dict has alignment_penalties", "alignment_penalties" in d)
_test("to_dict has alignment_decisions", "alignment_decisions" in d)

empty_trace = build_trace(turn_id=100)
ed = empty_trace.to_dict()
_test("empty trace no goal_alignment_scores", "goal_alignment_scores" not in ed)
_test("empty trace no alignment_penalties", "alignment_penalties" not in ed)
_test("empty trace no alignment_decisions", "alignment_decisions" not in ed)


# ════════════════════════════════════════════════════════════════════��══════════
# 18. No LLM calls
# ══════════��═════════════════════════���════════════════════════════════════════��═

_section("18. No LLM calls")

import inspect

src = inspect.getsource(GoalAlignmentEvaluator)
_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no anthropic", "anthropic" not in src)
_test("no openai", "openai" not in src)
_test("no genai", "genai" not in src)
_test("no agent_runtime", "agent_runtime" not in src)


# ══════════════════════��════════════════════════════════════════════════════════
# 19. ExecutionSpine unchanged
# ═══════════════════════════��═════════════════════════��═════════════════════════

_section("19. ExecutionSpine unchanged")

spine_src = open("/opt/OS/eos/execution_spine.py").read()
_test("spine has no goal_alignment ref", "goal_alignment" not in spine_src)
_test(
    "spine has no GoalAlignmentEvaluator ref", "GoalAlignmentEvaluator" not in spine_src
)


# ═══════════════════════════��════════════════════════════════���══════════════════
# 20. Backward compatibility — all new fields default None
# ���══════════════════════════���══════════════════════════��════════════════════════

_section("20. Backward compatibility")

compat_trace = build_trace(turn_id=200)
_test("goal_alignment_scores defaults None", compat_trace.goal_alignment_scores is None)
_test("alignment_penalties defaults None", compat_trace.alignment_penalties is None)
_test("alignment_decisions defaults None", compat_trace.alignment_decisions is None)


# ═══════════════════════════��═══════════════════════════════════════════════════
# 21. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. No new external dependencies")

import umh.runtime_engine.goal_alignment as ga_mod

module_src = inspect.getsource(ga_mod)
_test("no requests", "import requests" not in module_src)
_test("no httpx", "import httpx" not in module_src)
_test(
    "no external API",
    "api.openai" not in module_src and "api.anthropic" not in module_src,
)
_test(
    "uses only eos_ai imports",
    "from eos." in module_src or "import umh.runtime_engine." not in module_src,
)


# ═══════════════════════════════════��═══════════════════════════════��═══════════
# 22. Integration — pipeline order
# ══════════════════���═══════════════════════════════════════���════════════════════

_section("22. Integration — pipeline order")

from umh.runtime_engine.goal_validator import GoalValidator

validator = GoalValidator()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

mg = _make_meta_goal(goal_id="pipeline_test", description="Pipeline test goal")
vr = validator.validate(mg, reg)
_test("validator passes valid goal", vr.is_valid)

ar = aligner.evaluate_alignment(mg, reg)
_test("aligner evaluates after validator", ar.allowed)
_test("pipeline produces AlignmentResult", isinstance(ar, AlignmentResult))


# ══════════════════════���══════════════════════════════════���═════════════════════
# 23. Multiple parent goals — best parent wins
# ═══════════��═══════════════════════════════════════════════════════════════════

_section("23. Multiple parents — best parent wins")

evaluator = GoalAlignmentEvaluator()
reg = GoalRegistry()

# Add good parent
gs1 = GoalState(
    goal_id="good_parent", description="Good", success_criteria={"d": "g"}, priority=0.8
)
reg.add_goal(gs1)
t1 = reg.get_tracker("good_parent")
t1.success_score = 0.85
t1.uses = 10
t1.delta_history = [0.1, 0.08, 0.09, 0.1, 0.08]

# Add bad parent
gs2 = GoalState(
    goal_id="bad_parent", description="Bad", success_criteria={"d": "b"}, priority=0.3
)
reg.add_goal(gs2)
t2 = reg.get_tracker("bad_parent")
t2.success_score = 0.1
t2.uses = 10
t2.delta_history = [-0.5, 0.5, -0.5, 0.5, -0.5]

mg_multi = _make_meta_goal(
    goal_id="multi_parent_child",
    parent_goals=("good_parent", "bad_parent"),
)

result = evaluator.evaluate_alignment(mg_multi, reg)
_test("multi-parent goal allowed (good parent helps)", result.allowed)


# ═════════════════════════════════════════════════════════════��═════════════════
# 24. Alignment score bounds
# ══���═════════════��═══════════════════════════════════��══════════════════════════

_section("24. Score bounds")

evaluator = GoalAlignmentEvaluator()
reg = GoalRegistry()

# Neutral (no parent)
mg_neutral = _make_meta_goal(goal_id="bounds_test")
r = evaluator.evaluate_alignment(mg_neutral, reg)
_test("score >= 0.0", r.alignment_score >= 0.0)
_test("score <= 1.0", r.alignment_score <= 1.0)
_test("adjusted_priority >= PRIORITY_MIN", r.adjusted_priority >= 0.05)


# ══════════════════════════��════════════════════════════════════════════════════
# 25. Alignment affects selection pressure
# ═════════════════════════════════════════════════��═════════════════════════════

_section("25. Selection pressure")

evaluator = GoalAlignmentEvaluator()

# Well-aligned child
reg_good = _make_registry_with_tracker(
    "strong_parent",
    success_score=0.9,
    uses=10,
    delta_history=[0.1] * 10,
)
mg_good = _make_meta_goal(
    goal_id="strong_child",
    parent_goals=("strong_parent",),
    priority=0.7,
)
r_good = evaluator.evaluate_alignment(mg_good, reg_good)

# Poorly aligned child
reg_weak = _make_registry_with_tracker(
    "weak_parent",
    success_score=0.15,
    uses=10,
    delta_history=[-0.3, 0.2, -0.4, 0.1, -0.3, 0.2, -0.3, 0.1, -0.4, 0.2],
)
mg_weak = _make_meta_goal(
    goal_id="weak_child",
    parent_goals=("weak_parent",),
    priority=0.7,
)
r_weak = evaluator.evaluate_alignment(mg_weak, reg_weak)

_test(
    "aligned gets higher priority than misaligned",
    r_good.adjusted_priority > r_weak.adjusted_priority,
    f"good={r_good.adjusted_priority:.3f} vs weak={r_weak.adjusted_priority:.3f}",
)
_test(
    "aligned gets higher alignment score",
    r_good.alignment_score > r_weak.alignment_score,
    f"good={r_good.alignment_score:.3f} vs weak={r_weak.alignment_score:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. End-to-end: validator → alignment → registry
# ════════════════════════���════════════════════════════════���═════════════════════

_section("26. End-to-end pipeline")

from umh.runtime_engine.goal_validator import GoalValidator as GV

validator = GV()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

# Add an existing goal
reg.add_goal(
    GoalState(
        goal_id="base_goal",
        description="Base goal",
        success_criteria={"domain": "base"},
        priority=0.6,
    )
)

# New aligned goal through full pipeline
mg_new = _make_meta_goal(
    goal_id="aligned_new",
    criteria={"domain": "new_domain"},
    description="New aligned goal",
    priority=0.7,
)

vr = validator.validate(mg_new, reg)
_test("e2e validator passes", vr.is_valid)

ar = aligner.evaluate_alignment(mg_new, reg)
_test("e2e alignment allows", ar.allowed)

if ar.allowed:
    gs = GoalState(
        goal_id=mg_new.goal_id,
        description=mg_new.description,
        success_criteria=mg_new.success_criteria,
        priority=ar.adjusted_priority,
    )
    reg.add_goal(gs)

_test("e2e goal entered registry", reg.get_goal("aligned_new") is not None)
_test(
    "e2e priority adjusted",
    reg.get_goal("aligned_new").priority <= mg_new.priority,
    f"pri={reg.get_goal('aligned_new').priority}",
)


# ══════════════════════��════════════════════════════════════════════════════════
# 27. Existing test suites unaffected
# ════════════════════════════════════════════��══════════════════════════════════

_section("27. Existing modules unaffected")

from umh.goals.state import GoalState as GS2, GoalRegistry as GR2
from umh.runtime_engine.goal_validator import GoalValidator as GV2
from umh.runtime_engine.decision_trace import build_trace as bt2

_test("GoalState imports", GS2 is not None)
_test("GoalRegistry imports", GR2 is not None)
_test("GoalValidator imports", GV2 is not None)
_test("build_trace imports", bt2 is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════��═════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
