"""
Tests for Signal Attribution Layer.

Validates:
    - Each subsystem receives only its intended signals
    - Low-confidence signals do not reach world_model
    - Strategy signals contain only performance metrics
    - Prompt signals contain only corrective flags
    - World model signals are gated by confidence threshold
    - Deterministic behavior preserved
    - Backward compatibility with flat evaluation dicts
    - evaluate_outcome includes attributed signals
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


from umh.runtime_engine.signal_router import (
    AttributedSignals,
    PromptSignal,
    StrategySignal,
    WorldModelSignal,
    WORLD_MODEL_CONFIDENCE_THRESHOLD,
    route_signals,
)
from umh.runtime_engine.outcome_evaluator import evaluate_outcome


# ═════════════════════════════════════════════════════════════════════════════
# 1. Signal routing — basic structure
# ═════════════════════════════════════════════════════════════════════════════

_section("1. Signal Routing Structure")

eval_high = {
    "quality_score": 0.85,
    "confidence": 0.9,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}

signals = route_signals(eval_high)

_test(
    "returns AttributedSignals",
    isinstance(signals, AttributedSignals),
)
_test(
    "strategy is StrategySignal",
    isinstance(signals.strategy, StrategySignal),
)
_test(
    "prompt is PromptSignal",
    isinstance(signals.prompt, PromptSignal),
)
_test(
    "world_model is WorldModelSignal (high confidence)",
    isinstance(signals.world_model, WorldModelSignal),
)
_test(
    "raw is preserved",
    signals.raw == eval_high,
)


# ═════════════════════════════════════════════════════════════════════════════
# 2. Strategy signal isolation
# ═════════════════════════════════════════════════════════════════════════════

_section("2. Strategy Signal Isolation")

eval_with_flags = {
    "quality_score": 0.7,
    "confidence": 0.8,
    "flags": {
        "hallucination_risk": True,
        "low_information": True,
        "incomplete": True,
    },
    "reason": "some issues",
}

signals_flagged = route_signals(eval_with_flags)

strategy_dict = signals_flagged.strategy.to_dict()
_test(
    "strategy contains quality_score",
    "quality_score" in strategy_dict,
)
_test(
    "strategy contains confidence",
    "confidence" in strategy_dict,
)
_test(
    "strategy does NOT contain flags",
    "flags" not in strategy_dict,
    f"keys={list(strategy_dict.keys())}",
)
_test(
    "strategy does NOT contain hallucination_risk",
    "hallucination_risk" not in strategy_dict,
)
_test(
    "strategy does NOT contain reason",
    "reason" not in strategy_dict,
)
_test(
    "strategy score matches input",
    strategy_dict["quality_score"] == 0.7,
)


# ═════════════════════════════════════════════════════════════════════════════
# 3. Prompt signal isolation
# ═════════════════════════════════════════════════════════════════════════════

_section("3. Prompt Signal Isolation")

prompt_dict = signals_flagged.prompt.to_dict()
_test(
    "prompt contains flags",
    "flags" in prompt_dict,
)
_test(
    "prompt contains reason",
    "reason" in prompt_dict,
)
_test(
    "prompt does NOT contain quality_score",
    "quality_score" not in prompt_dict,
    f"keys={list(prompt_dict.keys())}",
)
_test(
    "prompt does NOT contain confidence",
    "confidence" not in prompt_dict,
)
_test(
    "prompt flags match input",
    prompt_dict["flags"]["hallucination_risk"] is True
    and prompt_dict["flags"]["incomplete"] is True
    and prompt_dict["flags"]["low_information"] is True,
)


# ═════════════════════════════════════════════════════════════════════════════
# 4. World model confidence gating
# ═════════════════════════════════════════════════════════════════════════════

_section("4. World Model Confidence Gating")

eval_low_conf = {
    "quality_score": 0.9,
    "confidence": 0.3,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}

signals_low = route_signals(eval_low_conf)
_test(
    "low-confidence → world_model is None",
    signals_low.world_model is None,
    f"confidence={eval_low_conf['confidence']}",
)

eval_threshold = {
    "quality_score": 0.9,
    "confidence": 0.6,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}

signals_at_threshold = route_signals(eval_threshold)
_test(
    "at-threshold → world_model routed",
    signals_at_threshold.world_model is not None,
    f"confidence={eval_threshold['confidence']}",
)

_test(
    "WORLD_MODEL_CONFIDENCE_THRESHOLD is 0.6",
    WORLD_MODEL_CONFIDENCE_THRESHOLD == 0.6,
)

eval_just_below = {
    "quality_score": 0.9,
    "confidence": 0.59,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}

signals_below = route_signals(eval_just_below)
_test(
    "just below threshold → world_model is None",
    signals_below.world_model is None,
    f"confidence={eval_just_below['confidence']}",
)


# ═════════════════════════════════════════════════════════════════════════════
# 5. World model outcome classification
# ═════════════════════════════════════════════════════════════════════════════

_section("5. World Model Outcome Classification")

eval_good = {
    "quality_score": 0.85,
    "confidence": 0.9,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "acceptable",
}
signals_good = route_signals(eval_good)
_test(
    "high quality → outcome=good",
    signals_good.world_model is not None and signals_good.world_model.outcome == "good",
)

eval_poor = {
    "quality_score": 0.2,
    "confidence": 0.8,
    "flags": {"hallucination_risk": True, "low_information": True, "incomplete": True},
    "reason": "error signal",
}
signals_poor = route_signals(eval_poor)
_test(
    "low quality → outcome=poor",
    signals_poor.world_model is not None and signals_poor.world_model.outcome == "poor",
)

eval_mid = {
    "quality_score": 0.55,
    "confidence": 0.8,
    "flags": {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "moderate",
}
signals_mid = route_signals(eval_mid)
_test(
    "mid quality → outcome=None (neutral)",
    signals_mid.world_model is not None and signals_mid.world_model.outcome is None,
)


# ═════════════════════════════════════════════════════════════════════════════
# 6. Cross-contamination prevention
# ═════════════════════════════════════════════════════════════════════════════

_section("6. Cross-Contamination Prevention")

eval_halluc_high_score = {
    "quality_score": 0.95,
    "confidence": 0.9,
    "flags": {
        "hallucination_risk": True,
        "low_information": False,
        "incomplete": False,
    },
    "reason": "hallucination detected",
}
signals_cross = route_signals(eval_halluc_high_score)

_test(
    "strategy does not see hallucination flag",
    "hallucination_risk" not in signals_cross.strategy.to_dict(),
)
_test(
    "strategy still gets the high score (flag-agnostic)",
    signals_cross.strategy.quality_score == 0.95,
)
_test(
    "prompt sees hallucination flag",
    signals_cross.prompt.hallucination_risk is True,
)
_test(
    "prompt does not carry quality_score",
    "quality_score" not in signals_cross.prompt.to_dict(),
)


# ═════════════════════════════════════════════════════════════════════════════
# 7. Frozen immutability
# ═════════════════════════════════════════════════════════════════════════════

_section("7. Signal Immutability")

sig = route_signals(eval_high)
try:
    sig.strategy.quality_score = 0.0  # type: ignore[misc]
    _test("strategy signal is immutable", False, "mutation succeeded")
except (
    AttributeError,
    FrozenInstanceError if "FrozenInstanceError" in dir() else AttributeError,
):
    _test("strategy signal is immutable", True)

try:
    sig.prompt.hallucination_risk = True  # type: ignore[misc]
    _test("prompt signal is immutable", False, "mutation succeeded")
except (
    AttributeError,
    FrozenInstanceError if "FrozenInstanceError" in dir() else AttributeError,
):
    _test("prompt signal is immutable", True)


# ═════════════════════════════════════════════════════════════════════════════
# 8. evaluate_outcome includes attributed signals
# ═════════════════════════════════════════════════════════════════════════════

_section("8. evaluate_outcome Attribution")

result = evaluate_outcome(
    input_text="What should I focus on for outreach today?",
    output_text=(
        "Focus on sending 20 DMs to fitness coaches on Instagram. "
        "Track reply rates. Follow up within 24 hours on all responses. "
        "Target coaches with 5K-50K followers who post about transformation."
    ),
)

_test(
    "evaluation contains 'signals' key",
    "signals" in result,
    f"keys={list(result.keys())}",
)

if "signals" in result:
    sig_dict = result["signals"]
    _test(
        "signals.strategy exists",
        "strategy" in sig_dict,
    )
    _test(
        "signals.prompt exists",
        "prompt" in sig_dict,
    )
    _test(
        "signals.world_model exists or is None",
        "world_model" in sig_dict,
    )
    _test(
        "signals.strategy has quality_score",
        sig_dict["strategy"].get("quality_score") is not None,
    )
    _test(
        "signals.prompt has flags",
        "flags" in sig_dict.get("prompt", {}),
    )
    _test(
        "signals.strategy does NOT have flags",
        "flags" not in sig_dict.get("strategy", {}),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 9. to_dict serialization
# ═════════════════════════════════════════════════════════════════════════════

_section("9. Serialization")

signals = route_signals(eval_high)
d = signals.to_dict()

_test(
    "to_dict has all 5 keys",
    set(d.keys()) == {"strategy", "prompt", "world_model", "horizon", "raw"},
    f"keys={set(d.keys())}",
)
_test(
    "strategy serializes correctly",
    d["strategy"]["quality_score"] == 0.85 and d["strategy"]["confidence"] == 0.9,
)
_test(
    "prompt serializes correctly",
    "flags" in d["prompt"] and "reason" in d["prompt"],
)
_test(
    "world_model serializes when present",
    d["world_model"] is not None and "outcome" in d["world_model"],
)

# Low confidence → world_model is None in serialized form
signals_lo = route_signals(eval_low_conf)
d_lo = signals_lo.to_dict()
_test(
    "world_model serializes as None when gated",
    d_lo["world_model"] is None,
)


# ═════════════════════════════════════════════════════════════════════════════
# 10. Deterministic behavior
# ═════════════════════════════════════════════════════════════════════════════

_section("10. Deterministic Behavior")

r1 = route_signals(eval_high)
r2 = route_signals(eval_high)

_test(
    "same input → same strategy signal",
    r1.strategy.to_dict() == r2.strategy.to_dict(),
)
_test(
    "same input → same prompt signal",
    r1.prompt.to_dict() == r2.prompt.to_dict(),
)
_test(
    "same input → same world_model signal",
    (r1.world_model is None and r2.world_model is None)
    or (
        r1.world_model is not None
        and r2.world_model is not None
        and r1.world_model.to_dict() == r2.world_model.to_dict()
    ),
)


# ═════════════════════════════════════════════════════════════════════════════
# 11. adaptive_prompt reads prompt signals
# ═════════════════════════════════════════════════════════════════════════════

_section("11. adaptive_prompt Uses Prompt Signals")

from umh.runtime_engine.adaptive_prompt import _get_prompt_flags


eval_with_signals = {
    "quality_score": 0.3,
    "confidence": 0.9,
    "flags": {
        "hallucination_risk": True,
        "low_information": False,
        "incomplete": True,
    },
    "reason": "bad",
    "signals": {
        "prompt": {
            "flags": {
                "hallucination_risk": True,
                "low_information": False,
                "incomplete": True,
            },
            "reason": "bad",
        },
        "strategy": {"quality_score": 0.3, "confidence": 0.9},
        "world_model": None,
    },
}

flags_from_attributed = _get_prompt_flags(eval_with_signals)
_test(
    "prefers attributed prompt signals",
    flags_from_attributed.get("hallucination_risk") is True
    and flags_from_attributed.get("incomplete") is True,
)

eval_no_signals = {
    "quality_score": 0.3,
    "confidence": 0.9,
    "flags": {
        "hallucination_risk": True,
        "low_information": True,
        "incomplete": False,
    },
    "reason": "fallback",
}

flags_fallback = _get_prompt_flags(eval_no_signals)
_test(
    "falls back to flat flags when no signals key",
    flags_fallback.get("hallucination_risk") is True
    and flags_fallback.get("low_information") is True,
)


# ═════════════════════════════════════════════════════════════════════════════
# 12. update_world_model respects gating
# ═════════════════════════════════════════════════════════════════════════════

_section("12. update_world_model Gating")

from unittest.mock import patch, MagicMock

_wm_calls: list[dict] = []


class FakeWorldModel:
    def __init__(self, org_id):
        self.org_id = org_id

    def update_from_interaction(self, message, response, outcome=None):
        _wm_calls.append({"message": message, "response": response, "outcome": outcome})


with patch("umh.runtime_engine.world_model.WorldModel", FakeWorldModel):
    from umh.runtime_engine.execution_spine import update_world_model

    # Case 1: attributed signal with outcome
    _wm_calls.clear()
    wm_sig = WorldModelSignal(outcome="good", quality_score=0.85, confidence=0.9)
    update_world_model("test", "response", "org1", world_model_signal=wm_sig)
    _test(
        "attributed signal → world model called with outcome",
        len(_wm_calls) == 1 and _wm_calls[0]["outcome"] == "good",
        f"calls={_wm_calls}",
    )

    # Case 2: attributed signal is None (gated)
    _wm_calls.clear()
    update_world_model(
        "test", "response", "org1", world_model_signal=None, evaluation=None
    )
    _test(
        "gated signal → world model NOT called",
        len(_wm_calls) == 0,
        f"calls={len(_wm_calls)}",
    )

    # Case 3: fallback path with low confidence (no attributed signal)
    _wm_calls.clear()
    eval_low = {"quality_score": 0.9, "confidence": 0.3}
    update_world_model("test", "response", "org1", evaluation=eval_low)
    _test(
        "fallback low confidence → world model NOT called",
        len(_wm_calls) == 0,
        f"calls={len(_wm_calls)}",
    )

    # Case 4: fallback path with high confidence
    _wm_calls.clear()
    eval_ok = {"quality_score": 0.85, "confidence": 0.8}
    update_world_model("test", "response", "org1", evaluation=eval_ok)
    _test(
        "fallback high confidence → world model called",
        len(_wm_calls) == 1 and _wm_calls[0]["outcome"] == "good",
        f"calls={_wm_calls}",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
