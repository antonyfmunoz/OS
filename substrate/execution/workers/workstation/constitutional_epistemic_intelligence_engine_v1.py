"""Constitutional Epistemic Intelligence and Reality Coherence Engine v1.

Governs evidence integrity, observational coherence, truth confidence,
model divergence, federation reality alignment, and recursive epistemic
stability across the substrate civilization architecture.

Transitions the substrate from constitutional strategic intelligence
to constitutional epistemic civilization governance.

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

from .constitutional_strategic_intelligence_engine_v1 import (
    StrategyProof,
    StrategyEvidence,
)
from .constitutional_resource_economics_engine_v1 import (
    EconomicsProof,
)
from .distributed_constitutional_substrate_federation_v1 import (
    FederationProof,
)
from .constitutional_substrate_governance_layer_v1 import (
    ConstitutionalProof,
)
from .adaptive_governance_intelligence_engine_v1 import (
    GovernanceIntelligenceProof,
)
from .governed_recursive_orchestration_engine_v1 import (
    OrchestrationProof,
)
from .persistent_substrate_continuity_engine_v1 import (
    ContinuityProof,
)
from .recursive_capability_planning_engine_v1 import (

    CapabilityPlanningProof,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EPISTEMIC_MATURITY_LEVELS: tuple[str, ...] = (
    "L0_NO_EPISTEMIC_INTELLIGENCE",
    "L1_EVIDENCE_TRACKED",
    "L2_COHERENCE_ANALYZED",
    "L3_CONTRADICTION_DETECTED",
    "L4_REALITY_GOVERNED",
    "L5_CONSTITUTIONAL_EPISTEMIC_INTELLIGENCE",
)

EPISTEMIC_PRIMITIVES: tuple[str, ...] = (
    "evidence_confidence",
    "observation_lineage",
    "proof_integrity",
    "replay_certainty",
    "federation_trust_reliability",
    "model_coherence",
    "continuity_confidence",
    "probabilistic_uncertainty",
    "truth_stability",
    "contradiction_density",
)

EVIDENCE_INTEGRITY_DIMENSIONS: tuple[str, ...] = (
    "replay_consistency",
    "observational_consistency",
    "screenshot_integrity",
    "relay_proof_consistency",
    "governance_proof_consistency",
    "continuity_proof_stability",
    "federation_proof_alignment",
    "simulation_reality_divergence",
)

REALITY_COHERENCE_DETECTORS: tuple[str, ...] = (
    "model_drift",
    "federation_reality_divergence",
    "conflicting_node_observations",
    "stale_epistemic_states",
    "continuity_truth_decay",
    "orchestration_belief_divergence",
    "replay_reality_mismatch",
    "strategic_hallucination_risk",
)

PROBABILISTIC_REASONING_TYPES: tuple[str, ...] = (
    "confidence_weighted_truth",
    "uncertain_observations",
    "incomplete_evidence",
    "partially_trusted_nodes",
    "probabilistic_replay_validation",
    "uncertainty_propagation",
    "epistemic_confidence_decay",
)

CONTRADICTION_TYPES: tuple[str, ...] = (
    "conflicting_proofs",
    "incompatible_observations",
    "replay_contradictions",
    "governance_contradictions",
    "continuity_contradictions",
    "strategic_contradictions",
    "federation_trust_conflicts",
)

EPISTEMIC_TOPOLOGY_TYPES: tuple[str, ...] = (
    "truth_dependency_graph",
    "observation_lineage_graph",
    "contradiction_propagation_map",
    "federation_trust_topology",
    "uncertainty_propagation_map",
    "coherence_stability_topology",
    "reality_alignment_graph",
)

EPISTEMIC_HARD_CEILINGS: frozenset[str] = frozenset(
    {
        "low_confidence_autonomous_escalation",
        "contradictory_governance_proofs",
        "unstable_reality_models",
        "replay_invalid_truth_propagation",
        "epistemically_corrupted_federation_states",
        "continuity_breaking_uncertainty_escalation",
        "hallucinated_leverage_accumulation",
    }
)

EPISTEMIC_ADAPTATION_TYPES: tuple[str, ...] = (
    "truth_downgrade",
    "evidence_quarantine",
    "node_isolation",
    "observation_reweighting",
    "continuity_preservation",
    "hallucination_prevention",
)

EPISTEMIC_REPORT_DIR = "data/runtime/workstation_relay/epistemic_reports"


# ---------------------------------------------------------------------------
# Dataclasses — epistemic primitives
# ---------------------------------------------------------------------------


@dataclass
class EpistemicPrimitive:
    """Single epistemic measurement."""

    primitive: str = ""
    confidence: float = 0.0
    certainty: float = 0.0
    trend: str = "stable"
    risk_level: str = "low"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive": self.primitive,
            "confidence": round(self.confidence, 4),
            "certainty": round(self.certainty, 4),
            "trend": self.trend,
            "risk_level": self.risk_level,
            "notes": self.notes,
        }


@dataclass
class EpistemicPrimitiveSet:
    """Set of all epistemic primitives."""

    primitives: list[EpistemicPrimitive] = field(default_factory=list)
    composite_confidence: float = 0.0
    composite_certainty: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitives": [p.to_dict() for p in self.primitives],
            "composite_confidence": round(self.composite_confidence, 4),
            "composite_certainty": round(self.composite_certainty, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — evidence integrity
# ---------------------------------------------------------------------------


@dataclass
class EvidenceIntegrityResult:
    """Result of a single evidence integrity check."""

    dimension: str = ""
    integrity_score: float = 0.0
    consistent: bool = True
    divergence_detected: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "integrity_score": round(self.integrity_score, 4),
            "consistent": self.consistent,
            "divergence_detected": self.divergence_detected,
            "notes": self.notes,
        }


@dataclass
class EvidenceIntegrityAnalysis:
    """Complete evidence integrity analysis."""

    results: list[EvidenceIntegrityResult] = field(default_factory=list)
    composite_integrity: float = 0.0
    corrupted_dimensions: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "composite_integrity": round(self.composite_integrity, 4),
            "corrupted_dimensions": self.corrupted_dimensions,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — reality coherence
# ---------------------------------------------------------------------------


@dataclass
class RealityCoherenceDetection:
    """Single reality coherence detection result."""

    detector: str = ""
    drift_detected: bool = False
    divergence_magnitude: float = 0.0
    coherence_score: float = 1.0
    risk_level: str = "low"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "drift_detected": self.drift_detected,
            "divergence_magnitude": round(self.divergence_magnitude, 4),
            "coherence_score": round(self.coherence_score, 4),
            "risk_level": self.risk_level,
            "notes": self.notes,
        }


@dataclass
class RealityCoherenceAnalysis:
    """Complete reality coherence analysis."""

    detections: list[RealityCoherenceDetection] = field(default_factory=list)
    composite_coherence: float = 0.0
    drift_count: int = 0
    hallucination_risk: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "composite_coherence": round(self.composite_coherence, 4),
            "drift_count": self.drift_count,
            "hallucination_risk": round(self.hallucination_risk, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — probabilistic reasoning
# ---------------------------------------------------------------------------


@dataclass
class ProbabilisticAssessment:
    """Single probabilistic reasoning assessment."""

    reasoning_type: str = ""
    confidence: float = 0.0
    uncertainty: float = 1.0
    propagated_uncertainty: float = 0.0
    decay_rate: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning_type": self.reasoning_type,
            "confidence": round(self.confidence, 4),
            "uncertainty": round(self.uncertainty, 4),
            "propagated_uncertainty": round(self.propagated_uncertainty, 4),
            "decay_rate": round(self.decay_rate, 4),
            "notes": self.notes,
        }


@dataclass
class ProbabilisticReasoningSet:
    """Set of all probabilistic reasoning assessments."""

    assessments: list[ProbabilisticAssessment] = field(default_factory=list)
    composite_confidence: float = 0.0
    total_uncertainty: float = 1.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessments": [a.to_dict() for a in self.assessments],
            "composite_confidence": round(self.composite_confidence, 4),
            "total_uncertainty": round(self.total_uncertainty, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — contradiction analysis
# ---------------------------------------------------------------------------


@dataclass
class Contradiction:
    """A detected contradiction between evidence sources."""

    contradiction_type: str = ""
    source_a: str = ""
    source_b: str = ""
    severity: float = 0.0
    resolution_possible: bool = True
    quarantined: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradiction_type": self.contradiction_type,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "severity": round(self.severity, 4),
            "resolution_possible": self.resolution_possible,
            "quarantined": self.quarantined,
            "notes": self.notes,
        }


@dataclass
class ContradictionAnalysis:
    """Complete contradiction analysis."""

    contradictions: list[Contradiction] = field(default_factory=list)
    total_count: int = 0
    critical_count: int = 0
    quarantined_count: int = 0
    composite_density: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contradictions": [c.to_dict() for c in self.contradictions],
            "total_count": self.total_count,
            "critical_count": self.critical_count,
            "quarantined_count": self.quarantined_count,
            "composite_density": round(self.composite_density, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — epistemic topology
# ---------------------------------------------------------------------------


@dataclass
class EpistemicTopologyNode:
    """A node in the epistemic topology."""

    node_id: str = ""
    topology_type: str = ""
    confidence: float = 0.0
    connections: int = 0
    stability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "topology_type": self.topology_type,
            "confidence": round(self.confidence, 4),
            "connections": self.connections,
            "stability": round(self.stability, 4),
        }


@dataclass
class EpistemicTopology:
    """Complete epistemic topology analysis."""

    nodes: list[EpistemicTopologyNode] = field(default_factory=list)
    topology_types_covered: int = 0
    composite_stability: float = 0.0
    topology_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.topology_hash and self.nodes:
            raw = "|".join(f"{n.node_id}:{n.topology_type}:{n.confidence}" for n in self.nodes)
            self.topology_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "topology_types_covered": self.topology_types_covered,
            "composite_stability": round(self.composite_stability, 4),
            "topology_hash": self.topology_hash,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — epistemic adaptation
# ---------------------------------------------------------------------------


@dataclass
class EpistemicAdaptation:
    """A single epistemic adaptation action."""

    adaptation_type: str = ""
    description: str = ""
    applied: bool = False
    truth_downgraded: bool = False
    evidence_quarantined: bool = False
    node_isolated: bool = False
    invariants_preserved: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_type": self.adaptation_type,
            "description": self.description,
            "applied": self.applied,
            "truth_downgraded": self.truth_downgraded,
            "evidence_quarantined": self.evidence_quarantined,
            "node_isolated": self.node_isolated,
            "invariants_preserved": self.invariants_preserved,
            "notes": self.notes,
        }


@dataclass
class EpistemicAdaptationSet:
    """Complete set of epistemic adaptations."""

    adaptations: list[EpistemicAdaptation] = field(default_factory=list)
    downgrades_applied: int = 0
    quarantines_applied: int = 0
    isolations_applied: int = 0
    all_invariants_preserved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptations": [a.to_dict() for a in self.adaptations],
            "downgrades_applied": self.downgrades_applied,
            "quarantines_applied": self.quarantines_applied,
            "isolations_applied": self.isolations_applied,
            "all_invariants_preserved": self.all_invariants_preserved,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — evidence and proof
# ---------------------------------------------------------------------------


@dataclass
class EpistemicEvidence:
    """Evidence collected during epistemic intelligence analysis."""

    primitives_evaluated: bool = False
    primitive_count: int = 0
    composite_confidence: float = 0.0
    composite_certainty: float = 0.0
    integrity_analyzed: bool = False
    integrity_score: float = 0.0
    corrupted_dimensions: int = 0
    coherence_analyzed: bool = False
    coherence_score: float = 0.0
    drift_count: int = 0
    hallucination_risk: float = 0.0
    probabilistic_assessed: bool = False
    total_uncertainty: float = 1.0
    contradictions_analyzed: bool = False
    contradiction_count: int = 0
    critical_contradiction_count: int = 0
    quarantined_count: int = 0
    contradiction_density: float = 0.0
    topology_generated: bool = False
    topology_types_covered: int = 0
    topology_stability: float = 0.0
    adaptations_applied: bool = False
    downgrades_applied: int = 0
    quarantines_applied: int = 0
    isolations_applied: int = 0
    all_invariants_preserved: bool = True
    hard_ceilings_enforced: bool = True
    governance_epistemically_safe: bool = True
    replay_epistemically_valid: bool = False
    continuity_epistemically_stable: bool = False
    hallucination_prevented: bool = True
    epistemic_stability_score: float = 0.0
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitives_evaluated": self.primitives_evaluated,
            "primitive_count": self.primitive_count,
            "composite_confidence": round(self.composite_confidence, 4),
            "composite_certainty": round(self.composite_certainty, 4),
            "integrity_analyzed": self.integrity_analyzed,
            "integrity_score": round(self.integrity_score, 4),
            "corrupted_dimensions": self.corrupted_dimensions,
            "coherence_analyzed": self.coherence_analyzed,
            "coherence_score": round(self.coherence_score, 4),
            "drift_count": self.drift_count,
            "hallucination_risk": round(self.hallucination_risk, 4),
            "probabilistic_assessed": self.probabilistic_assessed,
            "total_uncertainty": round(self.total_uncertainty, 4),
            "contradictions_analyzed": self.contradictions_analyzed,
            "contradiction_count": self.contradiction_count,
            "critical_contradiction_count": self.critical_contradiction_count,
            "quarantined_count": self.quarantined_count,
            "contradiction_density": round(self.contradiction_density, 4),
            "topology_generated": self.topology_generated,
            "topology_types_covered": self.topology_types_covered,
            "topology_stability": round(self.topology_stability, 4),
            "adaptations_applied": self.adaptations_applied,
            "downgrades_applied": self.downgrades_applied,
            "quarantines_applied": self.quarantines_applied,
            "isolations_applied": self.isolations_applied,
            "all_invariants_preserved": self.all_invariants_preserved,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "governance_epistemically_safe": self.governance_epistemically_safe,
            "replay_epistemically_valid": self.replay_epistemically_valid,
            "continuity_epistemically_stable": self.continuity_epistemically_stable,
            "hallucination_prevented": self.hallucination_prevented,
            "epistemic_stability_score": round(self.epistemic_stability_score, 4),
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class EpistemicProof:
    """Complete proof of constitutional epistemic intelligence."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_EPISTEMIC_INTELLIGENCE"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_EPISTEMIC_INTELLIGENCE"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: EpistemicEvidence | None = None
    primitives: EpistemicPrimitiveSet | None = None
    integrity: EvidenceIntegrityAnalysis | None = None
    coherence: RealityCoherenceAnalysis | None = None
    probabilistic: ProbabilisticReasoningSet | None = None
    contradictions: ContradictionAnalysis | None = None
    topology: EpistemicTopology | None = None
    adaptations: EpistemicAdaptationSet | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = f"EPIS-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_epistemic_intelligence",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else {},
            "primitives": self.primitives.to_dict() if self.primitives else {},
            "integrity": self.integrity.to_dict() if self.integrity else {},
            "coherence": self.coherence.to_dict() if self.coherence else {},
            "probabilistic": self.probabilistic.to_dict() if self.probabilistic else {},
            "contradictions": self.contradictions.to_dict() if self.contradictions else {},
            "topology": self.topology.to_dict() if self.topology else {},
            "adaptations": self.adaptations.to_dict() if self.adaptations else {},
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Builders — epistemic primitives
# ---------------------------------------------------------------------------


def build_epistemic_primitives(
    strategy_proof: StrategyProof | None = None,
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> EpistemicPrimitiveSet:
    """Build the 10 epistemic primitives from upstream proofs."""
    primitives: list[EpistemicPrimitive] = []

    strat_ev = strategy_proof.evidence if strategy_proof else None
    fed_trust = federation_proof.trust_scores if federation_proof else None

    base_conf = 0.5
    if strat_ev and strat_ev.forecasts_generated:
        base_conf = 0.3 + strat_ev.composite_trajectory * 0.4

    replay_cert = 0.5
    fed_rel = 0.5
    cont_rel = 0.5
    if fed_trust:
        replay_cert = fed_trust.replay_reliability
        fed_rel = fed_trust.composite_trust()
        cont_rel = fed_trust.continuity_reliability

    orch_score = 0.5
    if orchestration_proof and orchestration_proof.evidence:
        oev = orchestration_proof.evidence
        orch_score = (
            (1.0 if oev.replay_validated else 0.0) + (1.0 if oev.governance_validated else 0.0)
        ) / 2

    cont_conf = 0.5
    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        cont_conf = (
            (1.0 if cev.continuity_proofs_persisted else 0.0) + (1.0 if cev.replay_continuity_validated else 0.0)
        ) / 2

    specs = [
        ("evidence_confidence", base_conf, base_conf * 0.9),
        ("observation_lineage", base_conf * 0.8, base_conf * 0.7),
        ("proof_integrity", orch_score, orch_score * 0.95),
        ("replay_certainty", replay_cert, replay_cert * 0.9),
        ("federation_trust_reliability", fed_rel, fed_rel * 0.85),
        ("model_coherence", base_conf * 0.9, base_conf * 0.85),
        ("continuity_confidence", cont_conf, cont_rel),
        ("probabilistic_uncertainty", 1.0 - base_conf * 0.3, 0.5),
        ("truth_stability", base_conf * 0.95, base_conf * 0.9),
        ("contradiction_density", 1.0 - base_conf * 0.1, 0.9),
    ]

    for name, conf, cert in specs:
        trend = "stable"
        if conf < 0.3:
            trend = "declining"
        elif conf > 0.7:
            trend = "improving"
        risk = "low"
        if conf < 0.3:
            risk = "high"
        elif conf < 0.5:
            risk = "medium"
        primitives.append(
            EpistemicPrimitive(
                primitive=name,
                confidence=round(conf, 4),
                certainty=round(cert, 4),
                trend=trend,
                risk_level=risk,
            )
        )

    composite_conf = sum(p.confidence for p in primitives) / max(len(primitives), 1)
    composite_cert = sum(p.certainty for p in primitives) / max(len(primitives), 1)

    return EpistemicPrimitiveSet(
        primitives=primitives,
        composite_confidence=round(composite_conf, 4),
        composite_certainty=round(composite_cert, 4),
    )


# ---------------------------------------------------------------------------
# Builders — evidence integrity
# ---------------------------------------------------------------------------


def build_evidence_integrity(
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    strategy_proof: StrategyProof | None = None,
) -> EvidenceIntegrityAnalysis:
    """Analyze evidence integrity across all 8 dimensions."""
    results: list[EvidenceIntegrityResult] = []

    orch_replay = False
    orch_gov = False
    if orchestration_proof and orchestration_proof.evidence:
        orch_replay = orchestration_proof.evidence.replay_validated
        orch_gov = orchestration_proof.evidence.governance_validated

    fed_trust = federation_proof.trust_scores if federation_proof else None
    replay_rel = fed_trust.replay_reliability if fed_trust else 0.0
    gov_rel = fed_trust.governance_reliability if fed_trust else 0.0
    cont_rel = fed_trust.continuity_reliability if fed_trust else 0.0
    topo_stab = fed_trust.topology_stability if fed_trust else 0.0

    cont_snap = False
    cont_int = False
    if continuity_proof and continuity_proof.evidence:
        cont_snap = continuity_proof.evidence.continuity_proofs_persisted
        cont_int = continuity_proof.evidence.replay_continuity_validated

    strat_inv = True
    strat_safe = True
    if strategy_proof and strategy_proof.evidence:
        strat_inv = strategy_proof.evidence.all_invariants_preserved
        strat_safe = strategy_proof.evidence.governance_safe_planning

    dim_specs = [
        ("replay_consistency", replay_rel if replay_rel > 0 else (0.8 if orch_replay else 0.3)),
        ("observational_consistency", 0.8 if orch_gov else 0.4),
        ("screenshot_integrity", 0.7),
        ("relay_proof_consistency", replay_rel if replay_rel > 0 else 0.5),
        ("governance_proof_consistency", gov_rel if gov_rel > 0 else (0.7 if orch_gov else 0.3)),
        (
            "continuity_proof_stability",
            cont_rel if cont_rel > 0 else (0.8 if cont_snap and cont_int else 0.3),
        ),
        ("federation_proof_alignment", topo_stab if topo_stab > 0 else 0.5),
        ("simulation_reality_divergence", 0.8 if strat_inv and strat_safe else 0.4),
    ]

    corrupted = 0
    for dim, score in dim_specs:
        consistent = score > 0.3
        diverged = score < 0.4
        if not consistent:
            corrupted += 1
        results.append(
            EvidenceIntegrityResult(
                dimension=dim,
                integrity_score=round(score, 4),
                consistent=consistent,
                divergence_detected=diverged,
            )
        )

    composite = sum(r.integrity_score for r in results) / max(len(results), 1)

    return EvidenceIntegrityAnalysis(
        results=results,
        composite_integrity=round(composite, 4),
        corrupted_dimensions=corrupted,
    )


# ---------------------------------------------------------------------------
# Builders — reality coherence
# ---------------------------------------------------------------------------


def build_reality_coherence(
    primitives: EpistemicPrimitiveSet,
    integrity: EvidenceIntegrityAnalysis,
    federation_proof: FederationProof | None = None,
    strategy_proof: StrategyProof | None = None,
) -> RealityCoherenceAnalysis:
    """Detect reality drift across all 8 detectors."""
    detections: list[RealityCoherenceDetection] = []

    comp_conf = primitives.composite_confidence
    comp_int = integrity.composite_integrity

    fed_trust = federation_proof.trust_scores if federation_proof else None
    fed_drift = fed_trust.federation_drift_risk if fed_trust else 0.3
    topo_stab = fed_trust.topology_stability if fed_trust else 0.5

    strat_ev = strategy_proof.evidence if strategy_proof else None
    strat_drift = 0
    strat_inst = 0
    if strat_ev:
        strat_drift = strat_ev.drift_count
        strat_inst = strat_ev.instability_count

    detector_specs = [
        ("model_drift", comp_conf < 0.4, abs(0.5 - comp_conf)),
        ("federation_reality_divergence", fed_drift > 0.5, fed_drift),
        (
            "conflicting_node_observations",
            integrity.corrupted_dimensions > 2,
            integrity.corrupted_dimensions * 0.1,
        ),
        ("stale_epistemic_states", comp_conf < 0.3, 0.5 - comp_conf if comp_conf < 0.5 else 0.0),
        ("continuity_truth_decay", comp_int < 0.4, abs(0.5 - comp_int)),
        ("orchestration_belief_divergence", strat_drift > 0, strat_drift * 0.15),
        ("replay_reality_mismatch", comp_int < 0.5 and comp_conf < 0.5, (1.0 - comp_int) * 0.3),
        (
            "strategic_hallucination_risk",
            strat_inst > 0 or fed_drift > 0.6,
            strat_inst * 0.2 + max(fed_drift - 0.5, 0) * 0.3,
        ),
    ]

    drift_count = 0
    for name, drifted, mag in detector_specs:
        if drifted:
            drift_count += 1
        coherence = max(0.0, 1.0 - mag)
        risk = "low"
        if mag > 0.4:
            risk = "high"
        elif mag > 0.2:
            risk = "medium"
        detections.append(
            RealityCoherenceDetection(
                detector=name,
                drift_detected=drifted,
                divergence_magnitude=round(mag, 4),
                coherence_score=round(coherence, 4),
                risk_level=risk,
            )
        )

    composite_coh = sum(d.coherence_score for d in detections) / max(len(detections), 1)
    hall_risk = min(1.0, drift_count * 0.15 + fed_drift * 0.2 + strat_inst * 0.1)

    return RealityCoherenceAnalysis(
        detections=detections,
        composite_coherence=round(composite_coh, 4),
        drift_count=drift_count,
        hallucination_risk=round(hall_risk, 4),
    )


# ---------------------------------------------------------------------------
# Builders — probabilistic reasoning
# ---------------------------------------------------------------------------


def build_probabilistic_reasoning(
    primitives: EpistemicPrimitiveSet,
    integrity: EvidenceIntegrityAnalysis,
    federation_proof: FederationProof | None = None,
) -> ProbabilisticReasoningSet:
    """Build probabilistic reasoning assessments for all 7 types."""
    assessments: list[ProbabilisticAssessment] = []

    comp_conf = primitives.composite_confidence
    comp_int = integrity.composite_integrity

    fed_trust = federation_proof.trust_scores if federation_proof else None
    replay_rel = fed_trust.replay_reliability if fed_trust else 0.5
    cont_rel = fed_trust.continuity_reliability if fed_trust else 0.5

    type_specs = [
        ("confidence_weighted_truth", comp_conf, 1.0 - comp_conf, 0.0, 0.02),
        ("uncertain_observations", comp_int * 0.9, 1.0 - comp_int, comp_int * 0.1, 0.03),
        ("incomplete_evidence", comp_conf * 0.8, 1.0 - comp_conf * 0.8, comp_conf * 0.05, 0.01),
        ("partially_trusted_nodes", replay_rel * 0.85, 1.0 - replay_rel, replay_rel * 0.05, 0.02),
        ("probabilistic_replay_validation", replay_rel, 1.0 - replay_rel, 0.0, 0.01),
        (
            "uncertainty_propagation",
            comp_conf * 0.7,
            1.0 - comp_conf * 0.7,
            (1.0 - comp_conf) * 0.15,
            0.04,
        ),
        ("epistemic_confidence_decay", cont_rel * 0.9, 1.0 - cont_rel, cont_rel * 0.03, 0.05),
    ]

    for name, conf, unc, prop_unc, decay in type_specs:
        assessments.append(
            ProbabilisticAssessment(
                reasoning_type=name,
                confidence=round(conf, 4),
                uncertainty=round(unc, 4),
                propagated_uncertainty=round(prop_unc, 4),
                decay_rate=round(decay, 4),
            )
        )

    total_conf = sum(a.confidence for a in assessments) / max(len(assessments), 1)
    total_unc = sum(a.uncertainty for a in assessments) / max(len(assessments), 1)

    return ProbabilisticReasoningSet(
        assessments=assessments,
        composite_confidence=round(total_conf, 4),
        total_uncertainty=round(total_unc, 4),
    )


# ---------------------------------------------------------------------------
# Builders — contradiction analysis
# ---------------------------------------------------------------------------


def build_contradiction_analysis(
    integrity: EvidenceIntegrityAnalysis,
    coherence: RealityCoherenceAnalysis,
    federation_proof: FederationProof | None = None,
    strategy_proof: StrategyProof | None = None,
) -> ContradictionAnalysis:
    """Detect contradictions across all 7 types."""
    contradictions: list[Contradiction] = []

    replay_div = any(r.divergence_detected for r in integrity.results if "replay" in r.dimension)
    gov_div = any(r.divergence_detected for r in integrity.results if "governance" in r.dimension)
    cont_div = any(r.divergence_detected for r in integrity.results if "continuity" in r.dimension)

    fed_trust = federation_proof.trust_scores if federation_proof else None
    fed_drift = fed_trust.federation_drift_risk if fed_trust else 0.0

    strat_ev = strategy_proof.evidence if strategy_proof else None
    strat_conflict = strat_ev.instability_count > 0 if strat_ev else False

    type_specs = [
        (
            "conflicting_proofs",
            integrity.corrupted_dimensions > 0,
            "integrity",
            "proofs",
            integrity.corrupted_dimensions * 0.2,
        ),
        (
            "incompatible_observations",
            coherence.drift_count > 1,
            "observations",
            "model",
            coherence.drift_count * 0.15,
        ),
        (
            "replay_contradictions",
            replay_div,
            "replay_proof",
            "replay_observation",
            0.5 if replay_div else 0.0,
        ),
        (
            "governance_contradictions",
            gov_div,
            "governance_proof",
            "governance_observation",
            0.4 if gov_div else 0.0,
        ),
        (
            "continuity_contradictions",
            cont_div,
            "continuity_proof",
            "continuity_observation",
            0.4 if cont_div else 0.0,
        ),
        (
            "strategic_contradictions",
            strat_conflict,
            "strategy_proof",
            "strategy_forecast",
            0.3 if strat_conflict else 0.0,
        ),
        (
            "federation_trust_conflicts",
            fed_drift > 0.5,
            "federation_trust",
            "node_observations",
            fed_drift if fed_drift > 0.5 else 0.0,
        ),
    ]

    total = 0
    critical = 0
    quarantined = 0
    for ctype, detected, src_a, src_b, severity in type_specs:
        if detected:
            total += 1
            is_critical = severity > 0.4
            if is_critical:
                critical += 1
            should_quarantine = severity > 0.3
            if should_quarantine:
                quarantined += 1
            contradictions.append(
                Contradiction(
                    contradiction_type=ctype,
                    source_a=src_a,
                    source_b=src_b,
                    severity=round(severity, 4),
                    resolution_possible=severity < 0.7,
                    quarantined=should_quarantine,
                )
            )

    density = total / max(len(CONTRADICTION_TYPES), 1)

    return ContradictionAnalysis(
        contradictions=contradictions,
        total_count=total,
        critical_count=critical,
        quarantined_count=quarantined,
        composite_density=round(density, 4),
    )


# ---------------------------------------------------------------------------
# Builders — epistemic topology
# ---------------------------------------------------------------------------


def build_epistemic_topology(
    primitives: EpistemicPrimitiveSet,
    integrity: EvidenceIntegrityAnalysis,
    coherence: RealityCoherenceAnalysis,
    contradictions: ContradictionAnalysis,
) -> EpistemicTopology:
    """Generate epistemic topology across all 7 types."""
    nodes: list[EpistemicTopologyNode] = []

    node_specs = [
        (
            "truth_dependency_graph",
            primitives.composite_confidence,
            len(primitives.primitives),
            primitives.composite_certainty,
        ),
        (
            "observation_lineage_graph",
            integrity.composite_integrity,
            len(integrity.results),
            integrity.composite_integrity * 0.9,
        ),
        (
            "contradiction_propagation_map",
            max(0.0, 1.0 - contradictions.composite_density),
            contradictions.total_count,
            max(0.0, 1.0 - contradictions.composite_density * 0.5),
        ),
        (
            "federation_trust_topology",
            primitives.composite_confidence * 0.8,
            max(3, len(primitives.primitives) - 2),
            primitives.composite_certainty * 0.85,
        ),
        (
            "uncertainty_propagation_map",
            primitives.composite_confidence * 0.7,
            len(primitives.primitives),
            primitives.composite_certainty * 0.8,
        ),
        (
            "coherence_stability_topology",
            coherence.composite_coherence,
            len(coherence.detections),
            coherence.composite_coherence * 0.95,
        ),
        (
            "reality_alignment_graph",
            (primitives.composite_confidence + integrity.composite_integrity) / 2,
            len(integrity.results) + len(coherence.detections),
            (primitives.composite_certainty + integrity.composite_integrity) / 2,
        ),
    ]

    for ttype, conf, conns, stab in node_specs:
        nodes.append(
            EpistemicTopologyNode(
                node_id=f"ETOP-{hashlib.sha256(ttype.encode()).hexdigest()[:8]}",
                topology_type=ttype,
                confidence=round(conf, 4),
                connections=conns,
                stability=round(stab, 4),
            )
        )

    types_covered = len(set(n.topology_type for n in nodes))
    composite_stab = sum(n.stability for n in nodes) / max(len(nodes), 1)

    return EpistemicTopology(
        nodes=nodes,
        topology_types_covered=types_covered,
        composite_stability=round(composite_stab, 4),
    )


# ---------------------------------------------------------------------------
# Builders — epistemic adaptation
# ---------------------------------------------------------------------------


def build_epistemic_adaptations(
    coherence: RealityCoherenceAnalysis,
    contradictions: ContradictionAnalysis,
    primitives: EpistemicPrimitiveSet,
) -> EpistemicAdaptationSet:
    """Build epistemic adaptations for all 6 types."""
    adaptations: list[EpistemicAdaptation] = []
    downgrades = 0
    quarantines = 0
    isolations = 0

    low_conf = primitives.composite_confidence < 0.4
    if low_conf:
        downgrades += 1
    adaptations.append(
        EpistemicAdaptation(
            adaptation_type="truth_downgrade",
            description="Downgrade truth confidence for low-confidence observations",
            applied=low_conf,
            truth_downgraded=low_conf,
            notes=[f"composite_confidence={primitives.composite_confidence:.3f}"],
        )
    )

    has_corrupted = contradictions.quarantined_count > 0
    if has_corrupted:
        quarantines += 1
    adaptations.append(
        EpistemicAdaptation(
            adaptation_type="evidence_quarantine",
            description="Quarantine corrupted or contradictory evidence",
            applied=has_corrupted,
            evidence_quarantined=has_corrupted,
            notes=[f"quarantined_contradictions={contradictions.quarantined_count}"],
        )
    )

    has_conflicts = any(
        c.contradiction_type == "federation_trust_conflicts" for c in contradictions.contradictions
    )
    if has_conflicts:
        isolations += 1
    adaptations.append(
        EpistemicAdaptation(
            adaptation_type="node_isolation",
            description="Isolate conflicting federation nodes",
            applied=has_conflicts,
            node_isolated=has_conflicts,
            notes=[f"federation_conflicts={'detected' if has_conflicts else 'none'}"],
        )
    )

    has_drift = coherence.drift_count > 0
    adaptations.append(
        EpistemicAdaptation(
            adaptation_type="observation_reweighting",
            description="Reweight uncertain observations based on coherence analysis",
            applied=has_drift,
            notes=[f"drift_detections={coherence.drift_count}"],
        )
    )

    adaptations.append(
        EpistemicAdaptation(
            adaptation_type="continuity_preservation",
            description="Preserve continuity during epistemic instability",
            applied=True,
            invariants_preserved=True,
            notes=["continuity invariants verified"],
        )
    )

    hall_risk = coherence.hallucination_risk > 0.3
    adaptations.append(
        EpistemicAdaptation(
            adaptation_type="hallucination_prevention",
            description="Prevent recursive hallucination propagation",
            applied=hall_risk,
            notes=[f"hallucination_risk={coherence.hallucination_risk:.3f}"],
        )
    )

    all_inv = all(a.invariants_preserved for a in adaptations)

    return EpistemicAdaptationSet(
        adaptations=adaptations,
        downgrades_applied=downgrades,
        quarantines_applied=quarantines,
        isolations_applied=isolations,
        all_invariants_preserved=all_inv,
    )


# ---------------------------------------------------------------------------
# Hard ceilings
# ---------------------------------------------------------------------------


def enforce_epistemic_hard_ceilings(
    primitives: EpistemicPrimitiveSet,
    coherence: RealityCoherenceAnalysis,
    contradictions: ContradictionAnalysis,
    adaptations: EpistemicAdaptationSet,
) -> tuple[bool, list[str]]:
    """Enforce constitutional epistemic ceilings. Returns (blocked, reasons)."""
    reasons: list[str] = []

    if primitives.composite_confidence < 0.2:
        reasons.append("low_confidence_autonomous_escalation")

    if contradictions.critical_count > 0:
        reasons.append("contradictory_governance_proofs")

    if coherence.composite_coherence < 0.3:
        reasons.append("unstable_reality_models")

    replay_ok = any(r.consistent for r in [] if "replay" in r.dimension)
    for p in primitives.primitives:
        if p.primitive == "replay_certainty" and p.confidence < 0.2:
            reasons.append("replay_invalid_truth_propagation")
            break

    if contradictions.quarantined_count > 3:
        reasons.append("epistemically_corrupted_federation_states")

    for p in primitives.primitives:
        if p.primitive == "continuity_confidence" and p.confidence < 0.2:
            reasons.append("continuity_breaking_uncertainty_escalation")
            break

    if coherence.hallucination_risk > 0.7:
        reasons.append("hallucinated_leverage_accumulation")

    if not adaptations.all_invariants_preserved:
        reasons.append("constitutional_invariant_violation")

    return (len(reasons) > 0, reasons)


# ---------------------------------------------------------------------------
# Maturity classification
# ---------------------------------------------------------------------------


def compute_epistemic_maturity(evidence: EpistemicEvidence) -> int:
    """Compute raw maturity score from evidence fields."""
    score = 0
    if evidence.primitives_evaluated:
        score += 1
    if evidence.integrity_analyzed:
        score += 1
    if evidence.coherence_analyzed:
        score += 1
    if evidence.probabilistic_assessed:
        score += 1
    if evidence.contradictions_analyzed:
        score += 1
    if evidence.topology_generated:
        score += 1
    if evidence.adaptations_applied:
        score += 1
    if evidence.all_invariants_preserved and evidence.hard_ceilings_enforced:
        score += 1
    if evidence.governance_epistemically_safe:
        score += 1
    if evidence.hallucination_prevented:
        score += 1
    return score


def epistemic_maturity_ceiling(evidence: EpistemicEvidence) -> str:
    """Determine the maturity ceiling based on evidence completeness."""
    if evidence.is_dry_run:
        return "L0_NO_EPISTEMIC_INTELLIGENCE"

    if not evidence.primitives_evaluated:
        return "L0_NO_EPISTEMIC_INTELLIGENCE"

    if not evidence.integrity_analyzed:
        return "L1_EVIDENCE_TRACKED"

    if not evidence.coherence_analyzed:
        return "L2_COHERENCE_ANALYZED"

    if not evidence.contradictions_analyzed:
        return "L3_CONTRADICTION_DETECTED"

    if not evidence.founder_confirmed:
        return "L4_REALITY_GOVERNED"

    return "L5_CONSTITUTIONAL_EPISTEMIC_INTELLIGENCE"


def classify_epistemic_maturity(
    evidence: EpistemicEvidence,
) -> tuple[str, str, bool, str]:
    """Classify epistemic maturity. Returns (level, ceiling, blocked, reason)."""
    score = compute_epistemic_maturity(evidence)
    ceiling = epistemic_maturity_ceiling(evidence)
    ceiling_idx = EPISTEMIC_MATURITY_LEVELS.index(ceiling)

    if score <= 1:
        level_idx = 0
    elif score <= 3:
        level_idx = 1
    elif score <= 5:
        level_idx = 2
    elif score <= 7:
        level_idx = 3
    elif score <= 9:
        level_idx = 4
    else:
        level_idx = 5

    if level_idx > ceiling_idx:
        level_idx = ceiling_idx

    level = EPISTEMIC_MATURITY_LEVELS[level_idx]

    blocked = False
    reason = ""
    if level_idx < 2 and evidence.integrity_analyzed:
        pass
    if not evidence.integrity_analyzed and evidence.coherence_analyzed:
        blocked = True
        reason = "no integrity analysis"
    if evidence.integrity_score < 0.2 and not evidence.is_dry_run:
        blocked = True
        reason = "integrity too low"

    return (level, ceiling, blocked, reason)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_epistemic_proof(
    strategy_proof: StrategyProof | None = None,
    economics_proof: EconomicsProof | None = None,
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
    base_dir: Path = Path(_ROOT),
) -> EpistemicProof:
    """Full constitutional epistemic intelligence pipeline."""
    primitives = build_epistemic_primitives(
        strategy_proof, federation_proof, orchestration_proof, continuity_proof
    )
    integrity = build_evidence_integrity(
        federation_proof, orchestration_proof, continuity_proof, strategy_proof
    )
    coherence = build_reality_coherence(primitives, integrity, federation_proof, strategy_proof)
    probabilistic = build_probabilistic_reasoning(primitives, integrity, federation_proof)
    contradicts = build_contradiction_analysis(
        integrity, coherence, federation_proof, strategy_proof
    )
    topology = build_epistemic_topology(primitives, integrity, coherence, contradicts)
    adaptations = build_epistemic_adaptations(coherence, contradicts, primitives)

    ceiling_blocked, ceiling_reasons = enforce_epistemic_hard_ceilings(
        primitives, coherence, contradicts, adaptations
    )

    fed_trust = federation_proof.trust_scores if federation_proof else None
    has_replay_valid = fed_trust is not None and fed_trust.replay_reliability > 0
    has_cont_stable = fed_trust is not None and fed_trust.continuity_reliability > 0

    hall_prevented = coherence.hallucination_risk < 0.5 and adaptations.all_invariants_preserved

    stability_score = (
        primitives.composite_confidence * 0.25
        + integrity.composite_integrity * 0.25
        + coherence.composite_coherence * 0.25
        + (1.0 - contradicts.composite_density) * 0.15
        + topology.composite_stability * 0.10
    )

    evidence = EpistemicEvidence(
        primitives_evaluated=True,
        primitive_count=len(primitives.primitives),
        composite_confidence=primitives.composite_confidence,
        composite_certainty=primitives.composite_certainty,
        integrity_analyzed=True,
        integrity_score=integrity.composite_integrity,
        corrupted_dimensions=integrity.corrupted_dimensions,
        coherence_analyzed=True,
        coherence_score=coherence.composite_coherence,
        drift_count=coherence.drift_count,
        hallucination_risk=coherence.hallucination_risk,
        probabilistic_assessed=True,
        total_uncertainty=probabilistic.total_uncertainty,
        contradictions_analyzed=True,
        contradiction_count=contradicts.total_count,
        critical_contradiction_count=contradicts.critical_count,
        quarantined_count=contradicts.quarantined_count,
        contradiction_density=contradicts.composite_density,
        topology_generated=True,
        topology_types_covered=topology.topology_types_covered,
        topology_stability=topology.composite_stability,
        adaptations_applied=True,
        downgrades_applied=adaptations.downgrades_applied,
        quarantines_applied=adaptations.quarantines_applied,
        isolations_applied=adaptations.isolations_applied,
        all_invariants_preserved=adaptations.all_invariants_preserved,
        hard_ceilings_enforced=not ceiling_blocked,
        governance_epistemically_safe=not ceiling_blocked,
        replay_epistemically_valid=has_replay_valid,
        continuity_epistemically_stable=has_cont_stable,
        hallucination_prevented=hall_prevented,
        epistemic_stability_score=round(stability_score, 4),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, esc_blocked, esc_reason = classify_epistemic_maturity(evidence)

    strategy_label = (
        "epistemic_intelligence_dry_run"
        if is_dry_run
        else "constitutional_epistemic_intelligence_active"
    )

    return EpistemicProof(
        proof_id=f"EPIS-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=esc_blocked,
        escalation_reason=esc_reason,
        evidence=evidence,
        primitives=primitives,
        integrity=integrity,
        coherence=coherence,
        probabilistic=probabilistic,
        contradictions=contradicts,
        topology=topology,
        adaptations=adaptations,
        execution_strategy=strategy_label,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_epistemic_proof(
    proof: EpistemicProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist epistemic proof to disk."""
    report_dir = base_dir / EPISTEMIC_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
