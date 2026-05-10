"""
Semantic Space v1.2 — Hybrid Coordinate Index with Cosine Reranking

Coordinate system (NOT a true 3D spatial embedding):
    x = semantic position — PCA-1D projection of embedding (learned)
    y = abstraction level — rule-based categorical band (deterministic)
    z = temporal state    — rule-based recency/stability (deterministic)

Only x carries true semantic distance. y and z are organizational axes
that improve prefiltering but should never be treated as spatial dimensions.
Actual ranking is cosine-dominant (65% cosine, 20% spatial, 15% metadata).

Public API:
    project_query(query, pca_model) -> (x, y, z, embedding)
    region_search(graph, qcoord, top_k, ...) -> list[dict]
    expand_with_graph(graph, node_ids, hops) -> dict
    apply_wiki_layer(candidates, graph, max_expansions) -> list[dict]

Contract: spatial layer chooses where to look, graph chooses what is true.
Wiki layer adds human-curated navigational signal but never overrides graph truth.
"""

import json
import math
import re
import sys

import numpy as np

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

PCA_META_PATH = f"{_ROOT}/data/semantic_space/pca_v1.json"
EMBEDDING_STORE_PATH = f"{_ROOT}/data/semantic_space/embeddings_v1.json"

_GRAPH_SECTIONS = ("files", "classes", "functions")

# ---------------------------------------------------------------------------
# Default weights for spatial distance
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {"wx": 1.0, "wy": 1.3, "wz": 1.1}

_WEIGHT_OVERRIDES: list[tuple[re.Pattern, dict[str, float]]] = [
    (
        re.compile(r"what happened|recent|changed|latest|today|now|last|new", re.I),
        {"wx": 0.8, "wy": 0.9, "wz": 1.8},
    ),
    (
        re.compile(
            r"how does|architecture|design|system|overview|explain|structure", re.I
        ),
        {"wx": 1.0, "wy": 1.8, "wz": 0.7},
    ),
    (
        re.compile(
            r"what breaks|impact|change|blast radius|depends|affects|risk", re.I
        ),
        {"wx": 1.0, "wy": 1.5, "wz": 1.0},
    ),
    (
        re.compile(r"strateg|policy|principle|safety|guarantee|doctrine", re.I),
        {"wx": 0.9, "wy": 1.9, "wz": 0.5},
    ),
]

SPARSE_THRESHOLD = 8

# Metadata sub-score component weights (within the 0.10 metadata slice)
_META_W_IMPORTANCE = 0.40
_META_W_CONFIDENCE = 0.30
_META_W_HEAT = 0.20
_META_W_RISK = 0.10

_ACTION_QUERY_RE = re.compile(
    r"what breaks|impact|change|blast|risk|affects|depends", re.I
)

# ---------------------------------------------------------------------------
# Query → Y (rule-based)
# ---------------------------------------------------------------------------

_Y_RULES: list[tuple[re.Pattern, float]] = [
    (
        re.compile(
            r"architectur|principle|policy|strateg|doctrine|guarantee|safety", re.I
        ),
        0.90,
    ),
    (
        re.compile(r"workflow|service|module|system|how does|overview|design", re.I),
        0.65,
    ),
    (re.compile(r"depends|impact|breaks|change|blast.?radius", re.I), 0.55),
    (re.compile(r"file|function|class|method|import|call", re.I), 0.30),
    (re.compile(r"log|message|event|what happened|error|trace", re.I), 0.15),
]


def _query_to_y(query: str) -> float:
    for pattern, y in _Y_RULES:
        if pattern.search(query):
            return y
    return 0.50


# ---------------------------------------------------------------------------
# Query → Z (rule-based)
# ---------------------------------------------------------------------------

_Z_RULES: list[tuple[re.Pattern, float]] = [
    (re.compile(r"latest|recent|current|today|now|just|new|changed|last", re.I), 0.85),
    (re.compile(r"stable|foundational|core|canonical|permanent|base", re.I), 0.15),
]


def _query_to_z(query: str) -> float:
    for pattern, z in _Z_RULES:
        if pattern.search(query):
            return z
    return 0.50


# ---------------------------------------------------------------------------
# Query → X (embedding + PCA projection)
# ---------------------------------------------------------------------------


def _project_x(embedding: np.ndarray, pca_model: dict) -> float:
    """Project embedding to normalized x in [-1, 1] via PCA."""
    components = np.array(pca_model["pca_components"])
    mean = np.array(pca_model["pca_mean"])
    x_min = pca_model["x_min_raw"]
    x_max = pca_model["x_max_raw"]

    raw = float((components @ (embedding - mean)).item())

    span = x_max - x_min
    if span < 1e-10:
        return 0.0
    normalized = 2.0 * (raw - x_min) / span - 1.0
    return max(-1.0, min(1.0, normalized))


# ---------------------------------------------------------------------------
# Query classification
# ---------------------------------------------------------------------------


def _is_action_query(query: str) -> bool:
    return bool(_ACTION_QUERY_RE.search(query))


def _get_weight_overrides(query: str) -> dict[str, float]:
    for pattern, weights in _WEIGHT_OVERRIDES:
        if pattern.search(query):
            return weights
    return DEFAULT_WEIGHTS


# ---------------------------------------------------------------------------
# Metadata sub-score (shared between v1 and v1.1 paths)
# ---------------------------------------------------------------------------


def _metadata_score(coord: dict, is_action: bool) -> float:
    """Compute normalized metadata score in [0, 1].

    Uses importance, confidence, heat, and risk (risk only for action queries).
    """
    risk_val = coord["risk"] if is_action else 0.0
    raw = (
        _META_W_IMPORTANCE * coord["importance"]
        + _META_W_CONFIDENCE * coord["confidence"]
        + _META_W_HEAT * coord["heat"]
        + _META_W_RISK * risk_val
    )
    # Max theoretical raw ≈ 1.0 (all weights sum to 1.0, all inputs max 1.0)
    return min(1.0, raw)


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def cosine_sim(
    vec_a: list[float] | np.ndarray, vec_b: list[float] | np.ndarray
) -> float:
    """Cosine similarity. Assumes L2-normalized inputs (dot = cosine)."""
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------


def rerank_candidates(
    candidates: list[dict],
    query_embedding: np.ndarray | list[float] | None,
    embedding_store: dict[str, list[float]] | None,
    is_action: bool,
) -> list[dict]:
    """Rerank spatial candidates.

    v1.1 (cosine available):
        score = 0.20 * proximity + 0.65 * cosine_sim + 0.15 * metadata
        Cosine dominates — PCA proximity is a coarse prefilter, not a ranking signal.
    v1 (cosine unavailable):
        score = 0.70 * proximity + 0.30 * metadata
    """
    if not candidates:
        return candidates

    use_cosine = query_embedding is not None and embedding_store is not None
    q_emb = np.asarray(query_embedding, dtype=np.float32) if use_cosine else None
    max_dist = max(c["distance"] for c in candidates) or 1.0

    for c in candidates:
        coord = c["semantic_coord"]
        proximity = 1.0 - (c["distance"] / max_dist)
        meta = _metadata_score(coord, is_action)

        if use_cosine:
            node_emb = embedding_store.get(c["node_id"])
            if node_emb is not None:
                sim = cosine_sim(q_emb, node_emb)
                sim_score = (sim + 1.0) / 2.0  # shift [-1,1] → [0,1]
            else:
                sim_score = 0.5
            score = 0.20 * proximity + 0.65 * sim_score + 0.15 * meta
        else:
            sim_score = 0.0
            score = 0.70 * proximity + 0.30 * meta

        c["proximity_score"] = round(proximity, 6)
        c["semantic_similarity"] = round(sim_score, 6)
        c["metadata_score"] = round(meta, 6)
        c["score"] = round(score, 6)

    candidates.sort(key=lambda c: -c["score"])
    return candidates


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def project_query(
    query: str, pca_model: dict
) -> tuple[float, float, float, np.ndarray]:
    """Project a user query into semantic coordinate space.

    Returns (x, y, z, embedding) — the embedding is reusable for cosine
    reranking so callers never need to embed the query a second time.
    """
    from eos_ai.embedder import embed

    embedding = embed(query)
    x = _project_x(embedding, pca_model)
    y = _query_to_y(query)
    z = _query_to_z(query)
    return (x, y, z, embedding)


def region_search(
    graph: dict,
    qcoord: tuple[float, float, float],
    top_k: int = 25,
    weights: dict[str, float] | None = None,
    query: str = "",
    embedding_store: dict[str, list[float]] | None = None,
    query_embedding: np.ndarray | list[float] | None = None,
) -> list[dict]:
    """Dual-pool prefilter → cosine rerank → return top_k candidates.

    v1 (no cosine): spatial prefilter only, ranked by proximity + metadata.
    v1.1 (cosine):  union of PCA spatial pool + direct cosine pool, then
                    final rerank by cosine-dominant scoring.

    The dual-pool approach compensates for PCA's lossy 3D compression:
    PCA catches nodes that are structurally nearby, cosine catches nodes
    that are semantically similar but spatially misplaced.
    """
    if weights is None:
        weights = _get_weight_overrides(query) if query else DEFAULT_WEIGHTS

    wx = weights.get("wx", DEFAULT_WEIGHTS["wx"])
    wy = weights.get("wy", DEFAULT_WEIGHTS["wy"])
    wz = weights.get("wz", DEFAULT_WEIGHTS["wz"])
    qx, qy, qz = qcoord
    use_cosine = embedding_store is not None and query_embedding is not None

    # Build full node list with spatial distance
    all_nodes: list[dict] = []
    for section in _GRAPH_SECTIONS:
        for node_id, node in graph.get(section, {}).items():
            coord = node.get("semantic_coord")
            if not coord:
                continue
            dx = coord["x"] - qx
            dy = coord["y"] - qy
            dz = coord["z"] - qz
            dist = math.sqrt(wx * dx * dx + wy * dy * dy + wz * dz * dz)
            all_nodes.append(
                {
                    "node_id": node_id,
                    "section": section,
                    "distance": dist,
                    "semantic_coord": coord,
                }
            )

    is_action = _is_action_query(query)

    if not use_cosine:
        # v1 path: spatial only
        all_nodes.sort(key=lambda c: c["distance"])
        pre_rerank = all_nodes[: top_k * 2]
        pre_rerank = rerank_candidates(pre_rerank, None, None, is_action)
        result = pre_rerank[:top_k]
    else:
        # v1.1 dual-pool: PCA spatial pool + direct cosine pool → union → rerank
        q_emb = np.asarray(query_embedding, dtype=np.float32)

        # Pool A: top spatial candidates (PCA catches structural neighbors)
        all_nodes.sort(key=lambda c: c["distance"])
        spatial_pool_size = top_k * 4
        pool_a = {c["node_id"]: c for c in all_nodes[:spatial_pool_size]}

        # Pool B: top cosine candidates (catches semantically similar but
        # spatially misplaced nodes — the whole point of this upgrade)
        cosine_pool_size = top_k * 4
        cosine_scored: list[tuple[float, dict]] = []
        for c in all_nodes:
            node_emb = embedding_store.get(c["node_id"])
            if node_emb is not None:
                sim = cosine_sim(q_emb, node_emb)
            else:
                sim = 0.0
            cosine_scored.append((sim, c))
        cosine_scored.sort(key=lambda t: -t[0])
        pool_b = {t[1]["node_id"]: t[1] for t in cosine_scored[:cosine_pool_size]}

        # Union: deduplicate by node_id, pool_b entries fill gaps
        merged = dict(pool_a)
        merged.update({k: v for k, v in pool_b.items() if k not in merged})
        pre_rerank = list(merged.values())

        pre_rerank = rerank_candidates(
            pre_rerank, query_embedding, embedding_store, is_action
        )
        result = pre_rerank[:top_k]

    fallback = len(result) < SPARSE_THRESHOLD
    for c in result:
        c["fallback_used"] = fallback

    return result


def expand_with_graph(
    graph: dict,
    node_ids: list[str],
    hops: int = 1,
) -> dict:
    """Expand candidate nodes via graph edges (1-2 hop BFS)."""
    out_edges: dict[str, list[str]] = {}
    in_edges: dict[str, list[str]] = {}
    for edge in graph.get("edges", []):
        src = edge["from_id"]
        dst = edge["to_id"]
        out_edges.setdefault(src, []).append(dst)
        in_edges.setdefault(dst, []).append(src)

    visited: set[str] = set(node_ids)
    frontier = set(node_ids)

    for _ in range(hops):
        next_frontier: set[str] = set()
        for nid in frontier:
            for neighbor in out_edges.get(nid, []):
                if neighbor not in visited:
                    next_frontier.add(neighbor)
            for neighbor in in_edges.get(nid, []):
                if neighbor not in visited:
                    next_frontier.add(neighbor)
        visited.update(next_frontier)
        frontier = next_frontier

    all_nodes: dict[str, dict] = {}
    for section in _GRAPH_SECTIONS:
        for node_id, node in graph.get(section, {}).items():
            if node_id in visited:
                all_nodes[node_id] = {"section": section, "data": node}

    relevant_edges = [
        e
        for e in graph.get("edges", [])
        if e["from_id"] in visited and e["to_id"] in visited
    ]

    return {
        "nodes": all_nodes,
        "edges": relevant_edges,
        "seed_count": len(node_ids),
        "expanded_count": len(all_nodes),
        "hop_count": hops,
    }


# ---------------------------------------------------------------------------
# Wiki-aware layer (v1.2)
# ---------------------------------------------------------------------------


def apply_wiki_layer(
    candidates: list[dict],
    graph: dict,
    max_expansions: int = 3,
) -> list[dict]:
    """Enrich candidates with wiki signal and apply bounded rerank bonus.

    Steps:
        1. Build wiki index (cheap file scan, cached on WikiIndex instance)
        2. Enrich each candidate with wiki metadata
        3. Apply bounded wiki bonus to scores
        4. Traverse 1-hop wikilinks for additional candidates
        5. Re-sort by updated score

    Falls back cleanly: if wiki layer fails, returns candidates unchanged.
    """
    try:
        from core.wiki_navigation import (
            WikiIndex,
            enrich_candidates,
            wiki_rerank_bonus,
            wiki_traverse,
        )
    except ImportError:
        return candidates

    try:
        wiki_index = WikiIndex().build(graph)
        candidates = enrich_candidates(candidates, wiki_index)

        # Apply wiki bonus
        for c in candidates:
            bonus = wiki_rerank_bonus(c)
            c["wiki_bonus"] = round(bonus, 6)
            c["score"] = round(c.get("score", 0.0) + bonus, 6)

        # Wiki traversal: discover additional nodes via wikilinks
        expansion_ids = wiki_traverse(
            candidates, wiki_index, max_expansions=max_expansions
        )
        if expansion_ids:
            # Look up expanded nodes in graph and add as low-score candidates
            for node_id in expansion_ids:
                for section in _GRAPH_SECTIONS:
                    node = graph.get(section, {}).get(node_id)
                    if node and node.get("semantic_coord"):
                        wiki_meta = wiki_index.get_wiki_for_node(node_id)
                        candidates.append(
                            {
                                "node_id": node_id,
                                "section": section,
                                "distance": 999.0,
                                "semantic_coord": node["semantic_coord"],
                                "score": 0.01,
                                "wiki_bonus": 0.01,
                                "wiki": wiki_meta,
                                "wiki_traversal": True,
                                "proximity_score": 0.0,
                                "semantic_similarity": 0.0,
                                "metadata_score": 0.0,
                                "fallback_used": False,
                            }
                        )
                        break

        # Re-sort by score (wiki bonus may have changed ordering)
        candidates.sort(key=lambda c: -c["score"])
        return candidates

    except Exception:
        # Fallback: return candidates unchanged
        return candidates


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_pca_model(path: str = PCA_META_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def load_embedding_store(path: str = EMBEDDING_STORE_PATH) -> dict[str, list[float]]:
    with open(path) as f:
        return json.load(f)
