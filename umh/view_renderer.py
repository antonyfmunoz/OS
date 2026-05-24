"""View renderer — displays ViewFrame data from the substrate pipeline.

Reads from WorkstationViewSubscriber's ring buffer to show pipeline
activity: current stage, recent transitions, and trace IDs. This
closes the view socket loop — frames flow from the substrate pipeline
through ViewSocket → WorkstationViewSubscriber → this renderer.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_STAGE_NAMES: dict[int, str] = {
    0: "interpret",
    1: "recall",
    2: "lookup",
    3: "compose",
    4: "route",
    5: "execute",
    6: "trace",
    7: "feedback",
}


def _get_view_subscriber() -> Any:
    try:
        from umh.transport import get_view_subscriber

        return get_view_subscriber()
    except Exception:
        return None


def get_current_stage() -> str | None:
    """Return the name of the most recent pipeline stage, or None."""
    sub = _get_view_subscriber()
    if sub is None:
        return None
    stage = sub.last_stage
    if stage is None:
        return None
    return _STAGE_NAMES.get(stage, f"stage_{stage}")


def get_frame_count() -> int:
    """Return the number of buffered view frames."""
    sub = _get_view_subscriber()
    if sub is None:
        return 0
    return sub.frame_count


def get_recent_frames(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent frames as dicts for display."""
    sub = _get_view_subscriber()
    if sub is None:
        return []

    frames = sub.recent_frames[-limit:]
    result = []
    for f in frames:
        result.append(
            {
                "stage": _STAGE_NAMES.get(f.stage, f"stage_{f.stage}"),
                "event_type": f.event_type,
                "trace_id": str(f.trace_id)[:8] if f.trace_id else None,
                "timestamp": f.timestamp.strftime("%H:%M:%S")
                if hasattr(f.timestamp, "strftime")
                else str(f.timestamp),
                "data_keys": list(f.data.keys()) if f.data else [],
            }
        )
    return result


def format_view(limit: int = 10) -> str:
    """Format recent view frames for display."""
    frames = get_recent_frames(limit)
    if not frames:
        stage = get_current_stage()
        if stage:
            return f"Pipeline: last stage = {stage} (no recent frames)"
        return "Pipeline: no view frames received"

    lines = [f"Pipeline View ({len(frames)} recent frames):"]
    for f in frames:
        trace = f" [trace:{f['trace_id']}]" if f["trace_id"] else ""
        lines.append(f"  {f['timestamp']}  {f['stage']:<12s} {f['event_type']}{trace}")

    return "\n".join(lines)


def format_view_summary() -> str:
    """One-line summary for status display."""
    count = get_frame_count()
    stage = get_current_stage()
    if count == 0 and stage is None:
        return "no activity"
    parts = []
    if stage:
        parts.append(f"last: {stage}")
    if count:
        parts.append(f"{count} frames buffered")
    return ", ".join(parts)


def show_view(limit: int = 10) -> None:
    """Print view frame display."""
    print(format_view(limit))
