"""Wave 2 C1 — ExecutionAttemptStore + lifecycle + grant CAS.

Pins the canonical-attempt store contracts the whole slice rests on:
idempotent creation, CAS-protected lifecycle transitions, transition-table +
guard enforcement (verifier≠worker, proof-before-succeed), identity immutability,
grant states (Amendment v1 clause 1: no requested/denied), and grant CAS.
"""

from __future__ import annotations

import pytest

from substrate.execution.attempts.lifecycle import (
    TRANSITIONS,
    AttemptLifecycleError,
    is_legal_transition,
    validate_transition,
)
from substrate.execution.attempts.records import (
    ExecutionAttempt,
    ExecutionAttemptStatus,
    ExecutionAuthorizationGrant,
    ExecutionAuthorizationGrantStatus,
)
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
    )


def _attempt(**kw) -> ExecutionAttempt:
    base = dict(
        task_id="wp-a",
        objective_id="goal-1",
        plan_record_id="opr-1",
        plan_version=1,
        execution_authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        attempt_number=1,
        tenant_id="tenant-a",
        correlation_id="conv-1",
    )
    base.update(kw)
    return ExecutionAttempt(**base)


# ── Grant states (clause 1) ──────────────────────────────────────────────────


def test_grant_has_no_requested_or_denied_state():
    values = {s.value for s in ExecutionAuthorizationGrantStatus}
    assert "requested" not in values
    assert "denied" not in values
    assert values == {
        "activating",
        "active",
        "expired",
        "revoked",
        "invalidated",
        "failed_activation",
    }


# ── Idempotent creation ──────────────────────────────────────────────────────


def test_create_attempt_idempotent_returns_existing(store):
    a = _attempt()
    created, is_new = store.create_attempt_idempotent(a)
    assert is_new is True
    # Same logical key (task_id, authorization_ref, attempt_number) → no second row.
    dup, is_new2 = store.create_attempt_idempotent(_attempt(attempt_id="ea-other"))
    assert is_new2 is False
    assert dup.attempt_id == created.attempt_id
    assert len(store.attempts_for_task("wp-a")) == 1


def test_retry_is_a_new_attempt_number(store):
    store.create_attempt_idempotent(_attempt(attempt_number=1))
    a2, is_new = store.create_attempt_idempotent(
        _attempt(attempt_id="ea-2", attempt_number=2, previous_attempt_id="ea-1")
    )
    assert is_new is True
    attempts = store.attempts_for_task("wp-a")
    assert [x.attempt_number for x in attempts] == [1, 2]


# ── CAS transitions ──────────────────────────────────────────────────────────


def test_transition_cas_happy_path_and_history(store):
    a, _ = store.create_attempt_idempotent(_attempt())
    updated = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.READY.value,
        expected_record_version=0,
        expected_statuses=(ExecutionAttemptStatus.CREATED.value,),
        actor="scheduler",
        reason="frontier",
        updates={"assignment_id": "asn-1"},
    )
    assert updated.status == "ready"
    assert updated.record_version == 1
    assert updated.assignment_id == "asn-1"
    assert updated.transitions[-1]["from_status"] == "created"
    assert updated.transitions[-1]["to_status"] == "ready"


def test_transition_cas_version_conflict(store):
    a, _ = store.create_attempt_idempotent(_attempt())
    with pytest.raises(AttemptStoreConflict):
        store.transition_cas(
            a.attempt_id,
            ExecutionAttemptStatus.READY.value,
            expected_record_version=99,  # stale
            expected_statuses=(ExecutionAttemptStatus.CREATED.value,),
            actor="scheduler",
            updates={"assignment_id": "asn-1"},
        )


def test_transition_cas_status_conflict(store):
    a, _ = store.create_attempt_idempotent(_attempt())
    with pytest.raises(AttemptStoreConflict):
        store.transition_cas(
            a.attempt_id,
            ExecutionAttemptStatus.READY.value,
            expected_record_version=0,
            expected_statuses=(ExecutionAttemptStatus.RUNNING.value,),  # wrong
            actor="scheduler",
            updates={"assignment_id": "asn-1"},
        )


def test_transition_cas_rejects_immutable_field_write(store):
    a, _ = store.create_attempt_idempotent(_attempt())
    with pytest.raises(AttemptStoreConflict):
        store.transition_cas(
            a.attempt_id,
            ExecutionAttemptStatus.READY.value,
            expected_record_version=0,
            expected_statuses=(ExecutionAttemptStatus.CREATED.value,),
            actor="scheduler",
            updates={"task_id": "wp-hijacked", "assignment_id": "asn-1"},
        )


def test_illegal_transition_rejected(store):
    a, _ = store.create_attempt_idempotent(_attempt())
    with pytest.raises((AttemptStoreConflict, AttemptLifecycleError)):
        store.transition_cas(
            a.attempt_id,
            ExecutionAttemptStatus.SUCCEEDED.value,  # created→succeeded illegal
            expected_record_version=0,
            expected_statuses=(ExecutionAttemptStatus.CREATED.value,),
            actor="verifier:v1",
            updates={"proof_id": "p1", "verifier_identity": "v1"},
        )


# ── Lifecycle guards (clause 6) ──────────────────────────────────────────────


def test_succeed_requires_proof_and_distinct_verifier():
    a = _attempt(
        status=ExecutionAttemptStatus.VERIFYING.value,
        worker_identity="worker-1",
    )
    # No proof → reject.
    with pytest.raises(AttemptLifecycleError):
        validate_transition(a, "succeeded", "verifier:v1", {"verifier_identity": "v1"})
    # Verifier == worker → reject.
    with pytest.raises(AttemptLifecycleError):
        validate_transition(
            a, "succeeded", "verifier:worker-1", {"proof_id": "p1", "verifier_identity": "worker-1"}
        )
    # Non-verifier actor → reject.
    with pytest.raises(AttemptLifecycleError):
        validate_transition(
            a, "succeeded", "worker:worker-1", {"proof_id": "p1", "verifier_identity": "v1"}
        )
    # Proof + distinct verifier + verifier actor → OK.
    validate_transition(
        a, "succeeded", "verifier:v1", {"proof_id": "p1", "verifier_identity": "v1"}
    )


def test_dispatch_requires_package_lease_worker():
    a = _attempt(status=ExecutionAttemptStatus.LEASED.value, lease_id="lease-1")
    with pytest.raises(AttemptLifecycleError):
        validate_transition(a, "dispatched", "scheduler", {})  # no package/worker
    validate_transition(
        a,
        "dispatched",
        "scheduler",
        {"instruction_package_hash": "h", "worker_identity": "w", "lease_id": "lease-1"},
    )


def test_worker_cannot_cancel_own_attempt():
    a = _attempt(status=ExecutionAttemptStatus.RUNNING.value)
    with pytest.raises(AttemptLifecycleError):
        validate_transition(a, "cancelled", "worker:w1", {})
    validate_transition(a, "cancelled", "operator:u1", {})


def test_transition_table_terminal_states_have_no_exits():
    for terminal in ("succeeded", "cancelled", "rolled_back"):
        assert TRANSITIONS[terminal] == ()
    assert not is_legal_transition("succeeded", "running")


# ── Grant CAS ────────────────────────────────────────────────────────────────


def test_grant_create_idempotent_and_cas(store):
    g = ExecutionAuthorizationGrant(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        plan_record_id="opr-1",
        plan_version=1,
        objective_id="goal-1",
        tenant_id="tenant-a",
        task_frontier=["wp-a", "wp-b"],
    )
    created, is_new = store.create_grant_idempotent(g)
    assert is_new is True
    _, is_new2 = store.create_grant_idempotent(
        ExecutionAuthorizationGrant(decision_ref=g.decision_ref, plan_record_id="opr-1")
    )
    assert is_new2 is False

    created.status = ExecutionAuthorizationGrantStatus.ACTIVE.value
    updated = store.update_grant_cas(
        created,
        expected_record_version=0,
        expected_statuses=(ExecutionAuthorizationGrantStatus.ACTIVATING.value,),
    )
    assert updated.status == "active"
    assert updated.record_version == 1

    # Stale version → conflict.
    updated.status = ExecutionAuthorizationGrantStatus.REVOKED.value
    with pytest.raises(AttemptStoreConflict):
        store.update_grant_cas(updated, expected_record_version=0)


def test_grant_cas_rejects_immutable_field_change(store):
    g = ExecutionAuthorizationGrant(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        plan_record_id="opr-1",
        tenant_id="tenant-a",
    )
    created, _ = store.create_grant_idempotent(g)
    created.plan_record_id = "opr-HIJACK"
    with pytest.raises(AttemptStoreConflict):
        store.update_grant_cas(created, expected_record_version=0)
