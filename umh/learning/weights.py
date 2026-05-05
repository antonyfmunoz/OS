"""Adaptive scheduler weights — tunable scoring parameters.

Weights are explicit, serializable state. The scheduler receives them
as input — they are NOT global mutable state. Weight adaptation is
deterministic: same feedback history produces same weights.

Reversible: reset() returns to defaults at any time.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.learning.feedback import FeedbackStore
from umh.learning.metrics import MetricsAggregator


@dataclass
class SchedulerWeights:
    """Tunable weight parameters for the scoring function.

    These are passed as explicit input to the scorer — the scorer
    remains a pure function. Weights are the learned state.
    """

    priority_weight: float = 1.0
    wait_time_weight: float = 1.0
    node_fit_weight: float = 1.0
    cost_weight: float = 1.0
    success_bias: float = 10.0
    speed_bias: float = 0.01

    node_penalties: dict[str, float] = field(default_factory=dict)
    node_bonuses: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority_weight": self.priority_weight,
            "wait_time_weight": self.wait_time_weight,
            "node_fit_weight": self.node_fit_weight,
            "cost_weight": self.cost_weight,
            "success_bias": self.success_bias,
            "speed_bias": self.speed_bias,
            "node_penalties": dict(self.node_penalties),
            "node_bonuses": dict(self.node_bonuses),
        }

    def reset(self) -> None:
        """Reset all weights to defaults."""
        self.priority_weight = 1.0
        self.wait_time_weight = 1.0
        self.node_fit_weight = 1.0
        self.cost_weight = 1.0
        self.success_bias = 10.0
        self.speed_bias = 0.01
        self.node_penalties.clear()
        self.node_bonuses.clear()

    def get_node_adjustment(self, node_id: str) -> float:
        """Net adjustment for a node: bonus minus penalty."""
        bonus = self.node_bonuses.get(node_id, 0.0)
        penalty = self.node_penalties.get(node_id, 0.0)
        return bonus - penalty


_DEFAULT_WEIGHTS = SchedulerWeights()

_SUCCESS_THRESHOLD = 0.9
_FAILURE_THRESHOLD = 0.5
_SLOW_NODE_THRESHOLD_MS = 5000.0
_FAST_NODE_THRESHOLD_MS = 500.0
_PENALTY_INCREMENT = 5.0
_BONUS_INCREMENT = 3.0
_MAX_PENALTY = 50.0
_MAX_BONUS = 30.0


class WeightAdapter:
    """Adapts scheduler weights based on feedback metrics.

    Deterministic: same feedback store produces same weights.
    Does NOT modify the feedback store — read-only.
    """

    def __init__(self, aggregator: MetricsAggregator | None = None) -> None:
        self._aggregator = aggregator or MetricsAggregator()

    def adapt(self, store: FeedbackStore, weights: SchedulerWeights) -> SchedulerWeights:
        """Update weights based on current feedback. Mutates and returns weights.

        Deterministic: given the same store contents and starting weights,
        always produces the same result.
        """
        node_metrics = self._aggregator.node_metrics(store)

        for node_id, metrics in sorted(node_metrics.items()):
            if metrics.success_rate >= _SUCCESS_THRESHOLD and metrics.total_jobs >= 3:
                current_bonus = weights.node_bonuses.get(node_id, 0.0)
                weights.node_bonuses[node_id] = min(current_bonus + _BONUS_INCREMENT, _MAX_BONUS)

            if metrics.success_rate < _FAILURE_THRESHOLD and metrics.total_jobs >= 3:
                current_penalty = weights.node_penalties.get(node_id, 0.0)
                weights.node_penalties[node_id] = min(
                    current_penalty + _PENALTY_INCREMENT, _MAX_PENALTY
                )

            if metrics.avg_duration_ms > _SLOW_NODE_THRESHOLD_MS and metrics.total_jobs >= 3:
                current_penalty = weights.node_penalties.get(node_id, 0.0)
                weights.node_penalties[node_id] = min(
                    current_penalty + _PENALTY_INCREMENT * 0.5, _MAX_PENALTY
                )

            if metrics.avg_duration_ms < _FAST_NODE_THRESHOLD_MS and metrics.total_jobs >= 3:
                current_bonus = weights.node_bonuses.get(node_id, 0.0)
                weights.node_bonuses[node_id] = min(
                    current_bonus + _BONUS_INCREMENT * 0.5, _MAX_BONUS
                )

        return weights

    def compute_fresh(self, store: FeedbackStore) -> SchedulerWeights:
        """Compute weights from scratch using default starting point.

        Useful for deterministic replay — always produces the same
        result given the same feedback store.
        """
        weights = SchedulerWeights()
        return self.adapt(store, weights)
