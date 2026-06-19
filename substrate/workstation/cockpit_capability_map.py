"""Cockpit Capability Map — audit surface for cockpit routes, panels, stores.

Answers: "What does the cockpit contain, what's duplicated, what's missing,
what's MVP-required?"

Data-driven static registries seeded from known cockpit state. No dynamic
introspection. Two lookup tables cross-referenced to compute coverage.

Campaign 3, Workstream 1. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SurfaceCategory(str, Enum):
    ROUTE = "route"
    PANEL = "panel"
    STORE = "store"
    SUBSYSTEM = "subsystem"


class MVPStatus(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    DEV_ONLY = "dev_only"
    DEPRECATED = "deprecated"


class CoverageStatus(str, Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    MISSING_FRONTEND = "missing_frontend"
    MISSING_BACKEND = "missing_backend"
    ORPHAN = "orphan"


@dataclass
class CockpitSurface:
    surface_id: str
    category: SurfaceCategory
    name: str
    subsystem: str
    panel_link: str
    route_path: str
    mvp_status: MVPStatus
    coverage: CoverageStatus
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "category": self.category.value,
            "name": self.name,
            "subsystem": self.subsystem,
            "panel_link": self.panel_link,
            "route_path": self.route_path,
            "mvp_status": self.mvp_status.value,
            "coverage": self.coverage.value,
            "notes": self.notes,
        }


@dataclass
class DuplicationFinding:
    surface_a: str
    surface_b: str
    overlap_type: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_a": self.surface_a,
            "surface_b": self.surface_b,
            "overlap_type": self.overlap_type,
            "recommendation": self.recommendation,
        }


@dataclass
class CockpitCapabilitySnapshot:
    total_routes: int
    total_panels: int
    total_stores: int
    surfaces: list[CockpitSurface]
    duplications: list[DuplicationFinding]
    mvp_coverage: dict[str, int]
    coverage_distribution: dict[str, int]
    mvp_gaps: list[CockpitSurface]
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_routes": self.total_routes,
            "total_panels": self.total_panels,
            "total_stores": self.total_stores,
            "surfaces": [s.to_dict() for s in self.surfaces],
            "duplications": [d.to_dict() for d in self.duplications],
            "mvp_coverage": self.mvp_coverage,
            "coverage_distribution": self.coverage_distribution,
            "mvp_gaps": [s.to_dict() for s in self.mvp_gaps],
            "generated_at": self.generated_at,
        }


# ── Static Registries ──────────────────────────────────────────────────────
# Seeded from confirmed cockpit state. Updated when new routes/panels ship.

_ROUTE_REGISTRY: dict[str, dict[str, str]] = {
    "cockpit_agent_routes": {"subsystem": "agent_fleet", "panel_link": "agents", "mvp_status": "required"},
    "cockpit_approval_routes": {"subsystem": "approval_gate", "panel_link": "approvals", "mvp_status": "required"},
    "cockpit_activity_routes": {"subsystem": "execution_graph", "panel_link": "activity", "mvp_status": "required"},
    "cockpit_organism_routes": {"subsystem": "organism", "panel_link": "organism", "mvp_status": "dev_only"},
    "cockpit_organism_map_routes": {"subsystem": "organism", "panel_link": "organismmap", "mvp_status": "required"},
    "cockpit_execution_routes": {"subsystem": "execution_spine", "panel_link": "execution", "mvp_status": "required"},
    "cockpit_meta_ide_routes": {"subsystem": "meta_ide", "panel_link": "metaide", "mvp_status": "required"},
    "cockpit_work_routes": {"subsystem": "governed_work", "panel_link": "work", "mvp_status": "required"},
    "cockpit_knowledge_routes": {"subsystem": "knowledge", "panel_link": "knowledge", "mvp_status": "required"},
    "cockpit_settings_routes": {"subsystem": "settings", "panel_link": "settings", "mvp_status": "required"},
    "cockpit_command_center_routes": {"subsystem": "operator_snapshot", "panel_link": "commandcenter", "mvp_status": "required"},
    "cockpit_vision_routes": {"subsystem": "vision", "panel_link": "vision", "mvp_status": "optional"},
    "cockpit_rooms_routes": {"subsystem": "rooms", "panel_link": "rooms", "mvp_status": "optional"},
    "cockpit_broadcast_routes": {"subsystem": "broadcast", "panel_link": "broadcast", "mvp_status": "optional"},
    "cockpit_projection_routes": {"subsystem": "projection_port", "panel_link": "projections", "mvp_status": "required"},
    "cockpit_intelligence_routes": {"subsystem": "intelligence", "panel_link": "intelligence", "mvp_status": "dev_only"},
    "cockpit_operator_routes": {"subsystem": "operator", "panel_link": "operator", "mvp_status": "dev_only"},
    "cockpit_presence_routes": {"subsystem": "presence", "panel_link": "presence", "mvp_status": "dev_only"},
    "cockpit_continuity_routes": {"subsystem": "continuity", "panel_link": "continuity", "mvp_status": "dev_only"},
    "cockpit_session_routes": {"subsystem": "sessions", "panel_link": "sessions", "mvp_status": "dev_only"},
    "cockpit_tick_loop_routes": {"subsystem": "tick_loop", "panel_link": "tickloop", "mvp_status": "dev_only"},
    "cockpit_strategy_routes": {"subsystem": "strategy", "panel_link": "strategy", "mvp_status": "dev_only"},
    "cockpit_intent_routes": {"subsystem": "intent", "panel_link": "intent", "mvp_status": "dev_only"},
    "cockpit_commands_routes": {"subsystem": "commands", "panel_link": "commands", "mvp_status": "dev_only"},
    "cockpit_workstation_routes": {"subsystem": "workstation", "panel_link": "workstation", "mvp_status": "dev_only"},
    "cockpit_exec_coord_routes": {"subsystem": "exec_coordinator", "panel_link": "execcoord", "mvp_status": "dev_only"},
    "cockpit_executor_routes": {"subsystem": "executor", "panel_link": "executor", "mvp_status": "dev_only"},
    "cockpit_organism_loop_routes": {"subsystem": "organism_loop", "panel_link": "organismloop", "mvp_status": "dev_only"},
    "cockpit_reality_timeline_routes": {"subsystem": "reality_timeline", "panel_link": "realitytimeline", "mvp_status": "dev_only"},
    "cockpit_reality_intelligence_routes": {"subsystem": "reality_intelligence", "panel_link": "realityintelligence", "mvp_status": "dev_only"},
    "cockpit_engineering_routes": {"subsystem": "engineering", "panel_link": "engineering", "mvp_status": "dev_only"},
    "cockpit_config_routes": {"subsystem": "config", "panel_link": "", "mvp_status": "optional"},
    "cockpit_propagation_routes": {"subsystem": "propagation", "panel_link": "propagation", "mvp_status": "dev_only"},
    "cockpit_voice_routes": {"subsystem": "voice", "panel_link": "", "mvp_status": "optional"},
    "cockpit_tmux_routes": {"subsystem": "tmux", "panel_link": "tmux", "mvp_status": "dev_only"},
    "cockpit_self_build_routes": {"subsystem": "self_build", "panel_link": "selfbuild", "mvp_status": "dev_only"},
    "cockpit_universal_work_routes": {"subsystem": "universal_work", "panel_link": "universalwork", "mvp_status": "dev_only"},
    "cockpit_world_model_routes": {"subsystem": "world_model", "panel_link": "worldmodel", "mvp_status": "dev_only"},
    "cockpit_operator_timeline_routes": {"subsystem": "operator_timeline", "panel_link": "operatortimeline", "mvp_status": "dev_only"},
    "cockpit_workspace_routes": {"subsystem": "workspace", "panel_link": "workspace", "mvp_status": "dev_only"},
    "cockpit_workspace_observation_routes": {"subsystem": "workspace_observation", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_workspace_topology_routes": {"subsystem": "workspace_topology", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_workstation_control_routes": {"subsystem": "workstation_control", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_screen_awareness_routes": {"subsystem": "screen_awareness", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_node_topology_routes": {"subsystem": "node_topology", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_state_authority_routes": {"subsystem": "state_authority", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_service_dependency_routes": {"subsystem": "service_dependency", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_home_routes": {"subsystem": "operator_home", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_work_center_routes": {"subsystem": "work_center", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_operationalization_routes": {"subsystem": "operationalization", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_execution_graph_routes": {"subsystem": "execution_graph", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_infrastructure_routes": {"subsystem": "infrastructure", "panel_link": "", "mvp_status": "dev_only"},
    "cockpit_compounding_routes": {"subsystem": "compounding", "panel_link": "", "mvp_status": "dev_only"},
}

_PANEL_REGISTRY: dict[str, dict[str, str]] = {
    "commandcenter": {"subsystem": "operator_snapshot", "route_module": "cockpit_command_center_routes", "mvp_status": "required"},
    "work": {"subsystem": "governed_work", "route_module": "cockpit_work_routes", "mvp_status": "required"},
    "agents": {"subsystem": "agent_fleet", "route_module": "cockpit_agent_routes", "mvp_status": "required"},
    "approvals": {"subsystem": "approval_gate", "route_module": "cockpit_approval_routes", "mvp_status": "required"},
    "activity": {"subsystem": "execution_graph", "route_module": "cockpit_activity_routes", "mvp_status": "required"},
    "metaide": {"subsystem": "meta_ide", "route_module": "cockpit_meta_ide_routes", "mvp_status": "required"},
    "execution": {"subsystem": "execution_spine", "route_module": "cockpit_execution_routes", "mvp_status": "required"},
    "organismmap": {"subsystem": "organism", "route_module": "cockpit_organism_map_routes", "mvp_status": "required"},
    "knowledge": {"subsystem": "knowledge", "route_module": "cockpit_knowledge_routes", "mvp_status": "required"},
    "settings": {"subsystem": "settings", "route_module": "cockpit_settings_routes", "mvp_status": "required"},
    "projections": {"subsystem": "projection_port", "route_module": "cockpit_projection_routes", "mvp_status": "required"},
    "vision": {"subsystem": "vision", "route_module": "cockpit_vision_routes", "mvp_status": "optional"},
    "rooms": {"subsystem": "rooms", "route_module": "cockpit_rooms_routes", "mvp_status": "optional"},
    "broadcast": {"subsystem": "broadcast", "route_module": "cockpit_broadcast_routes", "mvp_status": "optional"},
    "dashboard": {"subsystem": "operator_snapshot", "route_module": "", "mvp_status": "deprecated"},
    "portfolio": {"subsystem": "", "route_module": "", "mvp_status": "dev_only"},
    "company": {"subsystem": "", "route_module": "", "mvp_status": "dev_only"},
    "tasks": {"subsystem": "governed_work", "route_module": "", "mvp_status": "deprecated"},
    "comms": {"subsystem": "", "route_module": "", "mvp_status": "dev_only"},
    "workflows": {"subsystem": "governed_work", "route_module": "", "mvp_status": "deprecated"},
    "tracking": {"subsystem": "", "route_module": "", "mvp_status": "dev_only"},
    "skills": {"subsystem": "knowledge", "route_module": "", "mvp_status": "deprecated"},
    "experiments": {"subsystem": "", "route_module": "", "mvp_status": "dev_only"},
    "infrastructure": {"subsystem": "organism", "route_module": "", "mvp_status": "deprecated"},
    "profile": {"subsystem": "profile", "route_module": "", "mvp_status": "dev_only"},
    "organism": {"subsystem": "organism", "route_module": "cockpit_organism_routes", "mvp_status": "dev_only"},
    "intelligence": {"subsystem": "intelligence", "route_module": "cockpit_intelligence_routes", "mvp_status": "dev_only"},
    "worldmodel": {"subsystem": "world_model", "route_module": "cockpit_world_model_routes", "mvp_status": "dev_only"},
    "selfbuild": {"subsystem": "self_build", "route_module": "cockpit_self_build_routes", "mvp_status": "dev_only"},
    "universalwork": {"subsystem": "universal_work", "route_module": "cockpit_universal_work_routes", "mvp_status": "dev_only"},
    "propagation": {"subsystem": "propagation", "route_module": "cockpit_propagation_routes", "mvp_status": "dev_only"},
    "operator": {"subsystem": "operator", "route_module": "cockpit_operator_routes", "mvp_status": "dev_only"},
    "runtime": {"subsystem": "execution_spine", "route_module": "", "mvp_status": "deprecated"},
    "tmux": {"subsystem": "tmux", "route_module": "cockpit_tmux_routes", "mvp_status": "dev_only"},
    "workspace": {"subsystem": "workspace", "route_module": "cockpit_workspace_routes", "mvp_status": "deprecated"},
    "strategy": {"subsystem": "strategy", "route_module": "cockpit_strategy_routes", "mvp_status": "dev_only"},
    "tickloop": {"subsystem": "tick_loop", "route_module": "cockpit_tick_loop_routes", "mvp_status": "dev_only"},
    "continuity": {"subsystem": "continuity", "route_module": "cockpit_continuity_routes", "mvp_status": "dev_only"},
    "presence": {"subsystem": "presence", "route_module": "cockpit_presence_routes", "mvp_status": "dev_only"},
    "commands": {"subsystem": "commands", "route_module": "cockpit_commands_routes", "mvp_status": "dev_only"},
    "workstation": {"subsystem": "workstation", "route_module": "cockpit_workstation_routes", "mvp_status": "dev_only"},
    "sessions": {"subsystem": "sessions", "route_module": "cockpit_session_routes", "mvp_status": "dev_only"},
    "execcoord": {"subsystem": "exec_coordinator", "route_module": "cockpit_exec_coord_routes", "mvp_status": "dev_only"},
    "executor": {"subsystem": "executor", "route_module": "cockpit_executor_routes", "mvp_status": "dev_only"},
    "organismloop": {"subsystem": "organism_loop", "route_module": "cockpit_organism_loop_routes", "mvp_status": "dev_only"},
    "operatortimeline": {"subsystem": "operator_timeline", "route_module": "cockpit_operator_timeline_routes", "mvp_status": "dev_only"},
    "realitytimeline": {"subsystem": "reality_timeline", "route_module": "cockpit_reality_timeline_routes", "mvp_status": "dev_only"},
    "realityintelligence": {"subsystem": "reality_intelligence", "route_module": "cockpit_reality_intelligence_routes", "mvp_status": "dev_only"},
    "metaide": {"subsystem": "meta_ide", "route_module": "cockpit_meta_ide_routes", "mvp_status": "required"},
    "engineering": {"subsystem": "engineering", "route_module": "cockpit_engineering_routes", "mvp_status": "dev_only"},
    "intent": {"subsystem": "intent", "route_module": "cockpit_intent_routes", "mvp_status": "dev_only"},
    "analytics": {"subsystem": "analytics", "route_module": "", "mvp_status": "optional"},
    "editor": {"subsystem": "meta_ide", "route_module": "", "mvp_status": "dev_only"},
}

# Panels that are redirected (deprecated aliases for canonical panels)
_REDIRECT_PANELS = {
    "dashboard", "tasks", "workflows", "skills", "runtime",
    "workspace", "infrastructure", "universalwork",
}

_STORE_REGISTRY: set[str] = {
    "cockpitStore", "configStore", "viewContextStore", "bootstrapStore",
    "chatStore", "executionStore", "operatorExperienceStore", "agentStore",
    "taskStore", "approvalStore", "operatorHomeStore", "realtimeStore",
    "screenAwarenessStore", "umhNodeStore", "serviceGraphStore",
    "workspaceTopologyStore", "intelligenceStore", "voiceStore",
    "voiceSessionStore", "deviceSessionStore", "visionStore",
    "roomsStore", "broadcastStore", "activityStore", "coherenceStore",
    "worldModelStore", "analyticsStore", "editorStore", "settingsStore",
    "metaIDEStore", "organismStore", "profileStore",
}

# MVP required surfaces — the 13 questions the cockpit must answer
_MVP_REQUIRED_PANELS: set[str] = {
    "commandcenter", "work", "agents", "approvals", "activity",
    "metaide", "execution", "organismmap", "knowledge", "settings",
    "projections",
}


def _classify_coverage(panel_id: str, panel_meta: dict[str, str]) -> CoverageStatus:
    has_route = bool(panel_meta.get("route_module"))
    has_subsystem = bool(panel_meta.get("subsystem"))

    if panel_id in _REDIRECT_PANELS:
        return CoverageStatus.ORPHAN

    if has_route and has_subsystem:
        return CoverageStatus.COVERED
    if has_route and not has_subsystem:
        return CoverageStatus.PARTIAL
    if not has_route and has_subsystem:
        return CoverageStatus.MISSING_BACKEND
    return CoverageStatus.ORPHAN


class CockpitCapabilityMap:
    """Deterministic cockpit surface auditor.

    Composes no external subsystems — purely data-driven from static registries.
    """

    def __init__(self) -> None:
        self._surfaces: list[CockpitSurface] | None = None
        self._duplications: list[DuplicationFinding] | None = None

    def _build_surfaces(self) -> list[CockpitSurface]:
        surfaces: list[CockpitSurface] = []

        for panel_id, meta in _PANEL_REGISTRY.items():
            mvp = MVPStatus(meta.get("mvp_status", "dev_only"))
            coverage = _classify_coverage(panel_id, meta)
            surfaces.append(CockpitSurface(
                surface_id=f"panel:{panel_id}",
                category=SurfaceCategory.PANEL,
                name=panel_id,
                subsystem=meta.get("subsystem", ""),
                panel_link=panel_id,
                route_path="",
                mvp_status=mvp,
                coverage=coverage,
            ))

        panel_routes = {m.get("route_module", "") for m in _PANEL_REGISTRY.values() if m.get("route_module")}
        for route_name, meta in _ROUTE_REGISTRY.items():
            if route_name not in panel_routes:
                mvp = MVPStatus(meta.get("mvp_status", "dev_only"))
                surfaces.append(CockpitSurface(
                    surface_id=f"route:{route_name}",
                    category=SurfaceCategory.ROUTE,
                    name=route_name,
                    subsystem=meta.get("subsystem", ""),
                    panel_link=meta.get("panel_link", ""),
                    route_path="",
                    mvp_status=mvp,
                    coverage=CoverageStatus.MISSING_FRONTEND if not meta.get("panel_link") else CoverageStatus.PARTIAL,
                ))

        return surfaces

    def _build_duplications(self) -> list[DuplicationFinding]:
        findings: list[DuplicationFinding] = []
        subsystem_panels: dict[str, list[str]] = {}
        for panel_id, meta in _PANEL_REGISTRY.items():
            sub = meta.get("subsystem", "")
            if sub and panel_id not in _REDIRECT_PANELS:
                subsystem_panels.setdefault(sub, []).append(panel_id)

        for sub, panels in subsystem_panels.items():
            if len(panels) > 1:
                for i in range(len(panels)):
                    for j in range(i + 1, len(panels)):
                        findings.append(DuplicationFinding(
                            surface_a=f"panel:{panels[i]}",
                            surface_b=f"panel:{panels[j]}",
                            overlap_type="same_data_source",
                            recommendation=f"Consider merging {panels[i]} and {panels[j]} (both use {sub})",
                        ))

        return findings

    def _ensure_built(self) -> None:
        if self._surfaces is None:
            self._surfaces = self._build_surfaces()
        if self._duplications is None:
            self._duplications = self._build_duplications()

    def snapshot(self) -> CockpitCapabilitySnapshot:
        self._ensure_built()
        assert self._surfaces is not None
        assert self._duplications is not None

        mvp_coverage: dict[str, int] = {}
        coverage_dist: dict[str, int] = {}
        gaps: list[CockpitSurface] = []

        for s in self._surfaces:
            mvp_coverage[s.mvp_status.value] = mvp_coverage.get(s.mvp_status.value, 0) + 1
            coverage_dist[s.coverage.value] = coverage_dist.get(s.coverage.value, 0) + 1

            if s.mvp_status == MVPStatus.REQUIRED and s.coverage != CoverageStatus.COVERED:
                gaps.append(s)

        return CockpitCapabilitySnapshot(
            total_routes=len(_ROUTE_REGISTRY),
            total_panels=len(_PANEL_REGISTRY),
            total_stores=len(_STORE_REGISTRY),
            surfaces=self._surfaces,
            duplications=self._duplications,
            mvp_coverage=mvp_coverage,
            coverage_distribution=coverage_dist,
            mvp_gaps=gaps,
        )

    def surfaces(
        self,
        category: str | None = None,
        mvp_status: str | None = None,
    ) -> list[CockpitSurface]:
        self._ensure_built()
        assert self._surfaces is not None

        result = self._surfaces
        if category:
            result = [s for s in result if s.category.value == category]
        if mvp_status:
            result = [s for s in result if s.mvp_status.value == mvp_status]
        return result

    def duplications(self) -> list[DuplicationFinding]:
        self._ensure_built()
        assert self._duplications is not None
        return self._duplications

    def mvp_gaps(self) -> list[CockpitSurface]:
        self._ensure_built()
        assert self._surfaces is not None
        return [
            s for s in self._surfaces
            if s.mvp_status == MVPStatus.REQUIRED and s.coverage != CoverageStatus.COVERED
        ]

    def coverage_for(self, subsystem: str) -> dict[str, Any]:
        self._ensure_built()
        assert self._surfaces is not None

        matching = [s for s in self._surfaces if s.subsystem == subsystem]
        dist: dict[str, int] = {}
        for s in matching:
            dist[s.coverage.value] = dist.get(s.coverage.value, 0) + 1

        return {
            "subsystem": subsystem,
            "total_surfaces": len(matching),
            "coverage_distribution": dist,
            "surfaces": [s.to_dict() for s in matching],
        }

    def summary(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "total_routes": snap.total_routes,
            "total_panels": snap.total_panels,
            "total_stores": snap.total_stores,
            "total_surfaces": len(snap.surfaces),
            "mvp_gap_count": len(snap.mvp_gaps),
            "duplication_count": len(snap.duplications),
            "mvp_coverage": snap.mvp_coverage,
            "coverage_distribution": snap.coverage_distribution,
        }
