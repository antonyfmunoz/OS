"""Simulation — strategy candidate generation and heuristic outcome simulation.

Generates variant strategies from a base strategy, simulates expected
outcomes using heuristic models, and produces scored results. All
computation is pure — no side effects, no I/O, no real task execution.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umh.model.behavior import UserBehaviorModel
from umh.runtime.strategy import ExecutionStrategy, _MAX_BATCH_SIZE, _MIN_BATCH_SIZE

if TYPE_CHECKING:
    from umh.runtime.calibration import CalibrationFactors


@dataclass(frozen=True)
class SimulatedOutcome:
    """Heuristic projection of a strategy's expected performance."""

    strategy: ExecutionStrategy
    label: str
    expected_completion_rate: float
    expected_latency: float
    expected_failure_risk: float
    estimated_effort: float
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "expected_completion_rate": round(self.expected_completion_rate, 4),
            "expected_latency": round(self.expected_latency, 4),
            "expected_failure_risk": round(self.expected_failure_risk, 4),
            "estimated_effort": round(self.estimated_effort, 4),
            "score": round(self.score, 4),
            "strategy": self.strategy.to_dict(),
        }


@dataclass(frozen=True)
class SimulationResult:
    """Complete simulation run: all candidates scored and ranked."""

    candidates: tuple[SimulatedOutcome, ...]
    selected: SimulatedOutcome
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates_evaluated": len(self.candidates),
            "selected": self.selected.to_dict(),
            "reason": self.reason,
            "all_candidates": [c.to_dict() for c in self.candidates],
        }

    @property
    def explanation(self) -> list[str]:
        lines: list[str] = [
            f"Selected '{self.selected.label}' (score {self.selected.score:.4f})",
            self.reason,
        ]
        for c in self.candidates:
            marker = ">>>" if c.label == self.selected.label else "   "
            lines.append(
                f"{marker} {c.label}: score={c.score:.4f} "
                f"completion={c.expected_completion_rate:.2f} "
                f"risk={c.expected_failure_risk:.2f}"
            )
        return lines


class StrategyGenerator:
    """Generates candidate strategies by varying a base strategy.

    Each variant explores one dimension of the strategy space.
    The base strategy is always included as a candidate.
    """

    def generate_candidates(
        self,
        base: ExecutionStrategy,
    ) -> list[ExecutionStrategy]:
        """Produce candidate strategies from the base.

        Always includes the base itself plus systematic variants.
        """
        candidates: list[ExecutionStrategy] = [base]

        smaller_batch = max(_MIN_BATCH_SIZE, base.batch_size - 2)
        if smaller_batch != base.batch_size:
            candidates.append(
                ExecutionStrategy(
                    batch_size=smaller_batch,
                    pacing=base.pacing,
                    retry_budget=base.retry_budget,
                    priority_bias=base.priority_bias,
                    prefer_morning=base.prefer_morning,
                    prefer_clustering=base.prefer_clustering,
                    adjustments=base.adjustments,
                )
            )

        larger_batch = min(_MAX_BATCH_SIZE, base.batch_size + 2)
        if larger_batch != base.batch_size:
            candidates.append(
                ExecutionStrategy(
                    batch_size=larger_batch,
                    pacing=base.pacing,
                    retry_budget=base.retry_budget,
                    priority_bias=base.priority_bias,
                    prefer_morning=base.prefer_morning,
                    prefer_clustering=base.prefer_clustering,
                    adjustments=base.adjustments,
                )
            )

        if base.retry_budget < 5:
            candidates.append(
                ExecutionStrategy(
                    batch_size=base.batch_size,
                    pacing=base.pacing,
                    retry_budget=min(5, base.retry_budget + 2),
                    priority_bias=base.priority_bias,
                    prefer_morning=base.prefer_morning,
                    prefer_clustering=base.prefer_clustering,
                    adjustments=base.adjustments,
                )
            )

        candidates.append(
            ExecutionStrategy(
                batch_size=base.batch_size,
                pacing=base.pacing * 1.3,
                retry_budget=base.retry_budget,
                priority_bias=base.priority_bias,
                prefer_morning=base.prefer_morning,
                prefer_clustering=base.prefer_clustering,
                adjustments=base.adjustments,
            )
        )

        candidates.append(
            ExecutionStrategy(
                batch_size=max(_MIN_BATCH_SIZE, base.batch_size - 1),
                pacing=base.pacing * 0.8,
                retry_budget=min(5, base.retry_budget + 1),
                priority_bias=base.priority_bias,
                prefer_morning=base.prefer_morning,
                prefer_clustering=base.prefer_clustering,
                adjustments=base.adjustments,
            )
        )

        return candidates

    def label_candidate(
        self, index: int, candidate: ExecutionStrategy, base: ExecutionStrategy
    ) -> str:
        """Generate a human-readable label for a candidate."""
        if index == 0:
            return "base"
        diffs: list[str] = []
        if candidate.batch_size < base.batch_size:
            diffs.append("smaller-batch")
        elif candidate.batch_size > base.batch_size:
            diffs.append("larger-batch")
        if candidate.retry_budget > base.retry_budget:
            diffs.append("aggressive-retry")
        if candidate.pacing > base.pacing:
            diffs.append("conservative-pacing")
        elif candidate.pacing < base.pacing:
            diffs.append("tight-pacing")
        return "+".join(diffs) if diffs else f"variant-{index}"


class SimulationEngine:
    """Heuristic simulation of strategy outcomes.

    Estimates performance metrics using the strategy parameters
    and optional behavior model context. No real execution occurs.
    """

    def simulate(
        self,
        strategy: ExecutionStrategy,
        model: UserBehaviorModel | None = None,
        calibration: CalibrationFactors | None = None,
    ) -> SimulatedOutcome:
        """Simulate the expected outcome of a strategy. Pure function."""
        completion = self._estimate_completion(strategy, model)
        latency = self._estimate_latency(strategy)
        risk = self._estimate_failure_risk(strategy, model)
        effort = self._estimate_effort(strategy)

        if calibration is not None:
            completion = max(0.0, min(1.0, completion * calibration.completion_factor))
            latency = max(0.1, latency * calibration.latency_factor)
            risk = max(0.0, min(1.0, risk * calibration.failure_factor))
            effort = max(0.1, effort * calibration.effort_factor)

        return SimulatedOutcome(
            strategy=strategy,
            label="",
            expected_completion_rate=completion,
            expected_latency=latency,
            expected_failure_risk=risk,
            estimated_effort=effort,
        )

    def _estimate_completion(
        self,
        strategy: ExecutionStrategy,
        model: UserBehaviorModel | None,
    ) -> float:
        base = 0.7
        if model is not None:
            trait = model.get_trait("completion_rate")
            if trait is not None and trait.confidence > 0.1:
                base = trait.value

        retry_boost = min(0.15, strategy.retry_budget * 0.03)
        batch_penalty = max(0.0, (strategy.batch_size - 5) * 0.02)

        return max(0.0, min(1.0, base + retry_boost - batch_penalty))

    def _estimate_latency(self, strategy: ExecutionStrategy) -> float:
        base_latency = strategy.batch_size * strategy.pacing
        return max(0.1, base_latency)

    def _estimate_failure_risk(
        self,
        strategy: ExecutionStrategy,
        model: UserBehaviorModel | None,
    ) -> float:
        base_risk = 0.2

        if model is not None:
            volatility = model.get_trait("volatility_index")
            if volatility is not None and volatility.confidence > 0.1:
                base_risk += volatility.value * 0.15

        batch_risk = max(0.0, (strategy.batch_size - 5) * 0.03)
        retry_reduction = min(0.1, strategy.retry_budget * 0.02)

        return max(0.0, min(1.0, base_risk + batch_risk - retry_reduction))

    def simulate_trajectory(
        self,
        strategies: list[ExecutionStrategy],
        model: UserBehaviorModel | None = None,
        calibration: CalibrationFactors | None = None,
    ) -> list[SimulatedOutcome]:
        """Simulate a sequence of strategies in order. Pure function."""
        return [self.simulate(s, model, calibration) for s in strategies]

    def _estimate_effort(self, strategy: ExecutionStrategy) -> float:
        return max(0.1, strategy.batch_size * 0.12 + strategy.retry_budget * 0.05)
