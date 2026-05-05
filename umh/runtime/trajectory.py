"""Trajectory — multi-step planning and trajectory simulation.

Generates sequences of strategies, simulates cumulative outcomes
over multiple steps, evaluates long-term trajectories, and selects
the best path. Only the first step of the selected trajectory is
executed — "plan to the horizon, act on step one."

Pure computation — no I/O, no subprocess, no state mutation.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umh.model.behavior import UserBehaviorModel
from umh.runtime.simulation import (
    SimulatedOutcome,
    SimulationEngine,
    StrategyGenerator,
)
from umh.runtime.strategy import ExecutionStrategy

if TYPE_CHECKING:
    from umh.runtime.calibration import CalibrationFactors


_DEFAULT_DEPTH = 3
_MIN_DEPTH = 2
_MAX_DEPTH = 5
_MAX_TRAJECTORIES = 50


@dataclass(frozen=True)
class TrajectoryStep:
    """One step in a trajectory with its simulated outcome."""

    step_index: int
    strategy: ExecutionStrategy
    outcome: SimulatedOutcome

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "strategy": self.strategy.to_dict(),
            "outcome": self.outcome.to_dict(),
        }


@dataclass(frozen=True)
class Trajectory:
    """A multi-step execution plan with cumulative metrics."""

    steps: tuple[TrajectoryStep, ...]
    label: str
    cumulative_completion: float
    cumulative_latency: float
    cumulative_risk: float
    cumulative_effort: float
    score: float = 0.0

    @property
    def depth(self) -> int:
        return len(self.steps)

    @property
    def first_strategy(self) -> ExecutionStrategy:
        return self.steps[0].strategy

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "depth": self.depth,
            "cumulative_completion": round(self.cumulative_completion, 4),
            "cumulative_latency": round(self.cumulative_latency, 4),
            "cumulative_risk": round(self.cumulative_risk, 4),
            "cumulative_effort": round(self.cumulative_effort, 4),
            "score": round(self.score, 4),
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass(frozen=True)
class TrajectoryResult:
    """Complete trajectory evaluation: all paths scored and ranked."""

    trajectories: tuple[Trajectory, ...]
    selected: Trajectory
    reason: str
    depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectories_evaluated": len(self.trajectories),
            "selected": self.selected.to_dict(),
            "reason": self.reason,
            "depth": self.depth,
            "all_trajectories": [t.to_dict() for t in self.trajectories],
        }

    @property
    def explanation(self) -> list[str]:
        lines: list[str] = [
            f"Selected '{self.selected.label}' "
            f"(score {self.selected.score:.4f}, depth {self.depth})",
            self.reason,
        ]
        for t in self.trajectories:
            marker = ">>>" if t.label == self.selected.label else "   "
            lines.append(
                f"{marker} {t.label}: score={t.score:.4f} "
                f"completion={t.cumulative_completion:.2f} "
                f"risk={t.cumulative_risk:.2f} "
                f"depth={t.depth}"
            )
        return lines


class TrajectoryGenerator:
    """Generates multi-step strategy sequences from a base strategy.

    Uses the single-step StrategyGenerator to create candidates at
    each depth level, then combines them into trajectories. Limits
    total trajectories to prevent combinatorial explosion.
    """

    def __init__(
        self,
        *,
        strategy_generator: StrategyGenerator | None = None,
        max_trajectories: int = _MAX_TRAJECTORIES,
    ) -> None:
        self._gen = strategy_generator or StrategyGenerator()
        self._max_trajectories = max(5, min(200, max_trajectories))

    @property
    def max_trajectories(self) -> int:
        return self._max_trajectories

    def generate_paths(
        self,
        base: ExecutionStrategy,
        depth: int = _DEFAULT_DEPTH,
    ) -> list[list[ExecutionStrategy]]:
        """Generate multi-step strategy paths.

        Returns lists of strategy sequences, each of length `depth`.
        The first step always comes from the candidate set; subsequent
        steps branch from representative strategies to limit growth.
        """
        depth = max(_MIN_DEPTH, min(_MAX_DEPTH, depth))
        first_candidates = self._gen.generate_candidates(base)

        paths: list[list[ExecutionStrategy]] = [[c] for c in first_candidates]

        for step in range(1, depth):
            next_paths: list[list[ExecutionStrategy]] = []
            for path in paths:
                last = path[-1]
                branches = self._gen.generate_candidates(last)
                representative = self._select_representative(branches)
                for branch in representative:
                    extended = list(path) + [branch]
                    next_paths.append(extended)
                    if len(next_paths) >= self._max_trajectories:
                        break
                if len(next_paths) >= self._max_trajectories:
                    break
            paths = next_paths

        return paths[: self._max_trajectories]

    def _select_representative(
        self,
        candidates: list[ExecutionStrategy],
    ) -> list[ExecutionStrategy]:
        """Pick a representative subset to limit combinatorial explosion.

        Takes the first, last, and middle candidate — three per branch
        gives manageable growth while preserving strategy diversity.
        """
        if len(candidates) <= 3:
            return candidates
        mid = len(candidates) // 2
        return [candidates[0], candidates[mid], candidates[-1]]

    def label_trajectory(
        self,
        index: int,
        path: list[ExecutionStrategy],
        base: ExecutionStrategy,
    ) -> str:
        """Generate a human-readable label for a trajectory."""
        if not path:
            return f"trajectory-{index}"

        first = path[0]
        parts: list[str] = []

        if first.batch_size < base.batch_size:
            parts.append("conservative-start")
        elif first.batch_size > base.batch_size:
            parts.append("aggressive-start")
        else:
            parts.append("steady-start")

        if len(path) > 1:
            last = path[-1]
            if last.batch_size > first.batch_size:
                parts.append("ramp-up")
            elif last.batch_size < first.batch_size:
                parts.append("ramp-down")
            else:
                parts.append("stable")

        return f"{'-'.join(parts)}-{index}"


class TrajectorySimulator:
    """Simulates multi-step trajectories using the single-step engine.

    Chains SimulationEngine calls and accumulates metrics:
    - completion compounds multiplicatively (each step's rate applied)
    - latency sums across steps
    - risk compounds: P(any failure) = 1 - product(1 - step_risk)
    - effort sums across steps
    """

    def __init__(
        self,
        *,
        engine: SimulationEngine | None = None,
    ) -> None:
        self._engine = engine or SimulationEngine()

    @property
    def engine(self) -> SimulationEngine:
        return self._engine

    def simulate(
        self,
        path: list[ExecutionStrategy],
        model: UserBehaviorModel | None = None,
        calibration: CalibrationFactors | None = None,
        label: str = "",
    ) -> Trajectory:
        """Simulate a multi-step trajectory. Pure function."""
        steps: list[TrajectoryStep] = []
        cum_completion = 1.0
        cum_latency = 0.0
        cum_no_failure = 1.0
        cum_effort = 0.0

        for i, strategy in enumerate(path):
            outcome = self._engine.simulate(strategy, model, calibration)

            cum_completion *= outcome.expected_completion_rate
            cum_latency += outcome.expected_latency
            cum_no_failure *= 1.0 - outcome.expected_failure_risk
            cum_effort += outcome.estimated_effort

            steps.append(
                TrajectoryStep(
                    step_index=i,
                    strategy=strategy,
                    outcome=outcome,
                )
            )

        cum_risk = 1.0 - cum_no_failure

        return Trajectory(
            steps=tuple(steps),
            label=label,
            cumulative_completion=max(0.0, min(1.0, cum_completion)),
            cumulative_latency=max(0.0, cum_latency),
            cumulative_risk=max(0.0, min(1.0, cum_risk)),
            cumulative_effort=max(0.0, cum_effort),
        )


_DEFAULT_COMPLETION_WEIGHT = 0.40
_DEFAULT_RISK_WEIGHT = 0.25
_DEFAULT_LATENCY_WEIGHT = 0.20
_DEFAULT_EFFORT_WEIGHT = 0.15


@dataclass(frozen=True)
class TrajectoryWeights:
    """Weights for trajectory scoring."""

    completion: float = _DEFAULT_COMPLETION_WEIGHT
    risk: float = _DEFAULT_RISK_WEIGHT
    latency: float = _DEFAULT_LATENCY_WEIGHT
    effort: float = _DEFAULT_EFFORT_WEIGHT

    def to_dict(self) -> dict[str, Any]:
        return {
            "completion": round(self.completion, 4),
            "risk": round(self.risk, 4),
            "latency": round(self.latency, 4),
            "effort": round(self.effort, 4),
        }


class TrajectoryEvaluator:
    """Scores and ranks trajectories using weighted criteria.

    Higher score = better trajectory. Uses the same inverse
    normalization as OutcomeEvaluator for consistency.
    """

    def __init__(self, weights: TrajectoryWeights | None = None) -> None:
        w = weights or TrajectoryWeights()
        total = w.completion + w.risk + w.latency + w.effort
        if total <= 0:
            total = 1.0
        self._w_completion = w.completion / total
        self._w_risk = w.risk / total
        self._w_latency = w.latency / total
        self._w_effort = w.effort / total

    @property
    def weights(self) -> TrajectoryWeights:
        return TrajectoryWeights(
            completion=self._w_completion,
            risk=self._w_risk,
            latency=self._w_latency,
            effort=self._w_effort,
        )

    def score(self, trajectory: Trajectory) -> float:
        """Compute a scalar score for a trajectory. Pure function."""
        completion_score = trajectory.cumulative_completion
        risk_score = 1.0 - trajectory.cumulative_risk
        latency_score = 1.0 / (1.0 + trajectory.cumulative_latency)
        effort_score = 1.0 / (1.0 + trajectory.cumulative_effort)

        return (
            self._w_completion * completion_score
            + self._w_risk * risk_score
            + self._w_latency * latency_score
            + self._w_effort * effort_score
        )

    def rank(self, trajectories: list[Trajectory]) -> list[Trajectory]:
        """Rank trajectories by score (highest first). Pure function."""
        scored = []
        for t in trajectories:
            s = self.score(t)
            scored.append(
                Trajectory(
                    steps=t.steps,
                    label=t.label,
                    cumulative_completion=t.cumulative_completion,
                    cumulative_latency=t.cumulative_latency,
                    cumulative_risk=t.cumulative_risk,
                    cumulative_effort=t.cumulative_effort,
                    score=s,
                )
            )
        scored.sort(key=lambda t: (-t.score, t.label))
        return scored


class TrajectoryPlanner:
    """End-to-end trajectory pipeline: generate → simulate → evaluate → select.

    Combines TrajectoryGenerator, TrajectorySimulator, and
    TrajectoryEvaluator. Returns the best trajectory; the caller
    should extract .first_strategy for immediate execution.
    """

    def __init__(
        self,
        *,
        generator: TrajectoryGenerator | None = None,
        simulator: TrajectorySimulator | None = None,
        evaluator: TrajectoryEvaluator | None = None,
    ) -> None:
        self._generator = generator or TrajectoryGenerator()
        self._simulator = simulator or TrajectorySimulator()
        self._evaluator = evaluator or TrajectoryEvaluator()

    @property
    def generator(self) -> TrajectoryGenerator:
        return self._generator

    @property
    def simulator(self) -> TrajectorySimulator:
        return self._simulator

    @property
    def evaluator(self) -> TrajectoryEvaluator:
        return self._evaluator

    def plan(
        self,
        base_strategy: ExecutionStrategy,
        *,
        depth: int = _DEFAULT_DEPTH,
        model: UserBehaviorModel | None = None,
        calibration: CalibrationFactors | None = None,
    ) -> TrajectoryResult:
        """Generate, simulate, evaluate, and select the best trajectory."""
        paths = self._generator.generate_paths(base_strategy, depth)

        trajectories: list[Trajectory] = []
        for i, path in enumerate(paths):
            label = self._generator.label_trajectory(i, path, base_strategy)
            traj = self._simulator.simulate(
                path,
                model,
                calibration,
                label=label,
            )
            trajectories.append(traj)

        ranked = self._evaluator.rank(trajectories)
        selected = ranked[0]

        reason = self._build_reason(selected, ranked)

        return TrajectoryResult(
            trajectories=tuple(ranked),
            selected=selected,
            reason=reason,
            depth=depth,
        )

    def _build_reason(
        self,
        selected: Trajectory,
        ranked: list[Trajectory],
    ) -> str:
        parts: list[str] = []

        if selected.cumulative_completion >= 0.5:
            parts.append("strong cumulative completion")
        elif selected.cumulative_completion >= 0.3:
            parts.append("moderate cumulative completion")
        else:
            parts.append("best available completion path")

        if selected.cumulative_risk < 0.3:
            parts.append("low cumulative risk")
        elif selected.cumulative_risk < 0.5:
            parts.append("acceptable cumulative risk")

        if len(ranked) > 1:
            runner_up = ranked[1]
            if (
                selected.cumulative_completion > runner_up.cumulative_completion
                and selected.cumulative_latency > runner_up.cumulative_latency
            ):
                parts.append("higher completion despite slower pace")

        return "; ".join(parts) if parts else "best overall trajectory score"
