"""Agent Workforce Runtime — Campaign 19.1.

Composes 4 existing runtimes into a workforce capacity view.
Answers: Which agents are idle? Overloaded? What should be delegated?
What capability gaps exist?

Read-only. No dispatch. No execute. No approve. No mutate.
Aggregate → normalize → present.

C19 substrate workstation subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class WorkforceHealth(str, Enum):
    """Agent workforce health — derived deterministically."""
    OPTIMAL = "optimal"
    ACTIVE = "active"
    CONSTRAINED = "constrained"
    OVERLOADED = "overloaded"
    IDLE = "idle"


@dataclass
class AgentWorkforceSnapshot:
    health: str = WorkforceHealth.IDLE.value
    total_agent_types: int = 0
    available_executor_count: int = 0
    active_dispatches: list[dict[str, Any]] = field(default_factory=list)
    idle_agents: list[dict[str, Any]] = field(default_factory=list)
    overloaded_agents: list[dict[str, Any]] = field(default_factory=list)
    pending_delegations: list[dict[str, Any]] = field(default_factory=list)
    delegation_success_rate: float = 0.0
    capability_coverage: dict[str, Any] = field(default_factory=dict)
    queue_depth: int = 0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "total_agent_types": self.total_agent_types,
            "available_executor_count": self.available_executor_count,
            "active_dispatches": self.active_dispatches,
            "idle_agents": self.idle_agents,
            "overloaded_agents": self.overloaded_agents,
            "pending_delegations": self.pending_delegations,
            "delegation_success_rate": round(self.delegation_success_rate, 4),
            "capability_coverage": self.capability_coverage,
            "queue_depth": self.queue_depth,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────


class AgentWorkforceRuntime:
    """Unified workforce capacity view — composes 4 runtimes.

    Read-only. Aggregate → normalize → present.
    """

    def __init__(
        self,
        agent_fleet: Any | None = None,
        delegation_readiness: Any | None = None,
        agent_registry: Any | None = None,
        execution_coordinator: Any | None = None,
    ) -> None:
        self._agent_fleet = agent_fleet
        self._delegation_readiness = delegation_readiness
        self._agent_registry = agent_registry
        self._execution_coordinator = execution_coordinator

    # ── Lazy accessors ────────────────────────────────────────────────

    @property
    def _fleet(self) -> Any:
        if self._agent_fleet is None:
            try:
                from substrate.organism.agent_fleet_runtime import AgentFleetRuntime
                self._agent_fleet = AgentFleetRuntime()
            except Exception:
                logger.debug("AgentFleetRuntime unavailable")
        return self._agent_fleet

    @property
    def _delegation(self) -> Any:
        if self._delegation_readiness is None:
            try:
                from substrate.organism.delegation_readiness_runtime import (
                    DelegationReadinessRuntime,
                )
                self._delegation_readiness = DelegationReadinessRuntime()
            except Exception:
                logger.debug("DelegationReadinessRuntime unavailable")
        return self._delegation_readiness

    @property
    def _registry(self) -> Any:
        if self._agent_registry is None:
            try:
                from substrate.organism.agent_registry import AgentRegistry
                self._agent_registry = AgentRegistry()
            except Exception:
                logger.debug("AgentRegistry unavailable")
        return self._agent_registry

    @property
    def _coord(self) -> Any:
        if self._execution_coordinator is None:
            try:
                from substrate.organism.execution_coordinator import ExecutionCoordinator
                self._execution_coordinator = ExecutionCoordinator()
            except Exception:
                logger.debug("ExecutionCoordinator unavailable")
        return self._execution_coordinator

    # ── Helpers ───────────────────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        if obj is None:
            return None
        fn = getattr(obj, method, None)
        if fn is None:
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("AgentWorkforceRuntime._safe_call(%s) failed: %s", method, exc)
            return None

    # ── State derivation ──────────────────────────────────────────────

    def health(self) -> WorkforceHealth:
        agent_types = self._get_agent_types()
        if not agent_types:
            return WorkforceHealth.IDLE

        active = self._get_active_dispatches()
        idle_list = self._get_idle_agents(agent_types, active)
        overloaded_list = self._get_overloaded_agents(agent_types, active)
        pending = self._get_pending_delegations()

        if overloaded_list:
            return WorkforceHealth.OVERLOADED

        if not active and pending:
            return WorkforceHealth.CONSTRAINED

        if active and not overloaded_list:
            return WorkforceHealth.ACTIVE

        if not active and not pending:
            return WorkforceHealth.IDLE

        return WorkforceHealth.OPTIMAL

    # ── Public API ────────────────────────────────────────────────────

    def snapshot(self) -> AgentWorkforceSnapshot:
        now = time.time()
        agent_types = self._get_agent_types()
        active = self._get_active_dispatches()
        idle_list = self._get_idle_agents(agent_types, active)
        overloaded_list = self._get_overloaded_agents(agent_types, active)
        pending = self._get_pending_delegations()
        success_rate = self._get_delegation_success_rate()
        coverage = self._get_capability_coverage(agent_types)
        queue = self._get_queue_depth()

        return AgentWorkforceSnapshot(
            health=self.health().value,
            total_agent_types=len(agent_types),
            available_executor_count=len(agent_types) - len(overloaded_list),
            active_dispatches=active,
            idle_agents=idle_list,
            overloaded_agents=overloaded_list,
            pending_delegations=pending,
            delegation_success_rate=success_rate,
            capability_coverage=coverage,
            queue_depth=queue,
            generated_at=now,
        )

    def idle(self) -> list[dict[str, Any]]:
        agent_types = self._get_agent_types()
        active = self._get_active_dispatches()
        return self._get_idle_agents(agent_types, active)

    def overloaded(self) -> list[dict[str, Any]]:
        agent_types = self._get_agent_types()
        active = self._get_active_dispatches()
        return self._get_overloaded_agents(agent_types, active)

    def pending_delegations(self) -> list[dict[str, Any]]:
        return self._get_pending_delegations()

    def capability_gaps(self) -> list[str]:
        agent_types = self._get_agent_types()
        coverage = self._get_capability_coverage(agent_types)
        return coverage.get("gaps", [])

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "ok": True,
            "health": snap.health,
            "total_agent_types": snap.total_agent_types,
            "available_executor_count": snap.available_executor_count,
            "active_dispatch_count": len(snap.active_dispatches),
            "idle_count": len(snap.idle_agents),
            "overloaded_count": len(snap.overloaded_agents),
            "pending_delegation_count": len(snap.pending_delegations),
            "delegation_success_rate": snap.delegation_success_rate,
            "queue_depth": snap.queue_depth,
            "generated_at": snap.generated_at,
        }

    # ── Internal data collection ──────────────────────────────────────

    def _get_agent_types(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._registry, "list_agents")
        if result is None:
            result = self._safe_call(self._registry, "all_agents")
        if result is None:
            return []
        if isinstance(result, dict):
            return [v.to_dict() if hasattr(v, "to_dict") else v for v in result.values()]
        if isinstance(result, list):
            return [a.to_dict() if hasattr(a, "to_dict") else a for a in result]
        return []

    def _get_active_dispatches(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._fleet, "active_dispatches")
        if result is None:
            snap = self._safe_call(self._fleet, "snapshot")
            if snap and hasattr(snap, "active_dispatches"):
                result = snap.active_dispatches
        if result is None:
            return []
        if isinstance(result, list):
            return [d.to_dict() if hasattr(d, "to_dict") else (d if isinstance(d, dict) else {}) for d in result]
        return []

    def _get_idle_agents(
        self,
        agent_types: list[dict[str, Any]],
        active: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        active_type_ids = {d.get("agent_type", "") for d in active}
        return [
            {"agent_type_id": a.get("agent_type_id", ""), "label": a.get("label", "")}
            for a in agent_types
            if a.get("agent_type_id", "") not in active_type_ids
        ]

    def _get_overloaded_agents(
        self,
        agent_types: list[dict[str, Any]],
        active: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        from collections import Counter
        dispatch_counts = Counter(d.get("agent_type", "") for d in active)
        overloaded = []
        for a in agent_types:
            type_id = a.get("agent_type_id", "")
            count = dispatch_counts.get(type_id, 0)
            if count > 1:
                overloaded.append({
                    "agent_type_id": type_id,
                    "label": a.get("label", ""),
                    "active_count": count,
                })
        return overloaded

    def _get_pending_delegations(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._delegation, "pending_delegations")
        if result is None:
            snap = self._safe_call(self._delegation, "snapshot")
            if snap and hasattr(snap, "assessments"):
                result = [
                    a for a in snap.assessments
                    if hasattr(a, "delegatable") and a.delegatable
                ]
        if result is None:
            return []
        if isinstance(result, list):
            return [d.to_dict() if hasattr(d, "to_dict") else (d if isinstance(d, dict) else {}) for d in result]
        return []

    def _get_delegation_success_rate(self) -> float:
        snap = self._safe_call(self._delegation, "snapshot")
        if snap and hasattr(snap, "avg_success_probability"):
            return float(snap.avg_success_probability)
        if snap and hasattr(snap, "assessments"):
            assessments = snap.assessments or []
            if assessments:
                probs = [
                    a.success_probability
                    for a in assessments
                    if hasattr(a, "success_probability")
                ]
                return sum(probs) / len(probs) if probs else 0.0
        return 0.0

    def _get_capability_coverage(self, agent_types: list[dict[str, Any]]) -> dict[str, Any]:
        all_domains: set[str] = set()
        covered_domains: set[str] = set()
        for a in agent_types:
            domains = a.get("allowed_domains", [])
            if domains:
                all_domains.update(domains)
                covered_domains.update(domains)

        known_domains = {
            "engineering", "infrastructure", "research", "strategy",
            "content", "outreach", "operations", "analytics",
        }
        all_domains.update(known_domains)
        gaps = sorted(all_domains - covered_domains)

        return {
            "total_domains": len(all_domains),
            "covered_domains": len(covered_domains),
            "coverage_ratio": round(len(covered_domains) / len(all_domains), 3) if all_domains else 0.0,
            "gaps": gaps,
        }

    def _get_queue_depth(self) -> int:
        result = self._safe_call(self._coord, "queue_depth")
        return result if isinstance(result, int) else 0
