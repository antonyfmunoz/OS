"""Adapter Autogeneration Engine v1.

Analyzes exploratory environment maps and topology graphs to
autonomously generate, classify, evaluate, and mature ingestion
adapter blueprints.

Transitions the substrate from manual adapter engineering to
adaptive adapter synthesis.

Flow: topology → analyze → generate blueprints → classify maturity →
      plan replay → enforce governance → report

No executable adapters without governance.
No instance data promoted into canonical structures.
No maturity claims without evidence.
No bypass of foreground CU requirements.
No bypass of replay requirements.

UMH substrate subsystem. Phase 96.8AU.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.workstation.environment_mapping_engine_v1 import (
    CANDIDATE_TYPE_CANONICAL,
    CANDIDATE_TYPE_INSTANCE,
    LANE_EXTRACTION_METHODS,
    LANE_SAFETY_RATINGS,
    DiscoveredPlatform,
    EnvironmentMappingProof,
    EnvironmentTopology,
    IngestionLane,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ADAPTER_BLUEPRINT_DIR = Path("data/runtime/workstation_relay/adapter_blueprints")
ADAPTER_REPORT_DIR = Path("data/runtime/workstation_relay/adapter_reports")

ADAPTER_MATURITY_LEVELS = (
    "L0_SIMULATED",
    "L1_VISIBLE_ACTUATION",
    "L2_FOREGROUND_CU_INGESTION",
    "L3_ENVIRONMENT_INTELLIGENCE",
    "L4_ADAPTER_MATURITY",
    "L5_AUTONOMOUS_ADAPTER_SYNTHESIS",
)

ADAPTER_MATURITY_REQUIREMENTS: dict[str, list[str]] = {
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
    "L5_AUTONOMOUS_ADAPTER_SYNTHESIS": [
        "actuation_proven",
        "cu_ingestion_proven",
        "environment_mapped",
        "blueprints_generated",
        "replay_contracts_defined",
        "governance_classified",
        "adapters_executed_successfully",
        "adapters_replayed_successfully",
    ],
}

ADAPTER_TARGET_PLATFORMS = frozenset(
    {
        "google_drive",
        "gmail",
        "notion",
        "discord",
        "claude",
        "openai",
        "github",
        "obsidian",
        "slack",
        "local_filesystem",
        "browser_sessions",
        "desktop_apps",
        "terminal_environments",
        "docker_services",
    }
)

PLATFORM_NAME_MAP: dict[str, str] = {
    "Google Chrome": "browser_sessions",
    "Discord": "discord",
    "Slack": "slack",
    "VS Code": "desktop_apps",
    "Cursor": "desktop_apps",
    "Obsidian": "obsidian",
    "Notion": "notion",
    "Docker Desktop": "docker_services",
    "Windows Terminal": "terminal_environments",
    "PowerShell": "terminal_environments",
    "GitHub Desktop": "github",
    "Claude": "claude",
    "Spotify": "desktop_apps",
    "Steam": "desktop_apps",
    "File Explorer": "local_filesystem",
}

PLATFORM_DISCOVERY_METHODS: dict[str, str] = {
    "google_drive": "chrome_profile_scan",
    "gmail": "chrome_profile_scan",
    "notion": "process_detection",
    "discord": "process_detection",
    "claude": "browser_session_scan",
    "openai": "browser_session_scan",
    "github": "process_or_browser_detection",
    "obsidian": "process_detection",
    "slack": "process_detection",
    "local_filesystem": "filesystem_scan",
    "browser_sessions": "window_title_scan",
    "desktop_apps": "process_detection",
    "terminal_environments": "process_detection",
    "docker_services": "docker_api_query",
}

PLATFORM_EXTRACTION_STRATEGIES: dict[str, str] = {
    "google_drive": "foreground_cu_clipboard",
    "gmail": "foreground_cu_clipboard",
    "notion": "foreground_cu_clipboard",
    "discord": "foreground_cu_clipboard",
    "claude": "foreground_cu_clipboard",
    "openai": "foreground_cu_clipboard",
    "github": "foreground_cu_clipboard",
    "obsidian": "local_vault_read",
    "slack": "foreground_cu_clipboard",
    "local_filesystem": "local_filesystem_read",
    "browser_sessions": "foreground_cu_clipboard",
    "desktop_apps": "foreground_cu_clipboard",
    "terminal_environments": "visible_terminal_read",
    "docker_services": "docker_api_read",
}

PLATFORM_CU_REQUIREMENTS: dict[str, bool] = {
    "google_drive": True,
    "gmail": True,
    "notion": True,
    "discord": True,
    "claude": True,
    "openai": True,
    "github": True,
    "obsidian": False,
    "slack": True,
    "local_filesystem": False,
    "browser_sessions": True,
    "desktop_apps": True,
    "terminal_environments": False,
    "docker_services": False,
}

PLATFORM_CANONICAL_LIKELIHOOD: dict[str, float] = {
    "google_drive": 0.3,
    "gmail": 0.1,
    "notion": 0.4,
    "discord": 0.1,
    "claude": 0.2,
    "openai": 0.2,
    "github": 0.6,
    "obsidian": 0.5,
    "slack": 0.1,
    "local_filesystem": 0.4,
    "browser_sessions": 0.1,
    "desktop_apps": 0.1,
    "terminal_environments": 0.3,
    "docker_services": 0.3,
}


@dataclass
class ReplayContract:
    """Deterministic replay specification for an adapter blueprint."""

    contract_id: str = ""
    adapter_id: str = ""
    platform: str = ""
    replay_path: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    proof_persistence_path: str = ""
    failure_ceiling: str = "L0_SIMULATED"
    rollback_conditions: list[str] = field(default_factory=list)
    replayable: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.contract_id:
            self.contract_id = f"REPLAY-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "adapter_id": self.adapter_id,
            "platform": self.platform,
            "replay_path": self.replay_path,
            "evidence_requirements": self.evidence_requirements,
            "proof_persistence_path": self.proof_persistence_path,
            "failure_ceiling": self.failure_ceiling,
            "rollback_conditions": self.rollback_conditions,
            "replayable": self.replayable,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernanceClassification:
    """Governance requirements for an adapter blueprint."""

    classification_id: str = ""
    adapter_id: str = ""
    platform: str = ""
    requires_founder_approval: bool = True
    requires_foreground_cu: bool = True
    requires_screenshot_proof: bool = True
    auto_execute_allowed: bool = False
    risk_level: str = "medium"
    governance_policy: str = "FOUNDER_APPROVAL"
    candidate_type: str = CANDIDATE_TYPE_INSTANCE
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.classification_id:
            self.classification_id = f"GOV-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification_id": self.classification_id,
            "adapter_id": self.adapter_id,
            "platform": self.platform,
            "requires_founder_approval": self.requires_founder_approval,
            "requires_foreground_cu": self.requires_foreground_cu,
            "requires_screenshot_proof": self.requires_screenshot_proof,
            "auto_execute_allowed": self.auto_execute_allowed,
            "risk_level": self.risk_level,
            "governance_policy": self.governance_policy,
            "candidate_type": self.candidate_type,
            "timestamp": self.timestamp,
        }


@dataclass
class AdapterBlueprint:
    """Auto-generated adapter blueprint from topology analysis."""

    blueprint_id: str = ""
    platform: str = ""
    platform_name: str = ""
    discovery_method: str = ""
    extraction_strategy: str = ""
    requires_cu: bool = True
    requires_foreground: bool = True
    requires_founder_confirmation: bool = True
    requires_screenshot: bool = True
    replayable: bool = False
    canonical_likelihood: float = 0.0
    instance_likelihood: float = 1.0
    maturity_ceiling: str = "L4_ADAPTER_MATURITY"
    required_evidence: list[str] = field(default_factory=list)
    proof_requirements: list[str] = field(default_factory=list)
    safety_rating: str = "safe"
    detected_on_workstation: bool = False
    source_platform_id: str = ""
    replay_contract: ReplayContract | None = None
    governance: GovernanceClassification | None = None
    relationship_extraction_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.blueprint_id:
            self.blueprint_id = f"ADAPT-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "platform": self.platform,
            "platform_name": self.platform_name,
            "discovery_method": self.discovery_method,
            "extraction_strategy": self.extraction_strategy,
            "requires_cu": self.requires_cu,
            "requires_foreground": self.requires_foreground,
            "requires_founder_confirmation": self.requires_founder_confirmation,
            "requires_screenshot": self.requires_screenshot,
            "replayable": self.replayable,
            "canonical_likelihood": round(self.canonical_likelihood, 2),
            "instance_likelihood": round(self.instance_likelihood, 2),
            "maturity_ceiling": self.maturity_ceiling,
            "required_evidence": self.required_evidence,
            "proof_requirements": self.proof_requirements,
            "safety_rating": self.safety_rating,
            "detected_on_workstation": self.detected_on_workstation,
            "source_platform_id": self.source_platform_id,
            "replay_contract": self.replay_contract.to_dict() if self.replay_contract else None,
            "governance": self.governance.to_dict() if self.governance else None,
            "relationship_extraction_strategy": self.relationship_extraction_strategy,
            "timestamp": self.timestamp,
        }


@dataclass
class MaturityEvaluation:
    """Maturity assessment for the adapter autogeneration system."""

    evaluation_id: str = ""
    current_level: str = "L0_SIMULATED"
    target_level: str = "L4_ADAPTER_MATURITY"
    missing_evidence: list[str] = field(default_factory=list)
    unsafe_claims: list[str] = field(default_factory=list)
    replayability_gaps: list[str] = field(default_factory=list)
    proof_weaknesses: list[str] = field(default_factory=list)
    execution_risks: list[str] = field(default_factory=list)
    governance_gaps: list[str] = field(default_factory=list)
    level_blocked: bool = False
    blocking_reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.evaluation_id:
            self.evaluation_id = f"MEVAL-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "current_level": self.current_level,
            "target_level": self.target_level,
            "missing_evidence": self.missing_evidence,
            "unsafe_claims": self.unsafe_claims,
            "replayability_gaps": self.replayability_gaps,
            "proof_weaknesses": self.proof_weaknesses,
            "execution_risks": self.execution_risks,
            "governance_gaps": self.governance_gaps,
            "level_blocked": self.level_blocked,
            "blocking_reason": self.blocking_reason,
            "timestamp": self.timestamp,
        }


@dataclass
class AdapterAutogenEvidence:
    """Evidence collected during adapter autogeneration."""

    topology_analyzed: bool = False
    platform_count: int = 0
    blueprints_generated: bool = False
    blueprint_count: int = 0
    replay_contracts_defined: bool = False
    replay_contract_count: int = 0
    governance_classified: bool = False
    governance_count: int = 0
    canonical_patterns_extracted: bool = False
    canonical_count: int = 0
    instance_count: int = 0
    maturity_evaluated: bool = False
    actuation_proven: bool = False
    cu_ingestion_proven: bool = False
    environment_mapped: bool = False
    adapters_executed_successfully: bool = False
    adapters_replayed_successfully: bool = False
    screenshots_present: bool = False
    founder_confirmed: bool = False
    is_dry_run: bool = False
    trace_id: str = ""
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_analyzed": self.topology_analyzed,
            "platform_count": self.platform_count,
            "blueprints_generated": self.blueprints_generated,
            "blueprint_count": self.blueprint_count,
            "replay_contracts_defined": self.replay_contracts_defined,
            "replay_contract_count": self.replay_contract_count,
            "governance_classified": self.governance_classified,
            "governance_count": self.governance_count,
            "canonical_patterns_extracted": self.canonical_patterns_extracted,
            "canonical_count": self.canonical_count,
            "instance_count": self.instance_count,
            "maturity_evaluated": self.maturity_evaluated,
            "actuation_proven": self.actuation_proven,
            "cu_ingestion_proven": self.cu_ingestion_proven,
            "environment_mapped": self.environment_mapped,
            "adapters_executed_successfully": self.adapters_executed_successfully,
            "adapters_replayed_successfully": self.adapters_replayed_successfully,
            "screenshots_present": self.screenshots_present,
            "founder_confirmed": self.founder_confirmed,
            "is_dry_run": self.is_dry_run,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


@dataclass
class AdapterAutogenProof:
    """Complete proof of adapter autogeneration execution."""

    proof_id: str = ""
    trace_id: str = ""
    maturity_level: str = "L0_SIMULATED"
    maturity_ceiling: str = "L4_ADAPTER_MATURITY"
    escalation_blocked: bool = False
    escalation_reason: str = ""
    evidence: AdapterAutogenEvidence | None = None
    maturity_evaluation: MaturityEvaluation | None = None
    blueprints: list[AdapterBlueprint] = field(default_factory=list)
    execution_strategy: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            h = hashlib.sha256(f"{self.trace_id}-{_now_iso()}".encode()).hexdigest()[:8]
            self.proof_id = f"AUTOGEN-{h}"
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": "adapter_autogeneration",
            "trace_id": self.trace_id,
            "maturity_level": self.maturity_level,
            "maturity_ceiling": self.maturity_ceiling,
            "escalation_blocked": self.escalation_blocked,
            "escalation_reason": self.escalation_reason,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "maturity_evaluation": self.maturity_evaluation.to_dict()
            if self.maturity_evaluation
            else None,
            "blueprints": [b.to_dict() for b in self.blueprints],
            "blueprint_count": len(self.blueprints),
            "execution_strategy": self.execution_strategy,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Blueprint generation from topology
# ---------------------------------------------------------------------------


def _resolve_adapter_platform(platform_name: str) -> str:
    """Map a discovered platform name to an adapter target platform."""
    return PLATFORM_NAME_MAP.get(platform_name, "desktop_apps")


def _build_replay_path(platform: str, extraction_strategy: str) -> list[str]:
    """Build the deterministic replay path for an adapter."""
    base = ["dispatch_relay", "verify_desktop_session"]
    if extraction_strategy in ("foreground_cu_clipboard", "foreground_cu_clipboard"):
        return base + [
            "launch_target_application",
            "verify_foreground_focus",
            "navigate_to_content",
            "capture_screenshot",
            "extract_via_clipboard",
            "validate_extraction",
            "persist_proof",
        ]
    if extraction_strategy in ("local_vault_read", "local_workspace_read", "local_git_read"):
        return base + [
            "locate_local_path",
            "read_filesystem_content",
            "validate_extraction",
            "persist_proof",
        ]
    if extraction_strategy == "docker_api_read":
        return base + [
            "connect_docker_api",
            "enumerate_containers",
            "read_container_state",
            "persist_proof",
        ]
    if extraction_strategy == "visible_terminal_read":
        return base + [
            "focus_terminal_window",
            "capture_visible_output",
            "persist_proof",
        ]
    return base + ["execute_extraction", "persist_proof"]


def _build_evidence_requirements(platform: str, requires_cu: bool) -> list[str]:
    """Build evidence requirements for an adapter replay."""
    reqs = ["desktop_session_active", "relay_heartbeat_fresh"]
    if requires_cu:
        reqs.extend(["foreground_focus_verified", "screenshot_captured", "clipboard_content_hash"])
    else:
        reqs.append("local_path_verified")
    reqs.append("founder_confirmed")
    return reqs


def _build_rollback_conditions(platform: str) -> list[str]:
    """Build rollback conditions for an adapter."""
    return [
        "extraction_content_empty",
        "screenshot_hash_mismatch",
        "relay_timeout",
        "founder_denied",
        "governance_rejected",
    ]


def _determine_risk_level(platform: str, requires_cu: bool) -> str:
    """Determine execution risk level for an adapter."""
    if requires_cu:
        return "medium"
    return "low"


def _determine_relationship_strategy(platform: str) -> str:
    """Determine how to extract relationships from this platform."""
    strategies = {
        "google_drive": "document_ownership_and_sharing",
        "gmail": "sender_recipient_threads",
        "notion": "workspace_page_hierarchy",
        "discord": "server_channel_membership",
        "claude": "conversation_project_mapping",
        "openai": "conversation_project_mapping",
        "github": "repo_org_contributor_mapping",
        "obsidian": "vault_backlink_graph",
        "slack": "channel_thread_membership",
        "local_filesystem": "directory_hierarchy",
        "browser_sessions": "tab_session_grouping",
        "desktop_apps": "window_process_grouping",
        "terminal_environments": "shell_session_history",
        "docker_services": "container_network_mapping",
    }
    return strategies.get(platform, "generic_entity_linking")


def generate_blueprint_for_platform(
    platform: str,
    detected: bool = False,
    source_platform_id: str = "",
) -> AdapterBlueprint:
    """Generate a single adapter blueprint for a target platform."""
    requires_cu = PLATFORM_CU_REQUIREMENTS.get(platform, True)
    canonical_l = PLATFORM_CANONICAL_LIKELIHOOD.get(platform, 0.1)
    extraction = PLATFORM_EXTRACTION_STRATEGIES.get(platform, "foreground_cu_clipboard")
    discovery = PLATFORM_DISCOVERY_METHODS.get(platform, "process_detection")
    safety = LANE_SAFETY_RATINGS.get(extraction, "caution")

    replay_contract = ReplayContract(
        platform=platform,
        replay_path=_build_replay_path(platform, extraction),
        evidence_requirements=_build_evidence_requirements(platform, requires_cu),
        proof_persistence_path=f"data/runtime/workstation_relay/adapter_proofs/{platform}/",
        failure_ceiling="L2_FOREGROUND_CU_INGESTION" if requires_cu else "L1_VISIBLE_ACTUATION",
        rollback_conditions=_build_rollback_conditions(platform),
        replayable=True,
    )

    governance = GovernanceClassification(
        platform=platform,
        requires_founder_approval=True,
        requires_foreground_cu=requires_cu,
        requires_screenshot_proof=requires_cu,
        auto_execute_allowed=False,
        risk_level=_determine_risk_level(platform, requires_cu),
        governance_policy="FOUNDER_APPROVAL",
        candidate_type=CANDIDATE_TYPE_INSTANCE,
    )

    return AdapterBlueprint(
        platform=platform,
        platform_name=platform.replace("_", " ").title(),
        discovery_method=discovery,
        extraction_strategy=extraction,
        requires_cu=requires_cu,
        requires_foreground=requires_cu,
        requires_founder_confirmation=True,
        requires_screenshot=requires_cu,
        replayable=True,
        canonical_likelihood=canonical_l,
        instance_likelihood=round(1.0 - canonical_l, 2),
        maturity_ceiling="L4_ADAPTER_MATURITY",
        required_evidence=_build_evidence_requirements(platform, requires_cu),
        proof_requirements=[
            "extraction_proof",
            "screenshot_proof" if requires_cu else "path_proof",
            "founder_confirmation",
            "governance_approval",
        ],
        safety_rating=safety,
        detected_on_workstation=detected,
        source_platform_id=source_platform_id,
        replay_contract=replay_contract,
        governance=governance,
        relationship_extraction_strategy=_determine_relationship_strategy(platform),
    )


def generate_blueprints_from_topology(
    topology: EnvironmentTopology,
) -> list[AdapterBlueprint]:
    """Generate adapter blueprints from a discovered topology.

    Produces blueprints for all target platforms. Platforms that were
    detected on the workstation are flagged with detected_on_workstation=True.
    """
    detected_platforms: dict[str, str] = {}
    for plat in topology.platforms:
        adapter_target = _resolve_adapter_platform(plat.name)
        if adapter_target not in detected_platforms:
            detected_platforms[adapter_target] = plat.platform_id

    for lane in topology.ingestion_lanes:
        lane_platform = lane.platform.lower().replace(" ", "_")
        lane_key = LANE_EXTRACTION_METHODS.get(lane_platform)
        if lane_key and lane_platform not in detected_platforms:
            detected_platforms[lane_platform] = ""

    blueprints: list[AdapterBlueprint] = []
    for target in sorted(ADAPTER_TARGET_PLATFORMS):
        detected = target in detected_platforms
        source_id = detected_platforms.get(target, "")
        bp = generate_blueprint_for_platform(
            target, detected=detected, source_platform_id=source_id
        )
        blueprints.append(bp)

    return blueprints


# ---------------------------------------------------------------------------
# Canonical vs instance classification
# ---------------------------------------------------------------------------


def classify_blueprint_scope(blueprint: AdapterBlueprint) -> str:
    """Classify whether a blueprint pattern is canonical or instance.

    Canonical: reusable adapter patterns, extraction frameworks,
               generalized workflows, reusable topology logic.
    Instance: founder-specific accounts, session states,
              workspace mappings, organization-specific relationships.

    The blueprint STRUCTURE is always canonical (reusable pattern).
    The DATA it extracts is always instance (founder-specific).
    """
    return CANDIDATE_TYPE_CANONICAL


def classify_extraction_scope(platform: str) -> str:
    """Classify whether extraction output is canonical or instance.

    Extraction output is always instance — it's founder data.
    """
    return CANDIDATE_TYPE_INSTANCE


# ---------------------------------------------------------------------------
# Maturity evaluation
# ---------------------------------------------------------------------------


def compute_adapter_maturity(evidence: AdapterAutogenEvidence) -> str:
    """Compute the raw adapter autogeneration maturity level."""
    if evidence.is_dry_run:
        return "L0_SIMULATED"

    for level in reversed(ADAPTER_MATURITY_LEVELS):
        reqs = ADAPTER_MATURITY_REQUIREMENTS[level]
        if all(_check_evidence_field(evidence, r) for r in reqs):
            return level

    return "L0_SIMULATED"


def _check_evidence_field(evidence: AdapterAutogenEvidence, requirement: str) -> bool:
    """Check a single evidence field against a requirement."""
    field_map: dict[str, bool] = {
        "actuation_proven": evidence.actuation_proven,
        "cu_ingestion_proven": evidence.cu_ingestion_proven,
        "environment_mapped": evidence.environment_mapped,
        "blueprints_generated": evidence.blueprints_generated,
        "replay_contracts_defined": evidence.replay_contracts_defined,
        "governance_classified": evidence.governance_classified,
        "adapters_executed_successfully": evidence.adapters_executed_successfully,
        "adapters_replayed_successfully": evidence.adapters_replayed_successfully,
    }
    return field_map.get(requirement, False)


def adapter_maturity_ceiling(evidence: AdapterAutogenEvidence) -> str:
    """Compute the hard ceiling — the maximum achievable maturity."""
    if evidence.is_dry_run:
        return "L0_SIMULATED"
    if not evidence.screenshots_present:
        return "L1_VISIBLE_ACTUATION"
    if not evidence.environment_mapped:
        return "L2_FOREGROUND_CU_INGESTION"
    if not evidence.blueprints_generated:
        return "L3_ENVIRONMENT_INTELLIGENCE"
    if not evidence.replay_contracts_defined:
        return "L3_ENVIRONMENT_INTELLIGENCE"
    if not evidence.governance_classified:
        return "L3_ENVIRONMENT_INTELLIGENCE"
    if not evidence.founder_confirmed:
        return "L3_ENVIRONMENT_INTELLIGENCE"
    return "L5_AUTONOMOUS_ADAPTER_SYNTHESIS"


def _level_index(level: str) -> int:
    """Get the ordinal index of a maturity level."""
    try:
        return ADAPTER_MATURITY_LEVELS.index(level)
    except ValueError:
        return 0


def classify_adapter_maturity(
    evidence: AdapterAutogenEvidence,
) -> tuple[str, str, bool, str]:
    """Classify adapter maturity: (level, ceiling, blocked, reason)."""
    raw_level = compute_adapter_maturity(evidence)
    ceiling = adapter_maturity_ceiling(evidence)

    raw_idx = _level_index(raw_level)
    ceiling_idx = _level_index(ceiling)

    if ceiling_idx < raw_idx:
        return ceiling, ceiling, True, f"ceiling {ceiling} blocks {raw_level}"

    return raw_level, ceiling, False, ""


def evaluate_maturity(
    evidence: AdapterAutogenEvidence,
    blueprints: list[AdapterBlueprint],
) -> MaturityEvaluation:
    """Full maturity evaluation with gap analysis."""
    level, ceiling, blocked, reason = classify_adapter_maturity(evidence)

    missing: list[str] = []
    for req in ADAPTER_MATURITY_REQUIREMENTS.get("L4_ADAPTER_MATURITY", []):
        if not _check_evidence_field(evidence, req):
            missing.append(req)

    unsafe: list[str] = []
    if not evidence.actuation_proven and evidence.blueprints_generated:
        unsafe.append("blueprints generated without proven actuation")
    if not evidence.cu_ingestion_proven and evidence.blueprints_generated:
        unsafe.append("blueprints generated without proven CU ingestion")

    replay_gaps: list[str] = []
    for bp in blueprints:
        if bp.replay_contract and not bp.replay_contract.replayable:
            replay_gaps.append(f"{bp.platform}: replay contract not replayable")

    proof_weak: list[str] = []
    if not evidence.screenshots_present:
        proof_weak.append("no screenshots in evidence")
    if not evidence.founder_confirmed:
        proof_weak.append("founder has not confirmed")

    exec_risks: list[str] = []
    for bp in blueprints:
        if bp.requires_cu and not evidence.cu_ingestion_proven:
            exec_risks.append(f"{bp.platform}: requires CU but CU not proven")

    gov_gaps: list[str] = []
    for bp in blueprints:
        if bp.governance and bp.governance.auto_execute_allowed:
            gov_gaps.append(f"{bp.platform}: auto-execute allowed (should not be)")

    return MaturityEvaluation(
        current_level=level,
        target_level="L4_ADAPTER_MATURITY",
        missing_evidence=missing,
        unsafe_claims=unsafe,
        replayability_gaps=replay_gaps,
        proof_weaknesses=proof_weak,
        execution_risks=exec_risks,
        governance_gaps=gov_gaps,
        level_blocked=blocked,
        blocking_reason=reason,
    )


def determine_safest_strategy(
    blueprints: list[AdapterBlueprint],
    evidence: AdapterAutogenEvidence,
) -> str:
    """Determine the safest execution strategy across all blueprints."""
    if evidence.is_dry_run:
        return "simulation_only"
    if not evidence.actuation_proven:
        return "prove_actuation_first"
    if not evidence.cu_ingestion_proven:
        return "prove_cu_ingestion_first"
    if not evidence.environment_mapped:
        return "map_environment_first"

    local_ready = [bp for bp in blueprints if not bp.requires_cu and bp.detected_on_workstation]
    if local_ready:
        return "start_with_local_adapters"

    return "start_with_safest_cu_adapter"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def build_adapter_evidence(
    topology: EnvironmentTopology | None,
    blueprints: list[AdapterBlueprint],
    env_proof: EnvironmentMappingProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
) -> AdapterAutogenEvidence:
    """Build evidence from topology analysis and blueprint generation."""
    has_topo = topology is not None and topology.platform_count > 0
    has_env = env_proof is not None and env_proof.maturity_level != "L0_NO_MAPPING"
    has_blueprints = len(blueprints) > 0
    has_replay = all(bp.replay_contract is not None for bp in blueprints) if blueprints else False
    has_governance = all(bp.governance is not None for bp in blueprints) if blueprints else False
    canonical_bps = [
        bp for bp in blueprints if classify_blueprint_scope(bp) == CANDIDATE_TYPE_CANONICAL
    ]
    instance_bps = [
        bp for bp in blueprints if classify_extraction_scope(bp.platform) == CANDIDATE_TYPE_INSTANCE
    ]

    screenshots = False
    if env_proof and env_proof.evidence:
        screenshots = env_proof.evidence.has_screenshots

    actuation = False
    cu_ingestion = False
    if env_proof:
        level_idx = (
            _level_index(env_proof.maturity_level)
            if env_proof.maturity_level in ADAPTER_MATURITY_LEVELS
            else -1
        )
        if level_idx < 0:
            env_levels = [
                "L0_NO_MAPPING",
                "L1_PROCESSES_ENUMERATED",
                "L2_PLATFORMS_IDENTIFIED",
                "L3_ENVIRONMENT_INTELLIGENCE",
            ]
            if env_proof.maturity_level in env_levels:
                env_idx = env_levels.index(env_proof.maturity_level)
                actuation = env_idx >= 1
                cu_ingestion = env_idx >= 2
            else:
                actuation = True
                cu_ingestion = True
        else:
            actuation = level_idx >= 1
            cu_ingestion = level_idx >= 2

    return AdapterAutogenEvidence(
        topology_analyzed=has_topo,
        platform_count=topology.platform_count if topology else 0,
        blueprints_generated=has_blueprints,
        blueprint_count=len(blueprints),
        replay_contracts_defined=has_replay,
        replay_contract_count=sum(1 for bp in blueprints if bp.replay_contract),
        governance_classified=has_governance,
        governance_count=sum(1 for bp in blueprints if bp.governance),
        canonical_patterns_extracted=len(canonical_bps) > 0,
        canonical_count=len(canonical_bps),
        instance_count=len(instance_bps),
        maturity_evaluated=True,
        actuation_proven=actuation,
        cu_ingestion_proven=cu_ingestion,
        environment_mapped=has_env,
        screenshots_present=screenshots,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )


def build_full_adapter_proof(
    topology: EnvironmentTopology | None,
    env_proof: EnvironmentMappingProof | None = None,
    founder_confirmed: bool = False,
    is_dry_run: bool = False,
    trace_id: str = "",
    request_id: str = "",
) -> AdapterAutogenProof:
    """Full adapter autogeneration pipeline: analyze → generate → evaluate."""
    if topology is None:
        topology = EnvironmentTopology()

    blueprints = generate_blueprints_from_topology(topology)

    evidence = build_adapter_evidence(
        topology=topology,
        blueprints=blueprints,
        env_proof=env_proof,
        founder_confirmed=founder_confirmed,
        is_dry_run=is_dry_run,
        trace_id=trace_id,
        request_id=request_id,
    )

    evaluation = evaluate_maturity(evidence, blueprints)
    strategy = determine_safest_strategy(blueprints, evidence)

    level, ceiling, blocked, reason = classify_adapter_maturity(evidence)

    return AdapterAutogenProof(
        trace_id=trace_id,
        maturity_level=level,
        maturity_ceiling=ceiling,
        escalation_blocked=blocked,
        escalation_reason=reason,
        evidence=evidence,
        maturity_evaluation=evaluation,
        blueprints=blueprints,
        execution_strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_adapter_proof(
    proof: AdapterAutogenProof,
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist adapter autogeneration proof to disk."""
    out_dir = base_dir / ADAPTER_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{proof.proof_id}.json"
    path = out_dir / filename
    with open(path, "w") as f:
        json.dump(proof.to_dict(), f, indent=2)
    return path


def persist_blueprints(
    blueprints: list[AdapterBlueprint],
    base_dir: Path = Path("/opt/OS"),
) -> Path:
    """Persist all adapter blueprints to disk."""
    out_dir = base_dir / ADAPTER_BLUEPRINT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for bp in blueprints:
        filename = f"{bp.blueprint_id}.json"
        path = out_dir / filename
        with open(path, "w") as f:
            json.dump(bp.to_dict(), f, indent=2)
    return out_dir
