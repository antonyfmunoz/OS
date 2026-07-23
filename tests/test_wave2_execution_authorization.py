"""Wave 2 C2 — execution authorization + activation unit of work.

Proves the Amendment v1 clause-1/clause-2 contract:
- ApprovalRequest is the Decision; the grant is only its bounded effect;
- plan acceptance grants zero execution authority (no grant until requested);
- a rejected Decision creates no ACTIVE grant;
- an approved Decision creates ONE bounded grant, ACTIVE only after every Task
  transition commits;
- stale/expired/revoked/invalidated grants fail;
- duplicate approval is idempotent;
- partial activation resumes without duplicate Tasks/grants/events.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.activation import activate_authorized_tasks
from substrate.execution.attempts.decisions import (
    ExecutionAuthorizationDecisionSource,
    ExecutionDecisionConflict,
    apply_execution_decision,
    execution_decision_ref,
    is_authorization_valid,
    request_execution_authorization,
    sweep_expired_authorizations,
)
from substrate.execution.attempts.records import ExecutionAuthorizationGrantStatus
from substrate.execution.attempts.store import ExecutionAttemptStore
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket


# ── Test doubles ─────────────────────────────────────────────────────────────


def _runner():
    """A governed-mutation runner double that runs execute_fn and reports success
    (stands in for the daemon-backed governed_mutation; the HIGH-risk decision
    spec is not degraded-eligible, so tests inject this explicitly)."""

    def run(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    return run


def _plan(status="approved", version=1, plan_id="opr-1", objective_id="goal-1", tasks=None):
    return SimpleNamespace(
        plan_record_id=plan_id,
        graph_version=version,
        objective_id=objective_id,
        status=status,
        workpacket_ids=tasks or ["wp-a", "wp-b"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
    )


@pytest.fixture()
def store(tmp_path):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / "attempts.jsonl"),
        grants_path=str(tmp_path / "grants.jsonl"),
        readiness_path=str(tmp_path / "readiness.jsonl"),
        leases_path=str(tmp_path / "leases.jsonl"),
    )


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(exist_ok=True)
    q = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    # Two PLANNED packets with the execution gate set (as the compiler produces).
    for pid in ("wp-a", "wp-b"):
        pkt = WorkPacket(
            title=pid,
            user_intent=f"do {pid}",
            approval_gates=["execution_authorization_required"],
            work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
        )
        pkt.packet_id = pid
        q.ingest_work_packet(pkt)
        q.update_packet_status(pid, PacketLifecycleStatus.CLASSIFIED, "test")
        q.update_packet_status(pid, PacketLifecycleStatus.PLANNED, "test")
    return q


# ── Request ──────────────────────────────────────────────────────────────────


def test_request_requires_accepted_plan(store):
    with pytest.raises(ExecutionDecisionConflict):
        request_execution_authorization(
            store, plan=_plan(status="awaiting_approval"), task_frontier=["wp-a"],
            tenant_id="tenant-a", mutation_runner=_runner(),
        )


def test_request_creates_one_activating_grant_no_authority(store):
    grant, approval = request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    assert grant.status == ExecutionAuthorizationGrantStatus.ACTIVATING.value
    assert approval.decision_kind == "execution_authorization"
    assert approval.authorization_effect == "execute_bounded_task_set"
    # A grant in ACTIVATING conveys no execution authority yet.
    ok, _ = is_authorization_valid(grant)
    assert ok is False
    # Idempotent: second request returns the SAME grant, no duplicate row.
    grant2, _ = request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    assert grant2.grant_id == grant.grant_id
    assert len(store.grants_for_plan("opr-1")) == 1


# ── Reject ───────────────────────────────────────────────────────────────────


def test_reject_creates_no_active_grant(store):
    ref = execution_decision_ref(_plan())
    request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    grant = apply_execution_decision(store, ref, "reject", mutation_runner=_runner())
    assert grant.status == ExecutionAuthorizationGrantStatus.FAILED_ACTIVATION.value
    assert not store.active_grants()


# ── Approve + activation unit of work ────────────────────────────────────────


def test_approve_activates_all_tasks_then_grant_active(store, queue):
    ref = execution_decision_ref(_plan())
    request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )

    def _activate(g):
        return activate_authorized_tasks(store, g, queue, mutation_runner=_runner())

    grant = apply_execution_decision(
        store, ref, "approve", activate_fn=_activate,
        latest_plan_lookup=lambda oid: _plan(), mutation_runner=_runner(),
    )
    assert grant.status == ExecutionAuthorizationGrantStatus.ACTIVE.value
    # Both Tasks walked PLANNED → APPROVED through canonical WorkPacket authority.
    assert queue.get_packet("wp-a").status == PacketLifecycleStatus.APPROVED
    assert queue.get_packet("wp-b").status == PacketLifecycleStatus.APPROVED
    # Now the grant is valid.
    ok, _ = is_authorization_valid(grant, latest_plan_lookup=lambda oid: _plan())
    assert ok is True


def test_duplicate_approval_idempotent(store, queue):
    ref = execution_decision_ref(_plan())
    request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )

    def _activate(g):
        return activate_authorized_tasks(store, g, queue, mutation_runner=_runner())

    g1 = apply_execution_decision(store, ref, "approve", activate_fn=_activate,
                                  latest_plan_lookup=lambda oid: _plan(), mutation_runner=_runner())
    g2 = apply_execution_decision(store, ref, "approve", activate_fn=_activate,
                                  latest_plan_lookup=lambda oid: _plan(), mutation_runner=_runner())
    assert g1.status == g2.status == ExecutionAuthorizationGrantStatus.ACTIVE.value
    assert len(store.grants_for_plan("opr-1")) == 1


def test_partial_activation_resumes_without_duplicates(store, queue):
    """If activation fails on one Task, the grant is FAILED_ACTIVATION and a
    retry resumes: already-APPROVED Tasks are skipped, no duplicate transitions."""
    ref = execution_decision_ref(_plan(tasks=["wp-a", "wp-b", "wp-missing"]))
    request_execution_authorization(
        store, plan=_plan(tasks=["wp-a", "wp-b", "wp-missing"]),
        task_frontier=["wp-a", "wp-b", "wp-missing"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    grant = store.get_grant(ref)
    # First activation: wp-missing is absent from the queue → partial failure.
    grant = activate_authorized_tasks(store, grant, queue, mutation_runner=_runner())
    assert grant.status == ExecutionAuthorizationGrantStatus.FAILED_ACTIVATION.value
    # wp-a and wp-b DID transition and are recorded as activated.
    assert set(grant.activated_task_ids) == {"wp-a", "wp-b"}
    assert queue.get_packet("wp-a").status == PacketLifecycleStatus.APPROVED
    # Add the missing packet and retry — resumes, does not re-transition wp-a/wp-b.
    pkt = WorkPacket(title="wp-missing", user_intent="x",
                     approval_gates=["execution_authorization_required"],
                     work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"})
    pkt.packet_id = "wp-missing"
    queue.ingest_work_packet(pkt)
    queue.update_packet_status("wp-missing", PacketLifecycleStatus.CLASSIFIED, "t")
    queue.update_packet_status("wp-missing", PacketLifecycleStatus.PLANNED, "t")
    # Reset grant to ACTIVATING for the resume (a real retry re-enters activation).
    grant.status = ExecutionAuthorizationGrantStatus.ACTIVATING.value
    store.update_grant_cas(grant, expected_record_version=grant.record_version)
    grant = activate_authorized_tasks(store, grant, queue, mutation_runner=_runner())
    assert grant.status == ExecutionAuthorizationGrantStatus.ACTIVE.value
    assert set(grant.activated_task_ids) == {"wp-a", "wp-b", "wp-missing"}


# ── Expiry / revocation / invalidation ───────────────────────────────────────


def test_expired_grant_is_swept_and_invalid(store):
    request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a"], tenant_id="tenant-a",
        ttl_seconds=1.0, now=1000.0, mutation_runner=_runner(),
    )
    n = sweep_expired_authorizations(store, now=2000.0, mutation_runner=_runner())
    assert n == 1
    ref = execution_decision_ref(_plan())
    grant = store.get_grant(ref)
    assert grant.status == ExecutionAuthorizationGrantStatus.EXPIRED.value


def test_revoke_active_grant(store, queue):
    ref = execution_decision_ref(_plan())
    request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    apply_execution_decision(
        store, ref, "approve",
        activate_fn=lambda g: activate_authorized_tasks(store, g, queue, mutation_runner=_runner()),
        latest_plan_lookup=lambda oid: _plan(), mutation_runner=_runner(),
    )
    grant = apply_execution_decision(store, ref, "revoke", mutation_runner=_runner())
    assert grant.status == ExecutionAuthorizationGrantStatus.REVOKED.value


def test_approve_after_plan_revision_is_invalidated(store):
    ref = execution_decision_ref(_plan(version=1))
    request_execution_authorization(
        store, plan=_plan(version=1), task_frontier=["wp-a"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    # A newer plan version now exists → approving the stale grant invalidates it.
    with pytest.raises(ExecutionDecisionConflict):
        apply_execution_decision(
            store, ref, "approve",
            latest_plan_lookup=lambda oid: _plan(version=2, plan_id="opr-2"),
            mutation_runner=_runner(),
        )
    grant = store.get_grant(ref)
    assert grant.status == ExecutionAuthorizationGrantStatus.INVALIDATED.value


# ── HUD source ───────────────────────────────────────────────────────────────


def test_decision_source_surfaces_pending_and_approves(store, queue):
    request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    src = ExecutionAuthorizationDecisionSource(
        store,
        latest_plan_lookup=lambda oid: _plan(),
        activate_fn=lambda g: activate_authorized_tasks(store, g, queue, mutation_runner=_runner()),
        mutation_runner=_runner(),
    )
    pending = src.pending_decisions()
    assert len(pending) == 1
    assert pending[0].source_type.value == "execution_authorization"
    assert pending[0].risk_class == "high"
    assert pending[0].context["details"]["task_frontier"] == ["wp-a", "wp-b"]

    ref = pending[0].approval_id
    assert src.approve(ref) is True
    assert not src.pending_decisions()  # no longer pending once ACTIVE


# ── Chat request seam: surfaces the HUD decision, starts zero attempts ────────


def test_execution_request_surfaces_decision_and_starts_zero_attempts(store):
    """The seam the chat rail calls: requesting execution creates an ACTIVATING
    grant (a HUD decision) and ZERO ExecutionAttempts. Plan acceptance conveyed
    no execution authority; the chat request conveys none either — only the HUD
    approval does."""
    grant, approval = request_execution_authorization(
        store, plan=_plan(), task_frontier=["wp-a", "wp-b"], tenant_id="tenant-a",
        mutation_runner=_runner(),
    )
    # A HUD decision now exists...
    assert grant.status == ExecutionAuthorizationGrantStatus.ACTIVATING.value
    src = ExecutionAuthorizationDecisionSource(store)
    assert len(src.pending_decisions()) == 1
    # ...but ZERO ExecutionAttempts have been created (nothing runs pre-HUD).
    assert store.active_attempts() == []
    assert store.attempts_for_task("wp-a") == []
    assert store.attempts_for_task("wp-b") == []
