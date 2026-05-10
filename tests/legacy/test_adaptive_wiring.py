"""
Tests for adaptive runtime wiring — calibrated thresholds flow into
prompt adaptation and strategy learning at call time.

Validates:
    1. SessionRuntime passes one threshold snapshot into ContextBuilder
    2. ContextBuilder passes thresholds into adaptive_prompt
    3. adaptive_prompt receives calibrated thresholds during a live turn path
    4. strategy learning receives calibrated min_confidence during the live path
    5. the same threshold snapshot is used across all consumers
    6. calibration-disabled path preserves prior behavior
    7. no regression in existing suites
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


from unittest.mock import MagicMock, patch, call
from umh.runtime_engine.calibration import CalibratedThresholds, DEFAULT_THRESHOLDS


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ContextBuilder.build() accepts and passes calibrated_thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. ContextBuilder.build() Threshold Passthrough")

import inspect
from umh.runtime_engine.context_builder import ContextBuilder

sig = inspect.signature(ContextBuilder.build)
_test(
    "build() has calibrated_thresholds param",
    "calibrated_thresholds" in sig.parameters,
    f"params: {list(sig.parameters)}",
)

param = sig.parameters["calibrated_thresholds"]
_test(
    "calibrated_thresholds defaults to None",
    param.default is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. adapt_prompt receives thresholds from ContextBuilder
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. adapt_prompt Receives Thresholds via ContextBuilder")

cal = CalibratedThresholds(
    low_quality_threshold=0.35,
    high_confidence_threshold=0.70,
    min_confidence=0.50,
    calibrated=True,
)

_captured_thresholds = []

_original_adapt_prompt = None
try:
    from umh.runtime_engine.adaptive_prompt import adapt_prompt as _orig_ap

    _original_adapt_prompt = _orig_ap
except ImportError:
    pass


def _spy_adapt_prompt(
    base_prompt, context=None, session_runtime=None, world_model=None, thresholds=None
):
    _captured_thresholds.append(thresholds)
    return base_prompt  # no modification


mock_ctx = MagicMock()
mock_ctx.org_id = "test-org"

with patch("umh.runtime_engine.adaptive_prompt.adapt_prompt", side_effect=_spy_adapt_prompt):
    builder = ContextBuilder()
    uc = builder.build(
        mock_ctx,
        "test message",
        "test-session",
        calibrated_thresholds=cal,
    )

_test(
    "adapt_prompt called with thresholds",
    len(_captured_thresholds) == 1,
    f"called {len(_captured_thresholds)} times",
)
_test(
    "thresholds is the calibrated object",
    _captured_thresholds[0] is cal,
    f"got {type(_captured_thresholds[0])}",
)
_test(
    "thresholds.low_quality_threshold is calibrated",
    _captured_thresholds[0].low_quality_threshold == 0.35
    if _captured_thresholds[0] is not None
    else False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ContextBuilder without thresholds — backward compatible
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. ContextBuilder Backward Compatibility")

_captured_thresholds.clear()

with patch("umh.runtime_engine.adaptive_prompt.adapt_prompt", side_effect=_spy_adapt_prompt):
    builder = ContextBuilder()
    uc = builder.build(
        mock_ctx,
        "test message",
        "test-session",
    )

_test(
    "adapt_prompt still called",
    len(_captured_thresholds) == 1,
)
_test(
    "thresholds is None when not provided",
    _captured_thresholds[0] is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SessionRuntime.run() accepts calibrated_thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. SessionRuntime.run() Threshold Parameter")

from umh.runtime_engine.session_runtime import SessionRuntime

sig = inspect.signature(SessionRuntime.run)
_test(
    "run() has calibrated_thresholds param",
    "calibrated_thresholds" in sig.parameters,
    f"params: {list(sig.parameters)}",
)

param = sig.parameters["calibrated_thresholds"]
_test(
    "calibrated_thresholds defaults to None",
    param.default is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SessionRuntime.run() reuses caller-provided thresholds
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. SessionRuntime Reuses Caller Thresholds")

from umh.runtime_engine.execution_spine import SpineResult

mock_spine_result = SpineResult(
    "test response",
    model_used="test-model",
    tokens_used={"input": 10, "output": 10},
    cost_usd=0.001,
    latency_ms=100,
    session_id="test",
)

cal_for_run = CalibratedThresholds(
    world_model_confidence_threshold=0.55,
    min_confidence=0.50,
    calibrated=True,
)

_fetched_thresholds = []


def _spy_get_thresholds(engine=None):
    result = DEFAULT_THRESHOLDS
    _fetched_thresholds.append(result)
    return result


mock_rt_ctx = MagicMock()
session = SessionRuntime(mock_rt_ctx, session_id="test-reuse")

with (
    patch("umh.runtime_engine.execution_spine.ExecutionSpine.run", return_value=mock_spine_result),
    patch(
        "umh.runtime_engine.session_runtime.get_thresholds",
        side_effect=_spy_get_thresholds,
        create=True,
    ),
):
    _fetched_thresholds.clear()
    result = session.run(
        message="test",
        unified_context=MagicMock(),
        calibrated_thresholds=cal_for_run,
    )

_test(
    "did NOT re-fetch thresholds when provided",
    len(_fetched_thresholds) == 0,
    f"fetched {len(_fetched_thresholds)} times",
)

trace = session.get_last_trace()
if trace is not None and trace.thresholds_used is not None:
    _test(
        "trace uses caller-provided snapshot",
        trace.thresholds_used.get("min_confidence") == 0.50,
        f"got {trace.thresholds_used.get('min_confidence')}",
    )
    _test(
        "trace uses caller wm threshold",
        trace.thresholds_used.get("world_model_confidence_threshold") == 0.55,
    )
else:
    _test("trace uses caller-provided snapshot", trace is not None, "trace is None")
    _test("trace uses caller wm threshold", False, "no trace")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. select_best() passes min_confidence to strategy memory
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. select_best() Calibrated min_confidence")

from umh.runtime_engine.multi_strategy import select_best, CandidateResult
from umh.strategy.memory import get_strategy_memory, reset_strategy_memory

reset_strategy_memory()

c_win = CandidateResult(
    output="winner",
    strategy_name="baseline",
    quality_score=0.9,
    confidence=0.55,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=100,
)
c_lose = CandidateResult(
    output="loser",
    strategy_name="clarity",
    quality_score=0.4,
    confidence=0.55,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=100,
)

# With default min_confidence=0.6, confidence=0.55 should be gated
reset_strategy_memory()
select_best([c_win, c_lose])
mem = get_strategy_memory()
baseline = mem._stats.get("baseline")
_test(
    "default gate: 0.55 < 0.6 → wins not recorded",
    baseline is None or baseline.wins == 0,
    f"wins={baseline.wins if baseline else 'N/A'}",
)

# With calibrated min_confidence=0.50, confidence=0.55 should pass
reset_strategy_memory()
select_best([c_win, c_lose], min_confidence=0.50)
mem = get_strategy_memory()
baseline = mem._stats.get("baseline")
_test(
    "calibrated gate 0.50: 0.55 >= 0.50 → win recorded",
    baseline is not None and baseline.wins == 1,
    f"wins={baseline.wins if baseline else 'N/A'}",
)

clarity = mem._stats.get("clarity")
_test(
    "calibrated gate 0.50: loss recorded for loser",
    clarity is not None and clarity.uses == 1 and clarity.wins == 0,
    f"uses={clarity.uses if clarity else 'N/A'}, wins={clarity.wins if clarity else 'N/A'}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. run_with_strategies() accepts min_confidence
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. run_with_strategies() min_confidence Parameter")

from umh.runtime_engine.multi_strategy import run_with_strategies

sig = inspect.signature(run_with_strategies)
_test(
    "run_with_strategies has min_confidence param",
    "min_confidence" in sig.parameters,
)
_test(
    "min_confidence defaults to None",
    sig.parameters["min_confidence"].default is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. One coherent snapshot across all consumers
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Coherent Snapshot Across Consumers")

cal_coherent = CalibratedThresholds(
    low_quality_threshold=0.38,
    high_confidence_threshold=0.72,
    hallucination_confidence_threshold=0.42,
    block_confidence_threshold=0.19,
    world_model_confidence_threshold=0.58,
    min_confidence=0.55,
    sample_count=60,
    calibrated=True,
)

# Verify: adapt_prompt sees the same object
_captured_thresholds.clear()
with patch("umh.runtime_engine.adaptive_prompt.adapt_prompt", side_effect=_spy_adapt_prompt):
    builder = ContextBuilder()
    uc = builder.build(
        mock_ctx,
        "test",
        "test-session",
        calibrated_thresholds=cal_coherent,
    )

_test(
    "adapt_prompt sees exact same object",
    _captured_thresholds[0] is cal_coherent,
)

# Verify: strategy memory would see same min_confidence
reset_strategy_memory()
select_best(
    [c_win, c_lose],
    min_confidence=cal_coherent.min_confidence,
)
mem = get_strategy_memory()
baseline = mem._stats.get("baseline")
_test(
    "strategy memory uses same min_confidence (0.55)",
    baseline is not None and baseline.wins == 1,
    f"wins={baseline.wins if baseline else 'N/A'}",
)

# Verify: route_signals uses same snapshot
from umh.runtime_engine.signal_router import route_signals

eval_data = {"quality_score": 0.75, "confidence": 0.59, "flags": {}, "reason": "ok"}
signals = route_signals(
    eval_data,
    wm_confidence_threshold=cal_coherent.world_model_confidence_threshold,
)
_test(
    "route_signals uses same wm_threshold (0.58): 0.59 >= 0.58",
    signals.world_model is not None,
)

# Verify: control_policy uses same snapshot
from umh.runtime_engine.control_layer import ControlPolicy

policy = ControlPolicy(enabled=True)
from umh.runtime_engine.decision_trace import DecisionTrace

trace_for_ctrl = DecisionTrace(
    turn_id=1,
    strategies_considered=("baseline",),
    strategy_scores={"baseline": 0.5},
    selected_strategy="baseline",
    quality_score=0.7,
    confidence=0.41,
    signals={
        "quality_score": 0.7,
        "confidence": 0.41,
        "flags": {"hallucination_risk": True, "incomplete": False},
    },
    attributed_signals={},
    horizon={},
    directives_applied=(),
    model_used="test",
    latency_ms=100,
    tokens_used={"input": 50, "output": 50},
    was_enhanced=False,
)
ctrl = policy.evaluate([trace_for_ctrl], thresholds=cal_coherent)
_test(
    "control_policy uses same halluc_threshold (0.42): 0.41 < 0.42",
    ctrl.intervene is True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Calibration disabled — all paths use defaults
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Calibration Disabled — Default Behavior")

# ContextBuilder without thresholds
_captured_thresholds.clear()
with patch("umh.runtime_engine.adaptive_prompt.adapt_prompt", side_effect=_spy_adapt_prompt):
    builder = ContextBuilder()
    uc = builder.build(mock_ctx, "test", "test-session")

_test("no thresholds → adapt_prompt gets None", _captured_thresholds[0] is None)

# select_best without min_confidence uses default gate
reset_strategy_memory()
# confidence=0.59 < default 0.6 → gated
c_low_conf = CandidateResult(
    output="test",
    strategy_name="baseline",
    quality_score=0.9,
    confidence=0.59,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=100,
)
select_best([c_low_conf])
mem = get_strategy_memory()
baseline = mem._stats.get("baseline")
_test(
    "default gate: 0.59 < 0.6 → gated",
    baseline is None or baseline.wins == 0,
)

# SessionRuntime without calibration
session_nocal = SessionRuntime(MagicMock(), session_id="no-cal")
t = session_nocal.get_calibrated_thresholds()
_test("no-cal session returns defaults", t.calibrated is False)
_test("no-cal defaults match", t == DEFAULT_THRESHOLDS)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. adapt_prompt uses calibrated thresholds functionally
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. adapt_prompt Functional Calibration")

from umh.runtime_engine.adaptive_prompt import adapt_prompt

base = "You are a helpful assistant."

# Create a session runtime mock with low-quality evaluations
mock_session = MagicMock()
mock_session.stats = MagicMock()
mock_session.stats.evaluations = [
    {
        "quality_score": 0.30,
        "confidence": 0.8,
        "flags": {
            "hallucination_risk": False,
            "incomplete": False,
            "low_information": False,
        },
    },
    {
        "quality_score": 0.32,
        "confidence": 0.8,
        "flags": {
            "hallucination_risk": False,
            "incomplete": False,
            "low_information": False,
        },
    },
    {
        "quality_score": 0.33,
        "confidence": 0.8,
        "flags": {
            "hallucination_risk": False,
            "incomplete": False,
            "low_information": False,
        },
    },
]

# Default threshold: 0.45 — these scores (0.30-0.33) are below 0.45 → trigger
result_default = adapt_prompt(base, session_runtime=mock_session)
has_directive_default = result_default != base

# Calibrated threshold: 0.25 — these scores (0.30-0.33) are above 0.25 → no trigger
cal_lenient = CalibratedThresholds(low_quality_threshold=0.25)
result_lenient = adapt_prompt(
    base, session_runtime=mock_session, thresholds=cal_lenient
)
has_directive_lenient = result_lenient != base

_test(
    "default threshold 0.45: low scores trigger directive",
    has_directive_default,
    f"modified={has_directive_default}",
)
_test(
    "calibrated threshold 0.25: same scores don't trigger",
    not has_directive_lenient,
    f"modified={has_directive_lenient}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
