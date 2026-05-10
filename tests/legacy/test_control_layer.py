"""
Tests for the Control Layer.

Validates:
    - Deterministic outputs across identical inputs
    - Intervention triggers correctly on hallucination + low confidence
    - Intervention triggers on low quality streak
    - Intervention triggers on incomplete response
    - No intervention when signals are normal
    - Strategy override works
    - Directives injected correctly
    - No effect when disabled
    - ControlDecision is frozen (immutable)
    - to_dict serialization is complete
    - get_last_control_decision helper works
    - Integration with DecisionTrace
    - Pending directives/strategy accessible via SessionRuntime
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


from umh.runtime_engine.control_layer import (
    ControlDecision,
    ControlPolicy,
    NO_INTERVENTION,
    get_last_control_decision,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace


def _make_trace(
    turn_id: int = 1,
    quality_score: float = 0.7,
    confidence: float = 0.8,
    hallucination_risk: bool = False,
    incomplete: bool = False,
    control_decision: object | None = None,
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
        control_decision=control_decision,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ControlDecision immutability
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. ControlDecision Immutability")

cd = ControlDecision(
    intervene=True,
    reason="test",
    inject_directives=("a", "b"),
)

_test("ControlDecision is frozen", hasattr(cd, "__dataclass_fields__"))

try:
    cd.intervene = False
    _test("mutation blocked", False, "should have raised FrozenInstanceError")
except AttributeError:
    _test("mutation blocked", True)

_test("inject_directives is tuple", isinstance(cd.inject_directives, tuple))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. to_dict serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. to_dict Serialization")

d = cd.to_dict()
expected_keys = {
    "intervene",
    "reason",
    "override_strategy",
    "inject_directives",
    "block_response",
}

_test("to_dict has all keys", set(d.keys()) == expected_keys, f"got {set(d.keys())}")
_test("inject_directives serialized as list", isinstance(d["inject_directives"], list))
_test("intervene is True", d["intervene"] is True)
_test("reason is test", d["reason"] == "test")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Disabled policy always returns NO_INTERVENTION
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Disabled Policy")

disabled = ControlPolicy(enabled=False)
traces = [_make_trace(hallucination_risk=True, confidence=0.1)]

result = disabled.evaluate(traces)
_test("disabled returns NO_INTERVENTION", result is NO_INTERVENTION)
_test("no intervention", result.intervene is False)
_test("reason is no_intervention", result.reason == "no_intervention")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Empty traces returns NO_INTERVENTION
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Empty Traces")

enabled = ControlPolicy(enabled=True)
result = enabled.evaluate([])
_test("empty traces → no intervention", result is NO_INTERVENTION)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Normal signals — no intervention
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Normal Signals")

normal_traces = [_make_trace(quality_score=0.8, confidence=0.9)]
result = enabled.evaluate(normal_traces)
_test("normal signals → no intervention", result.intervene is False)
_test("reason is no_intervention", result.reason == "no_intervention")
_test("no override_strategy", result.override_strategy is None)
_test("no directives", len(result.inject_directives) == 0)
_test("no block", result.block_response is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Hallucination + low confidence triggers intervention
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Hallucination + Low Confidence")

halluc_traces = [_make_trace(hallucination_risk=True, confidence=0.3)]
result = enabled.evaluate(halluc_traces)

_test("intervene is True", result.intervene is True)
_test(
    "reason is hallucination_low_confidence",
    result.reason == "hallucination_low_confidence",
)
_test("has directives", len(result.inject_directives) > 0)
_test(
    "directives mention precision",
    any("precise" in d.lower() for d in result.inject_directives),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Hallucination + HIGH confidence → no intervention
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Hallucination + High Confidence (no trigger)")

high_conf_halluc = [_make_trace(hallucination_risk=True, confidence=0.8)]
result = enabled.evaluate(high_conf_halluc)
_test("high confidence halluc → no intervention", result.intervene is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Block response on very low confidence
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Block Response Threshold")

very_low = [_make_trace(hallucination_risk=True, confidence=0.1)]
result = enabled.evaluate(very_low)
_test("very low confidence → block_response", result.block_response is True)

borderline = [_make_trace(hallucination_risk=True, confidence=0.3)]
result = enabled.evaluate(borderline)
_test("borderline confidence → no block", result.block_response is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Low quality streak triggers strategy override
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Low Quality Streak")

streak_traces = [
    _make_trace(turn_id=1, quality_score=0.3, confidence=0.8),
    _make_trace(turn_id=2, quality_score=0.35, confidence=0.8),
    _make_trace(turn_id=3, quality_score=0.4, confidence=0.8),
]
result = enabled.evaluate(streak_traces)

_test("streak intervenes", result.intervene is True)
_test("reason is low_quality_streak", result.reason == "low_quality_streak")
_test("override_strategy is structured", result.override_strategy == "structured")
_test("has directives", len(result.inject_directives) > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Non-streak (mixed quality) — no intervention
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Mixed Quality (no streak)")

mixed_traces = [
    _make_trace(turn_id=1, quality_score=0.3),
    _make_trace(turn_id=2, quality_score=0.8),
    _make_trace(turn_id=3, quality_score=0.3),
]
result = enabled.evaluate(mixed_traces)
_test("mixed quality → no streak intervention", result.reason != "low_quality_streak")


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Incomplete response triggers directives
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Incomplete Response")

incomplete_traces = [_make_trace(incomplete=True)]
result = enabled.evaluate(incomplete_traces)

_test("incomplete → intervene", result.intervene is True)
_test("reason is incomplete_response", result.reason == "incomplete_response")
_test("has directives", len(result.inject_directives) > 0)
_test(
    "directives mention answer/conclusion",
    any(
        "answer" in d.lower() or "conclusion" in d.lower()
        for d in result.inject_directives
    ),
)
_test("no strategy override for incomplete", result.override_strategy is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Priority: hallucination wins over incomplete
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Rule Priority")

both_traces = [_make_trace(hallucination_risk=True, confidence=0.2, incomplete=True)]
result = enabled.evaluate(both_traces)
_test(
    "hallucination takes priority over incomplete",
    result.reason == "hallucination_low_confidence",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Determinism
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Determinism")

det_traces = [_make_trace(hallucination_risk=True, confidence=0.3)]
r1 = enabled.evaluate(det_traces)
r2 = enabled.evaluate(det_traces)

_test("same input → same intervene", r1.intervene == r2.intervene)
_test("same input → same reason", r1.reason == r2.reason)
_test("same input → same directives", r1.inject_directives == r2.inject_directives)
_test(
    "same input → same override_strategy", r1.override_strategy == r2.override_strategy
)
_test("same input → same block_response", r1.block_response == r2.block_response)
_test("same input → same to_dict", r1.to_dict() == r2.to_dict())


# ═══════════════════════════════════════════════════════════════════════════════
# 14. DecisionTrace includes control_decision
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. DecisionTrace Integration")

ctrl = ControlDecision(
    intervene=True,
    reason="test_reason",
    inject_directives=("d1", "d2"),
)
trace_with_ctrl = _make_trace(control_decision=ctrl)

_test("control_decision attached", trace_with_ctrl.control_decision is ctrl)
_test("control_decision in to_dict", "control_decision" in trace_with_ctrl.to_dict())
_test(
    "control_decision.reason in serialized",
    trace_with_ctrl.to_dict()["control_decision"]["reason"] == "test_reason",
)

trace_without = _make_trace()
_test("control_decision is None by default", trace_without.control_decision is None)
_test(
    "no control_decision in to_dict when None",
    "control_decision" not in trace_without.to_dict(),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. build_trace accepts control_decision
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. build_trace with control_decision")

from umh.strategy.memory import reset_strategy_memory, get_strategy_memory

reset_strategy_memory()
get_strategy_memory().record_win("baseline", 0.7)

bt = build_trace(turn_id=99, control_decision=ctrl)
_test("build_trace passes control_decision through", bt.control_decision is ctrl)

bt_none = build_trace(turn_id=100)
_test("build_trace defaults control_decision to None", bt_none.control_decision is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. get_last_control_decision helper
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. get_last_control_decision")

_test("empty traces → None", get_last_control_decision([]) is None)

traces_with = [
    _make_trace(turn_id=1),
    _make_trace(turn_id=2, control_decision=ctrl),
]
last = get_last_control_decision(traces_with)
_test("returns control from last trace", last is ctrl)

traces_without = [_make_trace(turn_id=1), _make_trace(turn_id=2)]
_test("returns None when no control", get_last_control_decision(traces_without) is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. SessionRuntime integration (control_enabled)
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. SessionRuntime Integration")

from unittest.mock import MagicMock
from umh.runtime_engine.session_runtime import SessionRuntime

mock_ctx = MagicMock()

session_off = SessionRuntime(mock_ctx, session_id="test-off")
_test("control disabled by default", session_off._control_policy is None)
_test("pending directives empty", session_off.get_pending_control_directives() == [])
_test("pending strategy None", session_off.get_pending_strategy_override() is None)

session_on = SessionRuntime(mock_ctx, session_id="test-on", control_enabled=True)
_test("control enabled when requested", session_on._control_policy is not None)
_test("control policy is enabled", session_on._control_policy.enabled is True)

# Verify get_last_control_decision on empty session
_test(
    "no control decision on fresh session",
    session_on.get_last_control_decision() is None,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. NO_INTERVENTION singleton
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. NO_INTERVENTION Singleton")

_test(
    "NO_INTERVENTION is ControlDecision", isinstance(NO_INTERVENTION, ControlDecision)
)
_test("NO_INTERVENTION.intervene is False", NO_INTERVENTION.intervene is False)
_test("NO_INTERVENTION.reason", NO_INTERVENTION.reason == "no_intervention")
_test(
    "NO_INTERVENTION.override_strategy is None",
    NO_INTERVENTION.override_strategy is None,
)
_test(
    "NO_INTERVENTION.inject_directives empty",
    len(NO_INTERVENTION.inject_directives) == 0,
)
_test(
    "NO_INTERVENTION.block_response is False", NO_INTERVENTION.block_response is False
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
