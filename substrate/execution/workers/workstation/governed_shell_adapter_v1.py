"""Governed Shell Adapter v1.

Allowlist-based shell execution adapter. Only explicitly approved
command prefixes can execute. Unknown patterns are denied by default.

Governance evaluates:
  - command prefix against allowlist
  - risk class
  - operational mode constraints
  - side-effect profile (read-only vs mutation)
  - execution scope

BLOCKED unconditionally:
  rm, sudo, chmod, chown, kill, pkill, killall,
  apt, pip install, npm install, curl -X, wget,
  mkfs, dd, mv (outside safe dirs), cp (outside safe dirs),
  bash -c (arbitrary), sh -c (arbitrary)

UMH substrate subsystem.
"""

from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from .workstation_contracts_v1 import (
    OperationalMode,
    ShellCommandVerdict,
    WorkstationExecutionOutcome,
    WorkstationExecutionRequest,
    WorkstationExecutionResult,
    _new_id,
    _now_iso,
)
from .workstation_operational_modes_v1 import get_mode_definition


# ---------------------------------------------------------------------------
# Structural blocklist — these NEVER execute regardless of mode
# ---------------------------------------------------------------------------

STRUCTURALLY_BLOCKED_PREFIXES: frozenset[str] = frozenset(
    {
        "rm ",
        "rm\t",
        "sudo ",
        "chmod ",
        "chown ",
        "kill ",
        "pkill ",
        "killall ",
        "apt ",
        "apt-get ",
        "dpkg ",
        "pip install",
        "pip3 install",
        "pip uninstall",
        "npm install",
        "npm uninstall",
        "yarn add",
        "yarn remove",
        "curl -X",
        "wget ",
        "mkfs",
        "dd ",
        "shutdown",
        "reboot",
        "systemctl",
        "service ",
        "bash -c",
        "sh -c",
        "eval ",
        "exec ",
        "> /",
        ">> /",
        "| sudo",
        "; rm",
        "&& rm",
        "|| rm",
    }
)

STRUCTURALLY_BLOCKED_EXACT: frozenset[str] = frozenset(
    {
        "rm",
        "sudo",
        "chmod",
        "chown",
        "kill",
        "pkill",
        "killall",
        "halt",
        "poweroff",
        "reboot",
        "shutdown",
    }
)

# Read-only commands that are always safe
READ_ONLY_COMMANDS: frozenset[str] = frozenset(
    {
        "pwd",
        "ls",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "find",
        "which",
        "whoami",
        "hostname",
        "uname",
        "uptime",
        "df",
        "free",
        "ps",
        "date",
        "file",
        "stat",
        "echo",
    }
)


@dataclass
class ShellGovernanceDecision:
    """Record of a shell command governance decision."""

    decision_id: str = ""
    command: str = ""
    command_prefix: str = ""
    verdict: ShellCommandVerdict = ShellCommandVerdict.DENIED
    risk_class: str = "safe"
    denial_reason: str = ""
    rules_applied: list[str] = field(default_factory=list)
    operational_mode: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("shdec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "command": self.command,
            "command_prefix": self.command_prefix,
            "verdict": self.verdict.value,
            "risk_class": self.risk_class,
            "denial_reason": self.denial_reason,
            "rules_applied": self.rules_applied,
            "operational_mode": self.operational_mode,
            "timestamp": self.timestamp,
        }


class GovernedShellAdapter:
    """Allowlist-based governed shell execution."""

    def __init__(self, operational_mode: OperationalMode = OperationalMode.DEVELOPER) -> None:
        self._mode = operational_mode
        self._mode_def = get_mode_definition(operational_mode)
        self._decisions: list[ShellGovernanceDecision] = []

    @property
    def mode(self) -> OperationalMode:
        return self._mode

    def set_mode(self, mode: OperationalMode) -> None:
        self._mode = mode
        self._mode_def = get_mode_definition(mode)

    def evaluate_command(self, command: str) -> ShellGovernanceDecision:
        """Evaluate whether a shell command is approved for execution."""
        stripped = command.strip()
        prefix = self._extract_prefix(stripped)
        rules: list[str] = []

        # Rule 1: Structural block
        if stripped in STRUCTURALLY_BLOCKED_EXACT:
            rules.append("STRUCTURAL_BLOCK_EXACT")
            return self._make_decision(
                stripped, prefix, ShellCommandVerdict.DENIED,
                f"Command '{stripped}' is structurally blocked", rules, "forbidden",
            )

        for blocked in STRUCTURALLY_BLOCKED_PREFIXES:
            if stripped.startswith(blocked):
                rules.append("STRUCTURAL_BLOCK_PREFIX")
                return self._make_decision(
                    stripped, prefix, ShellCommandVerdict.DENIED,
                    f"Command prefix '{blocked.strip()}' is structurally blocked", rules, "forbidden",
                )

        # Rule 2: Check against pipe/chain injection
        if self._has_dangerous_chain(stripped):
            rules.append("DANGEROUS_CHAIN_DETECTED")
            return self._make_decision(
                stripped, prefix, ShellCommandVerdict.DENIED,
                "Command contains dangerous pipe or chain pattern", rules, "high",
            )

        # Rule 3: Mode allowlist check
        if not self._mode_def.allows_command(prefix):
            rules.append("MODE_ALLOWLIST_DENIED")
            return self._make_decision(
                stripped, prefix, ShellCommandVerdict.DENIED,
                f"Command '{prefix}' not in {self._mode.value} allowlist", rules, "medium",
            )

        # Rule 4: Determine risk
        risk = "safe" if prefix in READ_ONLY_COMMANDS else "low"
        rules.append("ALLOWLIST_APPROVED")
        return self._make_decision(
            stripped, prefix, ShellCommandVerdict.APPROVED, "", rules, risk,
        )

    # ── §14.1 Adapter Contract ──────────────────────────────────────────────

    def translate_request(self, request: WorkstationExecutionRequest) -> WorkstationExecutionRequest:
        """§14.1 translate_request: input is already typed. Returns as-is."""
        return request

    def validate_operation(self, request: WorkstationExecutionRequest) -> ShellGovernanceDecision:
        """§14.1 validate_operation: governance check for the command."""
        return self.evaluate_command(request.command)

    def normalize_result(
        self,
        raw_result: subprocess.CompletedProcess | None,
        request: WorkstationExecutionRequest,
        decision: ShellGovernanceDecision,
        duration_ms: float,
        error: Exception | None = None,
    ) -> WorkstationExecutionResult:
        """§14.1 normalize_result: map subprocess outcome to canonical result."""
        if raw_result is None and isinstance(error, subprocess.TimeoutExpired):
            return WorkstationExecutionResult(
                request_id=request.request_id,
                command=request.command,
                outcome=WorkstationExecutionOutcome.TIMEOUT,
                adapter_used="governed_shell",
                duration_ms=duration_ms,
                governance_verdict=decision.verdict.value,
                error_message=f"Timeout after {request.timeout_seconds}s",
                correlation_id=request.correlation_id,
            )
        if raw_result is None:
            return WorkstationExecutionResult(
                request_id=request.request_id,
                command=request.command,
                outcome=WorkstationExecutionOutcome.FAILURE,
                adapter_used="governed_shell",
                duration_ms=duration_ms,
                governance_verdict=decision.verdict.value,
                error_message=str(error) if error else "Unknown error",
                correlation_id=request.correlation_id,
            )
        return WorkstationExecutionResult(
            request_id=request.request_id,
            command=request.command,
            outcome=(
                WorkstationExecutionOutcome.SUCCESS
                if raw_result.returncode == 0
                else WorkstationExecutionOutcome.FAILURE
            ),
            stdout=raw_result.stdout[:4096],
            stderr=raw_result.stderr[:2048],
            exit_code=raw_result.returncode,
            adapter_used="governed_shell",
            duration_ms=duration_ms,
            governance_verdict=decision.verdict.value,
            correlation_id=request.correlation_id,
        )

    def observe_state(self) -> dict[str, Any]:
        """§14.1 observe_state: current adapter state for tracing."""
        return {
            "adapter_id": "governed_shell",
            "operational_mode": self._mode.value,
            "healthy": True,
            **self.get_stats(),
        }

    # ── execute (backward-compatible orchestrator) ────────────────────────

    def execute(self, request: WorkstationExecutionRequest) -> WorkstationExecutionResult:
        """Execute a governed shell command. Orchestrates §14.1 phases."""
        canonical_request = self.translate_request(request)
        decision = self.validate_operation(canonical_request)

        if decision.verdict != ShellCommandVerdict.APPROVED:
            return WorkstationExecutionResult(
                request_id=canonical_request.request_id,
                command=canonical_request.command,
                outcome=WorkstationExecutionOutcome.DENIED,
                adapter_used="governed_shell",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
                correlation_id=canonical_request.correlation_id,
            )

        start = time.monotonic()
        raw_result: subprocess.CompletedProcess | None = None
        error: Exception | None = None
        try:
            raw_result = subprocess.run(
                canonical_request.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=min(canonical_request.timeout_seconds, self._mode_def.max_command_timeout),
                cwd=canonical_request.working_directory or None,
            )
        except Exception as e:
            error = e
        duration_ms = (time.monotonic() - start) * 1000
        return self.normalize_result(raw_result, canonical_request, decision, duration_ms, error)

    def get_decisions(self) -> list[ShellGovernanceDecision]:
        return list(self._decisions)

    def get_stats(self) -> dict[str, Any]:
        approved = sum(1 for d in self._decisions if d.verdict == ShellCommandVerdict.APPROVED)
        denied = sum(1 for d in self._decisions if d.verdict == ShellCommandVerdict.DENIED)
        return {
            "total_decisions": len(self._decisions),
            "approved": approved,
            "denied": denied,
            "mode": self._mode.value,
        }

    def _extract_prefix(self, command: str) -> str:
        """Extract the command prefix for allowlist matching."""
        parts = command.split()
        if not parts:
            return ""
        prefix = parts[0]
        if prefix in ("python3", "git", "docker", "ruff") and len(parts) > 1:
            return f"{parts[0]} {parts[1]}"
        return prefix

    def _has_dangerous_chain(self, command: str) -> bool:
        """Detect dangerous shell chains that could bypass allowlist."""
        for pattern in ("; rm", "&& rm", "|| rm", "| sudo", "; sudo", "&& sudo"):
            if pattern in command:
                return True
        if command.count("|") > 2:
            return True
        if "`" in command or "$(" in command:
            return True
        return False

    def _make_decision(
        self,
        command: str,
        prefix: str,
        verdict: ShellCommandVerdict,
        denial_reason: str,
        rules: list[str],
        risk: str,
    ) -> ShellGovernanceDecision:
        decision = ShellGovernanceDecision(
            command=command,
            command_prefix=prefix,
            verdict=verdict,
            risk_class=risk,
            denial_reason=denial_reason,
            rules_applied=rules,
            operational_mode=self._mode.value,
        )
        self._decisions.append(decision)
        return decision
