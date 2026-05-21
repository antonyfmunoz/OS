"""
OutcomeFeedback — external outcome signals that ground learning in reality.

The system's internal evaluators (quality_score, goal_score, delta) assess
their own outputs. Without external validation, a consistently-wrong
strategy can still accumulate high internal scores (self-reinforcing drift).

This module introduces external outcome signals — user feedback, system
evaluations, external API results — that retroactively adjust the memory
layers (StrategyMemory, DirectiveMemory, GoalTracker) to reflect whether
a turn's output *actually worked*.

Key design:
    - Outcomes arrive asynchronously (possibly N turns after the decision).
    - Each outcome links to a specific turn_id via the DecisionTrace.
    - Processing is ordered: outcomes applied in arrival order for determinism.
    - Blend formula: adjusted = internal * (1 - oc) + outcome.success * oc
      where oc = outcome.confidence. High-confidence external signals
      dominate; low-confidence ones nudge.
    - No LLM calls. No randomness. Deterministic given same input order.

Usage::

    from umh.feedback.outcome_feedback import Outcome, OutcomeSource, OutcomeStore

    store = OutcomeStore()
    outcome = Outcome(
        turn_id=5,
        success=0.9,
        source=OutcomeSource.USER_FEEDBACK,
        confidence=0.8,
    )
    store.record(outcome)

    # SessionRuntime.record_outcome() handles the full pipeline:
    # lookup trace → extract strategy → apply to all memory layers.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

_log = logging.getLogger(__name__)

OUTCOME_CONFIDENCE_FLOOR = 0.1
MAX_PENDING_OUTCOMES = 200


class OutcomeSource(Enum):
    """Where the outcome signal originated."""

    USER_FEEDBACK = "user_feedback"
    SYSTEM_EVAL = "system_eval"
    EXTERNAL_API = "external_api"


@dataclass(frozen=True)
class Outcome:
    """A single external outcome signal linked to a decision turn."""

    turn_id: int
    success: float
    source: OutcomeSource
    confidence: float = 0.8
    outcome_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "outcome_id": self.outcome_id,
            "turn_id": self.turn_id,
            "success": round(self.success, 4),
            "source": self.source.value,
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
        }


NO_OUTCOME = Outcome(
    turn_id=-1,
    success=0.0,
    source=OutcomeSource.SYSTEM_EVAL,
    confidence=0.0,
    outcome_id="none",
    timestamp=0.0,
)


def compute_outcome_adjusted_score(
    internal_score: float,
    outcome_success: float,
    outcome_confidence: float,
) -> float:
    """Blend internal evaluation with external outcome signal.

    When outcome_confidence is high, external signal dominates.
    When low, internal signal dominates. Linear interpolation.

    Returns a float in [0.0, 1.0].
    """
    oc = max(0.0, min(1.0, outcome_confidence))
    blended = internal_score * (1.0 - oc) + outcome_success * oc
    return max(0.0, min(1.0, blended))


class OutcomeStore:
    """Ordered collection of outcomes for a session.

    Maintains insertion order for deterministic replay.
    Outcomes are keyed by turn_id for delayed-feedback lookup.
    """

    def __init__(self) -> None:
        self._outcomes: list[Outcome] = []
        self._by_turn: dict[int, list[Outcome]] = {}

    def record(self, outcome: Outcome) -> None:
        """Add an outcome. Maintains insertion order."""
        if outcome.confidence < OUTCOME_CONFIDENCE_FLOOR:
            _log.debug(
                "Outcome %s below confidence floor (%.2f < %.2f), skipped",
                outcome.outcome_id,
                outcome.confidence,
                OUTCOME_CONFIDENCE_FLOOR,
            )
            return

        self._outcomes.append(outcome)
        if len(self._outcomes) > MAX_PENDING_OUTCOMES:
            removed = self._outcomes.pop(0)
            turns = self._by_turn.get(removed.turn_id, [])
            if removed in turns:
                turns.remove(removed)

        self._by_turn.setdefault(outcome.turn_id, []).append(outcome)

    def get_for_turn(self, turn_id: int) -> list[Outcome]:
        """Return all outcomes for a specific turn, in insertion order."""
        return list(self._by_turn.get(turn_id, []))

    def get_latest_for_turn(self, turn_id: int) -> Outcome | None:
        """Return the most recent outcome for a turn, or None."""
        outcomes = self._by_turn.get(turn_id, [])
        return outcomes[-1] if outcomes else None

    @property
    def total_outcomes(self) -> int:
        return len(self._outcomes)

    @property
    def turns_with_outcomes(self) -> set[int]:
        return {o.turn_id for o in self._outcomes}

    def all_outcomes(self) -> list[Outcome]:
        """Return all outcomes in insertion order."""
        return list(self._outcomes)

    def to_dict(self) -> dict:
        return {
            "total": self.total_outcomes,
            "turns_covered": sorted(self.turns_with_outcomes),
            "outcomes": [o.to_dict() for o in self._outcomes],
        }


def apply_outcome_to_strategy_memory(
    strategy_name: str,
    internal_quality: float,
    outcome: Outcome,
    attribution_weight: float = 1.0,
) -> float:
    """Apply an outcome signal to StrategyMemory for a specific strategy.

    Computes the blended score and calls apply_outcome() on the memory.
    The attribution_weight scales the effective confidence — a factor
    with 30% attribution gets 30% of the outcome's correction strength.
    Returns the adjusted score that was applied.
    """
    adjusted = compute_outcome_adjusted_score(
        internal_quality, outcome.success, outcome.confidence
    )
    effective_confidence = outcome.confidence * max(0.0, min(1.0, attribution_weight))

    try:
        from umh.strategy.memory import get_strategy_memory

        mem = get_strategy_memory()
        mem.apply_outcome(strategy_name, adjusted, effective_confidence)
    except Exception as e:
        _log.debug("Strategy outcome application failed: %s", e)

    return adjusted


def apply_outcome_to_directive_memory(
    directive_key: str,
    internal_quality: float,
    outcome: Outcome,
    attribution_weight: float = 1.0,
) -> float:
    """Apply an outcome signal to DirectiveMemory for a specific directive.

    The attribution_weight scales the effective confidence.
    Returns the adjusted score that was applied.
    """
    adjusted = compute_outcome_adjusted_score(
        internal_quality, outcome.success, outcome.confidence
    )
    effective_confidence = outcome.confidence * max(0.0, min(1.0, attribution_weight))

    try:
        from umh.runtime_engine.directive_memory import get_directive_memory

        mem = get_directive_memory()
        mem.apply_outcome(directive_key, adjusted, effective_confidence)
    except Exception as e:
        _log.debug("Directive outcome application failed: %s", e)

    return adjusted


def apply_outcome_to_goal_tracker(
    goal_id: str,
    internal_goal_score: float,
    outcome: Outcome,
    goal_registry: object | None = None,
    attribution_weight: float = 1.0,
) -> float:
    """Apply an outcome signal to a GoalTracker.

    The attribution_weight scales the effective confidence.
    Returns the adjusted score that was applied.
    """
    adjusted = compute_outcome_adjusted_score(
        internal_goal_score, outcome.success, outcome.confidence
    )
    effective_confidence = outcome.confidence * max(0.0, min(1.0, attribution_weight))

    if goal_registry is not None:
        try:
            tracker = goal_registry.get_tracker(goal_id)
            if tracker is not None:
                tracker.apply_outcome(adjusted, effective_confidence)
        except Exception as e:
            _log.debug("Goal tracker outcome application failed: %s", e)

    return adjusted
