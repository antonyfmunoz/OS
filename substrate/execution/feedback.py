"""FeedbackCapture — captures execution quality signals.

Deterministic quality mapping from execution outcomes. Feeds into
the learning loop for adapter reliability tracking.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from substrate.types import (
    ExecutionOutcome,
    ExecutionResult,
    FeedbackRecord,
    FeedbackType,
    TraceRecord,
)

_QUALITY_MAP: dict[ExecutionOutcome, float] = {
    ExecutionOutcome.SUCCESS: 0.8,
    ExecutionOutcome.PARTIAL_SUCCESS: 0.6,
    ExecutionOutcome.BLOCKED: 0.5,
    ExecutionOutcome.FAILURE: 0.2,
    ExecutionOutcome.TIMEOUT: 0.1,
    ExecutionOutcome.REJECTED: 0.1,
}


@runtime_checkable
class FeedbackCapture(Protocol):
    async def capture(self, trace: TraceRecord, result: ExecutionResult) -> FeedbackRecord: ...

    async def persist(self, feedback: FeedbackRecord) -> None: ...


class ConcreteFeedbackCapture:
    """Deterministic feedback capture with Neon persistence."""

    async def capture(self, trace: TraceRecord, result: ExecutionResult) -> FeedbackRecord:
        quality = _QUALITY_MAP.get(result.outcome, 0.5)
        learning = ""
        if result.error:
            learning = f"Error: {result.error[:200]}"
        elif result.output:
            learning = f"Output length: {len(result.output)}"

        return FeedbackRecord(
            trace_id=trace.id,
            signal_id=result.signal_id,
            feedback_type=FeedbackType.IMPLICIT,
            outcome_quality=quality,
            learning_signal=learning[:500],
        )

    async def persist(self, feedback: FeedbackRecord) -> None:
        """Write feedback to Neon feedback table."""
        try:
            import os
            import sys

            sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))
            from dotenv import load_dotenv

            load_dotenv("/opt/OS/runtime/.env", override=True)
            from substrate.state.storage.db import get_conn

            with get_conn() as cur:
                cur.execute(
                    """INSERT INTO feedback (id, trace_id, signal_id, feedback_type, outcome_quality,
                       learning_signal, captured_at, metadata, org_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                       current_setting('app.current_org_id', true)::uuid)""",
                    (
                        str(feedback.id),
                        str(feedback.trace_id),
                        str(feedback.signal_id),
                        feedback.feedback_type.value,
                        feedback.outcome_quality,
                        feedback.learning_signal,
                        feedback.captured_at,
                        "{}",
                    ),
                )
        except Exception:
            pass
