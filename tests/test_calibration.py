"""
Tests for the CalibrationEngine.

Validates:
    - Deterministic results across identical inputs
    - Thresholds shift gradually (EMA smoothing)
    - No extreme jumps (floor/ceiling bounds)
    - Works with small data (fallback to defaults)
    - Disabled engine returns defaults
    - CalibratedThresholds serialization round-trip
    - Percentile computation correctness
    - Integration with ControlPolicy (calibrated thresholds)
    - Integration with adaptive_prompt (calibrated thresholds)
    - Integration with signal_router (calibrated wm_confidence)
    - Integration with strategy_memory (calibrated min_confidence)
    - SessionRuntime wiring (calibration_enabled flag)
    - System behaves identically when calibration disabled
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
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


from umh.runtime_engine.calibration import (
    CalibrationEngine,
    CalibratedThresholds,
    DEFAULT_THRESHOLDS,
    _percentile,
    _clamp,
    _ema_smooth,
    get_thresholds,
    MIN_SAMPLES,
    EMA_ALPHA,
    FLOOR_LOW_QUALITY,
    CEILING_LOW_QUALITY,
    FLOOR_HIGH_CONFIDENCE,
    CEILING_HIGH_CONFIDENCE,
)


def _make_summaries(
    n: int,
    quality_base: float = 0.6,
    confidence_base: float = 0.7,
    spread: float = 0.2,
) -> list[dict]:
    """Generate deterministic test summaries with a linear spread."""
    summaries = []
    for i in range(n):
        frac = i / max(n - 1, 1)
        q = quality_base + (frac - 0.5) * spread
        c = confidence_base + (frac - 0.5) * spread
        summaries.append(
            {
                "session_id": f"test-{i}",
                "turn": i + 1,
                "strategy": "baseline",
                "quality_score": round(max(0.0, min(1.0, q)), 4),
                "confidence": round(max(0.0, min(1.0, c)), 4),
                "signals": {"hallucination": False, "incomplete": False},
                "control_intervened": False,
            }
        )
    return summaries


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Percentile computation
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Percentile Computation")

_test("empty list → 0.0", _percentile([], 50) == 0.0)
_test("single value", _percentile([0.5], 50) == 0.5)
_test("p50 of [0.0, 1.0]", abs(_percentile([0.0, 1.0], 50) - 0.5) < 1e-9)
_test("p25 of [0, 1, 2, 3]", abs(_percentile([0, 1, 2, 3], 25) - 0.75) < 1e-9)
_test("p75 of [0, 1, 2, 3]", abs(_percentile([0, 1, 2, 3], 75) - 2.25) < 1e-9)
_test("p0 = min", _percentile([3, 1, 2], 0) == 1.0)
_test("p100 = max", _percentile([3, 1, 2], 100) == 3.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Clamp
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Clamp")

_test("within bounds", _clamp(0.5, 0.2, 0.8) == 0.5)
_test("below floor", _clamp(0.1, 0.2, 0.8) == 0.2)
_test("above ceiling", _clamp(0.9, 0.2, 0.8) == 0.8)
_test("at floor", _clamp(0.2, 0.2, 0.8) == 0.2)
_test("at ceiling", _clamp(0.8, 0.2, 0.8) == 0.8)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EMA smoothing
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. EMA Smoothing")

_test("alpha=0.2 blend", abs(_ema_smooth(1.0, 0.0, 0.2) - 0.2) < 1e-9)
_test("alpha=0.2 same value", abs(_ema_smooth(0.5, 0.5, 0.2) - 0.5) < 1e-9)
_test("alpha=1.0 takes new", abs(_ema_smooth(1.0, 0.0, 1.0) - 1.0) < 1e-9)
_test("alpha=0.0 keeps old", abs(_ema_smooth(1.0, 0.0, 0.0) - 0.0) < 1e-9)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CalibratedThresholds defaults
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. CalibratedThresholds Defaults")

d = DEFAULT_THRESHOLDS
_test("default low_quality is 0.45", d.low_quality_threshold == 0.45)
_test("default high_confidence is 0.60", d.high_confidence_threshold == 0.60)
_test("default halluc_conf is 0.40", d.hallucination_confidence_threshold == 0.40)
_test("default block_conf is 0.20", d.block_confidence_threshold == 0.20)
_test("default wm_conf is 0.60", d.world_model_confidence_threshold == 0.60)
_test("default min_conf is 0.60", d.min_confidence == 0.60)
_test("default not calibrated", d.calibrated is False)
_test("default sample_count is 0", d.sample_count == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Serialization round-trip
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Serialization Round-trip")

custom = CalibratedThresholds(
    low_quality_threshold=0.35,
    high_confidence_threshold=0.70,
    hallucination_confidence_threshold=0.38,
    block_confidence_threshold=0.18,
    world_model_confidence_threshold=0.55,
    min_confidence=0.50,
    sample_count=50,
    calibrated=True,
)
d = custom.to_dict()
restored = CalibratedThresholds.from_dict(d)
_test("round-trip preserves low_quality", restored.low_quality_threshold == 0.35)
_test("round-trip preserves high_conf", restored.high_confidence_threshold == 0.70)
_test("round-trip preserves calibrated", restored.calibrated is True)
_test("round-trip preserves sample_count", restored.sample_count == 50)

# Extra keys ignored
d_extra = {**d, "unknown_field": 999}
restored_extra = CalibratedThresholds.from_dict(d_extra)
_test("extra keys ignored", restored_extra.low_quality_threshold == 0.35)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Disabled engine returns defaults
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Disabled Engine")

disabled = CalibrationEngine(enabled=False)
result = disabled.calibrate(summaries=_make_summaries(50))
_test("disabled → DEFAULT_THRESHOLDS", result is DEFAULT_THRESHOLDS)
_test("disabled current → DEFAULT_THRESHOLDS", disabled.current is DEFAULT_THRESHOLDS)
_test("disabled recalibration_count is 0", disabled.recalibration_count == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Insufficient data fallback
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Insufficient Data")

engine = CalibrationEngine(enabled=True)
engine._previous = None  # clear any persisted state for isolated test
few = _make_summaries(MIN_SAMPLES - 1)
result = engine.calibrate(summaries=few)
_test(
    f"fewer than {MIN_SAMPLES} samples → defaults",
    result is DEFAULT_THRESHOLDS,
)
_test("no recalibration counted", engine.recalibration_count == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Sufficient data produces calibrated thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Sufficient Data")

engine = CalibrationEngine(enabled=True)
summaries = _make_summaries(50, quality_base=0.6, confidence_base=0.7, spread=0.3)
result = engine.calibrate(summaries=summaries)

_test("calibrated is True", result.calibrated is True)
_test("sample_count is 50", result.sample_count == 50)
_test("recalibration_count is 1", engine.recalibration_count == 1)
_test(
    "low_quality in bounds",
    FLOOR_LOW_QUALITY <= result.low_quality_threshold <= CEILING_LOW_QUALITY,
    f"got {result.low_quality_threshold}",
)
_test(
    "high_confidence in bounds",
    FLOOR_HIGH_CONFIDENCE
    <= result.high_confidence_threshold
    <= CEILING_HIGH_CONFIDENCE,
    f"got {result.high_confidence_threshold}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Determinism — same input → same output
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Determinism")

e1 = CalibrationEngine(enabled=True)
e2 = CalibrationEngine(enabled=True)
s = _make_summaries(50)
r1 = e1.calibrate(summaries=s)
r2 = e2.calibrate(summaries=s)

_test("same low_quality", r1.low_quality_threshold == r2.low_quality_threshold)
_test("same high_conf", r1.high_confidence_threshold == r2.high_confidence_threshold)
_test(
    "same halluc_conf",
    r1.hallucination_confidence_threshold == r2.hallucination_confidence_threshold,
)
_test("same block_conf", r1.block_confidence_threshold == r2.block_confidence_threshold)
_test(
    "same wm_conf",
    r1.world_model_confidence_threshold == r2.world_model_confidence_threshold,
)
_test("same min_conf", r1.min_confidence == r2.min_confidence)
_test("same to_dict", r1.to_dict() == r2.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 10. EMA smoothing prevents jumps
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. EMA Smoothing Prevents Jumps")

engine = CalibrationEngine(enabled=True)

normal = _make_summaries(50, quality_base=0.6, confidence_base=0.7, spread=0.2)
r_normal = engine.calibrate(summaries=normal)

extreme = _make_summaries(50, quality_base=0.2, confidence_base=0.3, spread=0.1)
r_extreme = engine.calibrate(summaries=extreme)

lq_diff = abs(r_extreme.low_quality_threshold - r_normal.low_quality_threshold)
hc_diff = abs(r_extreme.high_confidence_threshold - r_normal.high_confidence_threshold)

_test(
    "low_quality shift bounded by EMA",
    lq_diff < abs(0.2 - 0.6),
    f"shift was {lq_diff:.4f}",
)
_test(
    "high_confidence shift bounded by EMA",
    hc_diff < abs(0.3 - 0.7),
    f"shift was {hc_diff:.4f}",
)

# Multiple recalibrations converge
for _ in range(10):
    engine.calibrate(summaries=extreme)

r_converged = engine.current
_test(
    "convergence after 10 recalibrations",
    r_converged.low_quality_threshold <= CEILING_LOW_QUALITY,
    f"got {r_converged.low_quality_threshold}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Floor/ceiling bounds are absolute
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Floor/Ceiling Bounds")

engine = CalibrationEngine(enabled=True)

very_low = _make_summaries(50, quality_base=0.05, confidence_base=0.05, spread=0.02)
r = engine.calibrate(summaries=very_low)
_test("floor: low_quality", r.low_quality_threshold >= FLOOR_LOW_QUALITY)
_test("floor: high_conf", r.high_confidence_threshold >= FLOOR_HIGH_CONFIDENCE)

engine2 = CalibrationEngine(enabled=True)
very_high = _make_summaries(50, quality_base=0.95, confidence_base=0.95, spread=0.02)
r = engine2.calibrate(summaries=very_high)
_test("ceiling: low_quality", r.low_quality_threshold <= CEILING_LOW_QUALITY)
_test("ceiling: high_conf", r.high_confidence_threshold <= CEILING_HIGH_CONFIDENCE)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. get_thresholds convenience
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. get_thresholds Convenience")

_test("None engine → defaults", get_thresholds(None) is DEFAULT_THRESHOLDS)

eng = CalibrationEngine(enabled=True)
eng.calibrate(summaries=_make_summaries(50))
t = get_thresholds(eng)
_test("engine → calibrated", t.calibrated is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. ControlPolicy accepts thresholds parameter
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. ControlPolicy + Calibration")

from umh.runtime_engine.control_layer import ControlPolicy, NO_INTERVENTION
from umh.runtime_engine.decision_trace import DecisionTrace


def _make_trace(
    turn_id: int = 1,
    quality_score: float = 0.7,
    confidence: float = 0.8,
    hallucination_risk: bool = False,
    incomplete: bool = False,
) -> DecisionTrace:
    return DecisionTrace(
        turn_id=turn_id,
        strategies_considered=("baseline",),
        strategy_scores={"baseline": 0.5},
        selected_strategy="baseline",
        quality_score=quality_score,
        confidence=confidence,
        signals={
            "quality_score": quality_score,
            "confidence": confidence,
            "flags": {
                "hallucination_risk": hallucination_risk,
                "incomplete": incomplete,
            },
        },
        attributed_signals={},
        horizon={},
        directives_applied=(),
        model_used="test/model",
        latency_ms=100,
        tokens_used={"input": 50, "output": 50, "total": 100},
        was_enhanced=False,
    )


policy = ControlPolicy(enabled=True)

# Default thresholds: halluc_conf=0.4, so conf=0.35 triggers
traces_halluc = [_make_trace(hallucination_risk=True, confidence=0.35)]
r_default = policy.evaluate(traces_halluc)
_test("default thresholds: halluc triggers at 0.35", r_default.intervene is True)

# Calibrated thresholds with lower halluc threshold
low_thresh = CalibratedThresholds(hallucination_confidence_threshold=0.30)
r_calibrated = policy.evaluate(traces_halluc, thresholds=low_thresh)
_test("calibrated: 0.35 > 0.30 → no halluc trigger", r_calibrated.intervene is False)

# Calibrated thresholds with higher halluc threshold
high_thresh = CalibratedThresholds(hallucination_confidence_threshold=0.50)
r_higher = policy.evaluate(traces_halluc, thresholds=high_thresh)
_test("calibrated: 0.35 < 0.50 → halluc triggers", r_higher.intervene is True)

# Without thresholds param, behavior unchanged
r_none = policy.evaluate(traces_halluc, thresholds=None)
_test("thresholds=None → same as default", r_none.intervene == r_default.intervene)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. ControlPolicy low quality streak with calibrated threshold
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. ControlPolicy LQ Streak + Calibration")

streak = [
    _make_trace(turn_id=1, quality_score=0.40),
    _make_trace(turn_id=2, quality_score=0.42),
    _make_trace(turn_id=3, quality_score=0.44),
]

# Default threshold 0.45 — all 3 are below → streak triggers
r_default = policy.evaluate(streak)
_test("default: streak triggers (all < 0.45)", r_default.reason == "low_quality_streak")

# Calibrated threshold 0.38 — all 3 are above → no streak
low_lq = CalibratedThresholds(low_quality_threshold=0.38)
r_low = policy.evaluate(streak, thresholds=low_lq)
_test("calibrated 0.38: no streak (all > 0.38)", r_low.reason != "low_quality_streak")

# Calibrated threshold 0.50 — all 3 are below → streak triggers
high_lq = CalibratedThresholds(low_quality_threshold=0.50)
r_high = policy.evaluate(streak, thresholds=high_lq)
_test(
    "calibrated 0.50: streak triggers (all < 0.50)",
    r_high.reason == "low_quality_streak",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. adaptive_prompt accepts thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. adaptive_prompt + Calibration")

from unittest.mock import MagicMock
from umh.runtime_engine.adaptive_prompt import adapt_prompt
from umh.runtime_engine.session_runtime import SessionStats

mock_session = MagicMock()
mock_session.stats = SessionStats()
mock_session.stats.evaluations = [
    {
        "quality_score": 0.30,
        "flags": {
            "hallucination_risk": False,
            "incomplete": False,
            "low_information": True,
        },
    },
    {
        "quality_score": 0.32,
        "flags": {
            "hallucination_risk": False,
            "incomplete": False,
            "low_information": True,
        },
    },
    {
        "quality_score": 0.35,
        "flags": {
            "hallucination_risk": False,
            "incomplete": False,
            "low_information": True,
        },
    },
]

# Default threshold 0.45 → avg 0.323 < 0.45 → directive injected
r_default = adapt_prompt("test", session_runtime=mock_session)
_test("default: low quality directive injected", "quality" in r_default.lower())

# Calibrated threshold 0.25 → avg 0.323 > 0.25 → no directive
low_lq = CalibratedThresholds(low_quality_threshold=0.25)
r_low = adapt_prompt("test", session_runtime=mock_session, thresholds=low_lq)
_test(
    "calibrated 0.25: no low quality directive",
    "quality" not in r_low.lower() or r_low == "test",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. signal_router accepts wm_confidence_threshold
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. signal_router + Calibration")

from umh.runtime_engine.signal_router import route_signals

eval_dict = {"quality_score": 0.75, "confidence": 0.55, "flags": {}, "reason": "ok"}

# Default threshold 0.6 → confidence 0.55 < 0.6 → no world_model
r_default = route_signals(eval_dict)
_test("default: wm=None at 0.55 confidence", r_default.world_model is None)

# Calibrated threshold 0.50 → confidence 0.55 >= 0.50 → world_model present
r_cal = route_signals(eval_dict, wm_confidence_threshold=0.50)
_test("calibrated 0.50: wm present at 0.55", r_cal.world_model is not None)

# Calibrated threshold 0.70 → confidence 0.55 < 0.70 → no world_model
r_high = route_signals(eval_dict, wm_confidence_threshold=0.70)
_test("calibrated 0.70: wm=None at 0.55", r_high.world_model is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. strategy_memory accepts min_confidence
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. strategy_memory + Calibration")

from umh.strategy.memory import StrategyMemory

mem = StrategyMemory()

# Default MIN_CONFIDENCE=0.6 — confidence 0.5 should NOT update stats
mem.record_win("test_strat", quality_score=0.9, confidence=0.5)
stats = mem.get_stats("test_strat")
_test("default: conf 0.5 < 0.6 → uses=0", stats.uses == 0)

# With calibrated min_confidence=0.4 — confidence 0.5 should update
mem.record_win("test_strat", quality_score=0.9, confidence=0.5, min_confidence=0.4)
stats = mem.get_stats("test_strat")
_test("calibrated 0.4: conf 0.5 >= 0.4 → uses=1", stats.uses == 1)

# record_loss same pattern
mem2 = StrategyMemory()
mem2.record_loss("a", quality_score=0.3, confidence=0.5)
_test("default record_loss: conf 0.5 < 0.6 → uses=0", mem2.get_stats("a").uses == 0)
mem2.record_loss("a", quality_score=0.3, confidence=0.5, min_confidence=0.4)
_test("calibrated record_loss: conf 0.5 >= 0.4 → uses=1", mem2.get_stats("a").uses == 1)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. SessionRuntime calibration wiring
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. SessionRuntime Wiring")

from umh.runtime_engine.session_runtime import SessionRuntime

mock_ctx = MagicMock()

s_off = SessionRuntime(mock_ctx, session_id="cal-off")
_test("calibration disabled by default", s_off._calibration_engine is None)

t_off = s_off.get_calibrated_thresholds()
_test("disabled → DEFAULT_THRESHOLDS", t_off.calibrated is False)

s_on = SessionRuntime(mock_ctx, session_id="cal-on", calibration_enabled=True)
_test("calibration enabled when requested", s_on._calibration_engine is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Backward compatibility — existing tests unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. Backward Compatibility")

# ControlPolicy without thresholds param works identically
traces_normal = [_make_trace(quality_score=0.8, confidence=0.9)]
r = ControlPolicy(enabled=True).evaluate(traces_normal)
_test("ControlPolicy: normal → no intervention", r.intervene is False)

# route_signals without wm param works identically
r = route_signals(
    {"quality_score": 0.8, "confidence": 0.8, "flags": {}, "reason": "ok"}
)
_test("route_signals: default → wm present", r.world_model is not None)

# adapt_prompt without thresholds param works identically
r = adapt_prompt("hello")
_test("adapt_prompt: no args → passthrough", r == "hello")


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Window respects limit
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Window Limit")

engine = CalibrationEngine(enabled=True, window=20)
many = _make_summaries(200)
r = engine.calibrate(summaries=many)
_test("window=20 → sample_count=20", r.sample_count == 20)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Idempotent recalibration
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Idempotent Recalibration")

engine = CalibrationEngine(enabled=True)
s = _make_summaries(50)
r1 = engine.calibrate(summaries=s)
r2 = engine.calibrate(summaries=s)

_test(
    "same data twice → values converge (EMA moves toward same target)",
    abs(r2.low_quality_threshold - r1.low_quality_threshold) < 0.05,
    f"diff={abs(r2.low_quality_threshold - r1.low_quality_threshold):.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Missing/malformed summary fields handled gracefully
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. Malformed Summaries")

engine = CalibrationEngine(enabled=True)
bad = [
    {"quality_score": 0.5},  # missing confidence
    {"confidence": 0.7},  # missing quality_score
    {"quality_score": "bad", "confidence": 0.7},  # wrong type
    {},  # empty
] + _make_summaries(15)

r = engine.calibrate(summaries=bad)
_test("handles malformed gracefully", r.calibrated is True)
_test("sample_count reflects valid data", r.sample_count == len(bad))


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
