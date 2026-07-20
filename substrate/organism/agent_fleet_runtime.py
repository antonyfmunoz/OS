"""Agent Fleet Runtime — unified agent coordination layer.

Composes AgentCapabilityModel + ComputeFabricRuntime + ExecutorRuntime +
AgentRegistry + CompoundingEngine into a single facade that answers:
"Who should do this work?" — with agent, compute node, and deterministic rationale.

Campaign invariant: reduces operator external-loop dependency by eliminating
manual agent routing (ChatGPT ↔ Claude ↔ Codex ↔ Hermes bouncing).

W3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from substrate.state.runtime_paths import runtime_state_dir

logger = logging.getLogger(__name__)


def _fleet_dir() -> str:
    return str(runtime_state_dir("fleet", create=False))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FleetDispatchStatus(str, Enum):
    """Status of a fleet dispatch through its lifecycle."""

    ASSIGNED = "assigned"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class AssignmentRationale:
    """Why the fleet chose this agent + compute node."""

    capability_score: float = 0.0
    reliability_score: float = 0.0
    risk_clearance: bool = True
    domain_match: bool = True
    compute_health: str = "healthy"
    compute_headroom: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_score": round(self.capability_score, 3),
            "reliability_score": round(self.reliability_score, 3),
            "risk_clearance": self.risk_clearance,
            "domain_match": self.domain_match,
            "compute_health": self.compute_health,
            "compute_headroom": self.compute_headroom,
            "summary": self.summary,
        }


@dataclass
class FleetAssignment:
    """Deterministic assignment: agent + compute node + rationale."""

    assignment_id: str = field(default_factory=lambda: f"fa-{uuid4().hex[:8]}")
    agent_type: str = ""
    agent_label: str = ""
    compute_node_id: str = ""
    compute_node_type: str = ""
    rationale: AssignmentRationale = field(default_factory=AssignmentRationale)
    alternatives: list[str] = field(default_factory=list)
    capabilities_required: list[str] = field(default_factory=list)
    capabilities_matched: list[str] = field(default_factory=list)
    risk_class: str = "low"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "agent_type": self.agent_type,
            "agent_label": self.agent_label,
            "compute_node_id": self.compute_node_id,
            "compute_node_type": self.compute_node_type,
            "rationale": self.rationale.to_dict(),
            "alternatives": list(self.alternatives),
            "capabilities_required": list(self.capabilities_required),
            "capabilities_matched": list(self.capabilities_matched),
            "risk_class": self.risk_class,
            "created_at": self.created_at,
        }


@dataclass
class FleetDispatch:
    """Tracked dispatch of an assignment through the executor."""

    dispatch_id: str = field(default_factory=lambda: f"fd-{uuid4().hex[:8]}")
    assignment_id: str = ""
    agent_type: str = ""
    compute_node_id: str = ""
    executor_request_id: str = ""
    status: FleetDispatchStatus = FleetDispatchStatus.ASSIGNED
    description: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "assignment_id": self.assignment_id,
            "agent_type": self.agent_type,
            "compute_node_id": self.compute_node_id,
            "executor_request_id": self.executor_request_id,
            "status": self.status.value,
            "description": self.description,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


@dataclass
class FleetDispatchResult:
    """Outcome of a completed dispatch."""

    dispatch_id: str = ""
    success: bool = False
    duration_ms: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    learning_record_ids: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 1),
            "artifacts": list(self.artifacts),
            "learning_record_ids": list(self.learning_record_ids),
            "error": self.error,
        }


@dataclass
class FleetSnapshot:
    """Fleet-wide status view."""

    total_agents: int = 0
    active_dispatches: int = 0
    by_agent_type: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    capacity_remaining: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_agents": self.total_agents,
            "active_dispatches": self.active_dispatches,
            "by_agent_type": dict(self.by_agent_type),
            "by_status": dict(self.by_status),
            "capacity_remaining": self.capacity_remaining,
        }


@dataclass
class FleetHealth:
    """Fleet health aggregation."""

    agent_count: int = 0
    healthy_count: int = 0
    degraded_agents: list[str] = field(default_factory=list)
    bottleneck_analysis: str = ""
    overall_reliability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "healthy_count": self.healthy_count,
            "degraded_agents": list(self.degraded_agents),
            "bottleneck_analysis": self.bottleneck_analysis,
            "overall_reliability": round(self.overall_reliability, 3),
        }


@dataclass
class WaveResult:
    """Result of dispatching multiple assignments in parallel."""

    wave_id: str = field(default_factory=lambda: f"wv-{uuid4().hex[:8]}")
    dispatches: list[FleetDispatch] = field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    status: str = "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "dispatches": [d.to_dict() for d in self.dispatches],
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "status": self.status,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Fleet Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AgentFleetRuntime:
    """Unified agent coordination — composes capability, compute, executor, registry.

    Answers: "Who should do this work?" with agent + compute node + rationale.
    Then dispatches through the executor lifecycle and feeds outcomes back
    into the compounding engine for continuous learning.
    """

    def __init__(
        self,
        capability_model: Any,
        compute_fabric: Any,
        executor_runtime: Any | None = None,
        agent_registry: Any | None = None,
        compounding_engine: Any | None = None,
    ) -> None:
        self._capability_model = capability_model
        self._compute_fabric = compute_fabric
        self._executor_runtime = executor_runtime
        self._agent_registry = agent_registry
        self._compounding_engine = compounding_engine
        self._assignments: dict[str, FleetAssignment] = {}
        self._dispatches: dict[str, FleetDispatch] = {}
        self._results: dict[str, FleetDispatchResult] = {}
        self._dispatch_log_path = os.path.join(_fleet_dir(), "dispatches.jsonl")

    # ── Core: "Who should do this work?" ──────────────────────────

    def assign(
        self,
        capabilities_required: list[str],
        risk_class: str = "low",
        domain: str = "",
        description: str = "",
    ) -> FleetAssignment:
        """Deterministic assignment: best agent + best compute node + rationale.

        Scoring pipeline:
        1. Filter agents by risk clearance and domain match
        2. Score each agent by capability overlap + observed reliability
        3. Route to compute node via ComputeFabricRuntime
        4. Build human-readable rationale
        """
        registry = self._agent_registry
        if registry is None:
            return self._empty_assignment(
                capabilities_required, risk_class, "No agent registry configured"
            )

        all_agents = registry.all_agents()
        if not all_agents:
            return self._empty_assignment(capabilities_required, risk_class, "No agents registered")

        scored: list[tuple[Any, float, list[str], float]] = []
        for agent in all_agents:
            if not agent.can_handle_risk(risk_class):
                continue
            if domain and not agent.can_handle_domain(domain):
                continue

            matched = [c for c in capabilities_required if c in agent.capabilities]
            if not matched:
                continue

            cap_score = len(matched) / len(capabilities_required) if capabilities_required else 0.0

            reliability = 0.5
            profile = self._capability_model.get_profile(agent.agent_type_id)
            if profile and profile.total_attempts > 0:
                reliability = profile.overall_reliability

            combined = (cap_score * 0.6) + (reliability * 0.4)
            scored.append((agent, combined, matched, reliability))

        if not scored:
            return self._empty_assignment(
                capabilities_required,
                risk_class,
                f"No agent can handle capabilities={capabilities_required}, "
                f"risk={risk_class}, domain={domain}",
            )

        scored.sort(key=lambda t: -t[1])
        best_agent, best_score, best_matched, best_reliability = scored[0]
        alternatives = [s[0].agent_type_id for s in scored[1:]]

        compute_decision = self._compute_fabric.route(
            capability_needs=capabilities_required,
            risk_level=risk_class,
        )

        rationale = AssignmentRationale(
            capability_score=best_score,
            reliability_score=best_reliability,
            risk_clearance=True,
            domain_match=not domain or best_agent.can_handle_domain(domain),
            compute_health=compute_decision.target_node_type
            if compute_decision.target_node_id
            else "unknown",
            compute_headroom=0,
            summary=(
                f"Selected {best_agent.label} ({best_agent.agent_type_id}) "
                f"because it matches {len(best_matched)}/{len(capabilities_required)} capabilities "
                f"({', '.join(best_matched)}), has {best_reliability:.0%} reliability, "
                f"and compute routed to {compute_decision.target_node_id or 'no node'}."
            ),
        )

        assignment = FleetAssignment(
            agent_type=best_agent.agent_type_id,
            agent_label=best_agent.label,
            compute_node_id=compute_decision.target_node_id,
            compute_node_type=compute_decision.target_node_type,
            rationale=rationale,
            alternatives=alternatives,
            capabilities_required=list(capabilities_required),
            capabilities_matched=best_matched,
            risk_class=risk_class,
        )
        self._assignments[assignment.assignment_id] = assignment
        return assignment

    def _empty_assignment(
        self,
        caps: list[str],
        risk: str,
        reason: str,
    ) -> FleetAssignment:
        return FleetAssignment(
            agent_type="",
            agent_label="",
            compute_node_id="",
            compute_node_type="",
            rationale=AssignmentRationale(summary=reason),
            alternatives=[],
            capabilities_required=list(caps),
            capabilities_matched=[],
            risk_class=risk,
        )

    # ── Dispatch ──────────────────────────────────────────────────

    def dispatch(
        self,
        assignment: FleetAssignment,
        description: str = "",
    ) -> FleetDispatch:
        """Dispatch an assignment through the executor lifecycle."""
        dispatch = FleetDispatch(
            assignment_id=assignment.assignment_id,
            agent_type=assignment.agent_type,
            compute_node_id=assignment.compute_node_id,
            description=description or assignment.rationale.summary,
            status=FleetDispatchStatus.DISPATCHED,
            started_at=time.time(),
        )

        if self._executor_runtime is not None:
            try:
                from substrate.organism.executor_runtime import (
                    ExecutorRequest,
                    ExecutorType,
                )

                request = ExecutorRequest(
                    executor_type=ExecutorType.AGENT.value,
                    description=dispatch.description,
                    risk_class=assignment.risk_class,
                    context={
                        "agent_type": assignment.agent_type,
                        "compute_node_id": assignment.compute_node_id,
                        "capabilities_required": assignment.capabilities_required,
                    },
                )
                dispatch.executor_request_id = request.request_id
                dispatch.status = FleetDispatchStatus.EXECUTING
            except Exception as exc:
                logger.debug("Fleet dispatch executor error: %s", exc)
                dispatch.status = FleetDispatchStatus.FAILED
                dispatch.error = str(exc)

        self._dispatches[dispatch.dispatch_id] = dispatch
        self._persist_dispatch(dispatch)
        return dispatch

    def dispatch_wave(
        self,
        assignments: list[FleetAssignment],
    ) -> WaveResult:
        """Dispatch multiple assignments. Returns aggregated result."""
        dispatches = []
        succeeded = 0
        failed = 0
        for a in assignments:
            d = self.dispatch(a)
            dispatches.append(d)
            if d.status == FleetDispatchStatus.FAILED:
                failed += 1
            else:
                succeeded += 1

        return WaveResult(
            dispatches=dispatches,
            total=len(assignments),
            succeeded=succeeded,
            failed=failed,
            status="complete" if failed == 0 else "partial_failure",
        )

    # ── Dispatch lifecycle ────────────────────────────────────────

    def dispatch_result(self, dispatch_id: str) -> FleetDispatchResult | None:
        """Get result for a completed dispatch."""
        return self._results.get(dispatch_id)

    def record_outcome(
        self,
        dispatch_id: str,
        success: bool,
        duration_ms: float = 0.0,
        artifacts: list[str] | None = None,
    ) -> FleetDispatchResult:
        """Record execution outcome. Feeds back into capability model + compounding engine."""
        dispatch = self._dispatches.get(dispatch_id)

        result = FleetDispatchResult(
            dispatch_id=dispatch_id,
            success=success,
            duration_ms=duration_ms,
            artifacts=artifacts or [],
        )

        if dispatch:
            dispatch.status = (
                FleetDispatchStatus.COMPLETED if success else FleetDispatchStatus.FAILED
            )
            dispatch.completed_at = time.time()
            if not success:
                dispatch.error = "execution_failed"

            caps = []
            for d in self._dispatches.values():
                if d.dispatch_id == dispatch_id:
                    assignment = self._find_assignment_for_dispatch(d)
                    if assignment:
                        caps = assignment.capabilities_required
                    break

            if dispatch.agent_type and caps:
                records = self._capability_model.update_reliability(
                    agent_type=dispatch.agent_type,
                    capabilities_used=caps,
                    success=success,
                    duration_ms=duration_ms,
                )
                result.learning_record_ids = [r.record_id for r in records]

        self._results[dispatch_id] = result
        return result

    def _find_assignment_for_dispatch(self, dispatch: FleetDispatch) -> FleetAssignment | None:
        return self._assignments.get(dispatch.assignment_id)

    # ── Fleet queries ─────────────────────────────────────────────

    def fleet_status(self) -> FleetSnapshot:
        """Fleet-wide status snapshot."""
        registry = self._agent_registry
        total_agents = len(registry.all_agents()) if registry else 0

        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        active = 0

        for d in self._dispatches.values():
            by_type[d.agent_type] = by_type.get(d.agent_type, 0) + 1
            by_status[d.status.value] = by_status.get(d.status.value, 0) + 1
            if d.status in (FleetDispatchStatus.DISPATCHED, FleetDispatchStatus.EXECUTING):
                active += 1

        fabric_health = self._compute_fabric.health()
        capacity = fabric_health.get("total_capacity", 0) - fabric_health.get("total_workers", 0)

        return FleetSnapshot(
            total_agents=total_agents,
            active_dispatches=active,
            by_agent_type=by_type,
            by_status=by_status,
            capacity_remaining=max(0, capacity),
        )

    def active_dispatches(self) -> list[FleetDispatch]:
        """All currently executing dispatches."""
        return [
            d
            for d in self._dispatches.values()
            if d.status in (FleetDispatchStatus.DISPATCHED, FleetDispatchStatus.EXECUTING)
        ]

    def agent_utilization(self) -> dict[str, float]:
        """Per-agent-type utilization (active dispatches / total capacity)."""
        active_by_type: dict[str, int] = {}
        for d in self.active_dispatches():
            active_by_type[d.agent_type] = active_by_type.get(d.agent_type, 0) + 1

        fabric_health = self._compute_fabric.health()
        total_cap = max(fabric_health.get("total_capacity", 1), 1)

        result: dict[str, float] = {}
        registry = self._agent_registry
        if registry:
            for agent in registry.all_agents():
                active = active_by_type.get(agent.agent_type_id, 0)
                result[agent.agent_type_id] = round(active / total_cap, 3)
        return result

    def fleet_health(self) -> FleetHealth:
        """Aggregated fleet health from capability model + compute fabric."""
        registry = self._agent_registry
        if not registry:
            return FleetHealth()

        agents = registry.all_agents()
        total = len(agents)
        healthy = 0
        degraded: list[str] = []
        total_reliability = 0.0
        agents_with_data = 0

        for agent in agents:
            profile = self._capability_model.get_profile(agent.agent_type_id)
            if profile and profile.total_attempts > 0:
                agents_with_data += 1
                total_reliability += profile.overall_reliability
                if profile.overall_reliability >= 0.7:
                    healthy += 1
                else:
                    degraded.append(agent.agent_type_id)
            else:
                healthy += 1

        avg_reliability = total_reliability / agents_with_data if agents_with_data > 0 else 1.0

        bottleneck = ""
        active = self.active_dispatches()
        fabric_health = self._compute_fabric.health()
        total_cap = fabric_health.get("total_capacity", 0)
        if total_cap > 0 and len(active) >= total_cap:
            bottleneck = "compute_saturated"
        elif degraded:
            bottleneck = f"degraded_agents: {', '.join(degraded)}"

        return FleetHealth(
            agent_count=total,
            healthy_count=healthy,
            degraded_agents=degraded,
            bottleneck_analysis=bottleneck,
            overall_reliability=avg_reliability,
        )

    # ── Persistence ───────────────────────────────────────────────

    def _persist_dispatch(self, dispatch: FleetDispatch) -> None:
        try:
            os.makedirs(os.path.dirname(self._dispatch_log_path), exist_ok=True)
            with open(self._dispatch_log_path, "a") as f:
                f.write(json.dumps(dispatch.to_dict(), default=str) + "\n")
        except OSError as exc:
            logger.debug("Fleet dispatch persist error: %s", exc)
