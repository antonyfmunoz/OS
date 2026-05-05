"""Outcome memory — append-only storage for strategy execution outcomes.

Provides query and aggregation over historical outcomes:
    - list all outcomes
    - query by strategy name or state signature
    - compute per-strategy and per-state+strategy statistics
    - build performance signals with confidence
    - optional file persistence backend

Append-only: outcomes can be added but never removed or mutated.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.runtime.outcome import (
    OutcomeStatus,
    StrategyOutcome,
    StrategyPerformanceSignal,
    StrategyStats,
)

_log = logging.getLogger(__name__)


def _compute_stats(strategy_name: str, outcomes: list[StrategyOutcome]) -> StrategyStats:
    total = len(outcomes)
    if total == 0:
        return StrategyStats(
            strategy_name=strategy_name,
            total_count=0,
            success_count=0,
            failure_count=0,
            partial_count=0,
            unknown_count=0,
            average_success_score=0.0,
            average_latency=0.0,
            average_effort=0.0,
        )

    success = sum(1 for o in outcomes if o.status == OutcomeStatus.SUCCESS)
    failure = sum(1 for o in outcomes if o.status == OutcomeStatus.FAILURE)
    partial = sum(1 for o in outcomes if o.status == OutcomeStatus.PARTIAL)
    unknown = sum(1 for o in outcomes if o.status == OutcomeStatus.UNKNOWN)
    avg_score = sum(o.success_score for o in outcomes) / total
    avg_latency = sum(o.latency for o in outcomes) / total
    avg_effort = sum(o.effort for o in outcomes) / total

    return StrategyStats(
        strategy_name=strategy_name,
        total_count=total,
        success_count=success,
        failure_count=failure,
        partial_count=partial,
        unknown_count=unknown,
        average_success_score=avg_score,
        average_latency=avg_latency,
        average_effort=avg_effort,
    )


class OutcomeMemory:
    """Append-only memory for strategy execution outcomes."""

    def __init__(
        self,
        *,
        required_samples: int = 10,
        persistence_backend: Any | None = None,
    ) -> None:
        self._outcomes: list[StrategyOutcome] = []
        self._required_samples = max(1, required_samples)
        self._persistence_backend = persistence_backend
        self._persistence_errors: int = 0
        if persistence_backend is not None:
            self._load_from_backend()

    @property
    def count(self) -> int:
        return len(self._outcomes)

    @property
    def required_samples(self) -> int:
        return self._required_samples

    @property
    def persistence_errors(self) -> int:
        return self._persistence_errors

    def append(self, outcome: StrategyOutcome) -> None:
        self._outcomes.append(outcome)
        if self._persistence_backend is not None:
            try:
                ok = self._persistence_backend.append_outcome(outcome)
                if not ok:
                    self._persistence_errors += 1
            except Exception as e:
                _log.debug("Persistence append error (non-fatal): %s", e)
                self._persistence_errors += 1

    def list_outcomes(self) -> list[StrategyOutcome]:
        return list(self._outcomes)

    def query_by_strategy(self, strategy_name: str) -> list[StrategyOutcome]:
        return [o for o in self._outcomes if o.strategy_name == strategy_name]

    def query_by_state(self, state_signature: str) -> list[StrategyOutcome]:
        return [o for o in self._outcomes if o.state_signature == state_signature]

    def query_by_state_and_strategy(
        self, state_signature: str, strategy_name: str
    ) -> list[StrategyOutcome]:
        return [
            o
            for o in self._outcomes
            if o.state_signature == state_signature and o.strategy_name == strategy_name
        ]

    def compute_strategy_stats(self, strategy_name: str) -> StrategyStats:
        return _compute_stats(strategy_name, self.query_by_strategy(strategy_name))

    def compute_state_strategy_stats(
        self, state_signature: str, strategy_name: str
    ) -> StrategyStats:
        return _compute_stats(
            strategy_name,
            self.query_by_state_and_strategy(state_signature, strategy_name),
        )

    def get_performance_signal(self, strategy_name: str) -> StrategyPerformanceSignal:
        stats = self.compute_strategy_stats(strategy_name)
        confidence = min(1.0, stats.total_count / self._required_samples)
        return StrategyPerformanceSignal(
            strategy_name=strategy_name,
            sample_size=stats.total_count,
            success_rate=stats.success_rate,
            average_score=stats.average_success_score,
            confidence=confidence,
        )

    def get_strategy_feedback_factor(
        self, strategy_name: str, state_signature: str | None = None
    ) -> float:
        if state_signature is not None:
            stats = self.compute_state_strategy_stats(state_signature, strategy_name)
        else:
            stats = self.compute_strategy_stats(strategy_name)

        if stats.total_count < self._required_samples:
            return 1.0

        deviation = stats.average_success_score - 0.5
        raw = 1.0 + deviation * 0.2
        return max(0.90, min(1.10, raw))

    def list_strategies(self) -> list[str]:
        seen: list[str] = []
        for o in self._outcomes:
            if o.strategy_name not in seen:
                seen.append(o.strategy_name)
        return seen

    def _load_from_backend(self) -> None:
        try:
            loaded = self._persistence_backend.load_outcomes()
            self._outcomes.extend(loaded)
        except Exception as e:
            _log.debug("Persistence load error (non-fatal): %s", e)
            self._persistence_errors += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "required_samples": self._required_samples,
            "strategies": self.list_strategies(),
            "persistence_errors": self._persistence_errors,
        }
