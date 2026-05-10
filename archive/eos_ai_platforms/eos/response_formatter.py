"""
Response formatter — owns ALL text shaping for founder-facing EOS output.

Takes structured context dicts ({meta, state, insights, suggestions}) and
EAResponse data, produces founder-facing text.  No other module in the
platform layer produces user-facing text.

Design rules:
- Concise, operator-facing language.
- No meta commentary ("I delegated this to..." unless helpful).
- EA voice always — even when reporting specialist output.
- Present: what matters, what was done, what needs input, what happens next.
"""

from __future__ import annotations

from typing import Any, Optional

from eos_ai.platforms.eos.roles import EOSRole


# ─── Response shapes ─────────────────────────────────────────────────────────


def format_briefing(context: dict[str, Any]) -> str:
    """Format a status briefing from EA context."""
    state = context.get("state", {})
    insights = context.get("insights", [])
    suggestions = context.get("suggestions", [])

    lines: list[str] = []

    # Session state
    session = state.get("operator_session", {})
    day_status = "open" if session.get("is_day_open") else "closed"
    lines.append(f"Day is {day_status}.")

    # Task summary
    tasks = state.get("tasks", {})
    counts = tasks.get("counts", {})
    if counts:
        total = tasks.get("total", 0)
        blocked = counts.get("waiting_on_operator", 0)
        in_progress = counts.get("in_progress", 0)
        completed = counts.get("completed", 0)
        lines.append(
            f"Tasks: {total} total — {in_progress} active, "
            f"{completed} done, {blocked} waiting on you."
        )

    # Pipeline summary
    pipelines = state.get("pipelines", {})
    active_p = pipelines.get("active_count", 0)
    blocked_p = pipelines.get("blocked_count", 0)
    failed_p = pipelines.get("failed_count", 0)
    if active_p or blocked_p or failed_p:
        lines.append(
            f"Pipelines: {active_p} active, {blocked_p} blocked, {failed_p} failed."
        )

    # Perceptions
    perceptions = state.get("perceptions", {})
    critical = perceptions.get("critical_count", 0)
    warning = perceptions.get("warning_count", 0)
    if critical or warning:
        lines.append(f"Alerts: {critical} critical, {warning} warning.")

    # Insights
    if insights:
        lines.append("")
        for insight in insights:
            lines.append(f"— {insight}")

    # Suggestions
    if suggestions:
        lines.append("")
        lines.append("Next:")
        for suggestion in suggestions:
            lines.append(f"  • {suggestion}")

    return "\n".join(lines)


def format_strategic_recommendation(
    context: dict[str, Any],
    *,
    recommendation: Optional[str] = None,
) -> str:
    """Format a CEO-originated strategic recommendation through EA voice."""
    state = context.get("state", {})
    insights = context.get("insights", [])
    suggestions = context.get("suggestions", [])

    lines: list[str] = []

    # Execution health
    health = state.get("execution_health", {})
    if health:
        blocked = health.get("tasks_blocked", 0)
        active = health.get("pipelines_active", 0)
        failed = health.get("pipelines_failed", 0)
        lines.append(
            f"Execution: {blocked} blocked, {active} pipeline(s) running, "
            f"{failed} failed."
        )

    # Continuity
    continuity = state.get("continuity", {})
    priorities = continuity.get("unfinished_priorities", [])
    if priorities:
        lines.append(f"Carried priorities: {len(priorities)}")
        for p in priorities[:3]:
            lines.append(f"  — {p}")

    # Recommendation
    if recommendation:
        lines.append("")
        lines.append(recommendation)

    # Insights
    if insights:
        lines.append("")
        for insight in insights:
            lines.append(f"— {insight}")

    # Suggestions
    if suggestions:
        lines.append("")
        lines.append("Recommended:")
        for s in suggestions:
            lines.append(f"  • {s}")

    return "\n".join(lines)


def format_portfolio_recommendation(
    context: dict[str, Any],
    *,
    recommendation: Optional[str] = None,
) -> str:
    """Format a Portfolio Advisor recommendation through EA voice."""
    state = context.get("state", {})
    insights = context.get("insights", [])
    suggestions = context.get("suggestions", [])

    lines: list[str] = []

    # Risk indicators
    risk = state.get("risk_indicators", {})
    if risk.get("execution_blocked"):
        lines.append("Execution backlog is elevated — resource risk flagged.")
    if risk.get("critical_alerts"):
        lines.append("Critical alerts present — operational risk flagged.")

    # System health
    health = state.get("system_health", {})
    if health:
        lines.append(
            f"System: {health.get('total_tasks', 0)} tasks, "
            f"{health.get('tasks_blocked', 0)} blocked, "
            f"{health.get('critical_perceptions', 0)} critical alerts."
        )

    if recommendation:
        lines.append("")
        lines.append(recommendation)

    if insights:
        lines.append("")
        for insight in insights:
            lines.append(f"— {insight}")

    if suggestions:
        lines.append("")
        lines.append("Recommended:")
        for s in suggestions:
            lines.append(f"  • {s}")

    return "\n".join(lines)


def format_execution_summary(
    *,
    created_task_ids: list[str],
    created_pipeline_ids: list[str],
    blocked_items: list[str],
    extra: Optional[str] = None,
) -> str:
    """Format an execution handoff summary."""
    lines: list[str] = []

    if created_task_ids:
        lines.append(f"Created {len(created_task_ids)} task(s).")

    if created_pipeline_ids:
        lines.append(f"Created {len(created_pipeline_ids)} pipeline(s).")

    if blocked_items:
        lines.append("")
        lines.append("Blocked:")
        for item in blocked_items:
            lines.append(f"  — {item}")

    if extra:
        lines.append("")
        lines.append(extra)

    if not lines:
        lines.append("Acknowledged. No substrate work created.")

    return "\n".join(lines)


def format_blocked_decision_summary(
    blocked_titles: list[str],
) -> str:
    """Format a summary of items waiting on founder decision."""
    if not blocked_titles:
        return "No items waiting on your decision."

    lines = [f"{len(blocked_titles)} item(s) need your decision:"]
    for title in blocked_titles:
        lines.append(f"  — {title}")
    return "\n".join(lines)


# ─── Master formatter ────────────────────────────────────────────────────────


def format_ea_response(
    *,
    primary_role: EOSRole,
    delegated_role: EOSRole | None,
    context: dict[str, Any],
    summary_type: str,
    created_task_ids: list[str] | None = None,
    created_pipeline_ids: list[str] | None = None,
    blocked_items: list[str] | None = None,
    recommendation: str | None = None,
) -> str:
    """
    Master response formatter — routes to the appropriate shape formatter
    based on summary_type.

    Always returns EA-voiced text regardless of which specialist produced
    the underlying analysis.
    """
    if summary_type == "briefing":
        return format_briefing(context)

    if summary_type == "strategic_recommendation":
        return format_strategic_recommendation(context, recommendation=recommendation)

    if summary_type == "portfolio_recommendation":
        return format_portfolio_recommendation(context, recommendation=recommendation)

    if summary_type == "execution_summary":
        return format_execution_summary(
            created_task_ids=created_task_ids or [],
            created_pipeline_ids=created_pipeline_ids or [],
            blocked_items=blocked_items or [],
        )

    if summary_type == "blocked_decisions":
        titles = blocked_items or []
        return format_blocked_decision_summary(titles)

    # Fallback — briefing
    return format_briefing(context)
