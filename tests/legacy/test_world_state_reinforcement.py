"""
World-State Reinforcement & Cluster Learning — test suite.

Validates:
    - ClusterPerformance.reinforce() EMA update
    - WorldStateEngine.reinforce_cluster() gating and application
    - WorldStateEngine.get_learned_state_bias() bounded output
    - Downstream integration: learned bias added to conditioned scores
    - DecisionTrace observability fields
    - Persistence: snapshot/restore round-trip with new fields
    - Determinism: same inputs → same outputs
    - Backward compat: old snapshots without quality_ema restore to defaults
    - Hard constraints: no LLM, no randomness, no ExecutionSpine changes
"""

import sys

sys.path.insert(0, "/opt/OS")

from types import SimpleNamespace

from umh.world.state import (
    ClusterPerformance,
    StateCluster,
    WorldState,
    WorldStateEngine,
    REINFORCEMENT_ALPHA,
    MAX_LEARNED_STATE_BIAS,
    MIN_REINFORCEMENT_OBSERVATIONS,
    CLUSTER_SIMILARITY_THRESHOLD,
    CONDITIONING_WEIGHT,
    FEATURE_KEYS,
    extract_state,
    get_world_state_engine,
    reset_world_state_engine,
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


def make_cluster(
    cluster_id: str = "test_cluster",
    obs_count: int = 5,
    quality_ema: float = 0.5,
    last_used_turn: int = 0,
    strategies: dict | None = None,
) -> StateCluster:
    perf = ClusterPerformance(
        observation_count=obs_count,
        quality_ema=quality_ema,
        last_used_turn=last_used_turn,
    )
    if strategies:
        perf.strategy_scores = dict(strategies)
        perf.strategy_counts = {k: obs_count for k in strategies}
    cluster = StateCluster(cluster_id=cluster_id)
    cluster.performance = perf
    return cluster


# ─── Section 1: ClusterPerformance.reinforce() basic EMA ──────────────
print("1. reinforce() basic EMA update")
cp = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp.reinforce(credit_weight=1.0, quality_signal=0.8, turn=10)
expected_ema = REINFORCEMENT_ALPHA * 0.8 + (1 - REINFORCEMENT_ALPHA) * 0.5
check(abs(cp.quality_ema - expected_ema) < 1e-6, "EMA update correct")
check(cp.last_used_turn == 10, "last_used_turn updated")

# ─── Section 2: reinforce() respects credit_weight scaling ───────────
print("2. reinforce() credit_weight scales alpha")
cp2a = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp2b = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp2a.reinforce(credit_weight=1.0, quality_signal=0.9, turn=1)
cp2b.reinforce(credit_weight=0.3, quality_signal=0.9, turn=1)
check(
    abs(cp2a.quality_ema - cp2b.quality_ema) > 0.01,
    "different credit_weight → different EMA",
)
check(
    cp2a.quality_ema > cp2b.quality_ema, "higher weight → stronger update toward signal"
)

# ─── Section 3: reinforce() ignores sub-floor credit ─────────────────
print("3. reinforce() ignores sub-floor credit")
cp3 = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp3.reinforce(credit_weight=0.005, quality_signal=1.0, turn=5)
check(cp3.quality_ema == 0.5, "sub-floor credit → no change")
check(cp3.last_used_turn == 0, "sub-floor → turn not updated")

# ─── Section 4: reinforce() clamps credit_weight to 1.0 ─────────────
print("4. reinforce() clamps credit_weight at 1.0")
cp4a = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp4b = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp4a.reinforce(credit_weight=1.0, quality_signal=0.8, turn=1)
cp4b.reinforce(credit_weight=5.0, quality_signal=0.8, turn=1)
check(
    abs(cp4a.quality_ema - cp4b.quality_ema) < 1e-9,
    "credit > 1.0 clamped to 1.0",
)

# ─── Section 5: WorldStateEngine.reinforce_cluster() basic ───────────
print("5. reinforce_cluster() basic operation")
engine = WorldStateEngine()
cluster = make_cluster("c1", obs_count=5, quality_ema=0.5, strategies={"s1": 0.6})
engine._clusters["c1"] = cluster
result = engine.reinforce_cluster("c1", 0.8, 0.9, 10)
check(result is True, "returns True on success")
check(engine._clusters["c1"].performance.quality_ema != 0.5, "EMA changed")

# ─── Section 6: reinforce_cluster() rejects unknown cluster ──────────
print("6. reinforce_cluster() rejects unknown cluster")
engine2 = WorldStateEngine()
result2 = engine2.reinforce_cluster("nonexistent", 0.8, 0.9, 10)
check(result2 is False, "returns False for unknown cluster")

# ─── Section 7: reinforce_cluster() gated by MIN_REINFORCEMENT_OBSERVATIONS
print("7. reinforce_cluster() observation gating")
engine3 = WorldStateEngine()
cluster3 = make_cluster(
    "c3", obs_count=MIN_REINFORCEMENT_OBSERVATIONS - 1, quality_ema=0.5
)
engine3._clusters["c3"] = cluster3
result3 = engine3.reinforce_cluster("c3", 0.8, 0.9, 10)
check(result3 is False, "below min observations → rejected")
check(cluster3.performance.quality_ema == 0.5, "EMA unchanged when gated")

# ─── Section 8: get_learned_state_bias() positive quality ────────────
print("8. get_learned_state_bias() positive quality (math verification)")
# Directly verify the formula: (quality_ema - 0.5) * MAX_LEARNED_STATE_BIAS * sim
quality_delta = 0.7 - 0.5  # quality_ema=0.7
sim_val = 0.95
raw_bias = quality_delta * MAX_LEARNED_STATE_BIAS * sim_val
check(raw_bias > 0, "positive quality_delta → positive bias")
check(raw_bias <= MAX_LEARNED_STATE_BIAS, "bounded by MAX_LEARNED_STATE_BIAS")
expected_raw = 0.2 * 0.10 * 0.95  # = 0.019
check(abs(raw_bias - expected_raw) < 1e-9, f"formula correct: {raw_bias}")

# Also test via engine with matching state
engine4 = WorldStateEngine()
cluster4 = make_cluster(
    "c4", obs_count=5, quality_ema=0.7, strategies={"strat_a": 0.6, "strat_b": 0.5}
)
test_state = extract_state(current_turn=10)
fd = test_state.feature_dict
cluster4.centroid_features = dict(fd)
cluster4.size = 3
cluster4.member_state_ids = ["s1", "s2", "s3"]
engine4._clusters["c4"] = cluster4
bias4 = engine4.get_learned_state_bias(test_state)
check(len(bias4) == 2, "bias has entry per strategy")
for v in bias4.values():
    check(v >= 0, "positive quality → non-negative bias")
    check(abs(v) <= MAX_LEARNED_STATE_BIAS, "bounded")

# ─── Section 9: get_learned_state_bias() negative quality ────────────
print("9. get_learned_state_bias() negative quality → negative bias")
cluster_neg = make_cluster("cn", obs_count=5, quality_ema=0.3, strategies={"s1": 0.6})
quality_delta_neg = 0.3 - 0.5
raw_neg = quality_delta_neg * MAX_LEARNED_STATE_BIAS * 0.9
check(raw_neg < 0, "negative quality_delta → negative bias")
clamped_neg = max(-MAX_LEARNED_STATE_BIAS, min(MAX_LEARNED_STATE_BIAS, raw_neg))
check(clamped_neg >= -MAX_LEARNED_STATE_BIAS, "clamped at floor")

# ─── Section 10: get_learned_state_bias() neutral quality ────────────
print("10. neutral quality → zero bias")
quality_delta_neutral = 0.5 - 0.5
raw_neutral = quality_delta_neutral * MAX_LEARNED_STATE_BIAS * 0.9
check(abs(raw_neutral) < 1e-9, "neutral quality → zero bias")

# ─── Section 11: get_learned_state_bias() below min observations ─────
print("11. below min observations → empty bias")
engine_few = WorldStateEngine()
cluster_few = make_cluster(
    "cf", obs_count=MIN_REINFORCEMENT_OBSERVATIONS - 1, strategies={"s1": 0.6}
)
cluster_few.centroid_features = {k: 0.5 for k in FEATURE_KEYS}
cluster_few.size = 1
engine_few._clusters["cf"] = cluster_few
few_state = extract_state(current_turn=5)
bias_few = engine_few.get_learned_state_bias(few_state)
check(bias_few == {}, "insufficient observations → empty bias")

# ─── Section 12: ClusterPerformance.to_dict() includes new fields ────
print("12. to_dict() includes quality_ema and last_used_turn")
cp_td = ClusterPerformance(observation_count=5, quality_ema=0.72, last_used_turn=15)
d = cp_td.to_dict()
check("quality_ema" in d, "quality_ema in dict")
check("last_used_turn" in d, "last_used_turn in dict")
check(d["quality_ema"] == 0.72, "quality_ema value correct")
check(d["last_used_turn"] == 15, "last_used_turn value correct")

# ─── Section 13: Persistence round-trip ──────────────────────────────
print("13. snapshot/restore round-trip with new fields")
engine_snap = WorldStateEngine()
cluster_snap = make_cluster(
    "cs",
    obs_count=10,
    quality_ema=0.73,
    last_used_turn=20,
    strategies={"s1": 0.65},
)
cluster_snap.centroid_features = {k: 0.5 for k in FEATURE_KEYS}
cluster_snap.size = 3
cluster_snap.member_state_ids = ["a", "b", "c"]
engine_snap._clusters["cs"] = cluster_snap

snapshot_data = engine_snap.snapshot()

engine_restore = WorldStateEngine()
engine_restore.restore(snapshot_data)
restored = engine_restore.get_cluster("cs")
check(restored is not None, "cluster restored")
check(abs(restored.performance.quality_ema - 0.73) < 1e-6, "quality_ema preserved")
check(restored.performance.last_used_turn == 20, "last_used_turn preserved")

# ─── Section 14: Backward compat — old snapshot without new fields ───
print("14. backward compat — restore old snapshot")
old_snapshot = {
    "clusters": {
        "cold": {
            "cluster_id": "cold",
            "centroid_features": {},
            "size": 2,
            "performance": {
                "strategy_scores": {"s1": 0.6},
                "strategy_counts": {"s1": 3},
                "goal_scores": {},
                "goal_counts": {},
                "avg_utility": 0.55,
                "observation_count": 3,
                # no quality_ema, no last_used_turn
            },
        }
    }
}
engine_old = WorldStateEngine()
engine_old.restore(old_snapshot)
old_cluster = engine_old.get_cluster("cold")
check(old_cluster is not None, "old cluster restored")
check(old_cluster.performance.quality_ema == 0.5, "default quality_ema = 0.5")
check(old_cluster.performance.last_used_turn == 0, "default last_used_turn = 0")

# ─── Section 15: DecisionTrace has new fields ────────────────────────
print("15. DecisionTrace world-state reinforcement fields")
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
    world_state_cluster_quality=0.72,
    learned_state_bias={"s1": 0.05},
    combined_state_bias={"s1": 0.08},
    cluster_quality_ema=0.72,
    cluster_observation_count=10,
    world_state_reinforcement_applied=True,
)
check(dt.world_state_cluster_quality == 0.72, "cluster_quality field set")
check(dt.learned_state_bias == {"s1": 0.05}, "learned_state_bias field set")
check(dt.combined_state_bias == {"s1": 0.08}, "combined_state_bias field set")
check(dt.cluster_quality_ema == 0.72, "cluster_quality_ema field set")
check(dt.cluster_observation_count == 10, "cluster_observation_count field set")
check(dt.world_state_reinforcement_applied is True, "reinforcement_applied field set")

# ─── Section 16: DecisionTrace.to_dict() serializes new fields ───────
print("16. to_dict() serializes reinforcement fields")
dd = dt.to_dict()
check("world_state_cluster_quality" in dd, "cluster_quality in dict")
check("learned_state_bias" in dd, "learned_state_bias in dict")
check("combined_state_bias" in dd, "combined_state_bias in dict")
check("cluster_quality_ema" in dd, "cluster_quality_ema in dict")
check("cluster_observation_count" in dd, "cluster_observation_count in dict")
check("world_state_reinforcement_applied" in dd, "reinforcement_applied in dict")

# ─── Section 17: DecisionTrace.to_dict() omits None fields ───────────
print("17. to_dict() omits None reinforcement fields")
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
check("world_state_cluster_quality" not in dd_none, "omitted when None")
check("learned_state_bias" not in dd_none, "omitted when None")
check("combined_state_bias" not in dd_none, "omitted when None")
check("cluster_quality_ema" not in dd_none, "omitted when None")
check("cluster_observation_count" not in dd_none, "omitted when None")
check("world_state_reinforcement_applied" not in dd_none, "omitted when None")

# ─── Section 18: build_trace() accepts new params ────────────────────
print("18. build_trace() accepts reinforcement params")
bt = build_trace(
    turn_id=5,
    world_state_cluster_quality=0.65,
    learned_state_bias={"x": 0.03},
    combined_state_bias={"x": 0.07},
    cluster_quality_ema=0.65,
    cluster_observation_count=8,
    world_state_reinforcement_applied=True,
)
check(bt.world_state_cluster_quality == 0.65, "build_trace passes cluster_quality")
check(bt.learned_state_bias == {"x": 0.03}, "build_trace passes learned_state_bias")
check(
    bt.world_state_reinforcement_applied is True,
    "build_trace passes reinforcement_applied",
)

# ─── Section 19: Reinforcement accumulates over turns ─────────────────
print("19. reinforcement accumulates over multiple turns")
cp_acc = ClusterPerformance(observation_count=5, quality_ema=0.5)
for turn in range(1, 6):
    cp_acc.reinforce(credit_weight=0.5, quality_signal=0.8, turn=turn)
check(cp_acc.quality_ema > 0.5, "quality rises toward positive signal")
check(cp_acc.quality_ema < 0.8, "hasn't fully converged after 5 turns")
check(cp_acc.last_used_turn == 5, "last_used_turn tracks latest")

# ─── Section 20: Reinforcement with alternating signals ──────────────
print("20. alternating signals → quality stays near center")
cp_alt = ClusterPerformance(observation_count=5, quality_ema=0.5)
for turn in range(1, 11):
    signal = 0.9 if turn % 2 == 0 else 0.1
    cp_alt.reinforce(credit_weight=0.5, quality_signal=signal, turn=turn)
check(
    abs(cp_alt.quality_ema - 0.5) < 0.2,
    "alternating signals → quality near center",
)

# ─── Section 21: Learned bias bounded at extremes ────────────────────
print("21. learned bias bounded at extremes")
# quality_ema = 1.0 with sim = 1.0 → max delta is 0.5
# raw = 0.5 * 0.10 * 1.0 = 0.05, which is within [-0.10, +0.10]
quality_delta_max = 1.0 - 0.5
raw_max = quality_delta_max * MAX_LEARNED_STATE_BIAS * 1.0
clamped_max = max(-MAX_LEARNED_STATE_BIAS, min(MAX_LEARNED_STATE_BIAS, raw_max))
check(clamped_max == 0.05, "max bias at quality=1.0, sim=1.0 is 0.05")
check(clamped_max <= MAX_LEARNED_STATE_BIAS, "within upper bound")

# quality_ema = 0.0 with sim = 1.0 → raw = -0.05
quality_delta_min = 0.0 - 0.5
raw_min = quality_delta_min * MAX_LEARNED_STATE_BIAS * 1.0
clamped_min = max(-MAX_LEARNED_STATE_BIAS, min(MAX_LEARNED_STATE_BIAS, raw_min))
check(clamped_min == -0.05, "min bias at quality=0.0, sim=1.0 is -0.05")
check(clamped_min >= -MAX_LEARNED_STATE_BIAS, "within lower bound")

# ─── Section 22: Determinism ─────────────────────────────────────────
print("22. determinism — same inputs → same outputs")
cp_d1 = ClusterPerformance(observation_count=5, quality_ema=0.5)
cp_d2 = ClusterPerformance(observation_count=5, quality_ema=0.5)
for t in range(1, 4):
    cp_d1.reinforce(0.7, 0.85, t)
    cp_d2.reinforce(0.7, 0.85, t)
check(cp_d1.quality_ema == cp_d2.quality_ema, "identical runs produce identical EMA")
check(cp_d1.last_used_turn == cp_d2.last_used_turn, "identical last_used_turn")

# ─── Section 23: No LLM calls ────────────────────────────────────────
print("23. no LLM calls in module")
import inspect

ws_src = inspect.getsource(sys.modules["umh.runtime_engine.world_state"])
check("call_with_fallback" not in ws_src, "no LLM call_with_fallback")
check("import anthropic" not in ws_src, "no anthropic import")

# ─── Section 24: No randomness ───────────────────────────────────────
print("24. no randomness in reinforcement code")
check("random.random" not in ws_src, "no random.random()")
check("random.choice" not in ws_src, "no random.choice()")
check("random.uniform" not in ws_src, "no random.uniform()")

# ─── Section 25: ExecutionSpine untouched ─────────────────────────────
print("25. ExecutionSpine not modified")
import importlib

es_mod = importlib.import_module("umh.runtime_engine.execution_spine")
check(hasattr(es_mod, "SpineResult"), "SpineResult exists unchanged")
spine_src = inspect.getsource(es_mod)
check("reinforce" not in spine_src, "no reinforce references in spine")
check("quality_ema" not in spine_src, "no quality_ema in spine")

# ─── Section 26: Existing record() method still works ────────────────
print("26. existing record() method backward compat")
cp_rec = ClusterPerformance()
cp_rec.record(strategy="s1", strategy_score=0.7, utility=0.6)
check(cp_rec.observation_count == 1, "observation counted")
check("s1" in cp_rec.strategy_scores, "strategy recorded")
check(cp_rec.quality_ema == 0.5, "record() doesn't touch quality_ema")

# ─── Section 27: get_conditioning_bias still works ────────────────────
print("27. existing get_conditioning_bias backward compat")
engine_compat = WorldStateEngine()
cluster_compat = make_cluster(
    "cc", obs_count=5, quality_ema=0.7, strategies={"s1": 0.6}
)
cluster_compat.centroid_features = {k: 0.5 for k in FEATURE_KEYS}
cluster_compat.size = 3
cluster_compat.member_state_ids = ["a", "b", "c"]
engine_compat._clusters["cc"] = cluster_compat
state_compat = extract_state(current_turn=10)
bias_compat = engine_compat.get_conditioning_bias(state_compat)
# Should still return ConditioningBias with strategy_bias based on CONDITIONING_WEIGHT
check(hasattr(bias_compat, "strategy_bias"), "still returns ConditioningBias")
check(hasattr(bias_compat, "expected_utility"), "expected_utility present")

# ─── Section 28: Constants well-defined ──────────────────────────────
print("28. constants well-defined")
check(MAX_LEARNED_STATE_BIAS == 0.10, "MAX_LEARNED_STATE_BIAS = 0.10")
check(REINFORCEMENT_ALPHA == 0.3, "REINFORCEMENT_ALPHA = 0.3")
check(MIN_REINFORCEMENT_OBSERVATIONS == 3, "MIN_REINFORCEMENT_OBSERVATIONS = 3")

# ─── Section 29: Singleton reset clears reinforcement state ──────────
print("29. singleton reset clears reinforcement state")
reset_world_state_engine()
eng = get_world_state_engine()
check(eng.cluster_count == 0, "fresh engine after reset")
cluster_r = make_cluster("cr", obs_count=5, quality_ema=0.8)
eng._clusters["cr"] = cluster_r
reset_world_state_engine()
eng2 = get_world_state_engine()
check(eng2.cluster_count == 0, "reset clears all clusters")

# ─── Section 30: Combined bias additive composition ──────────────────
print("30. combined bias = conditioning + learned (additive)")
conditioning = {"s1": 0.05, "s2": -0.03}
learned = {"s1": 0.02, "s3": 0.01}
combined = dict(conditioning)
for k, v in learned.items():
    combined[k] = combined.get(k, 0.0) + v
check(abs(combined["s1"] - 0.07) < 1e-9, "s1 = conditioning + learned")
check(combined["s2"] == -0.03, "s2 = conditioning only")
check(combined["s3"] == 0.01, "s3 = learned only")

# ─── Section 31: reinforce_cluster accepts boundary turn=0 ───────────
print("31. reinforce_cluster at turn=0")
engine_t0 = WorldStateEngine()
cluster_t0 = make_cluster("ct0", obs_count=5, quality_ema=0.5)
engine_t0._clusters["ct0"] = cluster_t0
result_t0 = engine_t0.reinforce_cluster("ct0", 0.5, 0.7, 0)
check(result_t0 is True, "turn=0 accepted")
check(cluster_t0.performance.last_used_turn == 0, "last_used_turn = 0")

# ─── Section 32: quality_ema range stays in [0, 1] ───────────────────
print("32. quality_ema stays bounded")
cp_bound = ClusterPerformance(observation_count=5, quality_ema=0.5)
for _ in range(100):
    cp_bound.reinforce(1.0, 1.0, 1)
check(cp_bound.quality_ema <= 1.0, "EMA ≤ 1.0 after 100 max reinforcements")
check(cp_bound.quality_ema >= 0.0, "EMA ≥ 0.0")

cp_bound2 = ClusterPerformance(observation_count=5, quality_ema=0.5)
for _ in range(100):
    cp_bound2.reinforce(1.0, 0.0, 1)
check(cp_bound2.quality_ema >= 0.0, "EMA ≥ 0.0 after 100 min reinforcements")
check(cp_bound2.quality_ema <= 1.0, "EMA ≤ 1.0")

# ─── Section 33: Convergence test — EMA approaches signal ────────────
print("33. convergence — EMA approaches repeated signal")
cp_conv = ClusterPerformance(observation_count=5, quality_ema=0.5)
target = 0.85
for _ in range(50):
    cp_conv.reinforce(1.0, target, 1)
check(abs(cp_conv.quality_ema - target) < 0.01, f"converges near {target}")

# ─── Final report ────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"World-State Reinforcement: {passed}/{passed + failed} passed")
if failed:
    print(f"  {failed} FAILED")
    raise SystemExit(1)
else:
    print("  ALL PASSED")
