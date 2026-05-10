"""
Validation of the execution constraint layer.

Tests the complete chain: intent + risk + path/command → constraint_result →
composition with tool_policy → final_resolution → PermissionDecision.

Every test uses pure function calls — no mocking, no Discord, no tmux.

Proves:
  1. Path classification (approved, temp, outside, system, traversal)
  2. Command classification (safe, destructive, unknown)
  3. Command path extraction (strict, fail-safe)
  4. All 12 command decision matrix cells
  5. File read/write constraint logic
  6. Composition matrix (all 9 combinations)
  7. Integration through resolve_permission()
  8. PermissionDecision invariants
  9. Legacy path backwards compatibility
  10. Edge cases (no target, network, process exec)
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.execution_constraints import (
    CommandClass,
    ConstraintDecision,
    ConstraintType,
    PathScope,
    classify_command,
    classify_path_scope,
    evaluate_execution_constraints,
    get_approved_roots,
    _extract_command_target_path,
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
# SECTION 1: Approved Roots
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Approved Roots ──")

roots = get_approved_roots()
check("base roots always present", "/opt/OS" in roots)
check("returns list (not tuple)", isinstance(roots, list))


# With session that has active_workspace
class _FakeSession:
    active_workspace = "/home/test/project"


roots_ext = get_approved_roots(_FakeSession())
check(
    "session workspace appended",
    "/home/test/project" in roots_ext or any("project" in r for r in roots_ext),
)
check("base roots preserved with session", "/opt/OS" in roots_ext)


# Session without workspace
class _EmptySession:
    active_workspace = ""


roots_empty = get_approved_roots(_EmptySession())
check("empty workspace ignored", len(roots_empty) == len(roots))

# Session without attribute
roots_none = get_approved_roots(object())
check("no workspace attr handled", len(roots_none) == len(roots))


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Path Classification
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Path Classification ──")

check(
    "approved root exact",
    classify_path_scope("/opt/OS") == PathScope.APPROVED_ROOT,
    f"got {classify_path_scope('/opt/OS')}",
)
check(
    "approved root subpath",
    classify_path_scope("/opt/OS/eos/foo.py") == PathScope.APPROVED_ROOT,
    f"got {classify_path_scope('/opt/OS/eos/foo.py')}",
)
check(
    "temp root",
    classify_path_scope("/tmp/eos_workspace_123/file.txt") == PathScope.TEMP_ROOT,
    f"got {classify_path_scope('/tmp/eos_workspace_123/file.txt')}",
)
check(
    "outside root",
    classify_path_scope("/home/user/something.py") == PathScope.OUTSIDE_ROOT,
    f"got {classify_path_scope('/home/user/something.py')}",
)
check(
    "system path /etc",
    classify_path_scope("/etc/nginx/conf.d/default.conf") == PathScope.SYSTEM_PATH,
    f"got {classify_path_scope('/etc/nginx/conf.d/default.conf')}",
)
check(
    "system path /root",
    classify_path_scope("/root/.bashrc") == PathScope.SYSTEM_PATH,
    f"got {classify_path_scope('/root/.bashrc')}",
)
check(
    "system path exact /",
    classify_path_scope("/") == PathScope.SYSTEM_PATH,
    f"got {classify_path_scope('/')}",
)
check(
    "system path /usr",
    classify_path_scope("/usr/local/bin/python3") == PathScope.SYSTEM_PATH,
    f"got {classify_path_scope('/usr/local/bin/python3')}",
)
check(
    "system path /var",
    classify_path_scope("/var/log/syslog") == PathScope.SYSTEM_PATH,
    f"got {classify_path_scope('/var/log/syslog')}",
)

# Traversal prevention
check(
    "traversal to /etc resolved",
    classify_path_scope("/opt/OS/../../etc/passwd") == PathScope.SYSTEM_PATH,
    f"got {classify_path_scope('/opt/OS/../../etc/passwd')}",
)
check(
    "traversal staying in root",
    classify_path_scope("/opt/OS/eos/../eos/foo.py") == PathScope.APPROVED_ROOT,
    f"got {classify_path_scope('/opt/OS/eos/../eos/foo.py')}",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Command Classification
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Command Classification ──")

check("safe: git status", classify_command("git status") == CommandClass.SAFE)
check(
    "safe: python3 import check",
    classify_command("python3 -c 'from eos_ai import foo'") == CommandClass.SAFE,
)
check("safe: ruff format", classify_command("ruff format file.py") == CommandClass.SAFE)
check("safe: ls", classify_command("ls -la") == CommandClass.SAFE)
check(
    "destructive: rm -rf",
    classify_command("rm -rf /tmp/foo") == CommandClass.DESTRUCTIVE,
)
check(
    "destructive: git push",
    classify_command("git push origin main") == CommandClass.DESTRUCTIVE,
)
check(
    "destructive: sudo",
    classify_command("sudo apt install foo") == CommandClass.DESTRUCTIVE,
)
check("destructive: kill", classify_command("kill -9 1234") == CommandClass.DESTRUCTIVE)
check(
    "destructive: docker rm",
    classify_command("docker rm container") == CommandClass.DESTRUCTIVE,
)
check(
    "unknown: docker build", classify_command("docker build .") == CommandClass.UNKNOWN
)
check(
    "unknown: python3 script",
    classify_command("python3 /opt/OS/scripts/foo.py") == CommandClass.UNKNOWN,
)
check("unknown: empty", classify_command("") == CommandClass.UNKNOWN)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Command Path Extraction
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Command Path Extraction ──")

check(
    "single path extracted",
    _extract_command_target_path("rm -rf /opt/OS/tmp/") == "/opt/OS/tmp/",
)
check("no path returns empty", _extract_command_target_path("git status") == "")
check(
    "piped: first segment only",
    _extract_command_target_path("cat /etc/passwd | grep root") == "/etc/passwd",
)
check("multiple paths: fail safe", _extract_command_target_path("cp /a /b") == "")
check("empty command", _extract_command_target_path("") == "")
check("relative paths ignored", _extract_command_target_path("cat foo.py") == "")
check(
    "single path in complex command",
    _extract_command_target_path("ruff check /opt/OS/eos/foo.py")
    == "/opt/OS/eos/foo.py",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: Command Decision Matrix (all 12 cells)
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Command Decision Matrix ──")


# Helper: evaluate a command with a specific target path
def _cmd_constraint(cmd: str, target: str) -> tuple:
    """Returns (constraint_decision, constraint_type) for a command."""
    intent = _intent(IntentType.COMMAND, cmd=cmd)
    # We need to construct the command with the path embedded
    full_cmd = f"{cmd} {target}" if target else cmd
    intent_with_path = _intent(IntentType.COMMAND, cmd=full_cmd)
    result = evaluate_execution_constraints(intent_with_path, RiskLevel.MEDIUM)
    return result.result, result.constraint_type


# SAFE commands
r, t = _cmd_constraint("git status", "/opt/OS")
check("SAFE + APPROVED_ROOT → allowed", r == ConstraintDecision.ALLOWED, f"got {r}")

r, t = _cmd_constraint("ls", "/tmp/eos_workspace/")
check("SAFE + TEMP_ROOT → allowed", r == ConstraintDecision.ALLOWED, f"got {r}")

# For SAFE + OUTSIDE_ROOT, construct a safe command targeting outside path
safe_outside = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="cat /home/user/file.txt"),
    RiskLevel.MEDIUM,
)
check(
    "SAFE + OUTSIDE_ROOT → escalate",
    safe_outside.result == ConstraintDecision.ESCALATE,
    f"got {safe_outside.result}",
)

# For SAFE + SYSTEM_PATH
safe_system = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="cat /etc/passwd"),
    RiskLevel.MEDIUM,
)
check(
    "SAFE + SYSTEM_PATH → blocked",
    safe_system.result == ConstraintDecision.BLOCKED,
    f"got {safe_system.result}",
)

# DESTRUCTIVE commands
destr_approved = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="rm -rf /opt/OS/tmp/cache"),
    RiskLevel.HIGH,
)
check(
    "DESTRUCTIVE + APPROVED_ROOT → escalate",
    destr_approved.result == ConstraintDecision.ESCALATE,
    f"got {destr_approved.result}",
)

destr_temp = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="rm -rf /tmp/eos_build/"),
    RiskLevel.HIGH,
)
check(
    "DESTRUCTIVE + TEMP_ROOT → escalate",
    destr_temp.result == ConstraintDecision.ESCALATE,
    f"got {destr_temp.result}",
)

destr_outside = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="rm -rf /home/user/data"),
    RiskLevel.HIGH,
)
check(
    "DESTRUCTIVE + OUTSIDE_ROOT → blocked",
    destr_outside.result == ConstraintDecision.BLOCKED,
    f"got {destr_outside.result}",
)

destr_system = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="rm -rf /etc/nginx"),
    RiskLevel.HIGH,
)
check(
    "DESTRUCTIVE + SYSTEM_PATH → blocked",
    destr_system.result == ConstraintDecision.BLOCKED,
    f"got {destr_system.result}",
)

# UNKNOWN commands
unknown_approved = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="docker build /opt/OS"),
    RiskLevel.MEDIUM,
)
check(
    "UNKNOWN + APPROVED_ROOT → escalate",
    unknown_approved.result == ConstraintDecision.ESCALATE,
    f"got {unknown_approved.result}",
)

unknown_temp = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="docker build /tmp/eos_workspace/"),
    RiskLevel.MEDIUM,
)
check(
    "UNKNOWN + TEMP_ROOT → escalate",
    unknown_temp.result == ConstraintDecision.ESCALATE,
    f"got {unknown_temp.result}",
)

unknown_outside = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="docker build /home/user/"),
    RiskLevel.MEDIUM,
)
check(
    "UNKNOWN + OUTSIDE_ROOT → blocked",
    unknown_outside.result == ConstraintDecision.BLOCKED,
    f"got {unknown_outside.result}",
)

unknown_system = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="docker build /usr/local/"),
    RiskLevel.MEDIUM,
)
check(
    "UNKNOWN + SYSTEM_PATH → blocked",
    unknown_system.result == ConstraintDecision.BLOCKED,
    f"got {unknown_system.result}",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: File Read/Write Constraints
# ═══════════════════════════════════════════════════════════════════════════

print("\n── File Read/Write Constraints ──")

# FILE_READ
fr_approved = evaluate_execution_constraints(
    _intent(IntentType.FILE_READ, target="/opt/OS/eos/foo.py"),
    RiskLevel.LOW,
)
check(
    "FILE_READ approved_root → allowed",
    fr_approved.result == ConstraintDecision.ALLOWED,
)

fr_outside = evaluate_execution_constraints(
    _intent(IntentType.FILE_READ, target="/home/user/file.txt"),
    RiskLevel.LOW,
)
check(
    "FILE_READ outside_root → escalate",
    fr_outside.result == ConstraintDecision.ESCALATE,
)

fr_system = evaluate_execution_constraints(
    _intent(IntentType.FILE_READ, target="/etc/shadow"),
    RiskLevel.LOW,
)
check("FILE_READ system_path → blocked", fr_system.result == ConstraintDecision.BLOCKED)

fr_temp = evaluate_execution_constraints(
    _intent(IntentType.FILE_READ, target="/tmp/eos_cache/data.json"),
    RiskLevel.LOW,
)
check("FILE_READ temp_root → allowed", fr_temp.result == ConstraintDecision.ALLOWED)

fr_no_target = evaluate_execution_constraints(
    _intent(IntentType.FILE_READ, target=""),
    RiskLevel.LOW,
)
check(
    "FILE_READ no target → escalate (NO_TARGET)",
    fr_no_target.result == ConstraintDecision.ESCALATE
    and fr_no_target.constraint_type == ConstraintType.NO_TARGET,
)

# FILE_WRITE
fw_approved = evaluate_execution_constraints(
    _intent(IntentType.FILE_WRITE, target="/opt/OS/eos/bar.py"),
    RiskLevel.MEDIUM,
)
check(
    "FILE_WRITE approved_root → allowed",
    fw_approved.result == ConstraintDecision.ALLOWED,
)

fw_outside = evaluate_execution_constraints(
    _intent(IntentType.FILE_WRITE, target="/home/user/something.py"),
    RiskLevel.MEDIUM,
)
check(
    "FILE_WRITE outside_root → blocked", fw_outside.result == ConstraintDecision.BLOCKED
)
check(
    "FILE_WRITE outside_root → path_boundary type",
    fw_outside.constraint_type == ConstraintType.PATH_BOUNDARY,
)

fw_system = evaluate_execution_constraints(
    _intent(IntentType.FILE_WRITE, target="/etc/passwd"),
    RiskLevel.MEDIUM,
)
check(
    "FILE_WRITE system_path → blocked", fw_system.result == ConstraintDecision.BLOCKED
)

fw_temp = evaluate_execution_constraints(
    _intent(IntentType.FILE_WRITE, target="/tmp/eos_session/output.json"),
    RiskLevel.MEDIUM,
)
check("FILE_WRITE temp_root → allowed", fw_temp.result == ConstraintDecision.ALLOWED)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Edge Cases ──")

# NETWORK_CALL → escalate with network_scope
net_result = evaluate_execution_constraints(
    _intent(IntentType.NETWORK_CALL, cmd="curl", target="https://example.com"),
    RiskLevel.HIGH,
)
check("NETWORK_CALL → escalate", net_result.result == ConstraintDecision.ESCALATE)
check(
    "NETWORK_CALL → network_scope type",
    net_result.constraint_type == ConstraintType.NETWORK_SCOPE,
)

# PROCESS_EXEC → escalate with not_evaluated
proc_result = evaluate_execution_constraints(
    _intent(IntentType.PROCESS_EXEC, cmd="agent", target="some-agent"),
    RiskLevel.MEDIUM,
)
check("PROCESS_EXEC → escalate", proc_result.result == ConstraintDecision.ESCALATE)
check(
    "PROCESS_EXEC → not_evaluated type",
    proc_result.constraint_type == ConstraintType.NOT_EVALUATED,
)

# UNKNOWN intent → escalate with not_evaluated
unk_result = evaluate_execution_constraints(
    _intent(IntentType.UNKNOWN),
    RiskLevel.HIGH,
)
check("UNKNOWN intent → escalate", unk_result.result == ConstraintDecision.ESCALATE)
check(
    "UNKNOWN intent → not_evaluated type",
    unk_result.constraint_type == ConstraintType.NOT_EVALUATED,
)

# Command with no extractable path → escalate with no_target
no_path_cmd = evaluate_execution_constraints(
    _intent(IntentType.COMMAND, cmd="docker build ."),
    RiskLevel.MEDIUM,
)
check("command no path → escalate", no_path_cmd.result == ConstraintDecision.ESCALATE)
check(
    "command no path → no_target type",
    no_path_cmd.constraint_type == ConstraintType.NO_TARGET,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: Composition Matrix (all 9 combinations)
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Composition Matrix ──")

check(
    "ALLOW + ALLOWED → ALLOW",
    _combine_decisions(ToolPolicyDecision.ALLOW, ConstraintDecision.ALLOWED)
    == FinalResolution.ALLOW,
)

check(
    "ALLOW + ESCALATE → ESCALATE",
    _combine_decisions(ToolPolicyDecision.ALLOW, ConstraintDecision.ESCALATE)
    == FinalResolution.ESCALATE,
)

check(
    "ALLOW + BLOCKED → DENY",
    _combine_decisions(ToolPolicyDecision.ALLOW, ConstraintDecision.BLOCKED)
    == FinalResolution.DENY,
)

check(
    "ESCALATE + ALLOWED → ESCALATE",
    _combine_decisions(ToolPolicyDecision.ESCALATE, ConstraintDecision.ALLOWED)
    == FinalResolution.ESCALATE,
)

check(
    "ESCALATE + ESCALATE → ESCALATE",
    _combine_decisions(ToolPolicyDecision.ESCALATE, ConstraintDecision.ESCALATE)
    == FinalResolution.ESCALATE,
)

check(
    "ESCALATE + BLOCKED → DENY",
    _combine_decisions(ToolPolicyDecision.ESCALATE, ConstraintDecision.BLOCKED)
    == FinalResolution.DENY,
)

check(
    "DENY + ALLOWED → DENY",
    _combine_decisions(ToolPolicyDecision.DENY, ConstraintDecision.ALLOWED)
    == FinalResolution.DENY,
)

check(
    "DENY + ESCALATE → DENY",
    _combine_decisions(ToolPolicyDecision.DENY, ConstraintDecision.ESCALATE)
    == FinalResolution.DENY,
)

check(
    "DENY + BLOCKED → DENY",
    _combine_decisions(ToolPolicyDecision.DENY, ConstraintDecision.BLOCKED)
    == FinalResolution.DENY,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: Derivation Function
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Resolution Derivation ──")

check(
    "ALLOW + AUTO → AUTO_APPROVE",
    _derive_resolution(FinalResolution.ALLOW, ExecutionMode.AUTO)
    == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)

check(
    "DENY + AUTO → AUTO_DENY",
    _derive_resolution(FinalResolution.DENY, ExecutionMode.AUTO)
    == PermissionResolution.AUTO_DENY_AND_SUPPRESS,
)

check(
    "ESCALATE + AUTO → SURFACE",
    _derive_resolution(FinalResolution.ESCALATE, ExecutionMode.AUTO)
    == PermissionResolution.SURFACE_AND_WAIT,
)

check(
    "ALLOW + INTERACTIVE → SURFACE",
    _derive_resolution(FinalResolution.ALLOW, ExecutionMode.INTERACTIVE)
    == PermissionResolution.SURFACE_AND_WAIT,
)

check(
    "DENY + INTERACTIVE → SURFACE",
    _derive_resolution(FinalResolution.DENY, ExecutionMode.INTERACTIVE)
    == PermissionResolution.SURFACE_AND_WAIT,
)

check(
    "ESCALATE + INTERACTIVE → SURFACE",
    _derive_resolution(FinalResolution.ESCALATE, ExecutionMode.INTERACTIVE)
    == PermissionResolution.SURFACE_AND_WAIT,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: Integration — resolve_permission() end-to-end
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Integration: resolve_permission() ──")

# Test 1: Builder safe read inside workspace
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_READ, target="/opt/OS/eos/foo.py", cmd="read"),
    RiskLevel.LOW,
)
check("builder read approved → ALLOW", d.final_resolution == FinalResolution.ALLOW)
check("builder read approved → AUTO mode", d.execution_mode == ExecutionMode.AUTO)
check(
    "builder read approved → AUTO_APPROVE resolution",
    d.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)
check("builder read approved → constraint evaluated", d.constraint_evaluated is True)
check(
    "builder read approved → constraint ALLOWED",
    d.constraint_result == ConstraintDecision.ALLOWED,
)

# Test 2: Builder write inside workspace
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/opt/OS/eos/bar.py", cmd="write"),
    RiskLevel.MEDIUM,
)
check("builder write approved → ALLOW", d.final_resolution == FinalResolution.ALLOW)
check(
    "builder write approved → tool policy ALLOW",
    d.tool_policy_decision == ToolPolicyDecision.ALLOW,
)

# Test 3: Builder write outside approved root
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/home/user/something.py", cmd="write"),
    RiskLevel.MEDIUM,
)
check("builder write outside → DENY", d.final_resolution == FinalResolution.DENY)
check(
    "builder write outside → constraint BLOCKED",
    d.constraint_result == ConstraintDecision.BLOCKED,
)
check(
    "builder write outside → PATH_BOUNDARY type",
    d.constraint_type == ConstraintType.PATH_BOUNDARY,
)
check(
    "builder write outside → reason populated",
    d.constraint_reason is not None and "outside" in d.constraint_reason,
)

# Test 4: Builder destructive command targeting system path
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.COMMAND, cmd="rm -rf /etc/nginx"),
    RiskLevel.HIGH,
)
check(
    "builder rm system → DENY or ESCALATE from tool policy",
    d.final_resolution in (FinalResolution.DENY, FinalResolution.ESCALATE),
)
# Tool policy for builder COMMAND HIGH = ESCALATE
# Constraint for DESTRUCTIVE + SYSTEM_PATH = BLOCKED
# Combined: max(ESCALATE, DENY) = DENY
check("builder rm system → final DENY", d.final_resolution == FinalResolution.DENY)
check(
    "builder rm system → constraint BLOCKED",
    d.constraint_result == ConstraintDecision.BLOCKED,
)

# Test 5: DEX file read
d = resolve_permission(
    "dex_product_main",
    _intent(IntentType.FILE_READ, target="/opt/OS/data/report.json", cmd="read"),
    RiskLevel.LOW,
)
check("dex read approved → ALLOW", d.final_resolution == FinalResolution.ALLOW)
check("dex read approved → AUTO mode", d.execution_mode == ExecutionMode.AUTO)

# Test 6: Legacy call (no intent/risk)
d = resolve_permission("dex_builder_main")
check("legacy → ALLOW final", d.final_resolution == FinalResolution.ALLOW)
check("legacy → constraint not evaluated", d.constraint_evaluated is False)
check("legacy → constraint_result None", d.constraint_result is None)
check("legacy → constraint_type None", d.constraint_type is None)
check("legacy → constraint_reason None", d.constraint_reason is None)
check("legacy → tool_policy None", d.tool_policy_decision is None)

# Test 7: User-facing session → always INTERACTIVE + SURFACE
d = resolve_permission(
    "some_user_session",
    _intent(IntentType.COMMAND, cmd="rm -rf /"),
    RiskLevel.HIGH,
)
check("user-facing → INTERACTIVE mode", d.execution_mode == ExecutionMode.INTERACTIVE)
check(
    "user-facing → SURFACE_AND_WAIT resolution",
    d.resolution == PermissionResolution.SURFACE_AND_WAIT,
)

# Test 8: Tighten-only proof — tool policy ALLOW, constraint BLOCKED
# Builder FILE_WRITE MEDIUM = ALLOW, but path outside root = BLOCKED
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/home/evil/file.py", cmd="write"),
    RiskLevel.MEDIUM,
)
check("tighten: ALLOW + BLOCKED → DENY", d.final_resolution == FinalResolution.DENY)
check(
    "tighten: tool policy was ALLOW", d.tool_policy_decision == ToolPolicyDecision.ALLOW
)
check(
    "tighten: constraint was BLOCKED", d.constraint_result == ConstraintDecision.BLOCKED
)

# Test 9: Never-loosen proof — tool policy ESCALATE, constraint ALLOWED
# Builder NETWORK_CALL = ESCALATE, constraint ESCALATE (network_scope)
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.NETWORK_CALL, cmd="curl", target="https://api.example.com"),
    RiskLevel.HIGH,
)
check(
    "never-loosen: ESCALATE preserved", d.final_resolution == FinalResolution.ESCALATE
)

# Test 10: Path traversal attack
d = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_WRITE, target="/opt/OS/../../etc/passwd", cmd="write"),
    RiskLevel.MEDIUM,
)
check("traversal attack → DENY", d.final_resolution == FinalResolution.DENY)
check(
    "traversal attack → BLOCKED constraint",
    d.constraint_result == ConstraintDecision.BLOCKED,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: PermissionDecision Invariants
# ═══════════════════════════════════════════════════════════════════════════

print("\n── PermissionDecision Invariants ──")

# Invariant: resolution always matches derivation
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

# Invariant: constraint_evaluated=False ↔ all constraint fields None
d_legacy = resolve_permission("dex_builder_main")
check(
    "invariant: not-evaluated → all None",
    (
        d_legacy.constraint_evaluated is False
        and d_legacy.constraint_result is None
        and d_legacy.constraint_type is None
        and d_legacy.constraint_reason is None
    ),
)

d_full = resolve_permission(
    "dex_builder_main",
    _intent(IntentType.FILE_READ, target="/opt/OS/foo.py", cmd="read"),
    RiskLevel.LOW,
)
check(
    "invariant: evaluated → all populated",
    (
        d_full.constraint_evaluated is True
        and d_full.constraint_result is not None
        and d_full.constraint_type is not None
        and d_full.constraint_reason is not None
    ),
)

# PermissionDecision is frozen (immutable)
try:
    d_full.final_resolution = FinalResolution.DENY  # type: ignore
    check("invariant: frozen", False, "should have raised")
except AttributeError:
    check("invariant: frozen", True)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {PASS + FAIL}  |  PASS: {PASS}  |  FAIL: {FAIL}")
print(f"{'=' * 60}")

if FAIL > 0:
    sys.exit(1)
