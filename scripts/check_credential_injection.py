#!/usr/bin/env python3
"""Pre-commit gate: block plaintext credential patterns in code.

Credentials for computer use and browser automation must flow through
1Password (op run / op inject). This gate blocks:
  - --password in subprocess argument construction
  - CLERK_PASSWORD= as literal assignment
  - Hardcoded op:// URIs in Python code (belong in .tpl files only)

Usage:
  python3 scripts/check_credential_injection.py          # check staged files
  python3 scripts/check_credential_injection.py --all    # full codebase scan
  python3 scripts/check_credential_injection.py --file path  # single file
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCANNED_DIRS = [
    "substrate/",
    "adapters/",
    "transports/",
    "services/",
    "scripts/",
]

EXEMPT_FILES = {
    "scripts/check_credential_injection.py",
    "substrate/execution/credential_gate.py",
    # Collector receives credentials via env vars (op run injects them)
    "scripts/browser_gate_collector.py",
    # Redaction module: names the op:// pattern precisely so it can STRIP it
    # from captured probe output — no credential is ever stored or passed
    "substrate/understanding/reconstruction/runtime_probes.py",
}

EXEMPT_PATTERNS = [
    "/tests/",
    "/test_",
    "__pycache__",
    ".tpl",
]

CREDENTIAL_PATTERNS = [
    (
        re.compile(r"""['"]--password['"]"""),
        "plaintext --password argument — use 1Password op run for credential injection",
    ),
    (
        re.compile(r"""CLERK_PASSWORD\s*=\s*['"][^'"]"""),
        "hardcoded CLERK_PASSWORD assignment — use op run --env-file=<tpl>",
    ),
    (
        re.compile(r"""['"]op://[^'"]+['"]"""),
        "hardcoded op:// URI — op:// URIs belong in .tpl files, not in code",
    ),
]


def get_staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return [
        REPO_ROOT / f.strip()
        for f in result.stdout.splitlines()
        if f.strip().endswith(".py")
    ]


def get_all_files() -> list[Path]:
    files = []
    for scanned_dir in SCANNED_DIRS:
        dir_path = REPO_ROOT / scanned_dir
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

    in_scanned = any(rel.startswith(d) for d in SCANNED_DIRS)
    if not in_scanned:
        return []

    if is_exempt(path):
        return []

    try:
        content = path.read_text()
    except Exception:
        return []

    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        for pattern, message in CREDENTIAL_PATTERNS:
            if pattern.search(line):
                violations.append(f"  {rel}:{i}: {message}")

    return violations


def main() -> int:
    scan_all = "--all" in sys.argv
    single_file = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            single_file = Path(sys.argv[idx + 1])

    if single_file:
        files = [REPO_ROOT / single_file] if not single_file.is_absolute() else [single_file]
    elif scan_all:
        files = get_all_files()
    else:
        files = get_staged_files()
        files = [
            f
            for f in files
            if any(str(f.relative_to(REPO_ROOT)).startswith(d) for d in SCANNED_DIRS)
        ]

    if not files:
        return 0

    all_violations = []
    for f in files:
        if f.exists():
            all_violations.extend(check_file(f))

    if all_violations:
        print("Credential Injection Violation: plaintext credential patterns found")
        print("Use 1Password op run --env-file=<tpl> for credential injection")
        print("See .claude/rules/credential-injection.md")
        print()
        for v in all_violations:
            print(v)
        print()
        print(f"Total: {len(all_violations)} violations")
        if scan_all:
            print("\n(Scan mode — reporting only)")
            return 0
        return 1

    if scan_all:
        print(f"Credential Injection: {len(files)} files scanned — clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
