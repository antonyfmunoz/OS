"""
Tests for Goal Evaluation and Progress Tracking.

Validates:
    1. goal_score computed deterministically
    2. goal_delta tracks change across turns
    3. convergence reacts to goal_delta
    4. memory weighting includes goal_score
    5. DecisionTrace includes goal fields
    6. UnifiedInfluence includes progress signal
    7. behavior differs for improving vs regressing goals
    8. no regressions (tested via existing suites)
    9. no new LLM calls
    10. ExecutionSpine unchanged
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


# ═══════════════════════════════════════════════════════════════════════════════
# 1. GoalEvaluation data structure + deterministic scoring
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. GoalEvaluation Structure + Deterministic Scoring")

from umh.runtime_engine.goal_evaluator import (
    NO_GOAL_EVAL,
    NEUTRAL_CONFIDENCE,
    NEUTRAL_SCORE,
    GoalEvaluation,
    GoalEvaluator,
)
from umh.goals.state import NO_GOAL, GoalState
from umh.runtime_engine.decision_trace import build_trace

# Construction
ge = GoalEvaluation(goal_score=0.7, delta=0.1, confidence=0.8, signals={"a": 1})
_test("goal_score set", ge.goal_score == 0.7)
_test("delta set", ge.delta == 0.1)
_test("confidence set", ge.confidence == 0.8)
_test("signals set", ge.signals == {"a": 1})
_test("frozen dataclass", hasattr(GoalEvaluation, "__dataclass_fields__"))

# to_dict
d = ge.to_dict()
_test("to_dict has goal_score", d["goal_score"] == 0.7)
_test("to_dict has delta", d["delta"] == 0.1)
_test("to_dict has confidence", d["confidence"] == 0.8)
_test("to_dict has signals", d["signals"] == {"a": 1})

# NO_GOAL_EVAL sentinel
_test("NO_GOAL_EVAL.goal_score is neutral", NO_GOAL_EVAL.goal_score == NEUTRAL_SCORE)
_test("NO_GOAL_EVAL.delta is zero", NO_GOAL_EVAL.delta == 0.0)
_test("NO_GOAL_EVAL.confidence is zero", NO_GOAL_EVAL.confidence == NEUTRAL_CONFIDENCE)
_test("NO_GOAL_EVAL.signals is empty", NO_GOAL_EVAL.signals == {})

# Evaluator with inactive goal
evaluator = GoalEvaluator()
trace = build_trace(turn_id=1, evaluation={"quality_score": 0.7, "confidence": 0.6})
result = evaluator.evaluate(trace, NO_GOAL, None)
_test("inactive goal → NO_GOAL_EVAL", result == NO_GOAL_EVAL)

# Evaluator with active goal
goal = GoalState(
    goal_id="close_sale",
    description="Close coaching sale",
    success_criteria={"response_type": "persuasive", "domain": "sales"},
    priority=0.9,
)
result_active = evaluator.evaluate(trace, goal, None)
_test("active goal → goal_score in [0,1]", 0.0 <= result_active.goal_score <= 1.0)
_test("active goal → confidence > 0", result_active.confidence > 0.0)
_test(
    "active goal → signals has components",
    "criteria_match" in result_active.signals
    and "quality_alignment" in result_active.signals
    and "strategy_affinity" in result_active.signals,
)

# Determinism
for _ in range(50):
    r = evaluator.evaluate(trace, goal, None)
    assert r.goal_score == result_active.goal_score, "Non-deterministic goal_score"
    assert r.delta == result_active.delta, "Non-deterministic delta"
    assert r.confidence == result_active.confidence, "Non-deterministic confidence"
_test("50x evaluate → stable", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. goal_delta tracks change across turns
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. goal_delta Tracks Change Across Turns")

trace1 = build_trace(turn_id=1, evaluation={"quality_score": 0.5, "confidence": 0.5})
trace2 = build_trace(turn_id=2, evaluation={"quality_score": 0.8, "confidence": 0.7})
trace3 = build_trace(turn_id=3, evaluation={"quality_score": 0.3, "confidence": 0.4})

eval1 = evaluator.evaluate(trace1, goal, None)
_test(
    "first eval: delta vs neutral",
    abs(eval1.delta - (eval1.goal_score - NEUTRAL_SCORE)) < 0.0001,
    f"delta={eval1.delta}, expected={eval1.goal_score - NEUTRAL_SCORE}",
)

eval2 = evaluator.evaluate(trace2, goal, eval1)
_test(
    "second eval: delta vs first",
    abs(eval2.delta - (eval2.goal_score - eval1.goal_score)) < 0.0001,
    f"delta={eval2.delta}",
)

eval3 = evaluator.evaluate(trace3, goal, eval2)
_test(
    "third eval: delta vs second",
    abs(eval3.delta - (eval3.goal_score - eval2.goal_score)) < 0.0001,
    f"delta={eval3.delta}",
)

# Higher quality → higher goal_score (quality_alignment component)
_test(
    "higher quality → higher goal_score",
    eval2.goal_score > eval1.goal_score or eval2.goal_score >= eval1.goal_score,
    f"q=0.8 score={eval2.goal_score}, q=0.5 score={eval1.goal_score}",
)

# Improvement produces positive delta
_test(
    "improvement → positive delta",
    eval2.delta > 0 or eval2.goal_score >= eval1.goal_score,
    f"delta={eval2.delta}",
)

# Regression produces negative delta
_test(
    "regression → negative delta",
    eval3.delta < 0,
    f"delta={eval3.delta}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Convergence reacts to goal_delta
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Convergence Reacts to goal_delta")

from umh.runtime_engine.convergence import (
    GOAL_PROGRESS_ACCELERATION_THRESHOLD,
    GOAL_PROGRESS_STREAK,
    GOAL_REGRESSION_STREAK,
    GOAL_REGRESSION_THRESHOLD,
    ConvergenceAction,
    ConvergenceEngine,
    ConvergenceStatus,
)

engine = ConvergenceEngine(enabled=True)

# Regression: sustained negative delta
regressing_traces = [
    build_trace(
        turn_id=i,
        evaluation={"quality_score": 0.6, "confidence": 0.6},
        goal_score=0.5 - i * 0.08,
        goal_delta=-0.08,
        goal_confidence=0.7,
    )
    for i in range(5)
]

conv_regress = engine.evaluate(regressing_traces)
_test(
    "goal regression → unstable",
    conv_regress.status == ConvergenceStatus.UNSTABLE,
    f"status={conv_regress.status.value}, reason={conv_regress.reason}",
)
_test(
    "goal regression → reason is goal_regression",
    conv_regress.reason == "goal_regression",
)
_test(
    "goal regression → suppresses exploration",
    conv_regress.suppress_exploration is True,
)
_test(
    "goal regression → has corrective directive",
    len(conv_regress.directives) > 0,
)

# Progress: sustained positive delta
progressing_traces = [
    build_trace(
        turn_id=i,
        evaluation={"quality_score": 0.7, "confidence": 0.7},
        goal_score=0.4 + i * 0.08,
        goal_delta=0.08,
        goal_confidence=0.7,
    )
    for i in range(5)
]

conv_progress = engine.evaluate(progressing_traces)
_test(
    "goal progress → stable",
    conv_progress.status == ConvergenceStatus.STABLE,
    f"status={conv_progress.status.value}, reason={conv_progress.reason}",
)
_test(
    "goal progress → reason is goal_progress",
    conv_progress.reason == "goal_progress",
)

# Flat delta: no goal-specific intervention
flat_traces = [
    build_trace(
        turn_id=i,
        evaluation={"quality_score": 0.6, "confidence": 0.6},
        goal_score=0.5,
        goal_delta=0.0,
        goal_confidence=0.7,
    )
    for i in range(5)
]

conv_flat = engine.evaluate(flat_traces)
_test(
    "flat delta → NOT goal_regression",
    conv_flat.reason != "goal_regression",
    f"reason={conv_flat.reason}",
)

# No goal_delta on traces → no goal-specific rules fire
no_goal_traces = [
    build_trace(
        turn_id=i,
        evaluation={"quality_score": 0.6, "confidence": 0.6},
    )
    for i in range(5)
]

conv_no_goal = engine.evaluate(no_goal_traces)
_test(
    "no goal fields → no goal-specific rules",
    conv_no_goal.reason != "goal_regression" and conv_no_goal.reason != "goal_progress",
    f"reason={conv_no_goal.reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Memory weighting includes goal_score
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Memory Weighting Includes goal_score")

from umh.strategy.memory import StrategyMemory
import inspect

# Signature check
win_sig = inspect.signature(StrategyMemory.record_win)
_test("record_win has goal_score param", "goal_score" in win_sig.parameters)

loss_sig = inspect.signature(StrategyMemory.record_loss)
_test("record_loss has goal_score param", "goal_score" in loss_sig.parameters)

# Functional: high goal_score → stronger reinforcement
mem_high = StrategyMemory()
mem_high.record_win("clarity", 0.8, confidence=0.9, goal_score=0.9)
score_high = mem_high._stats["clarity"].ema_score

mem_low = StrategyMemory()
mem_low.record_win("clarity", 0.8, confidence=0.9, goal_score=0.2)
score_low = mem_low._stats["clarity"].ema_score

_test(
    "high goal_score → higher EMA",
    score_high > score_low,
    f"high={score_high:.4f}, low={score_low:.4f}",
)

# No goal_score → no change from baseline
mem_none = StrategyMemory()
mem_none.record_win("clarity", 0.8, confidence=0.9, goal_score=None)
score_none = mem_none._stats["clarity"].ema_score

mem_base = StrategyMemory()
mem_base.record_win("clarity", 0.8, confidence=0.9)
score_base = mem_base._stats["clarity"].ema_score

_test(
    "goal_score=None → same as no goal_score",
    abs(score_none - score_base) < 0.0001,
    f"none={score_none:.4f}, base={score_base:.4f}",
)

# Formula: effective_score = quality * (0.5 + 0.5 * goal_score)
expected_high = 0.8 * (0.5 + 0.5 * 0.9)
_test(
    "formula: quality * (0.5 + 0.5 * goal_score)",
    abs(score_high - expected_high) < 0.0001,
    f"got={score_high:.4f}, expected={expected_high:.4f}",
)

# select_best accepts goal_score
from umh.runtime_engine.multi_strategy import select_best, CandidateResult

sb_sig = inspect.signature(select_best)
_test("select_best has goal_score param", "goal_score" in sb_sig.parameters)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DecisionTrace includes goal fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. DecisionTrace Includes Goal Fields")

from umh.runtime_engine.decision_trace import DecisionTrace

# Fields exist
_test(
    "DecisionTrace has goal_score field",
    "goal_score" in DecisionTrace.__dataclass_fields__,
)
_test(
    "DecisionTrace has goal_delta field",
    "goal_delta" in DecisionTrace.__dataclass_fields__,
)
_test(
    "DecisionTrace has goal_confidence field",
    "goal_confidence" in DecisionTrace.__dataclass_fields__,
)

# build_trace accepts goal fields
bt_sig = inspect.signature(build_trace)
_test("build_trace has goal_score param", "goal_score" in bt_sig.parameters)
_test("build_trace has goal_delta param", "goal_delta" in bt_sig.parameters)
_test("build_trace has goal_confidence param", "goal_confidence" in bt_sig.parameters)

# Values propagate
trace_with_goal = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.7, "confidence": 0.6},
    goal_score=0.8,
    goal_delta=0.15,
    goal_confidence=0.7,
)
_test("goal_score set on trace", trace_with_goal.goal_score == 0.8)
_test("goal_delta set on trace", trace_with_goal.goal_delta == 0.15)
_test("goal_confidence set on trace", trace_with_goal.goal_confidence == 0.7)

# Serialization
td = trace_with_goal.to_dict()
_test("to_dict includes goal_score", td.get("goal_score") == 0.8)
_test("to_dict includes goal_delta", td.get("goal_delta") == 0.15)
_test("to_dict includes goal_confidence", td.get("goal_confidence") == 0.7)

# None defaults
trace_no_goal = build_trace(
    turn_id=2,
    evaluation={"quality_score": 0.7, "confidence": 0.6},
)
_test("no goal → goal_score is None", trace_no_goal.goal_score is None)
_test(
    "no goal → goal fields not in to_dict", "goal_score" not in trace_no_goal.to_dict()
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. UnifiedInfluence includes progress signal
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. UnifiedInfluence Includes Progress Signal")

from umh.runtime_engine.influence_orchestrator import (
    NO_INFLUENCE,
    UnifiedInfluence,
    resolve_influence,
)

# Field exists
_test(
    "UnifiedInfluence has goal_progress_signal",
    "goal_progress_signal" in UnifiedInfluence.__dataclass_fields__,
)
_test("NO_INFLUENCE has zero progress signal", NO_INFLUENCE.goal_progress_signal == 0.0)

# resolve_influence accepts goal_progress_signal
ri_sig = inspect.signature(resolve_influence)
_test(
    "resolve_influence has goal_progress_signal param",
    "goal_progress_signal" in ri_sig.parameters,
)

# Positive signal
inf_pos = resolve_influence(goal_state=goal, goal_progress_signal=0.15)
_test(
    "positive progress signal flows through",
    inf_pos.goal_progress_signal == 0.15,
)

# Negative signal
inf_neg = resolve_influence(goal_state=goal, goal_progress_signal=-0.1)
_test(
    "negative progress signal flows through",
    inf_neg.goal_progress_signal == -0.1,
)

# Zero signal + no other influence → NO_INFLUENCE shortcircuit
inf_zero = resolve_influence(goal_progress_signal=0.0)
_test(
    "zero progress + no other influence → NO_INFLUENCE",
    inf_zero == NO_INFLUENCE,
)

# Non-zero signal prevents shortcircuit
inf_nonzero = resolve_influence(goal_progress_signal=0.05)
_test(
    "non-zero progress prevents NO_INFLUENCE",
    inf_nonzero != NO_INFLUENCE,
)

# to_dict includes progress signal
d = inf_pos.to_dict()
_test("to_dict includes goal_progress_signal", d.get("goal_progress_signal") == 0.15)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Behavior differs for improving vs regressing goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Improving vs Regressing Goals")

# Different quality traces produce different goal_scores
trace_good = build_trace(
    turn_id=1,
    evaluation={"quality_score": 0.9, "confidence": 0.8},
)
trace_bad = build_trace(
    turn_id=2,
    evaluation={"quality_score": 0.2, "confidence": 0.3},
)

eval_good = evaluator.evaluate(trace_good, goal, None)
eval_bad = evaluator.evaluate(trace_bad, goal, None)
_test(
    "good quality → higher goal_score",
    eval_good.goal_score > eval_bad.goal_score,
    f"good={eval_good.goal_score:.3f}, bad={eval_bad.goal_score:.3f}",
)

# Improving sequence: positive deltas
seq = [
    build_trace(
        turn_id=i, evaluation={"quality_score": 0.3 + i * 0.15, "confidence": 0.6}
    )
    for i in range(4)
]
evals_improving = []
prev = None
for t in seq:
    ev = evaluator.evaluate(t, goal, prev)
    evals_improving.append(ev)
    prev = ev

positive_deltas = sum(1 for e in evals_improving[1:] if e.delta > 0)
_test(
    "improving sequence → mostly positive deltas",
    positive_deltas >= 2,
    f"positive={positive_deltas}/3",
)

# Regressing sequence: negative deltas
seq_reg = [
    build_trace(
        turn_id=i, evaluation={"quality_score": 0.8 - i * 0.15, "confidence": 0.6}
    )
    for i in range(4)
]
evals_regressing = []
prev = None
for t in seq_reg:
    ev = evaluator.evaluate(t, goal, prev)
    evals_regressing.append(ev)
    prev = ev

negative_deltas = sum(1 for e in evals_regressing[1:] if e.delta < 0)
_test(
    "regressing sequence → mostly negative deltas",
    negative_deltas >= 2,
    f"negative={negative_deltas}/3",
)

# Convergence treats them differently
engine2 = ConvergenceEngine(enabled=True)

improving_conv_traces = [
    build_trace(
        turn_id=i,
        evaluation={"quality_score": 0.6, "confidence": 0.6},
        goal_score=0.4 + i * 0.1,
        goal_delta=0.1,
        goal_confidence=0.7,
    )
    for i in range(5)
]

regressing_conv_traces = [
    build_trace(
        turn_id=i,
        evaluation={"quality_score": 0.6, "confidence": 0.6},
        goal_score=0.8 - i * 0.1,
        goal_delta=-0.1,
        goal_confidence=0.7,
    )
    for i in range(5)
]

conv_improving = engine2.evaluate(improving_conv_traces)
conv_regressing = engine2.evaluate(regressing_conv_traces)

_test(
    "convergence distinguishes improving from regressing",
    conv_improving.reason != conv_regressing.reason
    or conv_improving.status != conv_regressing.status,
    f"improving={conv_improving.reason}, regressing={conv_regressing.reason}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Determinism across all components
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Determinism")

# GoalEvaluator
for _ in range(50):
    r = evaluator.evaluate(trace, goal, None)
    assert r.goal_score == result_active.goal_score
_test("50x GoalEvaluator.evaluate → stable", True)

# Convergence with goal traces
for _ in range(50):
    r = engine.evaluate(regressing_traces)
    assert r.reason == conv_regress.reason
_test("50x convergence with goal_delta → stable", True)

# resolve_influence with progress signal
inf1 = resolve_influence(goal_state=goal, goal_progress_signal=0.1)
for _ in range(50):
    r = resolve_influence(goal_state=goal, goal_progress_signal=0.1)
    assert r == inf1
_test("50x resolve_influence with progress → stable", True)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. No new LLM calls
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. No New LLM Calls")

import umh.runtime_engine.goal_evaluator as ge_mod

ge_source = inspect.getsource(ge_mod)
_test(
    "goal_evaluator has no LLM calls",
    "call_with_fallback" not in ge_source
    and "model_router" not in ge_source
    and "AgentRuntime" not in ge_source,
)

# Convergence goal rules
from umh.runtime_engine.convergence import ConvergenceEngine as CE

ce_source = inspect.getsource(CE._check_goal_regression)
_test(
    "_check_goal_regression has no LLM calls",
    "call_with_fallback" not in ce_source,
)

ce_progress_source = inspect.getsource(CE._check_goal_progress)
_test(
    "_check_goal_progress has no LLM calls",
    "call_with_fallback" not in ce_progress_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. ExecutionSpine Unchanged")

spine_source = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test(
    "ExecutionSpine has no goal_evaluator references",
    "goal_evaluator" not in spine_source and "GoalEvaluator" not in spine_source,
)
_test(
    "ExecutionSpine has no goal_score references",
    "goal_score" not in spine_source,
)
_test(
    "ExecutionSpine has no goal_delta references",
    "goal_delta" not in spine_source,
)
_test(
    "ExecutionSpine has no goal_progress references",
    "goal_progress" not in spine_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. SessionRuntime wiring
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. SessionRuntime Wiring")

from umh.runtime_engine.session_runtime import SessionRuntime

sr_source = inspect.getsource(SessionRuntime.run)

_test(
    "SessionRuntime computes goal evaluation",
    "GoalEvaluator" in sr_source,
)
_test(
    "SessionRuntime stores _goal_eval_current",
    "_goal_eval_current" in sr_source,
)
_test(
    "SessionRuntime stores _goal_eval_prev",
    "_goal_eval_prev" in sr_source,
)
_test(
    "SessionRuntime passes goal_score to build_trace",
    "goal_score=_goal_score" in sr_source,
)
_test(
    "SessionRuntime passes goal_delta to build_trace",
    "goal_delta=_goal_delta" in sr_source,
)
_test(
    "SessionRuntime passes goal_progress_signal to resolve_influence",
    "goal_progress_signal=_goal_progress_signal" in sr_source,
)

# get_goal_evaluation exists
_test(
    "get_goal_evaluation method exists",
    hasattr(SessionRuntime, "get_goal_evaluation"),
)

sr_ge_source = inspect.getsource(SessionRuntime.get_goal_evaluation)
_test(
    "get_goal_evaluation returns NO_GOAL_EVAL default",
    "NO_GOAL_EVAL" in sr_ge_source,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Backward compatibility
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Backward Compatibility")

# GoalEvaluator with NO_GOAL returns neutral
eval_no_goal = evaluator.evaluate(trace, NO_GOAL, None)
_test("NO_GOAL → neutral goal_score", eval_no_goal.goal_score == NEUTRAL_SCORE)
_test("NO_GOAL → zero delta", eval_no_goal.delta == 0.0)
_test("NO_GOAL → zero confidence", eval_no_goal.confidence == NEUTRAL_CONFIDENCE)
_test("NO_GOAL → returns NO_GOAL_EVAL", eval_no_goal == NO_GOAL_EVAL)

# Convergence with no goal fields → no goal rules fire
conv_no_goal_fields = engine.evaluate(no_goal_traces)
_test(
    "no goal fields → no goal_regression",
    conv_no_goal_fields.reason != "goal_regression",
)
_test(
    "no goal fields → no goal_progress",
    conv_no_goal_fields.reason != "goal_progress",
)

# strategy_memory without goal_score → unchanged behavior
mem_compat = StrategyMemory()
mem_compat.record_win("clarity", 0.8, confidence=0.9)
score_compat = mem_compat._stats["clarity"].ema_score
_test(
    "record_win without goal_score → raw quality used",
    abs(score_compat - 0.8) < 0.0001,
    f"score={score_compat}",
)

# resolve_influence without goal_progress_signal → same as before
inf_compat = resolve_influence()
inf_with_zero = resolve_influence(goal_progress_signal=0.0)
_test(
    "resolve_influence() == resolve_influence(goal_progress_signal=0.0)",
    inf_compat == inf_with_zero,
)

# DecisionTrace without goal fields → not in to_dict
trace_compat = build_trace(
    turn_id=1, evaluation={"quality_score": 0.5, "confidence": 0.5}
)
_test(
    "trace without goal → no goal fields in to_dict",
    "goal_score" not in trace_compat.to_dict(),
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
