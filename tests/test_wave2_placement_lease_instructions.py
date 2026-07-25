"""Wave 2 C3 — placement, environment lease, and instruction compilation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.execution.attempts.dispatch import (
    DispatchBlocked,
    compile_attempt_package,
)
from substrate.execution.attempts.leases import LeaseError, LeaseManager
from substrate.execution.attempts.placement import PlacementError, place_attempt
from substrate.execution.attempts.records import ExecutionAttempt
from substrate.execution.attempts.store import ExecutionAttemptStore


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


def _packet(**kw):
    base = dict(
        packet_id="wp-a",
        title="backend change",
        user_intent="add search",
        desired_end_state="search works",
        constraints=[],
        validation_plan="run tests",
        required_tools=["shell", "git"],
        requirements={
            "required_skill_refs": [{"skill_id": "python"}],
            "required_capability_ids": ["code_write"],
        },
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _grant(**kw):
    base = dict(
        decision_ref="objective_plan:opr-1:execution_authorization:v1",
        tenant_id="tenant-a",
        task_frontier=["wp-a"],
        environment_classes=["git_worktree"],
        credential_scope_refs=[],
        risk_ceiling="high",
        authorized_scope_hash="hash123",
        verification_obligations=["independent verify"],
        cost_limit_usd=0.0,
        cost_enforceable=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _role(role_id="role-impl-op"):
    return SimpleNamespace(role_id=role_id, allowed_tools=["shell", "git"])


def _workers():
    return [
        {
            "worker_identity": "cc_cli_worktree@vps",
            "agent_type": "builder",
            "capabilities": ["code_write", "test"],
            "reliability": 0.9,
            "model_profile": {"model": "claude-opus"},
            "harness_profile": {"harness": "cc_cli"},
        },
        {
            "worker_identity": "codex@vps",
            "agent_type": "builder",
            "capabilities": ["code_write"],
            "reliability": 0.6,
            "model_profile": {"model": "codex"},
            "harness_profile": {"harness": "codex"},
        },
    ]


def _nodes():
    return [
        {"node_id": "vps", "headroom": 4},
        {"node_id": "beast", "headroom": 8},
    ]


# ── Placement ────────────────────────────────────────────────────────────────


def test_placement_records_full_assignment(store):
    asn = place_attempt(
        packet=_packet(),
        grant=_grant(),
        role_contract=_role(),
        attempt_id="ea-1",
        worker_candidates=_workers(),
        compute_nodes=_nodes(),
        verifier_role_id="role-verify-op",
        store=store,
        mutation_runner=_runner(),
    )
    assert asn.role_contract_id == "role-impl-op"
    assert asn.worker_identity == "cc_cli_worktree@vps"  # highest score
    assert asn.verifier_role_id == "role-verify-op"
    assert asn.compute_node_id == "beast"  # highest headroom
    assert asn.model_profile["model"] == "claude-opus"
    assert asn.skill_requirement_refs == [{"skill_id": "python"}]
    assert asn.tool_profile == ["shell", "git"]
    assert "codex@vps" in asn.alternatives
    # Durably persisted + reconstructable.
    assert store.assignment_for_attempt("ea-1")["assignment_id"] == asn.assignment_id


def test_placement_is_deterministic(store):
    kw = dict(
        packet=_packet(),
        grant=_grant(),
        role_contract=_role(),
        worker_candidates=_workers(),
        compute_nodes=_nodes(),
        verifier_role_id="role-verify-op",
        persist=False,
    )
    a = place_attempt(attempt_id="ea-1", **kw)
    b = place_attempt(attempt_id="ea-2", **kw)
    assert a.worker_identity == b.worker_identity
    assert a.compute_node_id == b.compute_node_id
    assert a.deterministic_scores == b.deterministic_scores


def test_placement_separation_of_duty(store):
    with pytest.raises(PlacementError):
        place_attempt(
            packet=_packet(),
            grant=_grant(),
            role_contract=_role("role-impl-op"),
            attempt_id="ea-1",
            worker_candidates=_workers(),
            compute_nodes=_nodes(),
            verifier_role_id="role-impl-op",  # same as worker role → SoD violation
            persist=False,
        )


def test_placement_no_eligible_worker_fails_closed(store):
    with pytest.raises(PlacementError):
        place_attempt(
            packet=_packet(requirements={"required_capability_ids": ["quantum"]}),
            grant=_grant(),
            role_contract=_role(),
            attempt_id="ea-1",
            worker_candidates=_workers(),
            compute_nodes=_nodes(),
            verifier_role_id="role-verify-op",
            persist=False,
        )


# ── Environment lease ────────────────────────────────────────────────────────


class _FakeSandbox:
    def __init__(self, repo_root, worktree_path):
        self._repo_root = repo_root
        self._wt = worktree_path
        self.cleaned = []

    def create_sandbox(self, candidate_id, candidate_slug, agent_type="developer_agent"):
        return SimpleNamespace(
            worktree_path=self._wt,
            branch_name="attempt/wp-a",
            base_commit="base123",
            sandbox_id="sb-1",
        )

    def cleanup_sandbox(self, sandbox_id):
        self.cleaned.append(sandbox_id)


def _attempt():
    a = ExecutionAttempt(task_id="wp-a", attempt_number=1)
    a.attempt_id = "ea-1"
    return a


def test_lease_acquire_and_one_active_per_task(store, tmp_path):
    sandbox = _FakeSandbox(str(tmp_path / "repo"), str(tmp_path / "wt"))
    lm = LeaseManager(store, sandbox, mutation_runner=_runner())
    asn = SimpleNamespace(
        worker_identity="w",
        compute_node_id="vps",
        environment_class="git_worktree",
        tool_profile=["shell"],
        worker_agent_type="builder",
    )
    lease = lm.acquire(attempt=_attempt(), assignment=asn, grant=_grant())
    assert lease.status == "active"
    assert lease.worktree_path == str(tmp_path / "wt")
    assert lease.snapshot_ref == "base123"
    # Honest enforcement ledger.
    assert lease.enforcement["diff_scope_post_hoc"] == "enforced"
    assert lease.enforcement["filesystem_namespace"] == "declared"
    # One active lease per task.
    with pytest.raises(LeaseError):
        lm.acquire(attempt=_attempt(), assignment=asn, grant=_grant())


def test_lease_rejects_repo_root_workspace(store, tmp_path):
    repo = str(tmp_path / "repo")
    sandbox = _FakeSandbox(repo, repo)  # worktree == repo root → forbidden
    lm = LeaseManager(store, sandbox, mutation_runner=_runner())
    asn = SimpleNamespace(
        worker_identity="w",
        compute_node_id="vps",
        environment_class="git_worktree",
        tool_profile=[],
        worker_agent_type="b",
    )
    with pytest.raises(LeaseError):
        lm.acquire(attempt=_attempt(), assignment=asn, grant=_grant())
    assert sandbox.cleaned == ["sb-1"]  # the bad worktree was cleaned up


def test_lease_release_and_revoke(store, tmp_path):
    sandbox = _FakeSandbox(str(tmp_path / "repo"), str(tmp_path / "wt"))
    lm = LeaseManager(store, sandbox, mutation_runner=_runner())
    asn = SimpleNamespace(
        worker_identity="w",
        compute_node_id="vps",
        environment_class="git_worktree",
        tool_profile=[],
        worker_agent_type="b",
    )
    lease = lm.acquire(attempt=_attempt(), assignment=asn, grant=_grant())
    lm.release(lease.lease_id)
    assert store.get_lease(lease.lease_id)["status"] == "released"
    # A new lease can now be acquired (previous released).
    lease2 = lm.acquire(attempt=_attempt(), assignment=asn, grant=_grant())
    lm.revoke(lease2.lease_id, "operator revoke")
    assert store.get_lease(lease2.lease_id)["status"] == "revoked"


# ── Instruction compilation ──────────────────────────────────────────────────


def _assignment_for_pkg():
    return SimpleNamespace(
        role_contract_id="role-impl-op",
        skill_requirement_refs=[{"skill_id": "python"}],
        tool_profile=["shell", "git"],
        model_profile={"model": "claude-opus"},
        environment_class="git_worktree",
    )


def _attempt_for_pkg():
    a = ExecutionAttempt(
        task_id="wp-a",
        plan_record_id="opr-1",
        plan_version=1,
        execution_authorization_ref="objective_plan:opr-1:execution_authorization:v1",
        timeout_seconds=600,
        max_turns=30,
    )
    a.attempt_id = "ea-1"
    return a


def test_compile_package_sealed_and_hashed():
    pkg = compile_attempt_package(
        attempt=_attempt_for_pkg(),
        packet=_packet(),
        assignment=_assignment_for_pkg(),
        grant=_grant(),
    )
    assert pkg.package_hash
    # The sealed hash covers operation_identity + governance + verification.
    assert pkg.compute_hash() == pkg.package_hash
    assert pkg.operation_identity["task_id"] == "wp-a"
    assert any("authorization_ref=" in g for g in pkg.governance_constraints)
    assert pkg.output_schema["required"] == ["status", "summary"]


def test_compile_package_tamper_changes_hash():
    pkg = compile_attempt_package(
        attempt=_attempt_for_pkg(),
        packet=_packet(),
        assignment=_assignment_for_pkg(),
        grant=_grant(),
    )
    original = pkg.package_hash
    pkg.governance_constraints.append("tampered=true")
    assert pkg.compute_hash() != original


def test_compilation_failure_blocks_dispatch():
    # No model in the model_profile → compile_instruction_package raises →
    # DispatchBlocked (fail closed, never dispatched).
    bad_assignment = _assignment_for_pkg()
    bad_assignment.model_profile = {}  # missing required "model"
    with pytest.raises(DispatchBlocked):
        compile_attempt_package(
            attempt=_attempt_for_pkg(),
            packet=_packet(),
            assignment=bad_assignment,
            grant=_grant(),
        )
