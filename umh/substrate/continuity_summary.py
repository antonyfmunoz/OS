"""
Continuity Summary — operator-facing day lifecycle report.

Composes data from ActionTracker, workstation_log, event_store,
node_controller, and OperatorSession into a single structured summary
plus a human-readable text block.

Consumed by:
    open_day()  — "what happened while I was away?"
    close_day() — "what state am I handing off?"

Design rules (mirror substrate conventions):
- Best-effort: every data source is read inside try/except.
  A partial summary is always better than a crash.
- Additive only: never modifies any store.
- Bounded: all list outputs are capped.
- Deterministic: no LLM calls. Pure data composition.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


_LOG_PREFIX = "[substrate.continuity_summary]"
_MAX_ITEMS = 20  # cap list outputs for readability


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    """Parse an ISO timestamp, returning None on failure."""
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ─── Data Model ──────────────────────────────────────────────────────────────


@dataclass
class ContinuitySummary:
    """Structured continuity report for the operator.

    Contains both machine-readable fields and a pre-rendered
    human-readable text block.
    """

    # Timestamps
    generated_at: str = field(default_factory=_utcnow)
    window_start: Optional[str] = None  # last close_day timestamp
    window_end: Optional[str] = None  # current open_day timestamp

    # Node health
    nodes_online: int = 0
    nodes_total: int = 0
    local_online: bool = False
    reconnect_detected: bool = False
    reconnected_nodes: list[str] = field(default_factory=list)
    stale_nodes: list[str] = field(default_factory=list)

    # Action tracker summary
    actions_completed: int = 0
    actions_failed: int = 0
    actions_expired: int = 0
    actions_pending: int = 0
    completed_action_kinds: list[str] = field(default_factory=list)
    failed_action_details: list[dict[str, Any]] = field(default_factory=list)
    expired_action_details: list[dict[str, Any]] = field(default_factory=list)

    # Overnight task execution results
    overnight_tasks_executed: int = 0
    overnight_tasks_succeeded: int = 0
    overnight_tasks_failed: int = 0
    overnight_task_details: list[dict[str, Any]] = field(default_factory=list)

    # Overnight / between-session activity
    workstation_events_count: int = 0
    notable_events: list[str] = field(default_factory=list)

    # Prior session continuity
    prior_continuity_notes: Optional[str] = None
    prior_unfinished: list[str] = field(default_factory=list)
    prior_resume_context: Optional[str] = None

    # Current state
    day_mode: Optional[str] = None
    active_workspace: Optional[str] = None
    active_scene: Optional[str] = None

    # Interaction archive summary (verbatim conversation continuity)
    interaction_total: int = 0
    interaction_inbound: int = 0
    interaction_outbound: int = 0
    interaction_interfaces: list[str] = field(default_factory=list)
    interaction_latest: Optional[str] = None
    interaction_window_count: int = 0  # count within continuity window

    # Presence runtime (v9)
    presence_mode: Optional[str] = None
    work_profile: Optional[str] = None
    effective_routing: Optional[str] = None

    # Human-readable summary
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "nodes": {
                "online": self.nodes_online,
                "total": self.nodes_total,
                "local_online": self.local_online,
                "reconnect_detected": self.reconnect_detected,
                "reconnected_nodes": self.reconnected_nodes,
                "stale_nodes": self.stale_nodes,
            },
            "actions": {
                "completed": self.actions_completed,
                "failed": self.actions_failed,
                "expired": self.actions_expired,
                "pending": self.actions_pending,
                "completed_kinds": self.completed_action_kinds,
                "failed_details": self.failed_action_details,
                "expired_details": self.expired_action_details,
            },
            "overnight_tasks": {
                "executed": self.overnight_tasks_executed,
                "succeeded": self.overnight_tasks_succeeded,
                "failed": self.overnight_tasks_failed,
                "details": self.overnight_task_details,
            },
            "activity": {
                "workstation_events": self.workstation_events_count,
                "notable_events": self.notable_events,
            },
            "prior_session": {
                "continuity_notes": self.prior_continuity_notes,
                "unfinished": self.prior_unfinished,
                "resume_context": self.prior_resume_context,
            },
            "current_state": {
                "day_mode": self.day_mode,
                "workspace": self.active_workspace,
                "scene": self.active_scene,
            },
            "interactions": {
                "total": self.interaction_total,
                "inbound": self.interaction_inbound,
                "outbound": self.interaction_outbound,
                "interfaces": self.interaction_interfaces,
                "latest": self.interaction_latest,
                "window_count": self.interaction_window_count,
            },
            "presence": {
                "mode": self.presence_mode,
                "profile": self.work_profile,
                "routing": self.effective_routing,
            },
            "text": self.text,
        }


# ─── Data Gatherers (each best-effort) ──────────────────────────────────────


def _gather_node_health(summary: ContinuitySummary) -> None:
    """Populate node health fields from NodeController."""
    try:
        from umh.substrate.node_controller import get_node_health_summary

        health = get_node_health_summary()
        summary.nodes_online = health.get("online_nodes", 0)
        summary.nodes_total = health.get("total_nodes", 0)
        summary.local_online = health.get("local_online", False)
        summary.stale_nodes = health.get("stale_nodes", [])

        # Check for reconnect: any node with reconnected_at set
        for node in health.get("nodes", []):
            reconnected_at = node.get("reconnected_at")
            prev_status = node.get("previous_status")
            if reconnected_at and prev_status:
                summary.reconnect_detected = True
                summary.reconnected_nodes.append(node["node_id"])
    except Exception as exc:
        _log(f"node health gather failed: {exc}")


def _gather_action_state(
    summary: ContinuitySummary,
    window_start: Optional[str],
) -> None:
    """Populate action tracker fields, filtered to the continuity window."""
    try:
        from umh.substrate.action_tracker import TrackedState, get_action_tracker

        tracker = get_action_tracker()

        # Get actions by terminal state
        completed = tracker.by_state(TrackedState.COMPLETED)
        failed = tracker.by_state(TrackedState.FAILED)
        expired = tracker.by_state(TrackedState.EXPIRED)
        pending = tracker.by_state(TrackedState.PENDING)
        dispatched = tracker.by_state(TrackedState.DISPATCHED)
        acknowledged = tracker.by_state(TrackedState.ACKNOWLEDGED)

        # Filter to window if we have a start time
        window_dt = _parse_iso(window_start) if window_start else None

        def _in_window(ts_str: Optional[str]) -> bool:
            if not window_dt or not ts_str:
                return True  # no window = include everything
            ts = _parse_iso(ts_str)
            return ts is not None and ts >= window_dt

        window_completed = [a for a in completed if _in_window(a.completed_at)]
        window_failed = [a for a in failed if _in_window(a.failed_at)]
        window_expired = [a for a in expired if _in_window(a.expired_at)]

        summary.actions_completed = len(window_completed)
        summary.actions_failed = len(window_failed)
        summary.actions_expired = len(window_expired)
        summary.actions_pending = len(pending) + len(dispatched) + len(acknowledged)

        # Completed kinds (deduplicated)
        kinds = sorted({a.kind for a in window_completed})
        summary.completed_action_kinds = kinds[:_MAX_ITEMS]

        # Failed details (bounded)
        for a in window_failed[:_MAX_ITEMS]:
            summary.failed_action_details.append(
                {
                    "action_id": a.action_id,
                    "kind": a.kind,
                    "node": a.target_node_id,
                    "detail": a.detail or "",
                    "failed_at": a.failed_at,
                }
            )

        # Expired details (bounded)
        for a in window_expired[:_MAX_ITEMS]:
            summary.expired_action_details.append(
                {
                    "action_id": a.action_id,
                    "kind": a.kind,
                    "node": a.target_node_id,
                    "detail": a.detail or "",
                    "expired_at": a.expired_at,
                }
            )

    except Exception as exc:
        _log(f"action state gather failed: {exc}")


def _gather_workstation_events(
    summary: ContinuitySummary,
    window_start: Optional[str],
) -> None:
    """Populate workstation log events within the continuity window."""
    try:
        from umh.substrate.workstation_log import read_recent

        events = read_recent(200)  # read a generous chunk
        window_dt = _parse_iso(window_start) if window_start else None

        # Notable event types worth surfacing to the operator
        notable_types = {
            "node_reconnected",
            "reconnect_sync",
            "action_failed",
            "action_expired",
            "daemon_crash",
            "bootstrap_started",
            "routing_decision",
        }

        in_window = []
        for evt in events:
            ts_str = evt.get("ts", "")
            if window_dt:
                ts = _parse_iso(ts_str)
                if ts is None or ts < window_dt:
                    continue
            in_window.append(evt)

        summary.workstation_events_count = len(in_window)

        # Extract notable events as concise strings
        for evt in in_window:
            etype = evt.get("event", "")
            if etype in notable_types:
                data = evt.get("data", {})
                ts_str = evt.get("ts", "")
                # Build a one-liner
                if etype == "node_reconnected":
                    node = data.get("node_id", "?")
                    prev = data.get("previous_status", "?")
                    summary.notable_events.append(
                        f"Node {node} reconnected (was {prev}) at {ts_str}"
                    )
                elif etype == "reconnect_sync":
                    expired_n = data.get("expired_actions", 0)
                    valid_n = data.get("valid_pending_actions", 0)
                    summary.notable_events.append(
                        f"Reconnect sync: {expired_n} expired, "
                        f"{valid_n} still valid at {ts_str}"
                    )
                elif etype == "action_failed":
                    kind = data.get("kind", "?")
                    detail = data.get("detail", "")[:80]
                    summary.notable_events.append(f"Action failed: {kind} — {detail}")
                elif etype == "action_expired":
                    kind = data.get("kind", "?")
                    summary.notable_events.append(f"Action expired: {kind} at {ts_str}")
                elif etype == "daemon_crash":
                    summary.notable_events.append(f"Daemon crash at {ts_str}")
                elif etype == "bootstrap_started":
                    profile = data.get("profile", "?")
                    summary.notable_events.append(
                        f"Workstation bootstrap ({profile}) at {ts_str}"
                    )

        # Cap notable events
        summary.notable_events = summary.notable_events[:_MAX_ITEMS]

    except Exception as exc:
        _log(f"workstation events gather failed: {exc}")


def _gather_prior_session(summary: ContinuitySummary) -> None:
    """Populate prior session continuity fields from OperatorSessionStore."""
    try:
        from umh.substrate.operator_session import OperatorSessionStore

        store = OperatorSessionStore.default()
        prior = store.get()
        if prior is None:
            return

        summary.window_start = prior.closed_at
        summary.prior_continuity_notes = prior.continuity_notes_for_next_open
        summary.prior_unfinished = list(prior.unfinished_priorities or [])
        summary.prior_resume_context = prior.last_resume_context
        summary.day_mode = prior.day_mode.value
        summary.active_workspace = prior.active_workspace
        summary.active_scene = prior.active_scene

    except Exception as exc:
        _log(f"prior session gather failed: {exc}")


def _gather_interaction_archive(
    summary: ContinuitySummary,
    window_start: Optional[str],
) -> None:
    """Populate interaction archive summary fields.

    Provides the continuity consumer with awareness of recent conversation
    activity without dumping full transcripts. Counts and metadata only.
    """
    try:
        from umh.substrate.interaction_archive import get_interaction_archive

        archive = get_interaction_archive()
        arch_summary = archive.summary()
        summary.interaction_total = arch_summary.get("total", 0)
        summary.interaction_inbound = arch_summary.get("inbound", 0)
        summary.interaction_outbound = arch_summary.get("outbound", 0)
        summary.interaction_interfaces = arch_summary.get("interfaces", [])
        summary.interaction_latest = arch_summary.get("latest")

        # Count interactions within the continuity window
        if window_start and summary.interaction_total > 0:
            window_interactions = archive.by_time_window(window_start)
            summary.interaction_window_count = len(window_interactions)
        else:
            summary.interaction_window_count = summary.interaction_total

    except Exception as exc:
        _log(f"interaction archive gather failed: {exc}")


def _gather_presence_runtime(summary: ContinuitySummary) -> None:
    """Populate presence/profile fields from presence_runtime."""
    try:
        from umh.substrate.presence_runtime import presence_for_continuity

        pres = presence_for_continuity()
        summary.presence_mode = pres.get("presence_mode")
        summary.work_profile = pres.get("work_profile")
        summary.effective_routing = pres.get("effective_routing")
    except Exception as exc:
        _log(f"presence runtime gather failed: {exc}")


def _gather_overnight_results(
    summary: ContinuitySummary,
    overnight_results: Optional[list[dict[str, Any]]] = None,
) -> None:
    """Populate overnight task execution results.

    Args:
        summary: The summary being built.
        overnight_results: Pre-fetched results from the prior session.
            Passed explicitly because by the time build_continuity_summary()
            runs inside open_day(), the store already holds the NEW session.
            If None, attempts to read from the current store (works when
            called outside the open_day flow, e.g. from close_day).
    """
    try:
        results = overnight_results
        if results is None:
            from umh.substrate.operator_session import OperatorSessionStore

            store = OperatorSessionStore.default()
            prior = store.get()
            if prior is not None:
                results = list(prior.overnight_results or [])

        if not results:
            return

        summary.overnight_tasks_executed = len(results)
        for r in results:
            status = r.get("status", "")
            if status == "completed":
                summary.overnight_tasks_succeeded += 1
            else:
                summary.overnight_tasks_failed += 1

        # Keep bounded details for the operator
        summary.overnight_task_details = results[:_MAX_ITEMS]

    except Exception as exc:
        _log(f"overnight results gather failed: {exc}")


# ─── Text Renderer ───────────────────────────────────────────────────────────


def _render_text(summary: ContinuitySummary) -> str:
    """Render a concise human-readable continuity summary.

    Not a dashboard. Not a dump. An operator briefing you could
    read on a phone screen in 15 seconds.
    """
    lines: list[str] = []
    lines.append("── Continuity Summary ──")

    # Node status
    node_line = f"Nodes: {summary.nodes_online}/{summary.nodes_total} online"
    if summary.local_online:
        node_line += " (local up)"
    else:
        node_line += " (local down)"
    lines.append(node_line)

    if summary.reconnect_detected:
        nodes = ", ".join(summary.reconnected_nodes)
        lines.append(f"⚡ Reconnect detected: {nodes}")

    if summary.stale_nodes:
        lines.append(f"⚠ Stale: {', '.join(summary.stale_nodes)}")

    # Overnight task results
    if summary.overnight_tasks_executed:
        on_line = f"Overnight: {summary.overnight_tasks_executed} task(s) executed"
        if summary.overnight_tasks_succeeded:
            on_line += f", {summary.overnight_tasks_succeeded} succeeded"
        if summary.overnight_tasks_failed:
            on_line += f", {summary.overnight_tasks_failed} failed"
        lines.append(on_line)
        # Surface failures explicitly
        for r in summary.overnight_task_details:
            if r.get("status") != "completed":
                title = r.get("title") or r.get("task_id", "?")
                lines.append(f"  ✗ {title}: {r.get('result', 'no detail')}")

    # Actions
    action_parts: list[str] = []
    if summary.actions_completed:
        action_parts.append(f"{summary.actions_completed} completed")
    if summary.actions_failed:
        action_parts.append(f"{summary.actions_failed} failed")
    if summary.actions_expired:
        action_parts.append(f"{summary.actions_expired} expired")
    if summary.actions_pending:
        action_parts.append(f"{summary.actions_pending} pending")

    if action_parts:
        lines.append(f"Actions: {', '.join(action_parts)}")
    else:
        lines.append("Actions: none tracked")

    if summary.completed_action_kinds:
        lines.append(f"  Completed types: {', '.join(summary.completed_action_kinds)}")

    # Failures worth calling out
    if summary.failed_action_details:
        lines.append("  Failures:")
        for f in summary.failed_action_details[:5]:
            detail = f["detail"][:60] if f["detail"] else "no detail"
            lines.append(f"    - {f['kind']}: {detail}")

    # Expired worth calling out
    if summary.expired_action_details:
        lines.append(f"  Expired: {len(summary.expired_action_details)} action(s)")

    # Notable events
    if summary.notable_events:
        lines.append(f"Events ({summary.workstation_events_count} total):")
        for evt in summary.notable_events[:5]:
            lines.append(f"  - {evt}")
    elif summary.workstation_events_count:
        lines.append(f"Events: {summary.workstation_events_count} (nothing notable)")

    # Interaction archive
    if summary.interaction_total > 0:
        ia_line = (
            f"Interactions: {summary.interaction_total} archived "
            f"({summary.interaction_inbound} in, {summary.interaction_outbound} out)"
        )
        if (
            summary.interaction_window_count
            and summary.interaction_window_count != summary.interaction_total
        ):
            ia_line += f", {summary.interaction_window_count} since last close"
        if summary.interaction_interfaces:
            ia_line += f" via {', '.join(summary.interaction_interfaces)}"
        lines.append(ia_line)

    # Presence runtime
    if summary.presence_mode:
        pres_line = f"Presence: {summary.presence_mode}"
        if summary.work_profile:
            pres_line += f" | Profile: {summary.work_profile}"
        if summary.effective_routing:
            pres_line += f" | Routing: {summary.effective_routing}"
        lines.append(pres_line)

    # Prior session continuity
    if summary.prior_continuity_notes:
        lines.append(f"Notes from last close: {summary.prior_continuity_notes}")

    if summary.prior_unfinished:
        items = ", ".join(str(x) for x in summary.prior_unfinished[:5])
        lines.append(f"Unfinished: {items}")

    if summary.prior_resume_context:
        lines.append(f"Resume context: {summary.prior_resume_context}")

    lines.append("────────────────────────")
    return "\n".join(lines)


# ─── Public API ──────────────────────────────────────────────────────────────


def build_continuity_summary(
    *,
    window_start: Optional[str] = None,
    overnight_results: Optional[list[dict[str, Any]]] = None,
) -> ContinuitySummary:
    """Build a full continuity summary for the operator.

    Args:
        window_start: ISO timestamp marking the start of the continuity
            window (typically the prior session's closed_at). If None,
            the prior session's closed_at is used. If no prior session
            exists, all available data is included.
        overnight_results: Pre-fetched overnight execution results from
            the prior session. Must be passed explicitly when called from
            open_day() because the store already holds the new session.

    Returns:
        ContinuitySummary with both structured data and rendered text.
    """
    summary = ContinuitySummary()

    # Gather prior session first — it sets window_start
    _gather_prior_session(summary)

    # Use explicit window_start if provided, else fall back to prior session
    effective_window = window_start or summary.window_start
    summary.window_start = effective_window
    summary.window_end = _utcnow()

    # Gather from all sources
    _gather_node_health(summary)
    _gather_action_state(summary, effective_window)
    _gather_workstation_events(summary, effective_window)
    _gather_overnight_results(summary, overnight_results=overnight_results)
    _gather_interaction_archive(summary, effective_window)
    _gather_presence_runtime(summary)

    # Render human-readable text
    summary.text = _render_text(summary)

    return summary


def build_close_snapshot() -> dict[str, Any]:
    """Build a structured snapshot at close_day time.

    Captures the current state that the next open_day() will need
    to produce a meaningful continuity summary. Stored in the
    session's last_briefing_summary field as a JSON string.
    """
    snapshot: dict[str, Any] = {
        "snapshot_at": _utcnow(),
        "type": "close_day_snapshot",
    }

    # Action tracker stats
    try:
        from umh.substrate.action_tracker import get_action_tracker

        snapshot["action_stats"] = get_action_tracker().stats()
    except Exception as exc:
        _log(f"close snapshot action_stats failed: {exc}")
        snapshot["action_stats"] = {}

    # Node health
    try:
        from umh.substrate.node_controller import get_node_health_summary

        health = get_node_health_summary()
        snapshot["node_health"] = {
            "total": health.get("total_nodes", 0),
            "online": health.get("online_nodes", 0),
            "local_online": health.get("local_online", False),
            "stale_nodes": health.get("stale_nodes", []),
        }
    except Exception as exc:
        _log(f"close snapshot node_health failed: {exc}")
        snapshot["node_health"] = {}

    # Workstation log summary
    try:
        from umh.substrate.workstation_log import log_summary

        snapshot["log_summary"] = log_summary()
    except Exception as exc:
        _log(f"close snapshot log_summary failed: {exc}")
        snapshot["log_summary"] = {}

    return snapshot


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "ContinuitySummary",
    "build_continuity_summary",
    "build_close_snapshot",
]
