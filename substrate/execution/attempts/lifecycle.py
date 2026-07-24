"""ExecutionAttempt lifecycle transition table + fail-closed guards.

The transition table is the single source of legal attempt state changes; the
store's ``transition_cas`` validates every write against it. Guards enforce the
non-negotiable execution invariants (directive §IV/§X + Amendment v1 clause 6):

- ``ready → leased`` requires a resolved assignment + AUTHORIZED readiness.
- ``leased → dispatched`` requires a sealed instruction package + an ACTIVE
  lease + the authorization re-validated at that instant.
- ``verifying → succeeded`` requires an AttemptProof id AND a verifier identity
  DISTINCT from the worker identity AND a ``verifier:*`` actor — an agent can
  never complete its own Task, and no Task completes without independent Proof.

A retry is always a NEW attempt (see records.previous_attempt_id), never a
re-transition of a FAILED one.
"""

from __future__ import annotations

import os
from typing import Any

from substrate.execution.attempts.records import ExecutionAttempt, ExecutionAttemptStatus

_S = ExecutionAttemptStatus

# Legal forward transitions. ``failed`` is terminal-except-rollback.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    _S.CREATED.value: (_S.READY.value, _S.BLOCKED.value, _S.CANCELLED.value),
    _S.READY.value: (_S.LEASED.value, _S.BLOCKED.value, _S.CANCELLED.value),
    _S.LEASED.value: (_S.DISPATCHED.value, _S.BLOCKED.value, _S.CANCELLED.value),
    _S.DISPATCHED.value: (_S.RUNNING.value, _S.FAILED.value, _S.CANCELLED.value),
    _S.RUNNING.value: (_S.VERIFYING.value, _S.FAILED.value, _S.CANCELLED.value),
    _S.VERIFYING.value: (_S.SUCCEEDED.value, _S.FAILED.value),
    _S.BLOCKED.value: (_S.READY.value, _S.CANCELLED.value),
    _S.FAILED.value: (_S.ROLLED_BACK.value,),
    _S.SUCCEEDED.value: (),
    _S.CANCELLED.value: (),
    _S.ROLLED_BACK.value: (),
}

TERMINAL: frozenset[str] = frozenset(
    {_S.SUCCEEDED.value, _S.FAILED.value, _S.CANCELLED.value, _S.ROLLED_BACK.value}
)


class AttemptLifecycleError(RuntimeError):
    """Raised when a requested transition is illegal or fails a guard."""


def is_legal_transition(from_status: str, to_status: str) -> bool:
    return to_status in TRANSITIONS.get(from_status, ())


def validate_transition(
    attempt: ExecutionAttempt,
    to_status: str,
    actor: str,
    updates: dict[str, Any] | None = None,
) -> None:
    """Fail-closed guard for one attempt transition. Raises on any violation.

    ``updates`` are the binding-field writes that accompany the transition
    (e.g. ``assignment_id`` on ready→leased); they are validated here BEFORE the
    store applies them.
    """
    updates = updates or {}
    from_status = attempt.status

    if not is_legal_transition(from_status, to_status):
        raise AttemptLifecycleError(
            f"attempt {attempt.attempt_id}: illegal transition {from_status!r} → {to_status!r}"
        )

    # ready → leased: placement + readiness must be resolved.
    if to_status == _S.LEASED.value:
        assignment_id = updates.get("assignment_id", attempt.assignment_id)
        if not assignment_id:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: ready→leased requires an assignment_id"
            )

    # leased → dispatched: sealed package + lease + worker must be present.
    if to_status == _S.DISPATCHED.value:
        pkg = updates.get("instruction_package_hash", attempt.instruction_package_hash)
        lease = updates.get("lease_id", attempt.lease_id)
        worker = updates.get("worker_identity", attempt.worker_identity)
        if not pkg:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: leased→dispatched requires a sealed "
                f"instruction_package_hash"
            )
        if not lease:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: leased→dispatched requires an active lease_id"
            )
        if not worker:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: leased→dispatched requires a worker_identity"
            )

    # verifying → succeeded: independent Proof + verifier ≠ worker (clause 6).
    if to_status == _S.SUCCEEDED.value:
        proof_id = updates.get("proof_id", attempt.proof_id)
        verifier = updates.get("verifier_identity", attempt.verifier_identity)
        worker = updates.get("worker_identity", attempt.worker_identity)
        if not proof_id:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: verifying→succeeded requires an AttemptProof "
                f"(no completion without independent Proof)"
            )
        if not verifier:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: verifying→succeeded requires a verifier_identity"
            )
        if worker and verifier == worker:
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: verifier ({verifier!r}) must differ from the "
                f"implementation worker ({worker!r}) — an agent cannot complete its own Task"
            )
        if not str(actor).startswith("verifier:"):
            raise AttemptLifecycleError(
                f"attempt {attempt.attempt_id}: verifying→succeeded must be actioned by a "
                f"verifier actor, got {actor!r}"
            )
        # DURABILITY: a truthy proof_id is NOT a Proof (finding C1). Reread the
        # canonical store from disk and confirm the record exists AND belongs to
        # this exact attempt. An in-memory-only, missing, corrupt or mismatched
        # Proof blocks the transition — the attempt stays VERIFYING/FAILED.
        _assert_durable_proof(attempt, proof_id)

    # cancellation is an operator/scheduler/system action, never a worker one.
    if to_status == _S.CANCELLED.value and str(actor).startswith("worker:"):
        raise AttemptLifecycleError(
            f"attempt {attempt.attempt_id}: a worker may not cancel its own attempt"
        )


def _assert_durable_proof(attempt: ExecutionAttempt, proof_id: str) -> None:
    """Fail closed unless ``proof_id`` names a DURABLE Proof for THIS attempt.

    Rereads the canonical ProofRuntime store from disk (never the in-memory map),
    then checks the record's recorded lineage binds it to this attempt.

    There is deliberately NO bypass. An earlier env hatch
    (``UMH_W2_ALLOW_NONDURABLE_PROOF``) was removed: it was ambient, unlogged,
    and inherited by the runner subprocess, so a stale export in any shell would
    have silently voided governed completion on a live billed run.
    """
    try:
        from substrate.organism.proof_runtime import ProofRuntime
    except ImportError as exc:  # substrate must be importable; fail closed
        raise AttemptLifecycleError(
            f"attempt {attempt.attempt_id}: cannot verify Proof durability: {exc}"
        ) from exc

    package = ProofRuntime().reread_durable(proof_id)
    if package is None:
        raise AttemptLifecycleError(
            f"attempt {attempt.attempt_id}: proof {proof_id!r} is not durably persisted "
            f"(missing, corrupt, or in-memory only) — refusing verifying→succeeded"
        )

    # The Proof must belong to THIS attempt. Both checks are FAIL-CLOSED: absent
    # lineage is a rejection, never a pass.
    #
    # These were previously guarded by truthiness (`if recorded_attempt and ...`),
    # so a Proof whose action carried no attempt_id satisfied the gate for EVERY
    # attempt — verified: a proof with an empty attempt_id completed an unrelated
    # attempt on the same task. The plan-execution path mints exactly that shape.
    # A softened check is where the guarantee dies.
    action = getattr(package, "action", {}) or {}
    recorded_attempt = str(action.get("attempt_id", "") or "")
    if recorded_attempt != attempt.attempt_id:
        raise AttemptLifecycleError(
            f"attempt {attempt.attempt_id}: proof {proof_id!r} is bound to attempt "
            f"{recorded_attempt!r} — a Proof may only complete the attempt it proves "
            f"(absent lineage is a rejection)"
        )
    recorded_task = str(getattr(package, "work_id", "") or "")
    if recorded_task != str(attempt.task_id or ""):
        raise AttemptLifecycleError(
            f"attempt {attempt.attempt_id}: proof {proof_id!r} proves task "
            f"{recorded_task!r}, not {attempt.task_id!r}"
        )


__all__ = [
    "TRANSITIONS",
    "TERMINAL",
    "AttemptLifecycleError",
    "is_legal_transition",
    "validate_transition",
]
