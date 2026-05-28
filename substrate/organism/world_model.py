"""World Model — organism-level self-model of UMH system state.

This is NOT the understanding/world_model (knowledge about the domain).
This is the organism knowing ITSELF — what subsystems exist, their state,
evidence for that state, known gaps, and uncertainties.

All extraction is deterministic. No LLM required.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class EntityStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL = "partial"
    DORMANT = "dormant"
    MISSING = "missing"
    UNKNOWN = "unknown"


class EntityCategory(str, Enum):
    SUBSYSTEM = "subsystem"
    CAPABILITY = "capability"
    INTERFACE = "interface"
    RUNTIME = "runtime"
    EXECUTION_PATH = "execution_path"
    GOVERNANCE = "governance"
    MEMORY = "memory"
    COCKPIT_SURFACE = "cockpit_surface"
    DEPLOYMENT = "deployment"
    DATA_STORE = "data_store"
    TRANSPORT = "transport"


class EvidenceType(str, Enum):
    FILE_EXISTS = "file_exists"
    IMPORT_SUCCEEDS = "import_succeeds"
    CLASS_DEFINED = "class_defined"
    ROUTE_REGISTERED = "route_registered"
    CONTAINER_RUNNING = "container_running"
    CONFIG_PRESENT = "config_present"
    DATA_FILE_NONEMPTY = "data_file_nonempty"
    TEST_EXISTS = "test_exists"
    API_RESPONDS = "api_responds"
    DAEMON_WIRED = "daemon_wired"


class GapSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class WorldEvidence:
    evidence_type: EvidenceType
    source: str
    detail: str
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.evidence_type.value,
            "source": self.source,
            "detail": self.detail,
            "observed_at": self.observed_at,
        }


@dataclass
class WorldGap:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    severity: GapSeverity = GapSeverity.MEDIUM
    entity_id: str = ""
    evidence: list[WorldEvidence] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "severity": self.severity.value,
            "entity_id": self.entity_id,
            "evidence": [e.to_dict() for e in self.evidence],
            "recommendation": self.recommendation,
        }


@dataclass
class WorldUncertainty:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    description: str = ""
    entity_id: str = ""
    reason: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "entity_id": self.entity_id,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class WorldCapability:
    name: str
    provided_by: str
    status: EntityStatus = EntityStatus.UNKNOWN
    evidence: list[WorldEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provided_by": self.provided_by,
            "status": self.status.value,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@dataclass
class WorldEntity:
    id: str
    name: str
    category: EntityCategory
    status: EntityStatus = EntityStatus.UNKNOWN
    description: str = ""
    module_path: str = ""
    evidence: list[WorldEvidence] = field(default_factory=list)
    capabilities: list[WorldCapability] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "description": self.description,
            "module_path": self.module_path,
            "evidence": [e.to_dict() for e in self.evidence],
            "capabilities": [c.to_dict() for c in self.capabilities],
            "depends_on": self.depends_on,
        }


@dataclass
class WorldModel:
    entities: dict[str, WorldEntity] = field(default_factory=dict)
    gaps: list[WorldGap] = field(default_factory=list)
    uncertainties: list[WorldUncertainty] = field(default_factory=list)
    extracted_at: float = field(default_factory=time.time)
    repo_root: str = field(default_factory=lambda: _REPO_ROOT)

    def add_entity(self, entity: WorldEntity) -> None:
        self.entities[entity.id] = entity

    def add_gap(self, gap: WorldGap) -> None:
        self.gaps.append(gap)

    def add_uncertainty(self, uncertainty: WorldUncertainty) -> None:
        self.uncertainties.append(uncertainty)

    def get_entity(self, entity_id: str) -> WorldEntity | None:
        return self.entities.get(entity_id)

    def get_entities_by_category(self, category: EntityCategory) -> list[WorldEntity]:
        return [e for e in self.entities.values() if e.category == category]

    def get_entities_by_status(self, status: EntityStatus) -> list[WorldEntity]:
        return [e for e in self.entities.values() if e.status == status]

    def get_gaps_by_severity(self, severity: GapSeverity) -> list[WorldGap]:
        return [g for g in self.gaps if g.severity == severity]

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        for e in self.entities.values():
            status_counts[e.status.value] = status_counts.get(e.status.value, 0) + 1
            category_counts[e.category.value] = category_counts.get(e.category.value, 0) + 1
        severity_counts: dict[str, int] = {}
        for g in self.gaps:
            severity_counts[g.severity.value] = severity_counts.get(g.severity.value, 0) + 1
        return {
            "total_entities": len(self.entities),
            "by_status": status_counts,
            "by_category": category_counts,
            "total_gaps": len(self.gaps),
            "gaps_by_severity": severity_counts,
            "total_uncertainties": len(self.uncertainties),
            "extracted_at": self.extracted_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "gaps": [g.to_dict() for g in self.gaps],
            "uncertainties": [u.to_dict() for u in self.uncertainties],
            "extracted_at": self.extracted_at,
        }


# ---------------------------------------------------------------------------
# Deterministic extractors — each examines a slice of observed reality
# ---------------------------------------------------------------------------

def _check_file(path: str) -> bool:
    return os.path.isfile(path)


def _check_dir(path: str) -> bool:
    return os.path.isdir(path)


def _check_import(module_path: str) -> bool:
    try:
        importlib.import_module(module_path)
        return True
    except Exception:
        return False


def _file_nonempty(path: str) -> bool:
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def _extract_subsystems(model: WorldModel) -> None:
    """Extract core UMH subsystems from observed files."""
    root = model.repo_root
    subsystems = [
        ("event_spine", "EventSpine", "substrate.organism.event_spine",
         "substrate/organism/event_spine.py", "Canonical organism event transport"),
        ("execution_journal", "ExecutionJournal", "substrate.organism.execution_journal",
         "substrate/organism/execution_journal.py", "Append-only execution ledger"),
        ("mutation_registry", "MutationRegistry", "substrate.organism.mutation_registry",
         "substrate/organism/mutation_registry.py", "Canonical mutation type registry"),
        ("autonomous_gateway", "AutonomousActionGateway", "substrate.organism.autonomous_action_gateway",
         "substrate/organism/autonomous_action_gateway.py", "Single funnel for autonomous actions"),
        ("readiness_model", "ReadinessModel", "substrate.organism.readiness_model",
         "substrate/organism/readiness_model.py", "6-dimension system readiness assessment"),
        ("bottleneck_engine", "BottleneckEngine", "substrate.organism.bottleneck_engine",
         "substrate/organism/bottleneck_engine.py", "Operational self-optimization engine"),
        ("organism_daemon", "OrganismDaemon", "substrate.organism.daemon",
         "substrate/organism/daemon.py", "Persistent organism daemon with subsystem wiring"),
        ("advisor", "Advisor", "substrate.organism.advisor",
         "substrate/organism/advisor.py", "Unified orchestration hub"),
        ("coordinator", "OrganismCoordinator", "substrate.organism.coordinator",
         "substrate/organism/coordinator.py", "DAG decomposition and execution"),
        ("governed_spine", "GovernedExecutionSpine", "substrate.organism.governed_spine",
         "substrate/organism/governed_spine.py", "Governance enforcement for mutations"),
        ("homeostasis", "HomeostasisEngine", "substrate.organism.homeostasis",
         "substrate/organism/homeostasis.py", "8-dimension self-regulation"),
        ("execution_economy", "ExecutionEconomy", "substrate.organism.execution_economy",
         "substrate/organism/execution_economy.py", "Execution cost/value tracking"),
        ("leverage_engine", "LeverageEngine", "substrate.organism.leverage_engine",
         "substrate/organism/leverage_engine.py", "Leverage metric aggregation"),
        ("next_action_engine", "NextActionEngine", "substrate.organism.next_action_engine",
         "substrate/organism/next_action_engine.py", "Next-action recommendation"),
        ("workload_runner", "WorkloadRunner", "substrate.organism.workload_runner",
         "substrate/organism/workload_runner.py", "Real operational job execution"),
        ("maintenance_loop", "MaintenanceLoop", "substrate.organism.maintenance_loop",
         "substrate/organism/maintenance_loop.py", "OBSERVE-mode autonomous maintenance"),
        ("assisted_executor", "AssistedExecutor", "substrate.organism.assisted_executor",
         "substrate/organism/assisted_executor.py", "Governed execution of approved actions"),
        ("leverage_assimilation", "LeverageAssimilator", "substrate.organism.leverage_assimilation",
         "substrate/organism/leverage_assimilation.py", "External framework ingestion"),
        ("recursion_governance", "RecursionGovernor", "substrate.organism.recursion_governance",
         "substrate/organism/recursion_governance.py", "Recursion depth governance"),
        ("advisor_hierarchy", "AdvisorHierarchy", "substrate.organism.advisor_hierarchy",
         "substrate/organism/advisor_hierarchy.py", "Multi-level advisory structure"),
    ]
    for sid, name, mod, fpath, desc in subsystems:
        entity = WorldEntity(
            id=sid, name=name,
            category=EntityCategory.SUBSYSTEM,
            description=desc,
            module_path=mod,
        )
        full_path = os.path.join(root, fpath)
        if _check_file(full_path):
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                source=fpath, detail=f"File exists at {fpath}",
            ))
            entity.status = EntityStatus.PARTIAL
        else:
            entity.status = EntityStatus.MISSING
            model.add_gap(WorldGap(
                description=f"Subsystem file missing: {fpath}",
                severity=GapSeverity.HIGH, entity_id=sid,
            ))

        test_path = os.path.join(root, f"substrate/organism/tests/test_{sid}.py")
        if _check_file(test_path):
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.TEST_EXISTS,
                source=f"substrate/organism/tests/test_{sid}.py",
                detail="Test file exists",
            ))

        model.add_entity(entity)


def _extract_adapters(model: WorldModel) -> None:
    """Extract adapter subsystems."""
    root = model.repo_root
    adapters = [
        ("model_router", "ModelRouter", "adapters/models/model_router.py",
         "Intelligence routing — call_with_fallback"),
        ("llm_adapter", "LLMAdapter", "adapters/models/llm_adapter.py",
         "LLM adapter wrapping model_router"),
        ("cc_sdk", "CC_SDK", "adapters/models/cc_sdk.py",
         "Claude Code CLI SDK — option 0 in routing chain"),
    ]
    for aid, name, fpath, desc in adapters:
        entity = WorldEntity(
            id=f"adapter_{aid}", name=name,
            category=EntityCategory.SUBSYSTEM,
            description=desc,
            module_path=fpath.replace("/", ".").replace(".py", ""),
        )
        if _check_file(os.path.join(root, fpath)):
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                source=fpath, detail=f"File exists",
            ))
            entity.status = EntityStatus.PARTIAL
        else:
            entity.status = EntityStatus.MISSING
        model.add_entity(entity)


def _extract_transports(model: WorldModel) -> None:
    """Extract transport interfaces."""
    root = model.repo_root
    transports = [
        ("discord_bot", "DiscordBot", "services/discord_bot.py", "Primary Discord bot"),
        ("operator_api", "OperatorAPI", "services/operator_api.py", "Operator REST API"),
        ("cockpit_api", "CockpitAPI", "saas/api/index.ts", "Cockpit TypeScript API"),
    ]
    for tid, name, fpath, desc in transports:
        entity = WorldEntity(
            id=f"transport_{tid}", name=name,
            category=EntityCategory.TRANSPORT,
            description=desc,
            module_path=fpath,
        )
        if _check_file(os.path.join(root, fpath)):
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                source=fpath, detail="File exists",
            ))
            entity.status = EntityStatus.PARTIAL
        else:
            entity.status = EntityStatus.MISSING
        model.add_entity(entity)


def _extract_cockpit_surfaces(model: WorldModel) -> None:
    """Extract cockpit panels from observed files."""
    root = model.repo_root
    panels_dir = os.path.join(root, "cockpit", "src", "renderer", "panels")
    if not _check_dir(panels_dir):
        panels_dir = os.path.join(root, "saas", "client", "src", "panels")
    if not _check_dir(panels_dir):
        model.add_uncertainty(WorldUncertainty(
            description="Cannot locate cockpit panels directory",
            reason="Neither cockpit/src/renderer/panels nor saas/client/src/panels found",
            confidence=0.3,
        ))
        return

    try:
        for fname in sorted(os.listdir(panels_dir)):
            if fname.endswith(".tsx") and "Panel" in fname:
                panel_id = fname.replace(".tsx", "").replace("Panel", "").lower()
                entity = WorldEntity(
                    id=f"panel_{panel_id}",
                    name=fname.replace(".tsx", ""),
                    category=EntityCategory.COCKPIT_SURFACE,
                    description=f"Cockpit panel: {fname}",
                    module_path=os.path.join(panels_dir, fname),
                )
                entity.evidence.append(WorldEvidence(
                    evidence_type=EvidenceType.FILE_EXISTS,
                    source=f"panels/{fname}",
                    detail="Panel component file exists",
                ))
                entity.status = EntityStatus.PARTIAL
                model.add_entity(entity)
    except OSError as exc:
        logger.warning("Failed to scan panels dir: %s", exc)


def _extract_data_stores(model: WorldModel) -> None:
    """Extract persistent data stores."""
    root = model.repo_root
    stores = [
        ("events_jsonl", "data/umh/organism/events.jsonl", "Organism event stream"),
        ("execution_journal_jsonl", "data/umh/organism/execution_journal.jsonl", "Execution journal"),
        ("learning_signals_jsonl", "data/umh/organism/learning_signals.jsonl", "Learning signals"),
        ("deliverables_jsonl", "data/umh/organism/deliverables.jsonl", "Agent deliverables"),
        ("messages_jsonl", "data/umh/organism/messages.jsonl", "Organism messages"),
        ("daemon_state_json", "data/umh/organism/daemon_state.json", "Daemon state snapshot"),
        ("intelligence_decisions", "data/umh/intelligence/decisions.jsonl", "Intelligence decisions"),
        ("intelligence_patterns", "data/umh/intelligence/patterns.json", "Intelligence patterns"),
    ]
    for sid, fpath, desc in stores:
        entity = WorldEntity(
            id=f"store_{sid}", name=sid,
            category=EntityCategory.DATA_STORE,
            description=desc,
            module_path=fpath,
        )
        full = os.path.join(root, fpath)
        if _file_nonempty(full):
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.DATA_FILE_NONEMPTY,
                source=fpath,
                detail=f"File exists with {size} bytes",
            ))
            entity.status = EntityStatus.OPERATIONAL
        elif _check_file(full):
            entity.status = EntityStatus.DEGRADED
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                source=fpath, detail="File exists but empty",
            ))
        else:
            entity.status = EntityStatus.MISSING
            model.add_gap(WorldGap(
                description=f"Data store missing: {fpath}",
                severity=GapSeverity.MEDIUM, entity_id=f"store_{sid}",
            ))
        model.add_entity(entity)


def _extract_governance(model: WorldModel) -> None:
    """Extract governance subsystems."""
    root = model.repo_root
    gov_files = [
        ("governance_control_plane", "substrate/control_plane/governance.py",
         "Deterministic risk classification"),
        ("governance_router", "substrate/control_plane/router.py",
         "Signal lifecycle orchestration"),
        ("governance_spine", "substrate/execution/spine.py",
         "8-stage execution pipeline"),
    ]
    for gid, fpath, desc in gov_files:
        entity = WorldEntity(
            id=gid, name=gid,
            category=EntityCategory.GOVERNANCE,
            description=desc,
            module_path=fpath.replace("/", ".").replace(".py", ""),
        )
        if _check_file(os.path.join(root, fpath)):
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                source=fpath, detail="File exists",
            ))
            entity.status = EntityStatus.PARTIAL
        else:
            entity.status = EntityStatus.MISSING
        model.add_entity(entity)


def _extract_deployment(model: WorldModel) -> None:
    """Extract deployment state from observed artifacts."""
    root = model.repo_root
    deployments = [
        ("docker_compose", "compose.yml", "Docker Compose configuration"),
        ("dockerfile", "Dockerfile", "Primary Dockerfile"),
        ("fly_toml", "fly.toml", "Fly.io deployment config"),
    ]
    for did, fpath, desc in deployments:
        entity = WorldEntity(
            id=f"deploy_{did}", name=did,
            category=EntityCategory.DEPLOYMENT,
            description=desc,
            module_path=fpath,
        )
        if _check_file(os.path.join(root, fpath)):
            entity.evidence.append(WorldEvidence(
                evidence_type=EvidenceType.FILE_EXISTS,
                source=fpath, detail="File exists",
            ))
            entity.status = EntityStatus.OPERATIONAL
        else:
            entity.status = EntityStatus.MISSING
        model.add_entity(entity)


def _extract_api_routes(model: WorldModel) -> None:
    """Extract cockpit API route files."""
    root = model.repo_root
    routes_dir = os.path.join(root, "saas", "api", "routes")
    if not _check_dir(routes_dir):
        return
    try:
        for fname in sorted(os.listdir(routes_dir)):
            if fname.endswith(".ts"):
                route_name = fname.replace(".ts", "")
                entity = WorldEntity(
                    id=f"route_{route_name}",
                    name=f"API Route: {route_name}",
                    category=EntityCategory.INTERFACE,
                    description=f"Cockpit API route group: /api/{route_name}",
                    module_path=f"saas/api/routes/{fname}",
                )
                entity.evidence.append(WorldEvidence(
                    evidence_type=EvidenceType.ROUTE_REGISTERED,
                    source=f"saas/api/routes/{fname}",
                    detail="Route file exists",
                ))
                entity.status = EntityStatus.OPERATIONAL
                model.add_entity(entity)
    except OSError as exc:
        logger.warning("Failed to scan routes dir: %s", exc)


def _detect_wiring_gaps(model: WorldModel) -> None:
    """Detect subsystems that exist but lack API/cockpit wiring."""
    subsystems_with_routes = set()
    for eid, entity in model.entities.items():
        if entity.category == EntityCategory.INTERFACE:
            route_name = eid.replace("route_", "")
            subsystems_with_routes.add(route_name)

    for eid, entity in model.entities.items():
        if entity.category == EntityCategory.SUBSYSTEM and entity.status != EntityStatus.MISSING:
            short_name = eid.replace("adapter_", "")
            if short_name not in subsystems_with_routes and "organism" not in subsystems_with_routes:
                model.add_uncertainty(WorldUncertainty(
                    description=f"Subsystem '{entity.name}' may lack dedicated API route",
                    entity_id=eid,
                    reason="No matching route file found (may be exposed via organism routes)",
                    confidence=0.4,
                ))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_world_model(repo_root: str | None = None) -> WorldModel:
    """Build a complete world model from observed reality. No LLM required."""
    model = WorldModel(repo_root=repo_root or _REPO_ROOT)
    _extract_subsystems(model)
    _extract_adapters(model)
    _extract_transports(model)
    _extract_cockpit_surfaces(model)
    _extract_data_stores(model)
    _extract_governance(model)
    _extract_deployment(model)
    _extract_api_routes(model)
    _detect_wiring_gaps(model)
    return model


def persist_world_model(model: WorldModel, path: str | None = None) -> str:
    """Persist world model snapshot to JSONL."""
    if path is None:
        path = os.path.join(model.repo_root, "data", "umh", "organism", "world_model.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(model.to_dict(), default=str) + "\n")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _REPO_ROOT)
    wm = extract_world_model()
    print(json.dumps(wm.summary(), indent=2))
    print(f"\nEntities: {len(wm.entities)}")
    for eid, entity in sorted(wm.entities.items()):
        print(f"  [{entity.status.value:11s}] {entity.category.value:18s} {entity.name}")
    print(f"\nGaps: {len(wm.gaps)}")
    for gap in wm.gaps:
        print(f"  [{gap.severity.value}] {gap.description}")
    print(f"\nUncertainties: {len(wm.uncertainties)}")
    for u in wm.uncertainties:
        print(f"  [{u.confidence:.0%}] {u.description}")
