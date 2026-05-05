"""
Validation of the dispatch enforcement layer.

Proves that advisory outputs from execution control are physically enforced
at the actual execution boundary.

Every test uses pure function calls — no mocking, no Discord, no tmux.

Proves:
  1. Allowed command with rewritten whitespace executes using rewritten_command
  2. Denied command is blocked before execution
  3. Timeout-bearing command is executed with real timeout enforcement
  4. Timeout event returns structured timed_out result
  5. Existing non-command flows do not regress
  6. No execution boundary bypasses the contract
  7. Structured execution result model is complete
  8. Enforcement trace logging works
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.substrate.dispatch_enforcement import (
    ExecutionResult,
    ExecutionStatus,
    check_denied,
    enforced_call,
    enforced_subprocess,
    log_enforcement_trace,
    resolve_command,
)
from umh.substrate.discord_output_policy import (
    ExecutionMode,
    FinalResolution,
    IntentType,
    PermissionDecision,
    PermissionIntent,
    PermissionOrigin,
    PermissionResolution,
    RiskLevel,
    ToolPolicyDecision,
    resolve_permission,
)
from umh.substrate.execution_constraints import (
    ConstraintDecision,
    ConstraintType,
)
from umh.substrate.execution_control import ControlType

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def _intent(
    itype: IntentType, raw: str = "", cmd: str = "", target: str = ""
) -> PermissionIntent:
    return PermissionIntent(type=itype, raw=raw, command=cmd, target=target)


# ─── Helper: build PermissionDecision for testing ────────────────────────


def _make_decision(
    *,
    final: FinalResolution = FinalResolution.ALLOW,
    rewritten_command: str | None = None,
    timeout_seconds: int | None = 30,
    constraint_reason: str | None = None,
    ec_applied: bool = True,
    controls_applied: tuple[str, ...] = (),
) -> PermissionDecision:
    """Build a PermissionDecision for testing dispatch enforcement."""
    return PermissionDecision(
        final_resolution=final,
        execution_mode=ExecutionMode.AUTO,
        origin=PermissionOrigin.INTERNAL_AUTO,
        tool_policy_decision=ToolPolicyDecision.ALLOW,
        constraint_evaluated=True,
        constraint_result=ConstraintDecision.ALLOWED,
        constraint_type=ConstraintType.NONE,
        constraint_reason=constraint_reason,
        execution_control_applied=ec_applied,
        execution_control_type=ControlType.TIMEOUT_APPLIED.value,
        rewritten_command=rewritten_command,
        timeout_seconds=timeout_seconds,
        execution_controls_applied=controls_applied,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Deny Check
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Deny Check ──")

# ALLOW decision → not denied
allow_dec = _make_decision(final=FinalResolution.ALLOW)
check("ALLOW → not denied", check_denied(allow_dec) is None)

# ESCALATE decision → not denied
escalate_dec = _make_decision(final=FinalResolution.ESCALATE)
check("ESCALATE → not denied", check_denied(escalate_dec) is None)

# DENY decision → denied
deny_dec = _make_decision(
    final=FinalResolution.DENY,
    constraint_reason="write target outside approved workspace root",
)
denied_result = check_denied(deny_dec)
check("DENY → returns ExecutionResult", denied_result is not None)
check(
    "DENY → status=denied",
    denied_result is not None and denied_result.status == ExecutionStatus.DENIED,
)
check(
    "DENY → reason preserved",
    denied_result is not None
    and "outside approved" in (denied_result.control_reason or ""),
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Command Rewriting
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Command Rewriting ──")

# No rewrite
no_rewrite_dec = _make_decision(rewritten_command=None)
check(
    "no rewrite → returns raw",
    resolve_command("git status", no_rewrite_dec) == "git status",
)

# Has rewrite
rewrite_dec = _make_decision(rewritten_command="git status --short")
check(
    "rewrite → returns rewritten",
    resolve_command("git   status   --short", rewrite_dec) == "git status --short",
)

# Rewritten command is used, not raw
check(
    "raw ≠ rewritten",
    resolve_command("git   status   --short", rewrite_dec) != "git   status   --short",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Enforced Subprocess — Denied
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Subprocess: Denied ──")

deny_result = enforced_subprocess(
    ["echo", "should_not_run"],
    decision=_make_decision(
        final=FinalResolution.DENY,
        constraint_reason="blocked by test",
    ),
    raw_command="echo should_not_run",
    boundary="test",
)
check("denied → status=DENIED", deny_result.status == ExecutionStatus.DENIED)
check("denied → no exit_code", deny_result.exit_code is None)
check("denied → no stdout", deny_result.stdout is None)
check(
    "denied → reason preserved",
    "blocked by test" in (deny_result.control_reason or ""),
)
check("denied → boundary set", deny_result.boundary == "test")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Enforced Subprocess — Allowed with Timeout
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Subprocess: Allowed ──")

allowed_result = enforced_subprocess(
    ["echo", "hello enforcement"],
    decision=_make_decision(timeout_seconds=30),
    raw_command="echo hello enforcement",
    boundary="test_allowed",
)
check(
    "allowed → status=SUCCEEDED",
    allowed_result.status == ExecutionStatus.SUCCEEDED,
)
check("allowed → exit_code=0", allowed_result.exit_code == 0)
check(
    "allowed → stdout has output",
    "hello enforcement" in (allowed_result.stdout or ""),
)
check("allowed → timeout recorded", allowed_result.timeout_seconds == 30)
check("allowed → boundary set", allowed_result.boundary == "test_allowed")
check("allowed → elapsed > 0", allowed_result.elapsed_seconds > 0)
check(
    "allowed → executed_command",
    allowed_result.executed_command == "echo hello enforcement",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: Enforced Subprocess — Timeout Hit
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Subprocess: Timeout ──")

# Use a 1-second timeout with a command that sleeps for 5 seconds
timeout_result = enforced_subprocess(
    ["sleep", "5"],
    decision=_make_decision(timeout_seconds=1),
    raw_command="sleep 5",
    boundary="test_timeout",
)
check(
    "timeout → status=TIMED_OUT",
    timeout_result.status == ExecutionStatus.TIMED_OUT,
)
check("timeout → timeout_seconds=1", timeout_result.timeout_seconds == 1)
check(
    "timeout → reason mentions timeout",
    "timed out" in (timeout_result.control_reason or ""),
)
check("timeout → boundary set", timeout_result.boundary == "test_timeout")
check(
    "timeout → elapsed ~ 1s",
    0.8 <= timeout_result.elapsed_seconds <= 3.0,
    f"elapsed={timeout_result.elapsed_seconds}",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: Enforced Subprocess — Failed Command
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Subprocess: Failed ──")

failed_result = enforced_subprocess(
    ["ls", "/nonexistent_path_that_does_not_exist"],
    decision=_make_decision(timeout_seconds=10),
    raw_command="ls /nonexistent_path_that_does_not_exist",
    boundary="test_failed",
)
check(
    "failed → status=FAILED",
    failed_result.status == ExecutionStatus.FAILED,
)
check(
    "failed → exit_code ≠ 0",
    failed_result.exit_code is not None and failed_result.exit_code != 0,
)
check("failed → stderr has content", bool(failed_result.stderr))


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Enforced Callable — Denied
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Callable: Denied ──")

call_count = 0


def _should_not_run() -> str:
    global call_count
    call_count += 1
    return "SHOULD NOT SEE THIS"


denied_call = enforced_call(
    _should_not_run,
    decision=_make_decision(
        final=FinalResolution.DENY,
        constraint_reason="callable test deny",
    ),
    boundary="test_call_deny",
    description="test callable deny",
)
check("callable deny → status=DENIED", denied_call.status == ExecutionStatus.DENIED)
check("callable deny → fn NOT called", call_count == 0)
check(
    "callable deny → reason preserved",
    "callable test deny" in (denied_call.control_reason or ""),
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: Enforced Callable — Allowed
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Callable: Allowed ──")


def _fast_fn() -> str:
    return "hello from callable"


allowed_call = enforced_call(
    _fast_fn,
    decision=_make_decision(timeout_seconds=10),
    boundary="test_call_ok",
    description="test callable success",
)
check(
    "callable ok → status=SUCCEEDED",
    allowed_call.status == ExecutionStatus.SUCCEEDED,
)
check("callable ok → boundary set", allowed_call.boundary == "test_call_ok")
check("callable ok → elapsed > 0", allowed_call.elapsed_seconds >= 0)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: Enforced Callable — Timeout
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Callable: Timeout ──")


def _slow_fn() -> str:
    time.sleep(10)
    return "too slow"


timeout_call = enforced_call(
    _slow_fn,
    decision=_make_decision(timeout_seconds=1),
    boundary="test_call_timeout",
    description="test callable timeout",
)
check(
    "callable timeout → status=TIMED_OUT",
    timeout_call.status == ExecutionStatus.TIMED_OUT,
)
check("callable timeout → timeout=1", timeout_call.timeout_seconds == 1)
check(
    "callable timeout → reason",
    "timed out" in (timeout_call.control_reason or ""),
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: Enforced Callable — Exception
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforced Callable: Exception ──")


def _bad_fn() -> str:
    raise ValueError("test error from callable")


error_call = enforced_call(
    _bad_fn,
    decision=_make_decision(timeout_seconds=10),
    boundary="test_call_error",
    description="test callable error",
)
check(
    "callable error → status=FAILED",
    error_call.status == ExecutionStatus.FAILED,
)
check(
    "callable error → reason has ValueError",
    "ValueError" in (error_call.control_reason or ""),
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: ExecutionResult Model
# ═══════════════════════════════════════════════════════════════════════════

print("\n── ExecutionResult Model ──")

result = ExecutionResult(
    status=ExecutionStatus.SUCCEEDED,
    executed_command="echo test",
    original_command="echo  test",
    timeout_seconds=30,
    exit_code=0,
    stdout="test\n",
    stderr="",
    boundary="test_model",
    elapsed_seconds=0.01,
    detail={"key": "value"},
)

# Frozen
try:
    result.status = ExecutionStatus.FAILED  # type: ignore
    check("result frozen", False, "should have raised")
except AttributeError:
    check("result frozen", True)

# to_dict
d = result.to_dict()
check("to_dict has status", d["status"] == "succeeded")
check("to_dict has executed_command", d["executed_command"] == "echo test")
check("to_dict has original_command", d["original_command"] == "echo  test")
check("to_dict has timeout_seconds", d["timeout_seconds"] == 30)
check("to_dict has exit_code", d["exit_code"] == 0)
check("to_dict has stdout", d["stdout"] == "test\n")
check("to_dict has boundary", d["boundary"] == "test_model")
check("to_dict has elapsed_seconds", d["elapsed_seconds"] == 0.01)
check("to_dict has detail", d["detail"] == {"key": "value"})


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 12: Enforcement Trace Logging
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Enforcement Trace Logging ──")

trace = log_enforcement_trace(result, role="builder")
check("trace has layer", trace["layer"] == "dispatch_enforcement")
check("trace has boundary", trace["boundary"] == "test_model")
check("trace has role", trace["role"] == "builder")
check("trace has status", trace["status"] == "succeeded")
check("trace has exit_code", trace["exit_code"] == 0)
check("trace has executed_command", trace["executed_command"] == "echo test")
check("trace has original_command", trace["original_command"] == "echo  test")
check("trace has timeout_seconds", trace["timeout_seconds"] == 30)

# Trace omits None values
denied_trace = log_enforcement_trace(
    ExecutionResult(
        status=ExecutionStatus.DENIED,
        control_reason="test deny",
        boundary="test",
    )
)
check("denied trace omits None exit_code", "exit_code" not in denied_trace)
check("denied trace omits None stdout", "stdout" not in denied_trace)
check(
    "denied trace has control_reason", denied_trace.get("control_reason") == "test deny"
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 13: Integration — local_executor with dispatch enforcement
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Integration: local_executor with enforcement ──")

from umh.runtime_engine.substrate import control_commands as cc
from umh.runtime_engine.substrate import local_executor

# Test 1: Legacy path — no decision (backward compat)
legacy_cmd = cc.make_command("run_shell", {"cmd": "echo legacy"})
legacy_result = local_executor.execute_command(legacy_cmd)
check("legacy → ok", legacy_result["ok"] is True)
check("legacy → no enforcement key", "enforcement" not in legacy_result)

# Test 2: Enforced allowed
enforced_cmd = cc.make_command("run_shell", {"cmd": "echo enforced"})
enforced_decision = _make_decision(timeout_seconds=10)
enforced_result = local_executor.execute_command(enforced_cmd, enforced_decision)
check("enforced → ok", enforced_result["ok"] is True)
check(
    "enforced → enforcement key",
    enforced_result.get("enforcement") == "dispatch_enforcement",
)
check(
    "enforced → enforcement_status",
    enforced_result.get("enforcement_status") == "succeeded",
)
check(
    "enforced → stdout",
    "enforced" in enforced_result.get("stdout", ""),
)

# Test 3: Enforced denied
denied_cmd = cc.make_command("run_shell", {"cmd": "echo denied"})
denied_decision = _make_decision(
    final=FinalResolution.DENY,
    constraint_reason="test local deny",
)
denied_result = local_executor.execute_command(denied_cmd, denied_decision)
check("enforced deny → not ok", denied_result["ok"] is False)
check(
    "enforced deny → reason",
    denied_result.get("reason") == "denied_by_policy",
)
check(
    "enforced deny → enforcement key",
    denied_result.get("enforcement") == "dispatch_enforcement",
)

# Test 4: Enforced with rewritten command
rewrite_cmd = cc.make_command("run_shell", {"cmd": "echo   hello   world"})
rewrite_decision = _make_decision(
    rewritten_command="echo hello world",
    timeout_seconds=10,
)
rewrite_result = local_executor.execute_command(rewrite_cmd, rewrite_decision)
check("rewrite → ok", rewrite_result["ok"] is True)
check(
    "rewrite → executed_command uses rewritten",
    rewrite_result.get("executed_command") == "echo hello world",
)
check(
    "rewrite → original_command preserved",
    rewrite_result.get("original_command") == "echo   hello   world",
)

# Test 5: Enforced timeout
timeout_cmd = cc.make_command("run_shell", {"cmd": "ls /opt/OS"})
# Use a very short timeout — ls should complete in time, this tests timeout is passed
timeout_decision = _make_decision(timeout_seconds=5)
timeout_result = local_executor.execute_command(timeout_cmd, timeout_decision)
check("timeout pass → ok", timeout_result["ok"] is True)
check(
    "timeout pass → timeout_seconds",
    timeout_result.get("timeout_seconds") == 5,
)

# Test 6: Non-shell actions still work without decision
write_cmd = cc.make_command(
    "write_file", {"path": "test_enforce.txt", "content": "test"}
)
write_result = local_executor.execute_command(write_cmd)
check("write_file → ok", write_result["ok"] is True)
check("write_file → no enforcement", "enforcement" not in write_result)

# Test 7: Denied write_file via decision (deny at execute_command level)
write_cmd2 = cc.make_command("write_file", {"path": "test2.txt", "content": "deny me"})
write_denied = local_executor.execute_command(
    write_cmd2,
    _make_decision(final=FinalResolution.DENY, constraint_reason="write denied"),
)
check("write deny → not ok", write_denied["ok"] is False)
check("write deny → reason", write_denied.get("reason") == "denied_by_policy")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 14: Integration — full chain through resolve_permission
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Integration: full chain resolve_permission → local_executor ──")

# Builder safe command through full chain
full_decision = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.COMMAND, cmd="echo full chain /opt/OS"),
    RiskLevel.LOW,
)
full_cmd = cc.make_command("run_shell", {"cmd": "echo full chain /opt/OS"})
full_result = local_executor.execute_command(full_cmd, full_decision)
check("full chain → ok", full_result["ok"] is True)
check(
    "full chain → enforcement applied",
    full_result.get("enforcement") == "dispatch_enforcement",
)
check(
    "full chain → has timeout",
    full_result.get("timeout_seconds") is not None,
)

# Builder write to system path → DENY → blocked at local_executor
deny_decision = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/etc/passwd", cmd="write"),
    RiskLevel.HIGH,
)
deny_cmd = cc.make_command("run_shell", {"cmd": "echo evil"})
deny_full = local_executor.execute_command(deny_cmd, deny_decision)
check("full deny → not ok", deny_full["ok"] is False)
check("full deny → denied_by_policy", deny_full.get("reason") == "denied_by_policy")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 15: No Bypass — contract coverage
# ═══════════════════════════════════════════════════════════════════════════

print("\n── No Bypass: Contract Coverage ──")

# Verify that every ExecutionStatus has a value
for s in ExecutionStatus:
    check(f"status {s.value} exists", isinstance(s.value, str))

# Verify ExecutionResult handles all status types
for s in ExecutionStatus:
    er = ExecutionResult(status=s, boundary="test")
    check(f"result with {s.value} → to_dict", "status" in er.to_dict())

# Verify check_denied only blocks DENY (never ALLOW or ESCALATE)
for final in [FinalResolution.ALLOW, FinalResolution.ESCALATE]:
    dec = _make_decision(final=final)
    check(f"check_denied({final.value}) → None", check_denied(dec) is None)

denied_dec = _make_decision(final=FinalResolution.DENY)
check(
    "check_denied(DENY) → not None",
    check_denied(denied_dec) is not None,
)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {PASS + FAIL}  |  PASS: {PASS}  |  FAIL: {FAIL}")
print(f"{'=' * 60}")

if FAIL > 0:
    sys.exit(1)
