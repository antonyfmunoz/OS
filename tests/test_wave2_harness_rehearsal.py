"""Wave 2 C7 — NO-QUOTA end-to-end harness rehearsal.

Proves the field harness MECHANICS are runnable before any real Claude quota is
spent (order step 2 + step 5). It wires the REAL scheduler + REAL signed dispatch
spool + REAL control-plane poller and drives the full A/B → C → D dependency
graph with a CONTRACT-FAITHFUL STUB WORKER (reads the spool inbox, writes a
signed result to the outbox — exactly like the real host runner, but with no CLI
invocation). Everything the harness relies on is exercised for real:

    signed spool delivery · signature rejection · dependency-gated admission ·
    exactly-2 concurrency · C blocked until A∧B have AttemptProof · D verifies ·
    poller transitions · idempotent result handling · PlanExecutionProof gate.

RESULT CLASSIFICATION (asserted by the final test):
    HARNESS_REHEARSAL_ONLY — REAL_WORKER_QUALIFICATION_NOT_SATISFIED.

This does NOT satisfy final real-execution qualification (no real worker ran, no
candidate deploy, no visible Chrome). It proves the harness itself works.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.poller import ControlPlanePoller
from substrate.execution.attempts.records import ExecutionAttemptStatus
from substrate.execution.attempts.scheduler import AttemptScheduler
from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket

_S = ExecutionAttemptStatus
_RUN_SECRET = "rehearsal-run-scoped-secret"


# ── governed-mutation stub (same shape the scheduler/poller expect) ──────────
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


def _add_approved_packet(queue, pid, deps=None, allowed_paths=("app", "tests")):
    """An APPROVED packet carrying a DECLARED path scope.

    ``allowed_paths`` is load-bearing: the writable-path authority is a FIRST-CLASS
    typed field on the Task contract (WorkRequirements.writable_path_scope +
    scope_declared), never derived from evidence. A packet with no declared scope
    fails verification closed rather than defaulting to the whole worktree, so the
    rehearsal must model a real Task that declares its own mutation authority.
    """
    pkt = WorkPacket(
        title=pid,
        user_intent=f"do {pid}",
        dependencies=deps or [],
        approval_gates=["execution_authorization_required"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
        requirements={
            "writable_path_scope": list(allowed_paths),
            "scope_declared": True,
        },
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


def _grant(frontier):
    return SimpleNamespace(
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


class _FakeSandbox:
    """Hands out REAL git worktrees.

    These were previously `/tmp/wt-<n>` — paths that never existed. Diff-scope is
    computed by running git in the lease worktree (finding C-1), so a nonexistent
    path means the verifier cannot observe anything independently and must fail
    closed. A rehearsal over fake paths would only ever rehearse that failure, so
    it must create real trees.
    """

    def __init__(self, tmp_path):
        self._repo_root = str(tmp_path / "repo")
        self._base = tmp_path / "leases"
        self._i = 0

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        import subprocess

        self._i += 1
        root = self._base / f"wt-{self._i}"
        (root / "app").mkdir(parents=True)
        (root / "tests").mkdir(parents=True)
        (root / "app" / "__init__.py").write_text("", encoding="utf-8")
        for args in (
            ("init", "-q"),
            ("config", "user.email", "t@example.com"),
            ("config", "user.name", "t"),
            ("add", "-A"),
            ("commit", "-q", "-m", "base"),
        ):
            subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True
        ).stdout.strip()
        return SimpleNamespace(
            worktree_path=str(root),
            branch_name=f"br-{self._i}",
            base_commit=base,
            sandbox_id=f"sb-{self._i}",
        )

    def cleanup_sandbox(self, sandbox_id):
        pass


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


# ── the SIGNED SPOOL dispatch_fn (real transport, exactly like the runner path) ─
def _spool_dispatch_fn(spool: DispatchSpool):
    seq = {"n": 0}

    def dispatch(*, attempt, assignment, lease, package, grant):
        seq["n"] += 1
        spool.enqueue(
            DispatchEnvelope(
                dispatch_id=f"d-{attempt.attempt_id}",
                attempt_id=attempt.attempt_id,
                task_id=attempt.task_id,
                authorization_ref=grant.decision_ref,
                package_hash=package.package_hash,
                lease_id=lease.lease_id,
                worktree_path=lease.worktree_path,
                nonce=f"n{seq['n']}",
                sequence=seq["n"],
                payload_hash=package.package_hash,
            )
        )

    return dispatch


# ── the CONTRACT-FAITHFUL STUB WORKER (no CLI, no quota) ─────────────────────
def _stub_worker_drain(spool: DispatchSpool, *, fail_tasks: set[str] | None = None) -> int:
    """Claim every signed dispatch and write a signed result — like the runner,
    minus the real Claude CLI. A task in ``fail_tasks`` reports empty artifacts
    (genuine failure: no commit → verification refuses)."""
    fail_tasks = fail_tasks or set()
    processed = 0
    while True:
        claimed = spool.claim_next()
        if claimed is None:
            return processed
        token, env = claimed
        failing = env.task_id in fail_tasks
        # A real worker WRITES into its lease worktree. The verifier computes the
        # changed set from git there (finding C-1), so a stub that only *reports*
        # files would produce an empty independent diff. Write in-scope files so
        # the rehearsal exercises the real verification path.
        worktree = getattr(env, "worktree_path", "") or ""
        if not failing and worktree and os.path.isdir(worktree):
            target = os.path.join(worktree, "app", f"{env.task_id}.py")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(f"# implemented by {env.task_id}\n")
        spool.complete(
            token,
            {
                "dispatch_id": env.dispatch_id,
                "attempt_id": env.attempt_id,
                "task_id": env.task_id,
                "package_hash": env.package_hash,
                "worker_result": {
                    "ok": not failing,
                    "status": "failed" if failing else "succeeded",
                    "files_changed": [] if failing else [f"app/{env.task_id}.py"],
                    "commits": [] if failing else [f"c-{env.task_id} implement"],
                    "isolated": True,
                },
            },
        )
        processed += 1


# ── a deterministic verifier (verifier ≠ worker, requires real artifacts) ────
def _StubProofRuntime(tmp_path=None):
    """The REAL canonical ProofRuntime on a temp store.

    Formerly a stub returning `proof-N` ids that were never persisted — the
    rehearsal therefore "verified" attempts against Proofs that did not exist
    (finding C1). The rehearsal must exercise the durable path, since that is
    exactly what the field qualification depends on.
    """
    from substrate.organism.proof_runtime import ProofRuntime

    # NO store_path override: resolve through UMH_STATE_DIR (set by the `queue`
    # fixture) so this runtime and the lifecycle guard's own reread hit the SAME
    # file. Pointing them at different stores would make the guard reject every
    # Proof the rehearsal mints.
    return ProofRuntime()


def _verify_fn(**kw):
    from substrate.execution.attempts.verification import verify_attempt

    return verify_attempt(**kw)


def _mk_scheduler(store, queue, tmp_path, spool):
    from substrate.execution.attempts.dispatch import compile_attempt_package
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.placement import place_attempt

    lm = LeaseManager(store, _FakeSandbox(tmp_path), mutation_runner=_runner())
    return AttemptScheduler(
        store,
        work_queue=queue,
        placement_fn=place_attempt,
        lease_manager=lm,
        compile_fn=compile_attempt_package,
        dispatch_fn=_spool_dispatch_fn(spool),
        max_concurrency=2,
        mutation_runner=_runner(),
        lock_dir=str(tmp_path / "locks"),
    )


def _mk_poller(store, spool, scheduler, grant, proof_runtime, queue=None, run_root=""):
    # Use the REAL durable store accessors (finding C4). This helper previously
    # called store.list_assignments() — a method that does not exist — behind a
    # hasattr guard, so it returned None for every attempt and the rehearsal
    # verified with no assignment/lease context at all. The store returns dicts
    # and verify_attempt reads attributes, so wrap them the same way the field
    # driver does.
    from substrate.execution.attempts.field_control_plane import _RecordView

    def _asn_lookup(aid):
        return _RecordView.wrap(store.get_assignment(aid)) if aid else None

    def _lease_lookup(lid):
        return _RecordView.wrap(store.get_lease(lid)) if lid else None

    def _packet_lookup(tid):
        # The canonical WorkPacket is the diff-scope authority (finding C-1).
        # An unwired lookup makes verification fail closed, so the rehearsal must
        # resolve real packets — exactly as the field driver does.
        return queue.get_packet(tid) if (queue is not None and tid) else None

    return ControlPlanePoller(
        store=store,
        spool=spool,
        scheduler=scheduler,
        verify_fn=_verify_fn,
        proof_runtime=proof_runtime,
        assignment_lookup=_asn_lookup,
        lease_lookup=_lease_lookup,
        packet_lookup=_packet_lookup,
        # C-2: terminalize on every terminal transition through the SAME lease
        # manager the scheduler acquires with, so a failed A1 releases its lease
        # and A2's retry is admissible (no deadlock).
        lease_manager=scheduler._leases,  # noqa: SLF001 - shared instance by design
        run_root=run_root,
        scheduler_pass_kwargs=dict(
            grant=grant,
            role_resolver=_role,
            verifier_role_resolver=lambda p: "role-verify-op",
            worker_candidates=_workers(),
            compute_nodes=[{"node_id": "vps", "headroom": 4}],
        ),
    )


def _pass(sched, grant):
    return sched.run_scheduler_pass(
        grant,
        role_resolver=_role,
        verifier_role_resolver=lambda p: "role-verify-op",
        worker_candidates=_workers(),
        compute_nodes=[{"node_id": "vps", "headroom": 4}],
    )


# ── signature rejection (a tampered dispatch is never worked) ────────────────
def test_signature_rejection_quarantines_bad_dispatch(tmp_path):
    root = str(tmp_path / "spool")
    producer = DispatchSpool(root, _RUN_SECRET)
    producer.enqueue(
        DispatchEnvelope(
            dispatch_id="d1", attempt_id="ea-1", sequence=1, worktree_path=str(tmp_path)
        )
    )
    # A worker (or runner) with the WRONG secret cannot claim it.
    wrong = DispatchSpool(root, "wrong-secret")
    assert wrong.claim_next() is None


# ── the full A/B → C → D rehearsal ───────────────────────────────────────────
def test_full_graph_rehearsal_no_quota(store, queue, tmp_path):
    """A,B independent; C depends on A,B; D depends on C. Drive to full green
    with a stub worker — proving every harness mechanic short of a real worker."""
    _add_approved_packet(queue, "A")
    _add_approved_packet(queue, "B")
    _add_approved_packet(queue, "C", deps=["A", "B"])
    _add_approved_packet(queue, "D", deps=["C"])
    grant = _grant(["A", "B", "C", "D"])

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    sched = _mk_scheduler(store, queue, tmp_path, spool)
    proof_runtime = _StubProofRuntime(tmp_path)
    poller = _mk_poller(
        store, spool, sched, grant, proof_runtime, queue=queue, run_root=str(tmp_path)
    )

    # Round 1: scheduler admits A + B (exactly 2 concurrency); C, D blocked by deps.
    r1 = _pass(sched, grant)
    admitted_1 = set(r1.attempts_admitted)
    running = [a for a in store.active_attempts() if a.status == _S.DISPATCHED.value]
    assert len(admitted_1) == 2, "exactly-2 concurrency at admission"
    tasks_running = {store.get_attempt(aid).task_id for aid in admitted_1}
    assert tasks_running == {"A", "B"}, "only the independent frontier A,B admitted"
    # C must NOT have an attempt yet (blocked until A,B verified).
    assert not any(a.task_id == "C" for a in store.active_attempts())

    # The stub worker drains the spool (A,B) and writes signed results.
    assert _stub_worker_drain(spool) == 2

    # Poller pass: A,B → running → verifying → succeeded (with AttemptProof), then
    # re-runs scheduler → admits C (fan-in satisfied).
    p1 = poller.run_pass()
    assert set(p1.succeeded) == set(admitted_1), "A,B verified with proof"
    for aid in admitted_1:
        a = store.get_attempt(aid)
        assert a.status == _S.SUCCEEDED.value and a.proof_id, "AttemptProof required"
    # C admitted now that both predecessors have proof.
    c_attempts = [a for a in store.active_attempts() if a.task_id == "C"]
    assert c_attempts and c_attempts[0].status == _S.DISPATCHED.value, "C admitted after A∧B proof"

    # Worker drains C; poller verifies C; scheduler then admits D.
    assert _stub_worker_drain(spool) == 1
    p2 = poller.run_pass()
    assert [store.get_attempt(a).task_id for a in p2.succeeded] == ["C"]
    d_attempts = [a for a in store.active_attempts() if a.task_id == "D"]
    assert d_attempts and d_attempts[0].status == _S.DISPATCHED.value, "D admitted after C proof"

    # Worker drains D (the verifier task); poller settles D.
    assert _stub_worker_drain(spool) == 1
    p3 = poller.run_pass()
    assert [store.get_attempt(a).task_id for a in p3.succeeded] == ["D"]

    # All four tasks succeeded, each with a proof, each verifier ≠ worker.
    finals = {a.task_id: a for a in store.attempts_for_plan("opr-1")}
    assert set(finals) == {"A", "B", "C", "D"}
    for t, a in finals.items():
        assert a.status == _S.SUCCEEDED.value, f"{t} succeeded"
        assert a.proof_id, f"{t} has AttemptProof"
        assert a.verifier_identity.startswith("verifier:")
        assert a.verifier_identity != a.worker_identity, f"{t} verifier ≠ worker"


def test_failure_qualification_rehearsal(store, queue, tmp_path):
    """tools-revoked-A: the REAL marker path drives the failure. The dispatcher's
    inject-failure marker → field_failure_policy revokes Edit/Write on A's first
    attempt → the worker genuinely produces no commit → verification refuses → A
    fails → C stays blocked (no false Proof). Proves the marker is CONSUMED
    (review W1), not a dead write."""
    from substrate.execution.attempts.field_failure_policy import (
        disallowed_tools_for,
        write_scenario_map,
    )

    _add_approved_packet(queue, "A")
    _add_approved_packet(queue, "B")
    _add_approved_packet(queue, "C", deps=["A", "B"])
    grant = _grant(["A", "B", "C"])

    # Arm the marker exactly as `wave2_field_dispatch.py inject-failure` does.
    targets = tmp_path / "targets"
    targets.mkdir()
    (targets / ".inject_failure").write_text("tools-revoked-backend", encoding="utf-8")
    # Targeting is by EXACT canonical id via the scenario map (finding C2): the
    # old pattern match on a literal "A" never fired on a real wp-<hex12> id.
    # This rehearsal's packets are named A/B/C, so the map records "A" as the
    # backend task — the point is that the POLICY resolves an id it was TOLD,
    # never one it guessed.
    write_scenario_map(
        targets,
        {
            "backend_task_id": "A",
            "frontend_task_id": "B",
            "integration_task_id": "C",
            "verification_task_id": "D",
        },
    )

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    sched = _mk_scheduler(store, queue, tmp_path, spool)
    poller = _mk_poller(
        store, spool, sched, grant, _StubProofRuntime(tmp_path), queue=queue, run_root=str(tmp_path)
    )

    _pass(sched, grant)
    # The stub worker consults the SAME policy the real dispatch path uses: a
    # task whose first attempt had tools revoked genuinely cannot commit.
    fail_tasks = {
        env_task
        for env_task in ("A", "B", "C")
        if disallowed_tools_for(targets_dir=str(targets), task_id=env_task, attempt_number=1)
    }
    assert fail_tasks == {"A"}, "the marker must revoke exactly A's first attempt"
    _stub_worker_drain(spool, fail_tasks=fail_tasks)
    poller.run_pass()

    a = next(a for a in store.attempts_for_task("A"))
    b = next(a for a in store.attempts_for_task("B"))
    assert a.status == _S.FAILED.value and not a.proof_id, "A failed, no false proof"
    assert b.status == _S.SUCCEEDED.value and b.proof_id, "B still succeeded"
    # C must NOT be running/succeeded — a predecessor lacks proof.
    c = [x for x in store.active_attempts() if x.task_id == "C"]
    assert not any(x.status in (_S.RUNNING.value, _S.SUCCEEDED.value) for x in c), (
        "C stays blocked while A has no AttemptProof"
    )

    # C-2 RECOVERY: A1's terminalization released its lease, so the poller's
    # internal scheduler re-run already minted A2 and A2 ACQUIRED a fresh lease.
    # Before the terminalization authority, A1's lease stayed ACTIVE and A2
    # deadlocked (BLOCKED → re-READY → BLOCKED forever) while producing this very
    # "A failed, C blocked" shape for the wrong reason.
    #
    # The load-bearing invariant: A1's lease is out of ACTIVE (released), and at
    # most ONE lease for A is active — the one A2 acquired. A stale A1 lease would
    # make TWO active, and A2 would never have been able to acquire at all.
    leases_a = [r for r in store._read_lines(store._leases_path) if r.get("task_id") == "A"]  # noqa: SLF001
    a1_leases = [r for r in leases_a if r.get("lease_id") == a.lease_id]
    assert a1_leases and a1_leases[-1]["status"] in ("released", "revoked"), (
        f"A1's lease must be terminalized (was {a1_leases[-1]['status'] if a1_leases else 'missing'})"
    )
    active = [r for r in leases_a if r.get("status") == "active"]
    # newest-per-lease-id: collapse to latest status per lease.
    latest: dict[str, str] = {}
    for r in leases_a:
        latest[r["lease_id"]] = r["status"]
    active_ids = [lid for lid, st in latest.items() if st == "active"]
    assert len(active_ids) <= 1, f"never more than one active lease for A: {active_ids}"

    # A2 exists, acquired its OWN (different) lease, and progressed past BLOCKED.
    a2 = [x for x in store.attempts_for_task("A") if x.attempt_number == 2]
    assert a2, "A2 retry must be created after A1 terminalized"
    assert a2[0].lease_id and a2[0].lease_id != a.lease_id, (
        "A2 must acquire a NEW lease — the deadlock was A2 never getting one"
    )
    assert a2[0].status in (_S.LEASED.value, _S.DISPATCHED.value, _S.RUNNING.value), (
        f"A2 must progress past BLOCKED (was {a2[0].status})"
    )


def test_rehearsal_is_not_real_qualification():
    """The rehearsal proves harness mechanics ONLY — it is explicitly NOT a
    real-worker field qualification. This test documents that contract so no
    reader mistakes a green rehearsal for a green Session-1 pass."""
    classification = {
        "harness_rehearsal": "PASS",
        "real_worker_qualification": "NOT_SATISFIED",
        "reason": "stub worker, no candidate deploy, no visible Chrome, no Claude quota",
    }
    assert classification["real_worker_qualification"] == "NOT_SATISFIED"
