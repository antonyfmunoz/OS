"""
Influence Integration — test suite.

Validates that final_influence_score is properly integrated into:
    - Strategy ranking (additive via INFLUENCE_WEIGHT)
    - Goal arbitration (multiplicative via GOAL_INFLUENCE_SCALE)
    - Plan confidence (additive via PLAN_INFLUENCE_WEIGHT)
    - DecisionTrace observability (4 new fields)

Also validates:
    - Determinism
    - Boundedness
    - Backward compatibility (zero influence = no change)
    - No LLM calls, no randomness, no ExecutionSpine changes
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.influence_scoring import (
    compute_influence_adjustment,
    compute_plan_influence,
    INFLUENCE_WEIGHT,
    PLAN_INFLUENCE_WEIGHT,
)
from umh.runtime_engine.goal_arbitrator import (
    GoalArbitrator,
    GOAL_INFLUENCE_SCALE,
    W_PRIORITY,
    W_SCORE,
    W_DELTA,
    W_RECENCY,
)
from umh.strategy.memory import StrategyMemory
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

passed = 0
failed = 0


def check(condition: bool, label: str) -> None:
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {label}")


# ─── Section 1: Constants defined correctly ──────────────────────────
print("1. constants defined correctly")
check(INFLUENCE_WEIGHT == 0.15, "INFLUENCE_WEIGHT = 0.15")
check(PLAN_INFLUENCE_WEIGHT == 0.10, "PLAN_INFLUENCE_WEIGHT = 0.10")
check(GOAL_INFLUENCE_SCALE == 0.20, "GOAL_INFLUENCE_SCALE = 0.20")

# ─── Section 2: compute_influence_adjustment basic ───────────────────
print("2. compute_influence_adjustment basic")
adj_zero = compute_influence_adjustment(0.0)
check(adj_zero == 0.0, "zero influence → zero adjustment")

adj_half = compute_influence_adjustment(0.5)
check(abs(adj_half - 0.5 * INFLUENCE_WEIGHT) < 1e-9, "0.5 → 0.5 * 0.15 = 0.075")

adj_one = compute_influence_adjustment(1.0)
check(abs(adj_one - INFLUENCE_WEIGHT) < 1e-9, "1.0 → 0.15")

# ─── Section 3: compute_influence_adjustment clamped ─────────────────
print("3. compute_influence_adjustment clamped inputs")
adj_neg = compute_influence_adjustment(-0.5)
check(adj_neg == 0.0, "negative input clamped to 0")

adj_big = compute_influence_adjustment(5.0)
check(abs(adj_big - INFLUENCE_WEIGHT) < 1e-9, "input > 1 clamped to 1.0 * weight")

# ─── Section 4: compute_plan_influence basic ─────────────────────────
print("4. compute_plan_influence basic")
plan_zero = compute_plan_influence(0.0)
check(plan_zero == 0.0, "zero → zero")

plan_half = compute_plan_influence(0.5)
check(abs(plan_half - 0.5 * PLAN_INFLUENCE_WEIGHT) < 1e-9, "0.5 → 0.05")

plan_one = compute_plan_influence(1.0)
check(abs(plan_one - PLAN_INFLUENCE_WEIGHT) < 1e-9, "1.0 → 0.10")

# ─── Section 5: Strategy ranking with influence_adjustment ───────────
print("5. strategy ranking with influence_adjustment")
sm = StrategyMemory()
sm.record_win("alpha", 0.8)
sm.record_win("beta", 0.6)
sm.record_win("gamma", 0.4)

ranked_base = sm.rank_strategies()
base_names = [n for n, _ in ranked_base]
check(base_names[0] == "alpha", "alpha is top without influence")

# With influence adjustment — order shouldn't change (uniform additive)
ranked_adj = sm.rank_strategies(influence_adjustment=0.05)
adj_names = [n for n, _ in ranked_adj]
check(adj_names == base_names, "uniform adjustment preserves relative order")

# ─── Section 6: Conditioned scores include influence ─────────────────
print("6. conditioned scores include influence_adjustment")
base_scores, cond_scores = sm.get_conditioned_scores(influence_adjustment=0.1)
for name in base_scores:
    check(
        abs(cond_scores[name] - (base_scores[name] + 0.1)) < 0.001,
        f"{name} conditioned = base + 0.1",
    )

# ─── Section 7: Zero influence = no change ──────────────────────────
print("7. zero influence = no change")
base0, cond0 = sm.get_conditioned_scores(influence_adjustment=0.0)
check(base0 == cond0, "zero adjustment → base == conditioned")

# ─── Section 8: Backward compat — no influence_adjustment param ──────
print("8. backward compat — rank_strategies without influence param")
ranked_compat = sm.rank_strategies()
check(len(ranked_compat) == 3, "rank_strategies works without param")
ranked_compat2 = sm.rank_strategies(conditioning_bias={"alpha": 0.01})
check(len(ranked_compat2) == 3, "with only bias, no influence — still works")

# ─── Section 9: Goal arbitration with influence_score ────────────────
print("9. goal arbitration with influence_score")
# Need a mock registry
from types import SimpleNamespace

mock_goals = [
    SimpleNamespace(goal_id="g1", priority=0.8),
    SimpleNamespace(goal_id="g2", priority=0.6),
]
mock_tracker_1 = SimpleNamespace(
    success_score=0.5,
    latest_delta=0.1,
    recency_weight=0.5,
    persistence_streak=2,
    compute_recency=lambda t: None,
)
mock_tracker_2 = SimpleNamespace(
    success_score=0.4,
    latest_delta=0.0,
    recency_weight=0.3,
    persistence_streak=1,
    compute_recency=lambda t: None,
)

mock_registry = SimpleNamespace(
    turn=5,
    get_all_goals=lambda: mock_goals,
    get_all_trackers=lambda: {"g1": mock_tracker_1, "g2": mock_tracker_2},
)

arb = GoalArbitrator()

# Without influence
result_no_inf = arb.select_active_goal(mock_registry)
util_g1_no = result_no_inf.utilities["g1"]
util_g2_no = result_no_inf.utilities["g2"]

# With influence
result_with_inf = arb.select_active_goal(mock_registry, influence_score=0.8)
util_g1_with = result_with_inf.utilities["g1"]
util_g2_with = result_with_inf.utilities["g2"]

# Both should be scaled up
check(util_g1_with > util_g1_no, "g1 utility increases with influence")
check(util_g2_with > util_g2_no, "g2 utility increases with influence")

# Scaling is multiplicative: (1 + 0.8 * 0.20) = 1.16
expected_scale = 1.0 + 0.8 * GOAL_INFLUENCE_SCALE
check(
    abs(util_g1_with - util_g1_no * expected_scale) < 1e-9,
    f"g1 scaled by {expected_scale}",
)
check(
    abs(util_g2_with - util_g2_no * expected_scale) < 1e-9,
    f"g2 scaled by {expected_scale}",
)

# ─── Section 10: Goal arbitration preserves relative order ───────────
print("10. goal arbitration preserves relative order")
check(
    result_no_inf.selected_goal_id == result_with_inf.selected_goal_id,
    "same winner with uniform scaling",
)

# ─── Section 11: Zero influence = no scaling ────────────────────────
print("11. zero influence = no goal scaling")
result_zero_inf = arb.select_active_goal(mock_registry, influence_score=0.0)
check(
    result_zero_inf.utilities["g1"] == util_g1_no,
    "zero influence → no utility change",
)

# ─── Section 12: blend_goals passes influence through ────────────────
print("12. blend_goals passes influence_score through")
mock_registry_blend = SimpleNamespace(
    turn=5,
    get_all_goals=lambda: mock_goals,
    get_all_trackers=lambda: {"g1": mock_tracker_1, "g2": mock_tracker_2},
    active_goal_id=None,
    set_active_goal=lambda gid: None,
    get_active_goal=lambda: None,
)
# blend_goals calls select_active_goal internally — just verify it accepts param
try:
    blend_result = arb.blend_goals(mock_registry_blend, influence_score=0.5)
    check(True, "blend_goals accepts influence_score param")
except TypeError:
    check(False, "blend_goals should accept influence_score")

# ─── Section 13: Determinism ────────────────────────────────────────
print("13. determinism")
adj_a = compute_influence_adjustment(0.73)
adj_b = compute_influence_adjustment(0.73)
check(adj_a == adj_b, "same input → same adjustment")

result_a = arb.select_active_goal(mock_registry, influence_score=0.6)
result_b = arb.select_active_goal(mock_registry, influence_score=0.6)
check(
    result_a.utilities == result_b.utilities,
    "same influence → same utilities",
)

# ─── Section 14: Boundedness ────────────────────────────────────────
print("14. boundedness")
for score in [0.0, 0.1, 0.5, 0.9, 1.0]:
    adj = compute_influence_adjustment(score)
    check(0 <= adj <= INFLUENCE_WEIGHT, f"adjustment bounded at score={score}")
    plan = compute_plan_influence(score)
    check(
        0 <= plan <= PLAN_INFLUENCE_WEIGHT, f"plan influence bounded at score={score}"
    )

# ─── Section 15: DecisionTrace new fields ───────────────────────────
print("15. DecisionTrace integration fields")
dt = DecisionTrace(
    turn_id=1,
    strategies_considered=("s1",),
    strategy_scores={"s1": 0.5},
    selected_strategy="s1",
    quality_score=0.6,
    confidence=0.7,
    signals={},
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test",
    latency_ms=0,
    tokens_used=None,
    was_enhanced=False,
    influence_applied=True,
    influence_adjustment=0.075,
    influence_pre_score=0.6,
    influence_post_score=0.675,
)
check(dt.influence_applied is True, "influence_applied set")
check(dt.influence_adjustment == 0.075, "influence_adjustment set")
check(dt.influence_pre_score == 0.6, "influence_pre_score set")
check(dt.influence_post_score == 0.675, "influence_post_score set")

# ─── Section 16: DecisionTrace.to_dict() serializes ─────────────────
print("16. to_dict() serializes integration fields")
dd = dt.to_dict()
check("influence_applied" in dd, "influence_applied in dict")
check("influence_adjustment" in dd, "influence_adjustment in dict")
check("influence_pre_score" in dd, "influence_pre_score in dict")
check("influence_post_score" in dd, "influence_post_score in dict")
check(dd["influence_adjustment"] == 0.075, "value correct")

# ─── Section 17: DecisionTrace.to_dict() omits None ─────────────────
print("17. to_dict() omits None integration fields")
dt_none = DecisionTrace(
    turn_id=1,
    strategies_considered=(),
    strategy_scores={},
    selected_strategy="",
    quality_score=0.0,
    confidence=0.0,
    signals={},
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test",
    latency_ms=0,
    tokens_used=None,
    was_enhanced=False,
)
dd_none = dt_none.to_dict()
check("influence_applied" not in dd_none, "omitted when None")
check("influence_adjustment" not in dd_none, "omitted when None")
check("influence_pre_score" not in dd_none, "omitted when None")
check("influence_post_score" not in dd_none, "omitted when None")

# ─── Section 18: build_trace() accepts integration params ───────────
print("18. build_trace() accepts integration params")
bt = build_trace(
    turn_id=5,
    influence_applied=True,
    influence_adjustment=0.1,
    influence_pre_score=0.5,
    influence_post_score=0.6,
)
check(bt.influence_applied is True, "build_trace passes influence_applied")
check(bt.influence_adjustment == 0.1, "build_trace passes influence_adjustment")
check(bt.influence_pre_score == 0.5, "build_trace passes influence_pre_score")
check(bt.influence_post_score == 0.6, "build_trace passes influence_post_score")

# ─── Section 19: Negative influence_score not applied to goals ───────
print("19. negative influence_score not applied to goals")
result_neg = arb.select_active_goal(mock_registry, influence_score=-0.5)
check(
    result_neg.utilities["g1"] == util_g1_no,
    "negative influence → no scaling (guard)",
)

# ─── Section 20: Single goal fast path unaffected ────────────────────
print("20. single goal fast path unaffected")
mock_single = SimpleNamespace(
    turn=5,
    get_all_goals=lambda: [SimpleNamespace(goal_id="only", priority=0.9)],
    get_all_trackers=lambda: {},
)
result_single = arb.select_active_goal(mock_single, influence_score=0.8)
check(result_single.selected_goal_id == "only", "single goal selected")
check(result_single.reason == "single_goal", "single_goal reason preserved")

# ─── Section 21: No LLM calls ──────────────────────────────────────
print("21. no LLM calls")
import inspect

inf_src = inspect.getsource(sys.modules["umh.runtime_engine.influence_scoring"])
check("call_with_fallback" not in inf_src, "no LLM in influence_scoring")

arb_src = inspect.getsource(sys.modules["umh.runtime_engine.goal_arbitrator"])
check("call_with_fallback" not in arb_src, "no LLM in goal_arbitrator")

sm_src = inspect.getsource(sys.modules["umh.runtime_engine.strategy_memory"])
check("call_with_fallback" not in sm_src, "no LLM in strategy_memory")

# ─── Section 22: No randomness ─────────────────────────────────────
print("22. no randomness")
for src, name in [
    (inf_src, "influence"),
    (arb_src, "arbitrator"),
    (sm_src, "strategy"),
]:
    check("random.random" not in src, f"no random.random in {name}")
    check("random.choice" not in src, f"no random.choice in {name}")

# ─── Section 23: ExecutionSpine untouched ───────────────────────────
print("23. ExecutionSpine not modified")
import importlib

es = importlib.import_module("umh.runtime_engine.execution_spine")
spine_src = inspect.getsource(es)
check("influence_adjustment" not in spine_src, "no influence_adjustment in spine")
check("INFLUENCE_WEIGHT" not in spine_src, "no INFLUENCE_WEIGHT in spine")

# ─── Section 24: Influence adjustment is additive in strategy ───────
print("24. influence adjustment is purely additive in strategy")
sm2 = StrategyMemory()
sm2.record_win("x", 0.7)
sm2.record_win("y", 0.3)

base_s, cond_s = sm2.get_conditioned_scores(influence_adjustment=0.05)
for name in base_s:
    diff = abs(cond_s[name] - base_s[name] - 0.05)
    check(diff < 0.001, f"{name}: conditioned - base = 0.05 (additive)")

# ─── Section 25: Goal scaling is multiplicative ─────────────────────
print("25. goal scaling is multiplicative")
util_no = util_g1_no
scale = 1.0 + 0.8 * GOAL_INFLUENCE_SCALE
util_yes = util_g1_with
check(
    abs(util_yes / util_no - scale) < 1e-6,
    f"ratio = {scale} (multiplicative confirmed)",
)

# ─── Section 26: Plan influence bounded ─────────────────────────────
print("26. plan influence stays bounded")
conf = 0.95
plan_adj = compute_plan_influence(1.0)
new_conf = min(1.0, conf + plan_adj)
check(new_conf <= 1.0, "plan confidence stays ≤ 1.0")

conf_low = 0.3
new_conf_low = min(1.0, conf_low + plan_adj)
check(new_conf_low > conf_low, "plan confidence increased")
check(new_conf_low <= 1.0, "still bounded")

# ─── Section 27: Influence monotonicity ─────────────────────────────
print("27. influence monotonicity")
scores = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
adjustments = [compute_influence_adjustment(s) for s in scores]
for i in range(len(adjustments) - 1):
    check(
        adjustments[i + 1] >= adjustments[i],
        f"adjustment monotonic at {scores[i + 1]}",
    )

plan_adjustments = [compute_plan_influence(s) for s in scores]
for i in range(len(plan_adjustments) - 1):
    check(
        plan_adjustments[i + 1] >= plan_adjustments[i],
        f"plan influence monotonic at {scores[i + 1]}",
    )

# ─── Final report ────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Influence Integration: {passed}/{passed + failed} passed")
if failed:
    print(f"  {failed} FAILED")
    raise SystemExit(1)
else:
    print("  ALL PASSED")
