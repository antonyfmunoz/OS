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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

ROOT = Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
GRAPH_JSON = ROOT / "data" / "codebase_graph.json"
OVERLAY_JSON = ROOT / "data" / "graphify_overlay.json"
# Canonical merged path (matches spec). The legacy name
# `codebase_graph_merged.json` is written as a symlink/copy for
# backwards compatibility with any downstream tooling that still
# reads the old path.
MERGED_JSON = ROOT / "data" / "merged_graph.json"
MERGED_LEGACY_JSON = ROOT / "data" / "codebase_graph_merged.json"


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
    overlay_enabled: bool = True,
) -> dict[str, Any]:
    primary = _load_json(GRAPH_JSON, "primary graph")

    # If overlay is explicitly disabled, emit a merged artifact that is an
    # exact mirror of the primary, tagged with overlay_enabled=false. This
    # lets downstream tooling read one file regardless of overlay state.
    if not overlay_enabled:
        merged_no_overlay = _assemble_merged(
            primary=primary,
            overlay=None,
            added_edges=[],
            overlay_enabled=False,
        )
        if not dry_run:
            _write_merged(merged_no_overlay, output_path, in_place)
        return {
            "mode": "overlay-disabled",
            "primary_edges": len(primary.get("edges", [])),
            "added_edges": 0,
            "overlay_enabled": False,
            "output": str(output_path),
        }

    try:
        overlay = _load_json(OVERLAY_JSON, "graphify overlay")
    except FileNotFoundError:
        # Overlay missing is not a failure — the system must work without
        # Graphify. Write a no-overlay merged artifact so consumers still
        # have a stable file to read.
        merged_no_overlay = _assemble_merged(
            primary=primary,
            overlay=None,
            added_edges=[],
            overlay_enabled=False,
        )
        if not dry_run:
            _write_merged(merged_no_overlay, output_path, in_place)
        return {
            "mode": "no-op",
            "reason": "overlay missing — run scripts/run_graphify.py first",
            "primary_edges": len(primary.get("edges", [])),
            "added_edges": 0,
            "overlay_enabled": False,
            "output": str(output_path),
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
        "primary_graph_timestamp": primary.get("generated_at"),
        "overlay_timestamp": overlay.get("generated_at"),
        "overlay_enabled": True,
        "counts_by_source": {
            "primary": len(primary_edges),
            "graphify": len(to_add),
        },
    }

    if dry_run:
        return report

    merged = _assemble_merged(
        primary=primary,
        overlay=overlay,
        added_edges=to_add,
        overlay_enabled=True,
    )

    backup_path = _write_merged(merged, output_path, in_place)
    if backup_path:
        report["in_place_backup"] = str(backup_path)
    report["output"] = str(GRAPH_JSON if in_place else output_path)
    return report


def _assemble_merged(
    *,
    primary: dict[str, Any],
    overlay: dict[str, Any] | None,
    added_edges: list[dict[str, Any]],
    overlay_enabled: bool,
) -> dict[str, Any]:
    """Build the merged artifact with spec-compliant provenance metadata."""
    merged = dict(primary)  # shallow copy; we'll only extend "edges"
    merged["edges"] = list(primary.get("edges", [])) + added_edges

    now = datetime.now(timezone.utc).isoformat()
    overlay_ts = overlay.get("generated_at") if overlay else None

    # Top-level provenance block — the keys here match the spec exactly
    # so any downstream consumer can read them without reaching into
    # the nested "graphify" sub-object.
    merged["merge_metadata"] = {
        "generated_at": now,
        "primary_graph_timestamp": primary.get("generated_at"),
        "overlay_timestamp": overlay_ts,
        "overlay_enabled": overlay_enabled,
        "counts_by_source": {
            "primary": len(primary.get("edges", [])),
            "graphify": len(added_edges),
        },
    }

    # Keep the existing nested "graphify" sub-object for the rich
    # clusters / co_occurrences payload — tooling that was already
    # reading it continues to work.
    if overlay is not None and overlay_enabled:
        merged["graphify"] = {
            "source": overlay.get("source"),
            "generated_at": overlay.get("generated_at"),
            "meta": overlay.get("meta", {}),
            "clusters": overlay.get("clusters", []),
            "co_occurrences": overlay.get("co_occurrences", []),
        }
    else:
        merged["graphify"] = {
            "source": None,
            "generated_at": None,
            "meta": {},
            "clusters": [],
            "co_occurrences": [],
            "disabled": True,
        }
    return merged


def _write_merged(
    merged: dict[str, Any],
    output_path: Path,
    in_place: bool,
) -> Path | None:
    """Persist the merged artifact. Returns backup path if in-place, else None.

    Also writes a legacy-named copy at `codebase_graph_merged.json` so the
    old path keeps working for any script that still references it.
    """
    target = GRAPH_JSON if in_place else output_path
    backup: Path | None = None
    if in_place:
        backup = GRAPH_JSON.with_suffix(".json.bak")
        backup.write_text(GRAPH_JSON.read_text())

    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(merged, indent=2, default=str)
    target.write_text(payload)

    # Legacy-path compatibility: write the same bytes to the old name
    # unless the caller is writing in-place to the primary graph.
    if not in_place and target != MERGED_LEGACY_JSON:
        MERGED_LEGACY_JSON.parent.mkdir(parents=True, exist_ok=True)
        MERGED_LEGACY_JSON.write_text(payload)
    return backup


def _print_stats() -> int:
    target = MERGED_JSON if MERGED_JSON.exists() else MERGED_LEGACY_JSON
    if not target.exists():
        print("merged graph not yet built — run scripts/merge_graphs.py first")
        return 1
    data = json.loads(target.read_text())
    overlay = data.get("graphify", {})
    meta = data.get("merge_metadata", {})
    print(
        json.dumps(
            {
                "path": str(target),
                "total_edges": len(data.get("edges", [])),
                "graphify_edges": sum(
                    1 for e in data.get("edges", []) if e.get("source") == "graphify"
                ),
                "clusters": len(overlay.get("clusters", [])),
                "co_occurrences": len(overlay.get("co_occurrences", [])),
                "overlay_enabled": meta.get("overlay_enabled"),
                "primary_graph_timestamp": meta.get("primary_graph_timestamp"),
                "overlay_timestamp": meta.get("overlay_timestamp"),
                "counts_by_source": meta.get("counts_by_source"),
                "generated_at": meta.get("generated_at"),
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
    p.add_argument(
        "--no-overlay",
        action="store_true",
        help="write a merged artifact that mirrors the primary only (overlay_enabled=false)",
    )
    p.add_argument("--stats", action="store_true")
    args = p.parse_args(argv)

    if args.stats:
        return _print_stats()

    try:
        report = merge(
            output_path=args.output,
            in_place=args.in_place,
            dry_run=args.dry_run,
            overlay_enabled=not args.no_overlay,
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
