"""Phase 79 execution summary — summarize recent harness activity.

Counts derived from traces/outcomes only. No causal attribution.
No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class ExecutionSummary:
    user_id: str = ""
    total_traces: int = 0
    success_count: int = 0
    partial_success_count: int = 0
    failure_count: int = 0
    denied_count: int = 0
    validation_failed_count: int = 0
    timeout_count: int = 0
    unknown_count: int = 0
    insufficient_data_count: int = 0
    recent_capabilities: list[str] = field(default_factory=list)
    recent_environments: list[str] = field(default_factory=list)
    recent_adapters: list[str] = field(default_factory=list)
    attention_required_count: int = 0
    generated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_traces": self.total_traces,
            "success_count": self.success_count,
            "partial_success_count": self.partial_success_count,
            "failure_count": self.failure_count,
            "denied_count": self.denied_count,
            "validation_failed_count": self.validation_failed_count,
            "timeout_count": self.timeout_count,
            "unknown_count": self.unknown_count,
            "insufficient_data_count": self.insufficient_data_count,
            "recent_capabilities": self.recent_capabilities,
            "recent_environments": self.recent_environments,
            "recent_adapters": self.recent_adapters,
            "attention_required_count": self.attention_required_count,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
        }


_STATUS_COUNTERS = {
    "success": "success_count",
    "partial_success": "partial_success_count",
    "failure": "failure_count",
    "denied": "denied_count",
    "validation_failed": "validation_failed_count",
    "timeout": "timeout_count",
    "unknown": "unknown_count",
    "insufficient_data": "insufficient_data_count",
}


def _extract_outcome_status(outcome: Any) -> str:
    if isinstance(outcome, dict):
        s = outcome.get("status", "")
        return s.value if hasattr(s, "value") else str(s)
    s = getattr(outcome, "status", "")
    return s.value if hasattr(s, "value") else str(s)


def summarize_executions(
    traces: list[Any] | None = None,
    outcomes: list[Any] | None = None,
    limit: int = 100,
) -> ExecutionSummary:
    """Summarize recent execution health from traces and outcomes."""
    summary = ExecutionSummary(generated_at=_iso_now())

    capabilities: set[str] = set()
    environments: set[str] = set()
    adapters: set[str] = set()

    trace_list = (traces or [])[:limit]
    summary.total_traces = len(trace_list)

    for t in trace_list:
        if isinstance(t, dict):
            events = t.get("events", [])
            result = t.get("result", {}) or {}
            status = t.get("status", "")
            error = t.get("error")
        else:
            events = getattr(t, "events", [])
            result = getattr(t, "result", {}) or {}
            status = getattr(t, "status", "")
            error = getattr(t, "error", None)

        for ev in events:
            payload = ev.get("payload", {}) if isinstance(ev, dict) else getattr(ev, "payload", {})
            if isinstance(payload, dict):
                cap = payload.get("capability", "")
                env = payload.get("environment", "")
                adp = payload.get("adapter_name", "")
                if cap:
                    capabilities.add(cap)
                if env:
                    environments.add(env)
                if adp:
                    adapters.add(adp)

        if isinstance(result, dict):
            cap = result.get("capability", "")
            adp = result.get("adapter_name", "")
            if cap:
                capabilities.add(cap)
            if adp:
                adapters.add(adp)

        if status == "failed" or error:
            summary.attention_required_count += 1

    if outcomes:
        for oc in outcomes[:limit]:
            status_str = _extract_outcome_status(oc)
            counter_attr = _STATUS_COUNTERS.get(status_str)
            if counter_attr:
                setattr(summary, counter_attr, getattr(summary, counter_attr) + 1)

    summary.recent_capabilities = sorted(capabilities)
    summary.recent_environments = sorted(environments)
    summary.recent_adapters = sorted(adapters)

    return summary


def summarize_by_capability(
    outcomes: list[Any] | None = None,
) -> dict[str, dict[str, int]]:
    """Group outcome counts by capability (if available in metadata)."""
    by_cap: dict[str, dict[str, int]] = {}
    for oc in outcomes or []:
        if isinstance(oc, dict):
            meta = oc.get("metadata", {})
            status = oc.get("status", "unknown")
        else:
            meta = getattr(oc, "metadata", {})
            s = getattr(oc, "status", "unknown")
            status = s.value if hasattr(s, "value") else str(s)
        cap = meta.get("capability", "unknown") if isinstance(meta, dict) else "unknown"
        by_cap.setdefault(cap, {})
        by_cap[cap][status] = by_cap[cap].get(status, 0) + 1
    return by_cap


def summarize_by_environment(
    outcomes: list[Any] | None = None,
) -> dict[str, dict[str, int]]:
    """Group outcome counts by environment (if available in metadata)."""
    by_env: dict[str, dict[str, int]] = {}
    for oc in outcomes or []:
        if isinstance(oc, dict):
            meta = oc.get("metadata", {})
            status = oc.get("status", "unknown")
        else:
            meta = getattr(oc, "metadata", {})
            s = getattr(oc, "status", "unknown")
            status = s.value if hasattr(s, "value") else str(s)
        env = meta.get("environment", "unknown") if isinstance(meta, dict) else "unknown"
        by_env.setdefault(env, {})
        by_env[env][status] = by_env[env].get(status, 0) + 1
    return by_env


def summarize_by_adapter(
    outcomes: list[Any] | None = None,
) -> dict[str, dict[str, int]]:
    """Group outcome counts by adapter (if available in metadata)."""
    by_adp: dict[str, dict[str, int]] = {}
    for oc in outcomes or []:
        if isinstance(oc, dict):
            meta = oc.get("metadata", {})
            status = oc.get("status", "unknown")
        else:
            meta = getattr(oc, "metadata", {})
            s = getattr(oc, "status", "unknown")
            status = s.value if hasattr(s, "value") else str(s)
        adp = meta.get("adapter", "unknown") if isinstance(meta, dict) else "unknown"
        by_adp.setdefault(adp, {})
        by_adp[adp][status] = by_adp[adp].get(status, 0) + 1
    return by_adp


def compute_attention_required(
    traces: list[Any] | None = None,
    outcomes: list[Any] | None = None,
) -> int:
    """Count items requiring human attention."""
    count = 0
    for t in traces or []:
        if isinstance(t, dict):
            if t.get("status") == "failed" or t.get("error"):
                count += 1
        else:
            if getattr(t, "status", "") == "failed" or getattr(t, "error", None):
                count += 1
    for oc in outcomes or []:
        status = _extract_outcome_status(oc)
        if status in ("failure", "timeout", "validation_failed"):
            count += 1
    return count
