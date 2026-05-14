"""Reusable orchestrator step helpers.

The three Phase-3/4/5 `_cp.py` wrappers (morning_prep, nightly_consolidation,
weekly_review) share a near-identical shape:

    log_decision(context=<cron invocation>, ...)
    action = run_action(type="run_script", inputs={path, args, timeout}, ...)
    print(summary)
    return 0 if action.status in (executed, validated, skipped_duplicate) else 1

This module extracts that pattern so new workflows can be added with
~20 lines of declarative config instead of ~100 lines of boilerplate.
Each wrapper keeps ownership of its idempotency-key shape, which is
the one knob that legitimately differs per workflow.

Also exposes two ActionStep factories for use inside a Pipeline:

    - script_step(...)   → ActionStep that invokes a shell script
    - api_step(...)      → ActionStep for call_api actions

These make pipeline composition (Phase 4 of the orchestrator build)
read closer to declarative config than boilerplate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from control_plane.actions.control_plane import log_decision, run_action

from .pipeline import ActionStep


# ---------------------------------------------------------------------------
# run_script workflow helper
# ---------------------------------------------------------------------------


@dataclass
class ScriptWorkflowSpec:
    """Declarative shape of a cron-invoked run_script workflow.

    `idempotency_key` is a fully-formed string (not a template), so
    callers can compute per-day or per-week keys with whatever logic
    they need. `description_suffix` is appended to the base description
    when a dry-run or similar variant is active.
    """

    name: str
    script_path: str
    description: str
    expected_output: str
    idempotency_key: str | None
    idempotency_ttl_seconds: int
    risk_level: str = "medium"
    timeout: int = 1800
    script_args: list[str] = field(default_factory=list)
    source_agent: str = "cron"
    reasoning: str = ""


def run_script_workflow(
    spec: ScriptWorkflowSpec,
    *,
    approve: bool,
    extra_decision_context: str | None = None,
) -> int:
    """Run a declarative run_script workflow through the Control Plane.

    Returns the exit code the `_cp.py` wrapper should return:
      - 0 on executed, validated (deferred), or skipped_duplicate
      - 1 on any other status

    Prints a JSON summary line on stdout so cron logs stay tail-able.
    """
    log_decision(
        context=extra_decision_context or f"scheduled invocation of {spec.name}",
        options_considered=[
            f"bash {spec.script_path} direct",
            "python wrapper via Control Plane",
        ],
        chosen_option="python wrapper via Control Plane",
        reasoning=spec.reasoning
        or (
            f"Route {spec.name} through the Control Plane so the "
            f"ritual has a full lifecycle record and can be deferred "
            f"when the operator has not pre-approved."
        ),
        source_agent=spec.source_agent,
    )

    action = run_action(
        type="run_script",
        description=spec.description,
        inputs={
            "path": spec.script_path,
            "args": list(spec.script_args),
            "timeout": spec.timeout,
        },
        risk_level=spec.risk_level,
        source_agent=spec.source_agent,
        explicit_approval=approve,
        expected_output=spec.expected_output,
        idempotency_key=spec.idempotency_key,
        idempotency_ttl_seconds=spec.idempotency_ttl_seconds,
    )

    print(
        json.dumps(
            {
                "id": action.id,
                "status": action.status,
                "idempotency_key": spec.idempotency_key,
                "validation": action.validation,
                "approval": action.approval,
                "result": {
                    k: v
                    for k, v in (action.result or {}).items()
                    if k
                    in (
                        "ok",
                        "returncode",
                        "stderr",
                        "deferred_path",
                        "notification",
                        "skipped",
                        "reason",
                        "original_action_id",
                    )
                },
            },
            indent=2,
            default=str,
        )
    )

    if action.status in ("executed", "validated", "skipped_duplicate"):
        return 0
    return 1


# ---------------------------------------------------------------------------
# Pipeline step factories
# ---------------------------------------------------------------------------


def script_step(
    *,
    name: str,
    script_path: str,
    description: str,
    expected_output: str = "",
    risk_level: str = "medium",
    timeout: int = 1800,
    script_args: list[str] | None = None,
    idempotency_key: str | None = None,
    idempotency_ttl_seconds: int | None = None,
    source_agent: str = "orchestrator",
) -> ActionStep:
    """Build an ActionStep that runs a shell script via run_action."""
    return ActionStep(
        name=name,
        type="run_script",
        description=description,
        inputs={
            "path": script_path,
            "args": list(script_args or []),
            "timeout": timeout,
        },
        expected_output=expected_output,
        risk_level=risk_level,
        source_agent=source_agent,
        idempotency_key=idempotency_key,
        idempotency_ttl_seconds=idempotency_ttl_seconds,
    )


def api_step(
    *,
    name: str,
    description: str,
    inputs: dict[str, Any],
    expected_output: str = "",
    risk_level: str = "low",
    idempotency_key: str | None = None,
    idempotency_ttl_seconds: int | None = None,
    source_agent: str = "orchestrator",
) -> ActionStep:
    """Build an ActionStep for a call_api action via run_action."""
    return ActionStep(
        name=name,
        type="call_api",
        description=description,
        inputs=dict(inputs),
        expected_output=expected_output,
        risk_level=risk_level,
        source_agent=source_agent,
        idempotency_key=idempotency_key,
        idempotency_ttl_seconds=idempotency_ttl_seconds,
    )


__all__ = [
    "ScriptWorkflowSpec",
    "run_script_workflow",
    "script_step",
    "api_step",
]
