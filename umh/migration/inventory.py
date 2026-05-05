"""Phase 83 legacy inventory — static file discovery and module classification.

Discovers Python modules under umh/ and classifies them by category.
No dynamic imports. No subprocess. No deletion. Safe if directories missing.
"""

from __future__ import annotations

import json
import os
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.migration.contracts import (
    LegacyModuleCategory,
    LegacyModuleRecord,
    LegacyModuleStatus,
    MigrationAction,
    MigrationInventory,
    MigrationRiskLevel,
)


_CATEGORY_PREFIXES: list[tuple[str, LegacyModuleCategory]] = [
    ("umh/runtime_engine/", LegacyModuleCategory.RUNTIME_ENGINE),
    ("umh/substrate/", LegacyModuleCategory.SUBSTRATE),
    ("umh/runtime/", LegacyModuleCategory.RUNTIME_INTELLIGENCE),
    ("umh/execution/", LegacyModuleCategory.EXECUTION),
    ("umh/governance/", LegacyModuleCategory.GOVERNANCE),
    ("umh/storage/", LegacyModuleCategory.STORAGE),
    ("umh/memory/", LegacyModuleCategory.MEMORY),
    ("umh/control/", LegacyModuleCategory.CONTROL),
    ("umh/adapters/", LegacyModuleCategory.ADAPTER),
    ("umh/observability/", LegacyModuleCategory.OBSERVABILITY),
    ("umh/interface/", LegacyModuleCategory.INTERFACE),
    ("umh/registry/", LegacyModuleCategory.REGISTRY),
    ("umh/ontology/", LegacyModuleCategory.ONTOLOGY),
    ("tests/", LegacyModuleCategory.TEST),
    ("docs/", LegacyModuleCategory.DOCS),
]

_CLEAN_CATEGORIES: frozenset[LegacyModuleCategory] = frozenset(
    {
        LegacyModuleCategory.EXECUTION,
        LegacyModuleCategory.GOVERNANCE,
        LegacyModuleCategory.STORAGE,
        LegacyModuleCategory.MEMORY,
        LegacyModuleCategory.CONTROL,
        LegacyModuleCategory.ADAPTER,
        LegacyModuleCategory.OBSERVABILITY,
        LegacyModuleCategory.INTERFACE,
        LegacyModuleCategory.REGISTRY,
        LegacyModuleCategory.ONTOLOGY,
    }
)


def module_path_to_module_name(path: str) -> str:
    """Convert a file path to a dotted module name."""
    path = path.replace("\\", "/")
    if path.endswith(".py"):
        path = path[:-3]
    if path.endswith("/__init__"):
        path = path[: -len("/__init__")]
    return path.replace("/", ".")


def classify_module_path(path: str) -> LegacyModuleCategory:
    """Classify a module path into a category based on its directory prefix."""
    path = path.replace("\\", "/")
    for prefix, category in _CATEGORY_PREFIXES:
        if prefix in path:
            return category
    return LegacyModuleCategory.UNKNOWN


def _default_status_for_category(category: LegacyModuleCategory) -> LegacyModuleStatus:
    if category in _CLEAN_CATEGORIES:
        return LegacyModuleStatus.ACTIVE_RETAINED
    if category == LegacyModuleCategory.RUNTIME_ENGINE:
        return LegacyModuleStatus.FUTURE_REVIEW
    if category == LegacyModuleCategory.SUBSTRATE:
        return LegacyModuleStatus.FUTURE_REVIEW
    if category == LegacyModuleCategory.RUNTIME_INTELLIGENCE:
        return LegacyModuleStatus.ACTIVE_RETAINED
    return LegacyModuleStatus.UNKNOWN


def _default_risk_for_category(category: LegacyModuleCategory) -> MigrationRiskLevel:
    if category in _CLEAN_CATEGORIES:
        return MigrationRiskLevel.NONE
    if category == LegacyModuleCategory.RUNTIME_ENGINE:
        return MigrationRiskLevel.MEDIUM
    if category == LegacyModuleCategory.SUBSTRATE:
        return MigrationRiskLevel.MEDIUM
    if category == LegacyModuleCategory.RUNTIME_INTELLIGENCE:
        return MigrationRiskLevel.LOW
    return MigrationRiskLevel.UNKNOWN


def _default_action_for_category(category: LegacyModuleCategory) -> MigrationAction:
    if category in _CLEAN_CATEGORIES:
        return MigrationAction.RETAIN
    if category == LegacyModuleCategory.RUNTIME_ENGINE:
        return MigrationAction.REVIEW_MANUALLY
    if category == LegacyModuleCategory.SUBSTRATE:
        return MigrationAction.REVIEW_MANUALLY
    if category == LegacyModuleCategory.RUNTIME_INTELLIGENCE:
        return MigrationAction.RETAIN
    return MigrationAction.UNKNOWN


def discover_python_modules(
    root_path: str = "/opt/OS/umh",
    include_tests: bool = False,
) -> list[str]:
    """Discover .py files under root_path. Safe if directory missing."""
    if not os.path.isdir(root_path):
        return []

    results: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, os.path.dirname(root_path))
        if "__pycache__" in rel_dir:
            continue
        if not include_tests and rel_dir.startswith("tests"):
            continue
        for fname in sorted(filenames):
            if fname.endswith(".py"):
                rel_path = os.path.join(rel_dir, fname).replace("\\", "/")
                results.append(rel_path)
    return results


def _build_record_from_path(rel_path: str) -> LegacyModuleRecord:
    category = classify_module_path(rel_path)
    return LegacyModuleRecord(
        module_path=rel_path,
        module_name=module_path_to_module_name(rel_path),
        category=category,
        status=_default_status_for_category(category),
        risk_level=_default_risk_for_category(category),
        migration_action=_default_action_for_category(category),
        source="phase83_static_discovery",
        tags=[category.value],
    )


def build_legacy_inventory(root_path: str = "/opt/OS") -> MigrationInventory:
    """Build a full inventory of legacy and clean modules under umh/."""
    umh_root = os.path.join(root_path, "umh")
    paths = discover_python_modules(umh_root)
    records = [_build_record_from_path(p) for p in paths]
    warnings: list[str] = []

    if not os.path.isdir(os.path.join(umh_root, "runtime_engine")):
        warnings.append("umh/runtime_engine/ directory not found — degrading safely")
    if not os.path.isdir(os.path.join(umh_root, "substrate")):
        warnings.append("umh/substrate/ directory not found — degrading safely")

    return MigrationInventory(
        generated_at=_iso_now(),
        root_path=root_path,
        records=records,
        warnings=warnings,
    )


def read_existing_module_inventory(
    path: str = "/opt/OS/docs/system/module_inventory.json",
) -> list[dict[str, Any]]:
    """Read pre-existing Phase 75A module inventory. Safe if missing."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def read_existing_dependency_graph(
    path: str = "/opt/OS/docs/system/dependency_graph.md",
) -> str:
    """Read pre-existing dependency graph. Safe if missing."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return ""


def read_existing_deprecation_plan(
    path: str = "/opt/OS/docs/system/deprecation_plan.md",
) -> str:
    """Read pre-existing deprecation plan. Safe if missing."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return ""


def summarize_inventory(records: list[LegacyModuleRecord]) -> dict[str, Any]:
    """Produce a summary of module classifications."""
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_risk: dict[str, int] = {}

    for r in records:
        by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        by_category[r.category.value] = by_category.get(r.category.value, 0) + 1
        by_risk[r.risk_level.value] = by_risk.get(r.risk_level.value, 0) + 1

    return {
        "total": len(records),
        "by_status": by_status,
        "by_category": by_category,
        "by_risk": by_risk,
    }
