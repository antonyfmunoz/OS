"""Action object — the canonical unit of control in EOS.

Every meaningful thing an agent wants to do is wrapped as an Action and
passed through the Control Plane (propose → validate → approve → execute → log).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


RiskLevel = str  # "low" | "medium" | "high"

ALLOWED_ACTION_TYPES: tuple[str, ...] = (
    "run_script",
    "shell_command",
    "write_file",
    "call_api",
    "compose_action",
)


@dataclass
class Action:
    """Canonical action record.

    Fields are flat + JSON-serialisable so the whole lifecycle can be logged
    as one record without custom encoders.
    """

    type: str
    description: str
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    risk_level: RiskLevel = "low"
    source_agent: str = "unknown"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # Lifecycle state — mutated as the action moves through the pipeline.
    status: str = "proposed"  # proposed|validated|approved|executed|failed|rejected
    validation: dict[str, Any] = field(default_factory=dict)
    approval: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    # Optional idempotency key (Phase 4). When set, run_action consults
    # the idempotency sentinel store before proposing. Backwards-compat:
    # `load_deferred` filters unknown keys, so pre-Phase-4 files load
    # with the default of None, and post-Phase-4 files load on old code
    # with the field silently dropped.
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def propose_action(
    type: str,
    description: str,
    *,
    inputs: dict[str, Any] | None = None,
    expected_output: str = "",
    risk_level: RiskLevel = "low",
    source_agent: str = "unknown",
    idempotency_key: str | None = None,
) -> Action:
    """Build an Action object in the `proposed` state.

    This does not log anything by itself — the Control Plane logs on
    every lifecycle transition. Splitting construction from logging keeps
    the Action pure and testable.
    """
    return Action(
        type=type,
        description=description,
        inputs=dict(inputs or {}),
        expected_output=expected_output,
        risk_level=risk_level,
        source_agent=source_agent,
        idempotency_key=idempotency_key,
    )
