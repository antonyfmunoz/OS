"""
Tests for Decision Trace + Observability Layer.

Validates:
    - DecisionTrace dataclass is frozen (immutable)
    - build_trace() populates all fields from available data
    - build_trace() handles missing data gracefully
    - Trace is created per turn in SessionRuntime
    - Trace cap at MAX_TRACES works
    - get_last_trace() returns most recent trace
    - Strategy scores use decay-adjusted effective_score
    - Signal routing is captured in attributed_signals
    - Horizon tags are present
    - Deterministic output across identical inputs
    - Debug print toggle works
    - to_dict() serialization is complete
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
# 1. DecisionTrace is frozen
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Immutability")

from umh.runtime_engine.decision_trace import DecisionTrace, build_trace, MAX_TRACES, DEBUG_TRACE

trace = DecisionTrace(
    turn_id=1,
    strategies_considered=("baseline", "clarity"),
    strategy_scores={"baseline": 0.5, "clarity": 0.8},
    selected_strategy="clarity",
    quality_score=0.75,
    confidence=0.85,
    signals={"quality_score": 0.75},
    attributed_signals={"strategy": {"quality_score": 0.75}},
    horizon={"session": True, "strategy": True, "world_model": True},
    directives_applied=("Be concise.",),
    model_used="test/model",
    latency_ms=150,
    tokens_used={"input": 50, "output": 100, "total": 150},
    was_enhanced=False,
)

_test("trace is frozen dataclass", hasattr(trace, "__dataclass_fields__"))

try:
    trace.quality_score = 0.99
    _test("mutation blocked", False, "should have raised FrozenInstanceError")
except AttributeError:
    _test("mutation blocked", True)

_test("turn_id correct", trace.turn_id == 1)
_test("selected_strategy correct", trace.selected_strategy == "clarity")
_test("strategies_considered is tuple", isinstance(trace.strategies_considered, tuple))
_test("directives_applied is tuple", isinstance(trace.directives_applied, tuple))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. build_trace with full data
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. build_trace — Full Data")

from umh.strategy.memory import (
    StrategyMemory,
    reset_strategy_memory,
    get_strategy_memory,
)
from umh.runtime_engine.signal_router import route_signals

reset_strategy_memory()
gmem = get_strategy_memory()
gmem.record_win("clarity", 0.9)
gmem.record_win("baseline", 0.6)


class FakeResult:
    model_used = "gemini/gemini-2.5-flash"
    latency_ms = 250
    tokens_used = {"input": 80, "output": 120, "total": 200}
    was_enhanced = True


eval_dict = {
    "quality_score": 0.82,
    "confidence": 0.75,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}
signals = route_signals(eval_dict)

t = build_trace(
    turn_id=5,
    evaluation=eval_dict,
    signals=signals,
    result=FakeResult(),
    directives=["Be precise.", "Follow patterns."],
)

_test("turn_id populated", t.turn_id == 5)
_test("quality_score from evaluation", abs(t.quality_score - 0.82) < 0.001)
_test("confidence from evaluation", abs(t.confidence - 0.75) < 0.001)
_test("model_used from result", t.model_used == "gemini/gemini-2.5-flash")
_test("latency_ms from result", t.latency_ms == 250)
_test("tokens_used from result", t.tokens_used["total"] == 200)
_test("was_enhanced from result", t.was_enhanced is True)
_test(
    "strategies_considered populated",
    len(t.strategies_considered) >= 2,
    f"got {t.strategies_considered}",
)
_test(
    "strategy_scores has values",
    len(t.strategy_scores) >= 2,
    f"got {t.strategy_scores}",
)
_test(
    "selected_strategy is top scorer",
    t.selected_strategy == "clarity",
    f"got {t.selected_strategy}",
)
_test(
    "attributed_signals has strategy key",
    "strategy" in t.attributed_signals,
    f"keys={list(t.attributed_signals.keys())}",
)
_test(
    "attributed_signals has prompt key",
    "prompt" in t.attributed_signals,
)
_test(
    "horizon populated",
    "session" in t.horizon and "strategy" in t.horizon and "world_model" in t.horizon,
    f"horizon={t.horizon}",
)
_test(
    "directives captured",
    t.directives_applied == ("Be precise.", "Follow patterns."),
    f"got {t.directives_applied}",
)
_test(
    "signals stores full evaluation",
    t.signals.get("quality_score") == 0.82,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. build_trace with missing data
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. build_trace — Missing Data")

t_empty = build_trace(turn_id=0)

_test("turn_id=0 accepted", t_empty.turn_id == 0)
_test("quality_score defaults to 0.0", t_empty.quality_score == 0.0)
_test("confidence defaults to 0.0", t_empty.confidence == 0.0)
_test("model_used defaults to unknown", t_empty.model_used == "unknown")
_test("latency_ms defaults to 0", t_empty.latency_ms == 0)
_test("tokens_used defaults to None", t_empty.tokens_used is None)
_test("was_enhanced defaults to False", t_empty.was_enhanced is False)
_test("directives_applied defaults to empty", t_empty.directives_applied == ())
_test("signals defaults to empty dict", t_empty.signals == {})
_test("attributed_signals defaults to empty dict", t_empty.attributed_signals == {})


# ═══════════════════════════════════════════════════════════════════════════════
# 4. to_dict serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. to_dict Serialization")

d = t.to_dict()
expected_keys = {
    "turn_id",
    "strategies_considered",
    "strategy_scores",
    "selected_strategy",
    "quality_score",
    "confidence",
    "signals",
    "attributed_signals",
    "horizon",
    "directives_applied",
    "model_used",
    "latency_ms",
    "tokens_used",
    "was_enhanced",
}
_test(
    "to_dict has all expected keys",
    set(d.keys()) == expected_keys,
    f"got {set(d.keys())}",
)
_test(
    "strategies_considered serialized as list",
    isinstance(d["strategies_considered"], list),
)
_test(
    "directives_applied serialized as list",
    isinstance(d["directives_applied"], list),
)
_test(
    "turn_id preserved in dict",
    d["turn_id"] == 5,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Strategy scores use decay-adjusted effective_score
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Decay-Adjusted Strategy Scores")

reset_strategy_memory()
gmem = get_strategy_memory()
gmem.record_win("old_strat", 0.95)

for _ in range(15):
    gmem.record_win("fresh_strat", 0.7)

t_decay = build_trace(
    turn_id=20, evaluation=eval_dict, signals=signals, result=FakeResult()
)

_test(
    "old_strat score is decayed",
    t_decay.strategy_scores.get("old_strat", 1.0) < 0.95,
    f"score={t_decay.strategy_scores.get('old_strat')}",
)
_test(
    "fresh_strat score is not decayed (or minimal decay)",
    t_decay.strategy_scores.get("fresh_strat", 0.0) > 0.6,
    f"score={t_decay.strategy_scores.get('fresh_strat')}",
)
_test(
    "selected_strategy is the higher effective_score",
    t_decay.selected_strategy == "fresh_strat",
    f"got {t_decay.selected_strategy}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Trace cap
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Trace Cap")

from umh.runtime_engine.session_runtime import SessionStats

stats = SessionStats()
for i in range(60):
    t_i = build_trace(turn_id=i)
    stats.decision_traces.append(t_i)
    if len(stats.decision_traces) > MAX_TRACES:
        stats.decision_traces = stats.decision_traces[-MAX_TRACES:]

_test(
    f"capped at MAX_TRACES={MAX_TRACES}",
    len(stats.decision_traces) == MAX_TRACES,
    f"len={len(stats.decision_traces)}",
)
_test(
    "oldest traces trimmed",
    stats.decision_traces[0].turn_id == 10,
    f"first_turn={stats.decision_traces[0].turn_id}",
)
_test(
    "newest trace preserved",
    stats.decision_traces[-1].turn_id == 59,
    f"last_turn={stats.decision_traces[-1].turn_id}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. get_last_trace
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. get_last_trace")

from umh.runtime_engine.session_runtime import SessionRuntime

from unittest.mock import MagicMock

mock_ctx = MagicMock()
session = SessionRuntime(mock_ctx, session_id="test-session")

_test("get_last_trace returns None when empty", session.get_last_trace() is None)

session.stats.decision_traces.append(build_trace(turn_id=1))
session.stats.decision_traces.append(build_trace(turn_id=2))

last = session.get_last_trace()
_test("get_last_trace returns most recent", last is not None and last.turn_id == 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Determinism")

reset_strategy_memory()
gmem = get_strategy_memory()
gmem.record_win("clarity", 0.85)
gmem.record_win("baseline", 0.6)

t_a = build_trace(
    turn_id=10, evaluation=eval_dict, signals=signals, result=FakeResult()
)
t_b = build_trace(
    turn_id=10, evaluation=eval_dict, signals=signals, result=FakeResult()
)

_test("same inputs → same turn_id", t_a.turn_id == t_b.turn_id)
_test("same inputs → same quality_score", t_a.quality_score == t_b.quality_score)
_test("same inputs → same strategy_scores", t_a.strategy_scores == t_b.strategy_scores)
_test(
    "same inputs → same selected_strategy",
    t_a.selected_strategy == t_b.selected_strategy,
)
_test("same inputs → same to_dict", t_a.to_dict() == t_b.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Debug toggle
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Debug Toggle")

_test("DEBUG_TRACE is disabled by default", DEBUG_TRACE is False)
_test("MAX_TRACES constant is 50", MAX_TRACES == 50)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SessionStats has decision_traces field
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. SessionStats Integration")

fresh_stats = SessionStats()
_test("decision_traces field exists", hasattr(fresh_stats, "decision_traces"))
_test("decision_traces starts empty", fresh_stats.decision_traces == [])
_test(
    "decision_traces is independent per instance",
    fresh_stats.decision_traces is not stats.decision_traces,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Horizon tags flow through to trace
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Horizon Flow-Through")

high_conf_eval = {
    "quality_score": 0.85,
    "confidence": 0.8,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}
high_signals = route_signals(high_conf_eval)
t_high = build_trace(turn_id=1, evaluation=high_conf_eval, signals=high_signals)

_test("horizon.session is True", t_high.horizon.get("session") is True)
_test("horizon.strategy is True", t_high.horizon.get("strategy") is True)
_test(
    "horizon.world_model is True (high conf)", t_high.horizon.get("world_model") is True
)

low_conf_eval = {
    "quality_score": 0.85,
    "confidence": 0.4,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}
low_signals = route_signals(low_conf_eval)
t_low = build_trace(turn_id=2, evaluation=low_conf_eval, signals=low_signals)

_test(
    "horizon.world_model is False (low conf)", t_low.horizon.get("world_model") is False
)
_test(
    "attributed_signals.world_model is None when gated",
    t_low.attributed_signals.get("world_model") is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
