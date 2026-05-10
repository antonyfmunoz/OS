"""Sequence memory — append-only storage for sequence execution outcomes.

Records predicted vs. actual scores for objective sequences, enabling
the meta-planner to learn from historical performance. All records
are immutable after creation. Learning is opt-in and does not affect
determinism unless explicitly enabled.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


_MIN_ADJUSTMENT = 0.5
_MAX_ADJUSTMENT = 1.5
_DEFAULT_RECENCY_DECAY = 0.9
_MIN_RECORDS_FOR_ADJUSTMENT = 3


@dataclass(frozen=True)
class ContextSignature:
    """Hash-based signature of planning context for grouping outcomes."""

    features: tuple[str, ...]
    hash_value: str = ""

    def __post_init__(self) -> None:
        if not self.hash_value:
            raw = "|".join(sorted(self.features))
            h = hashlib.sha256(raw.encode()).hexdigest()[:16]
            object.__setattr__(self, "hash_value", h)

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": list(self.features),
            "hash_value": self.hash_value,
        }


@dataclass(frozen=True)
class SequenceRecord:
    """Immutable record of a sequence execution outcome."""

    record_id: str
    objective_ids: tuple[str, ...]
    predicted_score: float
    actual_score: float
    delta: float
    timestamp: str
    context_signature: ContextSignature | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "objective_ids": list(self.objective_ids),
            "predicted_score": round(self.predicted_score, 4),
            "actual_score": round(self.actual_score, 4),
            "delta": round(self.delta, 4),
            "timestamp": self.timestamp,
            "context_signature": self.context_signature.to_dict()
            if self.context_signature
            else None,
        }


def make_sequence_record(
    record_id: str,
    objective_ids: list[str],
    predicted_score: float,
    actual_score: float,
    *,
    context_signature: ContextSignature | None = None,
    timestamp: str = "",
) -> SequenceRecord:
    """Create a SequenceRecord with computed delta."""
    return SequenceRecord(
        record_id=record_id,
        objective_ids=tuple(objective_ids),
        predicted_score=predicted_score,
        actual_score=actual_score,
        delta=actual_score - predicted_score,
        timestamp=timestamp or _iso_now(),
        context_signature=context_signature,
    )


class SequenceMemory:
    """Append-only store for sequence execution records.

    Supports querying by sequence pattern (exact or prefix match)
    and computing historical success rates and adjustment factors.
    Records are never mutated after creation.
    """

    def __init__(
        self,
        *,
        recency_decay: float = _DEFAULT_RECENCY_DECAY,
    ) -> None:
        self._records: list[SequenceRecord] = []
        self._recency_decay = max(0.5, min(1.0, recency_decay))

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def recency_decay(self) -> float:
        return self._recency_decay

    def append(self, record: SequenceRecord) -> None:
        """Append a record. Never modifies existing records."""
        self._records.append(record)

    def query_exact(self, objective_ids: list[str]) -> list[SequenceRecord]:
        """Find records with exactly matching objective sequence."""
        key = tuple(objective_ids)
        return [r for r in self._records if r.objective_ids == key]

    def query_prefix(self, prefix_ids: list[str]) -> list[SequenceRecord]:
        """Find records whose sequence starts with the given prefix."""
        prefix = tuple(prefix_ids)
        n = len(prefix)
        return [r for r in self._records if r.objective_ids[:n] == prefix]

    def query_contains(self, objective_id: str) -> list[SequenceRecord]:
        """Find records containing the given objective anywhere."""
        return [r for r in self._records if objective_id in r.objective_ids]

    def get_success_rate(self, objective_ids: list[str]) -> float | None:
        """Compute success rate for matching sequences.

        Success = actual_score >= predicted_score (delta >= 0).
        Returns None if no matching records exist.
        """
        matches = self.query_exact(objective_ids)
        if not matches:
            return None
        successes = sum(1 for r in matches if r.delta >= 0)
        return successes / len(matches)

    def get_avg_delta(self, objective_ids: list[str]) -> float | None:
        """Compute average delta for matching sequences.

        Returns None if no matching records exist.
        """
        matches = self.query_exact(objective_ids)
        if not matches:
            return None
        return sum(r.delta for r in matches) / len(matches)

    def get_recency_weighted_delta(self, objective_ids: list[str]) -> float | None:
        """Compute recency-weighted average delta.

        More recent records have higher weight. Uses exponential decay.
        Returns None if no matching records exist.
        """
        matches = self.query_exact(objective_ids)
        if not matches:
            return None

        total_weight = 0.0
        weighted_delta = 0.0
        n = len(matches)
        for i, rec in enumerate(matches):
            weight = self._recency_decay ** (n - 1 - i)
            weighted_delta += rec.delta * weight
            total_weight += weight

        if total_weight <= 0:
            return 0.0
        return weighted_delta / total_weight

    def compute_adjustment_factor(self, objective_ids: list[str]) -> float:
        """Compute scoring adjustment factor from historical performance.

        Based on success rate and recency-weighted delta.
        Clamped to [0.5, 1.5]. Returns 1.0 if insufficient data.
        """
        matches = self.query_exact(objective_ids)
        if len(matches) < _MIN_RECORDS_FOR_ADJUSTMENT:
            return 1.0

        success_rate = self.get_success_rate(objective_ids)
        if success_rate is None:
            return 1.0

        avg_delta = self.get_recency_weighted_delta(objective_ids)
        if avg_delta is None:
            return 1.0

        adjustment = 1.0 + (success_rate - 0.5) * 0.5 + avg_delta * 0.3
        return max(_MIN_ADJUSTMENT, min(_MAX_ADJUSTMENT, adjustment))

    def list_all(self) -> list[SequenceRecord]:
        """Return all records. Read-only snapshot."""
        return list(self._records)

    def clear(self) -> None:
        """Remove all records."""
        self._records.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "recency_decay": self._recency_decay,
            "records": [r.to_dict() for r in self._records],
        }
