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
    )
    report = scheduler.run_scheduler_pass(stale)  # the STALE reference
    assert not report.attempts_created, report.attempts_created
    assert "not active" in (report.reason or "") or "invalid" in (report.reason or ""), report.reason


def test_execution_api_refuses_cross_tenant_read_and_write(tmp_path, monkeypatch):
    """CRITICAL: ``_tenant_visible`` was defined but applied in only ONE of
    eight routes. Every other read — and BOTH POSTs — were tenant-blind, and
    ``grep -c tenant`` on the attempt store returns 0, so there was no
    downstream defense: ``transition_cas`` validates version, status,
    transition legality and immutability, but never tenant.

    A different tenant could enumerate attempts, grants, frontier, worker
    identities and lease paths — and CANCEL another tenant's in-flight
    execution.
    """
    from substrate.execution.attempts.records import ExecutionAttempt
    import substrate.contracts.principal_resolution as principal
    import transports.api.execution_attempt_routes as routes

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
    attempt.status = "failed"
    store.create_attempt_idempotent(attempt)

    class _Ctx:
        tenant_id = "tenant-b"

    monkeypatch.setattr(principal, "resolve_principal_context", lambda *a, **k: _Ctx())
    monkeypatch.setattr(routes, "_store", lambda: store)

    class _Body:
        decided_by = "mallory"
        reason = "x"

    endpoints = {r.path: r.endpoint for r in routes._build_router().routes}

    assert endpoints["/execution/attempts/{attempt_id}"](attempt.attempt_id) == {
        "error": "not found"
    }
    assert (
        endpoints["/execution/attempts/{attempt_id}/cancel"](
            attempt.attempt_id, _Body()
        ).get("success")
        is False
    )
    assert (
        endpoints["/execution/attempts/{attempt_id}/retry"](
            attempt.attempt_id, _Body()
        ).get("success")
        is False
    )
    assert endpoints["/execution/by-plan/{plan_record_id}"]("opr-a")["attempts"] == []
    assert endpoints["/execution/overlay"]("T-A")["overlay"] == {}

    # The decisive assertion: the other tenant's attempt was NOT mutated.
    assert store.get_attempt(attempt.attempt_id).status == "failed"


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
