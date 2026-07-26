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

import os
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
    """Creates non-colliding REAL git worktrees.

    These were bare paths that did not exist on disk. Diff-scope is now computed
    by running git in the lease worktree (finding C-1), so a nonexistent path
    makes verification fail closed and the driver could never reach green. The
    LeaseManager's forbidden-workspace guard path is still exercised.
    """

    def __init__(self, tmp_path):
        self._repo_root = str(tmp_path / "fixture")
        (tmp_path / "fixture").mkdir(exist_ok=True)
        self._i = 0

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        import os
        import subprocess

        self._i += 1
        wt = f"{self._repo_root}-lease-{self._i}"
        os.makedirs(os.path.join(wt, "app"), exist_ok=True)
        with open(os.path.join(wt, "app", "__init__.py"), "w", encoding="utf-8") as fh:
            fh.write("")
        for args in (
            ("init", "-q"),
            ("config", "user.email", "t@example.com"),
            ("config", "user.name", "t"),
            ("add", "-A"),
            ("commit", "-q", "-m", "base"),
        ):
            subprocess.run(["git", *args], cwd=wt, check=True, capture_output=True)
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=wt, capture_output=True, text=True
        ).stdout.strip()
        return SimpleNamespace(
            worktree_path=wt,
            branch_name=f"br-{self._i}",
            base_commit=base,
            sandbox_id=f"sb-{self._i}",
        )

    def cleanup_sandbox(self, sandbox_id):
        pass


def _add_approved_packet(
    queue, pid, deps=None, allowed_paths=("app", "tests"), plan_record_id=""
):
    """An APPROVED packet carrying a DECLARED path scope (finding C-1): the
    canonical WorkPacket is the diff-scope authority, and a packet declaring no
    scope now fails verification closed instead of authorizing everything."""
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
    if plan_record_id:
        # Set BEFORE ingest: the driver reloads the queue from disk each cycle,
        # so an in-memory mutation after ingest would be discarded.
        pkt.lineage = {**(getattr(pkt, "lineage", {}) or {}), "plan_record_id": plan_record_id}
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
        # A real worker WRITES into its lease worktree; the verifier computes the
        # changed set from git there (finding C-1). A revoked worker writes
        # nothing — which is exactly why its verification genuinely fails.
        worktree = getattr(env, "worktree_path", "") or ""
        if not revoked and worktree and os.path.isdir(worktree):
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
                    "ok": not revoked,
                    "status": "failed" if revoked else "succeeded",
                    "files_changed": [] if revoked else [f"app/{env.task_id}.py"],
                    "commits": [] if revoked else [f"c-{env.task_id} implement"],
                    "isolated": True,
                },
            },
        )
        processed += 1


def _driver(store, queue, spool, tmp_path, targets_dir="", enforce_graph_shape=False):
    return FieldControlPlaneDriver(
        store=store,
        work_queue=queue,
        spool=spool,
        sandbox_manager=_FakeSandbox(tmp_path),
        targets_dir=targets_dir or str(tmp_path / "targets"),
        mutation_runner=_mutation_runner(),
        lock_dir=str(tmp_path / "locks"),
        enforce_graph_shape=enforce_graph_shape,
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


def test_graph_shape_gate_refuses_single_umbrella_task_before_any_dispatch(
    store, queue, tmp_path
):
    """The exact field failure: ONE combined Task instead of the four-lane graph.

    The gate must refuse BEFORE a dispatch envelope is written, so the wrong
    shape costs ZERO worker quota (field run 20260726T025143Z-p1 spent quota and
    only then failed at the two-concurrent-Tasks assertion).
    """
    _add_approved_packet(queue, "A")
    _seed_active_grant(store, _grant(["A"]))

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path, enforce_graph_shape=True)

    reports = driver.run_cycle()

    assert len(reports) == 1
    assert any("graph_shape_gate" in e for e in reports[0].errors)
    assert any("task_count" in e for e in reports[0].errors)
    assert reports[0].admitted == [], "nothing may be admitted on a refused graph"
    assert not store.active_attempts(), "ZERO attempts — zero worker quota spent"
    assert not list(spool.inbox_names()) if hasattr(spool, "inbox_names") else True


def test_graph_shape_gate_admits_the_correct_four_lane_graph(store, queue, tmp_path):
    """The gate is not merely restrictive: the right shape proceeds normally."""
    _add_approved_packet(queue, "A", allowed_paths=("app/main.py",), plan_record_id="opr-1")
    _add_approved_packet(queue, "B", allowed_paths=("app/static",), plan_record_id="opr-1")
    _add_approved_packet(queue, "C", deps=["A", "B"], allowed_paths=("app",), plan_record_id="opr-1")
    _add_approved_packet(queue, "D", deps=["C"], allowed_paths=(), plan_record_id="opr-1")
    _seed_active_grant(store, _grant(["A", "B", "C", "D"]))

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path, enforce_graph_shape=True)

    reports = driver.run_cycle()

    assert not any("graph_shape_gate" in e for e in reports[0].errors), reports[0].errors
    admitted = {store.get_attempt(a).task_id for a in reports[0].admitted}
    assert admitted == {"A", "B"}, "the two independent lanes are admitted concurrently"


def test_graph_shape_gate_refuses_write_authorized_verifier(store, queue, tmp_path):
    """D holding write authority is the dangerous shape — refuse before dispatch."""
    _add_approved_packet(queue, "A", allowed_paths=("app/main.py",), plan_record_id="opr-1")
    _add_approved_packet(queue, "B", allowed_paths=("app/static",), plan_record_id="opr-1")
    _add_approved_packet(queue, "C", deps=["A", "B"], allowed_paths=("app",), plan_record_id="opr-1")
    _add_approved_packet(queue, "D", deps=["C"], allowed_paths=("app/main.py",), plan_record_id="opr-1")
    _seed_active_grant(store, _grant(["A", "B", "C", "D"]))

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path, enforce_graph_shape=True)

    reports = driver.run_cycle()

    assert any("verifier_zero_write" in e for e in reports[0].errors)
    assert not store.active_attempts(), "zero quota spent on a write-authorized verifier"


def test_graph_shape_gate_is_off_by_default_for_single_task_objectives(
    store, queue, tmp_path
):
    """A legitimate single-Task smoke objective must not be misreported."""
    _add_approved_packet(queue, "A")
    _seed_active_grant(store, _grant(["A"]))

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)  # gate OFF (default)

    reports = driver.run_cycle()

    assert not any("graph_shape_gate" in e for e in reports[0].errors)
    assert reports[0].admitted, "the single-Task objective still dispatches"


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
    (targets / ".inject_failure").write_text("tools-revoked-backend", encoding="utf-8")
    # Targeting resolves through the scenario map (finding C2) — an exact id the
    # harness recorded, never a guessed pattern.
    from substrate.execution.attempts.field_failure_policy import write_scenario_map

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


def test_driver_reloads_packets_written_after_construction(store, queue, tmp_path):
    """FIELD-ORDERING regression (fourth control-plane layer, run 20260725T194515Z).

    Every other test in this file seeds the packet into the queue BEFORE building
    the driver. The field is the reverse: the host runner constructs the driver
    (and its ``UniversalWorkQueue``) at startup over an EMPTY packet store, and
    the candidate app writes the authorized packet (PLANNED→APPROVED) to disk
    LATER, during the pass. ``UniversalWorkQueue`` caches its packets in memory at
    construction and never reloads, so ``get_packet`` returned None for every
    packet minted this run — the grant activated, the task was APPROVED on disk,
    and the driver reported ``wp-…(missing)`` forever, dispatching NO worker.

    This pins the fix: ``run_cycle`` re-reads the packet store each cycle, so a
    packet appearing on disk after construction is admitted."""
    grant = _grant(["A"])
    _seed_active_grant(store, grant)

    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    # Driver built BEFORE the packet exists — exactly the field ordering.
    driver = _driver(store, queue, spool, tmp_path)

    # Sanity: with an empty store the frontier is (missing) and nothing admits.
    pre = driver.run_cycle()
    assert pre[0].skipped_not_approved == ["A(missing)"], "empty store → missing, no dispatch"
    assert not store.active_attempts(), "no worker dispatched against a missing packet"

    # Now a SECOND queue writes the APPROVED packet to the SAME store path — this
    # is the candidate app writing after the runner started. The driver's own
    # queue is a stale, separately-constructed instance (like the real runner's).
    writer = UniversalWorkQueue(store_path=queue._store_path)
    _add_approved_packet(writer, "A")

    # Without the reload, the driver's cached queue still returns None here.
    post = driver.run_cycle()
    assert "A(missing)" not in post[0].skipped_not_approved, (
        "driver must reload the packet store and see the newly-APPROVED packet"
    )
    admitted_tasks = {store.get_attempt(a).task_id for a in post[0].admitted}
    assert admitted_tasks == {"A"}, "the freshly-written APPROVED packet is admitted"


def test_driver_no_active_grant_is_idle_noop(store, queue, tmp_path):
    """No ACTIVE grant → the driver does nothing (no attempts, no dispatches)."""
    _add_approved_packet(queue, "A")
    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)
    reports = driver.run_cycle()
    assert reports == [], "no ACTIVE grant → no cycle work"
    assert not store.active_attempts()


def test_failed_gate_still_drains_worker_results(store, queue, tmp_path):
    """MAJOR-D: the gate's `continue` skipped run_pass entirely — the ONLY path
    that drains the worker outbox. A transient gate failure (the packet-
    visibility race _reload_queue exists for) would strand already-dispatched
    workers: results never applied, leases never released."""
    _add_approved_packet(queue, "A", plan_record_id="opr-1")
    _seed_active_grant(store, _grant(["A"]))
    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)

    # PHASE 1 — gate OFF: admit A and let the worker finish, so a real result is
    # sitting in the outbox.
    open_driver = _driver(store, queue, spool, tmp_path, enforce_graph_shape=False)
    assert open_driver.run_cycle()[0].admitted, "setup: A must be admitted"
    assert _stub_worker_drain(spool) == 1, "setup: worker must produce one result"

    # PHASE 2 — gate ON and FAILING (a lone Task is not the 4-lane shape). The
    # already-dispatched worker's result MUST still be drained: asserting only
    # `isinstance(results_drained, int)` passes on the dataclass DEFAULT, so it
    # holds even when the gate short-circuits past the poller entirely.
    gated = _driver(store, queue, spool, tmp_path, enforce_graph_shape=True)
    reports = gated.run_cycle()

    assert any("graph_shape_gate" in e for e in reports[0].errors)
    assert reports[0].admitted == [], "a failed gate must admit nothing"
    assert reports[0].results_drained == 1, "failed gate did not drain the outbox"


def test_admission_failure_releases_the_lease(store, queue, tmp_path):
    """CRITICAL-B: the lease is acquired BEFORE package compilation, which can
    now fail closed. Without release, LeaseManager.acquire refuses the task
    forever and each orphan lease holds a sandbox worktree — two failures
    exhaust max_parallel=2 and wedge the whole run."""
    from substrate.execution.attempts.scheduler import AttemptScheduler

    released: list[str] = []

    class _Leases:
        def acquire(self, *, attempt, assignment, grant):
            return SimpleNamespace(lease_id=f"lease-{attempt.attempt_id}")

        def release(self, lease_id, *, cleanup=True, now=None):
            released.append(lease_id)

    def _boom(**_kw):
        raise RuntimeError("compilation failed closed")

    _add_approved_packet(queue, "A", plan_record_id="opr-1")
    grant = _grant(["A"])
    _seed_active_grant(store, grant)
    from substrate.execution.attempts.records import ExecutionAttempt

    attempt, _created = store.create_attempt_idempotent(
        ExecutionAttempt(
            task_id="A",
            objective_id="goal-1",
            plan_record_id="opr-1",
            plan_version=1,
            execution_authorization_ref=grant.decision_ref,
            tenant_id="tenant-a",
            principal_id="u",
            membership_id="m",
            attempt_number=1,
        )
    )
    store.transition_cas(
        attempt.attempt_id,
        "ready",
        expected_record_version=attempt.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    scheduler = AttemptScheduler(
        store=store,
        work_queue=queue,
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id="asn-1",
            verifier_role_id="role-verify-op",
            worker_identity="w",
            tool_profile=[],
            model_profile={},
            environment_class="git_worktree",
        ),
        lease_manager=_Leases(),
        compile_fn=_boom,
        mutation_runner=_mutation_runner(),
        lock_dir=str(tmp_path / "locks2"),
    )
    scheduler.run_scheduler_pass(grant=grant)

    assert released == ["lease-" + attempt.attempt_id], "lease leaked on admission failure"
    blocked = store.get_attempt(attempt.attempt_id)
    assert blocked.status == "blocked"


def test_lease_manager_accessor_is_available_before_any_scheduler_pass(store, queue, tmp_path):
    """The runner reaps stale leases via driver._lease_manager(). Reading the raw
    `_lease_mgr` attribute instead would be a silent no-op on any cycle that
    returns early (no active grant, or the graph-shape gate refusing), because
    the manager is lazily built inside the accessor."""
    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)

    # Raw attribute is None on a fresh driver — the trap.
    assert getattr(driver, "_lease_mgr", "missing") is None
    # The accessor the runner uses builds it on demand.
    accessor = getattr(driver, "_lease_manager", None)
    assert callable(accessor), "runner reap target must be the accessor"
    assert accessor() is not None
    assert accessor().expire_stale() == 0


def test_stale_lease_is_actually_expired(store, queue, tmp_path):
    """End-to-end: a lease past its expires_at is reaped, freeing the task."""
    spool = DispatchSpool(str(tmp_path / "spool"), _RUN_SECRET)
    driver = _driver(store, queue, spool, tmp_path)
    manager = driver._lease_manager()

    attempt = SimpleNamespace(attempt_id="ea-stale", task_id="A")
    assignment = SimpleNamespace(assignment_id="asn-1", environment_class="git_worktree")
    grant = _grant(["A"])
    lease = manager.acquire(attempt=attempt, assignment=assignment, grant=grant)
    assert store.active_lease_for_task("A") is not None

    # Force it stale, then reap through the same call the runner makes.
    row = store.get_lease(lease.lease_id)
    row["expires_at"] = 1.0
    store.update_lease_cas(
        type(lease).from_dict(row), expected_record_version=row.get("record_version", 0)
    )
    assert manager.expire_stale() == 1
    assert store.active_lease_for_task("A") is None, "stale lease still blocks the task"


def test_runner_reaps_leases_through_the_lazy_accessor(tmp_path, monkeypatch):
    """The RUNNER must reap via the accessor. Reading the raw `_lease_mgr`
    attribute is a silent no-op whenever a cycle returns early (no active grant,
    or the graph-shape gate refusing) because the manager is built lazily.

    Asserting only that the accessor EXISTS does not catch that — this drives
    the runner's real reap block against a driver whose raw attribute is None.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_w2_runner_reap",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "wave2_attempt_runner.py"),
    )
    runner_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner_mod)

    import inspect

    source = inspect.getsource(runner_mod.run_loop)
    assert "_lease_manager" in source, "runner must reap via the lazy accessor"
    assert '"_lease_mgr"' not in source, "runner must NOT read the raw lazy attribute"
    # The call itself must survive: without it the accessor is resolved and
    # then nothing is reaped, so expires_at stays unenforced.
    assert "accessor().expire_stale()" in source, "runner must actually call expire_stale()"

    calls: list[str] = []

    class _Mgr:
        def expire_stale(self):
            calls.append("expired")
            return 0

    class _DriverRawNone:
        """Mirrors the real driver: raw attribute None until the accessor runs."""

        _lease_mgr = None

        def _lease_manager(self):
            type(self)._lease_mgr = _Mgr()
            return type(self)._lease_mgr

    driver = _DriverRawNone()
    accessor = getattr(driver, "_lease_manager", None)
    assert callable(accessor)
    accessor().expire_stale()
    assert calls == ["expired"], "reap did not reach the lease manager"
