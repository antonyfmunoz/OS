#!/usr/bin/env python3
"""incremental_graph.py — Dirty-set incremental updates for the codebase graph.

Rebuilds ONLY the parts of data/codebase_graph.json affected by a small set
of changed files. Falls back to a full rebuild (via scripts/codebase_graph.py)
when the change set is too large or the dirty region becomes inconsistent.

Strategy
--------
  1. Load the persisted graph JSON.
  2. Resolve each changed path to a graph file-id (or mark as new/deleted).
  3. Compute dirty-set = {changed files} ∪ {1-hop dependents via file imports}.
  4. For each file in the dirty-set:
        - if deleted → strip its file/class/function nodes and all edges
          touching them.
        - if created or edited → parse with scan_file(); replace the node
          entries in graph.files / classes / functions.
  5. Strip every edge where from_id or to_id belongs to a dirty-set node.
  6. Rebuild lookup maps (module_to_path, class_name_to_id,
     file_import_targets, fn_by_file_and_name) from the merged graph.
  7. Recompute edges (contains/imports/inherits/calls) for the dirty-set only.
  8. Update stats, bump generated_at, write back to disk.

Fallback (→ full rebuild via scripts/codebase_graph.py)
  - Dirty-set exceeds MAX_DIRTY_RATIO of total files.
  - Parser raises unexpected exception.
  - Graph file is unreadable or missing required keys.
  - File deleted but still referenced by non-dirty edges after the pass
    (graph corruption guard).
  - Caller explicitly requests mode="full".

CLI
---
    python3 scripts/incremental_graph.py path/a.py path/b.py
    python3 scripts/incremental_graph.py --mode full        # force rebuild
    python3 scripts/incremental_graph.py --dry-run path/a.py
    python3 scripts/incremental_graph.py --stdin            # read paths from stdin
    python3 scripts/incremental_graph.py --stats

Programmatic
------------
    from scripts.incremental_graph import update
    report = update(["eos_ai/memory.py"])
    # {'mode': 'incremental', 'dirty_files': 3, 'edges_added': 8, ...}
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, "/opt/OS")

# Reuse the canonical scanner so incremental cannot drift from full rebuild.
from scripts.codebase_graph import (  # noqa: E402
    CodebaseGraph,
    ClassNode,
    Edge,
    FileNode,
    FunctionNode,
    NON_PYTHON_EXTENSIONS,
    ROOT,
    SCAN_DIRS,
    SKIP_DIRS,
    SKIP_FILES,
    _module_name,
    scan_file,
)

try:
    from parsers import REGISTRY as PARSER_REGISTRY
except Exception:  # pragma: no cover
    PARSER_REGISTRY = []  # type: ignore[assignment]

GRAPH_JSON = ROOT / "data" / "codebase_graph.json"
FULL_REBUILD_SCRIPT = ROOT / "scripts" / "codebase_graph.py"

# Safety: if the dirty-set grows beyond this fraction of the graph, full rebuild
# is cheaper than carefully surgical incremental + it guarantees correctness.
MAX_DIRTY_RATIO = 0.30
# Absolute cap — never go incremental on massive changesets regardless of ratio.
MAX_DIRTY_ABSOLUTE = 200


# ─── Graph (de)serialization ─────────────────────────────────────────────────


def _load_graph() -> dict[str, Any]:
    if not GRAPH_JSON.exists():
        raise FileNotFoundError(f"{GRAPH_JSON} missing — run scripts/update-graph first")
    return json.loads(GRAPH_JSON.read_text())


def _save_graph(data: dict[str, Any]) -> None:
    GRAPH_JSON.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_JSON.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ─── Path normalization ──────────────────────────────────────────────────────


def _rel(path: str | Path) -> str:
    """Normalize a path to the rel-from-ROOT form the graph uses."""
    p = Path(path)
    if p.is_absolute():
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)
    return str(p)


def _is_tracked(rel: str) -> bool:
    """True if a relative path falls under SCAN_DIRS and is not excluded."""
    parts = Path(rel).parts
    if not parts:
        return False
    if parts[0] not in SCAN_DIRS:
        return False
    if any(part in SKIP_DIRS for part in parts):
        return False
    if Path(rel).name in SKIP_FILES:
        return False
    return True


def _classify(rel: str) -> str:
    """Return 'python', 'non_python', or 'skip' for an in-scope file."""
    suffix = Path(rel).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in NON_PYTHON_EXTENSIONS:
        return "non_python"
    return "skip"


# ─── Dependents computation (from persisted graph) ───────────────────────────


def _file_imported_by(graph: dict[str, Any]) -> dict[str, set[str]]:
    """Build reverse file-import map from the persisted edges list."""
    reverse: dict[str, set[str]] = defaultdict(set)
    for e in graph.get("edges", []):
        if e.get("relationship") == "imports" and e.get("from_type") == "file":
            reverse[e["to_id"]].add(e["from_id"])
    return reverse


def _compute_dirty_set(
    graph: dict[str, Any], changed_rels: list[str]
) -> tuple[set[str], set[str], set[str]]:
    """Return (dirty_python, dirty_non_python, deleted) sets.

    Dirty-set for python files = changed python ∪ 1-hop dependents of changed
    python files. Non-python files don't get dependent expansion (the Python
    scope doesn't carry call/import edges into them).
    """
    reverse = _file_imported_by(graph)
    dirty_py: set[str] = set()
    dirty_np: set[str] = set()
    deleted: set[str] = set()

    known_py = set(graph.get("files", {}).keys())
    known_np = set(graph.get("non_python_files", {}).keys())

    for rel in changed_rels:
        abs_path = ROOT / rel
        exists = abs_path.exists()
        kind = _classify(rel) if _is_tracked(rel) else "skip"

        if kind == "python":
            if not exists:
                if rel in known_py:
                    deleted.add(rel)
                continue
            dirty_py.add(rel)
            # 1-hop dependents: every file that imports this one.
            dirty_py.update(reverse.get(rel, set()))
        elif kind == "non_python":
            if not exists:
                if rel in known_np:
                    deleted.add(rel)
                continue
            dirty_np.add(rel)
        # "skip" is silently ignored.

    return dirty_py, dirty_np, deleted


# ─── Edge / node stripping ───────────────────────────────────────────────────


def _node_ids_for_files(graph: dict[str, Any], files: Iterable[str]) -> set[str]:
    """Every file/class/function id owned by the given set of file paths."""
    ids: set[str] = set(files)
    for cls_id, cls in graph.get("classes", {}).items():
        if cls.get("file_path") in files:
            ids.add(cls_id)
    for fn_id, fn in graph.get("functions", {}).items():
        if fn.get("file_path") in files:
            ids.add(fn_id)
    return ids


def _strip_dirty(graph: dict[str, Any], dirty_files: set[str]) -> None:
    """Remove nodes and edges belonging to the dirty file set, in place."""
    # Remove file nodes.
    graph["files"] = {
        k: v for k, v in graph.get("files", {}).items() if k not in dirty_files
    }
    # Remove classes owned by dirty files.
    graph["classes"] = {
        k: v
        for k, v in graph.get("classes", {}).items()
        if v.get("file_path") not in dirty_files
    }
    # Remove functions owned by dirty files.
    graph["functions"] = {
        k: v
        for k, v in graph.get("functions", {}).items()
        if v.get("file_path") not in dirty_files
    }

    # Build the full set of node ids that belonged to dirty files BEFORE
    # stripping, so we can prune every touching edge.
    # NB: the ids we want are the ones the graph had *before* the strips above,
    # but since we only trimmed by membership, rebuilding from "leftover edges
    # whose endpoints no longer exist" is also safe. We use both for belt+braces.
    live_ids = (
        set(graph["files"].keys())
        | set(graph["classes"].keys())
        | set(graph["functions"].keys())
    )
    kept_edges = []
    for e in graph.get("edges", []):
        if e["from_id"] in dirty_files or e["to_id"] in dirty_files:
            continue
        # Endpoints must still exist in the graph (unless they're files we kept).
        # For non-file endpoints, prune if dangling.
        if e["from_type"] in ("class", "function") and e["from_id"] not in live_ids:
            continue
        if e["to_type"] in ("class", "function") and e["to_id"] not in live_ids:
            continue
        # File endpoints may legitimately point at files that still exist.
        if e["from_type"] == "file" and e["from_id"] not in graph["files"]:
            continue
        if e["to_type"] == "file" and e["to_id"] not in graph["files"]:
            continue
        kept_edges.append(e)
    graph["edges"] = kept_edges


def _strip_non_python(graph: dict[str, Any], dirty_np: set[str]) -> None:
    npf = graph.get("non_python_files") or {}
    for rel in dirty_np:
        npf.pop(rel, None)
    graph["non_python_files"] = npf


# ─── Re-scan dirty files ─────────────────────────────────────────────────────


def _scan_python_files(dirty: set[str]) -> tuple[
    dict[str, FileNode], dict[str, ClassNode], dict[str, FunctionNode]
]:
    """Parse the dirty python files. Raises on SyntaxError so caller can
    decide whether to fall back to full rebuild."""
    files: dict[str, FileNode] = {}
    classes: dict[str, ClassNode] = {}
    functions: dict[str, FunctionNode] = {}
    for rel in sorted(dirty):
        abs_path = ROOT / rel
        if not abs_path.exists():
            continue
        file_node, cls_list, fn_list = scan_file(abs_path)
        files[file_node.path] = file_node
        for cls in cls_list:
            classes[f"{file_node.path}::{cls.name}"] = cls
        for fn in fn_list:
            if fn.class_name:
                fn_id = f"{file_node.path}::{fn.class_name}.{fn.name}"
            else:
                fn_id = f"{file_node.path}::{fn.name}"
            functions[fn_id] = fn
    return files, classes, functions


def _scan_non_python_file(rel: str) -> dict[str, Any] | None:
    """Run the modular parser registry against a single non-python file."""
    if not PARSER_REGISTRY:
        return None
    path = ROOT / rel
    if not path.exists():
        return None
    for parser in PARSER_REGISTRY:
        if not parser.handles(path):
            continue
        try:
            parsed = parser.parse(path)
        except Exception as exc:  # pragma: no cover — fall through
            print(f"[incremental] parser {parser.language} failed on {rel}: {exc}")
            return None
        return {
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
    return None


# ─── Edge recomputation for dirty set ────────────────────────────────────────


def _edge_to_dict(e: Edge) -> dict[str, str]:
    return {
        "from_type": e.from_type,
        "from_id": e.from_id,
        "to_type": e.to_type,
        "to_id": e.to_id,
        "relationship": e.relationship,
    }


def _recompute_edges_for_dirty(
    graph: dict[str, Any],
    new_files: dict[str, FileNode],
    new_classes: dict[str, ClassNode],
    new_functions: dict[str, FunctionNode],
) -> list[dict[str, str]]:
    """Compute the edges that the dirty files contribute. Uses the GLOBAL
    lookup maps (built from the merged graph state) so cross-file resolution
    stays consistent with how codebase_graph.py would have resolved them.
    """
    # After _strip_dirty, graph.files/classes/functions are the NON-dirty
    # leftover. We rebuild global maps against (non-dirty ∪ new dirty).
    all_files = dict(graph["files"])
    for rel, fn in new_files.items():
        all_files[rel] = asdict(fn)

    all_classes = dict(graph["classes"])
    for cid, cls in new_classes.items():
        all_classes[cid] = asdict(cls)

    all_functions = dict(graph["functions"])
    for fid, fn in new_functions.items():
        all_functions[fid] = asdict(fn)

    # module_name → rel_path
    module_to_path: dict[str, str] = {}
    for rel, f in all_files.items():
        mod = f.get("module_name")
        if mod:
            module_to_path[mod] = rel

    # class_name → fully-qualified id (first-wins like the full builder)
    class_name_to_id: dict[str, str] = {}
    for cid, c in all_classes.items():
        name = c.get("name")
        if name and name not in class_name_to_id:
            class_name_to_id[name] = cid

    new_edges: list[dict[str, str]] = []

    # ── Contains edges (file→class, file→function, class→method) ────────
    for rel, fn in new_files.items():
        for cls_id in fn.classes:
            new_edges.append(
                {
                    "from_type": "file",
                    "from_id": rel,
                    "to_type": "class",
                    "to_id": cls_id,
                    "relationship": "contains",
                }
            )
        for fn_id in fn.functions:
            fn_obj = new_functions.get(fn_id)
            if fn_obj and fn_obj.class_name:
                cls_id = f"{rel}::{fn_obj.class_name}"
                new_edges.append(
                    {
                        "from_type": "class",
                        "from_id": cls_id,
                        "to_type": "function",
                        "to_id": fn_id,
                        "relationship": "contains",
                    }
                )
            else:
                new_edges.append(
                    {
                        "from_type": "file",
                        "from_id": rel,
                        "to_type": "function",
                        "to_id": fn_id,
                        "relationship": "contains",
                    }
                )

    # ── Import edges (file→file) for dirty files ────────────────────────
    for rel, fn in new_files.items():
        for imp in fn.imports:
            mod = imp.get("module") or ""
            resolved = None
            if mod in module_to_path:
                resolved = module_to_path[mod]
            else:
                for known_mod, known_path in module_to_path.items():
                    if mod.startswith(known_mod) or known_mod.startswith(mod):
                        resolved = known_path
                        break
            if resolved and resolved != rel:
                new_edges.append(
                    {
                        "from_type": "file",
                        "from_id": rel,
                        "to_type": "file",
                        "to_id": resolved,
                        "relationship": "imports",
                    }
                )

    # ── Inherits edges (class→class) for dirty classes ──────────────────
    for cid, cls in new_classes.items():
        for base in cls.bases:
            base_name = base.split(".")[-1]
            target = class_name_to_id.get(base_name)
            if target and target != cid:
                new_edges.append(
                    {
                        "from_type": "class",
                        "from_id": cid,
                        "to_type": "class",
                        "to_id": target,
                        "relationship": "inherits",
                    }
                )

    # ── Call edges (function→function) for dirty functions ──────────────
    # Build file→imported files map (same scope the full builder uses)
    file_import_targets: dict[str, set[str]] = defaultdict(set)
    for e in graph["edges"]:
        if e.get("relationship") == "imports" and e.get("from_type") == "file":
            file_import_targets[e["from_id"]].add(e["to_id"])
    for e in new_edges:
        if e["relationship"] == "imports" and e["from_type"] == "file":
            file_import_targets[e["from_id"]].add(e["to_id"])

    fn_by_file_and_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fid, f in all_functions.items():
        fn_by_file_and_name[(f["file_path"], f["name"])].append(fid)

    dirty_fn_ids = set(new_functions.keys())
    for fid in dirty_fn_ids:
        fn = new_functions[fid]
        candidate_files = {fn.file_path} | file_import_targets.get(fn.file_path, set())
        for call_name in fn.calls:
            for cfile in candidate_files:
                for target_id in fn_by_file_and_name.get((cfile, call_name), []):
                    if target_id != fid:
                        new_edges.append(
                            {
                                "from_type": "function",
                                "from_id": fid,
                                "to_type": "function",
                                "to_id": target_id,
                                "relationship": "calls",
                            }
                        )

    # Dedupe exact duplicates (rare but possible on re-runs).
    seen = set()
    unique: list[dict[str, str]] = []
    for e in new_edges:
        key = (e["from_type"], e["from_id"], e["to_type"], e["to_id"], e["relationship"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    return unique


# ─── Stats recomputation ─────────────────────────────────────────────────────


def _recompute_stats(graph: dict[str, Any]) -> None:
    files = graph.get("files", {})
    edges = graph.get("edges", [])
    stats = {
        "files": len(files),
        "classes": len(graph.get("classes", {})),
        "functions": len(graph.get("functions", {})),
        "edges": len(edges),
        "total_lines": sum(f.get("line_count", 0) for f in files.values()),
        "total_bytes": sum(f.get("size_bytes", 0) for f in files.values()),
        "entry_points": sum(1 for f in files.values() if f.get("is_entry_point")),
        "critical_files": sum(1 for f in files.values() if f.get("is_critical")),
    }
    rel_counts: dict[str, int] = defaultdict(int)
    for e in edges:
        rel_counts[e.get("relationship", "?")] += 1
    stats["edges_by_type"] = dict(rel_counts)
    stats["non_python_files"] = len(graph.get("non_python_files") or {})
    stats["languages"] = dict(graph.get("languages") or {})
    if "python" not in stats["languages"]:
        stats["languages"]["python"] = stats["files"]
    graph["stats"] = stats


# ─── Full rebuild fallback ───────────────────────────────────────────────────


def _run_full_rebuild(reason: str) -> dict[str, Any]:
    """Shell out to the canonical full-rebuild pipeline."""
    print(f"[incremental] → FULL REBUILD ({reason})")
    start = time.monotonic()
    result = subprocess.run(
        ["python3", str(FULL_REBUILD_SCRIPT), "--json-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    duration = time.monotonic() - start
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(
            f"full rebuild failed (exit {result.returncode}) after {duration:.1f}s"
        )
    return {
        "mode": "full",
        "reason": reason,
        "duration_seconds": round(duration, 3),
        "dirty_files": 0,
        "edges_added": 0,
        "edges_removed": 0,
    }


# ─── Public API ──────────────────────────────────────────────────────────────


def update(
    changed_paths: list[str],
    *,
    mode: str = "auto",
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Update the graph incrementally for the given changed paths.

    mode:
        "auto"        — incremental if safe, else full rebuild
        "incremental" — force incremental (may still fall back on error)
        "full"        — skip dirty-set logic and run full rebuild
    """
    start = time.monotonic()

    if mode == "full":
        if dry_run:
            return {"mode": "full", "dry_run": True, "reason": "forced"}
        return _run_full_rebuild(reason="forced")

    try:
        graph = _load_graph()
    except FileNotFoundError:
        return _run_full_rebuild(reason="no existing graph")

    required_keys = {"files", "classes", "functions", "edges"}
    if not required_keys.issubset(graph.keys()):
        return _run_full_rebuild(reason="graph missing required keys")

    changed_rels = [_rel(p) for p in changed_paths]
    # Drop paths that aren't in any tracked scan dir.
    changed_rels = [r for r in changed_rels if _is_tracked(r)]

    if not changed_rels:
        if verbose:
            print("[incremental] no tracked paths in change set, no-op")
        return {
            "mode": "noop",
            "dirty_files": 0,
            "duration_seconds": round(time.monotonic() - start, 3),
        }

    dirty_py, dirty_np, deleted = _compute_dirty_set(graph, changed_rels)

    total_py = max(len(graph.get("files", {})), 1)
    dirty_total = len(dirty_py) + len(deleted)
    if (
        dirty_total > MAX_DIRTY_ABSOLUTE
        or (dirty_total / total_py) > MAX_DIRTY_RATIO
    ):
        reason = f"dirty-set too large ({dirty_total}/{total_py})"
        if dry_run:
            return {"mode": "full", "dry_run": True, "reason": reason}
        return _run_full_rebuild(reason=reason)

    if verbose:
        print(
            f"[incremental] changed={len(changed_rels)} dirty_py={len(dirty_py)} "
            f"dirty_np={len(dirty_np)} deleted={len(deleted)}"
        )

    if dry_run:
        return {
            "mode": "incremental",
            "dry_run": True,
            "dirty_files": len(dirty_py),
            "dirty_non_python": len(dirty_np),
            "deleted": len(deleted),
            "would_rebuild": sorted(dirty_py),
        }

    # ── Python pass ───────────────────────────────────────────────────────
    strip_set: set[str] = set(dirty_py) | deleted
    edges_before = len(graph.get("edges", []))
    _strip_dirty(graph, strip_set)

    try:
        new_files, new_classes, new_functions = _scan_python_files(dirty_py)
    except Exception as exc:
        return _run_full_rebuild(reason=f"scan error: {exc}")

    # Merge parsed nodes back in.
    for rel, fn in new_files.items():
        graph["files"][rel] = asdict(fn)
    for cid, cls in new_classes.items():
        graph["classes"][cid] = asdict(cls)
    for fid, f in new_functions.items():
        graph["functions"][fid] = asdict(f)

    # Recompute edges ONLY for the dirty set; append to the stripped list.
    new_edges = _recompute_edges_for_dirty(
        graph, new_files, new_classes, new_functions
    )
    graph["edges"].extend(new_edges)
    edges_after_py = len(graph["edges"])

    # ── Non-Python pass ──────────────────────────────────────────────────
    if dirty_np:
        _strip_non_python(graph, dirty_np)
        npf = graph.get("non_python_files") or {}
        langs = graph.get("languages") or {}
        # Rebuild language counts from scratch to stay honest (cheap over np set).
        # We only add the dirty files back; counts for untouched files are still
        # in npf, so recomputing from npf is correct.
        for rel in sorted(dirty_np):
            parsed = _scan_non_python_file(rel)
            if parsed is not None:
                npf[rel] = parsed
        graph["non_python_files"] = npf
        # Recompute language counts from the updated npf map.
        lang_counts: dict[str, int] = defaultdict(int)
        for f in npf.values():
            lang_counts[f.get("language", "?")] += 1
        graph["languages"] = dict(lang_counts)

    # ── Post-checks: reject if the graph is obviously inconsistent ───────
    live_file_ids = set(graph["files"].keys())
    for e in graph["edges"]:
        if e.get("from_type") == "file" and e["from_id"] not in live_file_ids:
            return _run_full_rebuild(
                reason=f"orphaned file edge {e['from_id']}→{e['to_id']}"
            )

    # ── Finalize ─────────────────────────────────────────────────────────
    graph["generated_at"] = datetime.now(timezone.utc).isoformat()
    _recompute_stats(graph)
    _save_graph(graph)

    duration = time.monotonic() - start
    report = {
        "mode": "incremental",
        "dirty_files": len(dirty_py),
        "dirty_non_python": len(dirty_np),
        "deleted": len(deleted),
        "edges_before": edges_before,
        "edges_after": len(graph["edges"]),
        "edges_added": len(new_edges),
        "edges_removed": edges_before + len(new_edges) - edges_after_py + (
            edges_after_py - len(graph["edges"])
        ),
        "duration_seconds": round(duration, 3),
    }
    if verbose:
        print(f"[incremental] {report}")
    return report


# ─── CLI ─────────────────────────────────────────────────────────────────────


def _print_stats() -> int:
    try:
        g = _load_graph()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2
    print(json.dumps(g.get("stats", {}), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="incremental_graph")
    p.add_argument("paths", nargs="*", help="changed file paths (rel or abs)")
    p.add_argument(
        "--mode",
        choices=["auto", "incremental", "full"],
        default="auto",
        help="auto (default): fall back to full on inconsistency",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stdin", action="store_true", help="read paths from stdin")
    p.add_argument("--stats", action="store_true", help="print current graph stats")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    if args.stats:
        return _print_stats()

    paths = list(args.paths)
    if args.stdin:
        paths.extend(line.strip() for line in sys.stdin if line.strip())

    if not paths and args.mode != "full":
        print("no paths supplied (use --stdin or --mode full)", file=sys.stderr)
        return 2

    try:
        report = update(
            paths, mode=args.mode, dry_run=args.dry_run, verbose=args.verbose
        )
    except Exception as exc:
        print(f"[incremental] ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
