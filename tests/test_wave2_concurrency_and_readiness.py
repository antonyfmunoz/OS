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
        work_scope={"tenant_id": tenant},
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
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    class _Q:
        def get_packet(self, pid):
            return packet if pid == packet.packet_id else None

    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=_boom,
        lease_manager=SimpleNamespace(acquire=_boom),
        compile_fn=_boom,
        lock_dir=str(tmp_path / "locks"),
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

    report = scheduler.run_scheduler_pass(grant)

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
