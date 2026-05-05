"""Evaluator — weighted scoring and selection of simulated outcomes.

Scores SimulatedOutcome instances using configurable weights and
selects the best strategy. Deterministic and pure — no side effects.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umh.model.behavior import UserBehaviorModel
from umh.runtime.simulation import (
    SimulatedOutcome,
    SimulationEngine,
    SimulationResult,
    StrategyGenerator,
)
from umh.runtime.strategy import ExecutionStrategy

if TYPE_CHECKING:
    from umh.runtime.calibration import CalibrationFactors


_DEFAULT_COMPLETION_WEIGHT = 0.40
_DEFAULT_LATENCY_WEIGHT = 0.20
_DEFAULT_RISK_WEIGHT = 0.25
_DEFAULT_EFFORT_WEIGHT = 0.15


@dataclass(frozen=True)
class ScoringWeights:
    """Weights for outcome scoring. Must sum to 1.0 (normalized internally)."""

    completion: float = _DEFAULT_COMPLETION_WEIGHT
    latency: float = _DEFAULT_LATENCY_WEIGHT
    risk: float = _DEFAULT_RISK_WEIGHT
    effort: float = _DEFAULT_EFFORT_WEIGHT

    def to_dict(self) -> dict[str, Any]:
        return {
            "completion": round(self.completion, 4),
            "latency": round(self.latency, 4),
            "risk": round(self.risk, 4),
            "effort": round(self.effort, 4),
        }


class OutcomeEvaluator:
    """Scores and ranks simulated outcomes using weighted criteria.

    Higher score = better strategy. Completion and low risk are rewarded;
    high latency and effort are penalized.
    """

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        w = weights or ScoringWeights()
        total = w.completion + w.latency + w.risk + w.effort
        if total <= 0:
            total = 1.0
        self._w_completion = w.completion / total
        self._w_latency = w.latency / total
        self._w_risk = w.risk / total
        self._w_effort = w.effort / total

    @property
    def weights(self) -> ScoringWeights:
        return ScoringWeights(
            completion=self._w_completion,
            latency=self._w_latency,
            risk=self._w_risk,
            effort=self._w_effort,
        )

    def score(self, outcome: SimulatedOutcome) -> float:
        """Compute a scalar score for a simulated outcome. Pure function.

        Completion contributes positively; latency, risk, and effort
        contribute negatively (inverted so lower = better → higher score).
        """
        completion_score = outcome.expected_completion_rate
        latency_score = 1.0 / (1.0 + outcome.expected_latency)
        risk_score = 1.0 - outcome.expected_failure_risk
        effort_score = 1.0 / (1.0 + outcome.estimated_effort)

        return (
            self._w_completion * completion_score
            + self._w_latency * latency_score
            + self._w_risk * risk_score
            + self._w_effort * effort_score
        )

    def rank(self, outcomes: list[SimulatedOutcome]) -> list[SimulatedOutcome]:
        """Rank outcomes by score (highest first). Pure function."""
        scored = []
        for o in outcomes:
            s = self.score(o)
            scored.append(
                SimulatedOutcome(
                    strategy=o.strategy,
                    label=o.label,
                    expected_completion_rate=o.expected_completion_rate,
                    expected_latency=o.expected_latency,
                    expected_failure_risk=o.expected_failure_risk,
                    estimated_effort=o.estimated_effort,
                    score=s,
                )
            )
        scored.sort(key=lambda o: (-o.score, o.label))
        return scored


class StrategySimulator:
    """End-to-end pipeline: generate → simulate → evaluate → select.

    Combines StrategyGenerator, SimulationEngine, and OutcomeEvaluator
    into a single deterministic call.
    """

    def __init__(
        self,
        *,
        generator: StrategyGenerator | None = None,
        engine: SimulationEngine | None = None,
        evaluator: OutcomeEvaluator | None = None,
    ) -> None:
        self._generator = generator or StrategyGenerator()
        self._engine = engine or SimulationEngine()
        self._evaluator = evaluator or OutcomeEvaluator()

    @property
    def generator(self) -> StrategyGenerator:
        return self._generator

    @property
    def engine(self) -> SimulationEngine:
        return self._engine

    @property
    def evaluator(self) -> OutcomeEvaluator:
        return self._evaluator

    def run(
        self,
        base_strategy: ExecutionStrategy,
        model: UserBehaviorModel | None = None,
        calibration: CalibrationFactors | None = None,
    ) -> SimulationResult:
        """Generate, simulate, evaluate, and select the best strategy."""
        candidates = self._generator.generate_candidates(base_strategy)

        outcomes: list[SimulatedOutcome] = []
        for i, candidate in enumerate(candidates):
            label = self._generator.label_candidate(i, candidate, base_strategy)
            raw = self._engine.simulate(candidate, model, calibration)
            outcomes.append(
                SimulatedOutcome(
                    strategy=raw.strategy,
                    label=label,
                    expected_completion_rate=raw.expected_completion_rate,
                    expected_latency=raw.expected_latency,
                    expected_failure_risk=raw.expected_failure_risk,
                    estimated_effort=raw.estimated_effort,
                )
            )

        ranked = self._evaluator.rank(outcomes)
        selected = ranked[0]

        reason = self._build_reason(selected, ranked)

        return SimulationResult(
            candidates=tuple(ranked),
            selected=selected,
            reason=reason,
        )

    def _build_reason(
        self,
        selected: SimulatedOutcome,
        ranked: list[SimulatedOutcome],
    ) -> str:
        parts: list[str] = []

        if selected.expected_completion_rate >= 0.8:
            parts.append("high completion likelihood")
        elif selected.expected_completion_rate >= 0.6:
            parts.append("moderate completion likelihood")
        else:
            parts.append("best available completion rate")

        if selected.expected_failure_risk < 0.2:
            parts.append("low failure risk")
        elif selected.expected_failure_risk < 0.4:
            parts.append("acceptable failure risk")

        if len(ranked) > 1:
            runner_up = ranked[1]
            if selected.expected_latency > runner_up.expected_latency:
                parts.append("slightly higher latency accepted")

        return "; ".join(parts) if parts else "best overall score"
