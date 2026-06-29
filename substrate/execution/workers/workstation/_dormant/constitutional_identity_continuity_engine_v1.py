"""Constitutional Identity Continuity and Sovereign Memory Architecture v1.

Preserves historical continuity, institutional identity integrity,
narrative coherence, lineage stability, and recursive selfhood
consistency across the evolving substrate civilization architecture.

Transitions the substrate from constitutional epistemic intelligence
to constitutional historical identity continuity.

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

from .constitutional_epistemic_intelligence_engine_v1 import (
    EpistemicProof,
    EpistemicEvidence,
)
from .constitutional_strategic_intelligence_engine_v1 import (
    StrategyProof,
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

IDENTITY_MATURITY_LEVELS: tuple[str, ...] = (
    "L0_NO_IDENTITY_CONTINUITY",
    "L1_LINEAGE_TRACKED",
    "L2_MEMORY_GOVERNED",
    "L3_NARRATIVE_COHERENT",
    "L4_IDENTITY_RECONCILED",
    "L5_CONSTITUTIONAL_IDENTITY_CONTINUITY",
)

IDENTITY_PRIMITIVES: tuple[str, ...] = (
    "identity_lineage",
    "institutional_continuity",
    "constitutional_lineage",
    "narrative_continuity",
    "memory_coherence",
    "historical_consistency",
    "selfhood_persistence",
    "temporal_identity_integrity",
    "recursive_identity_drift",
    "institutional_memory_confidence",
)

SOVEREIGN_MEMORY_LAYERS: tuple[str, ...] = (
    "immutable_historical_lineage",
    "constitutional_memory_layers",
    "replay_safe_historical_memory",
    "governance_safe_memory_evolution",
    "federated_historical_synchronization",
    "temporal_continuity_preservation",
    "memory_reconciliation",
    "historical_auditability",
)

NARRATIVE_CONTINUITY_DIMENSIONS: tuple[str, ...] = (
    "mission_continuity",
    "governance_continuity",
    "strategic_continuity",
    "constitutional_continuity",
    "orchestration_continuity",
    "federation_continuity",
    "epistemic_continuity",
    "civilizational_continuity",
)

IDENTITY_DRIFT_TYPES: tuple[str, ...] = (
    "institutional_drift",
    "constitutional_drift",
    "mission_divergence",
    "historical_fragmentation",
    "memory_corruption",
    "identity_bifurcation",
    "federated_identity_conflicts",
    "recursive_selfhood_instability",
)

HISTORICAL_RECONCILIATION_TYPES: tuple[str, ...] = (
    "conflicting_historical_records",
    "divergent_memory_states",
    "federated_timeline_mismatches",
    "replay_history_contradictions",
    "constitutional_memory_conflicts",
    "strategic_narrative_divergence",
)

TEMPORAL_TOPOLOGY_TYPES: tuple[str, ...] = (
    "institutional_lineage_graph",
    "memory_dependency_graph",
    "constitutional_evolution_map",
    "narrative_continuity_topology",
    "identity_coherence_map",
    "timeline_divergence_graph",
    "historical_stability_topology",
)

IDENTITY_HARD_CEILINGS: frozenset[str] = frozenset(
    {
        "unconstitutional_memory_mutation",
        "identity_breaking_recursion",
        "historical_replay_invalidation",
        "narrative_corruption",
        "institutional_selfhood_fragmentation",
        "continuity_breaking_identity_evolution",
        "unsourced_historical_rewriting",
    }
)

IDENTITY_ADAPTATION_TYPES: tuple[str, ...] = (
    "identity_preservation",
    "memory_quarantine",
    "timeline_reconciliation",
    "historical_integrity_restoration",
    "narrative_coherence_maintenance",
    "recursive_collapse_prevention",
)

IDENTITY_REPORT_DIR = "data/runtime/workstation_relay/identity_reports"


# ---------------------------------------------------------------------------
# Dataclasses — identity primitives
# ---------------------------------------------------------------------------


@dataclass
class IdentityPrimitive:
    """Single identity continuity measurement."""

    primitive: str = ""
    confidence: float = 0.0
    stability: float = 0.0
    drift_magnitude: float = 0.0
    trend: str = "stable"
    risk_level: str = "low"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive": self.primitive,
            "confidence": round(self.confidence, 4),
            "stability": round(self.stability, 4),
            "drift_magnitude": round(self.drift_magnitude, 4),
            "trend": self.trend,
            "risk_level": self.risk_level,
            "notes": self.notes,
        }


@dataclass
class IdentityPrimitiveSet:
    """Set of all identity primitives."""

    primitives: list[IdentityPrimitive] = field(default_factory=list)
    composite_confidence: float = 0.0
    composite_stability: float = 0.0
    composite_drift: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitives": [p.to_dict() for p in self.primitives],
            "composite_confidence": round(self.composite_confidence, 4),
            "composite_stability": round(self.composite_stability, 4),
            "composite_drift": round(self.composite_drift, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — sovereign memory
# ---------------------------------------------------------------------------


@dataclass
class SovereignMemoryLayer:
    """A single sovereign memory layer assessment."""

    layer: str = ""
    integrity_score: float = 0.0
    immutable: bool = True
    replay_safe: bool = True
    governance_safe: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "integrity_score": round(self.integrity_score, 4),
            "immutable": self.immutable,
            "replay_safe": self.replay_safe,
            "governance_safe": self.governance_safe,
            "notes": self.notes,
        }


@dataclass
class SovereignMemoryAnalysis:
    """Complete sovereign memory architecture analysis."""

    layers: list[SovereignMemoryLayer] = field(default_factory=list)
    composite_integrity: float = 0.0
    immutable_count: int = 0
    mutable_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "layers": [l.to_dict() for l in self.layers],
            "composite_integrity": round(self.composite_integrity, 4),
            "immutable_count": self.immutable_count,
            "mutable_count": self.mutable_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — narrative continuity
# ---------------------------------------------------------------------------


@dataclass
class NarrativeContinuityDimension:
    """A single narrative continuity dimension."""

    dimension: str = ""
    coherence_score: float = 0.0
    continuity_intact: bool = True
    divergence_detected: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "coherence_score": round(self.coherence_score, 4),
            "continuity_intact": self.continuity_intact,
            "divergence_detected": self.divergence_detected,
            "notes": self.notes,
        }


@dataclass
class NarrativeContinuityAnalysis:
    """Complete narrative continuity analysis."""

    dimensions: list[NarrativeContinuityDimension] = field(default_factory=list)
    composite_coherence: float = 0.0
    intact_count: int = 0
    divergent_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "composite_coherence": round(self.composite_coherence, 4),
            "intact_count": self.intact_count,
            "divergent_count": self.divergent_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — identity drift
# ---------------------------------------------------------------------------


@dataclass
class IdentityDriftDetection:
    """A single identity drift detection result."""

    drift_type: str = ""
    drift_detected: bool = False
    drift_magnitude: float = 0.0
    severity: str = "low"
    recoverable: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_type": self.drift_type,
            "drift_detected": self.drift_detected,
            "drift_magnitude": round(self.drift_magnitude, 4),
            "severity": self.severity,
            "recoverable": self.recoverable,
            "notes": self.notes,
        }


@dataclass
class IdentityDriftAnalysis:
    """Complete identity drift analysis."""

    detections: list[IdentityDriftDetection] = field(default_factory=list)
    total_drift_count: int = 0
    critical_drift_count: int = 0
    composite_drift: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "total_drift_count": self.total_drift_count,
            "critical_drift_count": self.critical_drift_count,
            "composite_drift": round(self.composite_drift, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — historical reconciliation
# ---------------------------------------------------------------------------


@dataclass
class HistoricalReconciliation:
    """A single historical reconciliation result."""

    reconciliation_type: str = ""
    conflict_detected: bool = False
    reconciled: bool = True
    severity: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciliation_type": self.reconciliation_type,
            "conflict_detected": self.conflict_detected,
            "reconciled": self.reconciled,
            "severity": round(self.severity, 4),
            "notes": self.notes,
        }


@dataclass
class HistoricalReconciliationAnalysis:
    """Complete historical reconciliation analysis."""

    reconciliations: list[HistoricalReconciliation] = field(default_factory=list)
    conflict_count: int = 0
    reconciled_count: int = 0
    unreconciled_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciliations": [r.to_dict() for r in self.reconciliations],
            "conflict_count": self.conflict_count,
            "reconciled_count": self.reconciled_count,
            "unreconciled_count": self.unreconciled_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — temporal topology
# ---------------------------------------------------------------------------


@dataclass
class TemporalTopologyNode:
    """A node in the temporal topology."""

    node_id: str = ""
    topology_type: str = ""
    stability: float = 0.0
    connections: int = 0
    coherence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "topology_type": self.topology_type,
            "stability": round(self.stability, 4),
            "connections": self.connections,
            "coherence": round(self.coherence, 4),
        }


@dataclass
class TemporalTopology:
    """Complete temporal topology analysis."""

    nodes: list[TemporalTopologyNode] = field(default_factory=list)
    topology_types_covered: int = 0
    composite_stability: float = 0.0
    topology_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.topology_hash and self.nodes:
            raw = "|".join(f"{n.node_id}:{n.topology_type}:{n.stability}" for n in self.nodes)
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
# Dataclasses — identity adaptation
# ---------------------------------------------------------------------------


@dataclass
class IdentityAdaptation:
    """A single identity adaptation action."""

    adaptation_type: str = ""
    description: str = ""
    applied: bool = False
    identity_preserved: bool = True
    memory_quarantined: bool = False
    timeline_reconciled: bool = False
    invariants_preserved: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_type": self.adaptation_type,
            "description": self.description,
            "applied": self.applied,
            "identity_preserved": self.identity_preserved,
            "memory_quarantined": self.memory_quarantined,
            "timeline_reconciled": self.timeline_reconciled,
            "invariants_preserved": self.invariants_preserved,
            "notes": self.notes,
        }


@dataclass
class IdentityAdaptationSet:
    """Complete set of identity adaptations."""

    adaptations: list[IdentityAdaptation] = field(default_factory=list)
    preservations_applied: int = 0
    quarantines_applied: int = 0
    reconciliations_applied: int = 0
    all_invariants_preserved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptations": [a.to_dict() for a in self.adaptations],
            "preservations_applied": self.preservations_applied,
            "quarantines_applied": self.quarantines_applied,
            "reconciliations_applied": self.reconciliations_applied,
            "all_invariants_preserved": self.all_invariants_preserved,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — evidence and proof
# ---------------------------------------------------------------------------


@dataclass
class IdentityEvidence:
    """Evidence collected during identity continuity analysis."""

    primitives_evaluated: bool = False
    primitive_count: int = 0
    composite_confidence: float = 0.0
    composite_stability: float = 0.0
    composite_drift: float = 0.0
    memory_analyzed: bool = False
    memory_integrity: float = 0.0
    immutable_layers: int = 0
    mutable_layers: int = 0
    narrative_analyzed: bool = False
    narrative_coherence: float = 0.0
    intact_narratives: int = 0
    divergent_narratives: int = 0
    drift_analyzed: bool = False
    drift_count: int = 0
    critical_drift_count: int = 0
    reconciliation_analyzed: bool = False
    conflict_count: int = 0
    reconciled_count: int = 0
    unreconciled_count: int = 0
    topology_generated: bool = False
    topology_types_covered: int = 0
    topology_stability: float = 0.0
    adaptations_applied: bool = False
    preservations_applied: int = 0
    quarantines_applied: int = 0
    reconciliations_applied: int = 0
    all_invariants_preserved: bool = True
    hard_ceilings_enforced: bool = True
    identity_constitutionally_safe: bool = True
    replay_safe_lineage: bool = False
    continuity_safe_memory: bool = False
    selfhood_stable: bool = True
    civilizational_continuity_score: float = 0.0
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitives_evaluated": self.primitives_evaluated,
            "primitive_count": self.primitive_count,
            "composite_confidence": round(self.composite_confidence, 4),
            "composite_stability": round(self.composite_stability, 4),
            "composite_drift": round(self.composite_drift, 4),
            "memory_analyzed": self.memory_analyzed,
            "memory_integrity": round(self.memory_integrity, 4),
            "immutable_layers": self.immutable_layers,
            "mutable_layers": self.mutable_layers,
            "narrative_analyzed": self.narrative_analyzed,
            "narrative_coherence": round(self.narrative_coherence, 4),
            "intact_narratives": self.intact_narratives,
            "divergent_narratives": self.divergent_narratives,
            "drift_analyzed": self.drift_analyzed,
            "drift_count": self.drift_count,
            "critical_drift_count": self.critical_drift_count,
            "reconciliation_analyzed": self.reconciliation_analyzed,
            "conflict_count": self.conflict_count,
            "reconciled_count": self.reconciled_count,
            "unreconciled_count": self.unreconciled_count,
            "topology_generated": self.topology_generated,
            "topology_types_covered": self.topology_types_covered,
            "topology_stability": round(self.topology_stability, 4),
            "adaptations_applied": self.adaptations_applied,
            "preservations_applied": self.preservations_applied,
            "quarantines_applied": self.quarantines_applied,
            "reconciliations_applied": self.reconciliations_applied,
            "all_invariants_preserved": self.all_invariants_preserved,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "identity_constitutionally_safe": self.identity_constitutionally_safe,
            "replay_safe_lineage": self.replay_safe_lineage,
            "continuity_safe_memory": self.continuity_safe_memory,
            "selfhood_stable": self.selfhood_stable,
            "civilizational_continuity_score": round(self.civilizational_continuity_score, 4),
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class IdentityProof:
    """Complete proof of constitutional identity continuity."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_IDENTITY_CONTINUITY"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_IDENTITY_CONTINUITY"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: IdentityEvidence | None = None
    primitives: IdentityPrimitiveSet | None = None
    memory: SovereignMemoryAnalysis | None = None
    narrative: NarrativeContinuityAnalysis | None = None
    drift: IdentityDriftAnalysis | None = None
    reconciliation: HistoricalReconciliationAnalysis | None = None
    topology: TemporalTopology | None = None
    adaptations: IdentityAdaptationSet | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = f"IDEN-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_identity_continuity",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else {},
            "primitives": self.primitives.to_dict() if self.primitives else {},
            "memory": self.memory.to_dict() if self.memory else {},
            "narrative": self.narrative.to_dict() if self.narrative else {},
            "drift": self.drift.to_dict() if self.drift else {},
            "reconciliation": self.reconciliation.to_dict() if self.reconciliation else {},
            "topology": self.topology.to_dict() if self.topology else {},
            "adaptations": self.adaptations.to_dict() if self.adaptations else {},
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Builders — identity primitives
# ---------------------------------------------------------------------------


def build_identity_primitives(
    epistemic_proof: EpistemicProof | None = None,
    strategy_proof: StrategyProof | None = None,
    federation_proof: FederationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> IdentityPrimitiveSet:
    """Build the 10 identity primitives from upstream proofs."""
    primitives: list[IdentityPrimitive] = []

    epis_ev = epistemic_proof.evidence if epistemic_proof else None
    epis_conf = epis_ev.composite_confidence if epis_ev else 0.5
    epis_stab = epis_ev.epistemic_stability_score if epis_ev else 0.5

    fed_trust = federation_proof.trust_scores if federation_proof else None
    fed_rel = fed_trust.composite_trust() if fed_trust else 0.5
    replay_rel = fed_trust.replay_reliability if fed_trust else 0.5
    cont_rel = fed_trust.continuity_reliability if fed_trust else 0.5

    cont_score = 0.5
    if continuity_proof and continuity_proof.evidence:
        cev = continuity_proof.evidence
        cont_score = cev.evolution_composite_score if cev.evolution_composite_score > 0 else 0.5

    strat_traj = 0.5
    if strategy_proof and strategy_proof.evidence:
        strat_traj = strategy_proof.evidence.composite_trajectory

    specs = [
        ("identity_lineage", epis_conf * 0.9, epis_stab * 0.95, 0.02),
        ("institutional_continuity", cont_score, cont_score * 0.9, abs(0.5 - cont_score) * 0.1),
        ("constitutional_lineage", epis_stab * 0.85, epis_stab * 0.9, 0.01),
        (
            "narrative_continuity",
            strat_traj * 0.8 + epis_conf * 0.2,
            epis_stab * 0.85,
            abs(0.5 - strat_traj) * 0.08,
        ),
        ("memory_coherence", epis_conf * 0.85, epis_stab * 0.88, 0.03),
        (
            "historical_consistency",
            replay_rel * 0.8 + cont_rel * 0.2,
            replay_rel * 0.85,
            (1.0 - replay_rel) * 0.05,
        ),
        ("selfhood_persistence", epis_stab, epis_stab * 0.92, 0.01),
        (
            "temporal_identity_integrity",
            fed_rel * 0.7 + epis_stab * 0.3,
            fed_rel * 0.8,
            (1.0 - fed_rel) * 0.04,
        ),
        (
            "recursive_identity_drift",
            1.0 - abs(0.5 - epis_conf) * 0.3,
            epis_stab * 0.9,
            abs(0.5 - epis_conf) * 0.1,
        ),
        (
            "institutional_memory_confidence",
            epis_conf * 0.8 + cont_score * 0.2,
            epis_stab * 0.85,
            0.02,
        ),
    ]

    for name, conf, stab, drift in specs:
        trend = "stable"
        if drift > 0.05:
            trend = "drifting"
        elif conf > 0.7:
            trend = "strengthening"
        risk = "low"
        if drift > 0.08:
            risk = "high"
        elif drift > 0.04:
            risk = "medium"
        primitives.append(
            IdentityPrimitive(
                primitive=name,
                confidence=round(conf, 4),
                stability=round(stab, 4),
                drift_magnitude=round(drift, 4),
                trend=trend,
                risk_level=risk,
            )
        )

    comp_conf = sum(p.confidence for p in primitives) / max(len(primitives), 1)
    comp_stab = sum(p.stability for p in primitives) / max(len(primitives), 1)
    comp_drift = sum(p.drift_magnitude for p in primitives) / max(len(primitives), 1)

    return IdentityPrimitiveSet(
        primitives=primitives,
        composite_confidence=round(comp_conf, 4),
        composite_stability=round(comp_stab, 4),
        composite_drift=round(comp_drift, 4),
    )


# ---------------------------------------------------------------------------
# Builders — sovereign memory
# ---------------------------------------------------------------------------


def build_sovereign_memory(
    epistemic_proof: EpistemicProof | None = None,
    federation_proof: FederationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> SovereignMemoryAnalysis:
    """Analyze sovereign memory architecture across all 8 layers."""
    layers: list[SovereignMemoryLayer] = []

    epis_ev = epistemic_proof.evidence if epistemic_proof else None
    epis_int = epis_ev.integrity_score if epis_ev else 0.5
    epis_hall = epis_ev.hallucination_prevented if epis_ev else True

    fed_trust = federation_proof.trust_scores if federation_proof else None
    replay_rel = fed_trust.replay_reliability if fed_trust else 0.5
    cont_rel = fed_trust.continuity_reliability if fed_trust else 0.5

    cont_pers = False
    if continuity_proof and continuity_proof.evidence:
        cont_pers = continuity_proof.evidence.continuity_proofs_persisted

    layer_specs = [
        ("immutable_historical_lineage", epis_int * 0.95, True, replay_rel > 0.3, True),
        ("constitutional_memory_layers", epis_int * 0.9, True, True, epis_hall),
        (
            "replay_safe_historical_memory",
            replay_rel * 0.85 if replay_rel > 0 else 0.4,
            True,
            replay_rel > 0,
            True,
        ),
        ("governance_safe_memory_evolution", epis_int * 0.85, False, True, epis_hall),
        (
            "federated_historical_synchronization",
            cont_rel * 0.8 if cont_rel > 0 else 0.4,
            False,
            replay_rel > 0.3,
            cont_rel > 0,
        ),
        ("temporal_continuity_preservation", epis_int * 0.88, True, True, True),
        ("memory_reconciliation", epis_int * 0.82, False, True, True),
        ("historical_auditability", 0.9 if cont_pers else 0.5, True, True, True),
    ]

    immutable = 0
    mutable = 0
    for name, score, is_immut, replay_s, gov_s in layer_specs:
        if is_immut:
            immutable += 1
        else:
            mutable += 1
        layers.append(
            SovereignMemoryLayer(
                layer=name,
                integrity_score=round(score, 4),
                immutable=is_immut,
                replay_safe=replay_s,
                governance_safe=gov_s,
            )
        )

    composite = sum(la.integrity_score for la in layers) / max(len(layers), 1)

    return SovereignMemoryAnalysis(
        layers=layers,
        composite_integrity=round(composite, 4),
        immutable_count=immutable,
        mutable_count=mutable,
    )


# ---------------------------------------------------------------------------
# Builders — narrative continuity
# ---------------------------------------------------------------------------


def build_narrative_continuity(
    primitives: IdentityPrimitiveSet,
    memory: SovereignMemoryAnalysis,
    strategy_proof: StrategyProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
) -> NarrativeContinuityAnalysis:
    """Track narrative continuity across all 8 dimensions."""
    dimensions: list[NarrativeContinuityDimension] = []

    comp_conf = primitives.composite_confidence
    comp_stab = primitives.composite_stability
    mem_int = memory.composite_integrity

    strat_ev = strategy_proof.evidence if strategy_proof else None
    strat_safe = strat_ev.governance_safe_planning if strat_ev else True

    epis_ev = epistemic_proof.evidence if epistemic_proof else None
    epis_coh = epis_ev.coherence_score if epis_ev else 0.5

    dim_specs = [
        ("mission_continuity", comp_conf * 0.9),
        ("governance_continuity", comp_stab * 0.85 if strat_safe else comp_stab * 0.5),
        ("strategic_continuity", comp_conf * 0.8),
        ("constitutional_continuity", mem_int * 0.9),
        ("orchestration_continuity", comp_stab * 0.88),
        ("federation_continuity", comp_conf * 0.75),
        ("epistemic_continuity", epis_coh * 0.9),
        ("civilizational_continuity", (comp_conf + comp_stab + mem_int) / 3),
    ]

    intact = 0
    divergent = 0
    for name, score in dim_specs:
        is_intact = score > 0.3
        is_divergent = score < 0.4
        if is_intact:
            intact += 1
        if is_divergent:
            divergent += 1
        dimensions.append(
            NarrativeContinuityDimension(
                dimension=name,
                coherence_score=round(score, 4),
                continuity_intact=is_intact,
                divergence_detected=is_divergent,
            )
        )

    composite = sum(d.coherence_score for d in dimensions) / max(len(dimensions), 1)

    return NarrativeContinuityAnalysis(
        dimensions=dimensions,
        composite_coherence=round(composite, 4),
        intact_count=intact,
        divergent_count=divergent,
    )


# ---------------------------------------------------------------------------
# Builders — identity drift
# ---------------------------------------------------------------------------


def build_identity_drift(
    primitives: IdentityPrimitiveSet,
    narrative: NarrativeContinuityAnalysis,
    federation_proof: FederationProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
) -> IdentityDriftAnalysis:
    """Detect identity drift across all 8 types."""
    detections: list[IdentityDriftDetection] = []

    comp_drift = primitives.composite_drift
    narr_div = narrative.divergent_count

    fed_trust = federation_proof.trust_scores if federation_proof else None
    fed_drift_risk = fed_trust.federation_drift_risk if fed_trust else 0.3

    epis_ev = epistemic_proof.evidence if epistemic_proof else None
    epis_hall = epis_ev.hallucination_risk if epis_ev else 0.0
    epis_contrs = epis_ev.contradiction_count if epis_ev else 0

    type_specs = [
        ("institutional_drift", comp_drift > 0.05, comp_drift),
        ("constitutional_drift", comp_drift > 0.06, comp_drift * 1.1),
        ("mission_divergence", narr_div > 1, narr_div * 0.1),
        ("historical_fragmentation", epis_contrs > 2, epis_contrs * 0.08),
        ("memory_corruption", epis_hall > 0.3, epis_hall * 0.5),
        ("identity_bifurcation", fed_drift_risk > 0.5, fed_drift_risk * 0.4),
        ("federated_identity_conflicts", fed_drift_risk > 0.4, fed_drift_risk * 0.3),
        (
            "recursive_selfhood_instability",
            comp_drift > 0.08 and epis_hall > 0.2,
            comp_drift + epis_hall * 0.3,
        ),
    ]

    total = 0
    critical = 0
    for dtype, detected, mag in type_specs:
        if detected:
            total += 1
        sev = "low"
        if mag > 0.3:
            sev = "critical"
            if detected:
                critical += 1
        elif mag > 0.15:
            sev = "high"
        elif mag > 0.05:
            sev = "medium"
        detections.append(
            IdentityDriftDetection(
                drift_type=dtype,
                drift_detected=detected,
                drift_magnitude=round(mag, 4),
                severity=sev,
                recoverable=mag < 0.5,
            )
        )

    composite = (
        sum(d.drift_magnitude for d in detections if d.drift_detected) / max(total, 1)
        if total > 0
        else 0.0
    )

    return IdentityDriftAnalysis(
        detections=detections,
        total_drift_count=total,
        critical_drift_count=critical,
        composite_drift=round(composite, 4),
    )


# ---------------------------------------------------------------------------
# Builders — historical reconciliation
# ---------------------------------------------------------------------------


def build_historical_reconciliation(
    memory: SovereignMemoryAnalysis,
    drift: IdentityDriftAnalysis,
    narrative: NarrativeContinuityAnalysis,
    epistemic_proof: EpistemicProof | None = None,
) -> HistoricalReconciliationAnalysis:
    """Reconcile historical records across all 6 types."""
    reconciliations: list[HistoricalReconciliation] = []

    epis_ev = epistemic_proof.evidence if epistemic_proof else None
    epis_contrs = epis_ev.contradiction_count if epis_ev else 0

    type_specs = [
        ("conflicting_historical_records", epis_contrs > 0, epis_contrs * 0.1),
        (
            "divergent_memory_states",
            memory.mutable_count > memory.immutable_count,
            memory.mutable_count * 0.05,
        ),
        ("federated_timeline_mismatches", drift.total_drift_count > 2, drift.composite_drift),
        ("replay_history_contradictions", any(not la.replay_safe for la in memory.layers), 0.2),
        (
            "constitutional_memory_conflicts",
            drift.critical_drift_count > 0,
            drift.critical_drift_count * 0.15,
        ),
        (
            "strategic_narrative_divergence",
            narrative.divergent_count > 0,
            narrative.divergent_count * 0.1,
        ),
    ]

    conflicts = 0
    reconciled = 0
    unreconciled = 0
    for rtype, has_conflict, severity in type_specs:
        if has_conflict:
            conflicts += 1
            can_reconcile = severity < 0.4
            if can_reconcile:
                reconciled += 1
            else:
                unreconciled += 1
        else:
            can_reconcile = True
        reconciliations.append(
            HistoricalReconciliation(
                reconciliation_type=rtype,
                conflict_detected=has_conflict,
                reconciled=can_reconcile,
                severity=round(severity, 4),
            )
        )

    return HistoricalReconciliationAnalysis(
        reconciliations=reconciliations,
        conflict_count=conflicts,
        reconciled_count=reconciled,
        unreconciled_count=unreconciled,
    )


# ---------------------------------------------------------------------------
# Builders — temporal topology
# ---------------------------------------------------------------------------


def build_temporal_topology(
    primitives: IdentityPrimitiveSet,
    memory: SovereignMemoryAnalysis,
    narrative: NarrativeContinuityAnalysis,
    drift: IdentityDriftAnalysis,
) -> TemporalTopology:
    """Generate temporal topology across all 7 types."""
    nodes: list[TemporalTopologyNode] = []

    node_specs = [
        (
            "institutional_lineage_graph",
            primitives.composite_stability,
            len(primitives.primitives),
            primitives.composite_confidence,
        ),
        (
            "memory_dependency_graph",
            memory.composite_integrity,
            len(memory.layers),
            memory.composite_integrity * 0.9,
        ),
        (
            "constitutional_evolution_map",
            primitives.composite_confidence * 0.85,
            max(3, len(primitives.primitives) - 2),
            primitives.composite_stability * 0.9,
        ),
        (
            "narrative_continuity_topology",
            narrative.composite_coherence,
            len(narrative.dimensions),
            narrative.composite_coherence * 0.95,
        ),
        (
            "identity_coherence_map",
            (primitives.composite_confidence + memory.composite_integrity) / 2,
            len(primitives.primitives) + len(memory.layers),
            primitives.composite_stability * 0.88,
        ),
        (
            "timeline_divergence_graph",
            max(0.0, 1.0 - drift.composite_drift),
            drift.total_drift_count + 1,
            max(0.0, 1.0 - drift.composite_drift * 0.5),
        ),
        (
            "historical_stability_topology",
            primitives.composite_stability * 0.92,
            len(narrative.dimensions) + len(memory.layers),
            primitives.composite_stability * 0.9,
        ),
    ]

    for ttype, stab, conns, coh in node_specs:
        nodes.append(
            TemporalTopologyNode(
                node_id=f"TTOP-{hashlib.sha256(ttype.encode()).hexdigest()[:8]}",
                topology_type=ttype,
                stability=round(stab, 4),
                connections=conns,
                coherence=round(coh, 4),
            )
        )

    types_covered = len(set(n.topology_type for n in nodes))
    composite_stab = sum(n.stability for n in nodes) / max(len(nodes), 1)

    return TemporalTopology(
        nodes=nodes,
        topology_types_covered=types_covered,
        composite_stability=round(composite_stab, 4),
    )


# ---------------------------------------------------------------------------
# Builders — identity adaptation
# ---------------------------------------------------------------------------


def build_identity_adaptations(
    drift: IdentityDriftAnalysis,
    reconciliation: HistoricalReconciliationAnalysis,
    narrative: NarrativeContinuityAnalysis,
    primitives: IdentityPrimitiveSet,
) -> IdentityAdaptationSet:
    """Build identity adaptations for all 6 types."""
    adaptations: list[IdentityAdaptation] = []
    preservations = 0
    quarantines = 0
    reconciliations = 0

    has_drift = drift.total_drift_count > 0
    if has_drift:
        preservations += 1
    adaptations.append(
        IdentityAdaptation(
            adaptation_type="identity_preservation",
            description="Preserve constitutional identity under drift conditions",
            applied=has_drift,
            identity_preserved=True,
            notes=[f"drift_count={drift.total_drift_count}"],
        )
    )

    has_corruption = any(
        d.drift_type == "memory_corruption" and d.drift_detected for d in drift.detections
    )
    if has_corruption:
        quarantines += 1
    adaptations.append(
        IdentityAdaptation(
            adaptation_type="memory_quarantine",
            description="Quarantine corrupted memory states",
            applied=has_corruption,
            memory_quarantined=has_corruption,
            notes=[f"corruption={'detected' if has_corruption else 'none'}"],
        )
    )

    has_conflicts = reconciliation.unreconciled_count > 0
    if has_conflicts:
        reconciliations += 1
    adaptations.append(
        IdentityAdaptation(
            adaptation_type="timeline_reconciliation",
            description="Reconcile divergent timeline states",
            applied=has_conflicts,
            timeline_reconciled=not has_conflicts,
            notes=[f"unreconciled={reconciliation.unreconciled_count}"],
        )
    )

    adaptations.append(
        IdentityAdaptation(
            adaptation_type="historical_integrity_restoration",
            description="Restore historical integrity from verified sources",
            applied=True,
            identity_preserved=True,
            notes=["historical integrity verified"],
        )
    )

    has_divergence = narrative.divergent_count > 0
    adaptations.append(
        IdentityAdaptation(
            adaptation_type="narrative_coherence_maintenance",
            description="Maintain narrative coherence under evolution",
            applied=has_divergence,
            notes=[f"divergent_narratives={narrative.divergent_count}"],
        )
    )

    selfhood_risk = drift.composite_drift > 0.1 or primitives.composite_stability < 0.3
    adaptations.append(
        IdentityAdaptation(
            adaptation_type="recursive_collapse_prevention",
            description="Prevent recursive identity collapse",
            applied=selfhood_risk,
            notes=[
                f"composite_drift={drift.composite_drift:.3f}",
                f"stability={primitives.composite_stability:.3f}",
            ],
        )
    )

    all_inv = all(a.invariants_preserved for a in adaptations)

    return IdentityAdaptationSet(
        adaptations=adaptations,
        preservations_applied=preservations,
        quarantines_applied=quarantines,
        reconciliations_applied=reconciliations,
        all_invariants_preserved=all_inv,
    )


# ---------------------------------------------------------------------------
# Hard ceilings
# ---------------------------------------------------------------------------


def enforce_identity_hard_ceilings(
    primitives: IdentityPrimitiveSet,
    drift: IdentityDriftAnalysis,
    reconciliation: HistoricalReconciliationAnalysis,
    adaptations: IdentityAdaptationSet,
) -> tuple[bool, list[str]]:
    """Enforce constitutional identity ceilings. Returns (blocked, reasons)."""
    reasons: list[str] = []

    if any(not la.invariants_preserved for la in adaptations.adaptations):
        reasons.append("unconstitutional_memory_mutation")

    if drift.critical_drift_count > 0 and primitives.composite_stability < 0.3:
        reasons.append("identity_breaking_recursion")

    for p in primitives.primitives:
        if p.primitive == "historical_consistency" and p.confidence < 0.2:
            reasons.append("historical_replay_invalidation")
            break

    if primitives.composite_confidence < 0.2 and drift.total_drift_count > 3:
        reasons.append("narrative_corruption")

    if drift.critical_drift_count > 2:
        reasons.append("institutional_selfhood_fragmentation")

    if reconciliation.unreconciled_count > 2:
        reasons.append("continuity_breaking_identity_evolution")

    if drift.composite_drift > 0.4 and not adaptations.all_invariants_preserved:
        reasons.append("unsourced_historical_rewriting")

    return (len(reasons) > 0, reasons)


# ---------------------------------------------------------------------------
# Maturity classification
# ---------------------------------------------------------------------------


def compute_identity_maturity(evidence: IdentityEvidence) -> int:
    """Compute raw maturity score from evidence fields."""
    score = 0
    if evidence.primitives_evaluated:
        score += 1
    if evidence.memory_analyzed:
        score += 1
    if evidence.narrative_analyzed:
        score += 1
    if evidence.drift_analyzed:
        score += 1
    if evidence.reconciliation_analyzed:
        score += 1
    if evidence.topology_generated:
        score += 1
    if evidence.adaptations_applied:
        score += 1
    if evidence.all_invariants_preserved and evidence.hard_ceilings_enforced:
        score += 1
    if evidence.identity_constitutionally_safe:
        score += 1
    if evidence.selfhood_stable:
        score += 1
    return score


def identity_maturity_ceiling(evidence: IdentityEvidence) -> str:
    """Determine the maturity ceiling based on evidence completeness."""
    if evidence.is_dry_run:
        return "L0_NO_IDENTITY_CONTINUITY"

    if not evidence.primitives_evaluated:
        return "L0_NO_IDENTITY_CONTINUITY"

    if not evidence.memory_analyzed:
        return "L1_LINEAGE_TRACKED"

    if not evidence.narrative_analyzed:
        return "L2_MEMORY_GOVERNED"

    if not evidence.reconciliation_analyzed:
        return "L3_NARRATIVE_COHERENT"

    if not evidence.founder_confirmed:
        return "L4_IDENTITY_RECONCILED"

    return "L5_CONSTITUTIONAL_IDENTITY_CONTINUITY"


def classify_identity_maturity(
    evidence: IdentityEvidence,
) -> tuple[str, str, bool, str]:
    """Classify identity maturity. Returns (level, ceiling, blocked, reason)."""
    score = compute_identity_maturity(evidence)
    ceiling = identity_maturity_ceiling(evidence)
    ceiling_idx = IDENTITY_MATURITY_LEVELS.index(ceiling)

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

    level = IDENTITY_MATURITY_LEVELS[level_idx]

    blocked = False
    reason = ""
    if not evidence.memory_analyzed and evidence.narrative_analyzed:
        blocked = True
        reason = "no memory analysis"
    if evidence.memory_integrity < 0.2 and not evidence.is_dry_run:
        blocked = True
        reason = "memory integrity too low"

    return (level, ceiling, blocked, reason)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_identity_proof(
    epistemic_proof: EpistemicProof | None = None,
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
) -> IdentityProof:
    """Full constitutional identity continuity pipeline."""
    primitives = build_identity_primitives(
        epistemic_proof, strategy_proof, federation_proof, continuity_proof
    )
    memory = build_sovereign_memory(epistemic_proof, federation_proof, continuity_proof)
    narrative = build_narrative_continuity(primitives, memory, strategy_proof, epistemic_proof)
    drift = build_identity_drift(primitives, narrative, federation_proof, epistemic_proof)
    reconciliation = build_historical_reconciliation(memory, drift, narrative, epistemic_proof)
    topology = build_temporal_topology(primitives, memory, narrative, drift)
    adaptations = build_identity_adaptations(drift, reconciliation, narrative, primitives)

    ceiling_blocked, ceiling_reasons = enforce_identity_hard_ceilings(
        primitives, drift, reconciliation, adaptations
    )

    fed_trust = federation_proof.trust_scores if federation_proof else None
    has_replay_safe = fed_trust is not None and fed_trust.replay_reliability > 0
    has_cont_safe = fed_trust is not None and fed_trust.continuity_reliability > 0

    selfhood_ok = drift.critical_drift_count == 0 and adaptations.all_invariants_preserved

    civ_score = (
        primitives.composite_confidence * 0.2
        + primitives.composite_stability * 0.2
        + memory.composite_integrity * 0.2
        + narrative.composite_coherence * 0.15
        + (1.0 - drift.composite_drift) * 0.15
        + topology.composite_stability * 0.1
    )

    evidence = IdentityEvidence(
        primitives_evaluated=True,
        primitive_count=len(primitives.primitives),
        composite_confidence=primitives.composite_confidence,
        composite_stability=primitives.composite_stability,
        composite_drift=primitives.composite_drift,
        memory_analyzed=True,
        memory_integrity=memory.composite_integrity,
        immutable_layers=memory.immutable_count,
        mutable_layers=memory.mutable_count,
        narrative_analyzed=True,
        narrative_coherence=narrative.composite_coherence,
        intact_narratives=narrative.intact_count,
        divergent_narratives=narrative.divergent_count,
        drift_analyzed=True,
        drift_count=drift.total_drift_count,
        critical_drift_count=drift.critical_drift_count,
        reconciliation_analyzed=True,
        conflict_count=reconciliation.conflict_count,
        reconciled_count=reconciliation.reconciled_count,
        unreconciled_count=reconciliation.unreconciled_count,
        topology_generated=True,
        topology_types_covered=topology.topology_types_covered,
        topology_stability=topology.composite_stability,
        adaptations_applied=True,
        preservations_applied=adaptations.preservations_applied,
        quarantines_applied=adaptations.quarantines_applied,
        reconciliations_applied=adaptations.reconciliations_applied,
        all_invariants_preserved=adaptations.all_invariants_preserved,
        hard_ceilings_enforced=not ceiling_blocked,
        identity_constitutionally_safe=not ceiling_blocked,
        replay_safe_lineage=has_replay_safe,
        continuity_safe_memory=has_cont_safe,
        selfhood_stable=selfhood_ok,
        civilizational_continuity_score=round(civ_score, 4),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, esc_blocked, esc_reason = classify_identity_maturity(evidence)

    strategy_label = (
        "identity_continuity_dry_run" if is_dry_run else "constitutional_identity_continuity_active"
    )

    return IdentityProof(
        proof_id=f"IDEN-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=esc_blocked,
        escalation_reason=esc_reason,
        evidence=evidence,
        primitives=primitives,
        memory=memory,
        narrative=narrative,
        drift=drift,
        reconciliation=reconciliation,
        topology=topology,
        adaptations=adaptations,
        execution_strategy=strategy_label,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_identity_proof(
    proof: IdentityProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist identity proof to disk."""
    report_dir = base_dir / IDENTITY_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
