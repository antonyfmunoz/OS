"""
Runtime mode — explicit operator interaction modes.

Defines three modes that control how the system communicates with the operator
through Discord (or any transport):

  ACTIVE     — full interaction: summaries, approvals, artifacts, interactive responses
  PASSIVE    — important notifications and completion summaries only
  AUTONOMOUS — minimize interruptions, batch noncritical chatter, still record artifacts

Mode is readable by the delivery layer (operator_delivery.py) and stored in the
runtime session (runtime_session.py).

Design rules (substrate conventions):
- Additive only. No hot-path imports.
- Deterministic. Pure functions, no LLM calls.
- No side effects. Mode is a value, not a behavior trigger.
- Backward-compatible: absent mode defaults to ACTIVE (safest).
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Any

_LOG_PREFIX = "[substrate.runtime_mode]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Mode enum ──────────────────────────────────────────────────────────────


class RuntimeMode(str, Enum):
    """Operator interaction mode.

    ACTIVE:     Send interactive responses, approvals, summaries, artifacts.
                Full bidirectional communication.
    PASSIVE:    Send only important notifications and completion summaries.
                Suppress routine status updates.
    AUTONOMOUS: Minimize interruptions. Batch or suppress noncritical chatter.
                Still record artifacts and state for later review.
    """

    ACTIVE = "active"
    PASSIVE = "passive"
    AUTONOMOUS = "autonomous"


# ─── Default ────────────────────────────────────────────────────────────────

DEFAULT_MODE: RuntimeMode = RuntimeMode.ACTIVE


def resolve_mode(raw: str | None) -> RuntimeMode:
    """Resolve a raw string to a RuntimeMode, defaulting to ACTIVE.

    Handles None, empty string, and invalid values gracefully.
    """
    if not raw:
        return DEFAULT_MODE
    try:
        return RuntimeMode(raw.lower().strip())
    except ValueError:
        _log(f"invalid mode {raw!r}, defaulting to ACTIVE")
        return DEFAULT_MODE


# ─── Gating predicates ──────────────────────────────────────────────────────


class DeliveryClass(str, Enum):
    """Classification of a message for mode-gating purposes.

    CRITICAL:    Always delivered (errors, approval requests, system failures).
    COMPLETION:  Task/workflow completion summaries.
    STATUS:      Routine progress updates, heartbeats.
    VERBOSE:     Detailed trace data, debug info, intermediate steps.
    """

    CRITICAL = "critical"
    COMPLETION = "completion"
    STATUS = "status"
    VERBOSE = "verbose"


# Mode → which delivery classes are allowed
_DELIVERY_POLICY: dict[RuntimeMode, frozenset[DeliveryClass]] = {
    RuntimeMode.ACTIVE: frozenset(
        {
            DeliveryClass.CRITICAL,
            DeliveryClass.COMPLETION,
            DeliveryClass.STATUS,
            DeliveryClass.VERBOSE,
        }
    ),
    RuntimeMode.PASSIVE: frozenset(
        {
            DeliveryClass.CRITICAL,
            DeliveryClass.COMPLETION,
        }
    ),
    RuntimeMode.AUTONOMOUS: frozenset(
        {
            DeliveryClass.CRITICAL,
        }
    ),
}


def should_deliver(
    mode: RuntimeMode,
    delivery_class: DeliveryClass,
) -> bool:
    """Determine if a message should be delivered given the current mode.

    Returns True if the delivery class is allowed in the given mode.
    Unknown modes default to ACTIVE (deliver everything).
    """
    allowed = _DELIVERY_POLICY.get(mode, _DELIVERY_POLICY[RuntimeMode.ACTIVE])
    return delivery_class in allowed


def classify_delivery(
    *,
    is_failure: bool = False,
    is_approval: bool = False,
    is_completion: bool = False,
    is_status: bool = False,
) -> DeliveryClass:
    """Classify a message into a DeliveryClass based on its characteristics.

    Priority: critical (failure/approval) > completion > status > verbose.
    """
    if is_failure or is_approval:
        return DeliveryClass.CRITICAL
    if is_completion:
        return DeliveryClass.COMPLETION
    if is_status:
        return DeliveryClass.STATUS
    return DeliveryClass.VERBOSE


def mode_to_dict(mode: RuntimeMode) -> dict[str, Any]:
    """Serialize mode + policy to a dict for diagnostics."""
    allowed = _DELIVERY_POLICY.get(mode, _DELIVERY_POLICY[RuntimeMode.ACTIVE])
    return {
        "mode": mode.value,
        "allowed_classes": sorted(c.value for c in allowed),
        "is_default": mode == DEFAULT_MODE,
    }


__all__ = [
    "RuntimeMode",
    "DEFAULT_MODE",
    "resolve_mode",
    "DeliveryClass",
    "should_deliver",
    "classify_delivery",
    "mode_to_dict",
]
