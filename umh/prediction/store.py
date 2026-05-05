"""Prediction store — append-only registry of emitted predictions.

PredictionRecords are immutable snapshots of predictions at emission
time. Status transitions are forward-only (PENDING → MATCHED/MISSED/EXPIRED).
Core fields (intent snapshot, confidence, predicted actions) are never
mutated after creation.

Thread-safe. In-memory v1 — ready for persistence layer later.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.prediction.intent import UserIntent


@unique
class PredictionStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    MISSED = "missed"
    EXPIRED = "expired"


@dataclass
class PredictionRecord:
    """Tracked prediction with lifecycle status.

    Core fields (prediction_id, intent snapshot, confidence,
    predicted_actions, context_hash, emitted_at) are set at creation
    and NEVER modified. Only status and resolved_at change.
    """

    prediction_id: str
    intent_id: str
    inferred_goal: str
    confidence: float
    predicted_actions: tuple[str, ...]
    related_entities: tuple[str, ...]
    source: str
    context_hash: str
    emitted_at: str
    status: PredictionStatus = PredictionStatus.PENDING
    resolved_at: str = ""
    matched_job_id: str = ""
    tick_emitted: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "intent_id": self.intent_id,
            "inferred_goal": self.inferred_goal,
            "confidence": self.confidence,
            "predicted_actions": list(self.predicted_actions),
            "related_entities": list(self.related_entities),
            "source": self.source,
            "context_hash": self.context_hash,
            "emitted_at": self.emitted_at,
            "status": self.status.value,
            "resolved_at": self.resolved_at,
            "matched_job_id": self.matched_job_id,
            "tick_emitted": self.tick_emitted,
            "metadata": self.metadata,
        }


def _make_prediction_id() -> str:
    return f"pred_{uuid.uuid4().hex[:12]}"


def _compute_context_hash(intent: UserIntent) -> str:
    """Deterministic hash of the intent's key fields for deduplication."""
    content = f"{intent.inferred_goal}|{','.join(intent.predicted_actions)}|{','.join(intent.related_entities)}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def record_from_intent(
    intent: UserIntent,
    *,
    tick: int = 0,
) -> PredictionRecord:
    """Create a PredictionRecord from a UserIntent snapshot."""
    return PredictionRecord(
        prediction_id=_make_prediction_id(),
        intent_id=intent.intent_id,
        inferred_goal=intent.inferred_goal,
        confidence=intent.confidence,
        predicted_actions=intent.predicted_actions,
        related_entities=intent.related_entities,
        source=intent.source,
        context_hash=_compute_context_hash(intent),
        emitted_at=_iso_now(),
        tick_emitted=tick,
    )


_MAX_PREDICTION_RECORDS = 5000
_DEFAULT_EXPIRY_TICKS = 50


class PredictionStore:
    """Append-only registry of prediction records.

    Thread-safe. Records are never removed — only status transitions.
    Bounded by max_records (oldest records evicted on overflow).
    """

    def __init__(
        self,
        *,
        max_records: int = _MAX_PREDICTION_RECORDS,
        expiry_ticks: int = _DEFAULT_EXPIRY_TICKS,
    ) -> None:
        self._lock = threading.Lock()
        self._records: list[PredictionRecord] = []
        self._by_id: dict[str, PredictionRecord] = {}
        self._max_records = max_records
        self._expiry_ticks = expiry_ticks

    def append(self, record: PredictionRecord) -> None:
        """Store a prediction record. Append-only."""
        with self._lock:
            self._records.append(record)
            self._by_id[record.prediction_id] = record
            if len(self._records) > self._max_records:
                removed = self._records.pop(0)
                self._by_id.pop(removed.prediction_id, None)

    def get(self, prediction_id: str) -> PredictionRecord | None:
        with self._lock:
            return self._by_id.get(prediction_id)

    def list_pending(self) -> list[PredictionRecord]:
        with self._lock:
            return [r for r in self._records if r.status == PredictionStatus.PENDING]

    def list_all(self) -> list[PredictionRecord]:
        with self._lock:
            return list(self._records)

    def list_resolved(self) -> list[PredictionRecord]:
        with self._lock:
            return [r for r in self._records if r.status != PredictionStatus.PENDING]

    @property
    def total(self) -> int:
        with self._lock:
            return len(self._records)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if r.status == PredictionStatus.PENDING)

    def mark_matched(
        self,
        prediction_id: str,
        *,
        matched_job_id: str = "",
    ) -> bool:
        """Transition a PENDING prediction to MATCHED. Returns False if not found or not pending."""
        with self._lock:
            rec = self._by_id.get(prediction_id)
            if rec is None or rec.status != PredictionStatus.PENDING:
                return False
            rec.status = PredictionStatus.MATCHED
            rec.resolved_at = _iso_now()
            rec.matched_job_id = matched_job_id
            return True

    def mark_missed(self, prediction_id: str) -> bool:
        """Transition a PENDING prediction to MISSED."""
        with self._lock:
            rec = self._by_id.get(prediction_id)
            if rec is None or rec.status != PredictionStatus.PENDING:
                return False
            rec.status = PredictionStatus.MISSED
            rec.resolved_at = _iso_now()
            return True

    def expire_old_predictions(self, *, current_tick: int) -> int:
        """Mark PENDING predictions as EXPIRED if they exceed expiry_ticks."""
        expired_count = 0
        with self._lock:
            for rec in self._records:
                if rec.status != PredictionStatus.PENDING:
                    continue
                if current_tick - rec.tick_emitted >= self._expiry_ticks:
                    rec.status = PredictionStatus.EXPIRED
                    rec.resolved_at = _iso_now()
                    expired_count += 1
        return expired_count

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._by_id.clear()
