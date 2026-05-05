"""Phase 79 trace query — safe, read-only trace querying for operator views.

No trace mutation. No execution. No adapter calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.interface.views import TraceView

_MAX_QUERY_LIMIT = 100


@dataclass
class TraceQuery:
    user_id: str = ""
    session_id: str = ""
    status: str = ""
    capability: str = ""
    environment: str = ""
    adapter: str = ""
    limit: int = 25
    offset: int = 0
    since: str = ""
    until: str = ""
    include_raw: bool = False

    def effective_limit(self) -> int:
        return max(1, min(self.limit, _MAX_QUERY_LIMIT))


@dataclass
class TraceQueryResult:
    query: dict[str, Any] = field(default_factory=dict)
    total_returned: int = 0
    traces: list[TraceView] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total_returned": self.total_returned,
            "traces": [t.to_dict() for t in self.traces],
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def trace_to_view(
    trace: Any,
    outcome_lookup: dict[str, Any] | None = None,
) -> TraceView:
    """Convert a TraceRecord or dict to a TraceView."""
    if isinstance(trace, dict):
        trace_id = trace.get("trace_id", "")
        user_id = trace.get("user_id", "")
        status = trace.get("status", "")
        created_at = trace.get("created_at", "")
        completed_at = trace.get("completed_at", "")
        input_summary = trace.get("input_summary", "")
        error = trace.get("error")
        events = trace.get("events", [])
        result = trace.get("result", {})
    else:
        trace_id = getattr(trace, "trace_id", "")
        user_id = getattr(trace, "user_id", "")
        status = getattr(trace, "status", "")
        created_at = getattr(trace, "created_at", "")
        completed_at = getattr(trace, "completed_at", None) or ""
        input_summary = getattr(trace, "input_summary", "")
        error = getattr(trace, "error", None)
        events = getattr(trace, "events", [])
        result = getattr(trace, "result", {}) or {}

    capability = ""
    environment = ""
    adapter = ""
    for ev in events:
        payload = ev.get("payload", {}) if isinstance(ev, dict) else getattr(ev, "payload", {})
        if not capability:
            capability = payload.get("capability", "") if isinstance(payload, dict) else ""
        if not environment:
            environment = payload.get("environment", "") if isinstance(payload, dict) else ""
        if not adapter:
            adapter = payload.get("adapter_name", "") if isinstance(payload, dict) else ""

    if not adapter and isinstance(result, dict):
        adapter = result.get("adapter_name", "") or result.get("capability", "")

    duration_ms = None
    if created_at and completed_at:
        try:
            from datetime import datetime, timezone

            t0 = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            duration_ms = int((t1 - t0).total_seconds() * 1000)
        except Exception:
            pass

    outcome_status = ""
    if outcome_lookup and trace_id in outcome_lookup:
        oc = outcome_lookup[trace_id]
        if isinstance(oc, dict):
            outcome_status = oc.get("status", "")
        elif hasattr(oc, "status"):
            s = oc.status
            outcome_status = s.value if hasattr(s, "value") else str(s)

    attention = status == "failed" or bool(error)

    return TraceView(
        trace_id=trace_id,
        user_id=user_id,
        status=status,
        capability=capability,
        environment=environment,
        adapter=adapter,
        started_at=created_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        outcome_status=outcome_status,
        summary=input_summary[:200] if input_summary else "",
        attention_required=attention,
    )


def query_traces(
    trace_store: Any,
    query: TraceQuery,
) -> TraceQueryResult:
    """Query traces from a trace store with filters."""
    warnings: list[str] = []

    if trace_store is None:
        return TraceQueryResult(
            query={"error": "no_trace_store"},
            warnings=["trace store unavailable"],
        )

    try:
        raw_traces = trace_store.list_traces(limit=query.effective_limit())
    except Exception:
        return TraceQueryResult(
            query={"error": "list_failed"},
            warnings=["failed to list traces"],
        )

    views: list[TraceView] = []
    for t in raw_traces:
        view = trace_to_view(t)
        if query.user_id and view.user_id and view.user_id != query.user_id:
            continue
        if query.status and view.status and view.status != query.status:
            continue
        if query.capability and view.capability and view.capability != query.capability:
            continue
        views.append(view)

    return TraceQueryResult(
        query={
            "user_id": query.user_id,
            "status": query.status,
            "limit": query.effective_limit(),
        },
        total_returned=len(views),
        traces=views,
        warnings=warnings,
    )


def get_trace_view(
    trace_store: Any,
    trace_id: str,
    include_raw: bool = False,
) -> TraceView | None:
    """Get a single trace view by ID."""
    if trace_store is None:
        return None
    try:
        trace = trace_store.get_trace(trace_id)
    except Exception:
        return None
    if trace is None:
        return None
    view = trace_to_view(trace)
    if include_raw:
        raw = trace.to_dict() if hasattr(trace, "to_dict") else {}
        view.metadata["raw"] = raw
    return view


def list_recent_trace_views(
    trace_store: Any,
    user_id: str | None = None,
    limit: int = 25,
) -> list[TraceView]:
    """List recent traces as views."""
    q = TraceQuery(user_id=user_id or "", limit=limit)
    result = query_traces(trace_store, q)
    return result.traces
