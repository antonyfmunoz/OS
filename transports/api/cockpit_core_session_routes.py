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

from transports.api.governed import governed_mutation

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

        def _do_send():
            from substrate.execution.bridge.claude_session_bridge import (
                ensure_session,
                send_message,
            )
            ensure_result = ensure_session(target, session_name)
            if not ensure_result.get("ok"):
                return "session not available: %s" % ensure_result.get("reason", "unknown"), False
            send_message(target, session_name, text)
            _log_cc_trace(session_name, text, work_packet_id, "send")
            return f"sent to {session_name}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"claude session send to {session_name}",
            execute_fn=_do_send,
            source="cockpit",
            metadata={"session_name": session_name, "target": target},
        )
        return resp.to_http_dict()

    @router.post("/claude-session/capture")
    def claude_session_capture(payload: dict) -> dict:  # type: ignore[type-arg]
        """Capture output from a Claude Code session."""
        session_name = payload.get("session_name", "")
        target = payload.get("target", "local")
        work_packet_id = payload.get("work_packet_id", "")
        if not session_name:
            return {"error": "session_name required"}

        def _do_capture():
            from substrate.execution.bridge.claude_session_bridge import capture_output
            capture_output(target, session_name)
            _log_cc_trace(session_name, "", work_packet_id, "capture")
            return f"captured from {session_name}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"claude session capture from {session_name}",
            execute_fn=_do_capture,
            source="cockpit",
            metadata={"session_name": session_name, "target": target},
        )
        return resp.to_http_dict()

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

        def _do_tmux_send():
            try:
                from substrate.execution.workers.workstation.tmux_operational_adapter_v1 import (
                    TmuxOperationalAdapter,
                )
                adapter = TmuxOperationalAdapter()
                adapter.send_approved_command(session_name, text)
                return f"tmux send to {session_name}", True
            except Exception as exc:
                return str(exc), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"tmux send to {session_name}",
            execute_fn=_do_tmux_send,
            source="cockpit",
            metadata={"session_name": session_name},
        )
        return resp.to_http_dict()

    @router.post("/tmux/send-key")
    def tmux_send_key(payload: dict) -> dict:  # type: ignore[type-arg]
        """Send a special key (Ctrl+C, arrows, etc.) to a tmux session without Enter."""
        session_name = payload.get("session_name", "")
        key = payload.get("key", "")
        if not session_name or not key:
            return {"error": "session_name and key required"}
        allowed_keys = {
            "Up", "Down", "Left", "Right", "BSpace", "DC", "Escape", "Tab",
            "Home", "End", "PPage", "NPage", "Enter",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "C-c", "C-d", "C-z", "C-l", "C-a", "C-e", "C-k", "C-u", "C-w", "C-r",
        }
        if key not in allowed_keys:
            return {"error": f"key '{key}' not in allowed set"}

        def _do_send_key():
            try:
                from substrate.execution.cpu_gate import gated_subprocess_run
                result = gated_subprocess_run(
                    ["tmux", "send-keys", "-t", session_name, key],
                    capture_output=True, text=True, timeout=5,
                    caller="cockpit.tmux_send_key",
                )
                if result is None:
                    return "CPU gate blocked", False
                return f"key {key} sent to {session_name}", result.returncode == 0
            except Exception as exc:
                return str(exc), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"tmux send-key {key} to {session_name}",
            execute_fn=_do_send_key,
            source="cockpit",
            metadata={"session_name": session_name, "key": key},
        )
        return resp.to_http_dict()

    @router.post("/council/review")
    def council_review(payload: dict) -> dict:  # type: ignore[type-arg]
        """Trigger council review for a decision."""
        def _do_review():
            from substrate.organism.council import Council
            council = Council()
            council.review(
                decision_context=payload.get("context", ""),
                proposed_plan=payload.get("plan", ""),
                artifacts=payload.get("artifacts"),
            )
            return "council review completed", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent="council review",
            execute_fn=_do_review,
            source="cockpit",
        )
        return resp.to_http_dict()

    @router.post("/device/register")
    def device_register(payload: dict) -> dict:
        """Register a device session with the presence registry."""
        session_id = payload.get("session_id", "")
        device_id = payload.get("device_id", "")
        if not session_id or not device_id:
            raise HTTPException(status_code=400, detail="session_id and device_id required")

        def _do_register():
            from substrate.workstation.device_presence import DeviceSession, get_registry
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
            return f"device {device_id} registered: {session_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"register device {device_id}",
            execute_fn=_do_register,
            source="cockpit",
            metadata={"device_id": device_id, "session_id": session_id},
        )
        return resp.to_http_dict()

    @router.post("/device/heartbeat")
    def device_heartbeat(payload: dict) -> dict:
        """Heartbeat — refresh session last_seen and apply optional field updates."""
        session_id = payload.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")

        def _do_heartbeat():
            from substrate.workstation.device_presence import get_registry
            updates = {k: v for k, v in payload.items() if k != "session_id"}
            found = get_registry().heartbeat(session_id, updates=updates or None)
            if not found:
                return "session not found", False
            return f"heartbeat for {session_id}", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"device heartbeat {session_id}",
            execute_fn=_do_heartbeat,
            source="cockpit",
            metadata={"session_id": session_id},
        )
        return resp.to_http_dict()

    @router.get("/device/sessions")
    def device_sessions() -> dict:
        """List all active device sessions."""
        from substrate.workstation.device_presence import get_registry

        sessions = get_registry().get_active_sessions()
        return {"sessions": [s.to_dict() for s in sessions]}

    @router.post("/device/disconnect")
    def device_disconnect(payload: dict) -> dict:
        """Mark a session as disconnected."""
        session_id = payload.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")

        def _do_disconnect():
            from substrate.workstation.device_presence import get_registry
            get_registry().mark_disconnected(session_id)
            return f"session {session_id} disconnected", True

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"disconnect device session {session_id}",
            execute_fn=_do_disconnect,
            source="cockpit",
            metadata={"session_id": session_id},
        )
        return resp.to_http_dict()
