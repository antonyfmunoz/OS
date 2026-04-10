"""
Control Layer v2 — Remote Identity (lightweight).

Deterministic node identity + scope matching for the remote executor daemon.
NO crypto. NO networking. Just env/hostname lookups and a string compare.

Design rules (non-negotiable):
    * Pure data + tiny helpers. No I/O beyond os.environ / socket.gethostname.
    * Never raises — always returns a usable value.
    * Additive only. Does not touch the hot path.
"""

from __future__ import annotations

import os
import socket
from typing import Any

from eos_ai.substrate import control_commands as cc

LAYER_NAME = "remote_identity"
LAYER_VERSION = "v2"


def get_node_id() -> str:
    """
    Resolve this machine's substrate node id.

    Order:
        1. EOS_NODE_ID env var (explicit)
        2. socket.gethostname()
        3. "local" (last-resort default — matches v1 default node_id)
    """
    try:
        env = os.environ.get("EOS_NODE_ID")
        if env and env.strip():
            return env.strip()
    except Exception:  # noqa: BLE001
        pass
    try:
        host = socket.gethostname()
        if host and host.strip():
            return host.strip()
    except Exception:  # noqa: BLE001
        pass
    return "local"


def get_node_token() -> str:
    """
    Return the node's shared token (env EOS_NODE_TOKEN). Empty string if unset.
    Reserved for future authenticated dispatch — currently informational only.
    """
    try:
        return (os.environ.get("EOS_NODE_TOKEN") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def validate_command_scope(command: Any, node_id: str) -> bool:
    """
    Confirm a ControlCommand is addressed to this node.

    Accepts a ControlCommand or any object with a `.node_id` attribute, or a
    dict with a "node_id" key. Returns False on any malformed input — never
    raises.
    """
    if not node_id:
        return False
    try:
        if isinstance(command, cc.ControlCommand):
            return str(command.node_id) == str(node_id)
        if isinstance(command, dict):
            return str(command.get("node_id") or "") == str(node_id)
        cmd_node = getattr(command, "node_id", None)
        if cmd_node is None:
            return False
        return str(cmd_node) == str(node_id)
    except Exception:  # noqa: BLE001
        return False
