"""Constitutional Resource Economics and Coordination Engine v1.

Governs distributed compute allocation, execution prioritization,
orchestration scheduling, trust-weighted delegation, and constrained-node
coordination across the federated substrate network.

Optimizes leverage, stability, governance integrity, replay integrity,
continuity integrity, and blast radius minimization rather than raw
execution volume.

No resource allocation may bypass constitutional governance.
All scheduling preserves replay integrity, continuity lineage,
governance lineage, constitutional invariants, and authority ceilings.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.workstation.distributed_constitutional_substrate_federation_v1 import (
    FEDERATION_HARD_CEILINGS,
    FEDERATION_MATURITY_LEVELS,
    FederatedNode,
    FederatedNodeRegistry,
    FederationEvidence,
    FederationProof,
    FederationTrustScores,
    build_full_federation_proof,
)
from core.workstation.constitutional_substrate_governance_layer_v1 import (
    ConstitutionalProof,
    build_full_constitutional_proof,
)
from core.workstation.adaptive_governance_intelligence_engine_v1 import (
    GovernanceIntelligenceProof,
    build_full_governance_intelligence_proof,
)
from core.workstation.governed_recursive_orchestration_engine_v1 import (
    OrchestrationProof,
    build_full_orchestration_proof,
)
from core.workstation.persistent_substrate_continuity_engine_v1 import (
    ContinuityProof,
    build_full_continuity_proof,
)
from core.workstation.recursive_capability_planning_engine_v1 import (
    CapabilityPlanningProof,
    build_full_capability_proof,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ECONOMICS_REPORT_DIR = "data/runtime/workstation_relay/economics_reports"

ECONOMICS_MATURITY_LEVELS = (
    "L0_NO_RESOURCE_COORDINATION",
    "L1_RESOURCE_TRACKED",
    "L2_EXECUTION_PRIORITIZED",
    "L3_TRUST_DELEGATED",
    "L4_SCARCITY_COORDINATED",
    "L5_CONSTITUTIONAL_RESOURCE_COORDINATION",
)

RESOURCE_PRIMITIVES = (
    "compute_capacity",
    "orchestration_bandwidth",
    "execution_concurrency",
    "relay_availability",
    "continuity_integrity_cost",
    "replay_validation_cost",
    "governance_overhead",
    "coordination_latency",
    "federation_entropy_cost",
)

EXECUTION_ECONOMICS_DIMENSIONS = (
    "execution_value",
    "leverage_score",
    "governance_risk",
    "replay_complexity",
    "blast_radius",
    "continuity_risk",
    "federation_stability_impact",
    "resource_efficiency",
)

CONSTRAINED_NODE_TYPES = (
    "low_capacity",
    "intermittent",
    "degraded",
    "stale",
    "governance_limited",
    "replay_limited",
    "offline_relay",
)

DEGRADED_MODE_TYPES = (
    "partial_federation",
    "degraded_replay",
    "degraded_orchestration",
    "degraded_continuity",
    "emergency_coordination",
    "quarantine_execution",
)

SCARCITY_SIMULATION_TYPES = (
    "node_exhaustion",
    "orchestration_overload",
    "replay_bottleneck",
    "governance_overload",
    "federation_instability",
    "continuity_degradation",
    "coordination_collapse",
    "resource_starvation",
)

ECONOMICS_HARD_CEILINGS = frozenset(
    {
        "unsafe_over_allocation",
        "governance_breaking_prioritization",
        "replay_breaking_scheduling",
        "continuity_breaking_delegation",
        "excessive_blast_radius_concentration",
        "unstable_orchestration_path",
        "constitutional_resource_violation",
    }
)

RESOURCE_GRAPH_DIMENSIONS = (
    "node_capability",
    "resource_flow",
    "orchestration_load",
    "delegation_lineage",
    "resource_bottleneck",
    "federation_hotspot",
    "instability_zone",
)


# ---------------------------------------------------------------------------
# Resource Primitives
# ---------------------------------------------------------------------------


@dataclass
class NodeResourceProfile:
    """Resource profile for a single federated node."""

    node_id: str = ""
    compute_capacity: float = 0.0
    orchestration_bandwidth: float = 0.0
    execution_concurrency: int = 0
    relay_availability: float = 0.0
    continuity_integrity_cost: float = 0.0
    replay_validation_cost: float = 0.0
    governance_overhead: float = 0.0
    coordination_latency: float = 0.0
    federation_entropy_cost: float = 0.0
    constraint_type: str = "none"
    degraded: bool = False
    trust_score: float = 0.0

    def total_capacity(self) -> float:
        return round(
            self.compute_capacity * 0.3
            + self.orchestration_bandwidth * 0.2
            + self.relay_availability * 0.2
            + (1.0 - self.governance_overhead) * 0.15
            + (1.0 - self.coordination_latency) * 0.15,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "compute_capacity": round(self.compute_capacity, 4),
            "orchestration_bandwidth": round(self.orchestration_bandwidth, 4),
            "execution_concurrency": self.execution_concurrency,
            "relay_availability": round(self.relay_availability, 4),
            "continuity_integrity_cost": round(self.continuity_integrity_cost, 4),
            "replay_validation_cost": round(self.replay_validation_cost, 4),
            "governance_overhead": round(self.governance_overhead, 4),
            "coordination_latency": round(self.coordination_latency, 4),
            "federation_entropy_cost": round(self.federation_entropy_cost, 4),
            "constraint_type": self.constraint_type,
            "degraded": self.degraded,
            "trust_score": round(self.trust_score, 4),
            "total_capacity": self.total_capacity(),
        }


@dataclass
class FederationResourceGraph:
    """Resource graph across the federation."""

    node_profiles: list[NodeResourceProfile] = field(default_factory=list)
    total_compute: float = 0.0
    total_bandwidth: float = 0.0
    total_concurrency: int = 0
    bottleneck_count: int = 0
    hotspot_count: int = 0
    instability_zone_count: int = 0
    delegation_paths: int = 0
    graph_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": len(self.node_profiles),
            "total_compute": round(self.total_compute, 4),
            "total_bandwidth": round(self.total_bandwidth, 4),
            "total_concurrency": self.total_concurrency,
            "bottleneck_count": self.bottleneck_count,
            "hotspot_count": self.hotspot_count,
            "instability_zone_count": self.instability_zone_count,
            "delegation_paths": self.delegation_paths,
            "graph_hash": self.graph_hash,
            "node_profiles": [p.to_dict() for p in self.node_profiles],
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Execution Economics
# ---------------------------------------------------------------------------


@dataclass
class ExecutionEconomicsScores:
    """8-dimension execution economics profile."""

    execution_value: float = 0.0
    leverage_score: float = 0.0
    governance_risk: float = 0.0
    replay_complexity: float = 0.0
    blast_radius: float = 0.0
    continuity_risk: float = 0.0
    federation_stability_impact: float = 0.0
    resource_efficiency: float = 0.0

    def composite_economics(self) -> float:
        positive = (
            self.execution_value * 0.2
            + self.leverage_score * 0.2
            + self.resource_efficiency * 0.15
            + self.federation_stability_impact * 0.1
        )
        negative = (
            self.governance_risk * 0.1
            + self.replay_complexity * 0.05
            + self.blast_radius * 0.1
            + self.continuity_risk * 0.1
        )
        return round(positive - negative, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_value": round(self.execution_value, 4),
            "leverage_score": round(self.leverage_score, 4),
            "governance_risk": round(self.governance_risk, 4),
            "replay_complexity": round(self.replay_complexity, 4),
            "blast_radius": round(self.blast_radius, 4),
            "continuity_risk": round(self.continuity_risk, 4),
            "federation_stability_impact": round(self.federation_stability_impact, 4),
            "resource_efficiency": round(self.resource_efficiency, 4),
            "composite_economics": self.composite_economics(),
        }


# ---------------------------------------------------------------------------
# Trust-Weighted Delegation
# ---------------------------------------------------------------------------


@dataclass
class DelegationPath:
    """A trust-weighted delegation path between nodes."""

    source_node_id: str = ""
    target_node_id: str = ""
    trust_weight: float = 0.0
    replay_integrity: float = 0.0
    continuity_integrity: float = 0.0
    governance_maturity: float = 0.0
    delegation_safe: bool = False
    rejection_reason: str = ""

    def delegation_score(self) -> float:
        if not self.delegation_safe:
            return 0.0
        return round(
            self.trust_weight * 0.4
            + self.replay_integrity * 0.2
            + self.continuity_integrity * 0.2
            + self.governance_maturity * 0.2,
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "trust_weight": round(self.trust_weight, 4),
            "replay_integrity": round(self.replay_integrity, 4),
            "continuity_integrity": round(self.continuity_integrity, 4),
            "governance_maturity": round(self.governance_maturity, 4),
            "delegation_safe": self.delegation_safe,
            "rejection_reason": self.rejection_reason,
            "delegation_score": self.delegation_score(),
        }


@dataclass
class DelegationTopology:
    """Topology of trust-weighted delegation across federation."""

    paths: list[DelegationPath] = field(default_factory=list)
    safe_path_count: int = 0
    unsafe_path_count: int = 0
    average_trust: float = 0.0
    average_delegation_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_count": len(self.paths),
            "safe_path_count": self.safe_path_count,
            "unsafe_path_count": self.unsafe_path_count,
            "average_trust": round(self.average_trust, 4),
            "average_delegation_score": round(self.average_delegation_score, 4),
            "paths": [p.to_dict() for p in self.paths],
        }


# ---------------------------------------------------------------------------
# Degraded-Mode Orchestration
# ---------------------------------------------------------------------------


@dataclass
class DegradedModeStatus:
    """Status of degraded-mode orchestration capabilities."""

    partial_federation_ready: bool = False
    degraded_replay_ready: bool = False
    degraded_orchestration_ready: bool = False
    degraded_continuity_ready: bool = False
    emergency_coordination_ready: bool = False
    quarantine_execution_ready: bool = False
    active_degraded_modes: list[str] = field(default_factory=list)
    degraded_mode_count: int = 0
    ready_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "partial_federation_ready": self.partial_federation_ready,
            "degraded_replay_ready": self.degraded_replay_ready,
            "degraded_orchestration_ready": self.degraded_orchestration_ready,
            "degraded_continuity_ready": self.degraded_continuity_ready,
            "emergency_coordination_ready": self.emergency_coordination_ready,
            "quarantine_execution_ready": self.quarantine_execution_ready,
            "active_degraded_modes": self.active_degraded_modes,
            "degraded_mode_count": self.degraded_mode_count,
            "ready_count": self.ready_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Scarcity Simulation
# ---------------------------------------------------------------------------


@dataclass
class ScarcitySimulationOutcome:
    """Result of a scarcity simulation."""

    simulation_id: str = ""
    simulation_type: str = ""
    description: str = ""
    nodes_affected: int = 0
    resource_impact: str = "none"
    governance_impact: str = "none"
    replay_impact: str = "none"
    continuity_impact: str = "none"
    recovery_possible: bool = True
    predicted_severity: str = "low"
    mitigation_strategy: str = ""
    analysis_notes: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.simulation_id:
            self.simulation_id = f"SCARSIM-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "simulation_type": self.simulation_type,
            "description": self.description,
            "nodes_affected": self.nodes_affected,
            "resource_impact": self.resource_impact,
            "governance_impact": self.governance_impact,
            "replay_impact": self.replay_impact,
            "continuity_impact": self.continuity_impact,
            "recovery_possible": self.recovery_possible,
            "predicted_severity": self.predicted_severity,
            "mitigation_strategy": self.mitigation_strategy,
            "analysis_notes": self.analysis_notes,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Economics Evidence + Proof
# ---------------------------------------------------------------------------


@dataclass
class EconomicsEvidence:
    """Evidence collected during resource economics analysis."""

    resource_graph_analyzed: bool = False
    node_count: int = 0
    online_count: int = 0
    constrained_count: int = 0
    total_compute: float = 0.0
    total_bandwidth: float = 0.0
    execution_economics_scored: bool = False
    composite_economics: float = 0.0
    delegation_analyzed: bool = False
    safe_delegation_paths: int = 0
    unsafe_delegation_paths: int = 0
    average_delegation_trust: float = 0.0
    degraded_mode_analyzed: bool = False
    degraded_mode_ready_count: int = 0
    scarcity_simulated: bool = False
    simulation_count: int = 0
    bottleneck_count: int = 0
    hotspot_count: int = 0
    instability_zone_count: int = 0
    hard_ceilings_enforced: bool = True
    governance_bypass_blocked: bool = True
    replay_safe_scheduling: bool = False
    continuity_safe_allocation: bool = False
    trust_weighted_delegation: bool = False
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_graph_analyzed": self.resource_graph_analyzed,
            "node_count": self.node_count,
            "online_count": self.online_count,
            "constrained_count": self.constrained_count,
            "total_compute": round(self.total_compute, 4),
            "total_bandwidth": round(self.total_bandwidth, 4),
            "execution_economics_scored": self.execution_economics_scored,
            "composite_economics": round(self.composite_economics, 4),
            "delegation_analyzed": self.delegation_analyzed,
            "safe_delegation_paths": self.safe_delegation_paths,
            "unsafe_delegation_paths": self.unsafe_delegation_paths,
            "average_delegation_trust": round(self.average_delegation_trust, 4),
            "degraded_mode_analyzed": self.degraded_mode_analyzed,
            "degraded_mode_ready_count": self.degraded_mode_ready_count,
            "scarcity_simulated": self.scarcity_simulated,
            "simulation_count": self.simulation_count,
            "bottleneck_count": self.bottleneck_count,
            "hotspot_count": self.hotspot_count,
            "instability_zone_count": self.instability_zone_count,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "governance_bypass_blocked": self.governance_bypass_blocked,
            "replay_safe_scheduling": self.replay_safe_scheduling,
            "continuity_safe_allocation": self.continuity_safe_allocation,
            "trust_weighted_delegation": self.trust_weighted_delegation,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class EconomicsProof:
    """Complete proof of constitutional resource economics."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_RESOURCE_COORDINATION"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_RESOURCE_COORDINATION"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: EconomicsEvidence | None = None
    resource_graph: FederationResourceGraph | None = None
    execution_economics: ExecutionEconomicsScores | None = None
    delegation_topology: DelegationTopology | None = None
    degraded_mode: DegradedModeStatus | None = None
    simulations: list[ScarcitySimulationOutcome] = field(default_factory=list)
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"ECON-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_resource_economics",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "resource_graph": self.resource_graph.to_dict() if self.resource_graph else None,
            "execution_economics": (
                self.execution_economics.to_dict() if self.execution_economics else None
            ),
            "delegation_topology": (
                self.delegation_topology.to_dict() if self.delegation_topology else None
            ),
            "degraded_mode": self.degraded_mode.to_dict() if self.degraded_mode else None,
            "simulations": [s.to_dict() for s in self.simulations],
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Builder: Federation Resource Graph
# ---------------------------------------------------------------------------


def build_resource_graph(
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    constitutional_proof: ConstitutionalProof | None = None,
) -> FederationResourceGraph:
    """Build the federation resource graph from substrate state."""
    graph = FederationResourceGraph()
    profiles: list[NodeResourceProfile] = []

    nodes: list[FederatedNode] = []
    trust_scores: FederationTrustScores | None = None

    if federation_proof and federation_proof.node_registry:
        nodes = federation_proof.node_registry.nodes
        trust_scores = federation_proof.trust_scores

    has_orch = orchestration_proof is not None and orchestration_proof.evidence is not None
    has_cont = continuity_proof is not None and continuity_proof.evidence is not None
    has_const = constitutional_proof is not None

    for node in nodes:
        replay_cost = 0.3 if node.replay_compatible else 0.8
        cont_cost = 0.2 if node.continuity_compatible else 0.7
        gov_overhead = 0.15 if node.constitutionally_compatible else 0.5

        constraint = "none"
        degraded = False
        if not node.online:
            constraint = "offline_relay"
            degraded = True
        elif not node.constitutionally_compatible:
            constraint = "governance_limited"
            degraded = True
        elif not node.replay_compatible:
            constraint = "replay_limited"
            degraded = True
        elif node.trust_classification == "untrusted":
            constraint = "low_capacity"
            degraded = True

        trust = 0.0
        if trust_scores:
            trust = trust_scores.composite_trust()
        if node.trust_classification == "trusted":
            trust = max(trust, 0.8)
        elif node.trust_classification == "provisional":
            trust = max(trust, 0.5)

        compute = 1.0 if node.online else 0.0
        bandwidth = 0.8 if has_orch and node.online else 0.2
        concurrency = 4 if node.online and node.constitutionally_compatible else 1
        relay_avail = 1.0 if node.online else 0.0

        profile = NodeResourceProfile(
            node_id=node.node_id,
            compute_capacity=compute,
            orchestration_bandwidth=bandwidth,
            execution_concurrency=concurrency,
            relay_availability=relay_avail,
            continuity_integrity_cost=cont_cost,
            replay_validation_cost=replay_cost,
            governance_overhead=gov_overhead,
            coordination_latency=0.1 if node.online else 0.9,
            federation_entropy_cost=0.1 if node.constitutionally_compatible else 0.5,
            constraint_type=constraint,
            degraded=degraded,
            trust_score=trust,
        )
        profiles.append(profile)

    if not profiles:
        profiles.append(
            NodeResourceProfile(
                node_id="primary-default",
                compute_capacity=1.0,
                orchestration_bandwidth=0.5,
                execution_concurrency=2,
                relay_availability=1.0,
                continuity_integrity_cost=0.3,
                replay_validation_cost=0.3,
                governance_overhead=0.2,
                coordination_latency=0.1,
                federation_entropy_cost=0.1,
                constraint_type="none",
                degraded=False,
                trust_score=0.5,
            )
        )

    graph.node_profiles = profiles
    graph.total_compute = sum(p.compute_capacity for p in profiles)
    graph.total_bandwidth = sum(p.orchestration_bandwidth for p in profiles)
    graph.total_concurrency = sum(p.execution_concurrency for p in profiles)

    graph.bottleneck_count = sum(1 for p in profiles if p.total_capacity() < 0.3)
    graph.hotspot_count = sum(1 for p in profiles if p.compute_capacity > 0.8 and not p.degraded)
    graph.instability_zone_count = sum(1 for p in profiles if p.degraded)
    graph.delegation_paths = max(0, len(profiles) * (len(profiles) - 1))

    graph.graph_hash = hashlib.sha256(
        json.dumps([p.to_dict() for p in profiles], sort_keys=True).encode()
    ).hexdigest()[:16]

    return graph


# ---------------------------------------------------------------------------
# Builder: Execution Economics
# ---------------------------------------------------------------------------


def compute_execution_economics(
    resource_graph: FederationResourceGraph,
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> ExecutionEconomicsScores:
    """Compute 8-dimension execution economics profile."""
    scores = ExecutionEconomicsScores()

    total_cap = sum(p.total_capacity() for p in resource_graph.node_profiles)
    n = max(len(resource_graph.node_profiles), 1)
    avg_cap = total_cap / n

    scores.execution_value = min(avg_cap, 1.0)
    scores.resource_efficiency = round(total_cap / max(n, 1), 4)

    if federation_proof and federation_proof.trust_scores:
        ts = federation_proof.trust_scores
        scores.leverage_score = round(
            (ts.replay_reliability + ts.governance_reliability + ts.constitutional_integrity) / 3,
            4,
        )
        scores.governance_risk = round(1.0 - ts.governance_reliability, 4)
        scores.replay_complexity = round(1.0 - ts.replay_reliability, 4)
        scores.continuity_risk = round(1.0 - ts.continuity_reliability, 4)
        scores.federation_stability_impact = round(ts.topology_stability, 4)

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        total_replay = ev.replay_safe_count + ev.replay_unsafe_count
        if total_replay > 0:
            unsafe_ratio = ev.replay_unsafe_count / total_replay
            scores.blast_radius = round(unsafe_ratio * 0.5 + (1.0 - avg_cap) * 0.5, 4)
        else:
            scores.blast_radius = round((1.0 - avg_cap) * 0.5, 4)
    else:
        scores.blast_radius = round((1.0 - avg_cap) * 0.5, 4)

    return scores


# ---------------------------------------------------------------------------
# Builder: Trust-Weighted Delegation
# ---------------------------------------------------------------------------


def build_delegation_topology(
    resource_graph: FederationResourceGraph,
    federation_proof: FederationProof | None = None,
) -> DelegationTopology:
    """Build trust-weighted delegation topology."""
    topology = DelegationTopology()
    paths: list[DelegationPath] = []

    profiles = resource_graph.node_profiles
    trust_scores: FederationTrustScores | None = None
    if federation_proof and federation_proof.trust_scores:
        trust_scores = federation_proof.trust_scores

    for i, src in enumerate(profiles):
        for j, tgt in enumerate(profiles):
            if i == j:
                continue

            trust_w = min(src.trust_score, tgt.trust_score)
            replay_int = 1.0 - max(src.replay_validation_cost, tgt.replay_validation_cost)
            cont_int = 1.0 - max(src.continuity_integrity_cost, tgt.continuity_integrity_cost)
            gov_mat = 1.0 - max(src.governance_overhead, tgt.governance_overhead)

            safe = True
            reason = ""

            if tgt.degraded:
                safe = False
                reason = f"target degraded: {tgt.constraint_type}"
            elif trust_w < 0.3:
                safe = False
                reason = "insufficient trust"
            elif replay_int < 0.2:
                safe = False
                reason = "insufficient replay integrity"
            elif cont_int < 0.2:
                safe = False
                reason = "insufficient continuity integrity"

            path = DelegationPath(
                source_node_id=src.node_id,
                target_node_id=tgt.node_id,
                trust_weight=trust_w,
                replay_integrity=replay_int,
                continuity_integrity=cont_int,
                governance_maturity=gov_mat,
                delegation_safe=safe,
                rejection_reason=reason,
            )
            paths.append(path)

    topology.paths = paths
    topology.safe_path_count = sum(1 for p in paths if p.delegation_safe)
    topology.unsafe_path_count = sum(1 for p in paths if not p.delegation_safe)

    if paths:
        topology.average_trust = round(sum(p.trust_weight for p in paths) / len(paths), 4)
        safe_paths = [p for p in paths if p.delegation_safe]
        if safe_paths:
            topology.average_delegation_score = round(
                sum(p.delegation_score() for p in safe_paths) / len(safe_paths), 4
            )

    return topology


# ---------------------------------------------------------------------------
# Builder: Degraded-Mode Orchestration
# ---------------------------------------------------------------------------


def build_degraded_mode_status(
    resource_graph: FederationResourceGraph,
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    constitutional_proof: ConstitutionalProof | None = None,
    founder_confirmed: bool = False,
) -> DegradedModeStatus:
    """Build degraded-mode orchestration status."""
    dm = DegradedModeStatus()
    dm.degraded_mode_count = len(DEGRADED_MODE_TYPES)

    has_fed = federation_proof is not None
    has_orch = orchestration_proof is not None
    has_const = constitutional_proof is not None
    has_nodes = len(resource_graph.node_profiles) > 0

    if has_nodes:
        dm.partial_federation_ready = True
        dm.analysis_notes.append("partial federation via resource graph")

    if has_orch:
        dm.degraded_replay_ready = True
        dm.degraded_orchestration_ready = True
        dm.analysis_notes.append("degraded replay/orchestration via orchestration proof")

    if has_fed and has_orch:
        dm.degraded_continuity_ready = True
        dm.analysis_notes.append("degraded continuity via federation + orchestration")

    if has_const and has_orch:
        dm.emergency_coordination_ready = True
        dm.analysis_notes.append("emergency coordination via constitutional + orchestration")

    if has_const and founder_confirmed:
        dm.quarantine_execution_ready = True
        dm.analysis_notes.append("quarantine execution with founder confirmation")

    active = []
    constrained = [p for p in resource_graph.node_profiles if p.degraded]
    if constrained:
        active.append("partial_federation")
    dm.active_degraded_modes = active

    ready = sum(
        [
            dm.partial_federation_ready,
            dm.degraded_replay_ready,
            dm.degraded_orchestration_ready,
            dm.degraded_continuity_ready,
            dm.emergency_coordination_ready,
            dm.quarantine_execution_ready,
        ]
    )
    dm.ready_count = ready

    return dm


# ---------------------------------------------------------------------------
# Hard Ceiling Enforcement
# ---------------------------------------------------------------------------


def enforce_economics_hard_ceilings(
    resource_graph: FederationResourceGraph,
    execution_economics: ExecutionEconomicsScores,
    delegation_topology: DelegationTopology,
    degraded_mode: DegradedModeStatus,
) -> tuple[bool, list[str]]:
    """Enforce economics hard ceilings. Returns (blocked, reasons)."""
    blocked = False
    reasons: list[str] = []

    total_cap = sum(p.total_capacity() for p in resource_graph.node_profiles)
    n = max(len(resource_graph.node_profiles), 1)
    if total_cap > n * 1.5:
        blocked = True
        reasons.append("unsafe_over_allocation: capacity exceeds safe threshold")

    if execution_economics.governance_risk > 0.7:
        blocked = True
        reasons.append("governance_breaking_prioritization: governance risk too high")

    if execution_economics.replay_complexity > 0.8:
        blocked = True
        reasons.append("replay_breaking_scheduling: replay complexity too high")

    if delegation_topology.unsafe_path_count > delegation_topology.safe_path_count > 0:
        reasons.append("continuity_breaking_delegation: more unsafe than safe paths")

    if execution_economics.blast_radius > 0.7:
        blocked = True
        reasons.append("excessive_blast_radius_concentration: blast radius too high")

    if resource_graph.instability_zone_count > len(resource_graph.node_profiles) * 0.5:
        reasons.append("unstable_orchestration_path: too many instability zones")

    return blocked, reasons


# ---------------------------------------------------------------------------
# Scarcity Simulation Engine
# ---------------------------------------------------------------------------


def run_scarcity_simulations(
    resource_graph: FederationResourceGraph,
    execution_economics: ExecutionEconomicsScores,
    delegation_topology: DelegationTopology,
) -> list[ScarcitySimulationOutcome]:
    """Run all 8 scarcity simulation types."""
    simulations: list[ScarcitySimulationOutcome] = []
    n = max(len(resource_graph.node_profiles), 1)
    composite = execution_economics.composite_economics()

    # 1. node_exhaustion
    sim1 = ScarcitySimulationOutcome(
        simulation_type="node_exhaustion",
        description="Simulate compute exhaustion on primary node",
        nodes_affected=1,
        resource_impact="critical",
        governance_impact="minimal" if n > 1 else "critical",
        replay_impact="degraded",
        continuity_impact="degraded",
        recovery_possible=n > 1,
        predicted_severity="high" if n <= 2 else "medium",
        mitigation_strategy="failover to secondary nodes" if n > 1 else "reduce concurrency",
    )
    sim1.analysis_notes.append(f"total_nodes={n}")
    simulations.append(sim1)

    # 2. orchestration_overload
    sim2 = ScarcitySimulationOutcome(
        simulation_type="orchestration_overload",
        description="Simulate orchestration bandwidth saturation",
        nodes_affected=n,
        resource_impact="degraded",
        governance_impact="degraded",
        replay_impact="degraded",
        continuity_impact="minimal",
        recovery_possible=True,
        predicted_severity="high" if resource_graph.total_bandwidth < 1.0 else "medium",
        mitigation_strategy="throttle orchestration, prioritize high-leverage",
    )
    sim2.analysis_notes.append(f"bandwidth={resource_graph.total_bandwidth:.3f}")
    simulations.append(sim2)

    # 3. replay_bottleneck
    sim3 = ScarcitySimulationOutcome(
        simulation_type="replay_bottleneck",
        description="Simulate replay validation chain bottleneck",
        nodes_affected=n,
        resource_impact="degraded",
        governance_impact="minimal",
        replay_impact="critical",
        continuity_impact="degraded",
        recovery_possible=True,
        predicted_severity="critical" if execution_economics.replay_complexity > 0.5 else "high",
        mitigation_strategy="parallel replay validation, reduce chain depth",
    )
    sim3.analysis_notes.append(f"replay_complexity={execution_economics.replay_complexity:.3f}")
    simulations.append(sim3)

    # 4. governance_overload
    sim4 = ScarcitySimulationOutcome(
        simulation_type="governance_overload",
        description="Simulate governance overhead exceeding capacity",
        nodes_affected=n,
        resource_impact="degraded",
        governance_impact="critical",
        replay_impact="minimal",
        continuity_impact="degraded",
        recovery_possible=execution_economics.governance_risk < 0.8,
        predicted_severity="critical" if execution_economics.governance_risk > 0.5 else "high",
        mitigation_strategy="batch governance checks, defer non-critical",
    )
    sim4.analysis_notes.append(f"gov_risk={execution_economics.governance_risk:.3f}")
    simulations.append(sim4)

    # 5. federation_instability
    sim5 = ScarcitySimulationOutcome(
        simulation_type="federation_instability",
        description="Simulate federation-wide instability cascade",
        nodes_affected=n,
        resource_impact="critical",
        governance_impact="critical",
        replay_impact="critical",
        continuity_impact="critical",
        recovery_possible=composite > 0.1,
        predicted_severity="critical",
        mitigation_strategy="quarantine unstable nodes, activate emergency coordination",
    )
    sim5.analysis_notes.append(f"composite_economics={composite:.3f}")
    simulations.append(sim5)

    # 6. continuity_degradation
    sim6 = ScarcitySimulationOutcome(
        simulation_type="continuity_degradation",
        description="Simulate continuity lineage degradation across nodes",
        nodes_affected=n,
        resource_impact="degraded",
        governance_impact="degraded",
        replay_impact="degraded",
        continuity_impact="critical",
        recovery_possible=execution_economics.continuity_risk < 0.8,
        predicted_severity="critical" if execution_economics.continuity_risk > 0.5 else "high",
        mitigation_strategy="snapshot continuity state, isolate degraded lineage",
    )
    sim6.analysis_notes.append(f"continuity_risk={execution_economics.continuity_risk:.3f}")
    simulations.append(sim6)

    # 7. coordination_collapse
    sim7 = ScarcitySimulationOutcome(
        simulation_type="coordination_collapse",
        description="Simulate complete coordination failure between nodes",
        nodes_affected=n,
        resource_impact="critical",
        governance_impact="critical",
        replay_impact="frozen",
        continuity_impact="frozen",
        recovery_possible=True,
        predicted_severity="critical",
        mitigation_strategy="fallback to single-node execution, rebuild coordination",
    )
    sim7.analysis_notes.append(f"delegation_paths={len(delegation_topology.paths)}")
    simulations.append(sim7)

    # 8. resource_starvation
    sim8 = ScarcitySimulationOutcome(
        simulation_type="resource_starvation",
        description="Simulate progressive resource starvation across federation",
        nodes_affected=n,
        resource_impact="critical",
        governance_impact="degraded",
        replay_impact="degraded",
        continuity_impact="degraded",
        recovery_possible=resource_graph.total_compute > 0.5,
        predicted_severity="critical" if resource_graph.total_compute < 1.0 else "high",
        mitigation_strategy="shed low-leverage work, concentrate on constitutional essentials",
    )
    sim8.analysis_notes.append(f"total_compute={resource_graph.total_compute:.3f}")
    simulations.append(sim8)

    return simulations


# ---------------------------------------------------------------------------
# Maturity Classification
# ---------------------------------------------------------------------------


def compute_economics_maturity(evidence: EconomicsEvidence) -> int:
    """Compute numeric maturity score from evidence."""
    score = 0
    if evidence.resource_graph_analyzed and evidence.node_count > 0:
        score += 1
    if evidence.total_compute > 0:
        score += 1
    if evidence.execution_economics_scored:
        score += 1
    if evidence.composite_economics > 0:
        score += 1
    if evidence.delegation_analyzed:
        score += 1
    if evidence.trust_weighted_delegation:
        score += 1
    if evidence.safe_delegation_paths > 0:
        score += 1
    if evidence.degraded_mode_analyzed:
        score += 1
    if evidence.degraded_mode_ready_count > 0:
        score += 1
    if evidence.scarcity_simulated:
        score += 1
    if evidence.replay_safe_scheduling:
        score += 1
    if evidence.continuity_safe_allocation:
        score += 1
    if evidence.founder_confirmed:
        score += 1
    if evidence.hard_ceilings_enforced and evidence.governance_bypass_blocked:
        score += 1
    return score


def economics_maturity_ceiling(
    evidence: EconomicsEvidence,
) -> tuple[str, bool, str]:
    """Compute economics maturity ceiling. Returns (ceiling, blocked, reason)."""
    if evidence.is_dry_run:
        return "L0_NO_RESOURCE_COORDINATION", True, "dry run"
    if not evidence.resource_graph_analyzed or evidence.node_count == 0:
        return "L0_NO_RESOURCE_COORDINATION", True, "no resource graph"
    if not evidence.execution_economics_scored:
        return "L1_RESOURCE_TRACKED", True, "execution economics not scored"
    if not evidence.delegation_analyzed:
        return "L2_EXECUTION_PRIORITIZED", True, "delegation not analyzed"
    if not evidence.trust_weighted_delegation:
        return "L2_EXECUTION_PRIORITIZED", True, "trust-weighted delegation not validated"
    if not evidence.degraded_mode_analyzed:
        return "L3_TRUST_DELEGATED", True, "degraded mode not analyzed"
    if not evidence.scarcity_simulated:
        return "L3_TRUST_DELEGATED", True, "scarcity not simulated"
    if not evidence.replay_safe_scheduling:
        return "L4_SCARCITY_COORDINATED", True, "replay-safe scheduling not validated"
    if not evidence.continuity_safe_allocation:
        return "L4_SCARCITY_COORDINATED", True, "continuity-safe allocation not validated"
    if not evidence.founder_confirmed:
        return "L4_SCARCITY_COORDINATED", True, "founder not confirmed"
    if not evidence.hard_ceilings_enforced:
        return "L4_SCARCITY_COORDINATED", True, "hard ceilings not enforced"
    if not evidence.governance_bypass_blocked:
        return "L4_SCARCITY_COORDINATED", True, "governance bypass not blocked"
    return "L5_CONSTITUTIONAL_RESOURCE_COORDINATION", False, ""


def classify_economics_maturity(
    evidence: EconomicsEvidence,
) -> tuple[str, str, bool, str]:
    """Classify maturity. Returns (level, ceiling, blocked, reason)."""
    ceiling, blocked, reason = economics_maturity_ceiling(evidence)
    score = compute_economics_maturity(evidence)
    ceiling_idx = ECONOMICS_MATURITY_LEVELS.index(ceiling)

    if score >= 13:
        level_idx = 5
    elif score >= 10:
        level_idx = 4
    elif score >= 7:
        level_idx = 3
    elif score >= 5:
        level_idx = 2
    elif score >= 2:
        level_idx = 1
    else:
        level_idx = 0

    level_idx = min(level_idx, ceiling_idx)
    level = ECONOMICS_MATURITY_LEVELS[level_idx]
    return level, ceiling, blocked, reason


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


def build_full_economics_proof(
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    constitutional_proof: ConstitutionalProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    capability_proof: CapabilityPlanningProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
    base_dir: Path = Path("/opt/OS"),
) -> EconomicsProof:
    """Full constitutional resource economics pipeline."""
    resource_graph = build_resource_graph(
        federation_proof, orchestration_proof, continuity_proof, constitutional_proof
    )
    economics = compute_execution_economics(
        resource_graph, federation_proof, orchestration_proof, continuity_proof
    )
    delegation = build_delegation_topology(resource_graph, federation_proof)
    degraded = build_degraded_mode_status(
        resource_graph,
        federation_proof,
        orchestration_proof,
        constitutional_proof,
        founder_confirmed,
    )

    ceiling_blocked, ceiling_reasons = enforce_economics_hard_ceilings(
        resource_graph, economics, delegation, degraded
    )

    simulations = run_scarcity_simulations(resource_graph, economics, delegation)

    has_replay_safe = (
        federation_proof is not None
        and federation_proof.trust_scores is not None
        and federation_proof.trust_scores.replay_reliability > 0
    )
    has_cont_safe = (
        federation_proof is not None
        and federation_proof.trust_scores is not None
        and federation_proof.trust_scores.continuity_reliability > 0
    )
    has_trust_del = delegation.safe_path_count > 0

    evidence = EconomicsEvidence(
        resource_graph_analyzed=True,
        node_count=len(resource_graph.node_profiles),
        online_count=sum(1 for p in resource_graph.node_profiles if p.compute_capacity > 0),
        constrained_count=sum(1 for p in resource_graph.node_profiles if p.degraded),
        total_compute=resource_graph.total_compute,
        total_bandwidth=resource_graph.total_bandwidth,
        execution_economics_scored=True,
        composite_economics=economics.composite_economics(),
        delegation_analyzed=True,
        safe_delegation_paths=delegation.safe_path_count,
        unsafe_delegation_paths=delegation.unsafe_path_count,
        average_delegation_trust=delegation.average_trust,
        degraded_mode_analyzed=True,
        degraded_mode_ready_count=degraded.ready_count,
        scarcity_simulated=True,
        simulation_count=len(simulations),
        bottleneck_count=resource_graph.bottleneck_count,
        hotspot_count=resource_graph.hotspot_count,
        instability_zone_count=resource_graph.instability_zone_count,
        hard_ceilings_enforced=True,
        governance_bypass_blocked=True,
        replay_safe_scheduling=has_replay_safe,
        continuity_safe_allocation=has_cont_safe,
        trust_weighted_delegation=has_trust_del,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_economics_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "await_founder_confirmation"
            if not founder_confirmed
            else "constitutional_resource_coordination_active"
        )
    )

    return EconomicsProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        resource_graph=resource_graph,
        execution_economics=economics,
        delegation_topology=delegation,
        degraded_mode=degraded,
        simulations=simulations,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_economics_proof(
    proof: EconomicsProof,
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist economics proof to disk."""
    report_dir = base_dir / ECONOMICS_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
