"""UMH Orchestrator — unified facade for trace, proof, memory, and workstation.

Single entry point for creating traces, storing proofs, classifying outcomes,
generating memory candidates, and maintaining workstation state.

Also provides query and resume functions suitable for API endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.umh.memory.candidate_generator import MemoryCandidateGenerator
from services.umh.observability.outcome_classifier import OutcomeClassifier
from services.umh.observability.proof_store import ProofStore
from services.umh.observability.trace_store import TraceStatus, TraceStore
from services.umh.workstation.state import (
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationSnapshot,
    WorkstationStateManager,
)


class Orchestrator:
    """Facade that coordinates all UMH subsystems."""

    def __init__(self, data_root: str | Path = "data/umh"):
        root = Path(data_root)
        self.trace_store = TraceStore(root / "traces")
        self.proof_store = ProofStore(root / "proofs")
        self.candidate_gen = MemoryCandidateGenerator(root / "memory_candidates")
        self.classifier = OutcomeClassifier()
        self.state_manager = WorkstationStateManager(root / "workstation_state")
        self._session = WorkstationSessionState()
        self._profile = WorkstationProfile.detect()

    def execute_trace(
        self,
        input_signal: str,
        *,
        interpretation_ref: str = "",
        governance_decision: str = "",
        work_packet: dict[str, Any] | None = None,
        adapter_used: str = "",
        environment: str = "",
        execution_result: dict[str, Any] | None = None,
        proof_content: dict[str, Any] | None = None,
        proof_type: str = "execution_output",
        auto_candidate: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Full trace lifecycle: create → execute → classify → proof → candidate → state.

        Returns a summary dict with all generated IDs and classification.
        """
        now = datetime.now(timezone.utc).isoformat()

        trace = self.trace_store.create_trace(
            input_signal=input_signal,
            interpretation_ref=interpretation_ref,
            governance_decision=governance_decision,
            work_packet=work_packet,
            adapter_used=adapter_used,
            environment=environment or self._profile.active_environment,
            metadata=metadata,
        )

        self.trace_store.update_trace(
            trace.trace_id,
            status=TraceStatus.RUNNING,
            started_at=now,
        )

        exec_result = execution_result or {}
        classification = self.classifier.classify(exec_result)

        final_status = TraceStatus.COMPLETED
        if classification.category in ("failure", "error"):
            final_status = TraceStatus.FAILED
        elif classification.category == "timeout":
            final_status = TraceStatus.TIMEOUT
        elif classification.category == "skipped":
            final_status = TraceStatus.SKIPPED

        proof_id = ""
        if proof_content:
            proof = self.proof_store.store_proof(
                trace_id=trace.trace_id,
                proof_type=proof_type,
                content=proof_content,
                summary=classification.detail[:200],
            )
            proof_id = proof.proof_id

        candidate_id = ""
        if auto_candidate:
            candidate = self.candidate_gen.generate_from_trace(
                trace_id=trace.trace_id,
                input_signal=input_signal,
                outcome=classification.category,
                outcome_detail=classification.detail,
                execution_result=exec_result,
            )
            if candidate:
                candidate_id = candidate.candidate_id
                self._session.candidate_count += 1

        self.trace_store.update_trace(
            trace.trace_id,
            status=final_status,
            execution_result=exec_result,
            proof_artifact_id=proof_id,
            outcome=classification.category,
            outcome_detail=classification.detail,
            memory_candidate_ref=candidate_id,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        self._session.record_activity(trace.trace_id, classification.category)
        if classification.category in ("failure", "error"):
            self._session.record_error()

        return {
            "trace_id": trace.trace_id,
            "status": final_status,
            "outcome": classification.category,
            "outcome_detail": classification.detail,
            "outcome_confidence": classification.confidence,
            "proof_artifact_id": proof_id,
            "memory_candidate_id": candidate_id,
        }

    # --- Query functions (endpoint-ready) ---

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
