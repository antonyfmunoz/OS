"""Contradiction Engine — detect mismatches between declared and observed reality.

Examples:
  - Audit says public cockpit is live, but DNS points elsewhere
  - Module claims capability exists, but daemon does not wire it
  - Cockpit panel says live, but endpoint is missing
  - Mutation type registered, but no executor exists
  - Data store declared, but file is empty

All checks are deterministic. No LLM required.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class ContradictionSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ContradictionType(str, Enum):
    DECLARED_MISSING_OBSERVED = "declared_missing_observed"
    OBSERVED_MISSING_DECLARED = "observed_missing_declared"
    STALE_DEPLOYMENT = "stale_deployment"
    ROUTE_MISMATCH = "route_mismatch"
    API_CONTRACT_MISMATCH = "api_contract_mismatch"
    WIRING_MISMATCH = "wiring_mismatch"
    CAPABILITY_GAP = "capability_gap"
    SECURITY_MISMATCH = "security_mismatch"
    DEPENDENCY_MISMATCH = "dependency_mismatch"
    DATA_INTEGRITY = "data_integrity"
    STATUS_CONTRADICTION = "status_contradiction"


@dataclass
class Claim:
    source: str
    statement: str
    entity_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "statement": self.statement,
            "entity_id": self.entity_id,
        }


@dataclass
class Observation:
    source: str
    finding: str
    observed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "finding": self.finding,
            "observed_at": self.observed_at,
        }


@dataclass
class Contradiction:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    contradiction_type: ContradictionType = ContradictionType.DECLARED_MISSING_OBSERVED
    severity: ContradictionSeverity = ContradictionSeverity.MEDIUM
    claim: Claim | None = None
    observation: Observation | None = None
    confidence: float = 0.8
    evidence: str = ""
    recommended_fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.contradiction_type.value,
            "severity": self.severity.value,
            "claim": self.claim.to_dict() if self.claim else None,
            "observation": self.observation.to_dict() if self.observation else None,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommended_fix": self.recommended_fix,
        }


@dataclass
class ContradictionReport:
    contradictions: list[Contradiction] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)
    checks_performed: int = 0

    def add(self, contradiction: Contradiction) -> None:
        self.contradictions.append(contradiction)

    def by_severity(self, severity: ContradictionSeverity) -> list[Contradiction]:
        return [c for c in self.contradictions if c.severity == severity]

    def by_type(self, ctype: ContradictionType) -> list[Contradiction]:
        return [c for c in self.contradictions if c.contradiction_type == ctype]

    def summary(self) -> dict[str, Any]:
        sev_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for c in self.contradictions:
            sev_counts[c.severity.value] = sev_counts.get(c.severity.value, 0) + 1
            type_counts[c.contradiction_type.value] = type_counts.get(c.contradiction_type.value, 0) + 1
        return {
            "total": len(self.contradictions),
            "by_severity": sev_counts,
            "by_type": type_counts,
            "checks_performed": self.checks_performed,
            "checked_at": self.checked_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "contradictions": [c.to_dict() for c in self.contradictions],
            "checked_at": self.checked_at,
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """HTTP-safe serialization — strips internal sources and file paths."""
        safe_contradictions = []
        for c in self.contradictions:
            safe_contradictions.append({
                "id": c.id,
                "type": c.contradiction_type.value,
                "severity": c.severity.value,
                "confidence": c.confidence,
                "recommended_fix": c.recommended_fix,
            })
        return {
            "summary": self.summary(),
            "contradictions": safe_contradictions,
            "checked_at": self.checked_at,
        }


# ---------------------------------------------------------------------------
# Contradiction checks — each is a deterministic probe
# ---------------------------------------------------------------------------

def _check_missing_subsystem_files(report: ContradictionReport, world_model) -> None:
    """Subsystems declared in world model but files don't exist."""
    from substrate.organism.world_model import EntityCategory, EntityStatus
    for entity in world_model.get_entities_by_category(EntityCategory.SUBSYSTEM):
        if entity.status == EntityStatus.MISSING:
            report.add(Contradiction(
                contradiction_type=ContradictionType.DECLARED_MISSING_OBSERVED,
                severity=ContradictionSeverity.HIGH,
                claim=Claim(
                    source="world_model",
                    statement=f"Subsystem '{entity.name}' is expected to exist",
                    entity_id=entity.id,
                ),
                observation=Observation(
                    source="filesystem",
                    finding=f"File not found: {entity.module_path}",
                ),
                confidence=0.95,
                evidence=f"Subsystem {entity.id} listed but file missing",
                recommended_fix=f"Create {entity.module_path} or remove from expected subsystems",
            ))
    report.checks_performed += 1


def _check_empty_data_stores(report: ContradictionReport, world_model) -> None:
    """Data stores that exist but are empty (degraded state)."""
    from substrate.organism.world_model import EntityCategory, EntityStatus
    for entity in world_model.get_entities_by_category(EntityCategory.DATA_STORE):
        if entity.status == EntityStatus.DEGRADED:
            report.add(Contradiction(
                contradiction_type=ContradictionType.DATA_INTEGRITY,
                severity=ContradictionSeverity.MEDIUM,
                claim=Claim(
                    source="world_model",
                    statement=f"Data store '{entity.name}' should contain data",
                    entity_id=entity.id,
                ),
                observation=Observation(
                    source="filesystem",
                    finding=f"File exists but is empty: {entity.module_path}",
                ),
                confidence=0.85,
                evidence="File has zero bytes",
                recommended_fix=f"Verify data pipeline writes to {entity.module_path}",
            ))
    report.checks_performed += 1


def _check_orphaned_subsystems(report: ContradictionReport, dep_graph) -> None:
    """Subsystems with no dependency connections (may be unwired)."""
    orphans = dep_graph.orphaned_nodes()
    for nid in orphans:
        node = dep_graph.get_node(nid)
        if node and node.category == "subsystem":
            report.add(Contradiction(
                contradiction_type=ContradictionType.WIRING_MISMATCH,
                severity=ContradictionSeverity.LOW,
                claim=Claim(
                    source="dependency_graph",
                    statement=f"Subsystem '{node.name}' exists but has no dependencies",
                    entity_id=nid,
                ),
                observation=Observation(
                    source="dependency_graph",
                    finding=f"No edges connect to/from node '{nid}'",
                ),
                confidence=0.6,
                evidence="Orphaned in dependency graph",
                recommended_fix=f"Wire {node.name} into daemon or document why it's standalone",
            ))
    report.checks_performed += 1


def _check_deployment_files(report: ContradictionReport, world_model) -> None:
    """Deployment configs that should exist but don't."""
    from substrate.organism.world_model import EntityCategory, EntityStatus
    for entity in world_model.get_entities_by_category(EntityCategory.DEPLOYMENT):
        if entity.status == EntityStatus.MISSING:
            report.add(Contradiction(
                contradiction_type=ContradictionType.STALE_DEPLOYMENT,
                severity=ContradictionSeverity.MEDIUM,
                claim=Claim(
                    source="world_model",
                    statement=f"Deployment config '{entity.name}' expected",
                    entity_id=entity.id,
                ),
                observation=Observation(
                    source="filesystem",
                    finding=f"File not found: {entity.module_path}",
                ),
                confidence=0.9,
                evidence=f"Deployment file missing: {entity.module_path}",
                recommended_fix=f"Create {entity.module_path} or update deployment expectations",
            ))
    report.checks_performed += 1


def _check_route_panel_mismatch(report: ContradictionReport, world_model) -> None:
    """Cockpit panels that exist but have no matching API route."""
    from substrate.organism.world_model import EntityCategory
    panels = world_model.get_entities_by_category(EntityCategory.COCKPIT_SURFACE)
    routes = world_model.get_entities_by_category(EntityCategory.INTERFACE)
    route_names = {e.id.replace("route_", "") for e in routes}

    for panel in panels:
        panel_name = panel.id.replace("panel_", "").lower()
        has_route = any(
            panel_name in rn or rn in panel_name
            for rn in route_names
        )
        if not has_route and panel_name not in ("dashboard", "editor", "settings", "comms", "analytics"):
            report.add(Contradiction(
                contradiction_type=ContradictionType.ROUTE_MISMATCH,
                severity=ContradictionSeverity.INFO,
                claim=Claim(
                    source="cockpit",
                    statement=f"Panel '{panel.name}' exists in cockpit",
                    entity_id=panel.id,
                ),
                observation=Observation(
                    source="api_routes",
                    finding=f"No dedicated API route found for panel '{panel_name}'",
                ),
                confidence=0.4,
                evidence="Panel may use a shared route or have no backend",
                recommended_fix=f"Verify panel '{panel.name}' data source",
            ))
    report.checks_performed += 1


def _check_dependency_cycles(report: ContradictionReport, dep_graph) -> None:
    """Circular dependencies (architecture violations)."""
    cycles = dep_graph.circular_dependencies()
    for cycle in cycles:
        report.add(Contradiction(
            contradiction_type=ContradictionType.DEPENDENCY_MISMATCH,
            severity=ContradictionSeverity.HIGH,
            claim=Claim(
                source="architecture",
                statement="Dependency graph should be acyclic",
            ),
            observation=Observation(
                source="dependency_graph",
                finding=f"Cycle detected: {' → '.join(cycle)}",
            ),
            confidence=0.95,
            evidence=f"Cycle: {cycle}",
            recommended_fix="Break the cycle by introducing an abstract port or refactoring",
        ))
    report.checks_performed += 1


def _check_governance_missing(report: ContradictionReport, world_model) -> None:
    """Governance subsystems that should exist but don't."""
    from substrate.organism.world_model import EntityCategory, EntityStatus
    for entity in world_model.get_entities_by_category(EntityCategory.GOVERNANCE):
        if entity.status == EntityStatus.MISSING:
            report.add(Contradiction(
                contradiction_type=ContradictionType.CAPABILITY_GAP,
                severity=ContradictionSeverity.HIGH,
                claim=Claim(
                    source="world_model",
                    statement=f"Governance system '{entity.name}' is expected",
                    entity_id=entity.id,
                ),
                observation=Observation(
                    source="filesystem",
                    finding=f"File not found for governance: {entity.module_path}",
                ),
                confidence=0.9,
                evidence="Governance system missing",
                recommended_fix=f"Create or locate {entity.module_path}",
            ))
    report.checks_performed += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ContradictionEngine:
    """Runs all contradiction checks and produces a report."""

    def __init__(self, world_model=None, dependency_graph=None):
        self._world_model = world_model
        self._dep_graph = dependency_graph

    def _ensure_models(self) -> None:
        if self._world_model is None:
            from substrate.organism.world_model import extract_world_model
            self._world_model = extract_world_model()
        if self._dep_graph is None:
            from substrate.organism.dependency_graph import build_dependency_graph
            self._dep_graph = build_dependency_graph(self._world_model)

    def run(self) -> ContradictionReport:
        self._ensure_models()
        report = ContradictionReport()
        _check_missing_subsystem_files(report, self._world_model)
        _check_empty_data_stores(report, self._world_model)
        _check_orphaned_subsystems(report, self._dep_graph)
        _check_deployment_files(report, self._world_model)
        _check_route_panel_mismatch(report, self._world_model)
        _check_dependency_cycles(report, self._dep_graph)
        _check_governance_missing(report, self._world_model)
        return report


def detect_contradictions(world_model=None, dependency_graph=None) -> ContradictionReport:
    """Convenience function — run all contradiction checks."""
    engine = ContradictionEngine(world_model, dependency_graph)
    return engine.run()


def persist_contradictions(report: ContradictionReport, path: str | None = None) -> str:
    """Persist contradiction report to JSONL."""
    if path is None:
        path = os.path.join(_REPO_ROOT, "data", "umh", "organism", "contradictions.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(report.to_dict(), default=str) + "\n")
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, _REPO_ROOT)
    report = detect_contradictions()
    print(json.dumps(report.summary(), indent=2))
    for c in report.contradictions:
        sev = c.severity.value.upper()
        print(f"  [{sev}] {c.contradiction_type.value}: {c.evidence}")
        if c.recommended_fix:
            print(f"    → {c.recommended_fix}")
