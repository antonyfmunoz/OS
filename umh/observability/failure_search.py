"""Phase 79 failure search — find failures, denials, timeouts safely.

No causal inference. No root-cause claims. Evidence-derived only.
No execution. No mutation. No adapter calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now

_MAX_SEARCH_LIMIT = 100


class FailureCategory(str, Enum):
    FAILURE = "failure"
    DENIED = "denied"
    VALIDATION_FAILED = "validation_failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    INSUFFICIENT_DATA = "insufficient_data"
    WARNING = "warning"


@dataclass
class FailureRecord:
    record_id: str
    trace_id: str = ""
    outcome_id: str = ""
    user_id: str = ""
    category: FailureCategory = FailureCategory.UNKNOWN
    summary: str = ""
    error_preview: str = ""
    capability: str = ""
    environment: str = ""
    adapter: str = ""
    timestamp: str = ""
    attention_required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "trace_id": self.trace_id,
            "outcome_id": self.outcome_id,
            "user_id": self.user_id,
            "category": self.category.value,
            "summary": self.summary,
            "error_preview": self.error_preview,
            "capability": self.capability,
            "environment": self.environment,
            "adapter": self.adapter,
            "timestamp": self.timestamp,
            "attention_required": self.attention_required,
            "metadata": self.metadata,
        }


@dataclass
class FailureSearchQuery:
    user_id: str = ""
    category: str = ""
    capability: str = ""
    environment: str = ""
    limit: int = 25

    def effective_limit(self) -> int:
        return max(1, min(self.limit, _MAX_SEARCH_LIMIT))


@dataclass
class FailureSearchResult:
    query: dict[str, Any] = field(default_factory=dict)
    failures: list[FailureRecord] = field(default_factory=list)
    total_returned: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "failures": [f.to_dict() for f in self.failures],
            "total_returned": self.total_returned,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def _failure_id() -> str:
    return f"fail_{uuid.uuid4().hex[:10]}"


_STATUS_TO_CATEGORY: dict[str, FailureCategory] = {
    "failure": FailureCategory.FAILURE,
    "failed": FailureCategory.FAILURE,
    "denied": FailureCategory.DENIED,
    "validation_failed": FailureCategory.VALIDATION_FAILED,
    "timeout": FailureCategory.TIMEOUT,
    "unknown": FailureCategory.UNKNOWN,
    "insufficient_data": FailureCategory.INSUFFICIENT_DATA,
}


def trace_to_failure_record(trace: Any) -> FailureRecord | None:
    """Convert a failed/denied trace to a FailureRecord. Returns None if not a failure."""
    if isinstance(trace, dict):
        status = trace.get("status", "")
        trace_id = trace.get("trace_id", "")
        user_id = trace.get("user_id", "")
        error = trace.get("error", "") or ""
        input_summary = trace.get("input_summary", "")
        created_at = trace.get("created_at", "")
    else:
        status = getattr(trace, "status", "")
        trace_id = getattr(trace, "trace_id", "")
        user_id = getattr(trace, "user_id", "")
        error = getattr(trace, "error", "") or ""
        input_summary = getattr(trace, "input_summary", "")
        created_at = getattr(trace, "created_at", "")

    category = _STATUS_TO_CATEGORY.get(status)
    if category is None:
        if error:
            category = FailureCategory.WARNING
        else:
            return None

    return FailureRecord(
        record_id=_failure_id(),
        trace_id=trace_id,
        user_id=user_id,
        category=category,
        summary=input_summary[:200] if input_summary else status,
        error_preview=error[:200] if error else "",
        timestamp=created_at,
        attention_required=category
        in (
            FailureCategory.FAILURE,
            FailureCategory.TIMEOUT,
            FailureCategory.VALIDATION_FAILED,
        ),
    )


def outcome_to_failure_record(outcome: Any) -> FailureRecord | None:
    """Convert a non-success outcome to a FailureRecord. Returns None if success."""
    if isinstance(outcome, dict):
        status_raw = outcome.get("status", "")
        status_str = status_raw.value if hasattr(status_raw, "value") else str(status_raw)
        outcome_id = outcome.get("outcome_id", "")
        trace_id = outcome.get("trace_id", "")
        user_id = outcome.get("user_id", "")
        summary = outcome.get("summary", "")
        errors = outcome.get("errors", [])
        completed_at = outcome.get("completed_at", "")
    else:
        s = getattr(outcome, "status", "")
        status_str = s.value if hasattr(s, "value") else str(s)
        outcome_id = getattr(outcome, "outcome_id", "")
        trace_id = getattr(outcome, "trace_id", "")
        user_id = getattr(outcome, "user_id", "")
        summary = getattr(outcome, "summary", "")
        errors = getattr(outcome, "errors", [])
        completed_at = getattr(outcome, "completed_at", "")

    if status_str in ("success", "partial_success", "cancelled"):
        return None

    category = _STATUS_TO_CATEGORY.get(status_str, FailureCategory.UNKNOWN)
    error_preview = errors[0][:200] if errors else ""

    return FailureRecord(
        record_id=_failure_id(),
        outcome_id=outcome_id,
        trace_id=trace_id,
        user_id=user_id,
        category=category,
        summary=summary[:200] if summary else status_str,
        error_preview=error_preview,
        timestamp=completed_at,
        attention_required=category
        in (
            FailureCategory.FAILURE,
            FailureCategory.TIMEOUT,
            FailureCategory.VALIDATION_FAILED,
        ),
    )


def search_failures(
    traces: list[Any] | None = None,
    outcomes: list[Any] | None = None,
    query: FailureSearchQuery | None = None,
) -> FailureSearchResult:
    """Search for failures across traces and outcomes."""
    q = query or FailureSearchQuery()
    warnings: list[str] = []
    records: list[FailureRecord] = []

    for t in traces or []:
        try:
            rec = trace_to_failure_record(t)
            if rec is not None:
                records.append(rec)
        except Exception:
            warnings.append("failed to process a trace for failure search")

    for oc in outcomes or []:
        try:
            rec = outcome_to_failure_record(oc)
            if rec is not None:
                records.append(rec)
        except Exception:
            warnings.append("failed to process an outcome for failure search")

    if q.category:
        records = [r for r in records if r.category.value == q.category]
    if q.user_id:
        records = [r for r in records if r.user_id == q.user_id]
    if q.capability:
        records = [r for r in records if r.capability == q.capability]

    records = records[: q.effective_limit()]

    return FailureSearchResult(
        query={
            "category": q.category,
            "user_id": q.user_id,
            "limit": q.effective_limit(),
        },
        failures=records,
        total_returned=len(records),
        warnings=warnings,
    )
