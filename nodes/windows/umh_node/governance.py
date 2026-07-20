"""Node-side governance — validates capability requests against local policy."""

from __future__ import annotations

import logging
from typing import Any

from nodes.windows.umh_node.config import CapabilityConfig

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


# The one recognized dotted operation. The VPS runtime emits
# "<adapter>.execute" (substrate/organism/runtime_adapters.py); any other
# dotted operation is unknown and DENIED — suffixes are never stripped
# permissively (defense-in-depth for direct callers that skip the node
# client's adapter-key normalization).
_KNOWN_OPERATIONS = frozenset({"execute"})


def normalize_capability(capability_name: str) -> tuple[str, str]:
    """Split ``adapter[.operation]`` → (base, error). error is "" when legal.

    ``shell`` → ("shell", ""); ``shell.execute`` → ("shell", "");
    ``shell.rm`` → ("shell", "unknown capability operation 'rm' …").
    Policy (allowed_commands / allowed_paths / risk caps) always binds to the
    BASE adapter — a dotted operation never loosens it.
    """
    base, dot, operation = capability_name.partition(".")
    if dot and operation not in _KNOWN_OPERATIONS:
        return base, (
            f"unknown capability operation '{operation}' for '{base}' — "
            f"only {sorted(_KNOWN_OPERATIONS)} recognized"
        )
    return base, ""


def validate_request(
    capability_name: str,
    params: dict[str, Any],
    risk_class: str,
    cap_config: CapabilityConfig | None,
) -> tuple[bool, str]:
    """Validate a capability request against the node's local policy.

    Accepts the base adapter name or the canonical dotted form
    (``shell.execute``); the base-adapter policy applies identically to both.
    Unknown dotted operations are denied outright. Returns (allowed, reason).
    """
    base_name, op_error = normalize_capability(capability_name)
    if op_error:
        return False, op_error

    if cap_config is None:
        return False, f"capability '{capability_name}' not configured on this node"

    if not cap_config.enabled:
        return False, f"capability '{capability_name}' is disabled"

    if _risk_level(risk_class) > _risk_level(cap_config.max_risk_class):
        return False, (
            f"risk class {risk_class} exceeds node cap {cap_config.max_risk_class} "
            f"for {capability_name}"
        )

    if base_name == "shell" and cap_config.allowed_commands:
        command = params.get("command", "")
        cmd_base = command.split()[0] if command.split() else ""
        if cmd_base not in cap_config.allowed_commands:
            return False, f"command '{cmd_base}' not in allowed_commands for shell"

    if base_name == "filesystem" and cap_config.allowed_paths:
        path = params.get("path", "")
        if not any(path.startswith(ap) for ap in cap_config.allowed_paths):
            return False, f"path '{path}' not under any allowed_paths for filesystem"

    return True, "approved"
