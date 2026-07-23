"""Wave 2 C4 — AttemptScheduler dependency-aware admission + safety."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.records import ExecutionAttemptStatus
from substrate.execution.attempts.scheduler import AttemptScheduler
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket

_S = ExecutionAttemptStatus


def _runner():
    def run(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    return run


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(exist_ok=True)
    return UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))


def _add_approved_packet(queue, pid, deps=None):
    pkt = WorkPacket(title=pid, user_intent=f"do {pid}",
                     dependencies=deps or [],
                     approval_gates=["execution_authorization_required"],
                     work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"})
    pkt.packet_id = pid
    queue.ingest_work_packet(pkt)
    for s in (PacketLifecycleStatus.CLASSIFIED, PacketLifecycleStatus.PLANNED,
              PacketLifecycleStatus.READY_FOR_REVIEW, PacketLifecycleStatus.APPROVAL_PENDING,
              PacketLifecycleStatus.APPROVED):
        queue.update_packet_status(pid, s, "test")
    return pkt


def _grant(frontier, **kw):
    base = dict(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        tenant_id="tenant-a", plan_record_id="opr-1", plan_version=1, objective_id="goal-1",
        correlation_id="conv-1", status="active", task_frontier=frontier,
        max_attempts_per_task=2, environment_classes=["git_worktree"],
        credential_scope_refs=[], risk_ceiling="high", authorized_scope_hash="h",
        verification_obligations=["verify"], cost_limit_usd=0.0, cost_enforceable=False,
        principal_id="u", membership_id="m",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class _FakeSandbox:
    def __init__(self, tmp_path):
        self._repo_root = str(tmp_path / "repo")
        self._i = 0

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        self._i += 1
        return SimpleNamespace(worktree_path=f"/tmp/wt-{self._i}", branch_name=f"br-{self._i}",
                               base_commit="base", sandbox_id=f"sb-{self._i}")

    def cleanup_sandbox(self, sandbox_id):
        pass


def _mk_scheduler(store, queue, tmp_path, max_concurrency=2):
    from substrate.execution.attempts.dispatch import compile_attempt_package
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.placement import place_attempt

    lm = LeaseManager(store, _FakeSandbox(tmp_path), mutation_runner=_runner())
    return AttemptScheduler(
        store, work_queue=queue, placement_fn=place_attempt, lease_manager=lm,
        compile_fn=compile_attempt_package, dispatch_fn=None,
        max_concurrency=max_concurrency, mutation_runner=_runner(),
        lock_dir=str(tmp_path / "locks"),
    )


def _role(_pkt):
    return SimpleNamespace(role_id="role-impl-op", allowed_tools=["shell"])


def _workers():
    return [{"worker_identity": "cc@vps", "agent_type": "builder",
             "capabilities": ["code_write"], "reliability": 0.9,
             "model_profile": {"model": "claude-opus"}, "harness_profile": {"harness": "cc"}}]


def _pass(sched, grant):
    return sched.run_scheduler_pass(
        grant, role_resolver=_role, verifier_role_resolver=lambda p: "role-verify-op",
        worker_candidates=_workers(), compute_nodes=[{"node_id": "vps", "headroom": 4}],
    )


# ── Tests ────────────────────────────────────────────────────────────────────


def test_independent_lanes_admit_up_to_concurrency(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    _add_approved_packet(queue, "wp-b")
    sched = _mk_scheduler(store, queue, tmp_path, max_concurrency=2)
    report = _pass(sched, _grant(["wp-a", "wp-b"]))
    assert report.acquired
    assert len(report.attempts_created) == 2
    assert len(report.attempts_admitted) == 2  # both fit in 2 slots


def test_concurrency_cap_limits_admission(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    _add_approved_packet(queue, "wp-b")
    _add_approved_packet(queue, "wp-c")
    sched = _mk_scheduler(store, queue, tmp_path, max_concurrency=2)
    report = _pass(sched, _grant(["wp-a", "wp-b", "wp-c"]))
    assert len(report.attempts_admitted) == 2  # only 2 of 3 admitted


def test_fanin_task_blocked_until_predecessors_succeed(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    _add_approved_packet(queue, "wp-b")
    _add_approved_packet(queue, "wp-c", deps=["wp-a", "wp-b"])
    sched = _mk_scheduler(store, queue, tmp_path, max_concurrency=5)
    grant = _grant(["wp-a", "wp-b", "wp-c"])
    report = _pass(sched, grant)
    # A and B admitted; C NOT created (deps unsatisfied — no succeeded attempts).
    created_tasks = {store.get_attempt(aid).task_id for aid in report.attempts_created}
    assert created_tasks == {"wp-a", "wp-b"}
    assert "wp-c" not in created_tasks

    # Mark A and B succeeded (with proof) → C becomes ready next pass.
    for tid in ("wp-a", "wp-b"):
        att = store.attempts_for_task(tid)[0]
        # walk to succeeded via CAS (simulate real completion)
        for to, exp in [("running", ("dispatched",)), ("verifying", ("running",))]:
            att = store.transition_cas(att.attempt_id, to, att.record_version, exp,
                                       actor="worker:w", reason="t")
        store.transition_cas(att.attempt_id, "succeeded", att.record_version, ("verifying",),
                             actor="verifier:v", reason="done",
                             updates={"proof_id": f"proof-{tid}", "verifier_identity": "v",
                                      "worker_identity": "w"})
    report2 = _pass(sched, grant)
    created2 = {store.get_attempt(aid).task_id for aid in report2.attempts_created}
    assert "wp-c" in created2  # fan-in unblocked


def test_single_writer_lease_losing_tick_noops(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    sched = _mk_scheduler(store, queue, tmp_path)
    grant = _grant(["wp-a"])
    # Hold the lease manually, then a pass must no-op.
    key = "tenant-a:opr-1:v1"
    with sched._scheduler_lease(key) as got:
        assert got is True
        report = _pass(sched, grant)
        assert report.acquired is False
        assert report.attempts_created == []


def test_no_duplicate_attempt_on_repeated_pass(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    sched = _mk_scheduler(store, queue, tmp_path)
    grant = _grant(["wp-a"])
    _pass(sched, grant)
    _pass(sched, grant)  # second pass: attempt already active → no duplicate
    assert len(store.attempts_for_task("wp-a")) == 1


def test_failed_predecessor_blocks_dependent(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    _add_approved_packet(queue, "wp-c", deps=["wp-a"])
    sched = _mk_scheduler(store, queue, tmp_path, max_concurrency=5)
    grant = _grant(["wp-a", "wp-c"], max_attempts_per_task=1)
    _pass(sched, grant)
    # Fail wp-a's only attempt (max_attempts=1 → exhausted).
    att = store.attempts_for_task("wp-a")[0]
    att = store.transition_cas(att.attempt_id, "running", att.record_version, ("dispatched",),
                               actor="worker:w", reason="t")
    store.transition_cas(att.attempt_id, "failed", att.record_version, ("running",),
                         actor="worker:w", reason="boom")
    report = _pass(sched, grant)
    assert "wp-c" in report.attempts_blocked
