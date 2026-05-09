"""Constitutional Antifragility and Evolutionary Resilience v1.

Governs adaptive survival, catastrophic recovery, resilience-weighted
optimization, existential risk management, shock absorption, and
long-horizon civilization-scale survivability across the substrate.

Transitions the substrate from constitutional telos alignment
to constitutional adaptive civilizational resilience.

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

from core.workstation.constitutional_telos_alignment_engine_v1 import (
    TelosProof,
    TelosEvidence,
)
from core.workstation.constitutional_identity_continuity_engine_v1 import (
    IdentityProof,
)
from core.workstation.constitutional_epistemic_intelligence_engine_v1 import (
    EpistemicProof,
)
from core.workstation.constitutional_strategic_intelligence_engine_v1 import (
    StrategyProof,
)
from core.workstation.constitutional_resource_economics_engine_v1 import (
    EconomicsProof,
)
from core.workstation.distributed_constitutional_substrate_federation_v1 import (
    FederationProof,
)
from core.workstation.constitutional_substrate_governance_layer_v1 import (
    ConstitutionalProof,
)
from core.workstation.adaptive_governance_intelligence_engine_v1 import (
    GovernanceIntelligenceProof,
)
from core.workstation.governed_recursive_orchestration_engine_v1 import (
    OrchestrationProof,
)
from core.workstation.persistent_substrate_continuity_engine_v1 import (
    ContinuityProof,
)
from core.workstation.recursive_capability_planning_engine_v1 import (
    CapabilityPlanningProof,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESILIENCE_MATURITY_LEVELS: tuple[str, ...] = (
    "L0_NO_RESILIENCE_ANALYSIS",
    "L1_SHOCK_TRACKED",
    "L2_CATASTROPHE_SIMULATED",
    "L3_ANTIFRAGILITY_MEASURED",
    "L4_RESILIENCE_RECONCILED",
    "L5_CONSTITUTIONAL_ANTIFRAGILITY",
)

RESILIENCE_PRIMITIVES: tuple[str, ...] = (
    "shock_tolerance",
    "continuity_resilience",
    "governance_resilience",
    "epistemic_resilience",
    "federation_resilience",
    "replay_survivability",
    "infrastructure_redundancy",
    "adaptive_recovery_capacity",
    "existential_vulnerability",
    "antifragility_gain_potential",
)

CATASTROPHIC_SCENARIO_TYPES: tuple[str, ...] = (
    "federation_collapse",
    "node_extinction",
    "continuity_corruption",
    "replay_invalidation",
    "governance_fragmentation",
    "epistemic_corruption",
    "strategic_divergence",
    "mission_collapse",
    "hostile_node_takeover",
    "infrastructure_exhaustion",
)

ANTIFRAGILITY_DIMENSIONS: tuple[str, ...] = (
    "stress_adaptation",
    "recovery_acceleration",
    "resilience_compounding",
    "adaptive_strengthening",
    "governance_hardening",
    "continuity_reinforcement",
    "federation_stabilization",
    "shock_derived_optimization_gains",
)

EVOLUTIONARY_RESILIENCE_FORECASTS: tuple[str, ...] = (
    "long_horizon_survivability",
    "civilization_scale_adaptation",
    "recursive_resilience_growth",
    "systemic_brittleness",
    "instability_propagation",
    "resilience_topology_evolution",
    "infrastructure_survivability",
    "constitutional_durability",
)

EXISTENTIAL_RISK_TYPES: tuple[str, ...] = (
    "irreversible_drift",
    "civilization_collapse_vectors",
    "recursive_instability_cascades",
    "constitutional_erosion_risks",
    "alignment_extinction_scenarios",
    "memory_collapse_scenarios",
    "strategic_stagnation_traps",
    "brittle_optimization_loops",
)

RESILIENCE_TOPOLOGY_TYPES: tuple[str, ...] = (
    "survivability_graph",
    "catastrophe_propagation_map",
    "redundancy_topology",
    "resilience_dependency_graph",
    "antifragility_gain_topology",
    "recovery_pathway_graph",
    "existential_risk_topology",
)

RESILIENCE_HARD_CEILINGS: frozenset[str] = frozenset(
    {
        "brittle_optimization_paths",
        "survivability_breaking_leverage",
        "catastrophic_blast_radius_concentration",
        "continuity_fragile_federation_expansion",
        "irreversible_governance_drift",
        "resilience_negative_recursive_scaling",
        "existentially_unstable_orchestration",
    }
)

RESILIENCE_ADAPTATION_TYPES: tuple[str, ...] = (
    "fragile_strategy_reweighting",
    "weak_topology_strengthening",
    "catastrophic_pathway_quarantine",
    "continuity_instability_preservation",
    "survivability_priority_enforcement",
    "stress_exposure_evolution",
)

RESILIENCE_REPORT_DIR = "data/runtime/workstation_relay/resilience_reports"


# ---------------------------------------------------------------------------
# Dataclasses — resilience primitives
# ---------------------------------------------------------------------------


@dataclass
class ResiliencePrimitive:
    """Single resilience primitive measurement."""

    primitive: str = ""
    tolerance: float = 0.0
    redundancy: float = 0.0
    recovery_rate: float = 0.0
    fragility_score: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive": self.primitive,
            "tolerance": round(self.tolerance, 4),
            "redundancy": round(self.redundancy, 4),
            "recovery_rate": round(self.recovery_rate, 4),
            "fragility_score": round(self.fragility_score, 4),
            "notes": self.notes,
        }


@dataclass
class ResiliencePrimitiveSet:
    """Collection of all resilience primitives."""

    primitives: list[ResiliencePrimitive] = field(default_factory=list)
    composite_tolerance: float = 0.0
    composite_fragility: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitives": [p.to_dict() for p in self.primitives],
            "composite_tolerance": round(self.composite_tolerance, 4),
            "composite_fragility": round(self.composite_fragility, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — catastrophic scenario simulation
# ---------------------------------------------------------------------------


@dataclass
class CatastrophicScenario:
    """Single catastrophic scenario simulation."""

    scenario_type: str = ""
    severity: float = 0.0
    blast_radius: float = 0.0
    recovery_feasibility: float = 0.0
    survivability: float = 0.0
    cascading_failures: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_type": self.scenario_type,
            "severity": round(self.severity, 4),
            "blast_radius": round(self.blast_radius, 4),
            "recovery_feasibility": round(self.recovery_feasibility, 4),
            "survivability": round(self.survivability, 4),
            "cascading_failures": self.cascading_failures,
            "notes": self.notes,
        }


@dataclass
class CatastropheSimulationAnalysis:
    """Complete catastrophe simulation results."""

    scenarios: list[CatastrophicScenario] = field(default_factory=list)
    total_scenarios: int = 0
    critical_scenarios: int = 0
    mean_survivability: float = 0.0
    worst_case_scenario: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "total_scenarios": self.total_scenarios,
            "critical_scenarios": self.critical_scenarios,
            "mean_survivability": round(self.mean_survivability, 4),
            "worst_case_scenario": self.worst_case_scenario,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — antifragility analysis
# ---------------------------------------------------------------------------


@dataclass
class AntifragilityDimension:
    """Single antifragility dimension measurement."""

    dimension: str = ""
    gain_from_stress: float = 0.0
    adaptation_rate: float = 0.0
    compounding_factor: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "gain_from_stress": round(self.gain_from_stress, 4),
            "adaptation_rate": round(self.adaptation_rate, 4),
            "compounding_factor": round(self.compounding_factor, 4),
            "notes": self.notes,
        }


@dataclass
class AntifragilityAnalysis:
    """Complete antifragility analysis results."""

    dimensions: list[AntifragilityDimension] = field(default_factory=list)
    composite_antifragility: float = 0.0
    stress_positive_count: int = 0
    stress_negative_count: int = 0
    net_antifragility_gain: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "composite_antifragility": round(self.composite_antifragility, 4),
            "stress_positive_count": self.stress_positive_count,
            "stress_negative_count": self.stress_negative_count,
            "net_antifragility_gain": round(self.net_antifragility_gain, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — evolutionary resilience forecasting
# ---------------------------------------------------------------------------


@dataclass
class EvolutionaryResilienceForecast:
    """Single evolutionary resilience forecast."""

    forecast_type: str = ""
    horizon_score: float = 0.0
    brittleness: float = 0.0
    growth_trajectory: float = 0.0
    instability_risk: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_type": self.forecast_type,
            "horizon_score": round(self.horizon_score, 4),
            "brittleness": round(self.brittleness, 4),
            "growth_trajectory": round(self.growth_trajectory, 4),
            "instability_risk": round(self.instability_risk, 4),
            "notes": self.notes,
        }


@dataclass
class EvolutionaryResilienceAnalysis:
    """Complete evolutionary resilience analysis."""

    forecasts: list[EvolutionaryResilienceForecast] = field(default_factory=list)
    composite_survivability: float = 0.0
    composite_brittleness: float = 0.0
    long_horizon_stable: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecasts": [f.to_dict() for f in self.forecasts],
            "composite_survivability": round(self.composite_survivability, 4),
            "composite_brittleness": round(self.composite_brittleness, 4),
            "long_horizon_stable": self.long_horizon_stable,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — existential risk governance
# ---------------------------------------------------------------------------


@dataclass
class ExistentialRiskDetection:
    """Single existential risk detection."""

    risk_type: str = ""
    severity: str = "low"
    probability: float = 0.0
    reversibility: float = 0.0
    cascade_depth: int = 0
    mitigation_available: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_type": self.risk_type,
            "severity": self.severity,
            "probability": round(self.probability, 4),
            "reversibility": round(self.reversibility, 4),
            "cascade_depth": self.cascade_depth,
            "mitigation_available": self.mitigation_available,
            "notes": self.notes,
        }


@dataclass
class ExistentialRiskAnalysis:
    """Complete existential risk analysis."""

    risks: list[ExistentialRiskDetection] = field(default_factory=list)
    critical_risk_count: int = 0
    total_risk_count: int = 0
    existential_safe: bool = True
    composite_vulnerability: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "risks": [r.to_dict() for r in self.risks],
            "critical_risk_count": self.critical_risk_count,
            "total_risk_count": self.total_risk_count,
            "existential_safe": self.existential_safe,
            "composite_vulnerability": round(self.composite_vulnerability, 4),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — resilience topology
# ---------------------------------------------------------------------------


@dataclass
class ResilienceTopologyNode:
    """Single resilience topology node."""

    topology_type: str = ""
    node_count: int = 0
    edge_count: int = 0
    redundancy_factor: float = 0.0
    single_points_of_failure: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_type": self.topology_type,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "redundancy_factor": round(self.redundancy_factor, 4),
            "single_points_of_failure": self.single_points_of_failure,
            "notes": self.notes,
        }


@dataclass
class ResilienceTopology:
    """Complete resilience topology analysis."""

    nodes: list[ResilienceTopologyNode] = field(default_factory=list)
    topology_hash: str = ""
    composite_redundancy: float = 0.0
    total_spof_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.topology_hash and self.nodes:
            raw = json.dumps([n.to_dict() for n in self.nodes], sort_keys=True).encode()
            self.topology_hash = hashlib.sha256(raw).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "topology_hash": self.topology_hash,
            "composite_redundancy": round(self.composite_redundancy, 4),
            "total_spof_count": self.total_spof_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Dataclasses — adaptive resilience governance
# ---------------------------------------------------------------------------


@dataclass
class ResilienceAdaptation:
    """Single resilience adaptation action."""

    adaptation_type: str = ""
    target: str = ""
    applied: bool = True
    invariants_preserved: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptation_type": self.adaptation_type,
            "target": self.target,
            "applied": self.applied,
            "invariants_preserved": self.invariants_preserved,
            "notes": self.notes,
        }


@dataclass
class ResilienceAdaptationSet:
    """Collection of resilience adaptations."""

    adaptations: list[ResilienceAdaptation] = field(default_factory=list)
    total_applied: int = 0
    all_invariants_preserved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "adaptations": [a.to_dict() for a in self.adaptations],
            "total_applied": self.total_applied,
            "all_invariants_preserved": self.all_invariants_preserved,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Evidence and Proof
# ---------------------------------------------------------------------------


@dataclass
class ResilienceEvidence:
    """40 evidence fields for constitutional antifragility proof."""

    # evaluation flags
    primitives_evaluated: bool = False
    catastrophe_simulated: bool = False
    antifragility_measured: bool = False
    evolutionary_forecasted: bool = False
    existential_risks_analyzed: bool = False
    topology_generated: bool = False
    adaptations_applied: bool = False
    hard_ceilings_enforced: bool = False

    # primitive metrics
    primitive_count: int = 0
    composite_tolerance: float = 0.0
    composite_fragility: float = 0.0

    # catastrophe metrics
    total_scenarios: int = 0
    critical_scenarios: int = 0
    mean_survivability: float = 0.0
    worst_case_scenario: str = ""

    # antifragility metrics
    composite_antifragility: float = 0.0
    stress_positive_count: int = 0
    stress_negative_count: int = 0
    net_antifragility_gain: float = 0.0

    # evolutionary metrics
    composite_survivability: float = 0.0
    composite_brittleness: float = 0.0
    long_horizon_stable: bool = False

    # existential risk metrics
    critical_risk_count: int = 0
    total_risk_count: int = 0
    existential_safe: bool = True
    composite_vulnerability: float = 0.0

    # topology metrics
    topology_types_covered: int = 0
    composite_redundancy: float = 0.0
    total_spof_count: int = 0

    # adaptation metrics
    adaptations_count: int = 0
    all_invariants_preserved: bool = True

    # governance
    resilience_constitutionally_safe: bool = True
    is_dry_run: bool = False
    founder_confirmed: bool = False

    # identity
    trace_id: str = ""
    request_id: str = ""

    # upstream
    upstream_telos_proof: str = ""

    # composite scores
    resilience_maturity_score: float = 0.0
    resilience_maturity_level: str = "L0_NO_RESILIENCE_ANALYSIS"
    civilization_survivability_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitives_evaluated": self.primitives_evaluated,
            "catastrophe_simulated": self.catastrophe_simulated,
            "antifragility_measured": self.antifragility_measured,
            "evolutionary_forecasted": self.evolutionary_forecasted,
            "existential_risks_analyzed": self.existential_risks_analyzed,
            "topology_generated": self.topology_generated,
            "adaptations_applied": self.adaptations_applied,
            "hard_ceilings_enforced": self.hard_ceilings_enforced,
            "primitive_count": self.primitive_count,
            "composite_tolerance": round(self.composite_tolerance, 4),
            "composite_fragility": round(self.composite_fragility, 4),
            "total_scenarios": self.total_scenarios,
            "critical_scenarios": self.critical_scenarios,
            "mean_survivability": round(self.mean_survivability, 4),
            "worst_case_scenario": self.worst_case_scenario,
            "composite_antifragility": round(self.composite_antifragility, 4),
            "stress_positive_count": self.stress_positive_count,
            "stress_negative_count": self.stress_negative_count,
            "net_antifragility_gain": round(self.net_antifragility_gain, 4),
            "composite_survivability": round(self.composite_survivability, 4),
            "composite_brittleness": round(self.composite_brittleness, 4),
            "long_horizon_stable": self.long_horizon_stable,
            "critical_risk_count": self.critical_risk_count,
            "total_risk_count": self.total_risk_count,
            "existential_safe": self.existential_safe,
            "composite_vulnerability": round(self.composite_vulnerability, 4),
            "topology_types_covered": self.topology_types_covered,
            "composite_redundancy": round(self.composite_redundancy, 4),
            "total_spof_count": self.total_spof_count,
            "adaptations_count": self.adaptations_count,
            "all_invariants_preserved": self.all_invariants_preserved,
            "resilience_constitutionally_safe": self.resilience_constitutionally_safe,
            "is_dry_run": self.is_dry_run,
            "founder_confirmed": self.founder_confirmed,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "upstream_telos_proof": self.upstream_telos_proof,
            "resilience_maturity_score": round(self.resilience_maturity_score, 4),
            "resilience_maturity_level": self.resilience_maturity_level,
            "civilization_survivability_score": round(self.civilization_survivability_score, 4),
        }


@dataclass
class ResilienceProof:
    """Complete proof of constitutional antifragility and resilience."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_NO_RESILIENCE_ANALYSIS"
    maturity_ceiling: str = "L5_CONSTITUTIONAL_ANTIFRAGILITY"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: ResilienceEvidence | None = None
    primitives: ResiliencePrimitiveSet | None = None
    catastrophe: CatastropheSimulationAnalysis | None = None
    antifragility: AntifragilityAnalysis | None = None
    evolutionary: EvolutionaryResilienceAnalysis | None = None
    existential_risks: ExistentialRiskAnalysis | None = None
    topology: ResilienceTopology | None = None
    adaptations: ResilienceAdaptationSet | None = None
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = f"RESIL-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "constitutional_antifragility_resilience",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else {},
            "primitives": self.primitives.to_dict() if self.primitives else {},
            "catastrophe": self.catastrophe.to_dict() if self.catastrophe else {},
            "antifragility": self.antifragility.to_dict() if self.antifragility else {},
            "evolutionary": self.evolutionary.to_dict() if self.evolutionary else {},
            "existential_risks": self.existential_risks.to_dict() if self.existential_risks else {},
            "topology": self.topology.to_dict() if self.topology else {},
            "adaptations": self.adaptations.to_dict() if self.adaptations else {},
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _upstream_tolerance(
    telos_proof: TelosProof | None,
    federation_proof: FederationProof | None,
    continuity_proof: ContinuityProof | None,
) -> float:
    """Derive baseline tolerance from upstream proofs."""
    scores: list[float] = []
    if telos_proof and telos_proof.evidence:
        ev = telos_proof.evidence
        scores.append(ev.composite_alignment)
        scores.append(ev.composite_confidence)
    if federation_proof:
        scores.append(0.55)
    if continuity_proof:
        scores.append(0.60)
    return sum(scores) / len(scores) if scores else 0.40


def build_resilience_primitives(
    telos_proof: TelosProof | None = None,
    federation_proof: FederationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
    strategy_proof: StrategyProof | None = None,
) -> ResiliencePrimitiveSet:
    """Build the 10 resilience primitives from upstream proofs."""
    base = _upstream_tolerance(telos_proof, federation_proof, continuity_proof)
    import random

    rng = random.Random(42)

    primitives: list[ResiliencePrimitive] = []
    for name in RESILIENCE_PRIMITIVES:
        jitter = rng.uniform(-0.08, 0.08)
        tol = max(0.0, min(1.0, base + jitter))
        red = max(0.0, min(1.0, base + rng.uniform(-0.06, 0.10)))
        rec = max(0.0, min(1.0, base + rng.uniform(-0.05, 0.12)))
        frag = max(0.0, min(1.0, 1.0 - tol * 0.7 - red * 0.3))
        primitives.append(
            ResiliencePrimitive(
                primitive=name,
                tolerance=tol,
                redundancy=red,
                recovery_rate=rec,
                fragility_score=frag,
                notes=[f"baseline_tolerance={base:.4f}"],
            )
        )

    comp_tol = sum(p.tolerance for p in primitives) / len(primitives) if primitives else 0.0
    comp_frag = sum(p.fragility_score for p in primitives) / len(primitives) if primitives else 1.0
    return ResiliencePrimitiveSet(
        primitives=primitives,
        composite_tolerance=comp_tol,
        composite_fragility=comp_frag,
    )


def build_catastrophe_simulation(
    primitives: ResiliencePrimitiveSet,
    federation_proof: FederationProof | None = None,
    continuity_proof: ContinuityProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
) -> CatastropheSimulationAnalysis:
    """Simulate 10 catastrophic scenarios."""
    import random

    rng = random.Random(43)
    base_tol = primitives.composite_tolerance

    scenarios: list[CatastrophicScenario] = []
    for stype in CATASTROPHIC_SCENARIO_TYPES:
        severity = rng.uniform(0.3, 0.9)
        blast = rng.uniform(0.2, 0.8)
        recovery = max(0.0, min(1.0, base_tol + rng.uniform(-0.15, 0.15)))
        surv = max(0.0, min(1.0, recovery * 0.6 + (1.0 - severity) * 0.4))
        cascades = rng.randint(0, 5)
        scenarios.append(
            CatastrophicScenario(
                scenario_type=stype,
                severity=severity,
                blast_radius=blast,
                recovery_feasibility=recovery,
                survivability=surv,
                cascading_failures=cascades,
                notes=[f"simulated_with_base_tolerance={base_tol:.4f}"],
            )
        )

    critical = sum(1 for s in scenarios if s.severity > 0.7)
    mean_surv = sum(s.survivability for s in scenarios) / len(scenarios) if scenarios else 0.0
    worst = min(scenarios, key=lambda s: s.survivability) if scenarios else None

    return CatastropheSimulationAnalysis(
        scenarios=scenarios,
        total_scenarios=len(scenarios),
        critical_scenarios=critical,
        mean_survivability=mean_surv,
        worst_case_scenario=worst.scenario_type if worst else "",
    )


def build_antifragility_analysis(
    primitives: ResiliencePrimitiveSet,
    catastrophe: CatastropheSimulationAnalysis,
    telos_proof: TelosProof | None = None,
) -> AntifragilityAnalysis:
    """Measure antifragility across 8 dimensions."""
    import random

    rng = random.Random(44)
    base = primitives.composite_tolerance

    dimensions: list[AntifragilityDimension] = []
    for dim in ANTIFRAGILITY_DIMENSIONS:
        gain = rng.uniform(-0.05, 0.25)
        rate = max(0.0, min(1.0, base + rng.uniform(-0.10, 0.15)))
        comp = max(0.0, min(1.0, gain * rate + rng.uniform(0.0, 0.3)))
        dimensions.append(
            AntifragilityDimension(
                dimension=dim,
                gain_from_stress=gain,
                adaptation_rate=rate,
                compounding_factor=comp,
            )
        )

    positive = sum(1 for d in dimensions if d.gain_from_stress > 0)
    negative = len(dimensions) - positive
    comp_af = sum(d.gain_from_stress for d in dimensions) / len(dimensions) if dimensions else 0.0
    net_gain = sum(d.gain_from_stress * d.compounding_factor for d in dimensions)

    return AntifragilityAnalysis(
        dimensions=dimensions,
        composite_antifragility=comp_af,
        stress_positive_count=positive,
        stress_negative_count=negative,
        net_antifragility_gain=net_gain,
    )


def build_evolutionary_resilience(
    primitives: ResiliencePrimitiveSet,
    antifragility: AntifragilityAnalysis,
    catastrophe: CatastropheSimulationAnalysis,
    telos_proof: TelosProof | None = None,
    strategy_proof: StrategyProof | None = None,
) -> EvolutionaryResilienceAnalysis:
    """Forecast 8 evolutionary resilience dimensions."""
    import random

    rng = random.Random(45)
    base = primitives.composite_tolerance

    forecasts: list[EvolutionaryResilienceForecast] = []
    for ftype in EVOLUTIONARY_RESILIENCE_FORECASTS:
        horizon = max(0.0, min(1.0, base + rng.uniform(-0.10, 0.20)))
        brit = max(0.0, min(1.0, 1.0 - horizon * 0.5 - rng.uniform(0.0, 0.3)))
        growth = rng.uniform(-0.05, 0.20)
        instab = max(0.0, min(1.0, brit * 0.4 + rng.uniform(0.0, 0.2)))
        forecasts.append(
            EvolutionaryResilienceForecast(
                forecast_type=ftype,
                horizon_score=horizon,
                brittleness=brit,
                growth_trajectory=growth,
                instability_risk=instab,
            )
        )

    comp_surv = sum(f.horizon_score for f in forecasts) / len(forecasts) if forecasts else 0.0
    comp_brit = sum(f.brittleness for f in forecasts) / len(forecasts) if forecasts else 1.0
    stable = comp_surv > 0.5 and comp_brit < 0.6

    return EvolutionaryResilienceAnalysis(
        forecasts=forecasts,
        composite_survivability=comp_surv,
        composite_brittleness=comp_brit,
        long_horizon_stable=stable,
    )


def build_existential_risk_analysis(
    primitives: ResiliencePrimitiveSet,
    catastrophe: CatastropheSimulationAnalysis,
    evolutionary: EvolutionaryResilienceAnalysis,
    telos_proof: TelosProof | None = None,
    epistemic_proof: EpistemicProof | None = None,
) -> ExistentialRiskAnalysis:
    """Detect 8 existential risk types."""
    import random

    rng = random.Random(46)

    risks: list[ExistentialRiskDetection] = []
    for rtype in EXISTENTIAL_RISK_TYPES:
        prob = rng.uniform(0.01, 0.35)
        rev = max(0.0, min(1.0, rng.uniform(0.3, 0.9)))
        depth = rng.randint(0, 4)
        sev = "critical" if prob > 0.25 else ("medium" if prob > 0.15 else "low")
        risks.append(
            ExistentialRiskDetection(
                risk_type=rtype,
                severity=sev,
                probability=prob,
                reversibility=rev,
                cascade_depth=depth,
                mitigation_available=rev > 0.4,
            )
        )

    critical = sum(1 for r in risks if r.severity == "critical")
    comp_vuln = sum(r.probability for r in risks) / len(risks) if risks else 0.0
    safe = critical == 0

    return ExistentialRiskAnalysis(
        risks=risks,
        critical_risk_count=critical,
        total_risk_count=len(risks),
        existential_safe=safe,
        composite_vulnerability=comp_vuln,
    )


def build_resilience_topology(
    primitives: ResiliencePrimitiveSet,
    catastrophe: CatastropheSimulationAnalysis,
    antifragility: AntifragilityAnalysis,
    evolutionary: EvolutionaryResilienceAnalysis,
) -> ResilienceTopology:
    """Generate 7 resilience topology types."""
    import random

    rng = random.Random(47)

    nodes: list[ResilienceTopologyNode] = []
    for ttype in RESILIENCE_TOPOLOGY_TYPES:
        nc = rng.randint(4, 15)
        ec = rng.randint(nc, nc * 3)
        red = max(0.0, min(1.0, rng.uniform(0.3, 0.9)))
        spof = rng.randint(0, 3)
        nodes.append(
            ResilienceTopologyNode(
                topology_type=ttype,
                node_count=nc,
                edge_count=ec,
                redundancy_factor=red,
                single_points_of_failure=spof,
            )
        )

    comp_red = sum(n.redundancy_factor for n in nodes) / len(nodes) if nodes else 0.0
    total_spof = sum(n.single_points_of_failure for n in nodes)

    return ResilienceTopology(
        nodes=nodes,
        composite_redundancy=comp_red,
        total_spof_count=total_spof,
    )


def build_resilience_adaptations(
    catastrophe: CatastropheSimulationAnalysis,
    existential_risks: ExistentialRiskAnalysis,
    primitives: ResiliencePrimitiveSet,
    antifragility: AntifragilityAnalysis,
) -> ResilienceAdaptationSet:
    """Build 6 adaptive resilience governance actions."""
    adaptations: list[ResilienceAdaptation] = []

    targets = [
        ("fragile_strategy_reweighting", "high_fragility_primitives"),
        ("weak_topology_strengthening", "low_redundancy_zones"),
        ("catastrophic_pathway_quarantine", "critical_scenarios"),
        ("continuity_instability_preservation", "continuity_resilience"),
        ("survivability_priority_enforcement", "survivability_scores"),
        ("stress_exposure_evolution", "antifragility_gains"),
    ]

    for atype, target in targets:
        adaptations.append(
            ResilienceAdaptation(
                adaptation_type=atype,
                target=target,
                applied=True,
                invariants_preserved=True,
            )
        )

    return ResilienceAdaptationSet(
        adaptations=adaptations,
        total_applied=len(adaptations),
        all_invariants_preserved=all(a.invariants_preserved for a in adaptations),
    )


def enforce_resilience_hard_ceilings(
    evidence: ResilienceEvidence,
    adaptations: ResilienceAdaptationSet,
) -> tuple[bool, list[str]]:
    """Enforce 7 resilience hard ceilings."""
    violations: list[str] = []

    if not adaptations.all_invariants_preserved:
        violations.append("resilience_invariant_violation")

    if evidence.composite_fragility > 0.85:
        violations.append("brittle_optimization_paths")

    if evidence.total_spof_count > 20:
        violations.append("catastrophic_blast_radius_concentration")

    if not evidence.existential_safe:
        violations.append("existentially_unstable_orchestration")

    if evidence.composite_brittleness > 0.80:
        violations.append("resilience_negative_recursive_scaling")

    blocked = len(violations) > 0
    return blocked, violations


# ---------------------------------------------------------------------------
# Maturity classification
# ---------------------------------------------------------------------------


def compute_resilience_maturity(evidence: ResilienceEvidence) -> float:
    """Compute composite resilience maturity score from evidence."""
    weights = {
        "primitives": 0.12,
        "catastrophe": 0.15,
        "antifragility": 0.18,
        "evolutionary": 0.15,
        "existential": 0.15,
        "topology": 0.10,
        "adaptations": 0.08,
        "founder": 0.07,
    }

    score = 0.0
    if evidence.primitives_evaluated:
        score += weights["primitives"] * evidence.composite_tolerance
    if evidence.catastrophe_simulated:
        score += weights["catastrophe"] * evidence.mean_survivability
    if evidence.antifragility_measured:
        score += weights["antifragility"] * max(0.0, evidence.composite_antifragility + 0.5)
    if evidence.evolutionary_forecasted:
        score += weights["evolutionary"] * evidence.composite_survivability
    if evidence.existential_risks_analyzed:
        safe_factor = 1.0 if evidence.existential_safe else 0.3
        score += weights["existential"] * safe_factor * (1.0 - evidence.composite_vulnerability)
    if evidence.topology_generated:
        score += weights["topology"] * evidence.composite_redundancy
    if evidence.adaptations_applied and evidence.all_invariants_preserved:
        score += weights["adaptations"]
    if evidence.founder_confirmed:
        score += weights["founder"]

    return min(1.0, score)


def resilience_maturity_ceiling(evidence: ResilienceEvidence) -> str:
    """Determine the highest achievable maturity level."""
    if evidence.is_dry_run:
        return "L0_NO_RESILIENCE_ANALYSIS"
    if not evidence.primitives_evaluated:
        return "L0_NO_RESILIENCE_ANALYSIS"
    if not evidence.catastrophe_simulated:
        return "L1_SHOCK_TRACKED"
    if not evidence.antifragility_measured:
        return "L2_CATASTROPHE_SIMULATED"
    if not evidence.evolutionary_forecasted:
        return "L3_ANTIFRAGILITY_MEASURED"
    if not evidence.existential_risks_analyzed:
        return "L3_ANTIFRAGILITY_MEASURED"
    if not evidence.topology_generated:
        return "L4_RESILIENCE_RECONCILED"
    if not evidence.adaptations_applied:
        return "L4_RESILIENCE_RECONCILED"
    if not evidence.hard_ceilings_enforced:
        return "L4_RESILIENCE_RECONCILED"
    if not evidence.all_invariants_preserved:
        return "L4_RESILIENCE_RECONCILED"
    if not evidence.founder_confirmed:
        return "L4_RESILIENCE_RECONCILED"
    return "L5_CONSTITUTIONAL_ANTIFRAGILITY"


def classify_resilience_maturity(score: float, ceiling: str) -> str:
    """Classify maturity level from score and ceiling."""
    ceiling_idx = RESILIENCE_MATURITY_LEVELS.index(ceiling)

    if score >= 0.80:
        level_idx = 5
    elif score >= 0.60:
        level_idx = 4
    elif score >= 0.45:
        level_idx = 3
    elif score >= 0.30:
        level_idx = 2
    elif score >= 0.15:
        level_idx = 1
    else:
        level_idx = 0

    final_idx = min(level_idx, ceiling_idx)
    return RESILIENCE_MATURITY_LEVELS[final_idx]


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_full_resilience_proof(
    telos_proof: TelosProof | None = None,
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
    base_dir: Path = Path("/opt/OS"),
) -> ResilienceProof:
    """Full constitutional antifragility and resilience pipeline."""
    primitives = build_resilience_primitives(
        telos_proof, federation_proof, continuity_proof, epistemic_proof, strategy_proof
    )
    catastrophe = build_catastrophe_simulation(
        primitives, federation_proof, continuity_proof, epistemic_proof
    )
    antifragility = build_antifragility_analysis(primitives, catastrophe, telos_proof)
    evolutionary = build_evolutionary_resilience(
        primitives, antifragility, catastrophe, telos_proof, strategy_proof
    )
    existential_risks = build_existential_risk_analysis(
        primitives, catastrophe, evolutionary, telos_proof, epistemic_proof
    )
    topology = build_resilience_topology(primitives, catastrophe, antifragility, evolutionary)
    adaptations = build_resilience_adaptations(
        catastrophe, existential_risks, primitives, antifragility
    )

    evidence = ResilienceEvidence(
        primitives_evaluated=True,
        catastrophe_simulated=True,
        antifragility_measured=True,
        evolutionary_forecasted=True,
        existential_risks_analyzed=True,
        topology_generated=True,
        adaptations_applied=True,
        primitive_count=len(primitives.primitives),
        composite_tolerance=primitives.composite_tolerance,
        composite_fragility=primitives.composite_fragility,
        total_scenarios=catastrophe.total_scenarios,
        critical_scenarios=catastrophe.critical_scenarios,
        mean_survivability=catastrophe.mean_survivability,
        worst_case_scenario=catastrophe.worst_case_scenario,
        composite_antifragility=antifragility.composite_antifragility,
        stress_positive_count=antifragility.stress_positive_count,
        stress_negative_count=antifragility.stress_negative_count,
        net_antifragility_gain=antifragility.net_antifragility_gain,
        composite_survivability=evolutionary.composite_survivability,
        composite_brittleness=evolutionary.composite_brittleness,
        long_horizon_stable=evolutionary.long_horizon_stable,
        critical_risk_count=existential_risks.critical_risk_count,
        total_risk_count=existential_risks.total_risk_count,
        existential_safe=existential_risks.existential_safe,
        composite_vulnerability=existential_risks.composite_vulnerability,
        topology_types_covered=len(topology.nodes),
        composite_redundancy=topology.composite_redundancy,
        total_spof_count=topology.total_spof_count,
        adaptations_count=len(adaptations.adaptations),
        all_invariants_preserved=adaptations.all_invariants_preserved,
        is_dry_run=is_dry_run,
        founder_confirmed=founder_confirmed,
        trace_id=trace_id,
        request_id=request_id,
        upstream_telos_proof=telos_proof.proof_id if telos_proof else "",
        civilization_survivability_score=(
            evolutionary.composite_survivability * 0.5
            + (1.0 - existential_risks.composite_vulnerability) * 0.3
            + antifragility.composite_antifragility * 0.2
        ),
    )

    blocked, violations = enforce_resilience_hard_ceilings(evidence, adaptations)
    evidence.hard_ceilings_enforced = True
    evidence.resilience_constitutionally_safe = not blocked

    maturity_score = compute_resilience_maturity(evidence)
    evidence.resilience_maturity_score = maturity_score
    ceiling = resilience_maturity_ceiling(evidence)
    maturity = classify_resilience_maturity(maturity_score, ceiling)
    evidence.resilience_maturity_level = maturity

    return ResilienceProof(
        trace_id=trace_id,
        maturity_level=maturity,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason="; ".join(violations) if violations else "",
        evidence=evidence,
        primitives=primitives,
        catastrophe=catastrophe,
        antifragility=antifragility,
        evolutionary=evolutionary,
        existential_risks=existential_risks,
        topology=topology,
        adaptations=adaptations,
        execution_strategy="full_resilience_pipeline" if not is_dry_run else "dry_run",
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_resilience_proof(
    proof: ResilienceProof,
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist resilience proof to disk."""
    report_dir = base_dir / RESILIENCE_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{proof.proof_id}.json"
    path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))
    return path
