"""
Operator delivery — Discord response formatter for operator-facing messages.

Converts OperatorTrace / execution outcomes / approval requests into:
  1. Short Discord summary text (~6 lines max)
  2. Full artifact/report markdown content
  3. Optional attachment filename

This is a pure formatting layer — no transport side effects, no scheduler logic,
no LLM calls. It sits between the trace/execution data and the send_reply()
delivery API.

Design rules (substrate conventions):
- Additive only. No hot-path imports.
- Deterministic. Same input → same output.
- No side effects. Formatting only.
- Graceful degradation on missing fields.
- Transport-agnostic (produces text, not Discord objects).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any, Optional

from umh.substrate.operator_trace import OperatorTrace
from umh.substrate.runtime_mode import RuntimeMode

_LOG_PREFIX = "[substrate.operator_delivery]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _safe(value: Any, fallback: str = "—") -> str:
    """Return str(value) if truthy, else fallback."""
    if value is None or value == "":
        return fallback
    return str(value)


def _duration_str(started: str | None, completed: str | None) -> str:
    """Compute human-readable duration from ISO timestamps."""
    if not started or not completed:
        return "—"
    try:
        t0 = datetime.fromisoformat(started)
        t1 = datetime.fromisoformat(completed)
        delta = t1 - t0
        secs = delta.total_seconds()
        if secs < 60:
            return f"{secs:.1f}s"
        if secs < 3600:
            return f"{secs / 60:.1f}m"
        return f"{secs / 3600:.1f}h"
    except Exception:
        return "—"


# ─── Success summary ────────────────────────────────────────────────────────


def format_completion_summary(
    trace: OperatorTrace,
    *,
    title: str = "",
    result_text: str = "",
    started_at: str | None = None,
    completed_at: str | None = None,
    mode: RuntimeMode = RuntimeMode.ACTIVE,
) -> str:
    """Format a concise success summary for Discord (~6 lines).

    Shape:
        ✅ Task Complete — <short title>
        • Result: <1 sentence>
        • Steps: N/M
        • Mode: active
        📎 Full report attached
    """
    display_title = title or trace.intent_type or "Task"
    result_line = result_text or trace.terminal_reason or "Completed successfully"
    # Truncate result to one sentence
    if len(result_line) > 120:
        result_line = result_line[:117] + "..."

    duration = _duration_str(started_at, completed_at)

    lines = [f"✅ **Task Complete** — {display_title}"]
    lines.append(f"• Result: {result_line}")

    if trace.steps_total > 0:
        lines.append(f"• Steps: {trace.steps_executed}/{trace.steps_total}")

    if duration != "—":
        lines.append(f"• Time: {duration}")

    lines.append(f"• Mode: {mode.value}")
    lines.append("📎 Full report attached")

    return "\n".join(lines)


# ─── Failure summary ────────────────────────────────────────────────────────


def format_failure_summary(
    trace: OperatorTrace,
    *,
    title: str = "",
    cause: str = "",
    next_step: str = "",
    mode: RuntimeMode = RuntimeMode.ACTIVE,
) -> str:
    """Format a concise failure summary for Discord (~6 lines).

    Shape:
        ❌ Task Failed — <short title>
        • Cause: <1 sentence>
        • Next step: <1 sentence>
        • Mode: active
        📎 Full report attached
    """
    display_title = title or trace.intent_type or "Task"
    cause_line = cause or trace.terminal_reason or "Unknown failure"
    if len(cause_line) > 120:
        cause_line = cause_line[:117] + "..."

    next_step_line = next_step or "Review attached report"
    if len(next_step_line) > 120:
        next_step_line = next_step_line[:117] + "..."

    lines = [f"❌ **Task Failed** — {display_title}"]
    lines.append(f"• Cause: {cause_line}")
    lines.append(f"• Next step: {next_step_line}")

    if trace.steps_total > 0:
        lines.append(f"• Steps: {trace.steps_executed}/{trace.steps_total}")

    lines.append(f"• Mode: {mode.value}")
    lines.append("📎 Full report attached")

    return "\n".join(lines)


# ─── Approval summary ──────────────────────────────────────────────────────


def format_approval_summary(
    *,
    title: str = "",
    reason: str = "",
    approval_id: str = "",
    mode: RuntimeMode = RuntimeMode.ACTIVE,
) -> str:
    """Format a concise approval request for Discord (~5 lines).

    Shape:
        ⚠️ Approval Required — <short title>
        • Why: <1 sentence>
        • Action: approve / reject
        📎 Context attached
    """
    display_title = title or "Action"
    reason_line = reason or "Requires operator approval"
    if len(reason_line) > 120:
        reason_line = reason_line[:117] + "..."

    lines = [f"⚠️ **Approval Required** — {display_title}"]
    lines.append(f"• Why: {reason_line}")
    lines.append("• Action: approve / reject")

    if approval_id:
        lines.append(f"• Ref: `{approval_id[:12]}`")

    lines.append("📎 Context attached")

    return "\n".join(lines)


# ─── Full report builder ───────────────────────────────────────────────────


def build_full_report_markdown(
    trace: OperatorTrace,
    *,
    title: str = "",
    extra_sections: dict[str, str] | None = None,
) -> str:
    """Build a full markdown report from an OperatorTrace.

    Includes all trace data in readable sections. This is what gets
    attached as a .md file.
    """
    display_title = title or trace.intent_type or "Orchestration Report"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections: list[str] = []

    # Header
    sections.append(f"# {display_title}")
    sections.append(f"*Generated: {now}*")
    sections.append("")

    # Outcome
    status = trace.terminal_status or trace.intent_status or "unknown"
    status_emoji = {"completed": "✅", "failed": "❌"}.get(status, "❓")
    sections.append(f"## Outcome: {status_emoji} {status}")
    if trace.terminal_reason:
        sections.append(f"\n{trace.terminal_reason}")
    sections.append("")

    # Ingress
    if trace.ingress_source or trace.ingress_transport or trace.ingress_text:
        sections.append("## Ingress")
        if trace.ingress_source:
            sections.append(f"- **Source:** {trace.ingress_source}")
        if trace.ingress_transport:
            sections.append(f"- **Transport:** {trace.ingress_transport}")
        if trace.ingress_text:
            truncated = trace.ingress_text[:500]
            if len(trace.ingress_text) > 500:
                truncated += "..."
            sections.append(f"- **Text:** {truncated}")
        sections.append("")

    # Intent
    if trace.intent_id:
        sections.append("## Intent")
        sections.append(f"- **ID:** `{trace.intent_id}`")
        sections.append(f"- **Type:** {trace.intent_type or '—'}")
        sections.append(f"- **Status:** {trace.intent_status or '—'}")
        sections.append("")

    # Plan
    if trace.plan_id or trace.variant_id:
        sections.append("## Plan Selection")
        if trace.plan_id:
            sections.append(f"- **Plan ID:** `{trace.plan_id}`")
        if trace.variant_id:
            variant_label = trace.variant_id
            if trace.is_mutated_variant:
                variant_label += " (mutated)"
            sections.append(f"- **Variant:** `{variant_label}`")
        if trace.plan_score is not None:
            sections.append(f"- **Score:** {trace.plan_score:.3f}")
            sections.append(
                f"- **History:** {trace.plan_success_count} successes, "
                f"{trace.plan_failure_count} failures"
            )
        if trace.competition_result:
            sections.append(f"- **Competition:** {trace.competition_result}")
        sections.append("")

    # Execution
    if trace.steps_total > 0:
        sections.append("## Execution")
        sections.append(f"- **Steps:** {trace.steps_executed}/{trace.steps_total}")
        sections.append("")

    # Scheduler
    sections.append("## Scheduler Stats")
    sections.append(f"- **Events processed:** {trace.events_processed}")
    sections.append(f"- **Mutations applied:** {trace.mutations_applied}")
    if trace.event_types_processed:
        event_list = ", ".join(trace.event_types_processed[:20])
        if len(trace.event_types_processed) > 20:
            event_list += f" ... (+{len(trace.event_types_processed) - 20} more)"
        sections.append(f"- **Event types:** {event_list}")
    sections.append("")

    # Extra sections from caller
    if extra_sections:
        for heading, content in extra_sections.items():
            sections.append(f"## {heading}")
            sections.append(content)
            sections.append("")

    return "\n".join(sections)


# ─── Report filename ───────────────────────────────────────────────────────


def build_report_filename(
    trace: OperatorTrace,
    *,
    prefix: str = "report",
) -> str:
    """Build a deterministic filename for the report attachment.

    Pattern: {prefix}_{intent_type}_{date}.md
    """
    intent_slug = (trace.intent_type or "unknown").replace(" ", "_").lower()[:30]
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{intent_slug}_{date_str}.md"


# ─── Convenience: build complete delivery payload ──────────────────────────


def build_operator_response(
    trace: OperatorTrace,
    *,
    title: str = "",
    result_text: str = "",
    cause: str = "",
    next_step: str = "",
    started_at: str | None = None,
    completed_at: str | None = None,
    mode: RuntimeMode = RuntimeMode.ACTIVE,
    extra_report_sections: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a complete operator delivery payload from a trace.

    Returns:
        {
            "summary": str,          # short Discord text
            "full_report": str,      # markdown for attachment
            "filename": str,         # attachment filename
            "is_failure": bool,
            "is_approval": bool,
        }
    """
    is_failure = trace.terminal_status == "failed"

    if is_failure:
        summary = format_failure_summary(
            trace,
            title=title,
            cause=cause,
            next_step=next_step,
            mode=mode,
        )
    else:
        summary = format_completion_summary(
            trace,
            title=title,
            result_text=result_text,
            started_at=started_at,
            completed_at=completed_at,
            mode=mode,
        )

    full_report = build_full_report_markdown(
        trace,
        title=title,
        extra_sections=extra_report_sections,
    )
    filename = build_report_filename(trace)

    return {
        "summary": summary,
        "full_report": full_report,
        "filename": filename,
        "is_failure": is_failure,
        "is_approval": False,
    }


__all__ = [
    "format_completion_summary",
    "format_failure_summary",
    "format_approval_summary",
    "build_full_report_markdown",
    "build_report_filename",
    "build_operator_response",
]
