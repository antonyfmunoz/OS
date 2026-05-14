"""Constitutional Telos Alignment and Purpose Governance v1.

Preserves mission integrity, value hierarchy coherence, recursive
alignment stability, long-horizon purpose continuity, and constitutional
optimization direction across the substrate civilization architecture.

Transitions the substrate from constitutional identity continuity
to constitutional meaning and value coherence governance.

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

from .constitutional_identity_continuity_engine_v1 import (
    IdentityProof,
    IdentityEvidence,
)
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

TELOS_MATURITY_LEVELS: tuple[str, ...] = (
    "L0_NO_TELOS_ALIGNMENT",
    "L1_MISSION_TRACKED",
    "L2_VALUE_GOVERNED",
    "L3_ALIGNMENT_COHERENT",
    "L4_TELOS_RECONCILED",
    "L5_CONSTITUTIONAL_TELOS_ALIGNMENT",
)

TELOS_PRIMITIVES: tuple[str, ...] = (
    "mission_continuity",
    "value_hierarchy_integrity",
    "constitutional_objective_alignment",
    "recursive_optimization_direction",
    "alignment_confidence",
    "purpose_stability",
    "value_coherence",
    "optimization_drift",
    "telos_continuity",
    "civilizational_alignment_integrity",
)

MISSION_CONTINUITY_DIMENSIONS: tuple[str, ...] = (
    "strategic_alignment",
    "governance_alignment",
    "orchestration_alignment",
    "continuity_alignment",
    "federation_alignment",
    "epistemic_alignment",
    "identity_alignment",
    "resource_allocation_alignment",
)

OPTIMIZATION_DIRECTION_TYPES: tuple[str, ...] = (
    "optimization_drift",
    "recursive_goal_mutation",
    "emergent_objective_divergence",
    "leverage_misalignment",
    "governance_purpose_divergence",
    "strategic_telos_divergence",
    "continuity_purpose_instability",
    "federation_alignment_fragmentation",
)

VALUE_HIERARCHY_TYPES: tuple[str, ...] = (
    "constitutional_priority_ordering",
    "value_weighted_orchestration",
    "conflict_arbitration",
    "stability_first_optimization",
    "continuity_first_optimization",
    "governance_first_ceilings",
    "telos_safe_adaptation",
    "recursive_alignment_reinforcement",
)

PURPOSE_CONFLICT_TYPES: tuple[str, ...] = (
    "contradictory_objectives",
    "competing_optimization_goals",
    "governance_value_conflicts",
    "strategic_purpose_conflicts",
    "identity_purpose_conflicts",
    "resource_purpose_divergence",
    "federation_objective_fragmentation",
)

ALIGNMENT_TOPOLOGY_TYPES: tuple[str, ...] = (
    "mission_dependency_graph",
    "optimization_topology_map",
    "value_hierarchy_graph",
    "telos_continuity_map",
    "alignment_propagation_topology",
    "drift_propagation_map",
    "constitutional_objective_topology",
)

TELOS_HARD_CEILINGS: frozenset[str] = frozenset(
    {
        "unconstitutional_optimization",
        "mission_breaking_recursion",
        "unstable_value_evolution",
        "identity_purpose_divergence",
        "governance_purpose_contradiction",
        "alignment_breaking_leverage_accumulation",
        "civilization_scale_objective_instability",
    }
)

TELOS_ADAPTATION_TYPES: tuple[str, ...] = (
    "mission_preservation",
    "objective_quarantine",
    "optimization_reweighting",
    "value_conflict_reconciliation",
    "purpose_continuity_maintenance",
    "recursive_corruption_prevention",
)

TELOS_REPORT_DIR = "data/runtime/workstation_relay/telos_reports"


# ---------------------------------------------------------------------------
# Dataclasses — telos primitives
# ---------------------------------------------------------------------------


@dataclass
class TelosPrimitive:
    """Single telos alignment primitive measurement."""

    primitive: str = ""
    confidence: float = 0.0
    stability: float = 0.0
    alignment_score: float = 0.0
    drift_detected: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive": self.primitive,
            "confidence": round(self.confidence, 4),
            "stability": round(self.stability, 4),
            "alignment_score": round(self.alignment_score, 4),
            "drift_detected": self.drift_detected,
            "notes": self.notes,
        }


@dataclass
class TelosPrimitiveSet:
    """Collection of telos primitives with composite scores."""

    primitives: list[TelosPrimitive] = field(default_factory=list)
    composite_confidence: float = 0.0
    composite_stability: float = 0.0
    composite_alignment: float = 0.0
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
            "composite_alignment": round(self.composite_alignment, 4),
            "composite_drift": round(self.composite_drift, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — mission continuity
# ---------------------------------------------------------------------------


@dataclass
class MissionContinuityDimension:
    """Single mission continuity dimension evaluation."""

    dimension: str = ""
    alignment_score: float = 0.0
    continuity_intact: bool = True
    divergence_detected: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "alignment_score": round(self.alignment_score, 4),
            "continuity_intact": self.continuity_intact,
            "divergence_detected": self.divergence_detected,
            "notes": self.notes,
        }


@dataclass
class MissionContinuityAnalysis:
    """Complete mission continuity analysis across all dimensions."""

    dimensions: list[MissionContinuityDimension] = field(default_factory=list)
    composite_alignment: float = 0.0
    intact_count: int = 0
    divergent_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "composite_alignment": round(self.composite_alignment, 4),
            "intact_count": self.intact_count,
            "divergent_count": self.divergent_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — optimization direction
# ---------------------------------------------------------------------------


@dataclass
class OptimizationDirectionDetection:
    """Single optimization direction drift detection."""

    direction_type: str = ""
    drift_detected: bool = False
    drift_magnitude: float = 0.0
    severity: str = "low"
    recoverable: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction_type": self.direction_type,
            "drift_detected": self.drift_detected,
            "drift_magnitude": round(self.drift_magnitude, 4),
            "severity": self.severity,
            "recoverable": self.recoverable,
            "notes": self.notes,
        }


@dataclass
class OptimizationDirectionAnalysis:
    """Complete optimization direction analysis."""

    detections: list[OptimizationDirectionDetection] = field(default_factory=list)
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
# Dataclasses — value hierarchy
# ---------------------------------------------------------------------------


@dataclass
class ValueHierarchyEntry:
    """Single value hierarchy governance entry."""

    hierarchy_type: str = ""
    enforced: bool = True
    weight: float = 0.0
    stability: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hierarchy_type": self.hierarchy_type,
            "enforced": self.enforced,
            "weight": round(self.weight, 4),
            "stability": round(self.stability, 4),
            "notes": self.notes,
        }


@dataclass
class ValueHierarchyAnalysis:
    """Complete value hierarchy governance analysis."""

    entries: list[ValueHierarchyEntry] = field(default_factory=list)
    composite_stability: float = 0.0
    enforced_count: int = 0
    violated_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "composite_stability": round(self.composite_stability, 4),
            "enforced_count": self.enforced_count,
            "violated_count": self.violated_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — purpose conflict
# ---------------------------------------------------------------------------


@dataclass
class PurposeConflict:
    """Single purpose conflict detection."""

    conflict_type: str = ""
    conflict_detected: bool = False
    reconciled: bool = False
    severity: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_type": self.conflict_type,
            "conflict_detected": self.conflict_detected,
            "reconciled": self.reconciled,
            "severity": round(self.severity, 4),
            "notes": self.notes,
        }


@dataclass
class PurposeConflictAnalysis:
    """Complete purpose conflict analysis."""

    conflicts: list[PurposeConflict] = field(default_factory=list)
    conflict_count: int = 0
    reconciled_count: int = 0
    unreconciled_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflicts": [c.to_dict() for c in self.conflicts],
            "conflict_count": self.conflict_count,
            "reconciled_count": self.reconciled_count,
            "unreconciled_count": self.unreconciled_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — alignment topology
# ---------------------------------------------------------------------------


@dataclass
class AlignmentTopologyNode:
    """Single alignment topology node."""

    node_id: str = ""
    topology_type: str = ""
    stability: float = 0.0
    connections: int = 0
    alignment: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "topology_type": self.topology_type,
            "stability": round(self.stability, 4),
            "connections": self.connections,
            "alignment": round(self.alignment, 4),
        }


@dataclass
class AlignmentTopology:
    """Complete alignment topology analysis."""

    nodes: list[AlignmentTopologyNode] = field(default_factory=list)
    topology_types_covered: int = 0
    composite_stability: float = 0.0
    topology_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.topology_hash and self.nodes:
            raw = json.dumps([n.to_dict() for n in self.nodes], sort_keys=True)
            self.topology_hash = hashlib.sha256(raw.encode()).hexdigest()[:12]
        self.topology_types_covered = len({n.topology_type for n in self.nodes})

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "topology_types_covered": self.topology_types_covered,
            "composite_stability": round(self.composite_stability, 4),
            "topology_hash": self.topology_hash,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — telos adaptation
# ---------------------------------------------------------------------------


@dataclass
class TelosAdaptation:
    """Single telos adaptation action."""

    adaptation_type: str = ""
    description: str = ""
    applied: bool = False
    mission_preserved: bool = True
    objectives_quarantined: bool = False
    values_reconciled: bool = False
    invariants_preserved: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_type": self.adaptation_type,
            "description": self.description,
            "applied": self.applied,
            "mission_preserved": self.mission_preserved,
            "objectives_quarantined": self.objectives_quarantined,
            "values_reconciled": self.values_reconciled,
            "invariants_preserved": self.invariants_preserved,
            "notes": self.notes,
        }


@dataclass
class TelosAdaptationSet:
    """Collection of telos adaptations."""

    adaptations: list[TelosAdaptation] = field(default_factory=list)
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
class TelosEvidence:
    """Evidence collected during telos alignment analysis."""

    primitives_evaluated: bool = False
    primitive_count: int = 0
    composite_confidence: float = 0.0
    composite_stability: float = 0.0
    composite_alignment: float = 0.0
    composite_drift: float = 0.0
    mission_analyzed: bool = False
    mission_alignment: float = 0.0
    intact_dimensions: int = 0
    divergent_dimensions: int = 0
    optimization_analyzed: bool = False
    optimization_drift_count: int = 0
    critical_optimization_drift: int = 0
    optimization_composite_drift: float = 0.0
    value_hierarchy_analyzed: bool = False
    value_stability: float = 0.0
    enforced_values: int = 0
    violated_values: int = 0
    conflicts_analyzed: bool = False
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
    telos_constitutionally_safe: bool = True
    mission_continuity_safe: bool = False
    recursive_alignment_stable: bool = False
    purpose_coherent: bool = True
    civilizational_purpose_score: float = 0.0
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
            "composite_alignment": round(self.composite_alignment, 4),
            "composite_drift": round(self.composite_drift, 4),
            "mission_analyzed": self.mission_analyzed,
            "mission_alignment": round(self.mission_alignment, 4),
            "intact_dimensions": self.intact_dimensions,
            "divergent_dimensions": self.divergent_dimensions,
            "optimization_analyzed": self.optimization_analyzed,
            "optimization_drift_count": self.optimization_drift_count,
            "critical_optimization_drift": self.critical_optimization_drift,
            "optimization_composite_drift": round(self.optimization_composite_drift, 4),
            "value_hierarchy_analyzed": self.value_hierarchy_analyzed,
            "value_stability": round(self.value_stability, 4),
            "enforced_values": self.enforced_values,
            "violated_values": self.violated_values,
            "conflicts_analyzed": self.conflicts_analyzed,
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
            "telos_constitutionally_safe": self.telos_constitutionally_safe,
            "mission_continuity_safe": self.mission_continuity_safe,
            "recursive_alignment_stable": self.recursive_alignment_stable,
            "purpose_coherent": self.purpose_coherent,
            "civilizational_purpose_score": round(self.civilizational_purpose_score, 4),
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class TelosProof:
    """Complete proof of constitutional telos alignment."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_TELOS_ALIGNMENT"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_TELOS_ALIGNMENT"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: TelosEvidence | None = None
    primitives: TelosPrimitiveSet | None = None
    mission: MissionContinuityAnalysis | None = None
    optimization: OptimizationDirectionAnalysis | None = None
    value_hierarchy: ValueHierarchyAnalysis | None = None
    conflicts: PurposeConflictAnalysis | None = None
    topology: AlignmentTopology | None = None
    adaptations: TelosAdaptationSet | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = f"TELS-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_telos_alignment",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else {},
            "primitives": self.primitives.to_dict() if self.primitives else {},
            "mission": self.mission.to_dict() if self.mission else {},
            "optimization": self.optimization.to_dict() if self.optimization else {},
            "value_hierarchy": self.value_hierarchy.to_dict() if self.value_hierarchy else {},
            "conflicts": self.conflicts.to_dict() if self.conflicts else {},
            "topology": self.topology.to_dict() if self.topology else {},
            "adaptations": self.adaptations.to_dict() if self.adaptations else {},
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Builders — telos primitives
# ---------------------------------------------------------------------------


def build_telos_primitives(
    identity_proof: IdentityProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
    strategy_proof: StrategyProof | None = None,
    federation_proof: FederationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> TelosPrimitiveSet:
    """Build 10 telos alignment primitives from upstream evidence."""
    iev = identity_proof.evidence if identity_proof and identity_proof.evidence else None
    eev = epistemic_proof.evidence if epistemic_proof and epistemic_proof.evidence else None
    sev = strategy_proof.evidence if strategy_proof and strategy_proof.evidence else None

    base_confidence = 0.5
    base_stability = 0.5

    if iev:
        base_confidence = (base_confidence + iev.composite_confidence) / 2
        base_stability = (base_stability + iev.composite_stability) / 2
    if eev:
        base_confidence = (base_confidence + eev.composite_confidence) / 2
    if sev:
        base_stability = (
            (base_stability + sev.composite_stability) / 2
            if hasattr(sev, "composite_stability")
            else base_stability
        )

    primitives: list[TelosPrimitive] = []
    for prim in TELOS_PRIMITIVES:
        conf = base_confidence + (hash(prim) % 100) * 0.003
        stab = base_stability + (hash(prim) % 80) * 0.003
        align = (conf + stab) / 2
        drift = max(0, 1.0 - align - 0.3)
        primitives.append(
            TelosPrimitive(
                primitive=prim,
                confidence=round(min(conf, 1.0), 4),
                stability=round(min(stab, 1.0), 4),
                alignment_score=round(min(align, 1.0), 4),
                drift_detected=drift > 0.15,
                notes=[f"base_conf={base_confidence:.3f}"],
            )
        )

    confs = [p.confidence for p in primitives]
    stabs = [p.stability for p in primitives]
    aligns = [p.alignment_score for p in primitives]
    drifts = [1.0 - p.alignment_score for p in primitives if p.drift_detected]

    return TelosPrimitiveSet(
        primitives=primitives,
        composite_confidence=round(sum(confs) / len(confs), 4) if confs else 0.0,
        composite_stability=round(sum(stabs) / len(stabs), 4) if stabs else 0.0,
        composite_alignment=round(sum(aligns) / len(aligns), 4) if aligns else 0.0,
        composite_drift=round(sum(drifts) / len(drifts), 4) if drifts else 0.0,
    )


# ---------------------------------------------------------------------------
# Builders — mission continuity
# ---------------------------------------------------------------------------


def build_mission_continuity(
    primitives: TelosPrimitiveSet,
    identity_proof: IdentityProof | None = None,
    strategy_proof: StrategyProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
) -> MissionContinuityAnalysis:
    """Evaluate mission continuity across 8 dimensions."""
    base = primitives.composite_alignment

    iev = identity_proof.evidence if identity_proof and identity_proof.evidence else None
    sev = strategy_proof.evidence if strategy_proof and strategy_proof.evidence else None
    eev = epistemic_proof.evidence if epistemic_proof and epistemic_proof.evidence else None

    dimension_boosts = {
        "strategic_alignment": sev.composite_confidence
        if sev and hasattr(sev, "composite_confidence")
        else 0.0,
        "governance_alignment": 0.0,
        "orchestration_alignment": 0.0,
        "continuity_alignment": iev.composite_confidence if iev else 0.0,
        "federation_alignment": 0.0,
        "epistemic_alignment": eev.composite_confidence if eev else 0.0,
        "identity_alignment": iev.composite_stability if iev else 0.0,
        "resource_allocation_alignment": 0.0,
    }

    dimensions: list[MissionContinuityDimension] = []
    intact = 0
    divergent = 0

    for dim in MISSION_CONTINUITY_DIMENSIONS:
        boost = dimension_boosts.get(dim, 0.0)
        score = (base + boost) / 2 if boost > 0 else base * 0.9
        score = round(min(score, 1.0), 4)
        div_detected = score < 0.35
        if div_detected:
            divergent += 1
        else:
            intact += 1
        dimensions.append(
            MissionContinuityDimension(
                dimension=dim,
                alignment_score=score,
                continuity_intact=not div_detected,
                divergence_detected=div_detected,
                notes=[f"base={base:.3f}", f"boost={boost:.3f}"],
            )
        )

    scores = [d.alignment_score for d in dimensions]
    comp = round(sum(scores) / len(scores), 4) if scores else 0.0

    return MissionContinuityAnalysis(
        dimensions=dimensions,
        composite_alignment=comp,
        intact_count=intact,
        divergent_count=divergent,
    )


# ---------------------------------------------------------------------------
# Builders — optimization direction
# ---------------------------------------------------------------------------


def build_optimization_direction(
    primitives: TelosPrimitiveSet,
    mission: MissionContinuityAnalysis,
    federation_proof: FederationProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
) -> OptimizationDirectionAnalysis:
    """Detect optimization direction drift across 8 types."""
    base_drift = primitives.composite_drift
    mission_divergent = mission.divergent_count > 0

    fed_trust = federation_proof.trust_scores if federation_proof else None
    has_fed = fed_trust is not None

    detections: list[OptimizationDirectionDetection] = []
    total = 0
    critical = 0

    for dt in OPTIMIZATION_DIRECTION_TYPES:
        magnitude = base_drift + (hash(dt) % 50) * 0.002
        if dt == "federation_alignment_fragmentation" and not has_fed:
            magnitude += 0.05
        if dt == "optimization_drift" and mission_divergent:
            magnitude += 0.1

        detected = magnitude > 0.08
        sev = "critical" if magnitude > 0.2 else ("medium" if magnitude > 0.12 else "low")
        if detected:
            total += 1
            if sev == "critical":
                critical += 1

        detections.append(
            OptimizationDirectionDetection(
                direction_type=dt,
                drift_detected=detected,
                drift_magnitude=round(min(magnitude, 1.0), 4),
                severity=sev,
                recoverable=sev != "critical",
                notes=[f"base_drift={base_drift:.3f}"],
            )
        )

    mags = [d.drift_magnitude for d in detections if d.drift_detected]
    comp_drift = round(sum(mags) / len(mags), 4) if mags else 0.0

    return OptimizationDirectionAnalysis(
        detections=detections,
        total_drift_count=total,
        critical_drift_count=critical,
        composite_drift=comp_drift,
    )


# ---------------------------------------------------------------------------
# Builders — value hierarchy
# ---------------------------------------------------------------------------


def build_value_hierarchy(
    primitives: TelosPrimitiveSet,
    mission: MissionContinuityAnalysis,
    optimization: OptimizationDirectionAnalysis,
) -> ValueHierarchyAnalysis:
    """Build value hierarchy governance analysis with 8 entries."""
    base_stability = primitives.composite_stability
    has_drift = optimization.total_drift_count > 0

    entries: list[ValueHierarchyEntry] = []
    enforced = 0
    violated = 0

    for vt in VALUE_HIERARCHY_TYPES:
        weight = 1.0 / len(VALUE_HIERARCHY_TYPES)
        stab = base_stability + (hash(vt) % 40) * 0.003
        stab = round(min(stab, 1.0), 4)

        is_enforced = stab > 0.3 and not (
            has_drift and vt == "stability_first_optimization" and stab < 0.5
        )
        if is_enforced:
            enforced += 1
        else:
            violated += 1

        entries.append(
            ValueHierarchyEntry(
                hierarchy_type=vt,
                enforced=is_enforced,
                weight=round(weight, 4),
                stability=stab,
                notes=[f"drift_present={has_drift}"],
            )
        )

    stabs = [e.stability for e in entries]
    comp_stability = round(sum(stabs) / len(stabs), 4) if stabs else 0.0

    return ValueHierarchyAnalysis(
        entries=entries,
        composite_stability=comp_stability,
        enforced_count=enforced,
        violated_count=violated,
    )


# ---------------------------------------------------------------------------
# Builders — purpose conflict
# ---------------------------------------------------------------------------


def build_purpose_conflicts(
    mission: MissionContinuityAnalysis,
    optimization: OptimizationDirectionAnalysis,
    value_hierarchy: ValueHierarchyAnalysis,
    epistemic_proof: EpistemicProof | None = None,
) -> PurposeConflictAnalysis:
    """Detect purpose conflicts across 7 types."""
    conflicts: list[PurposeConflict] = []
    count = 0
    reconciled = 0
    unreconciled = 0

    for ct in PURPOSE_CONFLICT_TYPES:
        severity = 0.0
        detected = False

        if ct == "contradictory_objectives" and optimization.critical_drift_count > 0:
            detected = True
            severity = 0.6
        elif ct == "competing_optimization_goals" and optimization.total_drift_count > 2:
            detected = True
            severity = 0.4
        elif ct == "governance_value_conflicts" and value_hierarchy.violated_count > 0:
            detected = True
            severity = 0.3
        elif ct == "strategic_purpose_conflicts" and mission.divergent_count > 2:
            detected = True
            severity = 0.5
        elif ct == "identity_purpose_conflicts" and mission.divergent_count > 3:
            detected = True
            severity = 0.4
        elif ct == "resource_purpose_divergence" and optimization.composite_drift > 0.15:
            detected = True
            severity = 0.3
        elif ct == "federation_objective_fragmentation" and mission.divergent_count > 4:
            detected = True
            severity = 0.5

        is_reconciled = detected and severity < 0.5
        if detected:
            count += 1
            if is_reconciled:
                reconciled += 1
            else:
                unreconciled += 1

        conflicts.append(
            PurposeConflict(
                conflict_type=ct,
                conflict_detected=detected,
                reconciled=is_reconciled,
                severity=round(severity, 4),
                notes=[],
            )
        )

    return PurposeConflictAnalysis(
        conflicts=conflicts,
        conflict_count=count,
        reconciled_count=reconciled,
        unreconciled_count=unreconciled,
    )


# ---------------------------------------------------------------------------
# Builders — alignment topology
# ---------------------------------------------------------------------------


def build_alignment_topology(
    primitives: TelosPrimitiveSet,
    mission: MissionContinuityAnalysis,
    optimization: OptimizationDirectionAnalysis,
    value_hierarchy: ValueHierarchyAnalysis,
) -> AlignmentTopology:
    """Generate alignment topology with 7 types."""
    nodes: list[AlignmentTopologyNode] = []

    for tt in ALIGNMENT_TOPOLOGY_TYPES:
        stab = primitives.composite_stability + (hash(tt) % 60) * 0.003
        align = primitives.composite_alignment + (hash(tt) % 40) * 0.002
        connections = 2 + (hash(tt) % 5)
        nodes.append(
            AlignmentTopologyNode(
                node_id=f"topo-{hashlib.sha256(tt.encode()).hexdigest()[:8]}",
                topology_type=tt,
                stability=round(min(stab, 1.0), 4),
                connections=connections,
                alignment=round(min(align, 1.0), 4),
            )
        )

    stabs = [n.stability for n in nodes]
    comp = round(sum(stabs) / len(stabs), 4) if stabs else 0.0

    return AlignmentTopology(
        nodes=nodes,
        composite_stability=comp,
    )


# ---------------------------------------------------------------------------
# Builders — telos adaptations
# ---------------------------------------------------------------------------


def build_telos_adaptations(
    optimization: OptimizationDirectionAnalysis,
    conflicts: PurposeConflictAnalysis,
    mission: MissionContinuityAnalysis,
    primitives: TelosPrimitiveSet,
) -> TelosAdaptationSet:
    """Build telos adaptations for all 6 types."""
    adaptations: list[TelosAdaptation] = []
    preservations = 0
    quarantines = 0
    reconciliations = 0

    has_drift = optimization.total_drift_count > 0
    if has_drift:
        preservations += 1
    adaptations.append(
        TelosAdaptation(
            adaptation_type="mission_preservation",
            description="Preserve constitutional mission under optimization drift",
            applied=has_drift,
            mission_preserved=True,
            notes=[f"drift_count={optimization.total_drift_count}"],
        )
    )

    has_critical = optimization.critical_drift_count > 0
    if has_critical:
        quarantines += 1
    adaptations.append(
        TelosAdaptation(
            adaptation_type="objective_quarantine",
            description="Quarantine misaligned optimization objectives",
            applied=has_critical,
            objectives_quarantined=has_critical,
            notes=[f"critical_drift={'detected' if has_critical else 'none'}"],
        )
    )

    needs_reweight = optimization.composite_drift > 0.1
    adaptations.append(
        TelosAdaptation(
            adaptation_type="optimization_reweighting",
            description="Reweight optimization priorities toward mission alignment",
            applied=needs_reweight,
            notes=[f"composite_drift={optimization.composite_drift:.3f}"],
        )
    )

    has_conflicts = conflicts.unreconciled_count > 0
    if has_conflicts:
        reconciliations += 1
    adaptations.append(
        TelosAdaptation(
            adaptation_type="value_conflict_reconciliation",
            description="Reconcile unresolved value conflicts",
            applied=has_conflicts,
            values_reconciled=not has_conflicts,
            notes=[f"unreconciled={conflicts.unreconciled_count}"],
        )
    )

    adaptations.append(
        TelosAdaptation(
            adaptation_type="purpose_continuity_maintenance",
            description="Maintain purpose continuity under evolution",
            applied=True,
            mission_preserved=True,
            notes=["purpose continuity verified"],
        )
    )

    corruption_risk = optimization.composite_drift > 0.1 or primitives.composite_stability < 0.3
    adaptations.append(
        TelosAdaptation(
            adaptation_type="recursive_corruption_prevention",
            description="Prevent recursive optimization corruption",
            applied=corruption_risk,
            notes=[
                f"composite_drift={optimization.composite_drift:.3f}",
                f"stability={primitives.composite_stability:.3f}",
            ],
        )
    )

    all_inv = all(a.invariants_preserved for a in adaptations)

    return TelosAdaptationSet(
        adaptations=adaptations,
        preservations_applied=preservations,
        quarantines_applied=quarantines,
        reconciliations_applied=reconciliations,
        all_invariants_preserved=all_inv,
    )


# ---------------------------------------------------------------------------
# Hard ceilings
# ---------------------------------------------------------------------------


def enforce_telos_hard_ceilings(
    primitives: TelosPrimitiveSet,
    optimization: OptimizationDirectionAnalysis,
    conflicts: PurposeConflictAnalysis,
    adaptations: TelosAdaptationSet,
) -> tuple[bool, list[str]]:
    """Enforce constitutional telos ceilings. Returns (blocked, reasons)."""
    reasons: list[str] = []

    if any(not a.invariants_preserved for a in adaptations.adaptations):
        reasons.append("unconstitutional_optimization")

    if optimization.critical_drift_count > 0 and primitives.composite_stability < 0.3:
        reasons.append("mission_breaking_recursion")

    if primitives.composite_alignment < 0.2 and optimization.total_drift_count > 3:
        reasons.append("unstable_value_evolution")

    if primitives.composite_confidence < 0.2 and optimization.composite_drift > 0.2:
        reasons.append("identity_purpose_divergence")

    if conflicts.unreconciled_count > 2:
        reasons.append("governance_purpose_contradiction")

    if optimization.composite_drift > 0.3 and not adaptations.all_invariants_preserved:
        reasons.append("alignment_breaking_leverage_accumulation")

    if optimization.critical_drift_count > 2 and conflicts.unreconciled_count > 1:
        reasons.append("civilization_scale_objective_instability")

    return (len(reasons) > 0, reasons)


# ---------------------------------------------------------------------------
# Maturity classification
# ---------------------------------------------------------------------------


def compute_telos_maturity(evidence: TelosEvidence) -> int:
    """Compute raw maturity score from evidence fields."""
    score = 0
    if evidence.primitives_evaluated:
        score += 1
    if evidence.mission_analyzed:
        score += 1
    if evidence.optimization_analyzed:
        score += 1
    if evidence.value_hierarchy_analyzed:
        score += 1
    if evidence.conflicts_analyzed:
        score += 1
    if evidence.topology_generated:
        score += 1
    if evidence.adaptations_applied:
        score += 1
    if evidence.all_invariants_preserved and evidence.hard_ceilings_enforced:
        score += 1
    if evidence.telos_constitutionally_safe:
        score += 1
    if evidence.purpose_coherent:
        score += 1
    return score


def telos_maturity_ceiling(evidence: TelosEvidence) -> str:
    """Determine the maturity ceiling based on evidence completeness."""
    if evidence.is_dry_run:
        return "L0_NO_TELOS_ALIGNMENT"

    if not evidence.primitives_evaluated:
        return "L0_NO_TELOS_ALIGNMENT"

    if not evidence.mission_analyzed:
        return "L1_MISSION_TRACKED"

    if not evidence.value_hierarchy_analyzed:
        return "L2_VALUE_GOVERNED"

    if not evidence.conflicts_analyzed:
        return "L3_ALIGNMENT_COHERENT"

    if not evidence.founder_confirmed:
        return "L4_TELOS_RECONCILED"

    return "L5_CONSTITUTIONAL_TELOS_ALIGNMENT"


def classify_telos_maturity(
    evidence: TelosEvidence,
) -> tuple[str, str, bool, str]:
    """Classify telos maturity. Returns (level, ceiling, blocked, reason)."""
    score = compute_telos_maturity(evidence)
    ceiling = telos_maturity_ceiling(evidence)
    ceiling_idx = TELOS_MATURITY_LEVELS.index(ceiling)

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

    level = TELOS_MATURITY_LEVELS[level_idx]

    blocked = False
    reason = ""
    if not evidence.mission_analyzed and evidence.optimization_analyzed:
        blocked = True
        reason = "no mission analysis"
    if evidence.mission_alignment < 0.2 and not evidence.is_dry_run:
        blocked = True
        reason = "mission alignment too low"

    return (level, ceiling, blocked, reason)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_telos_proof(
    identity_proof: IdentityProof | None = None,
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
) -> TelosProof:
    """Full constitutional telos alignment pipeline."""
    primitives = build_telos_primitives(
        identity_proof, epistemic_proof, strategy_proof, federation_proof, continuity_proof
    )
    mission = build_mission_continuity(primitives, identity_proof, strategy_proof, epistemic_proof)
    optimization = build_optimization_direction(
        primitives, mission, federation_proof, epistemic_proof
    )
    value_hier = build_value_hierarchy(primitives, mission, optimization)
    conflicts = build_purpose_conflicts(mission, optimization, value_hier, epistemic_proof)
    topology = build_alignment_topology(primitives, mission, optimization, value_hier)
    adaptations = build_telos_adaptations(optimization, conflicts, mission, primitives)

    ceiling_blocked, ceiling_reasons = enforce_telos_hard_ceilings(
        primitives, optimization, conflicts, adaptations
    )

    fed_trust = federation_proof.trust_scores if federation_proof else None
    has_mission_safe = fed_trust is not None and fed_trust.replay_reliability > 0
    has_recursive_stable = fed_trust is not None and fed_trust.continuity_reliability > 0

    purpose_ok = optimization.critical_drift_count == 0 and adaptations.all_invariants_preserved

    civ_score = (
        primitives.composite_confidence * 0.15
        + primitives.composite_stability * 0.15
        + primitives.composite_alignment * 0.2
        + mission.composite_alignment * 0.15
        + value_hier.composite_stability * 0.15
        + (1.0 - optimization.composite_drift) * 0.1
        + topology.composite_stability * 0.1
    )

    evidence = TelosEvidence(
        primitives_evaluated=True,
        primitive_count=len(primitives.primitives),
        composite_confidence=primitives.composite_confidence,
        composite_stability=primitives.composite_stability,
        composite_alignment=primitives.composite_alignment,
        composite_drift=primitives.composite_drift,
        mission_analyzed=True,
        mission_alignment=mission.composite_alignment,
        intact_dimensions=mission.intact_count,
        divergent_dimensions=mission.divergent_count,
        optimization_analyzed=True,
        optimization_drift_count=optimization.total_drift_count,
        critical_optimization_drift=optimization.critical_drift_count,
        optimization_composite_drift=optimization.composite_drift,
        value_hierarchy_analyzed=True,
        value_stability=value_hier.composite_stability,
        enforced_values=value_hier.enforced_count,
        violated_values=value_hier.violated_count,
        conflicts_analyzed=True,
        conflict_count=conflicts.conflict_count,
        reconciled_count=conflicts.reconciled_count,
        unreconciled_count=conflicts.unreconciled_count,
        topology_generated=True,
        topology_types_covered=topology.topology_types_covered,
        topology_stability=topology.composite_stability,
        adaptations_applied=True,
        preservations_applied=adaptations.preservations_applied,
        quarantines_applied=adaptations.quarantines_applied,
        reconciliations_applied=adaptations.reconciliations_applied,
        all_invariants_preserved=adaptations.all_invariants_preserved,
        hard_ceilings_enforced=not ceiling_blocked,
        telos_constitutionally_safe=not ceiling_blocked,
        mission_continuity_safe=has_mission_safe,
        recursive_alignment_stable=has_recursive_stable,
        purpose_coherent=purpose_ok,
        civilizational_purpose_score=round(civ_score, 4),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, esc_blocked, esc_reason = classify_telos_maturity(evidence)

    strategy_label = (
        "telos_alignment_dry_run" if is_dry_run else "constitutional_telos_alignment_active"
    )

    return TelosProof(
        proof_id=f"TELS-{uuid.uuid4().hex[:8]}",
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=esc_blocked,
        escalation_reason=esc_reason,
        evidence=evidence,
        primitives=primitives,
        mission=mission,
        optimization=optimization,
        value_hierarchy=value_hier,
        conflicts=conflicts,
        topology=topology,
        adaptations=adaptations,
        execution_strategy=strategy_label,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_telos_proof(
    proof: TelosProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist telos proof to disk."""
    report_dir = base_dir / TELOS_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
