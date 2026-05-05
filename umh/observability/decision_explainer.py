"""Phase 79 decision explainer — explain what happened using trace evidence only.

No hallucinated reasoning. No causal inference. Evidence-derived.
Deterministic. Confidence bounded [0,1]. No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class DecisionExplanation:
    trace_id: str
    user_id: str = ""
    request_summary: str = ""
    interpreted_action: str = ""
    governance_summary: str = ""
    capability: str = ""
    environment: str = ""
    adapter: str = ""
    execution_summary: str = ""
    outcome_summary: str = ""
    feedback_summary: str = ""
    evidence: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    confidence: float = 0.5
    generated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "request_summary": self.request_summary,
            "interpreted_action": self.interpreted_action,
            "governance_summary": self.governance_summary,
            "capability": self.capability,
            "environment": self.environment,
            "adapter": self.adapter,
            "execution_summary": self.execution_summary,
            "outcome_summary": self.outcome_summary,
            "feedback_summary": self.feedback_summary,
            "evidence": self.evidence,
            "unknowns": self.unknowns,
            "confidence": self.confidence,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
        }


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _extract_dict(trace: Any) -> dict[str, Any]:
    if isinstance(trace, dict):
        return trace
    if hasattr(trace, "to_dict"):
        return trace.to_dict()
    return {}


def explain_governance(trace: Any) -> tuple[str, list[str], list[str]]:
    """Explain governance decision from trace. Returns (summary, evidence, unknowns)."""
    d = _extract_dict(trace)
    evidence: list[str] = []
    unknowns: list[str] = []

    events = d.get("events", [])
    for ev in events:
        payload = ev.get("payload", {}) if isinstance(ev, dict) else getattr(ev, "payload", {})
        ev_type = (
            ev.get("event_type", "") if isinstance(ev, dict) else getattr(ev, "event_type", "")
        )
        if ev_type == "governance" and isinstance(payload, dict):
            allowed = payload.get("allowed", None)
            reason = payload.get("reason", "")
            if allowed is False:
                evidence.append("governance denied execution")
                if reason:
                    evidence.append(f"governance reason: {reason[:120]}")
                return "denied", evidence, unknowns
            elif allowed is True:
                evidence.append("governance allowed execution")
                if reason:
                    evidence.append(f"governance reason: {reason[:120]}")
                return "allowed", evidence, unknowns

    unknowns.append("governance decision not found in trace events")
    return "unknown", evidence, unknowns


def explain_adapter_selection(trace: Any) -> tuple[str, list[str], list[str]]:
    """Explain which adapter was selected. Returns (adapter, evidence, unknowns)."""
    d = _extract_dict(trace)
    evidence: list[str] = []
    unknowns: list[str] = []

    result = d.get("result", {}) or {}
    adapter = ""

    if isinstance(result, dict):
        adapter = result.get("adapter_name", "") or result.get("capability", "")
        if adapter:
            evidence.append(f"adapter selected: {adapter}")

    events = d.get("events", [])
    for ev in events:
        payload = ev.get("payload", {}) if isinstance(ev, dict) else getattr(ev, "payload", {})
        if isinstance(payload, dict):
            adp = payload.get("adapter_name", "")
            if adp and not adapter:
                adapter = adp
                evidence.append(f"adapter from event: {adapter}")

    if not adapter:
        unknowns.append("adapter selection not recorded in trace")

    return adapter, evidence, unknowns


def explain_execution_result(trace: Any) -> tuple[str, list[str], list[str]]:
    """Explain execution result. Returns (summary, evidence, unknowns)."""
    d = _extract_dict(trace)
    evidence: list[str] = []
    unknowns: list[str] = []

    status = d.get("status", "")
    error = d.get("error", "")
    result = d.get("result", {}) or {}

    if status:
        evidence.append(f"trace status: {status}")

    if error:
        evidence.append(f"error present: {error[:120]}")
        return f"failed: {error[:80]}", evidence, unknowns

    if status == "completed" and result:
        return "completed with result", evidence, unknowns

    if status == "completed":
        return "completed", evidence, unknowns

    if status == "failed":
        return "failed (no error detail)", evidence, unknowns

    unknowns.append("execution result unclear from trace data")
    return "unknown", evidence, unknowns


def explain_unknowns(
    trace: Any,
    outcome: Any | None = None,
) -> list[str]:
    """List what is unknown or missing from the trace."""
    d = _extract_dict(trace)
    unknowns: list[str] = []

    if not d.get("events"):
        unknowns.append("no events recorded")
    if not d.get("result") and not d.get("error"):
        unknowns.append("no result or error recorded")
    if not d.get("created_at"):
        unknowns.append("no start timestamp")
    if not d.get("completed_at"):
        unknowns.append("no completion timestamp")

    if outcome is None:
        unknowns.append("no outcome record available")

    return unknowns


def explain_trace(
    trace: Any,
    outcome: Any | None = None,
    feedback_records: list[Any] | None = None,
) -> DecisionExplanation:
    """Build a complete explanation of what happened in a trace."""
    d = _extract_dict(trace)
    trace_id = d.get("trace_id", "")
    user_id = d.get("user_id", "")
    input_summary = d.get("input_summary", "")

    all_evidence: list[str] = []
    all_unknowns: list[str] = []

    gov_summary, gov_ev, gov_unk = explain_governance(trace)
    all_evidence.extend(gov_ev)
    all_unknowns.extend(gov_unk)

    adapter, adp_ev, adp_unk = explain_adapter_selection(trace)
    all_evidence.extend(adp_ev)
    all_unknowns.extend(adp_unk)

    exec_summary, exec_ev, exec_unk = explain_execution_result(trace)
    all_evidence.extend(exec_ev)
    all_unknowns.extend(exec_unk)

    all_unknowns.extend(explain_unknowns(trace, outcome))

    outcome_summary = ""
    if outcome is not None:
        if isinstance(outcome, dict):
            s = outcome.get("status", "")
            outcome_summary = f"{s}: {outcome.get('summary', '')[:80]}"
        else:
            s = getattr(outcome, "status", "")
            sv = s.value if hasattr(s, "value") else str(s)
            outcome_summary = f"{sv}: {getattr(outcome, 'summary', '')[:80]}"
        all_evidence.append(f"outcome: {outcome_summary[:100]}")

    feedback_summary = ""
    if feedback_records:
        fb_count = len(feedback_records)
        feedback_summary = f"{fb_count} feedback record(s)"
        all_evidence.append(feedback_summary)

    # capability/environment from events
    capability = ""
    environment = ""
    events = d.get("events", [])
    for ev in events:
        payload = ev.get("payload", {}) if isinstance(ev, dict) else getattr(ev, "payload", {})
        if isinstance(payload, dict):
            if not capability:
                capability = payload.get("capability", "")
            if not environment:
                environment = payload.get("environment", "")

    confidence = 0.5
    if all_evidence and not all_unknowns:
        confidence = 0.9
    elif all_evidence:
        confidence = max(0.3, 0.9 - 0.1 * len(all_unknowns))
    elif all_unknowns:
        confidence = 0.2

    return DecisionExplanation(
        trace_id=trace_id,
        user_id=user_id,
        request_summary=input_summary[:200] if input_summary else "",
        interpreted_action=d.get("input_summary", "")[:100],
        governance_summary=gov_summary,
        capability=capability,
        environment=environment,
        adapter=adapter,
        execution_summary=exec_summary,
        outcome_summary=outcome_summary,
        feedback_summary=feedback_summary,
        evidence=all_evidence,
        unknowns=all_unknowns,
        confidence=_clamp(confidence),
        generated_at=_iso_now(),
    )
