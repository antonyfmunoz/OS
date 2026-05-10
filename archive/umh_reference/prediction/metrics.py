"""Prediction accuracy metrics — read-only computation from stored records.

Computes accuracy rates, confidence calibration, and per-source
breakdowns from resolved PredictionRecords. Stateless — recomputes
from scratch on every call. Never mutates the underlying records.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from umh.prediction.store import PredictionRecord, PredictionStatus, PredictionStore


@dataclass(frozen=True)
class PredictionAccuracy:
    """Aggregate accuracy metrics for a set of predictions."""

    total_predictions: int
    pending: int
    matched: int
    missed: int
    expired: int
    accuracy_rate: float
    miss_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_predictions": self.total_predictions,
            "pending": self.pending,
            "matched": self.matched,
            "missed": self.missed,
            "expired": self.expired,
            "accuracy_rate": round(self.accuracy_rate, 4),
            "miss_rate": round(self.miss_rate, 4),
        }


@dataclass(frozen=True)
class ConfidenceBucket:
    """Accuracy within a confidence range."""

    bucket_low: float
    bucket_high: float
    count: int
    matched: int
    actual_accuracy: float
    avg_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "bucket": f"{self.bucket_low:.1f}-{self.bucket_high:.1f}",
            "count": self.count,
            "matched": self.matched,
            "actual_accuracy": round(self.actual_accuracy, 4),
            "avg_confidence": round(self.avg_confidence, 4),
        }


@dataclass(frozen=True)
class SourceAccuracy:
    """Accuracy metrics broken down by prediction source."""

    source: str
    total: int
    matched: int
    accuracy_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "total": self.total,
            "matched": self.matched,
            "accuracy_rate": round(self.accuracy_rate, 4),
        }


class PredictionMetrics:
    """Computes accuracy metrics from a PredictionStore. Stateless."""

    def compute_accuracy(
        self,
        records: list[PredictionRecord],
    ) -> PredictionAccuracy:
        """Compute aggregate accuracy from resolved records."""
        total = len(records)
        pending = sum(1 for r in records if r.status == PredictionStatus.PENDING)
        matched = sum(1 for r in records if r.status == PredictionStatus.MATCHED)
        missed = sum(1 for r in records if r.status == PredictionStatus.MISSED)
        expired = sum(1 for r in records if r.status == PredictionStatus.EXPIRED)

        resolved = matched + missed + expired
        accuracy_rate = matched / resolved if resolved > 0 else 0.0
        miss_rate = (missed + expired) / resolved if resolved > 0 else 0.0

        return PredictionAccuracy(
            total_predictions=total,
            pending=pending,
            matched=matched,
            missed=missed,
            expired=expired,
            accuracy_rate=accuracy_rate,
            miss_rate=miss_rate,
        )

    def compute_accuracy_from_store(
        self,
        store: PredictionStore,
    ) -> PredictionAccuracy:
        """Convenience: compute accuracy from a PredictionStore."""
        return self.compute_accuracy(store.list_all())

    def compute_confidence_calibration(
        self,
        records: list[PredictionRecord],
        *,
        bucket_count: int = 5,
    ) -> list[ConfidenceBucket]:
        """Compare predicted confidence vs actual accuracy in buckets.

        Divides the 0.0–1.0 confidence range into equal buckets and
        computes actual match rate in each. Well-calibrated predictions
        show confidence ≈ actual_accuracy per bucket.
        """
        resolved = [
            r for r in records
            if r.status in (PredictionStatus.MATCHED, PredictionStatus.MISSED, PredictionStatus.EXPIRED)
        ]
        if not resolved:
            return []

        bucket_width = 1.0 / bucket_count
        buckets: list[ConfidenceBucket] = []

        for i in range(bucket_count):
            low = i * bucket_width
            high = (i + 1) * bucket_width

            in_bucket = [
                r for r in resolved
                if low <= r.confidence < high or (i == bucket_count - 1 and r.confidence == high)
            ]
            if not in_bucket:
                continue

            count = len(in_bucket)
            matched = sum(1 for r in in_bucket if r.status == PredictionStatus.MATCHED)
            avg_conf = sum(r.confidence for r in in_bucket) / count

            buckets.append(
                ConfidenceBucket(
                    bucket_low=low,
                    bucket_high=high,
                    count=count,
                    matched=matched,
                    actual_accuracy=matched / count,
                    avg_confidence=avg_conf,
                )
            )

        return buckets

    def compute_source_accuracy(
        self,
        records: list[PredictionRecord],
    ) -> list[SourceAccuracy]:
        """Accuracy broken down by prediction source."""
        resolved = [
            r for r in records
            if r.status in (PredictionStatus.MATCHED, PredictionStatus.MISSED, PredictionStatus.EXPIRED)
        ]
        if not resolved:
            return []

        by_source: dict[str, list[PredictionRecord]] = {}
        for r in resolved:
            by_source.setdefault(r.source, []).append(r)

        results: list[SourceAccuracy] = []
        for source in sorted(by_source):
            group = by_source[source]
            total = len(group)
            matched = sum(1 for r in group if r.status == PredictionStatus.MATCHED)
            results.append(
                SourceAccuracy(
                    source=source,
                    total=total,
                    matched=matched,
                    accuracy_rate=matched / total if total > 0 else 0.0,
                )
            )

        return results
