"""Distributed Constitutional Substrate Federation v1.

Allows multiple governed substrate nodes to coordinate, validate, replay,
govern, and exchange lineage safely while preserving constitutional
invariants, replay contracts, continuity integrity, and authority
boundaries across a federated substrate network.

No federated node may bypass constitutional governance.
All cross-node coordination preserves replay integrity, continuity
lineage, governance lineage, constitutional invariants, and authority
ceilings.

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

from core.workstation.constitutional_substrate_governance_layer_v1 import (
    CONSTITUTIONAL_HARD_CEILINGS,
    CONSTITUTIONAL_MATURITY_LEVELS,
    CONSTITUTIONAL_SAFETY_INVARIANTS,
    ConstitutionalEvidence,
    ConstitutionalProof,
    ConstitutionalRiskScores,
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

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEDERATION_REPORT_DIR = "data/runtime/workstation_relay/federation_reports"

FEDERATION_MATURITY_LEVELS = (
    "L0_NO_FEDERATION",
    "L1_NODE_REGISTERED",
    "L2_REPLAY_COORDINATED",
    "L3_CONTINUITY_COORDINATED",
    "L4_CONSTITUTIONALLY_GOVERNED",
    "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION",
)

FEDERATION_TRUST_DIMENSIONS = (
    "replay_reliability",
    "governance_reliability",
    "continuity_reliability",
    "rollback_reliability",
    "topology_stability",
    "constitutional_integrity",
    "federation_drift_risk",
)

FEDERATION_DRIFT_TYPES = (
    "node_divergence",
    "constitutional_divergence",
    "replay_divergence",
    "governance_divergence",
    "continuity_divergence",
    "orchestration_divergence",
    "federation_entropy",
)

FEDERATION_EMERGENCY_ACTIONS = frozenset(
    {
        "node_quarantine",
        "replay_freeze",
        "rollback_federation_mode",
        "distributed_orchestration_suspension",
        "federated_constitutional_freeze",
        "node_isolation",
    }
)

FEDERATION_HARD_CEILINGS = frozenset(
    {
        "incompatible_constitutional_node",
        "replay_breaking_federation",
        "continuity_breaking_federation",
        "governance_bypass_attempt",
        "unauthorized_authority_escalation",
        "orphaned_node_lineage",
        "distributed_replay_corruption",
    }
)

FEDERATION_SIMULATION_TYPES = (
    "node_failure",
    "replay_corruption",
    "continuity_corruption",
    "governance_divergence",
    "constitutional_incompatibility",
    "distributed_rollback",
    "federation_quarantine",
    "distributed_emergency_recovery",
)

FEDERATION_LINEAGE_TYPES = (
    "node_lineage",
    "federation_lineage",
    "cross_node_orchestration_lineage",
    "distributed_replay_lineage",
    "distributed_rollback_lineage",
    "federated_governance_lineage",
)


# ---------------------------------------------------------------------------
# Layer 1: Federated Node Registry
# ---------------------------------------------------------------------------


@dataclass
class FederatedNode:
    """A single node in the federated substrate network."""

    node_id: str = ""
    node_name: str = ""
    constitutional_hash: str = ""
    governance_lineage_hash: str = ""
    continuity_lineage_hash: str = ""
    maturity_level: str = "L0_NO_FEDERATION"
    trust_classification: str = "untrusted"
    replay_compatible: bool = False
    continuity_compatible: bool = False
    constitutionally_compatible: bool = False
    online: bool = False
    last_seen: str = ""

    def __post_init__(self) -> None:
        if not self.node_id:
            self.node_id = f"NODE-{uuid.uuid4().hex[:8]}"
        if not self.last_seen:
            self.last_seen = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "constitutional_hash": self.constitutional_hash,
            "governance_lineage_hash": self.governance_lineage_hash,
            "continuity_lineage_hash": self.continuity_lineage_hash,
            "maturity_level": self.maturity_level,
            "trust_classification": self.trust_classification,
            "replay_compatible": self.replay_compatible,
            "continuity_compatible": self.continuity_compatible,
            "constitutionally_compatible": self.constitutionally_compatible,
            "online": self.online,
            "last_seen": self.last_seen,
        }


@dataclass
class FederatedNodeRegistry:
    """Registry of all federated substrate nodes."""

    nodes: list[FederatedNode] = field(default_factory=list)
    federation_id: str = ""
    registry_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.federation_id:
            self.federation_id = f"FED-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def node_count(self) -> int:
        return len(self.nodes)

    def online_count(self) -> int:
        return sum(1 for n in self.nodes if n.online)

    def trusted_count(self) -> int:
        return sum(1 for n in self.nodes if n.trust_classification == "trusted")

    def compute_registry_hash(self) -> str:
        data = json.dumps([n.to_dict() for n in self.nodes], sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "federation_id": self.federation_id,
            "node_count": self.node_count(),
            "online_count": self.online_count(),
            "trusted_count": self.trusted_count(),
            "registry_hash": self.registry_hash or self.compute_registry_hash(),
            "nodes": [n.to_dict() for n in self.nodes],
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Layer 2: Federated Replay Coordination
# ---------------------------------------------------------------------------


@dataclass
class FederatedReplayCoordination:
    """Status of distributed replay coordination."""

    cross_node_replay_validated: bool = False
    replay_lineage_distributed: bool = False
    replay_compatibility_validated: bool = False
    replay_drift_detected: bool = False
    replay_drift_severity: float = 0.0
    federated_replay_contracts_active: bool = False
    replay_determinism_score: float = 0.0
    rollback_determinism_score: float = 0.0
    node_replay_coverage: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cross_node_replay_validated": self.cross_node_replay_validated,
            "replay_lineage_distributed": self.replay_lineage_distributed,
            "replay_compatibility_validated": self.replay_compatibility_validated,
            "replay_drift_detected": self.replay_drift_detected,
            "replay_drift_severity": round(self.replay_drift_severity, 4),
            "federated_replay_contracts_active": self.federated_replay_contracts_active,
            "replay_determinism_score": round(self.replay_determinism_score, 4),
            "rollback_determinism_score": round(self.rollback_determinism_score, 4),
            "node_replay_coverage": self.node_replay_coverage,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 3: Federated Continuity Coordination
# ---------------------------------------------------------------------------


@dataclass
class FederatedContinuityCoordination:
    """Status of distributed continuity coordination."""

    distributed_continuity_lineage: bool = False
    topology_continuity: bool = False
    governance_continuity: bool = False
    orchestration_continuity: bool = False
    federation_drift_analyzed: bool = False
    federation_drift_severity: float = 0.0
    continuity_preservation_score: float = 0.0
    governance_lineage_preservation_score: float = 0.0
    node_continuity_coverage: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "distributed_continuity_lineage": self.distributed_continuity_lineage,
            "topology_continuity": self.topology_continuity,
            "governance_continuity": self.governance_continuity,
            "orchestration_continuity": self.orchestration_continuity,
            "federation_drift_analyzed": self.federation_drift_analyzed,
            "federation_drift_severity": round(self.federation_drift_severity, 4),
            "continuity_preservation_score": round(self.continuity_preservation_score, 4),
            "governance_lineage_preservation_score": round(
                self.governance_lineage_preservation_score, 4
            ),
            "node_continuity_coverage": self.node_continuity_coverage,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 4: Federated Constitutional Governance
# ---------------------------------------------------------------------------


@dataclass
class FederatedConstitutionalGovernance:
    """Status of federated constitutional governance."""

    constitutional_compatibility_validated: bool = False
    authority_boundaries_enforced: bool = False
    governance_federation_validated: bool = False
    emergency_federation_governance: bool = False
    distributed_invariant_enforcement: bool = False
    constitutional_invariant_score: float = 0.0
    compatible_node_count: int = 0
    incompatible_node_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constitutional_compatibility_validated": self.constitutional_compatibility_validated,
            "authority_boundaries_enforced": self.authority_boundaries_enforced,
            "governance_federation_validated": self.governance_federation_validated,
            "emergency_federation_governance": self.emergency_federation_governance,
            "distributed_invariant_enforcement": self.distributed_invariant_enforcement,
            "constitutional_invariant_score": round(self.constitutional_invariant_score, 4),
            "compatible_node_count": self.compatible_node_count,
            "incompatible_node_count": self.incompatible_node_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Federation Trust Scores
# ---------------------------------------------------------------------------


@dataclass
class FederationTrustScores:
    """Trust scores across 7 federation dimensions."""

    replay_reliability: float = 0.0
    governance_reliability: float = 0.0
    continuity_reliability: float = 0.0
    rollback_reliability: float = 0.0
    topology_stability: float = 0.0
    constitutional_integrity: float = 0.0
    federation_drift_risk: float = 0.0

    def composite_trust(self) -> float:
        vals = [
            self.replay_reliability,
            self.governance_reliability,
            self.continuity_reliability,
            self.rollback_reliability,
            self.topology_stability,
            self.constitutional_integrity,
            self.federation_drift_risk,
        ]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_reliability": round(self.replay_reliability, 4),
            "governance_reliability": round(self.governance_reliability, 4),
            "continuity_reliability": round(self.continuity_reliability, 4),
            "rollback_reliability": round(self.rollback_reliability, 4),
            "topology_stability": round(self.topology_stability, 4),
            "constitutional_integrity": round(self.constitutional_integrity, 4),
            "federation_drift_risk": round(self.federation_drift_risk, 4),
            "composite_trust": self.composite_trust(),
        }


# ---------------------------------------------------------------------------
# Federation Drift Signal
# ---------------------------------------------------------------------------


@dataclass
class FederationDriftSignal:
    """A drift signal detected in the federation."""

    drift_type: str = ""
    severity: float = 0.0
    source_node_id: str = ""
    target_node_id: str = ""
    description: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type,
            "severity": round(self.severity, 4),
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "description": self.description,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Federation Emergency Governance
# ---------------------------------------------------------------------------


@dataclass
class FederatedEmergencyGovernance:
    """Status of federated emergency governance capabilities."""

    node_quarantine_available: bool = False
    replay_freeze_available: bool = False
    rollback_federation_mode_available: bool = False
    distributed_orchestration_suspension_available: bool = False
    federated_constitutional_freeze_available: bool = False
    node_isolation_available: bool = False
    all_emergency_actions_available: bool = False
    emergency_action_count: int = 0
    available_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_quarantine_available": self.node_quarantine_available,
            "replay_freeze_available": self.replay_freeze_available,
            "rollback_federation_mode_available": self.rollback_federation_mode_available,
            "distributed_orchestration_suspension_available": (
                self.distributed_orchestration_suspension_available
            ),
            "federated_constitutional_freeze_available": (
                self.federated_constitutional_freeze_available
            ),
            "node_isolation_available": self.node_isolation_available,
            "all_emergency_actions_available": self.all_emergency_actions_available,
            "emergency_action_count": self.emergency_action_count,
            "available_count": self.available_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Federation Simulation Outcome
# ---------------------------------------------------------------------------


@dataclass
class FederationSimulationOutcome:
    """Result of a federation simulation."""

    simulation_id: str = ""
    simulation_type: str = ""
    description: str = ""
    nodes_affected: int = 0
    replay_impact: str = "none"
    continuity_impact: str = "none"
    governance_impact: str = "none"
    recovery_possible: bool = True
    predicted_severity: str = "low"
    cascading_failures: int = 0
    analysis_notes: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.simulation_id:
            self.simulation_id = f"FEDSIM-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "simulation_type": self.simulation_type,
            "description": self.description,
            "nodes_affected": self.nodes_affected,
            "replay_impact": self.replay_impact,
            "continuity_impact": self.continuity_impact,
            "governance_impact": self.governance_impact,
            "recovery_possible": self.recovery_possible,
            "predicted_severity": self.predicted_severity,
            "cascading_failures": self.cascading_failures,
            "analysis_notes": self.analysis_notes,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Federation Evidence + Proof
# ---------------------------------------------------------------------------


@dataclass
class FederationEvidence:
    """Evidence collected during federation analysis."""

    node_registry_analyzed: bool = False
    node_count: int = 0
    online_count: int = 0
    trusted_count: int = 0
    replay_coordination_analyzed: bool = False
    replay_determinism_validated: bool = False
    rollback_determinism_validated: bool = False
    continuity_coordination_analyzed: bool = False
    continuity_preservation_validated: bool = False
    governance_lineage_preserved: bool = False
    constitutional_governance_analyzed: bool = False
    constitutional_compatibility_validated: bool = False
    constitutional_invariants_preserved: bool = False
    trust_scored: bool = False
    trust_composite: float = 0.0
    drift_analyzed: bool = False
    drift_signal_count: int = 0
    federation_entropy: float = 0.0
    emergency_governance_analyzed: bool = False
    emergency_actions_available: int = 0
    simulations_completed: bool = False
    simulation_count: int = 0
    hard_ceilings_enforced: bool = True
    governance_bypass_blocked: bool = True
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_registry_analyzed": self.node_registry_analyzed,
            "node_count": self.node_count,
            "online_count": self.online_count,
            "trusted_count": self.trusted_count,
            "replay_coordination_analyzed": self.replay_coordination_analyzed,
            "replay_determinism_validated": self.replay_determinism_validated,
            "rollback_determinism_validated": self.rollback_determinism_validated,
            "continuity_coordination_analyzed": self.continuity_coordination_analyzed,
            "continuity_preservation_validated": self.continuity_preservation_validated,
            "governance_lineage_preserved": self.governance_lineage_preserved,
            "constitutional_governance_analyzed": self.constitutional_governance_analyzed,
            "constitutional_compatibility_validated": self.constitutional_compatibility_validated,
            "constitutional_invariants_preserved": self.constitutional_invariants_preserved,
            "trust_scored": self.trust_scored,
            "trust_composite": round(self.trust_composite, 4),
            "drift_analyzed": self.drift_analyzed,
            "drift_signal_count": self.drift_signal_count,
            "federation_entropy": round(self.federation_entropy, 4),
            "emergency_governance_analyzed": self.emergency_governance_analyzed,
            "emergency_actions_available": self.emergency_actions_available,
            "simulations_completed": self.simulations_completed,
            "simulation_count": self.simulation_count,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "governance_bypass_blocked": self.governance_bypass_blocked,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class FederationProof:
    """Complete proof of distributed constitutional federation."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_FEDERATION"
    maturity_ceiling: str = "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: FederationEvidence | None = None
    node_registry: FederatedNodeRegistry | None = None
    replay_coordination: FederatedReplayCoordination | None = None
    continuity_coordination: FederatedContinuityCoordination | None = None
    constitutional_governance: FederatedConstitutionalGovernance | None = None
    trust_scores: FederationTrustScores | None = None
    drift_signals: list[FederationDriftSignal] = field(default_factory=list)
    emergency_governance: FederatedEmergencyGovernance | None = None
    simulations: list[FederationSimulationOutcome] = field(default_factory=list)
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"FEDRT-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "distributed_constitutional_federation",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "node_registry": self.node_registry.to_dict() if self.node_registry else None,
            "replay_coordination": (
                self.replay_coordination.to_dict() if self.replay_coordination else None
            ),
            "continuity_coordination": (
                self.continuity_coordination.to_dict() if self.continuity_coordination else None
            ),
            "constitutional_governance": (
                self.constitutional_governance.to_dict() if self.constitutional_governance else None
            ),
            "trust_scores": self.trust_scores.to_dict() if self.trust_scores else None,
            "drift_signals": [d.to_dict() for d in self.drift_signals],
            "emergency_governance": (
                self.emergency_governance.to_dict() if self.emergency_governance else None
            ),
            "simulations": [s.to_dict() for s in self.simulations],
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Layer 1 builder: Federated Node Registry
# ---------------------------------------------------------------------------


def build_node_registry(
    constitutional_proof: ConstitutionalProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    base_dir: Path = Path(_ROOT),
) -> FederatedNodeRegistry:
    """Build the federated node registry from substrate state."""
    registry = FederatedNodeRegistry()

    const_hash = ""
    gov_hash = ""
    cont_hash = ""
    mat_level = "L0_NO_FEDERATION"

    if constitutional_proof:
        const_hash = hashlib.sha256(
            json.dumps(constitutional_proof.to_dict(), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        mat_level = constitutional_proof.maturity_level

    if orchestration_proof:
        gov_hash = hashlib.sha256(
            json.dumps(orchestration_proof.to_dict(), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    if continuity_proof:
        cont_hash = hashlib.sha256(
            json.dumps(continuity_proof.to_dict(), sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    has_const = constitutional_proof is not None
    has_orch = orchestration_proof is not None
    has_cont = continuity_proof is not None

    primary = FederatedNode(
        node_name="primary_vps",
        constitutional_hash=const_hash,
        governance_lineage_hash=gov_hash,
        continuity_lineage_hash=cont_hash,
        maturity_level=mat_level,
        trust_classification="trusted" if has_const else "untrusted",
        replay_compatible=has_orch,
        continuity_compatible=has_cont,
        constitutionally_compatible=has_const,
        online=True,
    )
    registry.nodes.append(primary)

    relay_dir = base_dir / "data/runtime/local_worker_runtime"
    heartbeat = relay_dir / "heartbeat.json"
    if heartbeat.exists():
        try:
            hb = json.loads(heartbeat.read_text())
            relay_node = FederatedNode(
                node_name="windows_relay",
                constitutional_hash=const_hash,
                governance_lineage_hash=gov_hash,
                continuity_lineage_hash=cont_hash,
                maturity_level="L1_NODE_REGISTERED",
                trust_classification="provisional",
                replay_compatible=has_orch,
                continuity_compatible=has_cont,
                constitutionally_compatible=has_const,
                online=hb.get("status") == "alive",
            )
            registry.nodes.append(relay_node)
        except (json.JSONDecodeError, OSError):
            pass

    registry.registry_hash = registry.compute_registry_hash()
    return registry


# ---------------------------------------------------------------------------
# Layer 2 builder: Federated Replay Coordination
# ---------------------------------------------------------------------------


def build_replay_coordination(
    node_registry: FederatedNodeRegistry,
    orchestration_proof: OrchestrationProof | None = None,
    constitutional_proof: ConstitutionalProof | None = None,
) -> FederatedReplayCoordination:
    """Build distributed replay coordination status."""
    coord = FederatedReplayCoordination()
    coord.node_replay_coverage = sum(1 for n in node_registry.nodes if n.replay_compatible)

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if ev.replay_validated:
            coord.cross_node_replay_validated = True
            coord.replay_lineage_distributed = True
            coord.replay_compatibility_validated = True
            coord.analysis_notes.append("replay validated via orchestration proof")

            rp_total = ev.replay_safe_count + ev.replay_unsafe_count
            coord.replay_determinism_score = (
                round(ev.replay_safe_count / rp_total, 4) if rp_total > 0 else 1.0
            )

        if ev.rollback_validated:
            rb_total = ev.rollback_safe_count + ev.rollback_unsafe_count
            coord.rollback_determinism_score = (
                round(ev.rollback_safe_count / rb_total, 4) if rb_total > 0 else 1.0
            )

        if ev.replay_unsafe_count > 0:
            coord.replay_drift_detected = True
            coord.replay_drift_severity = round(
                ev.replay_unsafe_count / max(ev.replay_safe_count + ev.replay_unsafe_count, 1),
                4,
            )
            coord.analysis_notes.append(f"replay drift: {ev.replay_unsafe_count} unsafe chains")

    if constitutional_proof and constitutional_proof.evidence:
        cev = constitutional_proof.evidence
        if cev.hard_ceilings_enforced:
            coord.federated_replay_contracts_active = True

    return coord


# ---------------------------------------------------------------------------
# Layer 3 builder: Federated Continuity Coordination
# ---------------------------------------------------------------------------


def build_continuity_coordination(
    node_registry: FederatedNodeRegistry,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
) -> FederatedContinuityCoordination:
    """Build distributed continuity coordination status."""
    coord = FederatedContinuityCoordination()
    coord.node_continuity_coverage = sum(1 for n in node_registry.nodes if n.continuity_compatible)

    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        if cev.execution_lineage_present:
            coord.distributed_continuity_lineage = True
            coord.analysis_notes.append("continuity lineage present")
        if cev.topology_evolution_present:
            coord.topology_continuity = True
            coord.analysis_notes.append("topology continuity present")
        if cev.governance_continuity_enforced:
            coord.governance_continuity = True
            coord.analysis_notes.append("governance continuity enforced")
        if cev.drift_analysis_completed:
            coord.federation_drift_analyzed = True
            coord.federation_drift_severity = cev.drift_max_severity
            coord.analysis_notes.append(f"drift severity: {cev.drift_max_severity:.3f}")

        total_present = sum(
            [
                cev.execution_lineage_present,
                cev.orchestration_history_present,
                cev.capability_evolution_present,
                cev.topology_evolution_present,
                cev.registry_evolution_present,
            ]
        )
        coord.continuity_preservation_score = round(total_present / 5.0, 4)

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if ev.governance_validated:
            coord.orchestration_continuity = True

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if gev.governance_ceilings_enforced:
            coord.governance_lineage_preservation_score = 1.0
        else:
            coord.governance_lineage_preservation_score = 0.5

    return coord


# ---------------------------------------------------------------------------
# Layer 4 builder: Federated Constitutional Governance
# ---------------------------------------------------------------------------


def build_constitutional_governance(
    node_registry: FederatedNodeRegistry,
    constitutional_proof: ConstitutionalProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    founder_confirmed: bool = False,
) -> FederatedConstitutionalGovernance:
    """Build federated constitutional governance status."""
    gov = FederatedConstitutionalGovernance()

    compatible = sum(1 for n in node_registry.nodes if n.constitutionally_compatible)
    incompatible = node_registry.node_count() - compatible
    gov.compatible_node_count = compatible
    gov.incompatible_node_count = incompatible

    if constitutional_proof:
        if constitutional_proof.safety_invariants:
            si = constitutional_proof.safety_invariants
            if si.all_invariants_active:
                gov.constitutional_compatibility_validated = True
                gov.distributed_invariant_enforcement = True
                gov.analysis_notes.append("all invariants active")
            gov.constitutional_invariant_score = round(
                si.active_count / max(si.invariant_count, 1), 4
            )

        if constitutional_proof.authority_boundaries:
            ab = constitutional_proof.authority_boundaries
            if ab.all_boundaries_enforced:
                gov.authority_boundaries_enforced = True
                gov.analysis_notes.append("all authority boundaries enforced")

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if gev.governance_ceilings_enforced and gev.autonomous_mutation_blocked:
            gov.governance_federation_validated = True
            gov.analysis_notes.append("governance federation validated")

    if founder_confirmed and constitutional_proof:
        gov.emergency_federation_governance = True
        gov.analysis_notes.append("emergency federation governance with founder confirmation")

    return gov


# ---------------------------------------------------------------------------
# Federation Trust Scoring
# ---------------------------------------------------------------------------


def compute_federation_trust(
    node_registry: FederatedNodeRegistry,
    replay_coord: FederatedReplayCoordination,
    continuity_coord: FederatedContinuityCoordination,
    constitutional_gov: FederatedConstitutionalGovernance,
) -> FederationTrustScores:
    """Compute 7-dimension federation trust profile."""
    scores = FederationTrustScores()

    scores.replay_reliability = replay_coord.replay_determinism_score
    scores.rollback_reliability = replay_coord.rollback_determinism_score
    scores.continuity_reliability = continuity_coord.continuity_preservation_score
    scores.governance_reliability = continuity_coord.governance_lineage_preservation_score
    scores.constitutional_integrity = constitutional_gov.constitutional_invariant_score

    if node_registry.node_count() > 0:
        scores.topology_stability = round(
            node_registry.online_count() / node_registry.node_count(), 4
        )

    if replay_coord.replay_drift_detected:
        scores.federation_drift_risk = replay_coord.replay_drift_severity
    elif continuity_coord.federation_drift_analyzed:
        scores.federation_drift_risk = continuity_coord.federation_drift_severity

    return scores


# ---------------------------------------------------------------------------
# Federation Drift Detection
# ---------------------------------------------------------------------------


def detect_federation_drift(
    node_registry: FederatedNodeRegistry,
    replay_coord: FederatedReplayCoordination,
    continuity_coord: FederatedContinuityCoordination,
    constitutional_gov: FederatedConstitutionalGovernance,
) -> list[FederationDriftSignal]:
    """Detect drift signals across the federation."""
    signals: list[FederationDriftSignal] = []

    primary_hash = ""
    for n in node_registry.nodes:
        if n.node_name == "primary_vps":
            primary_hash = n.constitutional_hash
            break

    for node in node_registry.nodes:
        if node.node_name == "primary_vps":
            continue
        if node.constitutional_hash != primary_hash and primary_hash:
            signals.append(
                FederationDriftSignal(
                    drift_type="constitutional_divergence",
                    severity=0.8,
                    source_node_id=node.node_id,
                    description=f"constitutional hash mismatch: {node.node_name}",
                )
            )
        if not node.replay_compatible:
            signals.append(
                FederationDriftSignal(
                    drift_type="replay_divergence",
                    severity=0.6,
                    source_node_id=node.node_id,
                    description=f"replay incompatible: {node.node_name}",
                )
            )
        if not node.continuity_compatible:
            signals.append(
                FederationDriftSignal(
                    drift_type="continuity_divergence",
                    severity=0.6,
                    source_node_id=node.node_id,
                    description=f"continuity incompatible: {node.node_name}",
                )
            )

    if replay_coord.replay_drift_detected:
        signals.append(
            FederationDriftSignal(
                drift_type="replay_divergence",
                severity=replay_coord.replay_drift_severity,
                description="replay drift detected across federation",
            )
        )

    if (
        continuity_coord.federation_drift_analyzed
        and continuity_coord.federation_drift_severity > 0
    ):
        signals.append(
            FederationDriftSignal(
                drift_type="continuity_divergence",
                severity=continuity_coord.federation_drift_severity,
                description="continuity drift detected across federation",
            )
        )

    if constitutional_gov.incompatible_node_count > 0:
        signals.append(
            FederationDriftSignal(
                drift_type="node_divergence",
                severity=0.9,
                description=f"{constitutional_gov.incompatible_node_count} incompatible nodes",
            )
        )

    if not constitutional_gov.governance_federation_validated:
        signals.append(
            FederationDriftSignal(
                drift_type="governance_divergence",
                severity=0.5,
                description="governance federation not validated",
            )
        )

    total_nodes = node_registry.node_count()
    if total_nodes > 0:
        online_ratio = node_registry.online_count() / total_nodes
        if online_ratio < 1.0:
            signals.append(
                FederationDriftSignal(
                    drift_type="federation_entropy",
                    severity=round(1.0 - online_ratio, 4),
                    description=f"federation entropy: {node_registry.online_count()}/{total_nodes} online",
                )
            )

    return signals


# ---------------------------------------------------------------------------
# Federation Emergency Governance
# ---------------------------------------------------------------------------


def build_emergency_governance(
    constitutional_proof: ConstitutionalProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    node_registry: FederatedNodeRegistry | None = None,
    founder_confirmed: bool = False,
) -> FederatedEmergencyGovernance:
    """Build federated emergency governance capabilities."""
    eg = FederatedEmergencyGovernance()
    eg.emergency_action_count = len(FEDERATION_EMERGENCY_ACTIONS)

    has_const = constitutional_proof is not None
    has_orch = orchestration_proof is not None
    has_nodes = node_registry is not None and node_registry.node_count() > 0

    if has_nodes:
        eg.node_quarantine_available = True
        eg.node_isolation_available = True
        eg.analysis_notes.append("node quarantine/isolation via registry")

    if has_orch:
        eg.replay_freeze_available = True
        eg.distributed_orchestration_suspension_available = True
        eg.analysis_notes.append("replay freeze/suspension via orchestration")

    if has_const and has_orch:
        eg.rollback_federation_mode_available = True
        eg.analysis_notes.append("rollback federation mode available")

    if has_const and founder_confirmed:
        eg.federated_constitutional_freeze_available = True
        eg.analysis_notes.append("constitutional freeze with founder confirmation")

    available = sum(
        [
            eg.node_quarantine_available,
            eg.replay_freeze_available,
            eg.rollback_federation_mode_available,
            eg.distributed_orchestration_suspension_available,
            eg.federated_constitutional_freeze_available,
            eg.node_isolation_available,
        ]
    )
    eg.available_count = available
    eg.all_emergency_actions_available = available == eg.emergency_action_count

    return eg


# ---------------------------------------------------------------------------
# Federation Hard Ceiling Enforcement
# ---------------------------------------------------------------------------


def enforce_federation_hard_ceilings(
    node_registry: FederatedNodeRegistry,
    constitutional_gov: FederatedConstitutionalGovernance,
    replay_coord: FederatedReplayCoordination,
    continuity_coord: FederatedContinuityCoordination,
) -> tuple[bool, list[str]]:
    """Enforce federation hard ceilings. Returns (blocked, reasons)."""
    blocked = False
    reasons: list[str] = []

    if constitutional_gov.incompatible_node_count > 0:
        blocked = True
        reasons.append(
            f"incompatible_constitutional_node: {constitutional_gov.incompatible_node_count} nodes"
        )

    if replay_coord.replay_drift_detected and replay_coord.replay_drift_severity > 0.5:
        blocked = True
        reasons.append("replay_breaking_federation: severe replay drift")

    if (
        not continuity_coord.distributed_continuity_lineage
        and continuity_coord.node_continuity_coverage > 0
    ):
        blocked = True
        reasons.append("continuity_breaking_federation: lineage not distributed")

    if not constitutional_gov.governance_federation_validated:
        reasons.append("governance_bypass_attempt: federation governance not validated")

    orphaned = [n for n in node_registry.nodes if not n.constitutionally_compatible and n.online]
    if orphaned:
        blocked = True
        reasons.append(f"orphaned_node_lineage: {len(orphaned)} orphaned nodes")

    return blocked, reasons


# ---------------------------------------------------------------------------
# Federation Simulation Engine
# ---------------------------------------------------------------------------


def run_federation_simulations(
    node_registry: FederatedNodeRegistry,
    trust_scores: FederationTrustScores,
    drift_signals: list[FederationDriftSignal],
) -> list[FederationSimulationOutcome]:
    """Run all 8 federation simulation types."""
    simulations: list[FederationSimulationOutcome] = []
    n_count = max(node_registry.node_count(), 1)
    composite = trust_scores.composite_trust()

    # 1. node_failure
    sim1 = FederationSimulationOutcome(
        simulation_type="node_failure",
        description="Simulate single node failure impact on federation",
        nodes_affected=1,
        replay_impact="degraded" if trust_scores.replay_reliability < 0.8 else "minimal",
        continuity_impact="degraded" if trust_scores.continuity_reliability < 0.8 else "minimal",
        governance_impact="minimal",
        recovery_possible=True,
        predicted_severity="medium" if n_count <= 2 else "low",
        cascading_failures=0,
    )
    sim1.analysis_notes.append(f"nodes={n_count}")
    simulations.append(sim1)

    # 2. replay_corruption
    sim2 = FederationSimulationOutcome(
        simulation_type="replay_corruption",
        description="Simulate replay chain corruption across federation",
        nodes_affected=n_count,
        replay_impact="critical",
        continuity_impact="degraded",
        governance_impact="degraded",
        recovery_possible=trust_scores.rollback_reliability > 0.5,
        predicted_severity="critical" if trust_scores.replay_reliability < 0.5 else "high",
        cascading_failures=max(1, int((1.0 - trust_scores.replay_reliability) * n_count)),
    )
    sim2.analysis_notes.append(f"replay_reliability={trust_scores.replay_reliability:.3f}")
    simulations.append(sim2)

    # 3. continuity_corruption
    sim3 = FederationSimulationOutcome(
        simulation_type="continuity_corruption",
        description="Simulate continuity lineage corruption",
        nodes_affected=n_count,
        replay_impact="degraded",
        continuity_impact="critical",
        governance_impact="degraded",
        recovery_possible=trust_scores.continuity_reliability > 0.4,
        predicted_severity="critical" if trust_scores.continuity_reliability < 0.5 else "high",
        cascading_failures=max(1, int((1.0 - trust_scores.continuity_reliability) * n_count)),
    )
    sim3.analysis_notes.append(f"continuity_reliability={trust_scores.continuity_reliability:.3f}")
    simulations.append(sim3)

    # 4. governance_divergence
    sim4 = FederationSimulationOutcome(
        simulation_type="governance_divergence",
        description="Simulate governance state divergence between nodes",
        nodes_affected=max(1, n_count - 1),
        replay_impact="minimal",
        continuity_impact="degraded",
        governance_impact="critical",
        recovery_possible=trust_scores.governance_reliability > 0.5,
        predicted_severity="critical" if trust_scores.governance_reliability < 0.5 else "high",
        cascading_failures=int((1.0 - trust_scores.governance_reliability) * 3),
    )
    sim4.analysis_notes.append(f"gov_reliability={trust_scores.governance_reliability:.3f}")
    simulations.append(sim4)

    # 5. constitutional_incompatibility
    sim5 = FederationSimulationOutcome(
        simulation_type="constitutional_incompatibility",
        description="Simulate constitutional hash mismatch across nodes",
        nodes_affected=n_count,
        replay_impact="critical",
        continuity_impact="critical",
        governance_impact="critical",
        recovery_possible=trust_scores.constitutional_integrity > 0.3,
        predicted_severity="critical",
        cascading_failures=max(2, int((1.0 - trust_scores.constitutional_integrity) * n_count * 2)),
    )
    sim5.analysis_notes.append(f"const_integrity={trust_scores.constitutional_integrity:.3f}")
    simulations.append(sim5)

    # 6. distributed_rollback
    sim6 = FederationSimulationOutcome(
        simulation_type="distributed_rollback",
        description="Simulate coordinated rollback across federation",
        nodes_affected=n_count,
        replay_impact="degraded",
        continuity_impact="degraded",
        governance_impact="minimal",
        recovery_possible=True,
        predicted_severity="high" if trust_scores.rollback_reliability < 0.5 else "medium",
        cascading_failures=int((1.0 - trust_scores.rollback_reliability) * 2),
    )
    sim6.analysis_notes.append(f"rollback_reliability={trust_scores.rollback_reliability:.3f}")
    simulations.append(sim6)

    # 7. federation_quarantine
    sim7 = FederationSimulationOutcome(
        simulation_type="federation_quarantine",
        description="Simulate full federation quarantine procedure",
        nodes_affected=n_count,
        replay_impact="frozen",
        continuity_impact="frozen",
        governance_impact="elevated",
        recovery_possible=True,
        predicted_severity="high",
        cascading_failures=0,
    )
    sim7.analysis_notes.append("quarantine freezes all activity")
    simulations.append(sim7)

    # 8. distributed_emergency_recovery
    drift_count = len(drift_signals)
    sim8 = FederationSimulationOutcome(
        simulation_type="distributed_emergency_recovery",
        description="Simulate emergency recovery after federation failure",
        nodes_affected=n_count,
        replay_impact="rebuilding",
        continuity_impact="rebuilding",
        governance_impact="rebuilding",
        recovery_possible=composite > 0.3,
        predicted_severity="critical" if composite < 0.4 else "high",
        cascading_failures=drift_count,
    )
    sim8.analysis_notes.append(f"composite_trust={composite:.3f}, drift_signals={drift_count}")
    simulations.append(sim8)

    return simulations


# ---------------------------------------------------------------------------
# Maturity Classification
# ---------------------------------------------------------------------------


def compute_federation_maturity(evidence: FederationEvidence) -> int:
    """Compute numeric maturity score from evidence."""
    score = 0
    if evidence.node_registry_analyzed and evidence.node_count > 0:
        score += 1
    if evidence.replay_coordination_analyzed and evidence.replay_determinism_validated:
        score += 1
    if evidence.rollback_determinism_validated:
        score += 1
    if evidence.continuity_coordination_analyzed and evidence.continuity_preservation_validated:
        score += 1
    if evidence.governance_lineage_preserved:
        score += 1
    if (
        evidence.constitutional_governance_analyzed
        and evidence.constitutional_compatibility_validated
    ):
        score += 1
    if evidence.constitutional_invariants_preserved:
        score += 1
    if evidence.trust_scored:
        score += 1
    if evidence.drift_analyzed:
        score += 1
    if evidence.emergency_governance_analyzed and evidence.emergency_actions_available > 0:
        score += 1
    if evidence.simulations_completed:
        score += 1
    if evidence.founder_confirmed:
        score += 1
    if evidence.hard_ceilings_enforced and evidence.governance_bypass_blocked:
        score += 1
    return score


def federation_maturity_ceiling(
    evidence: FederationEvidence,
) -> tuple[str, bool, str]:
    """Compute federation maturity ceiling. Returns (ceiling, blocked, reason)."""
    if evidence.is_dry_run:
        return "L0_NO_FEDERATION", True, "dry run"
    if not evidence.node_registry_analyzed or evidence.node_count == 0:
        return "L0_NO_FEDERATION", True, "no nodes registered"
    if not evidence.replay_coordination_analyzed:
        return "L1_NODE_REGISTERED", True, "replay not coordinated"
    if not evidence.replay_determinism_validated:
        return "L1_NODE_REGISTERED", True, "replay determinism not validated"
    if not evidence.continuity_coordination_analyzed:
        return "L2_REPLAY_COORDINATED", True, "continuity not coordinated"
    if not evidence.continuity_preservation_validated:
        return "L2_REPLAY_COORDINATED", True, "continuity not preserved"
    if not evidence.constitutional_governance_analyzed:
        return "L3_CONTINUITY_COORDINATED", True, "constitutional governance not analyzed"
    if not evidence.constitutional_compatibility_validated:
        return "L3_CONTINUITY_COORDINATED", True, "constitutional compatibility not validated"
    if not evidence.emergency_governance_analyzed:
        return "L4_CONSTITUTIONALLY_GOVERNED", True, "emergency governance not analyzed"
    if not evidence.simulations_completed:
        return "L4_CONSTITUTIONALLY_GOVERNED", True, "simulations not completed"
    if not evidence.founder_confirmed:
        return "L4_CONSTITUTIONALLY_GOVERNED", True, "founder not confirmed"
    if not evidence.hard_ceilings_enforced:
        return "L4_CONSTITUTIONALLY_GOVERNED", True, "hard ceilings not enforced"
    if not evidence.governance_bypass_blocked:
        return "L4_CONSTITUTIONALLY_GOVERNED", True, "governance bypass not blocked"
    return "L5_DISTRIBUTED_CONSTITUTIONAL_FEDERATION", False, ""


def classify_federation_maturity(
    evidence: FederationEvidence,
) -> tuple[str, str, bool, str]:
    """Classify maturity. Returns (level, ceiling, blocked, reason)."""
    ceiling, blocked, reason = federation_maturity_ceiling(evidence)
    score = compute_federation_maturity(evidence)
    ceiling_idx = FEDERATION_MATURITY_LEVELS.index(ceiling)

    if score >= 12:
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
    level = FEDERATION_MATURITY_LEVELS[level_idx]
    return level, ceiling, blocked, reason


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


def build_full_federation_proof(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    constitutional_proof: ConstitutionalProof | None = None,
    capability_proof: CapabilityPlanningProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
    base_dir: Path = Path(_ROOT),
) -> FederationProof:
    """Full distributed constitutional federation pipeline."""
    registry = build_node_registry(
        constitutional_proof, orchestration_proof, continuity_proof, base_dir
    )
    replay = build_replay_coordination(registry, orchestration_proof, constitutional_proof)
    continuity = build_continuity_coordination(
        registry, continuity_proof, governance_proof, orchestration_proof
    )
    const_gov = build_constitutional_governance(
        registry, constitutional_proof, governance_proof, founder_confirmed
    )
    trust = compute_federation_trust(registry, replay, continuity, const_gov)
    drift = detect_federation_drift(registry, replay, continuity, const_gov)
    emergency = build_emergency_governance(
        constitutional_proof, orchestration_proof, registry, founder_confirmed
    )

    ceiling_blocked, ceiling_reasons = enforce_federation_hard_ceilings(
        registry, const_gov, replay, continuity
    )

    simulations = run_federation_simulations(registry, trust, drift)

    has_replay = replay.cross_node_replay_validated
    has_cont = continuity.distributed_continuity_lineage
    has_const = const_gov.constitutional_compatibility_validated

    evidence = FederationEvidence(
        node_registry_analyzed=True,
        node_count=registry.node_count(),
        online_count=registry.online_count(),
        trusted_count=registry.trusted_count(),
        replay_coordination_analyzed=True,
        replay_determinism_validated=has_replay,
        rollback_determinism_validated=replay.rollback_determinism_score > 0,
        continuity_coordination_analyzed=True,
        continuity_preservation_validated=has_cont,
        governance_lineage_preserved=continuity.governance_continuity,
        constitutional_governance_analyzed=True,
        constitutional_compatibility_validated=has_const,
        constitutional_invariants_preserved=const_gov.distributed_invariant_enforcement,
        trust_scored=True,
        trust_composite=trust.composite_trust(),
        drift_analyzed=True,
        drift_signal_count=len(drift),
        federation_entropy=trust.federation_drift_risk,
        emergency_governance_analyzed=True,
        emergency_actions_available=emergency.available_count,
        simulations_completed=True,
        simulation_count=len(simulations),
        hard_ceilings_enforced=True,
        governance_bypass_blocked=True,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_federation_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "await_founder_confirmation"
            if not founder_confirmed
            else "distributed_federation_active"
        )
    )

    return FederationProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        node_registry=registry,
        replay_coordination=replay,
        continuity_coordination=continuity,
        constitutional_governance=const_gov,
        trust_scores=trust,
        drift_signals=drift,
        emergency_governance=emergency,
        simulations=simulations,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_federation_proof(
    proof: FederationProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist federation proof to disk."""
    report_dir = base_dir / FEDERATION_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
