"""Control Plane — the public entry point for the EOS Action System.

Lifecycle:
    propose → validate → approve → execute → log

Every transition is logged to the execution log. Callers get back the
fully-populated Action object so they can inspect status and results.

Deferred actions (medium/high risk without explicit approval) are
persisted to /opt/OS/logs/deferred/ and announced via the notifier
stack so they can be resumed later with `resume_action(action_id)`.
"""

from __future__ import annotations

from typing import Any

from .actions import Action, propose_action
from .validator import validate_action, approve_action
from .executor import execute_action
from .logging import log_execution, log_decision
from .tme import query_relevant_skills
from .deferred import save_deferred, load_deferred, delete_deferred, list_deferred
from .notifier import Notifier, default_notifier
from .policy import resolve_effective_risk


def _execute_approved(action: Action, *, consult_tme: bool) -> Action:
    """Run an already-approved action through execute + log."""
    if consult_tme:
        action.result.setdefault(
            "tme_consult", query_relevant_skills(action.description)
        )
    execute_action(action)
    log_execution(action)  # executed or failed
    return action


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
    notifier: Notifier | None = None,
    business_action_type: str | None = None,
) -> Action:
    """Push an action through the full Control Plane lifecycle.

    Returns the Action object with final state in `.status`, `.validation`,
    `.approval`, and `.result`. Every transition is persisted to
    /opt/OS/logs/execution/.

    If the action is deferred (medium/high risk, no explicit approval),
    it is also persisted to /opt/OS/logs/deferred/ and announced through
    the notifier stack.
    """
    # Policy bridge: if this runtime action also carries business-layer
    # semantics, upgrade the risk to the stricter of the two. Never
    # downgrades — a low-declared action with a business type mapped to
    # HIGH becomes high.
    effective_risk = resolve_effective_risk(risk_level, business_action_type)
    action = propose_action(
        type=type,
        description=description,
        inputs=inputs,
        expected_output=expected_output,
        risk_level=effective_risk,
        source_agent=source_agent,
    )
    if business_action_type:
        action.validation.setdefault("business_action_type", business_action_type)
        action.validation.setdefault("declared_risk", risk_level)
        action.validation.setdefault("effective_risk", effective_risk)
    log_execution(action)  # proposed

    validate_action(action)
    log_execution(action)  # validated or rejected
    if action.status == "rejected":
        return action

    approve_action(action, explicit_approval=explicit_approval)
    log_execution(action)  # approved or awaiting approval

    if action.status == "validated":
        # Deferred: persist so it can be resumed, and notify.
        deferred_path = save_deferred(action)
        action.result.setdefault("deferred_path", deferred_path)
        notif = notifier or default_notifier()
        action.result.setdefault("notification", notif.notify(action))
        log_execution(action)  # deferred (persisted + notified)
        return action

    if action.status != "approved":
        return action

    return _execute_approved(action, consult_tme=consult_tme)


def resume_action(
    action_id: str,
    *,
    consult_tme: bool = False,
) -> Action:
    """Approve and execute a previously-deferred action by id.

    Loads the persisted action, grants explicit approval, runs the
    executor, logs the full transition trail, and deletes the deferred
    file on any terminal state (executed or failed). If the action
    cannot be found, raises FileNotFoundError.
    """
    action = load_deferred(action_id)
    log_decision(
        context=f"resume_action({action_id})",
        options_considered=["ignore deferred", "approve + execute", "reject"],
        chosen_option="approve + execute",
        reasoning="Operator invoked resume_action; explicit approval granted.",
        related_action_id=action.id,
        source_agent=action.source_agent,
    )
    approve_action(action, explicit_approval=True)
    log_execution(action)  # approved
    if action.status != "approved":
        # Shouldn't happen for a previously-validated action, but log it.
        return action
    _execute_approved(action, consult_tme=consult_tme)
    # Terminal — remove from the deferred queue regardless of success/failure.
    delete_deferred(action_id)
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
    "resume_action",
    "list_deferred",
    "load_deferred",
]
