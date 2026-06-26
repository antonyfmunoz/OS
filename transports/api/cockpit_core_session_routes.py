"""Cockpit session & device routes — extracted from cockpit_core_routes.py.

Covers: Claude Code session bridge, tmux send, council review, device presence.
Phase 0.3 route split. UMH transport layer.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)

_RISKY_KEYWORDS = [
    "delete",
    "drop",
    "rm -rf",
    "force push",
    "reset --hard",
    "truncate",
    "--no-verify",
    "destroy",
]


def register_session_routes(router, _require_operator_role, helpers):
    """Register session/device routes onto the given router."""

    def _log_cc_trace(session: str, text: str, packet_id: str, action: str) -> None:
        """Log Claude Code bridge action to execution journal."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "cc_bridge",
            "action": action,
            "session": session,
            "packet_id": packet_id,
            "text_preview": text[:100] if text else "",
        }
        journal = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "organism",
            "execution_journal.jsonl",
        )
        try:
            os.makedirs(os.path.dirname(journal), exist_ok=True)
            with open(journal, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    @router.post("/claude-session/send")
    def claude_session_send(payload: dict) -> dict:  # type: ignore[type-arg]
        """Send a prompt to a Claude Code session via tmux bridge. Governed."""
        from substrate.execution.bridge.claude_session_bridge import (
            ensure_session,
            send_message,
        )

        session_name = payload.get("session_name", "")
        text = payload.get("text", "")
        target = payload.get("target", "local")
        work_packet_id = payload.get("work_packet_id", "")
        if not session_name or not text:
            return {"error": "session_name and text required"}
        text_lower = text.lower()
        blocked = [kw for kw in _RISKY_KEYWORDS if kw in text_lower]
        if blocked:
            return {
                "error": "risky_prompt_blocked",
                "reason": "Prompt contains risky keywords.",
                "blocked_keywords": blocked,
            }
        ensure_result = ensure_session(target, session_name)
        if not ensure_result.get("ok"):
            return {"error": "session not available: %s" % ensure_result.get("reason", "unknown")}
        send_result = send_message(target, session_name, text)
        _log_cc_trace(session_name, text, work_packet_id, "send")
        base: dict = send_result if isinstance(send_result, dict) else {"ok": True}  # type: ignore[assignment]
        return {**base, "work_packet_id": work_packet_id, "traced": True}

    @router.post("/claude-session/capture")
    def claude_session_capture(payload: dict) -> dict:  # type: ignore[type-arg]
        """Capture output from a Claude Code session."""
        from substrate.execution.bridge.claude_session_bridge import capture_output

        session_name = payload.get("session_name", "")
        target = payload.get("target", "local")
        work_packet_id = payload.get("work_packet_id", "")
        if not session_name:
            return {"error": "session_name required"}
        result = capture_output(target, session_name)
        _log_cc_trace(session_name, "", work_packet_id, "capture")
        base: dict = result if isinstance(result, dict) else {"output": str(result)}  # type: ignore[assignment]
        return {**base, "work_packet_id": work_packet_id}

    @router.get("/claude-session/list")
    def claude_session_list() -> dict:  # type: ignore[type-arg]
        """List active Claude Code sessions."""
        from substrate.execution.bridge.claude_session_bridge import list_sessions

        return list_sessions()  # type: ignore[return-value]

    @router.post("/tmux/send")
    def tmux_send(payload: dict) -> dict:  # type: ignore[type-arg]
        """Send keys to a tmux session (governed via TmuxOperationalAdapter)."""
        session_name = payload.get("session_name", "")
        text = payload.get("text", "")
        if not session_name or not text:
            return {"error": "session_name and text required"}
        try:
            from substrate.execution.workers.workstation.tmux_operational_adapter_v1 import (
                TmuxOperationalAdapter,
            )

            adapter = TmuxOperationalAdapter()
            result = adapter.send_approved_command(session_name, text)
            if hasattr(result, "to_dict"):
                return result.to_dict()  # type: ignore[union-attr]
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as exc:
            return {"error": str(exc)}

    @router.post("/council/review")
    def council_review(payload: dict) -> dict:  # type: ignore[type-arg]
        """Trigger council review for a decision."""
        from substrate.organism.council import Council

        council = Council()
        review = council.review(
            decision_context=payload.get("context", ""),
            proposed_plan=payload.get("plan", ""),
            artifacts=payload.get("artifacts"),
        )
        return {"ok": True, "review": review.to_dict()}

    @router.post("/device/register")
    def device_register(payload: dict) -> dict:
        """Register a device session with the presence registry."""
        from substrate.workstation.device_presence import DeviceSession, get_registry

        session_id = payload.get("session_id", "")
        device_id = payload.get("device_id", "")
        if not session_id or not device_id:
            raise HTTPException(status_code=400, detail="session_id and device_id required")

        session = DeviceSession(
            device_id=device_id,
            session_id=session_id,
            operator_id=payload.get("operator_id", "default"),
            client_type=payload.get("client_type", "desktop_browser"),
            device_label=payload.get("device_label", ""),
            control_surface=payload.get("control_surface", "fly_cockpit"),
            current_panel=payload.get("current_panel", ""),
            can_capture_audio=bool(payload.get("can_capture_audio", True)),
            can_play_audio=bool(payload.get("can_play_audio", True)),
            reachable_nodes=payload.get("reachable_nodes", ["cockpit", "vps"]),
        )
        get_registry().register_session(session)
        return {"ok": True, "session_id": session_id}

    @router.post("/device/heartbeat")
    def device_heartbeat(payload: dict) -> dict:
        """Heartbeat — refresh session last_seen and apply optional field updates."""
        from substrate.workstation.device_presence import get_registry

        session_id = payload.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")

        updates = {k: v for k, v in payload.items() if k != "session_id"}
        found = get_registry().heartbeat(session_id, updates=updates or None)
        if not found:
            return {"ok": False, "reason": "session not found"}
        return {"ok": True}

    @router.get("/device/sessions")
    def device_sessions() -> dict:
        """List all active device sessions."""
        from substrate.workstation.device_presence import get_registry

        sessions = get_registry().get_active_sessions()
        return {"sessions": [s.to_dict() for s in sessions]}

    @router.post("/device/disconnect")
    def device_disconnect(payload: dict) -> dict:
        """Mark a session as disconnected."""
        from substrate.workstation.device_presence import get_registry

        session_id = payload.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")

        get_registry().mark_disconnected(session_id)
        return {"ok": True}
