"""Wave 2 C7 — control-plane poller: spool outbox result → canonical transition.

Proves the poller (the ONLY thing that turns a signed spool result into a
canonical ledger transition) drives dispatched → running → verifying →
succeeded|failed correctly, trusts no worker self-report, enforces verifier ≠
worker, and is idempotent on re-delivered results. No Claude CLI quota spent —
the worker result is a plain dict and verification is a deterministic stub.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.poller import ControlPlanePoller  # noqa: E402
from substrate.execution.attempts.records import (  # noqa: E402
    ExecutionAttempt,
    ExecutionAttemptStatus,
)
from substrate.execution.attempts.store import ExecutionAttemptStore  # noqa: E402


# Lifecycle-mechanics tests mint a REAL durable Proof bound to the attempt under
# test, rather than disabling the durability guard. The former env hatch
# (UMH_W2_ALLOW_NONDURABLE_PROOF) was removed: it was ambient, unlogged, and any
# stale export silently voided governed completion on a live billed run.
def _attach_valid_verifier_evidence(rt, pkg, attempt, verifier_identity="verifier:v1"):
    """Attach a digest-valid, correctly-bound confined-verifier evidence record to
    a durable AttemptProof and re-persist — mirroring production _persist_proof.

    RV-HIGH-1: the verifying→succeeded gate now validates this evidence, so a stub
    verifier that mints a proof to complete an attempt must attach it (as the real
    field verifier does), or the completion is correctly refused.
    """
    from substrate.execution.attempts.verifier_isolation import (
        VERIFIER_EVIDENCE_TYPE,
        VerifierEvidence,
    )
    from substrate.organism.proof_runtime import ProofEvidence

    ev = VerifierEvidence(
        verifier_lease_id="vl-1",
        attempt_id=attempt.attempt_id,
        task_id=attempt.task_id,
        assignment_id="",
        verifier_identity=verifier_identity,
        verifier_role_id="role-verifier-op",
        worker_identity=getattr(attempt, "worker_identity", "") or "worker:w1",
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
    pkg.evidence.append(
        ProofEvidence(
            evidence_type=VERIFIER_EVIDENCE_TYPE,
            description="confined verifier run",
            data=ev.to_dict(),
        )
    )
    rt._persist_package(pkg)  # noqa: SLF001 - canonical seam, as production does


def _durable_proof_for(attempt, *, tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "proofstate"))
    from substrate.organism.proof_runtime import ProofRuntime

    rt = ProofRuntime()
    pkg = rt.create_direct(
        work_id=attempt.task_id,
        action={"classification": "attempt_proof", "attempt_id": attempt.attempt_id},
        outcome="attempt_proof:passed",
        operator="verifier:v1",
    )
    _attach_valid_verifier_evidence(rt, pkg, attempt)
    return pkg.proof_id


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )


def _dispatched_attempt(store, **kw) -> ExecutionAttempt:
    """Create an attempt and walk it to DISPATCHED via the real CAS path."""
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
    a = ExecutionAttempt(**base)
    a, _ = store.create_attempt_idempotent(a)
    a = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.READY.value,
        expected_record_version=a.record_version,
        expected_statuses=(ExecutionAttemptStatus.CREATED.value,),
        actor="test",
        reason="ready",
        updates={"assignment_id": "asn-1", "readiness_state": "authorized"},
    )
    a = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.LEASED.value,
        expected_record_version=a.record_version,
        expected_statuses=(ExecutionAttemptStatus.READY.value,),
        actor="test",
        reason="leased",
        updates={"lease_id": "l-1", "verifier_role_id": "role-verify-op"},
    )
    a = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.DISPATCHED.value,
        expected_record_version=a.record_version,
        expected_statuses=(ExecutionAttemptStatus.LEASED.value,),
        actor="test",
        reason="dispatched",
        updates={"instruction_package_hash": "ph-1", "worker_identity": "worker:cc_cli_worktree"},
    )
    return a


class _StubSpool:
    def __init__(self, results):
        self._results = list(results)

    def drain_results(self):
        out, self._results = self._results, []
        return out


class _StubScheduler:
    def __init__(self):
        self.passes = 0

    def run_scheduler_pass(self, **kw):
        self.passes += 1

        class _R:
            attempts_admitted: list = []

        return _R()


class _Verdict:
    def __init__(self, passed, proof_id="", checks=None):
        self.passed = passed
        self.proof_id = proof_id
        self.checks = checks or []


@pytest.fixture(autouse=True)
def _shared_proof_store(tmp_path, monkeypatch):
    """The fake verifier and the lifecycle guard must read the SAME proof store."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "proofstate"))


def _passing_verify(**kw):
    # The verifier identity MUST differ from the worker — assert it here so the
    # test fails loudly if the poller ever passes a colliding identity.
    assert kw["verifier_identity"].startswith("verifier:")
    assert kw["verifier_identity"] != kw["attempt"].worker_identity
    # Mint a REAL durable Proof bound to the attempt under verification, exactly
    # as the production verifier does. A hardcoded id no longer completes an
    # attempt: the lifecycle guard rereads the canonical store and checks
    # lineage, and its former env bypass was removed.
    from substrate.organism.proof_runtime import ProofRuntime

    attempt = kw["attempt"]
    rt = ProofRuntime()
    pkg = rt.create_direct(
        work_id=attempt.task_id,
        action={"classification": "attempt_proof", "attempt_id": attempt.attempt_id},
        outcome="attempt_proof:passed",
        operator=kw["verifier_identity"],
    )
    _attach_valid_verifier_evidence(rt, pkg, attempt, verifier_identity=kw["verifier_identity"])
    return _Verdict(
        passed=True, proof_id=pkg.proof_id, checks=[{"check_id": "artifacts", "ok": True}]
    )


def _failing_verify(**kw):
    return _Verdict(
        passed=False,
        proof_id="",
        checks=[{"check_id": "artifacts", "ok": False}, {"check_id": "tests", "ok": False}],
    )


def test_dispatched_result_drives_to_succeeded_with_proof(store):
    a = _dispatched_attempt(store)
    spool = _StubSpool(
        [
            {
                "attempt_id": a.attempt_id,
                "task_id": a.task_id,
                "worker_result": {
                    "ok": True,
                    "status": "succeeded",
                    "files_changed": ["app/main.py"],
                    "commits": ["abc add search"],
                    "isolated": True,
                    "capability_policy": {
                        "schema_version": 1,
                        "mode": "normal",
                        "enforced": False,
                        "task_id": a.task_id,
                        "attempt_id": a.attempt_id,
                    },
                },
            }
        ]
    )
    sched = _StubScheduler()
    poller = ControlPlanePoller(
        store=store, spool=spool, scheduler=sched, verify_fn=_passing_verify
    )

    report = poller.run_pass()

    assert report.results_drained == 1
    assert a.attempt_id in report.transitioned_running
    assert a.attempt_id in report.transitioned_verifying
    assert a.attempt_id in report.succeeded
    final = store.get_attempt(a.attempt_id)
    assert final.status == ExecutionAttemptStatus.SUCCEEDED.value
    # Assert the DURABLE property, not a hardcoded id: the proof must resolve
    # from the canonical store and be bound to this exact attempt.
    assert final.proof_id
    from substrate.organism.proof_runtime import ProofRuntime

    pkg = ProofRuntime().reread_durable(final.proof_id)
    assert pkg is not None, "the completing Proof must be durably persisted"
    assert pkg.action.get("attempt_id") == a.attempt_id
    assert final.verifier_identity.startswith("verifier:")
    # worker files/commits were recorded on the attempt
    assert final.files_changed == ["app/main.py"]
    assert final.capability_policy["mode"] == "normal"
    assert final.capability_policy["attempt_id"] == a.attempt_id
    # scheduler re-run after transitions (next frontier gets a chance to dispatch)
    assert sched.passes == 1


def test_failed_verification_never_produces_success_proof(store):
    a = _dispatched_attempt(store)
    spool = _StubSpool(
        [
            {
                "attempt_id": a.attempt_id,
                "task_id": a.task_id,
                "worker_result": {
                    "ok": True,
                    "status": "succeeded",  # worker CLAIMS success
                    "files_changed": [],
                    "commits": [],
                },
            }
        ]
    )
    poller = ControlPlanePoller(
        store=store, spool=spool, scheduler=_StubScheduler(), verify_fn=_failing_verify
    )

    report = poller.run_pass()

    assert a.attempt_id in report.failed
    final = store.get_attempt(a.attempt_id)
    # worker said "succeeded" but verification refused → FAILED, no proof.
    assert final.status == ExecutionAttemptStatus.FAILED.value
    assert final.proof_id == ""
    last = final.transitions[-1]
    last_reason = last.reason if hasattr(last, "reason") else last.get("reason", "")
    assert "verification refused" in last_reason


def test_redelivered_result_is_idempotent(store):
    a = _dispatched_attempt(store)
    result = {
        "attempt_id": a.attempt_id,
        "task_id": a.task_id,
        "worker_result": {
            "ok": True,
            "status": "succeeded",
            "files_changed": ["x"],
            "commits": ["c"],
        },
    }
    # First delivery → succeeded.
    p1 = ControlPlanePoller(
        store=store,
        spool=_StubSpool([result]),
        scheduler=_StubScheduler(),
        verify_fn=_passing_verify,
    )
    p1.run_pass()
    v1 = store.get_attempt(a.attempt_id).record_version

    # Re-delivery of the SAME result → no-op (already terminal).
    p2 = ControlPlanePoller(
        store=store,
        spool=_StubSpool([result]),
        scheduler=_StubScheduler(),
        verify_fn=_passing_verify,
    )
    report = p2.run_pass()
    assert any(a.attempt_id in i and "already succeeded" in i for i in report.ignored)
    assert store.get_attempt(a.attempt_id).record_version == v1  # unchanged


def test_result_for_unknown_attempt_is_ignored(store):
    poller = ControlPlanePoller(
        store=store,
        spool=_StubSpool([{"attempt_id": "ea-ghost", "worker_result": {}}]),
        scheduler=_StubScheduler(),
        verify_fn=_passing_verify,
    )
    report = poller.run_pass()
    assert any("not in ledger" in i for i in report.ignored)
    assert not report.succeeded and not report.failed


def test_empty_outbox_still_runs_scheduler(store):
    sched = _StubScheduler()
    poller = ControlPlanePoller(
        store=store, spool=_StubSpool([]), scheduler=sched, verify_fn=_passing_verify
    )
    report = poller.run_pass()
    assert report.results_drained == 0
    assert sched.passes == 1  # frontier still gets a dispatch opportunity


# ── RV-HIGH-2: a lease-release fault must be HEALED, not deadlock retry ──────
class _FaultyThenRevocableLeaseManager:
    """release() FAULTS (leaving the lease ACTIVE); revoke() SUCCEEDS.

    Models the exact RV-HIGH-2 hazard: terminalize's _release_lease raises/leaves
    the lease active, so retry would deadlock (one active lease per task). The
    poller must re-drive revoke() to unblock retry.
    """

    def __init__(self):
        self.revoked = []

    def release(self, lease_id, **kw):
        raise RuntimeError("simulated lease-store CAS conflict on release")

    def revoke(self, lease_id, reason, **kw):
        self.revoked.append((lease_id, reason))


def test_lease_release_fault_is_force_revoked_to_unblock_retry(store, tmp_path, monkeypatch):
    """RV-HIGH-2: when terminalize reports lease_released=False (a release fault),
    the poller re-drives revoke() so the task's ACTIVE lease is cleared and the
    next attempt is not deadlocked. Without the heal, the lease stays ACTIVE
    forever and retry BLOCKS↔READY."""
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    a = _dispatched_attempt(store)
    # Move to VERIFYING then to a terminal FAILED via CAS so terminalize accepts it.
    a = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.RUNNING.value,
        expected_record_version=a.record_version,
        expected_statuses=(ExecutionAttemptStatus.DISPATCHED.value,),
        actor="runner",
        reason="running",
    )
    a = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.VERIFYING.value,
        expected_record_version=a.record_version,
        expected_statuses=(ExecutionAttemptStatus.RUNNING.value,),
        actor="runner",
        reason="verifying",
    )
    a = store.transition_cas(
        a.attempt_id,
        ExecutionAttemptStatus.FAILED.value,
        expected_record_version=a.record_version,
        expected_statuses=(ExecutionAttemptStatus.VERIFYING.value,),
        actor="verifier:v1",
        reason="verification refused",
    )

    lm = _FaultyThenRevocableLeaseManager()
    poller = ControlPlanePoller(
        store=store,
        spool=_StubSpool([]),
        scheduler=_StubScheduler(),
        verify_fn=_passing_verify,
        lease_manager=lm,
        run_root=str(tmp_path / "targets"),
    )
    from substrate.execution.attempts.poller import PollerPassReport

    report = PollerPassReport()
    poller._terminalize(a, "failed", report)  # noqa: SLF001 - direct unit exercise

    # The release fault was healed by a force-revoke of the stranded lease.
    assert lm.revoked, "poller did not re-drive revoke after a release fault"
    assert lm.revoked[0][0] == a.lease_id
    assert any("force-revoked" in e for e in report.errors)
