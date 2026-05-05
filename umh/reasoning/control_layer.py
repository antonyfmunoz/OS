"""
ControlLayer — deterministic intervention engine for EOS.

Inspects DecisionTrace history and decides whether the next turn needs
behavioral overrides. All rules are deterministic — no LLM calls, no
randomness.

The ControlPolicy evaluates the most recent trace (and optionally the
trailing window) to produce a ControlDecision. That decision flows into
the adaptive prompt pipeline as injected directives and optional strategy
overrides.

Control affects NEXT turn only. The current turn is never re-run.

Disabled by default. Enable via ``ControlPolicy(enabled=True)``.

Usage::

    from umh.reasoning.control_layer import ControlPolicy, ControlDecision

    policy = ControlPolicy(enabled=True)
    decision = policy.evaluate(traces)

    if decision.intervene:
        # attach to trace, inject into adaptive_prompt pipeline
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.reasoning.calibration import CalibratedThresholds
    from umh.decision.trace import DecisionTrace

_log = logging.getLogger(__name__)

HALLUCINATION_CONFIDENCE_THRESHOLD = 0.4
LOW_QUALITY_STREAK_LENGTH = 3
LOW_QUALITY_THRESHOLD = 0.45
BLOCK_CONFIDENCE_THRESHOLD = 0.2


@dataclass(frozen=True)
class ControlDecision:
    """Immutable record of a control layer evaluation."""

    intervene: bool
    reason: str
    override_strategy: str | None = None
    inject_directives: tuple[str, ...] = ()
    block_response: bool = False

    def to_dict(self) -> dict:
        return {
            "intervene": self.intervene,
            "reason": self.reason,
            "override_strategy": self.override_strategy,
            "inject_directives": list(self.inject_directives),
            "block_response": self.block_response,
        }


NO_INTERVENTION = ControlDecision(intervene=False, reason="no_intervention")


class ControlPolicy:
    """Deterministic policy engine that evaluates traces and returns decisions.

    Disabled by default. Pass ``enabled=True`` to activate.
    When disabled, ``evaluate()`` always returns ``NO_INTERVENTION``.

    When ``thresholds`` is provided, uses calibrated values instead of
    module-level constants. This allows the CalibrationEngine to tune
    control sensitivity based on real outcome data.
    """

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def evaluate(
        self,
        traces: list[DecisionTrace],
        thresholds: CalibratedThresholds | None = None,
        goal_mode: object = None,
        goal_state: object = None,
    ) -> ControlDecision:
        """Evaluate the trace window and return a control decision.

        Rules are checked in priority order. The first matching rule wins.
        This ensures deterministic, predictable behavior.

        When ``thresholds`` is provided, uses calibrated values.
        When ``goal_mode`` is provided, threshold sensitivity is adjusted
        per mode (e.g. FAST = more tolerant, ACCURATE = stricter).
        When ``goal_state`` is provided, threshold sensitivity is further
        adjusted based on goal priority (high = stricter, low = looser).
        Otherwise falls back to module-level constants.
        """
        if not self.enabled or not traces:
            return NO_INTERVENTION

        halluc_thresh = (
            thresholds.hallucination_confidence_threshold
            if thresholds
            else HALLUCINATION_CONFIDENCE_THRESHOLD
        )
        lq_thresh = (
            thresholds.low_quality_threshold if thresholds else LOW_QUALITY_THRESHOLD
        )
        block_thresh = (
            thresholds.block_confidence_threshold
            if thresholds
            else BLOCK_CONFIDENCE_THRESHOLD
        )

        # Apply mode-specific sensitivity adjustments
        if goal_mode is not None:
            try:
                from umh.goals.mode import MODE_CONTROL_SENSITIVITY

                adjustments = MODE_CONTROL_SENSITIVITY.get(goal_mode, {})
                if "hallucination_confidence" in adjustments:
                    halluc_thresh *= adjustments["hallucination_confidence"]
                if "low_quality" in adjustments:
                    lq_thresh *= adjustments["low_quality"]
                if "block_confidence" in adjustments:
                    block_thresh *= adjustments["block_confidence"]
            except Exception as e:
                _log.debug("Goal mode sensitivity adjustment failed: %s", e)

        # Apply goal-state priority adjustments
        if goal_state is not None:
            try:
                from umh.goals.state import compute_control_threshold_adjustment

                g_adj = compute_control_threshold_adjustment(goal_state)
                if "hallucination_confidence" in g_adj:
                    halluc_thresh *= g_adj["hallucination_confidence"]
                if "low_quality" in g_adj:
                    lq_thresh *= g_adj["low_quality"]
                if "block_confidence" in g_adj:
                    block_thresh *= g_adj["block_confidence"]
            except Exception as e:
                _log.debug("Goal state threshold adjustment failed: %s", e)

        latest = traces[-1]
        signals = latest.signals or {}
        flags = signals.get("flags", {})

        # Rule 1: Hallucination + low confidence → hard intervention
        hallucination = flags.get("hallucination_risk", False)
        if hallucination and latest.confidence < halluc_thresh:
            _log.info(
                "Control: hallucination + low confidence (%.2f) on turn %d",
                latest.confidence,
                latest.turn_id,
            )
            return ControlDecision(
                intervene=True,
                reason="hallucination_low_confidence",
                inject_directives=(
                    "Be precise — only state facts you are confident about.",
                    "Do not assume unknown facts. If uncertain, say so.",
                ),
                block_response=latest.confidence < block_thresh,
            )

        # Rule 2: Repeated low quality streak → strategy override
        if len(traces) >= LOW_QUALITY_STREAK_LENGTH:
            recent = traces[-LOW_QUALITY_STREAK_LENGTH:]
            scores = [t.quality_score for t in recent]
            if all(s < lq_thresh for s in scores):
                avg = sum(scores) / len(scores)
                _log.info(
                    "Control: low quality streak (avg %.2f) over last %d turns",
                    avg,
                    LOW_QUALITY_STREAK_LENGTH,
                )
                return ControlDecision(
                    intervene=True,
                    reason="low_quality_streak",
                    override_strategy="structured",
                    inject_directives=(
                        "Recent responses scored low. "
                        "Switch to structured, precise output.",
                    ),
                )

        # Rule 3: Incomplete response → directive injection
        if flags.get("incomplete", False):
            _log.info("Control: incomplete response on turn %d", latest.turn_id)
            return ControlDecision(
                intervene=True,
                reason="incomplete_response",
                inject_directives=(
                    "Fully answer all parts of the question.",
                    "Ensure the response has a clear conclusion.",
                ),
            )

        return NO_INTERVENTION


def get_last_control_decision(traces: list) -> ControlDecision | None:
    """Return the control_decision from the most recent trace, or None."""
    if not traces:
        return None
    latest = traces[-1]
    return getattr(latest, "control_decision", None)
