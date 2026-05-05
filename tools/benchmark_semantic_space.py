#!/usr/bin/env python3
"""
Benchmark semantic space prefilter vs baseline graph retrieval.

Compares three paths:
  1. Baseline — substring search + 1-hop graph expansion
  2. v1      — PCA spatial prefilter + proximity rerank + graph expansion
  3. v1.1    — PCA spatial prefilter + cosine rerank + graph expansion

Usage:
    python3 scripts/benchmark_semantic_space.py
    python3 scripts/benchmark_semantic_space.py --scenario impact
    python3 scripts/benchmark_semantic_space.py --json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/opt/OS")

GRAPH_PATH = "/opt/OS/data/codebase_graph.json"
PCA_PATH = "/opt/OS/data/semantic_space/pca_v1.json"
RESULTS_PATH = "/opt/OS/data/semantic_space/benchmark_results.json"

_GRAPH_SECTIONS = ("files", "classes", "functions")

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, dict] = {
    "architecture": {
        "query": "How does the memory system work?",
        "known_relevant": [
            "eos/memory.py",
            "eos/embedding_engine.py",
            "eos/embedder.py",
            "eos/db.py",
            "eos/cognitive_loop.py",
        ],
        "search_terms": ["memory", "embedding", "interact"],
    },
    "impact": {
        "query": "What breaks if I change eos/memory.py?",
        "known_relevant": [
            "eos/memory.py",
            "eos/cognitive_loop.py",
            "eos/agent_runtime.py",
            "eos/embedding_engine.py",
            "services/discord_bot.py",
        ],
        "search_terms": ["memory", "Memory", "get_conn"],
    },
    "recent-state": {
        "query": "What has changed recently in the orchestration layer?",
        "known_relevant": [
            "eos/orchestrator.py",
            "scripts/orchestrator.py",
            "core/control_plane.py",
            "scripts/workflow_engine.py",
        ],
        "search_terms": ["orchestrat", "workflow", "scheduler"],
    },
    "cross-module": {
        "query": "How do workflows reach the action system?",
        "known_relevant": [
            "scripts/workflow_engine.py",
            "scripts/action_system.py",
            "core/control_plane.py",
            "eos/authority_engine.py",
        ],
        "search_terms": ["workflow", "action", "authority"],
    },
    "strategy": {
        "query": "What are the system's core safety guarantees?",
        "known_relevant": [
            "eos/authority_engine.py",
            "eos/ai_identity.py",
            "core/capability.py",
            "core/execution_contract.py",
            "eos/primitives.py",
        ],
        "search_terms": ["safety", "authority", "risk", "capability"],
    },
}


# ---------------------------------------------------------------------------
# Retrieval methods
# ---------------------------------------------------------------------------


def _baseline_retrieve(graph: dict, scenario: dict) -> dict:
    """Baseline: substring search + 1-hop graph expansion."""
    t0 = time.time()

    hits: set[str] = set()
    for term in scenario["search_terms"]:
        term_lower = term.lower()
        for section in _GRAPH_SECTIONS:
            for nid, node in graph.get(section, {}).items():
                if term_lower in nid.lower():
                    hits.add(nid)
                    continue
                if term_lower in (node.get("docstring") or "").lower():
                    hits.add(nid)

    out_edges, in_edges = _build_edge_index(graph)
    expanded = _expand_1hop(hits, out_edges, in_edges)
    elapsed = time.time() - t0

    return _result_dict("baseline", hits, expanded, elapsed)


def _semantic_retrieve(
    graph: dict,
    pca_model: dict,
    scenario: dict,
    embedding_store: dict[str, list[float]] | None = None,
) -> dict:
    """Semantic retrieval — shared by v1 (no cosine) and v1.1 (with cosine).

    When embedding_store is None, cosine rerank is skipped (v1 path).
    """
    from core.semantic_space import project_query, region_search, expand_with_graph

    query = scenario["query"]

    t0 = time.time()
    x, y, z, query_embedding = project_query(query, pca_model)

    candidates = region_search(
        graph,
        (x, y, z),
        top_k=25,
        query=query,
        embedding_store=embedding_store,
        query_embedding=query_embedding if embedding_store else None,
    )
    t_candidates = time.time() - t0

    candidate_ids = [c["node_id"] for c in candidates]
    expanded = expand_with_graph(graph, candidate_ids, hops=1)
    elapsed = time.time() - t0
    expanded_ids = sorted(expanded["nodes"].keys())

    method = "v1.1_pca_plus_cosine" if embedding_store else "v1_pca_only"
    return {
        "method": method,
        "candidate_count": len(candidates),
        "expanded_count": len(expanded_ids),
        "time_to_candidates_ms": round(t_candidates * 1000, 2),
        "time_to_final_ms": round(elapsed * 1000, 2),
        "token_estimate": len(expanded_ids) * 50,
        "node_ids": expanded_ids,
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def _compare(baseline: dict, variant: dict, known_relevant: list[str]) -> dict:
    """Compare a variant against baseline on recall, precision, tokens, latency."""
    b_ids = set(baseline["node_ids"])
    v_ids = set(variant["node_ids"])
    known = set(known_relevant)

    b_recall = len(b_ids & known) / max(len(known), 1)
    v_recall = len(v_ids & known) / max(len(known), 1)
    v_precision = len(v_ids & known) / max(len(v_ids), 1)

    token_change = 0.0
    if baseline["token_estimate"] > 0:
        token_change = (
            (variant["token_estimate"] - baseline["token_estimate"])
            / baseline["token_estimate"]
        ) * 100

    return {
        "baseline_recall": round(b_recall, 4),
        "variant_recall": round(v_recall, 4),
        "variant_precision": round(v_precision, 4),
        "token_change_pct": round(token_change, 1),
        "baseline_nodes": len(b_ids),
        "variant_nodes": len(v_ids),
        "overlap": len(b_ids & v_ids),
    }


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


def run_scenario(
    graph: dict,
    pca_model: dict,
    embedding_store: dict[str, list[float]],
    name: str,
    scenario: dict,
    verbose: bool = True,
) -> dict:
    """Run one scenario: baseline, v1, v1.1."""
    if verbose:
        print(f"\n{'=' * 70}")
        print(f"Scenario: {name}")
        print(f'Query: "{scenario["query"]}"')
        print(f"{'=' * 70}")

    baseline = _baseline_retrieve(graph, scenario)
    v1 = _semantic_retrieve(graph, pca_model, scenario)
    v11 = _semantic_retrieve(graph, pca_model, scenario, embedding_store)
    known = scenario["known_relevant"]

    cmp_v1 = _compare(baseline, v1, known)
    cmp_v11 = _compare(baseline, v11, known)

    if verbose:
        _print_variant("Baseline", baseline, None)
        _print_variant("v1 (PCA-only)", v1, cmp_v1)
        _print_variant("v1.1 (PCA+cosine)", v11, cmp_v11)

    return {
        "name": name,
        "query": scenario["query"],
        "baseline": baseline,
        "v1": v1,
        "v1.1": v11,
        "comparison_v1": cmp_v1,
        "comparison_v1.1": cmp_v11,
    }


def _print_variant(label: str, data: dict, cmp: dict | None) -> None:
    """Print one row of the benchmark table."""
    line = (
        f"  {label:22s}  "
        f"cand={data['candidate_count']:<4d}  "
        f"expanded={data['expanded_count']:<5d}  "
        f"time={data['time_to_final_ms']:>7.1f}ms  "
        f"tokens=~{data['token_estimate']}"
    )
    if cmp:
        line += (
            f"  recall={cmp['variant_recall']:.0%}  "
            f"prec={cmp['variant_precision']:.1%}  "
            f"tokens={cmp['token_change_pct']:+.0f}%"
        )
    print(line)


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def _recommendation(results: list[dict]) -> str:
    """Generate keep/rollback recommendation from v1.1 results."""
    wins = 0
    losses = 0

    for r in results:
        c = r["comparison_v1.1"]
        recall_ok = c["variant_recall"] >= c["baseline_recall"] - 0.1
        token_savings = c["token_change_pct"] < -15
        recall_worse = c["variant_recall"] < c["baseline_recall"] - 0.1

        if recall_worse and not token_savings:
            losses += 1
        elif recall_ok or token_savings:
            wins += 1

    total = len(results)
    if losses > total / 2:
        return "ROLL BACK — recall drops in majority of scenarios"
    if wins >= total * 0.6:
        return "KEEP — material improvement in majority of scenarios"
    if wins > 0:
        return "KEEP OPTIONAL — mixed results, keep as optional prefilter"
    return "KEEP OPTIONAL — no material improvement detected"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_edge_index(graph: dict) -> tuple[dict, dict]:
    out: dict[str, list[str]] = {}
    inp: dict[str, list[str]] = {}
    for edge in graph.get("edges", []):
        out.setdefault(edge["from_id"], []).append(edge["to_id"])
        inp.setdefault(edge["to_id"], []).append(edge["from_id"])
    return out, inp


def _expand_1hop(seeds: set[str], out_edges: dict, in_edges: dict) -> set[str]:
    expanded = set(seeds)
    for nid in seeds:
        expanded.update(out_edges.get(nid, []))
        expanded.update(in_edges.get(nid, []))
    return expanded


def _result_dict(
    method: str, candidates: set[str], expanded: set[str], elapsed: float
) -> dict:
    return {
        "method": method,
        "candidate_count": len(candidates),
        "expanded_count": len(expanded),
        "time_to_candidates_ms": round(elapsed * 1000, 2),
        "time_to_final_ms": round(elapsed * 1000, 2),
        "token_estimate": len(expanded) * 50,
        "node_ids": sorted(expanded),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark semantic space vs baseline")
    parser.add_argument(
        "--scenario", choices=list(SCENARIOS.keys()), help="Run single scenario"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--graph", default=GRAPH_PATH)
    parser.add_argument("--pca", default=PCA_PATH)
    args = parser.parse_args()

    print("[benchmark] Loading graph...")
    with open(args.graph) as f:
        graph = json.load(f)

    meta = graph.get("semantic_space_meta")
    if not meta or not meta.get("enabled"):
        print(
            "[error] Semantic space not built. "
            "Run: python3 scripts/build_semantic_coords.py"
        )
        sys.exit(1)

    print(
        f"[benchmark] {meta['node_count']} nodes, "
        f"version={meta['coord_version']}, "
        f"rerank={meta.get('rerank_mode', 'v1')}"
    )

    with open(args.pca) as f:
        pca_model = json.load(f)

    # Load embedding store for v1.1
    embed_path = meta.get("embedding_store_path", "")
    embed_full = os.path.join("/opt/OS", embed_path) if embed_path else ""
    if embed_full and os.path.exists(embed_full):
        print(f"[benchmark] Loading embedding store...")
        with open(embed_full) as f:
            embedding_store = json.load(f)
        print(f"[benchmark] {len(embedding_store)} embeddings loaded")
    else:
        print("[benchmark] No embedding store — v1.1 will run without cosine")
        embedding_store = {}

    # Run
    scenarios_to_run = (
        {args.scenario: SCENARIOS[args.scenario]} if args.scenario else SCENARIOS
    )
    results = []
    for name, scenario in scenarios_to_run.items():
        results.append(
            run_scenario(
                graph,
                pca_model,
                embedding_store,
                name,
                scenario,
                verbose=not args.json,
            )
        )

    rec = _recommendation(results)

    if args.json:
        print(
            json.dumps(
                {
                    "run_at": datetime.now(timezone.utc).isoformat(),
                    "recommendation": rec,
                    "scenarios": results,
                },
                indent=2,
                default=str,
            )
        )
    else:
        print(f"\n{'=' * 70}")
        print(f"RECOMMENDATION: {rec}")
        print(f"{'=' * 70}")

    # Persist
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(
            {
                "run_at": datetime.now(timezone.utc).isoformat(),
                "recommendation": rec,
                "scenario_count": len(results),
                "scenarios": results,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\n[benchmark] Results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
