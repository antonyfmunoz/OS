"""Live Execution Coordinator v1.

Coordinates execution across governed adapters:
  - shell embodiment (via WorkstationEmbodimentEngine)
  - browser embodiment (via BrowserGUIEmbodimentEngine)
  - GUI embodiment (via BrowserGUIEmbodimentEngine)
  - tmux embodiment (via WorkstationEmbodimentEngine)
  - runtime commands (direct dispatch)

The execution coordinator cannot execute directly.
It only coordinates governed adapters through their engines.

UMH substrate subsystem. Phase 96.8BR.
"""

from __future__ import annotations

import time
from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeDecision,
    RuntimeDecisionType,
    RuntimeExecutionPlan,
    RuntimeExecutionStep,
    RuntimeLineageReceipt,
    RuntimeOutcome,
    RuntimeOutcomeStatus,
    RuntimePhase,
    RuntimeSignal,
    RuntimeStepType,
    _content_hash,
    _new_id,
)
try:
    from substrate.execution.workers.workstation.workstation_operational_embodiment_engine_v1 import (
        WorkstationOperationalEmbodimentEngine,
    )
except ModuleNotFoundError:
    WorkstationOperationalEmbodimentEngine = None  # type: ignore[assignment,misc]

try:
    from substrate.execution.workers.workstation.browser_gui_embodiment_engine_v1 import (
        BrowserGUIEmbodimentEngine,
    )
except ModuleNotFoundError:
    BrowserGUIEmbodimentEngine = None  # type: ignore[assignment,misc]


class LiveExecutionCoordinator:
    """Coordinates execution across governed embodiment engines.

    Cannot execute directly — only dispatches through
    WorkstationEmbodimentEngine and BrowserGUIEmbodimentEngine.
    """

    def __init__(
        self,
        workstation_engine: WorkstationOperationalEmbodimentEngine | None = None,
        browser_engine: BrowserGUIEmbodimentEngine | None = None,
    ) -> None:
        if workstation_engine is not None:
            self._workstation = workstation_engine
        elif WorkstationOperationalEmbodimentEngine is not None:
            self._workstation = WorkstationOperationalEmbodimentEngine()
        else:
            self._workstation = None
        if browser_engine is not None:
            self._browser = browser_engine
        elif BrowserGUIEmbodimentEngine is not None:
            self._browser = BrowserGUIEmbodimentEngine()
        else:
            self._browser = None
        self._executions: int = 0
        self._successes: int = 0
        self._denials: int = 0
        self._failures: int = 0

    def execute_plan(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        plan: RuntimeExecutionPlan,
    ) -> RuntimeOutcome:
        """Execute a runtime execution plan through governed adapters."""
        start = time.monotonic()
        context.current_phase = RuntimePhase.EXECUTION

        steps_completed = 0
        last_result: dict[str, Any] = {}
        last_error = ""

        for step in plan.steps:
            step_result = self._execute_step(step, context)
            step.completed = step_result.get("succeeded", False)
            step.result_summary = step_result.get("summary", "")
            step.error_message = step_result.get("error", "")
            step.duration_ms = step_result.get("duration_ms", 0.0)

            if step.completed:
                steps_completed += 1
                last_result = step_result
            else:
                last_error = step.error_message
                break

        duration_ms = (time.monotonic() - start) * 1000
        all_completed = steps_completed == len(plan.steps)

        if all_completed:
            status = RuntimeOutcomeStatus.SUCCESS
            self._successes += 1
        elif last_error and "denied" in last_error.lower():
            status = RuntimeOutcomeStatus.DENIED
            self._denials += 1
        else:
            status = RuntimeOutcomeStatus.FAILED
            self._failures += 1

        self._executions += 1

        decision = RuntimeDecision(
            decision_type=RuntimeDecisionType.EXECUTE,
            phase=RuntimePhase.EXECUTION,
            input_summary=f"plan:{plan.plan_id} steps:{plan.total_steps}",
            output_summary=f"completed:{steps_completed}/{plan.total_steps} status:{status.value}",
            rules_applied=["governed_execution"],
            approved=all_completed,
            denial_reason=last_error if not all_completed else "",
            correlation_id=context.correlation_id,
        )
        context.add_decision(decision)

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.EXECUTION,
            action="execute_plan",
            component="execution_coordinator",
            input_hash=plan.content_hash(),
            output_hash=_content_hash({"status": status.value, "steps_completed": steps_completed}),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        return RuntimeOutcome(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            session_id=context.session_id,
            status=status,
            command_name=context.command_name,
            embodiment_path=plan.embodiment_path,
            steps_completed=steps_completed,
            steps_total=plan.total_steps,
            governance_verdict=context.governance_verdict,
            governance_rules=context.governance_rules,
            result_data=last_result,
            error_message=last_error,
            duration_ms=duration_ms,
            lineage_receipts=list(context.lineage_receipts),
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "executions": self._executions,
            "successes": self._successes,
            "denials": self._denials,
            "failures": self._failures,
        }

    def _execute_step(
        self,
        step: RuntimeExecutionStep,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Execute a single step through the appropriate embodiment engine."""
        start = time.monotonic()

        if step.step_type in (RuntimeStepType.SHELL, RuntimeStepType.TMUX):
            result = self._dispatch_workstation(step, context)
        elif step.step_type in (RuntimeStepType.BROWSER, RuntimeStepType.GUI):
            result = self._dispatch_browser(step, context)
        elif step.step_type == RuntimeStepType.INSPECT:
            result = self._dispatch_runtime_inspect(step, context)
        elif step.step_type == RuntimeStepType.MEMORY:
            result = self._dispatch_memory(step, context)
        elif step.step_type == RuntimeStepType.REPORT:
            result = self._dispatch_report(step, context)
        else:
            result = {
                "succeeded": False,
                "error": f"Unknown step type: {step.step_type.value}",
                "summary": "",
            }

        result["duration_ms"] = (time.monotonic() - start) * 1000
        return result

    def _dispatch_workstation(
        self,
        step: RuntimeExecutionStep,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Dispatch to workstation embodiment engine."""
        result = self._workstation.dispatch_command(step.command)
        succeeded = "error" not in result
        return {
            "succeeded": succeeded,
            "summary": f"workstation:{step.command}",
            "error": result.get("error", ""),
            "data": result,
        }

    def _dispatch_browser(
        self,
        step: RuntimeExecutionStep,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Dispatch to browser/GUI embodiment engine."""
        result = self._browser.dispatch_command(step.command)
        succeeded = "error" not in result
        return {
            "succeeded": succeeded,
            "summary": f"browser:{step.command}",
            "error": result.get("error", ""),
            "data": result,
        }

    def _dispatch_runtime_inspect(
        self,
        step: RuntimeExecutionStep,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Dispatch runtime inspection commands."""
        return {
            "succeeded": True,
            "summary": f"runtime_inspect:{step.command}",
            "data": {
                "command": step.command,
                "context_id": context.context_id,
                "session_id": context.session_id,
            },
        }

    def _dispatch_memory(
        self,
        step: RuntimeExecutionStep,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Dispatch memory operations."""
        return {
            "succeeded": True,
            "summary": f"memory:{step.command}",
            "data": {"command": step.command, "memory_context_count": len(context.memory_context)},
        }

    def _dispatch_report(
        self,
        step: RuntimeExecutionStep,
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """Dispatch report generation."""
        return {
            "succeeded": True,
            "summary": f"report:{step.command}",
            "data": {"command": step.command},
        }
