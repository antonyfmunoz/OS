#!/usr/bin/env python3
"""summarize_nodes.py — Append-only one-line summaries for every graph node.

Safe compression layer: we NEVER overwrite raw docstrings or source files.
Every run appends a new version record keyed by node id. Previous versions
stay in the file under "history" so nothing is lost.

Usage:
    python3 scripts/summarize_nodes.py              # refresh summaries
    python3 scripts/summarize_nodes.py --show <id>  # show versions for node
    python3 scripts/summarize_nodes.py --stats
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

ROOT = Path("/opt/OS")
GRAPH_JSON = ROOT / "data" / "codebase_graph.json"
SUMMARIES_JSON = ROOT / "data" / "node_summaries.json"


def _one_line(docstring: str | None, fallback: str) -> str:
    if not docstring:
        return fallback
    stripped = docstring.strip().split("\n", 1)[0]
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if len(stripped) > 160:
        stripped = stripped[:157] + "..."
    return stripped or fallback


def build_summaries() -> dict[str, Any]:
    if not GRAPH_JSON.exists():
        raise FileNotFoundError(f"{GRAPH_JSON} missing — run scripts/update-graph")

    graph = json.loads(GRAPH_JSON.read_text())

    if SUMMARIES_JSON.exists():
        store = json.loads(SUMMARIES_JSON.read_text())
    else:
        store = {"nodes": {}, "versions": 0}

    now = datetime.now(timezone.utc).isoformat()
    new_or_changed = 0

    for path_str, f in graph.get("files", {}).items():
        nid = f"file::{path_str}"
        summary = _one_line(f.get("docstring"), fallback=f"Python file {path_str}")
        new_or_changed += _upsert(store, nid, summary, now, f.get("docstring"))

    for cid, c in graph.get("classes", {}).items():
        summary = _one_line(c.get("docstring"), fallback=f"class {c.get('name')}")
        new_or_changed += _upsert(store, f"class::{cid}", summary, now, c.get("docstring"))

    for fid, fn in graph.get("functions", {}).items():
        summary = _one_line(fn.get("docstring"), fallback=f"function {fn.get('name')}")
        new_or_changed += _upsert(store, f"function::{fid}", summary, now, fn.get("docstring"))

    store["versions"] += 1
    store["last_run"] = now
    store["last_new_or_changed"] = new_or_changed
    SUMMARIES_JSON.write_text(json.dumps(store, indent=2))

    return {
        "total_nodes": len(store["nodes"]),
        "new_or_changed": new_or_changed,
        "version": store["versions"],
    }


def _upsert(
    store: dict[str, Any], nid: str, summary: str, ts: str, raw_doc: str | None
) -> int:
    """Append-only upsert: returns 1 if new or changed, 0 otherwise."""
    nodes = store["nodes"]
    record = nodes.get(nid)
    if record and record["current"]["summary"] == summary:
        return 0
    new_entry = {"summary": summary, "ts": ts, "raw_docstring": raw_doc}
    if record:
        record.setdefault("history", []).append(record["current"])
        record["current"] = new_entry
    else:
        nodes[nid] = {"current": new_entry, "history": []}
    return 1


def show(nid: str) -> int:
    if not SUMMARIES_JSON.exists():
        print("no summaries yet", file=sys.stderr)
        return 1
    store = json.loads(SUMMARIES_JSON.read_text())
    rec = store["nodes"].get(nid)
    if not rec:
        print(f"no record for {nid}", file=sys.stderr)
        return 1
    print(json.dumps(rec, indent=2))
    return 0


def stats() -> int:
    if not SUMMARIES_JSON.exists():
        print("no summaries yet")
        return 1
    store = json.loads(SUMMARIES_JSON.read_text())
    print(
        json.dumps(
            {
                "total_nodes": len(store["nodes"]),
                "versions": store.get("versions", 0),
                "last_run": store.get("last_run"),
                "last_new_or_changed": store.get("last_new_or_changed"),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="summarize_nodes")
    parser.add_argument("--show", metavar="NODE_ID")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args(argv)

    if args.show:
        return show(args.show)
    if args.stats:
        return stats()

    result = build_summaries()
    print(
        f"summaries: {result['total_nodes']} nodes, "
        f"{result['new_or_changed']} new/changed this run (v{result['version']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
