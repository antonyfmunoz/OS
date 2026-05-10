#!/usr/bin/env python3
"""
Query the semantic space — inspect coordinates, run queries, explore regions.

Usage:
    python3 scripts/query_semantic_space.py query "how does memory work"
    python3 scripts/query_semantic_space.py query "what breaks if I change memory" --show-scores
    python3 scripts/query_semantic_space.py coord eos_ai/memory.py
    python3 scripts/query_semantic_space.py neighbors eos_ai/memory.py
    python3 scripts/query_semantic_space.py region --x 0.1 --y 0.6 --z 0.8
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

GRAPH_PATH = "/opt/OS/data/codebase_graph.json"
PCA_PATH = "/opt/OS/data/semantic_space/pca_v1.json"

_GRAPH_SECTIONS = ("files", "classes", "functions")


def _load_graph(path: str = GRAPH_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def _load_pca(path: str = PCA_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def _check_semantic_space(graph: dict) -> bool:
    meta = graph.get("semantic_space_meta")
    if not meta or not meta.get("enabled"):
        print(
            "[error] Semantic space not built. "
            "Run: python3 scripts/build_semantic_coords.py"
        )
        return False
    return True


def _find_node(graph: dict, identifier: str) -> tuple[str, dict, str] | None:
    """Find a node by exact match, then substring match."""
    for section in _GRAPH_SECTIONS:
        if identifier in graph.get(section, {}):
            return identifier, graph[section][identifier], section
    for section in _GRAPH_SECTIONS:
        for nid, node in graph.get(section, {}).items():
            if identifier in nid:
                return nid, node, section
    return None


def _load_embedding_store(graph: dict) -> dict[str, list[float]] | None:
    """Load embedding store from path recorded in graph metadata."""
    from core.semantic_space import load_embedding_store

    meta = graph.get("semantic_space_meta", {})
    rel_path = meta.get("embedding_store_path")
    if not rel_path:
        return None
    full_path = os.path.join("/opt/OS", rel_path)
    if not os.path.exists(full_path):
        return None
    return load_embedding_store(full_path)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_query(args: argparse.Namespace) -> None:
    """Run a semantic query and show results."""
    from core.semantic_space import (
        project_query,
        region_search,
        expand_with_graph,
        apply_wiki_layer,
    )

    graph = _load_graph(args.graph)
    if not _check_semantic_space(graph):
        return

    pca_model = _load_pca(args.pca)
    query = args.text

    # Single embed: project_query returns (x, y, z, embedding)
    x, y, z, query_embedding = project_query(query, pca_model)
    print(f'\nQuery: "{query}"')
    print(f"Projected: x={x:.4f}  y={y:.4f}  z={z:.4f}")

    # Load embedding store for cosine rerank
    embedding_store = _load_embedding_store(graph)
    if embedding_store:
        print(f"[v1.1] Cosine rerank active ({len(embedding_store)} embeddings)")
    else:
        print("[v1.0] PCA-only mode (no embedding store)")
        query_embedding = None  # signal v1 path

    top_k = args.top_k or 25
    results = region_search(
        graph,
        (x, y, z),
        top_k=top_k,
        query=query,
        embedding_store=embedding_store,
        query_embedding=query_embedding,
    )

    # Wiki-aware enrichment (v1.2)
    show_wiki = getattr(args, "show_wiki", False)
    if show_wiki:
        pre_wiki_count = len(results)
        results = apply_wiki_layer(results, graph)
        wiki_enriched = sum(1 for r in results if r.get("wiki"))
        wiki_traversed = sum(1 for r in results if r.get("wiki_traversal"))
        print(
            f"[v1.2] Wiki layer: {wiki_enriched} enriched, "
            f"{wiki_traversed} via traversal"
        )

    _print_results(results, top_k, args.show_scores, show_wiki=show_wiki)

    if results and results[0].get("fallback_used"):
        print("\n[warn] Sparse results — graph fallback recommended")

    if args.expand:
        seed_ids = [r["node_id"] for r in results[:top_k]]
        expanded = expand_with_graph(graph, seed_ids, hops=args.hops or 1)
        print(
            f"\nGraph expansion: {expanded['seed_count']} seeds "
            f"-> {expanded['expanded_count']} nodes ({expanded['hop_count']} hops, "
            f"{len(expanded['edges'])} edges)"
        )


def _print_results(
    results: list[dict],
    top_k: int,
    show_scores: bool,
    show_wiki: bool = False,
) -> None:
    """Print result table in compact or detailed format."""
    n = min(len(results), top_k)
    print(f"\nTop {n} candidates:")

    if show_scores:
        header = (
            f"  {'#':<4} {'Score':>6} {'Prox':>6} {'Cos':>6} {'Meta':>6} {'Dist':>6}"
        )
        if show_wiki:
            header += f"  {'Wiki':>5} {'BL':>3}"
        header += "  Node ID"
        print(header)
        print("  " + "-" * (90 if show_wiki else 80))
        for i, r in enumerate(results[:top_k]):
            line = (
                f"  {i + 1:<4} {r['score']:6.4f} "
                f"{r.get('proximity_score', 0):6.4f} "
                f"{r.get('semantic_similarity', 0):6.4f} "
                f"{r.get('metadata_score', 0):6.4f} "
                f"{r['distance']:6.4f}"
            )
            if show_wiki:
                wb = r.get("wiki_bonus", 0)
                wiki = r.get("wiki")
                bl = wiki["incoming_link_count"] if wiki else 0
                tag = "T" if r.get("wiki_traversal") else ("W" if wiki else ".")
                line += f"  {tag}{wb:4.2f} {bl:>3}"
            line += f"  {r['node_id']}"
            print(line)
    else:
        header = f"  {'#':<4} {'Score':>6} {'Dist':>6} {'X':>7} {'Y':>7} {'Z':>7}"
        if show_wiki:
            header += f"  {'Wiki':>5}"
        header += "  Node ID"
        print(header)
        print("  " + "-" * (85 if show_wiki else 80))
        for i, r in enumerate(results[:top_k]):
            c = r["semantic_coord"]
            line = (
                f"  {i + 1:<4} {r['score']:6.4f} {r['distance']:6.4f} "
                f"{c['x']:7.4f} {c['y']:7.4f} {c['z']:7.4f}"
            )
            if show_wiki:
                wiki = r.get("wiki")
                wb = r.get("wiki_bonus", 0)
                tag = "T" if r.get("wiki_traversal") else ("W" if wiki else ".")
                line += f"  {tag}{wb:4.2f}"
            line += f"  {r['node_id']}"
            print(line)

    # Wiki detail section
    if show_wiki:
        wiki_results = [r for r in results[:top_k] if r.get("wiki")]
        if wiki_results:
            print(f"\n  Wiki mappings ({len(wiki_results)}):")
            for r in wiki_results:
                w = r["wiki"]
                promo = " [promoted]" if w.get("promoted_summary_present") else ""
                trav = " [traversal]" if r.get("wiki_traversal") else ""
                links = w.get("outgoing_wikilinks", [])
                link_str = f"  links: {', '.join(links[:5])}" if links else ""
                print(f"    {r['node_id']} → {w['wiki_path']}{promo}{trav}{link_str}")


def cmd_coord(args: argparse.Namespace) -> None:
    """Show coordinates for a specific node."""
    graph = _load_graph(args.graph)
    if not _check_semantic_space(graph):
        return

    found = _find_node(graph, args.node)
    if not found:
        print(f"[error] Node not found: {args.node}")
        return

    nid, node, section = found
    coord = node.get("semantic_coord")
    meta = node.get("semantic_meta")

    print(f"\nNode: {nid}  ({section})")
    if coord:
        print(f"  x (semantic):    {coord['x']:>8.4f}")
        print(f"  y (abstraction): {coord['y']:>8.4f}")
        print(f"  z (temporal):    {coord['z']:>8.4f}")
        print(f"  importance:      {coord['importance']:>8.4f}")
        print(f"  confidence:      {coord['confidence']:>8.4f}")
        print(f"  risk:            {coord['risk']:>8.4f}")
        print(f"  heat:            {coord['heat']:>8.4f}")
    if meta:
        print(f"  coord_version:   {meta.get('coord_version')}")


def cmd_neighbors(args: argparse.Namespace) -> None:
    """Show nearest neighbors to a node (spatial distance only)."""
    graph = _load_graph(args.graph)
    if not _check_semantic_space(graph):
        return

    found = _find_node(graph, args.node)
    if not found:
        print(f"[error] Node not found: {args.node}")
        return

    nid, node, section = found
    coord = node.get("semantic_coord")
    if not coord:
        print(f"[error] Node has no coordinates: {nid}")
        return

    from core.semantic_space import region_search

    qcoord = (coord["x"], coord["y"], coord["z"])
    top_k = args.top_k or 15
    results = region_search(graph, qcoord, top_k=top_k + 1)

    results = [r for r in results if r["node_id"] != nid][:top_k]

    print(f"\nNearest neighbors of {nid}:")
    print(f"  {'#':<4} {'Dist':>6} {'X':>7} {'Y':>7} {'Z':>7}  Node ID")
    print("  " + "-" * 70)
    for i, r in enumerate(results):
        c = r["semantic_coord"]
        print(
            f"  {i + 1:<4} {r['distance']:6.4f} "
            f"{c['x']:7.4f} {c['y']:7.4f} {c['z']:7.4f}  {r['node_id']}"
        )


def cmd_region(args: argparse.Namespace) -> None:
    """Show nodes in a specific region."""
    graph = _load_graph(args.graph)
    if not _check_semantic_space(graph):
        return

    from core.semantic_space import region_search

    qcoord = (args.x, args.y, args.z)
    top_k = args.top_k or 20
    results = region_search(graph, qcoord, top_k=top_k)

    print(f"\nRegion ({args.x:.2f}, {args.y:.2f}, {args.z:.2f}):")
    _print_results(results, top_k, show_scores=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Query semantic space")
    parser.add_argument("--graph", default=GRAPH_PATH)
    parser.add_argument("--pca", default=PCA_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    p_query = sub.add_parser("query", help="Run semantic query")
    p_query.add_argument("text", help="Query text")
    p_query.add_argument("--top-k", type=int, default=25)
    p_query.add_argument(
        "--show-scores", action="store_true", help="Show score breakdown"
    )
    p_query.add_argument(
        "--show-wiki", action="store_true", help="Show wiki-aware enrichment"
    )
    p_query.add_argument("--expand", action="store_true", help="Expand via graph")
    p_query.add_argument("--hops", type=int, default=1)

    p_coord = sub.add_parser("coord", help="Show node coordinates")
    p_coord.add_argument("node", help="Node ID or path")

    p_neigh = sub.add_parser("neighbors", help="Show nearest neighbors")
    p_neigh.add_argument("node", help="Node ID or path")
    p_neigh.add_argument("--top-k", type=int, default=15)

    p_region = sub.add_parser("region", help="Show nodes in region")
    p_region.add_argument("--x", type=float, required=True)
    p_region.add_argument("--y", type=float, required=True)
    p_region.add_argument("--z", type=float, required=True)
    p_region.add_argument("--top-k", type=int, default=20)

    args = parser.parse_args()
    cmd = {
        "query": cmd_query,
        "coord": cmd_coord,
        "neighbors": cmd_neighbors,
        "region": cmd_region,
    }
    cmd[args.command](args)


if __name__ == "__main__":
    main()
