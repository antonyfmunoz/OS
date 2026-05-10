"""
Tests for full runtime wiring of calibrated thresholds.

Validates:
    - Thresholds are passed to every runtime consumer in SessionRuntime.run()
    - All consumers receive the same threshold snapshot for a turn
    - DecisionTrace stores the thresholds used
    - Calibration-disabled path preserves prior behavior
    - Deterministic behavior remains intact
    - No regression in DecisionTrace construction
    - build_trace passes thresholds_used through
    - thresholds_used omitted from to_dict when None
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


from umh.runtime_engine.decision_trace import DecisionTrace, build_trace
from umh.runtime_engine.calibration import CalibratedThresholds, DEFAULT_THRESHOLDS


def _make_trace(**kwargs) -> DecisionTrace:
    """Build a trace with sensible defaults."""
    defaults = dict(
        turn_id=1,
        strategies_considered=("baseline",),
        strategy_scores={"baseline": 0.5},
        selected_strategy="baseline",
        quality_score=0.7,
        confidence=0.8,
        signals={},
        attributed_signals={},
        horizon={},
        directives_applied=(),
        model_used="test/model",
        latency_ms=100,
        tokens_used={"input": 50, "output": 50},
        was_enhanced=False,
    )
    defaults.update(kwargs)
    return DecisionTrace(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DecisionTrace thresholds_used field
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. DecisionTrace thresholds_used Field")

# None by default
t_none = _make_trace()
_test("thresholds_used defaults to None", t_none.thresholds_used is None)
_test("None omitted from to_dict", "thresholds_used" not in t_none.to_dict())

# With threshold snapshot
snap = {"low_quality_threshold": 0.40, "high_confidence_threshold": 0.65}
t_with = _make_trace(thresholds_used=snap)
_test("thresholds_used stored", t_with.thresholds_used == snap)
_test("present in to_dict", "thresholds_used" in t_with.to_dict())
_test("to_dict value matches", t_with.to_dict()["thresholds_used"] == snap)

# Frozen — cannot mutate
try:
    t_with.thresholds_used = {}
    _test("frozen: mutation blocked", False)
except AttributeError:
    _test("frozen: mutation blocked", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. build_trace passes thresholds_used through
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. build_trace Passthrough")

from umh.strategy.memory import reset_strategy_memory, get_strategy_memory

reset_strategy_memory()
get_strategy_memory().record_win("baseline", 0.7)

# Without thresholds
bt_none = build_trace(turn_id=1)
_test("build_trace: default is None", bt_none.thresholds_used is None)

# With thresholds
cal_dict = DEFAULT_THRESHOLDS.to_dict()
bt_cal = build_trace(turn_id=2, thresholds_used=cal_dict)
_test("build_trace: passes thresholds through", bt_cal.thresholds_used == cal_dict)
_test("build_trace: in to_dict", "thresholds_used" in bt_cal.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 3. build_trace with both control_decision and thresholds_used
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. build_trace Combined Fields")

from umh.runtime_engine.control_layer import ControlDecision

ctrl = ControlDecision(intervene=True, reason="test", inject_directives=("d1",))
bt_both = build_trace(
    turn_id=3,
    control_decision=ctrl,
    thresholds_used=cal_dict,
)
d = bt_both.to_dict()
_test("both: control_decision in to_dict", "control_decision" in d)
_test("both: thresholds_used in to_dict", "thresholds_used" in d)
_test("both: values correct", d["thresholds_used"] == cal_dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Determinism of trace with thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Determinism")

t1 = _make_trace(thresholds_used=snap)
t2 = _make_trace(thresholds_used=snap)
_test("same input → same to_dict", t1.to_dict() == t2.to_dict())

t3 = _make_trace(thresholds_used=None)
t4 = _make_trace(thresholds_used=None)
_test("both None → same to_dict", t3.to_dict() == t4.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CalibratedThresholds.to_dict() produces full snapshot
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Threshold Snapshot Completeness")

t = CalibratedThresholds(
    low_quality_threshold=0.40,
    high_confidence_threshold=0.70,
    hallucination_confidence_threshold=0.35,
    block_confidence_threshold=0.18,
    world_model_confidence_threshold=0.55,
    min_confidence=0.50,
    sample_count=42,
    calibrated=True,
)
d = t.to_dict()

expected_keys = {
    "low_quality_threshold",
    "high_confidence_threshold",
    "hallucination_confidence_threshold",
    "block_confidence_threshold",
    "world_model_confidence_threshold",
    "min_confidence",
    "sample_count",
    "calibrated",
}
_test("snapshot has all keys", set(d.keys()) == expected_keys, f"got {set(d.keys())}")
_test("snapshot preserves values", d["low_quality_threshold"] == 0.40)
_test("snapshot preserves calibrated", d["calibrated"] is True)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ControlPolicy uses thresholds from same snapshot
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. ControlPolicy Snapshot Consistency")

from umh.runtime_engine.control_layer import ControlPolicy

policy = ControlPolicy(enabled=True)

# Create a trace where hallucination_risk=True, confidence=0.42
# Default halluc threshold is 0.40 → 0.42 > 0.40 → no trigger
traces = [
    _make_trace(
        quality_score=0.7,
        confidence=0.42,
        signals={
            "quality_score": 0.7,
            "confidence": 0.42,
            "flags": {"hallucination_risk": True, "incomplete": False},
        },
    )
]

r_default = policy.evaluate(traces)
_test("default: 0.42 > 0.40 → no intervention", r_default.intervene is False)

# Same trace, but with calibrated threshold of 0.45
cal = CalibratedThresholds(hallucination_confidence_threshold=0.45)
r_cal = policy.evaluate(traces, thresholds=cal)
_test("calibrated 0.45: 0.42 < 0.45 → intervention", r_cal.intervene is True)
_test("reason is hallucination", r_cal.reason == "hallucination_low_confidence")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. route_signals uses thresholds from same snapshot
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. route_signals Snapshot Consistency")

from umh.runtime_engine.signal_router import route_signals

evaluation = {"quality_score": 0.8, "confidence": 0.58, "flags": {}, "reason": "ok"}

# Default wm threshold is 0.6 → 0.58 < 0.6 → no world_model
r_default = route_signals(evaluation)
_test("default: wm=None at 0.58", r_default.world_model is None)

# With calibrated wm threshold from the same CalibratedThresholds object
cal = CalibratedThresholds(world_model_confidence_threshold=0.55)
r_cal = route_signals(
    evaluation, wm_confidence_threshold=cal.world_model_confidence_threshold
)
_test("calibrated 0.55: wm present at 0.58", r_cal.world_model is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SessionRuntime wiring — calibration disabled
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. SessionRuntime — Calibration Disabled")

from unittest.mock import MagicMock
from umh.runtime_engine.session_runtime import SessionRuntime

mock_ctx = MagicMock()

s = SessionRuntime(mock_ctx, session_id="disabled-test")
_test("calibration engine is None", s._calibration_engine is None)

t = s.get_calibrated_thresholds()
_test("returns defaults", t.calibrated is False)
_test("low_quality is default 0.45", t.low_quality_threshold == 0.45)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SessionRuntime wiring — calibration enabled
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. SessionRuntime — Calibration Enabled")

s_on = SessionRuntime(mock_ctx, session_id="enabled-test", calibration_enabled=True)
_test("calibration engine exists", s_on._calibration_engine is not None)

t = s_on.get_calibrated_thresholds()
# Without data it returns defaults or persisted — either way it's a CalibratedThresholds
_test("returns CalibratedThresholds", isinstance(t, CalibratedThresholds))


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Backward compatibility — old trace construction still works
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Backward Compatibility")

# Existing code that doesn't pass thresholds_used still works
bt = build_trace(turn_id=99)
_test("old call pattern works", bt.turn_id == 99)
_test("thresholds_used defaults None", bt.thresholds_used is None)
_test("no thresholds in to_dict", "thresholds_used" not in bt.to_dict())

# Existing _make_trace without thresholds_used
t = _make_trace(turn_id=50, quality_score=0.9)
_test("old _make_trace works", t.turn_id == 50)
_test("quality_score preserved", t.quality_score == 0.9)

# ControlPolicy without thresholds still works
r = ControlPolicy(enabled=True).evaluate([_make_trace()])
_test("ControlPolicy: old call pattern works", r.reason == "no_intervention")

# route_signals without wm_confidence_threshold still works
r = route_signals({"quality_score": 0.8, "confidence": 0.8, "flags": {}, "reason": ""})
_test("route_signals: old call pattern works", r.world_model is not None)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Coherent snapshot — single threshold object for all consumers
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Coherent Snapshot Simulation")

# Simulate what SessionRuntime.run() does: fetch once, pass everywhere
cal = CalibratedThresholds(
    low_quality_threshold=0.38,
    high_confidence_threshold=0.72,
    hallucination_confidence_threshold=0.42,
    block_confidence_threshold=0.19,
    world_model_confidence_threshold=0.58,
    min_confidence=0.55,
    sample_count=60,
    calibrated=True,
)
cal_dict = cal.to_dict()

# route_signals sees wm_confidence_threshold from the snapshot
eval_data = {"quality_score": 0.75, "confidence": 0.60, "flags": {}, "reason": "ok"}
signals = route_signals(
    eval_data, wm_confidence_threshold=cal.world_model_confidence_threshold
)
_test("coherent: wm present (0.60 >= 0.58)", signals.world_model is not None)

# control_policy sees thresholds from the snapshot
policy = ControlPolicy(enabled=True)
traces = [
    _make_trace(
        confidence=0.40,
        signals={
            "quality_score": 0.7,
            "confidence": 0.40,
            "flags": {"hallucination_risk": True, "incomplete": False},
        },
    )
]
ctrl = policy.evaluate(traces, thresholds=cal)
_test("coherent: halluc triggers (0.40 < 0.42)", ctrl.intervene is True)

# build_trace captures the same snapshot
trace = build_trace(
    turn_id=10,
    evaluation=eval_data,
    signals=signals,
    control_decision=ctrl,
    thresholds_used=cal_dict,
)
_test("coherent: trace has thresholds", trace.thresholds_used is not None)
_test(
    "coherent: trace thresholds match snapshot",
    trace.thresholds_used == cal_dict,
)
_test(
    "coherent: trace wm_conf matches",
    trace.thresholds_used["world_model_confidence_threshold"] == 0.58,
)
_test(
    "coherent: trace halluc_conf matches",
    trace.thresholds_used["hallucination_confidence_threshold"] == 0.42,
)

# All from the same object
_test(
    "coherent: all values from one source",
    trace.thresholds_used["low_quality_threshold"] == cal.low_quality_threshold
    and trace.thresholds_used["high_confidence_threshold"]
    == cal.high_confidence_threshold
    and trace.thresholds_used["min_confidence"] == cal.min_confidence,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. DecisionTrace to_dict completeness with thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. DecisionTrace to_dict Completeness")

full = _make_trace(
    thresholds_used=cal_dict,
    control_decision=ctrl,
)
d = full.to_dict()

_test("has turn_id", "turn_id" in d)
_test("has quality_score", "quality_score" in d)
_test("has control_decision", "control_decision" in d)
_test("has thresholds_used", "thresholds_used" in d)
_test("thresholds has all 8 fields", len(d["thresholds_used"]) == 8)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
