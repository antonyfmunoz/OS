"""
Influence Scoring — test suite.

Validates:
    - Deterministic output
    - Identical inputs → identical results
    - Each component affects output
    - Removing a component changes score correctly
    - Weights applied correctly
    - Final score bounded [0, 1]
    - Decision trace logs all components
    - Input clamping
    - build_influence_snapshot normalization
    - No regressions in existing behavior
    - No LLM calls, no randomness, no ExecutionSpine changes
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.influence_scoring import (
    InfluenceComponent,
    InfluenceSnapshot,
    InfluenceResult,
    compute_influence_score,
    build_influence_snapshot,
    W_GOAL,
    W_PLAN,
    W_STRATEGY,
    W_STATE,
    W_CREDIT,
    W_EXPLORATION,
    W_COMMITMENT,
    NO_INFLUENCE_RESULT,
)
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


# ─── Section 1: Weights sum to 1.0 ──────────────────────────────────
print("1. weights sum to 1.0")
weight_sum = (
    W_GOAL + W_PLAN + W_STRATEGY + W_STATE + W_CREDIT + W_EXPLORATION + W_COMMITMENT
)
check(abs(weight_sum - 1.0) < 1e-9, f"weight sum = {weight_sum}")

# ─── Section 2: Individual weight values ─────────────────────────────
print("2. individual weight values")
check(W_GOAL == 0.30, "W_GOAL = 0.30")
check(W_PLAN == 0.20, "W_PLAN = 0.20")
check(W_STRATEGY == 0.15, "W_STRATEGY = 0.15")
check(W_STATE == 0.10, "W_STATE = 0.10")
check(W_CREDIT == 0.10, "W_CREDIT = 0.10")
check(W_EXPLORATION == 0.10, "W_EXPLORATION = 0.10")
check(W_COMMITMENT == 0.05, "W_COMMITMENT = 0.05")

# ─── Section 3: All-zero snapshot → zero score ──────────────────────
print("3. all-zero snapshot → zero score")
snap_zero = InfluenceSnapshot()
result_zero = compute_influence_score(snap_zero)
check(result_zero.final_score == 0.0, "zero inputs → zero score")
check(len(result_zero.components) == 7, "always 7 components")

# ─── Section 4: All-one snapshot → 1.0 score ────────────────────────
print("4. all-one snapshot → 1.0 score")
snap_one = InfluenceSnapshot(
    goal_score=1.0,
    plan_score=1.0,
    strategy_score=1.0,
    state_bias=1.0,
    credit_signal=1.0,
    exploration_signal=1.0,
    commitment_signal=1.0,
)
result_one = compute_influence_score(snap_one)
check(abs(result_one.final_score - 1.0) < 1e-9, "all 1.0 → score = 1.0")

# ─── Section 5: Determinism — same inputs → same outputs ────────────
print("5. determinism")
snap_a = InfluenceSnapshot(goal_score=0.7, plan_score=0.5, strategy_score=0.6)
snap_b = InfluenceSnapshot(goal_score=0.7, plan_score=0.5, strategy_score=0.6)
result_a = compute_influence_score(snap_a)
result_b = compute_influence_score(snap_b)
check(
    result_a.final_score == result_b.final_score, "identical inputs → identical score"
)
for ca, cb in zip(result_a.components, result_b.components):
    check(ca.contribution == cb.contribution, f"{ca.name} contribution identical")

# ─── Section 6: Each component affects output ───────────────────────
print("6. each component affects output")
base = InfluenceSnapshot(
    goal_score=0.5,
    plan_score=0.5,
    strategy_score=0.5,
    state_bias=0.5,
    credit_signal=0.5,
    exploration_signal=0.5,
    commitment_signal=0.5,
)
base_score = compute_influence_score(base).final_score

# Increase each component individually
for field_name in [
    "goal_score",
    "plan_score",
    "strategy_score",
    "state_bias",
    "credit_signal",
    "exploration_signal",
    "commitment_signal",
]:
    kwargs = {
        "goal_score": 0.5,
        "plan_score": 0.5,
        "strategy_score": 0.5,
        "state_bias": 0.5,
        "credit_signal": 0.5,
        "exploration_signal": 0.5,
        "commitment_signal": 0.5,
    }
    kwargs[field_name] = 0.9
    snap_mod = InfluenceSnapshot(**kwargs)
    mod_score = compute_influence_score(snap_mod).final_score
    check(mod_score > base_score, f"increasing {field_name} raises score")

# ─── Section 7: Removing a component reduces score ──────────────────
print("7. zeroing a component reduces score")
for field_name in [
    "goal_score",
    "plan_score",
    "strategy_score",
    "state_bias",
    "credit_signal",
    "exploration_signal",
    "commitment_signal",
]:
    kwargs = {
        "goal_score": 0.5,
        "plan_score": 0.5,
        "strategy_score": 0.5,
        "state_bias": 0.5,
        "credit_signal": 0.5,
        "exploration_signal": 0.5,
        "commitment_signal": 0.5,
    }
    kwargs[field_name] = 0.0
    snap_rem = InfluenceSnapshot(**kwargs)
    rem_score = compute_influence_score(snap_rem).final_score
    check(rem_score < base_score, f"zeroing {field_name} reduces score")

# ─── Section 8: Weights applied correctly ────────────────────────────
print("8. weights applied correctly")
snap_w = InfluenceSnapshot(
    goal_score=0.8,
    plan_score=0.6,
    strategy_score=0.7,
    state_bias=0.3,
    credit_signal=0.5,
    exploration_signal=0.4,
    commitment_signal=0.9,
)
result_w = compute_influence_score(snap_w)
expected = (
    0.8 * W_GOAL
    + 0.6 * W_PLAN
    + 0.7 * W_STRATEGY
    + 0.3 * W_STATE
    + 0.5 * W_CREDIT
    + 0.4 * W_EXPLORATION
    + 0.9 * W_COMMITMENT
)
check(
    abs(result_w.final_score - expected) < 1e-9,
    f"manual calculation matches: {result_w.final_score}",
)

# Verify each component's contribution
for comp in result_w.components:
    if comp.name == "goal":
        check(abs(comp.contribution - 0.8 * W_GOAL) < 1e-9, "goal contribution")
    elif comp.name == "plan":
        check(abs(comp.contribution - 0.6 * W_PLAN) < 1e-9, "plan contribution")
    elif comp.name == "strategy":
        check(abs(comp.contribution - 0.7 * W_STRATEGY) < 1e-9, "strategy contribution")

# ─── Section 9: Final score bounded [0, 1] ──────────────────────────
print("9. final score bounded")
# Even with extreme inputs, should be clamped
snap_extreme = InfluenceSnapshot(
    goal_score=5.0,
    plan_score=5.0,
    strategy_score=5.0,
    state_bias=5.0,
    credit_signal=5.0,
    exploration_signal=5.0,
    commitment_signal=5.0,
)
result_extreme = compute_influence_score(snap_extreme)
check(result_extreme.final_score <= 1.0, "extreme inputs → clamped to 1.0")
check(result_extreme.final_score >= 0.0, "score >= 0.0")

snap_neg = InfluenceSnapshot(
    goal_score=-1.0,
    plan_score=-1.0,
    strategy_score=-1.0,
    state_bias=-1.0,
    credit_signal=-1.0,
    exploration_signal=-1.0,
    commitment_signal=-1.0,
)
result_neg = compute_influence_score(snap_neg)
check(result_neg.final_score >= 0.0, "negative inputs → clamped to 0.0")
check(result_neg.final_score <= 1.0, "score <= 1.0")

# ─── Section 10: Input clamping ─────────────────────────────────────
print("10. input clamping per component")
snap_clamp = InfluenceSnapshot(goal_score=2.0, plan_score=-0.5)
result_clamp = compute_influence_score(snap_clamp)
for comp in result_clamp.components:
    check(0.0 <= comp.value <= 1.0, f"{comp.name} value clamped to [0,1]")

# ─── Section 11: Component count always 7 ───────────────────────────
print("11. always 7 components")
for snap in [snap_zero, snap_one, snap_w]:
    r = compute_influence_score(snap)
    check(len(r.components) == 7, "7 components")

# ─── Section 12: InfluenceComponent frozen ───────────────────────────
print("12. InfluenceComponent frozen")
comp = InfluenceComponent(name="test", value=0.5, weight=0.3, contribution=0.15)
try:
    comp.name = "changed"
    check(False, "should be frozen")
except AttributeError:
    check(True, "InfluenceComponent is frozen")

# ─── Section 13: InfluenceSnapshot frozen ────────────────────────────
print("13. InfluenceSnapshot frozen")
snap_frozen = InfluenceSnapshot(goal_score=0.5)
try:
    snap_frozen.goal_score = 0.9
    check(False, "should be frozen")
except AttributeError:
    check(True, "InfluenceSnapshot is frozen")

# ─── Section 14: InfluenceResult frozen ──────────────────────────────
print("14. InfluenceResult frozen")
result_frozen = compute_influence_score(snap_frozen)
try:
    result_frozen.final_score = 0.9
    check(False, "should be frozen")
except AttributeError:
    check(True, "InfluenceResult is frozen")

# ─── Section 15: to_dict() serialization ─────────────────────────────
print("15. to_dict() serialization")
result_ser = compute_influence_score(snap_w)
d = result_ser.to_dict()
check("final_score" in d, "final_score in dict")
check("components" in d, "components in dict")
check("weights" in d, "weights in dict")
check(len(d["components"]) == 7, "7 components in dict")
check(len(d["weights"]) == 7, "7 weights in dict")
for comp_d in d["components"]:
    check("name" in comp_d, "name in component dict")
    check("value" in comp_d, "value in component dict")
    check("weight" in comp_d, "weight in component dict")
    check("contribution" in comp_d, "contribution in component dict")

# ─── Section 16: InfluenceSnapshot.to_dict() ─────────────────────────
print("16. InfluenceSnapshot.to_dict()")
sd = snap_w.to_dict()
check("goal_score" in sd, "goal_score in snapshot dict")
check("plan_score" in sd, "plan_score in snapshot dict")
check("commitment_signal" in sd, "commitment_signal in snapshot dict")
check(len(sd) == 7, "7 fields in snapshot dict")

# ─── Section 17: NO_INFLUENCE_RESULT sentinel ────────────────────────
print("17. NO_INFLUENCE_RESULT sentinel")
check(NO_INFLUENCE_RESULT.final_score == 0.0, "sentinel score is 0")
check(len(NO_INFLUENCE_RESULT.components) == 0, "sentinel has no components")
check(NO_INFLUENCE_RESULT.weights == {}, "sentinel has no weights")

# ─── Section 18: build_influence_snapshot — all None inputs ──────────
print("18. build_influence_snapshot — all None → defaults")
snap_none = build_influence_snapshot()
check(snap_none.goal_score == 0.0, "default goal_score = 0")
check(snap_none.plan_score == 0.0, "default plan_score = 0")
check(snap_none.strategy_score == 0.0, "default strategy_score = 0")
check(snap_none.state_bias == 0.0, "default state_bias = 0")
check(snap_none.credit_signal == 0.0, "default credit_signal = 0")
check(snap_none.exploration_signal == 0.0, "default exploration_signal = 0")
check(snap_none.commitment_signal == 0.0, "default commitment_signal = 0")

# ─── Section 19: build_influence_snapshot — direct values ────────────
print("19. build_influence_snapshot — direct values")
snap_direct = build_influence_snapshot(
    goal_score=0.7, plan_confidence=0.6, strategy_score=0.8
)
check(snap_direct.goal_score == 0.7, "goal_score passed through")
check(snap_direct.plan_score == 0.6, "plan_confidence → plan_score")
check(snap_direct.strategy_score == 0.8, "strategy_score passed through")

# ─── Section 20: build_influence_snapshot — state_bias from dicts ────
print("20. build_influence_snapshot — state_bias normalization")
snap_bias = build_influence_snapshot(
    conditioning_bias={"strategy_bias": {"s1": 0.05, "s2": -0.03}},
    learned_state_bias={"s1": 0.02},
)
check(snap_bias.state_bias > 0, "state_bias computed from bias dicts")
check(snap_bias.state_bias <= 1.0, "state_bias bounded")

# ─── Section 21: build_influence_snapshot — exploration inversion ────
print("21. exploration rate inversion")
snap_exp_low = build_influence_snapshot(exploration_rate=0.1)
snap_exp_high = build_influence_snapshot(exploration_rate=0.9)
check(
    snap_exp_low.exploration_signal > snap_exp_high.exploration_signal,
    "low exploration rate → high exploitation signal",
)
check(abs(snap_exp_low.exploration_signal - 0.9) < 1e-9, "1.0 - 0.1 = 0.9")
check(abs(snap_exp_high.exploration_signal - 0.1) < 1e-9, "1.0 - 0.9 = 0.1")

# ─── Section 22: build_influence_snapshot — commitment from streaks ──
print("22. commitment from persistence_streaks")
snap_commit = build_influence_snapshot(persistence_streaks={"g1": 3.0, "g2": 1.0})
check(snap_commit.commitment_signal > 0, "commitment computed from streaks")
check(snap_commit.commitment_signal <= 1.0, "commitment bounded")

# ─── Section 23: build_influence_snapshot — credit_signal ────────────
print("23. credit signal normalization")
snap_credit = build_influence_snapshot(credit_total_signal=0.8)
check(snap_credit.credit_signal == 0.8, "credit signal passed through when ≤ 1")

snap_credit_big = build_influence_snapshot(credit_total_signal=5.0)
check(snap_credit_big.credit_signal == 1.0, "credit signal clamped at 1.0")

# ─── Section 24: DecisionTrace has new fields ────────────────────────
print("24. DecisionTrace influence fields")
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
    influence_components=(
        {"name": "goal", "value": 0.7, "weight": 0.3, "contribution": 0.21},
    ),
    influence_weights={"goal": 0.3},
    final_influence_score=0.55,
    influence_breakdown={"goal": 0.21},
)
check(dt.final_influence_score == 0.55, "final_influence_score set")
check(dt.influence_components is not None, "influence_components set")
check(dt.influence_weights == {"goal": 0.3}, "influence_weights set")
check(dt.influence_breakdown == {"goal": 0.21}, "influence_breakdown set")

# ─── Section 25: DecisionTrace.to_dict() serializes ──────────────────
print("25. to_dict() serializes influence fields")
dd = dt.to_dict()
check("final_influence_score" in dd, "final_influence_score in dict")
check("influence_components" in dd, "influence_components in dict")
check("influence_weights" in dd, "influence_weights in dict")
check("influence_breakdown" in dd, "influence_breakdown in dict")
check(dd["final_influence_score"] == 0.55, "value correct in dict")

# ─── Section 26: DecisionTrace.to_dict() omits None fields ──────────
print("26. to_dict() omits None influence fields")
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
check("final_influence_score" not in dd_none, "omitted when None")
check("influence_components" not in dd_none, "omitted when None")
check("influence_weights" not in dd_none, "omitted when None")
check("influence_breakdown" not in dd_none, "omitted when None")

# ─── Section 27: build_trace() accepts influence params ──────────────
print("27. build_trace() accepts influence params")
bt = build_trace(
    turn_id=5,
    influence_components=(
        {"name": "goal", "value": 0.5, "weight": 0.3, "contribution": 0.15},
    ),
    influence_weights={"goal": 0.3},
    final_influence_score=0.42,
    influence_breakdown={"goal": 0.15},
)
check(bt.final_influence_score == 0.42, "build_trace passes final_influence_score")
check(bt.influence_weights == {"goal": 0.3}, "build_trace passes influence_weights")

# ─── Section 28: Goal dominance — goal has highest weight ────────────
print("28. goal dominance — highest weight")
snap_goal_dom = InfluenceSnapshot(goal_score=1.0)
result_goal = compute_influence_score(snap_goal_dom)
goal_contrib = None
for c in result_goal.components:
    if c.name == "goal":
        goal_contrib = c.contribution
check(goal_contrib == W_GOAL, f"goal contribution = {W_GOAL}")
# Goal alone should produce the largest single-signal score
snap_plan_dom = InfluenceSnapshot(plan_score=1.0)
result_plan = compute_influence_score(snap_plan_dom)
check(
    result_goal.final_score > result_plan.final_score,
    "goal alone > plan alone",
)

# ─── Section 29: Additive composition — no interactions ──────────────
print("29. additive composition — no multiplicative interactions")
snap_parts = InfluenceSnapshot(goal_score=0.5, plan_score=0.5)
result_parts = compute_influence_score(snap_parts)
snap_goal_only = InfluenceSnapshot(goal_score=0.5)
snap_plan_only = InfluenceSnapshot(plan_score=0.5)
result_goal_only = compute_influence_score(snap_goal_only)
result_plan_only = compute_influence_score(snap_plan_only)
check(
    abs(
        result_parts.final_score
        - (result_goal_only.final_score + result_plan_only.final_score)
    )
    < 1e-9,
    "score(goal+plan) = score(goal) + score(plan) — pure additive",
)

# ─── Section 30: No LLM calls ───────────────────────────────────────
print("30. no LLM calls in module")
import inspect

src = inspect.getsource(sys.modules["umh.runtime_engine.influence_scoring"])
check("call_with_fallback" not in src, "no LLM calls")
check("import anthropic" not in src, "no anthropic import")

# ─── Section 31: No randomness ──────────────────────────────────────
print("31. no randomness")
check("random.random" not in src, "no random.random()")
check("random.choice" not in src, "no random.choice()")
check("random.uniform" not in src, "no random.uniform()")

# ─── Section 32: ExecutionSpine untouched ────────────────────────────
print("32. ExecutionSpine not modified")
import importlib

es = importlib.import_module("umh.runtime_engine.execution_spine")
check(hasattr(es, "SpineResult"), "SpineResult exists unchanged")
spine_src = inspect.getsource(es)
check("influence_scoring" not in spine_src, "no influence_scoring in spine")
check("final_influence_score" not in spine_src, "no final_influence_score in spine")

# ─── Section 33: Influence weights dict matches constants ────────────
print("33. weights dict matches constants")
snap_any = InfluenceSnapshot(goal_score=0.5)
result_any = compute_influence_score(snap_any)
w = result_any.weights
check(w["goal"] == W_GOAL, "dict goal matches constant")
check(w["plan"] == W_PLAN, "dict plan matches constant")
check(w["strategy"] == W_STRATEGY, "dict strategy matches constant")
check(w["state_bias"] == W_STATE, "dict state_bias matches constant")
check(w["credit"] == W_CREDIT, "dict credit matches constant")
check(w["exploration"] == W_EXPLORATION, "dict exploration matches constant")
check(w["commitment"] == W_COMMITMENT, "dict commitment matches constant")

# ─── Section 34: Half-signal test ────────────────────────────────────
print("34. half signals → exactly 0.5 score")
snap_half = InfluenceSnapshot(
    goal_score=0.5,
    plan_score=0.5,
    strategy_score=0.5,
    state_bias=0.5,
    credit_signal=0.5,
    exploration_signal=0.5,
    commitment_signal=0.5,
)
result_half = compute_influence_score(snap_half)
check(abs(result_half.final_score - 0.5) < 1e-9, "all 0.5 → score = 0.5")

# ─── Section 35: Component ordering stable ──────────────────────────
print("35. component ordering stable")
names = [c.name for c in result_half.components]
check(
    names
    == [
        "goal",
        "plan",
        "strategy",
        "state_bias",
        "credit",
        "exploration",
        "commitment",
    ],
    "components in canonical order",
)

# ─── Final report ────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Influence Scoring: {passed}/{passed + failed} passed")
if failed:
    print(f"  {failed} FAILED")
    raise SystemExit(1)
else:
    print("  ALL PASSED")
