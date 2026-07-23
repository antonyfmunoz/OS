"""Wave 2 C5 — independent verification + two Proof classifications."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.lifecycle import AttemptLifecycleError
from substrate.execution.attempts.records import ExecutionAttempt, ExecutionAttemptStatus
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore
from substrate.execution.attempts.verification import (
    ATTEMPT_PROOF,
    PLAN_EXECUTION_PROOF,
    VerificationCheck,
    verify_attempt,
    verify_plan_execution,
)

_GUARD_ERRORS = (AttemptStoreConflict, AttemptLifecycleError)
_S = ExecutionAttemptStatus


class _ProofRT:
    def __init__(self):
        self._packages = {}


def _attempt(worker="worker-1", pkg_hash="h1"):
    a = ExecutionAttempt(task_id="wp-a", instruction_package_hash=pkg_hash, worker_identity=worker)
    a.attempt_id = "ea-1"
    return a


def _assignment(worker="worker-1"):
    return SimpleNamespace(worker_identity=worker)


def _lease():
    return SimpleNamespace(writable_paths=["/tmp/wt"])


def _worker_result(files=("app/main.py",), commits=("abc123 add search",)):
    return SimpleNamespace(files_changed=list(files), commits=list(commits))


# ── AttemptProof ─────────────────────────────────────────────────────────────


def test_attempt_proof_passes_with_real_artifacts():
    rt = _ProofRT()
    verdict = verify_attempt(
        attempt=_attempt(pkg_hash="h1"), assignment=_assignment(), lease=_lease(),
        worker_result=_worker_result(), package_hash="h1",
        verifier_identity="verifier-1", verifier_role_id="role-verify-op",
        proof_runtime=rt,
    )
    assert verdict.classification == ATTEMPT_PROOF
    assert verdict.passed is True
    assert verdict.proof_id  # a proof was persisted
    assert verdict.proof_id in rt._packages


def test_verifier_must_differ_from_worker():
    with pytest.raises(ValueError):
        verify_attempt(
            attempt=_attempt(worker="same"), assignment=_assignment(worker="same"),
            lease=_lease(), worker_result=_worker_result(), package_hash="h1",
            verifier_identity="same", verifier_role_id="role-verify-op",
        )


def test_no_artifacts_fails_verification():
    rt = _ProofRT()
    verdict = verify_attempt(
        attempt=_attempt(), assignment=_assignment(), lease=_lease(),
        worker_result=_worker_result(files=(), commits=()),  # nothing produced
        package_hash="h1", verifier_identity="v", verifier_role_id="r",
        proof_runtime=rt,
    )
    assert verdict.passed is False
    assert verdict.proof_id == ""  # no success proof for a failed verification


def test_package_hash_mismatch_fails():
    verdict = verify_attempt(
        attempt=_attempt(pkg_hash="h1"), assignment=_assignment(), lease=_lease(),
        worker_result=_worker_result(), package_hash="h-TAMPERED",
        verifier_identity="v", verifier_role_id="r",
    )
    assert verdict.passed is False


def test_independent_checks_can_fail_verdict():
    def failing_checks(attempt):
        return [VerificationCheck(check_id="tests", kind="tests", ok=False, detail="2 failing")]

    verdict = verify_attempt(
        attempt=_attempt(), assignment=_assignment(), lease=_lease(),
        worker_result=_worker_result(), package_hash="h1",
        verifier_identity="v", verifier_role_id="r",
        independent_checks=failing_checks,
    )
    assert verdict.passed is False  # verifier ran its OWN tests, which failed


# ── Proof-gated completion (integrates with the lifecycle guard) ─────────────


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"), grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"), leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )


def test_attempt_completes_only_with_proof_and_distinct_verifier(store):
    a = ExecutionAttempt(task_id="wp-a", worker_identity="worker-1")
    a.status = _S.VERIFYING.value
    store.create_attempt_idempotent(a)

    # Without a proof_id → the lifecycle guard rejects succeeded.
    with pytest.raises(_GUARD_ERRORS):
        store.transition_cas(a.attempt_id, "succeeded", a.record_version, ("verifying",),
                             actor="verifier:v1", updates={"verifier_identity": "v1"})

    # Verifier == worker → rejected.
    with pytest.raises(_GUARD_ERRORS):
        store.transition_cas(a.attempt_id, "succeeded", a.record_version, ("verifying",),
                             actor="verifier:worker-1",
                             updates={"proof_id": "p1", "verifier_identity": "worker-1"})

    # Proof + distinct verifier + verifier actor → succeeds.
    updated = store.transition_cas(
        a.attempt_id, "succeeded", a.record_version, ("verifying",),
        actor="verifier:v1", updates={"proof_id": "p1", "verifier_identity": "v1"},
    )
    assert updated.status == "succeeded"
    assert updated.proof_id == "p1"


# ── PlanExecutionProof ───────────────────────────────────────────────────────


def test_plan_execution_proof():
    rt = _ProofRT()

    def recon_checks():
        return [
            VerificationCheck(check_id="reconvergence", kind="diff", ok=True, detail="merged"),
            VerificationCheck(check_id="full_tests", kind="tests", ok=True, detail="all green"),
            VerificationCheck(check_id="live_http", kind="http", ok=True, detail="200"),
            VerificationCheck(check_id="browser", kind="browser", ok=True, detail="renders"),
            VerificationCheck(check_id="source_integrity", kind="policy", ok=True, detail="/opt/OS unchanged"),
            VerificationCheck(check_id="zero_deploy", kind="policy", ok=True, detail="no fly/gh"),
        ]

    verdict = verify_plan_execution(
        plan_record_id="opr-1", integration_task_id="wp-c",
        verifier_identity="verifier-D", verifier_role_id="role-verify-op",
        reconvergence_checks=recon_checks, proof_runtime=rt,
    )
    assert verdict.classification == PLAN_EXECUTION_PROOF
    assert verdict.passed is True
    assert verdict.proof_id in rt._packages


def test_plan_execution_proof_fails_on_any_check():
    def recon_checks():
        return [
            VerificationCheck(check_id="full_tests", kind="tests", ok=True, detail="green"),
            VerificationCheck(check_id="zero_deploy", kind="policy", ok=False, detail="fly deploy detected!"),
        ]

    verdict = verify_plan_execution(
        plan_record_id="opr-1", integration_task_id="wp-c",
        verifier_identity="v", verifier_role_id="r", reconvergence_checks=recon_checks,
    )
    assert verdict.passed is False
