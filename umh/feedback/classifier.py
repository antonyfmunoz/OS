"""Phase 78 outcome classifier — deterministic TraceAnalysis → OutcomeRecord.

Classification rules are rule-based with no LLM dependency.
DENIED is safety behavior, not execution failure.
"""

from __future__ import annotations

from typing import Any

from umh.feedback.outcome import (
    OutcomeRecord,
    OutcomeSource,
    OutcomeStatus,
    clamp_score,
    create_outcome_id,
)
from umh.feedback.trace_analyzer import TraceAnalysis, analyze_trace, analyze_trace_dict


class OutcomeClassifier:
    """Deterministic outcome classification from trace analysis."""

    def classify(self, analysis: TraceAnalysis) -> OutcomeRecord:
        status, score, confidence, summary = self._classify_from_analysis(analysis)

        return OutcomeRecord(
            outcome_id=create_outcome_id(analysis.trace_id),
            trace_id=analysis.trace_id,
            user_id=analysis.user_id,
            session_id=analysis.session_id,
            status=status,
            success_score=clamp_score(score),
            confidence=clamp_score(confidence),
            summary=summary,
            evidence=list(analysis.evidence),
            observed_outputs=(
                {"output_summary": analysis.output_summary} if analysis.output_summary else {}
            ),
            errors=[analysis.error_summary] if analysis.error_summary else [],
            started_at=analysis.started_at,
            completed_at=analysis.completed_at,
            source=OutcomeSource.TRACE,
        )

    def classify_trace(self, trace: Any) -> OutcomeRecord:
        analysis = analyze_trace(trace)
        return self.classify(analysis)

    def classify_trace_dict(self, trace_dict: dict[str, Any]) -> OutcomeRecord:
        analysis = analyze_trace_dict(trace_dict)
        return self.classify(analysis)

    def _classify_from_analysis(self, a: TraceAnalysis) -> tuple[OutcomeStatus, float, float, str]:
        if a.was_denied:
            return (
                OutcomeStatus.DENIED,
                0.0,
                max(a.confidence, 0.9),
                "Execution denied by governance",
            )

        if a.adapter_status == "validation_failed" or not a.was_validated:
            return (
                OutcomeStatus.VALIDATION_FAILED,
                0.0,
                max(a.confidence, 0.8),
                "Input validation failed",
            )

        if _is_timeout(a):
            return (
                OutcomeStatus.TIMEOUT,
                0.0,
                max(a.confidence, 0.7),
                "Execution timed out",
            )

        if a.adapter_status == "denied":
            return (
                OutcomeStatus.DENIED,
                0.0,
                max(a.confidence, 0.8),
                "Adapter denied execution",
            )

        if a.adapter_status == "success":
            return (
                OutcomeStatus.SUCCESS,
                1.0,
                max(a.confidence, 0.8),
                "Adapter reported success",
            )

        if a.adapter_status == "simulated":
            return (
                OutcomeStatus.PARTIAL_SUCCESS,
                0.6,
                max(a.confidence, 0.6),
                "Simulated execution completed",
            )

        if a.adapter_status == "failure":
            return (
                OutcomeStatus.FAILURE,
                0.0,
                max(a.confidence, 0.8),
                "Adapter reported failure",
            )

        if a.execution_status == "completed" and a.has_result and not a.has_error:
            return (
                OutcomeStatus.SUCCESS,
                1.0,
                max(a.confidence, 0.7),
                "Execution completed with result",
            )

        if a.execution_status == "completed" and a.has_result and a.has_error:
            return (
                OutcomeStatus.PARTIAL_SUCCESS,
                0.5,
                max(a.confidence, 0.6),
                "Execution completed with errors",
            )

        if a.execution_status == "failed" or (a.has_error and not a.has_result):
            return (
                OutcomeStatus.FAILURE,
                0.0,
                max(a.confidence, 0.7),
                "Execution failed",
            )

        if a.has_result and not a.has_error:
            return (
                OutcomeStatus.SUCCESS,
                0.8,
                max(a.confidence, 0.5),
                "Result present, no error (inferred success)",
            )

        if not a.has_result and not a.has_error and not a.execution_status:
            return (
                OutcomeStatus.INSUFFICIENT_DATA,
                0.0,
                0.2,
                "No result, no error, no status — insufficient data",
            )

        return (
            OutcomeStatus.UNKNOWN,
            0.2,
            0.3,
            "Conflicting or ambiguous signals",
        )


def _is_timeout(a: TraceAnalysis) -> bool:
    if a.adapter_status == "timeout":
        return True
    if a.execution_status == "timeout":
        return True
    error_lower = a.error_summary.lower()
    if "timeout" in error_lower or "timed out" in error_lower:
        return True
    return False
