#!/usr/bin/env python3
"""
Build semantic coordinates for all graph nodes.

Usage:
    python3 scripts/build_semantic_coords.py
    python3 scripts/build_semantic_coords.py --rebuild
    python3 scripts/build_semantic_coords.py --dry-run
"""

import argparse
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/opt/OS")

GRAPH_PATH = "/opt/OS/data/codebase_graph.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build semantic coordinates for graph nodes"
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Force rebuild even if coordinates exist"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Compute but don't write to disk"
    )
    parser.add_argument("--graph", default=GRAPH_PATH, help="Path to graph JSON")
    args = parser.parse_args()

    print(f"[build] Loading graph from {args.graph}")
    with open(args.graph) as f:
        graph = json.load(f)

    existing_meta = graph.get("semantic_space_meta")
    if existing_meta and not args.rebuild:
        print(
            f"[build] Semantic space already built at {existing_meta.get('built_at')}"
        )
        print(f"[build]   version: {existing_meta.get('coord_version')}")
        print(f"[build]   nodes:   {existing_meta.get('node_count')}")
        print(f"[build]   rerank:  {existing_meta.get('rerank_mode', 'n/a')}")
        print("[build] Use --rebuild to force recomputation")
        return

    from core.coord_assignment import assign_semantic_coords

    t0 = time.time()
    graph = assign_semantic_coords(graph)
    elapsed = time.time() - t0

    meta = graph["semantic_space_meta"]
    print(f"\n[build] === Summary ===")
    print(f"[build] Nodes:    {meta['node_count']}")
    print(f"[build] Version:  {meta['coord_version']}")
    print(f"[build] Rerank:   {meta.get('rerank_mode', 'n/a')}")
    print(f"[build] PCA:      {meta['pca_model_path']}")
    print(f"[build] Embeddings: {meta.get('embedding_store_path', 'n/a')}")
    print(f"[build] Time:     {elapsed:.1f}s")

    _print_distribution_stats(graph)

    if args.dry_run:
        print("\n[build] Dry run — not writing to disk")
        return

    print(f"\n[build] Writing graph to {args.graph}")
    with open(args.graph, "w") as f:
        json.dump(graph, f, indent=2)
    print("[build] Done.")


def _print_distribution_stats(graph: dict) -> None:
    """Print coordinate and abstraction band statistics."""
    from core.coord_assignment import ABSTRACTION_BANDS

    xs, ys, zs = [], [], []
    importances, risks = [], []

    for section in ("files", "classes", "functions"):
        for node in graph.get(section, {}).values():
            coord = node.get("semantic_coord")
            if not coord:
                continue
            xs.append(coord["x"])
            ys.append(coord["y"])
            zs.append(coord["z"])
            importances.append(coord["importance"])
            risks.append(coord["risk"])

    if not xs:
        print("[build] No coordinates found")
        return

    print(f"\n[build] === Coordinate Distribution ===")
    for name, vals in [("x", xs), ("y", ys), ("z", zs)]:
        a = np.array(vals)
        print(
            f"[build] {name}: min={a.min():.3f}  max={a.max():.3f}  "
            f"mean={a.mean():.3f}  std={a.std():.3f}"
        )

    print(f"\n[build] === Metadata Distribution ===")
    for name, vals in [("importance", importances), ("risk", risks)]:
        a = np.array(vals)
        print(
            f"[build] {name}: min={a.min():.3f}  max={a.max():.3f}  mean={a.mean():.3f}"
        )

    # Band histogram: map each y to its nearest named band
    band_lookup = list(ABSTRACTION_BANDS.items()) + [("default", 0.50)]
    band_counts: dict[str, int] = {}
    for y in ys:
        closest_name = min(band_lookup, key=lambda pair: abs(pair[1] - y))[0]
        band_counts[closest_name] = band_counts.get(closest_name, 0) + 1

    print(f"\n[build] === Abstraction Bands ===")
    for band, count in sorted(band_counts.items(), key=lambda x: -x[1]):
        print(f"[build]   {band:12s}: {count}")


if __name__ == "__main__":
    main()
