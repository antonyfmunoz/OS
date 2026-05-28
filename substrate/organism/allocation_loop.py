"""Governed runtime allocation loop — continuous leverage allocator.

Runs as a tick stage, not a standalone loop. Each allocation cycle
evaluates the current RuntimeGraph topology, detects degraded or
dead runtimes, flags cost spikes, and emits decisions as events.

Integrates with existing subsystems:
  - RuntimeGraph: topology and capability awareness
  - RuntimeSupervisor: health state
  - ExecutionEconomy: cost/performance data
  - RecursionGovernor: throttle enforcement

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_economy import ExecutionEconomy
from substrate.organism.recursion_governance import RecursionGovernor
from substrate.organism.runtime_graph import AvailabilityStatus, RuntimeGraph
from substrate.organism.runtime_supervisor import RuntimeSupervisor

logger = logging.getLogger(__name__)


class AllocationStrategy(str, Enum):
    COST_OPTIMIZED = "cost_optimized"
    RELIABILITY_FIRST = "reliability_first"
    LATENCY_FIRST = "latency_first"
    BALANCED = "balanced"


@dataclass
class AllocationDecision:
    runtime_id: str
    action: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "action": self.action,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class AllocationLoop:
    """Continuous governed runtime allocation.

    Called each tick cycle to evaluate runtime topology and
    produce allocation decisions. Not a standalone loop —
    integrates as an AutonomousTick stage.
    """

    COST_SPIKE_THRESHOLD = 5.0

    def __init__(
        self,
        spine: EventSpine,
        graph: RuntimeGraph,
        supervisor: RuntimeSupervisor,
        economy: ExecutionEconomy,
        governor: RecursionGovernor,
        strategy: AllocationStrategy = AllocationStrategy.BALANCED,
    ) -> None:
        self._spine = spine
        self._graph = graph
        self._supervisor = supervisor
        self._economy = economy
        self._governor = governor
        self._strategy = strategy
        self._cycle_count = 0
        self._last_costs: dict[str, float] = {}
        self._recent_decisions: list[AllocationDecision] = []

    def allocation_cycle(self) -> list[AllocationDecision]:
        """Run one allocation cycle. Returns decisions made."""
        self._cycle_count += 1
        decisions: list[AllocationDecision] = []

        if self._governor.is_killed:
            decisions.append(AllocationDecision(
                runtime_id="*",
                action="throttled",
                reason="recursion governor kill switch active",
            ))
            self._emit_decisions(decisions)
            return decisions

        for node in self._graph.all_nodes():
            if node.status == AvailabilityStatus.DEGRADED:
                decisions.append(AllocationDecision(
                    runtime_id=node.runtime_id,
                    action="flag_degraded",
                    reason=f"runtime {node.runtime_id} is degraded",
                    metadata={"status": node.status.value},
                ))

            if node.status == AvailabilityStatus.UNAVAILABLE:
                decisions.append(AllocationDecision(
                    runtime_id=node.runtime_id,
                    action="flag_unavailable",
                    reason=f"runtime {node.runtime_id} is unavailable",
                ))

            current_cost = node.cost.effective_cost
            last_cost = self._last_costs.get(node.runtime_id, current_cost)
            if last_cost > 0 and current_cost / last_cost > self.COST_SPIKE_THRESHOLD:
                decisions.append(AllocationDecision(
                    runtime_id=node.runtime_id,
                    action="cost_spike",
                    reason=f"cost jumped from {last_cost:.4f} to {current_cost:.4f}",
                    metadata={"old_cost": last_cost, "new_cost": current_cost},
                ))
            self._last_costs[node.runtime_id] = current_cost

        self._recent_decisions = decisions
        self._emit_decisions(decisions)
        return decisions

    def _emit_decisions(self, decisions: list[AllocationDecision]) -> None:
        self._spine.emit(
            EventDomain.LEVERAGE,
            "allocation_cycle_completed",
            "allocation_loop",
            {
                "cycle": self._cycle_count,
                "decision_count": len(decisions),
                "decisions": [d.to_dict() for d in decisions[:20]],
                "strategy": self._strategy.value,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_count": self._cycle_count,
            "strategy": self._strategy.value,
            "decisions": [d.to_dict() for d in self._recent_decisions],
            "runtime_count": self._graph.node_count,
        }
