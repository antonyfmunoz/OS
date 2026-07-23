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
        task_id="wp-a", objective_id="goal-1", plan_record_id="opr-1", plan_version=1,
        execution_authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        attempt_number=1, tenant_id="tenant-a", correlation_id="conv-1",
    )
    base.update(kw)
    a = ExecutionAttempt(**base)
    a, _ = store.create_attempt_idempotent(a)
    a = store.transition_cas(a.attempt_id, ExecutionAttemptStatus.READY.value,
                             expected_record_version=a.record_version,
                             expected_statuses=(ExecutionAttemptStatus.CREATED.value,),
                             actor="test", reason="ready",
                             updates={"assignment_id": "asn-1", "readiness_state": "authorized"})
    a = store.transition_cas(a.attempt_id, ExecutionAttemptStatus.LEASED.value,
                             expected_record_version=a.record_version,
                             expected_statuses=(ExecutionAttemptStatus.READY.value,),
                             actor="test", reason="leased",
                             updates={"lease_id": "l-1", "verifier_role_id": "role-verify-op"})
    a = store.transition_cas(a.attempt_id, ExecutionAttemptStatus.DISPATCHED.value,
                             expected_record_version=a.record_version,
                             expected_statuses=(ExecutionAttemptStatus.LEASED.value,),
                             actor="test", reason="dispatched",
                             updates={"instruction_package_hash": "ph-1",
                                      "worker_identity": "worker:cc_cli_worktree"})
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


def _passing_verify(**kw):
    # The verifier identity MUST differ from the worker — assert it here so the
    # test fails loudly if the poller ever passes a colliding identity.
    assert kw["verifier_identity"].startswith("verifier:")
    assert kw["verifier_identity"] != kw["attempt"].worker_identity
    return _Verdict(passed=True, proof_id="proof-xyz",
                    checks=[{"check_id": "artifacts", "ok": True}])


def _failing_verify(**kw):
    return _Verdict(passed=False, proof_id="",
                    checks=[{"check_id": "artifacts", "ok": False},
                            {"check_id": "tests", "ok": False}])


def test_dispatched_result_drives_to_succeeded_with_proof(store):
    a = _dispatched_attempt(store)
    spool = _StubSpool([{
        "attempt_id": a.attempt_id, "task_id": a.task_id,
        "worker_result": {"ok": True, "status": "succeeded",
                          "files_changed": ["app/main.py"], "commits": ["abc add search"],
                          "isolated": True},
    }])
    sched = _StubScheduler()
    poller = ControlPlanePoller(store=store, spool=spool, scheduler=sched,
                                verify_fn=_passing_verify)

    report = poller.run_pass()

    assert report.results_drained == 1
    assert a.attempt_id in report.transitioned_running
    assert a.attempt_id in report.transitioned_verifying
    assert a.attempt_id in report.succeeded
    final = store.get_attempt(a.attempt_id)
    assert final.status == ExecutionAttemptStatus.SUCCEEDED.value
    assert final.proof_id == "proof-xyz"
    assert final.verifier_identity.startswith("verifier:")
    # worker files/commits were recorded on the attempt
    assert final.files_changed == ["app/main.py"]
    # scheduler re-run after transitions (next frontier gets a chance to dispatch)
    assert sched.passes == 1


def test_failed_verification_never_produces_success_proof(store):
    a = _dispatched_attempt(store)
    spool = _StubSpool([{
        "attempt_id": a.attempt_id, "task_id": a.task_id,
        "worker_result": {"ok": True, "status": "succeeded",  # worker CLAIMS success
                          "files_changed": [], "commits": []},
    }])
    poller = ControlPlanePoller(store=store, spool=spool, scheduler=_StubScheduler(),
                                verify_fn=_failing_verify)

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
    result = {"attempt_id": a.attempt_id, "task_id": a.task_id,
              "worker_result": {"ok": True, "status": "succeeded",
                                "files_changed": ["x"], "commits": ["c"]}}
    # First delivery → succeeded.
    p1 = ControlPlanePoller(store=store, spool=_StubSpool([result]),
                            scheduler=_StubScheduler(), verify_fn=_passing_verify)
    p1.run_pass()
    v1 = store.get_attempt(a.attempt_id).record_version

    # Re-delivery of the SAME result → no-op (already terminal).
    p2 = ControlPlanePoller(store=store, spool=_StubSpool([result]),
                            scheduler=_StubScheduler(), verify_fn=_passing_verify)
    report = p2.run_pass()
    assert any(a.attempt_id in i and "already succeeded" in i for i in report.ignored)
    assert store.get_attempt(a.attempt_id).record_version == v1  # unchanged


def test_result_for_unknown_attempt_is_ignored(store):
    poller = ControlPlanePoller(
        store=store,
        spool=_StubSpool([{"attempt_id": "ea-ghost", "worker_result": {}}]),
        scheduler=_StubScheduler(), verify_fn=_passing_verify)
    report = poller.run_pass()
    assert any("not in ledger" in i for i in report.ignored)
    assert not report.succeeded and not report.failed


def test_empty_outbox_still_runs_scheduler(store):
    sched = _StubScheduler()
    poller = ControlPlanePoller(store=store, spool=_StubSpool([]), scheduler=sched,
                                verify_fn=_passing_verify)
    report = poller.run_pass()
    assert report.results_drained == 0
    assert sched.passes == 1  # frontier still gets a dispatch opportunity
