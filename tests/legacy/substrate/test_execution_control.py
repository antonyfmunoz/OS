"""
Validation of the execution control layer.

Tests the complete chain: after resolve_permission returns ALLOW/ESCALATE,
execution controls shape HOW the action executes.

Every test uses pure function calls — no mocking, no Discord, no tmux.

Proves:
  1. Safe command receives normalized execution form
  2. Timeout defaults are attached correctly
  3. Denied commands do not reach execution control as executable actions
  4. Rewritten commands are logged/traceable
  5. No regression to existing permission flow
  6. Shell safety detection works
  7. Destructive command bounding works
  8. Non-command intents get timeouts only
  9. Integration through resolve_permission() includes execution control fields
  10. DENY from constraint composition skips execution control
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.execution_control import (
    ControlType,
    ExecutionControlResult,
    apply_execution_controls,
    _normalize_whitespace,
    _detect_shell_chains,
    _detect_dangerous_suffixes,
    _resolve_timeout,
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
    _combine_decisions,
    _derive_resolution,
)
from umh.substrate.execution_constraints import ConstraintDecision

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


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Whitespace Normalization
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Whitespace Normalization ──")

check("collapse multi space", _normalize_whitespace("git  status") == "git status")
check(
    "collapse tabs",
    _normalize_whitespace("git\t\tstatus") == "git status",
)
check(
    "strip leading/trailing",
    _normalize_whitespace("  git status  ") == "git status",
)
check("already clean", _normalize_whitespace("git status") == "git status")
check("empty string", _normalize_whitespace("") == "")
check(
    "mixed mess",
    _normalize_whitespace("  rm   -rf  /opt/OS/tmp/  ") == "rm -rf /opt/OS/tmp/",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Shell Chain Detection
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Shell Chain Detection ──")

check(
    "semicolon detected",
    "semicolon_chaining" in _detect_shell_chains("ls; rm -rf /"),
)
check(
    "and chaining detected",
    "and_chaining" in _detect_shell_chains("mkdir foo && cd foo"),
)
check(
    "or chaining detected",
    "or_chaining" in _detect_shell_chains("test -f foo || exit 1"),
)
check(
    "command substitution detected",
    "command_substitution" in _detect_shell_chains("echo $(whoami)"),
)
check(
    "backtick substitution detected",
    "backtick_substitution" in _detect_shell_chains("echo `whoami`"),
)
check("clean command", _detect_shell_chains("git status") == [])
check(
    "clean with pipe",
    "semicolon_chaining" not in _detect_shell_chains("cat file | grep foo"),
)
check(
    "multiple chains detected",
    len(_detect_shell_chains("ls; echo $(whoami) && rm -rf /")) >= 3,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Dangerous Suffix Detection
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Dangerous Suffix Detection ──")

check(
    "no_preserve_root detected",
    "no_preserve_root" in _detect_dangerous_suffixes("rm -rf / --no-preserve-root"),
)
check(
    "eval injection detected",
    "eval_injection" in _detect_dangerous_suffixes("eval $MALICIOUS"),
)
check(
    "exec replacement detected",
    "exec_replacement" in _detect_dangerous_suffixes("exec /bin/sh"),
)
check(
    "raw device redirect detected",
    "raw_device_redirect" in _detect_dangerous_suffixes("dd if=/dev/zero > /dev/sda"),
)
check("clean command", _detect_dangerous_suffixes("git status") == [])
check("normal rm", _detect_dangerous_suffixes("rm -rf /opt/OS/tmp/") == [])


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Timeout Resolution
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Timeout Resolution ──")

check("command low → 30s", _resolve_timeout(IntentType.COMMAND, RiskLevel.LOW) == 30)
check(
    "command medium → 120s",
    _resolve_timeout(IntentType.COMMAND, RiskLevel.MEDIUM) == 120,
)
check(
    "command high → 300s", _resolve_timeout(IntentType.COMMAND, RiskLevel.HIGH) == 300
)
check(
    "file read low → 15s", _resolve_timeout(IntentType.FILE_READ, RiskLevel.LOW) == 15
)
check(
    "file write medium → 60s",
    _resolve_timeout(IntentType.FILE_WRITE, RiskLevel.MEDIUM) == 60,
)
check(
    "network high → 300s",
    _resolve_timeout(IntentType.NETWORK_CALL, RiskLevel.HIGH) == 300,
)
check(
    "process high → 600s",
    _resolve_timeout(IntentType.PROCESS_EXEC, RiskLevel.HIGH) == 600,
)
check(
    "unknown falls back to 120s",
    _resolve_timeout(IntentType.UNKNOWN, RiskLevel.HIGH) == 120,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: DENY Guard
# ═══════════════════════════════════════════════════════════════════════════

print("\n── DENY Guard ──")

deny_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="rm -rf /"),
    RiskLevel.HIGH,
    FinalResolution.DENY,
)
check("DENY → allowed=False", deny_result.allowed is False)
check("DENY → no rewrite", deny_result.rewritten_command is None)
check("DENY → no timeout", deny_result.timeout_seconds is None)
check(
    "DENY → reason explains rejection",
    "DENY" in deny_result.control_reason,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: Non-Command Intents (timeout only)
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Non-Command Intents ──")

read_result = apply_execution_controls(
    "builder",
    _intent(IntentType.FILE_READ, target="/opt/OS/foo.py"),
    RiskLevel.LOW,
    FinalResolution.ALLOW,
)
check("file read → allowed", read_result.allowed is True)
check("file read → no rewrite", read_result.rewritten_command is None)
check("file read → timeout 15s", read_result.timeout_seconds == 15)
check(
    "file read → timeout control type",
    read_result.control_type == ControlType.TIMEOUT_APPLIED,
)
check("file read → controls list", "timeout" in read_result.controls_applied)

write_result = apply_execution_controls(
    "builder",
    _intent(IntentType.FILE_WRITE, target="/opt/OS/bar.py"),
    RiskLevel.MEDIUM,
    FinalResolution.ALLOW,
)
check("file write → timeout 60s", write_result.timeout_seconds == 60)

net_result = apply_execution_controls(
    "builder",
    _intent(IntentType.NETWORK_CALL, target="https://example.com"),
    RiskLevel.HIGH,
    FinalResolution.ESCALATE,
)
check("network → timeout 300s", net_result.timeout_seconds == 300)
check("network → allowed", net_result.allowed is True)

proc_result = apply_execution_controls(
    "builder",
    _intent(IntentType.PROCESS_EXEC, target="agent"),
    RiskLevel.MEDIUM,
    FinalResolution.ESCALATE,
)
check("process exec → timeout 300s", proc_result.timeout_seconds == 300)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Safe Command — Normalization + Timeout
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Safe Command Controls ──")

# Clean command — should just get timeout
clean_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="git status"),
    RiskLevel.LOW,
    FinalResolution.ALLOW,
)
check("clean cmd → allowed", clean_result.allowed is True)
check("clean cmd → no rewrite", clean_result.rewritten_command is None)
check("clean cmd → timeout 30s", clean_result.timeout_seconds == 30)

# Dirty whitespace command — should normalize
dirty_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="git   status   --short"),
    RiskLevel.LOW,
    FinalResolution.ALLOW,
)
check("dirty ws → rewritten", dirty_result.rewritten_command == "git status --short")
check(
    "dirty ws → normalization noted",
    "whitespace_normalized" in dirty_result.controls_applied,
)
check("dirty ws → traceable reason", "whitespace" in dirty_result.control_reason)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: Destructive Command Bounding
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Destructive Command Bounding ──")

destr_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="rm -rf /opt/OS/tmp/cache"),
    RiskLevel.HIGH,
    FinalResolution.ESCALATE,
)
check("destructive → allowed (escalate still runs)", destr_result.allowed is True)
check(
    "destructive → bounded flag",
    "destructive_bounded" in destr_result.controls_applied,
)
check(
    "destructive → timeout capped",
    "timeout_capped_destructive" in destr_result.controls_applied,
)
check(
    "destructive → timeout <= 60s",
    destr_result.timeout_seconds is not None and destr_result.timeout_seconds <= 60,
)
check(
    "destructive → reason mentions destructive",
    "destructive" in destr_result.control_reason,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: Shell Safety Detection in Commands
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Shell Safety Detection ──")

chain_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="ls /opt/OS && echo done"),
    RiskLevel.MEDIUM,
    FinalResolution.ALLOW,
)
check(
    "shell chain → detected",
    "shell_chain_detected" in chain_result.controls_applied,
)
check(
    "shell chain → reason mentions chaining",
    "chaining" in chain_result.control_reason,
)

subst_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="echo $(whoami)"),
    RiskLevel.MEDIUM,
    FinalResolution.ALLOW,
)
check(
    "cmd substitution → detected",
    "shell_chain_detected" in subst_result.controls_applied,
)

danger_result = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="rm -rf / --no-preserve-root"),
    RiskLevel.HIGH,
    FinalResolution.ESCALATE,
)
check(
    "dangerous suffix → detected",
    "dangerous_suffix_detected" in danger_result.controls_applied,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: Empty / Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Edge Cases ──")

empty_cmd = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd=""),
    RiskLevel.LOW,
    FinalResolution.ALLOW,
)
check("empty cmd → allowed", empty_cmd.allowed is True)
check("empty cmd → timeout only", empty_cmd.control_type == ControlType.TIMEOUT_APPLIED)
check("empty cmd → no rewrite", empty_cmd.rewritten_command is None)

whitespace_only = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="   "),
    RiskLevel.LOW,
    FinalResolution.ALLOW,
)
check("whitespace-only cmd → allowed", whitespace_only.allowed is True)
check(
    "whitespace-only cmd → timeout only",
    whitespace_only.control_type == ControlType.TIMEOUT_APPLIED,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: Integration — resolve_permission includes execution control
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Integration: resolve_permission() with execution control ──")

# Test 1: Builder safe read — should have execution control fields
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_READ, target="/opt/OS/eos/foo.py", cmd="read"),
    RiskLevel.LOW,
)
check("builder read → has ec applied", d.execution_control_applied is True)
check(
    "builder read → ec type populated",
    d.execution_control_type is not None,
    f"got {d.execution_control_type}",
)
check(
    "builder read → timeout populated",
    d.timeout_seconds is not None and d.timeout_seconds > 0,
    f"got {d.timeout_seconds}",
)
check("builder read → still ALLOW", d.final_resolution == FinalResolution.ALLOW)
check("builder read → no rewrite", d.rewritten_command is None)

# Test 2: Builder command — should have timeout
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.COMMAND, cmd="git status /opt/OS"),
    RiskLevel.LOW,
)
check("builder cmd → ec applied", d.execution_control_applied is True)
check(
    "builder cmd → timeout populated",
    d.timeout_seconds is not None,
    f"got {d.timeout_seconds}",
)

# Test 3: Builder write outside root → DENY → no execution control
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/home/user/evil.py", cmd="write"),
    RiskLevel.MEDIUM,
)
check("deny → ec NOT applied", d.execution_control_applied is False)
check("deny → ec type None", d.execution_control_type is None)
check("deny → timeout None", d.timeout_seconds is None)
check("deny → rewrite None", d.rewritten_command is None)
check("deny → still DENY", d.final_resolution == FinalResolution.DENY)

# Test 4: Builder destructive in system path → DENY → no execution control
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.COMMAND, cmd="rm -rf /etc/nginx"),
    RiskLevel.HIGH,
)
check("deny cmd → ec NOT applied", d.execution_control_applied is False)
check("deny cmd → final DENY", d.final_resolution == FinalResolution.DENY)

# Test 5: Legacy path — no execution control
d = resolve_permission("dex_builder_main")
check("legacy → ec NOT applied", d.execution_control_applied is False)
check("legacy → timeout None", d.timeout_seconds is None)

# Test 6: Dirty whitespace command through full chain
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.COMMAND, cmd="git   status   /opt/OS"),
    RiskLevel.LOW,
)
check("dirty ws via resolve → ec applied", d.execution_control_applied is True)
check(
    "dirty ws via resolve → rewritten",
    d.rewritten_command == "git status /opt/OS",
    f"got '{d.rewritten_command}'",
)
check(
    "dirty ws via resolve → controls list",
    "whitespace_normalized" in d.execution_controls_applied,
)

# Test 7: Escalated action still gets execution control
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.NETWORK_CALL, cmd="curl", target="https://api.example.com"),
    RiskLevel.HIGH,
)
check("escalate → ec applied", d.execution_control_applied is True)
check(
    "escalate → final ESCALATE preserved",
    d.final_resolution == FinalResolution.ESCALATE,
)
check("escalate → timeout populated", d.timeout_seconds is not None)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 12: No Regression — Existing Constraint Tests Still Pass
# ═══════════════════════════════════════════════════════════════════════════

print("\n── No Regression ──")

# Verify key invariants from the original test suite still hold
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_READ, target="/opt/OS/eos/foo.py", cmd="read"),
    RiskLevel.LOW,
)
check("regression: builder read → ALLOW", d.final_resolution == FinalResolution.ALLOW)
check("regression: builder read → AUTO mode", d.execution_mode == ExecutionMode.AUTO)
check(
    "regression: builder read → AUTO_APPROVE",
    d.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)
check("regression: builder read → constraint evaluated", d.constraint_evaluated is True)
check(
    "regression: builder read → constraint ALLOWED",
    d.constraint_result == ConstraintDecision.ALLOWED,
)

d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/home/evil/file.py", cmd="write"),
    RiskLevel.MEDIUM,
)
check(
    "regression: tighten ALLOW+BLOCKED → DENY",
    d.final_resolution == FinalResolution.DENY,
)
check(
    "regression: tool policy was ALLOW",
    d.tool_policy_decision == ToolPolicyDecision.ALLOW,
)
check(
    "regression: constraint was BLOCKED",
    d.constraint_result == ConstraintDecision.BLOCKED,
)

d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/opt/OS/../../etc/passwd", cmd="write"),
    RiskLevel.MEDIUM,
)
check("regression: traversal → DENY", d.final_resolution == FinalResolution.DENY)

# User-facing sessions still INTERACTIVE
d = resolve_permission(
    "some_user_session",
    _intent(IntentType.COMMAND, cmd="rm -rf /"),
    RiskLevel.HIGH,
)
check(
    "regression: user-facing → INTERACTIVE",
    d.execution_mode == ExecutionMode.INTERACTIVE,
)
check(
    "regression: user-facing → SURFACE_AND_WAIT",
    d.resolution == PermissionResolution.SURFACE_AND_WAIT,
)

# Resolution derivation invariant still holds
for session in ["dex_builder_main", "dex_product_main", "random_session"]:
    for intent_t in [IntentType.FILE_READ, IntentType.FILE_WRITE, IntentType.COMMAND]:
        for risk in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]:
            target = "/opt/OS/test.py" if intent_t != IntentType.COMMAND else ""
            cmd = "git status /opt/OS" if intent_t == IntentType.COMMAND else ""
            i = _intent(intent_t, cmd=cmd, target=target)
            d = resolve_permission(session, i, risk)
            expected_res = _derive_resolution(d.final_resolution, d.execution_mode)
            check(
                f"invariant [{session[:8]}|{intent_t.value}|{risk.value}]",
                d.resolution == expected_res,
                f"resolution={d.resolution.value} expected={expected_res.value}",
            )

# Frozen invariant still holds
try:
    d.final_resolution = FinalResolution.DENY  # type: ignore
    check("regression: frozen", False, "should have raised")
except AttributeError:
    check("regression: frozen", True)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 13: ExecutionControlResult is frozen
# ═══════════════════════════════════════════════════════════════════════════

print("\n── ExecutionControlResult Invariants ──")

ecr = apply_execution_controls(
    "builder",
    _intent(IntentType.COMMAND, cmd="git status"),
    RiskLevel.LOW,
    FinalResolution.ALLOW,
)
try:
    ecr.allowed = False  # type: ignore
    check("ecr frozen", False, "should have raised")
except AttributeError:
    check("ecr frozen", True)

check("ecr controls_applied is tuple", isinstance(ecr.controls_applied, tuple))


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {PASS + FAIL}  |  PASS: {PASS}  |  FAIL: {FAIL}")
print(f"{'=' * 60}")

if FAIL > 0:
    sys.exit(1)
