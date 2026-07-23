"""Wave 2 C7 — the host-side field control-plane DRIVER is wired and drives the
full graph over a real scheduler + real signed spool + real poller.

This is the seam the field qualification depends on: nothing INSIDE the candidate
container drives a scheduler pass, so a host-side ``FieldControlPlaneDriver`` must
turn an ACTIVE grant in the shared ledger into signed dispatch envelopes, drain
worker results, and advance the canonical ledger. These tests prove the driver's
``run_cycle()`` does exactly that — with a CONTRACT-FAITHFUL STUB WORKER (no CLI,
no quota), exactly like ``test_wave2_harness_rehearsal.py`` but exercising the
driver's own composition rather than a hand-wired scheduler/poller.

They also pin the anti-W1 guarantee at the DRIVER level: with the
``.inject_failure`` marker armed, the driver's ``dispatch_fn`` genuinely revokes
Edit/Write on A's first attempt (so the failure-qualification pass injects a real
failure, never a false green).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver
from substrate.execution.attempts.records import ExecutionAttemptStatus
from substrate.execution.attempts.spool import DispatchSpool
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket

_S = ExecutionAttemptStatus
_RUN_SECRET = "field-driver-run-secret"


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


class _FakeSandbox:
    """Creates non-colliding fake worktrees (no real git — the stub worker never
    touches them). Exercises the LeaseManager's forbidden-workspace guard path."""

    def __init__(self, tmp_path):
        self._repo_root = str(tmp_path / "fixture")
        (tmp_path / "fixture").mkdir(exist_ok=True)
        self._i = 0

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        self._i += 1
        wt = f"{self._repo_root}-lease-{self._i}"
        return SimpleNamespace(
            worktree_path=wt,
            branch_name=f"br-{self._i}",
            base_commit="base",
            sandbox_id=f"sb-{self._i}",
        )

    def cleanup_sandbox(self, sandbox_id):
        pass


def _add_approved_packet(queue, pid, deps=None):
    pkt = WorkPacket(
        title=pid,
        user_intent=f"do {pid}",
        dependencies=deps or [],
        approval_gates=["execution_authorization_required"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
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


def _mutation_runner():
    def run(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    return run


def _stub_worker_drain(spool, *, fail_tasks=None):
    """Claim every signed dispatch and write a signed result — like the runner,
    minus the real Claude CLI. A dispatch carrying revoked Edit/Write tools
    (failure injection) reports empty artifacts = a genuine failure."""
    fail_tasks = fail_tasks or set()
    processed = 0
    while True:
        claimed = spool.claim_next()
        if claimed is None:
            return processed
        token, env = claimed
        # A dispatch whose envelope revoked Edit/Write CANNOT commit → genuine
        # failure. This mirrors the real worker: the tool revocation is on the
        # envelope, and the stub honors it faithfully.
        revoked = bool(env.disallowed_tools) or env.task_id in fail_tasks
        spool.complete(
            token,
            {
                "dispatch_id": env.dispatch_id,
                "attempt_id": env.attempt_id,
                "task_id": env.task_id,
                "package_hash": env.package_hash,
                "worker_result": {
                    "ok": not revoked,
                    "status": "failed" if revoked else "succeeded",
                    "files_changed": [] if revoked else [f"app/{env.task_id}.py"],
                    "commits": [] if revoked else [f"c-{env.task_id} implement"],
                    "isolated": True,
                },
            },
        )
        processed += 1


def _driver(store, queue, spool, tmp_path, targets_dir=""):
    return FieldControlPlaneDriver(
        store=store,
        work_queue=queue,
        spool=spool,
        sandbox_manager=_FakeSandbox(tmp_path),
        targets_dir=targets_dir or str(tmp_path / "targets"),
        mutation_runner=_mutation_runner(),
        lock_dir=str(tmp_path / "locks"),
    )


def _seed_active_grant(store, grant):
    """Persist the grant as ACTIVE so the driver's active_grants() sees it."""
    from substrate.execution.attempts.records import ExecutionAuthorizationGrant

    g = ExecutionAuthorizationGrant(
        decision_ref=grant.decision_ref,
        tenant_id=grant.tenant_id,
        plan_record_id=grant.plan_record_id,
        plan_version=grant.plan_version,
        objective_id=grant.objective_id,
        status="active",
        task_frontier=list(grant.task_frontier),
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        risk_ceiling="high",
        authorized_scope_hash="h",
        principal_id="u",
        membership_id="m",
    )
    stored, _created = store.create_grant_idempotent(g)
    return stored


def test_driver_admits_independent_frontier_first(store, queue, tmp_path):
    _add_approved_packet(queue, "A")
    _add_approved_packet(queue, "B")
    _add_approved_packet(queue, "C", deps=["A", "B"])
    _seed_active_grant(store, _grant(["A", "B", "C"]))

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)

    reports = driver.run_cycle()
    assert len(reports) == 1
    admitted_tasks = {store.get_attempt(a).task_id for a in reports[0].admitted}
    assert admitted_tasks == {"A", "B"}, "exactly the independent frontier admitted (2-concurrency)"
    # C has no attempt yet (blocked on A∧B proof).
    assert not any(a.task_id == "C" for a in store.active_attempts())


def test_driver_drives_full_graph_to_green(store, queue, tmp_path):
    _add_approved_packet(queue, "A")
    _add_approved_packet(queue, "B")
    _add_approved_packet(queue, "C", deps=["A", "B"])
    _add_approved_packet(queue, "D", deps=["C"])
    _seed_active_grant(store, _grant(["A", "B", "C", "D"]))

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)

    # Cycle 1 admits A,B. Worker drains. Cycle 2 verifies A,B and admits C. etc.
    for _ in range(8):  # bounded — the graph is 4 deep, converges well within
        driver.run_cycle()
        _stub_worker_drain(spool)
        finals = {a.task_id: a for a in store.attempts_for_plan("opr-1")}
        if set(finals) == {"A", "B", "C", "D"} and all(
            a.status == _S.SUCCEEDED.value for a in finals.values()
        ):
            break

    finals = {a.task_id: a for a in store.attempts_for_plan("opr-1")}
    assert set(finals) == {"A", "B", "C", "D"}
    for t, a in finals.items():
        assert a.status == _S.SUCCEEDED.value, f"{t} succeeded"
        assert a.proof_id, f"{t} has an AttemptProof"
        assert a.verifier_identity.startswith("verifier:"), f"{t} verifier identity"
        assert a.verifier_identity != a.worker_identity, f"{t} verifier ≠ worker (SoD)"


def test_driver_dispatch_fn_consults_failure_marker(store, queue, tmp_path):
    """The load-bearing anti-W1 assertion at the DRIVER level: arming the
    .inject_failure marker makes the driver's dispatch_fn revoke Edit/Write on
    A's first attempt → the worker genuinely cannot commit → A fails → C stays
    blocked. No marker → clean run."""
    _add_approved_packet(queue, "A")
    _add_approved_packet(queue, "B")
    _add_approved_packet(queue, "C", deps=["A", "B"])
    _seed_active_grant(store, _grant(["A", "B", "C"]))

    targets = tmp_path / "targets"
    targets.mkdir()
    (targets / ".inject_failure").write_text("tools-revoked-a", encoding="utf-8")

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path, targets_dir=str(targets))

    driver.run_cycle()  # admits A,B; A's envelope must carry revoked tools
    # Inspect the inbox envelopes the driver wrote: A revoked, B not.
    _stub_worker_drain(spool)  # honors the revocation
    driver.run_cycle()  # verify pass

    a = next(iter(store.attempts_for_task("A")))
    b = next(iter(store.attempts_for_task("B")))
    assert a.status == _S.FAILED.value and not a.proof_id, "A genuinely failed, no false proof"
    assert b.status == _S.SUCCEEDED.value and b.proof_id, "B still succeeded"
    c = [x for x in store.active_attempts() if x.task_id == "C"]
    assert not any(x.status in (_S.RUNNING.value, _S.SUCCEEDED.value) for x in c), (
        "C stays blocked while A has no AttemptProof"
    )


def test_driver_no_active_grant_is_idle_noop(store, queue, tmp_path):
    """No ACTIVE grant → the driver does nothing (no attempts, no dispatches)."""
    _add_approved_packet(queue, "A")
    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)
    reports = driver.run_cycle()
    assert reports == [], "no ACTIVE grant → no cycle work"
    assert not store.active_attempts()
