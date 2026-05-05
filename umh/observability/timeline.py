"""Phase 79 execution timeline — chronological event views from traces/outcomes/feedback.

No execution. No mutation. No adapter calls. Deterministic ordering.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class TimelineEventType(str, Enum):
    INPUT_RECEIVED = "input_received"
    GOVERNANCE_EVALUATED = "governance_evaluated"
    EXECUTION_STARTED = "execution_started"
    ADAPTER_SELECTED = "adapter_selected"
    ADAPTER_COMPLETED = "adapter_completed"
    EXECUTION_COMPLETED = "execution_completed"
    OUTCOME_CLASSIFIED = "outcome_classified"
    FEEDBACK_RECORDED = "feedback_recorded"
    MEMORY_CANDIDATE_CREATED = "memory_candidate_created"
    SESSION_STARTED = "session_started"
    SESSION_UPDATED = "session_updated"
    UNKNOWN = "unknown"


def normalize_timeline_event_type(value: str) -> TimelineEventType:
    value = value.strip().lower()
    for member in TimelineEventType:
        if member.value == value:
            return member
    return TimelineEventType.UNKNOWN


@dataclass
class TimelineEvent:
    event_id: str
    trace_id: str = ""
    session_id: str = ""
    user_id: str = ""
    event_type: TimelineEventType = TimelineEventType.UNKNOWN
    timestamp: str = ""
    title: str = ""
    summary: str = ""
    severity: str = "info"
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "title": self.title,
            "summary": self.summary,
            "severity": self.severity,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionTimeline:
    user_id: str = ""
    session_id: str = ""
    events: list[TimelineEvent] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    generated_at: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "events": [e.to_dict() for e in self.events],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "generated_at": self.generated_at,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def _event_id() -> str:
    return f"tl_{uuid.uuid4().hex[:10]}"


def trace_to_timeline_events(trace: Any) -> list[TimelineEvent]:
    """Extract timeline events from a TraceRecord or dict."""
    events: list[TimelineEvent] = []

    if isinstance(trace, dict):
        trace_id = trace.get("trace_id", "")
        user_id = trace.get("user_id", "")
        status = trace.get("status", "")
        created_at = trace.get("created_at", "")
        completed_at = trace.get("completed_at", "")
        input_summary = trace.get("input_summary", "")
        error = trace.get("error")
        trace_events = trace.get("events", [])
    else:
        trace_id = getattr(trace, "trace_id", "")
        user_id = getattr(trace, "user_id", "")
        status = getattr(trace, "status", "")
        created_at = getattr(trace, "created_at", "")
        completed_at = getattr(trace, "completed_at", None) or ""
        input_summary = getattr(trace, "input_summary", "")
        error = getattr(trace, "error", None)
        trace_events = getattr(trace, "events", [])

    if created_at:
        events.append(
            TimelineEvent(
                event_id=_event_id(),
                trace_id=trace_id,
                user_id=user_id,
                event_type=TimelineEventType.INPUT_RECEIVED,
                timestamp=created_at,
                title="Input received",
                summary=input_summary[:120] if input_summary else "",
                source="trace",
            )
        )

    for ev in trace_events:
        if isinstance(ev, dict):
            ev_type = ev.get("event_type", "")
            ev_ts = ev.get("timestamp", "")
            ev_payload = ev.get("payload", {})
        else:
            ev_type = getattr(ev, "event_type", "")
            ev_ts = getattr(ev, "timestamp", "")
            ev_payload = getattr(ev, "payload", {})

        if ev_type == "governance":
            allowed = ev_payload.get("allowed", True) if isinstance(ev_payload, dict) else True
            severity = "info" if allowed else "warning"
            events.append(
                TimelineEvent(
                    event_id=_event_id(),
                    trace_id=trace_id,
                    user_id=user_id,
                    event_type=TimelineEventType.GOVERNANCE_EVALUATED,
                    timestamp=ev_ts or created_at,
                    title="Governance evaluated",
                    summary="allowed" if allowed else "denied",
                    severity=severity,
                    source="trace",
                )
            )
        elif ev_type in ("execution", "adapter", "backend"):
            events.append(
                TimelineEvent(
                    event_id=_event_id(),
                    trace_id=trace_id,
                    user_id=user_id,
                    event_type=TimelineEventType.EXECUTION_STARTED,
                    timestamp=ev_ts or created_at,
                    title="Execution event",
                    summary=ev_type,
                    source="trace",
                )
            )

    if completed_at:
        severity = "error" if status == "failed" else "info"
        events.append(
            TimelineEvent(
                event_id=_event_id(),
                trace_id=trace_id,
                user_id=user_id,
                event_type=TimelineEventType.EXECUTION_COMPLETED,
                timestamp=completed_at,
                title="Execution completed",
                summary=status,
                severity=severity,
                source="trace",
            )
        )

    return events


def outcome_to_timeline_event(outcome: Any) -> TimelineEvent:
    """Create a timeline event from an OutcomeRecord or dict."""
    if isinstance(outcome, dict):
        trace_id = outcome.get("trace_id", "")
        user_id = outcome.get("user_id", "")
        status = outcome.get("status", "")
        completed_at = outcome.get("completed_at", "")
        summary = outcome.get("summary", "")
    else:
        trace_id = getattr(outcome, "trace_id", "")
        user_id = getattr(outcome, "user_id", "")
        status_val = getattr(outcome, "status", "")
        status = status_val.value if hasattr(status_val, "value") else str(status_val)
        completed_at = getattr(outcome, "completed_at", "")
        summary = getattr(outcome, "summary", "")

    return TimelineEvent(
        event_id=_event_id(),
        trace_id=trace_id,
        user_id=user_id,
        event_type=TimelineEventType.OUTCOME_CLASSIFIED,
        timestamp=completed_at,
        title="Outcome classified",
        summary=f"{status}: {summary[:80]}" if summary else status,
        severity="error" if status in ("failure", "timeout") else "info",
        source="outcome",
    )


def feedback_to_timeline_event(feedback: Any) -> TimelineEvent:
    """Create a timeline event from a FeedbackRecord or dict."""
    if isinstance(feedback, dict):
        trace_id = feedback.get("trace_id", "")
        user_id = feedback.get("user_id", "")
        signal = feedback.get("signal_type", "")
        ts = feedback.get("timestamp", "")
        source = feedback.get("source", "")
    else:
        trace_id = getattr(feedback, "trace_id", "")
        user_id = getattr(feedback, "user_id", "")
        sig = getattr(feedback, "signal_type", "")
        signal = sig.value if hasattr(sig, "value") else str(sig)
        ts = getattr(feedback, "timestamp", "")
        src = getattr(feedback, "source", "")
        source = src.value if hasattr(src, "value") else str(src)

    return TimelineEvent(
        event_id=_event_id(),
        trace_id=trace_id,
        user_id=user_id,
        event_type=TimelineEventType.FEEDBACK_RECORDED,
        timestamp=ts,
        title="Feedback recorded",
        summary=signal,
        source=source or "feedback",
    )


def build_timeline(
    traces: list[Any] | None = None,
    outcomes: list[Any] | None = None,
    feedback: list[Any] | None = None,
    sessions: list[Any] | None = None,
    limit: int = 50,
) -> ExecutionTimeline:
    """Build a chronological timeline from all available data sources."""
    all_events: list[TimelineEvent] = []
    warnings: list[str] = []

    for t in traces or []:
        try:
            all_events.extend(trace_to_timeline_events(t))
        except Exception:
            warnings.append("failed to extract events from a trace")

    for o in outcomes or []:
        try:
            all_events.append(outcome_to_timeline_event(o))
        except Exception:
            warnings.append("failed to extract event from an outcome")

    for f in feedback or []:
        try:
            all_events.append(feedback_to_timeline_event(f))
        except Exception:
            warnings.append("failed to extract event from feedback")

    timestamped = [e for e in all_events if e.timestamp]
    untimed = [e for e in all_events if not e.timestamp]
    if untimed:
        warnings.append(f"{len(untimed)} events missing timestamps")

    timestamped.sort(key=lambda e: e.timestamp)
    sorted_events = timestamped + untimed
    sorted_events = sorted_events[:limit]

    start_time = sorted_events[0].timestamp if sorted_events and sorted_events[0].timestamp else ""
    end_time = ""
    for e in reversed(sorted_events):
        if e.timestamp:
            end_time = e.timestamp
            break

    return ExecutionTimeline(
        events=sorted_events,
        start_time=start_time,
        end_time=end_time,
        generated_at=_iso_now(),
        warnings=warnings,
    )
