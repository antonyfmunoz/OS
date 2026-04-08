"""Control Plane — the public entry point for the EOS Action System.

Lifecycle:
    propose → validate → approve → execute → log

Every transition is logged to the execution log. Callers get back the
fully-populated Action object so they can inspect status and results.
"""

from __future__ import annotations

from typing import Any

from .actions import Action, propose_action
from .validator import validate_action, approve_action
from .executor import execute_action
from .logging import log_execution, log_decision
from .tme import query_relevant_skills


def run_action(
    type: str,
    description: str,
    *,
    inputs: dict[str, Any] | None = None,
    expected_output: str = "",
    risk_level: str = "low",
    source_agent: str = "unknown",
    explicit_approval: bool = False,
    consult_tme: bool = False,
) -> Action:
    """Push an action through the full Control Plane lifecycle.

    Returns the Action object with final state in `.status`, `.validation`,
    `.approval`, and `.result`. Every transition is persisted to
    /opt/OS/logs/execution/.
    """
    action = propose_action(
        type=type,
        description=description,
        inputs=inputs,
        expected_output=expected_output,
        risk_level=risk_level,
        source_agent=source_agent,
    )
    log_execution(action)  # proposed

    validate_action(action)
    log_execution(action)  # validated or rejected
    if action.status == "rejected":
        return action

    approve_action(action, explicit_approval=explicit_approval)
    log_execution(action)  # approved or awaiting approval
    if action.status != "approved":
        return action

    if consult_tme:
        tme_result = query_relevant_skills(action.description)
        action.result.setdefault("tme_consult", tme_result)

    execute_action(action)
    log_execution(action)  # executed or failed
    return action


__all__ = [
    "Action",
    "propose_action",
    "validate_action",
    "approve_action",
    "execute_action",
    "log_execution",
    "log_decision",
    "query_relevant_skills",
    "run_action",
]
