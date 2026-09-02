"""Retry lifecycle + trusted-base re-anchor tests.

Proves three properties that the wave-2 diff_scope defect exposed:

1. A failed verification DOES create a retry attempt (the scheduler's
   retry path at scheduler.py:361-374 is correct).
2. The poller's ``blocked_reason`` includes check DETAIL strings, not
   just check IDs (so the operator can diagnose WHY diff_scope failed).
3. When the spool result carries a ``trusted_base``, the poller validates
   and re-anchors the lease's ``snapshot_ref`` before the verifier runs.
   Since the invocation-41 correction the shipped worker reports the
   CANONICAL, un-moved base (the projection is execution context, never a
   commit), so the re-anchor is a validated no-op on the field path — but
   the guarded forward-only machinery itself remains load-bearing.

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


def test_trusted_base_reanchors_lease_snapshot_ref(store, real_repo):
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
                "trusted_base": real_repo["trusted"],
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
                "snapshot_ref": real_repo["base"],
                "worktree_path": real_repo["path"],
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

    assert captured_lease_ref.get("ref") == real_repo["trusted"], (
        "the poller must re-anchor lease.snapshot_ref to the trusted_base "
        "before passing to the verifier"
    )


def test_trusted_base_reanchors_on_retry_attempts_too(store, real_repo):
    """A RETRY attempt must be re-anchored exactly like a first attempt.

    Mutation survivor M5. Every trusted-base test used attempt_number=1, so
    gating the re-anchor on ``attempt_number <= 1`` passed the whole suite —
    while every retry in the field would silently verify against the stale
    fixture base and fail diff_scope forever. That is the ORIGINAL defect,
    surviving on precisely the path that is supposed to recover from it: the
    first attempt would pass and its retry could never.

    The re-anchor depends only on the spool result, never on attempt_number.
    """
    captured = {}

    def _capturing_verify(**kw):
        lease = kw.get("lease")
        captured["ref"] = getattr(lease, "snapshot_ref", None)
        captured["attempt_number"] = getattr(kw.get("attempt"), "attempt_number", None)
        return _Verdict(passed=False, checks=[{"check_id": "t", "ok": False, "detail": "t"}])

    # attempt_number=3 — a second retry, the deepest realistic retry depth.
    a = _dispatched_attempt(store, attempt_number=3)
    spool = _StubSpool(
        [
            {
                "attempt_id": a.attempt_id,
                "task_id": a.task_id,
                "trusted_base": real_repo["trusted"],
                "worker_result": {"ok": True, "status": "succeeded", "files_changed": []},
            }
        ]
    )

    class _LeaseRecord:
        def __init__(self):
            self._d = {
                "lease_id": "l-1",
                "snapshot_ref": real_repo["base"],
                "worktree_path": real_repo["path"],
                "status": "active",
            }

        def __getattr__(self, name):
            try:
                return self._d[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    ControlPlanePoller(
        store=store,
        spool=spool,
        scheduler=_StubScheduler(),
        verify_fn=_capturing_verify,
        lease_lookup=lambda _lid: _LeaseRecord(),
    ).run_pass()

    assert captured.get("attempt_number") == 3, "fixture must actually be a retry attempt"
    assert captured.get("ref") == real_repo["trusted"], (
        "a retry attempt must be re-anchored to its trusted_base exactly like a "
        "first attempt — gating the re-anchor on attempt_number resurrects the "
        f"stale-base defect on every retry. Got: {captured.get('ref')!r}"
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


def test_runner_serializes_trusted_base_without_attribute_access(tmp_path):
    """A worker result WITHOUT ``trusted_base`` must degrade, never crash.

    Regression. The runner originally read ``result.trusted_base`` directly, so
    any worker result predating the field raised AttributeError inside
    ``_run_one_claim`` -- after the claim, before ``spool.complete()``. The
    dispatch died in between: no signed result reached the outbox, the attempt
    stayed inflight, and teardown reported an unprocessed dispatch.

    BEHAVIOURAL: drives the REAL ``_run_one_claim`` with a worker result that
    has no such attribute and asserts a signed result still reaches the spool
    with ``trusted_base == ""``. (An earlier version asserted on the runner's
    SOURCE TEXT, which pins spelling rather than behaviour.)
    """
    from tests.wave2_script_import import load_wave2_script

    runner = load_wave2_script("wave2_attempt_runner")

    class _NoTrustedBase:
        ok = True
        status = "succeeded"
        files_changed: list = []
        commits: list = []
        isolated = True

        def to_dict(self):
            return {"ok": True, "status": "succeeded", "files_changed": [], "commits": []}

    completed = {}

    class _Spool:
        def complete(self, token, result):
            completed["result"] = result

    envelope = type(
        "_E",
        (),
        {
            "dispatch_id": "d1",
            "attempt_id": "ea-1",
            "task_id": "wp-a",
            "package_hash": "ph",
            "lease_id": "l1",
            "worktree_path": str(tmp_path),
            "base_commit": "abc123",
            "timeout_seconds": 600,
            "max_turns": 30,
            "disallowed_tools": [],
            "governance_constraints": [],
            "ordered_context": [],
            "operation_identity": {},
            "verification_requirements": [],
        },
    )()

    runner._run_one_claim(
        spool=_Spool(),
        token="tok",
        envelope=envelope,
        oauth_token=None,
        run_root=str(tmp_path),
        run_worker=lambda **kw: _NoTrustedBase(),
    )

    assert "result" in completed, (
        "a worker result lacking trusted_base must still produce a signed spool "
        "result -- an AttributeError here strands the dispatch mid-claim"
    )
    assert completed["result"]["trusted_base"] == "", (
        f"absent trusted_base must degrade to empty string, got "
        f"{completed['result'].get('trusted_base')!r}"
    )


def test_shipped_worker_keeps_projection_out_of_git_and_base_unmoved(tmp_path, monkeypatch):
    """The SHIPPED trusted phase must hide the projection WITHOUT moving the base.

    Invocation-41 correction. The previous design committed the projection and
    returned a moved base; that kept the projection out of the worker's diff but
    put a DIVERGENT per-Task ``OBJECTIVE.md`` into every retained predecessor,
    so fan-in composition always conflicted (field run 20260808T014829Z-p1).

    BEHAVIOURAL: runs the real ``_mark_projection_execution_context`` against a
    real repo. The projection must be on disk, git-invisible (status, working
    diff, untracked listing), the base UNMOVED — and ``OBJECTIVE.md`` must be
    tracked at its CANONICAL blob, so two lanes retain identical system
    metadata and compose cleanly.
    """
    from substrate.execution.attempts.worker_claude_cli import (
        _mark_projection_execution_context,
    )

    repo = tmp_path / "wt"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.local")
    _git(repo, "config", "user.name", "t")
    (repo / "app").mkdir()
    (repo / "app" / "main.py").write_text("base\n")
    (repo / "OBJECTIVE.md").write_text("# canonical all-tasks objective\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    canonical_blob = _git(repo, "rev-parse", f"{base}:OBJECTIVE.md")

    # the trusted phase's system writes, uncommitted (exactly as projected)
    (repo / "OBJECTIVE.md").write_text("# task-local objective\n")
    (repo / "SHARED_CONTEXT.md").write_text("shared\n")

    _mark_projection_execution_context(str(repo), {"projected": True})

    # the base does NOT move: HEAD is still the canonical base commit.
    assert _git(repo, "rev-parse", "HEAD") == base, (
        "the trusted phase must not move the attempt base — a projection commit "
        "poisons fan-in composition with a divergent OBJECTIVE.md"
    )
    # git-invisible on every channel the verifier reads:
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "diff", "--name-only", base) == ""
    assert _git(repo, "ls-files", "--others", "--exclude-standard") == ""
    # the projected content is in effect on disk for the worker...
    assert (repo / "OBJECTIVE.md").read_text() == "# task-local objective\n"
    # ...while the TRACKED blob stays canonical: the retained commit's tree will
    # carry this blob, identical across all lanes.
    assert _git(repo, "rev-parse", "HEAD:OBJECTIVE.md") == canonical_blob

    # trusted_base == the unmoved base is trivially a legal re-anchor value for
    # the poller (self-ancestor), so the reporting chain stays valid.
    from substrate.execution.attempts.verification import reanchor_is_authorized

    ok, why = reanchor_is_authorized(worktree=str(repo), original_base=base, new_base=base)
    assert ok, f"the unmoved base must remain an authorized re-anchor value: {why}"


def test_production_checks_builder_uses_the_effective_base(tmp_path, monkeypatch):
    """The REAL field builder must pass the EFFECTIVE base to the verifier.

    Reviewer finding L-2: reverting ``_checks`` to read the lease's own
    snapshot_ref broke no test. The poller-side test proves the kwarg is PASSED;
    nothing proved the real builder USES it. Without this, diff_scope enforces
    the re-anchored base while the persisted Proof records the stale one.

    BEHAVIOURAL: intercepts ``run_confined_verifier_checks`` and asserts the
    base_commit it receives is the effective base, not the lease's stale one.
    """
    from substrate.execution.attempts import field_control_plane as fcp
    from substrate.execution.attempts import verifier_isolation as vi

    seen = {}

    def _fake_checks(**kw):
        seen["base_commit"] = kw.get("base_commit")
        return ([], None)

    monkeypatch.setattr(vi, "run_confined_verifier_checks", _fake_checks)

    cls = next(
        c
        for c in vars(fcp).values()
        if isinstance(c, type) and hasattr(c, "_independent_checks_for")
    )
    driver = cls.__new__(cls)
    driver._targets_dir = str(tmp_path)
    (tmp_path / "fixture").mkdir(exist_ok=True)

    class _StaleLease:
        worktree_path = str(tmp_path)
        snapshot_ref = "STALE_LEDGER_BASE"

    monkeypatch.setattr(cls, "_lease_lookup", lambda self, lid: _StaleLease(), raising=False)
    monkeypatch.setattr(cls, "_run_root", lambda self: str(tmp_path), raising=False)

    builder = driver._independent_checks_for(
        type("_A", (), {"lease_id": "l1", "attempt_id": "ea-1", "worker_identity": "w"})()
    )
    assert builder is not None, "the field control plane must supply a checks builder"

    builder(
        type("_A", (), {"lease_id": "l1", "attempt_id": "ea-1", "worker_identity": "w"})(),
        effective_base="EFFECTIVE_REANCHORED_BASE",
    )

    assert seen.get("base_commit") == "EFFECTIVE_REANCHORED_BASE", (
        "the real checks builder must record the base that was ENFORCED, not the "
        f"ledger's stale snapshot_ref. Got: {seen.get('base_commit')!r}"
    )


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


# ── the control that makes the re-anchor SAFE ───────────────────────────────


def _git(repo, *args):
    """Run git in ``repo``, asserting success. Test-local (not gated code)."""
    import subprocess

    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"git {' '.join(args)} failed: {r.stderr}"
    return (r.stdout or "").strip()


@pytest.fixture()
def real_repo(tmp_path):
    """A real git repo: base commit → trusted commit → worker commit."""
    repo = tmp_path / "wt"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.local")
    _git(repo, "config", "user.name", "t")
    (repo / "app").mkdir()
    (repo / "app" / "main.py").write_text("print('base')\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")

    (repo / "OBJECTIVE.md").write_text("# trusted system write\n")
    _git(repo, "add", "--", "OBJECTIVE.md")
    _git(repo, "commit", "-q", "-m", "trusted: projection")
    trusted = _git(repo, "rev-parse", "HEAD")

    (repo / "app" / "main.py").write_text("print('worker change')\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "worker")
    return {"path": str(repo), "base": base, "trusted": trusted}


class _Lease:
    def __init__(self, worktree_path, snapshot_ref):
        self.worktree_path = worktree_path
        self.snapshot_ref = snapshot_ref


def test_base_ancestry_check_rejects_a_base_detached_from_head(real_repo):
    """The ancestry check is the control that makes the re-anchor SAFE.

    Mutation survivor M7: deleting `_base_is_ancestor_of_head` from
    `_diff_scope_verdict` broke NO test. That control is load-bearing — the
    worker owns its own attempt ref, so `git reset --soft` / `commit --amend`
    moves HEAD off the trusted projection commit. The worker can then re-commit
    the trusted paths with content of its choosing while the scope diff still
    reads clean. Without ancestry, the re-anchor would hand the verifier a base
    the worker had already detached from.

    Fails CLOSED: a base not reachable from HEAD is a rejection.
    """
    from substrate.execution.attempts.verification import _base_is_ancestor_of_head

    repo = real_repo["path"]

    ok, detail = _base_is_ancestor_of_head(_Lease(repo, real_repo["trusted"]))
    assert ok, f"the trusted base IS an ancestor of HEAD, must pass: {detail}"

    ok, detail = _base_is_ancestor_of_head(_Lease(repo, real_repo["base"]))
    assert ok, f"the original base is also an ancestor of HEAD: {detail}"

    # A commit on a DISCONNECTED history — exactly what `reset --soft` off the
    # trusted commit leaves behind.
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-q", "--orphan", "sneak")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "detached")
    orphan = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", branch)

    ok, detail = _base_is_ancestor_of_head(_Lease(repo, orphan))
    assert not ok, "a base NOT reachable from HEAD must be REJECTED"
    assert "not an ancestor" in detail.lower()


def test_base_ancestry_check_fails_closed_on_unanswerable_input(real_repo):
    """An ancestry question that cannot be answered is never an answer of yes."""
    from substrate.execution.attempts.verification import _base_is_ancestor_of_head

    ok, detail = _base_is_ancestor_of_head(_Lease(real_repo["path"], ""))
    assert not ok and "snapshot_ref" in detail

    ok, detail = _base_is_ancestor_of_head(_Lease("/nonexistent/path/xyz", "abc123"))
    assert not ok and "not inspectable" in detail

    ok, _ = _base_is_ancestor_of_head(
        _Lease(real_repo["path"], "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    )
    assert not ok, "a base SHA that does not exist must be REJECTED, not passed"


def test_diff_scope_still_enforces_ancestry_after_reanchor(real_repo):
    """End-to-end: `_diff_scope_verdict` itself must reject a detached base.

    Kills M7 at the call site, not just the helper — deleting the ancestry call
    from `_diff_scope_verdict` must fail a test.
    """
    from substrate.execution.attempts.verification import _diff_scope_verdict

    repo = real_repo["path"]

    class _Packet:
        def __init__(self):
            # The real contract: allowed_paths_for reads WorkRequirements
            # writable_path_scope + scope_declared, and fails closed without
            # the flag. Mirror it exactly — a stub that skips scope_declared
            # tests a scope resolution that cannot happen in the field.
            self.requirements = {
                "writable_path_scope": ["app/main.py"],
                "scope_declared": True,
            }

    class _WR:
        files_changed = ["app/main.py"]
        commits = []

    # Re-anchored to the trusted commit: only the worker's in-scope change is
    # in range, so this is the PASSING shape the fix is supposed to produce.
    ok, detail = _diff_scope_verdict(
        lease=_Lease(repo, real_repo["trusted"]), packet=_Packet(), worker_result=_WR()
    )
    assert ok, f"re-anchored to trusted base, only app/main.py changed — expected pass: {detail}"

    # Anchored at the ORIGINAL base: OBJECTIVE.md is in range → the defect.
    ok, detail = _diff_scope_verdict(
        lease=_Lease(repo, real_repo["base"]), packet=_Packet(), worker_result=_WR()
    )
    assert not ok, "stale base pulls OBJECTIVE.md into range — must reject"
    assert "OBJECTIVE.md" in detail

    # A detached base must be rejected BY ANCESTRY, not by path scope.
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-q", "--orphan", "sneak2")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "detached")
    orphan = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", branch)

    ok, detail = _diff_scope_verdict(
        lease=_Lease(repo, orphan), packet=_Packet(), worker_result=_WR()
    )
    assert not ok, "a base detached from HEAD must be rejected"
    assert "ancestor" in detail.lower(), (
        f"rejection must come from the ANCESTRY check so the operator is told the "
        f"history is not the authorized one. Got: {detail!r}"
    )


# ── the re-anchor must be AUTHORIZED, never assumed ─────────────────────────


def test_forward_reanchor_to_worker_head_is_refused(real_repo):
    """A base moved FORWARD onto the worker's own commit must be REFUSED.

    Adversarial review finding (HIGH). Moving a diff base forward monotonically
    shrinks the observed change set, so anchoring at the worker's HEAD makes
    diff_scope return ``changed=0`` and PASS with out-of-scope files sitting in
    the tree. Reproduced against this very module: scope ['app/'] with a
    smuggled secret/key.txt — original base rejects, trusted base rejects
    (catching the smuggle), worker-HEAD base returns ``changed=0 outside=[]``.

    ``_base_is_ancestor_of_head`` does NOT catch this: every commit on the
    branch is an ancestor of HEAD, including the worker's own. It guards the
    base leaving the branch, never the base sliding forward along it.
    """
    from substrate.execution.attempts.verification import reanchor_is_authorized

    repo = real_repo["path"]
    worker_head = _git(repo, "rev-parse", "HEAD")

    ok, why = reanchor_is_authorized(
        worktree=repo, original_base=real_repo["base"], new_base=real_repo["trusted"]
    )
    assert ok, f"the legitimate trusted-projection re-anchor must be allowed: {why}"

    ok, why = reanchor_is_authorized(
        worktree=repo, original_base=real_repo["base"], new_base=worker_head
    )
    assert not ok, (
        "re-anchoring forward onto the worker's own commit hides every worker "
        "change from the scope check and must be REFUSED"
    )
    assert "non-trusted paths" in why, (
        f"refusal must name the non-trusted paths the re-anchor would skip. Got: {why!r}"
    )


def test_reanchor_requires_a_full_sha_not_a_movable_ref(real_repo):
    """A resolvable branch NAME must not anchor a scope diff.

    ``main`` resolves and is an ancestor of HEAD, so without an explicit full-SHA
    check it would be accepted — and a ref can be moved after the fact.
    """
    from substrate.execution.attempts.verification import reanchor_is_authorized

    repo = real_repo["path"]
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")

    ok, why = reanchor_is_authorized(
        worktree=repo, original_base=real_repo["base"], new_base=branch
    )
    assert not ok, "a movable ref name must not be accepted as a diff base"
    assert "full commit SHA" in why


def test_reanchor_refuses_a_base_on_a_different_history(real_repo):
    """Sideways movement onto an unrelated history is refused."""
    from substrate.execution.attempts.verification import reanchor_is_authorized

    repo = real_repo["path"]
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-q", "--orphan", "elsewhere")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "unrelated")
    orphan = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", branch)

    ok, why = reanchor_is_authorized(
        worktree=repo, original_base=real_repo["base"], new_base=orphan
    )
    assert not ok and "NOT an ancestor" in why


def test_reanchor_fails_closed_on_unanswerable_input(real_repo):
    """Empty, nonexistent and uninspectable inputs all REFUSE."""
    from substrate.execution.attempts.verification import reanchor_is_authorized

    repo = real_repo["path"]
    base = real_repo["base"]

    assert not reanchor_is_authorized(worktree=repo, original_base=base, new_base="")[0]
    assert not reanchor_is_authorized(worktree=repo, original_base="", new_base=base)[0]
    assert not reanchor_is_authorized(
        worktree="/nonexistent/xyz", original_base=base, new_base=real_repo["trusted"]
    )[0]
    assert not reanchor_is_authorized(worktree=repo, original_base=base, new_base="0" * 40)[0], (
        "a nonexistent SHA must be REFUSED, not passed"
    )

    # Identical base is a legitimate no-op, not a refusal.
    assert reanchor_is_authorized(worktree=repo, original_base=base, new_base=base)[0]


def test_poller_keeps_original_base_when_reanchor_is_refused(store, real_repo):
    """End-to-end: a refused re-anchor leaves the ORIGINAL base in place.

    Fail-closed means the attempt gets the pre-fix scope verdict (a rejection),
    never a pass — and the refusal is surfaced on the report, never swallowed.
    """
    repo = real_repo["path"]
    worker_head = _git(repo, "rev-parse", "HEAD")
    captured = {}

    def _capturing_verify(**kw):
        captured["ref"] = getattr(kw.get("lease"), "snapshot_ref", None)
        return _Verdict(passed=False, checks=[{"check_id": "t", "ok": False, "detail": "t"}])

    class _LeaseRecord:
        def __init__(self):
            self._d = {
                "lease_id": "l-1",
                "snapshot_ref": real_repo["base"],
                "worktree_path": repo,
                "status": "active",
            }

        def __getattr__(self, name):
            try:
                return self._d[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    a = _dispatched_attempt(store)
    report = ControlPlanePoller(
        store=store,
        spool=_StubSpool(
            [
                {
                    "attempt_id": a.attempt_id,
                    "task_id": a.task_id,
                    # a forward base onto the worker's own commit
                    "trusted_base": worker_head,
                    "worker_result": {"ok": True, "status": "succeeded", "files_changed": []},
                }
            ]
        ),
        scheduler=_StubScheduler(),
        verify_fn=_capturing_verify,
        lease_lookup=lambda _lid: _LeaseRecord(),
    ).run_pass()

    assert captured.get("ref") == real_repo["base"], (
        "a REFUSED re-anchor must leave the original authorized base in place, "
        f"not the forward base. Got: {captured.get('ref')!r}"
    )
    assert any("re-anchor refused" in e for e in report.errors), (
        f"the refusal must be surfaced on the report, never swallowed. Got: {report.errors}"
    )


def test_poller_threads_effective_base_to_the_checks_builder(store, real_repo):
    """The Proof must record the base that was actually ENFORCED.

    The checks builder re-resolves the lease from the store and gets the LEDGER's
    original snapshot_ref (the re-anchor is in-memory by design). Without
    threading the effective base, diff_scope enforces the re-anchored base while
    the persisted Proof records the stale one — a Proof attesting to a base that
    was not the one enforced.
    """
    seen = {}

    def _builder(att, *, effective_base=""):
        seen["effective_base"] = effective_base
        return None

    class _LeaseRecord:
        def __init__(self):
            self._d = {
                "lease_id": "l-1",
                "snapshot_ref": real_repo["base"],
                "worktree_path": real_repo["path"],
                "status": "active",
            }

        def __getattr__(self, name):
            try:
                return self._d[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    a = _dispatched_attempt(store)
    ControlPlanePoller(
        store=store,
        spool=_StubSpool(
            [
                {
                    "attempt_id": a.attempt_id,
                    "task_id": a.task_id,
                    "trusted_base": real_repo["trusted"],
                    "worker_result": {"ok": True, "status": "succeeded", "files_changed": []},
                }
            ]
        ),
        scheduler=_StubScheduler(),
        verify_fn=lambda **kw: _Verdict(
            passed=False, checks=[{"check_id": "t", "ok": False, "detail": "t"}]
        ),
        lease_lookup=lambda _lid: _LeaseRecord(),
        independent_checks_for=_builder,
    ).run_pass()

    assert seen.get("effective_base") == real_repo["trusted"], (
        "the checks builder must receive the ENFORCED base so the Proof records "
        f"it. Got: {seen.get('effective_base')!r}"
    )


def test_legacy_single_arg_checks_builder_still_works(store, real_repo):
    """A builder that does not accept effective_base keeps working."""
    called = {}

    def _legacy_builder(att):
        called["yes"] = True
        return None

    class _LeaseRecord:
        def __init__(self):
            self._d = {
                "lease_id": "l-1",
                "snapshot_ref": real_repo["base"],
                "worktree_path": real_repo["path"],
                "status": "active",
            }

        def __getattr__(self, name):
            try:
                return self._d[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    a = _dispatched_attempt(store)
    ControlPlanePoller(
        store=store,
        spool=_StubSpool(
            [
                {
                    "attempt_id": a.attempt_id,
                    "task_id": a.task_id,
                    "trusted_base": real_repo["trusted"],
                    "worker_result": {"ok": True, "status": "succeeded", "files_changed": []},
                }
            ]
        ),
        scheduler=_StubScheduler(),
        verify_fn=lambda **kw: _Verdict(
            passed=False, checks=[{"check_id": "t", "ok": False, "detail": "t"}]
        ),
        lease_lookup=lambda _lid: _LeaseRecord(),
        independent_checks_for=_legacy_builder,
    ).run_pass()

    assert called.get("yes"), "a single-argument checks builder must still be invoked"


def test_checks_builder_is_never_invoked_twice_on_internal_typeerror():
    """A TypeError from INSIDE the builder must propagate, not re-invoke it.

    Regression. Dispatching on ``try: builder(att, effective_base=…) except
    TypeError: builder(att)`` cannot distinguish "this callable rejects the
    kwarg" from "this callable raised TypeError from its own body". The
    production builder (``field_control_plane._checks``) spawns a CONFINED
    VERIFIER, so a swallowed TypeError means the verifier runs twice — the
    second time with the ledger's stale base, which is also the base the Proof
    would then record. Verified against the try/except form: two invocations.

    Dispatch is by signature, so a builder that accepts the kwarg is called
    exactly once and its error propagates.
    """
    calls = []

    def _accepts_but_raises(att, *, effective_base=""):
        calls.append(effective_base)
        raise TypeError("raised from inside the builder body")

    poller = ControlPlanePoller.__new__(ControlPlanePoller)
    poller._independent_checks_for = _accepts_but_raises

    class _L:
        snapshot_ref = "abc123"

    with pytest.raises(TypeError):
        poller._build_independent_checks(object(), _L())

    assert len(calls) == 1, (
        f"a builder that ACCEPTS effective_base must be invoked exactly once; "
        f"re-invoking it duplicates verifier side effects. Got {len(calls)} calls: {calls}"
    )


def test_effective_base_dispatch_handles_every_builder_shape():
    """Signature dispatch must be right for each realistic builder shape."""
    from substrate.execution.attempts.poller import _accepts_effective_base

    def kwonly(att, *, effective_base=""):
        return None

    def positional_or_kw(att, effective_base=""):
        return None

    def var_kw(att, **kw):
        return None

    def legacy(att):
        return None

    assert _accepts_effective_base(kwonly)
    assert _accepts_effective_base(positional_or_kw)
    assert _accepts_effective_base(var_kw)
    assert not _accepts_effective_base(legacy)
    assert not _accepts_effective_base(lambda att: None)
    # An unintrospectable callable falls back to the always-valid legacy form.
    assert not _accepts_effective_base(len)


def test_run_worker_in_lease_assigns_trusted_base_on_every_post_worker_return():
    """Both post-execution returns in the SHIPPED worker must set trusted_base.

    Reviewer finding L-1: blanking both ``trusted_base=base_commit`` assignments
    broke NO test, because the propagation chain was pinned only at its MIDDLE
    (WorkerResult holds the field; the runner serializes it; the poller consumes
    it) -- never at its SOURCE.

    The returns BEFORE the projection phase are fail-closed refusals with no
    diff to scope, so they correctly carry no base. The returns that follow real
    worker execution must carry it (the CANONICAL, un-moved base since the
    invocation-41 correction), or the runner ships "" and the poller loses the
    validated base-reporting channel under a fully green suite.

    Pins the ASSIGNMENT structurally (AST of the shipped function), not by
    grepping source text for a spelling.
    """
    import ast
    import inspect
    import textwrap

    from substrate.execution.attempts.worker_claude_cli import run_worker_in_lease

    fn = ast.parse(textwrap.dedent(inspect.getsource(run_worker_in_lease))).body[0]

    commit_line = min(
        n.lineno
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_mark_projection_execution_context"
    )

    post_returns = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Return)
        and isinstance(n.value, ast.Call)
        and getattr(n.value.func, "id", "") == "WorkerResult"
        and n.lineno > commit_line
    ]
    assert post_returns, "expected WorkerResult returns after the projection phase"

    def _kwargs(ret):
        return {k.arg for k in ret.value.keywords}

    def _trusted_base_value(ret):
        """The AST node assigned to trusted_base, or None if absent."""
        for k in ret.value.keywords:
            if k.arg == "trusted_base":
                return k.value
        return None

    # A return carrying worker OUTPUT (or a post-run duration) must carry the base.
    output_returns = [r for r in post_returns if _kwargs(r) & {"files_changed", "duration_seconds"}]
    assert output_returns, (
        "expected at least one WorkerResult return carrying real worker output "
        "after the trusted projection phase"
    )
    for r in output_returns:
        value = _trusted_base_value(r)
        assert value is not None, (
            f"the WorkerResult return at relative line {r.lineno} follows real "
            f"worker execution but does not set trusted_base -- the runner would "
            f'ship "" and the poller would decline to re-anchor (F-3 restored)'
        )
        # It must be the post-projection BASE, not a literal. `trusted_base=""`
        # keeps the keyword while silently restoring the defect, so presence
        # alone is not the property -- the assigned VALUE is.
        assert isinstance(value, ast.Name) and value.id == "base_commit", (
            f"the WorkerResult return at relative line {r.lineno} must assign "
            f"trusted_base=base_commit (the canonical, un-moved base). Got "
            f"{ast.dump(value)[:80]} -- a literal here ships no base and the "
            f"poller declines to re-anchor, restoring F-3 with a green suite."
        )
