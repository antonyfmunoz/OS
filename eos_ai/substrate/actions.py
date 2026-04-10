"""
SafeAction schema — structured intents for future local execution.

The substrate must NEVER ship raw shell commands to a local node. Instead the
VPS emits typed *intents* and the Station Daemon interprets them. This keeps
the trust boundary clean: the local node is the only thing that can touch the
local OS, and it only accepts a fixed vocabulary of actions.

This module defines that vocabulary. It is a contract, not an executor.

Usage:
    from eos_ai.substrate import SafeAction, ActionKind

    action = SafeAction(
        kind=ActionKind.OPEN_SCENE,
        payload={"scene": "deep_work"},
        issued_by="ea_orchestrator",
    )
    # → serialized and sent to station daemon via StationContract
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ActionKind(str, Enum):
    """
    Canonical intents. Anything a local node might do for EOS must map to
    one of these. Raw OS commands are explicitly excluded — add a new kind
    here rather than smuggling shell strings through `payload`.
    """

    OPEN_SCENE = "open_scene"              # activate a named workspace scene
    FOCUS_APP = "focus_app"                # raise a specific app window
    LAUNCH_APP = "launch_app"              # start an app by known id
    RUN_BROWSER_FLOW = "run_browser_flow"  # named, pre-registered flow
    SET_CONTROL_MODE = "set_control_mode"  # switch station control mode
    PLAY_SOUND = "play_sound"              # named sound asset
    SPEAK_TEXT = "speak_text"              # TTS on local audio output
    START_LISTENER = "start_listener"      # begin microphone capture
    STOP_LISTENER = "stop_listener"        # end microphone capture
    OPEN_URL = "open_url"                  # open an http(s) url in default browser


class ActionStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"  # station refused (unknown kind / policy)


def _new_id() -> str:
    return f"act_{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SafeAction:
    """
    A single intent dispatched from EOS to a node.

    `payload` is typed loosely as dict for now but each `kind` has an
    expected shape — documented inline. Station Daemon implementations
    validate strictly; this dataclass stays permissive so tests and
    scaffolding can construct actions without a schema dependency.

    Expected payloads by kind:
        OPEN_SCENE        {"scene": str}
        OPEN_URL          {"url": str}  # must be http:// or https://
        FOCUS_APP         {"app_id": str}
        LAUNCH_APP        {"app_id": str, "args": list[str] (optional)}
        RUN_BROWSER_FLOW  {"flow_id": str, "inputs": dict (optional)}
        SET_CONTROL_MODE  {"mode": str}  # see station.ControlMode
        PLAY_SOUND        {"sound_id": str}
        SPEAK_TEXT        {"text": str, "voice": str (optional)}
        START_LISTENER    {"listener_id": str}
        STOP_LISTENER     {"listener_id": str}
    """

    kind: ActionKind
    payload: dict[str, Any] = field(default_factory=dict)
    action_id: str = field(default_factory=_new_id)
    issued_by: Optional[str] = None  # role slug, e.g. "ea_orchestrator"
    target_node_id: Optional[str] = None
    issued_at: str = field(default_factory=_utcnow)
    status: ActionStatus = ActionStatus.PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "kind": self.kind.value,
            "payload": self.payload,
            "issued_by": self.issued_by,
            "target_node_id": self.target_node_id,
            "issued_at": self.issued_at,
            "status": self.status.value,
        }


@dataclass
class ActionResult:
    """Station Daemon → EOS response for a dispatched SafeAction."""

    action_id: str
    status: ActionStatus
    detail: Optional[str] = None
    returned_at: str = field(default_factory=_utcnow)
    data: dict[str, Any] = field(default_factory=dict)
