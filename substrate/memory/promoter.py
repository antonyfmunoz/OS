"""MemoryPromoter — evaluates candidates for promotion to durable storage.

Three-layer deduplication:
  1. Exact hash — identical content blocked
  2. Semantic similarity — paraphrased content detected via TF-IDF cosine
  3. Contradiction detection — conflicting memories flagged

Temporal decay: memories lose effective weight over time unless reconfirmed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from substrate.memory.candidate_generator import MemoryCandidate

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE_THRESHOLD = 0.7
SEMANTIC_SIMILARITY_THRESHOLD = 0.75
DECAY_HALF_LIFE_DAYS = 30
_NEGATION_MARKERS = frozenset(
    ["not", "never", "don't", "dont", "stop", "avoid", "wrong", "incorrect", "false"]
)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _tfidf_cosine(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Cosine similarity between two token lists using TF weighting."""
    if not tokens_a or not tokens_b:
        return 0.0
    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)
    all_terms = set(counter_a) | set(counter_b)
    dot = sum(counter_a.get(t, 0) * counter_b.get(t, 0) for t in all_terms)
    mag_a = math.sqrt(sum(v * v for v in counter_a.values()))
    mag_b = math.sqrt(sum(v * v for v in counter_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _detect_contradiction(text_a: str, text_b: str) -> bool:
    """Detect if two memories contradict each other."""
    tokens_a = set(_tokenize(text_a))
    tokens_b = set(_tokenize(text_b))
    overlap = tokens_a & tokens_b
    if len(overlap) < 3:
        return False
    neg_a = tokens_a & _NEGATION_MARKERS
    neg_b = tokens_b & _NEGATION_MARKERS
    return bool(neg_a) != bool(neg_b)


def _temporal_weight(
    promoted_at: int | float, half_life_days: float = DECAY_HALF_LIFE_DAYS
) -> float:
    """Exponential decay weight: 1.0 at promotion time, halves every half_life_days."""
    age_seconds = max(0, time.time() - promoted_at)
    age_days = age_seconds / 86400
    return math.pow(0.5, age_days / half_life_days)


class MemoryPromoter:
    """Promotes memory candidates with semantic dedup, contradiction detection, and temporal decay."""

    def __init__(
        self,
        path: Path | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._path = path or Path("data/umh/promoted_memories.json")
        self._threshold = confidence_threshold
        self._memories: list[dict[str, Any]] = []
        self._seen_hashes: set[str] = set()
        self._token_cache: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._memories = json.loads(self._path.read_text())
                self._seen_hashes = {m.get("content_hash", "") for m in self._memories}
                for m in self._memories:
                    mid = m.get("memory_id", "")
                    self._token_cache[mid] = _tokenize(m.get("content", ""))
            except (json.JSONDecodeError, OSError):
                self._memories = []
                self._seen_hashes = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._memories, indent=2, default=str))

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _find_semantic_duplicate(self, content: str) -> dict[str, Any] | None:
        """Find a semantically similar existing memory via TF-IDF cosine."""
        candidate_tokens = _tokenize(content)
        best_score = 0.0
        best_match: dict[str, Any] | None = None
        for mem in self._memories:
            mid = mem.get("memory_id", "")
            mem_tokens = self._token_cache.get(mid, _tokenize(mem.get("content", "")))
            score = _tfidf_cosine(candidate_tokens, mem_tokens)
            if score > best_score:
                best_score = score
                best_match = mem
        if best_score >= SEMANTIC_SIMILARITY_THRESHOLD and best_match:
            return {"match": best_match, "similarity": round(best_score, 3)}
        return None

    def _find_contradiction(self, content: str) -> dict[str, Any] | None:
        """Find an existing memory that contradicts the candidate."""
        for mem in self._memories:
            if _detect_contradiction(content, mem.get("content", "")):
                return {"contradicts": mem, "memory_id": mem.get("memory_id", "")}
        return None

    def evaluate(self, candidate: MemoryCandidate) -> dict[str, Any]:
        """Evaluate a candidate for promotion with 3-layer dedup."""
        content_hash = self._hash_content(candidate.content)

        if candidate.confidence < self._threshold:
            return {
                "promoted": False,
                "reason": f"Below threshold ({candidate.confidence:.2f} < {self._threshold})",
                "candidate_id": candidate.candidate_id,
            }

        if content_hash in self._seen_hashes:
            return {
                "promoted": False,
                "reason": "Exact duplicate content",
                "candidate_id": candidate.candidate_id,
            }

        sem_dup = self._find_semantic_duplicate(candidate.content)
        if sem_dup:
            return {
                "promoted": False,
                "reason": f"Semantic duplicate (similarity={sem_dup['similarity']})",
                "candidate_id": candidate.candidate_id,
                "similar_to": sem_dup["match"].get("memory_id", ""),
            }

        contradiction = self._find_contradiction(candidate.content)
        if contradiction:
            return {
                "promoted": False,
                "reason": f"Contradicts existing memory {contradiction['memory_id']}",
                "candidate_id": candidate.candidate_id,
                "contradicts": contradiction["memory_id"],
                "needs_governance": True,
            }

        memory = {
            "memory_id": f"mem-p-{candidate.candidate_id.split('-')[-1]}",
            "candidate_id": candidate.candidate_id,
            "trace_id": candidate.source_trace_id,
            "content": candidate.content,
            "confidence": candidate.confidence,
            "scope": candidate.scope,
            "tags": candidate.tags,
            "content_hash": content_hash,
            "promoted_at": int(time.time()),
            "last_confirmed": int(time.time()),
            "confirmation_count": 1,
        }

        self._memories.append(memory)
        self._seen_hashes.add(content_hash)
        self._token_cache[memory["memory_id"]] = _tokenize(candidate.content)
        self._save()

        return {
            "promoted": True,
            "memory_id": memory["memory_id"],
            "candidate_id": candidate.candidate_id,
        }

    def reconfirm(self, memory_id: str) -> bool:
        """Reconfirm a memory — resets decay clock and increments count."""
        for mem in self._memories:
            if mem.get("memory_id") == memory_id:
                mem["last_confirmed"] = int(time.time())
                mem["confirmation_count"] = mem.get("confirmation_count", 1) + 1
                self._save()
                return True
        return False

    def effective_confidence(self, memory: dict[str, Any]) -> float:
        """Memory confidence adjusted by temporal decay."""
        base = memory.get("confidence", 0.5)
        confirmed_at = memory.get("last_confirmed", memory.get("promoted_at", time.time()))
        decay = _temporal_weight(confirmed_at)
        boost = min(0.2, 0.05 * memory.get("confirmation_count", 1))
        return min(1.0, round(base * decay + boost, 4))

    def decay_audit(self) -> list[dict[str, Any]]:
        """Return memories with decayed confidence below threshold."""
        decayed = []
        for mem in self._memories:
            eff = self.effective_confidence(mem)
            if eff < self._threshold:
                decayed.append(
                    {
                        "memory_id": mem.get("memory_id"),
                        "original_confidence": mem.get("confidence"),
                        "effective_confidence": eff,
                        "age_days": (time.time() - mem.get("promoted_at", time.time())) / 86400,
                    }
                )
        return decayed

    def list_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._memories[-limit:]

    def stats(self) -> dict[str, int]:
        return {
            "total_memories": len(self._memories),
            "unique_hashes": len(self._seen_hashes),
            "decayed_count": len(self.decay_audit()),
        }
