#!/usr/bin/env python3
"""security_smoke_test.py — End-to-end smoke test for core.security.

Runs against a temp data dir so it never touches production state.
Covers:

    1. IdentityStore — create user, authenticate, verify token, revoke
    2. RBACEngine   — role checks at each risk tier
    3. ApprovalQueue — create, approve, reject, self-approval block
    4. AuditLog     — append, chain verify, tamper detection
    5. ExecutionContext — path guards, timeouts
    6. SecurityContext — end-to-end authorize_action flow
    7. ActionSystem integration — security-gated execute() path

Exit code 0 = all checks passed. Non-zero = specific failure printed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.capability import OperationKind, RiskTier  # noqa: E402
from core.security.approval import (  # noqa: E402
    ApprovalError,
    ApprovalQueue,
    ApprovalStatus,
)
from core.security.audit import AuditLog  # noqa: E402
from core.security.context import SecurityContext  # noqa: E402
from core.security.environments import env_for_name  # noqa: E402
from core.security.execution import (  # noqa: E402
    ExecutionContext,
    ExecutionDenied,
    RestrictedExecutor,
)
from core.security.identity import AuthError, IdentityStore  # noqa: E402
from core.security.rbac import RBACEngine, RoleName  # noqa: E402


class SmokeFail(SystemExit):
    def __init__(self, msg: str) -> None:
        super().__init__(f"SMOKE FAIL: {msg}")


def assert_eq(actual, expected, label: str) -> None:
    if actual != expected:
        raise SmokeFail(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(cond: bool, label: str) -> None:
    if not cond:
        raise SmokeFail(label)


def step(name: str) -> None:
    print(f"[smoke] {name}")


# ─── Tests ──────────────────────────────────────────────────────────────────


def test_identity(tmp: Path) -> None:
    step("identity: create + auth + verify + revoke")
    store = IdentityStore(
        users_path=tmp / "users.jsonl",
        secret_path=tmp / "secret.key",
        revocations_path=tmp / "revocations.jsonl",
    )

    user, raw_key = store.create_user("alice", "operator", display_name="Alice")
    assert_eq(user.user_id, "alice", "alice created")
    assert_true(len(raw_key) > 10, "api_key issued")

    # Wrong key
    try:
        store.authenticate("alice", "wrong-key")
        raise SmokeFail("wrong key should not authenticate")
    except AuthError:
        pass

    # Right key
    token = store.authenticate("alice", raw_key)
    assert_eq(token.user_id, "alice", "token user_id")
    assert_eq(token.role, "operator", "token role")

    # Verify round-trip
    reparsed = store.verify(token.raw)
    assert_eq(reparsed.jti, token.jti, "verify round-trip")

    # Revoke
    store.revoke(token.jti, reason="smoke test")
    try:
        store.verify(token.raw)
        raise SmokeFail("revoked token should not verify")
    except AuthError:
        pass

    # Role reassignment
    store.assign_role("alice", "admin")
    fresh_token = store.authenticate("alice", raw_key)
    assert_eq(fresh_token.role, "admin", "role after reassignment")

    # Disable
    store.disable_user("alice")
    try:
        store.authenticate("alice", raw_key)
        raise SmokeFail("disabled user should not authenticate")
    except AuthError:
        pass


def test_rbac() -> None:
    step("rbac: role checks")
    engine = RBACEngine()

    # Viewer: read ok
    c = engine.check(RoleName.VIEWER, OperationKind.READ_GRAPH, risk="none")
    assert_true(c.allowed and not c.needs_approval, "viewer can read")

    # Viewer: write denied
    c = engine.check(RoleName.VIEWER, OperationKind.EDIT_FILE, risk="low")
    assert_true(not c.allowed, "viewer cannot edit")

    # Operator: edit at low — auto
    c = engine.check(RoleName.OPERATOR, OperationKind.EDIT_FILE, risk="low")
    assert_true(c.allowed and not c.needs_approval, "operator edit-low auto")

    # Operator: edit at high — needs approval
    c = engine.check(RoleName.OPERATOR, OperationKind.EDIT_FILE, risk="high")
    assert_true(c.allowed and c.needs_approval, "operator edit-high needs approval")

    # Operator: delete denied
    c = engine.check(RoleName.OPERATOR, OperationKind.DELETE_FILE, risk="high")
    assert_true(not c.allowed, "operator cannot delete")

    # Admin: delete allowed
    c = engine.check(RoleName.ADMIN, OperationKind.DELETE_FILE, risk="critical")
    assert_true(c.allowed, "admin can delete-critical")

    # Approval authority
    assert_true(
        engine.can_approve(RoleName.OPERATOR, RiskTier.HIGH),
        "operator approves HIGH",
    )
    assert_true(
        not engine.can_approve(RoleName.OPERATOR, RiskTier.CRITICAL),
        "operator does NOT approve CRITICAL",
    )
    assert_true(
        engine.can_approve(RoleName.ADMIN, RiskTier.CRITICAL),
        "admin approves CRITICAL",
    )
    assert_true(
        not engine.can_approve(RoleName.VIEWER, RiskTier.LOW),
        "viewer approves nothing",
    )


def test_approval_queue(tmp: Path) -> None:
    step("approval: create + approve + reject + self-approve block")
    q = ApprovalQueue(approvals_dir=tmp / "approvals")

    req = q.create_request(
        requester="alice",
        requester_role="operator",
        action_type="edit_file",
        target="eos_ai/memory.py",
        operation="edit_file",
        risk="high",
        reason="fix logging",
    )
    assert_eq(req.status, ApprovalStatus.PENDING, "new request pending")

    # Self-approval blocked
    try:
        q.approve(
            req.request_id,
            approver="alice",
            approver_role="operator",
            can_approve_risk=True,
        )
        raise SmokeFail("self-approval should be blocked")
    except ApprovalError:
        pass

    # Non-self approval works
    decided = q.approve(
        req.request_id,
        approver="bob",
        approver_role="admin",
        can_approve_risk=True,
        reason="lgtm",
    )
    assert_eq(decided.status, ApprovalStatus.APPROVED, "approved")
    assert_eq(decided.approver, "bob", "approver recorded")

    # Can't re-approve
    try:
        q.approve(
            req.request_id,
            approver="bob",
            approver_role="admin",
            can_approve_risk=True,
        )
        raise SmokeFail("double-approve should fail")
    except ApprovalError:
        pass

    # Reject flow
    r2 = q.create_request(
        requester="alice",
        requester_role="operator",
        action_type="delete_file",
        target="some/file.py",
        operation="delete_file",
        risk="critical",
    )
    rejected = q.reject(
        r2.request_id,
        approver="bob",
        approver_role="admin",
        reason="too risky",
    )
    assert_eq(rejected.status, ApprovalStatus.REJECTED, "rejected")


def test_audit(tmp: Path) -> None:
    step("audit: append + chain verify + tamper detect")
    log = AuditLog(path=tmp / "audit.jsonl")

    ev1 = log.record(
        user="alice",
        role="operator",
        action="edit_file",
        target="a.py",
        outcome="allowed",
    )
    ev2 = log.record(
        user="alice",
        role="operator",
        action="edit_file",
        target="b.py",
        outcome="allowed",
    )
    ev3 = log.record(
        user="alice",
        role="operator",
        action="edit_file",
        target="c.py",
        outcome="denied",
        reason="rbac",
    )

    assert_true(ev1.prev_hash == "0" * 64, "genesis prev_hash")
    assert_eq(ev2.prev_hash, ev1.hash, "chain link 1→2")
    assert_eq(ev3.prev_hash, ev2.hash, "chain link 2→3")

    ok, detail = log.verify_chain()
    assert_true(ok, f"chain verify: {detail}")

    # Tamper: rewrite the middle row's target
    raw = (tmp / "audit.jsonl").read_text().splitlines()
    row = json.loads(raw[1])
    row["target"] = "TAMPERED.py"
    raw[1] = json.dumps(row)
    (tmp / "audit.jsonl").write_text("\n".join(raw) + "\n")

    ok, detail = log.verify_chain()
    assert_true(not ok, f"tamper detection: {detail}")


def test_execution(tmp: Path) -> None:
    step("execution: path guard + timeout")
    tmp.mkdir(parents=True, exist_ok=True)
    scope = tmp / "scope"
    scope.mkdir(parents=True, exist_ok=True)
    (scope / "hello.txt").write_text("hi")

    ctx = ExecutionContext(
        name="smoke",
        allowed_paths=[str(scope)],
        denied_paths=[str(scope / "nope")],
        timeout_seconds=2,
    )

    # Allowed read
    ctx.check_path(str(scope / "hello.txt"), mode="r")

    # Outside allow-list
    try:
        ctx.check_path("/etc/passwd", mode="r")
        raise SmokeFail("etc/passwd should be denied")
    except ExecutionDenied:
        pass

    # Shell metachar blocked
    try:
        ctx.check_command(["echo", "hi; rm -rf /"])
        raise SmokeFail("shell metachar should be denied")
    except ExecutionDenied:
        pass

    # Timeout
    exe = RestrictedExecutor(ctx)
    result = exe.run(["sleep", "5"], cwd=str(scope))
    assert_true(result.timed_out, "sleep 5 should time out at 2s")

    # Successful run
    result = exe.run(["ls"], cwd=str(scope))
    assert_eq(result.returncode, 0, "ls in scope")
    assert_true("hello.txt" in result.stdout, "ls sees hello.txt")


def test_security_context(tmp: Path) -> None:
    step("context: end-to-end authorize_action")
    tmp.mkdir(parents=True, exist_ok=True)
    sec_dir = tmp / "sec"
    sec_dir.mkdir(parents=True, exist_ok=True)

    identity = IdentityStore(
        users_path=sec_dir / "users.jsonl",
        secret_path=sec_dir / "secret.key",
        revocations_path=sec_dir / "revocations.jsonl",
    )
    alice, alice_key = identity.create_user("alice", "operator")
    bob, bob_key = identity.create_user("bob", "admin")

    sec = SecurityContext(
        identity=identity,
        rbac=RBACEngine(),
        queue=ApprovalQueue(approvals_dir=sec_dir / "approvals"),
        audit=AuditLog(path=sec_dir / "audit.jsonl"),
        env=env_for_name("prod"),
    )

    alice_token = identity.authenticate("alice", alice_key)
    bob_token = identity.authenticate("bob", bob_key)

    # Low-risk edit: auto-approve
    d = sec.authorize_action(
        token=alice_token,
        action_type="edit_file",
        target="docs/README.md",
        operation=OperationKind.EDIT_FILE,
        risk="low",
    )
    assert_eq(d.status, "approved", "operator low-risk auto-approved")

    # High-risk edit: pending
    d = sec.authorize_action(
        token=alice_token,
        action_type="edit_file",
        target="eos_ai/memory.py",
        operation=OperationKind.EDIT_FILE,
        risk="high",
    )
    assert_eq(d.status, "pending", "high risk → pending")
    assert_true(bool(d.approval_id), "approval_id set")

    # Bob approves
    decided = sec.approve(
        approver_token=bob_token,
        request_id=d.approval_id,
        reason="ok",
    )
    assert_eq(decided.status, ApprovalStatus.APPROVED, "bob approved")

    # Viewer denied
    viewer, v_key = identity.create_user("val", "viewer")
    v_token = identity.authenticate("val", v_key)
    d = sec.authorize_action(
        token=v_token,
        action_type="edit_file",
        target="x.py",
        operation=OperationKind.EDIT_FILE,
        risk="low",
    )
    assert_eq(d.status, "denied", "viewer edit denied")

    # Bad token denied
    d = sec.authorize_action(
        token="totally.fake",
        action_type="edit_file",
        target="x.py",
        operation=OperationKind.EDIT_FILE,
        risk="low",
    )
    assert_eq(d.status, "denied", "bad token denied")

    # Dev env blocks CRITICAL outright
    sec_dev = SecurityContext(
        identity=identity,
        rbac=RBACEngine(),
        queue=ApprovalQueue(approvals_dir=sec_dir / "approvals_dev"),
        audit=AuditLog(path=sec_dir / "audit_dev.jsonl"),
        env=env_for_name("dev"),
    )
    d = sec_dev.authorize_action(
        token=bob_token,
        action_type="delete_file",
        target="x.py",
        operation=OperationKind.DELETE_FILE,
        risk="critical",
    )
    assert_eq(d.status, "denied", "dev env blocks CRITICAL")

    # Audit chain integrity
    ok, detail = sec.audit.verify_chain()
    assert_true(ok, f"audit chain intact: {detail}")


def test_action_system_integration(tmp: Path) -> None:
    step("integration: ActionSystem with security gate")
    from core.environment import make_sandbox
    from scripts.action_system import ActionSystem, ActionType

    tmp.mkdir(parents=True, exist_ok=True)
    sec_dir = tmp / "ai_sec"
    sec_dir.mkdir(parents=True, exist_ok=True)
    identity = IdentityStore(
        users_path=sec_dir / "users.jsonl",
        secret_path=sec_dir / "secret.key",
        revocations_path=sec_dir / "revocations.jsonl",
    )
    _, op_key = identity.create_user("op", "operator")
    _, admin_key = identity.create_user("adm", "admin")
    op_token = identity.authenticate("op", op_key)
    admin_token = identity.authenticate("adm", admin_key)

    sbx = make_sandbox(name=f"sec-smoke-{int(time.time())}")
    sec = SecurityContext(
        identity=identity,
        rbac=RBACEngine(),
        queue=ApprovalQueue(approvals_dir=sec_dir / "approvals"),
        audit=AuditLog(path=sec_dir / "audit.jsonl"),
        env=env_for_name("sandbox"),
    )

    # Operator token with a simple WRITE_FILE action (LOW risk, auto)
    asys = ActionSystem(env=sbx, security=sec, actor_token=op_token)
    action = asys.propose(
        action_type=ActionType.WRITE_FILE,
        target="docs/security_smoke.md",
        payload={"content": "# smoke\n"},
        reason="smoke test",
    )
    result = asys.execute(action)
    assert_true(
        result.status.value in ("succeeded", "skipped_dry_run"),
        f"low-risk write succeeded (got {result.status.value})",
    )

    # High-risk: propose an edit to a hub file, no approve → pending/denied
    asys2 = ActionSystem(env=sbx, security=sec, actor_token=op_token)
    action2 = asys2.propose(
        action_type=ActionType.RUN_SCRIPT,
        target="scripts/some_script.py",  # RUN_SCRIPT defaults HIGH
        payload={},
        reason="smoke test high risk",
    )
    result2 = asys2.execute(action2)
    assert_true(
        result2.status.value == "rejected",
        f"high-risk unapproved should be rejected (got {result2.status.value})",
    )

    # Clean up the sandbox
    sbx.cleanup()


# ─── Runner ─────────────────────────────────────────────────────────────────


def main() -> int:
    print("=" * 60)
    print("core.security smoke test")
    print("=" * 60)
    with tempfile.TemporaryDirectory(prefix="eos-sec-smoke-") as tmpdir:
        tmp = Path(tmpdir)
        test_identity(tmp / "id")
        (tmp / "id").mkdir(exist_ok=True)
        test_rbac()
        test_approval_queue(tmp / "aq")
        test_audit(tmp / "audit")
        test_execution(tmp / "exec")
        test_security_context(tmp / "ctx")
        test_action_system_integration(tmp / "integration")

    print("-" * 60)
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
