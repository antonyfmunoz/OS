"""Orchestrator Awareness Runtime — synthesized reality model for the orchestrator.

Answers: "Does the orchestrator understand the complete state of UMH?"

Without this runtime: Right Rail = smart chatbot.
With this runtime: Right Rail = UMH Orchestrator.

Composes 23 subsystems across 6 domains into a single OrchestratorContext.
The orchestrator never needs to directly reason across dozens of runtimes
every time the operator types — it queries this runtime once.

Two distinct capability layers (do NOT conflate):
  - EmergentCapability (organism/capability_runtime.py) = what UMH learned to do
  - Capability enum (execution/runtime/capability_router.py) = job/tool capabilities

Campaign 4.0. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class AwarenessDomain(str, Enum):
    OPERATOR = "operator"
    COCKPIT = "cockpit"
    ORGANISM = "organism"
    EXECUTION = "execution"
    DEVELOPMENT = "development"
    SOURCE_TRUTH = "source_truth"


@dataclass
class OrchestratorContext:
    # Operator
    operator_state: dict[str, Any] = field(default_factory=dict)
    active_device: str = ""
    active_session: str = ""
    active_intents: list[dict[str, Any]] = field(default_factory=list)

    # Workspace
    active_projection: str = ""
    active_project: str = ""
    active_repo: str = ""
    active_directory: str = ""
    active_files: list[str] = field(default_factory=list)
    active_panel: str = ""
    active_capability_surface: str = ""

    # Execution
    active_agents: list[dict[str, Any]] = field(default_factory=list)
    active_compute_nodes: list[dict[str, Any]] = field(default_factory=list)
    active_executions: list[dict[str, Any]] = field(default_factory=list)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)

    # Organism
    projections: list[dict[str, Any]] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)
    workflows: list[dict[str, Any]] = field(default_factory=list)
    templates: dict[str, Any] = field(default_factory=dict)
    skills: list[dict[str, Any]] = field(default_factory=list)
    adapters: list[dict[str, Any]] = field(default_factory=list)
    operationalizations: dict[str, Any] = field(default_factory=dict)
    infrastructure: dict[str, Any] = field(default_factory=dict)
    documents: list[dict[str, Any]] = field(default_factory=list)
    codebases: list[dict[str, Any]] = field(default_factory=list)
    repositories: list[dict[str, Any]] = field(default_factory=list)
    devices: list[dict[str, Any]] = field(default_factory=list)

    # Health
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    coherence_summary: dict[str, Any] = field(default_factory=dict)
    continuity_state: dict[str, Any] = field(default_factory=dict)

    # Delegation
    preferred_execution_device: str = ""
    available_execution_devices: list[str] = field(default_factory=list)
    nested_orchestrators: list[dict[str, Any]] = field(default_factory=list)
    delegation_queue: dict[str, Any] = field(default_factory=dict)

    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_state": self.operator_state,
            "active_device": self.active_device,
            "active_session": self.active_session,
            "active_intents": self.active_intents,
            "active_projection": self.active_projection,
            "active_project": self.active_project,
            "active_repo": self.active_repo,
            "active_directory": self.active_directory,
            "active_files": self.active_files,
            "active_panel": self.active_panel,
            "active_capability_surface": self.active_capability_surface,
            "active_agents": self.active_agents,
            "active_compute_nodes": self.active_compute_nodes,
            "active_executions": self.active_executions,
            "active_loops": self.active_loops,
            "pending_approvals": self.pending_approvals,
            "projections": self.projections,
            "capabilities": self.capabilities,
            "workflows": self.workflows,
            "templates": self.templates,
            "skills": self.skills,
            "adapters": self.adapters,
            "operationalizations": self.operationalizations,
            "infrastructure": self.infrastructure,
            "documents": self.documents,
            "codebases": self.codebases,
            "repositories": self.repositories,
            "devices": self.devices,
            "recommendations": self.recommendations,
            "coherence_summary": self.coherence_summary,
            "continuity_state": self.continuity_state,
            "preferred_execution_device": self.preferred_execution_device,
            "available_execution_devices": self.available_execution_devices,
            "nested_orchestrators": self.nested_orchestrators,
            "delegation_queue": self.delegation_queue,
            "generated_at": self.generated_at,
        }


@dataclass
class DomainAwareness:
    domain: AwarenessDomain
    available: bool
    subsystem_count: int
    active_subsystems: int
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.value,
            "available": self.available,
            "subsystem_count": self.subsystem_count,
            "active_subsystems": self.active_subsystems,
            "summary": self.summary,
        }


@dataclass
class OrchestratorAwarenessSnapshot:
    context: OrchestratorContext
    domain_health: list[DomainAwareness] = field(default_factory=list)
    total_subsystems: int = 0
    active_subsystems: int = 0
    awareness_score: float = 0.0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "domain_health": [d.to_dict() for d in self.domain_health],
            "total_subsystems": self.total_subsystems,
            "active_subsystems": self.active_subsystems,
            "awareness_score": self.awareness_score,
            "generated_at": self.generated_at,
        }


# ── Helpers ───────────────────────────────────────────────────────────────


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("Awareness: %s.%s() failed: %s", type(obj).__name__, method, exc)
        return None


def _safe_dict(obj: Any, method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, dict):
        return result
    if result is not None and hasattr(result, "to_dict"):
        try:
            return result.to_dict()
        except Exception:
            pass
    return {}


def _safe_list(obj: Any, method: str, *args: Any, **kwargs: Any) -> list[Any]:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, list):
        return [
            item.to_dict() if hasattr(item, "to_dict") else
            (item if isinstance(item, dict) else {"value": str(item)})
            for item in result
        ]
    return []


# ── Runtime ───────────────────────────────────────────────────────────────


class OrchestratorAwarenessRuntime:
    """Synthesized reality model for the UMH orchestrator.

    Composes 23 subsystems across 6 domains. All methods are read-only.
    """

    TOTAL_SUBSYSTEMS = 23

    def __init__(
        self,
        # Operator domain (3)
        intent_runtime: Any | None = None,
        snapshot_runtime: Any | None = None,
        attention_engine: Any | None = None,
        # Cockpit domain (3)
        capability_map: Any | None = None,
        command_center: Any | None = None,
        execution_surface: Any | None = None,
        # Organism domain (7)
        capability_runtime: Any | None = None,
        capability_router: Any | None = None,
        operationalization_runtime: Any | None = None,
        infrastructure_runtime: Any | None = None,
        compounding_engine: Any | None = None,
        continuity_runtime: Any | None = None,
        template_registry: Any | None = None,
        # Execution domain (4)
        agent_fleet: Any | None = None,
        compute_fabric: Any | None = None,
        governed_work: Any | None = None,
        execution_graph: Any | None = None,
        delegation_runtime: Any | None = None,
        # Development domain (3)
        meta_ide: Any | None = None,
        build_loop: Any | None = None,
        projection_integration: Any | None = None,
        # Source truth domain (3)
        projection_port: Any | None = None,
        source_registry: Any | None = None,
        reconciliation_engine: Any | None = None,
    ) -> None:
        # Operator
        self._intent = intent_runtime
        self._snapshot = snapshot_runtime
        self._attention = attention_engine
        # Cockpit
        self._cap_map = capability_map
        self._cmd_center = command_center
        self._exec_surface = execution_surface
        # Organism
        self._cap_runtime = capability_runtime
        self._cap_router = capability_router
        self._ops_runtime = operationalization_runtime
        self._infra_runtime = infrastructure_runtime
        self._compounding = compounding_engine
        self._continuity = continuity_runtime
        self._templates = template_registry
        # Execution
        self._fleet = agent_fleet
        self._fabric = compute_fabric
        self._governed = governed_work
        self._graph = execution_graph
        self._delegation = delegation_runtime
        # Development
        self._meta_ide = meta_ide
        self._build_loop = build_loop
        self._proj_integration = projection_integration
        # Source truth
        self._proj_port = projection_port
        self._source_reg = source_registry
        self._reconciliation = reconciliation_engine

    # ── Primary interface ─────────────────────────────────────────────

    def context(self) -> OrchestratorContext:
        ctx = OrchestratorContext(generated_at=time.time())

        # Operator domain
        self._fill_operator(ctx)
        # Cockpit domain
        self._fill_cockpit(ctx)
        # Organism domain
        self._fill_organism(ctx)
        # Execution domain
        self._fill_execution(ctx)
        # Development domain
        self._fill_development(ctx)
        # Source truth domain
        self._fill_source_truth(ctx)

        return ctx

    def snapshot(self) -> OrchestratorAwarenessSnapshot:
        ctx = self.context()
        health = self.domain_health()
        active = sum(1 for d in health if d.available)
        total = self.TOTAL_SUBSYSTEMS
        active_subs = sum(d.active_subsystems for d in health)
        score = active_subs / total if total > 0 else 0.0
        return OrchestratorAwarenessSnapshot(
            context=ctx,
            domain_health=health,
            total_subsystems=total,
            active_subsystems=active_subs,
            awareness_score=round(score, 3),
            generated_at=ctx.generated_at,
        )

    # ── Domain-level queries ──────────────────────────────────────────

    def operator_awareness(self) -> dict[str, Any]:
        situation = _safe_dict(self._snapshot, "situation")
        attention = _safe_list(self._attention, "top", 5)
        intents = _safe_list(self._intent, "active_by_scope")
        return {
            "situation": situation,
            "attention_items": attention,
            "active_intents": intents,
            "subsystems_available": sum(1 for s in [
                self._intent, self._snapshot, self._attention,
            ] if s is not None),
        }

    def cockpit_awareness(self) -> dict[str, Any]:
        cap_snap = _safe_dict(self._cap_map, "snapshot")
        mvp_gaps = _safe_list(self._cap_map, "mvp_gaps")
        cmd_snap = _safe_dict(self._cmd_center, "snapshot")
        recommendations = _safe_list(self._cmd_center, "recommendations")
        exec_snap = _safe_dict(self._exec_surface, "snapshot")
        return {
            "capability_map": cap_snap,
            "mvp_gaps": mvp_gaps,
            "command_center": cmd_snap,
            "recommendations": recommendations,
            "execution_surface": exec_snap,
            "subsystems_available": sum(1 for s in [
                self._cap_map, self._cmd_center, self._exec_surface,
            ] if s is not None),
        }

    def organism_awareness(self) -> dict[str, Any]:
        emergent = _safe_dict(self._cap_runtime, "summary")
        ops = _safe_dict(self._ops_runtime, "summary")
        infra = _safe_dict(self._infra_runtime, "summary")
        infra_health = _safe_dict(self._infra_runtime, "health_check")
        compounding = _safe_dict(self._compounding, "summary")
        continuity = _safe_dict(self._continuity, "status")
        templates = _safe_dict(self._templates, "summary")
        return {
            "emergent_capabilities": emergent,
            "operationalizations": ops,
            "infrastructure": infra,
            "infrastructure_health": infra_health,
            "compounding": compounding,
            "continuity": continuity,
            "templates": templates,
            "subsystems_available": sum(1 for s in [
                self._cap_runtime, self._cap_router,
                self._ops_runtime, self._infra_runtime,
                self._compounding, self._continuity, self._templates,
            ] if s is not None),
        }

    def execution_awareness(self) -> dict[str, Any]:
        fleet = _safe_dict(self._fleet, "fleet_status")
        dispatches = _safe_list(self._fleet, "active_dispatches")
        nodes = _safe_list(self._fabric, "nodes")
        fabric_health = _safe_dict(self._fabric, "health")
        active_exec = _safe_list(self._fabric, "active_executions")
        governed_active = _safe_list(self._governed, "active")
        governed_blocked = _safe_list(self._governed, "blocked")
        graph_completeness = _safe_dict(self._graph, "audit_completeness")
        return {
            "fleet_status": fleet,
            "active_dispatches": dispatches,
            "compute_nodes": nodes,
            "fabric_health": fabric_health,
            "active_executions": active_exec,
            "governed_active": governed_active,
            "governed_blocked": governed_blocked,
            "lineage_completeness": graph_completeness,
            "subsystems_available": sum(1 for s in [
                self._fleet, self._fabric, self._governed, self._graph,
            ] if s is not None),
        }

    def development_awareness(self) -> dict[str, Any]:
        workspace = _safe_dict(self._meta_ide, "workspace_snapshot")
        ide_status = _safe_dict(self._meta_ide, "ide_status")
        active_dev = _safe_list(self._meta_ide, "active_development")
        build_status = _safe_dict(self._build_loop, "status")
        build_requests = _safe_list(self._build_loop, "active_requests")
        proj_snap = _safe_dict(self._proj_integration, "snapshot")
        return {
            "workspace": workspace,
            "ide_status": ide_status,
            "active_development": active_dev,
            "build_loop_status": build_status,
            "active_build_requests": build_requests,
            "projection_integration": proj_snap,
            "subsystems_available": sum(1 for s in [
                self._meta_ide, self._build_loop, self._proj_integration,
            ] if s is not None),
        }

    def source_truth_awareness(self) -> dict[str, Any]:
        registrations = _safe_list(self._proj_port, "list_registrations")
        sources = _safe_dict(self._source_reg, "summary")
        divergences = _safe_list(self._reconciliation, "list_divergences")
        return {
            "projection_registrations": registrations,
            "source_registry": sources,
            "divergences": divergences,
            "subsystems_available": sum(1 for s in [
                self._proj_port, self._source_reg, self._reconciliation,
            ] if s is not None),
        }

    # ── Domain health ─────────────────────────────────────────────────

    def domain_health(self) -> list[DomainAwareness]:
        domains = [
            (AwarenessDomain.OPERATOR, 3, [self._intent, self._snapshot, self._attention]),
            (AwarenessDomain.COCKPIT, 3, [self._cap_map, self._cmd_center, self._exec_surface]),
            (AwarenessDomain.ORGANISM, 7, [
                self._cap_runtime, self._cap_router, self._ops_runtime,
                self._infra_runtime, self._compounding, self._continuity, self._templates,
            ]),
            (AwarenessDomain.EXECUTION, 4, [self._fleet, self._fabric, self._governed, self._graph]),
            (AwarenessDomain.DEVELOPMENT, 3, [self._meta_ide, self._build_loop, self._proj_integration]),
            (AwarenessDomain.SOURCE_TRUTH, 3, [self._proj_port, self._source_reg, self._reconciliation]),
        ]
        result: list[DomainAwareness] = []
        for domain, count, subsystems in domains:
            active = sum(1 for s in subsystems if s is not None)
            result.append(DomainAwareness(
                domain=domain,
                available=active > 0,
                subsystem_count=count,
                active_subsystems=active,
                summary={"ratio": f"{active}/{count}"},
            ))
        return result

    def awareness_score(self) -> float:
        health = self.domain_health()
        active = sum(d.active_subsystems for d in health)
        return round(active / self.TOTAL_SUBSYSTEMS, 3) if self.TOTAL_SUBSYSTEMS > 0 else 0.0

    # ── Fill helpers (private) ────────────────────────────────────────

    def _fill_operator(self, ctx: OrchestratorContext) -> None:
        situation = _safe_dict(self._snapshot, "situation")
        attention = _safe_list(self._attention, "top", 5)
        changes = _safe_dict(self._snapshot, "changes")
        decisions = _safe_dict(self._snapshot, "decisions")

        ctx.operator_state = {
            "situation": situation,
            "attention": attention,
            "changes": changes,
            "decisions": decisions,
        }
        ctx.active_intents = _safe_list(self._intent, "active_by_scope")

        snapshot = _safe_dict(self._snapshot, "snapshot")
        ctx.active_device = snapshot.get("device", "")
        ctx.active_session = snapshot.get("session_id", "")

    def _fill_cockpit(self, ctx: OrchestratorContext) -> None:
        cap_snap = _safe_dict(self._cap_map, "snapshot")
        ctx.active_panel = cap_snap.get("active_panel", "")
        ctx.active_capability_surface = cap_snap.get("capability_surface", "")

        cmd_snap = _safe_dict(self._cmd_center, "snapshot")
        ctx.recommendations = cmd_snap.get("recommendations", [])
        if not isinstance(ctx.recommendations, list):
            ctx.recommendations = []

        exec_snap = _safe_dict(self._exec_surface, "snapshot")
        ctx.pending_approvals = exec_snap.get("pending_approvals", [])
        if not isinstance(ctx.pending_approvals, list):
            ctx.pending_approvals = []

    def _fill_organism(self, ctx: OrchestratorContext) -> None:
        # Emergent capabilities (what UMH learned to do)
        emergent = _safe_dict(self._cap_runtime, "summary")
        # Execution capabilities (job/tool capabilities)
        exec_caps: dict[str, Any] = {}
        if self._cap_router is not None:
            try:
                caps = getattr(self._cap_router, "capabilities", None)
                if callable(caps):
                    exec_caps = {"execution_capabilities": caps()}
                elif caps is not None:
                    exec_caps = {"execution_capabilities": caps}
            except Exception as exc:
                logger.debug("Awareness: capability_router query failed: %s", exc)

        ctx.capabilities = {
            "emergent": emergent,
            "execution": exec_caps,
        }

        ctx.operationalizations = _safe_dict(self._ops_runtime, "summary")
        ctx.infrastructure = _safe_dict(self._infra_runtime, "summary")
        ctx.templates = _safe_dict(self._templates, "summary")
        ctx.continuity_state = _safe_dict(self._continuity, "status")

        compounding = _safe_dict(self._compounding, "summary")
        ctx.workflows = compounding.get("promoted", [])
        if not isinstance(ctx.workflows, list):
            ctx.workflows = []

        infra_entities = _safe_list(self._infra_runtime, "list_entities")
        ctx.devices = [e for e in infra_entities if e.get("infra_type") == "device"]

    def _fill_execution(self, ctx: OrchestratorContext) -> None:
        fleet = _safe_dict(self._fleet, "fleet_status")
        ctx.active_agents = _safe_list(self._fleet, "active_dispatches")

        nodes = _safe_list(self._fabric, "nodes")
        ctx.active_compute_nodes = nodes

        active_exec = _safe_list(self._fabric, "active_executions")
        governed = _safe_list(self._governed, "active")
        ctx.active_executions = active_exec + governed

        ctx.delegation_queue = _safe_dict(self._delegation, "queue_status")
        ctx.nested_orchestrators = _safe_list(self._delegation, "active_missions")

    def _fill_development(self, ctx: OrchestratorContext) -> None:
        workspace = _safe_dict(self._meta_ide, "workspace_snapshot")
        ctx.repositories = workspace.get("repos", [])
        if not isinstance(ctx.repositories, list):
            ctx.repositories = []

        ide_status = _safe_dict(self._meta_ide, "ide_status")
        ctx.active_repo = ide_status.get("active_repo", "")
        ctx.active_directory = ide_status.get("active_directory", "")
        ctx.active_files = ide_status.get("active_files", [])
        if not isinstance(ctx.active_files, list):
            ctx.active_files = []

        proj_snap = _safe_dict(self._proj_integration, "snapshot")
        ctx.active_projection = proj_snap.get("active_projection", "")
        ctx.active_project = proj_snap.get("active_project", "")
        ctx.codebases = proj_snap.get("codebases", [])
        if not isinstance(ctx.codebases, list):
            ctx.codebases = []

        build_status = _safe_dict(self._build_loop, "status")
        ctx.active_loops = build_status.get("active_loops", [])
        if not isinstance(ctx.active_loops, list):
            ctx.active_loops = []

    def _fill_source_truth(self, ctx: OrchestratorContext) -> None:
        registrations = _safe_list(self._proj_port, "list_registrations")
        ctx.projections = registrations

        sources = _safe_dict(self._source_reg, "summary")
        ctx.documents = sources.get("documents", [])
        if not isinstance(ctx.documents, list):
            ctx.documents = []

        ctx.skills = sources.get("skills", [])
        if not isinstance(ctx.skills, list):
            ctx.skills = []

        ctx.adapters = sources.get("adapters", [])
        if not isinstance(ctx.adapters, list):
            ctx.adapters = []
