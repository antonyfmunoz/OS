"""Phase 77 resume summary — trace/session-derived continuity context.

Summaries are deterministic and derived from traces/sessions.
No LLM dependency.  No invented outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class PendingApprovalView:
    """Read-only view of a pending approval. Does NOT approve/deny."""

    approval_id: str
    trace_id: str = ""
    directive_summary: str = ""
    authority_required: str = ""
    requested_at: str = ""
    status: str = "pending"
    risk_level: str = ""
    environment: str = ""
    capability: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "trace_id": self.trace_id,
            "directive_summary": self.directive_summary,
            "authority_required": self.authority_required,
            "requested_at": self.requested_at,
            "status": self.status,
            "risk_level": self.risk_level,
            "environment": self.environment,
            "capability": self.capability,
        }


@dataclass
class TraceResumeSummary:
    """Trace/session-derived resume context."""

    user_id: str
    workstation_id: str = ""
    session_id: str = ""
    recent_trace_ids: list[str] = field(default_factory=list)
    recent_successes: int = 0
    recent_failures: int = 0
    recent_denials: int = 0
    pending_approvals: list[PendingApprovalView] = field(default_factory=list)
    active_tasks: list[str] = field(default_factory=list)
    last_mode: str = ""
    last_outcome_status: str = ""
    last_feedback_signal: str = ""
    memory_candidates_pending: int = 0
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    recommended_resume_points: list[str] = field(default_factory=list)
    generated_at: str = ""
    source: str = "trace_store"
    execution_health: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "workstation_id": self.workstation_id,
            "session_id": self.session_id,
            "recent_trace_ids": self.recent_trace_ids,
            "recent_successes": self.recent_successes,
            "recent_failures": self.recent_failures,
            "recent_denials": self.recent_denials,
            "pending_approvals": [a.to_dict() for a in self.pending_approvals],
            "active_tasks": self.active_tasks,
            "last_mode": self.last_mode,
            "last_outcome_status": self.last_outcome_status,
            "last_feedback_signal": self.last_feedback_signal,
            "memory_candidates_pending": self.memory_candidates_pending,
            "recent_outcomes": self.recent_outcomes,
            "recommended_resume_points": self.recommended_resume_points,
            "generated_at": self.generated_at,
            "source": self.source,
            "execution_health": self.execution_health,
        }


def summarize_recent_traces(
    trace_store: Any,
    user_id: str,
    limit: int = 10,
) -> tuple[list[str], int, int]:
    """Extract recent trace IDs, success count, failure count."""
    try:
        traces = trace_store.list_traces(limit=limit)
    except Exception:
        return [], 0, 0

    trace_ids = []
    successes = 0
    failures = 0

    for trace in traces:
        if hasattr(trace, "user_id") and trace.user_id and trace.user_id != user_id:
            continue
        trace_ids.append(trace.trace_id)
        if trace.status == "completed":
            successes += 1
        elif trace.status == "failed":
            failures += 1

    return trace_ids, successes, failures


def list_pending_approvals(
    user_id: str,
    approval_store: Any | None = None,
) -> list[PendingApprovalView]:
    """Build read-only views of pending approvals."""
    if approval_store is None:
        try:
            from umh.execution.approval import get_approval_store

            approval_store = get_approval_store()
        except Exception:
            return []

    try:
        pending = approval_store.list_pending()
    except Exception:
        return []

    views = []
    for req in pending:
        views.append(
            PendingApprovalView(
                approval_id=req.id,
                directive_summary=f"{req.operation}: {req.inputs_summary[:100]}",
                authority_required="",
                requested_at=req.created_at,
                status=req.status.value if hasattr(req.status, "value") else str(req.status),
                risk_level=req.risk_level,
                capability=req.capability_type,
            )
        )
    return views


def build_resume_summary(
    profile: Any,
    session: Any | None = None,
    trace_store: Any | None = None,
    approval_store: Any | None = None,
    feedback_store: Any | None = None,
) -> TraceResumeSummary:
    """Build a complete resume summary from profile + session + traces + feedback."""
    user_id = profile.user_id if hasattr(profile, "user_id") else ""
    workstation_id = profile.workstation_id if hasattr(profile, "workstation_id") else ""

    trace_ids: list[str] = []
    successes = 0
    failures = 0

    if trace_store is not None:
        trace_ids, successes, failures = summarize_recent_traces(trace_store, user_id, limit=10)

    approvals = list_pending_approvals(user_id, approval_store)

    session_id = ""
    last_mode = ""
    active_tasks: list[str] = []

    if session is not None:
        session_id = getattr(session, "session_id", "")
        last_mode = getattr(session, "active_mode", "")
        active_tasks = getattr(session, "active_task_ids", [])
    elif hasattr(profile, "active_session_id"):
        session_id = profile.active_session_id
    if not last_mode and hasattr(profile, "active_mode"):
        last_mode = profile.active_mode

    recent_denials = 0
    last_outcome_status = ""
    last_feedback_signal = ""
    memory_candidates_pending = 0
    recent_outcomes: list[dict[str, Any]] = []

    if feedback_store is not None:
        try:
            outcomes = feedback_store.list_outcomes(user_id=user_id, limit=10)
            for oc in outcomes:
                recent_outcomes.append(
                    {
                        "outcome_id": oc.outcome_id,
                        "status": oc.status.value
                        if hasattr(oc.status, "value")
                        else str(oc.status),
                        "trace_id": oc.trace_id,
                    }
                )
                if oc.status.value == "denied":
                    recent_denials += 1
            if outcomes:
                last_oc = outcomes[-1]
                last_outcome_status = (
                    last_oc.status.value
                    if hasattr(last_oc.status, "value")
                    else str(last_oc.status)
                )

            fb_list = feedback_store.list_feedback(user_id=user_id, limit=1)
            if fb_list:
                last_fb = fb_list[-1]
                last_feedback_signal = (
                    last_fb.signal_type.value
                    if hasattr(last_fb.signal_type, "value")
                    else str(last_fb.signal_type)
                )

            candidates = feedback_store.list_memory_candidates(user_id=user_id)
            memory_candidates_pending = sum(
                1
                for c in candidates
                if hasattr(c, "promotion_status")
                and (
                    c.promotion_status.value
                    if hasattr(c.promotion_status, "value")
                    else str(c.promotion_status)
                )
                == "candidate"
            )
        except Exception:
            pass

    resume_points: list[str] = []
    if failures > 0:
        resume_points.append(f"{failures} recent failures to review")
    if recent_denials > 0:
        resume_points.append(f"{recent_denials} recent denials")
    if approvals:
        resume_points.append(f"{len(approvals)} pending approvals")
    if active_tasks:
        resume_points.append(f"{len(active_tasks)} active tasks")
    if memory_candidates_pending > 0:
        resume_points.append(f"{memory_candidates_pending} memory candidates pending")

    return TraceResumeSummary(
        user_id=user_id,
        workstation_id=workstation_id,
        session_id=session_id,
        recent_trace_ids=trace_ids,
        recent_successes=successes,
        recent_failures=failures,
        recent_denials=recent_denials,
        pending_approvals=approvals,
        active_tasks=active_tasks,
        last_mode=last_mode,
        last_outcome_status=last_outcome_status,
        last_feedback_signal=last_feedback_signal,
        memory_candidates_pending=memory_candidates_pending,
        recent_outcomes=recent_outcomes,
        recommended_resume_points=resume_points,
        generated_at=_iso_now(),
    )


def format_resume_summary(summary: TraceResumeSummary) -> str:
    """Format a resume summary for display."""
    lines = [
        f"Session: {summary.session_id or 'none'}",
        f"Mode: {summary.last_mode or 'unknown'}",
        f"Recent traces: {len(summary.recent_trace_ids)} ({summary.recent_successes} ok, {summary.recent_failures} failed)",
        f"Pending approvals: {len(summary.pending_approvals)}",
        f"Active tasks: {len(summary.active_tasks)}",
    ]
    if summary.recommended_resume_points:
        lines.append("Resume points:")
        for point in summary.recommended_resume_points:
            lines.append(f"  - {point}")
    return "\n".join(lines)
