"""Phase 78 trace analyzer — deterministic evidence extraction from traces.

No LLM. No invented fields. Robust to sparse trace formats.
Supports TraceStore TraceRecord, adapter result traces, and
workstation context metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceAnalysis:
    trace_id: str
    user_id: str = ""
    session_id: str = ""
    has_result: bool = False
    has_error: bool = False
    was_denied: bool = False
    was_validated: bool = True
    adapter_status: str = ""
    governance_status: str = ""
    execution_status: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: int | None = None
    output_summary: str = ""
    error_summary: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "has_result": self.has_result,
            "has_error": self.has_error,
            "was_denied": self.was_denied,
            "was_validated": self.was_validated,
            "adapter_status": self.adapter_status,
            "governance_status": self.governance_status,
            "execution_status": self.execution_status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "output_summary": self.output_summary,
            "error_summary": self.error_summary,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }


def summarize_output(output: Any, max_len: int = 200) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output[:max_len]
    if isinstance(output, dict):
        keys = list(output.keys())[:5]
        return f"dict({', '.join(keys)})"[:max_len]
    return str(output)[:max_len]


def summarize_error(error: Any, max_len: int = 200) -> str:
    if error is None:
        return ""
    if isinstance(error, str):
        return error[:max_len]
    return str(error)[:max_len]


def extract_trace_user_id(trace: Any) -> str:
    if hasattr(trace, "user_id"):
        return trace.user_id or ""
    if isinstance(trace, dict):
        return trace.get("user_id", "")
    return ""


def extract_session_id(trace: Any) -> str:
    if isinstance(trace, dict):
        meta = trace.get("metadata", {})
        ws = meta.get("workstation", {})
        if ws.get("active_session_id"):
            return ws["active_session_id"]
        return trace.get("session_id", "")
    if hasattr(trace, "result") and isinstance(trace.result, dict):
        meta = trace.result.get("metadata", {})
        ws = meta.get("workstation", {})
        if ws.get("active_session_id"):
            return ws["active_session_id"]
    return ""


def extract_governance_status(trace: Any) -> str:
    if isinstance(trace, dict):
        gov = trace.get("governance", {})
        if isinstance(gov, dict):
            if gov.get("allowed") is False:
                return "denied"
            if gov.get("outcome"):
                return gov["outcome"]
            if gov.get("allowed") is True:
                return "allowed"
        events = trace.get("events", [])
        for ev in events:
            if isinstance(ev, dict) and ev.get("event_type") == "governance":
                payload = ev.get("payload", {})
                if payload.get("allowed") is False:
                    return "denied"
                return payload.get("outcome", "allowed")
        return ""

    if hasattr(trace, "events"):
        for ev in trace.events:
            et = ev.event_type if hasattr(ev, "event_type") else ev.get("event_type", "")
            if et == "governance":
                payload = ev.payload if hasattr(ev, "payload") else ev.get("payload", {})
                if isinstance(payload, dict):
                    if payload.get("allowed") is False:
                        return "denied"
                    return payload.get("outcome", "allowed")
    return ""


def extract_adapter_status(trace: Any) -> str:
    if isinstance(trace, dict):
        result = trace.get("result", {})
        if isinstance(result, dict):
            adapter_result = result.get("adapter_result", {})
            if isinstance(adapter_result, dict) and adapter_result.get("status"):
                return adapter_result["status"]
            if result.get("adapter_status"):
                return result["adapter_status"]
        events = trace.get("events", [])
        for ev in events:
            if isinstance(ev, dict) and ev.get("event_type") in ("adapter_result", "execution"):
                payload = ev.get("payload", {})
                if isinstance(payload, dict) and payload.get("status"):
                    return payload["status"]
        return ""

    if hasattr(trace, "result") and isinstance(trace.result, dict):
        adapter_result = trace.result.get("adapter_result", {})
        if isinstance(adapter_result, dict) and adapter_result.get("status"):
            return adapter_result["status"]
        if trace.result.get("adapter_status"):
            return trace.result["adapter_status"]

    if hasattr(trace, "events"):
        for ev in trace.events:
            et = ev.event_type if hasattr(ev, "event_type") else ""
            if et in ("adapter_result", "execution"):
                payload = ev.payload if hasattr(ev, "payload") else {}
                if isinstance(payload, dict) and payload.get("status"):
                    return payload["status"]
    return ""


def extract_execution_status(trace: Any) -> str:
    if isinstance(trace, dict):
        if trace.get("status"):
            return trace["status"]
        result = trace.get("result", {})
        if isinstance(result, dict) and result.get("status"):
            return result["status"]
        return ""

    if hasattr(trace, "status"):
        return trace.status or ""
    return ""


def analyze_trace(trace: Any) -> TraceAnalysis:
    """Analyze a TraceRecord or trace dict into structured evidence."""
    trace_id = ""
    if hasattr(trace, "trace_id"):
        trace_id = trace.trace_id
    elif isinstance(trace, dict):
        trace_id = trace.get("trace_id", "")

    user_id = extract_trace_user_id(trace)
    session_id = extract_session_id(trace)
    governance_status = extract_governance_status(trace)
    adapter_status = extract_adapter_status(trace)
    execution_status = extract_execution_status(trace)

    has_result = False
    has_error = False
    error_text = ""
    result_data: Any = None

    if hasattr(trace, "result"):
        result_data = trace.result
        has_result = bool(result_data)
    elif isinstance(trace, dict):
        result_data = trace.get("result")
        has_result = bool(result_data)

    if hasattr(trace, "error"):
        error_text = trace.error or ""
    elif isinstance(trace, dict):
        error_text = trace.get("error", "") or ""
    has_error = bool(error_text)

    was_denied = governance_status == "denied"
    was_validated = adapter_status != "validation_failed"

    started_at = ""
    completed_at = ""
    if hasattr(trace, "created_at"):
        started_at = trace.created_at or ""
    elif isinstance(trace, dict):
        started_at = trace.get("created_at", "")
    if hasattr(trace, "completed_at"):
        completed_at = trace.completed_at or ""
    elif isinstance(trace, dict):
        completed_at = trace.get("completed_at", "")

    evidence: list[str] = []
    confidence = 0.5

    if execution_status == "completed":
        evidence.append("trace_status=completed")
        confidence = max(confidence, 0.8)
    elif execution_status == "failed":
        evidence.append("trace_status=failed")
        confidence = max(confidence, 0.8)

    if was_denied:
        evidence.append("governance=denied")
        confidence = max(confidence, 0.9)

    if adapter_status:
        evidence.append(f"adapter_status={adapter_status}")
        confidence = max(confidence, 0.7)

    if has_error:
        evidence.append(f"error_present")
        confidence = max(confidence, 0.7)

    if has_result and not has_error and not was_denied:
        evidence.append("result_present_no_error")
        confidence = max(confidence, 0.7)

    if not evidence:
        confidence = 0.2

    return TraceAnalysis(
        trace_id=trace_id,
        user_id=user_id,
        session_id=session_id,
        has_result=has_result,
        has_error=has_error,
        was_denied=was_denied,
        was_validated=was_validated,
        adapter_status=adapter_status,
        governance_status=governance_status,
        execution_status=execution_status,
        started_at=started_at,
        completed_at=completed_at,
        output_summary=summarize_output(result_data),
        error_summary=summarize_error(error_text),
        evidence=evidence,
        confidence=confidence,
    )


def analyze_trace_dict(trace_dict: dict[str, Any]) -> TraceAnalysis:
    return analyze_trace(trace_dict)
