"""Wave 2 — lease acquisition is ATOMIC under real concurrency.

Round-7 adversarial review (F1, CRITICAL) reproduced TWO concurrent active
leases on a single Task through the production `LeaseManager.acquire` path:
5/25 trials directly, 1/20 through the real scheduler. `acquire()` read
`active_lease_for_task` OUTSIDE any lock and appended in a SEPARATE locked
call, and git-worktree creation sat in the unguarded window between them. Two
callers each observed "no active lease" and each appended.

Two active leases on one Task means two real workers mutating one workspace
under a single authorization, with two dispatch envelopes and two Proof paths —
it breaks the invariant that bounds the worktree, tool profile, credential
scope and billed worker quota.

The pre-existing `test_lease_acquire_and_one_active_per_task` could not see
this: it calls `acquire` twice SEQUENTIALLY, so it passes with or without the
fix. These tests use genuine OS-level concurrency against a SHARED store file
and FAIL on the pre-fix code.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.leases import LeaseError, LeaseManager
from substrate.execution.attempts.records import ExecutionAttempt
from substrate.execution.attempts.store import ExecutionAttemptStore


def _runner():
    def run(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    return run


class _SlowSandbox:
    """Sandbox whose worktree creation is SLOW.

    The real defect window is exactly the duration of `create_sandbox` (a git
    worktree add). Widening it deterministically is what turns a rare race into
    a reliable test, instead of depending on scheduler luck.
    """

    def __init__(self, repo_root: str, worktree: str, delay: float = 0.35) -> None:
        self._repo_root = repo_root
        self._worktree = worktree
        self._delay = delay
        self.cleaned: list[str] = []

    def create_sandbox(self, *, candidate_id, candidate_slug, agent_type):
        import time

        time.sleep(self._delay)
        return SimpleNamespace(
            worktree_path=self._worktree,
            branch_name=f"attempt/{candidate_id}",
            base_commit="base123",
            sandbox_id=f"sb-{candidate_id}",
        )

    def cleanup_sandbox(self, sandbox_id):
        self.cleaned.append(sandbox_id)
        return True


def _paths(tmp_path):
    return dict(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )


def _grant():
    return SimpleNamespace(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        tenant_id="tenant-a",
        task_frontier=["wp-a"],
        environment_classes=["git_worktree"],
        credential_scope_refs=[],
        cost_limit_usd=0.0,
        cost_enforceable=False,
    )


def _assignment():
    return SimpleNamespace(
        worker_identity="w",
        compute_node_id="vps",
        environment_class="git_worktree",
        tool_profile=["shell"],
        worker_agent_type="builder",
    )


def _child_acquire(paths: dict, worktree: str, attempt_id: str, barrier_path: str) -> None:
    """Acquire a lease for the SAME task in a separate OS process."""
    import time

    store = ExecutionAttemptStore(**paths)
    sandbox = _SlowSandbox(os.path.dirname(worktree), worktree)
    lm = LeaseManager(store, sandbox, mutation_runner=_runner())
    attempt = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    attempt.attempt_id = attempt_id

    # Rendezvous so both processes enter `acquire` at the same instant.
    deadline = time.time() + 10.0
    while not os.path.exists(barrier_path) and time.time() < deadline:
        time.sleep(0.005)

    try:
        lm.acquire(attempt=attempt, assignment=_assignment(), grant=_grant())
    except Exception:
        # Losing the race is the CORRECT outcome; the assertion lives in the
        # parent, which counts the durable rows.
        pass


def _active_leases_for(paths: dict, task_id: str) -> list[str]:
    latest: dict[str, dict] = {}
    path = paths["leases_path"]
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("task_id") == task_id:
                latest[row.get("lease_id", "")] = row
    return sorted(k for k, r in latest.items() if r.get("status") == "active")


def test_concurrent_acquire_yields_exactly_one_active_lease(tmp_path):
    """Two PROCESSES racing on one Task must produce exactly ONE active lease.

    Pre-fix this produced two. The check and the append are now one critical
    section (`append_lease_if_no_active`), so the loser fails closed.
    """
    paths = _paths(tmp_path)
    ExecutionAttemptStore(**paths)  # materialize the store files
    barrier = str(tmp_path / "go")

    ctx = mp.get_context("fork")
    procs = [
        ctx.Process(
            target=_child_acquire,
            args=(paths, str(tmp_path / f"wt{i}"), f"ea-{i}", barrier),
        )
        for i in (1, 2)
    ]
    for p in procs:
        p.start()
    open(barrier, "w").close()  # release both at once
    for p in procs:
        p.join(timeout=60)

    active = _active_leases_for(paths, "wp-a")
    assert len(active) == 1, f"expected exactly one active lease, got {active}"


def test_race_loser_cleans_up_its_worktree(tmp_path):
    """The process that loses the atomic claim must destroy its worktree.

    The worktree is created BEFORE the claim (to keep the critical section
    short), so the loser owns a sandbox it must not leak — teardown asserts
    `git worktree list` shows only the main tree.
    """
    paths = _paths(tmp_path)
    store = ExecutionAttemptStore(**paths)

    # Winner takes the only active lease.
    winner_sandbox = _SlowSandbox(str(tmp_path / "repo"), str(tmp_path / "wt1"), delay=0.0)
    lm1 = LeaseManager(store, winner_sandbox, mutation_runner=_runner())
    a1 = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    a1.attempt_id = "ea-1"
    lm1.acquire(attempt=a1, assignment=_assignment(), grant=_grant())

    # Loser: force it past the cheap pre-check so it reaches the atomic claim,
    # exactly as a real racing process does.
    loser_sandbox = _SlowSandbox(str(tmp_path / "repo"), str(tmp_path / "wt2"), delay=0.0)
    lm2 = LeaseManager(store, loser_sandbox, mutation_runner=_runner())
    a2 = ExecutionAttempt(task_id="wp-a", attempt_number=2)
    a2.attempt_id = "ea-2"

    class _BlindStore:
        """Pre-check sees nothing; the atomic claim still refuses."""

        def __init__(self, real):
            self._real = real

        def active_lease_for_task(self, task_id):
            return None

        def __getattr__(self, name):
            return getattr(self._real, name)

    lm2._store = _BlindStore(store)  # noqa: SLF001 — simulating the race window

    raised = False
    try:
        lm2.acquire(attempt=a2, assignment=_assignment(), grant=_grant())
    except Exception:
        raised = True

    assert raised, "loser must fail closed rather than acquire a second lease"
    assert loser_sandbox.cleaned == ["sb-ea-2"], (
        f"loser must clean up its worktree, cleaned={loser_sandbox.cleaned}"
    )
    assert len(_active_leases_for(paths, "wp-a")) == 1


def test_store_atomic_claim_refuses_second_active_lease(tmp_path):
    """Direct unit test of the store-level atomic claim."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    paths = _paths(tmp_path)
    store = ExecutionAttemptStore(**paths)

    store.append_lease_if_no_active(
        {"lease_id": "l-1", "task_id": "wp-a", "status": "active"}
    )
    try:
        store.append_lease_if_no_active(
            {"lease_id": "l-2", "task_id": "wp-a", "status": "active"}
        )
        raise AssertionError("second active lease for the same task must be refused")
    except AttemptStoreConflict:
        pass

    # A different Task is unaffected.
    store.append_lease_if_no_active(
        {"lease_id": "l-3", "task_id": "wp-b", "status": "active"}
    )
    assert _active_leases_for(paths, "wp-a") == ["l-1"]
    assert _active_leases_for(paths, "wp-b") == ["l-3"]

    # Once released, the task can be leased again.
    store.append_lease({"lease_id": "l-1", "task_id": "wp-a", "status": "released"})
    store.append_lease_if_no_active(
        {"lease_id": "l-4", "task_id": "wp-a", "status": "active"}
    )
    assert _active_leases_for(paths, "wp-a") == ["l-4"]


# ── F2: the admission lock must be keyed on the TASK, not the authorization ──


def test_admission_lock_key_is_the_task_not_the_grant(tmp_path):
    """Two grants differing only in plan_version must SERIALIZE on one Task.

    Round-7 review F2 (HIGH): `_scheduler_lease` is keyed
    `tenant:plan_record_id:version` — the AUTHORIZATION. Two grants for the same
    plan at different versions are both legitimately active and both name the
    same Task in their frontier, so they took DIFFERENT lock keys and never
    serialized against one another. The "single-writer scheduler" guarantee did
    not hold for the concurrent case that matters.

    The per-Task lock is keyed on the resource, so both contend on ONE key.
    """
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = ExecutionAttemptStore(**_paths(tmp_path))
    sched = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=lambda t: None),
        placement_fn=lambda **kw: None,
        lease_manager=None,
        compile_fn=lambda **kw: None,
        lock_dir=str(tmp_path / "locks"),
    )

    # Same tenant + same task, two different plan versions.
    keys = set()
    for _version in (1, 2):
        with sched._task_admission_lock("tenant-a", "wp-a"):  # noqa: SLF001
            pass
    for name in os.listdir(str(tmp_path / "locks")):
        if name.startswith("task-admission-"):
            keys.add(name)

    assert keys == {"task-admission-tenant-a_wp-a.lock"}, (
        f"both plan versions must contend on ONE task-keyed lock, got {sorted(keys)}"
    )


def test_task_admission_lock_actually_excludes(tmp_path):
    """The per-Task lock is a real interprocess mutex, not a no-op."""
    import time

    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = ExecutionAttemptStore(**_paths(tmp_path))
    lock_dir = str(tmp_path / "locks")

    def _hold(result_path: str) -> None:
        s = ExecutionAttemptStore(**_paths(tmp_path))
        sch = AttemptScheduler(
            s,
            work_queue=SimpleNamespace(get_packet=lambda t: None),
            placement_fn=lambda **kw: None,
            lease_manager=None,
            compile_fn=lambda **kw: None,
            lock_dir=lock_dir,
        )
        with sch._task_admission_lock("tenant-a", "wp-a"):  # noqa: SLF001
            with open(result_path, "a", encoding="utf-8") as fh:
                fh.write(f"enter {time.time()}\n")
            time.sleep(0.4)
            with open(result_path, "a", encoding="utf-8") as fh:
                fh.write(f"exit {time.time()}\n")

    marks = str(tmp_path / "marks.txt")
    ctx = mp.get_context("fork")
    procs = [ctx.Process(target=_hold, args=(marks,)) for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)

    lines = [ln.split() for ln in open(marks, encoding="utf-8").read().strip().split("\n")]
    events = [(w, float(t)) for w, t in lines]
    events.sort(key=lambda e: e[1])
    # Strict alternation proves mutual exclusion: enter, exit, enter, exit.
    assert [e[0] for e in events] == ["enter", "exit", "enter", "exit"], (
        f"critical sections overlapped — lock is not excluding: {events}"
    )
    assert store is not None


# ── N4: the admission verdict is an AUDIT RECORD and must not lie ───────────


def test_passing_checks_never_record_refusal_text():
    """A PASSING check must not carry the message that explains a REFUSAL.

    `check()` stored `detail` unconditionally while every call site passes the
    refusal message, so an ADMITTED verdict stated the exact opposite of what
    happened on 4 of 18 checks — e.g.

        PASS  task_in_authorized_frontier  task 'wp-a' not in the authorized frontier

    on a check that passed BECAUSE the task was in the frontier. This verdict is
    the durable audit record for a governed execution decision; a campaign whose
    root cause is "comments asserted guarantees nothing provided" cannot ship an
    audit trail with the same property (round-7 review N4).
    """
    from substrate.execution.attempts.admission import authorize_admission

    packet = SimpleNamespace(
        packet_id="wp-a",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "t", "target_kind": "k"},
        lineage={"plan_record_id": "opr-1"},
        requirements={"required_skill_refs": []},
        validation_plan="v",
        required_tools=[],
        rollback_plan="",
    )
    grant = SimpleNamespace(
        decision_ref="d",
        tenant_id="t",
        task_frontier=["wp-a"],
        plan_record_id="opr-1",
        plan_version=1,
        max_attempts_per_task=2,
        role_ids=[],
        allowed_tools=[],
        environment_classes=["git_worktree"],
        cost_limit_usd=0.0,
        cost_enforceable=False,
        verification_obligations=[],
        rollback_obligations=[],
        objective_id="goal-1",
    )
    attempt = SimpleNamespace(
        attempt_id="ea-1",
        task_id="wp-a",
        attempt_number=1,
        execution_authorization_ref="d",
    )
    verdict = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=SimpleNamespace(role_id="role-impl-op", allowed_tools=[]),
        verifier_role_id="role-verify-op",
        plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-1", status="approved"),
        attempts_for_task=lambda _t: [],
    )
    assert verdict.admitted

    lying = [c for c in verdict.checks if c.get("passed") and c.get("detail")]
    assert not lying, (
        "PASSING checks carry refusal text — the audit record states the "
        f"opposite of what happened: {[(c['check'], c['detail']) for c in lying]}"
    )

    # A refusal must still carry its full explanation.
    grant.task_frontier = []
    refused = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=SimpleNamespace(role_id="role-impl-op", allowed_tools=[]),
        verifier_role_id="role-verify-op",
        plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-1", status="approved"),
        attempts_for_task=lambda _t: [],
    )
    assert not refused.admitted
    assert refused.refusal_code == "task_outside_frontier"
    failed_with_detail = [
        c["check"] for c in refused.checks if not c["passed"] and c.get("detail")
    ]
    assert "task_in_authorized_frontier" in failed_with_detail, (
        "a refusal must still record WHY it refused"
    )


# ── C-1: the claim must be judged by the LEDGER, not by an exception ────────
#
# Round-8 independent review, CRITICAL. The store half of the F1 fix
# (`append_lease_if_no_active`) was correct, but `acquire` depended on
# `AttemptStoreConflict` PROPAGATING out of the governed runner — and every real
# runner CATCHES what `execute_fn` raises and returns a response object instead:
#   GovernedExecutionSpine._execute   (governed_spine.py:507)
#   MutationRouter.execute            (mutation_router.py:136-144)
#   route_mutation_degraded           (mutation_router.py:369-377)
#
# So on the production path the `except` never fired and `acquire` fell through
# to `return lease`, handing the race LOSER a lease that was never persisted,
# with its worktree leaked. That is WORSE than the original race: the loser
# believes it holds the lease, so `_admit` proceeds LEASED → compile → dispatch
# a real worker against a Task whose lease belongs to someone else. And since
# `release()`/`revoke()` both `get_lease(...)` and return silently on None, a
# never-persisted lease is invisible to terminalization — the leak is
# unrecoverable.
#
# Defect shape: confounder (d) — TEST WIRING INJECTED WHAT PRODUCTION NEVER
# SUPPLIES. The tests above use a raise-through runner, which no real runner is.
# These tests use runners that behave like the real ones.


def _swallowing_runner(**kw):
    """Behaves like every REAL governed runner: catches, returns, never raises."""
    fn = kw.get("execute_fn")
    try:
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)
    except Exception as exc:  # noqa: BLE001 — this swallowing IS the point
        return SimpleNamespace(success=False, output=str(exc))


def _refusing_runner(**kw):
    """Degraded mode: `execution_lease_mutate` is refused, execute_fn never runs."""
    return SimpleNamespace(success=False, output="degraded_mode_not_allowed")


class _BlindPreCheck:
    """Makes the cheap pre-check see nothing, as a real racing process does."""

    def __init__(self, real):
        self._real = real

    def active_lease_for_task(self, task_id):
        return None

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_race_loser_is_refused_even_when_the_runner_swallows_the_conflict(tmp_path):
    """The decisive test: a REALISTIC runner, not a raise-through one."""
    paths = _paths(tmp_path)
    store = ExecutionAttemptStore(**paths)
    sandbox = _SlowSandbox(str(tmp_path / "repo"), str(tmp_path / "wt"), delay=0.0)
    lm = LeaseManager(store, sandbox, mutation_runner=_swallowing_runner)

    a1 = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    a1.attempt_id = "ea-1"
    lm.acquire(attempt=a1, assignment=_assignment(), grant=_grant())

    lm._store = _BlindPreCheck(store)  # noqa: SLF001 — simulate the race window
    a2 = ExecutionAttempt(task_id="wp-a", attempt_number=2)
    a2.attempt_id = "ea-2"

    with pytest.raises(LeaseError):
        lm.acquire(attempt=a2, assignment=_assignment(), grant=_grant())

    assert len(_active_leases_for(paths, "wp-a")) == 1, (
        "a second lease persisted, or the loser was handed an unpersisted one"
    )
    assert "sb-ea-2" in sandbox.cleaned, (
        "the race loser leaked its worktree — release()/revoke() cannot reclaim "
        "a lease that was never persisted, so the leak is unrecoverable"
    )


def test_degraded_mutation_refusal_never_returns_a_phantom_lease(tmp_path):
    """`execution_lease_mutate` has degraded_mode_allowed=False.

    When the mutation is refused outright nothing persists — the caller must be
    REFUSED, not handed a lease object it would then dispatch a worker against.
    """
    paths = _paths(tmp_path)
    store = ExecutionAttemptStore(**paths)
    sandbox = _SlowSandbox(str(tmp_path / "repo"), str(tmp_path / "wt"), delay=0.0)
    lm = LeaseManager(store, sandbox, mutation_runner=_refusing_runner)

    attempt = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    attempt.attempt_id = "ea-1"

    with pytest.raises(LeaseError):
        lm.acquire(attempt=attempt, assignment=_assignment(), grant=_grant())

    assert _active_leases_for(paths, "wp-a") == [], "a phantom lease persisted"
    assert "sb-ea-1" in sandbox.cleaned, "worktree leaked on a refused mutation"


def test_acquire_is_judged_by_the_ledger_not_by_the_runners_return(tmp_path):
    """Even a runner that claims SUCCESS cannot conjure a lease.

    The durable ledger is the only authority. A runner returning success=True
    while nothing persisted must still refuse.
    """
    paths = _paths(tmp_path)
    store = ExecutionAttemptStore(**paths)
    sandbox = _SlowSandbox(str(tmp_path / "repo"), str(tmp_path / "wt"), delay=0.0)

    def _lying_runner(**kw):
        return SimpleNamespace(success=True, output="pretended to persist")

    lm = LeaseManager(store, sandbox, mutation_runner=_lying_runner)
    attempt = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    attempt.attempt_id = "ea-1"

    with pytest.raises(LeaseError):
        lm.acquire(attempt=attempt, assignment=_assignment(), grant=_grant())
    assert _active_leases_for(paths, "wp-a") == []
    assert "sb-ea-1" in sandbox.cleaned


# ── H-1: a REFUSED CAS transition must not look like a successful one ───────


def test_transition_refused_by_a_swallowing_runner_raises_not_returns_stale():
    """Round-8 H-1, executed and confirmed before fixing.

    `_transition` populated `result_holder` inside `execute_fn` and fell back to
    `return attempt` when the holder was empty. Because every real governed
    runner swallows what `execute_fn` raises, a REFUSED `transition_cas` left
    the holder empty and the method returned the STALE pre-transition attempt —
    indistinguishable from success. Callers then proceeded as though the attempt
    had advanced. Measured before the fix: an illegal ready→dispatched jump
    returned status 'ready' with the ledger unchanged and no signal at all.

    Same remedy as C-1: the durable ledger is the authority, not the runner's
    return value.
    """
    import tempfile

    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.store import AttemptStoreConflict

    tmp = tempfile.mkdtemp(prefix="h1-")
    store = ExecutionAttemptStore(
        attempts_path=os.path.join(tmp, "a.jsonl"),
        grants_path=os.path.join(tmp, "g.jsonl"),
        readiness_path=os.path.join(tmp, "r.jsonl"),
        leases_path=os.path.join(tmp, "l.jsonl"),
        assignments_path=os.path.join(tmp, "asn.jsonl"),
    )
    attempt = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    attempt.attempt_id = "ea-1"
    attempt.status = "ready"
    store.create_attempt_idempotent(attempt)

    sched = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=lambda _t: None),
        placement_fn=lambda **_k: None,
        lease_manager=None,
        compile_fn=lambda **_k: None,
        mutation_runner=_swallowing_runner,
        lock_dir=os.path.join(tmp, "locks"),
    )

    fresh = store.get_attempt("ea-1")
    with pytest.raises(AttemptStoreConflict):
        sched._transition(  # noqa: SLF001
            fresh, "dispatched", ("leased",), "scheduler", "illegal jump"
        )
    assert store.get_attempt("ea-1").status == "ready", "the ledger must be untouched"

    # A WELL-FORMED transition still commits — the fix must not refuse real work.
    fresh = store.get_attempt("ea-1")
    out = sched._transition(  # noqa: SLF001
        fresh,
        "leased",
        ("ready",),
        "scheduler",
        "placed + leased",
        updates={
            "assignment_id": "exasn-1",
            "lease_id": "lease-1",
            "verifier_role_id": "role-verify-op",
        },
    )
    assert out.status == "leased"
    assert store.get_attempt("ea-1").status == "leased"


def test_a_failed_ready_transition_does_not_abort_the_whole_scheduler_pass():
    """Self-found while auditing the H-1 fix — a fix that traded one defect for a worse one.

    `_transition` now RAISES when the ledger does not show the target status.
    Correct at the admission boundary. But `_create_attempt`'s `created → ready`
    call was unguarded, so the raise escaped the frontier loop and ABORTED
    `run_scheduler_pass` — killing work for every OTHER Task in the frontier,
    where before H-1 it degraded silently. A one-Task hiccup became a
    fleet-wide outage.

    Reproduced by swallowing only `execution_attempt_transition`:
        PASS ABORTED: AttemptStoreConflict ... → ready did not commit

    The Task is now dropped from THIS pass (it stays CREATED; the next pass
    retries it, and `create_attempt_idempotent` returns the same record so no
    duplicate is minted) and the pass continues.
    """
    import tempfile

    from substrate.execution.attempts.decisions import request_execution_authorization
    from substrate.execution.attempts.scheduler import AttemptScheduler

    def _plain(**kw):
        fn = kw.get("execute_fn")
        try:
            r = fn() if fn else ("", True)
            out, ok = r if isinstance(r, tuple) else (r, True)
            return SimpleNamespace(success=ok, output=out)
        except Exception as exc:  # noqa: BLE001
            return SimpleNamespace(success=False, output=str(exc))

    def _swallow_only_transitions(**kw):
        if kw.get("mutation_name") == "execution_attempt_transition":
            return SimpleNamespace(success=False, output="swallowed conflict")
        return _plain(**kw)

    tmp = tempfile.mkdtemp(prefix="pass-abort-")
    store = ExecutionAttemptStore(
        attempts_path=os.path.join(tmp, "a.jsonl"),
        grants_path=os.path.join(tmp, "g.jsonl"),
        readiness_path=os.path.join(tmp, "r.jsonl"),
        leases_path=os.path.join(tmp, "l.jsonl"),
        assignments_path=os.path.join(tmp, "asn.jsonl"),
    )
    plan = SimpleNamespace(
        plan_record_id="opr-1",
        objective_id="goal-1",
        graph_version=1,
        status="approved",
        workpacket_ids=["wp-a"],
        work_scope={"tenant_id": "t", "target_kind": "k"},
    )
    grant, _ = request_execution_authorization(
        store,
        plan=plan,
        task_frontier=["wp-a"],
        tenant_id="t",
        principal_id="u",
        membership_id="m",
        conversation_id="c",
        correlation_id="c",
        requested_by="op",
        mutation_runner=_plain,
    )
    grant.status = "active"
    store.update_grant_cas(grant, expected_record_version=grant.record_version)

    packet = SimpleNamespace(
        packet_id="wp-a",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "t", "target_kind": "k"},
        lineage={"plan_record_id": "opr-1"},
        requirements={"required_skill_refs": []},
        validation_plan="v",
        required_tools=[],
        rollback_plan="",
    )
    sched = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=lambda _t: packet),
        placement_fn=lambda **_k: None,
        lease_manager=None,
        compile_fn=lambda **_k: None,
        mutation_runner=_swallow_only_transitions,
        lock_dir=os.path.join(tmp, "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-1", status="approved"
        ),
    )

    # Must NOT raise: the pass completes and simply creates nothing this round.
    report = sched.run_scheduler_pass(store.get_grant(grant.decision_ref))
    assert report.acquired
    assert report.attempts_created == [], (
        "an attempt that could not be made READY must not be reported as created"
    )


def test_an_attempt_stranded_at_created_is_recovered_by_a_later_pass():
    """Self-found: the N-1 fix's own comment was false until this branch existed.

    `_create_attempt` returns None when its created→READY transition loses a
    CAS race, leaving the attempt CREATED "for the next pass to retry". But
    CREATED is not terminal, so the frontier loop's
    `if any(not a.is_terminal() ...): continue` guard skipped straight past it —
    the attempt BLOCKED ITS OWN RETRY and the Task was stranded forever, even
    after the interference cleared.

    Measured before this fix (pass 2 entirely healthy):
        pass1: [('ea-9b6cd2755', 'created', 1)]
        pass2: [('ea-9b6cd2755', 'created', 1)]   <- never recovers

    A later pass now promotes the orphan instead of skipping it, and mints no
    duplicate.
    """
    import tempfile

    from substrate.execution.attempts.decisions import request_execution_authorization
    from substrate.execution.attempts.scheduler import AttemptScheduler

    def _plain(**kw):
        fn = kw.get("execute_fn")
        try:
            r = fn() if fn else ("", True)
            out, ok = r if isinstance(r, tuple) else (r, True)
            return SimpleNamespace(success=ok, output=out)
        except Exception as exc:  # noqa: BLE001
            return SimpleNamespace(success=False, output=str(exc))

    class _BlockTransitions:
        """Swallows transitions while `block` is set — the real runner shape."""

        def __init__(self):
            self.block = True

        def __call__(self, **kw):
            if self.block and kw.get("mutation_name") == "execution_attempt_transition":
                return SimpleNamespace(success=False, output="swallowed conflict")
            return _plain(**kw)

    tmp = tempfile.mkdtemp(prefix="stranded-")
    store = ExecutionAttemptStore(
        attempts_path=os.path.join(tmp, "a.jsonl"),
        grants_path=os.path.join(tmp, "g.jsonl"),
        readiness_path=os.path.join(tmp, "r.jsonl"),
        leases_path=os.path.join(tmp, "l.jsonl"),
        assignments_path=os.path.join(tmp, "asn.jsonl"),
    )
    plan = SimpleNamespace(
        plan_record_id="opr-1",
        objective_id="goal-1",
        graph_version=1,
        status="approved",
        workpacket_ids=["wp-a"],
        work_scope={"tenant_id": "t", "target_kind": "k"},
    )
    grant, _ = request_execution_authorization(
        store,
        plan=plan,
        task_frontier=["wp-a"],
        tenant_id="t",
        principal_id="u",
        membership_id="m",
        conversation_id="c",
        correlation_id="c",
        requested_by="op",
        mutation_runner=_plain,
    )
    grant.status = "active"
    store.update_grant_cas(grant, expected_record_version=grant.record_version)

    packet = SimpleNamespace(
        packet_id="wp-a",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "t", "target_kind": "k"},
        lineage={"plan_record_id": "opr-1"},
        requirements={"required_skill_refs": []},
        validation_plan="v",
        required_tools=[],
        rollback_plan="",
    )
    runner = _BlockTransitions()
    sched = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=lambda _t: packet),
        placement_fn=lambda **_k: None,
        lease_manager=None,
        compile_fn=lambda **_k: None,
        mutation_runner=runner,
        lock_dir=os.path.join(tmp, "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-1", status="approved"
        ),
    )

    # Pass 1: the transition is swallowed → the attempt is stranded at CREATED.
    sched.run_scheduler_pass(store.get_grant(grant.decision_ref))
    after_1 = store.attempts_for_task("wp-a")
    assert len(after_1) == 1 and after_1[0].status == "created"

    # Pass 2: interference cleared. The orphan must be RECOVERED, not skipped.
    runner.block = False
    sched.run_scheduler_pass(store.get_grant(grant.decision_ref))
    after_2 = store.attempts_for_task("wp-a")

    assert len(after_2) == 1, (
        f"a duplicate attempt was minted for the stranded Task: "
        f"{[(a.attempt_id, a.status) for a in after_2]}"
    )
    assert after_2[0].status != "created", (
        "the attempt is STILL stranded at CREATED after a healthy pass — it is "
        "blocking its own retry and the Task will never execute"
    )
