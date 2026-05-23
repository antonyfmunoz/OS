"""
Lightweight text embedder — shared singleton used by memory.py and
skill_registry.py.

Model: BAAI/bge-small-en-v1.5 via fastembed
  - 384-dimensional float32 vectors
  - ONNX runtime, no GPU required
  - ~33MB model, cached after first download
  - Real semantic embeddings, not heuristics

Usage:
    from substrate.understanding.embedding.embedder import embed, cosine_similarity, DIMS

    vec = embed("analyze this lead who feels stuck")
    sim = cosine_similarity(vec_a, vec_b)   # float in [-1, 1]
"""

import numpy as np

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMS = 384

_model = None   # module-level singleton — loaded once per process


def _get_model():
    global _model
    if _model is None:
        try:
            from fastembed import TextEmbedding
            _model = TextEmbedding(_MODEL_NAME)
        except ImportError:
            raise ImportError(
                "fastembed is required for semantic search. "
                "Install with: pip install fastembed --break-system-packages"
            )
    return _model


def embed(text: str) -> np.ndarray:
    """
    Return a normalized 384-dim float32 embedding for text.
    L2-normalized so dot product == cosine similarity.
    """
    model = _get_model()
    vec   = np.array(next(model.embed([text])), dtype=np.float32)
    norm  = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two unit vectors.
    Both inputs must be L2-normalized (use embed() to guarantee this).
    Returns float in [-1, 1]; 1.0 = identical, 0.0 = orthogonal.
    """
    return float(np.dot(a, b))


def serialize(vec: np.ndarray) -> bytes:
    """Serialize float32 ndarray to bytes for SQLite BLOB storage."""
    return vec.astype(np.float32).tobytes()


def deserialize(blob: bytes) -> np.ndarray:
    """Deserialize bytes from SQLite BLOB back to float32 ndarray."""
    return np.frombuffer(blob, dtype=np.float32)
