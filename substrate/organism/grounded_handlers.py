"""Grounded status handlers — deterministic answers backed by real data.

Every handler in this module operates ONLY on collected grounding data.
None of them call call_with_fallback() or advisor.handle_signal().
If data is missing, the response says so explicitly.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _make_response(
    text: str,
    intent: str,
    grounding: dict[str, Any],
    suggested_actions: list[dict[str, Any]] | None = None,
) -> Any:
    """Build an AdvisorResponse with grounding metadata."""
    from substrate.organism.advisor_conversation import AdvisorResponse

    return AdvisorResponse(
        text=text,
        conversation_id="",
        intent=intent,
        metadata={
            "model_tier": "deterministic",
            "grounding": grounding,
        },
        suggested_actions=suggested_actions
        or [
            {
                "label": "Open Command Center",
                "action": "navigate",
                "payload": {"panel": "commandcenter"},
            },
        ],
    )


def _format_missing(result: Any) -> str:
    """Format missing-source blocker text."""
    parts = []
    for sid in result.missing:
        err = result.collector_errors.get(sid, "unavailable")
        parts.append(f"- **{sid}**: {err}")
    return "**Unavailable sources:**\n" + "\n".join(parts)


def _format_response_with_missing(result: Any) -> str:
    """Combine available data summary with missing-source disclosure."""
    sections = []
    if result.summary:
        sections.append(result.summary)
    if result.missing:
        sections.append(_format_missing(result))
    if not sections:
        return "No data sources available for this query."
    return "\n\n".join(sections)


# ── Public handlers ───────────────────────────────────────────────────────────


def handle_grounded_status(content: str) -> Any:
    """Composite system status — deterministic, never fabricated."""
    from substrate.organism.grounding_registry import (
        collect_grounding,
        detect_status_seeking,
    )

    query_type = detect_status_seeking(content) or "system_status"
    result = collect_grounding(query_type)

    text = _format_response_with_missing(result)

    return _make_response(
        text=text,
        intent="status_query",
        grounding=result.to_dict(),
        suggested_actions=[
            {
                "label": "Open Command Center",
                "action": "navigate",
                "payload": {"panel": "commandcenter"},
            },
            {
                "label": "What's Next?",
                "action": "query",
                "payload": {"content": "what should we do next"},
            },
        ],
    )


def handle_grounded_docker(content: str) -> Any:
    """Docker container status — real socket data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("docker_status")

    if result.confidence == "blocked":
        text = "I don't have live Docker data right now.\n\n" + _format_missing(result)
    else:
        text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_providers(content: str) -> Any:
    """Provider health — real registry data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("provider_health")

    if result.confidence == "blocked":
        text = "I can't check provider health right now.\n\n" + _format_missing(result)
    else:
        text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_blocked(content: str) -> Any:
    """Blocked work packets — real file data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("blocked_packets")
    text = _format_response_with_missing(result)

    return _make_response(
        text=text,
        intent="blocked_query",
        grounding=result.to_dict(),
        suggested_actions=[
            {
                "label": "Show All Packets",
                "action": "query",
                "payload": {"content": "show work packets"},
            },
            {
                "label": "Open Command Center",
                "action": "navigate",
                "payload": {"panel": "commandcenter"},
            },
        ],
    )


def handle_grounded_agents(content: str) -> Any:
    """Agent/workcell status — real heartbeat data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("agent_status")
    text = _format_response_with_missing(result)

    return _make_response(
        text=text,
        intent="agent_query",
        grounding=result.to_dict(),
    )


def handle_grounded_resume(content: str = "") -> Any:
    """Resume brief — deterministic data collection from real sources."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("system_status")

    sections = []
    if result.summary:
        sections.append("**Current State**\n" + result.summary)

    # Recent events from event log
    try:
        import os
        from pathlib import Path

        repo = os.environ.get("UMH_ROOT", "/opt/OS")
        events_path = Path(repo) / "data" / "umh" / "organism" / "events.jsonl"
        if events_path.exists():
            import json

            events: list[dict[str, Any]] = []
            with open(events_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
            recent = events[-10:] if events else []
            if recent:
                event_lines = []
                for e in recent:
                    ts = e.get("timestamp", "")[:19]
                    etype = e.get("type", e.get("event_type", ""))
                    desc = e.get("description", e.get("summary", ""))[:80]
                    event_lines.append(f"- {ts} [{etype}] {desc}")
                sections.append("**Recent Events**\n" + "\n".join(event_lines))
    except Exception:
        pass

    if result.missing:
        sections.append(_format_missing(result))

    text = "\n\n".join(sections) if sections else "No resume data available."

    return _make_response(
        text=text,
        intent="resume_query",
        grounding=result.to_dict(),
        suggested_actions=[
            {
                "label": "Show Approvals",
                "action": "query",
                "payload": {"content": "what needs approval"},
            },
            {
                "label": "Show Blocked",
                "action": "query",
                "payload": {"content": "what is blocked"},
            },
        ],
    )


def handle_grounded_vision(content: str) -> Any:
    """Vision/camera status — real relay data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("vision_status")
    text = _format_response_with_missing(result)

    return _make_response(
        text=text,
        intent="status_query",
        grounding=result.to_dict(),
    )


def handle_grounded_beast(content: str) -> Any:
    """Beast daemon health — real mesh data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("beast_health")

    if result.confidence == "blocked":
        text = "I don't have live Beast status right now.\n\n" + _format_missing(result)
    else:
        text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())
