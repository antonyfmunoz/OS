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


# Lifecycle-mechanics tests mint a REAL durable Proof bound to the attempt under
# test, rather than disabling the durability guard. The former env hatch
# (UMH_W2_ALLOW_NONDURABLE_PROOF) was removed: it was ambient, unlogged, and any
# stale export silently voided governed completion on a live billed run.
def _valid_verifier_evidence(attempt):
    """A digest-valid, correctly-bound confined-verifier evidence record.

    RV-HIGH-1: the verifying→succeeded gate now requires an AttemptProof to carry
    exactly-one digest-valid verifier evidence bound to this attempt/task. A bare
    proof (the pre-C-4a shape) no longer completes an attempt — so the durable
    proof a test mints to reach SUCCEEDED must be COMPLETE, as the field path is.
    """
    from substrate.execution.attempts.verifier_isolation import VerifierEvidence

    return VerifierEvidence(
        verifier_lease_id="vl-1",
        attempt_id=attempt.attempt_id,
        task_id=attempt.task_id,
        assignment_id="",
        verifier_identity="verifier:v1",
        verifier_role_id="role-verifier-op",
        worker_identity="worker:w1",
        package_hash="",
        base_commit="b" * 40,
        verified_commit="c" * 40,
        bwrap_argv=["bwrap"],
        bwrap_argv_digest="d",
        env_var_names=["PATH"],
        mount_policy={},
        isolation_probe={"ok": True},
        source_hashes_before={},
        source_hashes_after={},
        zero_diff=True,
        tests_ok=True,
        tests_detail="ok",
        started_at=1.0,
        ended_at=2.0,
        process_identity={"pid": 7, "valid": True},
        verifier_pid=7,
    ).finalize()


def _durable_proof_for(attempt, *, tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "proofstate"))
    from substrate.execution.attempts.verifier_isolation import VERIFIER_EVIDENCE_TYPE
    from substrate.organism.proof_runtime import ProofEvidence, ProofRuntime

    ev = _valid_verifier_evidence(attempt)
    rt = ProofRuntime()
    pkg = rt.create_direct(
        work_id=attempt.task_id,
        action={"classification": "attempt_proof", "attempt_id": attempt.attempt_id},
        outcome="attempt_proof:passed",
        operator="verifier:v1",
    )
    # Mirror the production _persist_proof path: attach the confined-verifier
    # evidence to the package and re-persist so the durable record carries it.
    pkg.evidence.append(
        ProofEvidence(
            evidence_type=VERIFIER_EVIDENCE_TYPE,
            description="confined verifier run",
            data=ev.to_dict(),
        )
    )
    rt._persist_package(pkg)  # noqa: SLF001 - canonical seam, as production does
    return pkg.proof_id


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
            updates={"proof_id": "p-unused-illegal-transition", "verifier_identity": "v1"},
        )


# ── Lifecycle guards (clause 6) ──────────────────────────────────────────────


def test_succeed_requires_proof_and_distinct_verifier(tmp_path, monkeypatch):
    a = _attempt(
        status=ExecutionAttemptStatus.VERIFYING.value,
        worker_identity="worker-1",
    )
    # A REAL durable Proof bound to this attempt — the durability guard has no
    # bypass, so lifecycle tests must mint one rather than disable the check.
    _pid = _durable_proof_for(a, tmp_path=tmp_path, monkeypatch=monkeypatch)
    # No proof → reject.
    with pytest.raises(AttemptLifecycleError):
        validate_transition(a, "succeeded", "verifier:v1", {"verifier_identity": "v1"})
    # Verifier == worker → reject.
    with pytest.raises(AttemptLifecycleError):
        validate_transition(
            a, "succeeded", "verifier:worker-1", {"proof_id": _pid, "verifier_identity": "worker-1"}
        )
    # Non-verifier actor → reject.
    with pytest.raises(AttemptLifecycleError):
        validate_transition(
            a, "succeeded", "worker:worker-1", {"proof_id": _pid, "verifier_identity": "v1"}
        )
    # Proof + distinct verifier + verifier actor → OK.
    validate_transition(
        a, "succeeded", "verifier:v1", {"proof_id": _pid, "verifier_identity": "v1"}
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
