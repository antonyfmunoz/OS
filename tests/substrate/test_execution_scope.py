"""
Validation of the execution scope layer (scoped task approval).

Tests the complete scope lifecycle: creation → registration → evaluation →
integration with resolve_permission() → expiry.

Every test uses pure function calls — no mocking, no Discord, no tmux.

Proves:
  1. Scope creation and registration
  2. Scoped task → file edits execute silently (WITHIN_SCOPE)
  3. Scoped task → rm triggers escalation (destructive action)
  4. Scoped task → write outside root triggers escalation
  5. No scope → normal behavior preserved
  6. Scope expires → normal behavior resumes
  7. Env/config file writes escalate within scope
  8. Network actions escalate within scope
  9. System path writes always escalate
  10. Scope revocation works
  11. PermissionDecision carries scope fields
  12. Integration: resolve_permission with task_id
"""

import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/opt/OS")

from umh.substrate.execution_scope import (
    DEFAULT_SCOPE_TTL_SECONDS,
    ExecutionScope,
    ScopeEvaluation,
    ScopeRegistry,
    ScopeVerdict,
    create_scope_for_task,
    evaluate_scope,
)

# ─── Helpers ──────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


def _check(label: str, condition: bool) -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  ✓ {label}")
    else:
        _FAIL += 1
        print(f"  ✗ FAIL: {label}")


def _setup_registry() -> ScopeRegistry:
    """Get a clean registry for each test group."""
    reg = ScopeRegistry()
    reg.clear_all()
    return reg


# ─── 1. Scope Creation and Registration ──────────────────────────────────


def test_scope_creation() -> None:
    print("\n1. Scope creation and registration")
    reg = _setup_registry()

    scope = create_scope_for_task(
        task_id="task_001",
        correlation_id="corr_001",
        allowed_roots=("/opt/OS/eos/substrate",),
        issued_by="operator",
    )

    _check("scope_id starts with scope_", scope.scope_id.startswith("scope_"))
    _check("task_id matches", scope.task_id == "task_001")
    _check("correlation_id matches", scope.correlation_id == "corr_001")
    _check("allowed_roots set", scope.allowed_roots == ("/opt/OS/eos/substrate",))
    _check("not expired", not scope.is_expired())
    _check("registered in registry", reg.get_by_task("task_001") is scope)
    _check("findable by correlation", reg.get_by_correlation("corr_001") is scope)
    _check("active count is 1", reg.active_count() == 1)


# ─── 2. Scoped Task → File Edits Execute Silently ────────────────────────


def test_within_scope_file_edit() -> None:
    print("\n2. Scoped task → file edits execute silently")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_edit",
        allowed_roots=("/opt/OS/eos/substrate",),
    )

    # File write within approved root
    result = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/eos/substrate/some_module.py",
    )
    _check("verdict is WITHIN_SCOPE", result.verdict == ScopeVerdict.WITHIN_SCOPE)
    _check("within_scope property True", result.within_scope)
    _check("scope_id present", result.scope_id == scope.scope_id)
    _check("no escalation_reason", result.escalation_reason is None)

    # File read within approved root
    result_read = evaluate_scope(
        scope,
        intent_type="file_read",
        target_path="/opt/OS/eos/substrate/nodes.py",
    )
    _check("read also within scope", result_read.within_scope)

    # Command within approved root
    result_cmd = evaluate_scope(
        scope,
        intent_type="command",
        target_path="/opt/OS/eos/substrate",
        command="ls -la",
    )
    _check("safe command within scope", result_cmd.within_scope)


# ─── 3. Scoped Task → rm Triggers Escalation ─────────────────────────────


def test_destructive_command_escalates() -> None:
    print("\n3. Scoped task → rm triggers escalation")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_rm",
        allowed_roots=("/opt/OS",),
    )

    # rm command — always escalates regardless of scope
    result = evaluate_scope(
        scope,
        intent_type="command",
        target_path="/opt/OS/eos/substrate/temp.py",
        command="rm /opt/OS/eos/substrate/temp.py",
    )
    _check("verdict is ESCALATE", result.verdict == ScopeVerdict.ESCALATE)
    _check("not within_scope", not result.within_scope)
    _check("reason mentions destructive", "destructive" in result.escalation_reason)

    # kill — always escalates
    result_kill = evaluate_scope(
        scope,
        intent_type="command",
        command="kill -9 1234",
    )
    _check("kill escalates", result_kill.verdict == ScopeVerdict.ESCALATE)

    # sudo rm — extracts base command past sudo
    result_sudo = evaluate_scope(
        scope,
        intent_type="command",
        command="sudo rm -rf /tmp/stuff",
    )
    _check("sudo rm escalates", result_sudo.verdict == ScopeVerdict.ESCALATE)


# ─── 4. Scoped Task → Write Outside Root Triggers Escalation ─────────────


def test_outside_root_escalates() -> None:
    print("\n4. Scoped task → write outside root triggers escalation")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_outside",
        allowed_roots=("/opt/OS/eos/substrate",),
    )

    # File write outside allowed root
    result = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/services/discord_bot.py",
    )
    _check("verdict is ESCALATE", result.verdict == ScopeVerdict.ESCALATE)
    _check("reason mentions outside", "outside" in result.escalation_reason)

    # Write to completely different tree
    result_etc = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/etc/passwd",
    )
    _check("system path escalates", result_etc.verdict == ScopeVerdict.ESCALATE)
    _check("reason mentions system", "system" in result_etc.escalation_reason)

    # Write to home directory (outside root)
    result_home = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/root/.bashrc",
    )
    _check("home dir escalates", result_home.verdict == ScopeVerdict.ESCALATE)


# ─── 5. No Scope → Normal Behavior ──────────────────────────────────────


def test_no_scope() -> None:
    print("\n5. No scope → normal behavior")

    result = evaluate_scope(
        scope=None,
        intent_type="file_write",
        target_path="/opt/OS/eos/substrate/test.py",
    )
    _check("verdict is NO_SCOPE", result.verdict == ScopeVerdict.NO_SCOPE)
    _check("not within_scope", not result.within_scope)
    _check("scope_id is None", result.scope_id is None)
    _check("no escalation_reason", result.escalation_reason is None)


# ─── 6. Scope Expires → Normal Behavior Resumes ──────────────────────────


def test_scope_expiry() -> None:
    print("\n6. Scope expires → normal behavior resumes")
    reg = _setup_registry()

    # Create scope with 1-second TTL
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(seconds=1)

    scope = ExecutionScope(
        scope_id="scope_expired_test",
        task_id="task_expired",
        correlation_id="corr_expired",
        allowed_roots=("/opt/OS",),
        allowed_intents=("file_write", "file_read", "command"),
        restricted_actions=frozenset(),
        escalation_required_actions=frozenset({"rm", "kill"}),
        created_at=(now - timedelta(hours=1)).isoformat(),
        expires_at=expired_time.isoformat(),
        issued_by="operator",
    )
    reg.register(scope)

    # Scope should be considered expired
    _check("scope is expired", scope.is_expired())

    # Evaluation should return SCOPE_EXPIRED
    result = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/eos/substrate/test.py",
    )
    _check("verdict is SCOPE_EXPIRED", result.verdict == ScopeVerdict.SCOPE_EXPIRED)
    _check("not within_scope", not result.within_scope)
    _check("reason mentions TTL", "TTL" in result.escalation_reason)

    # Registry should auto-evict expired scopes
    looked_up = reg.get_by_task("task_expired")
    _check("registry evicts expired scope", looked_up is None)


# ─── 7. Env/Config File Writes Escalate ──────────────────────────────────


def test_env_config_escalates() -> None:
    print("\n7. Env/config file writes escalate within scope")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_env",
        allowed_roots=("/opt/OS",),
    )

    # .env file
    result_env = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/umh/.env",
    )
    _check(".env escalates", result_env.verdict == ScopeVerdict.ESCALATE)
    _check("reason mentions config/env", "config/env" in result_env.escalation_reason)

    # Dockerfile
    result_docker = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/Dockerfile",
    )
    _check("Dockerfile escalates", result_docker.verdict == ScopeVerdict.ESCALATE)

    # requirements.txt
    result_req = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/requirements.txt",
    )
    _check("requirements.txt escalates", result_req.verdict == ScopeVerdict.ESCALATE)


# ─── 8. Network Actions Escalate ─────────────────────────────────────────


def test_network_escalates() -> None:
    print("\n8. Network actions escalate within scope")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_net",
        allowed_roots=("/opt/OS",),
        allowed_intents=("file_write", "file_read", "command", "network_call"),
    )

    result = evaluate_scope(
        scope,
        intent_type="network_call",
        target_path="https://api.example.com",
    )
    _check("network_call escalates", result.verdict == ScopeVerdict.ESCALATE)
    _check("reason mentions network", "network" in result.escalation_reason)


# ─── 9. System Path Always Escalates ──────────────────────────────────────


def test_system_path_escalates() -> None:
    print("\n9. System path writes always escalate")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_sys",
        # Even with root set to /
        allowed_roots=("/",),
    )

    for sys_path in ["/etc/hosts", "/usr/bin/test", "/var/log/syslog"]:
        result = evaluate_scope(
            scope,
            intent_type="file_write",
            target_path=sys_path,
        )
        _check(
            f"{sys_path} escalates",
            result.verdict == ScopeVerdict.ESCALATE
            and "system" in result.escalation_reason,
        )


# ─── 10. Scope Revocation ────────────────────────────────────────────────


def test_scope_revocation() -> None:
    print("\n10. Scope revocation")
    reg = _setup_registry()

    scope = create_scope_for_task(
        task_id="task_revoke",
        allowed_roots=("/opt/OS",),
    )

    _check("scope exists before revoke", reg.get_by_task("task_revoke") is not None)

    revoked = reg.revoke("task_revoke")
    _check("revoke returns True", revoked)
    _check("scope gone after revoke", reg.get_by_task("task_revoke") is None)

    # Double revoke is safe
    revoked_again = reg.revoke("task_revoke")
    _check("double revoke returns False", not revoked_again)

    # Revoking non-existent is safe
    revoked_none = reg.revoke("task_nonexistent")
    _check("revoke nonexistent returns False", not revoked_none)


# ─── 11. PermissionDecision Carries Scope Fields ─────────────────────────


def test_permission_decision_scope_fields() -> None:
    print("\n11. PermissionDecision carries scope fields")
    from umh.substrate.discord_output_policy import (
        FinalResolution,
        ExecutionMode,
        PermissionOrigin,
        PermissionDecision,
        PermissionResolution,
    )

    # Decision with scope fields
    decision = PermissionDecision(
        final_resolution=FinalResolution.ALLOW,
        execution_mode=ExecutionMode.INTERACTIVE,
        origin=PermissionOrigin.USER_FACING,
        tool_policy_decision=None,
        constraint_evaluated=False,
        constraint_result=None,
        constraint_type=None,
        constraint_reason=None,
        within_scope=True,
        scope_id="scope_test123",
        escalation_reason=None,
    )
    _check("within_scope is True", decision.within_scope)
    _check("scope_id populated", decision.scope_id == "scope_test123")
    _check(
        "within_scope overrides to AUTO_APPROVE",
        decision.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )

    # Decision without scope (default)
    decision_no_scope = PermissionDecision(
        final_resolution=FinalResolution.ALLOW,
        execution_mode=ExecutionMode.INTERACTIVE,
        origin=PermissionOrigin.USER_FACING,
        tool_policy_decision=None,
        constraint_evaluated=False,
        constraint_result=None,
        constraint_type=None,
        constraint_reason=None,
    )
    _check("default within_scope is False", not decision_no_scope.within_scope)
    _check(
        "interactive ALLOW without scope → SURFACE_AND_WAIT",
        decision_no_scope.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )


# ─── 12. Integration: resolve_permission with task_id ────────────────────


def test_resolve_permission_with_scope() -> None:
    print("\n12. Integration: resolve_permission with task_id")
    _setup_registry()

    from umh.substrate.discord_output_policy import (
        PermissionIntent,
        PermissionResolution,
        IntentType,
        RiskLevel,
        resolve_permission,
    )

    # Create scope for the task
    scope = create_scope_for_task(
        task_id="task_integration",
        allowed_roots=("/opt/OS/eos/substrate",),
    )

    # File write within scope → should resolve to AUTO_APPROVE (silent)
    intent_write = PermissionIntent(
        type=IntentType.FILE_WRITE,
        raw="Write(/opt/OS/eos/substrate/test.py)",
        command="",
        target="/opt/OS/eos/substrate/test.py",
    )
    decision = resolve_permission(
        "dex_builder_main",
        intent=intent_write,
        risk_level=RiskLevel.LOW,
        task_id="task_integration",
    )
    _check("within_scope is True", decision.within_scope)
    _check("scope_id populated", decision.scope_id == scope.scope_id)
    _check(
        "resolution is AUTO_APPROVE_AND_SUPPRESS",
        decision.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )

    # Same session, no task_id → normal behavior
    decision_no_task = resolve_permission(
        "dex_builder_main",
        intent=intent_write,
        risk_level=RiskLevel.LOW,
    )
    _check("no task_id → not within_scope", not decision_no_task.within_scope)

    # Same task, destructive command → should escalate
    intent_rm = PermissionIntent(
        type=IntentType.COMMAND,
        raw="Bash(rm /opt/OS/eos/substrate/temp.py)",
        command="rm /opt/OS/eos/substrate/temp.py",
        target="/opt/OS/eos/substrate/temp.py",
    )
    decision_rm = resolve_permission(
        "dex_builder_main",
        intent=intent_rm,
        risk_level=RiskLevel.HIGH,
        task_id="task_integration",
    )
    _check("rm not within_scope", not decision_rm.within_scope)
    _check(
        "rm escalation_reason present",
        decision_rm.escalation_reason is not None
        and "destructive" in decision_rm.escalation_reason,
    )


# ─── 13. Scope Serialization ─────────────────────────────────────────────


def test_scope_serialization() -> None:
    print("\n13. Scope serialization")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_serial",
        correlation_id="corr_serial",
        allowed_roots=("/opt/OS",),
        metadata={"reason": "approved by operator"},
    )

    d = scope.to_dict()
    _check("dict has scope_id", d["scope_id"] == scope.scope_id)
    _check("dict has task_id", d["task_id"] == "task_serial")
    _check("dict has correlation_id", d["correlation_id"] == "corr_serial")
    _check("dict has allowed_roots as list", d["allowed_roots"] == ["/opt/OS"])
    _check("dict has metadata", d["metadata"]["reason"] == "approved by operator")
    _check("dict has expires_at", "expires_at" in d)


# ─── 14. Restricted Actions ──────────────────────────────────────────────


def test_restricted_actions() -> None:
    print("\n14. Task-specific restricted actions")
    _setup_registry()

    scope = create_scope_for_task(
        task_id="task_restricted",
        allowed_roots=("/opt/OS",),
        restricted_actions=frozenset({"curl", "wget"}),
    )

    # Restricted command escalates
    result_curl = evaluate_scope(
        scope,
        intent_type="command",
        command="curl https://example.com",
    )
    _check("curl restricted → escalates", result_curl.verdict == ScopeVerdict.ESCALATE)
    _check("reason mentions restricted", "restricted" in result_curl.escalation_reason)

    # Non-restricted command within scope
    result_ls = evaluate_scope(
        scope,
        intent_type="command",
        target_path="/opt/OS",
        command="ls -la",
    )
    _check("ls not restricted → within scope", result_ls.within_scope)


# ─── 15. Intent Not In Scope ─────────────────────────────────────────────


def test_intent_not_in_scope() -> None:
    print("\n15. Intent type not in scope → outside scope")
    _setup_registry()

    # Only allow file_read
    scope = create_scope_for_task(
        task_id="task_intent",
        allowed_roots=("/opt/OS",),
        allowed_intents=("file_read",),
    )

    # file_write not allowed
    result = evaluate_scope(
        scope,
        intent_type="file_write",
        target_path="/opt/OS/eos/substrate/test.py",
    )
    _check("file_write outside scope", result.verdict == ScopeVerdict.OUTSIDE_SCOPE)
    _check("reason mentions intent", "intent" in result.escalation_reason)


# ─── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_scope_creation()
    test_within_scope_file_edit()
    test_destructive_command_escalates()
    test_outside_root_escalates()
    test_no_scope()
    test_scope_expiry()
    test_env_config_escalates()
    test_network_escalates()
    test_system_path_escalates()
    test_scope_revocation()
    test_permission_decision_scope_fields()
    test_resolve_permission_with_scope()
    test_scope_serialization()
    test_restricted_actions()
    test_intent_not_in_scope()

    print(f"\n{'=' * 50}")
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL > 0:
        sys.exit(1)
    else:
        print("All scope tests passed.")
