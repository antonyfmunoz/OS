"""
Context builder — assembles structured context dicts from substrate state.

Every context function returns a dict with four stable sections:

    {
        "meta":        {...},   # role, timestamp, request metadata
        "state":       {...},   # current system/domain state
        "insights":    [...],   # observations, anomalies, patterns
        "suggestions": [...],   # recommended next actions
    }

Design rules:
- Pure data — zero formatting, zero text shaping.
- Reads substrate stores; never mutates them.
- No LLM calls — all insights/suggestions are heuristic.
- Failures are swallowed and noted in insights, never raised.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any, Optional

from eos_ai.platforms.eos.roles import EOSRole


def _log(msg: str) -> None:
    print(f"[platform.eos.context_builder] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(fn, default=None):
    """Call fn(), return default on any exception."""
    try:
        return fn()
    except Exception as exc:
        _log(f"safe call failed: {exc}")
        return default


# ─── Substrate imports (lazy, best-effort) ───────────────────────────────────


def _get_operator_session():
    from eos_ai.substrate.operator_session import OperatorSessionStore

    return OperatorSessionStore.default().get()


def _get_task_summary() -> dict:
    from eos_ai.substrate.task_system import TaskStore, TaskStatus

    store = TaskStore.default()
    counts = store.count_by_status()
    blocked = store.by_status(TaskStatus.WAITING_ON_OPERATOR)
    return {
        "counts": counts,
        "blocked_titles": [t.title for t in blocked[:10]],
        "total": sum(counts.values()),
    }


def _get_pipeline_summary() -> dict:
    from eos_ai.substrate.task_pipeline import PipelineStore, PipelineStatus

    store = PipelineStore.default()
    active = store.by_status(PipelineStatus.IN_PROGRESS)
    blocked = store.by_status(PipelineStatus.WAITING_ON_OPERATOR)
    failed = store.by_status(PipelineStatus.FAILED)
    return {
        "active_count": len(active),
        "blocked_count": len(blocked),
        "failed_count": len(failed),
        "active_titles": [p.title for p in active[:5]],
        "blocked_titles": [p.title for p in blocked[:5]],
    }


def _get_perception_summary() -> dict:
    from eos_ai.substrate.perception import PerceptionStore, PerceptionSeverity

    store = PerceptionStore.default()
    critical = store.by_severity(PerceptionSeverity.CRITICAL)
    warning = store.by_severity(PerceptionSeverity.WARNING)
    return {
        "critical_count": len(critical),
        "warning_count": len(warning),
        "critical_summaries": [p.summary for p in critical[:5]],
        "warning_summaries": [p.summary for p in warning[:5]],
    }


def _get_station_summary() -> dict:
    from eos_ai.substrate.station_presence import get_station_summary

    return get_station_summary()


def _get_live_session_summary() -> dict:
    from eos_ai.substrate.live_sessions import LiveSessionStore, LiveSessionState

    store = LiveSessionStore.default()
    active = store.by_state(LiveSessionState.ACTIVE)
    return {
        "active_count": len(active),
        "active_titles": [s.title for s in active[:5]],
    }


# ─── EA context ──────────────────────────────────────────────────────────────


def build_ea_context(
    *,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build EA context — communication, coordination, next actions, blocked decisions.

    EA sees the widest view: tasks, pipelines, perceptions, session state,
    station presence, live sessions.
    """
    session = _safe(_get_operator_session)
    tasks = _safe(_get_task_summary, {})
    pipelines = _safe(_get_pipeline_summary, {})
    perceptions = _safe(_get_perception_summary, {})
    station = _safe(_get_station_summary, {})
    live_sessions = _safe(_get_live_session_summary, {})

    # ── meta ──
    meta: dict[str, Any] = {
        "role": EOSRole.EA.value,
        "timestamp": _utcnow(),
        "session_id": session_id,
        "day_open": session.is_day_open if session else False,
        "day_mode": session.day_mode.value if session else "inactive",
    }

    # ── state ──
    state: dict[str, Any] = {
        "operator_session": {
            "is_day_open": session.is_day_open if session else False,
            "day_mode": session.day_mode.value if session else "inactive",
            "active_workspace": session.active_workspace if session else None,
            "node_preference": session.node_preference if session else None,
        },
        "tasks": tasks,
        "pipelines": pipelines,
        "perceptions": perceptions,
        "station": station,
        "live_sessions": live_sessions,
    }

    # ── insights ──
    insights: list[str] = []

    blocked_tasks = tasks.get("counts", {}).get("waiting_on_operator", 0)
    if blocked_tasks > 0:
        insights.append(f"{blocked_tasks} task(s) waiting on operator decision")

    critical_count = perceptions.get("critical_count", 0)
    if critical_count > 0:
        insights.append(f"{critical_count} critical perception(s) detected")

    pipeline_blocked = pipelines.get("blocked_count", 0)
    if pipeline_blocked > 0:
        insights.append(f"{pipeline_blocked} pipeline(s) blocked on operator")

    pipeline_failed = pipelines.get("failed_count", 0)
    if pipeline_failed > 0:
        insights.append(f"{pipeline_failed} pipeline(s) in failed state")

    if session and not session.is_day_open:
        insights.append("Day is not open — tasks will queue for overnight")

    # ── suggestions ──
    suggestions: list[str] = []

    if blocked_tasks > 0:
        suggestions.append("Review blocked tasks and provide decisions")

    if critical_count > 0:
        suggestions.append("Address critical perceptions before other work")

    if session and not session.is_day_open:
        suggestions.append("Open the day to enable real-time task execution")

    if pipeline_failed > 0:
        suggestions.append("Inspect failed pipelines for retry or resolution")

    return {
        "meta": meta,
        "state": state,
        "insights": insights,
        "suggestions": suggestions,
    }


# ─── CEO context ─────────────────────────────────────────────────────────────


def build_ceo_context(
    *,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build CEO context — priorities, strategic state, blocked execution, direction.

    CEO sees: task health, pipeline progress, session continuity, perceptions
    filtered for strategic relevance.
    """
    session = _safe(_get_operator_session)
    tasks = _safe(_get_task_summary, {})
    pipelines = _safe(_get_pipeline_summary, {})
    perceptions = _safe(_get_perception_summary, {})

    meta: dict[str, Any] = {
        "role": EOSRole.CEO.value,
        "timestamp": _utcnow(),
        "session_id": session_id,
    }

    state: dict[str, Any] = {
        "execution_health": {
            "total_tasks": tasks.get("total", 0),
            "tasks_blocked": tasks.get("counts", {}).get("waiting_on_operator", 0),
            "tasks_in_progress": tasks.get("counts", {}).get("in_progress", 0),
            "tasks_completed": tasks.get("counts", {}).get("completed", 0),
            "pipelines_active": pipelines.get("active_count", 0),
            "pipelines_failed": pipelines.get("failed_count", 0),
        },
        "continuity": {
            "unfinished_priorities": (session.unfinished_priorities if session else []),
            "continuity_notes": (
                session.continuity_notes_for_next_open if session else None
            ),
            "last_resume_context": (session.last_resume_context if session else None),
        },
        "perceptions": {
            "critical_count": perceptions.get("critical_count", 0),
            "warning_count": perceptions.get("warning_count", 0),
        },
    }

    insights: list[str] = []

    blocked = tasks.get("counts", {}).get("waiting_on_operator", 0)
    if blocked > 0:
        insights.append(f"{blocked} decision(s) blocking execution")

    failed = pipelines.get("failed_count", 0)
    if failed > 0:
        insights.append(f"{failed} pipeline failure(s) may need strategic triage")

    if session and session.unfinished_priorities:
        insights.append(
            f"{len(session.unfinished_priorities)} unfinished priority(ies) "
            "carried from previous session"
        )

    suggestions: list[str] = []

    if blocked > 0:
        suggestions.append("Unblock waiting decisions to restore execution velocity")

    if session and session.unfinished_priorities:
        suggestions.append("Review carried priorities — reprioritize or close")

    if failed > 0:
        suggestions.append("Decide: retry, abandon, or restructure failed pipelines")

    return {
        "meta": meta,
        "state": state,
        "insights": insights,
        "suggestions": suggestions,
    }


# ─── Portfolio Advisor context ───────────────────────────────────────────────


def build_portfolio_context(
    *,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build Portfolio Advisor context — investment, capital, risk state.

    Portfolio Advisor sees: high-level execution health (as risk signal),
    perception anomalies (as risk indicators), and continuity state.
    This is intentionally thin for v1 — no real financial data sources yet.
    """
    session = _safe(_get_operator_session)
    tasks = _safe(_get_task_summary, {})
    perceptions = _safe(_get_perception_summary, {})

    meta: dict[str, Any] = {
        "role": EOSRole.PORTFOLIO_ADVISOR.value,
        "timestamp": _utcnow(),
        "session_id": session_id,
    }

    state: dict[str, Any] = {
        "system_health": {
            "total_tasks": tasks.get("total", 0),
            "tasks_blocked": tasks.get("counts", {}).get("waiting_on_operator", 0),
            "critical_perceptions": perceptions.get("critical_count", 0),
            "warning_perceptions": perceptions.get("warning_count", 0),
        },
        "risk_indicators": {
            "execution_blocked": (
                tasks.get("counts", {}).get("waiting_on_operator", 0) > 3
            ),
            "critical_alerts": perceptions.get("critical_count", 0) > 0,
        },
    }

    insights: list[str] = []

    if state["risk_indicators"]["execution_blocked"]:
        insights.append("Execution backlog exceeds threshold — resource risk")

    if state["risk_indicators"]["critical_alerts"]:
        insights.append("Critical system alerts present — operational risk")

    suggestions: list[str] = []

    if state["risk_indicators"]["execution_blocked"]:
        suggestions.append("Recommend operator attention to clear decision backlog")

    if state["risk_indicators"]["critical_alerts"]:
        suggestions.append(
            "Recommend addressing critical alerts before new commitments"
        )

    return {
        "meta": meta,
        "state": state,
        "insights": insights,
        "suggestions": suggestions,
    }


# ─── Unified context dispatcher ──────────────────────────────────────────────

_BUILDERS: dict[EOSRole, Any] = {
    EOSRole.EA: build_ea_context,
    EOSRole.CEO: build_ceo_context,
    EOSRole.PORTFOLIO_ADVISOR: build_portfolio_context,
}


def build_context_for_role(
    role: EOSRole,
    *,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build context for any EOS role.

    Falls back to EA context for GENERAL or unknown roles.
    """
    builder = _BUILDERS.get(role, build_ea_context)
    return builder(session_id=session_id)
