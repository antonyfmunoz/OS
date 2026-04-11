#!/usr/bin/env python3
"""merge_graphs.py — Merge graphify_overlay.json into codebase_graph.json.

RULES (non-negotiable):
  - Primary graph (data/codebase_graph.json) is SOURCE OF TRUTH.
  - The overlay is ADDITIVE ONLY. Core edges are never replaced.
  - Every overlay edge is tagged with "source": "graphify".
  - Output is written to data/codebase_graph_merged.json BY DEFAULT
    so the primary file is never touched. Optional --in-place flag
    writes back to the primary (use with caution).
  - Reversibility: deleting the merged file restores the system.

CLI
---
    python3 scripts/merge_graphs.py                          # write merged copy
    python3 scripts/merge_graphs.py --dry-run                # counts only
    python3 scripts/merge_graphs.py --output some/path.json  # custom output
    python3 scripts/merge_graphs.py --stats                  # stats from merged

The merged file has the same shape as the primary graph plus a top-level
"graphify" key holding the overlay metadata (clusters, co_occurrences).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

ROOT = Path("/opt/OS")
GRAPH_JSON = ROOT / "data" / "codebase_graph.json"
OVERLAY_JSON = ROOT / "data" / "graphify_overlay.json"
MERGED_JSON = ROOT / "data" / "codebase_graph_merged.json"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found at {path}")
    return json.loads(path.read_text())


def _edge_key(e: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Canonical key for a primary-graph edge."""
    return (
        e.get("from_type", ""),
        e.get("from_id", ""),
        e.get("to_type", ""),
        e.get("to_id", ""),
        e.get("relationship", ""),
    )


def _overlay_edge_to_primary(
    overlay_edge: dict[str, Any],
) -> dict[str, Any]:
    """Normalize an overlay edge {from, to, relationship} to the primary
    edge shape {from_type, from_id, to_type, to_id, relationship}."""
    return {
        "from_type": "file",
        "from_id": overlay_edge.get("from") or overlay_edge.get("from_id", ""),
        "to_type": "file",
        "to_id": overlay_edge.get("to") or overlay_edge.get("to_id", ""),
        "relationship": overlay_edge.get("relationship", "related"),
        "source": "graphify",
        "confidence": overlay_edge.get("confidence"),
    }


def merge(
    *,
    output_path: Path = MERGED_JSON,
    in_place: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    primary = _load_json(GRAPH_JSON, "primary graph")
    try:
        overlay = _load_json(OVERLAY_JSON, "graphify overlay")
    except FileNotFoundError:
        return {
            "mode": "no-op",
            "reason": "overlay missing — run scripts/run_graphify.py first",
            "primary_edges": len(primary.get("edges", [])),
            "added_edges": 0,
        }

    primary_edges = primary.get("edges", [])
    existing_keys = {_edge_key(e) for e in primary_edges}

    overlay_edges_raw = overlay.get("edges", [])
    to_add: list[dict[str, Any]] = []
    skipped_dupes = 0

    for oe in overlay_edges_raw:
        normalized = _overlay_edge_to_primary(oe)
        if not normalized["from_id"] or not normalized["to_id"]:
            continue
        if normalized["from_id"] == normalized["to_id"]:
            continue
        key = _edge_key(normalized)
        if key in existing_keys:
            skipped_dupes += 1
            continue
        # Safety: never allow an overlay edge to overwrite a core edge type.
        # Since we only append (not replace), this is guaranteed — but we
        # still assert that the overlay relationship is non-core.
        if normalized["relationship"] in {
            "contains",
            "imports",
            "inherits",
            "calls",
        }:
            skipped_dupes += 1
            continue
        to_add.append(normalized)
        existing_keys.add(key)

    report: dict[str, Any] = {
        "mode": "dry-run" if dry_run else ("in-place" if in_place else "copy"),
        "primary_edges": len(primary_edges),
        "overlay_edges": len(overlay_edges_raw),
        "added_edges": len(to_add),
        "skipped_duplicates": skipped_dupes,
        "clusters": len(overlay.get("clusters", [])),
        "co_occurrences": len(overlay.get("co_occurrences", [])),
        "primary_generated_at": primary.get("generated_at"),
        "overlay_generated_at": overlay.get("generated_at"),
    }

    if dry_run:
        return report

    # Assemble merged artifact. The merged file is a SUPERSET of the primary:
    # it has every primary field plus the appended overlay edges and a
    # top-level "graphify" block containing metadata + clusters.
    merged = dict(primary)  # shallow copy; we'll only extend "edges"
    merged["edges"] = list(primary_edges) + to_add
    merged["graphify"] = {
        "source": overlay.get("source"),
        "generated_at": overlay.get("generated_at"),
        "meta": overlay.get("meta", {}),
        "clusters": overlay.get("clusters", []),
        "co_occurrences": overlay.get("co_occurrences", []),
    }

    target = GRAPH_JSON if in_place else output_path
    if in_place:
        # Protect the primary file: keep a .bak before overwriting.
        backup = GRAPH_JSON.with_suffix(".json.bak")
        backup.write_text(GRAPH_JSON.read_text())
        report["in_place_backup"] = str(backup)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(merged, indent=2, default=str))
    report["output"] = str(target)
    return report


def _print_stats() -> int:
    if not MERGED_JSON.exists():
        print("merged graph not yet built — run scripts/merge_graphs.py first")
        return 1
    data = json.loads(MERGED_JSON.read_text())
    overlay = data.get("graphify", {})
    print(
        json.dumps(
            {
                "total_edges": len(data.get("edges", [])),
                "graphify_edges": sum(
                    1 for e in data.get("edges", []) if e.get("source") == "graphify"
                ),
                "clusters": len(overlay.get("clusters", [])),
                "co_occurrences": len(overlay.get("co_occurrences", [])),
                "primary_generated_at": data.get("generated_at"),
                "overlay_generated_at": overlay.get("generated_at"),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="merge_graphs")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output", type=Path, default=MERGED_JSON)
    p.add_argument(
        "--in-place",
        action="store_true",
        help="rewrite primary graph (backup saved to .json.bak)",
    )
    p.add_argument("--stats", action="store_true")
    args = p.parse_args(argv)

    if args.stats:
        return _print_stats()

    try:
        report = merge(
            output_path=args.output, in_place=args.in_place, dry_run=args.dry_run
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
