"""
Validation: enforcement is the default across all execution boundaries.

Proves:
  1. Pipeline run_step with enforcement decision → deny short-circuits
  2. Pipeline run_step with enforcement decision → handler still runs on ALLOW
  3. Pipeline run_step without decision → legacy behavior preserved
  4. Pipeline to_dict reports enforcement_mode (enforced vs legacy)
  5. Station daemon process_action with decision → deny short-circuits
  6. Station daemon process_action with decision → handler runs on ALLOW
  7. Station daemon process_action without decision → legacy path, tagged
  8. Station daemon no longer has _process_action / process_action_enforced bypass
  9. Non-executable pipeline handlers are unaffected by enforcement
  10. Enforcement trace data is present in enforced step results

Every test uses pure function calls — no Discord, no tmux, no network.
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.dispatch_enforcement import (
    ExecutionResult,
    ExecutionStatus,
)
from umh.substrate.discord_output_policy import (
    ExecutionMode,
    FinalResolution,
    PermissionOrigin,
    ToolPolicyDecision,
)
from umh.substrate.discord_output_policy import PermissionDecision
from umh.substrate.execution_constraints import (
    ConstraintDecision,
    ConstraintType,
)
from umh.substrate.execution_control import ControlType
from umh.substrate.pipeline import (
    Pipeline,
    PipelineStep,
    StepResult,
    register_handler,
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


def _make_decision(
    *,
    final: FinalResolution = FinalResolution.ALLOW,
    rewritten_command: str | None = None,
    timeout_seconds: int | None = 30,
    constraint_reason: str | None = None,
) -> PermissionDecision:
    """Build a PermissionDecision for testing."""
    return PermissionDecision(
        final_resolution=final,
        execution_mode=ExecutionMode.AUTO,
        origin=PermissionOrigin.INTERNAL_AUTO,
        tool_policy_decision=ToolPolicyDecision.ALLOW,
        constraint_evaluated=True,
        constraint_result=ConstraintDecision.ALLOWED,
        constraint_type=ConstraintType.NONE,
        constraint_reason=constraint_reason,
        execution_control_applied=True,
        execution_control_type=ControlType.TIMEOUT_APPLIED.value,
        rewritten_command=rewritten_command,
        timeout_seconds=timeout_seconds,
        execution_controls_applied=(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Register a test handler
# ═══════════════════════════════════════════════════════════════════════════

_test_handler_calls: list[str] = []


def _test_handler(step, context):
    """Simple handler that records calls for verification."""
    _test_handler_calls.append(step.name)
    return StepResult(
        status="succeeded",
        result={"handler": "test", "step_name": step.name},
    )


register_handler("test_handler", _test_handler)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Pipeline — Deny Short-Circuit
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Pipeline: Deny Short-Circuit ──")

_test_handler_calls.clear()
deny_decision = _make_decision(
    final=FinalResolution.DENY,
    constraint_reason="test pipeline deny",
)

pipe = Pipeline.new(
    "test_deny",
    [PipelineStep.new("s1", "test_handler")],
    context={"_enforcement_decision": deny_decision},
)
result = pipe.run()

check("deny → pipeline status=failed", result["status"] == "failed")
check("deny → handler NOT called", len(_test_handler_calls) == 0)

# Check the step result has enforcement metadata
step_result = result["steps"][0]["result"]
check(
    "deny → step result has enforcement",
    step_result is not None
    and step_result.get("result", {}).get("enforcement") == "dispatch_enforcement",
)
check(
    "deny → step result has denied status",
    step_result is not None
    and step_result.get("result", {}).get("enforcement_status") == "denied",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Pipeline — Allow with Enforcement
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Pipeline: Allow with Enforcement ──")

_test_handler_calls.clear()
allow_decision = _make_decision(timeout_seconds=30)

pipe2 = Pipeline.new(
    "test_allow",
    [PipelineStep.new("s2", "test_handler")],
    context={"_enforcement_decision": allow_decision},
)
result2 = pipe2.run()

check("allow → pipeline status=succeeded", result2["status"] == "succeeded")
check("allow → handler called", len(_test_handler_calls) == 1)
check("allow → handler called with right step", _test_handler_calls[0] == "s2")

# Check enforcement metadata injected
step_results = result2.get("step_results", {})
check(
    "allow → step result has enforcement tag",
    step_results.get("s2", {}).get("enforcement") == "dispatch_enforcement",
)
check(
    "allow → enforcement_mode = enforced",
    result2.get("enforcement_mode") == "enforced",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Pipeline — Legacy (No Decision)
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Pipeline: Legacy (No Decision) ──")

_test_handler_calls.clear()
pipe3 = Pipeline.new(
    "test_legacy",
    [PipelineStep.new("s3", "test_handler")],
)
result3 = pipe3.run()

check("legacy → pipeline status=succeeded", result3["status"] == "succeeded")
check("legacy → handler called", len(_test_handler_calls) == 1)
check(
    "legacy → enforcement_mode = legacy",
    result3.get("enforcement_mode") == "legacy",
)

# Step results should NOT have enforcement tag
step_results3 = result3.get("step_results", {})
check(
    "legacy → no enforcement tag in step result",
    "enforcement" not in step_results3.get("s3", {}),
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Pipeline — Multi-Step Deny Stops Pipeline
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Pipeline: Multi-Step Deny ──")

_test_handler_calls.clear()
deny_decision2 = _make_decision(
    final=FinalResolution.DENY,
    constraint_reason="multi-step deny",
)

pipe4 = Pipeline.new(
    "test_multi_deny",
    [
        PipelineStep.new("first", "test_handler"),
        PipelineStep.new("second", "test_handler"),
    ],
    context={"_enforcement_decision": deny_decision2},
)
result4 = pipe4.run()

check("multi deny → status=failed", result4["status"] == "failed")
check("multi deny → zero handlers called", len(_test_handler_calls) == 0)
check(
    "multi deny → only first step attempted",
    result4["steps"][0]["status"] == "failed",
)
check(
    "multi deny → second step still pending",
    result4["steps"][1]["status"] == "pending",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: Station Daemon — Deny Short-Circuit
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Station Daemon: Deny Short-Circuit ──")

from umh.substrate.station_daemon import StationDaemon
from umh.substrate.actions import ActionKind, ActionStatus

daemon = StationDaemon(
    node_id="test-daemon",
    dry_run=True,
)

deny_action = {
    "action_id": "test-deny-1",
    "kind": ActionKind.OPEN_URL.value,
    "payload": {"url": "https://example.com"},
}
daemon_deny_decision = _make_decision(
    final=FinalResolution.DENY,
    constraint_reason="daemon deny test",
)

outcome = daemon.process_action(deny_action, daemon_deny_decision, post_to_bus=False)

check(
    "daemon deny → REJECTED",
    outcome.status == ActionStatus.REJECTED,
)
check(
    "daemon deny → reason in detail",
    "denied by policy" in outcome.detail,
)
check(
    "daemon deny → enforcement tag",
    outcome.data.get("enforcement") == "dispatch_enforcement",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: Station Daemon — Allow with Enforcement
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Station Daemon: Allow with Enforcement ──")

allow_action = {
    "action_id": "test-allow-1",
    "kind": ActionKind.OPEN_URL.value,
    "payload": {"url": "https://example.com"},
}
daemon_allow_decision = _make_decision(timeout_seconds=30)

outcome2 = daemon.process_action(allow_action, daemon_allow_decision, post_to_bus=False)

check(
    "daemon allow → SUCCEEDED",
    outcome2.status == ActionStatus.SUCCEEDED,
)
check(
    "daemon allow → enforcement tag",
    outcome2.data.get("enforcement") == "dispatch_enforcement",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Station Daemon — Legacy Path (No Decision)
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Station Daemon: Legacy Path ──")

legacy_action = {
    "action_id": "test-legacy-1",
    "kind": ActionKind.OPEN_URL.value,
    "payload": {"url": "https://example.com"},
}

outcome3 = daemon.process_action(legacy_action, post_to_bus=False)

check(
    "daemon legacy → SUCCEEDED",
    outcome3.status == ActionStatus.SUCCEEDED,
)
check(
    "daemon legacy → enforcement_mode=legacy",
    outcome3.data.get("enforcement_mode") == "legacy",
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: Station Daemon — No Bypass APIs
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Station Daemon: No Bypass APIs ──")

check(
    "no _process_action method",
    not hasattr(daemon, "_process_action"),
)
check(
    "no process_action_enforced method",
    not hasattr(daemon, "process_action_enforced"),
)
check(
    "process_action is the public API",
    hasattr(daemon, "process_action"),
)
check(
    "_execute_handler is private",
    hasattr(daemon, "_execute_handler"),
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: Station Daemon — Unknown Kind
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Station Daemon: Unknown Kind ──")

bad_action = {
    "action_id": "test-bad-1",
    "kind": "totally_fake_kind",
    "payload": {},
}

outcome4 = daemon.process_action(bad_action, post_to_bus=False)
check(
    "unknown kind → REJECTED",
    outcome4.status == ActionStatus.REJECTED,
)
check(
    "unknown kind → detail mentions kind",
    "unknown action kind" in outcome4.detail,
)

# Same with decision — deny check happens first, then kind check
outcome5 = daemon.process_action(
    bad_action, _make_decision(timeout_seconds=5), post_to_bus=False
)
check(
    "unknown kind enforced → REJECTED",
    outcome5.status == ActionStatus.REJECTED,
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: Pipeline to_dict Enforcement Mode
# ═══════════════════════════════════════════════════════════════════════════

print("\n── Pipeline to_dict Enforcement Mode ──")

# Enforced pipeline
pipe_e = Pipeline.new(
    "enforced_pipe",
    [],
    context={"_enforcement_decision": _make_decision()},
)
check(
    "to_dict enforced mode",
    pipe_e.to_dict()["enforcement_mode"] == "enforced",
)
# Decision should not leak into serialized context
check(
    "to_dict hides _enforcement_decision",
    "_enforcement_decision" not in pipe_e.to_dict()["context"],
)

# Legacy pipeline
pipe_l = Pipeline.new("legacy_pipe", [])
check(
    "to_dict legacy mode",
    pipe_l.to_dict()["enforcement_mode"] == "legacy",
)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {PASS + FAIL}  |  PASS: {PASS}  |  FAIL: {FAIL}")
print(f"{'=' * 60}")

if FAIL > 0:
    sys.exit(1)
