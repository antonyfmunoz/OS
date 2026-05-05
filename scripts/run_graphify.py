#!/usr/bin/env python3
"""run_graphify.py — Pluggable enrichment layer (Graphify adapter).

Produces data/graphify_overlay.json — an additive enrichment over the
primary codebase_graph.json. NEVER writes to the primary graph.

Strategy
--------
    1. If an external "graphify" tool is available (binary on PATH, or a
       python module importable as `graphify`), invoke it and capture its
       output. This is a probe — the exact interface is unknown, so we
       accept either (a) JSON on stdout, or (b) a file written at a
       conventional location.
    2. If no external tool is available, run the INTERNAL enrichment
       pipeline, which produces equivalent structure using only stdlib
       and the existing graph.

Internal enrichment pipeline
----------------------------
    A. CLUSTERS — label-propagation community detection on the file
       import graph. Each file starts with its own label; we iterate,
       assigning each file the most common label among its neighbors
       (imports + imported-by). Converges quickly on modular codebases.

    B. CO-OCCURRENCE EDGES — pairs of files that share ≥3 distinct
       symbol tokens in docstrings (module, class, function docs), but
       have no direct import edge between them. Surfaces implicit
       conceptual coupling ("these files talk about the same things").

    C. CROSS-LANGUAGE LINKS — SQL file table names mentioned in Python
       docstrings or module names → one edge per (sql_file, py_file)
       pair flagged as references_schema.

Output shape (data/graphify_overlay.json)
-----------------------------------------
    {
      "generated_at": ISO timestamp,
      "source": "external:<tool>" | "internal",
      "meta": { "tool_version": str | null, "notes": str },
      "clusters": [
        { "id": "cluster_<n>", "label": str, "members": [file, ...] }
      ],
      "edges": [
        { "from": str, "to": str, "relationship": str, "source": "graphify", "confidence": float }
      ],
      "co_occurrences": [
        { "a": str, "b": str, "shared_terms": [str, ...] }
      ]
    }

CLI
---
    python3 scripts/run_graphify.py                   # auto-detect
    python3 scripts/run_graphify.py --force-internal  # skip external probe
    python3 scripts/run_graphify.py --dry-run         # report only, don't write
    python3 scripts/run_graphify.py --stats           # show overlay stats
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

ROOT = Path("/opt/OS")
GRAPH_JSON = ROOT / "data" / "codebase_graph.json"
OVERLAY_JSON = ROOT / "data" / "graphify_overlay.json"

# Label-propagation caps
LABEL_PROP_MAX_ITERS = 20
MIN_CLUSTER_SIZE = 2

# Co-occurrence tuning
CO_OCCUR_MIN_SHARED = 3
CO_OCCUR_MAX_PAIRS = 500  # cap to keep overlay small

# Stopwords for docstring tokenization
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "will", "with", "which", "when", "what",
    "where", "why", "how", "we", "you", "they", "not", "no", "can", "do",
    "does", "done", "into", "then", "than", "also", "all", "any", "if",
    "else", "so", "only", "one", "two", "three", "new", "old", "raw",
    "file", "files", "function", "functions", "class", "classes", "method",
    "methods", "module", "modules", "script", "scripts", "test", "tests",
    "use", "used", "uses", "run", "runs", "running", "load", "loads",
    "get", "set", "gets", "sets", "via", "using", "each", "per", "whether",
    "must", "should", "may", "would", "could",
}
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


# ─── External probe ──────────────────────────────────────────────────────────


def _probe_external() -> tuple[str | None, str | None]:
    """Return (invocation_hint, version_string) if an external Graphify is
    available, otherwise (None, None). 'invocation_hint' is one of:
      "binary"     — graphify binary on PATH
      "module"     — python module importable as graphify
    """
    # 1. Binary
    if shutil.which("graphify"):
        try:
            result = subprocess.run(
                ["graphify", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = (result.stdout or result.stderr).strip().splitlines()[0:1]
            return "binary", (version[0] if version else "unknown")
        except Exception:  # pragma: no cover
            return "binary", "unknown"

    # 2. Importable module
    try:
        spec = importlib.util.find_spec("graphify")
    except ValueError:
        spec = None
    if spec is not None:
        try:
            mod = importlib.import_module("graphify")
            return "module", str(getattr(mod, "__version__", "unknown"))
        except Exception:
            return None, None

    return None, None


def _run_external_binary() -> dict[str, Any] | None:
    """Invoke the binary and try to parse JSON from stdout. If the binary
    doesn't support stdout JSON, we give up and fall back — this is by
    design, since the binary interface is unknown.
    """
    cmd_candidates = [
        ["graphify", "--json", str(ROOT)],
        ["graphify", "export", "--format", "json", str(ROOT)],
        ["graphify", str(ROOT)],
    ]
    for cmd in cmd_candidates:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, cwd=str(ROOT)
            )
        except Exception:
            continue
        if result.returncode != 0:
            continue
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
    return None


def _run_external_module() -> dict[str, Any] | None:
    """Try a few conventional module entry points."""
    try:
        mod = importlib.import_module("graphify")
    except Exception:  # pragma: no cover
        return None
    for attr in ("export_overlay", "analyze", "run", "main"):
        fn = getattr(mod, attr, None)
        if callable(fn):
            try:
                result = fn(str(ROOT))
            except TypeError:
                try:
                    result = fn()
                except Exception:  # pragma: no cover
                    continue
            except Exception:  # pragma: no cover
                continue
            if isinstance(result, dict):
                return result
    return None


# ─── Internal enrichment: shared helpers ─────────────────────────────────────


def _load_graph() -> dict[str, Any]:
    if not GRAPH_JSON.exists():
        raise FileNotFoundError(f"{GRAPH_JSON} missing — run scripts/update-graph first")
    return json.loads(GRAPH_JSON.read_text())


def _file_import_graph(graph: dict[str, Any]) -> dict[str, set[str]]:
    """Build undirected file-import adjacency from graph edges."""
    adj: dict[str, set[str]] = defaultdict(set)
    for e in graph.get("edges", []):
        if e.get("relationship") == "imports" and e.get("from_type") == "file":
            a, b = e["from_id"], e["to_id"]
            adj[a].add(b)
            adj[b].add(a)
    # Include all known files so singletons still get a label.
    for rel in graph.get("files", {}):
        adj.setdefault(rel, set())
    return adj


# ─── Internal enrichment: clusters (label propagation) ───────────────────────


def _label_propagation(adj: dict[str, set[str]]) -> dict[str, str]:
    """Naive synchronous label propagation. Deterministic by sorted node order."""
    labels: dict[str, str] = {n: n for n in adj}
    for _ in range(LABEL_PROP_MAX_ITERS):
        changed = False
        for node in sorted(adj):
            neighbors = adj.get(node) or set()
            if not neighbors:
                continue
            counts = Counter(labels[n] for n in neighbors)
            # Break ties deterministically: prefer the lexicographically
            # smallest label among the max-count set.
            best = min(
                (lab for lab, c in counts.items() if c == max(counts.values())),
            )
            if labels[node] != best:
                labels[node] = best
                changed = True
        if not changed:
            break
    return labels


def _clusters_from_labels(labels: dict[str, str]) -> list[dict[str, Any]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for node, lab in labels.items():
        buckets[lab].append(node)
    clusters: list[dict[str, Any]] = []
    # Stable, size-desc order
    sorted_buckets = sorted(
        buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])
    )
    for i, (label, members) in enumerate(sorted_buckets):
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        clusters.append(
            {
                "id": f"cluster_{i:03d}",
                "label": label,
                "size": len(members),
                "members": sorted(members),
            }
        )
    return clusters


# ─── Internal enrichment: co-occurrence edges ────────────────────────────────


def _tokenize_doc(text: str | None) -> set[str]:
    if not text:
        return set()
    tokens = {
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 3
    }
    return tokens


def _co_occurrence_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Find file pairs that share ≥3 distinct docstring tokens AND have no
    direct import edge between them."""
    # Tokens per file from module docstring + class + function docstrings.
    tokens_by_file: dict[str, set[str]] = defaultdict(set)
    for rel, f in graph.get("files", {}).items():
        tokens_by_file[rel].update(_tokenize_doc(f.get("docstring")))
    for cid, c in graph.get("classes", {}).items():
        tokens_by_file[c["file_path"]].update(_tokenize_doc(c.get("docstring")))
    for fid, fn in graph.get("functions", {}).items():
        tokens_by_file[fn["file_path"]].update(_tokenize_doc(fn.get("docstring")))

    # Inverted index: token → set of files
    token_index: dict[str, set[str]] = defaultdict(set)
    for rel, toks in tokens_by_file.items():
        for t in toks:
            token_index[t].add(rel)
    # Drop noise terms that appear in too many files (not discriminating).
    total_files = max(len(graph.get("files", {})), 1)
    token_index = {
        t: files for t, files in token_index.items() if 2 <= len(files) <= max(5, total_files // 8)
    }

    # Existing direct import pairs (either direction) to skip.
    direct: set[tuple[str, str]] = set()
    for e in graph.get("edges", []):
        if e.get("relationship") == "imports" and e.get("from_type") == "file":
            a, b = sorted([e["from_id"], e["to_id"]])
            direct.add((a, b))

    # Count shared tokens per unordered pair.
    pair_counter: dict[tuple[str, str], list[str]] = defaultdict(list)
    for token, files in token_index.items():
        files_sorted = sorted(files)
        for i, a in enumerate(files_sorted):
            for b in files_sorted[i + 1 :]:
                key = (a, b)
                if key in direct:
                    continue
                pair_counter[key].append(token)

    co_edges = []
    for (a, b), shared in pair_counter.items():
        if len(shared) < CO_OCCUR_MIN_SHARED:
            continue
        co_edges.append(
            {
                "a": a,
                "b": b,
                "shared_terms": sorted(shared)[:10],
                "weight": len(shared),
            }
        )
    co_edges.sort(key=lambda r: (-r["weight"], r["a"], r["b"]))
    return co_edges[:CO_OCCUR_MAX_PAIRS]


# ─── Internal enrichment: cross-language links ───────────────────────────────


def _cross_language_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """SQL table names mentioned in Python docstrings → references_schema edges."""
    sql_tables: dict[str, list[str]] = defaultdict(list)  # table_name → [sql_file, ...]
    npf = graph.get("non_python_files") or {}
    for rel, f in npf.items():
        if f.get("language") != "sql":
            continue
        for sym in f.get("symbols", []):
            if sym.get("kind") == "table":
                name = sym.get("name")
                if name:
                    sql_tables[name.lower()].append(rel)
    if not sql_tables:
        return []

    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for rel, f in graph.get("files", {}).items():
        doc = (f.get("docstring") or "").lower()
        if not doc:
            continue
        for table, sql_files in sql_tables.items():
            # Match as whole word
            if re.search(rf"\b{re.escape(table)}\b", doc):
                for sql_file in sql_files:
                    key = (rel, sql_file, table)
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append(
                        {
                            "from": rel,
                            "to": sql_file,
                            "relationship": "references_schema",
                            "source": "graphify",
                            "confidence": 0.6,
                            "via_table": table,
                        }
                    )
    return edges


# ─── Assembly ────────────────────────────────────────────────────────────────


def _build_internal() -> dict[str, Any]:
    graph = _load_graph()
    adj = _file_import_graph(graph)
    labels = _label_propagation(adj)
    clusters = _clusters_from_labels(labels)
    co_pairs = _co_occurrence_edges(graph)
    cross_edges = _cross_language_edges(graph)

    # Promote co-occurrence pairs into the edge list for consumers that
    # only care about edges.
    edges: list[dict[str, Any]] = list(cross_edges)
    for pair in co_pairs:
        edges.append(
            {
                "from": pair["a"],
                "to": pair["b"],
                "relationship": "co_mentions",
                "source": "graphify",
                "confidence": round(min(1.0, pair["weight"] / 10.0), 2),
                "via_terms": pair["shared_terms"][:5],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "internal",
        "meta": {
            "tool_version": None,
            "notes": (
                "Internal enrichment: label-propagation clusters, "
                "co-occurrence edges (≥3 shared docstring tokens), "
                "cross-language schema refs."
            ),
        },
        "clusters": clusters,
        "edges": edges,
        "co_occurrences": co_pairs,
    }


def _build_external(invocation: str, version: str | None) -> dict[str, Any] | None:
    """Try the external Graphify; normalize its output to our overlay shape."""
    raw: dict[str, Any] | None = None
    if invocation == "binary":
        raw = _run_external_binary()
    elif invocation == "module":
        raw = _run_external_module()
    if raw is None:
        return None

    # Normalize: accept keys 'clusters', 'edges', 'co_occurrences' if present.
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": f"external:{invocation}",
        "meta": {
            "tool_version": version,
            "notes": "Adapted from external graphify output.",
        },
        "clusters": raw.get("clusters", []),
        "edges": [
            {**e, "source": "graphify"}
            for e in raw.get("edges", [])
            if isinstance(e, dict)
        ],
        "co_occurrences": raw.get("co_occurrences", []),
    }


def run(
    *, force_internal: bool = False, dry_run: bool = False, verbose: bool = False
) -> dict[str, Any]:
    overlay: dict[str, Any] | None = None
    if not force_internal:
        invocation, version = _probe_external()
        if invocation:
            if verbose:
                print(f"[graphify] external tool detected: {invocation} {version}")
            overlay = _build_external(invocation, version)
            if overlay is None and verbose:
                print("[graphify] external call failed, falling back to internal")
    if overlay is None:
        if verbose:
            print("[graphify] running internal enrichment")
        overlay = _build_internal()

    if not dry_run:
        OVERLAY_JSON.parent.mkdir(parents=True, exist_ok=True)
        OVERLAY_JSON.write_text(json.dumps(overlay, indent=2))

    return {
        "source": overlay["source"],
        "clusters": len(overlay.get("clusters", [])),
        "edges": len(overlay.get("edges", [])),
        "co_occurrences": len(overlay.get("co_occurrences", [])),
        "output": str(OVERLAY_JSON) if not dry_run else None,
    }


def _print_stats() -> int:
    if not OVERLAY_JSON.exists():
        print("no overlay yet — run scripts/run_graphify.py first", file=sys.stderr)
        return 1
    data = json.loads(OVERLAY_JSON.read_text())
    print(
        json.dumps(
            {
                "source": data.get("source"),
                "generated_at": data.get("generated_at"),
                "clusters": len(data.get("clusters", [])),
                "edges": len(data.get("edges", [])),
                "co_occurrences": len(data.get("co_occurrences", [])),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="run_graphify")
    p.add_argument("--force-internal", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    if args.stats:
        return _print_stats()

    try:
        report = run(
            force_internal=args.force_internal,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
