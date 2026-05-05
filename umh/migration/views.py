"""Phase 83 migration views — operator-safe read models for migration status.

UI-safe. Deterministic. Bounded. No secrets. No execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class LegacyModuleView:
    module_path: str = ""
    module_name: str = ""
    category: str = ""
    status: str = ""
    risk_level: str = ""
    migration_action: str = ""
    clean_equivalent: str | None = None
    reason: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_path": self.module_path,
            "module_name": self.module_name,
            "category": self.category,
            "status": self.status,
            "risk_level": self.risk_level,
            "migration_action": self.migration_action,
            "clean_equivalent": self.clean_equivalent,
            "reason": self.reason,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class MigrationMappingView:
    legacy_module: str = ""
    clean_equivalent: str = ""
    migration_action: str = ""
    confidence: float = 0.0
    blockers_count: int = 0
    required_tests_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "legacy_module": self.legacy_module,
            "clean_equivalent": self.clean_equivalent,
            "migration_action": self.migration_action,
            "confidence": self.confidence,
            "blockers_count": self.blockers_count,
            "required_tests_count": self.required_tests_count,
            "metadata": self.metadata,
        }


@dataclass
class ImportBoundaryFindingView:
    source_file: str = ""
    imported_module: str = ""
    status: str = ""
    severity: str = ""
    message: str = ""
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "imported_module": self.imported_module,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


@dataclass
class MigrationHealthView:
    health: str = "unknown"
    total_legacy_records: int = 0
    deprecated_count: int = 0
    duplicate_count: int = 0
    bypass_risk_count: int = 0
    future_review_count: int = 0
    mapped_count: int = 0
    unmapped_count: int = 0
    blocked_import_count: int = 0
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "total_legacy_records": self.total_legacy_records,
            "deprecated_count": self.deprecated_count,
            "duplicate_count": self.duplicate_count,
            "bypass_risk_count": self.bypass_risk_count,
            "future_review_count": self.future_review_count,
            "mapped_count": self.mapped_count,
            "unmapped_count": self.unmapped_count,
            "blocked_import_count": self.blocked_import_count,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


@dataclass
class MigrationDashboardView:
    generated_at: str = ""
    health: str = "unknown"
    legacy_modules: list[dict[str, Any]] = field(default_factory=list)
    mappings: list[dict[str, Any]] = field(default_factory=list)
    import_findings: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "health": self.health,
            "legacy_modules": self.legacy_modules,
            "mappings": self.mappings,
            "import_findings": self.import_findings,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def legacy_module_to_view(record: Any) -> LegacyModuleView:
    """Convert a LegacyModuleRecord to a view."""
    status = getattr(record, "status", "")
    cat = getattr(record, "category", "")
    risk = getattr(record, "risk_level", "")
    action = getattr(record, "migration_action", "")
    return LegacyModuleView(
        module_path=getattr(record, "module_path", ""),
        module_name=getattr(record, "module_name", ""),
        category=cat.value if hasattr(cat, "value") else str(cat),
        status=status.value if hasattr(status, "value") else str(status),
        risk_level=risk.value if hasattr(risk, "value") else str(risk),
        migration_action=action.value if hasattr(action, "value") else str(action),
        clean_equivalent=getattr(record, "clean_equivalent", None),
        reason=getattr(record, "reason", ""),
        tags=getattr(record, "tags", []),
    )


def migration_mapping_to_view(mapping: Any) -> MigrationMappingView:
    """Convert a MigrationMapping to a view."""
    action = getattr(mapping, "migration_action", "")
    return MigrationMappingView(
        legacy_module=getattr(mapping, "legacy_module", ""),
        clean_equivalent=getattr(mapping, "clean_equivalent", ""),
        migration_action=action.value if hasattr(action, "value") else str(action),
        confidence=getattr(mapping, "confidence", 0.0),
        blockers_count=len(getattr(mapping, "blockers", [])),
        required_tests_count=len(getattr(mapping, "required_tests", [])),
    )


def import_finding_to_view(finding: Any) -> ImportBoundaryFindingView:
    """Convert an ImportBoundaryFinding to a view."""
    status = getattr(finding, "status", "")
    return ImportBoundaryFindingView(
        source_file=getattr(finding, "source_file", ""),
        imported_module=getattr(finding, "imported_module", ""),
        status=status.value if hasattr(status, "value") else str(status),
        severity=getattr(finding, "severity", ""),
        message=getattr(finding, "message", ""),
        recommendation=getattr(finding, "recommendation", ""),
    )


def build_migration_health_view(
    registry: Any | None = None,
    findings: list[Any] | None = None,
) -> MigrationHealthView:
    """Build a health summary from a DeprecationRegistry and import findings."""
    from umh.migration.contracts import ImportBoundaryStatus, LegacyModuleStatus

    if registry is None:
        return MigrationHealthView(health="unknown")

    records = getattr(registry, "_records", [])
    mappings = getattr(registry, "_mappings", [])

    deprecated_count = sum(1 for r in records if r.status == LegacyModuleStatus.DEPRECATED)
    duplicate_count = sum(1 for r in records if r.status == LegacyModuleStatus.DUPLICATE)
    bypass_risk_count = sum(1 for r in records if r.status == LegacyModuleStatus.BYPASS_RISK)
    future_review_count = sum(1 for r in records if r.status == LegacyModuleStatus.FUTURE_REVIEW)
    mapped_count = len(mappings)
    unmapped_legacy = sum(
        1
        for r in records
        if r.status
        in (
            LegacyModuleStatus.FUTURE_REVIEW,
            LegacyModuleStatus.DEPRECATED,
            LegacyModuleStatus.BYPASS_RISK,
            LegacyModuleStatus.DUPLICATE,
        )
        and not r.clean_equivalent
    )

    blocked_import_count = 0
    if findings:
        blocked_import_count = sum(
            1 for f in findings if getattr(f, "status", None) == ImportBoundaryStatus.BLOCKED
        )

    warning_count = bypass_risk_count + blocked_import_count

    if bypass_risk_count == 0 and blocked_import_count == 0:
        health = "healthy"
    elif bypass_risk_count > 10 or blocked_import_count > 20:
        health = "degraded"
    else:
        health = "partial"

    return MigrationHealthView(
        health=health,
        total_legacy_records=len(records),
        deprecated_count=deprecated_count,
        duplicate_count=duplicate_count,
        bypass_risk_count=bypass_risk_count,
        future_review_count=future_review_count,
        mapped_count=mapped_count,
        unmapped_count=unmapped_legacy,
        blocked_import_count=blocked_import_count,
        warning_count=warning_count,
    )


def build_migration_dashboard_view(
    registry: Any | None = None,
    findings: list[Any] | None = None,
    limit: int = 100,
) -> MigrationDashboardView:
    """Build a full migration dashboard view."""
    from umh.migration.contracts import LegacyModuleStatus

    health_view = build_migration_health_view(registry, findings)

    legacy_modules: list[dict[str, Any]] = []
    mappings_views: list[dict[str, Any]] = []
    finding_views: list[dict[str, Any]] = []
    warnings: list[str] = []

    if registry is not None:
        records = getattr(registry, "_records", [])
        legacy_records = [
            r
            for r in records
            if r.status
            in (
                LegacyModuleStatus.FUTURE_REVIEW,
                LegacyModuleStatus.DEPRECATED,
                LegacyModuleStatus.BYPASS_RISK,
                LegacyModuleStatus.DUPLICATE,
            )
        ][:limit]
        legacy_modules = [legacy_module_to_view(r).to_dict() for r in legacy_records]

        registry_mappings = getattr(registry, "_mappings", [])[:limit]
        mappings_views = [migration_mapping_to_view(m).to_dict() for m in registry_mappings]

    if findings:
        finding_views = [import_finding_to_view(f).to_dict() for f in findings[:limit]]

    if health_view.bypass_risk_count > 0:
        warnings.append(f"{health_view.bypass_risk_count} bypass-risk modules detected")
    if health_view.blocked_import_count > 0:
        warnings.append(f"{health_view.blocked_import_count} blocked import boundary violations")

    return MigrationDashboardView(
        generated_at=_iso_now(),
        health=health_view.health,
        legacy_modules=legacy_modules,
        mappings=mappings_views,
        import_findings=finding_views,
        warnings=warnings,
    )
