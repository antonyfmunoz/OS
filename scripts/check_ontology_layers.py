#!/usr/bin/env python3
"""Pre-commit gate: enforces the ontology/metamodel layer contract (WP-P3-001).

UMH separates knowledge into four layers (see .claude/rules/ontology-layers.md):
  L1 External Operational Reality Model  — substrate/reality_model/
  L2 UMH Platform Metamodel / primitives — substrate/types.py, substrate/ontology/
  L3 Projection Domain Models            — projections/, understanding/domains/<name>.py
  L4 Semantic Grounding / bridge         — understanding/domains/contract.py, registry.py

Substrate must define the RULES of worlds, not the CONTENTS of one world. This
gate blocks NEW L3 contamination from entering the L2 metamodel surface
(substrate/types.py, substrate/ontology/). Existing contamination is frozen in
LEGACY_ONTOLOGY_LEAKS and may only SHRINK, never grow.

It flags three things in the L2 surface:
  1. A domain-object class whose fields carry projection-specific vocabulary
     (icp / offer / venture / monthly_revenue / north_star / stage_name ...).
  2. substrate/ontology/ importing substrate/state/business/ (BIS instance state)
     or any projections/ module (L2 importing L3).
  3. Instance/brand snake_case literals (empyrean_creative, lyfe_institute,
     personal_brand) embedded in the L2 surface.

Exit codes:
  0 — clean (or only frozen legacy leaks)
  1 — new L3-in-L2 contamination detected, commit blocked

Usage:
  python3 scripts/check_ontology_layers.py           # check staged files
  python3 scripts/check_ontology_layers.py --all      # scan the full L2 surface
  python3 scripts/check_ontology_layers.py --file X   # check a specific file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ── The L2 metamodel surface this gate guards ────────────────────────────────
# Only files under these prefixes are scanned. L2 is where projection contents
# must never leak. (L3 homes like understanding/domains/<name>.py are bridges
# and legitimately name their projection — they are NOT part of the L2 surface.)
_L2_SURFACE_PREFIXES = (
    "substrate/types.py",
    "substrate/ontology/",
)

# ── L3 projection-specific field vocabulary ──────────────────────────────────
# A domain-object field whose name matches one of these is EOS/CreatorOS/LyfeOS
# domain vocabulary, not a universal metamodel concept. A NEW L2 class carrying
# these fields is contamination.
_L3_FIELD_VOCAB: frozenset[str] = frozenset(
    {
        "icp",
        "primary_icp",
        "icp_description",
        "icp_demographics",
        "icp_psychographics",
        "icp_pain_points",
        "offer",
        "core_offer",
        "offer_name",
        "offer_price",
        "offer_promise",
        "offer_transformation",
        "price_point",
        "positioning",
        "monthly_revenue",
        "monthly_target",
        "north_star",
        "stage_name",
        "winning_content_angles",
        "proven_outreach_openers",
        "common_objections",
    }
)
# Matches `    field_name: type` or `    field_name = ...` class-body assignments.
_FIELD_DEF_RE = re.compile(r"^\s+([a-z_][a-z0-9_]*)\s*[:=]")
_CLASS_DEF_RE = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)")

# ── L3 imports forbidden inside L2 ontology ──────────────────────────────────
_FORBIDDEN_ONTOLOGY_IMPORTS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"^\s*(?:from|import)\s+substrate\.state\.business\b"),
        "ontology_imports_bis",
        "L2 ontology must not import L3 BIS state (substrate/state/business/)",
    ),
    (
        re.compile(r"^\s*(?:from|import)\s+projections\b"),
        "ontology_imports_projection",
        "L2 ontology must not import a projection (projections/)",
    ),
]

# ── Instance/brand snake_case literals that must not sit in the L2 surface ────
_INSTANCE_LITERAL_RE = re.compile(r"\b(empyrean_creative|lyfe_institute|personal_brand)\b")

# ── Shrink-only legacy ledger ────────────────────────────────────────────────
# Existing L3-in-L2 contamination frozen at WP-P3-001 (main bb39b3abd). The gate
# only blocks NEW leaks; every entry here is tech debt to be RELOCATED (not
# edited away) in a later guarded packet. This dict may only SHRINK — the
# non-growth test in tests/test_ontology_layer_contract.py enforces that.
# Format: relative path → set of frozen categories allowed in that file.
LEGACY_ONTOLOGY_LEAKS: dict[str, set[str]] = {
    # substrate/types.py — Company/Department/Portfolio carry EOS-specific fields
    # (stage_name, north_star, "maps to a venture"). Operator decision: the
    # abstract org primitives may stay L2, but these L3 fields are frozen
    # contamination for later relocation to projections/eos.
    "substrate/types.py": {"l3_field"},
    # substrate/ontology/ surface is otherwise clean today; no ontology import
    # leaks currently exist. (If one is found on --all it is a real regression.)
}

_EXCLUDES = {
    "__pycache__",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".claude/worktrees",
    "data/",
    "saas/",
    "skills/",
    "/tests/",
}


def _should_skip(path: Path) -> bool:
    rel = str(path.relative_to(_REPO_ROOT))
    return any(ex in rel for ex in _EXCLUDES)


def _in_l2_surface(rel_path: str) -> bool:
    return any(rel_path.startswith(p) for p in _L2_SURFACE_PREFIXES)


def _scan_file(filepath: Path) -> list[dict[str, str]]:
    """Scan a single L2-surface file for L3 contamination."""
    rel_path = str(filepath.relative_to(_REPO_ROOT))
    if not _in_l2_surface(rel_path):
        return []

    legacy_cats = LEGACY_ONTOLOGY_LEAKS.get(rel_path, set())
    violations: list[dict[str, str]] = []

    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    in_class = False
    for line_no, line in enumerate(lines, start=1):
        # Track class-body context for field-vocabulary detection.
        if _CLASS_DEF_RE.match(line):
            in_class = True
        elif line and not line[0].isspace():
            in_class = False

        stripped = line.strip()

        # 1. L3 field vocabulary inside a class body.
        if in_class:
            m = _FIELD_DEF_RE.match(line)
            if m and m.group(1) in _L3_FIELD_VOCAB:
                if "l3_field" not in legacy_cats:
                    violations.append(
                        {
                            "file": rel_path,
                            "line": str(line_no),
                            "category": "l3_field",
                            "content": stripped[:120],
                            "fix": f"'{m.group(1)}' is L3 projection vocabulary — "
                            "move this domain object to projections/ or a bridge",
                        }
                    )

        # 2. Forbidden L3 imports inside the ontology surface.
        for pattern, category, fix in _FORBIDDEN_ONTOLOGY_IMPORTS:
            if pattern.match(line) and category not in legacy_cats:
                violations.append(
                    {
                        "file": rel_path,
                        "line": str(line_no),
                        "category": category,
                        "content": stripped[:120],
                        "fix": fix,
                    }
                )

        # 3. Instance/brand snake_case literal in the L2 surface.
        if _INSTANCE_LITERAL_RE.search(line) and "instance_literal" not in legacy_cats:
            violations.append(
                {
                    "file": rel_path,
                    "line": str(line_no),
                    "category": "instance_literal",
                    "content": stripped[:120],
                    "fix": "Instance/brand literal — load from BIS/registry at runtime",
                }
            )

    return violations


def _get_staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    files = []
    for name in result.stdout.strip().splitlines():
        if name.endswith(".py") and _in_l2_surface(name):
            p = _REPO_ROOT / name
            if p.exists() and not _should_skip(p):
                files.append(p)
    return files


def _get_all_l2_files() -> list[Path]:
    """All Python files on the L2 surface (substrate/types.py + substrate/ontology/)."""
    files: list[Path] = []
    types_py = _REPO_ROOT / "substrate" / "types.py"
    if types_py.exists():
        files.append(types_py)
    ontology_dir = _REPO_ROOT / "substrate" / "ontology"
    if ontology_dir.exists():
        for p in ontology_dir.rglob("*.py"):
            if not _should_skip(p):
                files.append(p)
    return files


def main() -> int:
    args = sys.argv[1:]
    if "--all" in args:
        files = _get_all_l2_files()
        mode = "full L2-surface scan"
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
            print(f"Ontology Layer Gate: {len(files)} L2-surface files scanned — clean")
            legacy_count = sum(1 for cats in LEGACY_ONTOLOGY_LEAKS.values() if cats)
            print(f"  Legacy ontology leaks frozen: {legacy_count} files (shrink-only)")
        return 0

    print("\n" + "=" * 72)
    print("ONTOLOGY LAYER CONTRACT VIOLATION BLOCKED")
    print("=" * 72)
    print("\nL2 (substrate/types.py, substrate/ontology/) must not contain L3")
    print("projection domain objects, projection imports, or instance literals.")
    print("substrate defines the RULES of worlds, not the CONTENTS of one world.")
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
    print("  1. Move the projection-specific domain object to projections/<name>/")
    print("  2. Or express it as a domain bridge in understanding/domains/")
    print("  3. Load instance/brand values from BIS/registry at runtime")
    print("  4. If genuinely universal, remove the projection-specific fields")
    print("  See .claude/rules/ontology-layers.md")
    print("=" * 72)

    return 1


if __name__ == "__main__":
    sys.exit(main())
