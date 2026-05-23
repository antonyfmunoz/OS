"""Workstation Execution Orchestrator v1.

Coordinates workstation execution through the governed pipeline:
  1. Receive execution request
  2. Evaluate governance (shell adapter)
  3. Route to adapter (shell or tmux)
  4. Capture result
  5. Record observability
  6. Bridge continuity
  7. Preserve replay determinism

No adapter can be called directly from outside this orchestrator.

UMH substrate subsystem.
"""

from __future__ import annotations

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
from .governed_shell_adapter_v1 import GovernedShellAdapter
from .tmux_operational_adapter_v1 import TmuxOperationalAdapter
from .workstation_observability_pipeline_v1 import (
    WorkstationObservabilityPipeline,
)
from .workstation_continuity_bridge_v1 import (
    WorkstationContinuityBridge,
)
from .workstation_operational_modes_v1 import get_mode_definition


class WorkstationExecutionOrchestrator:
    """Coordinates governed workstation execution through a single pipeline."""

    def __init__(
        self,
        operational_mode: OperationalMode = OperationalMode.DEVELOPER,
        shell_adapter: GovernedShellAdapter | None = None,
        tmux_adapter: TmuxOperationalAdapter | None = None,
        observability: WorkstationObservabilityPipeline | None = None,
        continuity: WorkstationContinuityBridge | None = None,
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_mode_definition(operational_mode)
        self._shell = shell_adapter or GovernedShellAdapter(operational_mode)
        self._tmux = tmux_adapter or TmuxOperationalAdapter(operational_mode, self._shell)
        self._observability = observability or WorkstationObservabilityPipeline()
        self._continuity = continuity or WorkstationContinuityBridge()

        self._total_executions = 0
        self._total_successes = 0
        self._total_denials = 0
        self._total_failures = 0

    def set_mode(self, mode: OperationalMode) -> None:
        """Change operational mode across all adapters."""
        old_mode = self._mode
        self._mode = mode
        self._mode_def = get_mode_definition(mode)
        self._shell.set_mode(mode)
        self._tmux.set_mode(mode)
        self._continuity.bridge_mode_transition(old_mode, mode)

    def execute(self, request: WorkstationExecutionRequest) -> WorkstationExecutionResult:
        """Execute a workstation command through the governed pipeline."""
        self._total_executions += 1

        # Step 1: Governance evaluation
        decision = self._shell.evaluate_command(request.command)

        # Step 2: If denied, short-circuit
        if decision.verdict != ShellCommandVerdict.APPROVED:
            self._total_denials += 1
            result = WorkstationExecutionResult(
                request_id=request.request_id,
                command=request.command,
                outcome=WorkstationExecutionOutcome.DENIED,
                adapter_used="none",
                governance_verdict=decision.verdict.value,
                error_message=decision.denial_reason,
                correlation_id=request.correlation_id,
            )
            self._record(request, result, decision.rules_applied)
            return result

        # Step 3: Route to adapter
        if request.adapter_type == "tmux" and request.target_session:
            result = self._execute_tmux(request)
        else:
            result = self._execute_shell(request)

        # Step 4: Update counters
        if result.succeeded:
            self._total_successes += 1
        else:
            self._total_failures += 1

        # Step 5: Record observability + continuity
        self._record(request, result, decision.rules_applied)

        return result

    def execute_shell(self, command: str, **kwargs: Any) -> WorkstationExecutionResult:
        """Convenience: execute a shell command."""
        request = WorkstationExecutionRequest(
            command=command,
            adapter_type="shell",
            operational_mode=self._mode,
            **kwargs,
        )
        return self.execute(request)

    def execute_tmux(
        self, command: str, session_name: str, **kwargs: Any
    ) -> WorkstationExecutionResult:
        """Convenience: execute a command in a tmux session."""
        request = WorkstationExecutionRequest(
            command=command,
            adapter_type="tmux",
            target_session=session_name,
            operational_mode=self._mode,
            **kwargs,
        )
        return self.execute(request)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_executions": self._total_executions,
            "total_successes": self._total_successes,
            "total_denials": self._total_denials,
            "total_failures": self._total_failures,
            "success_rate": (
                self._total_successes / self._total_executions
                if self._total_executions > 0
                else 0.0
            ),
            "operational_mode": self._mode.value,
            "shell_stats": self._shell.get_stats(),
            "tmux_stats": self._tmux.get_stats(),
            "observability_stats": self._observability.get_stats(),
            "continuity_stats": self._continuity.get_stats(),
        }

    def _execute_shell(self, request: WorkstationExecutionRequest) -> WorkstationExecutionResult:
        """Execute through the governed shell adapter."""
        result = self._shell.execute(request)
        result.adapter_used = "governed_shell"
        return result

    def _execute_tmux(self, request: WorkstationExecutionRequest) -> WorkstationExecutionResult:
        """Execute through the tmux adapter."""
        if not self._mode_def.allows_adapter("tmux"):
            return WorkstationExecutionResult(
                request_id=request.request_id,
                command=request.command,
                outcome=WorkstationExecutionOutcome.DENIED,
                adapter_used="tmux",
                governance_verdict="denied",
                error_message=f"Tmux adapter not allowed in {self._mode.value}",
                correlation_id=request.correlation_id,
            )
        return self._tmux.send_approved_command(request.target_session, request.command)

    def _record(
        self,
        request: WorkstationExecutionRequest,
        result: WorkstationExecutionResult,
        governance_rules: list[str] | None = None,
    ) -> None:
        """Record execution to observability and continuity."""
        self._observability.record_execution(request, result)
        self._continuity.bridge_execution(result, governance_rules)
        if result.governance_verdict:
            self._continuity.bridge_governance_decision(
                command=request.command,
                verdict=result.governance_verdict,
                rules_applied=governance_rules or [],
                risk_class=request.risk_class,
                denial_reason=result.error_message if not result.succeeded else "",
            )
