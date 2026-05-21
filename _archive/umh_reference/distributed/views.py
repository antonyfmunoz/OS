"""Phase 87A distributed views — UI-safe read models for distributed runtime data.

No sensitive data exposed. No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeNodeView:
    node_id: str = ""
    name: str = ""
    node_type: str = ""
    roles: list[str] = field(default_factory=list)
    availability: str = ""
    capability_count: int = 0
    description: str = ""
    gpu: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type,
            "roles": self.roles,
            "availability": self.availability,
            "capability_count": self.capability_count,
            "description": self.description,
            "gpu": self.gpu,
            "metadata": self.metadata,
        }


@dataclass
class CapabilityView:
    capability_id: str = ""
    domain: str = ""
    name: str = ""
    description: str = ""
    source_affinity: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "source_affinity": self.source_affinity,
            "metadata": self.metadata,
        }


@dataclass
class RoutingPolicyView:
    policy_id: str = ""
    name: str = ""
    priority: str = ""
    source_affinity: str = ""
    requires_gpu: bool = False
    requires_browser: bool = False
    requires_local_accounts: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "priority": self.priority,
            "source_affinity": self.source_affinity,
            "requires_gpu": self.requires_gpu,
            "requires_browser": self.requires_browser,
            "requires_local_accounts": self.requires_local_accounts,
            "metadata": self.metadata,
        }


@dataclass
class ArtifactSyncView:
    policy_id: str = ""
    name: str = ""
    artifact_type: str = ""
    direction: str = ""
    sync_on_change: bool = False
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "direction": self.direction,
            "sync_on_change": self.sync_on_change,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class RoutingDecisionView:
    decision_id: str = ""
    task_description: str = ""
    selected_node: str = ""
    selected_node_type: str = ""
    reason: str = ""
    alternatives: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "task_description": self.task_description,
            "selected_node": self.selected_node,
            "selected_node_type": self.selected_node_type,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "warnings": self.warnings,
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }


@dataclass
class DistributedDashboardView:
    node_count: int = 0
    active_node_count: int = 0
    future_node_count: int = 0
    capability_count: int = 0
    routing_policy_count: int = 0
    sync_policy_count: int = 0
    top_nodes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "active_node_count": self.active_node_count,
            "future_node_count": self.future_node_count,
            "capability_count": self.capability_count,
            "routing_policy_count": self.routing_policy_count,
            "sync_policy_count": self.sync_policy_count,
            "top_nodes": self.top_nodes,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


# ─── Converters ─────────────────────────────────────────────────────


def node_to_view(node: Any) -> RuntimeNodeView:
    nt = getattr(node, "node_type", "")
    avail = getattr(node, "availability", "")
    roles = getattr(node, "roles", [])
    caps = getattr(node, "capabilities", [])
    return RuntimeNodeView(
        node_id=getattr(node, "node_id", ""),
        name=getattr(node, "name", ""),
        node_type=nt.value if hasattr(nt, "value") else str(nt),
        roles=[r.value if hasattr(r, "value") else str(r) for r in roles],
        availability=avail.value if hasattr(avail, "value") else str(avail),
        capability_count=len(caps),
        description=getattr(node, "description", ""),
        gpu=getattr(node, "gpu", False),
    )


def capability_to_view(cap: Any) -> CapabilityView:
    domain = getattr(cap, "domain", "")
    aff = getattr(cap, "source_affinity", "")
    return CapabilityView(
        capability_id=getattr(cap, "capability_id", ""),
        domain=domain.value if hasattr(domain, "value") else str(domain),
        name=getattr(cap, "name", ""),
        description=getattr(cap, "description", ""),
        source_affinity=aff.value if hasattr(aff, "value") else str(aff),
    )


def routing_policy_to_view(policy: Any) -> RoutingPolicyView:
    prio = getattr(policy, "priority", "")
    aff = getattr(policy, "source_affinity", "")
    return RoutingPolicyView(
        policy_id=getattr(policy, "policy_id", ""),
        name=getattr(policy, "name", ""),
        priority=prio.value if hasattr(prio, "value") else str(prio),
        source_affinity=aff.value if hasattr(aff, "value") else str(aff),
        requires_gpu=getattr(policy, "requires_gpu", False),
        requires_browser=getattr(policy, "requires_browser", False),
        requires_local_accounts=getattr(policy, "requires_local_accounts", False),
    )


def sync_policy_to_view(policy: Any) -> ArtifactSyncView:
    at = getattr(policy, "artifact_type", "")
    direction = getattr(policy, "direction", "")
    return ArtifactSyncView(
        policy_id=getattr(policy, "policy_id", ""),
        name=getattr(policy, "name", ""),
        artifact_type=at.value if hasattr(at, "value") else str(at),
        direction=direction.value if hasattr(direction, "value") else str(direction),
        sync_on_change=getattr(policy, "sync_on_change", False),
        description=getattr(policy, "description", ""),
    )


def routing_decision_to_view(decision: Any) -> RoutingDecisionView:
    snt = getattr(decision, "selected_node_type", "")
    return RoutingDecisionView(
        decision_id=getattr(decision, "decision_id", ""),
        task_description=getattr(decision, "task_description", ""),
        selected_node=getattr(decision, "selected_node_id", ""),
        selected_node_type=snt.value if hasattr(snt, "value") else str(snt),
        reason=getattr(decision, "reason", ""),
        alternatives=getattr(decision, "alternatives", []),
        warnings=getattr(decision, "warnings", []),
        confidence=getattr(decision, "confidence", 0.0),
    )


def build_distributed_dashboard_view(
    nodes: list[Any] | None = None,
    capabilities: list[Any] | None = None,
    routing_policies: list[Any] | None = None,
    sync_policies: list[Any] | None = None,
    warnings: list[str] | None = None,
) -> DistributedDashboardView:
    from umh.distributed.contracts import NodeAvailability

    all_nodes = nodes or []
    active = [
        n
        for n in all_nodes
        if getattr(n, "availability", None)
        in (
            NodeAvailability.ALWAYS_ON,
            NodeAvailability.ON_DEMAND,
            NodeAvailability.INTERMITTENT,
            NodeAvailability.SCHEDULED,
        )
    ]
    future = [n for n in all_nodes if getattr(n, "availability", None) == NodeAvailability.FUTURE]

    return DistributedDashboardView(
        node_count=len(all_nodes),
        active_node_count=len(active),
        future_node_count=len(future),
        capability_count=len(capabilities or []),
        routing_policy_count=len(routing_policies or []),
        sync_policy_count=len(sync_policies or []),
        top_nodes=[getattr(n, "name", str(n)) for n in active[:5]],
        warnings=warnings or [],
    )
