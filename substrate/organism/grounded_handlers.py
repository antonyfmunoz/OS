"""Grounded status handlers — deterministic answers backed by real data.

Every handler in this module operates ONLY on collected grounding data.
None of them call call_with_fallback() or advisor.handle_signal().
If data is missing, the response says so explicitly.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
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
        from substrate.state.runtime_paths import runtime_state_path

        events_path = runtime_state_path("organism", "events.jsonl", create_parent=False)
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


def _fetch_latest_frame() -> dict[str, Any] | None:
    """Fetch latest camera frame from vision relay. Returns None if unavailable."""
    import os
    import urllib.request

    relay_port = int(os.environ.get("VISION_RELAY_PORT", "8097"))
    health_port = relay_port + 1
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{health_port}/latest-frame", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("image_base64"):
                return data
    except Exception:
        pass
    return None


def handle_vision_analysis(content: str) -> Any:
    """Vision analysis — real frame + vision-capable model.

    Grounded: refuses to describe what it "sees" unless a real frame exists.
    Reuses analyze_snapshot() from camera_commands.py for the LLM call.
    """
    frame_data = _fetch_latest_frame()

    if not frame_data:
        return _make_response(
            text="No camera frame available. The camera may be off or no frames have been received yet.",
            intent="camera_control",
            grounding={"frame_available": False, "source": "vision_relay"},
            suggested_actions=[
                {
                    "label": "Turn On Camera",
                    "action": "query",
                    "payload": {"content": "turn on camera"},
                },
            ],
        )

    frame_meta = frame_data.get("meta", {})

    try:
        from substrate.workstation.camera_commands import analyze_snapshot

        analysis = analyze_snapshot(
            image_base64=frame_data["image_base64"],
            transcript=content,
        )
    except Exception as exc:
        logger.warning("vision analysis failed: %s", exc)
        analysis = None

    if analysis and "couldn't analyze" not in analysis.lower():
        text = f"**Camera Analysis**\n\n{analysis}"
        grounding = {
            "frame_available": True,
            "frame_timestamp": frame_meta.get("timestamp", ""),
            "source": "vision_relay + vision_model",
            "model_tier": "ai_enhanced",
        }
    else:
        text = (
            "I have a camera frame but no vision-capable model is available right now. "
            "The camera is active and streaming."
        )
        grounding = {
            "frame_available": True,
            "frame_timestamp": frame_meta.get("timestamp", ""),
            "source": "vision_relay",
            "model_tier": "deterministic",
            "vision_model_available": False,
        }

    return _make_response(
        text=text,
        intent="camera_control",
        grounding=grounding,
        suggested_actions=[
            {
                "label": "Take Snapshot",
                "action": "query",
                "payload": {"content": "take a snapshot"},
            },
            {
                "label": "Camera Status",
                "action": "query",
                "payload": {"content": "camera status"},
            },
        ],
    )


def handle_camera_control(content: str) -> Any:
    """Route CAMERA_CONTROL intent — deterministic sub-classification.

    Analysis operations (what do you see, analyze frame) go through grounded
    vision analysis. Control operations (start/stop/preset/status) go through
    the camera command dispatcher or grounded status handler.
    """
    from substrate.workstation.camera_commands import classify_camera_command

    cmd = classify_camera_command(content)

    if cmd.operation == "analyze" or cmd.needs_ai:
        return handle_vision_analysis(content)

    if cmd.operation == "status":
        return handle_grounded_vision(content)

    # Control operations (start, stop, preset, snapshot, save_preset)
    # return guidance — actual dispatch happens through cockpit WebSocket
    action_map = {
        "start": "Starting camera stream...",
        "stop": "Stopping camera stream...",
        "preset": f"Moving camera to preset: {cmd.preset_name}",
        "save_preset": f"Saving current position as preset: {cmd.save_name}",
        "snapshot": "Capturing snapshot...",
    }
    text = action_map.get(cmd.operation, f"Camera command: {cmd.operation}")

    return _make_response(
        text=text,
        intent="camera_control",
        grounding={"operation": cmd.operation, "source": "deterministic"},
        suggested_actions=[
            {
                "label": "Camera Status",
                "action": "query",
                "payload": {"content": "camera status"},
            },
        ],
    )


def handle_grounded_voice(content: str) -> Any:
    """Voice subsystem health — real provider/endpoint data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("voice_health")
    text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_approvals(content: str) -> Any:
    """Approval queue — real work packet data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("approval_status")
    text = _format_response_with_missing(result)

    return _make_response(
        text=text,
        intent="approval_query",
        grounding=result.to_dict(),
        suggested_actions=[
            {
                "label": "Show All Packets",
                "action": "query",
                "payload": {"content": "show work packets"},
            },
        ],
    )


def handle_grounded_deployments(content: str) -> Any:
    """Recent deployments — real git log data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("recent_deployments")
    text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_reports(content: str) -> Any:
    """Recent reports — real file data only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("recent_reports")
    text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_hermes(content: str) -> Any:
    """Hermes provider status — real health check only, never assumed healthy."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("hermes_status")
    text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_webhook(content: str) -> Any:
    """Webhook service health — real Docker state only."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("webhook_health")

    if result.confidence == "blocked":
        text = "I don't have live webhook status right now.\n\n" + _format_missing(result)
    else:
        text = _format_response_with_missing(result)

    return _make_response(text=text, intent="status_query", grounding=result.to_dict())


def handle_grounded_visual(content: str) -> Any:
    """Visual query — delegates to handle_vision_analysis for real frame + model."""
    return handle_vision_analysis(content)


def handle_grounded_composite_blockers(content: str) -> Any:
    """Composite blocker view — checks ALL blocker sources, not just work packets."""
    from substrate.organism.grounding_registry import collect_grounding

    result = collect_grounding("composite_blockers")

    sections = []

    # Work packet blockers
    bp_data = result.data.get("blocked_packets", {})
    blocked_items = bp_data.get("blocked", [])
    if blocked_items:
        lines = [
            f"- **{b.get('title', b.get('id', '?'))}**: {b.get('reason', 'no reason given')}"
            for b in blocked_items[:10]
        ]
        sections.append("**Blocked Work Packets:**\n" + "\n".join(lines))
    elif "blocked_packets" not in result.missing:
        sections.append("**Work Packets:** No blocked packets")

    # Provider blockers
    prov_data = result.data.get("providers", {})
    providers = prov_data.get("providers", [])
    unavailable = [p for p in providers if not p.get("available")]
    if unavailable:
        lines = [f"- {p['name']}: unavailable" for p in unavailable]
        sections.append("**Unavailable Providers:**\n" + "\n".join(lines))
    elif providers:
        sections.append(f"**Providers:** All {len(providers)} providers healthy")

    # Beast blocker
    beast_data = result.data.get("beast", {})
    if beast_data and not beast_data.get("connected", True):
        sections.append("**Beast:** Disconnected from mesh")
    elif beast_data:
        sections.append("**Beast:** Connected")

    # Docker blocker
    docker_data = result.data.get("docker", {})
    containers = docker_data.get("containers", [])
    unhealthy = [
        c
        for c in containers
        if "unhealthy" in c.get("status", "").lower() or "exited" in c.get("status", "").lower()
    ]
    if unhealthy:
        lines = [f"- {c['name']}: {c['status']}" for c in unhealthy]
        sections.append("**Unhealthy Containers:**\n" + "\n".join(lines))

    # Missing sources
    if result.missing:
        sections.append(_format_missing(result))

    if not sections:
        text = "No blockers detected and no data sources are missing."
    else:
        text = "\n\n".join(sections)

    return _make_response(
        text=text,
        intent="blocked_query",
        grounding=result.to_dict(),
        suggested_actions=[
            {
                "label": "Show System Status",
                "action": "query",
                "payload": {"content": "system status"},
            },
        ],
    )
