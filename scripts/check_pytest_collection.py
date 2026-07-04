#!/usr/bin/env python3
"""Pre-commit gate: blocks commits that break pytest collection.

pytest collection walks every test module and imports it. A single stale
symbol import (a test importing a name that a substrate module renamed or
removed) turns the whole `pytest --collect-only` run INTERRUPTED, which means
CI can no longer even enumerate the suite. This has happened three times
(WP-P0-011): tests importing `ExecutionMode`, `OutcomeRecord`, and
`SessionStatus` after those symbols were renamed in substrate.

This gate runs `pytest --collect-only` and blocks the commit if collection
reports any errors. It does NOT run the tests — only that every test module
imports and collects cleanly.

Scope:
  - When a test file (tests/**/*.py) or any imported substrate/adapters/
    transports Python file is staged, collection can break, so the gate runs.
  - When no such file is staged, the gate is a no-op (fast exit) so unrelated
    commits are not slowed by a full collection pass.
  - `--all` forces a full collection pass regardless of staged files.

Exit codes:
  0 — collection clean (or no relevant files staged)
  1 — collection reported errors, commit blocked

Usage:
  python3 scripts/check_pytest_collection.py           # gate on staged files
  python3 scripts/check_pytest_collection.py --all      # always run collection

UMH platform gate. Domain-agnostic.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Staging any Python file under these prefixes can break test collection:
# tests/ obviously, and the layers tests import from (a rename there is what
# strands a stale test import). Non-Python and doc-only changes are skipped.
_RELEVANT_PREFIXES = (
    "tests/",
    "substrate/",
    "adapters/",
    "transports/",
    "projections/",
    "saas/",
    "nodes/",
)


def _get_staged_files() -> list[str]:
    """Return staged (added/copied/modified/renamed) file paths."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return [line for line in result.stdout.strip().splitlines() if line]


def _has_relevant_change(staged: list[str]) -> bool:
    """True if any staged file could affect pytest collection."""
    for name in staged:
        if not name.endswith(".py"):
            continue
        if any(name.startswith(prefix) for prefix in _RELEVANT_PREFIXES):
            return True
    return False


def _run_collection() -> tuple[int, str]:
    """Run pytest --collect-only. Return (returncode, combined output)."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def main() -> int:
    args = sys.argv[1:]
    force = "--all" in args

    if not force:
        staged = _get_staged_files()
        if not _has_relevant_change(staged):
            # No test-affecting Python staged — nothing to collect.
            return 0

    returncode, output = _run_collection()

    # pytest --collect-only exits 0 on a clean collection. A non-zero exit here
    # means one or more modules failed to import/collect (returncode 2 =
    # INTERRUPTED by collection errors).
    if returncode == 0:
        print("Pytest Collection Gate: full suite collects cleanly")
        return 0

    print("\n" + "=" * 72)
    print("PYTEST COLLECTION BLOCKED")
    print("=" * 72)
    print("\n`pytest --collect-only` failed — a test module cannot be imported.")
    print("This is usually a test importing a symbol that substrate renamed or")
    print("removed. Fix the TEST import against the CURRENT symbol — do NOT add")
    print("a back-compat alias in substrate to keep a stale test green.\n")

    # Surface the error lines pytest emitted (ImportError, ERROR summary).
    error_lines = [
        line
        for line in output.splitlines()
        if ("ERROR" in line or "ImportError" in line or "Interrupted" in line)
    ]
    if error_lines:
        print("Collection errors:")
        for line in error_lines[-20:]:
            print(f"  {line}")
    else:
        # Fall back to the tail of raw output if no obvious error markers.
        print("Output tail:")
        for line in output.splitlines()[-20:]:
            print(f"  {line}")

    print("\n" + "=" * 72)
    print("How to fix:")
    print("  1. Run: python3 -m pytest tests --collect-only -q")
    print("  2. Open the failing test AND the real substrate module it imports")
    print("  3. Update the test's import to the current symbol name")
    print("  4. Re-run collection until it exits 0")
    print("=" * 72)

    return 1


if __name__ == "__main__":
    sys.exit(main())
