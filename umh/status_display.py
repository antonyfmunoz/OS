"""Status display — rich workstation dashboard replacing minimal ModeState.display().

Aggregates mode state, perception, operator state, approvals, outcomes,
scheduler, transport, continuity, and health into a single status view.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from umh.modes import ModeState

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


def build_status(
    mode_state: ModeState,
    session_id: str = "",
    text_only: bool = False,
    node_id: str = "workstation_local",
    perception: Any = None,
    scheduler: Any = None,
    continuity: Any = None,
    inference_checker: Any = None,
) -> str:
    """Build the full workstation status string."""
    persona_name = os.environ.get("UMH_PERSONA_NAME", "UMH")
    profiles = " + ".join(p.value for p in mode_state.profiles)
    sid = session_id[:8] if session_id else "(none)"
    voice_str = "text-only" if text_only else "ambient"

    webcam_str = "disabled"
    if perception is not None:
        snap = perception.get_snapshot()
        wc = snap.get("webcam", {})
        if wc.get("running"):
            webcam_str = "active (present)" if wc.get("face_detected") else "active (no face)"

    mesh_str = _get_mesh_str()
    operator_str = _get_operator_str(node_id)
    approval_str = _get_approval_str()
    outcome_str = _get_outcome_str()
    scheduler_str = _get_scheduler_str(scheduler)
    signal_str = _get_signal_str()

    w = 44
    lines = [
        "",
        "╔" + "═" * w + "╗",
        f"║  UMH Workstation — {persona_name:<{w - 21}s}║",
        "╠" + "═" * w + "╝",
        f"  Mode:      {profiles}",
        f"  Session:   {sid}",
        f"  Voice:     {voice_str}",
        f"  Webcam:    {webcam_str}",
        f"  Mesh:      {mesh_str}",
        f"  Operator:  {operator_str}",
        f"  Signals:   {signal_str}",
        f"  Scheduler: {scheduler_str}",
    ]

    pipeline_str = _get_pipeline_str()
    if pipeline_str and pipeline_str != "no activity":
        lines.append(f"  Pipeline:  {pipeline_str}")

    if approval_str:
        lines.append(f"  Approvals: {approval_str}")
    if outcome_str:
        lines.append(f"  Outcomes:  {outcome_str}")

    if continuity is not None:
        cont_str = _get_continuity_str(continuity)
        if cont_str:
            lines.append(f"  Continuity:{cont_str}")

    lines.append("")
    return "\n".join(lines)


def _get_mesh_str() -> str:
    try:
        from umh.mesh import get_node_count

        n = get_node_count()
        return f"{n} node{'s' if n != 1 else ''} online" if n else "standalone"
    except Exception:
        return "standalone"


def _get_operator_str(node_id: str) -> str:
    try:
        from substrate.execution.bridge.operator_state import get_operator_state_store

        store = get_operator_state_store()
        state = store.get_or_create(node_id)
        return state.mode.value
    except ImportError:
        return "unknown"
    except Exception:
        return "unknown"


def _get_pipeline_str() -> str:
    try:
        from umh.view_renderer import format_view_summary

        return format_view_summary()
    except Exception:
        return "no activity"


def _get_approval_str() -> str:
    try:
        from umh.approvals import pending_count

        n = pending_count()
        if n > 0:
            return f"{n} pending"
        return ""
    except Exception:
        return ""


def _get_outcome_str() -> str:
    try:
        from umh.outcomes import get_recent_outcomes

        outcomes = get_recent_outcomes(limit=5)
        if outcomes:
            return f"{len(outcomes)} recent"
        return ""
    except Exception:
        return ""


def _get_scheduler_str(scheduler: Any = None) -> str:
    if scheduler is None:
        return "not running"
    if scheduler.is_running:
        return f"running ({scheduler.trigger_count} triggers)"
    return "stopped"


def _get_signal_str() -> str:
    from umh.signals import _signal_socket

    if _signal_socket is not None:
        return "connected"
    return "disconnected"


def _get_continuity_str(continuity: Any) -> str:
    try:
        count = getattr(continuity, "execution_count", 0)
        if count:
            return f" {count} executions tracked"
        return " active"
    except Exception:
        return ""


def show_status(
    mode_state: ModeState,
    session_id: str = "",
    text_only: bool = False,
    node_id: str = "workstation_local",
    perception: Any = None,
    scheduler: Any = None,
    continuity: Any = None,
    inference_checker: Any = None,
) -> None:
    """Print the full status display."""
    print(
        build_status(
            mode_state=mode_state,
            session_id=session_id,
            text_only=text_only,
            node_id=node_id,
            perception=perception,
            scheduler=scheduler,
            continuity=continuity,
            inference_checker=inference_checker,
        )
    )
