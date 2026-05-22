"""Node-side governance — validates capability requests against local policy."""

from __future__ import annotations

import logging
from typing import Any

from daemon.umh_node.config import CapabilityConfig

logger = logging.getLogger(__name__)

RISK_ORDER = [
    "READ_ONLY",
    "SAFE_WRITE",
    "REVERSIBLE_WRITE",
    "IRREVERSIBLE_WRITE",
    "EXTERNAL_COMMUNICATION",
    "FINANCIAL",
    "SECURITY_SENSITIVE",
    "PHYSICAL_WORLD",
]


def _risk_level(risk_class: str) -> int:
    upper = risk_class.upper()
    if upper in RISK_ORDER:
        return RISK_ORDER.index(upper)
    return len(RISK_ORDER)


def validate_request(
    capability_name: str,
    params: dict[str, Any],
    risk_class: str,
    cap_config: CapabilityConfig | None,
) -> tuple[bool, str]:
    """Validate a capability request against the node's local policy.

    Returns (allowed, reason).
    """
    if cap_config is None:
        return False, f"capability '{capability_name}' not configured on this node"

    if not cap_config.enabled:
        return False, f"capability '{capability_name}' is disabled"

    if _risk_level(risk_class) > _risk_level(cap_config.max_risk_class):
        return False, (
            f"risk class {risk_class} exceeds node cap {cap_config.max_risk_class} "
            f"for {capability_name}"
        )

    if capability_name == "shell" and cap_config.allowed_commands:
        command = params.get("command", "")
        cmd_base = command.split()[0] if command.split() else ""
        if cmd_base not in cap_config.allowed_commands:
            return False, f"command '{cmd_base}' not in allowed_commands for shell"

    if capability_name == "filesystem" and cap_config.allowed_paths:
        path = params.get("path", "")
        if not any(path.startswith(ap) for ap in cap_config.allowed_paths):
            return False, f"path '{path}' not under any allowed_paths for filesystem"

    return True, "approved"
