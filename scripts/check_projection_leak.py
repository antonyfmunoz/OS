#!/usr/bin/env python3
"""Pre-commit gate: blocks projection-specific naming from substrate code.

substrate/ is the universal UMH platform. It must work for ANY projection
(EntrepreneurOS, CreatorOS, LyfeOS, or any future projection). Projection
names, prefixes, and branded identifiers belong in:
  - projections/ (application-specific logic)
  - services/ (deployment entrypoints)
  - transports/ (interface adapters)
  - configuration / env vars

This gate scans substrate/ Python files for projection-specific naming and
blocks commits that introduce new ones. Existing violations are grandfathered
in LEGACY_PROJECTION_LEAKS but must be migrated.

Projection naming categories:
  1. Class names (e.g., EntrepreneurOSGateway) — use UMH names (Gateway, SubstrateContext)
  2. Env var prefixes (e.g., EOS_ORG_ID) — use UMH_* prefix
  3. String prefixes (e.g., eos-ceo, eos_feature) — use projection-agnostic names
  4. Product names in code (e.g., "EntrepreneurOS") — use runtime lookup or generic terms
  5. Branded identifiers (e.g., CreatorOS, LyfeOS) — keep in projections/

Exit codes:
  0 — clean, no projection leaks
  1 — projection-specific naming detected, commit blocked

Usage:
  python3 scripts/check_projection_leak.py           # check staged files
  python3 scripts/check_projection_leak.py --all      # scan entire substrate
  python3 scripts/check_projection_leak.py --file X   # check specific file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECTION_PATTERNS: list[tuple[str, str, str]] = [
    (r'\bEntrepreneurOS(?:Gateway|Context|Orchestrator)\b',
     'eos_class', 'Use Gateway, SubstrateContext, or Orchestrator'),
    (r'\bEntrepreneurOS\b',
     'eos_brand', 'Projection name — use generic term or move to projections/'),
    (r'(?<!\bor\s)(?<!\bget\()(?<!")\bEOS_ORG_ID\b',
     'eos_env', 'Use UMH_ORG_ID with EOS_ORG_ID as fallback'),
    (r'(?<!\bor\s)(?<!\bget\()(?<!")\bEOS_USER_ID\b',
     'eos_env', 'Use UMH_USER_ID with EOS_USER_ID as fallback'),
    (r'(?<!\bor\s)(?<!\bget\()(?<!")\bEOS_PORTFOLIO_ID\b',
     'eos_env', 'Use UMH_PORTFOLIO_ID with EOS_PORTFOLIO_ID as fallback'),
    (r'\bCreatorOS\b',
     'creatoros_brand', 'Projection name — belongs in projections/'),
    (r'\bLyfeOS\b',
     'lyfeos_brand', 'Projection name — belongs in projections/'),
]

_COMPILED_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(pat), cat, fix)
    for pat, cat, fix in PROJECTION_PATTERNS
]

# Files that already contain projection references before this gate was installed.
# Each file is grandfathered — the gate only blocks NEW introductions.
# Format: relative path from repo root → set of categories allowed.
LEGACY_PROJECTION_LEAKS: dict[str, set[str]] = {
    # Backward compat aliases — these ARE the migration bridge
    "substrate/control_plane/runtime/gateway.py": {"eos_class"},
    "substrate/control_plane/orchestrator/orchestrator.py": {"eos_class"},
    "substrate/state/context/context.py": {"eos_class"},
    # Projection registry — product names are data entries, not code
    "substrate/state/registries/os_registry.py": {"eos_brand", "creatoros_brand", "lyfeos_brand"},
    # Architecture docstrings that list projection names for clarity
    "substrate/types.py": {"creatoros_brand", "lyfeos_brand"},
    "substrate/integrations/__init__.py": {"creatoros_brand", "lyfeos_brand"},
    "substrate/integrations/product_connections.py": {"creatoros_brand"},
    # Domain bridge modules — docstrings name their target projection
    "substrate/understanding/domains/creator.py": {"creatoros_brand"},
    "substrate/understanding/domains/life.py": {"lyfeos_brand"},
    # Env var fallback chains (UMH_* primary, EOS_* fallback)
    "substrate/state/storage/db.py": {"eos_env"},
    "substrate/self_model.py": {"eos_env"},
    "substrate/control_plane/registry.py": {"eos_env"},
    "substrate/control_plane/context/__init__.py": {"eos_env"},
    "substrate/control_plane/context/context_builder.py": {"eos_env"},
}

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
    """Scan a single file for projection-specific naming."""
    violations: list[dict[str, str]] = []
    rel_path = str(filepath.relative_to(_REPO_ROOT))
    legacy_cats = LEGACY_PROJECTION_LEAKS.get(rel_path, None)

    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#") and ("backward" in stripped.lower()
                                         or "compat" in stripped.lower()
                                         or "legacy" in stripped.lower()):
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
            print(f"Projection Boundary Gate: {len(files)} files scanned — clean")
            legacy_count = sum(1 for cats in LEGACY_PROJECTION_LEAKS.values() if cats)
            print(f"  Legacy leaks grandfathered: {legacy_count} files (tech debt)")
        return 0

    print("\n" + "=" * 72)
    print("PROJECTION BOUNDARY LEAK BLOCKED")
    print("=" * 72)
    print(f"\nSubstrate code must be projection-agnostic.")
    print(f"No projection names (EOS, CreatorOS, LyfeOS) in substrate/.")
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
    print("  1. Replace projection names with generic substrate names")
    print("  2. Move projection-specific code to projections/")
    print("  3. Use UMH_* env vars with EOS_* as fallback")
    print("  4. If this is a data entry (product name), add to LEGACY_PROJECTION_LEAKS")
    print("     in scripts/check_projection_leak.py with justification")
    print("=" * 72)

    return 1


if __name__ == "__main__":
    sys.exit(main())
