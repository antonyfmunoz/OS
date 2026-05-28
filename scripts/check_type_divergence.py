#!/usr/bin/env python3
"""Pre-commit gate: blocks commits that create types diverging from canonical registry.

Scans staged Python files for class definitions (Enum, BaseModel, dataclass)
whose names collide with the canonical type registry. If a collision is found
and the file is NOT the canonical source, the commit is blocked with actionable
error output telling the developer exactly where to import from.

Also detects semantic near-misses: if you define "TaskStatus" and "TaskType"
already exists, that's flagged as suspicious (not blocked, but warned).

Exit codes:
  0 — clean, no divergence
  1 — divergence detected, commit blocked

Usage:
  python3 scripts/check_type_divergence.py          # check staged files
  python3 scripts/check_type_divergence.py --all     # scan entire codebase
  python3 scripts/check_type_divergence.py --file X  # check specific file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from substrate.canonical_types import CANONICAL_TYPES, LEGACY_DUPLICATES

_EXCLUDES = {
    "__pycache__",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".claude/worktrees",
    "data/repos",
    "saas/",
    "skills/saas-dev-skill",
}

_TYPE_BASES = frozenset(
    {
        "Enum",
        "str, Enum",
        "int, Enum",
        "IntEnum",
        "StrEnum",
        "BaseModel",
        "TypedDict",
    }
)


def _file_to_module(filepath: str) -> str:
    """Convert file path to dotted module path."""
    p = filepath.replace("/opt/OS/", "").replace(".py", "").replace("/", ".")
    for worktree_prefix in [".claude.worktrees.", ".claude/worktrees/"]:
        if worktree_prefix.replace("/", ".") in p:
            parts = p.split(".")
            try:
                wt_idx = parts.index("worktrees")
                p = ".".join(parts[wt_idx + 2 :])
            except ValueError:
                pass
    return p


def _is_excluded(filepath: str) -> bool:
    return any(ex in filepath for ex in _EXCLUDES)


def _extract_type_definitions(filepath: str) -> list[tuple[str, int, str]]:
    """Parse a Python file and return (class_name, line_number, base_classes_str)."""
    try:
        source = Path(filepath).read_text()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, OSError):
        return []

    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases_str = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases_str.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases_str.append(base.attr)
        combined = ", ".join(bases_str)
        is_type_def = any(tb in combined for tb in _TYPE_BASES)
        is_dataclass = any(
            (isinstance(d, ast.Name) and d.id == "dataclass")
            or (isinstance(d, ast.Attribute) and d.attr == "dataclass")
            or (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Name)
                and d.func.id == "dataclass"
            )
            or (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr == "dataclass"
            )
            for d in node.decorator_list
        )
        if is_type_def or is_dataclass:
            results.append((node.name, node.lineno, combined))
    return results


def _get_staged_files() -> list[str]:
    """Get Python files staged for commit."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return [f"{root}/{f.strip()}" for f in result.stdout.splitlines() if f.strip().endswith(".py")]


def _get_all_python_files() -> list[str]:
    """Get all Python files in the repo."""
    root = Path("/opt/OS")
    return [str(p) for p in root.rglob("*.py") if not _is_excluded(str(p))]


def _similar_names(name: str, registry: dict[str, str]) -> list[str]:
    """Find canonical names that are suspiciously similar to the given name."""
    name_lower = name.lower()
    stem = name_lower.rstrip("s")
    matches = []
    for canonical in registry:
        canon_lower = canonical.lower()
        canon_stem = canon_lower.rstrip("s")
        if canon_lower == name_lower:
            continue
        if stem == canon_stem:
            matches.append(canonical)
        elif name_lower.endswith("status") and canon_lower.endswith("status"):
            prefix_a = name_lower.replace("status", "")
            prefix_b = canon_lower.replace("status", "")
            if prefix_a and prefix_b and (prefix_a in prefix_b or prefix_b in prefix_a):
                matches.append(canonical)
        elif name_lower.endswith("type") and canon_lower.endswith("type"):
            prefix_a = name_lower.replace("type", "")
            prefix_b = canon_lower.replace("type", "")
            if prefix_a and prefix_b and (prefix_a in prefix_b or prefix_b in prefix_a):
                matches.append(canonical)
    return matches


def check_files(files: list[str]) -> tuple[list[str], list[str]]:
    """Check files for type divergence. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    for filepath in files:
        if _is_excluded(filepath):
            continue
        module = _file_to_module(filepath)
        defs = _extract_type_definitions(filepath)

        for class_name, lineno, bases in defs:
            canonical_list = CANONICAL_TYPES.get(class_name)
            if canonical_list is not None:
                is_canonical = any(module == c or module.endswith(c) for c in canonical_list)
                is_legacy = class_name in LEGACY_DUPLICATES.get(module, set())
                if not is_canonical and not is_legacy:
                    errors.append(
                        f"  BLOCKED: {filepath}:{lineno}\n"
                        f"    Defines '{class_name}' (bases: {bases})\n"
                        f"    Already exists: from {canonical_list[0]} import {class_name}\n"
                    )
            else:
                similar = _similar_names(class_name, CANONICAL_TYPES)
                if similar:
                    warnings.append(
                        f"  WARNING: {filepath}:{lineno}\n"
                        f"    New type '{class_name}' is similar to: {', '.join(similar)}\n"
                        f"    Verify this is intentionally distinct, not a divergent copy.\n"
                    )

    return errors, warnings


def main() -> int:
    if "--all" in sys.argv:
        files = _get_all_python_files()
        mode = "full codebase"
    elif "--file" in sys.argv:
        idx = sys.argv.index("--file")
        files = [sys.argv[idx + 1]] if idx + 1 < len(sys.argv) else []
        mode = "specific file"
    else:
        files = _get_staged_files()
        mode = "staged files"

    if not files:
        return 0

    errors, warnings = check_files(files)

    if warnings:
        print(f"\n⚠ Type divergence warnings ({mode}):")
        print("─" * 60)
        for w in warnings:
            print(w)

    if errors:
        print(f"\n✗ TYPE DIVERGENCE DETECTED ({mode})")
        print("═" * 60)
        for e in errors:
            print(e)
        print("═" * 60)
        print("Fix: import from the canonical location shown above.")
        print("If this is genuinely new: add it to substrate/canonical_types.py")
        print("")
        return 1

    if "--verbose" in sys.argv:
        print(f"✓ No type divergence in {len(files)} files ({mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
