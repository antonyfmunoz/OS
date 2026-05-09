"""Recursive Capability Planning Engine v1.

Analyzes the substrate's own maturity state, identifies missing
capabilities, generates upgrade paths, prioritizes leverage
opportunities, and recursively proposes the next safest/highest-value
substrate expansions.

The engine may: analyze, classify, prioritize, propose, simulate,
generate upgrade plans.

The engine CANNOT: autonomously modify infrastructure, escalate
maturity, promote candidates, deploy adapters, or bypass governance.

UMH substrate subsystem. Phase 96.8AV.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.workstation.adapter_autogeneration_engine_v1 import (
    ADAPTER_MATURITY_LEVELS,
    ADAPTER_MATURITY_REQUIREMENTS,
    ADAPTER_TARGET_PLATFORMS,
    AdapterAutogenProof,
    AdapterBlueprint,
)
from core.workstation.environment_mapping_engine_v1 import (
    CANDIDATE_TYPE_CANONICAL,
    CANDIDATE_TYPE_INSTANCE,
    ENVIRONMENT_MAP_DIR,
    EnvironmentMappingProof,
    EnvironmentTopology,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


CAPABILITY_REPORT_DIR = Path("data/runtime/workstation_relay/capability_reports")

# ---------------------------------------------------------------------------
# Capability maturity levels (extends adapter L0-L5 with L5 planning)
# ---------------------------------------------------------------------------

CAPABILITY_MATURITY_LEVELS = (
    "L0_SIMULATED",
    "L1_VISIBLE_ACTUATION",
    "L2_FOREGROUND_CU_INGESTION",
    "L3_ENVIRONMENT_INTELLIGENCE",
    "L4_ADAPTER_MATURITY",
    "L5_RECURSIVE_CAPABILITY_PLANNING",
)

CAPABILITY_MATURITY_REQUIREMENTS: dict[str, list[str]] = {
    "L0_SIMULATED": [],
    "L1_VISIBLE_ACTUATION": ["actuation_proven"],
    "L2_FOREGROUND_CU_INGESTION": ["actuation_proven", "cu_ingestion_proven"],
    "L3_ENVIRONMENT_INTELLIGENCE": [
        "actuation_proven",
        "cu_ingestion_proven",
        "environment_mapped",
    ],
    "L4_ADAPTER_MATURITY": [
        "actuation_proven",
        "cu_ingestion_proven",
        "environment_mapped",
        "blueprints_generated",
        "replay_contracts_defined",
        "governance_classified",
    ],
    "L5_RECURSIVE_CAPABILITY_PLANNING": [
        "actuation_proven",
        "cu_ingestion_proven",
        "environment_mapped",
        "blueprints_generated",
        "replay_contracts_defined",
        "governance_classified",
        "capability_graph_generated",
        "leverage_analyzed",
        "upgrade_paths_proposed",
    ],
}

# ---------------------------------------------------------------------------
# Bottleneck categories
# ---------------------------------------------------------------------------

BOTTLENECK_CATEGORIES = frozenset(
    {
        "manual",
        "replay",
        "governance",
        "execution",
        "relay",
        "ingestion",
        "maturity",
        "scaling",
    }
)

# ---------------------------------------------------------------------------
# Capability definitions
# ---------------------------------------------------------------------------

SUBSTRATE_CAPABILITIES = (
    "relay_transport",
    "desktop_actuation",
    "foreground_cu",
    "clipboard_extraction",
    "screenshot_capture",
    "chrome_proof",
    "environment_discovery",
    "topology_mapping",
    "relationship_synthesis",
    "ingestion_lane_planning",
    "adapter_autogeneration",
    "replay_contract_generation",
    "governance_classification",
    "maturity_evaluation",
    "canonical_instance_separation",
    "proof_persistence",
    "founder_confirmation",
    "command_registration",
    "spine_routing",
    "router_routing",
    "recursive_planning",
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CapabilityNode:
    """A single capability in the capability graph."""

    capability_id: str = ""
    name: str = ""
    status: str = "missing"
    maturity_level: str = "L0_SIMULATED"
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    proven: bool = False
    replayable: bool = False
    governance_covered: bool = False
    evidence_quality: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.capability_id:
            self.capability_id = f"CAP-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "status": self.status,
            "maturity_level": self.maturity_level,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "proven": self.proven,
            "replayable": self.replayable,
            "governance_covered": self.governance_covered,
            "evidence_quality": round(self.evidence_quality, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class LeverageScore:
    """Scoring for a proposed upgrade."""

    score_id: str = ""
    upgrade_name: str = ""
    leverage_gain: float = 0.0
    governance_risk: float = 0.0
    replayability_impact: float = 0.0
    execution_complexity: float = 0.0
    evidence_quality: float = 0.0
    infrastructure_reuse: float = 0.0
    recursive_expansion_value: float = 0.0
    automation_potential: float = 0.0
    composite_score: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.score_id:
            self.score_id = f"LSCR-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()
        if self.composite_score == 0.0:
            self.composite_score = self._compute_composite()

    def _compute_composite(self) -> float:
        positive = (
            self.leverage_gain * 0.25
            + self.replayability_impact * 0.15
            + self.evidence_quality * 0.15
            + self.infrastructure_reuse * 0.15
            + self.recursive_expansion_value * 0.15
            + self.automation_potential * 0.15
        )
        penalty = self.governance_risk * 0.2 + self.execution_complexity * 0.2
        return round(max(0.0, positive - penalty), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id": self.score_id,
            "upgrade_name": self.upgrade_name,
            "leverage_gain": round(self.leverage_gain, 2),
            "governance_risk": round(self.governance_risk, 2),
            "replayability_impact": round(self.replayability_impact, 2),
            "execution_complexity": round(self.execution_complexity, 2),
            "evidence_quality": round(self.evidence_quality, 2),
            "infrastructure_reuse": round(self.infrastructure_reuse, 2),
            "recursive_expansion_value": round(self.recursive_expansion_value, 2),
            "automation_potential": round(self.automation_potential, 2),
            "composite_score": round(self.composite_score, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class Bottleneck:
    """An identified bottleneck in the substrate."""

    bottleneck_id: str = ""
    category: str = ""
    description: str = ""
    severity: float = 0.0
    affected_capabilities: list[str] = field(default_factory=list)
    resolution_path: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.bottleneck_id:
            self.bottleneck_id = f"BTNK-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bottleneck_id": self.bottleneck_id,
            "category": self.category,
            "description": self.description,
            "severity": round(self.severity, 2),
            "affected_capabilities": self.affected_capabilities,
            "resolution_path": self.resolution_path,
            "timestamp": self.timestamp,
        }


@dataclass
class UpgradeProposal:
    """A proposed substrate upgrade."""

    proposal_id: str = ""
    name: str = ""
    description: str = ""
    target_maturity: str = ""
    required_proofs: list[str] = field(default_factory=list)
    required_maturity: str = "L0_SIMULATED"
    required_infrastructure: list[str] = field(default_factory=list)
    replay_requirements: list[str] = field(default_factory=list)
    governance_constraints: list[str] = field(default_factory=list)
    execution_requirements: list[str] = field(default_factory=list)
    leverage_score: LeverageScore | None = None
    candidate_type: str = CANDIDATE_TYPE_CANONICAL
    safety_rating: str = "safe"
    priority: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proposal_id:
            self.proposal_id = f"UPGR-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "name": self.name,
            "description": self.description,
            "target_maturity": self.target_maturity,
            "required_proofs": self.required_proofs,
            "required_maturity": self.required_maturity,
            "required_infrastructure": self.required_infrastructure,
            "replay_requirements": self.replay_requirements,
            "governance_constraints": self.governance_constraints,
            "execution_requirements": self.execution_requirements,
            "leverage_score": self.leverage_score.to_dict() if self.leverage_score else None,
            "candidate_type": self.candidate_type,
            "safety_rating": self.safety_rating,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }


@dataclass
class CapabilityGraph:
    """Complete capability graph of the substrate."""

    graph_id: str = ""
    nodes: list[CapabilityNode] = field(default_factory=list)
    proven_count: int = 0
    missing_count: int = 0
    replayable_count: int = 0
    governance_covered_count: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.graph_id:
            self.graph_id = f"CGRAPH-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "node_count": len(self.nodes),
            "proven_count": self.proven_count,
            "missing_count": self.missing_count,
            "replayable_count": self.replayable_count,
            "governance_covered_count": self.governance_covered_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CapabilityPlanningEvidence:
    """Evidence collected during capability planning."""

    capability_graph_generated: bool = False
    capability_count: int = 0
    proven_count: int = 0
    missing_count: int = 0
    leverage_analyzed: bool = False
    leverage_score_count: int = 0
    bottlenecks_identified: bool = False
    bottleneck_count: int = 0
    upgrade_paths_proposed: bool = False
    upgrade_count: int = 0
    governance_analyzed: bool = False
    governance_gaps: int = 0
    replay_analyzed: bool = False
    replay_gaps: int = 0
    infrastructure_reuse_found: bool = False
    reuse_count: int = 0
    actuation_proven: bool = False
    cu_ingestion_proven: bool = False
    environment_mapped: bool = False
    blueprints_generated: bool = False
    replay_contracts_defined: bool = False
    governance_classified: bool = False
    screenshots_present: bool = False
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_graph_generated": self.capability_graph_generated,
            "capability_count": self.capability_count,
            "proven_count": self.proven_count,
            "missing_count": self.missing_count,
            "leverage_analyzed": self.leverage_analyzed,
            "leverage_score_count": self.leverage_score_count,
            "bottlenecks_identified": self.bottlenecks_identified,
            "bottleneck_count": self.bottleneck_count,
            "upgrade_paths_proposed": self.upgrade_paths_proposed,
            "upgrade_count": self.upgrade_count,
            "governance_analyzed": self.governance_analyzed,
            "governance_gaps": self.governance_gaps,
            "replay_analyzed": self.replay_analyzed,
            "replay_gaps": self.replay_gaps,
            "infrastructure_reuse_found": self.infrastructure_reuse_found,
            "reuse_count": self.reuse_count,
            "actuation_proven": self.actuation_proven,
            "cu_ingestion_proven": self.cu_ingestion_proven,
            "environment_mapped": self.environment_mapped,
            "blueprints_generated": self.blueprints_generated,
            "replay_contracts_defined": self.replay_contracts_defined,
            "governance_classified": self.governance_classified,
            "screenshots_present": self.screenshots_present,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class CapabilityPlanningProof:
    """Complete proof of recursive capability planning execution."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_SIMULATED"
    maturity_ceiling: str = "L5_RECURSIVE_CAPABILITY_PLANNING"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: CapabilityPlanningEvidence | None = None
    capability_graph: CapabilityGraph | None = None
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    upgrade_proposals: list[UpgradeProposal] = field(default_factory=list)
    safest_next_phase: str = ""
    highest_leverage_upgrade: str = ""
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"CAPPLAN-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "recursive_capability_planning",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "capability_graph": self.capability_graph.to_dict() if self.capability_graph else None,
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "bottleneck_count": len(self.bottlenecks),
            "upgrade_proposals": [u.to_dict() for u in self.upgrade_proposals],
            "upgrade_count": len(self.upgrade_proposals),
            "safest_next_phase": self.safest_next_phase,
            "highest_leverage_upgrade": self.highest_leverage_upgrade,
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Capability dependency map
# ---------------------------------------------------------------------------

CAPABILITY_DEPENDENCIES: dict[str, list[str]] = {
    "relay_transport": [],
    "desktop_actuation": ["relay_transport"],
    "foreground_cu": ["desktop_actuation"],
    "clipboard_extraction": ["foreground_cu"],
    "screenshot_capture": ["desktop_actuation"],
    "chrome_proof": ["desktop_actuation", "screenshot_capture"],
    "environment_discovery": ["relay_transport", "desktop_actuation"],
    "topology_mapping": ["environment_discovery"],
    "relationship_synthesis": ["topology_mapping"],
    "ingestion_lane_planning": ["topology_mapping", "relationship_synthesis"],
    "adapter_autogeneration": ["topology_mapping", "ingestion_lane_planning"],
    "replay_contract_generation": ["adapter_autogeneration"],
    "governance_classification": ["adapter_autogeneration"],
    "maturity_evaluation": ["adapter_autogeneration", "replay_contract_generation"],
    "canonical_instance_separation": ["topology_mapping"],
    "proof_persistence": ["relay_transport"],
    "founder_confirmation": [],
    "command_registration": [],
    "spine_routing": ["command_registration"],
    "router_routing": ["command_registration"],
    "recursive_planning": [
        "adapter_autogeneration",
        "replay_contract_generation",
        "governance_classification",
        "maturity_evaluation",
    ],
}


def _compute_dependents() -> dict[str, list[str]]:
    """Compute reverse dependency map."""
    dependents: dict[str, list[str]] = {cap: [] for cap in SUBSTRATE_CAPABILITIES}
    for cap, deps in CAPABILITY_DEPENDENCIES.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(cap)
    return dependents


_DEPENDENTS = _compute_dependents()

# ---------------------------------------------------------------------------
# Capability status from substrate state
# ---------------------------------------------------------------------------

CAPABILITY_PROOF_INDICATORS: dict[str, str] = {
    "relay_transport": "actuation_proven",
    "desktop_actuation": "actuation_proven",
    "foreground_cu": "cu_ingestion_proven",
    "clipboard_extraction": "cu_ingestion_proven",
    "screenshot_capture": "screenshots_present",
    "chrome_proof": "actuation_proven",
    "environment_discovery": "environment_mapped",
    "topology_mapping": "environment_mapped",
    "relationship_synthesis": "environment_mapped",
    "ingestion_lane_planning": "environment_mapped",
    "adapter_autogeneration": "blueprints_generated",
    "replay_contract_generation": "replay_contracts_defined",
    "governance_classification": "governance_classified",
    "maturity_evaluation": "blueprints_generated",
    "canonical_instance_separation": "environment_mapped",
    "proof_persistence": "actuation_proven",
    "founder_confirmation": "founder_confirmed",
    "command_registration": "actuation_proven",
    "spine_routing": "actuation_proven",
    "router_routing": "actuation_proven",
    "recursive_planning": "capability_graph_generated",
}


def build_capability_graph(evidence: CapabilityPlanningEvidence) -> CapabilityGraph:
    """Build the full capability graph from current evidence."""
    evidence_map: dict[str, bool] = {
        "actuation_proven": evidence.actuation_proven,
        "cu_ingestion_proven": evidence.cu_ingestion_proven,
        "environment_mapped": evidence.environment_mapped,
        "blueprints_generated": evidence.blueprints_generated,
        "replay_contracts_defined": evidence.replay_contracts_defined,
        "governance_classified": evidence.governance_classified,
        "screenshots_present": evidence.screenshots_present,
        "founder_confirmed": evidence.founder_confirmed,
        "capability_graph_generated": evidence.capability_graph_generated,
    }

    nodes: list[CapabilityNode] = []
    proven_count = 0
    missing_count = 0
    replayable_count = 0
    governance_count = 0

    for cap in SUBSTRATE_CAPABILITIES:
        indicator = CAPABILITY_PROOF_INDICATORS.get(cap, "")
        proven = evidence_map.get(indicator, False) if indicator else False

        deps = CAPABILITY_DEPENDENCIES.get(cap, [])
        all_deps_proven = (
            all(evidence_map.get(CAPABILITY_PROOF_INDICATORS.get(d, ""), False) for d in deps)
            if deps
            else True
        )

        status = "proven" if proven else ("blocked" if not all_deps_proven else "missing")
        replayable = proven and evidence.replay_contracts_defined
        gov_covered = proven and evidence.governance_classified

        eq = 0.0
        if proven:
            eq = 0.8
            if replayable:
                eq += 0.1
            if gov_covered:
                eq += 0.1

        if status == "proven":
            proven_count += 1
        else:
            missing_count += 1
        if replayable:
            replayable_count += 1
        if gov_covered:
            governance_count += 1

        maturity = "L0_SIMULATED"
        if proven and evidence.blueprints_generated and evidence.governance_classified:
            maturity = "L4_ADAPTER_MATURITY"
        elif proven and evidence.environment_mapped:
            maturity = "L3_ENVIRONMENT_INTELLIGENCE"
        elif proven and evidence.cu_ingestion_proven:
            maturity = "L2_FOREGROUND_CU_INGESTION"
        elif proven:
            maturity = "L1_VISIBLE_ACTUATION"

        node = CapabilityNode(
            name=cap,
            status=status,
            maturity_level=maturity,
            dependencies=deps,
            dependents=_DEPENDENTS.get(cap, []),
            proven=proven,
            replayable=replayable,
            governance_covered=gov_covered,
            evidence_quality=eq,
        )
        nodes.append(node)

    return CapabilityGraph(
        nodes=nodes,
        proven_count=proven_count,
        missing_count=missing_count,
        replayable_count=replayable_count,
        governance_covered_count=governance_count,
    )


# ---------------------------------------------------------------------------
# Bottleneck analysis
# ---------------------------------------------------------------------------


def analyze_bottlenecks(
    evidence: CapabilityPlanningEvidence,
    graph: CapabilityGraph,
) -> list[Bottleneck]:
    """Detect bottlenecks across all categories."""
    bottlenecks: list[Bottleneck] = []

    if not evidence.actuation_proven:
        bottlenecks.append(
            Bottleneck(
                category="execution",
                description="Desktop actuation not yet proven",
                severity=1.0,
                affected_capabilities=["desktop_actuation", "foreground_cu", "chrome_proof"],
                resolution_path="Execute !chrome-proof or !actuator-proof on live workstation",
            )
        )

    if not evidence.cu_ingestion_proven:
        bottlenecks.append(
            Bottleneck(
                category="ingestion",
                description="Foreground CU ingestion not yet proven",
                severity=0.9,
                affected_capabilities=["foreground_cu", "clipboard_extraction"],
                resolution_path="Execute !ingest-safe-doc-cu on live workstation",
            )
        )

    if not evidence.environment_mapped:
        bottlenecks.append(
            Bottleneck(
                category="maturity",
                description="Environment not yet mapped",
                severity=0.8,
                affected_capabilities=[
                    "environment_discovery",
                    "topology_mapping",
                    "relationship_synthesis",
                    "ingestion_lane_planning",
                ],
                resolution_path="Execute !explore-environment on live workstation",
            )
        )

    if not evidence.blueprints_generated:
        bottlenecks.append(
            Bottleneck(
                category="maturity",
                description="Adapter blueprints not yet generated",
                severity=0.7,
                affected_capabilities=["adapter_autogeneration", "replay_contract_generation"],
                resolution_path="Execute !adapter-report to generate blueprints",
            )
        )

    if not evidence.replay_contracts_defined:
        bottlenecks.append(
            Bottleneck(
                category="replay",
                description="Replay contracts not defined for all adapters",
                severity=0.6,
                affected_capabilities=["replay_contract_generation"],
                resolution_path="Execute !adapter-report to generate replay contracts",
            )
        )

    if not evidence.governance_classified:
        bottlenecks.append(
            Bottleneck(
                category="governance",
                description="Governance not classified for all adapters",
                severity=0.6,
                affected_capabilities=["governance_classification"],
                resolution_path="Execute !adapter-report to classify governance",
            )
        )

    if not evidence.screenshots_present:
        bottlenecks.append(
            Bottleneck(
                category="execution",
                description="No screenshot evidence available",
                severity=0.5,
                affected_capabilities=["screenshot_capture", "chrome_proof"],
                resolution_path="Execute any GUI command with screenshot capture enabled",
            )
        )

    if not evidence.founder_confirmed:
        bottlenecks.append(
            Bottleneck(
                category="manual",
                description="Founder has not confirmed current state",
                severity=0.4,
                affected_capabilities=["founder_confirmation"],
                resolution_path="Founder must approve via YES response",
            )
        )

    replay_gaps = [n for n in graph.nodes if n.proven and not n.replayable]
    if replay_gaps:
        bottlenecks.append(
            Bottleneck(
                category="replay",
                description=f"{len(replay_gaps)} proven capabilities lack replay contracts",
                severity=0.5,
                affected_capabilities=[n.name for n in replay_gaps],
                resolution_path="Generate replay contracts via !adapter-report",
            )
        )

    gov_gaps = [n for n in graph.nodes if n.proven and not n.governance_covered]
    if gov_gaps:
        bottlenecks.append(
            Bottleneck(
                category="governance",
                description=f"{len(gov_gaps)} proven capabilities lack governance coverage",
                severity=0.5,
                affected_capabilities=[n.name for n in gov_gaps],
                resolution_path="Classify governance via !adapter-report",
            )
        )

    blocked = [n for n in graph.nodes if n.status == "blocked"]
    if blocked:
        bottlenecks.append(
            Bottleneck(
                category="execution",
                description=f"{len(blocked)} capabilities blocked by unmet dependencies",
                severity=0.7,
                affected_capabilities=[n.name for n in blocked],
                resolution_path="Resolve dependency chain starting from lowest-level missing capability",
            )
        )

    manual_only = sum(
        1 for n in graph.nodes if n.name in ("founder_confirmation",) and not n.proven
    )
    if manual_only > 0:
        bottlenecks.append(
            Bottleneck(
                category="manual",
                description="Manual founder intervention required for confirmation",
                severity=0.3,
                affected_capabilities=["founder_confirmation"],
                resolution_path="Founder must be present and approve",
            )
        )

    return sorted(bottlenecks, key=lambda b: b.severity, reverse=True)


# ---------------------------------------------------------------------------
# Leverage scoring for upgrade proposals
# ---------------------------------------------------------------------------

UPGRADE_CATALOG: list[dict[str, Any]] = [
    {
        "name": "local_adapter_execution",
        "description": "Execute local-only adapters (Obsidian, filesystem, Docker) that don't require CU",
        "target_maturity": "L5_RECURSIVE_CAPABILITY_PLANNING",
        "required_proofs": ["environment_mapping_proof", "adapter_blueprint_proof"],
        "required_maturity": "L4_ADAPTER_MATURITY",
        "required_infrastructure": ["relay_transport", "local_filesystem_access"],
        "replay_requirements": ["deterministic_path", "proof_persistence"],
        "governance_constraints": ["founder_approval"],
        "execution_requirements": ["relay_healthy", "desktop_session_active"],
        "leverage_gain": 0.9,
        "governance_risk": 0.1,
        "replayability_impact": 0.8,
        "execution_complexity": 0.3,
        "evidence_quality": 0.8,
        "infrastructure_reuse": 0.9,
        "recursive_expansion_value": 0.7,
        "automation_potential": 0.8,
    },
    {
        "name": "cu_adapter_execution",
        "description": "Execute CU-based adapters (Gmail, Drive, Notion) requiring foreground interaction",
        "target_maturity": "L5_RECURSIVE_CAPABILITY_PLANNING",
        "required_proofs": ["cu_ingestion_proof", "adapter_blueprint_proof"],
        "required_maturity": "L4_ADAPTER_MATURITY",
        "required_infrastructure": ["relay_transport", "chrome_foreground", "clipboard"],
        "replay_requirements": ["deterministic_path", "screenshot_proof", "clipboard_hash"],
        "governance_constraints": ["founder_approval", "foreground_cu_required"],
        "execution_requirements": ["relay_healthy", "desktop_session_active", "chrome_focus"],
        "leverage_gain": 0.8,
        "governance_risk": 0.3,
        "replayability_impact": 0.7,
        "execution_complexity": 0.6,
        "evidence_quality": 0.7,
        "infrastructure_reuse": 0.7,
        "recursive_expansion_value": 0.8,
        "automation_potential": 0.6,
    },
    {
        "name": "multi_platform_ingestion",
        "description": "Parallel ingestion across multiple discovered platforms",
        "target_maturity": "L5_RECURSIVE_CAPABILITY_PLANNING",
        "required_proofs": ["adapter_blueprint_proof", "replay_contract_proof"],
        "required_maturity": "L4_ADAPTER_MATURITY",
        "required_infrastructure": ["relay_transport", "adapter_registry", "proof_persistence"],
        "replay_requirements": ["per_platform_replay", "cross_platform_dedup"],
        "governance_constraints": ["founder_approval", "per_platform_governance"],
        "execution_requirements": ["relay_healthy", "sequential_execution"],
        "leverage_gain": 0.7,
        "governance_risk": 0.4,
        "replayability_impact": 0.6,
        "execution_complexity": 0.7,
        "evidence_quality": 0.6,
        "infrastructure_reuse": 0.8,
        "recursive_expansion_value": 0.9,
        "automation_potential": 0.5,
    },
    {
        "name": "relationship_graph_expansion",
        "description": "Build cross-platform relationship graph from ingested data",
        "target_maturity": "L5_RECURSIVE_CAPABILITY_PLANNING",
        "required_proofs": ["topology_proof", "ingestion_proof"],
        "required_maturity": "L3_ENVIRONMENT_INTELLIGENCE",
        "required_infrastructure": ["topology_mapping", "relationship_synthesis"],
        "replay_requirements": ["deterministic_graph_build"],
        "governance_constraints": ["founder_approval"],
        "execution_requirements": ["environment_mapped"],
        "leverage_gain": 0.6,
        "governance_risk": 0.2,
        "replayability_impact": 0.5,
        "execution_complexity": 0.4,
        "evidence_quality": 0.7,
        "infrastructure_reuse": 0.6,
        "recursive_expansion_value": 0.8,
        "automation_potential": 0.7,
    },
    {
        "name": "world_model_integration",
        "description": "Integrate ingested data into UMH world model candidates",
        "target_maturity": "L5_RECURSIVE_CAPABILITY_PLANNING",
        "required_proofs": ["ingestion_proof", "world_model_candidate_proof"],
        "required_maturity": "L4_ADAPTER_MATURITY",
        "required_infrastructure": ["world_model_candidate_layer", "governance_engine"],
        "replay_requirements": ["candidate_lineage", "transformation_ledger"],
        "governance_constraints": ["founder_approval", "canonical_gate"],
        "execution_requirements": ["ingestion_complete", "candidate_assembled"],
        "leverage_gain": 0.9,
        "governance_risk": 0.5,
        "replayability_impact": 0.6,
        "execution_complexity": 0.8,
        "evidence_quality": 0.5,
        "infrastructure_reuse": 0.7,
        "recursive_expansion_value": 1.0,
        "automation_potential": 0.4,
    },
]


def score_upgrade(upgrade: dict[str, Any]) -> LeverageScore:
    """Score a single upgrade proposal."""
    return LeverageScore(
        upgrade_name=upgrade["name"],
        leverage_gain=upgrade.get("leverage_gain", 0.0),
        governance_risk=upgrade.get("governance_risk", 0.0),
        replayability_impact=upgrade.get("replayability_impact", 0.0),
        execution_complexity=upgrade.get("execution_complexity", 0.0),
        evidence_quality=upgrade.get("evidence_quality", 0.0),
        infrastructure_reuse=upgrade.get("infrastructure_reuse", 0.0),
        recursive_expansion_value=upgrade.get("recursive_expansion_value", 0.0),
        automation_potential=upgrade.get("automation_potential", 0.0),
    )


def generate_upgrade_proposals(
    evidence: CapabilityPlanningEvidence,
    graph: CapabilityGraph,
) -> list[UpgradeProposal]:
    """Generate ranked upgrade proposals from the catalog."""
    proposals: list[UpgradeProposal] = []

    for idx, upgrade in enumerate(UPGRADE_CATALOG):
        score = score_upgrade(upgrade)
        proposal = UpgradeProposal(
            name=upgrade["name"],
            description=upgrade["description"],
            target_maturity=upgrade["target_maturity"],
            required_proofs=upgrade.get("required_proofs", []),
            required_maturity=upgrade.get("required_maturity", "L0_SIMULATED"),
            required_infrastructure=upgrade.get("required_infrastructure", []),
            replay_requirements=upgrade.get("replay_requirements", []),
            governance_constraints=upgrade.get("governance_constraints", []),
            execution_requirements=upgrade.get("execution_requirements", []),
            leverage_score=score,
            candidate_type=CANDIDATE_TYPE_CANONICAL,
            safety_rating="safe",
            priority=idx + 1,
        )
        proposals.append(proposal)

    proposals.sort(
        key=lambda p: p.leverage_score.composite_score if p.leverage_score else 0.0, reverse=True
    )
    for i, p in enumerate(proposals):
        p.priority = i + 1

    return proposals


# ---------------------------------------------------------------------------
# Infrastructure self-analysis
# ---------------------------------------------------------------------------


def analyze_registries(base_dir: Path = Path("/opt/OS")) -> dict[str, Any]:
    """Analyze substrate registries."""
    registry_path = base_dir / "data/registries/local_worker_adapter_registry_v1.json"
    config_path = base_dir / "config/control_plane_router_v1.json"

    result: dict[str, Any] = {
        "adapter_registry_exists": registry_path.exists(),
        "router_config_exists": config_path.exists(),
        "adapter_count": 0,
        "config_action_count": 0,
    }

    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8-sig"))
            adapters = data.get("adapters", {})
            for adapter_data in adapters.values():
                result["adapter_count"] += len(adapter_data.get("capabilities", []))
        except (json.JSONDecodeError, OSError):
            pass

    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8-sig"))
            result["config_action_count"] = len(data.get("allowed_action_types", []))
        except (json.JSONDecodeError, OSError):
            pass

    return result


def analyze_proof_artifacts(base_dir: Path = Path("/opt/OS")) -> dict[str, Any]:
    """Analyze existing proof artifacts."""
    proof_dirs = {
        "runtime_proofs": base_dir / "data/runtime/runtime_proofs",
        "environment_maps": base_dir / ENVIRONMENT_MAP_DIR,
        "adapter_reports": base_dir / "data/runtime/workstation_relay/adapter_reports",
        "adapter_blueprints": base_dir / "data/runtime/workstation_relay/adapter_blueprints",
        "capability_reports": base_dir / CAPABILITY_REPORT_DIR,
        "relay_proofs": base_dir / "data/runtime/workstation_relay/proofs",
    }

    result: dict[str, Any] = {}
    for name, path in proof_dirs.items():
        if path.exists():
            files = list(path.glob("*.json"))
            result[name] = {"exists": True, "count": len(files)}
        else:
            result[name] = {"exists": False, "count": 0}

    return result


def analyze_governance_surface(base_dir: Path = Path("/opt/OS")) -> dict[str, Any]:
    """Analyze governance surface coverage."""
    from core.registry.canonical_command_registry_v1 import get_canonical_registry

    reg = get_canonical_registry()
    commands = list(reg)

    total = len(commands)
    founder_approval = sum(1 for e in commands if e.governance_policy == "FOUNDER_APPROVAL")
    screenshot_required = sum(1 for e in commands if e.require_screenshot_proof)
    foreground_required = sum(1 for e in commands if e.foreground_required)

    return {
        "total_commands": total,
        "founder_approval_required": founder_approval,
        "screenshot_required": screenshot_required,
        "foreground_required": foreground_required,
        "governance_coverage": round(founder_approval / total, 2) if total > 0 else 0.0,
    }


def find_infrastructure_reuse(
    graph: CapabilityGraph,
    proposals: list[UpgradeProposal],
) -> list[dict[str, str]]:
    """Identify infrastructure reuse opportunities."""
    reuse: list[dict[str, str]] = []

    proven_caps = {n.name for n in graph.nodes if n.proven}

    for proposal in proposals:
        for infra in proposal.required_infrastructure:
            matching = [c for c in proven_caps if infra in c or c in infra]
            if matching:
                reuse.append(
                    {
                        "upgrade": proposal.name,
                        "infrastructure": infra,
                        "reused_from": matching[0],
                    }
                )

    return reuse


# ---------------------------------------------------------------------------
# Maturity evaluation
# ---------------------------------------------------------------------------


def compute_capability_maturity(evidence: CapabilityPlanningEvidence) -> str:
    """Compute the raw capability planning maturity level."""
    if evidence.is_dry_run:
        return "L0_SIMULATED"

    for level in reversed(CAPABILITY_MATURITY_LEVELS):
        reqs = CAPABILITY_MATURITY_REQUIREMENTS[level]
        if all(_check_evidence(evidence, r) for r in reqs):
            return level

    return "L0_SIMULATED"


def _check_evidence(evidence: CapabilityPlanningEvidence, requirement: str) -> bool:
    """Check a single evidence field."""
    field_map: dict[str, bool] = {
        "actuation_proven": evidence.actuation_proven,
        "cu_ingestion_proven": evidence.cu_ingestion_proven,
        "environment_mapped": evidence.environment_mapped,
        "blueprints_generated": evidence.blueprints_generated,
        "replay_contracts_defined": evidence.replay_contracts_defined,
        "governance_classified": evidence.governance_classified,
        "capability_graph_generated": evidence.capability_graph_generated,
        "leverage_analyzed": evidence.leverage_analyzed,
        "upgrade_paths_proposed": evidence.upgrade_paths_proposed,
    }
    return field_map.get(requirement, False)


def capability_maturity_ceiling(evidence: CapabilityPlanningEvidence) -> str:
    """Compute hard ceiling for capability planning maturity."""
    if evidence.is_dry_run:
        return "L0_SIMULATED"
    if not evidence.screenshots_present:
        return "L1_VISIBLE_ACTUATION"
    if not evidence.environment_mapped:
        return "L2_FOREGROUND_CU_INGESTION"
    if not evidence.blueprints_generated:
        return "L3_ENVIRONMENT_INTELLIGENCE"
    if not evidence.governance_classified:
        return "L3_ENVIRONMENT_INTELLIGENCE"
    if not evidence.capability_graph_generated:
        return "L4_ADAPTER_MATURITY"
    if not evidence.leverage_analyzed:
        return "L4_ADAPTER_MATURITY"
    if not evidence.founder_confirmed:
        return "L4_ADAPTER_MATURITY"
    return "L5_RECURSIVE_CAPABILITY_PLANNING"


def _level_index(level: str) -> int:
    try:
        return CAPABILITY_MATURITY_LEVELS.index(level)
    except ValueError:
        return 0


def classify_capability_maturity(
    evidence: CapabilityPlanningEvidence,
) -> tuple[str, str, bool, str]:
    """Classify capability maturity: (level, ceiling, blocked, reason)."""
    raw = compute_capability_maturity(evidence)
    ceiling = capability_maturity_ceiling(evidence)

    raw_idx = _level_index(raw)
    ceil_idx = _level_index(ceiling)

    if ceil_idx < raw_idx:
        return ceiling, ceiling, True, f"ceiling {ceiling} blocks {raw}"

    return raw, ceiling, False, ""


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_planning_evidence(
    env_proof: EnvironmentMappingProof | None = None,
    adapter_proof: AdapterAutogenProof | None = None,
    graph: CapabilityGraph | None = None,
    bottlenecks: list[Bottleneck] | None = None,
    proposals: list[UpgradeProposal] | None = None,
    reuse_ops: list[dict[str, str]] | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
) -> CapabilityPlanningEvidence:
    """Build evidence from substrate analysis."""
    has_env = env_proof is not None and env_proof.maturity_level != "L0_NO_MAPPING"

    has_adapter = adapter_proof is not None
    has_blueprints = (
        has_adapter
        and adapter_proof.evidence is not None
        and adapter_proof.evidence.blueprints_generated
    )
    has_replay = (
        has_adapter
        and adapter_proof.evidence is not None
        and adapter_proof.evidence.replay_contracts_defined
    )
    has_governance = (
        has_adapter
        and adapter_proof.evidence is not None
        and adapter_proof.evidence.governance_classified
    )
    has_screenshots = False
    actuation = False
    cu_ingestion = False

    if has_adapter and adapter_proof.evidence is not None:
        has_screenshots = adapter_proof.evidence.screenshots_present
        actuation = adapter_proof.evidence.actuation_proven
        cu_ingestion = adapter_proof.evidence.cu_ingestion_proven
    elif has_env and env_proof.evidence is not None:
        has_screenshots = env_proof.evidence.has_screenshots
        actuation = True
        cu_ingestion = True

    has_graph = graph is not None and graph.proven_count > 0
    has_bottlenecks = bottlenecks is not None and len(bottlenecks) > 0
    has_proposals = proposals is not None and len(proposals) > 0
    has_reuse = reuse_ops is not None and len(reuse_ops) > 0

    gov_gaps = 0
    replay_gaps = 0
    if graph:
        gov_gaps = sum(1 for n in graph.nodes if n.proven and not n.governance_covered)
        replay_gaps = sum(1 for n in graph.nodes if n.proven and not n.replayable)

    return CapabilityPlanningEvidence(
        capability_graph_generated=has_graph,
        capability_count=len(graph.nodes) if graph else 0,
        proven_count=graph.proven_count if graph else 0,
        missing_count=graph.missing_count if graph else 0,
        leverage_analyzed=has_proposals,
        leverage_score_count=len(proposals) if proposals else 0,
        bottlenecks_identified=has_bottlenecks,
        bottleneck_count=len(bottlenecks) if bottlenecks else 0,
        upgrade_paths_proposed=has_proposals,
        upgrade_count=len(proposals) if proposals else 0,
        governance_analyzed=has_governance,
        governance_gaps=gov_gaps,
        replay_analyzed=has_replay,
        replay_gaps=replay_gaps,
        infrastructure_reuse_found=has_reuse,
        reuse_count=len(reuse_ops) if reuse_ops else 0,
        actuation_proven=actuation,
        cu_ingestion_proven=cu_ingestion,
        environment_mapped=has_env,
        blueprints_generated=has_blueprints,
        replay_contracts_defined=has_replay,
        governance_classified=has_governance,
        screenshots_present=has_screenshots,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )


def build_full_capability_proof(
    env_proof: EnvironmentMappingProof | None = None,
    adapter_proof: AdapterAutogenProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
) -> CapabilityPlanningProof:
    """Full recursive capability planning pipeline."""
    stub_evidence = CapabilityPlanningEvidence(
        actuation_proven=adapter_proof.evidence.actuation_proven
        if adapter_proof and adapter_proof.evidence
        else (env_proof is not None and env_proof.maturity_level != "L0_NO_MAPPING"),
        cu_ingestion_proven=adapter_proof.evidence.cu_ingestion_proven
        if adapter_proof and adapter_proof.evidence
        else (
            env_proof is not None
            and env_proof.maturity_level not in ("L0_NO_MAPPING", "L1_PROCESSES_ENUMERATED")
        ),
        environment_mapped=env_proof is not None and env_proof.maturity_level != "L0_NO_MAPPING",
        blueprints_generated=adapter_proof.evidence.blueprints_generated
        if adapter_proof and adapter_proof.evidence
        else False,
        replay_contracts_defined=adapter_proof.evidence.replay_contracts_defined
        if adapter_proof and adapter_proof.evidence
        else False,
        governance_classified=adapter_proof.evidence.governance_classified
        if adapter_proof and adapter_proof.evidence
        else False,
        screenshots_present=adapter_proof.evidence.screenshots_present
        if adapter_proof and adapter_proof.evidence
        else (
            env_proof is not None
            and env_proof.evidence is not None
            and env_proof.evidence.has_screenshots
        ),
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
    )

    graph = build_capability_graph(stub_evidence)

    stub_evidence.capability_graph_generated = graph.proven_count > 0

    bottlenecks = analyze_bottlenecks(stub_evidence, graph)
    proposals = generate_upgrade_proposals(stub_evidence, graph)
    reuse_ops = find_infrastructure_reuse(graph, proposals)

    evidence = build_planning_evidence(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        graph=graph,
        bottlenecks=bottlenecks,
        proposals=proposals,
        reuse_ops=reuse_ops,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    level, ceiling, blocked, reason = classify_capability_maturity(evidence)

    safest = ""
    highest = ""
    if proposals:
        safest = proposals[-1].name if proposals else ""
        highest = proposals[0].name if proposals else ""

    strategy = (
        "simulation_only"
        if is_dry_run
        else (
            "prove_prerequisites_first"
            if not stub_evidence.actuation_proven
            else "execute_safest_upgrade"
            if founder_confirmed
            else "await_founder_confirmation"
        )
    )

    return CapabilityPlanningProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        capability_graph=graph,
        bottlenecks=bottlenecks,
        upgrade_proposals=proposals,
        safest_next_phase=safest,
        highest_leverage_upgrade=highest,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_capability_proof(
    proof: CapabilityPlanningProof,
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist capability planning proof to disk."""
    out_dir = base_dir / CAPABILITY_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{proof.proof_id}.json"
    path = out_dir / filename
    with open(path, "w") as f:
        json.dump(proof.to_dict(), f, indent=2)
    return path
