#!/usr/bin/env python3
"""Pre-commit gate: block raw subprocess usage in substrate/ and organism/.

All subprocess calls in UMH substrate code must use the gated wrappers:
  - substrate.execution.cpu_gate.gated_subprocess_run
  - substrate.execution.cpu_gate.gated_popen

This prevents any code path from spawning processes without CPU load awareness.
Raw subprocess.run/Popen/call/check_output are only allowed in:
  - substrate/execution/cpu_gate.py itself (the gate implementation)
  - test files
  - scripts/ (which use cron-run wrapper instead)

Usage:
  python3 scripts/check_cpu_gate.py          # check staged files
  python3 scripts/check_cpu_gate.py --all    # full codebase scan
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

GATED_DIRS = [
    "substrate/",
    "adapters/",
    "transports/",
    "services/",
]

EXEMPT_FILES = {
    "substrate/execution/cpu_gate.py",
    "adapters/models/cc_sdk.py",
}

EXEMPT_PATTERNS = [
    "/tests/",
    "/test_",
    "__pycache__",
]

RAW_SUBPROCESS_RE = re.compile(
    r"(?<!gated_)subprocess\.(run|Popen|call|check_output|check_call)\s*\(",
)


def get_staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return [REPO_ROOT / f.strip() for f in result.stdout.splitlines() if f.strip().endswith(".py")]


def get_all_files() -> list[Path]:
    files = []
    for gated_dir in GATED_DIRS:
        dir_path = REPO_ROOT / gated_dir
        if dir_path.exists():
            files.extend(dir_path.rglob("*.py"))
    return files


def is_exempt(path: Path) -> bool:
    rel = str(path.relative_to(REPO_ROOT))
    if rel in EXEMPT_FILES:
        return True
    for pattern in EXEMPT_PATTERNS:
        if pattern in rel:
            return True
    return False


def check_file(path: Path) -> list[str]:
    violations = []
    rel = str(path.relative_to(REPO_ROOT))

    # Only check files in gated directories
    in_gated = any(rel.startswith(d) for d in GATED_DIRS)
    if not in_gated:
        return []

    if is_exempt(path):
        return []

    try:
        content = path.read_text()
    except Exception:
        return []

    for i, line in enumerate(content.splitlines(), 1):
        # Skip comments and string literals (rough heuristic)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        if RAW_SUBPROCESS_RE.search(line):
            violations.append(f"  {rel}:{i}: raw subprocess call — use gated_subprocess_run() or gated_popen()")

    return violations


def main() -> int:
    scan_all = "--all" in sys.argv

    if scan_all:
        files = get_all_files()
    else:
        files = get_staged_files()
        # Filter to gated dirs
        files = [f for f in files if any(
            str(f.relative_to(REPO_ROOT)).startswith(d) for d in GATED_DIRS
        )]

    if not files:
        return 0

    all_violations = []
    for f in files:
        if f.exists():
            all_violations.extend(check_file(f))

    if all_violations:
        print("CPU Gate Violation: raw subprocess calls found")
        print("Use gated_subprocess_run() or gated_popen() from substrate.execution.cpu_gate")
        print()
        for v in all_violations:
            print(v)
        print()
        print(f"Total: {len(all_violations)} violations")

        if scan_all:
            # In --all mode, report but don't fail (legacy code)
            print("\n(Legacy violations — migrate incrementally)")
            return 0
        return 1

    if scan_all:
        print(f"CPU Gate: {len(files)} files scanned — clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
