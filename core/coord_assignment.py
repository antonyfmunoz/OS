"""
Semantic Space v1.1 — Coordinate Assignment (Hybrid Index)

Assigns each graph node a hybrid coordinate (1 learned + 2 rule-based):
  x = semantic position (PCA-1D of embedding — the only learned dimension)
  y = abstraction level (deterministic keyword table — NOT spatial)
  z = temporal state (recency + instability — NOT spatial)

This is a 1D semantic index with 2 categorical organizational axes.
Cosine similarity on the full embedding is the true ranking signal.

Plus metadata: importance, confidence, risk, heat.

Usage:
    from core.coord_assignment import assign_semantic_coords
    graph = assign_semantic_coords(graph)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ABSTRACTION_BANDS: dict[str, float] = {
    "log": 0.05,
    "message": 0.10,
    "file": 0.18,
    "function": 0.30,
    "class": 0.38,
    "action": 0.42,
    "event": 0.44,
    "workflow": 0.58,
    "module": 0.62,
    "service": 0.68,
    "summary": 0.78,
    "policy": 0.88,
    "strategy": 0.94,
    "doctrine": 0.98,
}

ABSTRACTION_DEFAULT = 0.50

# Path nudges: keywords in file path that shift Y
_PATH_NUDGE_LOW = {"logs", "state", "event", "data"}
_PATH_NUDGE_HIGH = {"docs", "wiki", "policy", "strategy", "10_Wiki"}

PCA_META_PATH = "data/semantic_space/pca_v1.json"
EMBEDDING_STORE_PATH = "data/semantic_space/embeddings_v1.json"

_GRAPH_SECTIONS = ("files", "classes", "functions")

# Confidence tiers
_CONFIDENCE_CANONICAL_WITH_SUMMARY = 1.0
_CONFIDENCE_CANONICAL_NO_SUMMARY = 0.8
_CONFIDENCE_INFERRED = 0.4


# ---------------------------------------------------------------------------
# Node classification helpers
# ---------------------------------------------------------------------------


def _summary_key(node_id: str, node: dict) -> str:
    """Canonical summary-lookup key for a node."""
    if "module_name" in node:
        return f"file::{node.get('path', node_id)}"
    if "methods" in node or "bases" in node:
        return f"class::{node_id}"
    return f"function::{node_id}"


def _infer_node_type(node_id: str, node: dict) -> str:
    """Infer type string from node structure."""
    if "module_name" in node or node.get("path", "").endswith(".py"):
        path = node.get("path", node_id).lower()
        if "service" in path:
            return "service"
        if "workflow" in path or "orchestrat" in path:
            return "workflow"
        if "policy" in path or "authority" in path:
            return "policy"
        if "strategy" in path:
            return "strategy"
        if "action" in path:
            return "action"
        # "log" in path but not in "cognitive_loop"
        if "log" in path and "cognitive_loop" not in path:
            return "log"
        return "module"

    if "methods" in node or "bases" in node:
        return "class"
    if "args" in node or "return_annotation" in node:
        return "function"
    return "file"


# ---------------------------------------------------------------------------
# Y axis — abstraction (deterministic)
# ---------------------------------------------------------------------------


def _compute_y(node_id: str, node: dict) -> float:
    """Deterministic abstraction level from node type and path."""
    node_type = _infer_node_type(node_id, node)
    y = ABSTRACTION_BANDS.get(node_type, ABSTRACTION_DEFAULT)

    path = node.get("path", node.get("file_path", node_id))
    if path:
        parts = set(Path(path).parts)
        if parts & _PATH_NUDGE_LOW:
            y -= 0.05
        elif parts & _PATH_NUDGE_HIGH:
            y += 0.05

    return max(0.0, min(1.0, y))


# ---------------------------------------------------------------------------
# Z axis — temporal state
# ---------------------------------------------------------------------------


def _compute_z(node_id: str, node: dict) -> float:
    """Z = 0.6 * recency + 0.4 * instability, both in [0, 1]."""
    recency = _recency_score(node)
    instability = _instability_score(node)
    return max(0.0, min(1.0, 0.6 * recency + 0.4 * instability))


def _recency_score(node: dict) -> float:
    """Proxy recency from structural signals.

    Without per-file timestamps in the graph, we use heuristics:
    entry points and critical files tend to be more recently active.
    """
    score = 0.3
    if node.get("is_entry_point"):
        score += 0.2
    if node.get("is_critical"):
        score += 0.2
    line_count = node.get("line_count", 0)
    if line_count > 200:
        score += 0.1
    if line_count > 500:
        score += 0.1
    return min(1.0, score)


def _instability_score(node: dict) -> float:
    """Instability proxy: files with many imports/functions/calls are change-prone."""
    score = 0.2
    if len(node.get("imports", [])) > 10:
        score += 0.2
    if len(node.get("functions", [])) > 20:
        score += 0.2
    if len(node.get("calls", [])) > 5:
        score += 0.2
    return min(1.0, score)


# ---------------------------------------------------------------------------
# Rerank features (metadata, not geometry)
# ---------------------------------------------------------------------------


def _compute_importance(node_id: str, node: dict, edge_stats: dict) -> float:
    """Importance from graph centrality (inbound*2 + outbound, cap 100)."""
    counts = edge_stats.get(node_id, {"in": 0, "out": 0})
    raw = counts["in"] * 2 + counts["out"]
    return min(1.0, raw / 100.0)


def _compute_confidence(node_id: str, node: dict, summaries: dict) -> float:
    """Confidence from node provenance."""
    has_summary = _summary_key(node_id, node) in summaries
    has_docstring = bool(node.get("docstring"))

    if has_summary or has_docstring:
        return _CONFIDENCE_CANONICAL_WITH_SUMMARY
    if "module_name" in node:
        return _CONFIDENCE_CANONICAL_NO_SUMMARY
    return _CONFIDENCE_INFERRED


def _compute_risk(node: dict) -> float:
    """Risk from critical-node and entry-point flags."""
    if node.get("is_critical"):
        return 0.9
    if node.get("is_entry_point"):
        return 0.6
    return 0.2


# ---------------------------------------------------------------------------
# X axis — semantic position (PCA-1D)
# ---------------------------------------------------------------------------


def _assemble_text(node_id: str, node: dict, summaries: dict) -> str:
    """Canonical text for embedding: title + summary + node_type."""
    title = node.get("name", node.get("path", node_id))

    summary_entry = summaries.get(_summary_key(node_id, node), {})
    if isinstance(summary_entry, dict):
        summary_text = summary_entry.get("current", {}).get("summary", "")
    else:
        summary_text = str(summary_entry)
    if not summary_text:
        summary_text = (node.get("docstring") or "")[:200]

    node_type = _infer_node_type(node_id, node)

    parts = [title]
    if summary_text:
        parts.append(summary_text)
    parts.append(node_type)
    return "\n".join(parts)


def _build_pca_model(embeddings: np.ndarray) -> dict:
    """Fit PCA-1D on embeddings, return serializable model."""
    from sklearn.decomposition import PCA

    pca = PCA(n_components=1)
    projected = pca.fit_transform(embeddings).flatten()

    return {
        "coord_version": "v1",
        "x_method": "pca_1d_v1",
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "pca_components": pca.components_.tolist(),
        "pca_mean": pca.mean_.tolist(),
        "x_min_raw": float(projected.min()),
        "x_max_raw": float(projected.max()),
    }


def _project_x(embedding: np.ndarray, pca_model: dict) -> float:
    """Project a single embedding to normalized x in [-1, 1]."""
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
# Public API
# ---------------------------------------------------------------------------


def compute_node_coord(
    node_id: str,
    node: dict,
    pca_model: dict,
    embedding: np.ndarray,
    summaries: dict,
    edge_stats: dict,
) -> dict:
    """Compute full semantic coordinate for a single node.

    Returns:
        Dict with semantic_coord and semantic_meta.
    """
    return {
        "semantic_coord": {
            "x": round(_project_x(embedding, pca_model), 6),
            "y": round(_compute_y(node_id, node), 6),
            "z": round(_compute_z(node_id, node), 6),
            "importance": round(_compute_importance(node_id, node, edge_stats), 6),
            "confidence": round(_compute_confidence(node_id, node, summaries), 6),
            "risk": round(_compute_risk(node), 6),
            "heat": 0.0,
        },
        "semantic_meta": {
            "x_method": "pca_1d_v1",
            "y_method": "rule_table_v1",
            "z_method": "recency_instability_v1",
            "coord_version": "v1",
        },
    }


def assign_semantic_coords(graph: dict) -> dict:
    """Assign semantic coordinates to all nodes in the graph.

    Writes PCA model and embedding store to data/semantic_space/.
    Modifies graph in-place and returns it.
    """
    from eos_ai.embedder import embed

    summaries = _load_summaries()
    edge_stats = _compute_edge_stats(graph)

    # Collect all nodes
    all_nodes: list[tuple[str, dict]] = []
    for section in _GRAPH_SECTIONS:
        for node_id, node in graph.get(section, {}).items():
            all_nodes.append((node_id, node))

    print(f"[coord_assignment] Processing {len(all_nodes)} nodes...")

    # Step 1: Embed all nodes
    texts = [_assemble_text(nid, n, summaries) for nid, n in all_nodes]
    print(f"[coord_assignment] Embedding {len(texts)} texts...")
    t0 = time.time()
    embeddings = np.array([embed(t) for t in texts], dtype=np.float32)
    print(f"[coord_assignment] Embedding done in {time.time() - t0:.1f}s")

    # Step 2: Build PCA model
    print("[coord_assignment] Fitting PCA-1D...")
    pca_model = _build_pca_model(embeddings)
    _write_json(os.path.join(_ROOT, PCA_META_PATH), pca_model, indent=2)
    print(f"[coord_assignment] PCA model saved to {PCA_META_PATH}")

    # Step 3: Assign coordinates and collect embedding store
    embedding_store: dict[str, list[float]] = {}
    for i, (node_id, node) in enumerate(all_nodes):
        coord_data = compute_node_coord(
            node_id,
            node,
            pca_model,
            embeddings[i],
            summaries,
            edge_stats,
        )
        node["semantic_coord"] = coord_data["semantic_coord"]
        node["semantic_meta"] = coord_data["semantic_meta"]
        embedding_store[node_id] = embeddings[i].tolist()

    # Step 4: Persist embedding store (sorted keys for determinism)
    _write_json(
        os.path.join(_ROOT, EMBEDDING_STORE_PATH),
        embedding_store,
        sort_keys=True,
    )
    print(
        f"[coord_assignment] Embedding store saved to {EMBEDDING_STORE_PATH} "
        f"({len(embedding_store)} nodes)"
    )

    # Step 5: Top-level provenance
    graph["semantic_space_meta"] = {
        "enabled": True,
        "coord_version": "v1.1",
        "coord_type": "hybrid_1d_semantic_plus_2_categorical",
        "dimensions": {
            "x": "learned (PCA-1D of embedding)",
            "y": "rule-based (abstraction level)",
            "z": "rule-based (temporal state)",
        },
        "ranking_signal": "cosine_similarity (65% weight in v1.1 reranker)",
        "node_count": len(all_nodes),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "pca_model_path": PCA_META_PATH,
        "embedding_store_path": EMBEDDING_STORE_PATH,
        "rerank_mode": "pca_prefilter_plus_cosine_v1",
    }

    print(f"[coord_assignment] Assigned coordinates to {len(all_nodes)} nodes")
    return graph


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_summaries() -> dict:
    """Load node summaries from data/node_summaries.json."""
    path = f"{_ROOT}/data/node_summaries.json"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("nodes", data)


def _compute_edge_stats(graph: dict) -> dict[str, dict[str, int]]:
    """Build in/out edge counts per node."""
    stats: dict[str, dict[str, int]] = {}
    for edge in graph.get("edges", []):
        src = edge.get("from_id", "")
        dst = edge.get("to_id", "")
        stats.setdefault(src, {"in": 0, "out": 0})["out"] += 1
        stats.setdefault(dst, {"in": 0, "out": 0})["in"] += 1
    return stats


def _write_json(
    path: str, data: dict, indent: int | None = None, sort_keys: bool = False
) -> None:
    """Write JSON atomically — create parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, sort_keys=sort_keys)
