"""Commitment engine — goal persistence and switching decisions.

Evaluates whether the system should CONTINUE pursuing the active
objective, SWITCH to a better candidate, or ABANDON the current
goal entirely. Switching incurs a penalty proportional to progress
and time invested, preventing thrashing.

Pure computation — no I/O, no subprocess, no state mutation.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from umh.runtime.arbitration import Objective, ObjectiveEvaluator, ObjectiveScore
from umh.runtime.goal_state import GoalState


class CommitmentDecision(Enum):
    """Outcome of a commitment evaluation."""

    CONTINUE = "continue"
    SWITCH = "switch"
    ABANDON = "abandon"


_DEFAULT_PROGRESS_WEIGHT = 0.6
_DEFAULT_TIME_WEIGHT = 0.4
_DEFAULT_SWITCH_THRESHOLD = 0.15
_DEFAULT_ABANDON_THRESHOLD = 0.20
_DEFAULT_MAX_TICKS = 50
_DEFAULT_MIN_IMPROVEMENT = 0.05


@dataclass(frozen=True)
class SwitchingCost:
    """Computed cost of switching away from the current objective."""

    progress_penalty: float
    time_penalty: float
    total_penalty: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "progress_penalty": round(self.progress_penalty, 4),
            "time_penalty": round(self.time_penalty, 4),
            "total_penalty": round(self.total_penalty, 4),
        }


@dataclass(frozen=True)
class CommitmentResult:
    """Full commitment evaluation with explainability."""

    decision: CommitmentDecision
    active_objective: Objective
    active_score: ObjectiveScore
    candidate_objective: Objective | None
    candidate_score: ObjectiveScore | None
    switching_cost: SwitchingCost
    score_gap: float
    net_improvement: float
    progress: float
    ticks_invested: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "active_objective_id": self.active_objective.objective_id,
            "active_score": self.active_score.to_dict(),
            "candidate_objective_id": (
                self.candidate_objective.objective_id if self.candidate_objective else None
            ),
            "candidate_score": (self.candidate_score.to_dict() if self.candidate_score else None),
            "switching_cost": self.switching_cost.to_dict(),
            "score_gap": round(self.score_gap, 4),
            "net_improvement": round(self.net_improvement, 4),
            "progress": round(self.progress, 4),
            "ticks_invested": self.ticks_invested,
            "reason": self.reason,
        }

    @property
    def explanation(self) -> list[str]:
        lines: list[str] = [
            f"Decision: {self.decision.value}",
            f"Active: {self.active_objective.objective_id} "
            f"(score={self.active_score.total_score:.4f}, "
            f"progress={self.progress:.2f})",
        ]
        if self.candidate_objective is not None and self.candidate_score is not None:
            lines.append(
                f"Candidate: {self.candidate_objective.objective_id} "
                f"(score={self.candidate_score.total_score:.4f})"
            )
        lines.append(
            f"Switching cost: {self.switching_cost.total_penalty:.4f} "
            f"(progress={self.switching_cost.progress_penalty:.4f}, "
            f"time={self.switching_cost.time_penalty:.4f})"
        )
        lines.append(
            f"Score gap: {self.score_gap:.4f}, Net improvement: {self.net_improvement:.4f}"
        )
        lines.append(self.reason)
        return lines


class CommitmentEngine:
    """Evaluates whether to continue, switch, or abandon the active goal.

    Decision logic:
    1. Score both active and candidate objectives
    2. Compute switching cost from progress and time invested
    3. If no candidate: CONTINUE (or ABANDON if progress stalled)
    4. If candidate score - active score > switching_cost + threshold: SWITCH
    5. Otherwise: CONTINUE

    ABANDON triggers when progress is near zero after significant ticks
    and no viable candidate exists.
    """

    def __init__(
        self,
        *,
        evaluator: ObjectiveEvaluator | None = None,
        progress_weight: float = _DEFAULT_PROGRESS_WEIGHT,
        time_weight: float = _DEFAULT_TIME_WEIGHT,
        switch_threshold: float = _DEFAULT_SWITCH_THRESHOLD,
        abandon_threshold: float = _DEFAULT_ABANDON_THRESHOLD,
        max_ticks: int = _DEFAULT_MAX_TICKS,
        min_improvement: float = _DEFAULT_MIN_IMPROVEMENT,
    ) -> None:
        self._evaluator = evaluator or ObjectiveEvaluator()
        total = progress_weight + time_weight
        if total <= 0:
            total = 1.0
        self._progress_weight = progress_weight / total
        self._time_weight = time_weight / total
        self._switch_threshold = max(0.0, min(1.0, switch_threshold))
        self._abandon_threshold = max(0.0, min(1.0, abandon_threshold))
        self._max_ticks = max(1, max_ticks)
        self._min_improvement = max(0.0, min(1.0, min_improvement))

    @property
    def evaluator(self) -> ObjectiveEvaluator:
        return self._evaluator

    @property
    def progress_weight(self) -> float:
        return self._progress_weight

    @property
    def time_weight(self) -> float:
        return self._time_weight

    @property
    def switch_threshold(self) -> float:
        return self._switch_threshold

    @property
    def abandon_threshold(self) -> float:
        return self._abandon_threshold

    @property
    def max_ticks(self) -> int:
        return self._max_ticks

    @property
    def min_improvement(self) -> float:
        return self._min_improvement

    def compute_switching_cost(
        self,
        progress: float,
        ticks_invested: int,
    ) -> SwitchingCost:
        """Compute the cost of switching away from the current objective.

        Higher progress and more time invested → higher penalty.
        """
        clamped_progress = max(0.0, min(1.0, progress))
        time_ratio = min(1.0, ticks_invested / self._max_ticks)

        progress_penalty = self._progress_weight * clamped_progress
        time_penalty = self._time_weight * time_ratio

        return SwitchingCost(
            progress_penalty=progress_penalty,
            time_penalty=time_penalty,
            total_penalty=progress_penalty + time_penalty,
        )

    def decide(
        self,
        current_state: GoalState,
        candidate: Objective | None,
        current_tick: int,
    ) -> CommitmentResult:
        """Decide whether to CONTINUE, SWITCH, or ABANDON.

        Pure — no side effects, no state mutation.
        """
        active = current_state.active_objective
        active_score = self._evaluator.score(active)
        ticks_invested = current_state.elapsed_ticks(current_tick)
        progress = current_state.progress

        switching_cost = self.compute_switching_cost(progress, ticks_invested)

        candidate_score: ObjectiveScore | None = None
        score_gap = 0.0
        net_improvement = 0.0

        if candidate is not None:
            candidate_score = self._evaluator.score(candidate)
            score_gap = candidate_score.total_score - active_score.total_score
            net_improvement = score_gap - switching_cost.total_penalty

        if candidate is not None and candidate_score is not None:
            if net_improvement > self._min_improvement and score_gap > self._switch_threshold:
                reason = self._build_switch_reason(
                    active, candidate, score_gap, switching_cost, net_improvement
                )
                return CommitmentResult(
                    decision=CommitmentDecision.SWITCH,
                    active_objective=active,
                    active_score=active_score,
                    candidate_objective=candidate,
                    candidate_score=candidate_score,
                    switching_cost=switching_cost,
                    score_gap=score_gap,
                    net_improvement=net_improvement,
                    progress=progress,
                    ticks_invested=ticks_invested,
                    reason=reason,
                )

        if self._should_abandon(progress, ticks_invested, active_score):
            reason = self._build_abandon_reason(progress, ticks_invested, active_score)
            return CommitmentResult(
                decision=CommitmentDecision.ABANDON,
                active_objective=active,
                active_score=active_score,
                candidate_objective=candidate,
                candidate_score=candidate_score,
                switching_cost=switching_cost,
                score_gap=score_gap,
                net_improvement=net_improvement,
                progress=progress,
                ticks_invested=ticks_invested,
                reason=reason,
            )

        reason = self._build_continue_reason(active, progress, ticks_invested, switching_cost)
        return CommitmentResult(
            decision=CommitmentDecision.CONTINUE,
            active_objective=active,
            active_score=active_score,
            candidate_objective=candidate,
            candidate_score=candidate_score,
            switching_cost=switching_cost,
            score_gap=score_gap,
            net_improvement=net_improvement,
            progress=progress,
            ticks_invested=ticks_invested,
            reason=reason,
        )

    def _should_abandon(
        self,
        progress: float,
        ticks_invested: int,
        active_score: ObjectiveScore,
    ) -> bool:
        """Check if the active goal should be abandoned."""
        if ticks_invested < 3:
            return False
        if progress > self._abandon_threshold:
            return False
        if active_score.total_score < 0.2:
            return True
        time_ratio = ticks_invested / self._max_ticks
        if time_ratio > 0.5 and progress < 0.1:
            return True
        return False

    def _build_switch_reason(
        self,
        active: Objective,
        candidate: Objective,
        score_gap: float,
        switching_cost: SwitchingCost,
        net_improvement: float,
    ) -> str:
        parts: list[str] = [
            f"candidate '{candidate.objective_id}' outscores "
            f"'{active.objective_id}' by {score_gap:.4f}",
            f"net improvement {net_improvement:.4f} after penalty "
            f"{switching_cost.total_penalty:.4f}",
        ]
        return "; ".join(parts)

    def _build_continue_reason(
        self,
        active: Objective,
        progress: float,
        ticks_invested: int,
        switching_cost: SwitchingCost,
    ) -> str:
        parts: list[str] = []
        if progress > 0.5:
            parts.append(f"significant progress ({progress:.2f})")
        elif progress > 0.2:
            parts.append(f"moderate progress ({progress:.2f})")
        else:
            parts.append(f"early progress ({progress:.2f})")

        if switching_cost.total_penalty > 0.3:
            parts.append(f"high switching cost ({switching_cost.total_penalty:.4f})")
        elif switching_cost.total_penalty > 0.1:
            parts.append(f"moderate switching cost ({switching_cost.total_penalty:.4f})")

        parts.append(f"{ticks_invested} ticks invested in '{active.objective_id}'")
        return "; ".join(parts)

    def _build_abandon_reason(
        self,
        progress: float,
        ticks_invested: int,
        active_score: ObjectiveScore,
    ) -> str:
        parts: list[str] = []
        if active_score.total_score < 0.2:
            parts.append(f"very low objective score ({active_score.total_score:.4f})")
        if progress < 0.1:
            parts.append(f"near-zero progress ({progress:.4f}) after {ticks_invested} ticks")
        else:
            parts.append(f"stalled at {progress:.4f} progress after {ticks_invested} ticks")
        return "; ".join(parts)
