"""Phase 83 deprecation registry — typed in-memory registry for migration state.

Maintains a queryable collection of LegacyModuleRecords and MigrationMappings.
No deletion. No automatic source modification. No execution.
"""

from __future__ import annotations

from typing import Any

from umh.migration.contracts import (
    LegacyModuleCategory,
    LegacyModuleRecord,
    LegacyModuleStatus,
    MigrationAction,
    MigrationMapping,
    MigrationRiskLevel,
)


class DeprecationRegistry:
    """In-memory registry of legacy module records and migration mappings."""

    def __init__(self) -> None:
        self._records: list[LegacyModuleRecord] = []
        self._by_path: dict[str, LegacyModuleRecord] = {}
        self._by_name: dict[str, LegacyModuleRecord] = {}
        self._mappings: list[MigrationMapping] = []

    def register_record(self, record: LegacyModuleRecord) -> None:
        self._records.append(record)
        self._by_path[record.module_path] = record
        self._by_name[record.module_name] = record

    def register_many(self, records: list[LegacyModuleRecord]) -> None:
        for r in records:
            self.register_record(r)

    def register_mapping(self, mapping: MigrationMapping) -> None:
        self._mappings.append(mapping)

    def get_record(self, module_path_or_name: str) -> LegacyModuleRecord | None:
        rec = self._by_path.get(module_path_or_name)
        if rec is not None:
            return rec
        return self._by_name.get(module_path_or_name)

    def query(
        self,
        *,
        status: LegacyModuleStatus | None = None,
        category: LegacyModuleCategory | None = None,
        risk_level: MigrationRiskLevel | None = None,
        action: MigrationAction | None = None,
        limit: int = 100,
    ) -> list[LegacyModuleRecord]:
        results = list(self._records)
        if status is not None:
            results = [r for r in results if r.status == status]
        if category is not None:
            results = [r for r in results if r.category == category]
        if risk_level is not None:
            results = [r for r in results if r.risk_level == risk_level]
        if action is not None:
            results = [r for r in results if r.migration_action == action]
        return results[:limit]

    def list_deprecated(self, limit: int = 100) -> list[LegacyModuleRecord]:
        return self.query(status=LegacyModuleStatus.DEPRECATED, limit=limit)

    def list_bypass_risk(self, limit: int = 100) -> list[LegacyModuleRecord]:
        return self.query(status=LegacyModuleStatus.BYPASS_RISK, limit=limit)

    def list_future_review(self, limit: int = 100) -> list[LegacyModuleRecord]:
        return self.query(status=LegacyModuleStatus.FUTURE_REVIEW, limit=limit)

    def list_mappings(self, limit: int = 100) -> list[MigrationMapping]:
        return self._mappings[:limit]

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def mapping_count(self) -> int:
        return len(self._mappings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [r.to_dict() for r in self._records],
            "mappings": [m.to_dict() for m in self._mappings],
            "record_count": len(self._records),
            "mapping_count": len(self._mappings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeprecationRegistry:
        registry = cls()
        for r_data in data.get("records", []):
            registry.register_record(LegacyModuleRecord.from_dict(r_data))
        for m_data in data.get("mappings", []):
            registry.register_mapping(MigrationMapping.from_dict(m_data))
        return registry


def build_default_deprecation_registry(root_path: str = "/opt/OS") -> DeprecationRegistry:
    """Build a deprecation registry from static inventory discovery."""
    from umh.migration.inventory import build_legacy_inventory

    inventory = build_legacy_inventory(root_path)
    return build_registry_from_inventory(inventory)


def build_registry_from_inventory(
    inventory: Any,
) -> DeprecationRegistry:
    """Build a registry from an existing MigrationInventory."""
    registry = DeprecationRegistry()
    records = getattr(inventory, "records", [])
    registry.register_many(records)
    mappings = getattr(inventory, "mappings", [])
    for m in mappings:
        registry.register_mapping(m)
    return registry


def get_clean_equivalent_candidates(record: LegacyModuleRecord) -> list[str]:
    """Return possible clean equivalents for a legacy record."""
    if record.clean_equivalent:
        return [record.clean_equivalent]
    from umh.migration.classifier import detect_duplicate_concept

    equiv = detect_duplicate_concept(record.module_path)
    if equiv:
        return [equiv]
    return []


def explain_deprecation_status(record: LegacyModuleRecord) -> str:
    """Human-readable explanation of a record's deprecation status."""
    parts: list[str] = [
        f"{record.module_name}: status={record.status.value}, risk={record.risk_level.value}"
    ]
    if record.reason:
        parts.append(f"  reason: {record.reason}")
    if record.clean_equivalent:
        parts.append(f"  clean equivalent: {record.clean_equivalent}")
    if record.evidence:
        parts.append(f"  evidence: {len(record.evidence)} findings")
    parts.append(f"  recommended action: {record.migration_action.value}")
    return "\n".join(parts)
