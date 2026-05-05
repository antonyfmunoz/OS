"""Embedding layer — converts text to fixed-dimension vectors for similarity.

Pluggable: supports custom models via the EmbeddingModel protocol.
Default: TokenHashEmbedding — deterministic, no external dependencies.

All embeddings are cached (text hash → vector) for determinism and speed.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import hashlib
import math
import threading
from typing import Any, Protocol


_DEFAULT_DIM = 64
_MAX_CACHE_SIZE = 10000


class EmbeddingModel(Protocol):
    """Protocol for embedding models. Must be deterministic."""

    @property
    def dim(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


class TokenHashEmbedding:
    """Deterministic embedding via token hashing. No ML model required.

    Each token is hashed and mapped to a position in the vector.
    The result is L2-normalized.

    Same input always produces the same output.
    """

    def __init__(self, *, dim: int = _DEFAULT_DIM) -> None:
        if dim < 1:
            raise ValueError("dim must be >= 1")
        self._dim = dim
        self._lock = threading.Lock()
        self._cache: dict[str, list[float]] = {}

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        with self._lock:
            if text in self._cache:
                return list(self._cache[text])

        vec = self._compute(text)

        with self._lock:
            if len(self._cache) < _MAX_CACHE_SIZE:
                self._cache[text] = list(vec)

        return vec

    def _compute(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        tokens = text.lower().split()

        if not tokens:
            return vector

        for token in tokens:
            h = hashlib.sha256(token.encode()).digest()
            for i in range(min(len(h), self._dim)):
                vector[i % self._dim] += (h[i] - 128) / 128.0

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def cache_size(self) -> int:
        with self._lock:
            return len(self._cache)

    def get_state(self) -> dict[str, Any]:
        return {
            "dim": self._dim,
            "cache_size": self.cache_size(),
            "max_cache_size": _MAX_CACHE_SIZE,
        }
