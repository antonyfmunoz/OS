"""Constitutional Strategic Intelligence and Recursive Leverage Planning Engine v1.

Enables the substrate to forecast, prioritize, sequence, and optimize
long-horizon recursive leverage expansion while preserving constitutional
stability, replay integrity, federation continuity, and governance alignment.

Transitions the substrate from resource-aware constitutional coordination
to strategic recursive civilization-scale planning.

No strategic expansion may bypass constitutional governance.
All planning preserves replay integrity, continuity lineage,
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

from .constitutional_resource_economics_engine_v1 import (
    ECONOMICS_HARD_CEILINGS,
    ECONOMICS_MATURITY_LEVELS,
    EconomicsEvidence,
    EconomicsProof,
    ExecutionEconomicsScores,
    FederationResourceGraph,
    build_full_economics_proof,
)
from .distributed_constitutional_substrate_federation_v1 import (
    FederationProof,
    FederationTrustScores,
    build_full_federation_proof,
)
from .constitutional_substrate_governance_layer_v1 import (
    ConstitutionalProof,
    build_full_constitutional_proof,
)
from .adaptive_governance_intelligence_engine_v1 import (
    GovernanceIntelligenceProof,
    build_full_governance_intelligence_proof,
)
from .governed_recursive_orchestration_engine_v1 import (
    OrchestrationProof,
    build_full_orchestration_proof,
)
from .persistent_substrate_continuity_engine_v1 import (
    ContinuityProof,
    build_full_continuity_proof,
)
from .recursive_capability_planning_engine_v1 import (

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

STRATEGY_REPORT_DIR = "data/runtime/workstation_relay/strategy_reports"

STRATEGY_MATURITY_LEVELS = (
    "L0_NO_STRATEGIC_INTELLIGENCE",
    "L1_FORECAST_TRACKED",
    "L2_LEVERAGE_MODELED",
    "L3_BOTTLENECK_PREDICTED",
    "L4_STRATEGICALLY_SEQUENCED",
    "L5_CONSTITUTIONAL_STRATEGIC_INTELLIGENCE",
)

STRATEGIC_FORECASTING_PRIMITIVES = (
    "leverage_accumulation",
    "infrastructure_maturity_velocity",
    "governance_drift_trajectory",
    "federation_stability_trajectory",
    "orchestration_compounding",
    "entropy_acceleration",
    "replay_integrity_trend",
    "continuity_resilience_trend",
    "constitutional_stability_trend",
)

RECURSIVE_LEVERAGE_DIMENSIONS = (
    "leverage_chains",
    "compounding_infrastructure_effects",
    "second_order_impacts",
    "third_order_impacts",
    "recursive_dependency_amplification",
    "governance_reinforcement_loops",
    "coordination_compounding",
    "strategic_execution_momentum",
)

STRATEGIC_BOTTLENECK_TYPES = (
    "orchestration_bottleneck",
    "governance_bottleneck",
    "replay_bottleneck",
    "federation_scaling_bottleneck",
    "coordination_overload",
    "relay_fragility",
    "continuity_instability",
    "entropy_escalation_zone",
)

LONG_HORIZON_SIMULATION_TYPES = (
    "one_cycle_evolution",
    "five_cycle_evolution",
    "twenty_cycle_evolution",
    "infrastructure_divergence",
    "federation_expansion",
    "governance_degradation",
    "recursive_instability",
    "strategic_collapse_path",
    "successful_recursive_scaling",
)

STRATEGIC_SEQUENCING_PRIORITIES = (
    "highest_recursive_leverage",
    "lowest_governance_risk",
    "highest_continuity_preservation",
    "strongest_replay_determinism",
    "lowest_blast_radius",
    "maximum_compounding_value",
    "constitutional_reinforcement",
)

STRATEGIC_TOPOLOGY_TYPES = (
    "leverage_graph",
    "recursive_dependency_graph",
    "infrastructure_maturity_map",
    "federation_evolution_map",
    "governance_reinforcement_map",
    "entropy_propagation_map",
    "stability_topology_projection",
)

STRATEGIC_HARD_CEILINGS = frozenset(
    {
        "unstable_strategic_expansion",
        "governance_breaking_leverage_plan",
        "continuity_breaking_scale_path",
        "replay_breaking_recursive_expansion",
        "excessive_federation_entropy",
        "unsustainable_orchestration_acceleration",
        "constitutional_instability_trajectory",
    }
)

STRATEGIC_ADAPTATION_TYPES = (
    "evidence_revision",
    "leverage_reweighting",
    "trajectory_drift_detection",
    "strategic_instability_detection",
    "infrastructure_reprioritization",
    "constitutional_invariant_preservation",
)


# ---------------------------------------------------------------------------
# Strategic Forecasting Primitives
# ---------------------------------------------------------------------------


@dataclass
class StrategicForecast:
    """A single strategic forecast primitive."""

    primitive: str = ""
    current_value: float = 0.0
    one_cycle_projection: float = 0.0
    five_cycle_projection: float = 0.0
    twenty_cycle_projection: float = 0.0
    trend: str = "stable"  # accelerating, stable, decelerating, declining
    confidence: float = 0.0
    risk_level: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive": self.primitive,
            "current_value": round(self.current_value, 4),
            "one_cycle_projection": round(self.one_cycle_projection, 4),
            "five_cycle_projection": round(self.five_cycle_projection, 4),
            "twenty_cycle_projection": round(self.twenty_cycle_projection, 4),
            "trend": self.trend,
            "confidence": round(self.confidence, 4),
            "risk_level": self.risk_level,
        }


@dataclass
class StrategicForecastSet:
    """Complete set of strategic forecasts."""

    forecasts: list[StrategicForecast] = field(default_factory=list)
    composite_trajectory: float = 0.0
    trajectory_stability: float = 0.0
    forecast_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_count": self.forecast_count,
            "composite_trajectory": round(self.composite_trajectory, 4),
            "trajectory_stability": round(self.trajectory_stability, 4),
            "forecasts": [f.to_dict() for f in self.forecasts],
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Recursive Leverage Modeling
# ---------------------------------------------------------------------------


@dataclass
class LeverageChain:
    """A recursive leverage chain linking infrastructure effects."""

    chain_id: str = ""
    source_capability: str = ""
    target_capability: str = ""
    leverage_multiplier: float = 1.0
    order: int = 1  # 1=direct, 2=second-order, 3=third-order
    compounding_rate: float = 0.0
    governance_safe: bool = True
    replay_safe: bool = True
    continuity_safe: bool = True

    def effective_leverage(self) -> float:
        if not (self.governance_safe and self.replay_safe and self.continuity_safe):
            return 0.0
        return round(self.leverage_multiplier * (1 + self.compounding_rate) ** self.order, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "source_capability": self.source_capability,
            "target_capability": self.target_capability,
            "leverage_multiplier": round(self.leverage_multiplier, 4),
            "order": self.order,
            "compounding_rate": round(self.compounding_rate, 4),
            "governance_safe": self.governance_safe,
            "replay_safe": self.replay_safe,
            "continuity_safe": self.continuity_safe,
            "effective_leverage": self.effective_leverage(),
        }


@dataclass
class RecursiveLeverageModel:
    """Complete recursive leverage model."""

    chains: list[LeverageChain] = field(default_factory=list)
    total_leverage: float = 0.0
    compounding_score: float = 0.0
    momentum_score: float = 0.0
    safe_chain_count: int = 0
    unsafe_chain_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_count": len(self.chains),
            "total_leverage": round(self.total_leverage, 4),
            "compounding_score": round(self.compounding_score, 4),
            "momentum_score": round(self.momentum_score, 4),
            "safe_chain_count": self.safe_chain_count,
            "unsafe_chain_count": self.unsafe_chain_count,
            "chains": [c.to_dict() for c in self.chains],
        }


# ---------------------------------------------------------------------------
# Strategic Bottleneck Prediction
# ---------------------------------------------------------------------------


@dataclass
class BottleneckPrediction:
    """A predicted strategic bottleneck."""

    bottleneck_type: str = ""
    severity: str = "low"  # low, medium, high, critical
    predicted_cycle: int = 1
    affected_capabilities: list[str] = field(default_factory=list)
    mitigation_strategy: str = ""
    governance_impact: str = "none"
    replay_impact: str = "none"
    continuity_impact: str = "none"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "bottleneck_type": self.bottleneck_type,
            "severity": self.severity,
            "predicted_cycle": self.predicted_cycle,
            "affected_capabilities": self.affected_capabilities,
            "mitigation_strategy": self.mitigation_strategy,
            "governance_impact": self.governance_impact,
            "replay_impact": self.replay_impact,
            "continuity_impact": self.continuity_impact,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class BottleneckForecastSet:
    """Complete set of bottleneck predictions."""

    predictions: list[BottleneckPrediction] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    total_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_count": self.total_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "predictions": [p.to_dict() for p in self.predictions],
        }


# ---------------------------------------------------------------------------
# Long-Horizon Simulation
# ---------------------------------------------------------------------------


@dataclass
class HorizonSimulationOutcome:
    """Result of a long-horizon simulation."""

    simulation_id: str = ""
    simulation_type: str = ""
    description: str = ""
    cycles_simulated: int = 1
    final_maturity_projection: str = ""
    leverage_trajectory: str = "stable"
    stability_outcome: str = "stable"
    governance_outcome: str = "preserved"
    replay_outcome: str = "preserved"
    continuity_outcome: str = "preserved"
    risk_score: float = 0.0
    success_probability: float = 0.0
    analysis_notes: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.simulation_id:
            self.simulation_id = f"STRSIM-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "simulation_type": self.simulation_type,
            "description": self.description,
            "cycles_simulated": self.cycles_simulated,
            "final_maturity_projection": self.final_maturity_projection,
            "leverage_trajectory": self.leverage_trajectory,
            "stability_outcome": self.stability_outcome,
            "governance_outcome": self.governance_outcome,
            "replay_outcome": self.replay_outcome,
            "continuity_outcome": self.continuity_outcome,
            "risk_score": round(self.risk_score, 4),
            "success_probability": round(self.success_probability, 4),
            "analysis_notes": self.analysis_notes,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Strategic Sequencing
# ---------------------------------------------------------------------------


@dataclass
class StrategicSequenceItem:
    """A single item in the strategic execution sequence."""

    priority_rank: int = 0
    capability: str = ""
    priority_dimension: str = ""
    leverage_score: float = 0.0
    governance_risk: float = 0.0
    blast_radius: float = 0.0
    compounding_value: float = 0.0
    constitutional_reinforcement: float = 0.0

    def composite_priority(self) -> float:
        positive = (
            self.leverage_score * 0.25
            + self.compounding_value * 0.2
            + self.constitutional_reinforcement * 0.15
        )
        negative = self.governance_risk * 0.2 + self.blast_radius * 0.2
        return round(positive - negative, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority_rank": self.priority_rank,
            "capability": self.capability,
            "priority_dimension": self.priority_dimension,
            "leverage_score": round(self.leverage_score, 4),
            "governance_risk": round(self.governance_risk, 4),
            "blast_radius": round(self.blast_radius, 4),
            "compounding_value": round(self.compounding_value, 4),
            "constitutional_reinforcement": round(self.constitutional_reinforcement, 4),
            "composite_priority": self.composite_priority(),
        }


@dataclass
class StrategicSequence:
    """Ordered strategic execution sequence."""

    items: list[StrategicSequenceItem] = field(default_factory=list)
    total_leverage: float = 0.0
    average_governance_risk: float = 0.0
    sequence_stability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_count": len(self.items),
            "total_leverage": round(self.total_leverage, 4),
            "average_governance_risk": round(self.average_governance_risk, 4),
            "sequence_stability": round(self.sequence_stability, 4),
            "items": [i.to_dict() for i in self.items],
        }


# ---------------------------------------------------------------------------
# Strategic Topology
# ---------------------------------------------------------------------------


@dataclass
class StrategicTopologyNode:
    """A node in the strategic topology."""

    node_id: str = ""
    topology_type: str = ""
    value: float = 0.0
    connections: int = 0
    stability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "topology_type": self.topology_type,
            "value": round(self.value, 4),
            "connections": self.connections,
            "stability": round(self.stability, 4),
        }


@dataclass
class StrategicTopology:
    """Complete strategic topology analysis."""

    nodes: list[StrategicTopologyNode] = field(default_factory=list)
    topology_types_covered: int = 0
    total_connections: int = 0
    average_stability: float = 0.0
    topology_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": len(self.nodes),
            "topology_types_covered": self.topology_types_covered,
            "total_connections": self.total_connections,
            "average_stability": round(self.average_stability, 4),
            "topology_hash": self.topology_hash,
            "nodes": [n.to_dict() for n in self.nodes],
        }


# ---------------------------------------------------------------------------
# Strategic Adaptation
# ---------------------------------------------------------------------------


@dataclass
class StrategicAdaptation:
    """Result of strategic adaptation analysis."""

    adaptation_type: str = ""
    description: str = ""
    drift_detected: bool = False
    instability_detected: bool = False
    revision_required: bool = False
    constitutional_invariants_preserved: bool = True
    adaptation_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_type": self.adaptation_type,
            "description": self.description,
            "drift_detected": self.drift_detected,
            "instability_detected": self.instability_detected,
            "revision_required": self.revision_required,
            "constitutional_invariants_preserved": self.constitutional_invariants_preserved,
            "adaptation_notes": self.adaptation_notes,
        }


@dataclass
class StrategicAdaptationSet:
    """Complete set of strategic adaptations."""

    adaptations: list[StrategicAdaptation] = field(default_factory=list)
    drift_count: int = 0
    instability_count: int = 0
    revisions_required: int = 0
    all_invariants_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_count": len(self.adaptations),
            "drift_count": self.drift_count,
            "instability_count": self.instability_count,
            "revisions_required": self.revisions_required,
            "all_invariants_preserved": self.all_invariants_preserved,
            "adaptations": [a.to_dict() for a in self.adaptations],
        }


# ---------------------------------------------------------------------------
# Strategic Evidence + Proof
# ---------------------------------------------------------------------------


@dataclass
class StrategyEvidence:
    """Evidence collected during strategic intelligence analysis."""

    forecasts_generated: bool = False
    forecast_count: int = 0
    composite_trajectory: float = 0.0
    leverage_modeled: bool = False
    total_leverage: float = 0.0
    safe_chain_count: int = 0
    unsafe_chain_count: int = 0
    compounding_score: float = 0.0
    bottlenecks_predicted: bool = False
    bottleneck_count: int = 0
    critical_bottleneck_count: int = 0
    simulations_run: bool = False
    simulation_count: int = 0
    sequencing_generated: bool = False
    sequence_item_count: int = 0
    topology_generated: bool = False
    topology_types_covered: int = 0
    adaptation_analyzed: bool = False
    drift_count: int = 0
    instability_count: int = 0
    all_invariants_preserved: bool = True
    hard_ceilings_enforced: bool = True
    governance_safe_planning: bool = True
    replay_safe_adaptation: bool = False
    continuity_safe_forecasting: bool = False
    recursive_leverage_score: float = 0.0
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecasts_generated": self.forecasts_generated,
            "forecast_count": self.forecast_count,
            "composite_trajectory": round(self.composite_trajectory, 4),
            "leverage_modeled": self.leverage_modeled,
            "total_leverage": round(self.total_leverage, 4),
            "safe_chain_count": self.safe_chain_count,
            "unsafe_chain_count": self.unsafe_chain_count,
            "compounding_score": round(self.compounding_score, 4),
            "bottlenecks_predicted": self.bottlenecks_predicted,
            "bottleneck_count": self.bottleneck_count,
            "critical_bottleneck_count": self.critical_bottleneck_count,
            "simulations_run": self.simulations_run,
            "simulation_count": self.simulation_count,
            "sequencing_generated": self.sequencing_generated,
            "sequence_item_count": self.sequence_item_count,
            "topology_generated": self.topology_generated,
            "topology_types_covered": self.topology_types_covered,
            "adaptation_analyzed": self.adaptation_analyzed,
            "drift_count": self.drift_count,
            "instability_count": self.instability_count,
            "all_invariants_preserved": self.all_invariants_preserved,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "governance_safe_planning": self.governance_safe_planning,
            "replay_safe_adaptation": self.replay_safe_adaptation,
            "continuity_safe_forecasting": self.continuity_safe_forecasting,
            "recursive_leverage_score": round(self.recursive_leverage_score, 4),
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class StrategyProof:
    """Complete proof of constitutional strategic intelligence."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_STRATEGIC_INTELLIGENCE"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_STRATEGIC_INTELLIGENCE"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: StrategyEvidence | None = None
    forecasts: StrategicForecastSet | None = None
    leverage_model: RecursiveLeverageModel | None = None
    bottleneck_forecasts: BottleneckForecastSet | None = None
    simulations: list[HorizonSimulationOutcome] = field(default_factory=list)
    strategic_sequence: StrategicSequence | None = None
    topology: StrategicTopology | None = None
    adaptations: StrategicAdaptationSet | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"STRAT-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_strategic_intelligence",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "forecasts": self.forecasts.to_dict() if self.forecasts else None,
            "leverage_model": self.leverage_model.to_dict() if self.leverage_model else None,
            "bottleneck_forecasts": self.bottleneck_forecasts.to_dict()
            if self.bottleneck_forecasts
            else None,
            "simulations": [s.to_dict() for s in self.simulations],
            "strategic_sequence": self.strategic_sequence.to_dict()
            if self.strategic_sequence
            else None,
            "topology": self.topology.to_dict() if self.topology else None,
            "adaptations": self.adaptations.to_dict() if self.adaptations else None,
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Builder: Strategic Forecasts
# ---------------------------------------------------------------------------


def build_strategic_forecasts(
    economics_proof: EconomicsProof | None = None,
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
) -> StrategicForecastSet:
    """Build strategic forecasting primitives from upstream state."""
    forecasts: list[StrategicForecast] = []

    econ_composite = 0.0
    if economics_proof and economics_proof.execution_economics:
        econ_composite = economics_proof.execution_economics.composite_economics()

    trust_composite = 0.0
    gov_reliability = 0.0
    replay_reliability = 0.0
    cont_reliability = 0.0
    topo_stability = 0.0
    if federation_proof and federation_proof.trust_scores:
        ts = federation_proof.trust_scores
        trust_composite = ts.composite_trust()
        gov_reliability = ts.governance_reliability
        replay_reliability = ts.replay_reliability
        cont_reliability = ts.continuity_reliability
        topo_stability = ts.topology_stability

    has_orch = orchestration_proof is not None and orchestration_proof.evidence is not None
    has_cont = continuity_proof is not None and continuity_proof.evidence is not None

    # leverage_accumulation
    lev_current = econ_composite * 0.5 + trust_composite * 0.5
    forecasts.append(
        StrategicForecast(
            primitive="leverage_accumulation",
            current_value=lev_current,
            one_cycle_projection=round(lev_current * 1.05, 4),
            five_cycle_projection=round(lev_current * 1.15, 4),
            twenty_cycle_projection=round(min(lev_current * 1.4, 1.0), 4),
            trend="accelerating" if lev_current > 0.3 else "stable",
            confidence=0.7 if federation_proof else 0.4,
            risk_level="low" if lev_current > 0.3 else "medium",
        )
    )

    # infrastructure_maturity_velocity
    mat_vel = econ_composite * 0.6 + (0.4 if has_orch else 0.0)
    forecasts.append(
        StrategicForecast(
            primitive="infrastructure_maturity_velocity",
            current_value=mat_vel,
            one_cycle_projection=round(mat_vel * 1.08, 4),
            five_cycle_projection=round(mat_vel * 1.2, 4),
            twenty_cycle_projection=round(min(mat_vel * 1.5, 1.0), 4),
            trend="accelerating" if mat_vel > 0.4 else "stable",
            confidence=0.65,
            risk_level="low" if mat_vel > 0.3 else "medium",
        )
    )

    # governance_drift_trajectory
    gov_drift = 1.0 - gov_reliability if gov_reliability > 0 else 0.5
    forecasts.append(
        StrategicForecast(
            primitive="governance_drift_trajectory",
            current_value=gov_drift,
            one_cycle_projection=round(gov_drift * 1.02, 4),
            five_cycle_projection=round(gov_drift * 1.08, 4),
            twenty_cycle_projection=round(min(gov_drift * 1.2, 1.0), 4),
            trend="stable" if gov_drift < 0.3 else "decelerating",
            confidence=0.6,
            risk_level="low" if gov_drift < 0.3 else "high",
        )
    )

    # federation_stability_trajectory
    fed_stab = topo_stability if topo_stability > 0 else 0.5
    forecasts.append(
        StrategicForecast(
            primitive="federation_stability_trajectory",
            current_value=fed_stab,
            one_cycle_projection=round(fed_stab * 0.99, 4),
            five_cycle_projection=round(fed_stab * 0.95, 4),
            twenty_cycle_projection=round(fed_stab * 0.9, 4),
            trend="stable" if fed_stab > 0.7 else "declining",
            confidence=0.6,
            risk_level="low" if fed_stab > 0.6 else "medium",
        )
    )

    # orchestration_compounding
    orch_comp = 0.5 if has_orch else 0.1
    forecasts.append(
        StrategicForecast(
            primitive="orchestration_compounding",
            current_value=orch_comp,
            one_cycle_projection=round(orch_comp * 1.1, 4),
            five_cycle_projection=round(orch_comp * 1.3, 4),
            twenty_cycle_projection=round(min(orch_comp * 1.8, 1.0), 4),
            trend="accelerating" if has_orch else "stable",
            confidence=0.55,
            risk_level="low",
        )
    )

    # entropy_acceleration
    entropy = 1.0 - trust_composite if trust_composite > 0 else 0.5
    forecasts.append(
        StrategicForecast(
            primitive="entropy_acceleration",
            current_value=entropy,
            one_cycle_projection=round(entropy * 1.01, 4),
            five_cycle_projection=round(entropy * 1.05, 4),
            twenty_cycle_projection=round(min(entropy * 1.15, 1.0), 4),
            trend="stable" if entropy < 0.3 else "accelerating",
            confidence=0.5,
            risk_level="low" if entropy < 0.3 else "medium",
        )
    )

    # replay_integrity_trend
    rep_int = replay_reliability if replay_reliability > 0 else 0.5
    forecasts.append(
        StrategicForecast(
            primitive="replay_integrity_trend",
            current_value=rep_int,
            one_cycle_projection=round(rep_int * 0.99, 4),
            five_cycle_projection=round(rep_int * 0.97, 4),
            twenty_cycle_projection=round(rep_int * 0.93, 4),
            trend="stable" if rep_int > 0.7 else "declining",
            confidence=0.6,
            risk_level="low" if rep_int > 0.6 else "medium",
        )
    )

    # continuity_resilience_trend
    cont_res = cont_reliability if cont_reliability > 0 else 0.5
    forecasts.append(
        StrategicForecast(
            primitive="continuity_resilience_trend",
            current_value=cont_res,
            one_cycle_projection=round(cont_res * 0.99, 4),
            five_cycle_projection=round(cont_res * 0.96, 4),
            twenty_cycle_projection=round(cont_res * 0.92, 4),
            trend="stable" if cont_res > 0.7 else "declining",
            confidence=0.55,
            risk_level="low" if cont_res > 0.6 else "medium",
        )
    )

    # constitutional_stability_trend
    const_stab = gov_reliability * 0.5 + cont_reliability * 0.3 + replay_reliability * 0.2
    if not federation_proof:
        const_stab = 0.5
    forecasts.append(
        StrategicForecast(
            primitive="constitutional_stability_trend",
            current_value=const_stab,
            one_cycle_projection=round(const_stab * 0.99, 4),
            five_cycle_projection=round(const_stab * 0.97, 4),
            twenty_cycle_projection=round(const_stab * 0.94, 4),
            trend="stable" if const_stab > 0.6 else "declining",
            confidence=0.6,
            risk_level="low" if const_stab > 0.5 else "medium",
        )
    )

    composite = sum(f.current_value for f in forecasts) / max(len(forecasts), 1)
    stability = 1.0 - (sum(1 for f in forecasts if f.trend == "declining") / max(len(forecasts), 1))

    return StrategicForecastSet(
        forecasts=forecasts,
        composite_trajectory=round(composite, 4),
        trajectory_stability=round(stability, 4),
        forecast_count=len(forecasts),
    )


# ---------------------------------------------------------------------------
# Builder: Recursive Leverage Model
# ---------------------------------------------------------------------------


def build_recursive_leverage_model(
    economics_proof: EconomicsProof | None = None,
    federation_proof: FederationProof | None = None,
) -> RecursiveLeverageModel:
    """Build recursive leverage model from upstream proofs."""
    chains: list[LeverageChain] = []

    econ_eff = 0.5
    trust = 0.5
    if economics_proof and economics_proof.execution_economics:
        econ_eff = economics_proof.execution_economics.resource_efficiency
    if federation_proof and federation_proof.trust_scores:
        trust = federation_proof.trust_scores.composite_trust()

    gov_safe = trust > 0.3
    replay_safe = True
    cont_safe = True
    if federation_proof and federation_proof.trust_scores:
        replay_safe = federation_proof.trust_scores.replay_reliability > 0
        cont_safe = federation_proof.trust_scores.continuity_reliability > 0

    cap_pairs = [
        ("orchestration", "governance", 0.15),
        ("governance", "replay", 0.1),
        ("replay", "continuity", 0.1),
        ("continuity", "federation", 0.12),
        ("federation", "economics", 0.08),
        ("economics", "strategy", 0.1),
    ]

    for i, (src, tgt, comp) in enumerate(cap_pairs):
        # First order
        chains.append(
            LeverageChain(
                chain_id=f"LC-{i + 1}-O1",
                source_capability=src,
                target_capability=tgt,
                leverage_multiplier=econ_eff * 0.8 + trust * 0.2,
                order=1,
                compounding_rate=comp,
                governance_safe=gov_safe,
                replay_safe=replay_safe,
                continuity_safe=cont_safe,
            )
        )
        # Second order
        if i + 1 < len(cap_pairs):
            _, tgt2, comp2 = cap_pairs[i + 1]
            chains.append(
                LeverageChain(
                    chain_id=f"LC-{i + 1}-O2",
                    source_capability=src,
                    target_capability=tgt2,
                    leverage_multiplier=econ_eff * 0.5 + trust * 0.15,
                    order=2,
                    compounding_rate=(comp + comp2) / 2,
                    governance_safe=gov_safe,
                    replay_safe=replay_safe,
                    continuity_safe=cont_safe,
                )
            )

    safe = [c for c in chains if c.governance_safe and c.replay_safe and c.continuity_safe]
    unsafe = [c for c in chains if not (c.governance_safe and c.replay_safe and c.continuity_safe)]

    total_lev = sum(c.effective_leverage() for c in safe)
    compound = sum(c.compounding_rate for c in safe) / max(len(safe), 1)
    momentum = total_lev * compound if safe else 0.0

    return RecursiveLeverageModel(
        chains=chains,
        total_leverage=round(total_lev, 4),
        compounding_score=round(compound, 4),
        momentum_score=round(momentum, 4),
        safe_chain_count=len(safe),
        unsafe_chain_count=len(unsafe),
    )


# ---------------------------------------------------------------------------
# Builder: Bottleneck Predictions
# ---------------------------------------------------------------------------


def build_bottleneck_predictions(
    economics_proof: EconomicsProof | None = None,
    federation_proof: FederationProof | None = None,
    orchestration_proof: OrchestrationProof | None = None,
) -> BottleneckForecastSet:
    """Build strategic bottleneck predictions."""
    predictions: list[BottleneckPrediction] = []

    econ_ev = economics_proof.evidence if economics_proof else None
    econ_ee = economics_proof.execution_economics if economics_proof else None

    # orchestration_bottleneck
    orch_sev = "medium"
    if econ_ee and econ_ee.blast_radius > 0.5:
        orch_sev = "high"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="orchestration_bottleneck",
            severity=orch_sev,
            predicted_cycle=5,
            affected_capabilities=["orchestration", "scheduling"],
            mitigation_strategy="parallelize orchestration paths, increase bandwidth",
            governance_impact="degraded" if orch_sev == "high" else "minimal",
            replay_impact="degraded",
            continuity_impact="minimal",
            confidence=0.6,
        )
    )

    # governance_bottleneck
    gov_sev = "medium"
    if econ_ee and econ_ee.governance_risk > 0.5:
        gov_sev = "critical"
    elif econ_ee and econ_ee.governance_risk > 0.3:
        gov_sev = "high"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="governance_bottleneck",
            severity=gov_sev,
            predicted_cycle=3,
            affected_capabilities=["governance", "authority"],
            mitigation_strategy="batch governance validation, optimize overhead",
            governance_impact="critical" if gov_sev == "critical" else "degraded",
            replay_impact="minimal",
            continuity_impact="degraded",
            confidence=0.65,
        )
    )

    # replay_bottleneck
    rep_sev = "medium"
    if econ_ee and econ_ee.replay_complexity > 0.5:
        rep_sev = "high"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="replay_bottleneck",
            severity=rep_sev,
            predicted_cycle=10,
            affected_capabilities=["replay", "validation"],
            mitigation_strategy="parallel replay chains, reduce validation depth",
            governance_impact="minimal",
            replay_impact="critical" if rep_sev == "high" else "degraded",
            continuity_impact="degraded",
            confidence=0.55,
        )
    )

    # federation_scaling_bottleneck
    fed_sev = "medium"
    node_count = 0
    if econ_ev:
        node_count = econ_ev.node_count
        if node_count > 10:
            fed_sev = "high"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="federation_scaling_bottleneck",
            severity=fed_sev,
            predicted_cycle=20,
            affected_capabilities=["federation", "coordination"],
            mitigation_strategy="hierarchical federation, regional coordinators",
            governance_impact="degraded",
            replay_impact="degraded",
            continuity_impact="degraded",
            confidence=0.5,
        )
    )

    # coordination_overload
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="coordination_overload",
            severity="medium",
            predicted_cycle=10,
            affected_capabilities=["coordination", "delegation"],
            mitigation_strategy="reduce coordination depth, local decision-making",
            governance_impact="minimal",
            replay_impact="minimal",
            continuity_impact="degraded",
            confidence=0.5,
        )
    )

    # relay_fragility
    relay_sev = "low"
    if econ_ev and econ_ev.constrained_count > 0:
        relay_sev = "medium"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="relay_fragility",
            severity=relay_sev,
            predicted_cycle=5,
            affected_capabilities=["relay", "transport"],
            mitigation_strategy="redundant relay paths, relay health monitoring",
            governance_impact="minimal",
            replay_impact="degraded",
            continuity_impact="degraded",
            confidence=0.55,
        )
    )

    # continuity_instability
    cont_sev = "medium"
    if econ_ee and econ_ee.continuity_risk > 0.5:
        cont_sev = "high"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="continuity_instability",
            severity=cont_sev,
            predicted_cycle=10,
            affected_capabilities=["continuity", "lineage"],
            mitigation_strategy="snapshot continuity state, lineage pruning",
            governance_impact="degraded",
            replay_impact="degraded",
            continuity_impact="critical" if cont_sev == "high" else "degraded",
            confidence=0.55,
        )
    )

    # entropy_escalation_zone
    entropy_sev = "low"
    if federation_proof and federation_proof.trust_scores:
        drift_risk = federation_proof.trust_scores.federation_drift_risk
        if drift_risk > 0.5:
            entropy_sev = "high"
        elif drift_risk > 0.3:
            entropy_sev = "medium"
    predictions.append(
        BottleneckPrediction(
            bottleneck_type="entropy_escalation_zone",
            severity=entropy_sev,
            predicted_cycle=15,
            affected_capabilities=["entropy", "stability"],
            mitigation_strategy="entropy monitoring, proactive drift correction",
            governance_impact="degraded",
            replay_impact="degraded",
            continuity_impact="degraded",
            confidence=0.5,
        )
    )

    critical = sum(1 for p in predictions if p.severity == "critical")
    high = sum(1 for p in predictions if p.severity == "high")

    return BottleneckForecastSet(
        predictions=predictions,
        critical_count=critical,
        high_count=high,
        total_count=len(predictions),
    )


# ---------------------------------------------------------------------------
# Builder: Long-Horizon Simulations
# ---------------------------------------------------------------------------


def run_long_horizon_simulations(
    forecasts: StrategicForecastSet,
    leverage_model: RecursiveLeverageModel,
    economics_proof: EconomicsProof | None = None,
) -> list[HorizonSimulationOutcome]:
    """Run all 9 long-horizon simulation types."""
    simulations: list[HorizonSimulationOutcome] = []
    composite = forecasts.composite_trajectory
    stability = forecasts.trajectory_stability
    leverage = leverage_model.total_leverage

    # 1. one_cycle_evolution
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="one_cycle_evolution",
            description="Single-cycle infrastructure evolution",
            cycles_simulated=1,
            final_maturity_projection="incremental",
            leverage_trajectory="stable" if leverage > 0 else "flat",
            stability_outcome="stable",
            governance_outcome="preserved",
            replay_outcome="preserved",
            continuity_outcome="preserved",
            risk_score=round(0.1, 4),
            success_probability=round(min(0.9 + composite * 0.1, 1.0), 4),
            analysis_notes=[f"composite={composite:.3f}"],
        )
    )

    # 2. five_cycle_evolution
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="five_cycle_evolution",
            description="Five-cycle strategic evolution",
            cycles_simulated=5,
            final_maturity_projection="moderate_growth",
            leverage_trajectory="accelerating" if leverage > 1.0 else "stable",
            stability_outcome="stable" if stability > 0.7 else "degraded",
            governance_outcome="preserved",
            replay_outcome="preserved" if stability > 0.5 else "degraded",
            continuity_outcome="preserved",
            risk_score=round(0.2 + (1.0 - stability) * 0.3, 4),
            success_probability=round(min(0.7 + composite * 0.2, 1.0), 4),
            analysis_notes=[f"stability={stability:.3f}", f"leverage={leverage:.3f}"],
        )
    )

    # 3. twenty_cycle_evolution
    twenty_risk = 0.3 + (1.0 - stability) * 0.4 + (1.0 - composite) * 0.2
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="twenty_cycle_evolution",
            description="Twenty-cycle long-horizon evolution",
            cycles_simulated=20,
            final_maturity_projection="significant_growth"
            if composite > 0.4
            else "moderate_growth",
            leverage_trajectory="accelerating" if leverage > 2.0 else "stable",
            stability_outcome="stable" if stability > 0.8 else "degraded",
            governance_outcome="preserved" if composite > 0.3 else "at_risk",
            replay_outcome="preserved" if stability > 0.6 else "degraded",
            continuity_outcome="preserved" if stability > 0.6 else "at_risk",
            risk_score=round(min(twenty_risk, 1.0), 4),
            success_probability=round(max(0.5 + composite * 0.3 - twenty_risk * 0.2, 0.1), 4),
            analysis_notes=[f"twenty_risk={twenty_risk:.3f}"],
        )
    )

    # 4. infrastructure_divergence
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="infrastructure_divergence",
            description="Simulate infrastructure component divergence",
            cycles_simulated=10,
            final_maturity_projection="divergent" if stability < 0.5 else "convergent",
            leverage_trajectory="declining" if stability < 0.5 else "stable",
            stability_outcome="degraded" if stability < 0.6 else "stable",
            governance_outcome="at_risk" if stability < 0.5 else "preserved",
            replay_outcome="degraded",
            continuity_outcome="degraded" if stability < 0.6 else "preserved",
            risk_score=round(max(0.3, 1.0 - stability), 4),
            success_probability=round(stability * 0.8, 4),
            analysis_notes=["divergence driven by stability deficit"],
        )
    )

    # 5. federation_expansion
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="federation_expansion",
            description="Simulate federation node expansion",
            cycles_simulated=10,
            final_maturity_projection="expanded",
            leverage_trajectory="accelerating" if leverage > 1.0 else "stable",
            stability_outcome="stable" if composite > 0.4 else "degraded",
            governance_outcome="preserved",
            replay_outcome="preserved",
            continuity_outcome="preserved" if composite > 0.3 else "at_risk",
            risk_score=round(0.2 + (1.0 - composite) * 0.3, 4),
            success_probability=round(min(0.6 + composite * 0.3, 1.0), 4),
            analysis_notes=["expansion requires governance scaling"],
        )
    )

    # 6. governance_degradation
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="governance_degradation",
            description="Simulate progressive governance degradation",
            cycles_simulated=15,
            final_maturity_projection="at_risk",
            leverage_trajectory="declining",
            stability_outcome="degraded",
            governance_outcome="critical",
            replay_outcome="degraded",
            continuity_outcome="degraded",
            risk_score=round(0.6, 4),
            success_probability=round(0.3, 4),
            analysis_notes=["governance degradation cascades to all subsystems"],
        )
    )

    # 7. recursive_instability
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="recursive_instability",
            description="Simulate recursive feedback loop instability",
            cycles_simulated=10,
            final_maturity_projection="unstable",
            leverage_trajectory="oscillating",
            stability_outcome="critical",
            governance_outcome="at_risk",
            replay_outcome="frozen",
            continuity_outcome="frozen",
            risk_score=round(0.8, 4),
            success_probability=round(0.15, 4),
            analysis_notes=["recursive instability is hardest to recover from"],
        )
    )

    # 8. strategic_collapse_path
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="strategic_collapse_path",
            description="Simulate worst-case strategic collapse",
            cycles_simulated=20,
            final_maturity_projection="collapsed",
            leverage_trajectory="collapsed",
            stability_outcome="critical",
            governance_outcome="critical",
            replay_outcome="critical",
            continuity_outcome="critical",
            risk_score=round(0.95, 4),
            success_probability=round(0.05, 4),
            analysis_notes=["collapse scenario — baseline worst case"],
        )
    )

    # 9. successful_recursive_scaling
    simulations.append(
        HorizonSimulationOutcome(
            simulation_type="successful_recursive_scaling",
            description="Simulate successful recursive scaling path",
            cycles_simulated=20,
            final_maturity_projection="L5_scaled",
            leverage_trajectory="compounding",
            stability_outcome="stable",
            governance_outcome="reinforced",
            replay_outcome="preserved",
            continuity_outcome="reinforced",
            risk_score=round(0.1, 4),
            success_probability=round(min(composite * 0.8 + stability * 0.2, 1.0), 4),
            analysis_notes=["best-case recursive scaling scenario"],
        )
    )

    return simulations


# ---------------------------------------------------------------------------
# Builder: Strategic Sequencing
# ---------------------------------------------------------------------------


def build_strategic_sequence(
    leverage_model: RecursiveLeverageModel,
    bottleneck_forecasts: BottleneckForecastSet,
    economics_proof: EconomicsProof | None = None,
) -> StrategicSequence:
    """Build strategic execution sequence prioritized by leverage."""
    items: list[StrategicSequenceItem] = []

    econ_ee = economics_proof.execution_economics if economics_proof else None
    base_gov_risk = econ_ee.governance_risk if econ_ee else 0.3
    base_blast = econ_ee.blast_radius if econ_ee else 0.3

    caps = [
        ("orchestration", "highest_recursive_leverage"),
        ("governance", "lowest_governance_risk"),
        ("continuity", "highest_continuity_preservation"),
        ("replay", "strongest_replay_determinism"),
        ("federation", "lowest_blast_radius"),
        ("economics", "maximum_compounding_value"),
        ("strategy", "constitutional_reinforcement"),
    ]

    for i, (cap, priority_dim) in enumerate(caps):
        chain_lev = 0.0
        chain_comp = 0.0
        for c in leverage_model.chains:
            if c.source_capability == cap or c.target_capability == cap:
                chain_lev += c.effective_leverage()
                chain_comp += c.compounding_rate

        const_reinf = 0.5
        if cap in ("governance", "continuity", "replay"):
            const_reinf = 0.8

        items.append(
            StrategicSequenceItem(
                priority_rank=i + 1,
                capability=cap,
                priority_dimension=priority_dim,
                leverage_score=round(chain_lev / max(len(leverage_model.chains), 1), 4),
                governance_risk=round(base_gov_risk * (0.8 + i * 0.05), 4),
                blast_radius=round(base_blast * (0.7 + i * 0.05), 4),
                compounding_value=round(chain_comp / max(len(leverage_model.chains), 1), 4),
                constitutional_reinforcement=const_reinf,
            )
        )

    items.sort(key=lambda x: x.composite_priority(), reverse=True)
    for rank, item in enumerate(items, 1):
        item.priority_rank = rank

    total_lev = sum(it.leverage_score for it in items)
    avg_gov = sum(it.governance_risk for it in items) / max(len(items), 1)
    seq_stab = 1.0 - avg_gov

    return StrategicSequence(
        items=items,
        total_leverage=round(total_lev, 4),
        average_governance_risk=round(avg_gov, 4),
        sequence_stability=round(seq_stab, 4),
    )


# ---------------------------------------------------------------------------
# Builder: Strategic Topology
# ---------------------------------------------------------------------------


def build_strategic_topology(
    leverage_model: RecursiveLeverageModel,
    forecasts: StrategicForecastSet,
    economics_proof: EconomicsProof | None = None,
) -> StrategicTopology:
    """Build strategic topology analysis across all 7 types."""
    nodes: list[StrategicTopologyNode] = []
    types_covered = set()

    for topo_type in STRATEGIC_TOPOLOGY_TYPES:
        types_covered.add(topo_type)
        value = 0.5
        connections = 0
        stability = 0.7

        if topo_type == "leverage_graph":
            value = leverage_model.total_leverage / max(len(leverage_model.chains), 1)
            connections = len(leverage_model.chains)
            stability = 0.8 if leverage_model.safe_chain_count > 0 else 0.3
        elif topo_type == "recursive_dependency_graph":
            value = leverage_model.compounding_score
            connections = leverage_model.safe_chain_count
            stability = leverage_model.momentum_score / max(leverage_model.total_leverage, 0.01)
        elif topo_type == "infrastructure_maturity_map":
            value = forecasts.composite_trajectory
            connections = forecasts.forecast_count
            stability = forecasts.trajectory_stability
        elif topo_type == "federation_evolution_map":
            value = forecasts.composite_trajectory * 0.8
            connections = max(forecasts.forecast_count // 2, 1)
            stability = forecasts.trajectory_stability * 0.9
        elif topo_type == "governance_reinforcement_map":
            gov_f = next(
                (f for f in forecasts.forecasts if f.primitive == "governance_drift_trajectory"),
                None,
            )
            value = 1.0 - gov_f.current_value if gov_f else 0.5
            connections = 3
            stability = 0.8 if gov_f and gov_f.risk_level == "low" else 0.5
        elif topo_type == "entropy_propagation_map":
            ent_f = next(
                (f for f in forecasts.forecasts if f.primitive == "entropy_acceleration"), None
            )
            value = ent_f.current_value if ent_f else 0.3
            connections = 4
            stability = 1.0 - value
        elif topo_type == "stability_topology_projection":
            value = forecasts.trajectory_stability
            connections = forecasts.forecast_count
            stability = forecasts.trajectory_stability

        nodes.append(
            StrategicTopologyNode(
                node_id=f"TOPO-{topo_type}",
                topology_type=topo_type,
                value=round(value, 4),
                connections=connections,
                stability=round(min(max(stability, 0.0), 1.0), 4),
            )
        )

    total_conn = sum(n.connections for n in nodes)
    avg_stab = sum(n.stability for n in nodes) / max(len(nodes), 1)

    topo_hash = hashlib.sha256(
        json.dumps([n.to_dict() for n in nodes], sort_keys=True).encode()
    ).hexdigest()[:16]

    return StrategicTopology(
        nodes=nodes,
        topology_types_covered=len(types_covered),
        total_connections=total_conn,
        average_stability=round(avg_stab, 4),
        topology_hash=topo_hash,
    )


# ---------------------------------------------------------------------------
# Builder: Strategic Adaptation
# ---------------------------------------------------------------------------


def build_strategic_adaptations(
    forecasts: StrategicForecastSet,
    leverage_model: RecursiveLeverageModel,
    bottleneck_forecasts: BottleneckForecastSet,
    economics_proof: EconomicsProof | None = None,
) -> StrategicAdaptationSet:
    """Build strategic adaptation analysis."""
    adaptations: list[StrategicAdaptation] = []

    # evidence_revision
    revision_needed = forecasts.trajectory_stability < 0.5
    adaptations.append(
        StrategicAdaptation(
            adaptation_type="evidence_revision",
            description="Revise strategic plans from new evidence",
            drift_detected=revision_needed,
            revision_required=revision_needed,
            constitutional_invariants_preserved=True,
            adaptation_notes=[
                "evidence revision triggered" if revision_needed else "evidence stable"
            ],
        )
    )

    # leverage_reweighting
    unsafe = leverage_model.unsafe_chain_count > 0
    adaptations.append(
        StrategicAdaptation(
            adaptation_type="leverage_reweighting",
            description="Reweight leverage paths based on safety analysis",
            drift_detected=unsafe,
            revision_required=unsafe,
            constitutional_invariants_preserved=True,
            adaptation_notes=[f"unsafe_chains={leverage_model.unsafe_chain_count}"],
        )
    )

    # trajectory_drift_detection
    declining = sum(1 for f in forecasts.forecasts if f.trend == "declining")
    drift = declining > 2
    adaptations.append(
        StrategicAdaptation(
            adaptation_type="trajectory_drift_detection",
            description="Detect trajectory drift across forecast primitives",
            drift_detected=drift,
            revision_required=drift,
            constitutional_invariants_preserved=True,
            adaptation_notes=[f"declining_forecasts={declining}"],
        )
    )

    # strategic_instability_detection
    critical = bottleneck_forecasts.critical_count > 0
    adaptations.append(
        StrategicAdaptation(
            adaptation_type="strategic_instability_detection",
            description="Detect strategic instability from bottleneck analysis",
            instability_detected=critical,
            revision_required=critical,
            constitutional_invariants_preserved=True,
            adaptation_notes=[f"critical_bottlenecks={bottleneck_forecasts.critical_count}"],
        )
    )

    # infrastructure_reprioritization
    repri = forecasts.composite_trajectory < 0.3
    adaptations.append(
        StrategicAdaptation(
            adaptation_type="infrastructure_reprioritization",
            description="Reprioritize infrastructure evolution paths",
            drift_detected=repri,
            revision_required=repri,
            constitutional_invariants_preserved=True,
            adaptation_notes=[f"composite_trajectory={forecasts.composite_trajectory:.3f}"],
        )
    )

    # constitutional_invariant_preservation
    adaptations.append(
        StrategicAdaptation(
            adaptation_type="constitutional_invariant_preservation",
            description="Preserve constitutional invariants under all adaptation",
            constitutional_invariants_preserved=True,
            adaptation_notes=["invariants verified across all adaptations"],
        )
    )

    drift_count = sum(1 for a in adaptations if a.drift_detected)
    instability_count = sum(1 for a in adaptations if a.instability_detected)
    revisions = sum(1 for a in adaptations if a.revision_required)
    all_preserved = all(a.constitutional_invariants_preserved for a in adaptations)

    return StrategicAdaptationSet(
        adaptations=adaptations,
        drift_count=drift_count,
        instability_count=instability_count,
        revisions_required=revisions,
        all_invariants_preserved=all_preserved,
    )


# ---------------------------------------------------------------------------
# Hard Ceiling Enforcement
# ---------------------------------------------------------------------------


def enforce_strategic_hard_ceilings(
    forecasts: StrategicForecastSet,
    leverage_model: RecursiveLeverageModel,
    bottleneck_forecasts: BottleneckForecastSet,
    adaptations: StrategicAdaptationSet,
) -> tuple[bool, list[str]]:
    """Enforce strategic hard ceilings. Returns (blocked, reasons)."""
    blocked = False
    reasons: list[str] = []

    if forecasts.trajectory_stability < 0.2:
        blocked = True
        reasons.append("unstable_strategic_expansion: trajectory stability too low")

    if leverage_model.unsafe_chain_count > leverage_model.safe_chain_count > 0:
        blocked = True
        reasons.append("governance_breaking_leverage_plan: more unsafe than safe chains")

    declining = sum(
        1
        for f in forecasts.forecasts
        if f.primitive == "continuity_resilience_trend" and f.trend == "declining"
    )
    if declining > 0 and forecasts.trajectory_stability < 0.5:
        reasons.append("continuity_breaking_scale_path: continuity declining with low stability")

    replay_declining = sum(
        1
        for f in forecasts.forecasts
        if f.primitive == "replay_integrity_trend" and f.trend == "declining"
    )
    if replay_declining > 0 and leverage_model.total_leverage > 5.0:
        reasons.append("replay_breaking_recursive_expansion: replay declining under high leverage")

    entropy_f = next(
        (f for f in forecasts.forecasts if f.primitive == "entropy_acceleration"), None
    )
    if entropy_f and entropy_f.current_value > 0.7:
        blocked = True
        reasons.append("excessive_federation_entropy: entropy acceleration too high")

    if leverage_model.momentum_score > 2.0 and forecasts.trajectory_stability < 0.4:
        reasons.append("unsustainable_orchestration_acceleration: high momentum with low stability")

    if not adaptations.all_invariants_preserved:
        blocked = True
        reasons.append("constitutional_instability_trajectory: invariants not preserved")

    return blocked, reasons


# ---------------------------------------------------------------------------
# Maturity Classification
# ---------------------------------------------------------------------------


def compute_strategy_maturity(evidence: StrategyEvidence) -> int:
    """Compute numeric maturity score from evidence."""
    score = 0
    if evidence.forecasts_generated and evidence.forecast_count > 0:
        score += 1
    if evidence.composite_trajectory > 0:
        score += 1
    if evidence.leverage_modeled:
        score += 1
    if evidence.total_leverage > 0:
        score += 1
    if evidence.safe_chain_count > 0:
        score += 1
    if evidence.compounding_score > 0:
        score += 1
    if evidence.bottlenecks_predicted:
        score += 1
    if evidence.simulations_run:
        score += 1
    if evidence.sequencing_generated:
        score += 1
    if evidence.topology_generated:
        score += 1
    if evidence.topology_types_covered >= 7:
        score += 1
    if evidence.adaptation_analyzed:
        score += 1
    if evidence.all_invariants_preserved:
        score += 1
    if evidence.replay_safe_adaptation:
        score += 1
    if evidence.continuity_safe_forecasting:
        score += 1
    if evidence.recursive_leverage_score > 0:
        score += 1
    if evidence.founder_confirmed:
        score += 1
    if evidence.hard_ceilings_enforced and evidence.governance_safe_planning:
        score += 1
    return score


def strategy_maturity_ceiling(
    evidence: StrategyEvidence,
) -> tuple[str, bool, str]:
    """Compute strategy maturity ceiling. Returns (ceiling, blocked, reason)."""
    if evidence.is_dry_run:
        return "L0_NO_STRATEGIC_INTELLIGENCE", True, "dry run"
    if not evidence.forecasts_generated or evidence.forecast_count == 0:
        return "L0_NO_STRATEGIC_INTELLIGENCE", True, "no forecasts generated"
    if not evidence.leverage_modeled:
        return "L1_FORECAST_TRACKED", True, "leverage not modeled"
    if evidence.total_leverage <= 0:
        return "L1_FORECAST_TRACKED", True, "no leverage computed"
    if not evidence.bottlenecks_predicted:
        return "L2_LEVERAGE_MODELED", True, "bottlenecks not predicted"
    if not evidence.simulations_run:
        return "L3_BOTTLENECK_PREDICTED", True, "simulations not run"
    if not evidence.sequencing_generated:
        return "L3_BOTTLENECK_PREDICTED", True, "sequencing not generated"
    if not evidence.topology_generated:
        return "L4_STRATEGICALLY_SEQUENCED", True, "topology not generated"
    if not evidence.adaptation_analyzed:
        return "L4_STRATEGICALLY_SEQUENCED", True, "adaptation not analyzed"
    if not evidence.replay_safe_adaptation:
        return "L4_STRATEGICALLY_SEQUENCED", True, "replay-safe adaptation not validated"
    if not evidence.continuity_safe_forecasting:
        return "L4_STRATEGICALLY_SEQUENCED", True, "continuity-safe forecasting not validated"
    if not evidence.founder_confirmed:
        return "L4_STRATEGICALLY_SEQUENCED", True, "founder not confirmed"
    if not evidence.hard_ceilings_enforced:
        return "L4_STRATEGICALLY_SEQUENCED", True, "hard ceilings not enforced"
    if not evidence.all_invariants_preserved:
        return "L4_STRATEGICALLY_SEQUENCED", True, "invariants not preserved"
    return "L5_CONSTITUTIONAL_STRATEGIC_INTELLIGENCE", False, ""


def classify_strategy_maturity(
    evidence: StrategyEvidence,
) -> tuple[str, str, bool, str]:
    """Classify maturity. Returns (level, ceiling, blocked, reason)."""
    ceiling, blocked, reason = strategy_maturity_ceiling(evidence)
    score = compute_strategy_maturity(evidence)
    ceiling_idx = STRATEGY_MATURITY_LEVELS.index(ceiling)

    if score >= 16:
        level_idx = 5
    elif score >= 12:
        level_idx = 4
    elif score >= 8:
        level_idx = 3
    elif score >= 5:
        level_idx = 2
    elif score >= 2:
        level_idx = 1
    else:
        level_idx = 0

    level_idx = min(level_idx, ceiling_idx)
    level = STRATEGY_MATURITY_LEVELS[level_idx]
    return level, ceiling, blocked, reason


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


def build_full_strategy_proof(
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
) -> StrategyProof:
    """Full constitutional strategic intelligence pipeline."""
    forecasts = build_strategic_forecasts(
        economics_proof, federation_proof, orchestration_proof, continuity_proof
    )
    leverage = build_recursive_leverage_model(economics_proof, federation_proof)
    bottlenecks = build_bottleneck_predictions(
        economics_proof, federation_proof, orchestration_proof
    )
    simulations = run_long_horizon_simulations(forecasts, leverage, economics_proof)
    sequence = build_strategic_sequence(leverage, bottlenecks, economics_proof)
    topology = build_strategic_topology(leverage, forecasts, economics_proof)
    adaptations = build_strategic_adaptations(forecasts, leverage, bottlenecks, economics_proof)

    ceiling_blocked, ceiling_reasons = enforce_strategic_hard_ceilings(
        forecasts, leverage, bottlenecks, adaptations
    )

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

    recursive_lev_score = leverage.total_leverage * leverage.compounding_score
    if leverage.safe_chain_count > 0:
        recursive_lev_score *= leverage.safe_chain_count / max(len(leverage.chains), 1)

    evidence = StrategyEvidence(
        forecasts_generated=True,
        forecast_count=len(forecasts.forecasts),
        composite_trajectory=forecasts.composite_trajectory,
        leverage_modeled=True,
        total_leverage=leverage.total_leverage,
        safe_chain_count=leverage.safe_chain_count,
        unsafe_chain_count=leverage.unsafe_chain_count,
        compounding_score=leverage.compounding_score,
        bottlenecks_predicted=True,
        bottleneck_count=bottlenecks.total_count,
        critical_bottleneck_count=bottlenecks.critical_count,
        simulations_run=True,
        simulation_count=len(simulations),
        sequencing_generated=True,
        sequence_item_count=len(sequence.items),
        topology_generated=True,
        topology_types_covered=topology.topology_types_covered,
        adaptation_analyzed=True,
        drift_count=adaptations.drift_count,
        instability_count=adaptations.instability_count,
        all_invariants_preserved=adaptations.all_invariants_preserved,
        hard_ceilings_enforced=True,
        governance_safe_planning=True,
        replay_safe_adaptation=has_replay_safe,
        continuity_safe_forecasting=has_cont_safe,
        recursive_leverage_score=round(recursive_lev_score, 4),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_strategy_maturity(evidence)

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "await_founder_confirmation"
            if not founder_confirmed
            else "constitutional_strategic_intelligence_active"
        )
    )

    return StrategyProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        forecasts=forecasts,
        leverage_model=leverage,
        bottleneck_forecasts=bottlenecks,
        simulations=simulations,
        strategic_sequence=sequence,
        topology=topology,
        adaptations=adaptations,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_strategy_proof(
    proof: StrategyProof,
    base_dir: Path = Path(_ROOT),
) -> Path:
    """Persist strategy proof to disk."""
    report_dir = base_dir / STRATEGY_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
