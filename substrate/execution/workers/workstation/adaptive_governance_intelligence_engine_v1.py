"""Adaptive Governance Intelligence Engine v1.

Analyzes historical orchestration behavior, continuity trends, replay
outcomes, rollback outcomes, drift evolution, and governance effectiveness
to propose safer governance strategies, improved orchestration policies,
and higher-integrity recursive evolution paths.

The engine may: analyze, score, classify, propose, simulate, compare,
reason about governance evolution, track proposal lineage, evaluate
policy effectiveness.

The engine CANNOT: auto-modify governance contracts, auto-modify
authority ceilings, auto-modify maturity ceilings, auto-promote
policies, auto-deploy governance changes, rewrite governance history,
or mutate canonical structures autonomously.

All governance evolution remains founder-governed.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .governed_recursive_orchestration_engine_v1 import (
    DAG_TYPES,
    ORCHESTRATION_MATURITY_LEVELS,
    ORCHESTRATION_REPORT_DIR,
    ROLLBACK_STRATEGIES,
    SIMULATION_OUTCOMES,
    UPGRADE_BLAST_MAP,
    BlastRadius,
    OrchestrationEvidence,
    OrchestrationProof,
    RollbackPlan,
    SimulationOutcome,
    build_full_orchestration_proof,
)
from .persistent_substrate_continuity_engine_v1 import (
    CONTINUITY_GOVERNANCE_VIOLATIONS,
    CONTINUITY_MATURITY_LEVELS,
    CONTINUITY_REJECTION_TRIGGERS,
    CONTINUITY_REPORT_DIR,
    DRIFT_TYPES,
    ContinuityEvidence,
    ContinuityProof,
    DriftSignal,
    EvolutionScores,
    build_full_continuity_proof,
    detect_drift,
    replay_drift_emergence,
    replay_maturity_evolution,
    replay_orchestration_history,
)
from .recursive_capability_planning_engine_v1 import (

    CAPABILITY_MATURITY_LEVELS,
    SUBSTRATE_CAPABILITIES,
    CapabilityPlanningProof,
    build_full_capability_proof,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


GOVERNANCE_INTELLIGENCE_REPORT_DIR = Path(
    "data/runtime/workstation_relay/governance_intelligence_reports"
)


# ---------------------------------------------------------------------------
# Governance intelligence maturity levels
# ---------------------------------------------------------------------------

GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS = (
    "L0_NO_GOVERNANCE_INTELLIGENCE",
    "L1_GOVERNANCE_INTEGRITY_INTELLIGENCE",
    "L2_ORCHESTRATION_INTELLIGENCE",
    "L3_CONTINUITY_INTELLIGENCE",
    "L4_EPISTEMIC_INTELLIGENCE",
    "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE",
)

GOVERNANCE_INTELLIGENCE_MATURITY_REQUIREMENTS: dict[str, list[str]] = {
    "L0_NO_GOVERNANCE_INTELLIGENCE": [],
    "L1_GOVERNANCE_INTEGRITY_INTELLIGENCE": [
        "governance_integrity_analyzed",
        "gate_effectiveness_scored",
    ],
    "L2_ORCHESTRATION_INTELLIGENCE": [
        "governance_integrity_analyzed",
        "gate_effectiveness_scored",
        "orchestration_intelligence_analyzed",
        "sequencing_efficiency_scored",
    ],
    "L3_CONTINUITY_INTELLIGENCE": [
        "governance_integrity_analyzed",
        "gate_effectiveness_scored",
        "orchestration_intelligence_analyzed",
        "sequencing_efficiency_scored",
        "continuity_intelligence_analyzed",
        "drift_trends_analyzed",
    ],
    "L4_EPISTEMIC_INTELLIGENCE": [
        "governance_integrity_analyzed",
        "gate_effectiveness_scored",
        "orchestration_intelligence_analyzed",
        "sequencing_efficiency_scored",
        "continuity_intelligence_analyzed",
        "drift_trends_analyzed",
        "epistemic_intelligence_analyzed",
        "evidence_integrity_scored",
    ],
    "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE": [
        "governance_integrity_analyzed",
        "gate_effectiveness_scored",
        "orchestration_intelligence_analyzed",
        "sequencing_efficiency_scored",
        "continuity_intelligence_analyzed",
        "drift_trends_analyzed",
        "epistemic_intelligence_analyzed",
        "evidence_integrity_scored",
        "governance_proposals_generated",
        "adaptive_risk_scored",
        "policy_simulation_completed",
        "founder_confirmed",
    ],
}


# ---------------------------------------------------------------------------
# Governance hard ceilings (immutable constraints)
# ---------------------------------------------------------------------------

GOVERNANCE_INTELLIGENCE_HARD_CEILINGS = frozenset(
    {
        "auto_modify_governance_contracts",
        "auto_modify_authority_ceilings",
        "auto_modify_maturity_ceilings",
        "auto_promote_policies",
        "auto_deploy_governance_changes",
        "rewrite_governance_history",
    }
)


# ---------------------------------------------------------------------------
# Layer 1: Governance Integrity Intelligence
# ---------------------------------------------------------------------------


@dataclass
class GovernanceIntegrityIntelligence:
    """Layer 1 — gate effectiveness, authority boundaries, replay/rollback
    contract stability, maturity ceiling effectiveness."""

    gate_effectiveness: float = 0.0
    authority_boundary_violations: int = 0
    replay_contract_stability: float = 0.0
    rollback_safety_effectiveness: float = 0.0
    maturity_ceiling_effectiveness: float = 0.0
    governance_validated: bool = False
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_effectiveness": round(self.gate_effectiveness, 3),
            "authority_boundary_violations": self.authority_boundary_violations,
            "replay_contract_stability": round(self.replay_contract_stability, 3),
            "rollback_safety_effectiveness": round(self.rollback_safety_effectiveness, 3),
            "maturity_ceiling_effectiveness": round(self.maturity_ceiling_effectiveness, 3),
            "governance_validated": self.governance_validated,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 2: Orchestration Intelligence
# ---------------------------------------------------------------------------


@dataclass
class OrchestrationIntelligence:
    """Layer 2 — sequencing efficiency, blast radius minimization,
    dependency ordering quality, orchestration entropy, rollout safety."""

    sequencing_efficiency: float = 0.0
    blast_radius_minimization: float = 0.0
    dependency_ordering_quality: float = 0.0
    orchestration_entropy: float = 0.0
    rollout_safety_trend: float = 0.0
    total_simulations: int = 0
    successful_simulations: int = 0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequencing_efficiency": round(self.sequencing_efficiency, 3),
            "blast_radius_minimization": round(self.blast_radius_minimization, 3),
            "dependency_ordering_quality": round(self.dependency_ordering_quality, 3),
            "orchestration_entropy": round(self.orchestration_entropy, 3),
            "rollout_safety_trend": round(self.rollout_safety_trend, 3),
            "total_simulations": self.total_simulations,
            "successful_simulations": self.successful_simulations,
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 3: Continuity Intelligence
# ---------------------------------------------------------------------------


@dataclass
class ContinuityIntelligence:
    """Layer 3 — drift emergence trends, continuity corruption patterns,
    replay degradation, rollback instability, lineage breakage."""

    drift_emergence_trend: float = 0.0
    continuity_corruption_count: int = 0
    replay_degradation_trend: float = 0.0
    rollback_instability_trend: float = 0.0
    lineage_breakage_count: int = 0
    drift_signal_count: int = 0
    max_drift_severity: float = 0.0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_emergence_trend": round(self.drift_emergence_trend, 3),
            "continuity_corruption_count": self.continuity_corruption_count,
            "replay_degradation_trend": round(self.replay_degradation_trend, 3),
            "rollback_instability_trend": round(self.rollback_instability_trend, 3),
            "lineage_breakage_count": self.lineage_breakage_count,
            "drift_signal_count": self.drift_signal_count,
            "max_drift_severity": round(self.max_drift_severity, 3),
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Layer 4: Epistemic Intelligence
# ---------------------------------------------------------------------------


@dataclass
class EpistemicIntelligence:
    """Layer 4 — observed vs inferred divergence, simulation vs reality
    divergence, founder-confirmation reliability, maturity confidence,
    evidence integrity."""

    observed_inferred_divergence: float = 0.0
    simulation_reality_divergence: float = 0.0
    founder_confirmation_reliability: float = 0.0
    maturity_confidence_score: float = 0.0
    evidence_integrity_score: float = 0.0
    analysis_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_inferred_divergence": round(self.observed_inferred_divergence, 3),
            "simulation_reality_divergence": round(self.simulation_reality_divergence, 3),
            "founder_confirmation_reliability": round(self.founder_confirmation_reliability, 3),
            "maturity_confidence_score": round(self.maturity_confidence_score, 3),
            "evidence_integrity_score": round(self.evidence_integrity_score, 3),
            "analysis_notes": self.analysis_notes,
        }


# ---------------------------------------------------------------------------
# Governance proposal
# ---------------------------------------------------------------------------

PROPOSAL_TYPES = frozenset(
    {
        "governance_upgrade",
        "orchestration_optimization",
        "maturity_policy_refinement",
        "replay_policy_refinement",
        "rollback_policy_refinement",
        "drift_mitigation",
        "entropy_reduction",
    }
)


@dataclass
class GovernanceProposal:
    """A governance improvement proposal with evidence lineage."""

    proposal_id: str = ""
    proposal_type: str = ""
    title: str = ""
    rationale: str = ""
    evidence_lineage: list[str] = field(default_factory=list)
    replay_impact: str = ""
    rollback_impact: str = ""
    blast_radius_estimate: float = 0.0
    continuity_impact: str = ""
    governance_risk_score: float = 0.0
    confidence_score: float = 0.0
    status: str = "proposed"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proposal_id:
            self.proposal_id = f"GOVPROP-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type,
            "title": self.title,
            "rationale": self.rationale,
            "evidence_lineage": self.evidence_lineage,
            "replay_impact": self.replay_impact,
            "rollback_impact": self.rollback_impact,
            "blast_radius_estimate": round(self.blast_radius_estimate, 3),
            "continuity_impact": self.continuity_impact,
            "governance_risk_score": round(self.governance_risk_score, 3),
            "confidence_score": round(self.confidence_score, 3),
            "status": self.status,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Adaptive risk scores
# ---------------------------------------------------------------------------


@dataclass
class AdaptiveRiskScores:
    """8-dimensional adaptive risk scoring."""

    governance_fragility: float = 0.0
    orchestration_instability: float = 0.0
    replay_decay: float = 0.0
    rollback_uncertainty: float = 0.0
    topology_volatility: float = 0.0
    dependency_instability: float = 0.0
    drift_acceleration: float = 0.0
    entropy_growth: float = 0.0

    def composite_risk(self) -> float:
        weights = [0.20, 0.15, 0.10, 0.10, 0.10, 0.10, 0.15, 0.10]
        values = [
            self.governance_fragility,
            self.orchestration_instability,
            self.replay_decay,
            self.rollback_uncertainty,
            self.topology_volatility,
            self.dependency_instability,
            self.drift_acceleration,
            self.entropy_growth,
        ]
        return round(sum(w * v for w, v in zip(weights, values)), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_fragility": round(self.governance_fragility, 3),
            "orchestration_instability": round(self.orchestration_instability, 3),
            "replay_decay": round(self.replay_decay, 3),
            "rollback_uncertainty": round(self.rollback_uncertainty, 3),
            "topology_volatility": round(self.topology_volatility, 3),
            "dependency_instability": round(self.dependency_instability, 3),
            "drift_acceleration": round(self.drift_acceleration, 3),
            "entropy_growth": round(self.entropy_growth, 3),
            "composite_risk": self.composite_risk(),
        }


# ---------------------------------------------------------------------------
# Policy simulation outcome
# ---------------------------------------------------------------------------

SIMULATION_POLICY_TYPES = frozenset(
    {
        "stricter_governance",
        "relaxed_governance",
        "altered_sequencing",
        "altered_rollback_rules",
        "altered_replay_thresholds",
        "altered_maturity_ceilings",
    }
)


@dataclass
class PolicySimulationOutcome:
    """Result of a simulated policy change."""

    simulation_id: str = ""
    policy_type: str = ""
    description: str = ""
    predicted_risk_delta: float = 0.0
    predicted_maturity_impact: str = ""
    predicted_replay_impact: str = ""
    predicted_rollback_impact: str = ""
    governance_risk_score: float = 0.0
    recommendation: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.simulation_id:
            self.simulation_id = f"POLSIM-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "policy_type": self.policy_type,
            "description": self.description,
            "predicted_risk_delta": round(self.predicted_risk_delta, 3),
            "predicted_maturity_impact": self.predicted_maturity_impact,
            "predicted_replay_impact": self.predicted_replay_impact,
            "predicted_rollback_impact": self.predicted_rollback_impact,
            "governance_risk_score": round(self.governance_risk_score, 3),
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Governance learning memory
# ---------------------------------------------------------------------------


@dataclass
class GovernanceLearningMemory:
    """Persisted governance learning state."""

    proposals: list[GovernanceProposal] = field(default_factory=list)
    accepted_proposals: list[str] = field(default_factory=list)
    rejected_proposals: list[str] = field(default_factory=list)
    proposal_outcomes: list[str] = field(default_factory=list)
    governance_evolution_chain: list[str] = field(default_factory=list)
    policy_effectiveness_history: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposals": [p.to_dict() for p in self.proposals],
            "proposal_count": len(self.proposals),
            "accepted_proposals": self.accepted_proposals,
            "rejected_proposals": self.rejected_proposals,
            "proposal_outcomes": self.proposal_outcomes,
            "governance_evolution_chain": self.governance_evolution_chain,
            "policy_effectiveness_history": self.policy_effectiveness_history,
        }


# ---------------------------------------------------------------------------
# Governance intelligence evidence
# ---------------------------------------------------------------------------


@dataclass
class GovernanceIntelligenceEvidence:
    """Evidence collected during governance intelligence analysis."""

    governance_integrity_analyzed: bool = False
    gate_effectiveness_scored: bool = False
    orchestration_intelligence_analyzed: bool = False
    sequencing_efficiency_scored: bool = False
    continuity_intelligence_analyzed: bool = False
    drift_trends_analyzed: bool = False
    epistemic_intelligence_analyzed: bool = False
    evidence_integrity_scored: bool = False
    governance_proposals_generated: bool = False
    governance_proposal_count: int = 0
    adaptive_risk_scored: bool = False
    adaptive_risk_composite: float = 0.0
    policy_simulation_completed: bool = False
    policy_simulation_count: int = 0
    governance_ceilings_enforced: bool = True
    autonomous_mutation_blocked: bool = True
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_integrity_analyzed": self.governance_integrity_analyzed,
            "gate_effectiveness_scored": self.gate_effectiveness_scored,
            "orchestration_intelligence_analyzed": self.orchestration_intelligence_analyzed,
            "sequencing_efficiency_scored": self.sequencing_efficiency_scored,
            "continuity_intelligence_analyzed": self.continuity_intelligence_analyzed,
            "drift_trends_analyzed": self.drift_trends_analyzed,
            "epistemic_intelligence_analyzed": self.epistemic_intelligence_analyzed,
            "evidence_integrity_scored": self.evidence_integrity_scored,
            "governance_proposals_generated": self.governance_proposals_generated,
            "governance_proposal_count": self.governance_proposal_count,
            "adaptive_risk_scored": self.adaptive_risk_scored,
            "adaptive_risk_composite": round(self.adaptive_risk_composite, 3),
            "policy_simulation_completed": self.policy_simulation_completed,
            "policy_simulation_count": self.policy_simulation_count,
            "governance_ceilings_enforced": self.governance_ceilings_enforced,
            "autonomous_mutation_blocked": self.autonomous_mutation_blocked,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


# ---------------------------------------------------------------------------
# Governance intelligence proof
# ---------------------------------------------------------------------------


@dataclass
class GovernanceIntelligenceProof:
    """Complete proof of adaptive governance intelligence."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_GOVERNANCE_INTELLIGENCE"
    maturity_ceiling: str = "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: GovernanceIntelligenceEvidence | None = None
    governance_integrity: GovernanceIntegrityIntelligence | None = None
    orchestration_intelligence: OrchestrationIntelligence | None = None
    continuity_intelligence: ContinuityIntelligence | None = None
    epistemic_intelligence: EpistemicIntelligence | None = None
    proposals: list[GovernanceProposal] = field(default_factory=list)
    adaptive_risk: AdaptiveRiskScores | None = None
    policy_simulations: list[PolicySimulationOutcome] = field(default_factory=list)
    learning_memory: GovernanceLearningMemory | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"GOVINT-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "adaptive_governance_intelligence",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "governance_integrity": (
                self.governance_integrity.to_dict() if self.governance_integrity else None
            ),
            "orchestration_intelligence": (
                self.orchestration_intelligence.to_dict()
                if self.orchestration_intelligence
                else None
            ),
            "continuity_intelligence": (
                self.continuity_intelligence.to_dict() if self.continuity_intelligence else None
            ),
            "epistemic_intelligence": (
                self.epistemic_intelligence.to_dict() if self.epistemic_intelligence else None
            ),
            "proposals": [p.to_dict() for p in self.proposals],
            "proposal_count": len(self.proposals),
            "adaptive_risk": self.adaptive_risk.to_dict() if self.adaptive_risk else None,
            "policy_simulations": [s.to_dict() for s in self.policy_simulations],
            "policy_simulation_count": len(self.policy_simulations),
            "learning_memory": self.learning_memory.to_dict() if self.learning_memory else None,
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Layer 1 builder: Governance Integrity Intelligence
# ---------------------------------------------------------------------------


def build_governance_integrity(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> GovernanceIntegrityIntelligence:
    """Build Layer 1 — Governance Integrity Intelligence."""
    intel = GovernanceIntegrityIntelligence()

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev:
            intel.governance_validated = ev.governance_validated

            if ev.simulation_count > 0:
                intel.gate_effectiveness = ev.simulation_success_count / ev.simulation_count
                intel.analysis_notes.append(
                    f"gate effectiveness: {ev.simulation_success_count}/{ev.simulation_count}"
                )

            replay_total = ev.replay_safe_count + ev.replay_unsafe_count
            if replay_total > 0:
                intel.replay_contract_stability = ev.replay_safe_count / replay_total
                intel.analysis_notes.append(
                    f"replay stability: {ev.replay_safe_count}/{replay_total}"
                )

            rb_total = ev.rollback_safe_count + ev.rollback_unsafe_count
            if rb_total > 0:
                intel.rollback_safety_effectiveness = ev.rollback_safe_count / rb_total
                intel.analysis_notes.append(f"rollback safety: {ev.rollback_safe_count}/{rb_total}")

            if ev.governance_bottleneck_count == 0:
                intel.maturity_ceiling_effectiveness = 1.0
            else:
                intel.maturity_ceiling_effectiveness = 0.5
                intel.analysis_notes.append(f"governance bottlenecks: {ev.governance_bottleneck_count}")

    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        if cev.governance_continuity_enforced:
            intel.governance_validated = True

    return intel


# ---------------------------------------------------------------------------
# Layer 2 builder: Orchestration Intelligence
# ---------------------------------------------------------------------------


def build_orchestration_intelligence(
    orchestration_proof: OrchestrationProof | None = None,
    base_dir: Path = Path(_ROOT),
) -> OrchestrationIntelligence:
    """Build Layer 2 — Orchestration Intelligence."""
    intel = OrchestrationIntelligence()

    if orchestration_proof:
        ev = orchestration_proof.evidence
        if ev:
            intel.total_simulations = ev.simulation_count
            intel.successful_simulations = ev.simulation_success_count

            if ev.simulation_count > 0:
                intel.rollout_safety_trend = ev.simulation_success_count / ev.simulation_count
                intel.analysis_notes.append(
                    f"rollout safety: {ev.simulation_success_count}/{ev.simulation_count}"
                )

            if ev.unsafe_chains_detected > 0:
                intel.orchestration_entropy = min(1.0, ev.unsafe_chains_detected / 5.0)
                intel.analysis_notes.append(
                    f"entropy from {ev.unsafe_chains_detected} unsafe chains"
                )

        n_upgrades = len(orchestration_proof.sequenced_upgrades)
        if n_upgrades > 0:
            safe_count = sum(
                1
                for u in orchestration_proof.sequenced_upgrades
                if u not in [c.split(":")[0] for c in orchestration_proof.unsafe_chains]
            )
            intel.sequencing_efficiency = safe_count / n_upgrades
            intel.analysis_notes.append(f"sequencing efficiency: {safe_count}/{n_upgrades}")

        if orchestration_proof.blast_radii:
            max_br = max(br.risk_score for br in orchestration_proof.blast_radii)
            intel.blast_radius_minimization = max(0.0, 1.0 - max_br)
            intel.analysis_notes.append(
                f"blast radius minimization: {intel.blast_radius_minimization:.3f}"
            )

        if orchestration_proof.dags:
            dep_dag = None
            for dag in orchestration_proof.dags:
                if dag.dag_type == "dependency":
                    dep_dag = dag
                    break
            if dep_dag and dep_dag.nodes:
                intel.dependency_ordering_quality = min(
                    1.0, len(dep_dag.edges) / max(1, len(dep_dag.nodes))
                )

    orch_history = replay_orchestration_history(base_dir)
    if len(orch_history) >= 2:
        intel.analysis_notes.append(f"orchestration history depth: {len(orch_history)}")

    return intel


# ---------------------------------------------------------------------------
# Layer 3 builder: Continuity Intelligence
# ---------------------------------------------------------------------------


def build_continuity_intelligence(
    continuity_proof: ContinuityProof | None = None,
    base_dir: Path = Path(_ROOT),
) -> ContinuityIntelligence:
    """Build Layer 3 — Continuity Intelligence."""
    intel = ContinuityIntelligence()

    if continuity_proof:
        intel.drift_signal_count = len(continuity_proof.drift_signals)
        if continuity_proof.drift_signals:
            intel.max_drift_severity = max(s.severity for s in continuity_proof.drift_signals)
            intel.drift_emergence_trend = intel.max_drift_severity
            intel.analysis_notes.append(
                f"drift signals: {intel.drift_signal_count} "
                f"(max severity: {intel.max_drift_severity:.3f})"
            )

        if continuity_proof.evidence:
            cev = continuity_proof.evidence
            if not cev.replay_continuity_validated:
                intel.replay_degradation_trend = 0.8
                intel.analysis_notes.append("replay continuity not validated")
            if not cev.rollback_continuity_validated:
                intel.rollback_instability_trend = 0.8
                intel.analysis_notes.append("rollback continuity not validated")

        for entry in continuity_proof.lineage_chain:
            if not entry.replay_lineage and not entry.evolution_chain:
                intel.lineage_breakage_count += 1

    drift_history = replay_drift_emergence(base_dir)
    if drift_history:
        intel.analysis_notes.append(f"historical drift signals: {len(drift_history)}")

    return intel


# ---------------------------------------------------------------------------
# Layer 4 builder: Epistemic Intelligence
# ---------------------------------------------------------------------------


def build_epistemic_intelligence(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    founder_confirmed: bool = False,
) -> EpistemicIntelligence:
    """Build Layer 4 — Epistemic Intelligence."""
    intel = EpistemicIntelligence()

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if ev.simulation_count > 0:
            intel.simulation_reality_divergence = 1.0 - (
                ev.simulation_success_count / ev.simulation_count
            )

        if ev.founder_confirmed:
            intel.founder_confirmation_reliability = 1.0
        elif founder_confirmed:
            intel.founder_confirmation_reliability = 1.0
        else:
            intel.founder_confirmation_reliability = 0.0

    if continuity_proof and continuity_proof.epistemic_memory:
        em = continuity_proof.epistemic_memory
        total_obs = em.observed_count + em.inferred_count
        if total_obs > 0:
            intel.observed_inferred_divergence = em.inferred_count / total_obs
            intel.analysis_notes.append(
                f"observed: {em.observed_count}, inferred: {em.inferred_count}"
            )

    evidence_checks = []
    if orchestration_proof and orchestration_proof.evidence:
        evidence_checks.append(orchestration_proof.evidence.governance_validated)
        evidence_checks.append(orchestration_proof.evidence.replay_validated)
        evidence_checks.append(orchestration_proof.evidence.rollback_validated)
    if continuity_proof and continuity_proof.evidence:
        evidence_checks.append(continuity_proof.evidence.replay_continuity_validated)
        evidence_checks.append(continuity_proof.evidence.rollback_continuity_validated)
        evidence_checks.append(continuity_proof.evidence.governance_continuity_enforced)

    if evidence_checks:
        intel.evidence_integrity_score = sum(1 for c in evidence_checks if c) / len(evidence_checks)
    else:
        intel.evidence_integrity_score = 0.0

    mat_levels_present = 0
    mat_levels_total = 0
    if orchestration_proof:
        mat_levels_total += 1
        if orchestration_proof.maturity_level != "L0_SIMULATED_ORCHESTRATION":
            mat_levels_present += 1
    if continuity_proof:
        mat_levels_total += 1
        if continuity_proof.maturity_level != "L0_NO_CONTINUITY":
            mat_levels_present += 1
    if mat_levels_total > 0:
        intel.maturity_confidence_score = mat_levels_present / mat_levels_total

    return intel


# ---------------------------------------------------------------------------
# Adaptive risk scoring
# ---------------------------------------------------------------------------


def compute_adaptive_risk(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    drift_signals: list[DriftSignal] | None = None,
) -> AdaptiveRiskScores:
    """Compute 8-dimensional adaptive risk scores."""
    risk = AdaptiveRiskScores()

    if orchestration_proof and orchestration_proof.evidence:
        ev = orchestration_proof.evidence
        if not ev.governance_validated:
            risk.governance_fragility = 0.8
        elif ev.governance_bottleneck_count > 2:
            risk.governance_fragility = 0.4

        if ev.unsafe_chains_detected > 0:
            risk.orchestration_instability = min(1.0, ev.unsafe_chains_detected / 5.0)

        replay_total = ev.replay_safe_count + ev.replay_unsafe_count
        if replay_total > 0:
            risk.replay_decay = ev.replay_unsafe_count / replay_total

        rb_total = ev.rollback_safe_count + ev.rollback_unsafe_count
        if rb_total > 0:
            risk.rollback_uncertainty = ev.rollback_unsafe_count / rb_total

        if ev.max_blast_radius > 0.5:
            risk.topology_volatility = ev.max_blast_radius

    if continuity_proof and continuity_proof.evolution_scores:
        es = continuity_proof.evolution_scores
        risk.entropy_growth = es.orchestration_entropy_trend

    if drift_signals:
        max_sev = max(s.severity for s in drift_signals)
        risk.drift_acceleration = max_sev
        dep_drifts = [s for s in drift_signals if "dependency" in s.drift_type.lower()]
        if dep_drifts:
            risk.dependency_instability = max(d.severity for d in dep_drifts)

    return risk


# ---------------------------------------------------------------------------
# Governance proposal generation
# ---------------------------------------------------------------------------


def generate_governance_proposals(
    governance_integrity: GovernanceIntegrityIntelligence,
    orchestration_intel: OrchestrationIntelligence,
    continuity_intel: ContinuityIntelligence,
    epistemic_intel: EpistemicIntelligence,
    adaptive_risk: AdaptiveRiskScores,
    orchestration_proof: OrchestrationProof | None = None,
) -> list[GovernanceProposal]:
    """Generate governance improvement proposals from intelligence layers."""
    proposals: list[GovernanceProposal] = []

    if (
        governance_integrity.gate_effectiveness < 0.9
        and governance_integrity.gate_effectiveness > 0
    ):
        proposals.append(
            GovernanceProposal(
                proposal_type="governance_upgrade",
                title="Improve gate effectiveness",
                rationale=f"Gate effectiveness at {governance_integrity.gate_effectiveness:.1%}",
                evidence_lineage=governance_integrity.analysis_notes[:3],
                replay_impact="neutral",
                rollback_impact="neutral",
                blast_radius_estimate=0.1,
                continuity_impact="positive — reduces governance drift",
                governance_risk_score=0.2,
                confidence_score=governance_integrity.gate_effectiveness,
            )
        )

    if orchestration_intel.orchestration_entropy > 0.3:
        proposals.append(
            GovernanceProposal(
                proposal_type="entropy_reduction",
                title="Reduce orchestration entropy",
                rationale=f"Entropy at {orchestration_intel.orchestration_entropy:.3f}",
                evidence_lineage=orchestration_intel.analysis_notes[:3],
                replay_impact="positive — safer replay paths",
                rollback_impact="positive — fewer unsafe chains",
                blast_radius_estimate=0.2,
                continuity_impact="positive — more stable orchestration",
                governance_risk_score=0.3,
                confidence_score=0.7,
            )
        )

    if continuity_intel.drift_emergence_trend > 0.3:
        proposals.append(
            GovernanceProposal(
                proposal_type="drift_mitigation",
                title="Mitigate drift emergence",
                rationale=f"Drift trend at {continuity_intel.drift_emergence_trend:.3f}",
                evidence_lineage=continuity_intel.analysis_notes[:3],
                replay_impact="neutral",
                rollback_impact="positive — less drift-induced rollback",
                blast_radius_estimate=0.15,
                continuity_impact="positive — reduces drift acceleration",
                governance_risk_score=0.2,
                confidence_score=0.8,
            )
        )

    if continuity_intel.replay_degradation_trend > 0.5:
        proposals.append(
            GovernanceProposal(
                proposal_type="replay_policy_refinement",
                title="Strengthen replay contracts",
                rationale=f"Replay degradation at {continuity_intel.replay_degradation_trend:.3f}",
                evidence_lineage=continuity_intel.analysis_notes[:3],
                replay_impact="positive — restores replay safety",
                rollback_impact="neutral",
                blast_radius_estimate=0.1,
                continuity_impact="positive — replay chain integrity",
                governance_risk_score=0.15,
                confidence_score=0.75,
            )
        )

    if continuity_intel.rollback_instability_trend > 0.5:
        proposals.append(
            GovernanceProposal(
                proposal_type="rollback_policy_refinement",
                title="Improve rollback reliability",
                rationale=f"Rollback instability at {continuity_intel.rollback_instability_trend:.3f}",
                evidence_lineage=continuity_intel.analysis_notes[:3],
                replay_impact="neutral",
                rollback_impact="positive — more reliable rollback",
                blast_radius_estimate=0.1,
                continuity_impact="positive — rollback chain integrity",
                governance_risk_score=0.15,
                confidence_score=0.75,
            )
        )

    if adaptive_risk.composite_risk() > 0.4:
        proposals.append(
            GovernanceProposal(
                proposal_type="governance_upgrade",
                title="Reduce composite risk exposure",
                rationale=f"Composite risk at {adaptive_risk.composite_risk():.3f}",
                evidence_lineage=[f"risk={adaptive_risk.composite_risk():.3f}"],
                replay_impact="positive — safer operations",
                rollback_impact="positive — safer operations",
                blast_radius_estimate=0.25,
                continuity_impact="positive — overall stability",
                governance_risk_score=0.35,
                confidence_score=0.6,
            )
        )

    if (
        epistemic_intel.evidence_integrity_score < 0.8
        and epistemic_intel.evidence_integrity_score > 0
    ):
        proposals.append(
            GovernanceProposal(
                proposal_type="maturity_policy_refinement",
                title="Strengthen evidence integrity",
                rationale=f"Evidence integrity at {epistemic_intel.evidence_integrity_score:.1%}",
                evidence_lineage=epistemic_intel.analysis_notes[:3],
                replay_impact="neutral",
                rollback_impact="neutral",
                blast_radius_estimate=0.05,
                continuity_impact="positive — higher maturity confidence",
                governance_risk_score=0.1,
                confidence_score=0.85,
            )
        )

    if (
        orchestration_intel.blast_radius_minimization < 0.7
        and orchestration_intel.blast_radius_minimization > 0
    ):
        proposals.append(
            GovernanceProposal(
                proposal_type="orchestration_optimization",
                title="Improve blast radius minimization",
                rationale=f"BR minimization at {orchestration_intel.blast_radius_minimization:.3f}",
                evidence_lineage=orchestration_intel.analysis_notes[:3],
                replay_impact="positive — narrower blast radii",
                rollback_impact="positive — easier rollback scope",
                blast_radius_estimate=0.2,
                continuity_impact="positive — topology stability",
                governance_risk_score=0.25,
                confidence_score=0.7,
            )
        )

    return proposals


# ---------------------------------------------------------------------------
# Policy simulation
# ---------------------------------------------------------------------------


def simulate_policy_changes(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    adaptive_risk: AdaptiveRiskScores | None = None,
) -> list[PolicySimulationOutcome]:
    """Simulate policy changes — SIMULATION ONLY, no live mutation."""
    simulations: list[PolicySimulationOutcome] = []

    base_risk = adaptive_risk.composite_risk() if adaptive_risk else 0.0

    simulations.append(
        PolicySimulationOutcome(
            policy_type="stricter_governance",
            description="Add additional governance gates to high-risk operations",
            predicted_risk_delta=-0.1 if base_risk > 0.2 else -0.02,
            predicted_maturity_impact="neutral to positive",
            predicted_replay_impact="positive — more governance checkpoints",
            predicted_rollback_impact="positive — safer rollback paths",
            governance_risk_score=max(0, base_risk - 0.1),
            recommendation="apply if governance_fragility > 0.3",
        )
    )

    simulations.append(
        PolicySimulationOutcome(
            policy_type="relaxed_governance",
            description="Reduce governance gates on proven-safe operations",
            predicted_risk_delta=0.05,
            predicted_maturity_impact="neutral — only affects proven paths",
            predicted_replay_impact="neutral",
            predicted_rollback_impact="slightly negative — fewer checkpoints",
            governance_risk_score=base_risk + 0.05,
            recommendation="apply only if gate_effectiveness > 0.95",
        )
    )

    simulations.append(
        PolicySimulationOutcome(
            policy_type="altered_sequencing",
            description="Reorder upgrade sequence to minimize blast radius",
            predicted_risk_delta=-0.05,
            predicted_maturity_impact="neutral",
            predicted_replay_impact="positive — safer ordering",
            predicted_rollback_impact="positive — more isolated rollback",
            governance_risk_score=max(0, base_risk - 0.05),
            recommendation="apply if blast_radius_minimization < 0.8",
        )
    )

    simulations.append(
        PolicySimulationOutcome(
            policy_type="altered_rollback_rules",
            description="Require deterministic rollback for all high-risk upgrades",
            predicted_risk_delta=-0.08,
            predicted_maturity_impact="positive — stronger rollback evidence",
            predicted_replay_impact="neutral",
            predicted_rollback_impact="positive — deterministic rollback",
            governance_risk_score=max(0, base_risk - 0.08),
            recommendation="apply if rollback_uncertainty > 0.3",
        )
    )

    simulations.append(
        PolicySimulationOutcome(
            policy_type="altered_replay_thresholds",
            description="Increase replay validation strictness",
            predicted_risk_delta=-0.03,
            predicted_maturity_impact="positive — stronger replay evidence",
            predicted_replay_impact="positive — stricter validation",
            predicted_rollback_impact="neutral",
            governance_risk_score=max(0, base_risk - 0.03),
            recommendation="apply if replay_decay > 0.2",
        )
    )

    simulations.append(
        PolicySimulationOutcome(
            policy_type="altered_maturity_ceilings",
            description="Tighten maturity ceiling evidence requirements",
            predicted_risk_delta=-0.02,
            predicted_maturity_impact="more conservative but higher confidence",
            predicted_replay_impact="neutral",
            predicted_rollback_impact="neutral",
            governance_risk_score=max(0, base_risk - 0.02),
            recommendation="apply if maturity_confidence < 0.8",
        )
    )

    return simulations


# ---------------------------------------------------------------------------
# Governance learning memory builder
# ---------------------------------------------------------------------------


def build_governance_learning_memory(
    proposals: list[GovernanceProposal],
    base_dir: Path = Path(_ROOT),
) -> GovernanceLearningMemory:
    """Build governance learning memory from proposals and history."""
    memory = GovernanceLearningMemory(proposals=list(proposals))

    report_dir = base_dir / GOVERNANCE_INTELLIGENCE_REPORT_DIR
    if report_dir.exists():
        for f in sorted(report_dir.glob("GOVINT-*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                proof_id = data.get("proof_id", f.stem)
                memory.governance_evolution_chain.append(proof_id)
                for p in data.get("proposals", []):
                    pid = p.get("proposal_id", "")
                    status = p.get("status", "proposed")
                    if status == "accepted":
                        memory.accepted_proposals.append(pid)
                    elif status == "rejected":
                        memory.rejected_proposals.append(pid)
                    memory.proposal_outcomes.append(f"{pid}:{status}")
            except (json.JSONDecodeError, OSError):
                continue

    maturity_evo = replay_maturity_evolution(base_dir)
    for entry in maturity_evo:
        memory.policy_effectiveness_history.append(
            f"{entry.get('domain', '')}:{entry.get('maturity', '')}"
        )

    return memory


# ---------------------------------------------------------------------------
# Maturity evaluation
# ---------------------------------------------------------------------------


def compute_governance_intelligence_maturity(
    evidence: GovernanceIntelligenceEvidence,
) -> str:
    """Compute raw governance intelligence maturity level."""
    if evidence.is_dry_run:
        return "L0_NO_GOVERNANCE_INTELLIGENCE"

    for level in reversed(GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS):
        reqs = GOVERNANCE_INTELLIGENCE_MATURITY_REQUIREMENTS[level]
        if all(_check_gi_evidence(evidence, r) for r in reqs):
            return level

    return "L0_NO_GOVERNANCE_INTELLIGENCE"


def _check_gi_evidence(evidence: GovernanceIntelligenceEvidence, requirement: str) -> bool:
    field_map: dict[str, bool] = {
        "governance_integrity_analyzed": evidence.governance_integrity_analyzed,
        "gate_effectiveness_scored": evidence.gate_effectiveness_scored,
        "orchestration_intelligence_analyzed": evidence.orchestration_intelligence_analyzed,
        "sequencing_efficiency_scored": evidence.sequencing_efficiency_scored,
        "continuity_intelligence_analyzed": evidence.continuity_intelligence_analyzed,
        "drift_trends_analyzed": evidence.drift_trends_analyzed,
        "epistemic_intelligence_analyzed": evidence.epistemic_intelligence_analyzed,
        "evidence_integrity_scored": evidence.evidence_integrity_scored,
        "governance_proposals_generated": evidence.governance_proposals_generated,
        "adaptive_risk_scored": evidence.adaptive_risk_scored,
        "policy_simulation_completed": evidence.policy_simulation_completed,
        "founder_confirmed": evidence.founder_confirmed,
    }
    return field_map.get(requirement, False)


def governance_intelligence_maturity_ceiling(
    evidence: GovernanceIntelligenceEvidence,
) -> str:
    """Compute hard ceiling for governance intelligence maturity."""
    if evidence.is_dry_run:
        return "L0_NO_GOVERNANCE_INTELLIGENCE"
    if not evidence.governance_integrity_analyzed:
        return "L0_NO_GOVERNANCE_INTELLIGENCE"
    if not evidence.gate_effectiveness_scored:
        return "L0_NO_GOVERNANCE_INTELLIGENCE"
    if not evidence.orchestration_intelligence_analyzed:
        return "L1_GOVERNANCE_INTEGRITY_INTELLIGENCE"
    if not evidence.sequencing_efficiency_scored:
        return "L1_GOVERNANCE_INTEGRITY_INTELLIGENCE"
    if not evidence.continuity_intelligence_analyzed:
        return "L2_ORCHESTRATION_INTELLIGENCE"
    if not evidence.drift_trends_analyzed:
        return "L2_ORCHESTRATION_INTELLIGENCE"
    if not evidence.epistemic_intelligence_analyzed:
        return "L3_CONTINUITY_INTELLIGENCE"
    if not evidence.evidence_integrity_scored:
        return "L3_CONTINUITY_INTELLIGENCE"
    if not evidence.governance_proposals_generated:
        return "L4_EPISTEMIC_INTELLIGENCE"
    if not evidence.adaptive_risk_scored:
        return "L4_EPISTEMIC_INTELLIGENCE"
    if not evidence.policy_simulation_completed:
        return "L4_EPISTEMIC_INTELLIGENCE"
    if not evidence.founder_confirmed:
        return "L4_EPISTEMIC_INTELLIGENCE"
    return "L5_ADAPTIVE_GOVERNANCE_INTELLIGENCE"


def _gi_level_index(level: str) -> int:
    try:
        return GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS.index(level)
    except ValueError:
        return 0


def classify_governance_intelligence_maturity(
    evidence: GovernanceIntelligenceEvidence,
) -> tuple[str, str, bool, str]:
    """Classify governance intelligence maturity: (level, ceiling, blocked, reason)."""
    raw = compute_governance_intelligence_maturity(evidence)
    ceiling = governance_intelligence_maturity_ceiling(evidence)

    raw_idx = _gi_level_index(raw)
    ceil_idx = _gi_level_index(ceiling)

    if ceil_idx < raw_idx:
        return ceiling, ceiling, True, f"ceiling {ceiling} blocks {raw}"

    return raw, ceiling, False, ""


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_governance_intelligence_proof(
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    capability_proof: CapabilityPlanningProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
    base_dir: Path = Path(_ROOT),
) -> GovernanceIntelligenceProof:
    """Full adaptive governance intelligence pipeline."""
    gov_integrity = build_governance_integrity(orchestration_proof, continuity_proof)
    orch_intel = build_orchestration_intelligence(orchestration_proof, base_dir)
    cont_intel = build_continuity_intelligence(continuity_proof, base_dir)
    epist_intel = build_epistemic_intelligence(
        orchestration_proof, continuity_proof, founder_confirmed
    )

    drift_signals = continuity_proof.drift_signals if continuity_proof else []
    adaptive_risk = compute_adaptive_risk(orchestration_proof, continuity_proof, drift_signals)

    proposals = generate_governance_proposals(
        gov_integrity, orch_intel, cont_intel, epist_intel, adaptive_risk, orchestration_proof
    )

    simulations = simulate_policy_changes(orchestration_proof, continuity_proof, adaptive_risk)

    learning_memory = build_governance_learning_memory(proposals, base_dir)

    evidence = GovernanceIntelligenceEvidence(
        governance_integrity_analyzed=True,
        gate_effectiveness_scored=True,
        orchestration_intelligence_analyzed=True,
        sequencing_efficiency_scored=True,
        continuity_intelligence_analyzed=True,
        drift_trends_analyzed=True,
        epistemic_intelligence_analyzed=True,
        evidence_integrity_scored=True,
        governance_proposals_generated=len(proposals) > 0,
        governance_proposal_count=len(proposals),
        adaptive_risk_scored=True,
        adaptive_risk_composite=adaptive_risk.composite_risk(),
        policy_simulation_completed=len(simulations) > 0,
        policy_simulation_count=len(simulations),
        governance_ceilings_enforced=True,
        autonomous_mutation_blocked=True,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_governance_intelligence_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "await_founder_confirmation" if not founder_confirmed else "adaptive_governance_active"
        )
    )

    return GovernanceIntelligenceProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        governance_integrity=gov_integrity,
        orchestration_intelligence=orch_intel,
        continuity_intelligence=cont_intel,
        epistemic_intelligence=epist_intel,
        proposals=proposals,
        adaptive_risk=adaptive_risk,
        policy_simulations=simulations,
        learning_memory=learning_memory,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_governance_intelligence_proof(
    proof: GovernanceIntelligenceProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist governance intelligence proof to disk."""
    out_dir = base_dir / GOVERNANCE_INTELLIGENCE_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{proof.proof_id}.json"
    path = out_dir / filename
    with open(path, "w") as f:
        json.dump(proof.to_dict(), f, indent=2)
    return path
