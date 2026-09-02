"""Wave 2 C4 — AttemptScheduler dependency-aware admission + safety."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.records import ExecutionAttemptStatus
from substrate.execution.attempts.scheduler import AttemptScheduler
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket


# Lifecycle-mechanics tests mint a REAL durable Proof bound to the attempt under
# test, rather than disabling the durability guard. The former env hatch
# (UMH_W2_ALLOW_NONDURABLE_PROOF) was removed: it was ambient, unlogged, and any
# stale export silently voided governed completion on a live billed run.
def _durable_proof_for(attempt, *, tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "proofstate"))
    from substrate.organism.proof_runtime import ProofRuntime

    pkg = ProofRuntime().create_direct(
        work_id=attempt.task_id,
        action={"classification": "attempt_proof", "attempt_id": attempt.attempt_id},
        outcome="attempt_proof:passed",
        operator="verifier:v1",
    )
    return pkg.proof_id


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
    pkt = WorkPacket(
        title=pid,
        user_intent=f"do {pid}",
        dependencies=deps or [],
        approval_gates=["execution_authorization_required"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
        # The scheduler binds a grant to the Task it authorized: the packet's
        # OWN tenant and plan must equal the grant's, or a grant could name any
        # Task id in the system and have a real worker execute it (adversarial-
        # review CRITICAL). The canonical compiler stamps lineage.plan_record_id
        # on every materialized packet, so a fixture that omits it is modelling
        # a packet production never creates.
        lineage={"plan_record_id": "opr-1"},
        # Dispatch refuses a Task with undeclared mutation authority, so a
        # schedulable packet must declare its writable scope.
        requirements={"scope_declared": True, "writable_path_scope": ["app", "tests"]},
    )
    pkt.packet_id = pid
    queue.ingest_work_packet(pkt)
    for s in (
        PacketLifecycleStatus.CLASSIFIED,
        PacketLifecycleStatus.PLANNED,
        PacketLifecycleStatus.READY_FOR_REVIEW,
        PacketLifecycleStatus.APPROVAL_PENDING,
        PacketLifecycleStatus.APPROVED,
    ):
        queue.update_packet_status(pid, s, "test")
    return pkt


def _grant(frontier, **kw):
    base = dict(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        tenant_id="tenant-a",
        plan_record_id="opr-1",
        plan_version=1,
        objective_id="goal-1",
        correlation_id="conv-1",
        status="active",
        task_frontier=frontier,
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        credential_scope_refs=[],
        risk_ceiling="high",
        authorized_scope_hash="h",
        verification_obligations=["verify"],
        cost_limit_usd=0.0,
        cost_enforceable=False,
        principal_id="u",
        membership_id="m",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class _FakeSandbox:
    def __init__(self, tmp_path):
        self._repo_root = str(tmp_path / "repo")
        self._i = 0

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        self._i += 1
        return SimpleNamespace(
            worktree_path=f"/tmp/wt-{self._i}",
            branch_name=f"br-{self._i}",
            base_commit="base",
            sandbox_id=f"sb-{self._i}",
        )

    def cleanup_sandbox(self, sandbox_id):
        pass



def _fixture_plan_lookup(plan_record_id="opr-1"):
    """A lookup returning the APPROVED plan the grant names.

    Production grants copy `objective_id` from the plan at request time, so the
    planning store always resolves it; a synthetic grant whose objective was
    never persisted does not. The scheduler now asks the supersession question
    on EVERY pass (an ACTIVE grant for a superseded plan previously kept
    admitting, leasing and dispatching), and `is_authorization_valid` refuses
    when the lookup returns None — correctly. Tests therefore model the plan
    production would find, rather than disabling supersession.
    """
    from types import SimpleNamespace

    return lambda _objective_id: SimpleNamespace(
        plan_record_id=plan_record_id, status="approved"
    )

def _mk_scheduler(store, queue, tmp_path, max_concurrency=2):
    from substrate.execution.attempts.dispatch import compile_attempt_package
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.placement import place_attempt

    lm = LeaseManager(store, _FakeSandbox(tmp_path), mutation_runner=_runner())
    return AttemptScheduler(
        store,
        latest_plan_lookup=_fixture_plan_lookup(),
        work_queue=queue,
        placement_fn=place_attempt,
        lease_manager=lm,
        compile_fn=compile_attempt_package,
        dispatch_fn=None,
        max_concurrency=max_concurrency,
        mutation_runner=_runner(),
        lock_dir=str(tmp_path / "locks"),
    )


def _role(_pkt):
    return SimpleNamespace(role_id="role-impl-op", allowed_tools=["shell"])


def _workers():
    return [
        {
            "worker_identity": "cc@vps",
            "agent_type": "builder",
            "capabilities": ["code_write"],
            "reliability": 0.9,
            "model_profile": {"model": "claude-opus"},
            "harness_profile": {"harness": "cc"},
        }
    ]


def _persist_grant(sched, grant):
    """Production grants ALWAYS come from the ledger (`store.active_grants()`),
    and the scheduler now rereads the grant under its lock so a revocation
    committed after the caller captured its reference is seen. Tests must
    therefore persist the grant like production does, rather than hand the
    scheduler an object that exists only in memory.
    """
    from substrate.execution.attempts.records import ExecutionAuthorizationGrant

    payload = {
        k: v for k, v in vars(grant).items() if not k.startswith("_")
    }
    record = ExecutionAuthorizationGrant(
        **{k: v for k, v in payload.items() if k != "status"}
    )
    record.status = getattr(grant, "status", "active")
    existing = sched._store.get_grant(record.decision_ref)
    if existing is None:
        created, _ = sched._store.create_grant_idempotent(record)
        if created.status != record.status:
            created.status = record.status
            sched._store.update_grant_cas(
                created, expected_record_version=created.record_version
            )
    return grant


def _pass(sched, grant):
    _persist_grant(sched, grant)
    return sched.run_scheduler_pass(
        grant,
        role_resolver=_role,
        verifier_role_resolver=lambda p: "role-verify-op",
        worker_candidates=_workers(),
        compute_nodes=[{"node_id": "vps", "headroom": 4}],
    )


def _blocked_attempt(store, grant, task_id, blocked_reason):
    """Create one attempt and park it BLOCKED with the given reason, via legal
    transitions (created → blocked), mirroring _admit's failure path."""
    from substrate.execution.attempts.records import ExecutionAttempt

    att, _ = store.create_attempt_idempotent(
        ExecutionAttempt(
            task_id=task_id,
            objective_id=getattr(grant, "objective_id", ""),
            plan_record_id=getattr(grant, "plan_record_id", ""),
            plan_version=getattr(grant, "plan_version", 0),
            execution_authorization_ref=getattr(grant, "decision_ref", ""),
            attempt_number=1,
            tenant_id=getattr(grant, "tenant_id", ""),
        )
    )
    return store.transition_cas(
        att.attempt_id,
        _S.BLOCKED.value,
        att.record_version,
        (_S.CREATED.value,),
        actor="scheduler",
        reason=f"admission failed: {blocked_reason}",
        updates={"blocked_reason": blocked_reason},
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


def test_fanin_task_blocked_until_predecessors_succeed(store, queue, tmp_path, monkeypatch):
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
            att = store.transition_cas(
                att.attempt_id, to, att.record_version, exp, actor="worker:w", reason="t"
            )
        store.transition_cas(
            att.attempt_id,
            "succeeded",
            att.record_version,
            ("verifying",),
            actor="verifier:v",
            reason="done",
            updates={
                "proof_id": _durable_proof_for(att, tmp_path=tmp_path, monkeypatch=monkeypatch),
                "verifier_identity": "v",
                "worker_identity": "w",
            },
        )
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


def test_cpu_gate_blocked_attempt_is_rearmed_and_readmitted(store, queue, tmp_path):
    """FIELD regression (sixth control-plane layer, run 20260725T205058Z).

    A CPU-gate refusal during lease acquisition parks the attempt in BLOCKED
    (non-terminal, recoverable) with a reason naming the CPU gate. But nothing
    moved it back: the admission loop only admits READY attempts, and the
    frontier loop SKIPS a task that has any non-terminal attempt — so the task
    stayed wedged forever ("no eligible work") even after load dropped. This pins
    the re-arm: the next pass transitions the CPU-blocked attempt BLOCKED→READY
    and re-admits it. A block from a NON-transient cause must stay parked."""
    _add_approved_packet(queue, "wp-a")
    sched = _mk_scheduler(store, queue, tmp_path)
    grant = _grant(["wp-a"])
    # A CPU-gate-blocked attempt: created → blocked (legal) with a CPU reason,
    # exactly as _admit parks it when the lease git-subprocess is CPU-gated.
    att = _blocked_attempt(
        store, grant, "wp-a", "git rev-parse refused by CPU gate (host overloaded)"
    )
    assert store.get_attempt(att.attempt_id).status == _S.BLOCKED.value

    # Next pass: the transient block must be re-armed to READY and re-admitted —
    # NO new attempt is created (the existing one is reused).
    report = _pass(sched, grant)
    after = store.get_attempt(att.attempt_id)
    assert after.status != _S.BLOCKED.value, "CPU-blocked attempt must be re-armed, not stay wedged"
    assert not report.attempts_created, "re-arm reuses the existing attempt, mints no new one"
    assert len(store.attempts_for_task("wp-a")) == 1, "no duplicate attempt from re-arm"


def test_non_transient_block_is_not_rearmed(store, queue, tmp_path):
    """A block whose reason is NOT the CPU gate stays parked for inspection."""
    _add_approved_packet(queue, "wp-a")
    sched = _mk_scheduler(store, queue, tmp_path)
    grant = _grant(["wp-a"])
    att = _blocked_attempt(store, grant, "wp-a", "genuine admission fault, not transient")
    _pass(sched, grant)
    assert store.get_attempt(att.attempt_id).status == _S.BLOCKED.value, (
        "a non-transient block must NOT be re-armed"
    )


def test_failed_predecessor_blocks_dependent(store, queue, tmp_path):
    _add_approved_packet(queue, "wp-a")
    _add_approved_packet(queue, "wp-c", deps=["wp-a"])
    sched = _mk_scheduler(store, queue, tmp_path, max_concurrency=5)
    grant = _grant(["wp-a", "wp-c"], max_attempts_per_task=1)
    _pass(sched, grant)
    # Fail wp-a's only attempt (max_attempts=1 → exhausted).
    att = store.attempts_for_task("wp-a")[0]
    att = store.transition_cas(
        att.attempt_id, "running", att.record_version, ("dispatched",), actor="worker:w", reason="t"
    )
    store.transition_cas(
        att.attempt_id, "failed", att.record_version, ("running",), actor="worker:w", reason="boom"
    )
    report = _pass(sched, grant)
    assert "wp-c" in report.attempts_blocked
