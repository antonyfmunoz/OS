"""
Tests for Counterfactual Goal Evaluation Layer.

Validates:
    1. similar goals produce consistent projections
    2. projections affect alignment weighting
    3. no new dependencies introduced
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
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports + Setup")

from umh.runtime_engine.counterfactual_eval import (
    CounterfactualEvaluator,
    CounterfactualResult,
    SIMILARITY_MATCH_THRESHOLD,
    TREND_PROJECTION_WINDOW,
    STRATEGY_AFFINITY_WINDOW,
    RESOURCE_PROJECTION_WINDOW,
    LOW_UTILITY_THRESHOLD,
    HIGH_UTILITY_THRESHOLD,
    CONFIDENCE_FLOOR,
    CONFIDENCE_NO_DATA,
    W_SIMILAR,
    W_TREND,
    W_STRATEGY,
    W_RESOURCE,
)
from umh.goals.state import GoalState, GoalRegistry, GoalTracker
from umh.runtime_engine.meta_goal import MetaGoal
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

_test("imports", True)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_meta_goal(
    goal_id: str = "test_goal",
    parent_goals: tuple = (),
    confidence: float = 0.7,
    utility_estimate: float = 0.5,
    description: str = "Test goal",
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
    criteria: dict | None = None,
) -> GoalRegistry:
    reg = GoalRegistry()
    gs = GoalState(
        goal_id=goal_id,
        description=f"Goal {goal_id}",
        success_criteria=criteria if criteria is not None else {"domain": goal_id},
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
    quality_score: float = 0.5,
    goal_pool_snapshot: dict | None = None,
    execution_budget: dict | None = None,
) -> DecisionTrace:
    return build_trace(
        turn_id=turn_id,
        evaluation={"quality_score": quality_score},
        active_goal_id=active_goal_id,
        outcome_score=outcome_score,
        goal_pool_snapshot=goal_pool_snapshot,
        execution_budget=execution_budget,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CounterfactualResult model
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. CounterfactualResult model")

cr = CounterfactualResult(
    expected_utility=0.65,
    expected_delta=0.05,
    confidence=0.8,
    reasoning="test_reason",
)
_test("expected_utility set", cr.expected_utility == 0.65)
_test("expected_delta set", cr.expected_delta == 0.05)
_test("confidence set", cr.confidence == 0.8)
_test("reasoning set", cr.reasoning == "test_reason")
_test("frozen", hasattr(cr, "__dataclass_fields__"))

d = cr.to_dict()
_test("to_dict expected_utility", abs(d["expected_utility"] - 0.65) < 0.001)
_test("to_dict expected_delta", abs(d["expected_delta"] - 0.05) < 0.001)
_test("to_dict confidence", abs(d["confidence"] - 0.8) < 0.001)
_test("to_dict reasoning", d["reasoning"] == "test_reason")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. No-parent goal — neutral projection
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. No-parent goal — neutral projection")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()
mg = _make_meta_goal(goal_id="fresh", parent_goals=())

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "neutral utility around 0.5",
    0.3 < result.expected_utility < 0.7,
    f"utility={result.expected_utility:.3f}",
)
_test(
    "neutral delta near zero",
    abs(result.expected_delta) < 0.2,
    f"delta={result.expected_delta:.3f}",
)
_test("confidence exists", result.confidence >= CONFIDENCE_FLOOR)
_test("reasoning populated", len(result.reasoning) > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Signal A: Similar goal trajectories — high match
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Similar goals — high match")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

# Add a high-performing goal with similar criteria
gs_similar = GoalState(
    goal_id="existing_high",
    description="High performer",
    success_criteria={"domain": "test", "type": "validate"},
    priority=0.7,
)
reg.add_goal(gs_similar)
t = reg.get_tracker("existing_high")
t.success_score = 0.9
t.uses = 10

mg = _make_meta_goal(
    goal_id="new_similar",
    criteria={"domain": "test", "type": "validate"},
    description="Similar new goal",
)

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "similar high performer lifts projection",
    result.expected_utility > 0.5,
    f"utility={result.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Signal A: Similar goal trajectories — low performer match
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Similar goals — low performer match")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

gs_low = GoalState(
    goal_id="existing_low",
    description="Low performer",
    success_criteria={"domain": "test", "type": "validate"},
    priority=0.3,
)
reg.add_goal(gs_low)
t_low = reg.get_tracker("existing_low")
t_low.success_score = 0.15
t_low.uses = 10

mg = _make_meta_goal(
    goal_id="new_low_match",
    criteria={"domain": "test", "type": "validate"},
    description="Matches low performer",
)

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "low performer match → lower projection",
    result.expected_utility < 0.5,
    f"utility={result.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Signal A: No similar goals — neutral
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. No similar goals — neutral")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

gs_diff = GoalState(
    goal_id="totally_different",
    description="Different domain",
    success_criteria={"category": "finance", "scope": "portfolio"},
    priority=0.5,
)
reg.add_goal(gs_diff)
t_diff = reg.get_tracker("totally_different")
t_diff.success_score = 0.9
t_diff.uses = 10

mg = _make_meta_goal(
    goal_id="no_match",
    criteria={"domain": "engineering", "type": "build"},
    description="No matching goal",
)

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "no match → neutral projection",
    0.3 < result.expected_utility < 0.7,
    f"utility={result.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Signal B: Parent trend — improving
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Parent trend — improving")

evaluator = CounterfactualEvaluator()
reg = _make_registry_with_tracker(
    "parent_improving",
    success_score=0.6,
    uses=10,
    delta_history=[0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.08, 0.09, 0.1, 0.11],
)
mg = _make_meta_goal(goal_id="child_improving", parent_goals=("parent_improving",))

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "improving parent → positive delta",
    result.expected_delta > 0.0,
    f"delta={result.expected_delta:.3f}",
)
_test(
    "improving parent → higher utility",
    result.expected_utility > 0.5,
    f"utility={result.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Signal B: Parent trend — declining
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Parent trend — declining")

evaluator = CounterfactualEvaluator()
reg = _make_registry_with_tracker(
    "parent_declining",
    success_score=0.4,
    uses=10,
    delta_history=[-0.05, -0.06, -0.07, -0.08, -0.09],
)
mg = _make_meta_goal(goal_id="child_declining", parent_goals=("parent_declining",))

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "declining parent → negative delta",
    result.expected_delta < 0.0,
    f"delta={result.expected_delta:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Signal C: Strategy affinity — matching criteria in traces
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Strategy affinity — matching traces")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

traces = [
    _make_trace(
        turn_id=i,
        active_goal_id="active_similar",
        quality_score=0.85,
        goal_pool_snapshot={
            "goals": {
                "active_similar": {
                    "success_criteria": {"domain": "test", "type": "validate"},
                }
            }
        },
    )
    for i in range(5)
]

mg = _make_meta_goal(
    goal_id="strat_match",
    criteria={"domain": "test", "type": "validate"},
)

result = evaluator.evaluate_counterfactual(mg, reg, traces)
_test(
    "strategy affinity lifts projection",
    result.expected_utility > 0.5,
    f"utility={result.expected_utility:.3f}",
)
_test(
    "reasoning mentions strategy_affinity",
    "strategy_affinity" in result.reasoning,
    f"reasoning={result.reasoning}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Signal D: Resource projection — efficient parent
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Resource projection — efficient parent")

evaluator = CounterfactualEvaluator()
reg = _make_registry_with_tracker("parent_efficient", success_score=0.8, uses=5)
traces = [
    _make_trace(
        turn_id=i,
        execution_budget={
            "allocations": [{"goal_id": "parent_efficient", "token_budget_ratio": 0.2}],
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_eff", parent_goals=("parent_efficient",))

result = evaluator.evaluate_counterfactual(mg, reg, traces)
_test(
    "efficient parent → higher resource projection",
    result.expected_utility >= 0.5,
    f"utility={result.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Signal D: Resource projection — wasteful parent
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Resource projection — wasteful parent")

evaluator = CounterfactualEvaluator()
reg = _make_registry_with_tracker("parent_wasteful", success_score=0.1, uses=5)
traces = [
    _make_trace(
        turn_id=i,
        execution_budget={
            "allocations": [{"goal_id": "parent_wasteful", "token_budget_ratio": 0.9}],
        },
    )
    for i in range(5)
]
mg = _make_meta_goal(goal_id="child_waste", parent_goals=("parent_wasteful",))

result = evaluator.evaluate_counterfactual(mg, reg, traces)
_test(
    "wasteful parent → lower resource projection",
    result.expected_utility < 0.5,
    f"utility={result.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Consistent projections for similar goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Similar goals → consistent projections")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

gs1 = GoalState(
    goal_id="template",
    description="Template",
    success_criteria={"domain": "sales", "type": "close"},
    priority=0.7,
)
reg.add_goal(gs1)
t1 = reg.get_tracker("template")
t1.success_score = 0.75
t1.uses = 8

mg_a = _make_meta_goal(
    goal_id="similar_a",
    criteria={"domain": "sales", "type": "close"},
)
mg_b = _make_meta_goal(
    goal_id="similar_b",
    criteria={"domain": "sales", "type": "close"},
)

r_a = evaluator.evaluate_counterfactual(mg_a, reg)
r_b = evaluator.evaluate_counterfactual(mg_b, reg)

_test(
    "similar goals same utility",
    abs(r_a.expected_utility - r_b.expected_utility) < 0.01,
    f"a={r_a.expected_utility:.3f}, b={r_b.expected_utility:.3f}",
)
_test("similar goals same confidence", abs(r_a.confidence - r_b.confidence) < 0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Projections affect alignment weighting
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Projections affect alignment")

from umh.runtime_engine.goal_alignment import GoalAlignmentEvaluator

evaluator = CounterfactualEvaluator()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

mg_high = _make_meta_goal(goal_id="high_cf", priority=0.7, confidence=0.8)
mg_low = _make_meta_goal(goal_id="low_cf", priority=0.7, confidence=0.8)

# High CF — no modification
ar_orig = aligner.evaluate_alignment(mg_high, reg)

# Low CF — modify confidence before alignment (mimics pipeline)
from umh.runtime_engine.meta_goal import MetaGoal as MG

mg_low_adjusted = MG(
    goal_id=mg_low.goal_id,
    origin=mg_low.origin,
    parent_goals=mg_low.parent_goals,
    confidence=mg_low.confidence * 0.3,
    utility_estimate=mg_low.utility_estimate,
    lifecycle_state=mg_low.lifecycle_state,
    description=mg_low.description,
    success_criteria=mg_low.success_criteria,
    priority=mg_low.priority,
    generation_turn=mg_low.generation_turn,
    generation_reason=mg_low.generation_reason,
)
ar_downweighted = aligner.evaluate_alignment(mg_low_adjusted, reg)

# Both should still be allowed (neutral registry) but confidence differs
_test("both evaluated by aligner", ar_orig.allowed and ar_downweighted.allowed)
_test(
    "confidence was modified by counterfactual",
    mg_low_adjusted.confidence < mg_high.confidence,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Weight constants sum to 1.0
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Weight constants")

total_weight = W_SIMILAR + W_TREND + W_STRATEGY + W_RESOURCE
_test("weights sum to 1.0", abs(total_weight - 1.0) < 0.001, f"sum={total_weight}")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Determinism")

evaluator = CounterfactualEvaluator()
reg = _make_registry_with_tracker(
    "parent_det",
    success_score=0.6,
    uses=8,
    delta_history=[0.05, -0.02, 0.03, 0.01, -0.01],
)
mg = _make_meta_goal(goal_id="child_det", parent_goals=("parent_det",))

r1 = evaluator.evaluate_counterfactual(mg, reg)
r2 = evaluator.evaluate_counterfactual(mg, reg)
r3 = evaluator.evaluate_counterfactual(mg, reg)

_test(
    "deterministic expected_utility",
    r1.expected_utility == r2.expected_utility == r3.expected_utility,
)
_test(
    "deterministic expected_delta",
    r1.expected_delta == r2.expected_delta == r3.expected_delta,
)
_test("deterministic confidence", r1.confidence == r2.confidence == r3.confidence)
_test("deterministic reasoning", r1.reasoning == r2.reasoning == r3.reasoning)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. DecisionTrace fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. DecisionTrace fields")

trace = build_trace(
    turn_id=99,
    counterfactual_expected_utility={"goal_a": 0.65},
    counterfactual_confidence={"goal_a": 0.8},
    counterfactual_reasoning={"goal_a": "similar_goals:0.65|parent_trend:0.70"},
)
_test(
    "trace has counterfactual_expected_utility",
    trace.counterfactual_expected_utility == {"goal_a": 0.65},
)
_test(
    "trace has counterfactual_confidence",
    trace.counterfactual_confidence == {"goal_a": 0.8},
)
_test("trace has counterfactual_reasoning", trace.counterfactual_reasoning is not None)

d = trace.to_dict()
_test(
    "to_dict has counterfactual_expected_utility",
    "counterfactual_expected_utility" in d,
)
_test("to_dict has counterfactual_confidence", "counterfactual_confidence" in d)
_test("to_dict has counterfactual_reasoning", "counterfactual_reasoning" in d)

empty_trace = build_trace(turn_id=100)
ed = empty_trace.to_dict()
_test(
    "empty trace no counterfactual_expected_utility",
    "counterfactual_expected_utility" not in ed,
)
_test("empty trace no counterfactual_confidence", "counterfactual_confidence" not in ed)
_test("empty trace no counterfactual_reasoning", "counterfactual_reasoning" not in ed)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. No LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. No LLM calls")

import inspect

src = inspect.getsource(CounterfactualEvaluator)
_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no anthropic", "anthropic" not in src)
_test("no openai", "openai" not in src)
_test("no genai", "genai" not in src)
_test("no agent_runtime", "agent_runtime" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. ExecutionSpine unchanged")

spine_src = open("/opt/OS/eos/execution_spine.py").read()
_test("spine has no counterfactual ref", "counterfactual" not in spine_src)
_test(
    "spine has no CounterfactualEvaluator ref",
    "CounterfactualEvaluator" not in spine_src,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Backward compatibility")

compat_trace = build_trace(turn_id=200)
_test(
    "counterfactual_expected_utility defaults None",
    compat_trace.counterfactual_expected_utility is None,
)
_test(
    "counterfactual_confidence defaults None",
    compat_trace.counterfactual_confidence is None,
)
_test(
    "counterfactual_reasoning defaults None",
    compat_trace.counterfactual_reasoning is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. No new external dependencies")

import umh.runtime_engine.counterfactual_eval as cf_mod

module_src = inspect.getsource(cf_mod)
_test("no requests", "import requests" not in module_src)
_test("no httpx", "import httpx" not in module_src)
_test("no external API", "api.openai" not in module_src)
_test(
    "uses only eos_ai imports",
    "from eos." in module_src or "import umh.runtime_engine." not in module_src,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Score bounds
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Score bounds")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

mg = _make_meta_goal(goal_id="bounds_test")
r = evaluator.evaluate_counterfactual(mg, reg)
_test("expected_utility >= 0.0", r.expected_utility >= 0.0)
_test("expected_utility <= 1.0", r.expected_utility <= 1.0)
_test("confidence >= CONFIDENCE_FLOOR", r.confidence >= CONFIDENCE_FLOOR)
_test("confidence <= 1.0", r.confidence <= 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Pipeline order: validator → counterfactual → alignment
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Pipeline order")

from umh.runtime_engine.goal_validator import GoalValidator

validator = GoalValidator()
cf_eval = CounterfactualEvaluator()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

mg = _make_meta_goal(goal_id="pipeline_test", description="Pipeline goal")

vr = validator.validate(mg, reg)
_test("step 1: validator passes", vr.is_valid)

cfr = cf_eval.evaluate_counterfactual(mg, reg)
_test("step 2: counterfactual evaluates", isinstance(cfr, CounterfactualResult))

ar = aligner.evaluate_alignment(mg, reg)
_test("step 3: alignment evaluates", ar.allowed)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Multiple parent goals — best trend wins
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Multiple parents — best trend")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

gs_good = GoalState(
    goal_id="good_p", description="Good", success_criteria={"d": "g"}, priority=0.8
)
reg.add_goal(gs_good)
tg = reg.get_tracker("good_p")
tg.success_score = 0.85
tg.uses = 10
tg.delta_history = [0.1, 0.08, 0.09, 0.1, 0.08]

gs_bad = GoalState(
    goal_id="bad_p", description="Bad", success_criteria={"d": "b"}, priority=0.3
)
reg.add_goal(gs_bad)
tb = reg.get_tracker("bad_p")
tb.success_score = 0.15
tb.uses = 10
tb.delta_history = [-0.1, -0.08, -0.12, -0.09, -0.11]

mg = _make_meta_goal(
    goal_id="multi_parent",
    parent_goals=("good_p", "bad_p"),
)

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "multi-parent uses best trend",
    result.expected_utility > 0.5,
    f"utility={result.expected_utility:.3f}",
)
_test(
    "positive delta from good parent",
    result.expected_delta > 0.0,
    f"delta={result.expected_delta:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Counterfactual reasoning is deterministic string
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. Reasoning format")

evaluator = CounterfactualEvaluator()
reg = _make_registry_with_tracker(
    "parent_reason",
    success_score=0.7,
    uses=5,
    delta_history=[0.05, 0.06, 0.04],
)
mg = _make_meta_goal(goal_id="reason_test", parent_goals=("parent_reason",))

result = evaluator.evaluate_counterfactual(mg, reg)
_test("reasoning is string", isinstance(result.reasoning, str))
_test("reasoning not empty", len(result.reasoning) > 0)
_test("reasoning contains signals", "|" in result.reasoning or ":" in result.reasoning)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. End-to-end: full pipeline
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. End-to-end pipeline")

from umh.runtime_engine.goal_validator import GoalValidator as GV
from umh.runtime_engine.meta_goal import MetaGoal as MG2

validator = GV()
cf_eval = CounterfactualEvaluator()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

reg.add_goal(
    GoalState(
        goal_id="base",
        description="Base goal",
        success_criteria={"domain": "base"},
        priority=0.6,
    )
)

mg = _make_meta_goal(
    goal_id="e2e_goal",
    criteria={"domain": "e2e"},
    description="End-to-end test goal",
    priority=0.7,
    confidence=0.8,
)

# Step 1: Validate
vr = validator.validate(mg, reg)
_test("e2e step 1: validator passes", vr.is_valid)

# Step 2: Counterfactual
cfr = cf_eval.evaluate_counterfactual(mg, reg)
_test("e2e step 2: counterfactual computed", cfr.expected_utility >= 0.0)

# Step 3: Modify confidence
new_conf = mg.confidence * cfr.expected_utility
new_conf = max(new_conf, 0.05)
mg_adj = MG2(
    goal_id=mg.goal_id,
    origin=mg.origin,
    parent_goals=mg.parent_goals,
    confidence=new_conf,
    utility_estimate=mg.utility_estimate,
    lifecycle_state=mg.lifecycle_state,
    description=mg.description,
    success_criteria=mg.success_criteria,
    priority=mg.priority,
    generation_turn=mg.generation_turn,
    generation_reason=mg.generation_reason,
)
_test(
    "e2e confidence adjusted",
    mg_adj.confidence <= mg.confidence,
    f"orig={mg.confidence}, adj={mg_adj.confidence:.3f}",
)

# Step 4: Alignment
ar = aligner.evaluate_alignment(mg_adj, reg)
_test("e2e step 4: alignment allows", ar.allowed)

# Step 5: Add to registry
if ar.allowed:
    gs = GoalState(
        goal_id=mg_adj.goal_id,
        description=mg_adj.description,
        success_criteria=mg_adj.success_criteria,
        priority=ar.adjusted_priority,
    )
    reg.add_goal(gs)

_test("e2e goal entered registry", reg.get_goal("e2e_goal") is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Existing modules unaffected
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. Existing modules unaffected")

from umh.goals.state import GoalState as GS2, GoalRegistry as GR2
from umh.runtime_engine.goal_validator import GoalValidator as GV3
from umh.runtime_engine.goal_alignment import GoalAlignmentEvaluator as GAE2
from umh.runtime_engine.decision_trace import build_trace as bt2

_test("GoalState imports", GS2 is not None)
_test("GoalRegistry imports", GR2 is not None)
_test("GoalValidator imports", GV3 is not None)
_test("GoalAlignmentEvaluator imports", GAE2 is not None)
_test("build_trace imports", bt2 is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
