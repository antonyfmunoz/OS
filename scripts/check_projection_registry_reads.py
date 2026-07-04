#!/usr/bin/env python3
"""Pre-commit gate: exactly one reader of data/umh/projection_registry.json.

WP-P3 read-side convergence. `data/umh/projection_registry.json` is a SEED/CONFIG
input, not a runtime registry. It must be opened by exactly ONE canonical code
path — `substrate/sockets/projection_port.py` (the projection registration port,
via `_read_umh_seed_file` / `seed_from_umh_registry` / `load_seed_config`). Every
other consumer must read it through that port's view
(`ProjectionPort.load_seed_config()` or `load_umh_projection_seed()`), never by
opening the file itself.

Detection is AST-based to avoid false positives: a module violates only if it
contains an `open(...)` call whose path argument resolves (directly, or through
simple local string assignments / os.path.join) to `projection_registry.json`.
A mere comment/docstring/default-arg mention of the filename does NOT trip the
gate, and a module that opens OTHER registries in the same file is not flagged.

Exit codes:
  0 — clean: only the canonical port reads the file
  1 — a non-port module opens the projection registry directly

Usage:
  python3 scripts/check_projection_registry_reads.py          # staged files
  python3 scripts/check_projection_registry_reads.py --all    # scan whole tree
  python3 scripts/check_projection_registry_reads.py --file X # one file

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The ONE module allowed to open data/umh/projection_registry.json.
CANONICAL_OWNER = "substrate/sockets/projection_port.py"

REGISTRY_FILENAME = "projection_registry.json"


def _str_contains_registry(node: ast.AST) -> bool:
    """True if this AST node is a string literal naming the registry file."""
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and REGISTRY_FILENAME in node.value
    )


class _RegistryOpenVisitor(ast.NodeVisitor):
    """Finds open() calls whose path arg resolves to projection_registry.json.

    Resolves through:
      - direct string literals: open("...projection_registry.json")
      - os.path.join(..., "projection_registry.json"): open(os.path.join(...))
      - local variables bound (anywhere in the module) to either of the above,
        including `x = a or os.path.join(..., "projection_registry.json")`.
    """

    def __init__(self) -> None:
        self.registry_vars: set[str] = set()
        self.found = False

    # ── pass 1: collect variable names bound to a registry path ──
    def _expr_is_registry_path(self, node: ast.AST) -> bool:
        if _str_contains_registry(node):
            return True
        if isinstance(node, ast.Call):  # os.path.join(..., "projection_registry.json")
            if any(_str_contains_registry(a) for a in node.args):
                return True
        if isinstance(node, ast.BoolOp):  # a or os.path.join(...json)
            return any(self._expr_is_registry_path(v) for v in node.values)
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._expr_is_registry_path(node.value):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.registry_vars.add(tgt.id)
        self.generic_visit(node)

    # ── open() detection ──
    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        is_open = (isinstance(func, ast.Name) and func.id == "open") or (
            isinstance(func, ast.Attribute) and func.attr == "open"
        )
        if is_open and node.args:
            arg = node.args[0]
            if self._expr_is_registry_path(arg):
                self.found = True
            elif isinstance(arg, ast.Name) and arg.id in self.registry_vars:
                self.found = True
        self.generic_visit(node)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _is_canonical(rel_path: str) -> bool:
    return rel_path.replace("\\", "/") == CANONICAL_OWNER


def _check_file(path: Path) -> str | None:
    rel = _rel(path)
    if _is_canonical(rel) or path.suffix != ".py":
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if REGISTRY_FILENAME not in text:
        return None
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    visitor = _RegistryOpenVisitor()
    # two passes so a var assigned after its use is still resolved
    visitor.visit(tree)
    if visitor.registry_vars:
        visitor.found = False
        visitor.visit(tree)
    if visitor.found:
        return (
            f"{rel}: opens data/umh/{REGISTRY_FILENAME} directly. "
            f"Route the read through the canonical ProjectionPort view "
            f"(load_umh_projection_seed() / ProjectionPort.load_seed_config()) "
            f"instead — the file is a seed input, only {CANONICAL_OWNER} may open it."
        )
    return None


def _staged_python_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
    except OSError:
        return []
    files = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.endswith(".py"):
            p = REPO_ROOT / line
            if p.exists():
                files.append(p)
    return files


def _all_python_files() -> list[Path]:
    roots = ["substrate", "transports", "services", "adapters", "projections", "nodes"]
    files: list[Path] = []
    for r in roots:
        d = REPO_ROOT / r
        if d.is_dir():
            files.extend(d.rglob("*.py"))
    return files


def main() -> int:
    args = sys.argv[1:]
    if "--all" in args:
        targets = _all_python_files()
    elif "--file" in args:
        idx = args.index("--file")
        targets = [Path(args[idx + 1])]
    else:
        targets = _staged_python_files()

    violations: list[str] = []
    for path in targets:
        msg = _check_file(path)
        if msg:
            violations.append(msg)

    print("Projection registry read gate")
    print("=" * 50)
    if violations:
        print(f"\n✗ {len(violations)} non-canonical reader(s) of {REGISTRY_FILENAME}:\n")
        for v in violations:
            print(f"  - {v}")
        print(
            f"\nOnly {CANONICAL_OWNER} may open the projection registry. "
            f"It is a seed input, not a runtime registry."
        )
        return 1
    print(f"\n✓ PASS — only {CANONICAL_OWNER} reads data/umh/{REGISTRY_FILENAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
