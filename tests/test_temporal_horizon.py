"""
Tests for Temporal Horizon Evaluation.

Proves:
    1. Goals with low immediate utility but strong future payoff survive
    2. Purely bad goals still suppressed
    3. No regressions
    4. Determinism preserved
    5. No LLM calls
    6. ExecutionSpine unchanged
"""

import sys
import inspect

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

from umh.runtime_engine.counterfactual_eval import (
    CounterfactualResult,
    CounterfactualEvaluator,
    HORIZON_WEIGHT,
    UNCERTAINTY_WEIGHT,
    CONFIDENCE_FLOOR,
    HORIZON_TRACE_WINDOW,
    HORIZON_ENABLEMENT_MIN_USES,
    HORIZON_DELAYED_PAYOFF_WINDOW,
    HIGH_QUALITY_THRESHOLD,
)
from umh.runtime_engine.adaptive_exploration import (
    ExplorationController,
    HORIZON_FUTURE_BOOST,
    DEFAULT_EXPLORATION,
    MIN_EXPLORATION,
    MAX_EXPLORATION,
)
from umh.runtime_engine.decision_trace import build_trace
from umh.goals.state import GoalState, GoalRegistry
from umh.runtime_engine.meta_goal import MetaGoal

_test("all imports succeed", True)


# ── Helpers ────────────────────────────────────────────────────────────────


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
        success_criteria=criteria if criteria is not None else {"domain": "test"},
        priority=priority,
        generation_turn=1,
        generation_reason="test",
    )


def _make_trace(
    turn_id: int = 1,
    active_goal_id: str | None = None,
    quality_score: float = 0.5,
    goal_pool_snapshot: dict | None = None,
) -> object:
    return build_trace(
        turn_id=turn_id,
        evaluation={"quality_score": quality_score},
        active_goal_id=active_goal_id,
        goal_pool_snapshot=goal_pool_snapshot,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CounterfactualResult — horizon_value field
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. CounterfactualResult — Horizon Fields")

cr_with_horizon = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
    horizon_value=0.6,
    horizon_reason="enablement:0.60",
)
_test("horizon_value stored", cr_with_horizon.horizon_value == 0.6)
_test("horizon_reason stored", cr_with_horizon.horizon_reason == "enablement:0.60")
_test(
    "effective_utility includes horizon",
    cr_with_horizon.effective_utility > 0.3 + cr_with_horizon.exploration_boost,
    f"effective={cr_with_horizon.effective_utility:.3f}",
)

expected_effective = min(
    1.0,
    0.3 + (1.0 - 0.8) * UNCERTAINTY_WEIGHT + HORIZON_WEIGHT * 0.6,
)
_test(
    "effective_utility formula correct",
    abs(cr_with_horizon.effective_utility - expected_effective) < 0.001,
    f"got={cr_with_horizon.effective_utility:.4f}, expected={expected_effective:.4f}",
)

# Default horizon_value = 0.0 — backward compat
cr_no_horizon = CounterfactualResult(
    expected_utility=0.3,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
)
_test("default horizon_value is 0.0", cr_no_horizon.horizon_value == 0.0)
_test("default horizon_reason is empty", cr_no_horizon.horizon_reason == "")

# to_dict includes horizon fields
d = cr_with_horizon.to_dict()
_test("to_dict has horizon_value", "horizon_value" in d)
_test("to_dict has horizon_reason", "horizon_reason" in d)
_test("to_dict horizon_value correct", abs(d["horizon_value"] - 0.6) < 0.001)

d_no = cr_no_horizon.to_dict()
_test("to_dict horizon_value present even when 0", "horizon_value" in d_no)
_test(
    "to_dict no horizon_reason when empty",
    "horizon_reason" not in d_no,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. HORIZON_WEIGHT constant
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. HORIZON_WEIGHT Constant")

_test("HORIZON_WEIGHT is 0.25", HORIZON_WEIGHT == 0.25)
_test("HORIZON_FUTURE_BOOST is 0.08", HORIZON_FUTURE_BOOST == 0.08)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. effective_utility formula: expected + exploration + horizon
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Effective Utility — Three Components")

cr = CounterfactualResult(
    expected_utility=0.2,
    expected_delta=0.0,
    confidence=0.5,
    reasoning="test",
    horizon_value=0.8,
)

exploration = (1.0 - 0.5) * UNCERTAINTY_WEIGHT
horizon_contribution = HORIZON_WEIGHT * 0.8
expected = min(1.0, 0.2 + exploration + horizon_contribution)

_test(
    "three-component formula",
    abs(cr.effective_utility - expected) < 0.001,
    f"got={cr.effective_utility:.4f}, expected={expected:.4f}",
)

# Clamping: high values stay at 1.0
cr_high = CounterfactualResult(
    expected_utility=0.9,
    expected_delta=0.0,
    confidence=0.1,
    reasoning="test",
    horizon_value=0.9,
)
_test(
    "clamped to 1.0",
    cr_high.effective_utility == 1.0,
    f"got={cr_high.effective_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Core test: low immediate utility + strong future payoff → survives
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Low Immediate + Strong Future → Survives")

# Goal with low expected_utility but high horizon_value
future_goal = CounterfactualResult(
    expected_utility=0.2,
    expected_delta=0.0,
    confidence=0.7,
    reasoning="test",
    horizon_value=0.8,
)

# Goal with moderate expected_utility, no horizon value
immediate_goal = CounterfactualResult(
    expected_utility=0.35,
    expected_delta=0.0,
    confidence=0.7,
    reasoning="test",
    horizon_value=0.0,
)

_test(
    "future goal effective_utility > immediate goal",
    future_goal.effective_utility > immediate_goal.effective_utility,
    f"future={future_goal.effective_utility:.3f}, immediate={immediate_goal.effective_utility:.3f}",
)

# Confidence modulation: future goal survives better
mg_conf = 0.7
future_conf = mg_conf * future_goal.effective_utility
immediate_conf = mg_conf * immediate_goal.effective_utility
_test(
    "future goal confidence > immediate confidence",
    future_conf > immediate_conf,
    f"future_conf={future_conf:.3f}, immediate_conf={immediate_conf:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Purely bad goals still suppressed
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Purely Bad Goals Still Suppressed")

# High confidence, low utility, no horizon value
known_bad = CounterfactualResult(
    expected_utility=0.1,
    expected_delta=-0.05,
    confidence=0.95,
    reasoning="test",
    horizon_value=0.0,
)

mg_conf = 0.8
suppressed = mg_conf * known_bad.effective_utility
_test(
    "known bad: still deeply suppressed",
    suppressed < 0.15,
    f"suppressed_conf={suppressed:.3f}",
)
_test(
    "known bad: horizon contributes nothing",
    abs(
        known_bad.effective_utility
        - (known_bad.expected_utility + known_bad.exploration_boost)
    )
    < 0.001,
)

# Even with some horizon, known bad stays low if horizon is modest
modest_horizon = CounterfactualResult(
    expected_utility=0.1,
    expected_delta=-0.05,
    confidence=0.95,
    reasoning="test",
    horizon_value=0.2,
)
modest_conf = mg_conf * modest_horizon.effective_utility
_test(
    "modest horizon + bad utility: still below 0.2",
    modest_conf < 0.2,
    f"modest_conf={modest_conf:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Signal A: Enablement — parent spawns high-performing children
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Horizon Signal A: Enablement")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

# Add a parent goal
parent = GoalState(
    goal_id="parent",
    description="Parent",
    success_criteria={"domain": "parent"},
    priority=0.7,
)
reg.add_goal(parent)

# Add child goals that were spawned (meta_origin = specialization)
for i in range(3):
    child = GoalState(
        goal_id=f"child_{i}",
        description=f"Child {i}",
        success_criteria={"domain": "child", "_meta_origin": "specialization"},
        priority=0.5,
    )
    reg.add_goal(child)
    tracker = reg.get_tracker(f"child_{i}")
    tracker.success_score = 0.85
    tracker.uses = 5

mg = _make_meta_goal(
    goal_id="new_child",
    parent_goals=("parent",),
    criteria={"domain": "new_child"},
)

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "enablement signal contributes to horizon",
    result.horizon_value > 0.0,
    f"horizon={result.horizon_value:.3f}",
)
_test(
    "horizon_reason mentions enablement",
    "enablement" in result.horizon_reason,
    f"reason={result.horizon_reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Signal B: Transition probability
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Horizon Signal B: Transition")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

# Build traces where active goal has similar criteria and next turn is high quality
traces = []
for i in range(8):
    traces.append(
        _make_trace(
            turn_id=i,
            active_goal_id="similar_goal",
            quality_score=0.5,
            goal_pool_snapshot={
                "goals": {
                    "similar_goal": {
                        "success_criteria": {"domain": "test", "type": "build"},
                    }
                }
            },
        )
    )
    # Next turn has high quality (will be picked up as transition)
    traces.append(
        _make_trace(
            turn_id=i * 10 + 1,
            active_goal_id="other",
            quality_score=0.85,
            goal_pool_snapshot={"goals": {}},
        )
    )

mg = _make_meta_goal(
    goal_id="transition_test",
    criteria={"domain": "test", "type": "build"},
)

result = evaluator.evaluate_counterfactual(mg, reg, traces)
_test(
    "transition signal detected",
    result.horizon_value > 0.0,
    f"horizon={result.horizon_value:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Signal C: Delayed payoff
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Horizon Signal C: Delayed Payoff")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

# Parent with improving delta trend
delayed_parent = GoalState(
    goal_id="delayed_parent",
    description="Late bloomer",
    success_criteria={"domain": "dp"},
    priority=0.5,
)
reg.add_goal(delayed_parent)
tracker = reg.get_tracker("delayed_parent")
tracker.success_score = 0.4
tracker.uses = 8
# First half: poor. Second half: improving.
tracker.delta_history = [-0.05, -0.03, 0.01, 0.04, 0.08]

mg = _make_meta_goal(
    goal_id="delayed_child",
    parent_goals=("delayed_parent",),
    criteria={"domain": "delayed_child"},
)

result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "delayed payoff signal contributes",
    result.horizon_value > 0.0,
    f"horizon={result.horizon_value:.3f}",
)
_test(
    "horizon_reason mentions delayed_payoff",
    "delayed_payoff" in result.horizon_reason,
    f"reason={result.horizon_reason}",
)

# Parent with declining trend should NOT trigger delayed payoff
reg2 = GoalRegistry()
declining = GoalState(
    goal_id="declining_parent",
    description="Declining",
    success_criteria={"domain": "dec"},
    priority=0.5,
)
reg2.add_goal(declining)
t2 = reg2.get_tracker("declining_parent")
t2.success_score = 0.6
t2.uses = 8
t2.delta_history = [0.05, 0.03, -0.01, -0.04, -0.08]

mg2 = _make_meta_goal(
    goal_id="declining_child",
    parent_goals=("declining_parent",),
    criteria={"domain": "declining_child"},
)
result2 = evaluator.evaluate_counterfactual(mg2, reg2)
_test(
    "declining trend → no delayed payoff",
    "delayed_payoff" not in result2.horizon_reason,
    f"reason={result2.horizon_reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Signal D: Goal graph expansion
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Horizon Signal D: Graph Expansion")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

# Existing goals have {domain, type} criteria
existing = GoalState(
    goal_id="existing",
    description="Existing",
    success_criteria={"domain": "sales", "type": "close"},
    priority=0.6,
)
reg.add_goal(existing)

# New goal with novel criteria keys
mg_novel = _make_meta_goal(
    goal_id="novel_goal",
    criteria={"domain": "sales", "channel": "outbound", "market": "enterprise"},
)

result = evaluator.evaluate_counterfactual(mg_novel, reg)
_test(
    "novel criteria → expansion signal",
    result.horizon_value > 0.0,
    f"horizon={result.horizon_value:.3f}",
)
_test(
    "horizon_reason mentions expansion",
    "expansion" in result.horizon_reason,
    f"reason={result.horizon_reason}",
)

# Same criteria → no expansion signal
mg_same = _make_meta_goal(
    goal_id="same_goal",
    criteria={"domain": "eng", "type": "build"},
)
reg3 = GoalRegistry()
reg3.add_goal(
    GoalState(
        goal_id="exists",
        description="E",
        success_criteria={"domain": "eng", "type": "build"},
        priority=0.5,
    )
)
result3 = evaluator.evaluate_counterfactual(mg_same, reg3)
_test(
    "same criteria → no expansion signal",
    "expansion" not in result3.horizon_reason,
    f"reason={result3.horizon_reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. No horizon → horizon_value = 0.0
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. No Data → Zero Horizon")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

mg = _make_meta_goal(goal_id="no_data")
result = evaluator.evaluate_counterfactual(mg, reg)
_test(
    "no data → horizon_value = 0.0",
    result.horizon_value == 0.0,
    f"horizon={result.horizon_value}",
)
_test(
    "no data → empty horizon_reason",
    result.horizon_reason == "",
    f"reason={result.horizon_reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. ExplorationController responds to horizon_value
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. ExplorationController — Horizon Signal")

ctrl_high = ExplorationController()
state_high = ctrl_high.compute(horizon_value=0.7)
_test(
    "high horizon → above default",
    state_high.exploration_rate > DEFAULT_EXPLORATION,
    f"rate={state_high.exploration_rate:.4f}",
)
_test(
    "reason contains horizon_future",
    "horizon_future" in state_high.reason,
    f"reason={state_high.reason}",
)

ctrl_low = ExplorationController()
state_low = ctrl_low.compute(horizon_value=0.1)
_test(
    "low horizon → no boost",
    "horizon_future" not in state_low.reason,
    f"reason={state_low.reason}",
)

ctrl_none = ExplorationController()
state_none = ctrl_none.compute(horizon_value=None)
_test(
    "None horizon → no boost",
    "horizon_future" not in state_none.reason,
)

# Verify boost magnitude
ctrl_w = ExplorationController()
ctrl_wo = ExplorationController()
sw = ctrl_w.compute(horizon_value=0.7)
swo = ctrl_wo.compute()
_test(
    "boost matches HORIZON_FUTURE_BOOST",
    abs((sw.exploration_rate - swo.exploration_rate) - HORIZON_FUTURE_BOOST) < 0.001,
    f"diff={sw.exploration_rate - swo.exploration_rate:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. DecisionTrace captures horizon fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. DecisionTrace — Horizon Fields")

trace = build_trace(
    turn_id=50,
    counterfactual_horizon_value={"goal_a": 0.6, "goal_b": 0.0},
    counterfactual_horizon_reason={"goal_a": "enablement:0.60|transition:0.50"},
)
_test(
    "trace has horizon_value",
    trace.counterfactual_horizon_value == {"goal_a": 0.6, "goal_b": 0.0},
)
_test(
    "trace has horizon_reason",
    trace.counterfactual_horizon_reason is not None,
)

d = trace.to_dict()
_test("to_dict has horizon_value", "counterfactual_horizon_value" in d)
_test("to_dict has horizon_reason", "counterfactual_horizon_reason" in d)

# Empty trace
empty = build_trace(turn_id=51)
_test("empty: horizon_value None", empty.counterfactual_horizon_value is None)
_test("empty: horizon_reason None", empty.counterfactual_horizon_reason is None)
ed = empty.to_dict()
_test("empty to_dict: no horizon_value", "counterfactual_horizon_value" not in ed)
_test("empty to_dict: no horizon_reason", "counterfactual_horizon_reason" not in ed)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Determinism")

# CounterfactualResult
cr1 = CounterfactualResult(0.3, 0.0, 0.5, "test", 0.6, "h")
cr2 = CounterfactualResult(0.3, 0.0, 0.5, "test", 0.6, "h")
_test("deterministic effective_utility", cr1.effective_utility == cr2.effective_utility)
_test("deterministic horizon_value", cr1.horizon_value == cr2.horizon_value)

# ExplorationController
ctrl_a = ExplorationController()
ctrl_b = ExplorationController()
sa = ctrl_a.compute(horizon_value=0.6, counterfactual_uncertainty=0.4)
sb = ctrl_b.compute(horizon_value=0.6, counterfactual_uncertainty=0.4)
_test("deterministic rate with horizon", sa.exploration_rate == sb.exploration_rate)
_test("deterministic reason with horizon", sa.reason == sb.reason)

# Full evaluator
evaluator = CounterfactualEvaluator()
reg = GoalRegistry()
reg.add_goal(
    GoalState("p", "P", {"domain": "p", "_meta_origin": "specialization"}, 0.5)
)
reg.get_tracker("p").success_score = 0.8
reg.get_tracker("p").uses = 5
mg = _make_meta_goal("det_test", parent_goals=("p",))
r1 = evaluator.evaluate_counterfactual(mg, reg)
r2 = evaluator.evaluate_counterfactual(mg, reg)
_test("evaluator deterministic horizon", r1.horizon_value == r2.horizon_value)
_test("evaluator deterministic effective", r1.effective_utility == r2.effective_utility)

# 100x
vals = [
    CounterfactualResult(0.3, 0.0, 0.5, "t", 0.7, "r").effective_utility
    for _ in range(100)
]
_test("100x identical", len(set(vals)) == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. No regressions — backward compat
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. No Regressions")

# CounterfactualResult without horizon fields
cr_compat = CounterfactualResult(
    expected_utility=0.5,
    expected_delta=0.02,
    confidence=0.7,
    reasoning="compat",
)
_test("compat: horizon defaults 0.0", cr_compat.horizon_value == 0.0)
_test("compat: horizon_reason empty", cr_compat.horizon_reason == "")
_test(
    "compat: effective = expected + exploration (no horizon)",
    abs(cr_compat.effective_utility - min(1.0, 0.5 + (1.0 - 0.7) * UNCERTAINTY_WEIGHT))
    < 0.001,
)

# ExplorationController backward compat
ctrl = ExplorationController()
s = ctrl.compute(convergence_status="stable", goal_deltas=[0.05])
_test(
    "exploration compat: works without horizon",
    MIN_EXPLORATION <= s.exploration_rate <= MAX_EXPLORATION,
)

# build_trace backward compat
t = build_trace(
    turn_id=200,
    counterfactual_expected_utility={"g": 0.5},
)
_test("trace compat: horizon defaults None", t.counterfactual_horizon_value is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. No LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. No LLM Calls")

import umh.runtime_engine.counterfactual_eval as cf_mod

src = inspect.getsource(cf_mod)
_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no anthropic", "anthropic" not in src)
_test("no openai", "openai" not in src)
_test("no genai", "genai" not in src)
_test("no agent_runtime", "agent_runtime" not in src)
_test("no import random", "import random" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. ExecutionSpine Unchanged")

spine_src = open("/opt/OS/eos/execution_spine.py").read()
_test("spine: no horizon ref", "horizon_value" not in spine_src)
_test("spine: no HORIZON_WEIGHT ref", "HORIZON_WEIGHT" not in spine_src)
_test("spine: no counterfactual ref", "counterfactual" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Short-term vs long-term tradeoff exists
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Short-Term vs Long-Term Tradeoff")

# Short-term goal: high immediate, no horizon
short_term = CounterfactualResult(
    expected_utility=0.6,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
    horizon_value=0.0,
)

# Long-term goal: lower immediate, high horizon
long_term = CounterfactualResult(
    expected_utility=0.40,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
    horizon_value=0.9,
)

_test(
    "short-term has higher expected_utility",
    short_term.expected_utility > long_term.expected_utility,
)
_test(
    "long-term has higher horizon_value",
    long_term.horizon_value > short_term.horizon_value,
)

# The tradeoff: who wins on effective_utility depends on the magnitudes
_test(
    "tradeoff exists: long-term can beat short-term",
    long_term.effective_utility > short_term.effective_utility,
    f"long={long_term.effective_utility:.3f}, short={short_term.effective_utility:.3f}",
)

# But short-term still wins if horizon is small
small_horizon = CounterfactualResult(
    expected_utility=0.40,
    expected_delta=0.0,
    confidence=0.8,
    reasoning="test",
    horizon_value=0.3,
)
_test(
    "small horizon: short-term still wins",
    short_term.effective_utility > small_horizon.effective_utility,
    f"short={short_term.effective_utility:.3f}, small_h={small_horizon.effective_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. End-to-end pipeline
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. End-to-End Pipeline")

from umh.runtime_engine.goal_validator import GoalValidator
from umh.runtime_engine.goal_alignment import GoalAlignmentEvaluator
from umh.runtime_engine.adaptive_exploration import exploration_rate_to_budget_modifier
from umh.runtime_engine.execution_budget import derive_budget

evaluator = CounterfactualEvaluator()
validator = GoalValidator()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

# Setup: parent with improving trend
parent_g = GoalState(
    goal_id="e2e_parent",
    description="E2E parent",
    success_criteria={"domain": "e2e"},
    priority=0.6,
)
reg.add_goal(parent_g)
pt = reg.get_tracker("e2e_parent")
pt.success_score = 0.5
pt.uses = 6
pt.delta_history = [-0.03, -0.01, 0.02, 0.05, 0.08]

# Novel child goal
mg = _make_meta_goal(
    goal_id="e2e_child",
    parent_goals=("e2e_parent",),
    criteria={"domain": "e2e", "novel_key": "value"},
    description="E2E child",
    confidence=0.6,
)

# Step 1: Validate
vr = validator.validate(mg, reg)
_test("e2e: validator passes", vr.is_valid)

# Step 2: Counterfactual with horizon
cfr = evaluator.evaluate_counterfactual(mg, reg)
_test("e2e: horizon_value >= 0", cfr.horizon_value >= 0.0)
_test(
    "e2e: effective includes horizon",
    cfr.effective_utility >= cfr.expected_utility,
)

# Step 3: Confidence modulation
new_conf = max(0.05, mg.confidence * cfr.effective_utility)
_test(
    "e2e: confidence modulated",
    new_conf > 0.0,
    f"new_conf={new_conf:.3f}",
)

# Step 4: ExplorationController
ctrl = ExplorationController()
exp = ctrl.compute(horizon_value=cfr.horizon_value)
_test("e2e: exploration computed", exp.exploration_rate > 0)

# Step 5: Build trace
trace = build_trace(
    turn_id=999,
    counterfactual_expected_utility={"e2e_child": cfr.expected_utility},
    counterfactual_confidence={"e2e_child": cfr.confidence},
    counterfactual_horizon_value={"e2e_child": cfr.horizon_value},
    counterfactual_horizon_reason={"e2e_child": cfr.horizon_reason},
    exploration_rate=exp.exploration_rate,
)
td = trace.to_dict()
_test("e2e: trace has horizon", "counterfactual_horizon_value" in td)
_test("e2e: trace has exploration", "exploration_rate" in td)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Horizon value is bounded [0.0, 1.0]
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. Horizon Value Bounds")

evaluator = CounterfactualEvaluator()
reg = GoalRegistry()

# Many children with high scores
for i in range(10):
    c = GoalState(
        goal_id=f"hc_{i}",
        description=f"High child {i}",
        success_criteria={"_meta_origin": "specialization"},
        priority=0.5,
    )
    reg.add_goal(c)
    t = reg.get_tracker(f"hc_{i}")
    t.success_score = 0.95
    t.uses = 10

mg = _make_meta_goal("bound_test", parent_goals=("hc_0",))
result = evaluator.evaluate_counterfactual(mg, reg)
_test("horizon_value <= 1.0", result.horizon_value <= 1.0)
_test("horizon_value >= 0.0", result.horizon_value >= 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. No New Dependencies")

src = inspect.getsource(cf_mod)
_test("no requests", "import requests" not in src)
_test("no httpx", "import httpx" not in src)
_test("no numpy", "import numpy" not in src)
_test("no external API", "api.openai" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
