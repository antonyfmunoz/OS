"""Phase 83 migration contracts — typed envelopes for legacy module classification.

Every legacy module gets a LegacyModuleRecord. Migration mappings connect legacy
paths to clean equivalents. Import boundary rules prevent clean modules from
depending on deprecated paths.

No execution. No dynamic import of legacy modules. No mutation. No subprocess.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class LegacyModuleStatus(str, Enum):
    ACTIVE_RETAINED = "active_retained"
    DEPRECATED = "deprecated"
    MIGRATED = "migrated"
    DUPLICATE = "duplicate"
    BYPASS_RISK = "bypass_risk"
    FUTURE_REVIEW = "future_review"
    UNKNOWN = "unknown"


class LegacyModuleCategory(str, Enum):
    RUNTIME_ENGINE = "runtime_engine"
    SUBSTRATE = "substrate"
    RUNTIME_INTELLIGENCE = "runtime_intelligence"
    EXECUTION = "execution"
    GOVERNANCE = "governance"
    STORAGE = "storage"
    MEMORY = "memory"
    CONTROL = "control"
    ADAPTER = "adapter"
    OBSERVABILITY = "observability"
    INTERFACE = "interface"
    REGISTRY = "registry"
    ONTOLOGY = "ontology"
    TEST = "test"
    DOCS = "docs"
    UNKNOWN = "unknown"


class MigrationAction(str, Enum):
    RETAIN = "retain"
    WRAP = "wrap"
    MIGRATE_IMPORTS = "migrate_imports"
    CREATE_SHIM = "create_shim"
    MARK_DEPRECATED = "mark_deprecated"
    FUTURE_DELETE = "future_delete"
    REVIEW_MANUALLY = "review_manually"
    DO_NOT_TOUCH = "do_not_touch"
    UNKNOWN = "unknown"


class MigrationRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ImportBoundaryStatus(str, Enum):
    ALLOWED = "allowed"
    COMPATIBILITY_ALLOWED = "compatibility_allowed"
    DEPRECATED_IMPORT = "deprecated_import"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


def normalize_legacy_status(value: str) -> LegacyModuleStatus:
    value = value.strip().lower()
    for member in LegacyModuleStatus:
        if member.value == value:
            return member
    return LegacyModuleStatus.UNKNOWN


def normalize_module_category(value: str) -> LegacyModuleCategory:
    value = value.strip().lower()
    for member in LegacyModuleCategory:
        if member.value == value:
            return member
    return LegacyModuleCategory.UNKNOWN


def normalize_migration_action(value: str) -> MigrationAction:
    value = value.strip().lower()
    for member in MigrationAction:
        if member.value == value:
            return member
    return MigrationAction.UNKNOWN


def normalize_migration_risk(value: str) -> MigrationRiskLevel:
    value = value.strip().lower()
    for member in MigrationRiskLevel:
        if member.value == value:
            return member
    return MigrationRiskLevel.UNKNOWN


def normalize_import_boundary_status(value: str) -> ImportBoundaryStatus:
    value = value.strip().lower()
    for member in ImportBoundaryStatus:
        if member.value == value:
            return member
    return ImportBoundaryStatus.UNKNOWN


@dataclass
class LegacyModuleRecord:
    module_path: str
    module_name: str
    category: LegacyModuleCategory = LegacyModuleCategory.UNKNOWN
    status: LegacyModuleStatus = LegacyModuleStatus.UNKNOWN
    risk_level: MigrationRiskLevel = MigrationRiskLevel.UNKNOWN
    reason: str = ""
    clean_equivalent: str | None = None
    migration_action: MigrationAction = MigrationAction.UNKNOWN
    owner: str | None = None
    source: str = ""
    evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_path": self.module_path,
            "module_name": self.module_name,
            "category": self.category.value,
            "status": self.status.value,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "clean_equivalent": self.clean_equivalent,
            "migration_action": self.migration_action.value,
            "owner": self.owner,
            "source": self.source,
            "evidence": self.evidence,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegacyModuleRecord:
        return cls(
            module_path=data.get("module_path", ""),
            module_name=data.get("module_name", ""),
            category=normalize_module_category(data.get("category", "")),
            status=normalize_legacy_status(data.get("status", "")),
            risk_level=normalize_migration_risk(data.get("risk_level", "")),
            reason=data.get("reason", ""),
            clean_equivalent=data.get("clean_equivalent"),
            migration_action=normalize_migration_action(data.get("migration_action", "")),
            owner=data.get("owner"),
            source=data.get("source", ""),
            evidence=data.get("evidence", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MigrationMapping:
    mapping_id: str = ""
    legacy_module: str = ""
    clean_equivalent: str = ""
    migration_action: MigrationAction = MigrationAction.UNKNOWN
    confidence: float = 0.0
    reason: str = ""
    required_tests: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mapping_id:
            self.mapping_id = f"mm_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "legacy_module": self.legacy_module,
            "clean_equivalent": self.clean_equivalent,
            "migration_action": self.migration_action.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "required_tests": self.required_tests,
            "blockers": self.blockers,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MigrationMapping:
        return cls(
            mapping_id=data.get("mapping_id", ""),
            legacy_module=data.get("legacy_module", ""),
            clean_equivalent=data.get("clean_equivalent", ""),
            migration_action=normalize_migration_action(data.get("migration_action", "")),
            confidence=data.get("confidence", 0.0),
            reason=data.get("reason", ""),
            required_tests=data.get("required_tests", []),
            blockers=data.get("blockers", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ImportBoundaryRule:
    rule_id: str = ""
    source_pattern: str = ""
    forbidden_import_pattern: str = ""
    allowed_exceptions: list[str] = field(default_factory=list)
    status: ImportBoundaryStatus = ImportBoundaryStatus.BLOCKED
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.rule_id:
            self.rule_id = f"ibr_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "source_pattern": self.source_pattern,
            "forbidden_import_pattern": self.forbidden_import_pattern,
            "allowed_exceptions": self.allowed_exceptions,
            "status": self.status.value,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImportBoundaryRule:
        return cls(
            rule_id=data.get("rule_id", ""),
            source_pattern=data.get("source_pattern", ""),
            forbidden_import_pattern=data.get("forbidden_import_pattern", ""),
            allowed_exceptions=data.get("allowed_exceptions", []),
            status=normalize_import_boundary_status(data.get("status", "")),
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ImportBoundaryFinding:
    finding_id: str = ""
    source_file: str = ""
    imported_module: str = ""
    status: ImportBoundaryStatus = ImportBoundaryStatus.UNKNOWN
    rule_id: str | None = None
    severity: str = "warning"
    message: str = ""
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.finding_id:
            self.finding_id = f"ibf_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "source_file": self.source_file,
            "imported_module": self.imported_module,
            "status": self.status.value,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImportBoundaryFinding:
        return cls(
            finding_id=data.get("finding_id", ""),
            source_file=data.get("source_file", ""),
            imported_module=data.get("imported_module", ""),
            status=normalize_import_boundary_status(data.get("status", "")),
            rule_id=data.get("rule_id"),
            severity=data.get("severity", "warning"),
            message=data.get("message", ""),
            recommendation=data.get("recommendation", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MigrationInventory:
    generated_at: str = ""
    root_path: str = ""
    records: list[LegacyModuleRecord] = field(default_factory=list)
    mappings: list[MigrationMapping] = field(default_factory=list)
    findings: list[ImportBoundaryFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "root_path": self.root_path,
            "records": [r.to_dict() for r in self.records],
            "mappings": [m.to_dict() for m in self.mappings],
            "findings": [f.to_dict() for f in self.findings],
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
