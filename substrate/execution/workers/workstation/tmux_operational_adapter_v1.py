"""Tmux Operational Adapter v1.

Governed tmux interaction adapter. Inspects sessions, panes,
and running commands. Can create controlled sessions and send
approved commands through the governed shell adapter.

NOT allowed:
  - arbitrary shell escalation
  - destructive commands via send-keys
  - hidden background loops
  - unmonitored session creation

UMH substrate subsystem.
"""

from __future__ import annotations

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
    WorkstationSession,
    _new_id,
    _now_iso,
)
from .workstation_operational_modes_v1 import get_mode_definition
from .governed_shell_adapter_v1 import GovernedShellAdapter


@dataclass
class TmuxGovernanceDecision:
    """Record of a tmux operation governance decision."""

    decision_id: str = ""
    operation: str = ""
    target_session: str = ""
    verdict: ShellCommandVerdict = ShellCommandVerdict.DENIED
    denial_reason: str = ""
    rules_applied: list[str] = field(default_factory=list)
    operational_mode: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("tmuxdec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "operation": self.operation,
            "target_session": self.target_session,
            "verdict": self.verdict.value,
            "denial_reason": self.denial_reason,
            "rules_applied": self.rules_applied,
            "operational_mode": self.operational_mode,
            "timestamp": self.timestamp,
        }


def _run_tmux(args: list[str], timeout: int = 5) -> tuple[str, str, int]:
    """Run a tmux command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            ["tmux"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "tmux not found", 127
    except subprocess.TimeoutExpired:
        return "", "tmux command timed out", 124


class TmuxOperationalAdapter:
    """Governed tmux interaction adapter."""

    def __init__(
        self,
        operational_mode: OperationalMode = OperationalMode.DEVELOPER,
        shell_adapter: GovernedShellAdapter | None = None,
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_mode_definition(operational_mode)
        self._shell = shell_adapter or GovernedShellAdapter(operational_mode)
        self._decisions: list[TmuxGovernanceDecision] = []

    def set_mode(self, mode: OperationalMode) -> None:
        self._mode = mode
        self._mode_def = get_mode_definition(mode)
        self._shell.set_mode(mode)

    def list_sessions(self) -> list[WorkstationSession]:
        """List active tmux sessions."""
        decision = self._evaluate("list-sessions", "")
        if decision.verdict != ShellCommandVerdict.APPROVED:
            return []

        stdout, stderr, rc = _run_tmux(
            ["list-sessions", "-F", "#{session_name}:#{session_created}:#{session_windows}"]
        )
        if rc != 0:
            return []

        sessions = []
        for line in stdout.strip().splitlines():
            parts = line.split(":", 2)
            name = parts[0] if parts else "unknown"
            sessions.append(
                WorkstationSession(
                    session_name=name,
                    session_type="tmux",
                    is_active=True,
                    started_at=parts[1] if len(parts) > 1 else "",
                )
            )
        return sessions

    def list_panes(self, session_name: str = "") -> list[dict[str, Any]]:
        """List panes in a tmux session."""
        decision = self._evaluate("list-panes", session_name)
        if decision.verdict != ShellCommandVerdict.APPROVED:
            return []

        args = ["list-panes", "-F", "#{pane_index}:#{pane_current_command}:#{pane_current_path}"]
        if session_name:
            args.extend(["-t", session_name])
        else:
            args.append("-a")

        stdout, stderr, rc = _run_tmux(args)
        if rc != 0:
            return []

        panes = []
        for line in stdout.strip().splitlines():
            parts = line.split(":", 2)
            panes.append(
                {
                    "pane_index": parts[0] if parts else "",
                    "current_command": parts[1] if len(parts) > 1 else "",
                    "current_path": parts[2] if len(parts) > 2 else "",
                }
            )
        return panes

    def inspect_session(self, session_name: str) -> WorkstationSession | None:
        """Get detailed info about a specific session."""
        decision = self._evaluate("display-message", session_name)
        if decision.verdict != ShellCommandVerdict.APPROVED:
            return None

        panes = self.list_panes(session_name)
        stdout, _, rc = _run_tmux(
            ["display-message", "-t", session_name, "-p", "#{session_name}:#{session_created}"]
        )
        if rc != 0:
            return None

        parts = stdout.strip().split(":", 1)
        return WorkstationSession(
            session_name=parts[0] if parts else session_name,
            session_type="tmux",
            panes=panes,
            is_active=True,
            started_at=parts[1] if len(parts) > 1 else "",
        )

    def send_approved_command(
        self, session_name: str, command: str
    ) -> WorkstationExecutionResult:
        """Send a governed command to a tmux session via send-keys."""
        # First: governance on tmux send-keys operation
        tmux_decision = self._evaluate("send-keys", session_name)
        if tmux_decision.verdict != ShellCommandVerdict.APPROVED:
            return WorkstationExecutionResult(
                command=command,
                outcome=WorkstationExecutionOutcome.DENIED,
                adapter_used="tmux",
                governance_verdict=tmux_decision.verdict.value,
                error_message=tmux_decision.denial_reason,
            )

        # Second: governance on the actual command content
        shell_decision = self._shell.evaluate_command(command)
        if shell_decision.verdict != ShellCommandVerdict.APPROVED:
            return WorkstationExecutionResult(
                command=command,
                outcome=WorkstationExecutionOutcome.DENIED,
                adapter_used="tmux+shell",
                governance_verdict=shell_decision.verdict.value,
                error_message=shell_decision.denial_reason,
            )

        start = time.monotonic()
        stdout, stderr, rc = _run_tmux(
            ["send-keys", "-t", session_name, command, "Enter"]
        )
        duration_ms = (time.monotonic() - start) * 1000

        return WorkstationExecutionResult(
            command=command,
            outcome=(
                WorkstationExecutionOutcome.SUCCESS
                if rc == 0
                else WorkstationExecutionOutcome.FAILURE
            ),
            stdout=stdout[:2048],
            stderr=stderr[:1024],
            exit_code=rc,
            adapter_used="tmux",
            duration_ms=duration_ms,
            governance_verdict=shell_decision.verdict.value,
        )

    def get_decisions(self) -> list[TmuxGovernanceDecision]:
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

    def _evaluate(self, operation: str, target_session: str) -> TmuxGovernanceDecision:
        """Evaluate whether a tmux operation is allowed."""
        rules: list[str] = []

        if not self._mode_def.allows_tmux(operation):
            rules.append("MODE_TMUX_DENIED")
            decision = TmuxGovernanceDecision(
                operation=operation,
                target_session=target_session,
                verdict=ShellCommandVerdict.DENIED,
                denial_reason=f"Tmux operation '{operation}' not allowed in {self._mode.value}",
                rules_applied=rules,
                operational_mode=self._mode.value,
            )
            self._decisions.append(decision)
            return decision

        rules.append("TMUX_ALLOWLIST_APPROVED")
        decision = TmuxGovernanceDecision(
            operation=operation,
            target_session=target_session,
            verdict=ShellCommandVerdict.APPROVED,
            rules_applied=rules,
            operational_mode=self._mode.value,
        )
        self._decisions.append(decision)
        return decision
