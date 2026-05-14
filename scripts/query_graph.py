#!/usr/bin/env python3
"""query_graph.py — Retrieval layer over the EOS codebase knowledge graph.

Reads data/codebase_graph.json and answers structural questions without
opening source files. Use this BEFORE grepping or reading implementations.

CLI:
    python3 scripts/query_graph.py deps <node>
    python3 scripts/query_graph.py dependents <node>
    python3 scripts/query_graph.py path <from> <to>
    python3 scripts/query_graph.py entry-points
    python3 scripts/query_graph.py critical
    python3 scripts/query_graph.py centrality [--top N]
    python3 scripts/query_graph.py search <term>
    python3 scripts/query_graph.py stats
    python3 scripts/query_graph.py freshness

Programmatic:
    from scripts.query_graph import GraphQuery
    q = GraphQuery.load()
    q.dependents("state/memory/memory.py")
    q.path("services/discord_bot.py", "runtime/db.py")

A node can be a file path (runtime/memory.py), a module
(runtime.memory), a class id (runtime/memory.py::Memory), or
a function id (runtime/memory.py::Memory.remember).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import os
ROOT = Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
GRAPH_JSON = ROOT / "data" / "codebase_graph.json"
STALE_HOURS = 24


@dataclass
class GraphQuery:
    """Indexed view of the codebase graph with traversal + ranking."""

    raw: dict[str, Any]
    out_edges: dict[str, list[tuple[str, str]]]  # node -> [(neighbor, rel)]
    in_edges: dict[str, list[tuple[str, str]]]
    file_imports: dict[str, set[str]]  # file -> {imported file}
    file_imported_by: dict[str, set[str]]

    @classmethod
    def load(cls, path: Path = GRAPH_JSON) -> "GraphQuery":
        if not path.exists():
            raise FileNotFoundError(
                f"Graph not found at {path}. Run scripts/update-graph first."
            )
        raw = json.loads(path.read_text())
        out_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)
        in_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for e in raw.get("edges", []):
            out_edges[e["from_id"]].append((e["to_id"], e["relationship"]))
            in_edges[e["to_id"]].append((e["from_id"], e["relationship"]))

        # File-level import graph (resolve module imports to file paths).
        module_to_file: dict[str, str] = {}
        for path_str, file in raw.get("files", {}).items():
            module_to_file[file["module_name"]] = path_str

        file_imports: dict[str, set[str]] = defaultdict(set)
        for path_str, file in raw.get("files", {}).items():
            for imp in file.get("imports", []):
                mod = imp.get("module") or ""
                # Match longest module prefix available.
                candidate = None
                while mod:
                    if mod in module_to_file:
                        candidate = module_to_file[mod]
                        break
                    if "." not in mod:
                        break
                    mod = mod.rsplit(".", 1)[0]
                if candidate and candidate != path_str:
                    file_imports[path_str].add(candidate)

        file_imported_by: dict[str, set[str]] = defaultdict(set)
        for src, targets in file_imports.items():
            for t in targets:
                file_imported_by[t].add(src)

        return cls(
            raw=raw,
            out_edges=dict(out_edges),
            in_edges=dict(in_edges),
            file_imports=dict(file_imports),
            file_imported_by=dict(file_imported_by),
        )

    # ─── Node resolution ─────────────────────────────────────────────────

    def resolve(self, token: str) -> str | None:
        """Resolve a user-supplied token to a node id in the graph."""
        if token in self.raw.get("files", {}):
            return token
        if token in self.raw.get("classes", {}):
            return token
        if token in self.raw.get("functions", {}):
            return token
        # module name -> file
        for path_str, f in self.raw.get("files", {}).items():
            if f["module_name"] == token:
                return path_str
        # bare filename
        for path_str in self.raw.get("files", {}):
            if path_str.endswith("/" + token) or path_str == token:
                return path_str
        return None

    # ─── Core queries ────────────────────────────────────────────────────

    def dependencies(self, node: str) -> list[str]:
        """What this node depends on (what it imports or calls)."""
        resolved = self.resolve(node) or node
        if resolved in self.file_imports:
            return sorted(self.file_imports[resolved])
        return sorted({t for t, _ in self.out_edges.get(resolved, [])})

    def dependents(self, node: str) -> list[str]:
        """What depends on this node (reverse lookup)."""
        resolved = self.resolve(node) or node
        if resolved in self.file_imported_by:
            return sorted(self.file_imported_by[resolved])
        return sorted({s for s, _ in self.in_edges.get(resolved, [])})

    def path(self, src: str, dst: str, max_depth: int = 6) -> list[str] | None:
        """BFS over the file-level import graph between two files."""
        src_r = self.resolve(src)
        dst_r = self.resolve(dst)
        if not src_r or not dst_r:
            return None
        if src_r == dst_r:
            return [src_r]
        visited = {src_r}
        queue: deque[list[str]] = deque([[src_r]])
        while queue:
            path = queue.popleft()
            if len(path) > max_depth:
                continue
            current = path[-1]
            for neighbor in self.file_imports.get(current, ()):
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == dst_r:
                    return new_path
                visited.add(neighbor)
                queue.append(new_path)
        return None

    def entry_points(self) -> list[str]:
        return sorted(
            p
            for p, f in self.raw.get("files", {}).items()
            if f.get("is_entry_point")
        )

    def critical_files(self) -> list[str]:
        return sorted(
            p for p, f in self.raw.get("files", {}).items() if f.get("is_critical")
        )

    def centrality(self, top: int = 25) -> list[tuple[str, int, int]]:
        """Rank files by (imported_by + imports) — simple centrality proxy."""
        scored = []
        for path_str in self.raw.get("files", {}):
            inbound = len(self.file_imported_by.get(path_str, ()))
            outbound = len(self.file_imports.get(path_str, ()))
            scored.append((path_str, inbound, outbound))
        scored.sort(key=lambda r: (r[1] * 2 + r[2]), reverse=True)
        return scored[:top]

    def search(self, term: str) -> list[str]:
        term_l = term.lower()
        hits: list[str] = []
        for path_str, f in self.raw.get("files", {}).items():
            if term_l in path_str.lower() or term_l in (f.get("module_name") or "").lower():
                hits.append(f"file::{path_str}")
            if term_l in (f.get("docstring") or "").lower():
                hits.append(f"file::{path_str} (doc)")
        for cid in self.raw.get("classes", {}):
            if term_l in cid.lower():
                hits.append(f"class::{cid}")
        for fid in self.raw.get("functions", {}):
            if term_l in fid.lower():
                hits.append(f"function::{fid}")
        for path_str, f in (self.raw.get("non_python_files") or {}).items():
            if term_l in path_str.lower():
                hits.append(f"file::{path_str} [{f.get('language')}]")
            for sym in f.get("symbols", []):
                if term_l in sym.get("name", "").lower():
                    hits.append(f"{sym.get('kind')}::{path_str}::{sym.get('name')}")
        return hits

    def freshness(self) -> dict[str, Any]:
        ts_str = self.raw.get("generated_at") or ""
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return {"generated_at": ts_str, "stale": True, "reason": "unparseable timestamp"}
        age = datetime.now(timezone.utc) - ts
        stale = age.total_seconds() > STALE_HOURS * 3600
        return {
            "generated_at": ts_str,
            "age_hours": round(age.total_seconds() / 3600, 2),
            "stale": stale,
            "threshold_hours": STALE_HOURS,
        }

    # ─── Multi-language ──────────────────────────────────────────────────

    def languages(self) -> dict[str, int]:
        """Language-coverage counts from the last graph build."""
        langs = dict(self.raw.get("languages") or {})
        if "python" not in langs:
            langs["python"] = len(self.raw.get("files") or {})
        return langs

    def non_python_files(self, language: str | None = None) -> list[str]:
        """All non-Python files in the graph, optionally filtered by language."""
        npf = self.raw.get("non_python_files") or {}
        if language is None:
            return sorted(npf.keys())
        return sorted(p for p, f in npf.items() if f.get("language") == language)


# ─── CLI ────────────────────────────────────────────────────────────────────


def _print_list(rows: Iterable[Any]) -> None:
    for r in rows:
        print(r)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="query_graph")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_deps = sub.add_parser("deps", help="what this node depends on")
    p_deps.add_argument("node")

    p_depd = sub.add_parser("dependents", help="what depends on this node")
    p_depd.add_argument("node")

    p_path = sub.add_parser("path", help="trace import path A -> B")
    p_path.add_argument("src")
    p_path.add_argument("dst")
    p_path.add_argument("--max-depth", type=int, default=6)

    sub.add_parser("entry-points", help="list entry-point files")
    sub.add_parser("critical", help="list critical files")

    p_cent = sub.add_parser("centrality", help="rank files by centrality")
    p_cent.add_argument("--top", type=int, default=25)

    p_search = sub.add_parser("search", help="substring search over nodes")
    p_search.add_argument("term")

    sub.add_parser("stats", help="graph stats")
    sub.add_parser("freshness", help="graph freshness / staleness check")
    sub.add_parser("languages", help="language coverage from parser registry")

    p_files = sub.add_parser("files", help="list files, optionally filtered by language")
    p_files.add_argument("--language", default=None, help="e.g. typescript, javascript, sql")

    args = parser.parse_args(argv)
    try:
        q = GraphQuery.load()
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.cmd == "deps":
        _print_list(q.dependencies(args.node))
    elif args.cmd == "dependents":
        _print_list(q.dependents(args.node))
    elif args.cmd == "path":
        result = q.path(args.src, args.dst, max_depth=args.max_depth)
        if result is None:
            print(f"no path from {args.src} to {args.dst}")
            return 1
        print(" -> ".join(result))
    elif args.cmd == "entry-points":
        _print_list(q.entry_points())
    elif args.cmd == "critical":
        _print_list(q.critical_files())
    elif args.cmd == "centrality":
        for path_str, inbound, outbound in q.centrality(top=args.top):
            print(f"{inbound:4d} in | {outbound:4d} out  {path_str}")
    elif args.cmd == "search":
        _print_list(q.search(args.term))
    elif args.cmd == "stats":
        print(json.dumps(q.raw.get("stats", {}), indent=2))
    elif args.cmd == "freshness":
        print(json.dumps(q.freshness(), indent=2))
    elif args.cmd == "languages":
        langs = q.languages()
        total = sum(langs.values())
        for lang, count in sorted(langs.items(), key=lambda r: -r[1]):
            pct = (count / total * 100) if total else 0
            print(f"  {lang:<15s} {count:>5d}  ({pct:5.1f}%)")
        print(f"  {'total':<15s} {total:>5d}")
    elif args.cmd == "files":
        if args.language:
            if args.language == "python":
                _print_list(sorted(q.raw.get("files", {}).keys()))
            else:
                _print_list(q.non_python_files(args.language))
        else:
            _print_list(sorted(q.raw.get("files", {}).keys()) + q.non_python_files())
    return 0


if __name__ == "__main__":
    sys.exit(main())
