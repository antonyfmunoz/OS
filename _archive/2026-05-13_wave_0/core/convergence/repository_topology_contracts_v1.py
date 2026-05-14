"""Repository Topology Contracts v1.

14 contracts and 4 enums for repository convergence —
physically coherent operational system aligned with intended
end-state architecture.

The repository itself must become constitutionally coherent,
not merely the runtime semantics.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deterministic_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"{prefix}{h}"


class ConvergencePhase(Enum):
    SCANNED = "scanned"
    CLASSIFIED = "classified"
    VERIFIED = "verified"
    QUARANTINED = "quarantined"
    CONVERGED = "converged"
    INGESTION_READY = "ingestion_ready"
    ARCHIVED = "archived"


class ConvergenceEventType(Enum):
    TOPOLOGY_SCANNED = "topology_scanned"
    NAMESPACE_VERIFIED = "namespace_verified"
    DUPLICATE_DETECTED = "duplicate_detected"
    RUNTIME_QUARANTINED = "runtime_quarantined"
    IMPORT_GRAPH_VERIFIED = "import_graph_verified"
    RUNTIME_ENTRYPOINT_VERIFIED = "runtime_entrypoint_verified"
    FILESYSTEM_VERIFIED = "filesystem_verified"
    INGESTION_READINESS_VERIFIED = "ingestion_readiness_verified"
    CONVERGENCE_BOUNDARY_DENIED = "convergence_boundary_denied"


class SubsystemClassification(Enum):
    CANONICAL = "canonical"
    DEPRECATED = "deprecated"
    QUARANTINED = "quarantined"
    EXPERIMENTAL = "experimental"
    DEAD = "dead"
    CONFLICTING = "conflicting"


class ConvergenceDomain(Enum):
    TOPOLOGY = "topology"
    NAMESPACE = "namespace"
    DUPLICATE = "duplicate"
    QUARANTINE = "quarantine"
    IMPORT_GRAPH = "import_graph"
    ENTRYPOINT = "entrypoint"
    FILESYSTEM = "filesystem"
    INGESTION = "ingestion"


@dataclass
class CanonicalRepositoryTopology:
    topology_id: str = ""
    root_path: str = ""
    canonical_directories: list[str] = field(default_factory=list)
    total_directories_scanned: int = 0
    total_files_scanned: int = 0
    topology_hash: str = ""
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id or _deterministic_id("rtopo-", self.created_at),
            "root_path": self.root_path,
            "canonical_directories": self.canonical_directories,
            "total_directories_scanned": self.total_directories_scanned,
            "total_files_scanned": self.total_files_scanned,
            "topology_hash": self.topology_hash,
            "created_at": self.created_at,
        }


@dataclass
class RuntimeTopologyState:
    state_id: str = ""
    runtime_roots: list[str] = field(default_factory=list)
    spine_count: int = 0
    orchestration_roots: int = 0
    entrypoints: list[str] = field(default_factory=list)
    single_spine: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id or _deterministic_id("rtstt-", self.timestamp),
            "runtime_roots": self.runtime_roots,
            "spine_count": self.spine_count,
            "orchestration_roots": self.orchestration_roots,
            "entrypoints": self.entrypoints,
            "single_spine": self.single_spine,
            "timestamp": self.timestamp,
        }


@dataclass
class NamespaceConvergenceState:
    convergence_id: str = ""
    namespaces_checked: int = 0
    duplicates_found: int = 0
    stale_aliases_found: int = 0
    shadow_trees_found: int = 0
    converged: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "convergence_id": self.convergence_id or _deterministic_id("nsconv-", self.timestamp),
            "namespaces_checked": self.namespaces_checked,
            "duplicates_found": self.duplicates_found,
            "stale_aliases_found": self.stale_aliases_found,
            "shadow_trees_found": self.shadow_trees_found,
            "converged": self.converged,
            "timestamp": self.timestamp,
        }


@dataclass
class DuplicateSubsystemState:
    detection_id: str = ""
    subsystem_type: str = ""
    instances_found: list[str] = field(default_factory=list)
    canonical_instance: str = ""
    classification: str = "canonical"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detection_id": self.detection_id or _deterministic_id("dupss-", self.subsystem_type, self.timestamp),
            "subsystem_type": self.subsystem_type,
            "instances_found": self.instances_found,
            "canonical_instance": self.canonical_instance,
            "classification": self.classification,
            "timestamp": self.timestamp,
        }


@dataclass
class RepositoryBoundaryState:
    boundary_id: str = ""
    action: str = ""
    allowed: bool = False
    reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id or _deterministic_id("rbnds-", self.action, self.timestamp),
            "action": self.action,
            "allowed": self.allowed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class ImportGraphState:
    graph_id: str = ""
    total_modules: int = 0
    cyclic_imports: int = 0
    bypass_imports: int = 0
    orphan_modules: int = 0
    hidden_roots: int = 0
    canonical: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id or _deterministic_id("igraph-", self.timestamp),
            "total_modules": self.total_modules,
            "cyclic_imports": self.cyclic_imports,
            "bypass_imports": self.bypass_imports,
            "orphan_modules": self.orphan_modules,
            "hidden_roots": self.hidden_roots,
            "canonical": self.canonical,
            "timestamp": self.timestamp,
        }


@dataclass
class RuntimeEntrypointState:
    entrypoint_id: str = ""
    canonical_spine: str = ""
    canonical_orchestration_root: str = ""
    canonical_entrypoint: str = ""
    hidden_adapters: int = 0
    hidden_dispatch_loops: int = 0
    alternate_roots: int = 0
    single_spine_verified: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrypoint_id": self.entrypoint_id or _deterministic_id("rtent-", self.timestamp),
            "canonical_spine": self.canonical_spine,
            "canonical_orchestration_root": self.canonical_orchestration_root,
            "canonical_entrypoint": self.canonical_entrypoint,
            "hidden_adapters": self.hidden_adapters,
            "hidden_dispatch_loops": self.hidden_dispatch_loops,
            "alternate_roots": self.alternate_roots,
            "single_spine_verified": self.single_spine_verified,
            "timestamp": self.timestamp,
        }


@dataclass
class DriftDetectionState:
    drift_id: str = ""
    domain: str = ""
    drift_detected: bool = False
    details: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_id": self.drift_id or _deterministic_id("drift-", self.domain, self.timestamp),
            "domain": self.domain,
            "drift_detected": self.drift_detected,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class ConvergenceReceipt:
    receipt_id: str = ""
    run_id: str = ""
    outcome: str = "incomplete"
    duplicates_quarantined: int = 0
    ingestion_ready: bool = False
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id or _deterministic_id("cvrcpt-", self.run_id, self.created_at),
            "run_id": self.run_id,
            "outcome": self.outcome,
            "duplicates_quarantined": self.duplicates_quarantined,
            "ingestion_ready": self.ingestion_ready,
            "created_at": self.created_at,
        }


@dataclass
class QuarantineState:
    quarantine_id: str = ""
    path: str = ""
    reason: str = ""
    classification: str = "dead"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "quarantine_id": self.quarantine_id or _deterministic_id("qrtn-", self.path, self.timestamp),
            "path": self.path,
            "reason": self.reason,
            "classification": self.classification,
            "timestamp": self.timestamp,
        }


@dataclass
class CanonicalDirectoryState:
    directory_id: str = ""
    path: str = ""
    canonical: bool = True
    owner_domain: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directory_id": self.directory_id or _deterministic_id("cdir-", self.path, self.timestamp),
            "path": self.path,
            "canonical": self.canonical,
            "owner_domain": self.owner_domain,
            "timestamp": self.timestamp,
        }


@dataclass
class IngestionReadinessState:
    readiness_id: str = ""
    directories_exist: bool = False
    runtime_paths_valid: bool = False
    dependencies_canonical: bool = False
    import_graph_stable: bool = False
    continuity_valid: bool = False
    replay_valid: bool = False
    observability_valid: bool = False
    ready: bool = False
    timestamp: str = field(default_factory=_now_iso)

    @property
    def readiness_score(self) -> float:
        checks = [
            self.directories_exist,
            self.runtime_paths_valid,
            self.dependencies_canonical,
            self.import_graph_stable,
            self.continuity_valid,
            self.replay_valid,
            self.observability_valid,
        ]
        return sum(1 for c in checks if c) / len(checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness_id": self.readiness_id or _deterministic_id("ingrd-", self.timestamp),
            "directories_exist": self.directories_exist,
            "runtime_paths_valid": self.runtime_paths_valid,
            "dependencies_canonical": self.dependencies_canonical,
            "import_graph_stable": self.import_graph_stable,
            "continuity_valid": self.continuity_valid,
            "replay_valid": self.replay_valid,
            "observability_valid": self.observability_valid,
            "ready": self.ready,
            "readiness_score": self.readiness_score,
            "timestamp": self.timestamp,
        }


@dataclass
class FilesystemIntegrityState:
    integrity_id: str = ""
    canonical_structure_valid: bool = False
    expected_topology_valid: bool = False
    deterministic_structure: bool = False
    ownership_mapping_valid: bool = False
    layout_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrity_id": self.integrity_id or _deterministic_id("fsint-", self.timestamp),
            "canonical_structure_valid": self.canonical_structure_valid,
            "expected_topology_valid": self.expected_topology_valid,
            "deterministic_structure": self.deterministic_structure,
            "ownership_mapping_valid": self.ownership_mapping_valid,
            "layout_hash": self.layout_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class ConvergedRuntimeState:
    state_id: str = ""
    single_spine: bool = False
    single_orchestration_root: bool = False
    no_duplicate_governance: bool = False
    no_duplicate_cognition: bool = False
    no_duplicate_ingestion: bool = False
    no_hidden_roots: bool = False
    no_speculative_branching: bool = False
    timestamp: str = field(default_factory=_now_iso)

    @property
    def convergence_score(self) -> float:
        checks = [
            self.single_spine,
            self.single_orchestration_root,
            self.no_duplicate_governance,
            self.no_duplicate_cognition,
            self.no_duplicate_ingestion,
            self.no_hidden_roots,
            self.no_speculative_branching,
        ]
        return sum(1 for c in checks if c) / len(checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id or _deterministic_id("cvrt-", self.timestamp),
            "single_spine": self.single_spine,
            "single_orchestration_root": self.single_orchestration_root,
            "no_duplicate_governance": self.no_duplicate_governance,
            "no_duplicate_cognition": self.no_duplicate_cognition,
            "no_duplicate_ingestion": self.no_duplicate_ingestion,
            "no_hidden_roots": self.no_hidden_roots,
            "no_speculative_branching": self.no_speculative_branching,
            "convergence_score": self.convergence_score,
            "timestamp": self.timestamp,
        }
