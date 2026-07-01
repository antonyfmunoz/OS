#!/usr/bin/env python3
"""Pre-commit gate: blocks commits introducing ungoverned mutation endpoints.

After C34, every POST/PUT/PATCH/DELETE handler in transports/api/ must route
through governed_mutation() (Python) or governedMutation() (TypeScript).
Direct state mutations that bypass the GovernedExecutionSpine are illegal.

Exit codes:
  0 — clean, all mutations governed
  1 — ungoverned mutation detected, commit blocked

Usage:
  python3 scripts/check_ungoverned_mutations.py           # check staged files
  python3 scripts/check_ungoverned_mutations.py --all      # scan full codebase
  python3 scripts/check_ungoverned_mutations.py --file X   # check specific file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ROUTE_DIRS = [
    "transports/api/",
    "saas/",
    "services/",
]

GOVERNED_PATTERNS_PY = [
    re.compile(r"governed_mutation\s*\("),
    re.compile(r"from\s+transports\.api\.governed\s+import"),
]

GOVERNED_PATTERNS_TS = [
    re.compile(r"governedMutation\s*\("),
    re.compile(r"from\s+['\"].*governed_bridge['\"]"),
]

MUTATION_ROUTE_DECORATOR_PY = re.compile(
    r"""@\w+\.(post|put|patch|delete)\s*\(""",
    re.IGNORECASE | re.VERBOSE,
)

MUTATION_METHOD_IN_ADD_ROUTE = re.compile(
    r"""methods\s*=\s*\[\s*"(POST|PUT|PATCH|DELETE)""",
    re.IGNORECASE,
)

DIRECT_SQL_WRITE = re.compile(
    r"""cur\.execute\s*\(\s*["']{1,3}\s*(INSERT|UPDATE|DELETE|ALTER|DROP)""",
    re.IGNORECASE,
)

MUTATION_ROUTE_TS = re.compile(
    r"""\.(post|put|patch|delete)\s*\(""",
    re.IGNORECASE,
)

EXEMPT_FILES = {
    "transports/api/governed.py",
    "transports/api/http/lib/governed_bridge.ts",
    "transports/api/cockpit_spine_router.py",
}

GRANDFATHERED_FILES: set[str] = {
    "services/goal_api.py",
    "services/higgsfield_webhook.py",
}


def _is_route_file(path: str) -> bool:
    return any(path.startswith(d) for d in ROUTE_DIRS)


def _is_exempt(path: str) -> bool:
    return path in EXEMPT_FILES or path in GRANDFATHERED_FILES


def _check_python_file(filepath: Path) -> list[str]:
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    lines = content.splitlines()
    has_mutation_route = False
    has_governed_import = False
    has_direct_sql_write = False

    for line in lines:
        if MUTATION_ROUTE_DECORATOR_PY.search(line):
            has_mutation_route = True
        if MUTATION_METHOD_IN_ADD_ROUTE.search(line):
            has_mutation_route = True
        if DIRECT_SQL_WRITE.search(line):
            has_direct_sql_write = True
        for pat in GOVERNED_PATTERNS_PY:
            if pat.search(line):
                has_governed_import = True
                break

    if has_mutation_route and not has_governed_import:
        for i, line in enumerate(lines, 1):
            if MUTATION_ROUTE_DECORATOR_PY.search(line) or MUTATION_METHOD_IN_ADD_ROUTE.search(line):
                violations.append(
                    f"  {filepath}:{i} — mutation route without governed_mutation()"
                )

    if has_direct_sql_write and not has_governed_import:
        for i, line in enumerate(lines, 1):
            if DIRECT_SQL_WRITE.search(line):
                violations.append(
                    f"  {filepath}:{i} — direct SQL write without governed_mutation()"
                )

    return violations


def _check_ts_file(filepath: Path) -> list[str]:
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    lines = content.splitlines()
    has_mutation_route = False
    has_governed_import = False

    for line in lines:
        if MUTATION_ROUTE_TS.search(line):
            has_mutation_route = True
        for pat in GOVERNED_PATTERNS_TS:
            if pat.search(line):
                has_governed_import = True
                break

    if has_mutation_route and not has_governed_import:
        for i, line in enumerate(lines, 1):
            if MUTATION_ROUTE_TS.search(line):
                violations.append(
                    f"  {filepath}:{i} — mutation route without governedMutation()"
                )

    return violations


def _get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def _get_all_route_files() -> list[str]:
    files = []
    for route_dir in ROUTE_DIRS:
        dirpath = REPO_ROOT / route_dir
        if dirpath.exists():
            for fp in dirpath.rglob("*"):
                if fp.suffix in (".py", ".ts") and fp.is_file():
                    files.append(str(fp.relative_to(REPO_ROOT)))
    return files


def main() -> int:
    if "--all" in sys.argv:
        candidates = _get_all_route_files()
    elif "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            candidates = [sys.argv[idx + 1]]
        else:
            print("ERROR: --file requires a path argument", file=sys.stderr)
            return 1
    else:
        staged = _get_staged_files()
        candidates = [f for f in staged if _is_route_file(f)]

    if not candidates:
        return 0

    all_violations: list[str] = []
    checked = 0

    for rel_path in candidates:
        if _is_exempt(rel_path):
            continue

        filepath = REPO_ROOT / rel_path
        if not filepath.exists():
            continue

        checked += 1
        if filepath.suffix == ".py":
            all_violations.extend(_check_python_file(filepath))
        elif filepath.suffix == ".ts":
            all_violations.extend(_check_ts_file(filepath))

    if all_violations:
        print(f"Ungoverned Mutation Gate: {len(all_violations)} violations in {checked} files")
        print()
        for v in all_violations:
            print(v)
        print()
        print("Fix: import governed_mutation() from transports.api.governed")
        print("     and route all mutations through it.")
        print()
        print("See CLAUDE.md C34 Canonical Mutation Law for details.")
        return 1

    scanned_label = f"{checked} files scanned" if checked else "no route files in commit"
    print(f"Ungoverned Mutation Gate: {scanned_label} — clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
