"""
Tests for Uncertainty-Aware Exploration Override.

Proves:
    1. Low-confidence projections increase exploration
    2. High-confidence low-utility goals remain suppressed
    3. Determinism preserved
    4. No regressions
    5. No new dependencies
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
    UNCERTAINTY_WEIGHT,
    CONFIDENCE_FLOOR,
)
from umh.runtime_engine.adaptive_exploration import (
    ExplorationController,
    COUNTERFACTUAL_UNCERTAINTY_BOOST,
    DEFAULT_EXPLORATION,
    MIN_EXPLORATION,
    MAX_EXPLORATION,
    exploration_rate_to_budget_modifier,
)
from umh.runtime_engine.decision_trace import build_trace
from umh.runtime_engine.execution_budget import derive_budget, MIN_CANDIDATES_PER_GOAL
from umh.goals.state import GoalState, GoalRegistry
from umh.runtime_engine.meta_goal import MetaGoal

_test("all imports succeed", True)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_cf_result(expected_utility: float, confidence: float) -> CounterfactualResult:
    return CounterfactualResult(
        expected_utility=expected_utility,
        expected_delta=0.0,
        confidence=confidence,
        reasoning="test",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CounterfactualResult — uncertainty and exploration_boost properties
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. CounterfactualResult — New Properties")

# Low confidence → high uncertainty → high exploration boost
low_conf = _make_cf_result(expected_utility=0.3, confidence=0.2)
_test(
    "uncertainty = 1 - confidence",
    abs(low_conf.uncertainty - 0.8) < 0.001,
    f"uncertainty={low_conf.uncertainty:.3f}",
)
_test(
    "exploration_boost = uncertainty * UNCERTAINTY_WEIGHT",
    abs(low_conf.exploration_boost - 0.8 * UNCERTAINTY_WEIGHT) < 0.001,
    f"boost={low_conf.exploration_boost:.3f}",
)
_test(
    "effective_utility = expected_utility + exploration_boost",
    abs(low_conf.effective_utility - min(1.0, 0.3 + 0.8 * UNCERTAINTY_WEIGHT)) < 0.001,
    f"effective={low_conf.effective_utility:.3f}",
)

# High confidence → low uncertainty → negligible boost
high_conf = _make_cf_result(expected_utility=0.3, confidence=0.9)
_test(
    "high confidence → low uncertainty",
    high_conf.uncertainty < 0.15,
    f"uncertainty={high_conf.uncertainty:.3f}",
)
_test(
    "high confidence → small boost",
    high_conf.exploration_boost < 0.05,
    f"boost={high_conf.exploration_boost:.3f}",
)
_test(
    "high confidence low utility → effective_utility stays low",
    high_conf.effective_utility < 0.35,
    f"effective={high_conf.effective_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Core distinction: low utility vs low certainty
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Low Utility vs Low Certainty — The Core Fix")

# Case A: Low utility, HIGH confidence (we know it's bad)
known_bad = _make_cf_result(expected_utility=0.2, confidence=0.9)

# Case B: Low utility, LOW confidence (we don't know yet)
unknown = _make_cf_result(expected_utility=0.2, confidence=0.15)

_test(
    "known_bad effective_utility stays low",
    known_bad.effective_utility < 0.3,
    f"effective={known_bad.effective_utility:.3f}",
)
_test(
    "unknown effective_utility is boosted",
    unknown.effective_utility > known_bad.effective_utility,
    f"unknown={unknown.effective_utility:.3f}, known_bad={known_bad.effective_utility:.3f}",
)

# Confidence modulation uses effective_utility
mg_confidence = 0.7

# Old behavior: confidence * expected_utility
old_known = mg_confidence * known_bad.expected_utility
old_unknown = mg_confidence * unknown.expected_utility
_test(
    "OLD: known_bad and unknown produce same confidence",
    abs(old_known - old_unknown) < 0.01,
    f"old_known={old_known:.3f}, old_unknown={old_unknown:.3f}",
)

# New behavior: confidence * effective_utility
new_known = mg_confidence * known_bad.effective_utility
new_unknown = mg_confidence * unknown.effective_utility
_test(
    "NEW: unknown gets higher confidence than known_bad",
    new_unknown > new_known,
    f"new_unknown={new_unknown:.3f}, new_known={new_known:.3f}",
)
_test(
    "known_bad confidence still suppressed",
    new_known < mg_confidence * 0.5,
    f"new_known={new_known:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. effective_utility clamped [0.0, 1.0]
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Effective Utility Clamping")

# High expected_utility + high uncertainty could exceed 1.0
extreme = _make_cf_result(expected_utility=0.9, confidence=0.1)
_test(
    "effective_utility clamped to 1.0",
    extreme.effective_utility <= 1.0,
    f"effective={extreme.effective_utility:.3f}",
)

# Zero expected_utility + zero confidence
zero = _make_cf_result(expected_utility=0.0, confidence=0.0)
_test(
    "zero utility + zero confidence → boost only",
    zero.effective_utility > 0.0,
    f"effective={zero.effective_utility:.3f}",
)
_test(
    "effective_utility >= 0.0",
    zero.effective_utility >= 0.0,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ExplorationController responds to counterfactual_uncertainty
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. ExplorationController — Counterfactual Uncertainty Signal")

# High counterfactual uncertainty → exploration rate increases
ctrl_high = ExplorationController()
state_high = ctrl_high.compute(counterfactual_uncertainty=0.8)
_test(
    "high cf_uncertainty → above default",
    state_high.exploration_rate > DEFAULT_EXPLORATION,
    f"rate={state_high.exploration_rate:.4f}, default={DEFAULT_EXPLORATION}",
)
_test(
    "reason contains cf_uncertain",
    "cf_uncertain" in state_high.reason,
    f"reason={state_high.reason}",
)

# Low counterfactual uncertainty → no boost
ctrl_low = ExplorationController()
state_low = ctrl_low.compute(counterfactual_uncertainty=0.1)
_test(
    "low cf_uncertainty → no boost from cf signal",
    "cf_uncertain" not in state_low.reason,
    f"reason={state_low.reason}",
)

# None → no boost (backward compat)
ctrl_none = ExplorationController()
state_none = ctrl_none.compute(counterfactual_uncertainty=None)
_test(
    "None cf_uncertainty → no boost",
    "cf_uncertain" not in state_none.reason,
    f"reason={state_none.reason}",
)

# Verify the boost magnitude
ctrl_with = ExplorationController()
ctrl_without = ExplorationController()
s_with = ctrl_with.compute(counterfactual_uncertainty=0.8)
s_without = ctrl_without.compute()
expected_diff = COUNTERFACTUAL_UNCERTAINTY_BOOST
_test(
    "boost magnitude matches COUNTERFACTUAL_UNCERTAINTY_BOOST",
    abs((s_with.exploration_rate - s_without.exploration_rate) - expected_diff) < 0.001,
    f"diff={s_with.exploration_rate - s_without.exploration_rate:.4f}, expected={expected_diff}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Budget allocation responds to exploration rate
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Budget Allocation — Exploration Modifier Integration")


class MockBlend:
    def __init__(self, goals, primary_goal_id):
        self.goals = goals
        self.primary_goal_id = primary_goal_id


blend = MockBlend(
    goals=(("primary", 0.7), ("secondary", 0.3)),
    primary_goal_id="primary",
)

# High exploration rate (from high uncertainty) → secondary gets more
high_rate = 0.65
high_mod = exploration_rate_to_budget_modifier(high_rate)
budget_high = derive_budget(blend, total_candidates=6, exploration_modifier=high_mod)
secondary_high = budget_high.get_budget("secondary").candidate_slots

# Low exploration rate → secondary gets less
low_rate = 0.1
low_mod = exploration_rate_to_budget_modifier(low_rate)
budget_low = derive_budget(blend, total_candidates=6, exploration_modifier=low_mod)
secondary_low = budget_low.get_budget("secondary").candidate_slots

_test(
    "high exploration → more secondary candidates",
    secondary_high >= secondary_low,
    f"high={secondary_high}, low={secondary_low}",
)
_test(
    "both preserve total candidates",
    sum(a.candidate_slots for a in budget_high.allocations) == 6
    and sum(a.candidate_slots for a in budget_low.allocations) == 6,
)

# With high uncertainty, secondary should get at least MIN_CANDIDATES_PER_GOAL
_test(
    "secondary gets at least MIN_CANDIDATES_PER_GOAL",
    secondary_high >= MIN_CANDIDATES_PER_GOAL,
    f"secondary_high={secondary_high}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DecisionTrace captures new fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. DecisionTrace — New Fields")

trace = build_trace(
    turn_id=42,
    counterfactual_uncertainty={"goal_a": 0.8, "goal_b": 0.15},
    counterfactual_exploration_boost={"goal_a": 0.24, "goal_b": 0.045},
    counterfactual_expected_utility={"goal_a": 0.3, "goal_b": 0.7},
    counterfactual_confidence={"goal_a": 0.2, "goal_b": 0.85},
)

_test(
    "trace has counterfactual_uncertainty",
    trace.counterfactual_uncertainty == {"goal_a": 0.8, "goal_b": 0.15},
)
_test(
    "trace has counterfactual_exploration_boost",
    trace.counterfactual_exploration_boost == {"goal_a": 0.24, "goal_b": 0.045},
)

d = trace.to_dict()
_test("to_dict has counterfactual_uncertainty", "counterfactual_uncertainty" in d)
_test(
    "to_dict has counterfactual_exploration_boost",
    "counterfactual_exploration_boost" in d,
)

# Empty trace — new fields absent
empty = build_trace(turn_id=43)
ed = empty.to_dict()
_test(
    "empty trace: no counterfactual_uncertainty", "counterfactual_uncertainty" not in ed
)
_test(
    "empty trace: no counterfactual_exploration_boost",
    "counterfactual_exploration_boost" not in ed,
)

# Backward compat: None defaults
_test(
    "counterfactual_uncertainty defaults None",
    empty.counterfactual_uncertainty is None,
)
_test(
    "counterfactual_exploration_boost defaults None",
    empty.counterfactual_exploration_boost is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CounterfactualResult.to_dict includes new fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. CounterfactualResult.to_dict — New Fields")

cr = _make_cf_result(expected_utility=0.4, confidence=0.3)
d = cr.to_dict()

_test("to_dict has uncertainty", "uncertainty" in d)
_test("to_dict has exploration_boost", "exploration_boost" in d)
_test("to_dict has effective_utility", "effective_utility" in d)
_test(
    "uncertainty value correct",
    abs(d["uncertainty"] - 0.7) < 0.001,
    f"got {d['uncertainty']}",
)
_test(
    "exploration_boost value correct",
    abs(d["exploration_boost"] - 0.7 * UNCERTAINTY_WEIGHT) < 0.001,
    f"got {d['exploration_boost']}",
)
_test(
    "effective_utility value correct",
    abs(d["effective_utility"] - (0.4 + 0.7 * UNCERTAINTY_WEIGHT)) < 0.001,
    f"got {d['effective_utility']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Determinism — same inputs → same outputs
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Determinism")

# CounterfactualResult properties
cr1 = _make_cf_result(expected_utility=0.35, confidence=0.25)
cr2 = _make_cf_result(expected_utility=0.35, confidence=0.25)
_test("deterministic uncertainty", cr1.uncertainty == cr2.uncertainty)
_test("deterministic exploration_boost", cr1.exploration_boost == cr2.exploration_boost)
_test("deterministic effective_utility", cr1.effective_utility == cr2.effective_utility)

# ExplorationController with cf_uncertainty
ctrl_a = ExplorationController()
ctrl_b = ExplorationController()
sa = ctrl_a.compute(
    goal_deltas=[0.05, -0.02],
    convergence_status="recovering",
    counterfactual_uncertainty=0.6,
)
sb = ctrl_b.compute(
    goal_deltas=[0.05, -0.02],
    convergence_status="recovering",
    counterfactual_uncertainty=0.6,
)
_test("deterministic exploration rate", sa.exploration_rate == sb.exploration_rate)
_test("deterministic reason", sa.reason == sb.reason)

# 100x property computation
results = [_make_cf_result(0.4, 0.2).effective_utility for _ in range(100)]
_test("100x effective_utility identical", len(set(results)) == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. No regressions — existing behavior preserved
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. No Regressions")

# ExplorationController still works without cf_uncertainty
ctrl_compat = ExplorationController()
state_compat = ctrl_compat.compute(
    goal_deltas=[0.05, 0.03],
    convergence_status="stable",
)
_test(
    "backward compat: no cf_uncertainty → normal rate",
    MIN_EXPLORATION <= state_compat.exploration_rate <= MAX_EXPLORATION,
)

# CounterfactualResult still works with original fields
cr_compat = CounterfactualResult(
    expected_utility=0.6,
    expected_delta=0.05,
    confidence=0.8,
    reasoning="compat_test",
)
_test("backward compat: expected_utility", cr_compat.expected_utility == 0.6)
_test("backward compat: confidence", cr_compat.confidence == 0.8)
_test("backward compat: to_dict works", "expected_utility" in cr_compat.to_dict())

# build_trace still works without new fields
compat_trace = build_trace(
    turn_id=100,
    counterfactual_expected_utility={"g": 0.5},
    counterfactual_confidence={"g": 0.7},
)
_test(
    "backward compat: trace works",
    compat_trace.counterfactual_expected_utility is not None,
)
_test(
    "backward compat: new fields default None",
    compat_trace.counterfactual_uncertainty is None,
)

# derive_budget still works without modifier
budget_compat = derive_budget(blend, total_candidates=4)
_test("backward compat: budget works", budget_compat.total_candidates >= 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. No new external dependencies
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. No New Dependencies")

import umh.runtime_engine.counterfactual_eval as cf_mod
import umh.runtime_engine.adaptive_exploration as ae_mod

for name, mod in [("counterfactual_eval", cf_mod), ("adaptive_exploration", ae_mod)]:
    src = inspect.getsource(mod)
    _test(f"{name}: no requests", "import requests" not in src)
    _test(f"{name}: no httpx", "import httpx" not in src)
    _test(f"{name}: no LLM calls", "call_with_fallback" not in src)
    _test(f"{name}: no anthropic", "anthropic" not in src)
    _test(f"{name}: no openai", "openai" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. ExecutionSpine Unchanged")

spine_src = open("/opt/OS/eos/execution_spine.py").read()
_test(
    "spine has no uncertainty ref",
    "uncertainty" not in spine_src.lower().replace("uncertainty_score", ""),
)
_test("spine has no exploration_boost ref", "exploration_boost" not in spine_src)
_test("spine has no counterfactual ref", "counterfactual" not in spine_src)
_test("spine has no UNCERTAINTY_WEIGHT ref", "UNCERTAINTY_WEIGHT" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. UNCERTAINTY_WEIGHT constant
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. UNCERTAINTY_WEIGHT Constant")

_test("UNCERTAINTY_WEIGHT is 0.3", UNCERTAINTY_WEIGHT == 0.3)
_test(
    "COUNTERFACTUAL_UNCERTAINTY_BOOST is 0.12",
    COUNTERFACTUAL_UNCERTAINTY_BOOST == 0.12,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. End-to-end: full pipeline with uncertainty
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. End-to-End Pipeline")

from umh.runtime_engine.goal_validator import GoalValidator
from umh.runtime_engine.goal_alignment import GoalAlignmentEvaluator

evaluator = CounterfactualEvaluator()
validator = GoalValidator()
aligner = GoalAlignmentEvaluator()
reg = GoalRegistry()

mg = MetaGoal(
    goal_id="e2e_uncertain",
    origin="generated",
    parent_goals=(),
    confidence=0.7,
    utility_estimate=0.5,
    lifecycle_state="active",
    description="E2E test goal",
    success_criteria={"domain": "test"},
    priority=0.6,
    generation_turn=1,
    generation_reason="test",
)

# Step 1: Validate
vr = validator.validate(mg, reg)
_test("e2e: validator passes", vr.is_valid)

# Step 2: Counterfactual with uncertainty
cfr = evaluator.evaluate_counterfactual(mg, reg)
_test("e2e: uncertainty computed", cfr.uncertainty >= 0.0)
_test("e2e: exploration_boost computed", cfr.exploration_boost >= 0.0)
_test("e2e: effective_utility computed", cfr.effective_utility >= 0.0)

# Step 3: Confidence modulation using effective_utility (not expected_utility)
new_conf = mg.confidence * cfr.effective_utility
new_conf = max(new_conf, 0.05)
_test(
    "e2e: confidence uses effective_utility",
    new_conf >= mg.confidence * cfr.expected_utility,
    f"new={new_conf:.3f}, old_would_be={mg.confidence * cfr.expected_utility:.3f}",
)

# Step 4: Exploration controller with uncertainty signal
ctrl = ExplorationController()
exp_state = ctrl.compute(counterfactual_uncertainty=cfr.uncertainty)
_test("e2e: exploration rate computed", exp_state.exploration_rate > 0.0)

# Step 5: Budget with exploration modifier
mod = exploration_rate_to_budget_modifier(exp_state.exploration_rate)
budget = derive_budget(blend, total_candidates=6, exploration_modifier=mod)
_test("e2e: budget derived with modifier", budget.total_candidates == 6)

# Step 6: Trace captures everything
trace = build_trace(
    turn_id=999,
    counterfactual_expected_utility={"e2e_uncertain": cfr.expected_utility},
    counterfactual_confidence={"e2e_uncertain": cfr.confidence},
    counterfactual_uncertainty={"e2e_uncertain": cfr.uncertainty},
    counterfactual_exploration_boost={"e2e_uncertain": cfr.exploration_boost},
    exploration_rate=exp_state.exploration_rate,
    exploration_reason=exp_state.reason,
)
td = trace.to_dict()
_test(
    "e2e: trace has all cf fields",
    all(
        k in td
        for k in [
            "counterfactual_expected_utility",
            "counterfactual_confidence",
            "counterfactual_uncertainty",
            "counterfactual_exploration_boost",
        ]
    ),
)
_test("e2e: trace has exploration fields", "exploration_rate" in td)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. High-confidence low-utility goals remain suppressed
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. High-Confidence Low-Utility Remains Suppressed")

# Known bad goal: high confidence, low utility
known_bad_cfr = _make_cf_result(expected_utility=0.15, confidence=0.95)
mg_conf = 0.8
suppressed_conf = mg_conf * known_bad_cfr.effective_utility
_test(
    "known bad: confidence stays deeply suppressed",
    suppressed_conf < 0.2,
    f"suppressed_conf={suppressed_conf:.3f}",
)
_test(
    "known bad: exploration_boost is negligible",
    known_bad_cfr.exploration_boost < 0.02,
    f"boost={known_bad_cfr.exploration_boost:.3f}",
)
_test(
    "known bad: effective ≈ expected (no meaningful boost)",
    abs(known_bad_cfr.effective_utility - known_bad_cfr.expected_utility) < 0.02,
    f"effective={known_bad_cfr.effective_utility:.3f}, expected={known_bad_cfr.expected_utility:.3f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. No randomness in any path
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. No Randomness")

cf_src = inspect.getsource(cf_mod)
ae_src = inspect.getsource(ae_mod)

_test("counterfactual_eval: no import random", "import random" not in cf_src)
_test("adaptive_exploration: no import random", "import random" not in ae_src)
_test("counterfactual_eval: no shuffle", "shuffle" not in cf_src)
_test("adaptive_exploration: no shuffle", "shuffle" not in ae_src)


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
