"""Governed Recursive Orchestration Engine v1.

Safely sequences, simulates, validates, replays, and governs
multi-phase recursive substrate evolution plans. Builds execution
DAGs, calculates blast radius, validates replayability and rollback
feasibility, sequences upgrade waves, and prevents unsafe recursive
expansion.

The engine may: orchestrate, simulate, sequence, validate, analyze,
classify risk, generate rollback plans, compute blast radius.

The engine CANNOT: auto-deploy infrastructure, auto-promote maturity,
auto-modify canonical registries, auto-merge recursive plans, bypass
founder approval, or bypass governance replay contracts.

UMH substrate subsystem. Phase 96.8AW.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.workstation.recursive_capability_planning_engine_v1 import (
    CAPABILITY_DEPENDENCIES,
    CAPABILITY_MATURITY_LEVELS,
    SUBSTRATE_CAPABILITIES,
    UPGRADE_CATALOG,
    CapabilityGraph,
    CapabilityPlanningEvidence,
    CapabilityPlanningProof,
    LeverageScore,
    UpgradeProposal,
    build_capability_graph,
    generate_upgrade_proposals,
    score_upgrade,
)
from core.workstation.environment_mapping_engine_v1 import (
    CANDIDATE_TYPE_CANONICAL,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ORCHESTRATION_REPORT_DIR = Path("data/runtime/workstation_relay/orchestration_reports")

# ---------------------------------------------------------------------------
# Orchestration maturity levels
# ---------------------------------------------------------------------------

ORCHESTRATION_MATURITY_LEVELS = (
    "L0_SIMULATED_ORCHESTRATION",
    "L1_REPLAY_SAFE_ORCHESTRATION",
    "L2_ROLLBACK_SAFE_ORCHESTRATION",
    "L3_GOVERNED_ORCHESTRATION",
    "L4_RECURSIVE_ORCHESTRATION",
    "L5_GOVERNED_RECURSIVE_ORCHESTRATION",
)

ORCHESTRATION_MATURITY_REQUIREMENTS: dict[str, list[str]] = {
    "L0_SIMULATED_ORCHESTRATION": [],
    "L1_REPLAY_SAFE_ORCHESTRATION": [
        "dag_generated",
        "replay_validated",
    ],
    "L2_ROLLBACK_SAFE_ORCHESTRATION": [
        "dag_generated",
        "replay_validated",
        "rollback_validated",
    ],
    "L3_GOVERNED_ORCHESTRATION": [
        "dag_generated",
        "replay_validated",
        "rollback_validated",
        "governance_validated",
    ],
    "L4_RECURSIVE_ORCHESTRATION": [
        "dag_generated",
        "replay_validated",
        "rollback_validated",
        "governance_validated",
        "sequencing_validated",
        "blast_radius_analyzed",
    ],
    "L5_GOVERNED_RECURSIVE_ORCHESTRATION": [
        "dag_generated",
        "replay_validated",
        "rollback_validated",
        "governance_validated",
        "sequencing_validated",
        "blast_radius_analyzed",
        "simulation_completed",
        "founder_confirmed",
    ],
}

# ---------------------------------------------------------------------------
# DAG types
# ---------------------------------------------------------------------------

DAG_TYPES = frozenset(
    {
        "execution",
        "dependency",
        "governance",
        "rollback",
        "replay",
        "maturity",
        "infrastructure_mutation",
    }
)

# ---------------------------------------------------------------------------
# Simulation outcome types
# ---------------------------------------------------------------------------

SIMULATION_OUTCOMES = frozenset(
    {
        "successful_rollout",
        "partial_rollout",
        "stale_rollout",
        "replay_failure",
        "relay_disconnect",
        "governance_rejection",
        "rollback_recovery",
        "partial_infrastructure_mutation",
    }
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DAGNode:
    """A node in an orchestration DAG."""

    node_id: str = ""
    name: str = ""
    dag_type: str = "execution"
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    status: str = "pending"
    replay_safe: bool = False
    rollback_safe: bool = False
    governance_approved: bool = False
    blast_radius: float = 0.0
    wave: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.node_id:
            self.node_id = f"DAGN-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "dag_type": self.dag_type,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "status": self.status,
            "replay_safe": self.replay_safe,
            "rollback_safe": self.rollback_safe,
            "governance_approved": self.governance_approved,
            "blast_radius": round(self.blast_radius, 3),
            "wave": self.wave,
            "timestamp": self.timestamp,
        }


@dataclass
class OrchestrationDAG:
    """A complete orchestration DAG."""

    dag_id: str = ""
    dag_type: str = "execution"
    nodes: list[DAGNode] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    has_cycles: bool = False
    wave_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.dag_id:
            self.dag_id = f"DAG-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "dag_type": self.dag_type,
            "nodes": [n.to_dict() for n in self.nodes],
            "node_count": len(self.nodes),
            "edges": [list(e) for e in self.edges],
            "edge_count": len(self.edges),
            "has_cycles": self.has_cycles,
            "wave_count": self.wave_count,
            "timestamp": self.timestamp,
        }


@dataclass
class BlastRadius:
    """Blast radius analysis for a proposed upgrade."""

    analysis_id: str = ""
    upgrade_name: str = ""
    affected_registries: list[str] = field(default_factory=list)
    affected_relays: list[str] = field(default_factory=list)
    affected_adapters: list[str] = field(default_factory=list)
    affected_execution_chains: list[str] = field(default_factory=list)
    affected_proofs: list[str] = field(default_factory=list)
    affected_governance_surfaces: list[str] = field(default_factory=list)
    affected_topology_layers: list[str] = field(default_factory=list)
    total_affected: int = 0
    risk_score: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.analysis_id:
            self.analysis_id = f"BLAST-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()
        if self.total_affected == 0:
            self.total_affected = (
                len(self.affected_registries)
                + len(self.affected_relays)
                + len(self.affected_adapters)
                + len(self.affected_execution_chains)
                + len(self.affected_proofs)
                + len(self.affected_governance_surfaces)
                + len(self.affected_topology_layers)
            )
        if self.risk_score == 0.0 and self.total_affected > 0:
            self.risk_score = round(min(1.0, self.total_affected / 20.0), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "upgrade_name": self.upgrade_name,
            "affected_registries": self.affected_registries,
            "affected_relays": self.affected_relays,
            "affected_adapters": self.affected_adapters,
            "affected_execution_chains": self.affected_execution_chains,
            "affected_proofs": self.affected_proofs,
            "affected_governance_surfaces": self.affected_governance_surfaces,
            "affected_topology_layers": self.affected_topology_layers,
            "total_affected": self.total_affected,
            "risk_score": round(self.risk_score, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class RollbackPlan:
    """Rollback plan for a proposed upgrade."""

    plan_id: str = ""
    upgrade_name: str = ""
    rollback_strategy: str = ""
    rollback_replay_contract: list[str] = field(default_factory=list)
    rollback_dependency_validation: list[str] = field(default_factory=list)
    rollback_blast_radius: float = 0.0
    rollback_maturity_impact: str = ""
    rollback_safe: bool = False
    rollback_deterministic: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.plan_id:
            self.plan_id = f"RBACK-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "upgrade_name": self.upgrade_name,
            "rollback_strategy": self.rollback_strategy,
            "rollback_replay_contract": self.rollback_replay_contract,
            "rollback_dependency_validation": self.rollback_dependency_validation,
            "rollback_blast_radius": round(self.rollback_blast_radius, 3),
            "rollback_maturity_impact": self.rollback_maturity_impact,
            "rollback_safe": self.rollback_safe,
            "rollback_deterministic": self.rollback_deterministic,
            "timestamp": self.timestamp,
        }


@dataclass
class SimulationOutcome:
    """Result of a rollout simulation."""

    outcome_id: str = ""
    outcome_type: str = ""
    upgrade_name: str = ""
    succeeded: bool = False
    replay_intact: bool = False
    rollback_viable: bool = False
    governance_satisfied: bool = False
    blast_radius_acceptable: bool = False
    failure_reason: str = ""
    recovery_path: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.outcome_id:
            self.outcome_id = f"SIM-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "outcome_type": self.outcome_type,
            "upgrade_name": self.upgrade_name,
            "succeeded": self.succeeded,
            "replay_intact": self.replay_intact,
            "rollback_viable": self.rollback_viable,
            "governance_satisfied": self.governance_satisfied,
            "blast_radius_acceptable": self.blast_radius_acceptable,
            "failure_reason": self.failure_reason,
            "recovery_path": self.recovery_path,
            "timestamp": self.timestamp,
        }


@dataclass
class OrchestrationEvidence:
    """Evidence collected during orchestration analysis."""

    dag_generated: bool = False
    dag_count: int = 0
    replay_validated: bool = False
    replay_safe_count: int = 0
    replay_unsafe_count: int = 0
    rollback_validated: bool = False
    rollback_safe_count: int = 0
    rollback_unsafe_count: int = 0
    governance_validated: bool = False
    governance_bottleneck_count: int = 0
    sequencing_validated: bool = False
    wave_count: int = 0
    blast_radius_analyzed: bool = False
    max_blast_radius: float = 0.0
    simulation_completed: bool = False
    simulation_count: int = 0
    simulation_success_count: int = 0
    unsafe_chains_detected: int = 0
    conflict_count: int = 0
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dag_generated": self.dag_generated,
            "dag_count": self.dag_count,
            "replay_validated": self.replay_validated,
            "replay_safe_count": self.replay_safe_count,
            "replay_unsafe_count": self.replay_unsafe_count,
            "rollback_validated": self.rollback_validated,
            "rollback_safe_count": self.rollback_safe_count,
            "rollback_unsafe_count": self.rollback_unsafe_count,
            "governance_validated": self.governance_validated,
            "governance_bottleneck_count": self.governance_bottleneck_count,
            "sequencing_validated": self.sequencing_validated,
            "wave_count": self.wave_count,
            "blast_radius_analyzed": self.blast_radius_analyzed,
            "max_blast_radius": round(self.max_blast_radius, 3),
            "simulation_completed": self.simulation_completed,
            "simulation_count": self.simulation_count,
            "simulation_success_count": self.simulation_success_count,
            "unsafe_chains_detected": self.unsafe_chains_detected,
            "conflict_count": self.conflict_count,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class OrchestrationProof:
    """Complete proof of governed recursive orchestration."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_SIMULATED_ORCHESTRATION"
    maturity_ceiling: str = "L5_GOVERNED_RECURSIVE_ORCHESTRATION"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: OrchestrationEvidence | None = None
    dags: list[OrchestrationDAG] = field(default_factory=list)
    blast_radii: list[BlastRadius] = field(default_factory=list)
    rollback_plans: list[RollbackPlan] = field(default_factory=list)
    simulations: list[SimulationOutcome] = field(default_factory=list)
    sequenced_upgrades: list[str] = field(default_factory=list)
    unsafe_chains: list[str] = field(default_factory=list)
    governance_bottlenecks: list[str] = field(default_factory=list)
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"ORCHPROOF-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "governed_recursive_orchestration",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "dags": [d.to_dict() for d in self.dags],
            "dag_count": len(self.dags),
            "blast_radii": [b.to_dict() for b in self.blast_radii],
            "rollback_plans": [r.to_dict() for r in self.rollback_plans],
            "simulations": [s.to_dict() for s in self.simulations],
            "sequenced_upgrades": self.sequenced_upgrades,
            "unsafe_chains": self.unsafe_chains,
            "governance_bottlenecks": self.governance_bottlenecks,
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Upgrade blast radius mapping
# ---------------------------------------------------------------------------

UPGRADE_BLAST_MAP: dict[str, dict[str, list[str]]] = {
    "local_adapter_execution": {
        "registries": ["adapter_registry", "command_registry"],
        "relays": ["local_wsl_worker"],
        "adapters": ["obsidian", "local_filesystem", "docker_services"],
        "execution_chains": ["relay_transport", "proof_persistence"],
        "proofs": ["adapter_blueprint_proof", "environment_mapping_proof"],
        "governance_surfaces": ["founder_approval"],
        "topology_layers": ["local_filesystem", "docker_services"],
    },
    "cu_adapter_execution": {
        "registries": ["adapter_registry", "command_registry"],
        "relays": ["windows_interactive_desktop_relay"],
        "adapters": ["gmail", "google_drive", "notion"],
        "execution_chains": [
            "relay_transport",
            "chrome_foreground",
            "clipboard_extraction",
        ],
        "proofs": ["cu_ingestion_proof", "adapter_blueprint_proof"],
        "governance_surfaces": [
            "founder_approval",
            "foreground_cu_required",
            "screenshot_proof",
        ],
        "topology_layers": ["browser_sessions", "desktop_apps"],
    },
    "multi_platform_ingestion": {
        "registries": ["adapter_registry", "command_registry", "proof_registry"],
        "relays": ["windows_interactive_desktop_relay", "local_wsl_worker"],
        "adapters": ["all_discovered_adapters"],
        "execution_chains": [
            "relay_transport",
            "adapter_selection",
            "proof_persistence",
        ],
        "proofs": ["adapter_blueprint_proof", "replay_contract_proof"],
        "governance_surfaces": [
            "founder_approval",
            "per_platform_governance",
        ],
        "topology_layers": ["all_discovered_platforms"],
    },
    "relationship_graph_expansion": {
        "registries": ["topology_registry"],
        "relays": [],
        "adapters": [],
        "execution_chains": ["topology_mapping", "relationship_synthesis"],
        "proofs": ["topology_proof", "ingestion_proof"],
        "governance_surfaces": ["founder_approval"],
        "topology_layers": ["cross_platform_graph"],
    },
    "world_model_integration": {
        "registries": [
            "adapter_registry",
            "command_registry",
            "world_model_registry",
        ],
        "relays": ["local_wsl_worker"],
        "adapters": ["world_model_candidate_layer"],
        "execution_chains": [
            "ingestion_pipeline",
            "candidate_assembly",
            "governance_gate",
        ],
        "proofs": [
            "ingestion_proof",
            "world_model_candidate_proof",
            "transformation_ledger",
        ],
        "governance_surfaces": [
            "founder_approval",
            "canonical_gate",
            "transformation_ledger",
        ],
        "topology_layers": ["world_model_candidate_layer"],
    },
}

# ---------------------------------------------------------------------------
# Rollback strategy mapping
# ---------------------------------------------------------------------------

ROLLBACK_STRATEGIES: dict[str, dict[str, Any]] = {
    "local_adapter_execution": {
        "strategy": "revert_adapter_registry_and_remove_proofs",
        "replay_contract": [
            "restore_adapter_registry_snapshot",
            "remove_generated_proofs",
            "verify_registry_hash",
        ],
        "dependency_validation": [
            "no_downstream_adapters_depend_on_local",
            "no_active_ingestion_pipelines",
        ],
        "blast_radius": 0.2,
        "maturity_impact": "L4_ADAPTER_MATURITY",
        "deterministic": True,
    },
    "cu_adapter_execution": {
        "strategy": "revert_adapter_registry_and_clear_cu_proofs",
        "replay_contract": [
            "restore_adapter_registry_snapshot",
            "clear_cu_specific_proofs",
            "verify_chrome_state_neutral",
        ],
        "dependency_validation": [
            "no_downstream_ingestion_from_cu_adapters",
            "no_world_model_candidates_from_cu",
        ],
        "blast_radius": 0.4,
        "maturity_impact": "L4_ADAPTER_MATURITY",
        "deterministic": True,
    },
    "multi_platform_ingestion": {
        "strategy": "halt_ingestion_and_quarantine_candidates",
        "replay_contract": [
            "stop_all_ingestion_pipelines",
            "quarantine_unverified_candidates",
            "restore_platform_adapter_state",
        ],
        "dependency_validation": [
            "no_candidates_promoted_to_canonical",
            "no_world_model_mutations",
        ],
        "blast_radius": 0.6,
        "maturity_impact": "L3_ENVIRONMENT_INTELLIGENCE",
        "deterministic": False,
    },
    "relationship_graph_expansion": {
        "strategy": "discard_expanded_graph_and_restore_base",
        "replay_contract": [
            "remove_cross_platform_edges",
            "restore_base_topology",
            "verify_topology_hash",
        ],
        "dependency_validation": [
            "no_ingestion_lanes_depend_on_expanded_graph",
        ],
        "blast_radius": 0.2,
        "maturity_impact": "L3_ENVIRONMENT_INTELLIGENCE",
        "deterministic": True,
    },
    "world_model_integration": {
        "strategy": "quarantine_candidates_and_freeze_world_model",
        "replay_contract": [
            "freeze_world_model_writes",
            "quarantine_all_new_candidates",
            "restore_pre_integration_snapshot",
            "verify_canonical_integrity",
        ],
        "dependency_validation": [
            "no_canonical_promotions_from_integration",
            "no_downstream_agents_consuming_new_entries",
        ],
        "blast_radius": 0.8,
        "maturity_impact": "L4_ADAPTER_MATURITY",
        "deterministic": False,
    },
}

# ---------------------------------------------------------------------------
# DAG construction
# ---------------------------------------------------------------------------


def _detect_cycles(
    adjacency: dict[str, list[str]],
) -> bool:
    """Detect cycles in a directed graph via DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in adjacency}

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for neighbor in adjacency.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    for node in adjacency:
        if color[node] == WHITE:
            if dfs(node):
                return True
    return False


def _topological_sort(
    adjacency: dict[str, list[str]],
) -> list[str]:
    """Kahn's algorithm topological sort. Returns empty on cycle."""
    in_degree: dict[str, int] = {n: 0 for n in adjacency}
    for deps in adjacency.values():
        for d in deps:
            if d in in_degree:
                in_degree[d] = in_degree.get(d, 0) + 1

    queue = sorted([n for n, deg in in_degree.items() if deg == 0])
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in adjacency.get(node, []):
            if neighbor in in_degree:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        queue.sort()

    if len(result) != len(adjacency):
        return []
    return result


def _assign_waves(
    adjacency: dict[str, list[str]],
    order: list[str],
) -> dict[str, int]:
    """Assign execution waves based on dependency depth."""
    waves: dict[str, int] = {}
    for node in order:
        dep_waves = [waves.get(d, 0) for d in adjacency.get(node, []) if d in waves]
        waves[node] = (max(dep_waves) + 1) if dep_waves else 0
    return waves


def build_execution_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build the execution DAG from upgrade proposals."""
    adjacency: dict[str, list[str]] = {}
    name_set = {p.name for p in proposals}

    for p in proposals:
        deps = [r for r in p.required_infrastructure if r in name_set and r != p.name]
        adjacency[p.name] = deps

    has_cycles = _detect_cycles(adjacency)
    order = _topological_sort(adjacency) if not has_cycles else []
    waves = _assign_waves(adjacency, order) if order else {}

    reverse: dict[str, list[str]] = {n: [] for n in adjacency}
    for n, deps in adjacency.items():
        for d in deps:
            if d in reverse:
                reverse[d].append(n)

    nodes: list[DAGNode] = []
    edges: list[tuple[str, str]] = []

    for p in proposals:
        deps = adjacency.get(p.name, [])
        node = DAGNode(
            name=p.name,
            dag_type="execution",
            dependencies=deps,
            dependents=reverse.get(p.name, []),
            wave=waves.get(p.name, 0),
        )
        nodes.append(node)
        for d in deps:
            edges.append((d, p.name))

    wave_count = (max(waves.values()) + 1) if waves else 0

    return OrchestrationDAG(
        dag_type="execution",
        nodes=nodes,
        edges=edges,
        has_cycles=has_cycles,
        wave_count=wave_count,
    )


def build_dependency_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build dependency DAG from required_proofs relationships."""
    adjacency: dict[str, list[str]] = {}
    proof_to_upgrade: dict[str, str] = {}

    for p in proposals:
        adjacency[p.name] = []
        for proof in p.required_proofs:
            proof_to_upgrade[proof] = p.name

    for p in proposals:
        for proof in p.required_proofs:
            for other in proposals:
                if other.name != p.name and proof in [rp for rp in other.required_proofs]:
                    if other.name not in adjacency[p.name]:
                        adjacency[p.name].append(other.name)

    has_cycles = _detect_cycles(adjacency)
    order = _topological_sort(adjacency) if not has_cycles else []
    waves = _assign_waves(adjacency, order) if order else {}

    nodes = [
        DAGNode(
            name=p.name,
            dag_type="dependency",
            dependencies=adjacency.get(p.name, []),
            wave=waves.get(p.name, 0),
        )
        for p in proposals
    ]
    edges = [(dep, name) for name, deps in adjacency.items() for dep in deps]

    return OrchestrationDAG(
        dag_type="dependency",
        nodes=nodes,
        edges=edges,
        has_cycles=has_cycles,
        wave_count=(max(waves.values()) + 1) if waves else 0,
    )


def build_governance_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build governance DAG from governance constraints."""
    nodes: list[DAGNode] = []
    for p in proposals:
        gov_approved = len(p.governance_constraints) <= 1
        nodes.append(
            DAGNode(
                name=p.name,
                dag_type="governance",
                governance_approved=gov_approved,
            )
        )
    return OrchestrationDAG(
        dag_type="governance",
        nodes=nodes,
    )


def build_rollback_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build rollback DAG from rollback strategies."""
    nodes: list[DAGNode] = []
    for p in proposals:
        strategy = ROLLBACK_STRATEGIES.get(p.name, {})
        rollback_safe = strategy.get("deterministic", False)
        nodes.append(
            DAGNode(
                name=p.name,
                dag_type="rollback",
                rollback_safe=rollback_safe,
                blast_radius=strategy.get("blast_radius", 1.0),
            )
        )
    return OrchestrationDAG(dag_type="rollback", nodes=nodes)


def build_replay_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build replay DAG from replay requirements."""
    nodes: list[DAGNode] = []
    for p in proposals:
        has_replay = len(p.replay_requirements) > 0
        nodes.append(
            DAGNode(
                name=p.name,
                dag_type="replay",
                replay_safe=has_replay,
            )
        )
    return OrchestrationDAG(dag_type="replay", nodes=nodes)


def build_maturity_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build maturity DAG from required maturity levels."""
    maturity_order = list(CAPABILITY_MATURITY_LEVELS)
    adjacency: dict[str, list[str]] = {p.name: [] for p in proposals}

    for p in proposals:
        p_idx = (
            maturity_order.index(p.required_maturity)
            if p.required_maturity in maturity_order
            else 0
        )
        for other in proposals:
            if other.name == p.name:
                continue
            o_idx = (
                maturity_order.index(other.required_maturity)
                if other.required_maturity in maturity_order
                else 0
            )
            if o_idx < p_idx:
                adjacency[p.name].append(other.name)

    has_cycles = _detect_cycles(adjacency)
    order = _topological_sort(adjacency) if not has_cycles else []
    waves = _assign_waves(adjacency, order) if order else {}

    nodes = [
        DAGNode(
            name=p.name,
            dag_type="maturity",
            dependencies=adjacency.get(p.name, []),
            wave=waves.get(p.name, 0),
        )
        for p in proposals
    ]

    return OrchestrationDAG(
        dag_type="maturity",
        nodes=nodes,
        has_cycles=has_cycles,
        wave_count=(max(waves.values()) + 1) if waves else 0,
    )


def build_infrastructure_mutation_dag(
    proposals: list[UpgradeProposal],
) -> OrchestrationDAG:
    """Build infrastructure mutation DAG."""
    nodes: list[DAGNode] = []
    for p in proposals:
        blast = UPGRADE_BLAST_MAP.get(p.name, {})
        total = sum(len(v) for v in blast.values())
        nodes.append(
            DAGNode(
                name=p.name,
                dag_type="infrastructure_mutation",
                blast_radius=min(1.0, total / 20.0),
            )
        )
    return OrchestrationDAG(dag_type="infrastructure_mutation", nodes=nodes)


def build_all_dags(
    proposals: list[UpgradeProposal],
) -> list[OrchestrationDAG]:
    """Build all 7 DAG types."""
    return [
        build_execution_dag(proposals),
        build_dependency_dag(proposals),
        build_governance_dag(proposals),
        build_rollback_dag(proposals),
        build_replay_dag(proposals),
        build_maturity_dag(proposals),
        build_infrastructure_mutation_dag(proposals),
    ]


# ---------------------------------------------------------------------------
# Blast radius analysis
# ---------------------------------------------------------------------------


def compute_blast_radius(upgrade_name: str) -> BlastRadius:
    """Compute blast radius for a single upgrade."""
    blast_map = UPGRADE_BLAST_MAP.get(upgrade_name, {})
    return BlastRadius(
        upgrade_name=upgrade_name,
        affected_registries=blast_map.get("registries", []),
        affected_relays=blast_map.get("relays", []),
        affected_adapters=blast_map.get("adapters", []),
        affected_execution_chains=blast_map.get("execution_chains", []),
        affected_proofs=blast_map.get("proofs", []),
        affected_governance_surfaces=blast_map.get("governance_surfaces", []),
        affected_topology_layers=blast_map.get("topology_layers", []),
    )


def compute_all_blast_radii(
    proposals: list[UpgradeProposal],
) -> list[BlastRadius]:
    """Compute blast radius for all proposals."""
    return [compute_blast_radius(p.name) for p in proposals]


# ---------------------------------------------------------------------------
# Rollback planning
# ---------------------------------------------------------------------------


def build_rollback_plan(upgrade_name: str) -> RollbackPlan:
    """Build rollback plan for a single upgrade."""
    strategy = ROLLBACK_STRATEGIES.get(upgrade_name, {})
    return RollbackPlan(
        upgrade_name=upgrade_name,
        rollback_strategy=strategy.get("strategy", "no_strategy_defined"),
        rollback_replay_contract=strategy.get("replay_contract", []),
        rollback_dependency_validation=strategy.get("dependency_validation", []),
        rollback_blast_radius=strategy.get("blast_radius", 1.0),
        rollback_maturity_impact=strategy.get("maturity_impact", "L0_SIMULATED"),
        rollback_safe=strategy.get("deterministic", False),
        rollback_deterministic=strategy.get("deterministic", False),
    )


def build_all_rollback_plans(
    proposals: list[UpgradeProposal],
) -> list[RollbackPlan]:
    """Build rollback plans for all proposals."""
    return [build_rollback_plan(p.name) for p in proposals]


# ---------------------------------------------------------------------------
# Rollout simulation
# ---------------------------------------------------------------------------


def simulate_rollout(
    upgrade_name: str,
    outcome_type: str,
    rollback_plan: RollbackPlan,
    blast: BlastRadius,
) -> SimulationOutcome:
    """Simulate a single rollout scenario."""
    if outcome_type == "successful_rollout":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=True,
            replay_intact=True,
            rollback_viable=rollback_plan.rollback_safe,
            governance_satisfied=True,
            blast_radius_acceptable=blast.risk_score < 0.7,
        )
    elif outcome_type == "partial_rollout":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=False,
            replay_intact=True,
            rollback_viable=rollback_plan.rollback_safe,
            governance_satisfied=True,
            blast_radius_acceptable=blast.risk_score < 0.7,
            failure_reason="partial_completion",
            recovery_path="rollback_to_checkpoint",
        )
    elif outcome_type == "stale_rollout":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=False,
            replay_intact=False,
            rollback_viable=rollback_plan.rollback_safe,
            governance_satisfied=False,
            blast_radius_acceptable=True,
            failure_reason="stale_infrastructure_state",
            recovery_path="refresh_and_retry",
        )
    elif outcome_type == "replay_failure":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=False,
            replay_intact=False,
            rollback_viable=rollback_plan.rollback_deterministic,
            governance_satisfied=True,
            blast_radius_acceptable=blast.risk_score < 0.5,
            failure_reason="replay_contract_violation",
            recovery_path="rollback_and_regenerate_contract",
        )
    elif outcome_type == "relay_disconnect":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=False,
            replay_intact=True,
            rollback_viable=True,
            governance_satisfied=True,
            blast_radius_acceptable=True,
            failure_reason="relay_transport_lost",
            recovery_path="wait_for_relay_reconnection",
        )
    elif outcome_type == "governance_rejection":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=False,
            replay_intact=True,
            rollback_viable=True,
            governance_satisfied=False,
            blast_radius_acceptable=True,
            failure_reason="governance_policy_violation",
            recovery_path="obtain_founder_approval",
        )
    elif outcome_type == "rollback_recovery":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=rollback_plan.rollback_deterministic,
            replay_intact=rollback_plan.rollback_deterministic,
            rollback_viable=True,
            governance_satisfied=True,
            blast_radius_acceptable=rollback_plan.rollback_blast_radius < 0.5,
            failure_reason=""
            if rollback_plan.rollback_deterministic
            else "non_deterministic_rollback",
            recovery_path="manual_intervention" if not rollback_plan.rollback_deterministic else "",
        )
    elif outcome_type == "partial_infrastructure_mutation":
        return SimulationOutcome(
            outcome_type=outcome_type,
            upgrade_name=upgrade_name,
            succeeded=False,
            replay_intact=False,
            rollback_viable=rollback_plan.rollback_safe and blast.risk_score < 0.5,
            governance_satisfied=False,
            blast_radius_acceptable=False,
            failure_reason="partial_mutation_left_inconsistent_state",
            recovery_path="manual_rollback_required",
        )
    return SimulationOutcome(
        outcome_type="unknown",
        upgrade_name=upgrade_name,
        failure_reason="unknown_outcome_type",
    )


def simulate_all_rollouts(
    proposals: list[UpgradeProposal],
    rollback_plans: list[RollbackPlan],
    blast_radii: list[BlastRadius],
) -> list[SimulationOutcome]:
    """Simulate all outcome types for all proposals."""
    rb_map = {r.upgrade_name: r for r in rollback_plans}
    br_map = {b.upgrade_name: b for b in blast_radii}

    outcomes: list[SimulationOutcome] = []
    for p in proposals:
        rb = rb_map.get(p.name, RollbackPlan(upgrade_name=p.name))
        br = br_map.get(p.name, BlastRadius(upgrade_name=p.name))
        for outcome_type in sorted(SIMULATION_OUTCOMES):
            outcomes.append(simulate_rollout(p.name, outcome_type, rb, br))
    return outcomes


# ---------------------------------------------------------------------------
# Replayability enforcement
# ---------------------------------------------------------------------------


def validate_replay_safety(
    proposals: list[UpgradeProposal],
    rollback_plans: list[RollbackPlan],
) -> tuple[list[str], list[str]]:
    """Validate replay safety. Returns (safe, unsafe) proposal names."""
    safe: list[str] = []
    unsafe: list[str] = []
    rb_map = {r.upgrade_name: r for r in rollback_plans}

    for p in proposals:
        rb = rb_map.get(p.name)
        has_replay = len(p.replay_requirements) > 0
        has_rollback = rb is not None and rb.rollback_safe
        has_governance = len(p.governance_constraints) > 0

        if has_replay and has_rollback and has_governance:
            safe.append(p.name)
        else:
            unsafe.append(p.name)

    return safe, unsafe


# ---------------------------------------------------------------------------
# Unsafe chain detection
# ---------------------------------------------------------------------------


def detect_unsafe_chains(
    proposals: list[UpgradeProposal],
    rollback_plans: list[RollbackPlan],
    blast_radii: list[BlastRadius],
) -> list[str]:
    """Detect unsafe recursive upgrade chains."""
    unsafe: list[str] = []
    rb_map = {r.upgrade_name: r for r in rollback_plans}
    br_map = {b.upgrade_name: b for b in blast_radii}

    for p in proposals:
        rb = rb_map.get(p.name)
        br = br_map.get(p.name)

        reasons: list[str] = []
        if rb and not rb.rollback_deterministic:
            reasons.append("non_deterministic_rollback")
        if br and br.risk_score >= 0.7:
            reasons.append("high_blast_radius")
        if not p.governance_constraints:
            reasons.append("no_governance_constraints")
        if not p.replay_requirements:
            reasons.append("no_replay_requirements")

        if reasons:
            unsafe.append(f"{p.name}: {', '.join(reasons)}")

    return unsafe


# ---------------------------------------------------------------------------
# Governance bottleneck detection
# ---------------------------------------------------------------------------


def detect_governance_bottlenecks(
    proposals: list[UpgradeProposal],
) -> list[str]:
    """Detect governance bottlenecks across proposals."""
    bottlenecks: list[str] = []

    multi_gov = [p for p in proposals if len(p.governance_constraints) > 1]
    if multi_gov:
        for p in multi_gov:
            bottlenecks.append(
                f"{p.name}: requires {len(p.governance_constraints)} "
                f"governance approvals ({', '.join(p.governance_constraints)})"
            )

    no_gov = [p for p in proposals if not p.governance_constraints]
    if no_gov:
        for p in no_gov:
            bottlenecks.append(f"{p.name}: no governance constraints defined")

    return bottlenecks


# ---------------------------------------------------------------------------
# Recursive sequencing
# ---------------------------------------------------------------------------


def sequence_upgrades(
    proposals: list[UpgradeProposal],
    blast_radii: list[BlastRadius],
    rollback_plans: list[RollbackPlan],
) -> list[str]:
    """Sequence upgrades by safety-first priority.

    Priority order:
    1. safest (replay + rollback safe)
    2. most replayable
    3. highest leverage
    4. lowest governance risk
    5. highest infrastructure reuse
    6. lowest blast radius
    """
    rb_map = {r.upgrade_name: r for r in rollback_plans}
    br_map = {b.upgrade_name: b for b in blast_radii}

    def sort_key(p: UpgradeProposal) -> tuple:
        rb = rb_map.get(p.name)
        br = br_map.get(p.name)

        safety = 1.0 if (rb and rb.rollback_safe) else 0.0
        if len(p.replay_requirements) > 0:
            safety += 0.5

        replay = len(p.replay_requirements) / 5.0
        leverage = p.leverage_score.composite_score if p.leverage_score else 0.0
        gov_risk = p.leverage_score.governance_risk if p.leverage_score else 1.0
        infra_reuse = p.leverage_score.infrastructure_reuse if p.leverage_score else 0.0
        blast = br.risk_score if br else 1.0

        return (
            -safety,
            -replay,
            -leverage,
            gov_risk,
            -infra_reuse,
            blast,
        )

    sorted_proposals = sorted(proposals, key=sort_key)
    return [p.name for p in sorted_proposals]


# ---------------------------------------------------------------------------
# Orchestration conflict detection
# ---------------------------------------------------------------------------


def detect_conflicts(
    proposals: list[UpgradeProposal],
    blast_radii: list[BlastRadius],
) -> list[str]:
    """Detect orchestration conflicts between proposals."""
    conflicts: list[str] = []
    br_map = {b.upgrade_name: b for b in blast_radii}

    for i, p1 in enumerate(proposals):
        for p2 in proposals[i + 1 :]:
            br1 = br_map.get(p1.name)
            br2 = br_map.get(p2.name)
            if not br1 or not br2:
                continue

            shared_registries = set(br1.affected_registries) & set(br2.affected_registries)
            shared_relays = set(br1.affected_relays) & set(br2.affected_relays)

            if shared_registries or shared_relays:
                conflicts.append(
                    f"{p1.name} <-> {p2.name}: shared "
                    f"registries={list(shared_registries)} "
                    f"relays={list(shared_relays)}"
                )

    return conflicts


# ---------------------------------------------------------------------------
# Maturity evaluation
# ---------------------------------------------------------------------------


def compute_orchestration_maturity(
    evidence: OrchestrationEvidence,
) -> str:
    """Compute raw orchestration maturity level."""
    if evidence.is_dry_run:
        return "L0_SIMULATED_ORCHESTRATION"

    for level in reversed(ORCHESTRATION_MATURITY_LEVELS):
        reqs = ORCHESTRATION_MATURITY_REQUIREMENTS[level]
        if all(_check_orch_evidence(evidence, r) for r in reqs):
            return level

    return "L0_SIMULATED_ORCHESTRATION"


def _check_orch_evidence(evidence: OrchestrationEvidence, requirement: str) -> bool:
    field_map: dict[str, bool] = {
        "dag_generated": evidence.dag_generated,
        "replay_validated": evidence.replay_validated,
        "rollback_validated": evidence.rollback_validated,
        "governance_validated": evidence.governance_validated,
        "sequencing_validated": evidence.sequencing_validated,
        "blast_radius_analyzed": evidence.blast_radius_analyzed,
        "simulation_completed": evidence.simulation_completed,
        "founder_confirmed": evidence.founder_confirmed,
    }
    return field_map.get(requirement, False)


def orchestration_maturity_ceiling(
    evidence: OrchestrationEvidence,
) -> str:
    """Compute hard ceiling for orchestration maturity."""
    if evidence.is_dry_run:
        return "L0_SIMULATED_ORCHESTRATION"
    if not evidence.dag_generated:
        return "L0_SIMULATED_ORCHESTRATION"
    if not evidence.replay_validated:
        return "L0_SIMULATED_ORCHESTRATION"
    if not evidence.rollback_validated:
        return "L1_REPLAY_SAFE_ORCHESTRATION"
    if not evidence.governance_validated:
        return "L2_ROLLBACK_SAFE_ORCHESTRATION"
    if not evidence.sequencing_validated:
        return "L3_GOVERNED_ORCHESTRATION"
    if not evidence.blast_radius_analyzed:
        return "L3_GOVERNED_ORCHESTRATION"
    if not evidence.simulation_completed:
        return "L4_RECURSIVE_ORCHESTRATION"
    if not evidence.founder_confirmed:
        return "L4_RECURSIVE_ORCHESTRATION"
    return "L5_GOVERNED_RECURSIVE_ORCHESTRATION"


def _orch_level_index(level: str) -> int:
    try:
        return ORCHESTRATION_MATURITY_LEVELS.index(level)
    except ValueError:
        return 0


def classify_orchestration_maturity(
    evidence: OrchestrationEvidence,
) -> tuple[str, str, bool, str]:
    """Classify orchestration maturity: (level, ceiling, blocked, reason)."""
    raw = compute_orchestration_maturity(evidence)
    ceiling = orchestration_maturity_ceiling(evidence)

    raw_idx = _orch_level_index(raw)
    ceil_idx = _orch_level_index(ceiling)

    if ceil_idx < raw_idx:
        return ceiling, ceiling, True, f"ceiling {ceiling} blocks {raw}"

    return raw, ceiling, False, ""


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_orchestration_proof(
    capability_proof: CapabilityPlanningProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
) -> OrchestrationProof:
    """Full governed recursive orchestration pipeline."""
    if capability_proof and capability_proof.upgrade_proposals:
        proposals = capability_proof.upgrade_proposals
    else:
        stub_evidence = CapabilityPlanningEvidence()
        stub_graph = build_capability_graph(stub_evidence)
        proposals = generate_upgrade_proposals(stub_evidence, stub_graph)

    dags = build_all_dags(proposals)
    blast_radii = compute_all_blast_radii(proposals)
    rollback_plans = build_all_rollback_plans(proposals)
    simulations = simulate_all_rollouts(proposals, rollback_plans, blast_radii)
    replay_safe, replay_unsafe = validate_replay_safety(proposals, rollback_plans)
    unsafe_chains = detect_unsafe_chains(proposals, rollback_plans, blast_radii)
    gov_bottlenecks = detect_governance_bottlenecks(proposals)
    sequenced = sequence_upgrades(proposals, blast_radii, rollback_plans)
    conflicts = detect_conflicts(proposals, blast_radii)

    exec_dag = dags[0] if dags else None
    dag_ok = exec_dag is not None and not exec_dag.has_cycles

    rb_safe_count = sum(1 for r in rollback_plans if r.rollback_safe)
    rb_unsafe_count = len(rollback_plans) - rb_safe_count

    sim_success = sum(1 for s in simulations if s.succeeded)
    max_blast = max((b.risk_score for b in blast_radii), default=0.0)

    evidence = OrchestrationEvidence(
        dag_generated=dag_ok,
        dag_count=len(dags),
        replay_validated=len(replay_safe) > 0,
        replay_safe_count=len(replay_safe),
        replay_unsafe_count=len(replay_unsafe),
        rollback_validated=rb_safe_count > 0,
        rollback_safe_count=rb_safe_count,
        rollback_unsafe_count=rb_unsafe_count,
        governance_validated=len(gov_bottlenecks) == 0
        or all("no governance" not in b for b in gov_bottlenecks),
        governance_bottleneck_count=len(gov_bottlenecks),
        sequencing_validated=len(sequenced) > 0,
        wave_count=exec_dag.wave_count if exec_dag else 0,
        blast_radius_analyzed=len(blast_radii) > 0,
        max_blast_radius=max_blast,
        simulation_completed=len(simulations) > 0,
        simulation_count=len(simulations),
        simulation_success_count=sim_success,
        unsafe_chains_detected=len(unsafe_chains),
        conflict_count=len(conflicts),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_orchestration_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else ("await_founder_confirmation" if not founder_confirmed else "execute_safest_sequence")
    )

    return OrchestrationProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        dags=dags,
        blast_radii=blast_radii,
        rollback_plans=rollback_plans,
        simulations=simulations,
        sequenced_upgrades=sequenced,
        unsafe_chains=unsafe_chains,
        governance_bottlenecks=gov_bottlenecks,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_orchestration_proof(
    proof: OrchestrationProof,
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist orchestration proof to disk."""
    out_dir = base_dir / ORCHESTRATION_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{proof.proof_id}.json"
    path = out_dir / filename
    with open(path, "w") as f:
        json.dump(proof.to_dict(), f, indent=2)
    return path
