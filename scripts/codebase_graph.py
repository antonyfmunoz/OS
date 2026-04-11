#!/usr/bin/env python3
"""
codebase_graph.py — Persistent codebase knowledge graph for EOS.

Scans the entire codebase using Python AST, extracts structure,
dependencies, and relationships, then generates an Obsidian vault
of interconnected markdown files with wikilinks.

Pipeline:
  1. SCAN   — recursively parse all Python files via ast
  2. GRAPH  — build nodes (file, class, function) and edges (imports, calls, depends_on)
  3. RENDER — generate Obsidian markdown in 10_Wiki/codebase/

Usage:
    python3 scripts/codebase_graph.py                # full rebuild
    python3 scripts/codebase_graph.py --json-only    # emit JSON, skip markdown
    python3 scripts/codebase_graph.py --stats        # print stats only
    python3 scripts/codebase_graph.py --module eos_ai.gateway  # single module
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import textwrap
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

try:
    from parsers import REGISTRY as PARSER_REGISTRY
    from parsers.base import ParsedFile
except Exception:  # pragma: no cover — allow running before parsers/ exists
    PARSER_REGISTRY = []  # type: ignore[assignment]
    ParsedFile = None  # type: ignore[assignment,misc]

# ─── Configuration ────────────────────────────────────────────────────────────

ROOT = Path("/opt/OS")
WIKI_DIR = ROOT / "10_Wiki" / "codebase"
JSON_OUT = ROOT / "data" / "codebase_graph.json"
CLOUD_MD = WIKI_DIR / "cloud.md"
INDEX_MD = WIKI_DIR / "index.md"

# Directories to scan (relative to ROOT)
SCAN_DIRS = [
    "eos_ai",
    "services",
    "scripts",
    "core",
]

# Directories and patterns to skip
SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".obsidian",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".eggs",
    "archive",
    "saas",
}

SKIP_FILES = {
    "__init__.py",
    "setup.py",
    "conftest.py",
}

# Files that are critical entry points
CRITICAL_FILES = {
    "eos_ai/cognitive_loop.py",
    "eos_ai/gateway.py",
    "eos_ai/agent_runtime.py",
    "eos_ai/model_router.py",
    "eos_ai/orchestrator.py",
    "eos_ai/db.py",
    "eos_ai/memory.py",
    "eos_ai/agent_hierarchy.py",
    "eos_ai/ai_identity.py",
    "eos_ai/primitives.py",
    "services/discord_bot.py",
    "services/telegram_control.py",
}

# Entry point patterns (server start, main block, CLI)
ENTRY_PATTERNS = [
    r'if\s+__name__\s*==\s*["\']__main__["\']',
    r"app\.run\(",
    r"bot\.run\(",
    r"uvicorn\.run\(",
    r"argparse\.ArgumentParser",
]


# ─── Data Structures ─────────────────────────────────────────────────────────


@dataclass
class FunctionNode:
    """A function or method extracted from AST."""

    name: str
    file_path: str  # relative to ROOT
    line: int
    end_line: int | None
    decorators: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    return_annotation: str | None = None
    docstring: str | None = None
    calls: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: str | None = None


@dataclass
class ClassNode:
    """A class extracted from AST."""

    name: str
    file_path: str
    line: int
    end_line: int | None
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    methods: list[str] = field(default_factory=list)


@dataclass
class FileNode:
    """A Python file with its extracted contents."""

    path: str  # relative to ROOT
    module_name: str
    docstring: str | None = None
    imports: list[dict[str, str]] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    is_entry_point: bool = False
    is_critical: bool = False
    line_count: int = 0
    size_bytes: int = 0


@dataclass
class Edge:
    """A directed relationship between two nodes."""

    from_type: str  # file, class, function
    from_id: str
    to_type: str
    to_id: str
    relationship: str  # imports, calls, depends_on, inherits, contains


@dataclass
class CodebaseGraph:
    """The complete knowledge graph."""

    files: dict[str, FileNode] = field(default_factory=dict)
    classes: dict[str, ClassNode] = field(default_factory=dict)
    functions: dict[str, FunctionNode] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    generated_at: str = ""
    stats: dict[str, int] = field(default_factory=dict)
    # Non-Python files indexed by the modular parser registry.
    # Shape: {rel_path: {language, line_count, size_bytes, docstring, symbols[], imports[], is_entry_point}}
    non_python_files: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Language coverage counts (python, typescript, javascript, sql, config:json, ...)
    languages: dict[str, int] = field(default_factory=dict)


# ─── Phase 1: Scanner ────────────────────────────────────────────────────────


def _rel(path: Path) -> str:
    """Path relative to ROOT as string."""
    return str(path.relative_to(ROOT))


def _module_name(path: Path) -> str:
    """Convert file path to Python module name."""
    rel = path.relative_to(ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _decorator_name(node: ast.expr) -> str:
    """Extract decorator name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return "unknown"


def _extract_calls(node: ast.AST) -> list[str]:
    """Extract function/method call names from an AST subtree."""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return calls


def _annotation_str(node: ast.expr | None) -> str | None:
    """Convert annotation AST node to string."""
    if node is None:
        return None
    return ast.unparse(node)


def _is_entry_point(source: str) -> bool:
    """Check if file contains entry point patterns."""
    return any(re.search(p, source) for p in ENTRY_PATTERNS)


def scan_file(path: Path) -> tuple[FileNode, list[ClassNode], list[FunctionNode]]:
    """Parse a single Python file and extract all nodes."""
    rel_path = _rel(path)
    source = path.read_text(encoding="utf-8", errors="replace")

    file_node = FileNode(
        path=rel_path,
        module_name=_module_name(path),
        line_count=source.count("\n") + 1,
        size_bytes=path.stat().st_size,
        is_entry_point=_is_entry_point(source),
        is_critical=rel_path in CRITICAL_FILES,
    )

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return file_node, [], []

    # Module docstring
    file_node.docstring = ast.get_docstring(tree)

    # Imports
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                file_node.imports.append(
                    {
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                file_node.imports.append(
                    {
                        "type": "from",
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                    }
                )

    classes: list[ClassNode] = []
    functions: list[FunctionNode] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            cls = ClassNode(
                name=node.name,
                file_path=rel_path,
                line=node.lineno,
                end_line=node.end_lineno,
                bases=[ast.unparse(b) for b in node.bases],
                decorators=[_decorator_name(d) for d in node.decorator_list],
                docstring=ast.get_docstring(node),
                methods=[],
            )

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn = FunctionNode(
                        name=item.name,
                        file_path=rel_path,
                        line=item.lineno,
                        end_line=item.end_lineno,
                        decorators=[_decorator_name(d) for d in item.decorator_list],
                        args=[
                            a.arg
                            for a in item.args.args
                            if a.arg != "self" and a.arg != "cls"
                        ],
                        return_annotation=_annotation_str(item.returns),
                        docstring=ast.get_docstring(item),
                        calls=_extract_calls(item),
                        is_method=True,
                        class_name=node.name,
                    )
                    cls.methods.append(item.name)
                    fn_id = f"{rel_path}::{node.name}.{item.name}"
                    functions.append(fn)
                    file_node.functions.append(fn_id)

            classes.append(cls)
            file_node.classes.append(f"{rel_path}::{node.name}")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = FunctionNode(
                name=node.name,
                file_path=rel_path,
                line=node.lineno,
                end_line=node.end_lineno,
                decorators=[_decorator_name(d) for d in node.decorator_list],
                args=[
                    a.arg for a in node.args.args if a.arg != "self" and a.arg != "cls"
                ],
                return_annotation=_annotation_str(node.returns),
                docstring=ast.get_docstring(node),
                calls=_extract_calls(node),
                is_method=False,
            )
            fn_id = f"{rel_path}::{node.name}"
            functions.append(fn)
            file_node.functions.append(fn_id)

    return file_node, classes, functions


def scan_codebase(target_module: str | None = None) -> CodebaseGraph:
    """Scan all Python files and build the graph."""
    graph = CodebaseGraph(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    python_files: list[Path] = []
    for scan_dir in SCAN_DIRS:
        base = ROOT / scan_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            # Skip excluded dirs
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.name in SKIP_FILES:
                continue
            # Filter to single module if requested
            if target_module:
                mod = _module_name(path)
                if not mod.startswith(target_module):
                    continue
            python_files.append(path)

    print(f"[scan] Found {len(python_files)} Python files")

    # Module name → relative path lookup for import resolution
    module_to_path: dict[str, str] = {}

    for path in python_files:
        file_node, classes, functions = scan_file(path)
        rel = file_node.path
        graph.files[rel] = file_node
        module_to_path[file_node.module_name] = rel

        for cls in classes:
            cls_id = f"{rel}::{cls.name}"
            graph.classes[cls_id] = cls
            # File contains class
            graph.edges.append(
                Edge(
                    from_type="file",
                    from_id=rel,
                    to_type="class",
                    to_id=cls_id,
                    relationship="contains",
                )
            )

        for fn in functions:
            if fn.class_name:
                fn_id = f"{rel}::{fn.class_name}.{fn.name}"
                cls_id = f"{rel}::{fn.class_name}"
                # Class contains method
                graph.edges.append(
                    Edge(
                        from_type="class",
                        from_id=cls_id,
                        to_type="function",
                        to_id=fn_id,
                        relationship="contains",
                    )
                )
            else:
                fn_id = f"{rel}::{fn.name}"
                # File contains function
                graph.edges.append(
                    Edge(
                        from_type="file",
                        from_id=rel,
                        to_type="function",
                        to_id=fn_id,
                        relationship="contains",
                    )
                )
            graph.functions[fn_id] = fn

    # ── Build edges from imports ──────────────────────────────────────────

    for rel, file_node in graph.files.items():
        for imp in file_node.imports:
            mod = imp["module"]
            # Resolve internal imports
            resolved = None
            if mod in module_to_path:
                resolved = module_to_path[mod]
            else:
                # Try parent module (from eos_ai.db import get_conn)
                for known_mod, known_path in module_to_path.items():
                    if mod.startswith(known_mod) or known_mod.startswith(mod):
                        resolved = known_path
                        break

            if resolved and resolved != rel:
                graph.edges.append(
                    Edge(
                        from_type="file",
                        from_id=rel,
                        to_type="file",
                        to_id=resolved,
                        relationship="imports",
                    )
                )

    # ── Build edges from class inheritance ────────────────────────────────

    class_name_to_id: dict[str, str] = {}
    for cls_id, cls in graph.classes.items():
        class_name_to_id[cls.name] = cls_id

    for cls_id, cls in graph.classes.items():
        for base in cls.bases:
            base_name = base.split(".")[-1]
            if base_name in class_name_to_id:
                graph.edges.append(
                    Edge(
                        from_type="class",
                        from_id=cls_id,
                        to_type="class",
                        to_id=class_name_to_id[base_name],
                        relationship="inherits",
                    )
                )

    # ── Build edges from function calls ───────────────────────────────────
    # Scope: only resolve calls within the same file or files this file imports.
    # This prevents "get()" in file A from linking to every "get()" globally.

    # Build file → set of imported file paths
    file_import_targets: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.relationship == "imports" and edge.from_type == "file":
            file_import_targets[edge.from_id].add(edge.to_id)

    # Build (file_path, fn_name) → fn_id for scoped lookup
    fn_by_file_and_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fn_id, fn in graph.functions.items():
        fn_by_file_and_name[(fn.file_path, fn.name)].append(fn_id)

    for fn_id, fn in graph.functions.items():
        # Candidate files: same file + imported files
        candidate_files = {fn.file_path} | file_import_targets.get(fn.file_path, set())
        for call_name in fn.calls:
            for cfile in candidate_files:
                for target_id in fn_by_file_and_name.get((cfile, call_name), []):
                    if target_id != fn_id:
                        graph.edges.append(
                            Edge(
                                from_type="function",
                                from_id=fn_id,
                                to_type="function",
                                to_id=target_id,
                                relationship="calls",
                            )
                        )

    # ── Stats ─────────────────────────────────────────────────────────────

    graph.stats = {
        "files": len(graph.files),
        "classes": len(graph.classes),
        "functions": len(graph.functions),
        "edges": len(graph.edges),
        "total_lines": sum(f.line_count for f in graph.files.values()),
        "total_bytes": sum(f.size_bytes for f in graph.files.values()),
        "entry_points": sum(1 for f in graph.files.values() if f.is_entry_point),
        "critical_files": sum(1 for f in graph.files.values() if f.is_critical),
    }

    rel_counts = defaultdict(int)
    for e in graph.edges:
        rel_counts[e.relationship] += 1
    graph.stats["edges_by_type"] = dict(rel_counts)

    # ── Multi-language pass via modular parser registry ──────────────────
    # Additive: does not touch Python graph shape. Fills graph.non_python_files
    # with JS/TS/SQL/config files so query_graph.py can surface language coverage.
    scan_non_python(graph, target_module=target_module)

    graph.stats["files"] = len(graph.files)
    graph.stats["non_python_files"] = len(graph.non_python_files)
    graph.stats["languages"] = dict(graph.languages)
    # "python" language count mirrors graph.files for a single source of truth.
    if "python" not in graph.stats["languages"]:
        graph.stats["languages"]["python"] = len(graph.files)

    print(
        f"[scan] {graph.stats['files']} py files, "
        f"{graph.stats['non_python_files']} non-py files, "
        f"{graph.stats['classes']} classes, "
        f"{graph.stats['functions']} functions, "
        f"{graph.stats['edges']} edges"
    )

    return graph


# ─── Multi-language scanner ──────────────────────────────────────────────────


# File-type extensions handled by the modular parser registry.
NON_PYTHON_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sql"}
# Only scan non-Python files inside the same SCAN_DIRS the Python pass uses.
# JSON/YAML config is intentionally left out of the graph JSON to keep file
# size bounded; parsers.REGISTRY still handles them when called directly.


def scan_non_python(graph: CodebaseGraph, target_module: str | None = None) -> None:
    """Walk SCAN_DIRS for non-Python files and dispatch through parsers.REGISTRY."""
    if not PARSER_REGISTRY:
        return

    for scan_dir in SCAN_DIRS:
        base = ROOT / scan_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in NON_PYTHON_EXTENSIONS:
                continue
            rel = str(path.relative_to(ROOT))
            if target_module and not rel.startswith(target_module.replace(".", "/")):
                continue

            parsed: ParsedFile | None = None
            for parser in PARSER_REGISTRY:
                if parser.handles(path):
                    try:
                        parsed = parser.parse(path)
                    except Exception as exc:  # pragma: no cover — never fail the whole scan
                        print(f"[scan] parser {parser.language} failed on {rel}: {exc}")
                        parsed = None
                    break
            if parsed is None:
                continue

            graph.non_python_files[rel] = {
                "language": parsed.language,
                "line_count": parsed.line_count,
                "size_bytes": parsed.size_bytes,
                "docstring": parsed.docstring,
                "symbols": [
                    {
                        "name": s.name,
                        "kind": s.kind,
                        "line": s.line,
                        "parent": s.parent,
                    }
                    for s in parsed.symbols
                ],
                "imports": [
                    {
                        "module": i.module,
                        "symbol": i.symbol,
                        "alias": i.alias,
                        "kind": i.kind,
                    }
                    for i in parsed.imports
                ],
                "is_entry_point": parsed.is_entry_point,
            }
            graph.languages[parsed.language] = graph.languages.get(parsed.language, 0) + 1


# ─── Phase 2: JSON Export ─────────────────────────────────────────────────────


def export_json(graph: CodebaseGraph) -> Path:
    """Write graph to JSON for machine consumption."""
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "generated_at": graph.generated_at,
        "stats": graph.stats,
        "files": {k: asdict(v) for k, v in graph.files.items()},
        "classes": {k: asdict(v) for k, v in graph.classes.items()},
        "functions": {k: asdict(v) for k, v in graph.functions.items()},
        "edges": [asdict(e) for e in graph.edges],
        "non_python_files": graph.non_python_files,
        "languages": dict(graph.languages),
    }

    JSON_OUT.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"[json] Written to {JSON_OUT} ({JSON_OUT.stat().st_size:,} bytes)")
    return JSON_OUT


# ─── Phase 3: Obsidian Vault Generator ───────────────────────────────────────


def _slug(name: str) -> str:
    """Convert a node ID to an Obsidian-safe filename slug."""
    # eos_ai/gateway.py::GatewayRouter.classify → eos_ai-gateway-GatewayRouter-classify
    return re.sub(r"[/:.\s]+", "-", name).strip("-")


def _wikilink(node_id: str) -> str:
    """Create an Obsidian wikilink for a node ID."""
    return f"[[{_slug(node_id)}]]"


def _truncate_docstring(doc: str | None, max_lines: int = 5) -> str:
    """Truncate docstring for summary display."""
    if not doc:
        return "*No docstring.*"
    lines = doc.strip().split("\n")
    if len(lines) <= max_lines:
        return doc.strip()
    return "\n".join(lines[:max_lines]) + "\n..."


def _build_reverse_index(graph: CodebaseGraph) -> dict[str, list[Edge]]:
    """Build a reverse lookup: to_id → list of edges pointing to it."""
    reverse: dict[str, list[Edge]] = defaultdict(list)
    for edge in graph.edges:
        reverse[edge.to_id].append(edge)
    return reverse


def _build_forward_index(graph: CodebaseGraph) -> dict[str, list[Edge]]:
    """Build forward lookup: from_id → list of edges from it."""
    forward: dict[str, list[Edge]] = defaultdict(list)
    for edge in graph.edges:
        forward[edge.from_id].append(edge)
    return forward


def generate_obsidian(graph: CodebaseGraph) -> None:
    """Generate the full Obsidian vault from the graph."""
    # Clean and recreate
    if WIKI_DIR.exists():
        import shutil

        # Preserve cloud.md if it exists and we're regenerating
        cloud_backup = None
        if CLOUD_MD.exists():
            cloud_backup = CLOUD_MD.read_text()
        shutil.rmtree(WIKI_DIR)

    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    (WIKI_DIR / "files").mkdir(exist_ok=True)
    (WIKI_DIR / "modules").mkdir(exist_ok=True)
    (WIKI_DIR / "classes").mkdir(exist_ok=True)
    (WIKI_DIR / "functions").mkdir(exist_ok=True)

    reverse = _build_reverse_index(graph)
    forward = _build_forward_index(graph)

    file_count = 0

    # ── File pages ────────────────────────────────────────────────────────

    for rel_path, fnode in sorted(graph.files.items()):
        slug = _slug(rel_path)
        tags = []
        if fnode.is_critical:
            tags.append("critical")
        if fnode.is_entry_point:
            tags.append("entry-point")

        incoming = reverse.get(rel_path, [])
        outgoing = forward.get(rel_path, [])

        imported_by = [e.from_id for e in incoming if e.relationship == "imports"]
        imports_to = [e.to_id for e in outgoing if e.relationship == "imports"]
        contains = [e.to_id for e in outgoing if e.relationship == "contains"]

        lines = [
            "---",
            "type: codebase-file",
            f"path: {rel_path}",
            f"module: {fnode.module_name}",
            f"lines: {fnode.line_count}",
            f"size: {fnode.size_bytes}",
        ]
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
        lines.extend(
            [
                f"generated: {graph.generated_at[:10]}",
                "---",
                "",
                f"# {rel_path}",
                "",
            ]
        )

        if fnode.is_critical:
            lines.append(
                "> **CRITICAL FILE** — Core infrastructure. Read before modifying.\n"
            )
        if fnode.is_entry_point:
            lines.append(
                "> **ENTRY POINT** — Contains `if __name__` or server start.\n"
            )

        # Description
        lines.append(f"{_truncate_docstring(fnode.docstring)}\n")

        # Stats
        lines.append(
            f"**Lines:** {fnode.line_count} | **Size:** {fnode.size_bytes:,} bytes\n"
        )

        # Imports (what this file depends on)
        if imports_to:
            lines.append("## Depends On\n")
            for dep in sorted(set(imports_to)):
                lines.append(f"- {_wikilink(dep)}")
            lines.append("")

        # Imported by (what depends on this file)
        if imported_by:
            lines.append("## Used By\n")
            for user in sorted(set(imported_by)):
                lines.append(f"- {_wikilink(user)}")
            lines.append("")

        # Contains
        if contains:
            lines.append("## Contains\n")
            for item_id in contains:
                if item_id in graph.classes:
                    cls = graph.classes[item_id]
                    lines.append(
                        f"- **class** {_wikilink(item_id)} — {len(cls.methods)} methods"
                    )
                elif item_id in graph.functions:
                    fn = graph.functions[item_id]
                    ret = f" → {fn.return_annotation}" if fn.return_annotation else ""
                    lines.append(
                        f"- **fn** {_wikilink(item_id)}`({', '.join(fn.args)}){ret}`"
                    )
            lines.append("")

        # Raw imports list
        if fnode.imports:
            lines.append("## Import Statements\n")
            lines.append("```python")
            for imp in fnode.imports:
                if imp["type"] == "import":
                    alias_part = f" as {imp['alias']}" if imp.get("alias") else ""
                    lines.append(f"import {imp['module']}{alias_part}")
                else:
                    name = imp.get("name", "*")
                    alias_part = f" as {imp['alias']}" if imp.get("alias") else ""
                    lines.append(f"from {imp['module']} import {name}{alias_part}")
            lines.append("```\n")

        md_path = WIKI_DIR / "files" / f"{slug}.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        file_count += 1

    # ── Class pages ───────────────────────────────────────────────────────

    for cls_id, cls in sorted(graph.classes.items()):
        slug = _slug(cls_id)
        incoming = reverse.get(cls_id, [])
        outgoing = forward.get(cls_id, [])

        inherits_from = [e.to_id for e in outgoing if e.relationship == "inherits"]
        inherited_by = [e.from_id for e in incoming if e.relationship == "inherits"]
        methods = [e.to_id for e in outgoing if e.relationship == "contains"]

        lines = [
            "---",
            "type: codebase-class",
            f"file: {cls.file_path}",
            f"line: {cls.line}",
            f"generated: {graph.generated_at[:10]}",
            "---",
            "",
            f"# {cls.name}",
            "",
            f"**File:** {_wikilink(cls.file_path)} | **Line:** {cls.line}\n",
            f"{_truncate_docstring(cls.docstring)}\n",
        ]

        if cls.bases:
            lines.append("## Inherits From\n")
            for base in cls.bases:
                if base in class_name_to_id:
                    lines.append(f"- {_wikilink(class_name_to_id[base])}")
                else:
                    lines.append(f"- `{base}`")
            lines.append("")

        if inherited_by:
            lines.append("## Inherited By\n")
            for child in inherited_by:
                lines.append(f"- {_wikilink(child)}")
            lines.append("")

        if methods:
            lines.append("## Methods\n")
            for method_id in methods:
                if method_id in graph.functions:
                    fn = graph.functions[method_id]
                    ret = f" → {fn.return_annotation}" if fn.return_annotation else ""
                    doc = (
                        (fn.docstring or "").split("\n")[0][:80] if fn.docstring else ""
                    )
                    lines.append(
                        f"- {_wikilink(method_id)}`({', '.join(fn.args)}){ret}` — {doc}"
                    )
            lines.append("")

        if cls.decorators:
            lines.append("## Decorators\n")
            for dec in cls.decorators:
                lines.append(f"- `@{dec}`")
            lines.append("")

        md_path = WIKI_DIR / "classes" / f"{slug}.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        file_count += 1

    # ── Function pages (only public, non-dunder) ─────────────────────────

    for fn_id, fn in sorted(graph.functions.items()):
        # Skip private/dunder methods for vault size control
        if fn.name.startswith("_") and not fn.name.startswith("__init__"):
            continue

        slug = _slug(fn_id)
        incoming = reverse.get(fn_id, [])
        outgoing = forward.get(fn_id, [])

        called_by = [e.from_id for e in incoming if e.relationship == "calls"]
        calls_to = [e.to_id for e in outgoing if e.relationship == "calls"]

        ret = f" → {fn.return_annotation}" if fn.return_annotation else ""
        title = f"{fn.class_name}.{fn.name}" if fn.class_name else fn.name

        lines = [
            "---",
            "type: codebase-function",
            f"file: {fn.file_path}",
            f"line: {fn.line}",
            f"generated: {graph.generated_at[:10]}",
            "---",
            "",
            f"# {title}",
            "",
            f"**File:** {_wikilink(fn.file_path)} | **Line:** {fn.line}",
            f"**Signature:** `{fn.name}({', '.join(fn.args)}){ret}`\n",
        ]

        if fn.class_name:
            cls_id_ref = f"{fn.file_path}::{fn.class_name}"
            lines.append(f"**Class:** {_wikilink(cls_id_ref)}\n")

        lines.append(f"{_truncate_docstring(fn.docstring)}\n")

        if calls_to:
            lines.append("## Calls\n")
            for target in sorted(set(calls_to))[:20]:
                lines.append(f"- {_wikilink(target)}")
            lines.append("")

        if called_by:
            lines.append("## Called By\n")
            for caller in sorted(set(called_by))[:20]:
                lines.append(f"- {_wikilink(caller)}")
            lines.append("")

        if fn.decorators:
            lines.append("## Decorators\n")
            for dec in fn.decorators:
                lines.append(f"- `@{dec}`")
            lines.append("")

        md_path = WIKI_DIR / "functions" / f"{slug}.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        file_count += 1

    # ── Module summary pages ──────────────────────────────────────────────

    modules: dict[str, list[str]] = defaultdict(list)
    for rel_path in graph.files:
        top = rel_path.split("/")[0]
        modules[top].append(rel_path)

    for mod_name, file_paths in sorted(modules.items()):
        total_lines = sum(graph.files[f].line_count for f in file_paths)
        total_classes = sum(len(graph.files[f].classes) for f in file_paths)
        total_functions = sum(len(graph.files[f].functions) for f in file_paths)
        critical = [f for f in file_paths if graph.files[f].is_critical]
        entries = [f for f in file_paths if graph.files[f].is_entry_point]

        lines = [
            "---",
            "type: codebase-module",
            f"generated: {graph.generated_at[:10]}",
            "---",
            "",
            f"# {mod_name}/",
            "",
            f"**Files:** {len(file_paths)} | "
            f"**Lines:** {total_lines:,} | "
            f"**Classes:** {total_classes} | "
            f"**Functions:** {total_functions}\n",
        ]

        if critical:
            lines.append("## Critical Files\n")
            for f in sorted(critical):
                lines.append(f"- {_wikilink(f)}")
            lines.append("")

        if entries:
            lines.append("## Entry Points\n")
            for f in sorted(entries):
                lines.append(f"- {_wikilink(f)}")
            lines.append("")

        lines.append("## All Files\n")
        for f in sorted(file_paths):
            fnode = graph.files[f]
            tag = ""
            if fnode.is_critical:
                tag = " **[CRITICAL]**"
            elif fnode.is_entry_point:
                tag = " *[entry]*"
            doc_line = (
                (fnode.docstring or "").split("\n")[0][:60] if fnode.docstring else ""
            )
            lines.append(
                f"- {_wikilink(f)} ({fnode.line_count} lines){tag} — {doc_line}"
            )
        lines.append("")

        md_path = WIKI_DIR / "modules" / f"{mod_name}.md"
        md_path.write_text("\n".join(lines), encoding="utf-8")
        file_count += 1

    # ── Index page ────────────────────────────────────────────────────────

    _generate_index(graph, modules, file_count)

    # ── Cloud context ─────────────────────────────────────────────────────

    _generate_cloud(graph)

    print(f"[obsidian] Generated {file_count} markdown files in {WIKI_DIR}")


def _generate_index(
    graph: CodebaseGraph,
    modules: dict[str, list[str]],
    total_pages: int,
) -> None:
    """Generate the index.md for the codebase graph."""
    lines = [
        "---",
        "type: codebase-index",
        f"generated: {graph.generated_at[:10]}",
        "---",
        "",
        "# Codebase Knowledge Graph",
        "",
        f"Auto-generated map of the EOS codebase. "
        f"**{total_pages}** pages covering "
        f"**{graph.stats['files']}** files, "
        f"**{graph.stats['classes']}** classes, "
        f"**{graph.stats['functions']}** functions.\n",
        "## How to Use This Graph\n",
        "1. Start here at the index",
        "2. Navigate to a module overview for high-level understanding",
        "3. Follow wikilinks to specific files, classes, or functions",
        "4. Each page shows dependencies (Depends On) and dependents (Used By)",
        "5. See [[cloud]] for AI agent instructions\n",
        "## Modules\n",
    ]

    for mod_name, file_paths in sorted(modules.items()):
        total_lines = sum(graph.files[f].line_count for f in file_paths)
        lines.append(
            f"- [[{mod_name}]] — {len(file_paths)} files, {total_lines:,} lines"
        )
    lines.append("")

    # Critical files
    critical = [rel for rel, f in graph.files.items() if f.is_critical]
    if critical:
        lines.append("## Critical Files\n")
        lines.append("These are core infrastructure files. Read before modifying.\n")
        for f in sorted(critical):
            fnode = graph.files[f]
            doc = (fnode.docstring or "").split("\n")[0][:60]
            lines.append(f"- {_wikilink(f)} — {doc}")
        lines.append("")

    # Entry points
    entries = [rel for rel, f in graph.files.items() if f.is_entry_point]
    if entries:
        lines.append("## Entry Points\n")
        for f in sorted(entries):
            lines.append(f"- {_wikilink(f)}")
        lines.append("")

    # Top-level stats
    lines.extend(
        [
            "## Stats\n",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Files | {graph.stats['files']} |",
            f"| Classes | {graph.stats['classes']} |",
            f"| Functions | {graph.stats['functions']} |",
            f"| Edges | {graph.stats['edges']} |",
            f"| Total Lines | {graph.stats['total_lines']:,} |",
            f"| Entry Points | {graph.stats['entry_points']} |",
            f"| Critical Files | {graph.stats['critical_files']} |",
            "",
        ]
    )

    edge_types = graph.stats.get("edges_by_type", {})
    if edge_types:
        lines.append("### Edge Types\n")
        for etype, count in sorted(edge_types.items(), key=lambda x: -x[1]):
            lines.append(f"- **{etype}**: {count}")
        lines.append("")

    INDEX_MD.write_text("\n".join(lines), encoding="utf-8")


def _generate_cloud(graph: CodebaseGraph) -> None:
    """Generate cloud.md — the AI context instruction file."""
    content = textwrap.dedent(f"""\
    ---
    type: codebase-cloud
    generated: {graph.generated_at[:10]}
    ---

    # Cloud Context — Codebase Knowledge Graph

    This file instructs AI agents on how to use the preloaded
    codebase knowledge graph stored in `10_Wiki/codebase/`.

    ## What This Is

    A persistent, structured knowledge graph of the entire EOS codebase.
    It contains {graph.stats["files"]} files, {graph.stats["classes"]} classes,
    and {graph.stats["functions"]} functions with full dependency mapping.

    Every node (file, class, function) is a markdown page with:
    - What it depends on (Depends On section with wikilinks)
    - What depends on it (Used By section with wikilinks)
    - What it contains (classes, functions)
    - Docstring summary
    - Line count and location

    ## How to Navigate

    ```
    10_Wiki/codebase/
      index.md          ← Start here. Module list, critical files, entry points.
      cloud.md          ← This file. AI instructions.
      modules/          ← One page per top-level directory (eos_ai, services, etc.)
      files/            ← One page per Python file with full dependency map
      classes/          ← One page per class with methods and inheritance
      functions/        ← One page per public function with call graph
    ```

    ## Rules for AI Agents

    1. **Always check this graph first** before scanning files.
       The graph already knows every file, class, function, and dependency.

    2. **Only open a file when you need to read implementation details.**
       The graph gives you structure and relationships — you only need
       the actual source when you need to understand logic.

    3. **Use the dependency map to understand impact.**
       Before modifying a file, check its "Used By" section to understand
       what will be affected.

    4. **Start from modules, drill into files.**
       `modules/eos_ai.md` gives you the full module overview.
       Follow wikilinks to specific files.

    5. **Critical files require extra care.**
       Files tagged `critical` are core infrastructure. Read the file
       AND its dependents before making changes.

    6. **Entry points are where execution starts.**
       Files tagged `entry-point` contain `if __name__` blocks or
       server start logic. These are the roots of the call graph.

    ## Machine-Readable Graph

    The full graph is also available as JSON at:
    `data/codebase_graph.json`

    Use this for programmatic queries, custom analysis, or
    feeding into other tools.

    ## Freshness

    This graph was generated on {graph.generated_at[:10]}.
    Run `scripts/update-graph` to rebuild after code changes.
    The graph does NOT auto-update — treat it as a snapshot.
    If a file referenced in the graph doesn't exist, the graph is stale.
    """)

    CLOUD_MD.write_text(content, encoding="utf-8")


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build persistent codebase knowledge graph for EOS"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Export JSON only, skip Obsidian generation",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print stats and exit",
    )
    parser.add_argument(
        "--module",
        type=str,
        default=None,
        help="Scan a single module (e.g., eos_ai.gateway)",
    )
    args = parser.parse_args()

    print(f"[codebase_graph] Starting scan at {datetime.now(timezone.utc).isoformat()}")
    graph = scan_codebase(target_module=args.module)

    if args.stats:
        print(json.dumps(graph.stats, indent=2))
        return

    export_json(graph)

    if not args.json_only:
        # Need class_name_to_id in scope for class page generation
        global class_name_to_id
        class_name_to_id = {}
        for cls_id, cls in graph.classes.items():
            class_name_to_id[cls.name] = cls_id

        generate_obsidian(graph)

    print(
        f"[codebase_graph] Done. Graph: {graph.stats['files']} files, "
        f"{graph.stats['edges']} edges."
    )


if __name__ == "__main__":
    main()
