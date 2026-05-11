"""
Control Layer v1 — Command Envelope.

Defines ControlCommand: the deterministic, JSON-serializable unit of work
that flows VPS (brain) → Control Bridge → Local Agent (hands).

Design rules (non-negotiable):
    * Pure data + tiny helpers. No I/O. No execution. No side effects.
    * Deterministic: same inputs → same envelope (modulo command_id/created_at).
    * Bounded: payload is shallow, action is from a closed set.
    * Safe-degrading: validation never raises; returns (ok, reason).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

LAYER_NAME = "control_commands"
LAYER_VERSION = "v1"

# Closed set of allowed actions. The local executor enforces this again.
ALLOWED_ACTIONS = ("run_shell", "write_file", "run_python")

# Bounds for payload sanity (the executor enforces stricter rules per-action).
MAX_PAYLOAD_KEYS = 16
MAX_STRING_LEN = 8_192


@dataclass
class ControlCommand:
    """Single explicit operator-issued command."""

    action: str
    payload: dict[str, Any]
    issued_by: str
    node_id: str = "local"
    target: str = "local"
    command_id: str = field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:12]}")
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ControlCommand":
        # Tolerant constructor — only known fields, defaults for the rest.
        return cls(
            action=str(data.get("action") or ""),
            payload=dict(data.get("payload") or {}),
            issued_by=str(data.get("issued_by") or "unknown"),
            node_id=str(data.get("node_id") or "local"),
            target=str(data.get("target") or "local"),
            command_id=str(data.get("command_id") or f"cmd_{uuid.uuid4().hex[:12]}"),
            created_at=float(data.get("created_at") or time.time()),
        )


def make_command(
    action: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    issued_by: str = "operator",
    node_id: str = "local",
) -> ControlCommand:
    """Construct a command with sane defaults."""
    return ControlCommand(
        action=str(action or ""),
        payload=dict(payload or {}),
        issued_by=str(issued_by or "operator"),
        node_id=str(node_id or "local"),
        target="local",
    )


def validate(cmd: ControlCommand) -> tuple[bool, str]:
    """
    Shallow envelope validation. Returns (ok, reason).
    Never raises. Action-specific rules live in the executor.
    """
    try:
        if not isinstance(cmd, ControlCommand):
            return False, "not_a_control_command"
        if cmd.action not in ALLOWED_ACTIONS:
            return False, f"action_not_allowed:{cmd.action}"
        if not isinstance(cmd.payload, dict):
            return False, "payload_not_dict"
        if len(cmd.payload) > MAX_PAYLOAD_KEYS:
            return False, "payload_too_large"
        for k, v in cmd.payload.items():
            if not isinstance(k, str):
                return False, "payload_key_not_str"
            if isinstance(v, str) and len(v) > MAX_STRING_LEN:
                return False, "payload_string_too_long"
        if cmd.target != "local":
            return False, f"target_not_supported:{cmd.target}"
        if not cmd.command_id:
            return False, "missing_command_id"
        return True, "ok"
    except Exception:  # noqa: BLE001
        return False, "validation_exception"
