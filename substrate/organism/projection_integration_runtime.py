"""Projection Integration Runtime — audit/mapping layer over projections.

Answers: "What projections exist, how are they connected to UMH, what gaps
remain before we can build them from inside the cockpit?"

Read-only integration layer. Does NOT implement projection features.
Supports multi-machine code locations (VPS + Windows), unavailable locations,
alias normalization, build readiness scoring.

Campaign 3.5. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProjectionMachineType(str, Enum):
    VPS = "vps"
    WINDOWS = "windows"
    LOCAL = "local"
    UNKNOWN = "unknown"


class ProjectionAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ProjectionMaturityLevel(str, Enum):
    MATURE_PARTIAL = "mature_partial"
    EARLY_PARTIAL = "early_partial"
    STUB = "stub"
    UNKNOWN = "unknown"


class IntegrationGapType(str, Enum):
    MISSING_REGISTRATION = "missing_registration"
    MISSING_CODE_LOCATION = "missing_code_location"
    MISSING_SUBSTRATE_CONNECTION = "missing_substrate_connection"
    DUPLICATED_MEMORY = "duplicated_memory"
    DUPLICATED_EXECUTION = "duplicated_execution"
    DUPLICATED_GOVERNANCE = "duplicated_governance"
    DUPLICATED_AGENT_RUNTIME = "duplicated_agent_runtime"
    BROKEN_ROUTE = "broken_route"
    MISSING_COCKPIT_SURFACE = "missing_cockpit_surface"
    INACCESSIBLE_CODEBASE = "inaccessible_codebase"


@dataclass
class ProjectionCodeLocation:
    location_id: str = ""
    projection_id: str = ""
    machine: ProjectionMachineType = ProjectionMachineType.UNKNOWN
    root_path: str = ""
    repo_url: str = ""
    branch: str = ""
    availability_status: ProjectionAvailability = ProjectionAvailability.UNKNOWN
    last_seen: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.location_id:
            self.location_id = f"loc-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "projection_id": self.projection_id,
            "machine": self.machine.value,
            "root_path": self.root_path,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "availability_status": self.availability_status.value,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }


@dataclass
class ProjectionIntegrationGap:
    gap_id: str = ""
    projection_id: str = ""
    gap_type: IntegrationGapType = IntegrationGapType.MISSING_REGISTRATION
    severity: str = "medium"
    description: str = ""
    recommended_integration_action: str = ""
    does_not_require_feature_completion: bool = True

    def __post_init__(self) -> None:
        if not self.gap_id:
            self.gap_id = f"gap-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "projection_id": self.projection_id,
            "gap_type": self.gap_type.value,
            "severity": self.severity,
            "description": self.description,
            "recommended_integration_action": self.recommended_integration_action,
            "does_not_require_feature_completion": self.does_not_require_feature_completion,
        }


@dataclass
class ProjectionIntegrationProfile:
    projection_id: str = ""
    name: str = ""
    maturity_level: ProjectionMaturityLevel = ProjectionMaturityLevel.UNKNOWN
    description: str = ""
    code_locations: list[ProjectionCodeLocation] = field(default_factory=list)
    substrate_capabilities_consumed: list[str] = field(default_factory=list)
    operationalizations_consumed: list[str] = field(default_factory=list)
    infrastructure_dependencies: list[str] = field(default_factory=list)
    cockpit_surfaces: list[str] = field(default_factory=list)
    duplicated_substrate_concerns: list[str] = field(default_factory=list)
    integration_gaps: list[ProjectionIntegrationGap] = field(default_factory=list)
    last_audited: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "name": self.name,
            "maturity_level": self.maturity_level.value,
            "description": self.description,
            "code_locations": [loc.to_dict() for loc in self.code_locations],
            "substrate_capabilities_consumed": self.substrate_capabilities_consumed,
            "operationalizations_consumed": self.operationalizations_consumed,
            "infrastructure_dependencies": self.infrastructure_dependencies,
            "cockpit_surfaces": self.cockpit_surfaces,
            "duplicated_substrate_concerns": self.duplicated_substrate_concerns,
            "integration_gaps": [g.to_dict() for g in self.integration_gaps],
            "last_audited": self.last_audited,
        }


@dataclass
class ProjectionBuildReadiness:
    projection_id: str = ""
    can_inspect_from_meta_ide: bool = False
    can_route_work_via_agent_fleet: bool = False
    can_select_compute_target: bool = False
    missing_requirements: list[str] = field(default_factory=list)
    readiness_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "can_inspect_from_meta_ide": self.can_inspect_from_meta_ide,
            "can_route_work_via_agent_fleet": self.can_route_work_via_agent_fleet,
            "can_select_compute_target": self.can_select_compute_target,
            "missing_requirements": self.missing_requirements,
            "readiness_score": self.readiness_score,
        }


@dataclass
class ProjectionIntegrationSnapshot:
    projections: list[ProjectionIntegrationProfile] = field(default_factory=list)
    total: int = 0
    connected: int = 0
    partially_connected: int = 0
    unavailable: int = 0
    critical_gaps: int = 0
    readiness_summary: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projections": [p.to_dict() for p in self.projections],
            "total": self.total,
            "connected": self.connected,
            "partially_connected": self.partially_connected,
            "unavailable": self.unavailable,
            "critical_gaps": self.critical_gaps,
            "readiness_summary": self.readiness_summary,
            "generated_at": self.generated_at,
        }


# ── Alias Normalization ────────────────────────────────────────────────────

_PROJECTION_ALIASES: dict[str, str] = {
    "entrepreneuros": "entrepreneuros",
    "eos": "entrepreneuros",
    "EntrepreneurOS": "entrepreneuros",
    "EOS": "entrepreneuros",
    "lyfeos": "lyfeos",
    "LyfeOS": "lyfeos",
    "LYFEOS": "lyfeos",
    "creatoros": "creatoros",
    "CreatorOS": "creatoros",
    "CREATOROS": "creatoros",
}


def _normalize_projection_id(raw: str) -> str:
    return _PROJECTION_ALIASES.get(raw, _PROJECTION_ALIASES.get(raw.lower(), raw.lower()))


# ── Known Projection Seed Data ─────────────────────────────────────────────

_KNOWN_PROJECTIONS: dict[str, dict[str, Any]] = {
    "lyfeos": {
        "name": "LyfeOS",
        "maturity": "mature_partial",
        "description": "Life management projection — most mature partial integration",
        "locations": [
            {"machine": "vps", "root_path": "projections/lyfeos"},
        ],
        "substrate_capabilities": ["signals", "handlers", "correlation", "outcomes", "tables"],
    },
    "entrepreneuros": {
        "name": "EntrepreneurOS",
        "maturity": "early_partial",
        "description": "Entrepreneur/business projection — agents, views, workflows",
        "locations": [
            {"machine": "vps", "root_path": "projections/eos"},
        ],
        "substrate_capabilities": ["agents", "views", "workflows", "pipeline"],
    },
    "creatoros": {
        "name": "CreatorOS",
        "maturity": "early_partial",
        "description": "Creator/content projection — integration layer only",
        "locations": [
            {"machine": "vps", "root_path": "projections/creatoros"},
        ],
        "substrate_capabilities": ["signals", "handlers", "correlation", "outcomes", "tables"],
    },
}


class ProjectionIntegrationRuntime:
    """Read-only integration/audit layer over existing projection partials.

    Composes ProjectionPort, ProjectionSourceRegistry,
    ProjectionReconciliationEngine, CapabilityRuntime,
    OperationalizationRuntime, InfrastructureRuntime,
    ComputeFabricRuntime, MetaIDERuntime, AgentFleetRuntime.
    """

    def __init__(
        self,
        projection_port: Any | None = None,
        source_registry: Any | None = None,
        reconciliation_engine: Any | None = None,
        capability_runtime: Any | None = None,
        operationalization_runtime: Any | None = None,
        infrastructure_runtime: Any | None = None,
        compute_fabric: Any | None = None,
        meta_ide: Any | None = None,
        agent_fleet: Any | None = None,
        intent_runtime: Any | None = None,
    ) -> None:
        self._projection_port = projection_port
        self._source_registry = source_registry
        self._reconciliation = reconciliation_engine
        self._capability = capability_runtime
        self._operationalization = operationalization_runtime
        self._infrastructure = infrastructure_runtime
        self._compute_fabric = compute_fabric
        self._meta_ide = meta_ide
        self._agent_fleet = agent_fleet
        self._intent = intent_runtime
        self._extra_locations: dict[str, list[ProjectionCodeLocation]] = {}
        self._profiles_cache: dict[str, ProjectionIntegrationProfile] = {}

    def register_projection_location(
        self,
        projection_id: str,
        machine: str,
        root_path: str = "",
        repo_url: str = "",
        branch: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ProjectionCodeLocation:
        norm_id = _normalize_projection_id(projection_id)
        machine_type = ProjectionMachineType(machine) if machine in ProjectionMachineType.__members__.values() else ProjectionMachineType.UNKNOWN
        try:
            machine_type = ProjectionMachineType(machine)
        except ValueError:
            machine_type = ProjectionMachineType.UNKNOWN

        availability = self._probe_availability(machine_type, root_path)

        loc = ProjectionCodeLocation(
            projection_id=norm_id,
            machine=machine_type,
            root_path=root_path,
            repo_url=repo_url,
            branch=branch,
            availability_status=availability,
            last_seen=time.time() if availability == ProjectionAvailability.AVAILABLE else 0.0,
            metadata=metadata or {},
        )

        self._extra_locations.setdefault(norm_id, []).append(loc)
        self._profiles_cache.pop(norm_id, None)
        return loc

    def _probe_availability(
        self, machine: ProjectionMachineType, root_path: str,
    ) -> ProjectionAvailability:
        if machine == ProjectionMachineType.VPS:
            umh_root = os.environ.get("UMH_ROOT", "/opt/OS")
            full_path = os.path.join(umh_root, root_path) if not os.path.isabs(root_path) else root_path
            if os.path.isdir(full_path):
                return ProjectionAvailability.AVAILABLE
            return ProjectionAvailability.UNAVAILABLE
        if machine in (ProjectionMachineType.WINDOWS, ProjectionMachineType.LOCAL):
            return ProjectionAvailability.UNKNOWN
        return ProjectionAvailability.UNKNOWN

    def _build_locations(self, projection_id: str) -> list[ProjectionCodeLocation]:
        locations: list[ProjectionCodeLocation] = []
        seed = _KNOWN_PROJECTIONS.get(projection_id, {})
        for loc_data in seed.get("locations", []):
            machine = ProjectionMachineType(loc_data.get("machine", "unknown"))
            root_path = loc_data.get("root_path", "")
            availability = self._probe_availability(machine, root_path)
            locations.append(ProjectionCodeLocation(
                projection_id=projection_id,
                machine=machine,
                root_path=root_path,
                availability_status=availability,
                last_seen=time.time() if availability == ProjectionAvailability.AVAILABLE else 0.0,
            ))
        locations.extend(self._extra_locations.get(projection_id, []))
        return locations

    def _detect_gaps(
        self, projection_id: str, locations: list[ProjectionCodeLocation],
    ) -> list[ProjectionIntegrationGap]:
        gaps: list[ProjectionIntegrationGap] = []

        has_available = any(
            loc.availability_status == ProjectionAvailability.AVAILABLE
            for loc in locations
        )
        if not has_available:
            gaps.append(ProjectionIntegrationGap(
                projection_id=projection_id,
                gap_type=IntegrationGapType.INACCESSIBLE_CODEBASE,
                severity="high",
                description=f"No accessible code location for {projection_id}",
                recommended_integration_action="Register an available code location or connect Windows node",
            ))

        if not locations:
            gaps.append(ProjectionIntegrationGap(
                projection_id=projection_id,
                gap_type=IntegrationGapType.MISSING_CODE_LOCATION,
                severity="critical",
                description=f"No code locations registered for {projection_id}",
                recommended_integration_action="Register at least one code location",
            ))

        if self._projection_port:
            try:
                registrations = self._projection_port.list_registrations()
                reg_ids = set()
                if registrations:
                    reg_ids = {
                        getattr(r, "projection_id", getattr(r, "name", str(r)))
                        for r in registrations
                    }
                if projection_id not in reg_ids:
                    gaps.append(ProjectionIntegrationGap(
                        projection_id=projection_id,
                        gap_type=IntegrationGapType.MISSING_REGISTRATION,
                        severity="medium",
                        description=f"{projection_id} not registered in ProjectionPort",
                        recommended_integration_action="Register projection in ProjectionPort at startup",
                    ))
            except Exception:
                logger.debug("ProjectionPort unavailable for gap detection", exc_info=True)

        return gaps

    def _detect_duplicated_concerns(self, projection_id: str) -> list[str]:
        duplicated: list[str] = []
        if self._reconciliation:
            try:
                divergences = self._reconciliation.list_divergences()
                if divergences:
                    for d in divergences:
                        d_proj = getattr(d, "projection_id", "")
                        if d_proj == projection_id:
                            d_type = getattr(d, "divergence_type", str(d))
                            duplicated.append(str(d_type))
            except Exception:
                logger.debug("ReconciliationEngine unavailable", exc_info=True)
        return duplicated

    def _get_substrate_capabilities(self, projection_id: str) -> list[str]:
        seed = _KNOWN_PROJECTIONS.get(projection_id, {})
        caps = list(seed.get("substrate_capabilities", []))

        if self._projection_port:
            try:
                port_caps = self._projection_port.capabilities_for(projection_id)
                if port_caps:
                    for c in port_caps:
                        name = getattr(c, "name", str(c))
                        if name not in caps:
                            caps.append(name)
            except Exception:
                logger.debug("ProjectionPort capabilities_for failed", exc_info=True)

        return caps

    def audit_projection(self, projection_id: str) -> ProjectionIntegrationProfile:
        norm_id = _normalize_projection_id(projection_id)
        seed = _KNOWN_PROJECTIONS.get(norm_id, {})

        locations = self._build_locations(norm_id)
        gaps = self._detect_gaps(norm_id, locations)
        duplicated = self._detect_duplicated_concerns(norm_id)
        caps = self._get_substrate_capabilities(norm_id)

        maturity_str = seed.get("maturity", "unknown")
        try:
            maturity = ProjectionMaturityLevel(maturity_str)
        except ValueError:
            maturity = ProjectionMaturityLevel.UNKNOWN

        profile = ProjectionIntegrationProfile(
            projection_id=norm_id,
            name=seed.get("name", norm_id),
            maturity_level=maturity,
            description=seed.get("description", ""),
            code_locations=locations,
            substrate_capabilities_consumed=caps,
            duplicated_substrate_concerns=duplicated,
            integration_gaps=gaps,
            last_audited=time.time(),
        )

        self._profiles_cache[norm_id] = profile
        return profile

    def audit_all(self) -> ProjectionIntegrationSnapshot:
        profiles: list[ProjectionIntegrationProfile] = []
        all_ids = set(_KNOWN_PROJECTIONS.keys()) | set(self._extra_locations.keys())
        for pid in sorted(all_ids):
            profiles.append(self.audit_projection(pid))
        return self._build_snapshot(profiles)

    def projection_profile(self, projection_id: str) -> ProjectionIntegrationProfile:
        norm_id = _normalize_projection_id(projection_id)
        if norm_id in self._profiles_cache:
            return self._profiles_cache[norm_id]
        return self.audit_projection(norm_id)

    def code_locations(self, projection_id: str) -> list[ProjectionCodeLocation]:
        norm_id = _normalize_projection_id(projection_id)
        return self._build_locations(norm_id)

    def substrate_consumption(self, projection_id: str) -> dict[str, Any]:
        norm_id = _normalize_projection_id(projection_id)
        caps = self._get_substrate_capabilities(norm_id)
        return {
            "projection_id": norm_id,
            "capabilities": caps,
            "count": len(caps),
        }

    def detect_duplicated_substrate_concerns(self, projection_id: str) -> list[str]:
        norm_id = _normalize_projection_id(projection_id)
        return self._detect_duplicated_concerns(norm_id)

    def integration_gaps(self, projection_id: str) -> list[ProjectionIntegrationGap]:
        norm_id = _normalize_projection_id(projection_id)
        locations = self._build_locations(norm_id)
        return self._detect_gaps(norm_id, locations)

    def build_readiness(self, projection_id: str) -> ProjectionBuildReadiness:
        norm_id = _normalize_projection_id(projection_id)
        locations = self._build_locations(norm_id)
        gaps = self._detect_gaps(norm_id, locations)

        has_available = any(
            loc.availability_status == ProjectionAvailability.AVAILABLE
            for loc in locations
        )
        can_inspect = has_available and self._meta_ide is not None

        high_severity_gaps = [g for g in gaps if g.severity in ("high", "critical")]
        can_route_work = self._agent_fleet is not None and len(high_severity_gaps) == 0

        can_select_compute = False
        if self._compute_fabric:
            try:
                nodes = self._compute_fabric.nodes()
                if nodes:
                    can_select_compute = any(
                        getattr(n, "status", "") == "online" or
                        getattr(n, "available", False)
                        for n in nodes
                    )
            except Exception:
                logger.debug("ComputeFabric nodes check failed", exc_info=True)

        missing: list[str] = []
        if not can_inspect:
            missing.append("No available code location for Meta IDE inspection")
        if not can_route_work:
            if self._agent_fleet is None:
                missing.append("AgentFleetRuntime not available")
            if high_severity_gaps:
                missing.append(f"{len(high_severity_gaps)} high/critical integration gaps block routing")
        if not can_select_compute:
            missing.append("No online compute target available")

        score = sum([can_inspect, can_route_work, can_select_compute]) / 3.0

        return ProjectionBuildReadiness(
            projection_id=norm_id,
            can_inspect_from_meta_ide=can_inspect,
            can_route_work_via_agent_fleet=can_route_work,
            can_select_compute_target=can_select_compute,
            missing_requirements=missing,
            readiness_score=round(score, 2),
        )

    def snapshot(self) -> ProjectionIntegrationSnapshot:
        all_ids = set(_KNOWN_PROJECTIONS.keys()) | set(self._extra_locations.keys())
        profiles = [self.projection_profile(pid) for pid in sorted(all_ids)]
        return self._build_snapshot(profiles)

    def _build_snapshot(
        self, profiles: list[ProjectionIntegrationProfile],
    ) -> ProjectionIntegrationSnapshot:
        connected = 0
        partial = 0
        unavailable = 0
        critical_gaps = 0
        readiness: dict[str, Any] = {}

        for p in profiles:
            has_available = any(
                loc.availability_status == ProjectionAvailability.AVAILABLE
                for loc in p.code_locations
            )
            has_gaps = len(p.integration_gaps) > 0

            if has_available and not has_gaps:
                connected += 1
            elif has_available and has_gaps:
                partial += 1
            else:
                unavailable += 1

            for g in p.integration_gaps:
                if g.severity == "critical":
                    critical_gaps += 1

            br = self.build_readiness(p.projection_id)
            readiness[p.projection_id] = br.to_dict()

        return ProjectionIntegrationSnapshot(
            projections=profiles,
            total=len(profiles),
            connected=connected,
            partially_connected=partial,
            unavailable=unavailable,
            critical_gaps=critical_gaps,
            readiness_summary=readiness,
        )
