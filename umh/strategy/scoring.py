"""UMH Strategy Scoring — compare strategy versions by performance.

Provides deterministic scoring functions that evaluate strategy quality
based on observed performance metrics. Pure functions, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from umh.strategy.history import PerformanceMetrics, StrategyVersion
from umh.strategy.models import StepComplexity, Strategy


@dataclass
class StrategyScore:
    """Composite score for a strategy version."""

    efficiency: float = 0.0
    reliability: float = 0.0
    complexity: float = 0.0
    overall: float = 0.0

    def to_dict(self) -> dict:
        return {
            "efficiency": round(self.efficiency, 3),
            "reliability": round(self.reliability, 3),
            "complexity": round(self.complexity, 3),
            "overall": round(self.overall, 3),
        }


def score_strategy(version: StrategyVersion) -> StrategyScore:
    """Score a strategy version based on its performance and structure.

    Returns a StrategyScore with three dimensions plus an overall composite.
    All scores are 0.0-1.0.
    """
    perf = version.performance
    strategy = version.strategy

    efficiency = _score_efficiency(perf)
    reliability = _score_reliability(perf)
    complexity = _score_complexity(strategy)

    overall = (efficiency * 0.4) + (reliability * 0.4) + (complexity * 0.2)

    return StrategyScore(
        efficiency=efficiency,
        reliability=reliability,
        complexity=complexity,
        overall=overall,
    )


def _score_efficiency(perf: PerformanceMetrics) -> float:
    """Score based on task completion rate and speed."""
    if perf.evaluations == 0:
        return 0.5

    completion_ratio = perf.success_rate
    retry_penalty = min(perf.tasks_retried / max(perf.evaluations, 1), 1.0)

    return max(0.0, min(1.0, completion_ratio - (retry_penalty * 0.2)))


def _score_reliability(perf: PerformanceMetrics) -> float:
    """Score based on failure rate and consistency."""
    if perf.evaluations == 0:
        return 0.5

    failure_rate = perf.tasks_failed / max(perf.tasks_completed + perf.tasks_failed, 1)
    return max(0.0, 1.0 - failure_rate)


def _score_complexity(strategy: Strategy) -> float:
    """Score inversely proportional to step complexity.

    Simpler strategies score higher (fewer steps, lower complexity).
    """
    if not strategy.steps:
        return 0.5

    complexity_weights = {
        StepComplexity.LOW: 1.0,
        StepComplexity.MEDIUM: 0.7,
        StepComplexity.HIGH: 0.4,
    }

    total = sum(complexity_weights.get(s.estimated_complexity, 0.5) for s in strategy.steps)
    avg = total / len(strategy.steps)

    step_penalty = max(0, len(strategy.steps) - 3) * 0.05
    return max(0.0, min(1.0, avg - step_penalty))


def compare_versions(v1: StrategyVersion, v2: StrategyVersion) -> dict:
    """Compare two strategy versions by score.

    Returns dict with scores and which is better.
    """
    s1 = score_strategy(v1)
    s2 = score_strategy(v2)

    return {
        "version_1": {"version_id": v1.version_id, "score": s1.to_dict()},
        "version_2": {"version_id": v2.version_id, "score": s2.to_dict()},
        "better": v1.version_id if s1.overall >= s2.overall else v2.version_id,
        "improvement": round(s2.overall - s1.overall, 3),
    }
