"""Phase 78 feedback loop orchestrator — trace → outcome → feedback → memory candidate.

Single pipeline function that processes a trace through the full
Phase 78 feedback loop. No execution. No adapter calls. No world-model
updates. No policy updates. No automatic memory promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.feedback.classifier import OutcomeClassifier
from umh.feedback.memory_bridge import MemoryCandidate, create_memory_candidate_from_outcome
from umh.feedback.outcome import OutcomeRecord
from umh.feedback.records import FeedbackRecord, feedback_from_outcome
from umh.feedback.store import FeedbackStore
from umh.feedback.trace_analyzer import TraceAnalysis, analyze_trace


@dataclass
class FeedbackLoopResult:
    trace_id: str
    outcome: OutcomeRecord | None = None
    feedback: FeedbackRecord | None = None
    memory_candidate: MemoryCandidate | None = None
    status: str = "pending"
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "memory_candidate": (
                self.memory_candidate.to_dict() if self.memory_candidate else None
            ),
            "status": self.status,
            "errors": self.errors,
            "metadata": self.metadata,
        }


def process_trace_feedback(
    trace: Any,
    store: FeedbackStore | None = None,
) -> FeedbackLoopResult:
    """Process a trace through the full Phase 78 feedback loop.

    Pipeline:
      1. analyze_trace → TraceAnalysis
      2. classify → OutcomeRecord
      3. feedback_from_outcome → FeedbackRecord
      4. create_memory_candidate_from_outcome → MemoryCandidate (conservative)
      5. append to store if provided
    """
    trace_id = ""
    if hasattr(trace, "trace_id"):
        trace_id = trace.trace_id
    elif isinstance(trace, dict):
        trace_id = trace.get("trace_id", "")

    result = FeedbackLoopResult(trace_id=trace_id)

    try:
        analysis = analyze_trace(trace)
    except Exception as e:
        result.errors.append(f"trace_analysis_failed: {e}")
        result.status = "error"
        return result

    classifier = OutcomeClassifier()
    try:
        outcome = classifier.classify(analysis)
        result.outcome = outcome
    except Exception as e:
        result.errors.append(f"classification_failed: {e}")
        result.status = "error"
        return result

    try:
        feedback = feedback_from_outcome(outcome)
        result.feedback = feedback
    except Exception as e:
        result.errors.append(f"feedback_creation_failed: {e}")

    try:
        candidate = create_memory_candidate_from_outcome(outcome, feedback)
        result.memory_candidate = candidate
    except Exception as e:
        result.errors.append(f"memory_candidate_failed: {e}")

    if store is not None:
        try:
            store.append_outcome(outcome)
            if result.feedback:
                store.append_feedback(result.feedback)
            if result.memory_candidate:
                store.append_memory_candidate(result.memory_candidate)
        except Exception as e:
            result.errors.append(f"store_append_failed: {e}")

    result.status = "completed" if not result.errors else "partial"
    result.metadata = {
        "outcome_id": outcome.outcome_id if result.outcome else None,
        "feedback_id": result.feedback.feedback_id if result.feedback else None,
        "candidate_id": (result.memory_candidate.candidate_id if result.memory_candidate else None),
    }
    return result
