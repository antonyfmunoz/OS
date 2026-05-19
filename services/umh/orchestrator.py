"""UMH Orchestrator — read-only query facade over UMH subsystems.

Write path: use ExecutionPipeline.submit_signal() (services/umh/control_plane/pipeline.py).
This class provides query and resume functions suitable for API endpoints,
reading from the same stores that the pipeline writes to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.umh.memory.candidate_generator import MemoryCandidateGenerator
from services.umh.observability.outcome_classifier import OutcomeClassifier
from services.umh.observability.proof_store import ProofStore
from services.umh.observability.trace_store import TraceStore
from services.umh.workstation.state import (
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationStateManager,
)


class Orchestrator:
    """Read-only query facade over UMH subsystems."""

    def __init__(self, data_root: str | Path = "data/umh"):
        root = Path(data_root)
        self.trace_store = TraceStore(root / "traces")
        self.proof_store = ProofStore(root / "proofs")
        self.candidate_gen = MemoryCandidateGenerator(root / "memory_candidates")
        self.classifier = OutcomeClassifier()
        self.state_manager = WorkstationStateManager(root / "workstation_state")
        self._session = WorkstationSessionState()
        self._profile = WorkstationProfile.detect()

    def get_traces(
        self,
        *,
        status: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> dict[str, Any]:
        """Query traces. Suitable for GET /api/umh/traces."""
        traces = self.trace_store.query_traces(
            status=status, outcome=outcome, limit=limit, since=since
        )
        return {
            "traces": traces,
            "total": self.trace_store.count(),
            "query": {
                "status": status,
                "outcome": outcome,
                "limit": limit,
                "since": since,
            },
        }

    def get_trace_detail(self, trace_id: str) -> dict[str, Any] | None:
        """Get full trace with proofs and candidates."""
        trace = self.trace_store.get_trace(trace_id)
        if not trace:
            return None
        proofs = self.proof_store.proofs_for_trace(trace_id)
        candidates = self.candidate_gen.get_candidates(trace_id=trace_id)
        return {
            "trace": trace.to_dict(),
            "proofs": [p.to_dict() for p in proofs],
            "memory_candidates": [c.to_dict() for c in candidates],
        }

    def get_resume(self) -> dict[str, Any]:
        """Build resume state. Suitable for GET /api/umh/resume."""
        recent = self.trace_store.recent_traces(10)
        snapshot = self.state_manager.build_snapshot(
            profile=self._profile,
            session=self._session,
            recent_traces=recent,
        )
        return snapshot.to_dict()

    def get_stats(self) -> dict[str, Any]:
        """Summary statistics across all subsystems."""
        return {
            "traces": self.trace_store.count(),
            "candidates": self.candidate_gen.count(),
            "session_errors": self._session.error_count,
            "session_traces": self._session.trace_count,
            "session_candidates": self._session.candidate_count,
        }
