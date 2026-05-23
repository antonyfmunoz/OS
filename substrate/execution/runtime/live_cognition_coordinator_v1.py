"""Live Cognition Coordinator v1.

Coordinates the cognitive phase of runtime spine traversal:
  - interpret signal into command/intent
  - decompose complex signals into steps
  - retrieve relevant memory context
  - retrieve continuity context (open loops, resume state)
  - expand domain context
  - produce a runtime execution plan

The cognition coordinator does NOT execute.
It only produces plans and context for the execution coordinator.

UMH substrate subsystem.
"""

from __future__ import annotations

from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeDecision,
    RuntimeDecisionType,
    RuntimeExecutionPlan,
    RuntimeExecutionStep,
    RuntimeLineageReceipt,
    RuntimePhase,
    RuntimeSignal,
    RuntimeStepType,
    _content_hash,
    _new_id,
    _now_iso,
)


KNOWN_STEP_TYPES: dict[str, RuntimeStepType] = {
    "shell": RuntimeStepType.SHELL,
    "browser": RuntimeStepType.BROWSER,
    "gui": RuntimeStepType.GUI,
    "tmux": RuntimeStepType.TMUX,
    "memory": RuntimeStepType.MEMORY,
    "report": RuntimeStepType.REPORT,
    "inspect": RuntimeStepType.INSPECT,
}

WORKSTATION_COMMANDS: frozenset[str] = frozenset(
    {
        "workstation-status",
        "tmux-status",
        "runtime-sessions",
        "resume-work",
        "operational-state",
        "environment-health",
        "replay-validate",
        "execution-history",
        "mode-info",
    }
)

BROWSER_COMMANDS: frozenset[str] = frozenset(
    {
        "browser-status",
        "browser-tabs",
        "browser-inspect",
        "browser-summary",
        "gui-state",
        "visible-actuation-log",
    }
)

RUNTIME_COMMANDS: frozenset[str] = frozenset(
    {
        "runtime-status",
        "runtime-lineage",
        "runtime-open-loops",
        "runtime-resume",
        "runtime-observe",
        "runtime-replay",
        "runtime-governance",
        "runtime-context",
    }
)


class LiveCognitionCoordinator:
    """Coordinates cognition: interpretation, planning, context retrieval.

    Does NOT execute. Produces RuntimeContext and RuntimeExecutionPlan
    for the execution coordinator to carry out.
    """

    def __init__(self) -> None:
        self._interpretations: int = 0
        self._plans_created: int = 0
        self._memory_retrievals: int = 0
        self._continuity_retrievals: int = 0

    def interpret(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
    ) -> RuntimeContext:
        """Interpret a signal into command name, intent type, and domain."""
        raw = signal.raw_input.strip().lstrip("!")
        parts = raw.split(maxsplit=1)
        command_name = parts[0] if parts else raw
        args_str = parts[1] if len(parts) > 1 else ""

        context.command_name = command_name
        if args_str:
            context.command_args = {"raw_args": args_str}

        context.intent_type = self._classify_intent(command_name)
        context.domain = self._resolve_domain(command_name)
        context.current_phase = RuntimePhase.COGNITION

        decision = RuntimeDecision(
            decision_type=RuntimeDecisionType.ROUTE,
            phase=RuntimePhase.COGNITION,
            input_summary=f"signal:{signal.raw_input}",
            output_summary=f"command:{command_name} intent:{context.intent_type} domain:{context.domain}",
            rules_applied=["interpret_signal"],
            approved=True,
            correlation_id=context.correlation_id,
        )
        context.add_decision(decision)

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.COGNITION,
            action="interpret",
            component="cognition_coordinator",
            input_hash=signal.content_hash(),
            output_hash=context.content_hash(),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        self._interpretations += 1
        return context

    def retrieve_memory_context(
        self,
        context: RuntimeContext,
        memory_entries: list[dict[str, Any]] | None = None,
    ) -> RuntimeContext:
        """Attach relevant memory context to the runtime context."""
        context.memory_context = memory_entries or []
        self._memory_retrievals += 1
        return context

    def retrieve_continuity_context(
        self,
        context: RuntimeContext,
        continuity_state: dict[str, Any] | None = None,
        open_loops: list[dict[str, Any]] | None = None,
    ) -> RuntimeContext:
        """Attach continuity state and open loops to the runtime context."""
        context.continuity_context = continuity_state or {}
        context.open_loops = open_loops or []
        self._continuity_retrievals += 1
        return context

    def create_plan(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
    ) -> RuntimeExecutionPlan:
        """Create an execution plan from interpreted context.

        Single-command signals produce a single-step plan.
        The cognition coordinator does not decompose into
        multi-step plans autonomously — that requires explicit
        step definitions from the caller.
        """
        plan = RuntimeExecutionPlan(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            embodiment_path=context.embodiment_path
            or self._resolve_embodiment(context.command_name),
        )

        step_type = self._resolve_step_type(context.command_name, context.domain)
        step = RuntimeExecutionStep(
            step_index=0,
            step_type=step_type,
            command=context.command_name,
            target=context.command_args.get("raw_args", ""),
            adapter=self._resolve_adapter(step_type),
            environment=context.environment_resolved or "vps_local",
            risk_class=context.risk_class,
        )
        plan.steps.append(step)
        plan.finalize()

        decision = RuntimeDecision(
            decision_type=RuntimeDecisionType.PLAN,
            phase=RuntimePhase.PLANNING,
            input_summary=f"command:{context.command_name} domain:{context.domain}",
            output_summary=f"plan:{plan.plan_id} steps:{plan.total_steps} embodiment:{plan.embodiment_path}",
            rules_applied=["single_command_plan"],
            approved=True,
            correlation_id=context.correlation_id,
        )
        context.add_decision(decision)

        receipt = RuntimeLineageReceipt(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            phase=RuntimePhase.PLANNING,
            action="create_plan",
            component="cognition_coordinator",
            input_hash=context.content_hash(),
            output_hash=plan.content_hash(),
        )
        context.add_lineage_receipt(receipt.receipt_id)

        self._plans_created += 1
        return plan

    def create_multi_step_plan(
        self,
        signal: RuntimeSignal,
        context: RuntimeContext,
        steps: list[dict[str, Any]],
    ) -> RuntimeExecutionPlan:
        """Create a multi-step plan from explicit step definitions."""
        plan = RuntimeExecutionPlan(
            signal_id=signal.signal_id,
            correlation_id=context.correlation_id,
            embodiment_path=context.embodiment_path or "multi_step",
        )

        for i, step_def in enumerate(steps):
            step_type_str = step_def.get("step_type", "inspect")
            step_type = KNOWN_STEP_TYPES.get(step_type_str, RuntimeStepType.INSPECT)
            step = RuntimeExecutionStep(
                step_index=i,
                step_type=step_type,
                command=step_def.get("command", ""),
                target=step_def.get("target", ""),
                adapter=step_def.get("adapter", self._resolve_adapter(step_type)),
                environment=step_def.get("environment", "vps_local"),
                risk_class=step_def.get("risk_class", "safe"),
            )
            plan.steps.append(step)

        plan.finalize()
        self._plans_created += 1
        return plan

    def get_stats(self) -> dict[str, Any]:
        return {
            "interpretations": self._interpretations,
            "plans_created": self._plans_created,
            "memory_retrievals": self._memory_retrievals,
            "continuity_retrievals": self._continuity_retrievals,
        }

    def _classify_intent(self, command_name: str) -> str:
        if command_name in RUNTIME_COMMANDS | WORKSTATION_COMMANDS | BROWSER_COMMANDS:
            return "query"
        if command_name.startswith("report-") or command_name.endswith("-report"):
            return "report"
        if command_name.startswith("ingest-"):
            return "ingestion"
        return "command"

    def _resolve_domain(self, command_name: str) -> str:
        if command_name in WORKSTATION_COMMANDS:
            return "workstation"
        if command_name in BROWSER_COMMANDS:
            return "browser"
        if command_name in RUNTIME_COMMANDS:
            return "runtime"
        if command_name.startswith("ingest-"):
            return "ingestion"
        if command_name.startswith("memory-"):
            return "memory"
        return "general"

    def _resolve_embodiment(self, command_name: str) -> str:
        if command_name in WORKSTATION_COMMANDS:
            return "workstation"
        if command_name in BROWSER_COMMANDS:
            return "browser"
        if command_name in RUNTIME_COMMANDS:
            return "runtime"
        return "spine"

    def _resolve_step_type(self, command_name: str, domain: str) -> RuntimeStepType:
        if domain == "workstation":
            if "tmux" in command_name:
                return RuntimeStepType.TMUX
            return RuntimeStepType.SHELL
        if domain == "browser":
            if "gui" in command_name:
                return RuntimeStepType.GUI
            return RuntimeStepType.BROWSER
        if domain == "memory":
            return RuntimeStepType.MEMORY
        if command_name.startswith("report-") or command_name.endswith("-report"):
            return RuntimeStepType.REPORT
        return RuntimeStepType.INSPECT

    def _resolve_adapter(self, step_type: RuntimeStepType) -> str:
        adapters: dict[RuntimeStepType, str] = {
            RuntimeStepType.SHELL: "governed_shell",
            RuntimeStepType.BROWSER: "governed_browser",
            RuntimeStepType.GUI: "visible_gui",
            RuntimeStepType.TMUX: "tmux_operational",
            RuntimeStepType.MEMORY: "memory_store",
            RuntimeStepType.REPORT: "report_generator",
            RuntimeStepType.INSPECT: "runtime_inspector",
        }
        return adapters.get(step_type, "runtime_inspector")
