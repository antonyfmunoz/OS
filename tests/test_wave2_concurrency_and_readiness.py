"""Wave 2 R3 — real two-worker concurrency, spool lifecycle, readiness exit.

Pins finding C3 and SEC-C3:

* The runner claimed ONE envelope per iteration and ran the worker synchronously,
  so A and B never overlapped — "exactly-2 concurrency" was unobtainable — and
  because both envelopes were stamped ``expires_at = now + timeout_seconds`` at
  dispatch, B was quarantined as expired while A held the whole budget. Nothing
  reaped the spool, so B's attempt stranded in DISPATCHED forever, permanently
  consuming a concurrency slot.
* ``deploy_candidate`` recorded readiness and then ignored it: a candidate that
  never came up still exited 0.

Overlap is proven by MEASURED wall-clock, not by inspecting the code: each stub
worker records its own start/finish and the test asserts
``max(started) < min(finished)``.
"""

from __future__ import annotations

import json
import os
import threading
import time
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

_SECRET = "r3-run-secret"


def _envelope(n: int, *, expires_in: float = 1800.0, timeout: int = 600) -> DispatchEnvelope:
    return DispatchEnvelope(
        dispatch_id=f"d-ea-{n}-{n:04d}",
        attempt_id=f"ea-{n}",
        task_id=f"wp-{n}",
        worktree_path=f"/tmp/wt-{n}",
        nonce=f"nonce-{n}",
        sequence=n,
        expires_at=time.time() + expires_in,
        timeout_seconds=timeout,
    )


# ── real concurrency ────────────────────────────────────────────────────────



def _prod_role_resolver(_packet=None):
    """The role shape PRODUCTION always supplies (field_control_plane.py:361).

    The admission authority refuses `role_not_authorized` when no role resolves.
    A positive-control test that omits the resolver would then be refused for a
    reason it is not testing, and its "was admitted" assertion could no longer
    fail for the right cause. Passing the production shape keeps these controls
    load-bearing.
    """
    from types import SimpleNamespace

    return SimpleNamespace(
        role_id="role-impl-op", allowed_tools=["shell"], prohibited_skill_ids=[]
    )


def test_two_workers_overlap_in_wall_clock(tmp_path):
    """A and B must be RUNNING at the same instant.

    The old sequential loop made this impossible; the assertion is on measured
    timestamps so it cannot pass by inspection.
    """
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    spool.enqueue(_envelope(1))
    spool.enqueue(_envelope(2))

    started: dict[str, float] = {}
    finished: dict[str, float] = {}
    lock = threading.Lock()
    barrier = threading.Barrier(2, timeout=10)

    def _worker(token, env):
        with lock:
            started[env.attempt_id] = time.time()
        # Both workers must be inside this window simultaneously, or the barrier
        # times out — which IS the sequential-execution failure mode.
        barrier.wait()
        time.sleep(0.05)
        with lock:
            finished[env.attempt_id] = time.time()
        spool.complete(token, {"attempt_id": env.attempt_id, "worker_result": {"ok": True}})

    claims = [spool.claim_next(), spool.claim_next()]
    assert all(c is not None for c in claims), "both envelopes must be claimable"

    threads = [threading.Thread(target=_worker, args=c) for c in claims]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(started) == 2 and len(finished) == 2
    assert max(started.values()) < min(finished.values()), (
        "A and B did not overlap: max(started) must precede min(finished)"
    )


def test_each_claim_is_exclusive(tmp_path):
    """Two workers claim DIFFERENT envelopes — never the same one twice."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    spool.enqueue(_envelope(1))
    spool.enqueue(_envelope(2))

    first = spool.claim_next()
    second = spool.claim_next()
    third = spool.claim_next()

    assert first is not None and second is not None
    assert first[1].attempt_id != second[1].attempt_id, "the same envelope was claimed twice"
    assert third is None, "only the enqueued envelopes may be claimed"


def test_concurrent_claims_never_duplicate(tmp_path):
    """Racing claimers must partition the inbox — os.replace is the arbiter."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    for n in range(8):
        spool.enqueue(_envelope(n))

    seen: list[str] = []
    lock = threading.Lock()

    def _claimer():
        while True:
            claimed = spool.claim_next()
            if claimed is None:
                return
            with lock:
                seen.append(claimed[1].attempt_id)

    threads = [threading.Thread(target=_claimer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(seen) == 8, f"expected 8 claims, got {len(seen)}"
    assert len(set(seen)) == 8, f"duplicate claims: {seen}"


# ── expiry governs CLAIMABILITY only ────────────────────────────────────────


def test_claimed_envelope_does_not_expire_while_executing(tmp_path):
    """Once claimed, an envelope is the worker's — a long sibling run must not
    invalidate it. This is the exact B-quarantined-by-A failure."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    # A claim budget that elapses DURING execution.
    spool.enqueue(_envelope(1, expires_in=0.3))
    claimed = spool.claim_next()
    assert claimed is not None
    token, env = claimed

    time.sleep(0.5)  # the claim deadline passes while "executing"

    # The result is still accepted: expiry is not re-checked after the claim.
    spool.complete(token, {"attempt_id": env.attempt_id, "worker_result": {"ok": True}})
    results = spool.drain_results()
    assert len(results) == 1 and results[0]["attempt_id"] == "ea-1"


def test_stale_unclaimed_envelope_is_reaped(tmp_path):
    """An UNCLAIMED envelope past its claim budget is quarantined, not left to
    strand its attempt in DISPATCHED forever."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    spool.enqueue(_envelope(1, expires_in=-1.0))  # already past its deadline
    spool.enqueue(_envelope(2, expires_in=1800.0))

    reaped = spool.reap_stale_unclaimed()
    assert len(reaped) == 1, f"exactly the stale envelope should be reaped: {reaped}"

    # The live one is still claimable.
    claimed = spool.claim_next()
    assert claimed is not None and claimed[1].attempt_id == "ea-2"


# ── crash recovery without duplicate attempts ───────────────────────────────


def test_abandoned_inflight_is_recovered_without_duplicating_the_attempt(tmp_path):
    """A crashed worker's claim returns to the inbox and is re-claimable with the
    SAME attempt id — recovery must not mint a second active attempt."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    spool.enqueue(_envelope(1))
    claimed = spool.claim_next()
    assert claimed is not None
    original_attempt = claimed[1].attempt_id

    # The worker "crashes": the claim sits in inflight with no result.
    assert spool.claim_next() is None, "nothing else should be claimable"

    recovered = spool.recover_stale_inflight(older_than_seconds=0.0)
    assert len(recovered) == 1, "the abandoned claim must be recovered"

    reclaimed = spool.claim_next()
    assert reclaimed is not None
    assert reclaimed[1].attempt_id == original_attempt, (
        "recovery must reuse the SAME attempt id, not mint a duplicate"
    )


def test_live_inflight_is_not_stolen(tmp_path):
    """A slow-but-live worker must never have its claim taken away."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    spool.enqueue(_envelope(1))
    assert spool.claim_next() is not None

    recovered = spool.recover_stale_inflight(older_than_seconds=3600.0)
    assert recovered == [], "a recent claim must not be recovered"
    assert spool.claim_next() is None


# ── readiness controls the exit code ────────────────────────────────────────


def _dispatcher():
    import importlib.util
    import sys

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "wave2_field_dispatch.py",
    )
    spec = importlib.util.spec_from_file_location("_w2fd_r3", path)
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec_module: a module-level @dataclass (QualificationVerdict)
    # makes dataclasses resolve `sys.modules[cls.__module__]` during class
    # construction. An unregistered synthetic module name resolves to None and
    # crashes the import. Registering it is the documented-correct use of
    # module_from_spec and is idempotent across repeated loads in this suite.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_not_ready_deploy_declares_failure():
    """A deploy whose readiness is False must NOT report success."""
    mod = _dispatcher()
    assert mod._result_declares_failure({"deploy_ok": False, "failure_reason": "NOT READY"})
    assert not mod._result_declares_failure({"deploy_ok": True})


@pytest.mark.parametrize(
    "result",
    [
        {"started": False, "reason": "runner did not come up"},
        {"armed": False, "invalid_reason": "no scenario map"},
        {"ok": False, "refused": "candidate is not ready"},
        {"refused": "beast collector worktree is not at the candidate commit"},
        {"results": [{"ok": True}, {"ok": False}]},
    ],
)
def test_failed_verdicts_are_detected(result):
    """Every failure shape a command can return must exit non-zero."""
    assert _dispatcher()._result_declares_failure(result)


@pytest.mark.parametrize(
    "result",
    [
        {"deploy_ok": True},
        {"started": True, "isolation_ok": True},
        {"armed": True, "target_task_id": "wp-abc123"},
        {"results": [{"ok": True}, {"ok": True}]},
        {},  # a command with no verdict key keeps exiting 0
    ],
)
def test_successful_verdicts_are_not_flagged(result):
    assert not _dispatcher()._result_declares_failure(result)


def test_run_passes_refuses_when_candidate_not_ready(monkeypatch):
    """A failed readiness gate consumes ZERO worker quota: no dispatch is
    written and the result declares failure."""
    mod = _dispatcher()
    monkeypatch.setattr(mod, "_wait_candidate_ready", lambda *a, **k: {"ready": False})

    dispatched: list[str] = []
    monkeypatch.setattr(mod, "dispatch_pass", lambda *a, **k: dispatched.append("DISPATCHED") or {})

    out = mod.run_passes(mod.Runner(dry_run=False), sha="deadbeef", scenario="smoke", passes=1)
    assert out["ok"] is False
    assert out["passes"] == 0
    assert dispatched == [], "no worker dispatch may occur when readiness fails"
    assert mod._result_declares_failure(out)


def test_dispatch_id_is_unique_per_dispatch(tmp_path):
    """Review W6: `d-<attempt_id>` collided on re-dispatch and the spool write
    (os.replace) silently clobbered the pending envelope."""
    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    seen = set()
    for _ in range(50):
        from uuid import uuid4

        did = f"d-ea-1-{uuid4().hex[:8]}"
        assert did not in seen, "dispatch ids must not collide"
        seen.add(did)
        spool.enqueue(
            DispatchEnvelope(dispatch_id=did, attempt_id="ea-1", sequence=1, nonce=uuid4().hex)
        )
    inbox = os.listdir(os.path.join(str(tmp_path / "spool"), "inbox"))
    assert len(inbox) == 50, f"every dispatch must persist its own file, got {len(inbox)}"


def test_no_attempt_is_ever_created_without_an_active_grant(tmp_path):
    """Producer-census closure: the ONE ExecutionAttempt producer
    (``AttemptScheduler._create_attempt``) is unreachable for any grant that is
    not ACTIVE.

    Reviewer A's fresh-head review declared the ExecutionAttempt /
    ExecutionAuthorizationGrant / ApprovalRequest producer census explicitly NOT
    ATTEMPTED, so this closes it by execution. The census itself is singular:
    one attempt producer (scheduler.py `_create_attempt` → the store's
    `create_attempt_idempotent`), one grant producer (decisions.py), one
    approval producer (decisions.py). There is no second owner.

    Placement, lease acquisition, and instruction compilation are passed
    sentinels that RAISE — so a non-ACTIVE grant slipping past the status check
    is loud, not silently tolerated.
    """
    from types import SimpleNamespace

    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.store import ExecutionAttemptStore

    def _boom(*_a, **_k):
        raise AssertionError("admission reached with a non-ACTIVE grant")

    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )
    scheduler = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=_boom),
        placement_fn=_boom,
        lease_manager=SimpleNamespace(acquire=_boom),
        compile_fn=_boom,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-1", status="approved"
        ),
    )

    for status in (
        "expired",
        "revoked",
        "activating",
        "invalidated",
        "failed_activation",
        "",
    ):
        grant = SimpleNamespace(
            status=status,
            tenant_id="t",
            plan_record_id="opr-1",
            plan_version=1,
            decision_ref="d:1:execution_authorization:v1",
            task_frontier=["A"],
            objective_id="goal-1",
            principal_id="u",
            membership_id="m",
            correlation_id="c",
            max_attempts_per_task=1,
        )
        report = scheduler.run_scheduler_pass(grant)
        # The scheduler now REREADS the grant from the ledger under the lock, so
        # an unpersisted caller-supplied object fails closed at the reread — a
        # stricter refusal than the old status-field check, and the correct one.
        assert not report.attempts_created, (status, report.attempts_created)
        assert not report.attempts_admitted, (status, report.attempts_admitted)
        assert report.reason, status


def test_execution_api_retry_route_is_fail_closed_and_mints_nothing(tmp_path, monkeypatch):
    """Closes the third declared coverage gap: is the execution API an
    alternate Task-production or authority-minting door?

    It is not. ``POST /execution/attempts/{id}/retry`` refuses every non-ACTIVE
    grant state AND a missing grant, and even on success it creates no
    ExecutionAttempt — it records the operator request and the next scheduler
    pass mints the linked attempt under the ACTIVE grant. Authority stays with
    the ONE producer (AttemptScheduler), never with the transport.
    """
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.store import ExecutionAttemptStore
    import transports.api.execution_attempt_routes as routes

    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )
    attempt = ExecutionAttempt(
        task_id="A",
        plan_record_id="opr-1",
        plan_version=1,
        execution_authorization_ref="ref-1",
        attempt_number=1,
        tenant_id="t",
        objective_id="goal-1",
    )
    attempt.status = "failed"
    store.create_attempt_idempotent(attempt)

    # Pin the caller's tenant to the attempt's own. Without this the test
    # depended on ambient principal resolution: once the cross-tenant test ran
    # first, the leaked context made the tenant guard (correctly) filter this
    # attempt out, and this test failed under -k while passing in isolation.
    import substrate.contracts.principal_resolution as principal

    class _Ctx:
        tenant_id = "t"

    monkeypatch.setattr(principal, "resolve_principal_context", lambda *a, **k: _Ctx())

    class _Store:
        def __init__(self, status):
            self.status = status

        def get_attempt(self, aid):
            return store.get_attempt(aid)

        def get_grant(self, ref):
            if self.status is None:
                return None
            grant = ExecutionAuthorizationGrant(
                decision_ref=ref,
                tenant_id="t",
                plan_record_id="opr-1",
                plan_version=1,
                task_frontier=["A"],
            )
            grant.status = self.status
            return grant

    class _Body:
        decided_by = "op"
        reason = "r"

    original = routes._store
    before = len(store.attempts_for_plan("opr-1"))
    try:
        for status in ("expired", "revoked", "activating", "invalidated", None):
            routes._store = lambda s=status: _Store(s)
            endpoint = {
                r.path: r.endpoint for r in routes._build_router().routes
            }["/execution/attempts/{attempt_id}/retry"]
            out = endpoint(attempt.attempt_id, _Body())
            assert out.get("success") is False, (status, out)

        routes._store = lambda: _Store("active")
        endpoint = {r.path: r.endpoint for r in routes._build_router().routes}[
            "/execution/attempts/{attempt_id}/retry"
        ]
        out = endpoint(attempt.attempt_id, _Body())
        assert out.get("success") is True, out
    finally:
        routes._store = original

    # The decisive assertion: no attempt was minted by the transport.
    assert len(store.attempts_for_plan("opr-1")) == before


def _grant_store(tmp_path):
    from substrate.execution.attempts.store import ExecutionAttemptStore

    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
        assignments_path=str(tmp_path / "assignments.jsonl"),
    )


def test_expired_or_not_yet_valid_grant_mints_no_attempt(tmp_path):
    """CRITICAL: the sole ExecutionAttempt producer checked only the grant's
    STATUS FIELD (`status != "active"`) and never evaluated authorization
    VALIDITY. A grant that was expired — or not yet within its window — but
    whose status field still read "active" minted attempts, acquired leases and
    spent real billed worker quota. The time window was decorative.

    ``is_authorization_valid`` had ZERO production callers; so did
    ``evaluate_execution_readiness`` and ``sweep_expired_authorizations``.

    NOTE ON METHOD: an earlier self-check varied the status FIELD across
    expired/revoked/... and reported the path safe. That test was shaped like
    the code instead of like the threat — status is the one dimension that WAS
    checked. This test varies the time window while status stays "active".
    """
    from types import SimpleNamespace

    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler

    def _boom(*_a, **_k):
        raise AssertionError("admission reached with an INVALID grant")

    store = _grant_store(tmp_path)
    scheduler = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=_boom),
        placement_fn=_boom,
        lease_manager=SimpleNamespace(acquire=_boom),
        compile_fn=_boom,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-1", status="approved"
        ),
    )
    now = time.time()

    for ref, kwargs, expected in (
        ("ref-expired", {"expires_at": now - 3600}, "expired"),
        ("ref-future", {"not_before": now + 3600}, "not yet active"),
    ):
        grant = ExecutionAuthorizationGrant(
            decision_ref=ref,
            tenant_id="t",
            plan_record_id="opr-1",
            plan_version=1,
            task_frontier=["A"],
            objective_id="goal-1",
            **kwargs,
        )
        grant.status = "active"  # the field the old check looked at
        created, _ = store.create_grant_idempotent(grant)
        report = scheduler.run_scheduler_pass(created)
        assert expected in (report.reason or ""), (ref, report.reason)
        assert not report.attempts_created, (ref, report.attempts_created)


def test_scheduler_rereads_the_grant_so_a_committed_revocation_is_seen(tmp_path):
    """The grant reference is captured BEFORE the lock, so a revocation
    committed in between was invisible for the life of that reference — the
    "Re-read canonical state AFTER lock acquisition" docstring was false."""
    from types import SimpleNamespace

    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler

    def _boom(*_a, **_k):
        raise AssertionError("admission reached with a REVOKED grant")

    store = _grant_store(tmp_path)
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-revoke",
        tenant_id="t",
        plan_record_id="opr-1",
        plan_version=1,
        task_frontier=["A"],
        objective_id="goal-1",
        expires_at=time.time() + 3600,
    )
    grant.status = "active"
    stale, _ = store.create_grant_idempotent(grant)

    # Revoke it durably AFTER the caller captured `stale`.
    fresh = store.get_grant("ref-revoke")
    fresh.status = "revoked"
    store.update_grant_cas(fresh, expected_record_version=fresh.record_version)

    scheduler = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=_boom),
        placement_fn=_boom,
        lease_manager=SimpleNamespace(acquire=_boom),
        compile_fn=_boom,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-1", status="approved"
        ),
    )
    report = scheduler.run_scheduler_pass(stale)  # the STALE reference
    assert not report.attempts_created, report.attempts_created
    assert "not active" in (report.reason or "") or "invalid" in (report.reason or ""), report.reason


def _tenant_routes(tmp_path, monkeypatch, caller_tenant, victim_status="running"):
    """Seed ONE attempt owned by tenant-a and resolve the caller to
    ``caller_tenant``. Returns (store, attempt, endpoints)."""
    from substrate.execution.attempts.records import ExecutionAttempt
    import substrate.contracts.principal_resolution as principal
    import transports.api.execution_attempt_routes as routes

    from substrate.execution.attempts.records import ExecutionAuthorizationGrant

    store = _grant_store(tmp_path)
    attempt = ExecutionAttempt(
        task_id="T-A",
        plan_record_id="opr-a",
        plan_version=1,
        execution_authorization_ref="ref-a",
        attempt_number=1,
        tenant_id="tenant-a",
        objective_id="goal-a",
    )
    attempt.status = victim_status
    store.create_attempt_idempotent(attempt)

    # An ACTIVE grant owned by tenant-a MUST exist, otherwise /frontier and
    # /authorizations return empty because there is nothing to leak — and the
    # cross-tenant assertion would pass for the wrong reason (exactly the C-1
    # defect, one layer down: mutating those two guards away kept the suite
    # green until this grant was seeded).
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-a",
        tenant_id="tenant-a",
        plan_record_id="opr-a",
        plan_version=1,
        task_frontier=["T-A"],
        objective_id="goal-a",
    )
    grant.status = "active"
    store.create_grant_idempotent(grant)

    class _Ctx:
        tenant_id = caller_tenant

    monkeypatch.setattr(principal, "resolve_principal_context", lambda *a, **k: _Ctx())
    monkeypatch.setattr(routes, "_store", lambda: store)
    return store, attempt, {r.path: r.endpoint for r in routes._build_router().routes}


class _CancelBody:
    decided_by = "mallory"
    reason = "x"


def test_every_execution_route_refuses_cross_tenant_access(tmp_path, monkeypatch):
    """HIGH (review C-1): the per-route tenant guards were VACUOUS.

    The previous version of this test asserted on only 5 of 8 routes, and its
    cancel/retry assertions passed for the WRONG REASON: the victim attempt was
    ``failed``, so ``transition_cas`` refused ``failed -> cancelled`` on
    LIFECYCLE grounds before tenancy was ever consulted. Removing the cancel
    tenant guard entirely left this suite green. Only a blanket
    ``_tenant_visible -> True`` was caught; each individual per-route guard
    could be deleted and ship green.

    Every route is now asserted individually, and the victim is RUNNING so a
    cancel refusal can only come from tenancy.
    """
    store, attempt, endpoints = _tenant_routes(tmp_path, monkeypatch, "tenant-b")

    assert endpoints["/execution/attempts"]()["attempts"] == []
    assert endpoints["/execution/attempts/{attempt_id}"](attempt.attempt_id) == {
        "error": "not found"
    }
    assert endpoints["/execution/frontier"]()["frontier"] == []
    assert endpoints["/execution/authorizations"]()["authorizations"] == []
    assert endpoints["/execution/by-plan/{plan_record_id}"]("opr-a")["attempts"] == []
    assert endpoints["/execution/overlay"]("T-A")["overlay"] == {}
    assert (
        endpoints["/execution/attempts/{attempt_id}/retry"](
            attempt.attempt_id, _CancelBody()
        ).get("success")
        is False
    )
    # DECISIVE. Two confounders had to be removed before this assertion could
    # mean anything: (1) a `failed` victim made transition_cas refuse on
    # LIFECYCLE grounds, (2) `governed_mutation` refuses in degraded mode when
    # no control plane is up. With BOTH removed — a RUNNING victim and a
    # permitting mutation runner — the only thing left that can refuse the
    # cancel is tenancy.
    import transports.api.governed as governed

    def _permit(**kw):
        fn = kw.get("execute_fn")
        out = fn() if callable(fn) else ("", True)
        return SimpleNamespace(success=True, output=out[0] if isinstance(out, tuple) else out)

    monkeypatch.setattr(governed, "governed_mutation", _permit)
    assert (
        endpoints["/execution/attempts/{attempt_id}/cancel"](
            attempt.attempt_id, _CancelBody()
        ).get("success")
        is False
    )
    assert store.get_attempt(attempt.attempt_id).status == "running"


def test_same_tenant_cancel_is_permitted_so_the_guard_is_not_blanket_denial(
    tmp_path, monkeypatch
):
    """Control for the test above: with the caller's tenant MATCHING, cancel
    must reach the lifecycle. Without this, a guard that denied everything
    would satisfy the cross-tenant assertions for the wrong reason — the exact
    defect class being fixed."""
    store, attempt, endpoints = _tenant_routes(tmp_path, monkeypatch, "tenant-a")

    assert endpoints["/execution/attempts/{attempt_id}"](attempt.attempt_id).get(
        "attempt_id"
    ) == attempt.attempt_id
    out = endpoints["/execution/attempts/{attempt_id}/cancel"](
        attempt.attempt_id, _CancelBody()
    )
    assert "not found" not in str(out.get("error", "")), out


def test_empty_tenant_is_denied_on_both_sides(tmp_path, monkeypatch):
    """HIGH (review C-2): ``_tenant_visible`` returned True when EITHER side was
    empty, on the surface exposing worker identities, lease paths,
    files_changed, commits and CANCEL.

    Row side was LIVE: attempt ``ea-cf043ef5e0a0`` exists in runtime state with
    ``tenant_id=''`` and status ``running`` — globally readable and cancellable.
    Caller side was latent: ``_caller_tenant()`` catches Exception and returns
    ``""``, so a principal-resolution FAILURE granted universal visibility
    instead of removing it.
    """
    # (a) caller cannot resolve a tenant -> sees nothing
    store, attempt, endpoints = _tenant_routes(tmp_path, monkeypatch, "")
    assert endpoints["/execution/attempts"]()["attempts"] == []
    assert endpoints["/execution/attempts/{attempt_id}"](attempt.attempt_id) == {
        "error": "not found"
    }
    assert (
        endpoints["/execution/attempts/{attempt_id}/cancel"](
            attempt.attempt_id, _CancelBody()
        ).get("success")
        is False
    )
    assert store.get_attempt(attempt.attempt_id).status == "running"

    # (b) a row WITHOUT a tenant is not globally visible
    from substrate.execution.attempts.records import ExecutionAttempt

    orphan = ExecutionAttempt(
        task_id="T-ORPHAN",
        plan_record_id="opr-orphan",
        plan_version=1,
        execution_authorization_ref="ref-o",
        attempt_number=1,
        tenant_id="",
        objective_id="goal-o",
    )
    orphan.status = "running"
    store.create_attempt_idempotent(orphan)

    import substrate.contracts.principal_resolution as principal

    class _Ctx:
        tenant_id = "tenant-b"

    monkeypatch.setattr(principal, "resolve_principal_context", lambda *a, **k: _Ctx())
    import transports.api.execution_attempt_routes as routes

    endpoints = {r.path: r.endpoint for r in routes._build_router().routes}
    assert endpoints["/execution/attempts/{attempt_id}"](orphan.attempt_id) == {
        "error": "not found"
    }
    assert orphan.attempt_id not in str(endpoints["/execution/attempts"]())


def test_production_decision_source_wires_the_supersession_lookup():
    """HIGH: production built ``ExecutionAuthorizationDecisionSource`` with no
    ``latest_plan_lookup``, so the supersession guard in
    ``apply_execution_decision`` (``if latest_plan_lookup is not None:``) was
    never entered — a stale v1 grant could be approved to ACTIVE after the plan
    was revised to v2. The only writer of INVALIDATED lives in that same block,
    so a superseded frontier also kept being admitted and dispatched.

    Defaulted inside the source rather than at one call site, so it holds for
    EVERY caller (same pattern as the defaulted ``activate_fn``).
    """
    from substrate.execution.attempts.decisions import ExecutionAuthorizationDecisionSource

    source = ExecutionAuthorizationDecisionSource()
    assert source._latest_plan_lookup is not None
    assert callable(source._latest_plan_lookup)


def test_spool_refuses_a_replayed_envelope_but_allows_recovery(tmp_path):
    """HIGH: the signed ``nonce`` (commented "anti-replay: must not reset on
    restart") was never checked. An envelope COPIED back into the inbox
    verified cleanly — the signature covers the original fields — and was
    re-executed: duplicate billed quota and duplicate mutations in the lease
    worktree. Signature proves authenticity, never freshness.

    The control half matters as much: authorized crash RECOVERY must still
    work, so recovery releases the marker. Recovery is the spool returning its
    own abandoned claim; replay is an unauthorized copy.
    """
    import shutil

    spool = DispatchSpool(str(tmp_path / "spool"), _SECRET)
    envelope = _envelope(1)
    name = spool.enqueue(envelope)

    assert spool.claim_next() is not None
    shutil.copy(
        str(tmp_path / "spool" / "inflight" / name),
        str(tmp_path / "spool" / "inbox" / name),
    )
    assert spool.claim_next() is None, "a replayed envelope must be refused"
    assert any(
        "replayed" in n for n in os.listdir(str(tmp_path / "spool" / "quarantine"))
    )

    # A DIFFERENT legitimate dispatch still flows.
    spool.enqueue(_envelope(2))
    assert spool.claim_next() is not None


def _bound_packet(tenant, plan, pid="T-1"):
    return SimpleNamespace(
        packet_id=pid,
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": tenant, "target_kind": "umh_substrate"},
        lineage={"plan_record_id": plan},
    )


def _bind_scheduler(tmp_path, packet, grant_tenant="tenant-A", grant_plan="opr-A"):
    """Scheduler whose placement/lease/compile all RAISE, so any admission of an
    unbound packet is loud rather than silently tolerated."""
    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = _grant_store(tmp_path)

    def _boom(*_a, **_k):
        raise AssertionError("admission reached with a packet NOT bound to the grant")

    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-bind",
        tenant_id=grant_tenant,
        plan_record_id=grant_plan,
        plan_version=1,
        task_frontier=[packet.packet_id],
        objective_id="goal-bind",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
        # Match the sole production grant producer (decisions.py:208/215),
        # which always stamps these; the raw dataclass defaults are empty.
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    class _Q:
        def get_packet(self, pid):
            return packet if pid == packet.packet_id else None

    def _permit(**kw):
        """A PERMITTING mutation runner.

        Without this the scheduler used the default runner, which fails closed
        on `execution_attempt_create` in-process (no control plane), so
        `assert not attempts_created` held whether or not the binding guard
        refused — and the `_boom` sentinels never fired. A mutant that RECORDS
        the block but returns True instead of False shipped green
        (adversarial-review HIGH: the same vacuity shape as C-1, reintroduced).
        """
        fn = kw.get("execute_fn")
        out = fn() if callable(fn) else ("", True)
        return SimpleNamespace(
            success=True, output=out[0] if isinstance(out, tuple) else out
        )

    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=_boom,
        lease_manager=SimpleNamespace(acquire=_boom),
        compile_fn=_boom,
        lock_dir=str(tmp_path / "locks"),
        mutation_runner=_permit,
        # The plan resolves (production copies objective_id from the plan), so
        # the ONLY thing that can refuse here is the tenant/plan binding.
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id=grant_plan, status="approved"
        ),
    )
    return store, scheduler, created


@pytest.mark.parametrize(
    "pkt_tenant,pkt_plan,why",
    [
        ("tenant-VICTIM", "opr-A", "another tenant's Task"),
        ("tenant-A", "opr-OTHER", "another plan's Task"),
        ("", "opr-A", "unbound tenant"),
        ("tenant-A", "", "unbound plan"),
    ],
)
def test_grant_cannot_execute_a_task_it_does_not_own(tmp_path, pkt_tenant, pkt_plan, why):
    """CRITICAL (review A-1): the sole attempt producer performed NO tenant,
    plan, or plan-version binding — it enforced only "the id string appears in
    task_frontier" and then COPIED the grant's tenant onto the attempt.

    Any principal who got a grant approved for their own plan could name ANY
    Task id in the system and have a real worker execute it — in a lease
    worktree, spending billed quota, mutating a repository — against another
    tenant's Task, another plan, or a stale plan version. The store is
    tenant-blind, so there was no downstream defense.

    The checks that would have bound it live in the readiness module, which no
    production caller invokes. This is the same defect class already fixed on
    the API surface; this is the surface that actually spends quota.
    """
    packet = _bound_packet(pkt_tenant, pkt_plan)
    store, scheduler, grant = _bind_scheduler(tmp_path, packet)

    report = scheduler.run_scheduler_pass(grant)

    assert not report.attempts_created, (why, report.attempts_created)
    assert packet.packet_id in report.attempts_blocked, (why, report.attempts_blocked)
    assert store.attempts_for_plan("opr-A") == [], why


def test_a_correctly_bound_task_is_not_blocked_by_the_binding_check(tmp_path):
    """Control: the binding guard must not be blanket denial. A packet whose
    tenant AND plan match the grant passes the check and proceeds to admission
    (the sentinel then fires, proving the guard let it through)."""
    packet = _bound_packet("tenant-A", "opr-A")
    _store, scheduler, grant = _bind_scheduler(tmp_path, packet)

    # Production always supplies a role resolver; without one the admission
    # authority blocks on `role_not_authorized`, which would satisfy this
    # test's "was it blocked?" assertion for a reason that has nothing to do
    # with the binding guard under test.
    report = scheduler.run_scheduler_pass(
        grant,
        role_resolver=lambda p: _prod_role_resolver(p),
        verifier_role_resolver=lambda p: "role-verify-op",
    )

    # The DECISIVE assertion is that the binding check did not block it. It is
    # not admitted here only because `execution_attempt_create` is refused in
    # degraded mode (no control plane in-process) — a different gate entirely,
    # and one that must not be mistaken for the binding guard. Asserting
    # "blocked is empty" isolates the guard under test.
    assert packet.packet_id not in report.attempts_blocked, report.attempts_blocked


def test_superseded_plan_stops_admission_on_the_very_next_pass(tmp_path):
    """HIGH (review A-4): supersession was enforced ONLY at approve time.

    `is_authorization_valid` skips its supersession branch when
    `latest_plan_lookup is None`, and the scheduler called it bare — so a grant
    approved while the plan was v1 kept admitting, leasing and dispatching after
    the operator revised to v2. Wiring the default lookup into the decision
    source closed the approve-time hole only; the scheduler is the component
    that runs EVERY pass, and it never asked the question.

    My own commit message for the earlier fix described this consequence as
    closed. It was not — only half of it was.
    """
    packet = _bound_packet("tenant-A", "opr-A")
    store, scheduler, grant = _bind_scheduler(tmp_path, packet)

    # The plan has moved on: latest is now opr-A-v2, not the grant's opr-A.
    scheduler._latest_plan_lookup = lambda _o: SimpleNamespace(
        plan_record_id="opr-A-v2", status="approved"
    )

    report = scheduler.run_scheduler_pass(grant)

    assert not report.attempts_created, report.attempts_created
    assert "invalidated by a newer plan" in (report.reason or ""), report.reason
    assert store.attempts_for_plan("opr-A") == []


def test_unresolvable_plan_fails_closed_at_admission(tmp_path):
    """A grant whose objective resolves to NO plan must not dispatch. Production
    grants copy `objective_id` from the plan at request time, so an
    unresolvable objective means the planning state is gone or wrong — which is
    not a licence to execute."""
    packet = _bound_packet("tenant-A", "opr-A")
    store, scheduler, grant = _bind_scheduler(tmp_path, packet)
    scheduler._latest_plan_lookup = lambda _o: None

    report = scheduler.run_scheduler_pass(grant)

    assert not report.attempts_created, report.attempts_created
    assert "no plan" in (report.reason or ""), report.reason


def test_default_scheduler_construction_carries_a_supersession_lookup(tmp_path):
    """The DEFAULT construction must be wired — not merely wirable.

    Every test above injects `latest_plan_lookup`, so they prove the guard works
    when supplied and prove nothing about production. Deleting the constructor
    default therefore left them all green (mutation M-A4b SURVIVED). That is the
    exact defect class this slice keeps producing: a contract that exists but
    production never fires. This asserts the default itself.
    """
    from substrate.execution.attempts.scheduler import AttemptScheduler

    scheduler = AttemptScheduler(
        _grant_store(tmp_path),
        work_queue=SimpleNamespace(get_packet=lambda _p: None),
        placement_fn=lambda **_k: None,
        lease_manager=SimpleNamespace(acquire=lambda **_k: None),
        compile_fn=lambda **_k: None,
        lock_dir=str(tmp_path / "locks"),
    )
    assert scheduler._latest_plan_lookup is not None
    assert callable(scheduler._latest_plan_lookup)
    # And it must really query the planning store, not be a stub that returns a
    # truthy object for anything.
    assert scheduler._latest_plan_lookup("goal-that-does-not-exist") is None


def test_default_field_driver_forwards_a_supersession_lookup(tmp_path):
    """Same question one layer up: the field control-plane driver builds its own
    scheduler, so the driver's default must reach the scheduler's default."""
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    driver = FieldControlPlaneDriver(
        store=_grant_store(tmp_path),
        work_queue=SimpleNamespace(get_packet=lambda _p: None),
        spool=DispatchSpool(str(tmp_path / "spool"), _SECRET),
        sandbox_manager=SimpleNamespace(),
        targets_dir=str(tmp_path / "targets"),
        lock_dir=str(tmp_path / "locks"),
    )
    # None here means "inherit the scheduler's real default", never "skip".
    assert not hasattr(driver, "_latest_plan_lookup") or driver._latest_plan_lookup is None
    scheduler = driver._build_scheduler()
    assert scheduler._latest_plan_lookup is not None
    assert scheduler._latest_plan_lookup("goal-that-does-not-exist") is None


def test_plan_revision_mints_a_new_record_id_so_binding_is_version_binding():
    """The Task<->grant binding compares `plan_record_id`, NOT `plan_version` —
    and that is sufficient ONLY because a revision mints a FRESH
    `plan_record_id` (compiler.py: `new_plan.plan_record_id = ...  # fresh id`).

    `WorkLineageContext` carries no version field at all, so a packet cannot be
    compared on version even in principle. If a future change ever made a
    revision REUSE the record id, the binding check would silently stop being
    version-binding and a v1 packet would satisfy a v2 grant. This pins the
    invariant the binding depends on.
    """
    from substrate.contracts.work_context import WorkLineageContext
    from substrate.execution.planning.records import ObjectivePlanRecord

    assert not hasattr(WorkLineageContext(), "plan_version"), (
        "packets now carry a plan version — the binding check should compare it"
    )
    assert ObjectivePlanRecord().plan_record_id != ObjectivePlanRecord().plan_record_id


def test_admission_refuses_a_ready_attempt_the_grant_does_not_own(tmp_path):
    """CRITICAL (review R2-1): the A-1 binding fix guarded attempt CREATION and
    left ADMISSION open — the door that actually spends quota.

    ``_admit`` selected from ``store.active_attempts()``, which reads the ENTIRE
    ledger and is tenant-blind and grant-blind. Every READY attempt in a shared
    multi-tenant store was leased, compiled and dispatched under whatever grant
    the pass happened to hold. The attacker's grant is entirely legitimate for
    their own plan and its ``task_frontier`` is EMPTY — it names nothing at all.
    """
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = _grant_store(tmp_path)
    victim = ExecutionAttempt(
        task_id="VICTIM-TASK",
        plan_record_id="opr-VICTIM",
        plan_version=1,
        execution_authorization_ref="ref-VICTIM",
        attempt_number=1,
        tenant_id="tenant-VICTIM",
        objective_id="goal-v",
    )
    victim, _ = store.create_attempt_idempotent(victim)
    store.transition_cas(
        victim.attempt_id,
        "ready",
        expected_record_version=victim.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    placed: list = []
    leased: list = []
    dispatched: list = []
    victim_packet = SimpleNamespace(
        packet_id="VICTIM-TASK",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "tenant-VICTIM", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-VICTIM"},
    )

    class _Q:
        def get_packet(self, pid):
            return victim_packet if pid == "VICTIM-TASK" else None

    attacker = ExecutionAuthorizationGrant(
        decision_ref="ref-ATTACKER",
        tenant_id="tenant-ATTACKER",
        plan_record_id="opr-ATTACKER",
        plan_version=1,
        task_frontier=[],  # names NOTHING
        objective_id="goal-a",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
    )
    attacker.status = "active"
    created, _ = store.create_grant_idempotent(attacker)

    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: placed.append(kw.get("attempt_id"))
        or SimpleNamespace(assignment_id="as", worker_identity="w", verifier_role_id="v"),
        lease_manager=SimpleNamespace(
            acquire=lambda **kw: leased.append(kw.get("attempt_id"))
            or SimpleNamespace(lease_id="L", worktree_path=str(tmp_path), base_commit="c")
        ),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="h"),
        dispatch_fn=lambda **kw: dispatched.append(kw.get("attempt_id")),
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-ATTACKER", status="approved"
        ),
    )

    report = scheduler.run_scheduler_pass(created)

    assert placed == [], "another tenant's Task was PLACED"
    assert leased == [], "another tenant's Task was LEASED"
    assert dispatched == [], "another tenant's Task was DISPATCHED"
    assert report.attempts_admitted == [], report.attempts_admitted
    assert store.get_attempt(victim.attempt_id).status == "ready"


def test_admission_admits_a_ready_attempt_the_grant_DOES_own(tmp_path):
    """Control for R2-1: the admission binding must discriminate, not deny. A
    grant that owns the Task still places, leases and dispatches it."""
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = _grant_store(tmp_path)
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-OWN",
        tenant_id="tenant-A",
        plan_record_id="opr-A",
        plan_version=1,
        task_frontier=["OWN-TASK"],
        objective_id="goal-a",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
        # The SOLE production grant producer (`request_execution_authorization`)
        # always stamps environment_classes=["git_worktree"] (decisions.py:208);
        # the raw dataclass default is []. A fixture built straight from the
        # dataclass therefore models a grant production cannot mint, and the
        # admission authority correctly refuses it (`no_environment_class`).
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    attempt = ExecutionAttempt(
        task_id="OWN-TASK",
        plan_record_id="opr-A",
        plan_version=1,
        execution_authorization_ref="ref-OWN",
        attempt_number=1,
        tenant_id="tenant-A",
        objective_id="goal-a",
    )
    attempt, _ = store.create_attempt_idempotent(attempt)
    store.transition_cas(
        attempt.attempt_id,
        "ready",
        expected_record_version=attempt.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    packet = SimpleNamespace(
        packet_id="OWN-TASK",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "tenant-A", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-A"},
    )

    class _Q:
        def get_packet(self, pid):
            return packet if pid == "OWN-TASK" else None

    placed: list = []
    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: placed.append(kw.get("attempt_id"))
        or SimpleNamespace(assignment_id="as", worker_identity="w", verifier_role_id="v"),
        lease_manager=SimpleNamespace(
            acquire=lambda **kw: SimpleNamespace(
                lease_id="L", worktree_path=str(tmp_path), base_commit="c"
            )
        ),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="h"),
        dispatch_fn=lambda **kw: None,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-A", status="approved"
        ),
    )

    scheduler.run_scheduler_pass(
        created,
        role_resolver=lambda p: _prod_role_resolver(p),
        verifier_role_resolver=lambda p: "role-verify-op",
    )
    assert placed == [attempt.attempt_id], "a grant was refused its OWN Task"


def test_retry_route_refuses_cross_tenant_with_a_retryable_victim(tmp_path, monkeypatch):
    """HIGH (review R2-4): the retry tenant guard was UNTESTED. The
    cross-tenant test used a RUNNING victim, but retry requires ``failed`` — so
    the status check refused first and the tenant guard could be deleted green.

    The victim here is FAILED, i.e. legitimately retryable, and the grant it
    references is ACTIVE. The only thing left that can refuse is tenancy.
    """
    from substrate.execution.attempts.records import ExecutionAuthorizationGrant

    store, attempt, endpoints = _tenant_routes(
        tmp_path, monkeypatch, "tenant-b", victim_status="failed"
    )
    # An ACTIVE grant for the victim's own plan, so `retry` cannot refuse for
    # lack of authorization either.
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-a",
        tenant_id="tenant-a",
        plan_record_id="opr-a",
        plan_version=1,
        task_frontier=["T-A"],
        objective_id="goal-a",
        expires_at=time.time() + 3600,
    )
    grant.status = "active"
    try:
        store.create_grant_idempotent(grant)
    except Exception:
        pass

    out = endpoints["/execution/attempts/{attempt_id}/retry"](
        attempt.attempt_id, _CancelBody()
    )
    assert out.get("success") is False, out
    assert "not found" in str(out.get("error", "")), (
        "retry refused for a reason OTHER than tenancy — the guard is untested again"
    )


def test_admission_revalidates_a_packet_that_changed_after_the_frontier_check(tmp_path):
    """CRITICAL (review R2-2): the packet is RE-READ in ``_admit`` after the
    frontier loop already checked it, so it must be RE-VALIDATED there.

    This isolates the second call: the attempt IS in the grant's frontier and
    DOES carry the grant's authorization_ref, so the frontier narrowing admits
    it — and only the re-validation can catch that the packet's tenant changed
    between the two reads. Without it, deleting the second binding call ships
    green (verified: the R2-1 test alone does not cover it).
    """
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = _grant_store(tmp_path)
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-own",
        tenant_id="tenant-A",
        plan_record_id="opr-A",
        plan_version=1,
        task_frontier=["T-DRIFT"],
        objective_id="goal-a",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
        # The SOLE production grant producer (`request_execution_authorization`)
        # always stamps environment_classes=["git_worktree"] (decisions.py:208);
        # the raw dataclass default is []. A fixture built straight from the
        # dataclass therefore models a grant production cannot mint, and the
        # admission authority correctly refuses it (`no_environment_class`).
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    attempt = ExecutionAttempt(
        task_id="T-DRIFT",
        plan_record_id="opr-A",
        plan_version=1,
        execution_authorization_ref="ref-own",
        attempt_number=1,
        tenant_id="tenant-A",
        objective_id="goal-a",
    )
    attempt, _ = store.create_attempt_idempotent(attempt)
    store.transition_cas(
        attempt.attempt_id,
        "ready",
        expected_record_version=attempt.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    # The packet DRIFTS: by the time _admit re-reads it, it belongs elsewhere.
    drifted = SimpleNamespace(
        packet_id="T-DRIFT",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "tenant-SOMEONE-ELSE", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-A"},
    )

    class _Q:
        def get_packet(self, pid):
            return drifted if pid == "T-DRIFT" else None

    placed: list = []
    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: placed.append(kw.get("attempt_id"))
        or SimpleNamespace(assignment_id="as", worker_identity="w", verifier_role_id="v"),
        lease_manager=SimpleNamespace(
            acquire=lambda **kw: SimpleNamespace(
                lease_id="L", worktree_path=str(tmp_path), base_commit="c"
            )
        ),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="h"),
        dispatch_fn=lambda **kw: None,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-A", status="approved"
        ),
    )

    scheduler.run_scheduler_pass(created)
    assert placed == [], "a drifted packet was placed — admission did not re-validate"


def test_admission_will_not_run_an_attempt_minted_under_a_different_grant(tmp_path):
    """The frontier/authorization narrowing in ``_admit`` is INDEPENDENTLY
    load-bearing, not redundant with the packet re-validation.

    Two grants can legitimately share a tenant AND a plan — so a packet-level
    binding check passes for both. What separates them is which grant the
    ATTEMPT was minted under. Here the attempt belongs to ``ref-ONE`` while the
    pass is held by ``ref-TWO`` (empty frontier); the packet check cannot tell
    them apart, and only the narrowing refuses.
    """
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = _grant_store(tmp_path)
    attempt = ExecutionAttempt(
        task_id="T",
        plan_record_id="opr-A",
        plan_version=1,
        execution_authorization_ref="ref-ONE",
        attempt_number=1,
        tenant_id="tenant-A",
        objective_id="goal-a",
    )
    attempt, _ = store.create_attempt_idempotent(attempt)
    store.transition_cas(
        attempt.attempt_id,
        "ready",
        expected_record_version=attempt.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    packet = SimpleNamespace(
        packet_id="T",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "tenant-A", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-A"},
    )

    class _Q:
        def get_packet(self, pid):
            return packet

    other = ExecutionAuthorizationGrant(
        decision_ref="ref-TWO",
        tenant_id="tenant-A",
        plan_record_id="opr-A",
        plan_version=1,
        task_frontier=[],
        objective_id="goal-a",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
    )
    other.status = "active"
    created, _ = store.create_grant_idempotent(other)

    placed: list = []
    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: placed.append(kw.get("attempt_id"))
        or SimpleNamespace(assignment_id="as", worker_identity="w", verifier_role_id="v"),
        lease_manager=SimpleNamespace(
            acquire=lambda **kw: SimpleNamespace(
                lease_id="L", worktree_path=str(tmp_path), base_commit="c"
            )
        ),
        compile_fn=lambda **kw: SimpleNamespace(package_hash="h"),
        dispatch_fn=lambda **kw: None,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-A", status="approved"
        ),
    )

    scheduler.run_scheduler_pass(created)
    assert placed == [], "an attempt minted under another grant was admitted"


# ── R2-5 / R3: the ONE canonical admission authority ────────────────────────
#
# `evaluate_execution_readiness` defined 15 fail-closed checks and had ZERO
# production callers. The scheduler open-coded a partial subset and never asked
# the rest, so bounds the OPERATOR sets on the execution decision were
# decorative: `grant.role_ids`, `grant.allowed_tools` and `grant.cost_limit_usd`
# imposed nothing. Worse, `lifecycle.py` claimed ready→leased required
# "AUTHORIZED readiness" and `placement.py` claimed tools were "already
# validated ... in readiness" — comments asserting guarantees no code provided.
#
# These tests drive the REAL production entry point (`run_scheduler_pass`) with
# the real placement/lease/compile pipeline. Each asserts that admission creates
# NO attempt of its own, NO lease, and NO dispatch envelope — not merely that a
# boolean flipped.


def _admission_world(tmp_path, *, packet_kw=None, grant_kw=None):
    """A production-shaped world: one APPROVED packet, one ACTIVE grant, and a
    scheduler whose lease/compile/dispatch RECORD what they were asked to do.

    Everything defaults to the shape production actually mints, so any refusal
    is attributable to the single field the caller overrode.
    """
    from substrate.execution.attempts.records import (
        ExecutionAttempt,
        ExecutionAuthorizationGrant,
    )
    from substrate.execution.attempts.scheduler import AttemptScheduler

    store = _grant_store(tmp_path)
    leased: list = []
    compiled: list = []
    dispatched: list = []

    pkt_defaults = dict(
        packet_id="T-ADM",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "tenant-A", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-A"},
        requirements={"scope_declared": True, "writable_path_scope": ["app"]},
        validation_plan="verification node of the owning plan",
        required_tools=[],
        rollback_plan="",
    )
    pkt_defaults.update(packet_kw or {})
    packet = SimpleNamespace(**pkt_defaults)

    grant_defaults = dict(
        decision_ref="ref-ADM",
        tenant_id="tenant-A",
        plan_record_id="opr-A",
        plan_version=1,
        task_frontier=[packet.packet_id],
        objective_id="goal-adm",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
    )
    grant_defaults.update(grant_kw or {})
    grant = ExecutionAuthorizationGrant(**grant_defaults)
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    attempt = ExecutionAttempt(
        task_id=packet.packet_id,
        plan_record_id="opr-A",
        plan_version=1,
        execution_authorization_ref=created.decision_ref,
        attempt_number=1,
        tenant_id="tenant-A",
    )
    stored, _ = store.create_attempt_idempotent(attempt)
    store.transition_cas(
        stored.attempt_id,
        "ready",
        expected_record_version=stored.record_version,
        expected_statuses=("created",),
        actor="test",
        reason="ready",
    )

    class _Q:
        def get_packet(self, pid):
            return packet if pid == packet.packet_id else None

    def _permit(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=lambda **kw: SimpleNamespace(
            assignment_id="asn-1",
            worker_identity="w",
            verifier_role_id="role-verify-op",
            tool_profile=[],
            model_profile={},
            environment_class="git_worktree",
        ),
        lease_manager=SimpleNamespace(
            acquire=lambda **kw: (
                leased.append(kw.get("attempt").attempt_id)
                or SimpleNamespace(
                    lease_id="L", worktree_path=str(tmp_path), base_commit="c"
                )
            ),
            release=lambda *a, **k: None,
        ),
        compile_fn=lambda **kw: (
            compiled.append(kw.get("attempt").attempt_id)
            or SimpleNamespace(package_hash="h")
        ),
        dispatch_fn=lambda **kw: dispatched.append(kw.get("attempt").attempt_id),
        mutation_runner=_permit,
        lock_dir=str(tmp_path / "locks"),
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-A", status="approved"
        ),
    )
    return store, scheduler, created, stored, leased, compiled, dispatched


def _run_admission(tmp_path, **kw):
    store, sched, grant, attempt, leased, compiled, dispatched = _admission_world(
        tmp_path, **kw
    )
    report = sched.run_scheduler_pass(
        grant,
        role_resolver=lambda p: _prod_role_resolver(p),
        verifier_role_resolver=lambda p: "role-verify-op",
    )
    return SimpleNamespace(
        report=report,
        leased=leased,
        compiled=compiled,
        dispatched=dispatched,
        attempt=attempt,
        store=store,
    )


def test_admission_control_admits_a_fully_valid_task(tmp_path):
    """CONTROL. Without this, every refusal test below could pass because the
    gate refuses everything — which is a broken gate, not a strict one."""
    r = _run_admission(tmp_path)
    assert r.report.attempts_admitted == [r.attempt.attempt_id], r.report
    assert r.leased == [r.attempt.attempt_id], "a valid Task must acquire its lease"
    assert r.dispatched == [r.attempt.attempt_id], "a valid Task must dispatch"


@pytest.mark.parametrize(
    "label,packet_kw,grant_kw",
    [
        # The OPERATOR's role bound. `grant.role_ids` was never read at admission.
        ("role_not_authorized", None, {"role_ids": ["role-SOMETHING-ELSE"]}),
        # The OPERATOR's tool bound. placement.py claimed readiness checked this.
        (
            "tool_not_authorized",
            {"required_tools": ["rm_rf_everything"]},
            {"allowed_tools": ["shell"]},
        ),
        # Amendment v1 clause 8: an unenforceable ceiling must BLOCK.
        (
            "unenforceable_cost_ceiling",
            None,
            {"cost_limit_usd": 500.0, "cost_enforceable": False},
        ),
        # WorkScope completeness — target_kind had no admission consumer at all.
        ("incomplete_work_scope", {"work_scope": {"tenant_id": "tenant-A"}}, None),
        # No environment class ⇒ no structural rollback guarantee.
        ("no_environment_class", None, {"environment_classes": []}),
        # A Task with no verification obligation must not burn billed quota.
        (
            "no_verification_obligation",
            {"validation_plan": ""},
            {"verification_obligations": []},
        ),
        # Cross-tenant and wrong-plan remain refused by the same one authority.
        ("cross_tenant", {"work_scope": {"tenant_id": "tenant-B", "target_kind": "x"}}, None),
        ("wrong_plan", {"lineage": {"plan_record_id": "opr-OTHER"}}, None),
        # A packet that went terminal between creation and admission (TOCTOU).
        ("task_not_admissible", {"status": SimpleNamespace(value="completed")}, None),
    ],
)
def test_admission_refuses_and_spends_nothing(tmp_path, label, packet_kw, grant_kw):
    """Each violation must produce ZERO lease, ZERO package, ZERO dispatch.

    Asserting only "not admitted" would be satisfied by a refusal anywhere; the
    side-effect assertions prove no billed quota, no worktree and no envelope
    were committed before the refusal.
    """
    r = _run_admission(tmp_path, packet_kw=packet_kw, grant_kw=grant_kw)
    assert not r.report.attempts_admitted, f"{label}: admitted despite violation"
    assert not r.leased, f"{label}: a lease was acquired for a refused admission"
    assert not r.compiled, f"{label}: a package was sealed for a refused admission"
    assert not r.dispatched, f"{label}: a dispatch envelope was emitted"


def test_admission_refusal_is_recorded_on_the_attempt(tmp_path):
    """A refusal must be VISIBLE — the attempt parks BLOCKED with a truthful
    reason, rather than silently vanishing from the frontier each pass."""
    r = _run_admission(tmp_path, grant_kw={"role_ids": ["role-SOMETHING-ELSE"]})
    blocked = r.store.get_attempt(r.attempt.attempt_id)
    assert blocked.status == "blocked", blocked.status
    assert "role" in (blocked.blocked_reason or "").lower(), blocked.blocked_reason


def test_prohibited_skill_is_refused_at_admission(tmp_path):
    """`skills_role_authorized` is a PROHIBITED-class check in readiness — the
    hardest verdict — and had no production counterpart at all."""
    store, sched, grant, attempt, leased, compiled, dispatched = _admission_world(
        tmp_path,
        packet_kw={
            "requirements": {
                "scope_declared": True,
                "writable_path_scope": ["app"],
                "required_skill_refs": [{"skill_id": "skill-FORBIDDEN"}],
            }
        },
    )
    report = sched.run_scheduler_pass(
        grant,
        role_resolver=lambda p: SimpleNamespace(
            role_id="role-impl-op",
            allowed_tools=["shell"],
            prohibited_skill_ids=["skill-FORBIDDEN"],
        ),
        verifier_role_resolver=lambda p: "role-verify-op",
    )
    assert not report.attempts_admitted, "a prohibited skill was admitted"
    assert not leased and not dispatched, "prohibited skill reached lease/dispatch"


def test_admission_refuses_when_the_plan_was_superseded(tmp_path):
    """Supersession is asked at the admission boundary, not only at approve."""
    store, sched, grant, attempt, leased, compiled, dispatched = _admission_world(
        tmp_path
    )
    sched._latest_plan_lookup = lambda _o: SimpleNamespace(
        plan_record_id="opr-NEWER", status="approved"
    )
    report = sched.run_scheduler_pass(
        grant,
        role_resolver=lambda p: _prod_role_resolver(p),
        verifier_role_resolver=lambda p: "role-verify-op",
    )
    assert not report.attempts_admitted, "a superseded plan still admitted"
    assert not leased and not dispatched


def test_readiness_module_is_no_longer_the_only_authority(tmp_path):
    """The canonical authority must be REACHABLE from the production path.

    Not a source-string test: it asserts the scheduler's admission actually
    consults `authorize_admission` by observing that a violation ONLY that
    function knows about (an unenforceable cost ceiling) changes the outcome.
    """
    valid = _run_admission(tmp_path / "a")
    violating = _run_admission(
        tmp_path / "b", grant_kw={"cost_limit_usd": 900.0, "cost_enforceable": False}
    )
    assert valid.report.attempts_admitted, "control must admit"
    assert not violating.report.attempts_admitted, (
        "the cost bound is decided by no other component — if this admits, "
        "authorize_admission is not on the production path"
    )


# ── admission authority: DIRECT unit tests ─────────────────────────────────
#
# The scheduler refuses some conditions EARLIER than the admission boundary
# (attempt budget at creation time; supersession via `is_authorization_valid`
# before the loop). Driving those only through `run_scheduler_pass` therefore
# cannot kill a mutation of the admission-level guard — the earlier refusal
# satisfies the assertion, exactly the confounder class that let R2-3/R2-4 ship
# green. These call the authority DIRECTLY so each guard is independently
# load-bearing, and they are defense-in-depth for the earlier gates, not
# duplicates of them.


def _adm_inputs(*, packet_kw=None, grant_kw=None, attempt_kw=None, role_kw=None):
    pkt = dict(
        packet_id="T",
        status=SimpleNamespace(value="approved"),
        work_scope={"tenant_id": "t", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "p"},
        requirements={},
        validation_plan="verification node of the owning plan",
        required_tools=[],
        rollback_plan="",
    )
    pkt.update(packet_kw or {})
    grant = dict(
        decision_ref="r",
        tenant_id="t",
        plan_record_id="p",
        plan_version=1,
        task_frontier=["T"],
        max_attempts_per_task=2,
        role_ids=[],
        allowed_tools=[],
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
        rollback_obligations=[],
        cost_limit_usd=0.0,
        cost_enforceable=False,
        objective_id="g",
    )
    grant.update(grant_kw or {})
    att = dict(
        task_id="T", attempt_id="a", execution_authorization_ref="r", attempt_number=1
    )
    att.update(attempt_kw or {})
    role = dict(
        role_id="role-impl-op",
        allowed_tools=["shell"],
        prohibited_skill_ids=[],
        permitted_skill_ids=[],
    )
    role.update(role_kw or {})
    return (
        SimpleNamespace(**pkt),
        SimpleNamespace(**grant),
        SimpleNamespace(**att),
        SimpleNamespace(**role),
    )


def _adm(**kw):
    """Call the authority with the resolvers PRODUCTION always supplies.

    `plan_lookup` and `attempts_for_task` are keyword-optional for ergonomics
    but NOT optional in effect: an absent resolver REFUSES rather than skipping
    its check (a guard that vanishes when its lookup is missing is the exact
    fail-open shape this module removes). Defaults here therefore model the
    scheduler, which always passes both.
    """
    from substrate.execution.attempts.admission import authorize_admission

    plan_lookup = kw.pop(
        "plan_lookup",
        lambda _o: SimpleNamespace(plan_record_id="p", status="approved"),
    )
    attempts_for_task = kw.pop("attempts_for_task", lambda _t: [])
    packet, grant, attempt, role = _adm_inputs(**kw)
    return authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id="role-verify-op",
        plan_lookup=plan_lookup,
        attempts_for_task=attempts_for_task,
    )


def test_admission_unit_control_admits():
    """Control for the direct unit tests — otherwise every refusal below could
    pass because the authority refuses unconditionally."""
    v = _adm()
    assert v.admitted, (v.refusal_code, v.failed_checks())


def test_admission_refuses_attempt_beyond_the_authorized_budget():
    """`max_attempts_per_task` re-checked AT the boundary.

    The scheduler also caps attempt CREATION, so this cannot be proven through
    a scheduler pass — an attempt beyond budget is never created there. But an
    attempt created under a PREVIOUS pass (or a grant whose budget was since
    reduced) reaches admission, and this is the guard that stops it.
    """
    v = _adm(grant_kw={"max_attempts_per_task": 1}, attempt_kw={"attempt_number": 5})
    assert not v.admitted
    assert v.refusal_code == "attempt_budget_exhausted", v.refusal_code


def test_admission_refuses_a_superseded_plan_at_the_boundary():
    """Supersession asked AGAIN at admission (defense in depth).

    `run_scheduler_pass` refuses a superseded grant before the loop, so that
    path cannot exercise this guard. It exists because admission must not rely
    on a check that ran earlier against a possibly-staler view.
    """
    v = _adm(plan_lookup=lambda _o: SimpleNamespace(plan_record_id="p-NEWER", status="approved"))
    assert not v.admitted
    assert v.refusal_code == "plan_superseded_or_unapproved", v.refusal_code


def test_admission_refuses_an_unresolvable_plan():
    """A lookup that cannot resolve the plan is a REFUSAL, never a pass."""
    v = _adm(plan_lookup=lambda _o: None)
    assert not v.admitted
    assert v.refusal_code == "plan_unresolvable", v.refusal_code


def test_admission_refuses_an_environment_without_a_rollback_guarantee():
    """A NON-EMPTY environment class that is not rollback-guaranteed.

    The `environment_classes=[]` vector is refused by `environment_class_declared`
    FIRST, so it cannot prove this guard — using it would leave the rollback
    check deletable-green. `bare_host` is declared (passing check 11) but has no
    structural rollback, so only this guard refuses it.
    """
    v = _adm(grant_kw={"environment_classes": ["bare_host"]})
    assert not v.admitted
    assert v.refusal_code == "no_rollback_guarantee", v.refusal_code


def test_admission_accepts_a_declared_rollback_on_an_unusual_environment():
    """An explicitly DECLARED rollback rescues a non-structural environment —
    proving the guard checks a rollback guarantee, not the literal env string."""
    v = _adm(
        grant_kw={"environment_classes": ["bare_host"], "rollback_obligations": ["snapshot restore"]}
    )
    assert v.admitted, (v.refusal_code, v.failed_checks())


def test_admission_refuses_an_attempt_minted_under_a_different_grant():
    """The R2-1 shape at the authority level: an attempt whose authorization
    ref is not this grant's must never be admitted by this pass."""
    v = _adm(attempt_kw={"execution_authorization_ref": "SOME-OTHER-GRANT"})
    assert not v.admitted
    assert v.refusal_code == "attempt_not_authorized_by_this_grant", v.refusal_code


def test_admission_refuses_a_task_outside_the_frontier():
    v = _adm(grant_kw={"task_frontier": ["SOMETHING-ELSE"]})
    assert not v.admitted
    assert v.refusal_code == "task_outside_frontier", v.refusal_code


def test_admission_refuses_a_stale_plan_version_when_the_packet_declares_one():
    """A packet stamped with a plan_version different from the grant's."""
    v = _adm(packet_kw={"lineage": {"plan_record_id": "p", "plan_version": 7}})
    assert not v.admitted
    assert v.refusal_code == "stale_plan_version", v.refusal_code


def test_admission_refuses_when_the_attempt_ledger_is_unreadable():
    """Fail closed: an unreadable ledger removes authority, never confers it."""
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, role = _adm_inputs()

    def _boom(_task_id):
        raise OSError("ledger unreadable")

    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id="role-verify-op",
        attempts_for_task=_boom,
    )
    assert not v.admitted
    assert v.refusal_code == "ledger_unreadable", v.refusal_code


def test_admission_refuses_a_second_live_attempt_for_the_same_task():
    """Exactly-once: a Task with a live sibling attempt must not admit another."""
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, role = _adm_inputs()
    sibling = SimpleNamespace(
        attempt_id="OTHER", status="running", is_terminal=lambda: False
    )
    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id="role-verify-op",
        attempts_for_task=lambda _t: [sibling],
    )
    assert not v.admitted
    assert v.refusal_code == "duplicate_active_attempt", v.refusal_code


def test_admission_refuses_a_verifier_equal_to_the_worker_role():
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, role = _adm_inputs()
    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id=role.role_id,  # SAME as the worker role
    )
    assert not v.admitted
    assert v.refusal_code == "verifier_not_distinct", v.refusal_code


def test_admission_refuses_an_empty_verifier():
    """Empty must REFUSE, not skip the comparison (the placement.py fail-open)."""
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, role = _adm_inputs()
    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id="",
    )
    assert not v.admitted
    assert v.refusal_code == "verifier_not_distinct", v.refusal_code


def test_admission_refuses_when_no_role_resolves():
    """A None RoleContract is a refusal, not an unchecked pass."""
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, _role = _adm_inputs()
    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=None,
        verifier_role_id="role-verify-op",
    )
    assert not v.admitted
    assert v.refusal_code == "role_not_authorized", v.refusal_code


def test_admission_enforces_the_intersection_of_role_and_grant_tools():
    """A tool permitted by the ROLE but not by the GRANT must still refuse —
    the bound is the INTERSECTION, not either set alone."""
    v = _adm(
        packet_kw={"required_tools": ["Edit"]},
        role_kw={"allowed_tools": ["Edit", "shell"]},
        grant_kw={"allowed_tools": ["shell"]},  # grant does NOT authorize Edit
    )
    assert not v.admitted
    assert v.refusal_code == "tool_not_authorized", v.refusal_code


def test_admission_refuses_when_no_plan_lookup_is_supplied():
    """An ABSENT resolver must REFUSE, never skip its check.

    `readiness.evaluate_execution_readiness` skipped its authorization check
    whenever no validator was injected, and `is_authorization_valid` still
    skips supersession when `latest_plan_lookup` is None. A guard that silently
    disappears with its resolver is the fail-open shape this module removes, so
    omitting the lookup is a refusal here.
    """
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, role = _adm_inputs()
    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id="role-verify-op",
        attempts_for_task=lambda _t: [],
        # plan_lookup deliberately omitted
    )
    assert not v.admitted
    assert v.refusal_code == "plan_lookup_unavailable", v.refusal_code


def test_admission_refuses_when_no_attempt_ledger_lookup_is_supplied():
    """Same rule for the sibling-attempt resolver."""
    from substrate.execution.attempts.admission import authorize_admission

    packet, grant, attempt, role = _adm_inputs()
    v = authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id="role-verify-op",
        plan_lookup=lambda _o: SimpleNamespace(plan_record_id="p", status="approved"),
        # attempts_for_task deliberately omitted
    )
    assert not v.admitted
    assert v.refusal_code == "sibling_lookup_unavailable", v.refusal_code


# ── adversarial-review round 3 (F1/F2/F3/F5) ───────────────────────────────


def test_disjoint_role_and_grant_tools_refuse_rather_than_vacate():
    """F1 (HIGH): a NARROWER operator bound must not admit MORE.

    The predicate was `t for t in pkt_tools if permitted_tools and t not in
    permitted_tools` — copied from readiness.py. It VACATES whenever
    `permitted_tools` is empty, and an empty set arises when role and grant
    tool sets are DISJOINT. So tightening `grant.allowed_tools` from ["shell"]
    (which correctly refused "Bash") to ["python"] (disjoint from role
    ["shell"]) turned the guard OFF and admitted "rm_rf".

    An inversion, not a gap — and a direct violation of this module's own rule
    that empty data is a REFUSAL.
    """
    v = _adm(
        packet_kw={"required_tools": ["rm_rf"]},
        role_kw={"allowed_tools": ["shell"]},
        grant_kw={"allowed_tools": ["python"]},  # DISJOINT from the role
    )
    assert not v.admitted, "disjoint role/grant tool sets admitted an arbitrary tool"
    assert v.refusal_code == "role_grant_tool_disjoint", v.refusal_code


def test_narrowing_the_operator_tool_bound_never_widens_what_is_admitted():
    """The monotonicity property F1 broke, stated directly.

    Whatever a broad bound refuses, a narrower bound must also refuse.
    """
    broad = _adm(
        packet_kw={"required_tools": ["Bash"]},
        role_kw={"allowed_tools": ["shell"]},
        grant_kw={"allowed_tools": ["shell"]},
    )
    narrowed = _adm(
        packet_kw={"required_tools": ["Bash"]},
        role_kw={"allowed_tools": ["shell"]},
        grant_kw={"allowed_tools": ["python"]},  # strictly narrower authority
    )
    assert not broad.admitted, "control: an unpermitted tool must refuse"
    assert not narrowed.admitted, (
        "narrowing the operator's tool bound ADMITTED work the broader bound "
        "refused — the guard inverts"
    )


def test_a_role_permitting_no_tools_refuses_a_task_that_needs_one():
    """An EMPTY role allowlist means the role permits NO tools — never 'no limit'."""
    v = _adm(
        packet_kw={"required_tools": ["shell"]},
        role_kw={"allowed_tools": []},
        grant_kw={"allowed_tools": []},
    )
    assert not v.admitted
    assert v.refusal_code == "tool_not_authorized", v.refusal_code


def test_a_task_needing_no_tools_is_unaffected_by_tool_bounds():
    """Control: the tool guard must not refuse work that requires no tools."""
    v = _adm(packet_kw={"required_tools": []}, grant_kw={"allowed_tools": ["python"]})
    assert v.admitted, (v.refusal_code, v.failed_checks())


def test_skill_allowlist_enforces_when_the_role_declares_one():
    """F2 (HIGH): the ALLOWLIST half must actually fire.

    Production's `_RoleView` had no `permitted_skill_ids` field at all, so
    `getattr(..., [])` supplied empty and the allowlist half was unreachable —
    a Task requiring ANY skill was admitted. The prohibited-skill test passed
    only because it injected a bespoke role object (injected-wiring confounder).
    """
    v = _adm(
        packet_kw={
            "requirements": {"required_skill_refs": [{"skill_id": "skill-EXFILTRATE"}]}
        },
        role_kw={"permitted_skill_ids": ["skill-ALLOWED"]},
    )
    assert not v.admitted, "a skill outside the role's allowlist was admitted"
    assert v.refusal_code == "skill_not_authorized", v.refusal_code


def test_production_role_view_carries_the_fields_admission_reads():
    """Field parity: a field `_RoleView` OMITS silently disables its guard.

    Admission reads role fields by `getattr` with an empty default, so an
    absent field is not "unset" — it is "this check never fires". This asserts
    the production role shape actually carries what admission consults.
    """
    from substrate.execution.attempts.field_control_plane import _default_role_resolver

    role = _default_role_resolver(None)
    for f in ("role_id", "allowed_tools", "permitted_skill_ids", "prohibited_skill_ids"):
        assert hasattr(role, f), (
            f"production role contract has no {f!r} — the admission guard that "
            f"reads it can never fire"
        )


def test_no_environment_class_refuses_even_when_rollback_is_declared():
    """F3 (MEDIUM): the corner where check 11 is the SOLE refuser.

    The `environment_classes=[]` vector is also refused by check 12
    (`structural_rollback = bool(env_classes) and ...`), so that case left
    check 11 deletable-green. With a DECLARED rollback, check 12 passes and
    only check 11 refuses — the one input where it is load-bearing.
    """
    v = _adm(
        grant_kw={
            "environment_classes": [],
            "rollback_obligations": ["snapshot restore"],
        }
    )
    assert not v.admitted, "no environment class was admitted"
    assert v.refusal_code == "no_environment_class", v.refusal_code


def test_negative_cost_limit_is_malformed_not_absent():
    """F5 (LOW): `<= 0.0` treated a negative ceiling as 'no ceiling declared'."""
    v = _adm(grant_kw={"cost_limit_usd": -5.0, "cost_enforceable": False})
    assert not v.admitted
    assert v.refusal_code == "malformed_cost_ceiling", v.refusal_code
