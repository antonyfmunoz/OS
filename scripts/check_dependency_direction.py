#!/usr/bin/env python3
"""Pre-commit gate: blocks commits that violate UMH architecture dependency direction.

The four-layer architecture has strict one-way dependency flow:

    projections/saas  →  transports  →  adapters  →  substrate

Each layer may only import from layers below it. Never upward. Never sideways
between peers at the same level (e.g., substrate/ importing from services/).

Additionally:
  - saas/ (EOS projection) must not contain UMH platform infrastructure
  - substrate/ must not import from transports/, services/, projections/, saas/
  - transports/ must not import from projections/ or saas/

Exit codes:
  0 — clean, dependency direction respected
  1 — violation detected, commit blocked

Usage:
  python3 scripts/check_dependency_direction.py           # check staged files
  python3 scripts/check_dependency_direction.py --all      # scan full codebase
  python3 scripts/check_dependency_direction.py --file X   # check specific file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Forbidden Import Rules ────────────────────────────────────────────────────
# (source_dir_prefix, forbidden_import_pattern, category, fix_message)

IMPORT_RULES: list[tuple[str, str, str, str]] = [
    # substrate/ must never import from upper layers
    ("substrate/", r"^\s*from\s+transports\b", "substrate_imports_transport",
     "substrate/ cannot import from transports/ — use an abstract port in substrate/sockets/"),
    ("substrate/", r"^\s*from\s+services\b", "substrate_imports_services",
     "substrate/ cannot import from services/ — use an abstract port in substrate/sockets/"),
    ("substrate/", r"^\s*from\s+projections\b", "substrate_imports_projections",
     "substrate/ cannot import from projections/"),
    ("substrate/", r"^\s*import\s+transports\b", "substrate_imports_transport",
     "substrate/ cannot import from transports/ — use an abstract port in substrate/sockets/"),
    ("substrate/", r"^\s*import\s+services\b", "substrate_imports_services",
     "substrate/ cannot import from services/ — use an abstract port in substrate/sockets/"),

    # adapters/ must not import from upper layers
    ("adapters/", r"^\s*from\s+transports\b", "adapters_imports_transport",
     "adapters/ cannot import from transports/"),
    ("adapters/", r"^\s*from\s+services\b", "adapters_imports_services",
     "adapters/ cannot import from services/"),
    ("adapters/", r"^\s*from\s+projections\b", "adapters_imports_projections",
     "adapters/ cannot import from projections/"),

    # transports/ must not import from projection layer
    ("transports/", r"^\s*from\s+projections\b", "transport_imports_projections",
     "transports/ cannot import from projections/"),
]

# ── Files grandfathered for existing violations ───────────────────────────────
# Each entry: relative path from repo root.
# These are tech debt — each should be migrated to use abstract ports.
# Added 2026-05-28 during SaaS layer separation.
LEGACY_VIOLATIONS: set[str] = {
    # substrate/ → projections/ (uses lazy import, should use projection_port)
    "substrate/integrations/product_connections.py",
    # substrate/organism/tests/ → transports/ (integration tests, cross boundary by design)
    "substrate/organism/tests/test_phase62_spine_enforcement.py",
    "substrate/organism/tests/test_phase92_self_improvement.py",
    "substrate/organism/tests/test_report_dispatcher.py",
    # adapters/ → transports/ (webhook post, should use notification_port)
    "adapters/google_workspace/gws_scanner.py",
    # transports/ → projections/ (EOS-specific cockpit views, needs projection port)
    "transports/api/app.py",
    "transports/api/cockpit.py",
    # EOS analytics route calls organism bridge (should be split into UMH + EOS parts)
    "saas/api/routes/analytics.ts",
}

# ── Infrastructure-in-projection detector ─────────────────────────────────────
# Patterns that indicate UMH infrastructure landed in saas/ (EOS projection).
# These check file paths, not import statements.

INFRA_IN_PROJECTION_DIRS: list[tuple[str, str]] = [
    ("saas/bridge/", "Python bridges belong in transports/api/, not in saas/"),
    ("saas/api/middleware/", "Auth middleware belongs in transports/api/http/middleware/"),
    ("saas/api/lib/python_bridge", "Bridge spawner belongs in transports/api/http/lib/"),
]

INFRA_ROUTE_PATTERNS: list[tuple[str, str]] = [
    (r"callOrganism\(", "Organism bridge calls belong in transports/api/http/routes/, not saas/"),
    (r"organism\.(snapshot|status|health|governor|supervisor|workcells|runtimes)",
     "Organism route handlers belong in transports/api/http/routes/organism.ts"),
]


def _get_staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return [REPO_ROOT / f for f in result.stdout.strip().split("\n") if f]


def _get_all_files() -> list[Path]:
    py_files = list(REPO_ROOT.glob("substrate/**/*.py"))
    py_files += list(REPO_ROOT.glob("adapters/**/*.py"))
    py_files += list(REPO_ROOT.glob("transports/**/*.py"))
    py_files += list(REPO_ROOT.glob("transports/**/*.ts"))
    py_files += list(REPO_ROOT.glob("saas/**/*.py"))
    py_files += list(REPO_ROOT.glob("saas/**/*.ts"))
    return [f for f in py_files if "__pycache__" not in str(f) and "node_modules" not in str(f)]


def _check_file(filepath: Path) -> list[tuple[str, int, str, str]]:
    violations: list[tuple[str, int, str, str]] = []
    rel = str(filepath.relative_to(REPO_ROOT))

    if rel in LEGACY_VIOLATIONS:
        return []

    # Check import direction violations (Python files only)
    if filepath.suffix == ".py":
        try:
            content = filepath.read_text(errors="replace")
            lines = content.splitlines()
        except OSError:
            return []

        in_docstring = False
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # Track triple-quoted docstrings
            triple_count = stripped.count('"""') + stripped.count("'''")
            if triple_count == 1:
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            for src_prefix, pattern, category, fix in IMPORT_RULES:
                if rel.startswith(src_prefix) and re.search(pattern, line):
                    violations.append((category, line_num, stripped, fix))

    # Check infrastructure-in-projection (file path based)
    for dir_pattern, fix in INFRA_IN_PROJECTION_DIRS:
        if rel.startswith(dir_pattern):
            violations.append(("infra_in_projection", 0, rel, fix))

    # Check infrastructure route patterns in saas/ TypeScript
    if rel.startswith("saas/api/routes/") and filepath.suffix == ".ts":
        try:
            lines = filepath.read_text(errors="replace").splitlines()
        except OSError:
            return []

        for line_num, line in enumerate(lines, 1):
            for pattern, fix in INFRA_ROUTE_PATTERNS:
                if re.search(pattern, line):
                    violations.append(("infra_route_in_projection", line_num, line.strip(), fix))

    return violations


def main() -> int:
    mode = "staged"
    target_file = None

    if "--all" in sys.argv:
        mode = "all"
    elif "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            target_file = Path(sys.argv[idx + 1])
            mode = "file"

    if mode == "staged":
        files = _get_staged_files()
        files = [f for f in files if f.suffix in (".py", ".ts")]
    elif mode == "all":
        files = _get_all_files()
    elif mode == "file" and target_file:
        files = [REPO_ROOT / target_file if not target_file.is_absolute() else target_file]
    else:
        files = []

    if not files:
        return 0

    all_violations: dict[str, list[tuple[str, int, str, str]]] = {}

    for filepath in files:
        if not filepath.exists():
            continue
        violations = _check_file(filepath)
        if violations:
            rel = str(filepath.relative_to(REPO_ROOT))
            all_violations[rel] = violations

    if not all_violations:
        total = len(files)
        label = "full scan" if mode == "all" else "staged"
        print(f"Dependency Direction Gate: {total} files scanned — clean")
        if LEGACY_VIOLATIONS:
            print(f"  Legacy violations grandfathered: {len(LEGACY_VIOLATIONS)} files (tech debt)")
        return 0

    # Report violations
    total_count = sum(len(v) for v in all_violations.values())
    print("=" * 72)
    print("DEPENDENCY DIRECTION VIOLATION BLOCKED")
    print("=" * 72)
    print()
    print("Architecture layers have strict one-way dependency flow:")
    print("  projections/saas  →  transports  →  adapters  →  substrate")
    print()
    print(f"Scanned: {'full scan' if mode == 'all' else 'staged'} ({len(files)} files)")
    print(f"Violations: {total_count}")
    print()

    by_category: dict[str, list[tuple[str, int, str, str]]] = {}
    for filepath, violations in all_violations.items():
        for cat, line_num, text, fix in violations:
            by_category.setdefault(cat, []).append((filepath, line_num, text, fix))

    for category, entries in sorted(by_category.items()):
        print(f"── {category} ({len(entries)} violations) ──")
        for filepath, line_num, text, fix in entries:
            loc = f"{filepath}:{line_num}" if line_num else filepath
            print(f"  {loc}")
            print(f"    {text[:100]}")
            print(f"    → Fix: {fix}")
        print()

    print("=" * 72)
    print("How to fix:")
    print("  1. Move the code to the correct architectural layer")
    print("  2. Use abstract ports (substrate/sockets/) for cross-layer communication")
    print("  3. If this is a genuine legacy violation, add to LEGACY_VIOLATIONS")
    print("     in scripts/check_dependency_direction.py with justification")
    print("=" * 72)

    return 1


if __name__ == "__main__":
    sys.exit(main())
