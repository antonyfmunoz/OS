#!/usr/bin/env python3
"""Pre-commit gate: blocks commits that leak instance-specific values into substrate code.

The substrate is the universal platform. It must work for ANY user, ANY org,
ANY AI name, ANY company. Instance-specific values belong in:
  - BIS (Business Instance State) loaded at runtime
  - Environment variables
  - Configuration files
  - Projection/integration layers (NOT substrate/)

This gate scans substrate/ Python files for hardcoded instance values and
blocks commits that introduce new ones. Existing violations are grandfathered
in LEGACY_INSTANCE_LEAKS but must be migrated.

Instance context categories:
  1. AI persona name (e.g., "DEX") — use get_ai_name()
  2. Founder/user identity (e.g., "Antony", "Munoz") — use BIS
  3. Company/venture names (e.g., "Lyfe Institute") — use BIS
  4. Infrastructure addresses (e.g., IPs, hostnames) — use env vars
  5. Account identifiers (e.g., GitHub usernames) — use env vars
  6. Session name prefixes derived from AI name — use config

Exit codes:
  0 — clean, no new instance leaks
  1 — new instance leak detected, commit blocked

Usage:
  python3 scripts/check_instance_leak.py           # check staged files
  python3 scripts/check_instance_leak.py --all      # scan entire substrate
  python3 scripts/check_instance_leak.py --file X   # check specific file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# ── Instance Values That Must Never Appear in Substrate ──────────────────────
# Each entry: (pattern, category, what to use instead)
# Patterns are case-insensitive word-boundary matches.

INSTANCE_PATTERNS: list[tuple[str, str, str]] = [
    # AI persona name
    (r'\bDEX\b', 'ai_name', 'get_ai_name() from substrate.control_plane.identity'),
    # Founder/user identity
    (r'\bAntony\b', 'founder_name', 'BIS founder profile at runtime'),
    (r'\bMunoz\b', 'founder_name', 'BIS founder profile at runtime'),
    # Company/venture names
    (r'\bLyfe Institute\b', 'company_name', 'BIS venture registry at runtime'),
    (r'\bEmpyrean\s+(?:Studio|Creative)\b', 'company_name', 'BIS venture registry at runtime'),
    (r'\bInitiate Arena\b', 'product_name', 'BIS product registry at runtime'),
    (r'\bMunoz (?:Conglomerate|Holdings)\b', 'company_name', 'BIS org profile at runtime'),
    # Infrastructure (Tailscale IPs for specific nodes)
    (r'\b100\.77\.233\.50\b', 'infra_ip', 'env var (e.g., UMH_VPS_IP)'),
    (r'\b100\.74\.199\.102\b', 'infra_ip', 'env var (e.g., UMH_BEAST_IP)'),
    # Account identifiers
    (r'antonyfmunoz', 'account_id', 'env var (e.g., GITHUB_USER)'),
    (r'antonys beast pc', 'account_id', 'env var for SSH host identity'),
    (r'antony-workstation', 'node_id', 'env var or BIS node registry'),
    # Session name prefixes derived from instance AI name
    (r'\bdex_(?:builder|product|main|discord|unnamed)\b', 'session_prefix',
     'config-driven session naming from get_ai_name()'),
]

# Compile once
_COMPILED_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(pat, re.IGNORECASE), cat, fix)
    for pat, cat, fix in INSTANCE_PATTERNS
]

# ── Legacy Leaks ─────────────────────────────────────────────────────────────
# Files that already contain instance values before this gate was installed.
# Each file is grandfathered — the gate only blocks NEW introductions.
# These are TECHNICAL DEBT. Each should be migrated to use runtime values.
# Format: relative path from repo root → set of categories allowed.

LEGACY_INSTANCE_LEAKS: dict[str, set[str]] = {
    # All 45 legacy leaks have been migrated to runtime lookups.
    # This dict is intentionally empty — the gate now blocks all instance values
    # in substrate/ code with zero exceptions.
}

# ── Directories to skip ──────────────────────────────────────────────────────
_EXCLUDES = {
    "__pycache__", ".git", "node_modules", ".mypy_cache",
    ".ruff_cache", ".pytest_cache", ".claude/worktrees",
    "data/", "saas/", "skills/", "/tests/",
}

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _should_skip(path: Path) -> bool:
    rel = str(path.relative_to(_REPO_ROOT))
    return any(ex in rel for ex in _EXCLUDES)


def _scan_file(filepath: Path) -> list[dict[str, str]]:
    """Scan a single file for instance-specific values."""
    violations: list[dict[str, str]] = []
    rel_path = str(filepath.relative_to(_REPO_ROOT))
    legacy_cats = LEGACY_INSTANCE_LEAKS.get(rel_path, None)

    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    for line_no, line in enumerate(lines, start=1):
        # Skip comments that are documenting the migration
        stripped = line.strip()
        if stripped.startswith("#") and ("TODO" in stripped or "LEGACY" in stripped
                                         or "migrate" in stripped.lower()):
            continue

        for pattern, category, fix in _COMPILED_PATTERNS:
            if pattern.search(line):
                if legacy_cats is not None and category in legacy_cats:
                    continue
                violations.append({
                    "file": rel_path,
                    "line": str(line_no),
                    "category": category,
                    "content": line.strip()[:120],
                    "fix": fix,
                })

    return violations


def _get_staged_files() -> list[Path]:
    """Get Python files staged for commit under substrate/."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT),
    )
    files = []
    for name in result.stdout.strip().splitlines():
        if name.startswith("substrate/") and name.endswith(".py"):
            p = _REPO_ROOT / name
            if p.exists() and not _should_skip(p):
                files.append(p)
    return files


def _get_all_substrate_files() -> list[Path]:
    """Get all Python files under substrate/."""
    files = []
    for p in (_REPO_ROOT / "substrate").rglob("*.py"):
        if not _should_skip(p):
            files.append(p)
    return files


def main() -> int:
    args = sys.argv[1:]
    if "--all" in args:
        files = _get_all_substrate_files()
        mode = "full scan"
    elif "--file" in args:
        idx = args.index("--file")
        target = Path(args[idx + 1]) if idx + 1 < len(args) else None
        if target is None:
            print("ERROR: --file requires a path argument", file=sys.stderr)
            return 1
        if not target.is_absolute():
            target = _REPO_ROOT / target
        files = [target] if target.exists() else []
        mode = f"single file: {target}"
    else:
        files = _get_staged_files()
        mode = "staged files"

    all_violations: list[dict[str, str]] = []
    for f in files:
        all_violations.extend(_scan_file(f))

    if not all_violations:
        if "--all" in args:
            print(f"Instance Context Gate: {len(files)} files scanned — clean")
            legacy_count = sum(
                1 for f, cats in LEGACY_INSTANCE_LEAKS.items()
                if cats  # non-empty = has known leaks
            )
            print(f"  Legacy leaks grandfathered: {legacy_count} files (tech debt)")
        return 0

    print("\n" + "=" * 72)
    print("INSTANCE CONTEXT LEAK BLOCKED")
    print("=" * 72)
    print(f"\nSubstrate code must be instance-agnostic.")
    print(f"Scanned: {mode} ({len(files)} files)")
    print(f"Violations: {len(all_violations)}\n")

    by_category: dict[str, list[dict[str, str]]] = {}
    for v in all_violations:
        by_category.setdefault(v["category"], []).append(v)

    for cat, violations in sorted(by_category.items()):
        print(f"── {cat} ({len(violations)} violations) ──")
        for v in violations:
            print(f"  {v['file']}:{v['line']}")
            print(f"    {v['content']}")
            print(f"    → Fix: {v['fix']}")
        print()

    print("=" * 72)
    print("How to fix:")
    print("  1. Replace hardcoded values with runtime lookups (BIS, env, config)")
    print("  2. If this is a legitimate default/fallback, add to LEGACY_INSTANCE_LEAKS")
    print("     in scripts/check_instance_leak.py with justification")
    print("=" * 72)

    return 1


if __name__ == "__main__":
    sys.exit(main())
