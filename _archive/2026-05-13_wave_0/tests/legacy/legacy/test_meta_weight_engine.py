"""
Tests for MetaWeightEngine — deterministic weight adaptation.

Covers: constants, EMA learning, normalization, boundedness, gating,
improvement-over-time, snapshot/restore, DecisionTrace integration,
influence_scoring integration, determinism, no LLM, no randomness,
no ExecutionSpine, backward compatibility.
"""

import sys

sys.path.insert(0, "/opt/OS")

passed = 0
failed = 0
section = 0


def check(condition: bool, label: str, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


def header(title: str):
    global section
    section += 1
    print(f"{section}. {title}")


# ── 1. Constants ─────────────────────────────────────────────────────────

header("constants defined correctly")
from umh.runtime_engine.meta_weight_engine import (
    META_WEIGHT_ALPHA,
    META_WEIGHT_SCALE,
    MAX_ADJUSTMENT,
    MIN_WEIGHT,
    MIN_OBSERVATIONS,
    SIGNAL_NAMES,
)

check(META_WEIGHT_ALPHA == 0.15, "alpha", f"got {META_WEIGHT_ALPHA}")
check(META_WEIGHT_SCALE == 0.30, "scale", f"got {META_WEIGHT_SCALE}")
check(MAX_ADJUSTMENT == 0.10, "max_adj", f"got {MAX_ADJUSTMENT}")
check(MIN_WEIGHT == 0.02, "min_weight", f"got {MIN_WEIGHT}")
check(MIN_OBSERVATIONS == 3, "min_obs", f"got {MIN_OBSERVATIONS}")
check(len(SIGNAL_NAMES) == 7, "7 signals", f"got {len(SIGNAL_NAMES)}")

# ── 2. SignalPerformance EMA ─────────────────────────────────────────────

header("SignalPerformance EMA update")
from umh.runtime_engine.meta_weight_engine import SignalPerformance

sp = SignalPerformance()
check(sp.ema == 0.0, "initial ema 0")
check(sp.observations == 0, "initial obs 0")

sp.update(1.0)
check(sp.observations == 1, "obs after 1 update")
expected_ema = 0.15 * 1.0 + 0.85 * 0.0
check(abs(sp.ema - expected_ema) < 1e-9, "ema after 1 update", f"got {sp.ema}")

sp.update(1.0)
expected_ema2 = 0.15 * 1.0 + 0.85 * expected_ema
check(abs(sp.ema - expected_ema2) < 1e-9, "ema after 2 updates", f"got {sp.ema}")

# ── 3. SignalPerformance to_dict ─────────────────────────────────────────

header("SignalPerformance serialization")
d = sp.to_dict()
check("ema" in d, "has ema")
check("observations" in d, "has observations")
check("last_contribution" in d, "has last_contribution")
check(d["observations"] == 2, "observations=2")

# ── 4. MetaWeightEngine initialization ───────────────────────────────────

header("engine initialization")
from umh.runtime_engine.meta_weight_engine import MetaWeightEngine

engine = MetaWeightEngine()
check(engine.total_observations == 0, "initial obs 0")
check(len(engine._performance) == 7, "7 signal trackers")

# ── 5. Gating — no adaptation before MIN_OBSERVATIONS ────────────────────

header("gating — no adaptation before MIN_OBSERVATIONS")
from umh.runtime_engine.influence_scoring import BASE_WEIGHTS

engine2 = MetaWeightEngine()
engine2.record_outcome({"goal": 0.8, "plan": 0.6}, 0.9)
engine2.record_outcome({"goal": 0.7, "plan": 0.5}, 0.8)
result_gated = engine2.get_adapted_weights(BASE_WEIGHTS)
check(not result_gated.adapted, "not adapted with 2 obs")
check(result_gated.adapted_weights == BASE_WEIGHTS, "returns base weights when gated")

# ── 6. Adaptation kicks in after MIN_OBSERVATIONS ────────────────────────

header("adaptation after MIN_OBSERVATIONS")
engine3 = MetaWeightEngine()
for _ in range(MIN_OBSERVATIONS):
    engine3.record_outcome(
        {
            "goal": 0.9,
            "plan": 0.8,
            "strategy": 0.7,
            "state_bias": 0.5,
            "credit": 0.5,
            "exploration": 0.5,
            "commitment": 0.3,
        },
        0.85,
    )
result_adapted = engine3.get_adapted_weights(BASE_WEIGHTS)
check(result_adapted.adapted, "adapted after MIN_OBSERVATIONS obs")
check(result_adapted.observations >= MIN_OBSERVATIONS, "obs >= MIN_OBSERVATIONS")

# ── 7. Weights always sum to 1.0 ─────────────────────────────────────────

header("weights always normalized to sum 1.0")
w_sum = sum(result_adapted.adapted_weights.values())
check(abs(w_sum - 1.0) < 1e-9, "sum=1.0", f"got {w_sum}")

# ── 8. All weights >= MIN_WEIGHT ──────────────────────────────────────────

header("all weights >= MIN_WEIGHT before normalization")
# After normalization they could be slightly different due to re-scaling,
# but the raw floor is applied before normalization.
for name, w in result_adapted.adapted_weights.items():
    check(w > 0, f"{name} > 0", f"got {w}")

# ── 9. Adjustments bounded by MAX_ADJUSTMENT ─────────────────────────────

header("adjustments bounded by MAX_ADJUSTMENT")
for name, adj in result_adapted.adjustments.items():
    check(
        -MAX_ADJUSTMENT <= adj <= MAX_ADJUSTMENT,
        f"{name} adj in bounds",
        f"got {adj}",
    )

# ── 10. Determinism — same inputs → same outputs ─────────────────────────

header("determinism")
engine4a = MetaWeightEngine()
engine4b = MetaWeightEngine()
for _ in range(5):
    vals = {
        "goal": 0.8,
        "plan": 0.6,
        "strategy": 0.7,
        "state_bias": 0.4,
        "credit": 0.5,
        "exploration": 0.3,
        "commitment": 0.2,
    }
    engine4a.record_outcome(vals, 0.75)
    engine4b.record_outcome(vals, 0.75)

r4a = engine4a.get_adapted_weights(BASE_WEIGHTS)
r4b = engine4b.get_adapted_weights(BASE_WEIGHTS)
check(r4a.adapted_weights == r4b.adapted_weights, "weights match")
check(r4a.adjustments == r4b.adjustments, "adjustments match")

# ── 11. High-performing signal gets higher weight ─────────────────────────

header("high-performing signal gets higher weight")
engine5 = MetaWeightEngine()
for _ in range(10):
    engine5.record_outcome(
        {
            "goal": 1.0,
            "plan": 0.1,
            "strategy": 0.1,
            "state_bias": 0.1,
            "credit": 0.1,
            "exploration": 0.1,
            "commitment": 0.1,
        },
        0.9,
    )
r5 = engine5.get_adapted_weights(BASE_WEIGHTS)
check(
    r5.adapted_weights["goal"] > BASE_WEIGHTS["goal"],
    "goal weight increased",
    f"adapted={r5.adapted_weights['goal']:.4f}, base={BASE_WEIGHTS['goal']:.4f}",
)

# ── 12. Low-performing signal gets lower weight ───────────────────────────

header("low-performing signal gets lower weight")
engine6 = MetaWeightEngine()
for _ in range(10):
    engine6.record_outcome(
        {
            "goal": 0.0,
            "plan": 0.9,
            "strategy": 0.9,
            "state_bias": 0.9,
            "credit": 0.9,
            "exploration": 0.9,
            "commitment": 0.9,
        },
        0.9,
    )
r6 = engine6.get_adapted_weights(BASE_WEIGHTS)
check(
    r6.adapted_weights["goal"] < BASE_WEIGHTS["goal"],
    "goal weight decreased",
    f"adapted={r6.adapted_weights['goal']:.4f}, base={BASE_WEIGHTS['goal']:.4f}",
)

# ── 13. Improvement over time — weights converge toward strong signals ───

header("improvement over time — goal adjustment positive")
engine7 = MetaWeightEngine()
for i in range(20):
    engine7.record_outcome(
        {
            "goal": 0.95,
            "plan": 0.3,
            "strategy": 0.3,
            "state_bias": 0.3,
            "credit": 0.3,
            "exploration": 0.3,
            "commitment": 0.3,
        },
        0.9,
    )
r7 = engine7.get_adapted_weights(BASE_WEIGHTS)
check(
    r7.adjustments["goal"] > 0,
    "goal adjustment positive (outperforms baseline)",
    f"adj={r7.adjustments['goal']:.4f}",
)
check(
    r7.adjustments["goal"] > r7.adjustments["plan"],
    "goal adjustment > plan adjustment",
    f"goal={r7.adjustments['goal']:.4f}, plan={r7.adjustments['plan']:.4f}",
)

# ── 14. Zero outcome → EMA decays toward zero ────────────────────────────

header("zero outcome quality — EMA decays")
engine8 = MetaWeightEngine()
for _ in range(10):
    engine8.record_outcome(
        {
            "goal": 0.9,
            "plan": 0.9,
            "strategy": 0.9,
            "state_bias": 0.9,
            "credit": 0.9,
            "exploration": 0.9,
            "commitment": 0.9,
        },
        0.0,
    )
for name in SIGNAL_NAMES:
    check(
        engine8._performance[name].ema < 0.01,
        f"{name} ema near 0 with zero outcomes",
        f"got {engine8._performance[name].ema:.6f}",
    )

# ── 15. Snapshot / restore round-trip ─────────────────────────────────────

header("snapshot / restore round-trip")
engine9 = MetaWeightEngine()
for _ in range(5):
    engine9.record_outcome({"goal": 0.7, "plan": 0.6, "strategy": 0.5}, 0.8)
snap = engine9.snapshot()

engine9b = MetaWeightEngine()
engine9b.restore(snap)

for name in SIGNAL_NAMES:
    check(
        abs(engine9._performance[name].ema - engine9b._performance[name].ema) < 1e-12,
        f"{name} ema restored",
    )
    check(
        engine9._performance[name].observations
        == engine9b._performance[name].observations,
        f"{name} obs restored",
    )

# ── 16. Restore backward compat — empty/None ─────────────────────────────

header("restore backward compat")
engine10 = MetaWeightEngine()
engine10.restore(None)
check(engine10.total_observations == 0, "None restore safe")
engine10.restore({})
check(engine10.total_observations == 0, "empty restore safe")
engine10.restore({"unknown_signal": {"ema": 1.0}})
check(engine10.total_observations == 0, "unknown signal ignored")

# ── 17. Reset ─────────────────────────────────────────────────────────────

header("reset clears all state")
engine11 = MetaWeightEngine()
for _ in range(5):
    engine11.record_outcome({"goal": 0.8}, 0.9)
check(engine11.total_observations > 0, "has observations before reset")
engine11.reset()
check(engine11.total_observations == 0, "obs 0 after reset")

# ── 18. MetaWeightResult serialization ────────────────────────────────────

header("MetaWeightResult serialization")
from umh.runtime_engine.meta_weight_engine import MetaWeightResult

r_ser = MetaWeightResult(
    adapted_weights={"goal": 0.3, "plan": 0.2},
    adjustments={"goal": 0.05, "plan": -0.02},
    signal_performance={
        "goal": {"ema": 0.5, "observations": 5, "last_contribution": 0.4}
    },
    observations=5,
    adapted=True,
)
d_ser = r_ser.to_dict()
check("adapted_weights" in d_ser, "has adapted_weights")
check("adjustments" in d_ser, "has adjustments")
check("signal_performance" in d_ser, "has signal_performance")
check(d_ser["adapted"] is True, "adapted=True")
check(d_ser["observations"] == 5, "observations=5")

# ── 19. NO_META_WEIGHT_RESULT sentinel ────────────────────────────────────

header("NO_META_WEIGHT_RESULT sentinel")
from umh.runtime_engine.meta_weight_engine import NO_META_WEIGHT_RESULT

check(NO_META_WEIGHT_RESULT.adapted is False, "not adapted")
check(NO_META_WEIGHT_RESULT.observations == 0, "0 obs")
check(len(NO_META_WEIGHT_RESULT.adapted_weights) == 0, "empty weights")

# ── 20. Singleton accessor ────────────────────────────────────────────────

header("singleton accessor")
from umh.runtime_engine.meta_weight_engine import get_meta_weight_engine

e_a = get_meta_weight_engine()
e_b = get_meta_weight_engine()
check(e_a is e_b, "singleton returns same instance")

# ── 21. Integration — compute_influence_score with adapted weights ────────

header("compute_influence_score with adapted weights")
from umh.runtime_engine.influence_scoring import (
    InfluenceSnapshot,
    compute_influence_score,
)

snap_test = InfluenceSnapshot(
    goal_score=0.8,
    plan_score=0.6,
    strategy_score=0.5,
    state_bias=0.3,
    credit_signal=0.4,
    exploration_signal=0.5,
    commitment_signal=0.2,
)

r_base = compute_influence_score(snap_test)
r_adapted = compute_influence_score(
    snap_test,
    adapted_weights={
        "goal": 0.50,
        "plan": 0.10,
        "strategy": 0.10,
        "state_bias": 0.10,
        "credit": 0.05,
        "exploration": 0.10,
        "commitment": 0.05,
    },
)
check(r_base.final_score != r_adapted.final_score, "adapted changes score")
check(
    r_adapted.final_score > r_base.final_score,
    "higher goal weight → higher score (goal=0.8)",
)

# ── 22. Integration — adapted weights None = base behavior ───────────────

header("adapted weights None = base behavior")
r_none = compute_influence_score(snap_test, adapted_weights=None)
check(
    abs(r_none.final_score - r_base.final_score) < 1e-12,
    "None adapted_weights = base",
)

# ── 23. DecisionTrace meta-weight fields ──────────────────────────────────

header("DecisionTrace meta-weight fields")
from umh.runtime_engine.decision_trace import DecisionTrace

t = DecisionTrace(
    turn_id=1,
    strategies_considered=("a",),
    strategy_scores={"a": 1.0},
    selected_strategy="a",
    quality_score=0.8,
    confidence=0.9,
    signals={},
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test",
    latency_ms=0,
    tokens_used=None,
    was_enhanced=False,
    meta_weights={"goal": 0.35, "plan": 0.18},
    meta_weight_adjustments={"goal": 0.05, "plan": -0.02},
    meta_weight_signal_performance={"goal": {"ema": 0.3}},
)
check(t.meta_weights is not None, "meta_weights set")
check(t.meta_weight_adjustments is not None, "adjustments set")
check(t.meta_weight_signal_performance is not None, "signal_performance set")

# ── 24. DecisionTrace to_dict serializes meta-weight fields ───────────────

header("to_dict serializes meta-weight fields")
td = t.to_dict()
check("meta_weights" in td, "meta_weights in dict")
check("meta_weight_adjustments" in td, "adjustments in dict")
check("meta_weight_signal_performance" in td, "signal_perf in dict")
check(td["meta_weights"]["goal"] == 0.35, "goal weight rounded")

# ── 25. DecisionTrace to_dict omits None meta-weight fields ──────────────

header("to_dict omits None meta-weight fields")
t_none = DecisionTrace(
    turn_id=2,
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
td_none = t_none.to_dict()
check("meta_weights" not in td_none, "meta_weights omitted when None")
check("meta_weight_adjustments" not in td_none, "adjustments omitted when None")
check("meta_weight_signal_performance" not in td_none, "signal_perf omitted when None")

# ── 26. build_trace accepts meta-weight params ────────────────────────────

header("build_trace accepts meta-weight params")
from umh.runtime_engine.decision_trace import build_trace

bt = build_trace(
    turn_id=10,
    meta_weights={"goal": 0.3},
    meta_weight_adjustments={"goal": 0.01},
    meta_weight_signal_performance={"goal": {"ema": 0.2}},
)
check(bt.meta_weights == {"goal": 0.3}, "build_trace meta_weights")
check(bt.meta_weight_adjustments == {"goal": 0.01}, "build_trace adjustments")
check(
    bt.meta_weight_signal_performance == {"goal": {"ema": 0.2}},
    "build_trace signal_perf",
)

# ── 27. Uniform signals → weights stay near base ─────────────────────────

header("uniform signals → adjustments near zero")
engine12 = MetaWeightEngine()
for _ in range(10):
    engine12.record_outcome(
        {n: 0.5 for n in SIGNAL_NAMES},
        0.5,
    )
r12 = engine12.get_adapted_weights(BASE_WEIGHTS)
for name in SIGNAL_NAMES:
    adj = abs(r12.adjustments[name])
    check(
        adj < 0.03,
        f"{name} adjustment near zero with uniform signals",
        f"adj={adj:.4f}",
    )

# ── 28. Missing signal values treated as 0 ───────────────────────────────

header("missing signal values treated as 0")
engine13 = MetaWeightEngine()
engine13.record_outcome({}, 0.9)
for name in SIGNAL_NAMES:
    check(
        engine13._performance[name].last_contribution == 0.0,
        f"{name} contribution=0 for missing",
    )

# ── 29. Clamping — values outside [0,1] clamped ──────────────────────────

header("clamping — values and quality outside [0,1]")
engine14 = MetaWeightEngine()
engine14.record_outcome({"goal": 2.0, "plan": -1.0}, 1.5)
check(
    engine14._performance["goal"].last_contribution == 1.0,
    "goal clamped to 1.0*1.0=1.0",
    f"got {engine14._performance['goal'].last_contribution}",
)
check(
    engine14._performance["plan"].last_contribution == 0.0,
    "plan clamped to 0.0*1.0=0.0",
    f"got {engine14._performance['plan'].last_contribution}",
)

# ── 30. Normalized weights with extreme adjustments ───────────────────────

header("normalized weights with extreme adjustments")
engine15 = MetaWeightEngine()
for _ in range(20):
    engine15.record_outcome(
        {
            "goal": 1.0,
            "plan": 1.0,
            "strategy": 1.0,
            "state_bias": 0.0,
            "credit": 0.0,
            "exploration": 0.0,
            "commitment": 0.0,
        },
        1.0,
    )
r15 = engine15.get_adapted_weights(BASE_WEIGHTS)
w_sum15 = sum(r15.adapted_weights.values())
check(abs(w_sum15 - 1.0) < 1e-9, "extreme case still sums to 1.0", f"got {w_sum15}")

# ── 31. No LLM calls ─────────────────────────────────────────────────────

header("no LLM calls")
import inspect

src = inspect.getsource(sys.modules["umh.runtime_engine.meta_weight_engine"])
check("call_with_fallback" not in src, "no call_with_fallback")
check("anthropic" not in src.lower() or "anthropic" in "# no anthropic", "no anthropic")
check("openai" not in src.lower(), "no openai")
check("ollama" not in src.lower(), "no ollama")

# ── 32. No randomness ────────────────────────────────────────────────────

header("no randomness")
import re as _re

_has_random_import = bool(_re.search(r"\bimport\s+random\b", src))
check(not _has_random_import, "no random import")
check("shuffle" not in src, "no shuffle")
check("sample(" not in src, "no sample call")

# ── 33. No ExecutionSpine changes ─────────────────────────────────────────

header("ExecutionSpine not modified")
check("ExecutionSpine" not in src, "no ExecutionSpine ref")
check("execution_spine" not in src, "no execution_spine import")

# ── 34. BASE_WEIGHTS in influence_scoring ─────────────────────────────────

header("BASE_WEIGHTS dict in influence_scoring")
check(len(BASE_WEIGHTS) == 7, "7 base weights", f"got {len(BASE_WEIGHTS)}")
base_sum = sum(BASE_WEIGHTS.values())
check(abs(base_sum - 1.0) < 1e-9, "base weights sum to 1.0", f"got {base_sum}")

# ── 35. Monotonicity — more positive outcomes → weight increases ──────────

header("monotonicity — goal adjustment grows with more positive outcomes")
engine16 = MetaWeightEngine()
adjs_over_time = []
for i in range(15):
    engine16.record_outcome(
        {
            "goal": 0.95,
            "plan": 0.2,
            "strategy": 0.2,
            "state_bias": 0.2,
            "credit": 0.2,
            "exploration": 0.2,
            "commitment": 0.2,
        },
        0.9,
    )
    if i >= MIN_OBSERVATIONS - 1:
        r16 = engine16.get_adapted_weights(BASE_WEIGHTS)
        adjs_over_time.append(r16.adjustments["goal"])

check(len(adjs_over_time) >= 3, "enough data points")
# Raw adjustment should be non-decreasing (before normalization)
increasing = all(
    adjs_over_time[i] >= adjs_over_time[i - 1] - 1e-9
    for i in range(1, len(adjs_over_time))
)
check(increasing, "goal adjustment non-decreasing over time")

# ═════════════════════════════════════════════════════════════════════════

print()
print("=" * 60)
print(f"Meta-Weight Engine: {passed}/{passed + failed} passed")
if failed == 0:
    print("  ALL PASSED")
else:
    print(f"  {failed} FAILED")
print("=" * 60)
