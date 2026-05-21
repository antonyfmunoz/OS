"""Phase 83 import boundary — prevents clean modules from depending on deprecated paths.

Uses AST-based import parsing. No dynamic module imports. No subprocess.
Findings only — no automatic blocking at runtime.
"""

from __future__ import annotations

import ast
import os
from typing import Any

from umh.migration.contracts import (
    ImportBoundaryFinding,
    ImportBoundaryRule,
    ImportBoundaryStatus,
)


def build_default_import_boundary_rules() -> list[ImportBoundaryRule]:
    """Build the default set of import boundary rules."""
    rules: list[ImportBoundaryRule] = []

    clean_packages = [
        "umh/control",
        "umh/execution",
        "umh/adapters",
        "umh/storage",
        "umh/memory",
        "umh/registry",
        "umh/ontology",
        "umh/observability",
        "umh/interface",
    ]

    for pkg in clean_packages:
        rules.append(
            ImportBoundaryRule(
                rule_id=f"ibr_{pkg.replace('/', '_')}_no_runtime_engine",
                source_pattern=pkg,
                forbidden_import_pattern="umh.runtime_engine",
                status=ImportBoundaryStatus.BLOCKED,
                reason=f"Clean package {pkg} should not import runtime_engine",
            )
        )

    exec_substrate_sources = ["umh/control", "umh/execution", "umh/adapters"]
    for pkg in exec_substrate_sources:
        rules.append(
            ImportBoundaryRule(
                rule_id=f"ibr_{pkg.replace('/', '_')}_no_substrate_workers",
                source_pattern=pkg,
                forbidden_import_pattern="umh.substrate",
                allowed_exceptions=["umh.substrate.nodes"],
                status=ImportBoundaryStatus.BLOCKED,
                reason=f"Clean package {pkg} should not import substrate directly",
            )
        )

    return rules


def parse_imports_from_file(file_path: str) -> list[str]:
    """Parse import statements from a Python file using AST. No module execution."""
    if not os.path.isfile(file_path):
        return []
    try:
        with open(file_path, "r", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except (SyntaxError, Exception):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def classify_import_boundary(
    source_file: str,
    imported_module: str,
    rules: list[ImportBoundaryRule] | None = None,
) -> ImportBoundaryStatus:
    """Classify whether a particular import is allowed by boundary rules."""
    if rules is None:
        rules = build_default_import_boundary_rules()

    source_normalized = source_file.replace("\\", "/")

    for rule in rules:
        if rule.source_pattern not in source_normalized:
            continue
        if not imported_module.startswith(rule.forbidden_import_pattern):
            continue
        for exc in rule.allowed_exceptions:
            if imported_module.startswith(exc):
                return ImportBoundaryStatus.COMPATIBILITY_ALLOWED
        return rule.status

    return ImportBoundaryStatus.ALLOWED


def is_import_allowed(
    source_file: str,
    imported_module: str,
    rules: list[ImportBoundaryRule] | None = None,
) -> bool:
    """Check if an import is allowed by boundary rules."""
    status = classify_import_boundary(source_file, imported_module, rules)
    return status in (ImportBoundaryStatus.ALLOWED, ImportBoundaryStatus.COMPATIBILITY_ALLOWED)


def scan_import_boundaries(
    root_path: str = "/opt/OS/umh",
    rules: list[ImportBoundaryRule] | None = None,
    include_tests: bool = False,
) -> list[ImportBoundaryFinding]:
    """Scan all Python files for import boundary violations."""
    if rules is None:
        rules = build_default_import_boundary_rules()

    if not os.path.isdir(root_path):
        return []

    findings: list[ImportBoundaryFinding] = []

    for dirpath, _dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, os.path.dirname(root_path))
        if "__pycache__" in rel_dir:
            continue
        if not include_tests and rel_dir.startswith("tests"):
            continue
        if "migration" in rel_dir:
            continue

        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.join(rel_dir, fname).replace("\\", "/")

            imports = parse_imports_from_file(full_path)
            for imp in imports:
                status = classify_import_boundary(rel_path, imp, rules)
                if status in (ImportBoundaryStatus.BLOCKED, ImportBoundaryStatus.DEPRECATED_IMPORT):
                    matching_rule = None
                    for rule in rules:
                        if rule.source_pattern in rel_path and imp.startswith(
                            rule.forbidden_import_pattern
                        ):
                            matching_rule = rule
                            break

                    findings.append(
                        ImportBoundaryFinding(
                            source_file=rel_path,
                            imported_module=imp,
                            status=status,
                            rule_id=matching_rule.rule_id if matching_rule else None,
                            severity="warning",
                            message=f"{rel_path} imports {imp}",
                            recommendation=f"Migrate import from {imp} to clean equivalent",
                        )
                    )

    return findings


def import_boundary_findings_to_report(findings: list[ImportBoundaryFinding]) -> dict[str, Any]:
    """Summarize import boundary findings."""
    blocked = [f for f in findings if f.status == ImportBoundaryStatus.BLOCKED]
    deprecated = [f for f in findings if f.status == ImportBoundaryStatus.DEPRECATED_IMPORT]

    by_source: dict[str, int] = {}
    for f in findings:
        by_source[f.source_file] = by_source.get(f.source_file, 0) + 1

    return {
        "total_findings": len(findings),
        "blocked_count": len(blocked),
        "deprecated_import_count": len(deprecated),
        "affected_files": len(by_source),
        "top_offenders": sorted(by_source.items(), key=lambda x: -x[1])[:10],
        "findings": [f.to_dict() for f in findings],
    }
