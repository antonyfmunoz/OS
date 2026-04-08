"""Control Plane — the public entry point for the EOS Action System.

Lifecycle:
    propose → validate → approve → execute → log

Every transition is logged to the execution log. Callers get back the
fully-populated Action object so they can inspect status and results.

Deferred actions (medium/high risk without explicit approval) are
persisted to /opt/OS/logs/deferred/ and announced via the notifier
stack so they can be resumed later with `resume_action(action_id)`.

Phase 4 adds an optional `idempotency_key` kwarg. When set, the
Control Plane consults `core.action_system.idempotency` BEFORE
proposing. Duplicate calls within the TTL return a synthetic Action
with status="skipped_duplicate" pointing at the original action_id.
Failed runs and dropped-deferred runs are allowed to retry.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from . import idempotency
from .actions import Action, propose_action
from .deferred import DEFERRED_DIR, delete_deferred, list_deferred, load_deferred, save_deferred
from .executor import execute_action
from .logging import log_decision, log_execution
from .notifier import Notifier, default_notifier
from .policy import resolve_effective_risk
from .tme import query_relevant_skills
from .validator import approve_action, validate_action


def _execute_approved(action: Action, *, consult_tme: bool) -> Action:
    """Run an already-approved action through execute + log."""
    if consult_tme:
        action.result.setdefault(
            "tme_consult", query_relevant_skills(action.description)
        )
    execute_action(action)
    log_execution(action)  # executed or failed
    return action


def _skipped_duplicate(
    *,
    original_action_id: str,
    reason: str,
    ok: bool,
    idempotency_key: str,
    extra: dict[str, Any] | None = None,
) -> Action:
    """Build a synthetic Action representing an idempotency hit.

    No log write, no queue write — this is a pure return value meant
    to let the caller see what happened without creating duplicate
    lifecycle trail.
    """
    act = Action(
        type="idempotency_skip",
        description=f"duplicate suppressed: {reason}",
        status="skipped_duplicate",
        idempotency_key=idempotency_key,
    )
    act.result = {
        "ok": ok,
        "skipped": True,
        "reason": reason,
        "original_action_id": original_action_id,
    }
    if extra:
        act.result.update(extra)
    return act


def _deferred_file_exists(action_id: str) -> bool:
    return os.path.isfile(os.path.join(DEFERRED_DIR, f"{action_id}.json"))


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
    idempotency_key: str | None = None,
    idempotency_ttl_seconds: int | None = None,
) -> Action:
    """Push an action through the full Control Plane lifecycle.

    Returns the Action object with final state in `.status`, `.validation`,
    `.approval`, and `.result`. Every transition is persisted to
    /opt/OS/logs/execution/.

    If `idempotency_key` is set, a sentinel file is consulted before any
    propose/validate/execute work is done. See
    `core/action_system/idempotency.py` for the full state machine.
    """
    # ---------------- Idempotency pre-flight ----------------
    if idempotency_key is not None:
        ttl = int(idempotency_ttl_seconds or 0)
        existing = idempotency.read(idempotency_key)
        if existing is not None and not existing.is_expired():
            status = existing.status
            if status == "in_flight":
                return _skipped_duplicate(
                    original_action_id=existing.action_id,
                    reason="idempotency conflict: already in-flight",
                    ok=False,
                    idempotency_key=idempotency_key,
                    extra={"conflict_action_id": existing.action_id},
                )
            if status == "executed":
                return _skipped_duplicate(
                    original_action_id=existing.action_id,
                    reason="already executed this key",
                    ok=True,
                    idempotency_key=idempotency_key,
                )
            if status == "deferred":
                # If the associated deferred file is still on disk, the
                # operator still owes a decision on it — suppress the
                # retry. If the file is gone (dropped without resume),
                # treat the slot as free and overwrite the sentinel.
                if _deferred_file_exists(existing.action_id):
                    return _skipped_duplicate(
                        original_action_id=existing.action_id,
                        reason="already deferred for this key; awaiting operator",
                        ok=False,
                        idempotency_key=idempotency_key,
                        extra={"deferred_action_id": existing.action_id},
                    )
                # fall through — force_claim below
            # status == "failed" → fall through and retry
        # Claim (or overwrite) the slot. We use force_claim here because
        # we've already decided above that overwriting is correct.
        # For a fully-missing sentinel, force_claim is equivalent to a
        # first write.
        new_action_id = str(uuid.uuid4())
        idempotency.force_claim(
            idempotency_key,
            action_id=new_action_id,
            ttl_seconds=ttl,
        )
    else:
        new_action_id = None  # noqa — unused when idempotency is off

    # ---------------- Normal lifecycle ----------------
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
        idempotency_key=idempotency_key,
    )
    # When idempotency is in play, we pre-allocated the id so the
    # sentinel and action agree. Otherwise Action generated its own.
    if new_action_id is not None:
        action.id = new_action_id

    if business_action_type:
        action.validation.setdefault("business_action_type", business_action_type)
        action.validation.setdefault("declared_risk", risk_level)
        action.validation.setdefault("effective_risk", effective_risk)
    log_execution(action)  # proposed

    validate_action(action)
    log_execution(action)  # validated or rejected
    if action.status == "rejected":
        # Rejected actions are caller bugs; do NOT keep the sentinel.
        # Clearing lets the next call reproduce the error for debugging.
        if idempotency_key is not None:
            idempotency.clear(idempotency_key)
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
        if idempotency_key is not None:
            idempotency.complete(idempotency_key, "deferred")
        return action

    if action.status != "approved":
        # Critical blocked or other non-approval. Do not hold the slot.
        if idempotency_key is not None:
            idempotency.clear(idempotency_key)
        return action

    _execute_approved(action, consult_tme=consult_tme)
    if idempotency_key is not None:
        idempotency.complete(
            idempotency_key,
            "executed" if action.status == "executed" else "failed",
        )
    return action


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
    # Flip the idempotency sentinel if this action was keyed.
    if action.idempotency_key:
        idempotency.complete(
            action.idempotency_key,
            "executed" if action.status == "executed" else "failed",
        )
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
