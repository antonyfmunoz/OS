"""Persistent Substrate Continuity Engine v1.

Maintains long-lived operational continuity, execution lineage,
orchestration memory, drift awareness, capability evolution history,
and recursive temporal state across sessions, reboots, deployments,
and orchestration cycles.

The engine may: observe, persist, replay, classify, compare, reason
about substrate evolution, detect drift, track lineage, score trends.

The engine CANNOT: rewrite lineage, mutate historical proofs, delete
orchestration history, rewrite governance outcomes, rewrite replay
outcomes, overwrite maturity evidence, auto-promote canonical memory,
or mutate canonical structures autonomously.

UMH substrate subsystem. Phase 96.8AX.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.workstation.governed_recursive_orchestration_engine_v1 import (
    DAG_TYPES,
    ORCHESTRATION_MATURITY_LEVELS,
    ORCHESTRATION_REPORT_DIR,
    SIMULATION_OUTCOMES,
    OrchestrationEvidence,
    OrchestrationProof,
    build_full_orchestration_proof,
)
from core.workstation.recursive_capability_planning_engine_v1 import (
    CAPABILITY_MATURITY_LEVELS,
    SUBSTRATE_CAPABILITIES,
    CapabilityPlanningProof,
    build_full_capability_proof,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


CONTINUITY_REPORT_DIR = Path("data/runtime/workstation_relay/continuity_reports")

# ---------------------------------------------------------------------------
# Continuity maturity levels
# ---------------------------------------------------------------------------

CONTINUITY_MATURITY_LEVELS = (
    "L0_NO_CONTINUITY",
    "L1_EXECUTION_CONTINUITY",
    "L2_CAPABILITY_CONTINUITY",
    "L3_TOPOLOGY_CONTINUITY",
    "L4_EPISTEMIC_CONTINUITY",
    "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY",
)

CONTINUITY_MATURITY_REQUIREMENTS: dict[str, list[str]] = {
    "L0_NO_CONTINUITY": [],
    "L1_EXECUTION_CONTINUITY": [
        "execution_lineage_present",
        "orchestration_history_present",
    ],
    "L2_CAPABILITY_CONTINUITY": [
        "execution_lineage_present",
        "orchestration_history_present",
        "capability_evolution_present",
        "maturity_transitions_present",
    ],
    "L3_TOPOLOGY_CONTINUITY": [
        "execution_lineage_present",
        "orchestration_history_present",
        "capability_evolution_present",
        "maturity_transitions_present",
        "topology_evolution_present",
        "registry_evolution_present",
    ],
    "L4_EPISTEMIC_CONTINUITY": [
        "execution_lineage_present",
        "orchestration_history_present",
        "capability_evolution_present",
        "maturity_transitions_present",
        "topology_evolution_present",
        "registry_evolution_present",
        "drift_analysis_completed",
        "replay_continuity_validated",
    ],
    "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY": [
        "execution_lineage_present",
        "orchestration_history_present",
        "capability_evolution_present",
        "maturity_transitions_present",
        "topology_evolution_present",
        "registry_evolution_present",
        "drift_analysis_completed",
        "replay_continuity_validated",
        "rollback_continuity_validated",
        "governance_continuity_enforced",
        "continuity_proofs_persisted",
        "founder_confirmed",
    ],
}


# ---------------------------------------------------------------------------
# Data structures — Layer 1: Execution Continuity Memory
# ---------------------------------------------------------------------------


@dataclass
class ExecutionLineageEntry:
    """A single execution event in the lineage chain."""

    entry_id: str = ""
    command: str = ""
    action_type: str = ""
    trace_id: str = ""
    request_id: str = ""
    proof_id: str = ""
    maturity_at_execution: str = ""
    outcome: str = ""
    parent_entry_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.entry_id:
            self.entry_id = f"EXEC-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "command": self.command,
            "action_type": self.action_type,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "proof_id": self.proof_id,
            "maturity_at_execution": self.maturity_at_execution,
            "outcome": self.outcome,
            "parent_entry_id": self.parent_entry_id,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionContinuityMemory:
    """Layer 1 — command lineage, execution chains, orchestration
    DAG history, rollback history, replay history."""

    lineage: list[ExecutionLineageEntry] = field(default_factory=list)
    orchestration_dag_history: list[str] = field(default_factory=list)
    rollback_history: list[str] = field(default_factory=list)
    replay_history: list[str] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.lineage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage": [e.to_dict() for e in self.lineage],
            "lineage_depth": self.depth,
            "orchestration_dag_history": self.orchestration_dag_history,
            "rollback_history": self.rollback_history,
            "replay_history": self.replay_history,
        }


# ---------------------------------------------------------------------------
# Data structures — Layer 2: Capability Continuity Memory
# ---------------------------------------------------------------------------


@dataclass
class MaturityTransition:
    """A single maturity level transition."""

    transition_id: str = ""
    from_level: str = ""
    to_level: str = ""
    domain: str = ""
    evidence_hash: str = ""
    founder_confirmed: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.transition_id:
            self.transition_id = f"MTRANS-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "domain": self.domain,
            "evidence_hash": self.evidence_hash,
            "founder_confirmed": self.founder_confirmed,
            "timestamp": self.timestamp,
        }


@dataclass
class CapabilityContinuityMemory:
    """Layer 2 — capability evolution, maturity transitions,
    dependency evolution, orchestration evolution, relay evolution."""

    capability_evolution: list[str] = field(default_factory=list)
    maturity_transitions: list[MaturityTransition] = field(default_factory=list)
    dependency_evolution: list[str] = field(default_factory=list)
    orchestration_evolution: list[str] = field(default_factory=list)
    relay_evolution: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_evolution": self.capability_evolution,
            "maturity_transitions": [t.to_dict() for t in self.maturity_transitions],
            "dependency_evolution": self.dependency_evolution,
            "orchestration_evolution": self.orchestration_evolution,
            "relay_evolution": self.relay_evolution,
        }


# ---------------------------------------------------------------------------
# Data structures — Layer 3: Topology Continuity Memory
# ---------------------------------------------------------------------------


@dataclass
class TopologyContinuityMemory:
    """Layer 3 — graph evolution, node additions/removals, governance
    surface evolution, blast radius trends, registry evolution."""

    graph_evolution: list[str] = field(default_factory=list)
    node_additions: list[str] = field(default_factory=list)
    node_removals: list[str] = field(default_factory=list)
    governance_surface_evolution: list[str] = field(default_factory=list)
    blast_radius_trends: list[float] = field(default_factory=list)
    registry_evolution: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_evolution": self.graph_evolution,
            "node_additions": self.node_additions,
            "node_removals": self.node_removals,
            "governance_surface_evolution": self.governance_surface_evolution,
            "blast_radius_trends": [round(t, 3) for t in self.blast_radius_trends],
            "registry_evolution": self.registry_evolution,
        }


# ---------------------------------------------------------------------------
# Data structures — Layer 4: Epistemic Continuity Memory
# ---------------------------------------------------------------------------


@dataclass
class EpistemicContinuityMemory:
    """Layer 4 — observed vs inferred, replay-safe vs non-replay-safe,
    deterministic vs non-deterministic, founder-confirmed vs simulated,
    maturity-ceiling transitions."""

    observed_count: int = 0
    inferred_count: int = 0
    replay_safe_count: int = 0
    non_replay_safe_count: int = 0
    deterministic_count: int = 0
    non_deterministic_count: int = 0
    founder_confirmed_count: int = 0
    simulated_count: int = 0
    maturity_ceiling_transitions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_count": self.observed_count,
            "inferred_count": self.inferred_count,
            "replay_safe_count": self.replay_safe_count,
            "non_replay_safe_count": self.non_replay_safe_count,
            "deterministic_count": self.deterministic_count,
            "non_deterministic_count": self.non_deterministic_count,
            "founder_confirmed_count": self.founder_confirmed_count,
            "simulated_count": self.simulated_count,
            "maturity_ceiling_transitions": self.maturity_ceiling_transitions,
        }


# ---------------------------------------------------------------------------
# Temporal substrate snapshot
# ---------------------------------------------------------------------------


@dataclass
class SubstrateSnapshot:
    """Point-in-time snapshot of the entire substrate state."""

    snapshot_id: str = ""
    orchestration_maturity: str = ""
    capability_maturity: str = ""
    continuity_maturity: str = ""
    capability_count: int = 0
    proven_capabilities: int = 0
    dag_count: int = 0
    simulation_count: int = 0
    registry_hash: str = ""
    continuity_hash: str = ""
    replay_hash: str = ""
    drift_signatures: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            self.snapshot_id = f"SNAP-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "orchestration_maturity": self.orchestration_maturity,
            "capability_maturity": self.capability_maturity,
            "continuity_maturity": self.continuity_maturity,
            "capability_count": self.capability_count,
            "proven_capabilities": self.proven_capabilities,
            "dag_count": self.dag_count,
            "simulation_count": self.simulation_count,
            "registry_hash": self.registry_hash,
            "continuity_hash": self.continuity_hash,
            "replay_hash": self.replay_hash,
            "drift_signatures": self.drift_signatures,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------

DRIFT_TYPES = frozenset(
    {
        "registry_divergence",
        "topology_divergence",
        "orchestration_divergence",
        "maturity_drift",
        "replay_drift",
        "relay_drift",
        "governance_drift",
        "execution_lineage_corruption",
    }
)


@dataclass
class DriftSignal:
    """A detected drift signal."""

    signal_id: str = ""
    drift_type: str = ""
    severity: float = 0.0
    description: str = ""
    expected: str = ""
    observed: str = ""
    remediation: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = f"DRIFT-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "drift_type": self.drift_type,
            "severity": round(self.severity, 3),
            "description": self.description,
            "expected": self.expected,
            "observed": self.observed,
            "remediation": self.remediation,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Recursive continuity lineage
# ---------------------------------------------------------------------------


@dataclass
class ContinuityLineageEntry:
    """A single entry in the recursive continuity lineage chain."""

    lineage_id: str = ""
    parent_orchestration_id: str = ""
    parent_continuity_id: str = ""
    replay_lineage: list[str] = field(default_factory=list)
    rollback_lineage: list[str] = field(default_factory=list)
    evolution_chain: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.lineage_id:
            self.lineage_id = f"CLIN-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "parent_orchestration_id": self.parent_orchestration_id,
            "parent_continuity_id": self.parent_continuity_id,
            "replay_lineage": self.replay_lineage,
            "rollback_lineage": self.rollback_lineage,
            "evolution_chain": self.evolution_chain,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Substrate evolution scoring
# ---------------------------------------------------------------------------


@dataclass
class EvolutionScores:
    """Substrate evolution trend scores."""

    stability_trend: float = 0.0
    governance_integrity_trend: float = 0.0
    replayability_trend: float = 0.0
    rollbackability_trend: float = 0.0
    orchestration_entropy_trend: float = 0.0
    drift_acceleration_trend: float = 0.0
    capability_leverage_trend: float = 0.0

    def composite(self) -> float:
        positive = (
            self.stability_trend * 0.25
            + self.governance_integrity_trend * 0.15
            + self.replayability_trend * 0.15
            + self.rollbackability_trend * 0.15
            + self.capability_leverage_trend * 0.15
        )
        penalty = self.orchestration_entropy_trend * 0.1 + self.drift_acceleration_trend * 0.15
        return max(0.0, round(positive - penalty, 3))

    def to_dict(self) -> dict[str, Any]:
        return {
            "stability_trend": round(self.stability_trend, 3),
            "governance_integrity_trend": round(self.governance_integrity_trend, 3),
            "replayability_trend": round(self.replayability_trend, 3),
            "rollbackability_trend": round(self.rollbackability_trend, 3),
            "orchestration_entropy_trend": round(self.orchestration_entropy_trend, 3),
            "drift_acceleration_trend": round(self.drift_acceleration_trend, 3),
            "capability_leverage_trend": round(self.capability_leverage_trend, 3),
            "composite_score": self.composite(),
        }


# ---------------------------------------------------------------------------
# Continuity evidence
# ---------------------------------------------------------------------------


@dataclass
class ContinuityEvidence:
    """Evidence collected during continuity analysis."""

    execution_lineage_present: bool = False
    execution_lineage_depth: int = 0
    orchestration_history_present: bool = False
    orchestration_history_count: int = 0
    capability_evolution_present: bool = False
    capability_evolution_count: int = 0
    maturity_transitions_present: bool = False
    maturity_transition_count: int = 0
    topology_evolution_present: bool = False
    topology_evolution_count: int = 0
    registry_evolution_present: bool = False
    registry_evolution_count: int = 0
    drift_analysis_completed: bool = False
    drift_signal_count: int = 0
    drift_max_severity: float = 0.0
    replay_continuity_validated: bool = False
    replay_chain_count: int = 0
    rollback_continuity_validated: bool = False
    rollback_chain_count: int = 0
    governance_continuity_enforced: bool = False
    continuity_proofs_persisted: bool = False
    snapshot_count: int = 0
    evolution_composite_score: float = 0.0
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_lineage_present": self.execution_lineage_present,
            "execution_lineage_depth": self.execution_lineage_depth,
            "orchestration_history_present": self.orchestration_history_present,
            "orchestration_history_count": self.orchestration_history_count,
            "capability_evolution_present": self.capability_evolution_present,
            "capability_evolution_count": self.capability_evolution_count,
            "maturity_transitions_present": self.maturity_transitions_present,
            "maturity_transition_count": self.maturity_transition_count,
            "topology_evolution_present": self.topology_evolution_present,
            "topology_evolution_count": self.topology_evolution_count,
            "registry_evolution_present": self.registry_evolution_present,
            "registry_evolution_count": self.registry_evolution_count,
            "drift_analysis_completed": self.drift_analysis_completed,
            "drift_signal_count": self.drift_signal_count,
            "drift_max_severity": round(self.drift_max_severity, 3),
            "replay_continuity_validated": self.replay_continuity_validated,
            "replay_chain_count": self.replay_chain_count,
            "rollback_continuity_validated": self.rollback_continuity_validated,
            "rollback_chain_count": self.rollback_chain_count,
            "governance_continuity_enforced": self.governance_continuity_enforced,
            "continuity_proofs_persisted": self.continuity_proofs_persisted,
            "snapshot_count": self.snapshot_count,
            "evolution_composite_score": round(self.evolution_composite_score, 3),
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


# ---------------------------------------------------------------------------
# Continuity proof
# ---------------------------------------------------------------------------


@dataclass
class ContinuityProof:
    """Complete proof of persistent substrate continuity."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_CONTINUITY"
    maturity_ceiling: str = "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: ContinuityEvidence | None = None
    execution_memory: ExecutionContinuityMemory | None = None
    capability_memory: CapabilityContinuityMemory | None = None
    topology_memory: TopologyContinuityMemory | None = None
    epistemic_memory: EpistemicContinuityMemory | None = None
    snapshots: list[SubstrateSnapshot] = field(default_factory=list)
    drift_signals: list[DriftSignal] = field(default_factory=list)
    lineage_chain: list[ContinuityLineageEntry] = field(default_factory=list)
    evolution_scores: EvolutionScores | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"CONTPROOF-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "persistent_substrate_continuity",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "execution_memory": (
                self.execution_memory.to_dict() if self.execution_memory else None
            ),
            "capability_memory": (
                self.capability_memory.to_dict() if self.capability_memory else None
            ),
            "topology_memory": (self.topology_memory.to_dict() if self.topology_memory else None),
            "epistemic_memory": (
                self.epistemic_memory.to_dict() if self.epistemic_memory else None
            ),
            "snapshots": [s.to_dict() for s in self.snapshots],
            "snapshot_count": len(self.snapshots),
            "drift_signals": [d.to_dict() for d in self.drift_signals],
            "drift_signal_count": len(self.drift_signals),
            "lineage_chain": [l.to_dict() for l in self.lineage_chain],
            "lineage_depth": len(self.lineage_chain),
            "evolution_scores": (
                self.evolution_scores.to_dict() if self.evolution_scores else None
            ),
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Continuity governance ceilings (immutable constraints)
# ---------------------------------------------------------------------------

CONTINUITY_GOVERNANCE_VIOLATIONS = frozenset(
    {
        "lineage_rewrite",
        "historical_proof_mutation",
        "orchestration_history_deletion",
        "governance_outcome_rewrite",
        "replay_outcome_rewrite",
        "maturity_evidence_overwrite",
        "canonical_auto_promotion",
    }
)


# ---------------------------------------------------------------------------
# Continuity hard ceilings (rejection triggers)
# ---------------------------------------------------------------------------

CONTINUITY_REJECTION_TRIGGERS = frozenset(
    {
        "orphaned_orchestration_chain",
        "broken_replay_lineage",
        "broken_rollback_lineage",
        "maturity_jump_without_evidence",
        "topology_mutation_without_lineage",
        "governance_gap",
        "continuity_corruption",
    }
)


# ---------------------------------------------------------------------------
# Build execution continuity memory
# ---------------------------------------------------------------------------


def build_execution_continuity(
    orchestration_proof: OrchestrationProof | None = None,
    base_dir: Path = Path("/opt/OS"),
) -> ExecutionContinuityMemory:
    """Build Layer 1 — Execution Continuity Memory."""
    memory = ExecutionContinuityMemory()

    orch_dir = base_dir / ORCHESTRATION_REPORT_DIR
    if orch_dir.exists():
        orch_files = sorted(orch_dir.glob("ORCHPROOF-*.json"))
        for f in orch_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                entry = ExecutionLineageEntry(
                    command="!orchestration-report",
                    action_type="orchestration_report",
                    trace_id=data.get("trace_id", ""),
                    proof_id=data.get("proof_id", ""),
                    maturity_at_execution=data.get("maturity_level", ""),
                    outcome="completed",
                )
                memory.lineage.append(entry)
                memory.orchestration_dag_history.append(data.get("proof_id", f.stem))
            except (json.JSONDecodeError, OSError):
                continue

    cap_dir = base_dir / "data/runtime/workstation_relay/capability_reports"
    if cap_dir.exists():
        cap_files = sorted(cap_dir.glob("CAPPROOF-*.json"))
        for f in cap_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                entry = ExecutionLineageEntry(
                    command="!capability-report",
                    action_type="capability_report",
                    trace_id=data.get("trace_id", ""),
                    proof_id=data.get("proof_id", ""),
                    maturity_at_execution=data.get("maturity_level", ""),
                    outcome="completed",
                )
                memory.lineage.append(entry)
            except (json.JSONDecodeError, OSError):
                continue

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev:
            for rb in orchestration_proof.rollback_plans:
                if rb.rollback_safe:
                    memory.rollback_history.append(rb.upgrade_name)
            replay_safe_names = [
                u
                for u in orchestration_proof.sequenced_upgrades
                if u not in [c.split(":")[0] for c in orchestration_proof.unsafe_chains]
            ]
            memory.replay_history.extend(replay_safe_names)

    return memory


# ---------------------------------------------------------------------------
# Build capability continuity memory
# ---------------------------------------------------------------------------


def build_capability_continuity(
    orchestration_proof: OrchestrationProof | None = None,
    base_dir: Path = Path("/opt/OS"),
) -> CapabilityContinuityMemory:
    """Build Layer 2 — Capability Continuity Memory."""
    memory = CapabilityContinuityMemory()

    for cap_name in sorted(SUBSTRATE_CAPABILITIES):
        memory.capability_evolution.append(cap_name)

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev and ev.dag_generated:
            memory.orchestration_evolution.append(orchestration_proof.maturity_level)
        for dag in orchestration_proof.dags:
            if dag.dag_type == "maturity":
                for node in dag.nodes:
                    transition = MaturityTransition(
                        from_level="L0_SIMULATED_ORCHESTRATION",
                        to_level=orchestration_proof.maturity_level,
                        domain=node.name,
                    )
                    memory.maturity_transitions.append(transition)

        for u in orchestration_proof.sequenced_upgrades:
            memory.dependency_evolution.append(u)

    return memory


# ---------------------------------------------------------------------------
# Build topology continuity memory
# ---------------------------------------------------------------------------


def build_topology_continuity(
    orchestration_proof: OrchestrationProof | None = None,
    base_dir: Path = Path("/opt/OS"),
) -> TopologyContinuityMemory:
    """Build Layer 3 — Topology Continuity Memory."""
    memory = TopologyContinuityMemory()

    from core.registry.canonical_command_registry_v1 import (
        get_canonical_registry,
    )

    reg = get_canonical_registry()
    memory.registry_evolution.append(f"registry_hash={reg.registry_hash()} count={len(reg)}")

    if orchestration_proof:
        for dag in orchestration_proof.dags:
            memory.graph_evolution.append(
                f"{dag.dag_type}: nodes={len(dag.nodes)} "
                f"edges={len(dag.edges)} waves={dag.wave_count}"
            )

        for br in orchestration_proof.blast_radii:
            memory.blast_radius_trends.append(br.risk_score)
            for gs in br.affected_governance_surfaces:
                if gs not in memory.governance_surface_evolution:
                    memory.governance_surface_evolution.append(gs)

        for dag in orchestration_proof.dags:
            for node in dag.nodes:
                if node.name not in memory.node_additions:
                    memory.node_additions.append(node.name)

    return memory


# ---------------------------------------------------------------------------
# Build epistemic continuity memory
# ---------------------------------------------------------------------------


def build_epistemic_continuity(
    orchestration_proof: OrchestrationProof | None = None,
    founder_confirmed: bool = False,
) -> EpistemicContinuityMemory:
    """Build Layer 4 — Epistemic Continuity Memory."""
    memory = EpistemicContinuityMemory()

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev:
            if ev.founder_confirmed:
                memory.founder_confirmed_count += 1
                memory.observed_count += 1
            else:
                memory.simulated_count += 1
                memory.inferred_count += 1

            memory.replay_safe_count = ev.replay_safe_count
            memory.non_replay_safe_count = ev.replay_unsafe_count
            memory.deterministic_count = ev.rollback_safe_count
            memory.non_deterministic_count = ev.rollback_unsafe_count

            memory.maturity_ceiling_transitions.append(
                f"{orchestration_proof.maturity_level} "
                f"(ceiling: {orchestration_proof.maturity_ceiling})"
            )

    if founder_confirmed and memory.founder_confirmed_count == 0:
        memory.founder_confirmed_count = 1
        memory.observed_count += 1

    return memory


# ---------------------------------------------------------------------------
# Build temporal substrate snapshot
# ---------------------------------------------------------------------------


def build_substrate_snapshot(
    orchestration_proof: OrchestrationProof | None = None,
    capability_proof: CapabilityPlanningProof | None = None,
    continuity_maturity: str = "L0_NO_CONTINUITY",
    base_dir: Path = Path("/opt/OS"),
) -> SubstrateSnapshot:
    """Build a point-in-time substrate snapshot."""
    from core.registry.canonical_command_registry_v1 import (
        get_canonical_registry,
    )

    reg = get_canonical_registry()

    orch_maturity = ""
    dag_count = 0
    sim_count = 0
    if orchestration_proof:
        orch_maturity = orchestration_proof.maturity_level
        dag_count = len(orchestration_proof.dags)
        ev = orchestration_proof.evidence
        sim_count = ev.simulation_count if ev else 0

    cap_maturity = ""
    cap_count = len(SUBSTRATE_CAPABILITIES)
    proven = 0
    if capability_proof:
        cap_maturity = capability_proof.maturity_level
        graph = capability_proof.capability_graph
        if graph:
            proven = graph.proven_count

    snapshot_data = json.dumps(
        {
            "orch": orch_maturity,
            "cap": cap_maturity,
            "cont": continuity_maturity,
            "reg": reg.registry_hash(),
        },
        sort_keys=True,
    )
    continuity_hash = hashlib.sha256(snapshot_data.encode()).hexdigest()[:12]

    replay_data = json.dumps(
        {"dag_count": dag_count, "sim_count": sim_count},
        sort_keys=True,
    )
    replay_hash = hashlib.sha256(replay_data.encode()).hexdigest()[:12]

    return SubstrateSnapshot(
        orchestration_maturity=orch_maturity,
        capability_maturity=cap_maturity,
        continuity_maturity=continuity_maturity,
        capability_count=cap_count,
        proven_capabilities=proven,
        dag_count=dag_count,
        simulation_count=sim_count,
        registry_hash=reg.registry_hash(),
        continuity_hash=continuity_hash,
        replay_hash=replay_hash,
    )


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def detect_drift(
    orchestration_proof: OrchestrationProof | None = None,
    previous_snapshot: SubstrateSnapshot | None = None,
    base_dir: Path = Path("/opt/OS"),
) -> list[DriftSignal]:
    """Detect substrate drift signals."""
    signals: list[DriftSignal] = []

    from core.registry.canonical_command_registry_v1 import (
        get_canonical_registry,
    )

    reg = get_canonical_registry()

    config_path = base_dir / "config/control_plane_router_v1.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
            config_actions = set(config.get("allowed_action_types", []))
            registry_actions = reg.actions
            if config_actions != registry_actions:
                missing = registry_actions - config_actions
                extra = config_actions - registry_actions
                signals.append(
                    DriftSignal(
                        drift_type="registry_divergence",
                        severity=0.8,
                        description="Config/registry action mismatch",
                        expected=f"{len(registry_actions)} actions",
                        observed=(f"missing={list(missing)} extra={list(extra)}"),
                        remediation="Sync config with canonical registry",
                    )
                )
        except (json.JSONDecodeError, OSError):
            signals.append(
                DriftSignal(
                    drift_type="registry_divergence",
                    severity=0.9,
                    description="Config file unreadable",
                    remediation="Verify config/control_plane_router_v1.json",
                )
            )

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev and ev.unsafe_chains_detected > 0:
            signals.append(
                DriftSignal(
                    drift_type="orchestration_divergence",
                    severity=0.5,
                    description=(f"{ev.unsafe_chains_detected} unsafe chains detected"),
                    remediation="Review unsafe chains before execution",
                )
            )
        if ev and ev.governance_bottleneck_count > 2:
            signals.append(
                DriftSignal(
                    drift_type="governance_drift",
                    severity=0.4,
                    description=(f"{ev.governance_bottleneck_count} governance bottlenecks"),
                    remediation="Reduce governance surface complexity",
                )
            )

    if previous_snapshot:
        current_hash = reg.registry_hash()
        if previous_snapshot.registry_hash and previous_snapshot.registry_hash != current_hash:
            signals.append(
                DriftSignal(
                    drift_type="registry_divergence",
                    severity=0.6,
                    description="Registry hash changed since last snapshot",
                    expected=previous_snapshot.registry_hash,
                    observed=current_hash,
                    remediation="Verify registry change was intentional",
                )
            )

    orch_dir = base_dir / ORCHESTRATION_REPORT_DIR
    if orch_dir.exists():
        orch_files = sorted(orch_dir.glob("ORCHPROOF-*.json"))
        if len(orch_files) >= 2:
            try:
                d1 = json.loads(orch_files[-2].read_text(encoding="utf-8-sig"))
                d2 = json.loads(orch_files[-1].read_text(encoding="utf-8-sig"))
                m1 = d1.get("maturity_level", "")
                m2 = d2.get("maturity_level", "")
                if m1 and m2 and m1 != m2:
                    idx1 = (
                        ORCHESTRATION_MATURITY_LEVELS.index(m1)
                        if m1 in ORCHESTRATION_MATURITY_LEVELS
                        else 0
                    )
                    idx2 = (
                        ORCHESTRATION_MATURITY_LEVELS.index(m2)
                        if m2 in ORCHESTRATION_MATURITY_LEVELS
                        else 0
                    )
                    if abs(idx2 - idx1) > 1:
                        signals.append(
                            DriftSignal(
                                drift_type="maturity_drift",
                                severity=0.7,
                                description=(f"Maturity jump: {m1} -> {m2}"),
                                expected="single-level transition",
                                observed=f"{abs(idx2 - idx1)}-level jump",
                                remediation="Verify evidence chain",
                            )
                        )
            except (json.JSONDecodeError, OSError, IndexError):
                pass

    return signals


# ---------------------------------------------------------------------------
# Build recursive continuity lineage
# ---------------------------------------------------------------------------


def build_continuity_lineage(
    orchestration_proof: OrchestrationProof | None = None,
    previous_continuity_id: str = "",
    base_dir: Path = Path("/opt/OS"),
) -> list[ContinuityLineageEntry]:
    """Build the recursive continuity lineage chain."""
    chain: list[ContinuityLineageEntry] = []

    orch_dir = base_dir / ORCHESTRATION_REPORT_DIR
    if orch_dir.exists():
        orch_files = sorted(orch_dir.glob("ORCHPROOF-*.json"))
        prev_id = previous_continuity_id
        for f in orch_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                proof_id = data.get("proof_id", f.stem)

                replay_lin: list[str] = []
                rollback_lin: list[str] = []
                for sim in data.get("simulations", []):
                    if sim.get("replay_intact"):
                        replay_lin.append(sim.get("upgrade_name", ""))
                for rp in data.get("rollback_plans", []):
                    if rp.get("rollback_safe"):
                        rollback_lin.append(rp.get("upgrade_name", ""))

                entry = ContinuityLineageEntry(
                    parent_orchestration_id=proof_id,
                    parent_continuity_id=prev_id,
                    replay_lineage=list(set(replay_lin)),
                    rollback_lineage=list(set(rollback_lin)),
                    evolution_chain=data.get("sequenced_upgrades", []),
                )
                chain.append(entry)
                prev_id = entry.lineage_id
            except (json.JSONDecodeError, OSError):
                continue

    return chain


# ---------------------------------------------------------------------------
# Continuity replay engine
# ---------------------------------------------------------------------------


def replay_orchestration_history(
    base_dir: Path = Path("/opt/OS"),
) -> list[dict[str, Any]]:
    """Replay orchestration history from persisted proofs."""
    history: list[dict[str, Any]] = []
    orch_dir = base_dir / ORCHESTRATION_REPORT_DIR
    if not orch_dir.exists():
        return history

    for f in sorted(orch_dir.glob("ORCHPROOF-*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            history.append(
                {
                    "proof_id": data.get("proof_id", ""),
                    "maturity_level": data.get("maturity_level", ""),
                    "dag_count": data.get("dag_count", 0),
                    "execution_strategy": data.get("execution_strategy", ""),
                    "timestamp": data.get("timestamp", ""),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return history


def replay_maturity_evolution(
    base_dir: Path = Path("/opt/OS"),
) -> list[dict[str, str]]:
    """Replay maturity level evolution across all proof types."""
    evolution: list[dict[str, str]] = []

    cap_dir = base_dir / "data/runtime/workstation_relay/capability_reports"
    if cap_dir.exists():
        for f in sorted(cap_dir.glob("CAPPROOF-*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                evolution.append(
                    {
                        "domain": "capability",
                        "maturity": data.get("maturity_level", ""),
                        "timestamp": data.get("timestamp", ""),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue

    orch_dir = base_dir / ORCHESTRATION_REPORT_DIR
    if orch_dir.exists():
        for f in sorted(orch_dir.glob("ORCHPROOF-*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                evolution.append(
                    {
                        "domain": "orchestration",
                        "maturity": data.get("maturity_level", ""),
                        "timestamp": data.get("timestamp", ""),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue

    return evolution


def replay_drift_emergence(
    base_dir: Path = Path("/opt/OS"),
) -> list[dict[str, Any]]:
    """Replay drift emergence from continuity reports."""
    drifts: list[dict[str, Any]] = []
    cont_dir = base_dir / CONTINUITY_REPORT_DIR
    if not cont_dir.exists():
        return drifts

    for f in sorted(cont_dir.glob("CONTPROOF-*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
            for sig in data.get("drift_signals", []):
                drifts.append(sig)
        except (json.JSONDecodeError, OSError):
            continue
    return drifts


# ---------------------------------------------------------------------------
# Validate continuity integrity
# ---------------------------------------------------------------------------


def validate_replay_continuity(
    lineage_chain: list[ContinuityLineageEntry],
) -> bool:
    """Validate replay continuity — every entry must have replay lineage."""
    if not lineage_chain:
        return False
    for entry in lineage_chain:
        if not entry.replay_lineage and not entry.evolution_chain:
            return False
    return True


def validate_rollback_continuity(
    lineage_chain: list[ContinuityLineageEntry],
) -> bool:
    """Validate rollback continuity — every entry must have rollback
    lineage."""
    if not lineage_chain:
        return False
    for entry in lineage_chain:
        if not entry.rollback_lineage and not entry.evolution_chain:
            return False
    return True


def validate_governance_continuity(
    orchestration_proof: OrchestrationProof | None = None,
) -> bool:
    """Validate governance continuity — no governance gaps."""
    if not orchestration_proof:
        return False
    ev = orchestration_proof.evidence
    if not ev:
        return False
    return ev.governance_validated


def detect_continuity_corruption(
    lineage_chain: list[ContinuityLineageEntry],
    execution_memory: ExecutionContinuityMemory,
) -> list[str]:
    """Detect continuity corruption — orphans, broken chains, gaps."""
    corruptions: list[str] = []

    if not lineage_chain and execution_memory.depth > 0:
        corruptions.append("orphaned_orchestration_chain")

    seen_parents: set[str] = set()
    for entry in lineage_chain:
        if entry.parent_continuity_id and entry.parent_continuity_id not in seen_parents:
            if lineage_chain.index(entry) > 0:
                prev = lineage_chain[lineage_chain.index(entry) - 1]
                if prev.lineage_id != entry.parent_continuity_id:
                    corruptions.append("broken_replay_lineage")
                    break
        seen_parents.add(entry.lineage_id)

    if execution_memory.depth > 0 and not execution_memory.rollback_history:
        corruptions.append("broken_rollback_lineage")

    return corruptions


# ---------------------------------------------------------------------------
# Substrate evolution scoring
# ---------------------------------------------------------------------------


def compute_evolution_scores(
    orchestration_proof: OrchestrationProof | None = None,
    drift_signals: list[DriftSignal] | None = None,
    lineage_chain: list[ContinuityLineageEntry] | None = None,
) -> EvolutionScores:
    """Compute substrate evolution trend scores."""
    scores = EvolutionScores()

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev:
            total = ev.replay_safe_count + ev.replay_unsafe_count
            if total > 0:
                scores.replayability_trend = ev.replay_safe_count / total

            rb_total = ev.rollback_safe_count + ev.rollback_unsafe_count
            if rb_total > 0:
                scores.rollbackability_trend = ev.rollback_safe_count / rb_total

            if ev.governance_validated:
                scores.governance_integrity_trend = 1.0
            else:
                scores.governance_integrity_trend = 0.5

            if ev.simulation_count > 0:
                scores.stability_trend = ev.simulation_success_count / ev.simulation_count

            if ev.unsafe_chains_detected > 0:
                scores.orchestration_entropy_trend = min(1.0, ev.unsafe_chains_detected / 5.0)

    if drift_signals:
        max_sev = max(s.severity for s in drift_signals) if drift_signals else 0.0
        scores.drift_acceleration_trend = max_sev

    if lineage_chain:
        total_evolution = sum(len(e.evolution_chain) for e in lineage_chain)
        scores.capability_leverage_trend = min(1.0, total_evolution / 10.0)

    return scores


# ---------------------------------------------------------------------------
# Maturity evaluation
# ---------------------------------------------------------------------------


def compute_continuity_maturity(
    evidence: ContinuityEvidence,
) -> str:
    """Compute raw continuity maturity level."""
    if evidence.is_dry_run:
        return "L0_NO_CONTINUITY"

    for level in reversed(CONTINUITY_MATURITY_LEVELS):
        reqs = CONTINUITY_MATURITY_REQUIREMENTS[level]
        if all(_check_cont_evidence(evidence, r) for r in reqs):
            return level

    return "L0_NO_CONTINUITY"


def _check_cont_evidence(evidence: ContinuityEvidence, requirement: str) -> bool:
    field_map: dict[str, bool] = {
        "execution_lineage_present": evidence.execution_lineage_present,
        "orchestration_history_present": evidence.orchestration_history_present,
        "capability_evolution_present": evidence.capability_evolution_present,
        "maturity_transitions_present": evidence.maturity_transitions_present,
        "topology_evolution_present": evidence.topology_evolution_present,
        "registry_evolution_present": evidence.registry_evolution_present,
        "drift_analysis_completed": evidence.drift_analysis_completed,
        "replay_continuity_validated": evidence.replay_continuity_validated,
        "rollback_continuity_validated": evidence.rollback_continuity_validated,
        "governance_continuity_enforced": evidence.governance_continuity_enforced,
        "continuity_proofs_persisted": evidence.continuity_proofs_persisted,
        "founder_confirmed": evidence.founder_confirmed,
    }
    return field_map.get(requirement, False)


def continuity_maturity_ceiling(
    evidence: ContinuityEvidence,
) -> str:
    """Compute hard ceiling for continuity maturity."""
    if evidence.is_dry_run:
        return "L0_NO_CONTINUITY"
    if not evidence.execution_lineage_present:
        return "L0_NO_CONTINUITY"
    if not evidence.orchestration_history_present:
        return "L0_NO_CONTINUITY"
    if not evidence.capability_evolution_present:
        return "L1_EXECUTION_CONTINUITY"
    if not evidence.maturity_transitions_present:
        return "L1_EXECUTION_CONTINUITY"
    if not evidence.topology_evolution_present:
        return "L2_CAPABILITY_CONTINUITY"
    if not evidence.registry_evolution_present:
        return "L2_CAPABILITY_CONTINUITY"
    if not evidence.drift_analysis_completed:
        return "L3_TOPOLOGY_CONTINUITY"
    if not evidence.replay_continuity_validated:
        return "L3_TOPOLOGY_CONTINUITY"
    if not evidence.rollback_continuity_validated:
        return "L4_EPISTEMIC_CONTINUITY"
    if not evidence.governance_continuity_enforced:
        return "L4_EPISTEMIC_CONTINUITY"
    if not evidence.continuity_proofs_persisted:
        return "L4_EPISTEMIC_CONTINUITY"
    if not evidence.founder_confirmed:
        return "L4_EPISTEMIC_CONTINUITY"
    return "L5_PERSISTENT_GOVERNED_SUBSTRATE_CONTINUITY"


def _cont_level_index(level: str) -> int:
    try:
        return CONTINUITY_MATURITY_LEVELS.index(level)
    except ValueError:
        return 0


def classify_continuity_maturity(
    evidence: ContinuityEvidence,
) -> tuple[str, str, bool, str]:
    """Classify continuity maturity: (level, ceiling, blocked, reason)."""
    raw = compute_continuity_maturity(evidence)
    ceiling = continuity_maturity_ceiling(evidence)

    raw_idx = _cont_level_index(raw)
    ceil_idx = _cont_level_index(ceiling)

    if ceil_idx < raw_idx:
        return ceiling, ceiling, True, f"ceiling {ceiling} blocks {raw}"

    return raw, ceiling, False, ""


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_continuity_proof(
    orchestration_proof: OrchestrationProof | None = None,
    capability_proof: CapabilityPlanningProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
    base_dir: Path = Path("/opt/OS"),
) -> ContinuityProof:
    """Full persistent substrate continuity pipeline."""
    exec_memory = build_execution_continuity(orchestration_proof, base_dir)
    cap_memory = build_capability_continuity(orchestration_proof, base_dir)
    topo_memory = build_topology_continuity(orchestration_proof, base_dir)
    epist_memory = build_epistemic_continuity(orchestration_proof, founder_confirmed)

    lineage_chain = build_continuity_lineage(orchestration_proof, "", base_dir)
    drift_signals = detect_drift(orchestration_proof, None, base_dir)
    snapshot = build_substrate_snapshot(
        orchestration_proof, capability_proof, "L0_NO_CONTINUITY", base_dir
    )

    replay_valid = validate_replay_continuity(lineage_chain)
    rollback_valid = validate_rollback_continuity(lineage_chain)
    governance_valid = validate_governance_continuity(orchestration_proof)
    corruptions = detect_continuity_corruption(lineage_chain, exec_memory)

    evolution = compute_evolution_scores(orchestration_proof, drift_signals, lineage_chain)

    orch_history = replay_orchestration_history(base_dir)
    maturity_evo = replay_maturity_evolution(base_dir)

    max_drift = max(s.severity for s in drift_signals) if drift_signals else 0.0

    evidence = ContinuityEvidence(
        execution_lineage_present=exec_memory.depth > 0,
        execution_lineage_depth=exec_memory.depth,
        orchestration_history_present=len(orch_history) > 0,
        orchestration_history_count=len(orch_history),
        capability_evolution_present=len(cap_memory.capability_evolution) > 0,
        capability_evolution_count=len(cap_memory.capability_evolution),
        maturity_transitions_present=len(cap_memory.maturity_transitions) > 0,
        maturity_transition_count=len(cap_memory.maturity_transitions),
        topology_evolution_present=len(topo_memory.graph_evolution) > 0,
        topology_evolution_count=len(topo_memory.graph_evolution),
        registry_evolution_present=len(topo_memory.registry_evolution) > 0,
        registry_evolution_count=len(topo_memory.registry_evolution),
        drift_analysis_completed=True,
        drift_signal_count=len(drift_signals),
        drift_max_severity=max_drift,
        replay_continuity_validated=replay_valid,
        replay_chain_count=len(lineage_chain),
        rollback_continuity_validated=rollback_valid,
        rollback_chain_count=len([e for e in lineage_chain if e.rollback_lineage]),
        governance_continuity_enforced=governance_valid,
        continuity_proofs_persisted=True,
        snapshot_count=1,
        evolution_composite_score=evolution.composite(),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_continuity_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "await_founder_confirmation"
            if not founder_confirmed
            else "persistent_continuity_active"
        )
    )

    return ContinuityProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        execution_memory=exec_memory,
        capability_memory=cap_memory,
        topology_memory=topo_memory,
        epistemic_memory=epist_memory,
        snapshots=[snapshot],
        drift_signals=drift_signals,
        lineage_chain=lineage_chain,
        evolution_scores=evolution,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_continuity_proof(
    proof: ContinuityProof,
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist continuity proof to disk."""
    out_dir = base_dir / CONTINUITY_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{proof.proof_id}.json"
    path = out_dir / filename
    with open(path, "w") as f:
        json.dump(proof.to_dict(), f, indent=2)
    return path
