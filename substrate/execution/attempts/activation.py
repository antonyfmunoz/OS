"""Task-activation unit of work (Amendment v1 clause 2).

Applying an approved execution authorization is ONE recoverable, idempotent
operation:

    approved ApprovalRequest
    → grant ACTIVATING
    → resolve the exact authorized WorkPacket set
    → close the ``execution_authorization`` gate on those Tasks
    → transition PLANNED Tasks to APPROVED (canonical WorkPacket authority)
    → emit one canonical event chain
    → mark the grant ACTIVE only after every required Task transition commits.

Partial failure NEVER produces an ACTIVE grant — the grant lands in
FAILED_ACTIVATION and a retry resumes idempotently (already-APPROVED Tasks are
skipped, no duplicate Tasks/grants/events). The canonical WorkPacket transition
path is PLANNED → READY_FOR_REVIEW → APPROVAL_PENDING → APPROVED; each hop is a
governed WorkPacket-authority write, so this closes the gate through the Task
owner rather than mutating packet state behind its back.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from substrate.execution.attempts.events import emit_execution_event
from substrate.execution.attempts.records import (
    ExecutionAuthorizationGrant,
    ExecutionAuthorizationGrantStatus,
)
from substrate.execution.attempts.store import ExecutionAttemptStore

logger = logging.getLogger(__name__)

_GRANT = ExecutionAuthorizationGrantStatus
EXECUTION_GATE = "execution_authorization_required"

# The canonical PLANNED → APPROVED walk (WorkPacket authority).
_ACTIVATION_PATH = [
    ("planned", "ready_for_review", "execution authorized — advancing to review"),
    ("ready_for_review", "approval_pending", "execution authorized — pending gate close"),
    (
        "approval_pending",
        "approved",
        "execution authorization gate closed — approved for execution",
    ),
]


def _packet_status_value(packet: Any) -> str:
    return getattr(getattr(packet, "status", None), "value", getattr(packet, "status", ""))


def activate_authorized_tasks(
    store: ExecutionAttemptStore,
    grant: ExecutionAuthorizationGrant,
    work_queue: Any,
    *,
    now: float | None = None,
    mutation_runner: Callable[..., Any] | None = None,
    packet_status_enum: Any | None = None,
) -> ExecutionAuthorizationGrant:
    """Run the activation unit of work for one approved grant. Returns the grant
    (ACTIVE on success, FAILED_ACTIVATION on partial failure)."""
    now = time.time() if now is None else now
    if packet_status_enum is None:
        from substrate.organism.work_packet import PacketLifecycleStatus as packet_status_enum

    runner = mutation_runner
    if runner is None:
        from substrate.execution.intent.loop import _substrate_native_governed_mutation

        runner = _substrate_native_governed_mutation

    def _activate_unit() -> tuple[str, bool]:
        activated: list[str] = list(grant.activated_task_ids)
        failures: list[str] = []

        for task_id in grant.task_frontier:
            if task_id in activated:
                continue  # idempotent resume — already transitioned to APPROVED
            packet = work_queue.get_packet(task_id)
            if packet is None:
                failures.append(f"{task_id}: packet not found")
                continue
            try:
                _advance_packet_to_approved(
                    work_queue, packet, task_id, packet_status_enum, now
                )
                activated.append(task_id)
                emit_execution_event(
                    "execution.task_authorization_gate_closed",
                    {"task_id": task_id, "decision_ref": grant.decision_ref},
                    correlation_id=grant.correlation_id,
                )
            except Exception as exc:  # a single Task failure fails the activation
                logger.debug("activation of %s failed: %s", task_id, exc)
                failures.append(f"{task_id}: {exc}")

        # Persist activation progress on the grant (idempotent resume marker).
        grant.activated_task_ids = activated

        if failures:
            grant.status = _GRANT.FAILED_ACTIVATION.value
            grant.decision_log.append(
                {"event": "activation_failed", "failures": failures, "at": now}
            )
            store.update_grant_cas(
                grant,
                expected_record_version=grant.record_version,
                expected_statuses=(_GRANT.ACTIVATING.value,),
            )
            return (f"activation failed: {grant.decision_ref}", True)

        # Every required Task transition committed → mark ACTIVE.
        grant.status = _GRANT.ACTIVE.value
        grant.decision_log.append(
            {"event": "activated", "activated_task_ids": activated, "at": now}
        )
        store.update_grant_cas(
            grant,
            expected_record_version=grant.record_version,
            expected_statuses=(_GRANT.ACTIVATING.value,),
        )
        return (f"execution authorization active: {grant.decision_ref}", True)

    response = runner(
        mutation_name="execution_authorization_decision",
        intent=f"activate execution authorization {grant.decision_ref}",
        execute_fn=_activate_unit,
        source="execution_attempts_activation",
        metadata={"decision_ref": grant.decision_ref, "task_count": len(grant.task_frontier)},
    )
    if not bool(getattr(response, "success", False)):
        _record_activation_failure(
            store,
            grant.decision_ref,
            f"activation commit rejected by governance: {getattr(response, 'output', '')}",
            now,
            runner,
        )
        raise RuntimeError(
            f"activation commit rejected by governance: {getattr(response, 'output', '')}"
        )
    if grant.status == _GRANT.FAILED_ACTIVATION.value:
        emit_execution_event(
            "execution.authorization_activation_failed",
            {"decision_ref": grant.decision_ref, "failures": [
                entry.get("failures", [])
                for entry in grant.decision_log
                if entry.get("event") == "activation_failed"
            ][-1]},
            correlation_id=grant.correlation_id,
        )
    elif grant.status == _GRANT.ACTIVE.value:
        emit_execution_event(
            "execution.authorization_activated",
            {"decision_ref": grant.decision_ref, "activated_task_ids": grant.activated_task_ids},
            correlation_id=grant.correlation_id,
        )
    return grant


def _record_activation_failure(
    store: ExecutionAttemptStore,
    decision_ref: str,
    reason: str,
    now: float,
    runner: Callable[..., Any],
) -> None:
    """Persist an explicit failed_activation state after an activation crash.

    This is not a manual promotion or a fallback authority path: it is the same
    governed ``execution_authorization_decision`` mutation, used only to turn a
    stranded ACTIVATING grant into an explicit non-active terminal failure after
    the activation unit reports failure. If the original mutation never executed
    because governance was unavailable, this no-ops/fails closed and no packet
    side effects should exist.
    """

    def _fail() -> tuple[str, bool]:
        fresh = store.get_grant(decision_ref)
        if fresh is None:
            return (f"activation failure: grant {decision_ref} vanished", False)
        if fresh.status != _GRANT.ACTIVATING.value:
            return (f"activation failure observed after status {fresh.status}", True)
        fresh.status = _GRANT.FAILED_ACTIVATION.value
        fresh.decision_log.append(
            {"event": "activation_failed", "reason": reason[:500], "at": now}
        )
        store.update_grant_cas(
            fresh,
            expected_record_version=fresh.record_version,
            expected_statuses=(_GRANT.ACTIVATING.value,),
        )
        return (f"activation failed: {decision_ref}", True)

    failure_response = runner(
        mutation_name="execution_authorization_decision",
        intent=f"fail activation for {decision_ref}",
        execute_fn=_fail,
        source="execution_attempts_activation",
        metadata={"decision_ref": decision_ref, "reason": reason[:200]},
    )
    if bool(getattr(failure_response, "success", False)):
        emit_execution_event(
            "execution.authorization_activation_failed",
            {"decision_ref": decision_ref, "reason": reason[:500]},
            correlation_id=getattr(store.get_grant(decision_ref), "correlation_id", ""),
        )


def _advance_packet_to_approved(
    work_queue: Any,
    packet: Any,
    task_id: str,
    packet_status_enum: Any,
    now: float,
) -> None:
    """Walk one packet PLANNED → APPROVED along the canonical path. Idempotent:
    a packet already at/after APPROVED is a no-op; a packet mid-path resumes."""
    terminal_ok = {"approved", "delegated", "executing", "validating", "completed"}
    for from_status, to_status, reason in _ACTIVATION_PATH:
        current = _packet_status_value(packet)
        if current in terminal_ok:
            return  # already authorized/executing — nothing to do
        if current != from_status:
            # Not at this hop's starting point; if we've already passed it, keep
            # walking, else the packet is in an unexpected state → raise.
            if current in {s for s, _, _ in _ACTIVATION_PATH}:
                continue
            raise RuntimeError(
                f"packet {task_id} in unexpected status {current!r} for activation"
            )
        work_queue.update_packet_status(
            task_id, getattr(packet_status_enum, to_status.upper()), reason
        )
        packet = work_queue.get_packet(task_id)


__all__ = ["activate_authorized_tasks", "EXECUTION_GATE"]
