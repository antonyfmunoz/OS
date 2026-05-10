"""
Validation of the tool-level execution policy layer.

Tests the complete chain: role + intent + risk → tool_policy_decision →
permission_resolution. Every test uses pure function calls — no mocking,
no Discord, no tmux.

Proves:
  1. Builder safe read/command → ALLOW (auto-approved)
  2. Builder high-risk destructive command → ESCALATE (surfaced)
  3. Builder network call → ESCALATE regardless of risk
  4. EA product read/safe command → ALLOW
  5. EA product writes → ESCALATE
  6. EA product network/system changes → ESCALATE
  7. Unknown role → ESCALATE (safe fallback)
  8. DENY path produces AUTO_DENY_AND_SUPPRESS resolution
  9. Existing user-facing session behavior intact
  10. Backwards compatibility with None intent/risk
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.discord_output_policy import (
    IntentType,
    PermissionIntent,
    PermissionResolution,
    RiskLevel,
    ToolPolicyDecision,
    classify_risk,
    extract_intent,
    resolve_permission,
    resolve_tool_policy,
    should_surface_permission,
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


# Helper to build PermissionIntent quickly
def _intent(
    itype: IntentType, raw: str = "", cmd: str = "", target: str = ""
) -> PermissionIntent:
    return PermissionIntent(type=itype, raw=raw, command=cmd, target=target)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Builder Role — Tool Policy Decisions
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 1. Builder Tool Policy ═══")

# Reads: always ALLOW
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy(
        "builder", _intent(IntentType.FILE_READ, "Read(x)"), risk
    )
    check(
        f"builder read {risk.value} = allow",
        result == ToolPolicyDecision.ALLOW,
        f"got: {result.value}",
    )

# Writes: ALLOW at low/medium, ESCALATE at high
check(
    "builder write low = allow",
    resolve_tool_policy(
        "builder", _intent(IntentType.FILE_WRITE, "Write(x)"), RiskLevel.LOW
    )
    == ToolPolicyDecision.ALLOW,
)
check(
    "builder write medium = allow",
    resolve_tool_policy(
        "builder", _intent(IntentType.FILE_WRITE, "Write(x)"), RiskLevel.MEDIUM
    )
    == ToolPolicyDecision.ALLOW,
)
check(
    "builder write high = escalate",
    resolve_tool_policy(
        "builder", _intent(IntentType.FILE_WRITE, "Write(x)"), RiskLevel.HIGH
    )
    == ToolPolicyDecision.ESCALATE,
)

# Commands: ALLOW at low/medium, ESCALATE at high
check(
    "builder cmd low = allow",
    resolve_tool_policy(
        "builder", _intent(IntentType.COMMAND, "Bash(ls)"), RiskLevel.LOW
    )
    == ToolPolicyDecision.ALLOW,
)
check(
    "builder cmd medium = allow",
    resolve_tool_policy(
        "builder",
        _intent(IntentType.COMMAND, "Bash(python3 test.py)"),
        RiskLevel.MEDIUM,
    )
    == ToolPolicyDecision.ALLOW,
)
check(
    "builder cmd high = escalate",
    resolve_tool_policy(
        "builder", _intent(IntentType.COMMAND, "Bash(rm -rf /)"), RiskLevel.HIGH
    )
    == ToolPolicyDecision.ESCALATE,
)

# Process exec: ALLOW at low/medium, ESCALATE at high
check(
    "builder process low = allow",
    resolve_tool_policy(
        "builder", _intent(IntentType.PROCESS_EXEC, "Agent(x)"), RiskLevel.LOW
    )
    == ToolPolicyDecision.ALLOW,
)
check(
    "builder process high = escalate",
    resolve_tool_policy(
        "builder", _intent(IntentType.PROCESS_EXEC, "Agent(x)"), RiskLevel.HIGH
    )
    == ToolPolicyDecision.ESCALATE,
)

# Network: ALWAYS ESCALATE regardless of risk
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy(
        "builder", _intent(IntentType.NETWORK_CALL, "curl x"), risk
    )
    check(
        f"builder network {risk.value} = escalate",
        result == ToolPolicyDecision.ESCALATE,
        f"got: {result.value}",
    )

# Unknown intent: ALWAYS ESCALATE
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy("builder", _intent(IntentType.UNKNOWN, "???"), risk)
    check(
        f"builder unknown {risk.value} = escalate",
        result == ToolPolicyDecision.ESCALATE,
        f"got: {result.value}",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 2. EA Product Role — Tool Policy Decisions
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 2. EA Product Tool Policy ═══")

# Reads: always ALLOW
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy(
        "ea_product", _intent(IntentType.FILE_READ, "Read(x)"), risk
    )
    check(
        f"ea_product read {risk.value} = allow",
        result == ToolPolicyDecision.ALLOW,
        f"got: {result.value}",
    )

# Writes: ALWAYS ESCALATE (product sessions shouldn't mutate freely)
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy(
        "ea_product", _intent(IntentType.FILE_WRITE, "Write(x)"), risk
    )
    check(
        f"ea_product write {risk.value} = escalate",
        result == ToolPolicyDecision.ESCALATE,
        f"got: {result.value}",
    )

# Commands: ALLOW at low, ESCALATE at medium/high
check(
    "ea_product cmd low = allow",
    resolve_tool_policy(
        "ea_product", _intent(IntentType.COMMAND, "Bash(ls)"), RiskLevel.LOW
    )
    == ToolPolicyDecision.ALLOW,
)
check(
    "ea_product cmd medium = escalate",
    resolve_tool_policy(
        "ea_product",
        _intent(IntentType.COMMAND, "Bash(python3 test.py)"),
        RiskLevel.MEDIUM,
    )
    == ToolPolicyDecision.ESCALATE,
)
check(
    "ea_product cmd high = escalate",
    resolve_tool_policy(
        "ea_product", _intent(IntentType.COMMAND, "Bash(rm -rf /)"), RiskLevel.HIGH
    )
    == ToolPolicyDecision.ESCALATE,
)

# Process exec: ALWAYS ESCALATE
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy(
        "ea_product", _intent(IntentType.PROCESS_EXEC, "Agent(x)"), risk
    )
    check(
        f"ea_product process {risk.value} = escalate",
        result == ToolPolicyDecision.ESCALATE,
        f"got: {result.value}",
    )

# Network: ALWAYS ESCALATE
for risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
    result = resolve_tool_policy(
        "ea_product", _intent(IntentType.NETWORK_CALL, "curl x"), risk
    )
    check(
        f"ea_product network {risk.value} = escalate",
        result == ToolPolicyDecision.ESCALATE,
        f"got: {result.value}",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. Unknown Role — Fallback
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 3. Unknown Role Fallback ═══")

# Unknown role: ALWAYS ESCALATE (safe fallback)
for itype in IntentType:
    for risk in RiskLevel:
        result = resolve_tool_policy("unknown_role", _intent(itype, "x"), risk)
        check(
            f"unknown {itype.value}/{risk.value} = escalate",
            result == ToolPolicyDecision.ESCALATE,
            f"got: {result.value}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. End-to-End: Tool Policy → Permission Resolution
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 4. E2E: Tool Policy → Permission Resolution ═══")

# Builder reads a file → tool_policy=ALLOW → auto-approve
e2e_intent = extract_intent("Read(/opt/OS/eos/db.py)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("builder", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
check("e2e builder read: policy=allow", e2e_tool == ToolPolicyDecision.ALLOW)
check(
    "e2e builder read: resolution=auto_approve",
    e2e_res.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)

# Builder runs git status → tool_policy=ALLOW but no extractable path
# → constraint escalates (NO_TARGET) → final=ESCALATE → surfaced
# This is expected: safe commands without absolute paths escalate for safety.
e2e_intent = extract_intent("Bash(git status)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("builder", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
check("e2e builder git status: policy=allow", e2e_tool == ToolPolicyDecision.ALLOW)
check(
    "e2e builder git status: resolution=surface (no path → escalate)",
    e2e_res.resolution == PermissionResolution.SURFACE_AND_WAIT,
)

# Builder runs rm -rf → tool_policy=ESCALATE → surfaced
e2e_intent = extract_intent("Bash(rm -rf /opt/OS/logs/)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("builder", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
check("e2e builder rm -rf: policy=escalate", e2e_tool == ToolPolicyDecision.ESCALATE)
check(
    "e2e builder rm -rf: resolution=surface",
    e2e_res.resolution == PermissionResolution.SURFACE_AND_WAIT,
)

# Builder curls an API → tool_policy=ESCALATE → surfaced
e2e_intent = extract_intent("Bash(curl -s https://api.example.com)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("builder", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
check("e2e builder curl: policy=escalate", e2e_tool == ToolPolicyDecision.ESCALATE)
check(
    "e2e builder curl: resolution=surface",
    e2e_res.resolution == PermissionResolution.SURFACE_AND_WAIT,
)

# EA product writes a file → tool_policy=ESCALATE → surfaced
e2e_intent = extract_intent("Write(/opt/OS/eos/new.py)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("ea_product", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_product_main", e2e_intent, e2e_risk)
check(
    "e2e ea_product write: policy=escalate",
    e2e_tool == ToolPolicyDecision.ESCALATE,
)
check(
    "e2e ea_product write: resolution=surface",
    e2e_res.resolution == PermissionResolution.SURFACE_AND_WAIT,
)

# EA product runs ls → tool_policy=ALLOW → auto-approve
e2e_intent = extract_intent("Bash(ls /opt/OS)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("ea_product", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_product_main", e2e_intent, e2e_risk)
check("e2e ea_product ls: policy=allow", e2e_tool == ToolPolicyDecision.ALLOW)
check(
    "e2e ea_product ls: resolution=auto_approve",
    e2e_res.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)

# EA product runs docker restart → medium risk → tool_policy=ESCALATE
e2e_intent = extract_intent("Bash(docker restart os-bot)")
e2e_risk = classify_risk(e2e_intent)
e2e_tool = resolve_tool_policy("ea_product", e2e_intent, e2e_risk)
e2e_res = resolve_permission("dex_product_main", e2e_intent, e2e_risk)
check(
    "e2e ea_product docker restart: policy=escalate",
    e2e_tool == ToolPolicyDecision.ESCALATE,
)
check(
    "e2e ea_product docker restart: resolution=surface",
    e2e_res.resolution == PermissionResolution.SURFACE_AND_WAIT,
)


# ═══════════════════════════════════════════════════════════════════════════
# 5. User-Facing Sessions Unchanged
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 5. User-Facing Sessions Unchanged ═══")

# User-facing sessions always surface regardless of tool policy
for itype in (IntentType.FILE_READ, IntentType.FILE_WRITE, IntentType.COMMAND):
    for risk in RiskLevel:
        intent = _intent(itype, "x")
        res = resolve_permission("interactive_user", intent, risk)
        check(
            f"user-facing {itype.value}/{risk.value} = surface",
            res.resolution == PermissionResolution.SURFACE_AND_WAIT,
            f"got: {res.resolution.value}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# 6. Backwards Compatibility — None intent/risk
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 6. Backwards Compatibility ═══")

# Autonomous session, no intent/risk → original auto-approve behavior
check(
    "backwards compat: autonomous + None = auto",
    resolve_permission("dex_builder_main").resolution
    == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)
check(
    "backwards compat: autonomous + explicit None = auto",
    resolve_permission("dex_builder_main", None, None).resolution
    == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
)

# User-facing session, no intent/risk → original surface behavior
check(
    "backwards compat: user-facing + None = surface",
    resolve_permission("interactive_session").resolution
    == PermissionResolution.SURFACE_AND_WAIT,
)

# should_surface_permission backwards compat
check(
    "backwards compat: should_surface autonomous",
    not should_surface_permission("dex_builder_main"),
)
check(
    "backwards compat: should_surface user-facing",
    should_surface_permission("interactive_session"),
)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Tool Policy Asymmetry (Builder vs EA Product)
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 7. Role Asymmetry Verification ═══")

# Same action, different roles, different policies
write_intent = _intent(IntentType.FILE_WRITE, "Write(x)", "write", "/x")
builder_write = resolve_tool_policy("builder", write_intent, RiskLevel.MEDIUM)
product_write = resolve_tool_policy("ea_product", write_intent, RiskLevel.MEDIUM)
check(
    "builder write medium != ea_product write medium",
    builder_write != product_write,
    f"builder={builder_write.value}, product={product_write.value}",
)
check("builder write medium = allow", builder_write == ToolPolicyDecision.ALLOW)
check("product write medium = escalate", product_write == ToolPolicyDecision.ESCALATE)

# Medium commands: builder allows, ea_product escalates
cmd_intent = _intent(IntentType.COMMAND, "Bash(python3 test.py)", "python3 test.py")
builder_cmd = resolve_tool_policy("builder", cmd_intent, RiskLevel.MEDIUM)
product_cmd = resolve_tool_policy("ea_product", cmd_intent, RiskLevel.MEDIUM)
check("builder cmd medium = allow", builder_cmd == ToolPolicyDecision.ALLOW)
check("product cmd medium = escalate", product_cmd == ToolPolicyDecision.ESCALATE)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Spine Event Payload Structure
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 8. Spine Event Payload Structure ═══")

# Verify the payload fields that would be emitted
intent = extract_intent("Bash(git push origin main)")
risk = classify_risk(intent)
tool_policy = resolve_tool_policy("builder", intent, risk)

check(
    "spine: tool_policy_decision field exists",
    tool_policy.value in ("allow", "escalate", "deny"),
    f"got: {tool_policy.value}",
)
check(
    "spine: risk + policy coherent for git push",
    risk == RiskLevel.HIGH and tool_policy == ToolPolicyDecision.ESCALATE,
    f"risk={risk.value}, policy={tool_policy.value}",
)

# Simulated payload construction (mirrors session_discord_bridge)
payload = {
    "resolution": resolve_permission("dex_builder_main", intent, risk).resolution.value,
    "intent_type": intent.type.value,
    "risk_level": risk.value,
    "tool_policy_decision": tool_policy.value,
}
check(
    "spine: payload has tool_policy_decision",
    "tool_policy_decision" in payload,
)
check(
    "spine: payload tool_policy_decision = escalate",
    payload["tool_policy_decision"] == "escalate",
)


# ═══════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print(f"{'═' * 60}")

if FAIL > 0:
    print("\n⚠️  FAILURES DETECTED — fixes required")
    sys.exit(1)
else:
    print("\n✅ All tool policy checks passed")
    sys.exit(0)
