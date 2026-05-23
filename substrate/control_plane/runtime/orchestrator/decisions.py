"""Decision helpers for signal handler workflows.

These are tiny, deterministic predicates that inspect an action dict
(as it appears in an execution log record or a signal payload) and
answer one question each:

  - should_retry(action)    → is it safe to re-run this?
  - should_escalate(action) → does a human need to see this?
  - should_ignore(action)   → is this noise we can silently drop?

No ML. No heuristics beyond a handful of hand-written rules. The
rules intentionally mirror the ones in `core.orchestrator.loop` so
that a handler workflow decides the same way the loop would if it
had to decide in-process.

The "retry count" is derived from today's decision log: every time
the loop (or a handler) logs a retry decision against an action id,
that counts as one retry. Keeping the count in the log instead of a
separate counter means there's exactly one source of truth.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from substrate.control_plane.actions.logging import DECISION_LOG_DIR

# Action types that are safe to re-run blindly. Matches LoopConfig
# defaults — if you change one, change both.
RETRY_ELIGIBLE_TYPES: tuple[str, ...] = ("shell_command", "call_api")

# Risk levels that always go straight to escalation, no auto-retry.
ALWAYS_ESCALATE_RISK: tuple[str, ...] = ("high",)

# Max automatic retries per action id per UTC day.
MAX_RETRIES_PER_DAY = 1


# ---------------------------------------------------------------------------
# Retry-count derivation
# ---------------------------------------------------------------------------


def _today_decision_log_path() -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(DECISION_LOG_DIR, f"{day}-decisions.jsonl")


def retry_count_today(action_id: str) -> int:
    """How many retry decisions have been logged against this action today.

    Counts any decision whose `context` is `orchestrator.loop.retry`
    OR `orchestrator.handler.retry` and whose `related_action_id`
    matches. Returns 0 if the log is missing.
    """
    if not action_id:
        return 0
    path = _today_decision_log_path()
    if not os.path.isfile(path):
        return 0
    count = 0
    try:
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("related_action_id") != action_id:
                    continue
                ctx = rec.get("context", "")
                if ctx in (
                    "orchestrator.loop.retry",
                    "orchestrator.handler.retry",
                ):
                    count += 1
    except OSError:
        return 0
    return count


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def _action_type(action: dict[str, Any]) -> str:
    return str(action.get("type") or "")


def _risk(action: dict[str, Any]) -> str:
    return str(action.get("risk_level") or "low").lower()


def _has_idempotency(action: dict[str, Any]) -> bool:
    return bool(action.get("idempotency_key"))


def should_retry(action: dict[str, Any]) -> bool:
    """True if this failed action can be safely re-run automatically.

    Rules (all must hold):
      1. Action type is in RETRY_ELIGIBLE_TYPES.
      2. Action has an idempotency key (so a retry is a no-op if the
         previous run actually succeeded mid-failure).
      3. Risk level is not in ALWAYS_ESCALATE_RISK.
      4. Fewer than MAX_RETRIES_PER_DAY retry decisions logged today
         for this action id.
    """
    if _action_type(action) not in RETRY_ELIGIBLE_TYPES:
        return False
    if not _has_idempotency(action):
        return False
    if _risk(action) in ALWAYS_ESCALATE_RISK:
        return False
    action_id = str(action.get("id") or "")
    if retry_count_today(action_id) >= MAX_RETRIES_PER_DAY:
        return False
    return True


def should_escalate(action: dict[str, Any]) -> bool:
    """True if this failure should surface to a human.

    An action escalates when it is NOT retry-eligible — either because
    its type is destructive (run_script, write_file), it has no
    idempotency guarantee, it is high-risk, or it has already burned
    its automatic retry budget for the day. Escalation is the safe
    default when in doubt.
    """
    return not should_retry(action)


def should_ignore(action: dict[str, Any]) -> bool:
    """True if this action can be silently dropped without human attention.

    Current rule: the only thing we ignore is an idempotency_skip
    synthetic action whose result already reports ok=True. Everything
    else either retries or escalates.
    """
    if _action_type(action) == "idempotency_skip":
        result = action.get("result") or {}
        return bool(result.get("ok"))
    return False


__all__ = [
    "RETRY_ELIGIBLE_TYPES",
    "ALWAYS_ESCALATE_RISK",
    "MAX_RETRIES_PER_DAY",
    "retry_count_today",
    "should_retry",
    "should_escalate",
    "should_ignore",
]
