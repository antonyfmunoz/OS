"""Retry lifecycle + trusted-base re-anchor tests.

Proves three properties that the wave-2 diff_scope defect exposed:

1. A failed verification DOES create a retry attempt (the scheduler's
   retry path at scheduler.py:361-374 is correct).
2. The poller's ``blocked_reason`` includes check DETAIL strings, not
   just check IDs (so the operator can diagnose WHY diff_scope failed).
3. When the spool result carries a ``trusted_base`` (from the trusted
   projection commit), the poller re-anchors the lease's
   ``snapshot_ref`` before the verifier runs, so system writes
   (OBJECTIVE.md, SHARED_CONTEXT.md) are excluded from the scope diff.

No Claude CLI quota spent — worker results are plain dicts and
verification is a deterministic stub.
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

# ── fixtures ────────────────────────────────────────────────────────────────


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
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "proofstate"))


def _failing_verify_with_detail(**kw):
    """Verification fails with a diff_scope check that has a DETAIL string."""
    return _Verdict(
        passed=False,
        proof_id="",
        checks=[
            {"check_id": "artifacts", "ok": True, "detail": "files=3 commits=1"},
            {
                "check_id": "diff_scope",
                "ok": False,
                "detail": (
                    "changes outside authorized scope: changed=5 "
                    "allowed=['app/main.py', 'app/store.py'] "
                    "outside=['OBJECTIVE.md', 'SHARED_CONTEXT.md']"
                ),
            },
        ],
    )


# ── test: blocked_reason includes check detail ──────────────────────────────


def test_blocked_reason_includes_check_detail_not_just_id(store):
    """The poller's blocked_reason on a failed verification must include the
    detail string from each failing check, not just the check_id. Without
    this, 'verification refused: diff_scope' gives zero diagnostic value.
    """
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
                },
            }
        ]
    )
    poller = ControlPlanePoller(
        store=store,
        spool=spool,
        scheduler=_StubScheduler(),
        verify_fn=_failing_verify_with_detail,
    )

    report = poller.run_pass()

    assert a.attempt_id in report.failed
    final = store.get_attempt(a.attempt_id)
    assert final.status == ExecutionAttemptStatus.FAILED.value
    br = final.blocked_reason
    assert "diff_scope" in br
    assert "outside" in br, (
        f"blocked_reason must include the diff_scope detail (paths outside scope), "
        f"not just the check_id. Got: {br!r}"
    )


# ── test: trusted_base re-anchors lease for verifier ────────────────────────


def test_trusted_base_reanchors_lease_snapshot_ref(store):
    """When the spool result carries a trusted_base, the poller must update
    the lease's snapshot_ref BEFORE passing it to the verifier. This is the
    F-3 fix: the trusted projection commits system writes past the original
    base, so the verifier's diff must start from the post-projection commit.
    """
    captured_lease_ref = {}

    def _capturing_verify(**kw):
        lease = kw.get("lease")
        ref = getattr(lease, "snapshot_ref", None)
        if ref is None and isinstance(lease, dict):
            ref = lease.get("snapshot_ref")
        captured_lease_ref["ref"] = ref
        return _Verdict(
            passed=False,
            checks=[{"check_id": "test", "ok": False, "detail": "test"}],
        )

    a = _dispatched_attempt(store)
    spool = _StubSpool(
        [
            {
                "attempt_id": a.attempt_id,
                "task_id": a.task_id,
                "trusted_base": "aaaa1111bbbb2222cccc3333dddd4444eeee5555",
                "worker_result": {
                    "ok": True,
                    "status": "succeeded",
                    "files_changed": ["app/main.py"],
                    "commits": ["abc add search"],
                },
            }
        ]
    )

    class _LeaseRecord:
        def __init__(self):
            self._d = {
                "lease_id": "l-1",
                "snapshot_ref": "0000000000000000000000000000000000000000",
                "worktree_path": "/tmp/test-lease",
                "status": "active",
            }

        def __getattr__(self, name):
            try:
                return self._d[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    lease_record = _LeaseRecord()

    poller = ControlPlanePoller(
        store=store,
        spool=spool,
        scheduler=_StubScheduler(),
        verify_fn=_capturing_verify,
        lease_lookup=lambda _lid: lease_record,
    )

    poller.run_pass()

    assert captured_lease_ref.get("ref") == "aaaa1111bbbb2222cccc3333dddd4444eeee5555", (
        "the poller must re-anchor lease.snapshot_ref to the trusted_base "
        "before passing to the verifier"
    )


def test_no_trusted_base_leaves_lease_unchanged(store):
    """When the spool result has no trusted_base (empty or absent), the lease
    snapshot_ref is passed to the verifier unchanged."""
    captured_lease_ref = {}

    def _capturing_verify(**kw):
        lease = kw.get("lease")
        ref = getattr(lease, "snapshot_ref", None)
        if ref is None and isinstance(lease, dict):
            ref = lease.get("snapshot_ref")
        captured_lease_ref["ref"] = ref
        return _Verdict(
            passed=False,
            checks=[{"check_id": "test", "ok": False, "detail": "test"}],
        )

    a = _dispatched_attempt(store)
    original_ref = "orig111122223333444455556666777788889999"
    spool = _StubSpool(
        [
            {
                "attempt_id": a.attempt_id,
                "task_id": a.task_id,
                # no trusted_base key
                "worker_result": {
                    "ok": True,
                    "status": "succeeded",
                    "files_changed": ["app/main.py"],
                    "commits": ["abc"],
                },
            }
        ]
    )

    class _LeaseRecord:
        def __init__(self):
            self._d = {
                "lease_id": "l-1",
                "snapshot_ref": original_ref,
                "worktree_path": "/tmp/test-lease",
                "status": "active",
            }

        def __getattr__(self, name):
            try:
                return self._d[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    lease_record = _LeaseRecord()

    poller = ControlPlanePoller(
        store=store,
        spool=spool,
        scheduler=_StubScheduler(),
        verify_fn=_capturing_verify,
        lease_lookup=lambda _lid: lease_record,
    )

    poller.run_pass()

    assert captured_lease_ref.get("ref") == original_ref, (
        "without trusted_base, the lease snapshot_ref must remain unchanged"
    )


# ── test: WorkerResult carries trusted_base ─────────────────────────────────


def test_worker_result_carries_trusted_base():
    """WorkerResult.trusted_base is serialized in to_dict() and available for
    the spool result."""
    from substrate.execution.attempts.worker_claude_cli import WorkerResult

    r = WorkerResult(ok=True, status="succeeded", trusted_base="abc123")
    d = r.to_dict()
    assert d["trusted_base"] == "abc123"


def test_worker_result_trusted_base_defaults_empty():
    from substrate.execution.attempts.worker_claude_cli import WorkerResult

    r = WorkerResult()
    assert r.trusted_base == ""
    assert r.to_dict()["trusted_base"] == ""


# ── mutation tests: retry path guards ───────────────────────────────────────


def _walk_to_failed(store, attempt):
    """Walk an attempt through the full lifecycle to FAILED."""
    for to_status, from_statuses, updates in [
        (
            ExecutionAttemptStatus.READY.value,
            (ExecutionAttemptStatus.CREATED.value,),
            {"assignment_id": f"asn-{attempt.attempt_id[:8]}", "readiness_state": "authorized"},
        ),
        (
            ExecutionAttemptStatus.LEASED.value,
            (ExecutionAttemptStatus.READY.value,),
            {"lease_id": f"l-{attempt.attempt_id[:8]}", "verifier_role_id": "role-verify-op"},
        ),
        (
            ExecutionAttemptStatus.DISPATCHED.value,
            (ExecutionAttemptStatus.LEASED.value,),
            {"worker_identity": "w:1", "instruction_package_hash": "ph-1"},
        ),
        (ExecutionAttemptStatus.RUNNING.value, (ExecutionAttemptStatus.DISPATCHED.value,), {}),
        (ExecutionAttemptStatus.VERIFYING.value, (ExecutionAttemptStatus.RUNNING.value,), {}),
        (ExecutionAttemptStatus.FAILED.value, (ExecutionAttemptStatus.VERIFYING.value,), {}),
    ]:
        attempt = store.transition_cas(
            attempt.attempt_id,
            to_status,
            expected_record_version=attempt.record_version,
            expected_statuses=from_statuses,
            actor="test",
            reason=f"walk to {to_status}",
            updates=updates,
        )
    return attempt


def _make_scheduler_fixtures(store, tmp_path, task_id, plan_record_id, decision_ref):
    """Build and persist a real grant + queue for scheduler tests."""
    from substrate.execution.attempts.records import (
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    grant = ExecutionAuthorizationGrant(
        decision_ref=decision_ref,
        plan_record_id=plan_record_id,
        plan_version=1,
        objective_id="goal-1",
        tenant_id="tenant-a",
        status="active",
        task_frontier=[task_id],
        max_attempts_per_task=2,
    )
    store.create_grant_idempotent(grant)

    class _Queue:
        def get_packet(self, tid):
            class _P:
                packet_id = tid
                task_id = tid
                status = type("_S", (), {"value": "approved"})()
                work_scope = {"tenant_id": "tenant-a"}
                lineage = {"plan_record_id": plan_record_id}
                dependencies = []

            return _P()

        def list_packets(self, **kw):
            return [self.get_packet(task_id)]

    def _placement_fn(packet, **kw):
        class _Placed:
            worker_identity = "worker:w1"
            verifier_role_id = "role-verify-op"
            compute_node = "node-1"

        return _Placed()

    class _LM:
        def acquire(self, **kw):
            class _Lease:
                lease_id = f"l-{task_id[:8]}"
                worktree_path = str(tmp_path / "lease")
                snapshot_ref = "deadbeef"
                status = "active"

            return _Lease()

        def release(self, lid, **kw):
            pass

    def _compile_fn(attempt, **kw):
        class _Pkg:
            package_hash = "ph-retry"
            governance_constraints = []

        return _Pkg()

    class _LatestPlan:
        def __init__(self):
            self.plan_record_id = plan_record_id
            self.status = "approved"

    def _passthrough_runner(mutation_name, intent, execute_fn, **kw):
        execute_fn()

    scheduler = AttemptScheduler(
        store,
        work_queue=_Queue(),
        placement_fn=_placement_fn,
        lease_manager=_LM(),
        compile_fn=_compile_fn,
        dispatch_fn=lambda a, p, **kw: None,
        max_concurrency=2,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _oid: _LatestPlan(),
        mutation_runner=_passthrough_runner,
    )

    return grant, scheduler


def test_scheduler_retry_creates_attempt_when_prior_failed(tmp_path, monkeypatch):
    """Mutation test: the scheduler creates a retry attempt when the prior
    attempt is FAILED and attempt_number < max_attempts_per_task.

    This test exercises the EXACT retry path at scheduler.py:361-374. A
    mutation that removes the retry creation or changes the comparison
    operator (> vs >=) would fail this test.
    """
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))

    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )

    a1 = ExecutionAttempt(
        task_id="wp-retry-test",
        objective_id="goal-1",
        plan_record_id="opr-retry",
        plan_version=1,
        execution_authorization_ref="objective_plan:opr-retry:execution_authorization:v1",
        attempt_number=1,
        tenant_id="tenant-a",
        correlation_id="conv-1",
    )
    a1, _ = store.create_attempt_idempotent(a1)
    _walk_to_failed(store, a1)

    decision_ref = "objective_plan:opr-retry:execution_authorization:v1"
    grant, scheduler = _make_scheduler_fixtures(
        store, tmp_path, "wp-retry-test", "opr-retry", decision_ref
    )

    report = scheduler.run_scheduler_pass(
        grant=grant,
        role_resolver=lambda _r: None,
        verifier_role_resolver=lambda _r: None,
        worker_candidates=["node-1"],
        compute_nodes=["node-1"],
    )

    assert report.retries_created, (
        "scheduler must create a retry attempt when the prior attempt FAILED "
        "and attempt_number <= max_attempts_per_task"
    )
    assert len(report.attempts_created) == 1
    retry_id = report.attempts_created[0]
    retry = store.get_attempt(retry_id)
    assert retry.attempt_number == 2
    assert retry.task_id == "wp-retry-test"


def test_scheduler_does_not_retry_when_exhausted(tmp_path, monkeypatch):
    """Mutation test: no retry when attempt_number would exceed
    max_attempts_per_task. Guards against changing > to >= at line 365.
    """
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))

    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )

    for n in (1, 2):
        a = ExecutionAttempt(
            task_id="wp-exhausted",
            objective_id="goal-1",
            plan_record_id="opr-exhaust",
            plan_version=1,
            execution_authorization_ref="objective_plan:opr-exhaust:execution_authorization:v1",
            attempt_number=n,
            tenant_id="tenant-a",
            correlation_id="conv-1",
        )
        a, _ = store.create_attempt_idempotent(a)
        _walk_to_failed(store, a)

    decision_ref = "objective_plan:opr-exhaust:execution_authorization:v1"
    grant, scheduler = _make_scheduler_fixtures(
        store, tmp_path, "wp-exhausted", "opr-exhaust", decision_ref
    )

    report = scheduler.run_scheduler_pass(
        grant=grant,
        role_resolver=lambda _r: None,
        verifier_role_resolver=lambda _r: None,
        worker_candidates=["node-1"],
        compute_nodes=["node-1"],
    )

    assert not report.attempts_created, (
        "scheduler must NOT create a retry when max_attempts_per_task is exhausted"
    )
    assert "wp-exhausted" in report.attempts_blocked
