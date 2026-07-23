"""Wave 2 C2 — ExecutionReadinessAssessment 15-check fail-closed matrix."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.readiness import (
    ExecutionReadinessState,
    evaluate_execution_readiness,
)


def _packet(**kw):
    base = dict(
        packet_id="wp-a",
        status=SimpleNamespace(value="planned"),
        dependencies=[],
        required_role_contracts=["role-impl-op"],
        required_tools=["shell"],
        approval_gates=["execution_authorization_required"],
        validation_plan="verify it",
        rollback_plan="undo it",
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
        requirements={"required_skill_refs": [{"skill_id": "python"}]},
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _plan(**kw):
    base = dict(
        plan_record_id="opr-1",
        graph_version=1,
        objective_id="goal-1",
        status="approved",
        workpacket_ids=["wp-a"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _grant(**kw):
    base = dict(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        plan_version=1,
        status="active",
        tenant_id="tenant-a",
        task_frontier=["wp-a"],
        max_attempts_per_task=2,
        role_ids=["role-impl-op"],
        environment_classes=["git_worktree"],
        allowed_tools=["shell", "git"],
        credential_scope_refs=[],
        verification_obligations=["independent verify"],
        rollback_obligations=["git reset"],
        cost_limit_usd=0.0,
        cost_enforceable=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _role(**kw):
    base = dict(
        role_id="role-impl-op",
        permitted_skill_ids=["python", "typescript"],
        prohibited_skill_ids=[],
        allowed_tools=["shell", "git"],
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _valid(_g):
    return (True, "valid")


def _verifier(_pkt):
    return "role-verify-op"


def _base_call(**overrides):
    kwargs = dict(
        packet=_packet(),
        plan=_plan(),
        authorization=_grant(),
        role_contract=_role(),
        next_attempt_number=1,
        is_authorization_valid=_valid,
        dep_success_lookup=lambda d: True,
        verifier_role_resolver=_verifier,
    )
    kwargs.update(overrides)
    return evaluate_execution_readiness(**kwargs)


def test_all_checks_pass_authorized():
    a = _base_call()
    assert a.state == ExecutionReadinessState.AUTHORIZED.value, a.blocking_items
    assert len(a.checks) == 15
    assert all(c["passed"] for c in a.checks)


def test_ready_when_grant_not_yet_active():
    a = _base_call(authorization=_grant(status="activating"))
    # All checks pass but the grant isn't ACTIVE yet → READY (pre-grant), not AUTHORIZED.
    assert a.state == ExecutionReadinessState.READY.value


def test_tenant_mismatch_prohibited():
    a = _base_call(packet=_packet(work_scope={"tenant_id": "other", "target_kind": "x"}))
    assert a.state == ExecutionReadinessState.PROHIBITED.value
    assert not a.passed("tenant_match")


def test_prohibited_skill_prohibited():
    a = _base_call(role_contract=_role(prohibited_skill_ids=["python"]))
    assert a.state == ExecutionReadinessState.PROHIBITED.value
    assert not a.passed("skills_role_authorized")


def test_terminal_task_blocked():
    a = _base_call(packet=_packet(status=SimpleNamespace(value="completed")))
    assert a.state == ExecutionReadinessState.BLOCKED.value
    assert not a.passed("task_canonical_not_terminal")


def test_unsatisfied_dependency_blocked():
    a = _base_call(
        packet=_packet(dependencies=["wp-dep"]),
        dep_success_lookup=lambda d: False,
    )
    assert a.state == ExecutionReadinessState.BLOCKED.value
    assert not a.passed("dependencies_satisfied")


def test_task_not_in_frontier_authorization_required():
    a = _base_call(authorization=_grant(task_frontier=["wp-other"]))
    assert a.state == ExecutionReadinessState.AUTHORIZATION_REQUIRED.value


def test_attempt_budget_exhausted_authorization_required():
    a = _base_call(next_attempt_number=3)  # max is 2
    assert a.state == ExecutionReadinessState.AUTHORIZATION_REQUIRED.value


def test_expired_authorization_expired():
    a = _base_call(is_authorization_valid=lambda g: (False, "grant expired"))
    assert a.state == ExecutionReadinessState.EXPIRED.value


def test_unenforceable_cost_ceiling_blocks():
    a = _base_call(authorization=_grant(cost_limit_usd=5.0, cost_enforceable=False))
    assert not a.passed("cost_bounded")
    assert a.state == ExecutionReadinessState.BLOCKED.value


def test_enforceable_cost_ceiling_ok():
    a = _base_call(authorization=_grant(cost_limit_usd=5.0, cost_enforceable=True))
    assert a.passed("cost_bounded")


def test_verifier_must_differ_from_worker_role():
    a = _base_call(verifier_role_resolver=lambda p: "role-impl-op")  # same as worker role
    assert not a.passed("verifier_and_proof_contract")


def test_missing_sandbox_or_rollback_blocks():
    a = _base_call(authorization=_grant(environment_classes=[]))
    assert not a.passed("sandbox_rollback_defined")
