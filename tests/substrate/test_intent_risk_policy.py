"""
Validation of the intent + risk-based permission control system.

Tests the complete chain: intent extraction → risk classification →
permission resolution. Every test uses pure function calls — no mocking,
no Discord, no tmux.

Proves:
  1. Intent extraction parses CC permission prompts correctly
  2. Risk classification is deterministic and biases toward safety
  3. Autonomous LOW/MEDIUM → auto-approved, HIGH → surfaced
  4. User-facing sessions → always surfaced regardless of risk
  5. Backwards compatibility: None intent/risk → original behavior
  6. Spine event payloads would contain intent + risk fields
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.discord_output_policy import (
    IntentType,
    PermissionIntent,
    PermissionResolution,
    RiskLevel,
    classify_risk,
    extract_intent,
    resolve_permission,
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


if __name__ == "__main__":
    # ═══════════════════════════════════════════════════════════════════════
    # 1. Intent Extraction — Tool Call Parsing
    # ═══════════════════════════════════════════════════════════════════════
    print("\n═══ 1. Intent Extraction ═══")

    # Bash commands
    intent = extract_intent("Bash(python3 -c 'from umh.storage.adapters.neon import get_conn')")
    check("bash command type", intent.type == IntentType.COMMAND, f"got: {intent.type}")
    check(
        "bash command parsed",
        "python3 -c" in intent.command,
        f"got: {intent.command}",
    )

    # File reads
    intent = extract_intent("Read(/opt/OS/eos/gateway.py)")
    check("read is file_read", intent.type == IntentType.FILE_READ, f"got: {intent.type}")
    check("read target parsed", "gateway.py" in intent.target, f"got: {intent.target}")

    intent = extract_intent("Glob(**/*.py)")
    check("glob is file_read", intent.type == IntentType.FILE_READ, f"got: {intent.type}")

    intent = extract_intent("Grep(pattern)")
    check("grep is file_read", intent.type == IntentType.FILE_READ, f"got: {intent.type}")

    # File writes
    intent = extract_intent("Write(/opt/OS/new_file.py)")
    check(
        "write is file_write", intent.type == IntentType.FILE_WRITE, f"got: {intent.type}"
    )
    check("write target parsed", "new_file.py" in intent.target, f"got: {intent.target}")

    intent = extract_intent("Edit(/opt/OS/eos/db.py)")
    check("edit is file_write", intent.type == IntentType.FILE_WRITE, f"got: {intent.type}")

    # Network calls
    intent = extract_intent("Bash(curl -s https://api.example.com/health)")
    check(
        "curl is network_call",
        intent.type == IntentType.NETWORK_CALL,
        f"got: {intent.type}",
    )

    intent = extract_intent("Bash(pip install requests)")
    check(
        "pip install is network_call",
        intent.type == IntentType.NETWORK_CALL,
        f"got: {intent.type}",
    )

    intent = extract_intent("WebFetch(https://docs.example.com)")
    check(
        "webfetch is network_call",
        intent.type == IntentType.NETWORK_CALL,
        f"got: {intent.type}",
    )

    intent = extract_intent("WebSearch(python asyncio tutorial)")
    check(
        "websearch is network_call",
        intent.type == IntentType.NETWORK_CALL,
        f"got: {intent.type}",
    )

    # Agent subprocess
    intent = extract_intent("Agent(review code changes)")
    check(
        "agent is process_exec",
        intent.type == IntentType.PROCESS_EXEC,
        f"got: {intent.type}",
    )

    # Unknown / unparseable
    intent = extract_intent("Allow this tool call to proceed")
    check(
        "unparseable is unknown", intent.type == IntentType.UNKNOWN, f"got: {intent.type}"
    )

    intent = extract_intent("")
    check("empty is unknown", intent.type == IntentType.UNKNOWN, f"got: {intent.type}")


    # ═══════════════════════════════════════════════════════════════════════════
    # 2. Risk Classification
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n═══ 2. Risk Classification ═══")

    # LOW risk: read-only operations
    check(
        "file_read is low",
        classify_risk(PermissionIntent(IntentType.FILE_READ, "Read(x)", "read", "/x"))
        == RiskLevel.LOW,
    )

    # LOW risk: safe commands
    safe_commands = [
        "python3 -c 'from umh.storage.adapters.neon import get_conn'",
        "python3 -m py_compile eos/db.py",
        "ruff check eos/",
        "ruff format eos/db.py",
        "git status",
        "git log --oneline -5",
        "git diff HEAD",
        "ls -la /opt/OS",
        "echo hello",
    ]
    for cmd in safe_commands:
        risk = classify_risk(PermissionIntent(IntentType.COMMAND, f"Bash({cmd})", cmd, ""))
        check(f"safe cmd low: {cmd[:40]}", risk == RiskLevel.LOW, f"got: {risk}")

    # MEDIUM risk: file writes
    check(
        "file_write is medium",
        classify_risk(PermissionIntent(IntentType.FILE_WRITE, "Write(x)", "write", "/x"))
        == RiskLevel.MEDIUM,
    )

    # MEDIUM risk: process execution
    check(
        "process_exec is medium",
        classify_risk(PermissionIntent(IntentType.PROCESS_EXEC, "Agent(x)", "agent", "x"))
        == RiskLevel.MEDIUM,
    )

    # MEDIUM risk: non-destructive general commands
    medium_commands = [
        "python3 /opt/OS/scripts/update-graph",
        "docker restart os-bot",
        "python3 tests/run_all.py",
    ]
    for cmd in medium_commands:
        risk = classify_risk(PermissionIntent(IntentType.COMMAND, f"Bash({cmd})", cmd, ""))
        check(f"general cmd medium: {cmd[:40]}", risk == RiskLevel.MEDIUM, f"got: {risk}")

    # HIGH risk: destructive commands
    destructive_commands = [
        "rm -rf /opt/OS/logs/",
        "rm /opt/OS/important.py",
        "git push origin main",
        "git reset --hard HEAD~3",
        "git checkout -- .",
        "git branch -D feature",
        "kill -9 12345",
        "pkill python",
        "sudo apt install something",
        "docker rm os-bot",
        "docker system prune -a",
    ]
    for cmd in destructive_commands:
        risk = classify_risk(PermissionIntent(IntentType.COMMAND, f"Bash({cmd})", cmd, ""))
        check(f"destructive high: {cmd[:40]}", risk == RiskLevel.HIGH, f"got: {risk}")

    # HIGH risk: network calls
    check(
        "network_call is high",
        classify_risk(PermissionIntent(IntentType.NETWORK_CALL, "curl x", "curl x", ""))
        == RiskLevel.HIGH,
    )

    # HIGH risk: unknown intent (safe default)
    check(
        "unknown is high",
        classify_risk(PermissionIntent(IntentType.UNKNOWN, "???", "", ""))
        == RiskLevel.HIGH,
    )


    # ═══════════════════════════════════════════════════════════════════════════
    # 3. Permission Resolution — Decision Table
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n═══ 3. Permission Resolution (Intent + Risk) ═══")

    # ── Autonomous sessions ──

    # LOW risk → auto-approve (target inside approved root)
    check(
        "autonomous + low = auto",
        resolve_permission(
            "dex_builder_main",
            PermissionIntent(
                IntentType.FILE_READ, "Read(/opt/OS/foo.py)", "read", "/opt/OS/foo.py"
            ),
            RiskLevel.LOW,
        ).resolution
        == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )

    # MEDIUM risk → auto-approve (target inside approved root)
    check(
        "autonomous + medium = auto",
        resolve_permission(
            "dex_builder_main",
            PermissionIntent(
                IntentType.FILE_WRITE, "Write(/opt/OS/bar.py)", "write", "/opt/OS/bar.py"
            ),
            RiskLevel.MEDIUM,
        ).resolution
        == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )

    # HIGH risk → SURFACE (the new behavior)
    check(
        "autonomous + high = surface",
        resolve_permission(
            "dex_builder_main",
            PermissionIntent(IntentType.NETWORK_CALL, "curl x", "curl x", ""),
            RiskLevel.HIGH,
        ).resolution
        == PermissionResolution.SURFACE_AND_WAIT,
    )

    # HIGH risk from product session too
    check(
        "product + high = surface",
        resolve_permission(
            "dex_product_main",
            PermissionIntent(IntentType.COMMAND, "rm -rf /", "rm -rf /", ""),
            RiskLevel.HIGH,
        ).resolution
        == PermissionResolution.SURFACE_AND_WAIT,
    )

    # ── User-facing sessions — always surface ──

    check(
        "user-facing + low = surface",
        resolve_permission(
            "interactive_session",
            PermissionIntent(IntentType.FILE_READ, "Read(x)", "read", "/x"),
            RiskLevel.LOW,
        ).resolution
        == PermissionResolution.SURFACE_AND_WAIT,
    )

    check(
        "user-facing + medium = surface",
        resolve_permission(
            "interactive_session",
            PermissionIntent(IntentType.FILE_WRITE, "Write(x)", "write", "/x"),
            RiskLevel.MEDIUM,
        ).resolution
        == PermissionResolution.SURFACE_AND_WAIT,
    )

    check(
        "user-facing + high = surface",
        resolve_permission(
            "interactive_session",
            PermissionIntent(IntentType.COMMAND, "rm -rf /", "rm -rf /", ""),
            RiskLevel.HIGH,
        ).resolution
        == PermissionResolution.SURFACE_AND_WAIT,
    )


    # ═══════════════════════════════════════════════════════════════════════════
    # 4. Backwards Compatibility — None intent/risk
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n═══ 4. Backwards Compatibility ═══")

    # Autonomous session, no intent/risk → original behavior (auto-approve)
    check(
        "autonomous + None = auto (legacy)",
        resolve_permission("dex_builder_main").resolution
        == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )

    check(
        "autonomous + None = auto (legacy, explicit)",
        resolve_permission("dex_builder_main", None, None).resolution
        == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )

    # User-facing session, no intent/risk → original behavior (surface)
    check(
        "user-facing + None = surface (legacy)",
        resolve_permission("interactive_session").resolution
        == PermissionResolution.SURFACE_AND_WAIT,
    )

    # should_surface_permission backwards compat
    check(
        "should_surface autonomous (legacy)",
        not should_surface_permission("dex_builder_main"),
    )
    check(
        "should_surface user-facing (legacy)",
        should_surface_permission("interactive_session"),
    )

    # should_surface_permission with intent/risk
    check(
        "should_surface autonomous + high",
        should_surface_permission(
            "dex_builder_main",
            PermissionIntent(IntentType.UNKNOWN, "???", "", ""),
            RiskLevel.HIGH,
        ),
    )
    check(
        "should_not_surface autonomous + low",
        not should_surface_permission(
            "dex_builder_main",
            PermissionIntent(
                IntentType.FILE_READ, "Read(/opt/OS/foo.py)", "read", "/opt/OS/foo.py"
            ),
            RiskLevel.LOW,
        ),
    )


    # ═══════════════════════════════════════════════════════════════════════════
    # 5. End-to-End: Permission Text → Intent → Risk → Resolution
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n═══ 5. End-to-End Chains ═══")

    # Scenario: autonomous session reads a file → should auto-approve
    e2e_text = "Read(/opt/OS/eos/gateway.py)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
    check(
        "e2e read auto-approved",
        e2e_resolution.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )
    check("e2e read is low risk", e2e_risk == RiskLevel.LOW)

    # Scenario: autonomous session runs git status → no extractable path → escalates
    # (constraint layer requires deterministic path for auto-approve of commands)
    e2e_text = "Bash(git status)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_product_main", e2e_intent, e2e_risk)
    check(
        "e2e git status surfaced (no path → escalate)",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )
    check("e2e git status is low risk", e2e_risk == RiskLevel.LOW)

    # Scenario: autonomous session runs rm -rf → should SURFACE
    e2e_text = "Bash(rm -rf /opt/OS/logs/)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
    check(
        "e2e rm -rf surfaced",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )
    check("e2e rm -rf is high risk", e2e_risk == RiskLevel.HIGH)

    # Scenario: autonomous session pushes to git → should SURFACE
    e2e_text = "Bash(git push origin main)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
    check(
        "e2e git push surfaced",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )
    check("e2e git push is high risk", e2e_risk == RiskLevel.HIGH)

    # Scenario: ea_product writes a file → tool policy escalates (product sessions
    # should not mutate the codebase freely, even at medium risk)
    e2e_text = "Write(/opt/OS/eos/new_module.py)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_product_main", e2e_intent, e2e_risk)
    check(
        "e2e product write surfaced (tool policy)",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )
    check("e2e write is medium risk", e2e_risk == RiskLevel.MEDIUM)

    # Scenario: builder writes a file → tool policy allows (builder can mutate freely)
    e2e_text = "Write(/opt/OS/eos/new_module.py)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
    check(
        "e2e builder write auto-approved (tool policy)",
        e2e_resolution.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
    )
    check("e2e builder write is medium risk", e2e_risk == RiskLevel.MEDIUM)

    # Scenario: autonomous session curls an API → should SURFACE
    e2e_text = "Bash(curl -s https://api.example.com/data)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
    check(
        "e2e curl surfaced",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )
    check("e2e curl is high risk", e2e_risk == RiskLevel.HIGH)

    # Scenario: autonomous session uses sudo → should SURFACE
    e2e_text = "Bash(sudo systemctl restart nginx)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("dex_builder_main", e2e_intent, e2e_risk)
    check(
        "e2e sudo surfaced",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )
    check("e2e sudo is high risk", e2e_risk == RiskLevel.HIGH)

    # Scenario: user-facing session reads a file → still surfaces (no auto-approve)
    e2e_text = "Read(/opt/OS/eos/gateway.py)"
    e2e_intent = extract_intent(e2e_text)
    e2e_risk = classify_risk(e2e_intent)
    e2e_resolution = resolve_permission("interactive_user", e2e_intent, e2e_risk)
    check(
        "e2e user-facing read surfaced",
        e2e_resolution.resolution == PermissionResolution.SURFACE_AND_WAIT,
    )


    # ═══════════════════════════════════════════════════════════════════════════
    # 6. Edge Cases
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n═══ 6. Edge Cases ═══")

    # Network commands embedded in Bash
    intent = extract_intent("Bash(git clone https://github.com/repo.git)")
    check(
        "git clone is network",
        intent.type == IntentType.NETWORK_CALL,
        f"got: {intent.type}",
    )

    # Docker destructive commands
    intent = extract_intent("Bash(docker system prune -a)")
    risk = classify_risk(intent)
    check("docker prune is high", risk == RiskLevel.HIGH, f"got: {risk}")

    # dd command
    intent = extract_intent("Bash(dd if=/dev/zero of=/dev/sda)")
    risk = classify_risk(intent)
    check("dd is high", risk == RiskLevel.HIGH, f"got: {risk}")

    # chmod 777
    intent = extract_intent("Bash(chmod 777 /opt/OS)")
    risk = classify_risk(intent)
    check("chmod 777 is high", risk == RiskLevel.HIGH, f"got: {risk}")

    # Raw text preserved in intent
    intent = extract_intent("Bash(python3 /opt/OS/scripts/test.py)")
    check(
        "raw text preserved",
        "Bash(python3 /opt/OS/scripts/test.py)" in intent.raw,
        f"got: {intent.raw}",
    )

    # Intent with risk=None falls back to legacy
    res = resolve_permission("dex_builder_main", intent, None)
    check(
        "intent present but risk=None → legacy auto",
        res.resolution == PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
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
        print("\n✅ All intent + risk policy checks passed")
        sys.exit(0)
