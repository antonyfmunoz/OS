"""Signal handler workflows.

Each handler is a plain callable `(context: dict) -> dict` that the
orchestrator can run via `run_workflow()`. The context passed by the
loop has shape:

    {
      "signal": "<signal_name>",
      "payload": { ... emission payload ... },
      "emission_id": "<uuid>",
    }

Handlers follow three rules:

1. NEVER execute side effects directly. Any state change must go
   through `run_action()`.
2. NEVER re-emit the signal they handle. The loop/emitter is the
   observer; handlers are the reactor. Circular signals are bugs.
3. Always return a dict with an "ok" key so the orchestrator and
   loop reports can distinguish success from failure uniformly.

Three handlers ship in Phase 6:

- handle_deferred_stale        — log + file-notify operator about a
                                 stale deferred action. No approval.
- handle_action_failed         — record escalation and file-notify.
                                 No retries here — retries belong to
                                 the retry handler.
- handle_action_retry_requested — if the action still passes
                                 `should_retry()`, re-invoke it via
                                 `run_action()` with a retry-scoped
                                 idempotency key. Otherwise escalate.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from core.action_system.control_plane import log_decision, run_action
from core.action_system.notifier import NOTIFICATION_QUEUE

from .decisions import should_escalate, should_ignore, should_retry


# ---------------------------------------------------------------------------
# Operator notification (file-only — decoupled from any live transport)
# ---------------------------------------------------------------------------


def _append_operator_notice(
    *,
    kind: str,
    action: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a structured notice to the shared deferred notification queue.

    Reusing `/opt/OS/logs/deferred/notifications.jsonl` means any
    existing Discord/Telegram drainer picks these notices up without
    new wiring. The `kind` field distinguishes operator alerts from
    plain deferred-approval requests.
    """
    record = {
        "notified_at": datetime.now(timezone.utc).isoformat(),
        "channel": "file",
        "kind": kind,
        "action_id": action.get("id"),
        "type": action.get("type"),
        "description": action.get("description"),
        "risk_level": action.get("risk_level"),
        "source_agent": action.get("source_agent"),
    }
    if extra:
        record.update(extra)
    os.makedirs(os.path.dirname(NOTIFICATION_QUEUE), exist_ok=True)
    with open(NOTIFICATION_QUEUE, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return {"ok": True, "kind": kind, "path": NOTIFICATION_QUEUE}


def _action_from_context(context: dict[str, Any]) -> dict[str, Any]:
    payload = context.get("payload") or {}
    return dict(payload.get("action") or {})


# ---------------------------------------------------------------------------
# deferred_stale
# ---------------------------------------------------------------------------


def handle_deferred_stale(context: dict[str, Any]) -> dict[str, Any]:
    """React to a stale deferred action.

    The loop emits this when a deferred action has been waiting longer
    than `LoopConfig.stale_deferred_seconds`. The handler does three
    things:

      1. Logs a decision so the audit trail shows the handler ran.
      2. Appends an operator notice to the shared notification queue.
      3. Returns a dict summarizing what it did.

    The handler NEVER approves the action. Stale does not mean safe.
    """
    payload = context.get("payload") or {}
    action = _action_from_context(context)
    action_id = action.get("id") or payload.get("action_id")
    age_seconds = payload.get("age_seconds")

    log_decision(
        context="orchestrator.handler.deferred_stale",
        options_considered=["notify operator", "ignore"],
        chosen_option="notify operator",
        reasoning=(
            f"Deferred action {action_id} has been waiting "
            f"{age_seconds}s. Surfacing for operator review; no "
            f"approval granted by handler."
        ),
        related_action_id=action_id,
        source_agent="orchestrator.handler",
    )
    notice = _append_operator_notice(
        kind="deferred_stale",
        action=action,
        extra={
            "age_seconds": age_seconds,
            "approve_cmd": (
                f"python3 /opt/OS/scripts/deferred.py approve {action_id}"
                if action_id
                else None
            ),
        },
    )
    return {
        "ok": True,
        "handler": "deferred_stale",
        "action_id": action_id,
        "age_seconds": age_seconds,
        "notice": notice,
    }


# ---------------------------------------------------------------------------
# action_failed
# ---------------------------------------------------------------------------


def handle_action_failed(context: dict[str, Any]) -> dict[str, Any]:
    """React to a failed action that the loop already decided to escalate.

    The loop only emits `action_failed` for actions it judged
    NOT retry-eligible. The handler double-checks with
    `should_ignore` / `should_escalate` so the rules live in exactly
    one place, then notifies the operator.
    """
    action = _action_from_context(context)
    action_id = action.get("id")

    if should_ignore(action):
        log_decision(
            context="orchestrator.handler.action_failed",
            options_considered=["ignore", "escalate"],
            chosen_option="ignore",
            reasoning=(
                f"Failed action {action_id} matches ignore rule "
                f"(type={action.get('type')})."
            ),
            related_action_id=action_id,
            source_agent="orchestrator.handler",
        )
        return {
            "ok": True,
            "handler": "action_failed",
            "action_id": action_id,
            "decision": "ignored",
        }

    # Default path: escalate. The decision log already carries the
    # loop's escalation record; we add the handler's own so the audit
    # trail reflects that a human notifier fired.
    log_decision(
        context="orchestrator.handler.action_failed",
        options_considered=["notify operator", "ignore"],
        chosen_option="notify operator",
        reasoning=(
            f"Failed action {action_id} (type={action.get('type')}, "
            f"risk={action.get('risk_level')}) is not retry-eligible. "
            f"Operator notification appended to deferred notification "
            f"queue."
        ),
        related_action_id=action_id,
        source_agent="orchestrator.handler",
    )
    notice = _append_operator_notice(
        kind="action_failed",
        action=action,
        extra={
            "stderr": (action.get("result") or {}).get("stderr"),
            "returncode": (action.get("result") or {}).get("returncode"),
        },
    )
    return {
        "ok": True,
        "handler": "action_failed",
        "action_id": action_id,
        "decision": "escalated",
        "notice": notice,
    }


# ---------------------------------------------------------------------------
# action_retry_requested
# ---------------------------------------------------------------------------


def handle_action_retry_requested(context: dict[str, Any]) -> dict[str, Any]:
    """Retry a previously-failed action via the Control Plane.

    The loop emits `action_retry_requested` only when the original
    action was retry-eligible, but the handler re-checks with
    `should_retry()` so that:

      - If the retry budget is now exhausted (because a second cycle
        saw the same failure), we escalate instead of retrying again.
      - The single source of truth for "is this retryable" stays in
        `core.orchestrator.decisions`.

    When we do retry, the key shape `retry:<original_id>:<utc_date>`
    guarantees:

      - At most one automatic retry per action id per day (the
        Control Plane's own idempotency store dedupes the second
        invocation inside the same day).
      - The retry does not collide with the original action's
        idempotency key (which is scoped to whatever the caller used,
        e.g. `morning_prep:<date>`).
    """
    action = _action_from_context(context)
    action_id = action.get("id")
    action_type = action.get("type") or ""
    inputs = dict(action.get("inputs") or {})
    risk = action.get("risk_level") or "low"
    description = action.get("description") or f"retry of {action_id}"

    if not should_retry(action):
        log_decision(
            context="orchestrator.handler.action_retry_requested",
            options_considered=["retry", "escalate"],
            chosen_option="escalate",
            reasoning=(
                f"Retry requested for action {action_id} but "
                f"should_retry() is now False (budget exhausted or "
                f"type/risk changed). Escalating."
            ),
            related_action_id=action_id,
            source_agent="orchestrator.handler",
        )
        notice = _append_operator_notice(
            kind="retry_exhausted",
            action=action,
        )
        return {
            "ok": True,
            "handler": "action_retry_requested",
            "action_id": action_id,
            "decision": "escalated",
            "notice": notice,
        }

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    retry_key = f"retry:{action_id}:{day}"

    log_decision(
        context="orchestrator.handler.retry",
        options_considered=["retry", "escalate"],
        chosen_option="retry",
        reasoning=(
            f"Retrying action {action_id} (type={action_type}) via "
            f"Control Plane with idempotency_key={retry_key!r}. "
            f"Explicit approval granted because the original action "
            f"already cleared validation."
        ),
        related_action_id=action_id,
        source_agent="orchestrator.handler",
    )

    retried = run_action(
        type=action_type,
        description=f"[retry] {description}",
        inputs=inputs,
        risk_level=risk,
        source_agent="orchestrator.handler",
        explicit_approval=True,
        idempotency_key=retry_key,
        idempotency_ttl_seconds=23 * 3600,
    )

    ok = retried.status in ("executed", "skipped_duplicate") and bool(
        (retried.result or {}).get("ok", retried.status == "executed")
    )
    return {
        "ok": ok,
        "handler": "action_retry_requested",
        "original_action_id": action_id,
        "retry_action_id": retried.id,
        "retry_status": retried.status,
        "retry_result": {
            k: v
            for k, v in (retried.result or {}).items()
            if k in ("ok", "returncode", "stderr", "skipped", "reason")
        },
    }


__all__ = [
    "handle_deferred_stale",
    "handle_action_failed",
    "handle_action_retry_requested",
]
