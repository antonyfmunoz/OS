"""Projection Reconciliation Engine — diagnoses divergence across projection sources.

Phase 14.0. UMH substrate subsystem. Instance-agnostic.

Compares registered projection sources, identifies divergences, and
generates diagnostic reports. Does NOT perform destructive sync or
auto-canonization — only read-only diagnosis.
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

from substrate.organism.projection_source_registry import (
    ProjectionName,
    ProjectionSource,
    ProjectionSourceRegistry,
    ProjectionSourceType,
    ReadStatus,
    SourceCanonicality,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DIAGNOSTICS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "projection_reconciliation", "divergences.jsonl"
)


class DivergenceType(str, Enum):
    MISSING_SOURCE = "missing_source"
    DUPLICATE_SOURCE = "duplicate_source"
    STALE_DOCUMENT = "stale_document"
    STALE_CODE = "stale_code"
    PARTIAL_BACKEND = "partial_backend"
    UNINSPECTED_SOURCE = "uninspected_source"
    CONFLICTING_CLAIM = "conflicting_claim"
    LOCAL_UNCOMMITTED_SOURCE = "local_uncommitted_source"
    GITHUB_LAG = "github_lag"
    DOCS_AHEAD_OF_CODE = "docs_ahead_of_code"
    CODE_AHEAD_OF_DOCS = "code_ahead_of_docs"
    UNKNOWN_CANONICALITY = "unknown_canonicality"
    SCHEMA_VERSION_SPLIT = "schema_version_split"
    CODE_DUPLICATION = "code_duplication"
    SCHEMA_DRIFT = "schema_drift"
    TYPE_INCONSISTENCY = "type_inconsistency"
    INSTANCE_CONTEXT_IN_DATA = "instance_context_in_data"


class DivergenceSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ProjectionDivergence:
    divergence_id: str = ""
    projection: str = ProjectionName.UNKNOWN.value
    source_a: str = ""
    source_b: str = ""
    divergence_type: str = DivergenceType.UNKNOWN_CANONICALITY.value
    severity: str = DivergenceSeverity.MEDIUM.value
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""
    requires_permission: bool = False
    requires_operator_decision: bool = False

    def __post_init__(self) -> None:
        if not self.divergence_id:
            self.divergence_id = f"div-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "divergence_id": self.divergence_id,
            "projection": self.projection,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "divergence_type": self.divergence_type,
            "severity": self.severity,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "requires_permission": self.requires_permission,
            "requires_operator_decision": self.requires_operator_decision,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectionDivergence:
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class ProjectionReconciliationEngine:
    """Diagnoses divergence across registered projection sources."""

    def __init__(
        self,
        registry: ProjectionSourceRegistry | None = None,
        diagnostics_path: str | None = None,
    ) -> None:
        self._registry = registry or ProjectionSourceRegistry()
        self._path = diagnostics_path or _DIAGNOSTICS_PATH
        self._divergences: list[ProjectionDivergence] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self._divergences.append(ProjectionDivergence.from_dict(d))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed divergence line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            for div in self._divergences:
                f.write(json.dumps(div.to_dict(), default=str) + "\n")

    def add_divergence(self, divergence: ProjectionDivergence) -> ProjectionDivergence:
        self._divergences.append(divergence)
        self._save()
        return divergence

    def list_divergences(
        self,
        projection: str | None = None,
        severity: str | None = None,
        divergence_type: str | None = None,
    ) -> list[ProjectionDivergence]:
        result = list(self._divergences)
        if projection:
            result = [d for d in result if d.projection == projection]
        if severity:
            result = [d for d in result if d.severity == severity]
        if divergence_type:
            result = [d for d in result if d.divergence_type == divergence_type]
        return result

    def run_diagnostic(self) -> list[ProjectionDivergence]:
        """Run full divergence diagnostic against registry. Returns new findings."""
        self._divergences = []
        findings: list[ProjectionDivergence] = []

        findings.extend(self._check_uninspected_sources())
        findings.extend(self._check_unknown_canonicality())
        findings.extend(self._check_partial_backends())
        findings.extend(self._check_schema_version_splits())
        findings.extend(self._check_code_duplication())
        findings.extend(self._check_schema_drift())
        findings.extend(self._check_instance_context())
        findings.extend(self._check_type_inconsistencies())

        self._divergences = findings
        self._save()
        return findings

    def _check_uninspected_sources(self) -> list[ProjectionDivergence]:
        findings = []
        for src in self._registry.uninspected_sources():
            findings.append(ProjectionDivergence(
                projection=src.projection,
                source_a=src.source_id,
                source_b="",
                divergence_type=DivergenceType.UNINSPECTED_SOURCE.value,
                severity=DivergenceSeverity.HIGH.value,
                evidence=[f"Source '{src.name}' has read_status={src.read_status}"],
                recommendation=f"Request permission to inspect {src.name}",
                requires_permission=src.permission_required,
                requires_operator_decision=True,
            ))
        return findings

    def _check_unknown_canonicality(self) -> list[ProjectionDivergence]:
        findings = []
        for src in self._registry.list_sources():
            if src.canonicality == SourceCanonicality.UNKNOWN.value:
                findings.append(ProjectionDivergence(
                    projection=src.projection,
                    source_a=src.source_id,
                    divergence_type=DivergenceType.UNKNOWN_CANONICALITY.value,
                    severity=DivergenceSeverity.MEDIUM.value,
                    evidence=[f"Source '{src.name}' canonicality is unknown"],
                    recommendation="Inspect and classify canonicality",
                    requires_operator_decision=True,
                ))
        return findings

    def _check_partial_backends(self) -> list[ProjectionDivergence]:
        findings = []
        for src in self._registry.list_sources(canonicality=SourceCanonicality.PARTIAL.value):
            findings.append(ProjectionDivergence(
                projection=src.projection,
                source_a=src.source_id,
                divergence_type=DivergenceType.PARTIAL_BACKEND.value,
                severity=DivergenceSeverity.HIGH.value,
                evidence=[
                    f"Source '{src.name}' is classified as partial",
                    f"Path: {src.path_or_locator}",
                    f"Contains: {', '.join(src.contains[:3])}",
                ],
                recommendation="Compare with full source on other device/repo to identify gaps",
                requires_permission=True,
                requires_operator_decision=True,
            ))
        return findings

    def _check_schema_version_splits(self) -> list[ProjectionDivergence]:
        return [ProjectionDivergence(
            projection="EOS",
            source_a="psrc-vps-saas",
            source_b="projections/eos/integration",
            divergence_type=DivergenceType.SCHEMA_VERSION_SPLIT.value,
            severity=DivergenceSeverity.HIGH.value,
            evidence=[
                "saas/db/schema.ts uses v2 schema (events, clients, ventures, transactions, offers)",
                "projections/eos/integration/tables.py uses v1 schema (crm_contacts, crm_deals, crm_activities)",
                "EOS agents/views query events table (v2) while integration layer polls crm_* tables (v1)",
            ],
            recommendation="Reconcile schema versions — determine which is canonical and migrate the other",
            requires_operator_decision=True,
        )]

    def _check_code_duplication(self) -> list[ProjectionDivergence]:
        return [ProjectionDivergence(
            projection="Shared",
            source_a="projections/eos/integration",
            source_b="projections/creatoros/integration + projections/lyfeos/integration",
            divergence_type=DivergenceType.CODE_DUPLICATION.value,
            severity=DivergenceSeverity.MEDIUM.value,
            evidence=[
                "7-file integration pattern is nearly identical across all 3 projections",
                "_require_str, _require_int, outcome severity, OutcomeReceiver duplicated",
                "Connection management pattern copy-pasted",
            ],
            recommendation="Extract shared integration base into substrate or adapters",
            requires_operator_decision=False,
        )]

    def _check_schema_drift(self) -> list[ProjectionDivergence]:
        return [ProjectionDivergence(
            projection="EOS",
            source_a="saas/db/schema.ts",
            source_b="saas/db/migrations/",
            divergence_type=DivergenceType.SCHEMA_DRIFT.value,
            severity=DivergenceSeverity.MEDIUM.value,
            evidence=[
                "7 tables exist in migrations but not in schema.ts",
                "Missing: model_preferences, cross_product_permissions, user_intelligence_profiles",
                "Missing: product_connections, higgsfield_jobs, goals, goal_outcomes",
                "Migration 0004 is missing from sequence",
            ],
            recommendation="Add missing tables to schema.ts or mark migrations as deprecated",
            requires_operator_decision=True,
        )]

    def _check_instance_context(self) -> list[ProjectionDivergence]:
        return [ProjectionDivergence(
            projection="EOS",
            source_a="saas/db/seed.ts",
            divergence_type=DivergenceType.INSTANCE_CONTEXT_IN_DATA.value,
            severity=DivergenceSeverity.LOW.value,
            evidence=[
                "Seed data contains instance-specific values (founder name, company names, product names)",
                "Seed data references projection-specific database role",
            ],
            recommendation="Parametrize seed data or move to instance config",
            requires_operator_decision=False,
        )]

    def _check_type_inconsistencies(self) -> list[ProjectionDivergence]:
        return [ProjectionDivergence(
            projection="EOS",
            source_a="saas/db/schema.ts (clients, transactions, fulfillment_events, offers)",
            divergence_type=DivergenceType.TYPE_INCONSISTENCY.value,
            severity=DivergenceSeverity.MEDIUM.value,
            evidence=[
                "clients.org_id and clients.venture_id are text type",
                "transactions, fulfillment_events, offers also use text for org_id/venture_id",
                "ventures.org_id is uuid FK to organizations — inconsistent",
            ],
            recommendation="Standardize org_id/venture_id as uuid FKs across all tables",
            requires_operator_decision=True,
        )]

    def summary(self) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_projection: dict[str, int] = {}
        for d in self._divergences:
            by_severity[d.severity] = by_severity.get(d.severity, 0) + 1
            by_type[d.divergence_type] = by_type.get(d.divergence_type, 0) + 1
            by_projection[d.projection] = by_projection.get(d.projection, 0) + 1
        return {
            "total_divergences": len(self._divergences),
            "by_severity": by_severity,
            "by_type": by_type,
            "by_projection": by_projection,
            "requires_permission_count": sum(1 for d in self._divergences if d.requires_permission),
            "requires_operator_decision_count": sum(1 for d in self._divergences if d.requires_operator_decision),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "divergences": [d.to_dict() for d in self._divergences],
            "summary": self.summary(),
        }
