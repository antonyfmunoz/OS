"""
ConvergenceEngine — trajectory-aware stability assessment for EOS.

Evaluates whether recent session behavior is stably good, temporarily
green, oscillating, or degrading.  Produces a ConvergenceDecision that
queues corrective state for the *next* turn — never modifies the current
turn or blocks response generation.

Sits after the control layer in the post-turn pipeline:

    spine result → evaluation → signals → trace → control → **convergence**

Control is reactive (single turn).  Convergence is trajectory-aware
(sliding window of turns).

All rules are deterministic — no LLM calls, no randomness.
Disabled by default.  Enable via ``ConvergenceEngine(enabled=True)``.

Usage::

    from umh.runtime_engine.convergence import ConvergenceEngine, ConvergenceDecision

    engine = ConvergenceEngine(enabled=True)
    decision = engine.evaluate(traces)

    if decision.action != ConvergenceAction.NONE:
        # queue corrective state for next turn
        ...
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.runtime_engine.decision_trace import DecisionTrace

_log = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────

STABILITY_WINDOW = 5
QUALITY_FLOOR = 0.50
CONFIDENCE_FLOOR = 0.40
INTERVENTION_RECURRENCE_THRESHOLD = 3
OSCILLATION_WINDOW = 6
RECOVERY_IMPROVEMENT_THRESHOLD = 0.10
GOAL_REGRESSION_THRESHOLD = -0.05
GOAL_REGRESSION_STREAK = 2
GOAL_PROGRESS_ACCELERATION_THRESHOLD = 0.05
GOAL_PROGRESS_STREAK = 3


class ConvergenceStatus(enum.Enum):
    """Trajectory-level stability assessment."""

    STABLE = "stable"
    UNSTABLE = "unstable"
    RECOVERING = "recovering"


class ConvergenceAction(enum.Enum):
    """Corrective action to queue for the next turn."""

    NONE = "none"
    REINFORCE = "reinforce"
    ADD_CORRECTIVE_DIRECTIVE = "add_corrective_directive"
    SUPPRESS_SYNTHESIS = "suppress_synthesis"
    SUPPRESS_EXPLORATION = "suppress_exploration"
    ESCALATE_CONTROL = "escalate_control"


@dataclass(frozen=True)
class ConvergenceDecision:
    """Immutable record of a convergence evaluation."""

    status: ConvergenceStatus
    action: ConvergenceAction
    reason: str
    confidence: float
    directives: tuple[str, ...] = ()
    suppress_synthesis: bool = False
    suppress_exploration: bool = False

    def to_dict(self) -> dict:
        d: dict = {
            "status": self.status.value,
            "action": self.action.value,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
        }
        if self.directives:
            d["directives"] = list(self.directives)
        if self.suppress_synthesis:
            d["suppress_synthesis"] = True
        if self.suppress_exploration:
            d["suppress_exploration"] = True
        return d


NO_ACTION = ConvergenceDecision(
    status=ConvergenceStatus.STABLE,
    action=ConvergenceAction.NONE,
    reason="no_evaluation",
    confidence=0.0,
)


class ConvergenceEngine:
    """Deterministic trajectory-aware stability engine.

    Evaluates a sliding window of DecisionTraces and produces a
    ConvergenceDecision.  Rules are checked in priority order —
    first matching rule wins.

    Disabled by default.  When disabled, ``evaluate()`` returns NO_ACTION.
    """

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def evaluate(self, traces: list[DecisionTrace]) -> ConvergenceDecision:
        """Evaluate recent trace history for convergence.

        Rules (priority order):
            1. Intervention recurrence → unstable
            2. Quality oscillation → unstable
            3. Persistent low quality despite interventions → unstable
            4. Post-intervention improvement → recovering
            5. Sustained healthy window → stable
            6. Insufficient data → stable (no action)
        """
        if not self.enabled or not traces:
            return NO_ACTION

        window = traces[-STABILITY_WINDOW:]

        # Rule 1: Recurring control interventions
        decision = self._check_intervention_recurrence(window)
        if decision is not None:
            return decision

        # Rule 2: Quality oscillation
        decision = self._check_oscillation(traces)
        if decision is not None:
            return decision

        # Rule 2.5: Goal regression (sustained negative delta)
        decision = self._check_goal_regression(window)
        if decision is not None:
            return decision

        # Rule 3: Persistent low quality despite interventions
        decision = self._check_persistent_low_quality(window)
        if decision is not None:
            return decision

        # Rule 4: Recovery after intervention (accelerated by goal progress)
        decision = self._check_recovery(traces)
        if decision is not None:
            return decision

        # Rule 4.5: Sustained goal progress → stable even without full window
        decision = self._check_goal_progress(window)
        if decision is not None:
            return decision

        # Rule 5: Sustained healthy window
        decision = self._check_stable(window)
        if decision is not None:
            return decision

        # Insufficient data
        return ConvergenceDecision(
            status=ConvergenceStatus.STABLE,
            action=ConvergenceAction.NONE,
            reason="insufficient_data",
            confidence=0.3,
        )

    # ─── Rule implementations ───────────────────────────────────────────

    def _check_intervention_recurrence(
        self, window: list[DecisionTrace]
    ) -> ConvergenceDecision | None:
        """Rule 1: Too many control interventions in the window → unstable."""
        intervention_count = sum(1 for t in window if _has_intervention(t))
        if intervention_count >= INTERVENTION_RECURRENCE_THRESHOLD:
            _log.info(
                "Convergence: %d interventions in last %d turns → unstable",
                intervention_count,
                len(window),
            )
            return ConvergenceDecision(
                status=ConvergenceStatus.UNSTABLE,
                action=ConvergenceAction.ESCALATE_CONTROL,
                reason="intervention_recurrence",
                confidence=min(intervention_count / len(window), 1.0),
                directives=(
                    "System is unstable — prioritize precision over coverage.",
                    "Avoid speculative content.",
                ),
                suppress_synthesis=True,
                suppress_exploration=True,
            )
        return None

    def _check_oscillation(
        self, traces: list[DecisionTrace]
    ) -> ConvergenceDecision | None:
        """Rule 2: Quality score oscillating up/down → unstable."""
        if len(traces) < OSCILLATION_WINDOW:
            return None

        recent = traces[-OSCILLATION_WINDOW:]
        scores = [t.quality_score for t in recent]

        direction_changes = 0
        for i in range(2, len(scores)):
            prev_delta = scores[i - 1] - scores[i - 2]
            curr_delta = scores[i] - scores[i - 1]
            if (
                prev_delta * curr_delta < 0
                and abs(prev_delta) > 0.05
                and abs(curr_delta) > 0.05
            ):
                direction_changes += 1

        if direction_changes >= OSCILLATION_WINDOW - 3:
            avg_score = sum(scores) / len(scores)
            _log.info(
                "Convergence: %d direction changes in %d turns (avg %.2f) → unstable",
                direction_changes,
                OSCILLATION_WINDOW,
                avg_score,
            )
            return ConvergenceDecision(
                status=ConvergenceStatus.UNSTABLE,
                action=ConvergenceAction.SUPPRESS_EXPLORATION,
                reason="quality_oscillation",
                confidence=direction_changes / (OSCILLATION_WINDOW - 1),
                directives=("Quality is oscillating — maintain consistent approach.",),
                suppress_exploration=True,
            )
        return None

    def _check_persistent_low_quality(
        self, window: list[DecisionTrace]
    ) -> ConvergenceDecision | None:
        """Rule 3: All recent turns below floor AND at least one intervention → unstable."""
        if len(window) < 3:
            return None

        all_low = all(t.quality_score < QUALITY_FLOOR for t in window)
        any_intervention = any(_has_intervention(t) for t in window)

        if all_low and any_intervention:
            avg = sum(t.quality_score for t in window) / len(window)
            _log.info(
                "Convergence: persistent low quality (avg %.2f) with interventions → unstable",
                avg,
            )
            return ConvergenceDecision(
                status=ConvergenceStatus.UNSTABLE,
                action=ConvergenceAction.ADD_CORRECTIVE_DIRECTIVE,
                reason="persistent_low_quality",
                confidence=1.0 - avg,
                directives=(
                    "Multiple turns have scored poorly despite corrections.",
                    "Simplify response structure. Focus on accuracy.",
                ),
                suppress_synthesis=True,
            )
        return None

    def _check_recovery(
        self, traces: list[DecisionTrace]
    ) -> ConvergenceDecision | None:
        """Rule 4: Quality improved after a recent intervention → recovering."""
        if len(traces) < 3:
            return None

        for i in range(len(traces) - 1, max(len(traces) - 4, 0), -1):
            if _has_intervention(traces[i]):
                post = traces[i + 1 :] if i + 1 < len(traces) else []
                if not post:
                    continue
                pre_score = traces[i].quality_score
                post_avg = sum(t.quality_score for t in post) / len(post)
                improvement = post_avg - pre_score

                if improvement >= RECOVERY_IMPROVEMENT_THRESHOLD:
                    _log.info(
                        "Convergence: quality improved %.2f after intervention at turn %d → recovering",
                        improvement,
                        traces[i].turn_id,
                    )
                    return ConvergenceDecision(
                        status=ConvergenceStatus.RECOVERING,
                        action=ConvergenceAction.REINFORCE,
                        reason="post_intervention_improvement",
                        confidence=min(improvement / 0.3, 1.0),
                    )
        return None

    def _check_stable(self, window: list[DecisionTrace]) -> ConvergenceDecision | None:
        """Rule 5: All recent turns healthy with no interventions → stable."""
        if len(window) < STABILITY_WINDOW:
            return None

        all_healthy = all(
            t.quality_score >= QUALITY_FLOOR and t.confidence >= CONFIDENCE_FLOOR
            for t in window
        )
        no_interventions = not any(_has_intervention(t) for t in window)

        if all_healthy and no_interventions:
            avg_quality = sum(t.quality_score for t in window) / len(window)
            return ConvergenceDecision(
                status=ConvergenceStatus.STABLE,
                action=ConvergenceAction.NONE,
                reason="sustained_healthy_window",
                confidence=avg_quality,
            )
        return None

    def _check_goal_regression(
        self, window: list[DecisionTrace]
    ) -> ConvergenceDecision | None:
        """Rule 2.5: Sustained negative goal_delta → treat as instability."""
        deltas = [
            getattr(t, "goal_delta", None)
            for t in window
            if getattr(t, "goal_delta", None) is not None
        ]
        if len(deltas) < GOAL_REGRESSION_STREAK:
            return None

        recent_deltas = deltas[-GOAL_REGRESSION_STREAK:]
        if all(d <= GOAL_REGRESSION_THRESHOLD for d in recent_deltas):
            avg_delta = sum(recent_deltas) / len(recent_deltas)
            _log.info(
                "Convergence: goal regressing (avg delta %.3f) over %d turns → unstable",
                avg_delta,
                len(recent_deltas),
            )
            return ConvergenceDecision(
                status=ConvergenceStatus.UNSTABLE,
                action=ConvergenceAction.ADD_CORRECTIVE_DIRECTIVE,
                reason="goal_regression",
                confidence=min(abs(avg_delta) * 5, 1.0),
                directives=(
                    "Goal progress is declining. Re-align responses with the objective.",
                ),
                suppress_exploration=True,
            )
        return None

    def _check_goal_progress(
        self, window: list[DecisionTrace]
    ) -> ConvergenceDecision | None:
        """Rule 4.5: Sustained positive goal_delta → accelerate recovery."""
        deltas = [
            getattr(t, "goal_delta", None)
            for t in window
            if getattr(t, "goal_delta", None) is not None
        ]
        if len(deltas) < GOAL_PROGRESS_STREAK:
            return None

        recent_deltas = deltas[-GOAL_PROGRESS_STREAK:]
        if all(d >= GOAL_PROGRESS_ACCELERATION_THRESHOLD for d in recent_deltas):
            avg_delta = sum(recent_deltas) / len(recent_deltas)
            _log.info(
                "Convergence: goal progressing (avg delta +%.3f) over %d turns → stable",
                avg_delta,
                len(recent_deltas),
            )
            return ConvergenceDecision(
                status=ConvergenceStatus.STABLE,
                action=ConvergenceAction.NONE,
                reason="goal_progress",
                confidence=min(avg_delta * 5, 1.0),
            )
        return None


def _has_intervention(trace: DecisionTrace) -> bool:
    """Check whether a trace had a control intervention."""
    ctrl = getattr(trace, "control_decision", None)
    if ctrl is None:
        return False
    return getattr(ctrl, "intervene", False)
