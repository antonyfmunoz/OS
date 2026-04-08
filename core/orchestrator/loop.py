"""Autonomous loop — deterministic orchestration cycle.

One cycle does exactly four things, in order:

  1. Drain pending signals: for each pending emission, dispatch every
     registered handler via the orchestrator, then move the emission
     file into processed/.

  2. Scan stale deferred actions: if any deferred action has been
     waiting longer than `stale_deferred_seconds`, log a decision and
     emit the `deferred_stale` signal. This lets operators wire a
     notifier workflow without the loop ever approving on its own.

  3. Scan recent failures from today's execution log: for each unique
     failed action, apply a simple policy — retry once (if the action
     is idempotent and retry-eligible) or escalate (log + emit
     `action_failed` signal).

  4. Return a cycle report.

Explicitly NOT in scope:
  - No infinite loops inside this module. Callers decide the cadence
    (cron, systemd timer, tmux loop). `run_forever()` is provided as a
    convenience for dev use only, with a configurable sleep.
  - No ML, no heuristics. Failure policy is a hand-written ruleset.
  - The loop NEVER bypasses the Control Plane.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.action_system.deferred import list_deferred
from core.action_system.logging import (
    DECISION_LOG_DIR,
    EXECUTION_LOG_DIR,
    log_decision,
)

from .orchestrator import Orchestrator, default_orchestrator
from .signals import (
    SignalEmission,
    emit_signal,
    get_handlers,
    list_pending,
    list_signals,
    mark_processed,
)


# ---------------------------------------------------------------------------
# Cycle configuration
# ---------------------------------------------------------------------------


@dataclass
class LoopConfig:
    stale_deferred_seconds: int = 6 * 3600  # 6h
    failure_scan_limit: int = 200  # lines from today's execution log
    max_retries_per_action: int = 1
    interval_seconds: int = 300  # used only by run_forever()
    retry_eligible_types: tuple[str, ...] = (
        # Only action types that are safe to re-run blindly. run_script
        # and write_file can be destructive in arbitrary ways — leave
        # them to explicit operator resume.
        "shell_command",
        "call_api",
    )


# ---------------------------------------------------------------------------
# Cycle report
# ---------------------------------------------------------------------------


@dataclass
class CycleReport:
    started_at: str
    finished_at: str
    signals_drained: int = 0
    workflows_triggered: int = 0
    stale_deferred: int = 0
    failures_detected: int = 0
    retries_attempted: int = 0
    escalations: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "signals_drained": self.signals_drained,
            "workflows_triggered": self.workflows_triggered,
            "stale_deferred": self.stale_deferred,
            "failures_detected": self.failures_detected,
            "retries_attempted": self.retries_attempted,
            "escalations": self.escalations,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Signal draining
# ---------------------------------------------------------------------------


def _drain_signals(orch: Orchestrator, report: CycleReport) -> None:
    for signal_name in list_signals():
        handlers = get_handlers(signal_name)
        pending: list[SignalEmission] = list_pending(signal_name)
        for emission in pending:
            if not handlers:
                # Nothing bound — leave the emission in pending so a
                # handler registered later can still pick it up, but
                # record that we saw it.
                report.details.append(
                    {
                        "kind": "signal_no_handler",
                        "signal": signal_name,
                        "emission_id": emission.emission_id,
                    }
                )
                continue

            report.signals_drained += 1
            outcomes: list[dict[str, Any]] = []
            any_failed = False
            for wf_name in handlers:
                try:
                    result = orch.run_workflow(
                        wf_name,
                        context={
                            "signal": signal_name,
                            "payload": emission.payload,
                            "emission_id": emission.emission_id,
                        },
                    )
                    report.workflows_triggered += 1
                    outcomes.append({"workflow": wf_name, "status": result["status"]})
                    if result["status"] != "ok":
                        any_failed = True
                except KeyError:
                    outcomes.append({"workflow": wf_name, "status": "unregistered"})
                    any_failed = True
                except Exception as e:  # defensive — loop must not die
                    outcomes.append(
                        {
                            "workflow": wf_name,
                            "status": "error",
                            "error": f"{type(e).__name__}: {e}",
                        }
                    )
                    any_failed = True

            mark_processed(emission, "failed" if any_failed else "ok")
            report.details.append(
                {
                    "kind": "signal_drained",
                    "signal": signal_name,
                    "emission_id": emission.emission_id,
                    "outcomes": outcomes,
                }
            )


# ---------------------------------------------------------------------------
# Stale deferred scan
# ---------------------------------------------------------------------------


def _scan_stale_deferred(config: LoopConfig, report: CycleReport) -> None:
    now = datetime.now(timezone.utc)
    for entry in list_deferred():
        deferred_at_str = entry.get("deferred_at")
        if not deferred_at_str:
            continue
        try:
            deferred_at = datetime.fromisoformat(deferred_at_str)
        except ValueError:
            continue
        age = (now - deferred_at).total_seconds()
        if age < config.stale_deferred_seconds:
            continue

        report.stale_deferred += 1
        action_blob = entry.get("action", {})
        action_id = action_blob.get("id")
        log_decision(
            context="orchestrator.loop.stale_deferred",
            options_considered=["ignore", "emit deferred_stale signal"],
            chosen_option="emit deferred_stale signal",
            reasoning=(
                f"Deferred action {action_id} has been waiting {int(age)}s "
                f"(threshold {config.stale_deferred_seconds}s)."
            ),
            related_action_id=action_id,
            source_agent="orchestrator.loop",
        )
        emit_signal(
            "deferred_stale",
            payload={
                "action_id": action_id,
                "age_seconds": int(age),
                "action": action_blob,
            },
        )
        report.details.append(
            {
                "kind": "stale_deferred",
                "action_id": action_id,
                "age_seconds": int(age),
            }
        )


# ---------------------------------------------------------------------------
# Failure scan + retry/escalate policy
# ---------------------------------------------------------------------------


def _today_execution_log_path() -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(EXECUTION_LOG_DIR, f"{day}-execution.jsonl")


def _read_recent_failures(limit: int) -> list[dict[str, Any]]:
    path = _today_execution_log_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            lines = f.readlines()
    except OSError:
        return []
    failures: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        action = record.get("action", {})
        if action.get("status") == "failed":
            failures.append(record)
    return failures


_FOLLOWUP_CONTEXTS = {
    "orchestrator.loop.retry",
    "orchestrator.loop.escalate",
}


def _already_followed_up(action_id: str) -> bool:
    """Check today's decision log for any follow-up on this action id.

    Prevents the loop from retrying OR re-escalating the same failure
    every cycle. Retries and escalations are both one-shot per day.
    """
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(DECISION_LOG_DIR, f"{day}-decisions.jsonl")
    if not os.path.isfile(path):
        return False
    try:
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    rec.get("related_action_id") == action_id
                    and rec.get("context") in _FOLLOWUP_CONTEXTS
                ):
                    return True
    except OSError:
        return False
    return False


def _scan_failures(config: LoopConfig, report: CycleReport) -> None:
    seen: set[str] = set()
    for record in _read_recent_failures(config.failure_scan_limit):
        action = record.get("action", {})
        action_id = action.get("id")
        if not action_id or action_id in seen:
            continue
        seen.add(action_id)

        # One-shot-per-day: don't keep re-emitting signals for the same
        # failed action every cycle.
        if _already_followed_up(action_id):
            continue

        report.failures_detected += 1

        action_type = action.get("type", "")
        eligible = action_type in config.retry_eligible_types and action.get(
            "idempotency_key"
        )

        if eligible:
            report.retries_attempted += 1
            log_decision(
                context="orchestrator.loop.retry",
                options_considered=["retry", "escalate", "ignore"],
                chosen_option="retry",
                reasoning=(
                    f"Failed action {action_id} is idempotent + retry-eligible "
                    f"(type={action_type}). Retry will be re-emitted as a "
                    f"signal for operator-owned retry workflow."
                ),
                related_action_id=action_id,
                source_agent="orchestrator.loop",
            )
            emit_signal(
                "action_retry_requested",
                payload={"action": action},
            )
            report.details.append({"kind": "retry_requested", "action_id": action_id})
        else:
            report.escalations += 1
            log_decision(
                context="orchestrator.loop.escalate",
                options_considered=["retry", "escalate", "ignore"],
                chosen_option="escalate",
                reasoning=(
                    f"Failed action {action_id} is not eligible for automatic "
                    f"retry (type={action_type}). Escalating via action_failed "
                    f"signal."
                ),
                related_action_id=action_id,
                source_agent="orchestrator.loop",
            )
            emit_signal(
                "action_failed",
                payload={"action": action},
            )
            report.details.append({"kind": "escalated", "action_id": action_id})


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_cycle(
    orch: Orchestrator | None = None,
    config: LoopConfig | None = None,
) -> CycleReport:
    """Run exactly one orchestrator cycle. Safe to call from cron."""
    orch = orch or default_orchestrator()
    config = config or LoopConfig()
    report = CycleReport(
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at="",
    )
    try:
        _drain_signals(orch, report)
        _scan_stale_deferred(config, report)
        _scan_failures(config, report)
    finally:
        report.finished_at = datetime.now(timezone.utc).isoformat()
    return report


def run_forever(
    orch: Orchestrator | None = None,
    config: LoopConfig | None = None,
    max_cycles: int | None = None,
) -> None:
    """Dev-mode convenience runner. Prefer cron/systemd in production.

    Stops after `max_cycles` if provided — useful for smoke tests.
    """
    config = config or LoopConfig()
    cycles = 0
    while True:
        report = run_cycle(orch=orch, config=config)
        print(json.dumps(report.to_dict(), default=str))
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            return
        time.sleep(max(1, config.interval_seconds))


__all__ = [
    "LoopConfig",
    "CycleReport",
    "run_cycle",
    "run_forever",
]
