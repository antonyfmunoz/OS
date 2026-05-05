"""Phase 78 feedback store — append-only persistence for feedback artifacts.

Append-only. No delete/clear/pop. In-memory with optional StorageBackend
backing. No memory promotion happens here.
"""

from __future__ import annotations

import threading
from typing import Any

from umh.feedback.memory_bridge import MemoryCandidate
from umh.feedback.outcome import OutcomeRecord
from umh.feedback.records import FeedbackRecord


class FeedbackStore:
    """Append-only store for Phase 78 feedback artifacts. Thread-safe."""

    def __init__(self) -> None:
        self._outcomes: list[OutcomeRecord] = []
        self._outcomes_by_id: dict[str, OutcomeRecord] = {}
        self._feedback: list[FeedbackRecord] = []
        self._candidates: list[MemoryCandidate] = []
        self._lock = threading.Lock()

    def append_outcome(self, outcome: OutcomeRecord) -> None:
        with self._lock:
            self._outcomes.append(outcome)
            self._outcomes_by_id[outcome.outcome_id] = outcome

    def append_feedback(self, feedback: FeedbackRecord) -> None:
        with self._lock:
            self._feedback.append(feedback)

    def append_memory_candidate(self, candidate: MemoryCandidate) -> None:
        with self._lock:
            self._candidates.append(candidate)

    def get_outcome(self, outcome_id: str) -> OutcomeRecord | None:
        return self._outcomes_by_id.get(outcome_id)

    def list_outcomes(
        self,
        user_id: str | None = None,
        trace_id: str | None = None,
        limit: int = 50,
    ) -> list[OutcomeRecord]:
        results = list(self._outcomes)
        if user_id:
            results = [o for o in results if o.user_id == user_id]
        if trace_id:
            results = [o for o in results if o.trace_id == trace_id]
        return results[-limit:]

    def list_feedback(
        self,
        user_id: str | None = None,
        trace_id: str | None = None,
        outcome_id: str | None = None,
        limit: int = 50,
    ) -> list[FeedbackRecord]:
        results = list(self._feedback)
        if user_id:
            results = [f for f in results if f.user_id == user_id]
        if trace_id:
            results = [f for f in results if f.trace_id == trace_id]
        if outcome_id:
            results = [f for f in results if f.outcome_id == outcome_id]
        return results[-limit:]

    def list_memory_candidates(
        self,
        user_id: str | None = None,
        trace_id: str | None = None,
        outcome_id: str | None = None,
        limit: int = 50,
    ) -> list[MemoryCandidate]:
        results = list(self._candidates)
        if user_id:
            results = [c for c in results if c.user_id == user_id]
        if trace_id:
            results = [c for c in results if c.trace_id == trace_id]
        if outcome_id:
            results = [c for c in results if c.outcome_id == outcome_id]
        return results[-limit:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcomes": [o.to_dict() for o in self._outcomes],
            "feedback": [f.to_dict() for f in self._feedback],
            "memory_candidates": [c.to_dict() for c in self._candidates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackStore:
        store = cls()
        for o in data.get("outcomes", []):
            store.append_outcome(OutcomeRecord.from_dict(o))
        for f in data.get("feedback", []):
            store.append_feedback(FeedbackRecord.from_dict(f))
        for c in data.get("memory_candidates", []):
            store.append_memory_candidate(MemoryCandidate.from_dict(c))
        return store


_feedback_store: FeedbackStore | None = None
_store_lock = threading.Lock()


def get_feedback_store() -> FeedbackStore:
    global _feedback_store
    if _feedback_store is None:
        with _store_lock:
            if _feedback_store is None:
                _feedback_store = FeedbackStore()
    return _feedback_store


def reset_feedback_store(store: FeedbackStore | None = None) -> None:
    global _feedback_store
    with _store_lock:
        _feedback_store = store


def export_storage_descriptors(
    store: FeedbackStore | None = None,
    limit: int = 200,
) -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    if store is None:
        store = get_feedback_store()

    descriptors: list[StorageRecordDescriptor] = []

    for o in store.list_outcomes(limit=limit):
        descriptors.append(
            StorageRecordDescriptor(
                record_id=o.outcome_id,
                record_type=StorageRecordType.OUTCOME,
                scope=StorageScope.USER if o.user_id else StorageScope.SYSTEM,
                mutability=StorageMutability.APPEND_ONLY,
                source=StorageSource.EXECUTION,
                backend_type=StorageBackendType.MEMORY,
                owner_id=o.user_id,
                created_at=getattr(o, "timestamp", ""),
            )
        )

    for f in store.list_feedback(limit=limit):
        descriptors.append(
            StorageRecordDescriptor(
                record_id=f.feedback_id,
                record_type=StorageRecordType.FEEDBACK,
                scope=StorageScope.USER if f.user_id else StorageScope.SYSTEM,
                mutability=StorageMutability.APPEND_ONLY,
                source=StorageSource.FEEDBACK_LOOP,
                backend_type=StorageBackendType.MEMORY,
                owner_id=f.user_id,
                created_at=getattr(f, "timestamp", ""),
            )
        )

    for c in store.list_memory_candidates(limit=limit):
        descriptors.append(
            StorageRecordDescriptor(
                record_id=c.candidate_id,
                record_type=StorageRecordType.MEMORY_CANDIDATE,
                scope=StorageScope.USER if c.user_id else StorageScope.SYSTEM,
                mutability=StorageMutability.PROMOTABLE,
                source=StorageSource.FEEDBACK_LOOP,
                backend_type=StorageBackendType.MEMORY,
                owner_id=c.user_id,
                created_at=getattr(c, "created_at", ""),
            )
        )

    return descriptors
