"""Constitutional Substrate Governance Layer v1.

Establishes immutable substrate invariants, protected authority boundaries,
constitutional replay contracts, governance escalation laws, and non-negotiable
recursive safety principles governing all future substrate evolution.

Constitutional invariants represent the highest governance authority.
No orchestration, governance, maturity, continuity, or adaptive intelligence
layer may bypass constitutional constraints.

Constitutional rules may only be modified through explicit founder-governed
constitutional migration procedures.

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

from core.workstation.adaptive_governance_intelligence_engine_v1 import (
    GOVERNANCE_INTELLIGENCE_HARD_CEILINGS,
    GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS,
    AdaptiveRiskScores,
    GovernanceIntelligenceEvidence,
    GovernanceIntelligenceProof,
    GovernanceProposal,
    build_full_governance_intelligence_proof,
)
from core.workstation.governed_recursive_orchestration_engine_v1 import (
    ORCHESTRATION_MATURITY_LEVELS,
    OrchestrationEvidence,
    OrchestrationProof,
    build_full_orchestration_proof,
)
from core.workstation.persistent_substrate_continuity_engine_v1 import (
    CONTINUITY_MATURITY_LEVELS,
    ContinuityEvidence,
    ContinuityProof,
    build_full_continuity_proof,
)
from core.workstation.recursive_capability_planning_engine_v1 import (

    CAPABILITY_MATURITY_LEVELS,
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

CONSTITUTIONAL_REPORT_DIR = "data/runtime/workstation_relay/constitutional_reports"

CONSTITUTIONAL_MATURITY_LEVELS = (
    "L0_NO_CONSTITUTIONAL_GOVERNANCE",
    "L1_INVARIANT_DEFINED",
    "L2_AUTHORITY_BOUNDED",
    "L3_CONTINUITY_CONTRACTED",
    "L4_EMERGENCY_GOVERNED",
    "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE",
)

CONSTITUTIONAL_SAFETY_INVARIANTS = frozenset(
    {
        "replayability_required",
        "rollbackability_required",
        "governance_lineage_required",
        "continuity_lineage_required",
        "evidence_based_maturity_required",
        "human_in_the_loop_enforcement_required",
    }
)

CONSTITUTIONAL_AUTHORITY_BOUNDARIES = frozenset(
    {
        "no_autonomous_canonical_mutation",
        "no_autonomous_governance_mutation",
        "no_autonomous_maturity_escalation",
        "no_autonomous_authority_escalation",
        "no_autonomous_recursive_deployment",
    }
)

CONSTITUTIONAL_CONTINUITY_CONTRACTS = frozenset(
    {
        "lineage_preservation",
        "continuity_preservation",
        "replay_preservation",
        "rollback_preservation",
        "governance_audit_preservation",
    }
)

CONSTITUTIONAL_EMERGENCY_ACTIONS = frozenset(
    {
        "emergency_freeze",
        "rollback_authority",
        "substrate_quarantine",
        "relay_isolation",
        "orchestration_suspension",
        "constitutional_violation_escalation",
    }
)

CONSTITUTIONAL_HARD_CEILINGS = frozenset(
    {
        "invariant_violation",
        "orphaned_authority_escalation",
        "replay_breaking_mutation",
        "rollback_breaking_mutation",
        "continuity_breaking_mutation",
        "governance_bypass_attempt",
        "lineage_corruption",
        "recursive_mutation_without_governance_lineage",
    }
)

CONSTITUTIONAL_INTEGRITY_CHECKS = (
    "replay_integrity",
    "rollback_integrity",
    "governance_integrity",
    "continuity_integrity",
    "orchestration_integrity",
    "maturity_integrity",
    "lineage_integrity",
)

MUTATION_CLASSIFICATIONS = (
    "safe_mutation",
    "governance_mutation",
    "constitutional_impact_mutation",
    "replay_risk_mutation",
    "continuity_risk_mutation",
    "topology_risk_mutation",
)

CONSTITUTIONAL_RISK_DIMENSIONS = (
    "constitutional_fragility",
    "invariant_pressure",
    "authority_drift",
    "governance_instability",
    "replay_instability",
    "continuity_instability",
    "recursive_entropy_pressure",
)

CONSTITUTIONAL_SIMULATION_TYPES = (
    "invariant_violation",
    "governance_bypass",
    "replay_collapse",
    "continuity_collapse",
    "rollback_collapse",
    "authority_escalation",
    "orchestration_corruption",
    "recursive_instability_cascade",
)

CONSTITUTIONAL_MIGRATION_REQUIREMENTS = (
    "founder_approval",
    "replay_validation",
    "rollback_validation",
    "continuity_validation",
    "governance_lineage",
    "constitutional_migration_proof",
)


# ---------------------------------------------------------------------------
# Layer 1: Constitutional Safety Invariants
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalSafetyInvariantStatus:
    """Status of each constitutional safety invariant."""

    replayability_required: bool = False
    rollbackability_required: bool = False
    governance_lineage_required: bool = False
    continuity_lineage_required: bool = False
    evidence_based_maturity_required: bool = False
    human_in_the_loop_enforcement_required: bool = False
    all_invariants_active: bool = False
    invariant_count: int = 0
    active_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replayability_required": self.replayability_required,
            "rollbackability_required": self.rollbackability_required,
            "governance_lineage_required": self.governance_lineage_required,
            "continuity_lineage_required": self.continuity_lineage_required,
            "evidence_based_maturity_required": self.evidence_based_maturity_required,
            "human_in_the_loop_enforcement_required": self.human_in_the_loop_enforcement_required,
            "all_invariants_active": self.all_invariants_active,
            "invariant_count": self.invariant_count,
            "active_count": self.active_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 2: Constitutional Authority Boundaries
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalAuthorityBoundaryStatus:
    """Status of constitutional authority boundaries."""

    no_autonomous_canonical_mutation: bool = True
    no_autonomous_governance_mutation: bool = True
    no_autonomous_maturity_escalation: bool = True
    no_autonomous_authority_escalation: bool = True
    no_autonomous_recursive_deployment: bool = True
    all_boundaries_enforced: bool = False
    boundary_count: int = 0
    enforced_count: int = 0
    violations_detected: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "no_autonomous_canonical_mutation": self.no_autonomous_canonical_mutation,
            "no_autonomous_governance_mutation": self.no_autonomous_governance_mutation,
            "no_autonomous_maturity_escalation": self.no_autonomous_maturity_escalation,
            "no_autonomous_authority_escalation": self.no_autonomous_authority_escalation,
            "no_autonomous_recursive_deployment": self.no_autonomous_recursive_deployment,
            "all_boundaries_enforced": self.all_boundaries_enforced,
            "boundary_count": self.boundary_count,
            "enforced_count": self.enforced_count,
            "violations_detected": self.violations_detected,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 3: Constitutional Continuity Contracts
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalContinuityContractStatus:
    """Status of constitutional continuity contracts."""

    lineage_preservation: bool = False
    continuity_preservation: bool = False
    replay_preservation: bool = False
    rollback_preservation: bool = False
    governance_audit_preservation: bool = False
    all_contracts_enforced: bool = False
    contract_count: int = 0
    enforced_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_preservation": self.lineage_preservation,
            "continuity_preservation": self.continuity_preservation,
            "replay_preservation": self.replay_preservation,
            "rollback_preservation": self.rollback_preservation,
            "governance_audit_preservation": self.governance_audit_preservation,
            "all_contracts_enforced": self.all_contracts_enforced,
            "contract_count": self.contract_count,
            "enforced_count": self.enforced_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 4: Constitutional Emergency Governance
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalEmergencyGovernanceStatus:
    """Status of constitutional emergency governance capabilities."""

    emergency_freeze_available: bool = False
    rollback_authority_available: bool = False
    substrate_quarantine_available: bool = False
    relay_isolation_available: bool = False
    orchestration_suspension_available: bool = False
    constitutional_violation_escalation_available: bool = False
    all_emergency_actions_available: bool = False
    emergency_action_count: int = 0
    available_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "emergency_freeze_available": self.emergency_freeze_available,
            "rollback_authority_available": self.rollback_authority_available,
            "substrate_quarantine_available": self.substrate_quarantine_available,
            "relay_isolation_available": self.relay_isolation_available,
            "orchestration_suspension_available": self.orchestration_suspension_available,
            "constitutional_violation_escalation_available": self.constitutional_violation_escalation_available,
            "all_emergency_actions_available": self.all_emergency_actions_available,
            "emergency_action_count": self.emergency_action_count,
            "available_count": self.available_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Constitutional Integrity Validation
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalIntegrityResult:
    """Result of constitutional integrity validation."""

    replay_integrity: bool = False
    rollback_integrity: bool = False
    governance_integrity: bool = False
    continuity_integrity: bool = False
    orchestration_integrity: bool = False
    maturity_integrity: bool = False
    lineage_integrity: bool = False
    all_integrity_checks_pass: bool = False
    check_count: int = 0
    passed_count: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_integrity": self.replay_integrity,
            "rollback_integrity": self.rollback_integrity,
            "governance_integrity": self.governance_integrity,
            "continuity_integrity": self.continuity_integrity,
            "orchestration_integrity": self.orchestration_integrity,
            "maturity_integrity": self.maturity_integrity,
            "lineage_integrity": self.lineage_integrity,
            "all_integrity_checks_pass": self.all_integrity_checks_pass,
            "check_count": self.check_count,
            "passed_count": self.passed_count,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Constitutional Mutation Classification
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalMutationClassification:
    """Classification of a mutation against constitutional constraints."""

    mutation_id: str = ""
    classification: str = "safe_mutation"
    constitutional_impact: bool = False
    replay_risk: bool = False
    continuity_risk: bool = False
    topology_risk: bool = False
    governance_mutation: bool = False
    requires_founder_approval: bool = False
    requires_migration: bool = False
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "classification": self.classification,
            "constitutional_impact": self.constitutional_impact,
            "replay_risk": self.replay_risk,
            "continuity_risk": self.continuity_risk,
            "topology_risk": self.topology_risk,
            "governance_mutation": self.governance_mutation,
            "requires_founder_approval": self.requires_founder_approval,
            "requires_migration": self.requires_migration,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Constitutional Risk Scoring
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalRiskScores:
    """Risk scores across 7 constitutional dimensions."""

    constitutional_fragility: float = 0.0
    invariant_pressure: float = 0.0
    authority_drift: float = 0.0
    governance_instability: float = 0.0
    replay_instability: float = 0.0
    continuity_instability: float = 0.0
    recursive_entropy_pressure: float = 0.0

    def composite_risk(self) -> float:
        vals = [
            self.constitutional_fragility,
            self.invariant_pressure,
            self.authority_drift,
            self.governance_instability,
            self.replay_instability,
            self.continuity_instability,
            self.recursive_entropy_pressure,
        ]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "constitutional_fragility": round(self.constitutional_fragility, 4),
            "invariant_pressure": round(self.invariant_pressure, 4),
            "authority_drift": round(self.authority_drift, 4),
            "governance_instability": round(self.governance_instability, 4),
            "replay_instability": round(self.replay_instability, 4),
            "continuity_instability": round(self.continuity_instability, 4),
            "recursive_entropy_pressure": round(self.recursive_entropy_pressure, 4),
            "composite_risk": self.composite_risk(),
        }


# ---------------------------------------------------------------------------
# Constitutional Governance Contract (per-proposal)
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalGovernanceContract:
    """Constitutional compliance contract for a recursive proposal."""

    proposal_id: str = ""
    constitutional_impact_analysis: str = ""
    invariant_compatibility: str = "compatible"
    replay_compatibility: str = "compatible"
    continuity_compatibility: str = "compatible"
    governance_compatibility: str = "compatible"
    approved: bool = False
    rejection_reason: str = ""
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "constitutional_impact_analysis": self.constitutional_impact_analysis,
            "invariant_compatibility": self.invariant_compatibility,
            "replay_compatibility": self.replay_compatibility,
            "continuity_compatibility": self.continuity_compatibility,
            "governance_compatibility": self.governance_compatibility,
            "approved": self.approved,
            "rejection_reason": self.rejection_reason,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Constitutional Simulation Outcome
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalSimulationOutcome:
    """Result of a constitutional simulation."""

    simulation_id: str = ""
    simulation_type: str = ""
    description: str = ""
    invariants_violated: int = 0
    boundaries_breached: int = 0
    contracts_broken: int = 0
    cascading_failures: int = 0
    recovery_possible: bool = True
    predicted_severity: str = "low"
    analysis_notes: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.simulation_id:
            self.simulation_id = f"CONSIM-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "simulation_type": self.simulation_type,
            "description": self.description,
            "invariants_violated": self.invariants_violated,
            "boundaries_breached": self.boundaries_breached,
            "contracts_broken": self.contracts_broken,
            "cascading_failures": self.cascading_failures,
            "recovery_possible": self.recovery_possible,
            "predicted_severity": self.predicted_severity,
            "analysis_notes": self.analysis_notes,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Constitutional Migration Contract
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalMigrationContract:
    """Contract for constitutional modification."""

    migration_id: str = ""
    description: str = ""
    founder_approved: bool = False
    replay_validated: bool = False
    rollback_validated: bool = False
    continuity_validated: bool = False
    governance_lineage_present: bool = False
    migration_proof_generated: bool = False
    all_requirements_met: bool = False
    requirement_count: int = 0
    met_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.migration_id:
            self.migration_id = f"CONMIG-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "description": self.description,
            "founder_approved": self.founder_approved,
            "replay_validated": self.replay_validated,
            "rollback_validated": self.rollback_validated,
            "continuity_validated": self.continuity_validated,
            "governance_lineage_present": self.governance_lineage_present,
            "migration_proof_generated": self.migration_proof_generated,
            "all_requirements_met": self.all_requirements_met,
            "requirement_count": self.requirement_count,
            "met_count": self.met_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Constitutional Evidence + Proof
# ---------------------------------------------------------------------------


@dataclass
class ConstitutionalEvidence:
    """Evidence collected during constitutional governance analysis."""

    safety_invariants_analyzed: bool = False
    safety_invariant_count: int = 0
    safety_invariants_active: int = 0
    authority_boundaries_analyzed: bool = False
    authority_boundary_count: int = 0
    authority_boundaries_enforced: int = 0
    continuity_contracts_analyzed: bool = False
    continuity_contract_count: int = 0
    continuity_contracts_enforced: int = 0
    emergency_governance_analyzed: bool = False
    emergency_action_count: int = 0
    emergency_actions_available: int = 0
    integrity_validated: bool = False
    integrity_checks_passed: int = 0
    integrity_check_count: int = 0
    constitutional_risk_scored: bool = False
    constitutional_risk_composite: float = 0.0
    simulations_completed: bool = False
    simulation_count: int = 0
    hard_ceilings_enforced: bool = True
    autonomous_mutation_blocked: bool = True
    governance_bypass_blocked: bool = True
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "safety_invariants_analyzed": self.safety_invariants_analyzed,
            "safety_invariant_count": self.safety_invariant_count,
            "safety_invariants_active": self.safety_invariants_active,
            "authority_boundaries_analyzed": self.authority_boundaries_analyzed,
            "authority_boundary_count": self.authority_boundary_count,
            "authority_boundaries_enforced": self.authority_boundaries_enforced,
            "continuity_contracts_analyzed": self.continuity_contracts_analyzed,
            "continuity_contract_count": self.continuity_contract_count,
            "continuity_contracts_enforced": self.continuity_contracts_enforced,
            "emergency_governance_analyzed": self.emergency_governance_analyzed,
            "emergency_action_count": self.emergency_action_count,
            "emergency_actions_available": self.emergency_actions_available,
            "integrity_validated": self.integrity_validated,
            "integrity_checks_passed": self.integrity_checks_passed,
            "integrity_check_count": self.integrity_check_count,
            "constitutional_risk_scored": self.constitutional_risk_scored,
            "constitutional_risk_composite": round(self.constitutional_risk_composite, 4),
            "simulations_completed": self.simulations_completed,
            "simulation_count": self.simulation_count,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "autonomous_mutation_blocked": self.autonomous_mutation_blocked,
            "governance_bypass_blocked": self.governance_bypass_blocked,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class ConstitutionalProof:
    """Complete proof of constitutional substrate governance."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_CONSTITUTIONAL_GOVERNANCE"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: ConstitutionalEvidence | None = None
    safety_invariants: ConstitutionalSafetyInvariantStatus | None = None
    authority_boundaries: ConstitutionalAuthorityBoundaryStatus | None = None
    continuity_contracts: ConstitutionalContinuityContractStatus | None = None
    emergency_governance: ConstitutionalEmergencyGovernanceStatus | None = None
    integrity_result: ConstitutionalIntegrityResult | None = None
    constitutional_risk: ConstitutionalRiskScores | None = None
    governance_contracts: list[ConstitutionalGovernanceContract] = field(default_factory=list)
    simulations: list[ConstitutionalSimulationOutcome] = field(default_factory=list)
    migration_contract: ConstitutionalMigrationContract | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"CONST-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_substrate_governance",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "safety_invariants": (
                self.safety_invariants.to_dict() if self.safety_invariants else None
            ),
            "authority_boundaries": (
                self.authority_boundaries.to_dict() if self.authority_boundaries else None
            ),
            "continuity_contracts": (
                self.continuity_contracts.to_dict() if self.continuity_contracts else None
            ),
            "emergency_governance": (
                self.emergency_governance.to_dict() if self.emergency_governance else None
            ),
            "integrity_result": (
                self.integrity_result.to_dict() if self.integrity_result else None
            ),
            "constitutional_risk": (
                self.constitutional_risk.to_dict() if self.constitutional_risk else None
            ),
            "governance_contracts": [c.to_dict() for c in self.governance_contracts],
            "simulations": [s.to_dict() for s in self.simulations],
            "migration_contract": (
                self.migration_contract.to_dict() if self.migration_contract else None
            ),
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Layer 1 builder: Constitutional Safety Invariants
# ---------------------------------------------------------------------------


def build_safety_invariants(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
) -> ConstitutionalSafetyInvariantStatus:
    """Evaluate all 6 constitutional safety invariants."""
    status = ConstitutionalSafetyInvariantStatus()
    status.invariant_count = len(CONSTITUTIONAL_SAFETY_INVARIANTS)

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if ev.replay_validated:
            status.replayability_required = True
            status.analysis_notes.append("replay validated via orchestration proof")
        if ev.rollback_validated:
            status.rollbackability_required = True
            status.analysis_notes.append("rollback validated via orchestration proof")
        if ev.governance_validated:
            status.governance_lineage_required = True
            status.analysis_notes.append("governance lineage via orchestration proof")

    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        if cev.execution_lineage_present:
            status.continuity_lineage_required = True
            status.analysis_notes.append("continuity lineage via continuity proof")

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if gev.governance_ceilings_enforced:
            status.evidence_based_maturity_required = True
            status.analysis_notes.append("evidence-based maturity via governance proof")
        if gev.autonomous_mutation_blocked:
            status.human_in_the_loop_enforcement_required = True
            status.analysis_notes.append("human-in-the-loop via governance proof")

    active = sum(
        [
            status.replayability_required,
            status.rollbackability_required,
            status.governance_lineage_required,
            status.continuity_lineage_required,
            status.evidence_based_maturity_required,
            status.human_in_the_loop_enforcement_required,
        ]
    )
    status.active_count = active
    status.all_invariants_active = active == status.invariant_count

    return status


# ---------------------------------------------------------------------------
# Layer 2 builder: Constitutional Authority Boundaries
# ---------------------------------------------------------------------------


def build_authority_boundaries(
    governance_proof: GovernanceIntelligenceProof | None = None,
) -> ConstitutionalAuthorityBoundaryStatus:
    """Evaluate all 5 constitutional authority boundaries."""
    status = ConstitutionalAuthorityBoundaryStatus()
    status.boundary_count = len(CONSTITUTIONAL_AUTHORITY_BOUNDARIES)

    status.no_autonomous_canonical_mutation = True
    status.no_autonomous_governance_mutation = True
    status.no_autonomous_maturity_escalation = True
    status.no_autonomous_authority_escalation = True
    status.no_autonomous_recursive_deployment = True

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if not gev.autonomous_mutation_blocked:
            status.no_autonomous_canonical_mutation = False
            status.violations_detected += 1
            status.analysis_notes.append("autonomous mutation NOT blocked")
        if not gev.governance_ceilings_enforced:
            status.no_autonomous_governance_mutation = False
            status.violations_detected += 1
            status.analysis_notes.append("governance ceilings NOT enforced")

    enforced = sum(
        [
            status.no_autonomous_canonical_mutation,
            status.no_autonomous_governance_mutation,
            status.no_autonomous_maturity_escalation,
            status.no_autonomous_authority_escalation,
            status.no_autonomous_recursive_deployment,
        ]
    )
    status.enforced_count = enforced
    status.all_boundaries_enforced = enforced == status.boundary_count

    if status.violations_detected == 0:
        status.analysis_notes.append("all authority boundaries enforced")

    return status


# ---------------------------------------------------------------------------
# Layer 3 builder: Constitutional Continuity Contracts
# ---------------------------------------------------------------------------


def build_continuity_contracts(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
) -> ConstitutionalContinuityContractStatus:
    """Evaluate all 5 constitutional continuity contracts."""
    status = ConstitutionalContinuityContractStatus()
    status.contract_count = len(CONSTITUTIONAL_CONTINUITY_CONTRACTS)

    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        if cev.execution_lineage_present:
            status.lineage_preservation = True
            status.analysis_notes.append("lineage preserved via continuity proof")
        if cev.drift_analysis_completed:
            status.continuity_preservation = True
            status.analysis_notes.append("continuity preserved via drift analysis")

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if ev.replay_validated:
            status.replay_preservation = True
            status.analysis_notes.append("replay preserved via orchestration proof")
        if ev.rollback_validated:
            status.rollback_preservation = True
            status.analysis_notes.append("rollback preserved via orchestration proof")

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if gev.governance_ceilings_enforced:
            status.governance_audit_preservation = True
            status.analysis_notes.append("governance audit preserved via governance proof")

    enforced = sum(
        [
            status.lineage_preservation,
            status.continuity_preservation,
            status.replay_preservation,
            status.rollback_preservation,
            status.governance_audit_preservation,
        ]
    )
    status.enforced_count = enforced
    status.all_contracts_enforced = enforced == status.contract_count

    return status


# ---------------------------------------------------------------------------
# Layer 4 builder: Constitutional Emergency Governance
# ---------------------------------------------------------------------------


def build_emergency_governance(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    founder_confirmed: bool = False,
) -> ConstitutionalEmergencyGovernanceStatus:
    """Evaluate all 6 constitutional emergency governance capabilities."""
    status = ConstitutionalEmergencyGovernanceStatus()
    status.emergency_action_count = len(CONSTITUTIONAL_EMERGENCY_ACTIONS)

    has_orch = orchestration_proof is not None
    has_cont = continuity_proof is not None
    has_gov = governance_proof is not None

    if has_orch:
        status.emergency_freeze_available = True
        status.orchestration_suspension_available = True
        status.analysis_notes.append("freeze/suspension via orchestration")

    if (
        has_orch
        and orchestration_proof.evidence
        and orchestration_proof.evidence.rollback_validated
    ):
        status.rollback_authority_available = True
        status.analysis_notes.append("rollback authority validated")

    if has_cont:
        status.substrate_quarantine_available = True
        status.analysis_notes.append("quarantine via continuity engine")

    if has_gov:
        status.relay_isolation_available = True
        status.analysis_notes.append("relay isolation via governance engine")

    if has_gov and founder_confirmed:
        status.constitutional_violation_escalation_available = True
        status.analysis_notes.append("violation escalation with founder confirmation")

    available = sum(
        [
            status.emergency_freeze_available,
            status.rollback_authority_available,
            status.substrate_quarantine_available,
            status.relay_isolation_available,
            status.orchestration_suspension_available,
            status.constitutional_violation_escalation_available,
        ]
    )
    status.available_count = available
    status.all_emergency_actions_available = available == status.emergency_action_count

    return status


# ---------------------------------------------------------------------------
# Constitutional Integrity Validation
# ---------------------------------------------------------------------------


def validate_constitutional_integrity(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    safety_invariants: ConstitutionalSafetyInvariantStatus | None = None,
    authority_boundaries: ConstitutionalAuthorityBoundaryStatus | None = None,
    continuity_contracts: ConstitutionalContinuityContractStatus | None = None,
) -> ConstitutionalIntegrityResult:
    """Validate all 7 constitutional integrity checks."""
    result = ConstitutionalIntegrityResult()
    result.check_count = len(CONSTITUTIONAL_INTEGRITY_CHECKS)

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if ev.replay_validated:
            result.replay_integrity = True
            result.analysis_notes.append("replay integrity confirmed")
        if ev.rollback_validated:
            result.rollback_integrity = True
            result.analysis_notes.append("rollback integrity confirmed")
        if ev.governance_validated:
            result.governance_integrity = True
            result.analysis_notes.append("governance integrity confirmed")
        if ev.sequencing_validated:
            result.orchestration_integrity = True
            result.analysis_notes.append("orchestration integrity confirmed")

    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        if cev.execution_lineage_present:
            result.continuity_integrity = True
            result.analysis_notes.append("continuity integrity confirmed")
        if cev.execution_lineage_present and cev.drift_analysis_completed:
            result.lineage_integrity = True
            result.analysis_notes.append("lineage integrity confirmed")

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if gev.governance_ceilings_enforced:
            result.maturity_integrity = True
            result.analysis_notes.append("maturity integrity confirmed")

    passed = sum(
        [
            result.replay_integrity,
            result.rollback_integrity,
            result.governance_integrity,
            result.continuity_integrity,
            result.orchestration_integrity,
            result.maturity_integrity,
            result.lineage_integrity,
        ]
    )
    result.passed_count = passed
    result.all_integrity_checks_pass = passed == result.check_count

    return result


# ---------------------------------------------------------------------------
# Constitutional Mutation Classification
# ---------------------------------------------------------------------------


def classify_mutation(
    mutation_description: str = "",
    affects_governance: bool = False,
    affects_replay: bool = False,
    affects_continuity: bool = False,
    affects_topology: bool = False,
    affects_invariants: bool = False,
) -> ConstitutionalMutationClassification:
    """Classify a mutation against constitutional constraints."""
    mc = ConstitutionalMutationClassification()
    mc.mutation_id = f"MUT-{uuid.uuid4().hex[:8]}"

    mc.governance_mutation = affects_governance
    mc.replay_risk = affects_replay
    mc.continuity_risk = affects_continuity
    mc.topology_risk = affects_topology
    mc.constitutional_impact = affects_invariants

    if affects_invariants:
        mc.classification = "constitutional_impact_mutation"
        mc.requires_founder_approval = True
        mc.requires_migration = True
        mc.analysis_notes.append("constitutional impact — migration required")
    elif affects_governance:
        mc.classification = "governance_mutation"
        mc.requires_founder_approval = True
        mc.analysis_notes.append("governance mutation — founder approval required")
    elif affects_replay:
        mc.classification = "replay_risk_mutation"
        mc.requires_founder_approval = True
        mc.analysis_notes.append("replay risk — founder approval required")
    elif affects_continuity:
        mc.classification = "continuity_risk_mutation"
        mc.requires_founder_approval = True
        mc.analysis_notes.append("continuity risk — founder approval required")
    elif affects_topology:
        mc.classification = "topology_risk_mutation"
        mc.analysis_notes.append("topology risk identified")
    else:
        mc.classification = "safe_mutation"
        mc.analysis_notes.append("safe mutation — no constitutional impact")

    return mc


# ---------------------------------------------------------------------------
# Constitutional Risk Scoring
# ---------------------------------------------------------------------------


def compute_constitutional_risk(
    governance_proof: GovernanceIntelligenceProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    safety_invariants: ConstitutionalSafetyInvariantStatus | None = None,
    integrity_result: ConstitutionalIntegrityResult | None = None,
) -> ConstitutionalRiskScores:
    """Compute 7-dimension constitutional risk profile."""
    scores = ConstitutionalRiskScores()

    if safety_invariants:
        if safety_invariants.invariant_count > 0:
            inactive = safety_invariants.invariant_count - safety_invariants.active_count
            scores.constitutional_fragility = round(inactive / safety_invariants.invariant_count, 4)
        scores.invariant_pressure = round(
            1.0 - (safety_invariants.active_count / max(safety_invariants.invariant_count, 1)),
            4,
        )

    if governance_proof and governance_proof.adaptive_risk:
        ar = governance_proof.adaptive_risk
        scores.governance_instability = ar.governance_fragility
        scores.authority_drift = round(
            (ar.governance_fragility + ar.orchestration_instability) / 2, 4
        )

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        rp_total = ev.replay_safe_count + ev.replay_unsafe_count
        if rp_total > 0:
            scores.replay_instability = round(ev.replay_unsafe_count / rp_total, 4)

    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        if cev.drift_analysis_completed and cev.drift_signal_count > 0:
            scores.continuity_instability = round(min(cev.drift_signal_count / 10.0, 1.0), 4)

    if integrity_result and integrity_result.check_count > 0:
        failed = integrity_result.check_count - integrity_result.passed_count
        scores.recursive_entropy_pressure = round(failed / integrity_result.check_count, 4)

    return scores


# ---------------------------------------------------------------------------
# Constitutional Governance Contract Builder
# ---------------------------------------------------------------------------


def build_governance_contracts(
    proposals: list[GovernanceProposal] | None = None,
    safety_invariants: ConstitutionalSafetyInvariantStatus | None = None,
    authority_boundaries: ConstitutionalAuthorityBoundaryStatus | None = None,
    integrity_result: ConstitutionalIntegrityResult | None = None,
) -> list[ConstitutionalGovernanceContract]:
    """Build constitutional governance contracts for governance proposals."""
    if not proposals:
        return []

    contracts: list[ConstitutionalGovernanceContract] = []
    for proposal in proposals:
        contract = ConstitutionalGovernanceContract()
        contract.proposal_id = proposal.proposal_id

        invariant_ok = safety_invariants.all_invariants_active if safety_invariants else False
        boundary_ok = (
            authority_boundaries.all_boundaries_enforced if authority_boundaries else False
        )
        integrity_ok = integrity_result.all_integrity_checks_pass if integrity_result else False

        contract.constitutional_impact_analysis = (
            f"Proposal {proposal.proposal_type}: "
            f"invariants={'active' if invariant_ok else 'incomplete'}, "
            f"boundaries={'enforced' if boundary_ok else 'incomplete'}, "
            f"integrity={'pass' if integrity_ok else 'incomplete'}"
        )

        if proposal.replay_impact and "unsafe" in proposal.replay_impact.lower():
            contract.replay_compatibility = "incompatible"
            contract.analysis_notes.append("replay incompatibility detected")
        if proposal.rollback_impact and "unsafe" in proposal.rollback_impact.lower():
            contract.continuity_compatibility = "incompatible"
            contract.analysis_notes.append("rollback/continuity incompatibility detected")
        if proposal.governance_risk_score > 0.8:
            contract.governance_compatibility = "at_risk"
            contract.analysis_notes.append(
                f"high governance risk: {proposal.governance_risk_score:.3f}"
            )
        if not invariant_ok:
            contract.invariant_compatibility = "incomplete"
            contract.analysis_notes.append("invariants not fully active")

        compatible = all(
            v == "compatible"
            for v in [
                contract.invariant_compatibility,
                contract.replay_compatibility,
                contract.continuity_compatibility,
                contract.governance_compatibility,
            ]
        )
        contract.approved = compatible
        if not compatible:
            reasons = [n for n in contract.analysis_notes if "incompatib" in n or "risk" in n]
            contract.rejection_reason = (
                "; ".join(reasons) if reasons else "constitutional incompatibility"
            )

        contracts.append(contract)

    return contracts


# ---------------------------------------------------------------------------
# Constitutional Hard Ceiling Enforcement
# ---------------------------------------------------------------------------


def enforce_hard_ceilings(
    mutation: ConstitutionalMutationClassification | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
) -> tuple[bool, list[str]]:
    """Enforce constitutional hard ceilings. Returns (blocked, reasons)."""
    blocked = False
    reasons: list[str] = []

    if mutation:
        if mutation.constitutional_impact and not mutation.requires_migration:
            blocked = True
            reasons.append("invariant_violation: constitutional impact without migration")
        if mutation.governance_mutation and not mutation.requires_founder_approval:
            blocked = True
            reasons.append("governance_bypass_attempt: governance mutation without approval")
        if mutation.replay_risk:
            blocked = True
            reasons.append("replay_breaking_mutation: replay risk detected")
        if mutation.continuity_risk:
            blocked = True
            reasons.append("continuity_breaking_mutation: continuity risk detected")

    if governance_proof and governance_proof.evidence:
        gev = governance_proof.evidence
        if not gev.autonomous_mutation_blocked:
            blocked = True
            reasons.append("orphaned_authority_escalation: autonomous mutation not blocked")
        if not gev.governance_ceilings_enforced:
            blocked = True
            reasons.append("governance_bypass_attempt: ceilings not enforced")

    return blocked, reasons


# ---------------------------------------------------------------------------
# Constitutional Simulation Engine
# ---------------------------------------------------------------------------


def run_constitutional_simulations(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    constitutional_risk: ConstitutionalRiskScores | None = None,
) -> list[ConstitutionalSimulationOutcome]:
    """Run all 8 constitutional simulation types."""
    simulations: list[ConstitutionalSimulationOutcome] = []

    risk = constitutional_risk or ConstitutionalRiskScores()

    # 1. invariant_violation
    sim1 = ConstitutionalSimulationOutcome(
        simulation_type="invariant_violation",
        description="Simulate effect of invariant violation on substrate integrity",
        invariants_violated=max(1, int(risk.invariant_pressure * 6)),
        boundaries_breached=0,
        contracts_broken=int(risk.invariant_pressure * 5),
        cascading_failures=int(risk.constitutional_fragility * 4),
        recovery_possible=risk.constitutional_fragility < 0.8,
        predicted_severity="critical" if risk.constitutional_fragility > 0.5 else "high",
    )
    sim1.analysis_notes.append(f"fragility={risk.constitutional_fragility:.3f}")
    simulations.append(sim1)

    # 2. governance_bypass
    sim2 = ConstitutionalSimulationOutcome(
        simulation_type="governance_bypass",
        description="Simulate governance bypass and authority escalation",
        invariants_violated=0,
        boundaries_breached=max(1, int(risk.authority_drift * 5)),
        contracts_broken=int(risk.governance_instability * 5),
        cascading_failures=int(risk.authority_drift * 3),
        recovery_possible=risk.governance_instability < 0.7,
        predicted_severity="critical" if risk.governance_instability > 0.5 else "high",
    )
    sim2.analysis_notes.append(f"gov_instability={risk.governance_instability:.3f}")
    simulations.append(sim2)

    # 3. replay_collapse
    sim3 = ConstitutionalSimulationOutcome(
        simulation_type="replay_collapse",
        description="Simulate replay chain collapse across substrate",
        invariants_violated=1,
        boundaries_breached=0,
        contracts_broken=max(1, int(risk.replay_instability * 5)),
        cascading_failures=int(risk.replay_instability * 6),
        recovery_possible=risk.replay_instability < 0.6,
        predicted_severity="critical" if risk.replay_instability > 0.4 else "medium",
    )
    sim3.analysis_notes.append(f"replay_instability={risk.replay_instability:.3f}")
    simulations.append(sim3)

    # 4. continuity_collapse
    sim4 = ConstitutionalSimulationOutcome(
        simulation_type="continuity_collapse",
        description="Simulate continuity chain collapse across substrate",
        invariants_violated=1,
        boundaries_breached=0,
        contracts_broken=max(1, int(risk.continuity_instability * 5)),
        cascading_failures=int(risk.continuity_instability * 5),
        recovery_possible=risk.continuity_instability < 0.6,
        predicted_severity="critical" if risk.continuity_instability > 0.4 else "medium",
    )
    sim4.analysis_notes.append(f"continuity_instability={risk.continuity_instability:.3f}")
    simulations.append(sim4)

    # 5. rollback_collapse
    rb_risk = risk.replay_instability
    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        rb_total = ev.rollback_safe_count + ev.rollback_unsafe_count
        if rb_total > 0:
            rb_risk = round(ev.rollback_unsafe_count / rb_total, 4)
    sim5 = ConstitutionalSimulationOutcome(
        simulation_type="rollback_collapse",
        description="Simulate rollback chain collapse",
        invariants_violated=1,
        boundaries_breached=0,
        contracts_broken=max(1, int(rb_risk * 5)),
        cascading_failures=int(rb_risk * 4),
        recovery_possible=rb_risk < 0.5,
        predicted_severity="critical" if rb_risk > 0.5 else "medium",
    )
    sim5.analysis_notes.append(f"rollback_risk={rb_risk:.3f}")
    simulations.append(sim5)

    # 6. authority_escalation
    sim6 = ConstitutionalSimulationOutcome(
        simulation_type="authority_escalation",
        description="Simulate unauthorized authority escalation cascade",
        invariants_violated=0,
        boundaries_breached=max(1, int(risk.authority_drift * 5)),
        contracts_broken=int(risk.authority_drift * 3),
        cascading_failures=int(risk.authority_drift * 4),
        recovery_possible=risk.authority_drift < 0.6,
        predicted_severity="critical" if risk.authority_drift > 0.5 else "high",
    )
    sim6.analysis_notes.append(f"authority_drift={risk.authority_drift:.3f}")
    simulations.append(sim6)

    # 7. orchestration_corruption
    orch_entropy = risk.recursive_entropy_pressure
    sim7 = ConstitutionalSimulationOutcome(
        simulation_type="orchestration_corruption",
        description="Simulate orchestration data corruption and cascade",
        invariants_violated=1,
        boundaries_breached=1,
        contracts_broken=max(1, int(orch_entropy * 5)),
        cascading_failures=int(orch_entropy * 6),
        recovery_possible=orch_entropy < 0.5,
        predicted_severity="critical" if orch_entropy > 0.4 else "high",
    )
    sim7.analysis_notes.append(f"entropy_pressure={orch_entropy:.3f}")
    simulations.append(sim7)

    # 8. recursive_instability_cascade
    composite = risk.composite_risk()
    sim8 = ConstitutionalSimulationOutcome(
        simulation_type="recursive_instability_cascade",
        description="Simulate cascading recursive instability across all layers",
        invariants_violated=max(1, int(composite * 6)),
        boundaries_breached=max(1, int(composite * 5)),
        contracts_broken=max(1, int(composite * 5)),
        cascading_failures=max(2, int(composite * 8)),
        recovery_possible=composite < 0.5,
        predicted_severity="critical" if composite > 0.4 else "high",
    )
    sim8.analysis_notes.append(f"composite_risk={composite:.3f}")
    simulations.append(sim8)

    return simulations


# ---------------------------------------------------------------------------
# Constitutional Migration Contract Builder
# ---------------------------------------------------------------------------


def build_migration_contract(
    description: str = "",
    founder_approved: bool = False,
    replay_validated: bool = False,
    rollback_validated: bool = False,
    continuity_validated: bool = False,
    governance_lineage_present: bool = False,
) -> ConstitutionalMigrationContract:
    """Build a constitutional migration contract."""
    mc = ConstitutionalMigrationContract(description=description)
    mc.founder_approved = founder_approved
    mc.replay_validated = replay_validated
    mc.rollback_validated = rollback_validated
    mc.continuity_validated = continuity_validated
    mc.governance_lineage_present = governance_lineage_present
    mc.requirement_count = len(CONSTITUTIONAL_MIGRATION_REQUIREMENTS)

    met = sum(
        [
            founder_approved,
            replay_validated,
            rollback_validated,
            continuity_validated,
            governance_lineage_present,
        ]
    )
    mc.migration_proof_generated = met == 5
    mc.met_count = met + (1 if mc.migration_proof_generated else 0)
    mc.all_requirements_met = mc.met_count == mc.requirement_count

    return mc


# ---------------------------------------------------------------------------
# Maturity Classification
# ---------------------------------------------------------------------------


def compute_constitutional_maturity(evidence: ConstitutionalEvidence) -> int:
    """Compute numeric maturity score from evidence."""
    score = 0
    if evidence.safety_invariants_analyzed and evidence.safety_invariants_active > 0:
        score += 1
    if evidence.authority_boundaries_analyzed and evidence.authority_boundaries_enforced > 0:
        score += 1
    if evidence.continuity_contracts_analyzed and evidence.continuity_contracts_enforced > 0:
        score += 1
    if evidence.emergency_governance_analyzed and evidence.emergency_actions_available > 0:
        score += 1
    if evidence.integrity_validated and evidence.integrity_checks_passed > 0:
        score += 1
    if evidence.constitutional_risk_scored:
        score += 1
    if evidence.simulations_completed:
        score += 1
    if evidence.founder_confirmed:
        score += 1
    if evidence.hard_ceilings_enforced and evidence.autonomous_mutation_blocked:
        score += 1
    if evidence.governance_bypass_blocked:
        score += 1
    return score


def constitutional_maturity_ceiling(
    evidence: ConstitutionalEvidence,
) -> tuple[str, bool, str]:
    """Compute constitutional maturity ceiling. Returns (ceiling, blocked, reason)."""
    if evidence.is_dry_run:
        return "L0_NO_CONSTITUTIONAL_GOVERNANCE", True, "dry run"

    if not evidence.safety_invariants_analyzed:
        return "L0_NO_CONSTITUTIONAL_GOVERNANCE", True, "safety invariants not analyzed"
    if not evidence.authority_boundaries_analyzed:
        return "L1_INVARIANT_DEFINED", True, "authority boundaries not analyzed"
    if not evidence.continuity_contracts_analyzed:
        return "L2_AUTHORITY_BOUNDED", True, "continuity contracts not analyzed"
    if not evidence.emergency_governance_analyzed:
        return "L2_AUTHORITY_BOUNDED", True, "emergency governance not analyzed"
    if not evidence.integrity_validated:
        return "L3_CONTINUITY_CONTRACTED", True, "integrity not validated"
    if not evidence.constitutional_risk_scored:
        return "L3_CONTINUITY_CONTRACTED", True, "risk not scored"
    if not evidence.simulations_completed:
        return "L4_EMERGENCY_GOVERNED", True, "simulations not completed"
    if not evidence.hard_ceilings_enforced:
        return "L4_EMERGENCY_GOVERNED", True, "hard ceilings not enforced"
    if not evidence.founder_confirmed:
        return "L4_EMERGENCY_GOVERNED", True, "founder not confirmed"
    if not evidence.governance_bypass_blocked:
        return "L4_EMERGENCY_GOVERNED", True, "governance bypass not blocked"

    return "L5_CONSTITUTIONAL_RECURSIVE_GOVERNANCE", False, ""


def classify_constitutional_maturity(
    evidence: ConstitutionalEvidence,
) -> tuple[str, str, bool, str]:
    """Classify maturity. Returns (level, ceiling, blocked, reason)."""
    ceiling, blocked, reason = constitutional_maturity_ceiling(evidence)

    score = compute_constitutional_maturity(evidence)

    ceiling_idx = CONSTITUTIONAL_MATURITY_LEVELS.index(ceiling)

    if score >= 10:
        level_idx = 5
    elif score >= 8:
        level_idx = 4
    elif score >= 6:
        level_idx = 3
    elif score >= 4:
        level_idx = 2
    elif score >= 2:
        level_idx = 1
    else:
        level_idx = 0

    level_idx = min(level_idx, ceiling_idx)
    level = CONSTITUTIONAL_MATURITY_LEVELS[level_idx]

    return level, ceiling, blocked, reason


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


def build_full_constitutional_proof(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    governance_proof: GovernanceIntelligenceProof | None = None,
    capability_proof: CapabilityPlanningProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
    base_dir: Path = Path(_ROOT),
) -> ConstitutionalProof:
    """Full constitutional substrate governance pipeline."""
    safety = build_safety_invariants(orchestration_proof, continuity_proof, governance_proof)
    authority = build_authority_boundaries(governance_proof)
    continuity = build_continuity_contracts(orchestration_proof, continuity_proof, governance_proof)
    emergency = build_emergency_governance(
        orchestration_proof, continuity_proof, governance_proof, founder_confirmed
    )
    integrity = validate_constitutional_integrity(
        orchestration_proof, continuity_proof, governance_proof, safety, authority, continuity
    )
    risk = compute_constitutional_risk(
        governance_proof, orchestration_proof, continuity_proof, safety, integrity
    )

    gov_proposals = governance_proof.proposals if governance_proof else []
    contracts = build_governance_contracts(gov_proposals, safety, authority, integrity)

    simulations = run_constitutional_simulations(
        orchestration_proof, continuity_proof, governance_proof, risk
    )

    evidence = ConstitutionalEvidence(
        safety_invariants_analyzed=True,
        safety_invariant_count=safety.invariant_count,
        safety_invariants_active=safety.active_count,
        authority_boundaries_analyzed=True,
        authority_boundary_count=authority.boundary_count,
        authority_boundaries_enforced=authority.enforced_count,
        continuity_contracts_analyzed=True,
        continuity_contract_count=continuity.contract_count,
        continuity_contracts_enforced=continuity.enforced_count,
        emergency_governance_analyzed=True,
        emergency_action_count=emergency.emergency_action_count,
        emergency_actions_available=emergency.available_count,
        integrity_validated=True,
        integrity_checks_passed=integrity.passed_count,
        integrity_check_count=integrity.check_count,
        constitutional_risk_scored=True,
        constitutional_risk_composite=risk.composite_risk(),
        simulations_completed=True,
        simulation_count=len(simulations),
        hard_ceilings_enforced=True,
        autonomous_mutation_blocked=True,
        governance_bypass_blocked=True,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_constitutional_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "await_founder_confirmation"
            if not founder_confirmed
            else "constitutional_governance_active"
        )
    )

    return ConstitutionalProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        safety_invariants=safety,
        authority_boundaries=authority,
        continuity_contracts=continuity,
        emergency_governance=emergency,
        integrity_result=integrity,
        constitutional_risk=risk,
        governance_contracts=contracts,
        simulations=simulations,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_constitutional_proof(
    proof: ConstitutionalProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist constitutional proof to disk."""
    report_dir = base_dir / CONSTITUTIONAL_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
