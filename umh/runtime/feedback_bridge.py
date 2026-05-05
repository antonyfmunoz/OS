"""Feedback bridge — records execution outcomes and produces feedback summaries.

Connects the state → decision → outcome chain:
    1. Records an outcome into OutcomeMemory
    2. Creates a DecisionOutcomeLink
    3. Computes strategy stats (global and state-specific)
    4. Produces an explainable FeedbackRecord

Does NOT execute actions. Observation and recording only.
No I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.runtime.outcome import (
    DecisionOutcomeLink,
    StrategyOutcome,
    StrategyStats,
)
from umh.runtime.outcome_memory import OutcomeMemory


@dataclass(frozen=True)
class FeedbackRecord:
    """Result of recording an outcome through the feedback bridge."""

    link: DecisionOutcomeLink
    outcome: StrategyOutcome
    strategy_stats: StrategyStats
    state_strategy_stats: StrategyStats
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "link": self.link.to_dict(),
            "outcome": self.outcome.to_dict(),
            "strategy_stats": self.strategy_stats.to_dict(),
            "state_strategy_stats": self.state_strategy_stats.to_dict(),
            "explanation": self.explanation,
        }


def _build_explanation(
    outcome: StrategyOutcome,
    strategy_stats: StrategyStats,
    state_strategy_stats: StrategyStats,
) -> str:
    parts: list[str] = []
    parts.append(
        f"Strategy '{outcome.strategy_name}' executed with status={outcome.status.value}, "
        f"score={outcome.success_score:.2f}"
    )
    parts.append(f"State: {outcome.state_signature}")

    if strategy_stats.total_count > 0:
        parts.append(
            f"Global: {strategy_stats.total_count} executions, "
            f"success_rate={strategy_stats.success_rate:.2f}, "
            f"avg_score={strategy_stats.average_success_score:.2f}"
        )
    else:
        parts.append("Global: no prior executions")

    if state_strategy_stats.total_count > 0:
        parts.append(
            f"State-specific: {state_strategy_stats.total_count} executions, "
            f"success_rate={state_strategy_stats.success_rate:.2f}, "
            f"avg_score={state_strategy_stats.average_success_score:.2f}"
        )
    else:
        parts.append("State-specific: no prior executions in this state")

    if strategy_stats.total_count < 10:
        parts.append(f"Confidence: LOW ({strategy_stats.total_count}/10 samples)")
    else:
        parts.append("Confidence: sufficient data")

    return "; ".join(parts)


class FeedbackBridge:
    """Records outcomes and produces feedback summaries.

    Does NOT execute actions. Observation and recording only.
    """

    def __init__(self, outcome_memory: OutcomeMemory) -> None:
        self._memory = outcome_memory
        self._links: list[DecisionOutcomeLink] = []

    @property
    def outcome_memory(self) -> OutcomeMemory:
        return self._memory

    @property
    def link_count(self) -> int:
        return len(self._links)

    def record_outcome(
        self,
        outcome: StrategyOutcome,
        objective_id: str = "",
    ) -> FeedbackRecord:
        self._memory.append(outcome)

        link = DecisionOutcomeLink(
            state_signature=outcome.state_signature,
            decision_id=outcome.decision_id,
            strategy_name=outcome.strategy_name,
            objective_id=objective_id,
            outcome_id=outcome.outcome_id,
        )
        self._links.append(link)

        strategy_stats = self._memory.compute_strategy_stats(outcome.strategy_name)
        state_strategy_stats = self._memory.compute_state_strategy_stats(
            outcome.state_signature, outcome.strategy_name
        )

        explanation = _build_explanation(outcome, strategy_stats, state_strategy_stats)

        return FeedbackRecord(
            link=link,
            outcome=outcome,
            strategy_stats=strategy_stats,
            state_strategy_stats=state_strategy_stats,
            explanation=explanation,
        )

    def get_links(self) -> list[DecisionOutcomeLink]:
        return list(self._links)

    def get_links_for_strategy(self, strategy_name: str) -> list[DecisionOutcomeLink]:
        return [l for l in self._links if l.strategy_name == strategy_name]

    def get_links_for_state(self, state_signature: str) -> list[DecisionOutcomeLink]:
        return [l for l in self._links if l.state_signature == state_signature]

    def get_feedback_summary(self, strategy_name: str) -> dict[str, Any]:
        stats = self._memory.compute_strategy_stats(strategy_name)
        signal = self._memory.get_performance_signal(strategy_name)
        factor = self._memory.get_strategy_feedback_factor(strategy_name)
        return {
            "strategy_name": strategy_name,
            "stats": stats.to_dict(),
            "performance_signal": signal.to_dict(),
            "feedback_factor": round(factor, 4),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_count": self.link_count,
            "outcome_count": self._memory.count,
            "strategies": self._memory.list_strategies(),
        }
