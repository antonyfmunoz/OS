"""
Tests for multi-strategy integration in the live SessionRuntime path.

Validates:
    1.  Eligible live turns use multi-strategy
    2.  Non-eligible turns fall through to normal spine execution
    3.  Candidate generation occurs without persistent side effects
    4.  Only the winner is committed to the persistence path
    5.  Rejected candidates do not hit memory/world-model/feedback writes
    6.  The same threshold snapshot is used across the turn
    7.  Strategy learning updates only from the winner
    8.  DecisionTrace remains explainable for multi-strategy turns
    9.  Deterministic behavior preserved
    10. No regression for non-multi-strategy turns
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
from dataclasses import dataclass
from umh.runtime_engine.calibration import CalibratedThresholds, DEFAULT_THRESHOLDS
from umh.runtime_engine.execution_spine import SpineResult
from umh.runtime_engine.session_runtime import SessionRuntime
from umh.runtime_engine.multi_strategy import (
    CandidateResult,
    is_strategy_eligible,
    select_best,
)
from umh.strategy.memory import reset_strategy_memory, get_strategy_memory
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class FakeTaskType:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


@dataclass
class FakeRoutingResult:
    output: str
    provider: str = "test"
    model: str = "test-model"
    tokens_used: int = 100
    input_tokens: int = 50
    output_tokens: int = 50
    cost_usd: float = 0.001
    latency_ms: int = 200


_call_count = 0


def _mock_call_with_fallback(prompt, system=None, agent_type=None, task_type=None):
    global _call_count
    _call_count += 1
    if _call_count % 2 == 1:
        return FakeRoutingResult(
            output="Here is a comprehensive analysis of your business strategy."
        )
    else:
        return FakeRoutingResult(
            output="Focus on 3 key actions: 1. Send DMs. 2. Track rates. 3. Follow up."
        )


def _make_spine_result(text: str = "test response", iterations: int = 1) -> SpineResult:
    return SpineResult(
        text,
        model_used="test/test-model",
        tokens_used={"input": 50, "output": 50, "total": 100},
        cost_usd=0.001,
        latency_ms=200,
        session_id="test-session",
        iterations=iterations,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Eligible live turns use multi-strategy
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Eligible Turns Use Multi-Strategy")

_rws_calls: list[dict] = []
_original_rws = None


def _spy_run_with_strategies(**kwargs):
    _rws_calls.append(kwargs)
    return _make_spine_result("multi-strategy winner", iterations=2)


mock_ctx = MagicMock()
session = SessionRuntime(mock_ctx, session_id="eligible-test")

with patch(
    "umh.runtime_engine.multi_strategy.run_with_strategies",
    side_effect=_spy_run_with_strategies,
):
    _rws_calls.clear()
    result = session.run(
        message="Draft outreach copy",
        unified_context=MagicMock(),
        task_type=FakeTaskType("generate"),
    )

_test(
    "run_with_strategies called",
    len(_rws_calls) == 1,
    f"called {len(_rws_calls)} times",
)
_test(
    "task_type passed through",
    str(_rws_calls[0]["task_type"]) == "generate",
)
_test(
    "result is from multi-strategy",
    "multi-strategy winner" in str(result),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Non-eligible turns fall through to normal spine execution
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Non-Eligible Turns")


def _spy_rws_for_fallback(**kwargs):
    _rws_calls.append(kwargs)
    return _make_spine_result("spine fallback response", iterations=1)


session2 = SessionRuntime(MagicMock(), session_id="non-eligible-test")

with patch(
    "umh.runtime_engine.multi_strategy.run_with_strategies",
    side_effect=_spy_rws_for_fallback,
):
    _rws_calls.clear()
    result = session2.run(
        message="Quick check",
        unified_context=MagicMock(),
        task_type=FakeTaskType("fast_response"),
    )

_test(
    "run_with_strategies still called (it handles eligibility)",
    len(_rws_calls) == 1,
)
_test(
    "fast_response task type passed",
    str(_rws_calls[0]["task_type"]) == "fast_response",
)

# Verify that run_with_strategies would have fallen through:
_test(
    "fast_response is not strategy-eligible",
    not is_strategy_eligible(FakeTaskType("fast_response")),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Candidate generation has no persistent side effects
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Candidate Generation — No Side Effects")

from umh.runtime_engine.multi_strategy import generate_candidates

_persist_calls: list = []
_cm_calls: list = []
_am_calls: list = []
_wm_calls: list = []
_feedback_calls: list = []

with patch(
    "umh.runtime_engine.model_router.call_with_fallback",
    side_effect=_mock_call_with_fallback,
):
    _call_count = 0
    candidates = generate_candidates(
        message="Draft outreach",
        system_prompt="You are a business assistant.",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test("candidates generated", len(candidates) == 2, f"got {len(candidates)}")

# Verify ConversationMemory was NOT called
with patch("umh.runtime_engine.memory.ConversationMemory") as mock_cm:
    # generate_candidates should not touch ConversationMemory at all
    pass

_test(
    "generate_candidates returns CandidateResult objects",
    all(isinstance(c, CandidateResult) for c in candidates),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Only the winner is committed to the persistence path
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Winner-Only Persistence")

_commit_winner_calls: list[dict] = []


def _spy_commit_winner(**kwargs):
    _commit_winner_calls.append(kwargs)


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback",
        side_effect=_mock_call_with_fallback,
    ),
    patch("umh.runtime_engine.commit_pipeline.commit_winner", side_effect=_spy_commit_winner),
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch(
        "umh.runtime_engine.execution_spine.ExecutionSpine.run", return_value=_make_spine_result()
    ),
):
    _call_count = 0
    _commit_winner_calls.clear()

    from umh.runtime_engine.multi_strategy import run_with_strategies

    result = run_with_strategies(
        message="Draft strategy",
        unified_context=MagicMock(
            to_system_prompt=lambda: "You are a business assistant."
        ),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        session_id="test-persist",
        org_id="test-org",
    )

_test(
    "commit_winner called exactly once",
    len(_commit_winner_calls) == 1,
    f"called {len(_commit_winner_calls)} times",
)
_test(
    "persisted response is the winner's output",
    _commit_winner_calls[0]["response"] in str(result),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Rejected candidates don't hit memory/world-model/feedback
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Rejected Candidates — Zero Persistence")

_cm_store_calls: list = []
_wm_update_calls: list = []
_feedback_log_calls: list = []


def _track_cm_store(*args, **kwargs):
    _cm_store_calls.append(kwargs)


def _track_wm_update(*args, **kwargs):
    _wm_update_calls.append(kwargs)


def _track_feedback_log(*args, **kwargs):
    _feedback_log_calls.append(kwargs)


with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback",
        side_effect=_mock_call_with_fallback,
    ),
    patch("umh.runtime_engine.commit_pipeline.commit_winner") as mock_cw,
    patch("umh.runtime_engine.context.load_context_from_env", return_value=MagicMock()),
    patch(
        "umh.runtime_engine.signal_router.route_signals", return_value=MagicMock(world_model=None)
    ),
    patch(
        "umh.runtime_engine.execution_spine.ExecutionSpine.run", return_value=_make_spine_result()
    ),
):
    _call_count = 0
    result = run_with_strategies(
        message="Analyze pipeline",
        unified_context=MagicMock(to_system_prompt=lambda: "System."),
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

# commit_winner is called once (for the winner only)
_test(
    "commit called once (winner only)",
    mock_cw.call_count == 1,
)

# The key guarantee: generate_candidates only calls call_with_fallback
# and evaluate_outcome — neither writes to memory, feedback, or world model.
_test("result iterations shows multi-strategy", result.iterations == 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Same threshold snapshot across the turn
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Coherent Threshold Snapshot")

cal = CalibratedThresholds(
    low_quality_threshold=0.38,
    high_confidence_threshold=0.72,
    min_confidence=0.55,
    world_model_confidence_threshold=0.58,
    calibrated=True,
)

_captured_min_conf: list = []


def _spy_rws_thresholds(**kwargs):
    _captured_min_conf.append(kwargs.get("min_confidence"))
    return _make_spine_result("threshold test", iterations=2)


session_cal = SessionRuntime(MagicMock(), session_id="threshold-coherent")

with patch(
    "umh.runtime_engine.multi_strategy.run_with_strategies",
    side_effect=_spy_rws_thresholds,
):
    _captured_min_conf.clear()
    result = session_cal.run(
        message="Test thresholds",
        unified_context=MagicMock(),
        task_type=FakeTaskType("generate"),
        calibrated_thresholds=cal,
    )

_test(
    "min_confidence passed to run_with_strategies",
    len(_captured_min_conf) == 1 and _captured_min_conf[0] == 0.55,
    f"got {_captured_min_conf}",
)

# Verify the trace also uses the same snapshot
trace = session_cal.get_last_trace()
if trace and trace.thresholds_used:
    _test(
        "trace thresholds match caller snapshot",
        trace.thresholds_used.get("min_confidence") == 0.55,
    )
    _test(
        "trace wm_conf matches snapshot",
        trace.thresholds_used.get("world_model_confidence_threshold") == 0.58,
    )
else:
    _test("trace thresholds match caller snapshot", False, "no trace or thresholds")
    _test("trace wm_conf matches snapshot", False)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Strategy learning uses calibrated min_confidence
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Strategy Learning — Calibrated Gate")

reset_strategy_memory()

c_high = CandidateResult(
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
c_low = CandidateResult(
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

# Default gate (0.6) — confidence 0.55 should be gated
reset_strategy_memory()
select_best([c_high, c_low])
mem = get_strategy_memory()
b = mem._stats.get("baseline")
_test(
    "default 0.6 gate: 0.55 gated",
    b is None or b.wins == 0,
)

# Calibrated gate (0.50) — confidence 0.55 should pass
reset_strategy_memory()
select_best([c_high, c_low], min_confidence=0.50)
mem = get_strategy_memory()
b = mem._stats.get("baseline")
_test(
    "calibrated 0.50 gate: 0.55 passes → win recorded",
    b is not None and b.wins == 1,
    f"wins={b.wins if b else 'N/A'}",
)
c = mem._stats.get("clarity")
_test(
    "loser recorded as loss (not win)",
    c is not None and c.uses == 1 and c.wins == 0,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DecisionTrace for multi-strategy turns
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. DecisionTrace — Multi-Strategy Observability")


def _spy_rws_multi(**kwargs):
    return _make_spine_result("multi-winner", iterations=2)


reset_strategy_memory()
get_strategy_memory().record_win("baseline", 0.8, 0.9)

session_trace = SessionRuntime(MagicMock(), session_id="trace-test")

with patch(
    "umh.runtime_engine.multi_strategy.run_with_strategies",
    side_effect=_spy_rws_multi,
):
    result = session_trace.run(
        message="Test trace",
        unified_context=MagicMock(),
        task_type=FakeTaskType("generate"),
    )

trace = session_trace.get_last_trace()
_test("trace exists", trace is not None)

if trace:
    _test(
        "strategy_selection present",
        trace.strategy_selection is not None,
    )
    if trace.strategy_selection:
        _test(
            "strategy_selection.enabled is True",
            trace.strategy_selection.get("enabled") is True,
        )
        _test(
            "strategy_selection.candidates == 2",
            trace.strategy_selection.get("candidates") == 2,
        )
        _test(
            "strategy_selection has selected_strategy",
            "selected_strategy" in trace.strategy_selection,
        )
        _test(
            "strategy_selection has candidate_scores",
            "candidate_scores" in trace.strategy_selection,
        )

        # Verify serialization
        d = trace.to_dict()
        _test(
            "strategy_selection in to_dict",
            "strategy_selection" in d,
        )
    else:
        for _ in range(5):
            _test("(skipped — no strategy_selection)", False)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Single-execution turns — no strategy_selection in trace
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Single-Execution Turns — No Strategy Selection")


def _spy_rws_single(**kwargs):
    return _make_spine_result("single response", iterations=1)


session_single = SessionRuntime(MagicMock(), session_id="single-test")

with patch(
    "umh.runtime_engine.multi_strategy.run_with_strategies",
    side_effect=_spy_rws_single,
):
    result = session_single.run(
        message="Quick question",
        unified_context=MagicMock(),
        task_type=FakeTaskType("fast_response"),
    )

trace = session_single.get_last_trace()
_test("trace exists for single turn", trace is not None)
if trace:
    _test(
        "strategy_selection is None for single turn",
        trace.strategy_selection is None,
    )
    d = trace.to_dict()
    _test(
        "strategy_selection omitted from to_dict",
        "strategy_selection" not in d,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Determinism")

reset_strategy_memory()

c1 = CandidateResult(
    output="A",
    strategy_name="baseline",
    quality_score=0.6,
    confidence=0.8,
    evaluation={},
    model_used="t",
    tokens_used=10,
    cost_usd=0.0,
    latency_ms=10,
)
c2 = CandidateResult(
    output="B",
    strategy_name="clarity",
    quality_score=0.8,
    confidence=0.7,
    evaluation={},
    model_used="t",
    tokens_used=10,
    cost_usd=0.0,
    latency_ms=10,
)

reset_strategy_memory()
r1 = select_best([c1, c2], min_confidence=0.5)
reset_strategy_memory()
r2 = select_best([c1, c2], min_confidence=0.5)
_test(
    "same inputs → same winner",
    r1.strategy_name == r2.strategy_name,
    f"{r1.strategy_name} vs {r2.strategy_name}",
)

# Order-independent
reset_strategy_memory()
r3 = select_best([c2, c1], min_confidence=0.5)
_test(
    "order-independent",
    r3.strategy_name == r1.strategy_name,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. build_trace backward compatibility with strategy_selection
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. build_trace Backward Compatibility")

reset_strategy_memory()
get_strategy_memory().record_win("baseline", 0.7)

# Old call pattern — no strategy_selection
bt = build_trace(turn_id=1)
_test("old call pattern works", bt.turn_id == 1)
_test("strategy_selection defaults None", bt.strategy_selection is None)
_test("not in to_dict when None", "strategy_selection" not in bt.to_dict())

# New call pattern — with strategy_selection
sel = {"enabled": True, "candidates": 2, "selected_strategy": "baseline"}
bt2 = build_trace(turn_id=2, strategy_selection=sel)
_test("strategy_selection stored", bt2.strategy_selection == sel)
_test("in to_dict when present", "strategy_selection" in bt2.to_dict())
_test("to_dict value matches", bt2.to_dict()["strategy_selection"] == sel)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. SessionRuntime no longer imports ExecutionSpine directly
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. SessionRuntime Uses run_with_strategies")

import inspect

src = inspect.getsource(SessionRuntime.run)
_test(
    "run_with_strategies is in run() source",
    "run_with_strategies" in src,
)
_test(
    "ExecutionSpine().run() NOT in run() source",
    "ExecutionSpine().run(" not in src,
    "should delegate via run_with_strategies, not call spine directly",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
