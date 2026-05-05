"""
SignalRouter — decouples evaluation signals by consumer purpose.

Each subsystem receives only the signals relevant to its function:
    - strategy: raw performance metrics (score + confidence)
    - prompt: corrective flags (hallucination, incompleteness)
    - world_model: high-confidence observations for long-term learning

Confidence gating happens here, at the routing boundary, so consumers
never need to filter individually.

No LLM calls. No randomness. Pure deterministic routing.

Usage::

    from umh.runtime_engine.signal_router import route_signals, AttributedSignals

    evaluation = evaluate_outcome(input_text, output_text, context)
    signals = route_signals(evaluation)

    # Each consumer gets its typed view:
    signals.strategy   # {"quality_score": 0.85, "confidence": 0.9}
    signals.prompt     # {"flags": {...}, "low_quality_streak": False}
    signals.world_model  # {"outcome": "good", ...} or None if low-confidence
"""

from __future__ import annotations

from dataclasses import dataclass

WORLD_MODEL_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class StrategySignal:
    """Signals for strategy_memory: raw performance only."""

    quality_score: float
    confidence: float

    def to_dict(self) -> dict:
        return {"quality_score": self.quality_score, "confidence": self.confidence}


@dataclass(frozen=True)
class PromptSignal:
    """Signals for adaptive_prompt: corrective flags only."""

    hallucination_risk: bool
    incomplete: bool
    low_information: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "flags": {
                "hallucination_risk": self.hallucination_risk,
                "incomplete": self.incomplete,
                "low_information": self.low_information,
            },
            "reason": self.reason,
        }


@dataclass(frozen=True)
class WorldModelSignal:
    """Signals for world_model: high-confidence observations only."""

    outcome: str | None
    quality_score: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class HorizonTag:
    """Which memory horizons this evaluation applies to."""

    session: bool
    strategy: bool
    world_model: bool

    def to_dict(self) -> dict:
        return {
            "session": self.session,
            "strategy": self.strategy,
            "world_model": self.world_model,
        }


@dataclass(frozen=True)
class AttributedSignals:
    """Container for all routed signals. Consumers access their typed view."""

    strategy: StrategySignal
    prompt: PromptSignal
    world_model: WorldModelSignal | None
    horizon: HorizonTag
    raw: dict

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.to_dict(),
            "prompt": self.prompt.to_dict(),
            "world_model": self.world_model.to_dict() if self.world_model else None,
            "horizon": self.horizon.to_dict(),
            "raw": self.raw,
        }


def route_signals(
    evaluation: dict,
    wm_confidence_threshold: float | None = None,
) -> AttributedSignals:
    """Route a flat evaluation dict into purpose-specific signal views.

    Confidence gating for world_model happens here — if the evaluator
    confidence is below threshold, world_model receives None.

    When ``wm_confidence_threshold`` is provided (from calibration),
    uses that instead of the module-level constant.
    """
    wm_thresh = (
        wm_confidence_threshold
        if wm_confidence_threshold is not None
        else WORLD_MODEL_CONFIDENCE_THRESHOLD
    )

    quality_score = evaluation.get("quality_score", 0.5)
    confidence = evaluation.get("confidence", 0.5)
    flags = evaluation.get("flags", {})
    reason = evaluation.get("reason", "")

    strategy = StrategySignal(
        quality_score=quality_score,
        confidence=confidence,
    )

    prompt = PromptSignal(
        hallucination_risk=bool(flags.get("hallucination_risk", False)),
        incomplete=bool(flags.get("incomplete", False)),
        low_information=bool(flags.get("low_information", False)),
        reason=reason,
    )

    world_model: WorldModelSignal | None = None
    if confidence >= wm_thresh:
        outcome: str | None = None
        if quality_score >= 0.7:
            outcome = "good"
        elif quality_score < 0.4:
            outcome = "poor"
        world_model = WorldModelSignal(
            outcome=outcome,
            quality_score=quality_score,
            confidence=confidence,
        )

    horizon = HorizonTag(
        session=True,
        strategy=True,
        world_model=confidence >= wm_thresh,
    )

    return AttributedSignals(
        strategy=strategy,
        prompt=prompt,
        world_model=world_model,
        horizon=horizon,
        raw=evaluation,
    )
