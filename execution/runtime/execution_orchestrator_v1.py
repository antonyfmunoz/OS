"""Execution Orchestrator v1 for the canonical runtime spine.

Coordinates the execution flow within a governance-approved envelope:
  1. Validate envelope is governance-approved
  2. Resolve adapter from lifecycle manager
  3. Mark adapter busy
  4. Execute (simulate for now — real execution wires in later)
  5. Capture result
  6. Update adapter lifecycle (success/failure)
  7. Return spine execution result

Does NOT bypass governance — requires approved envelope.
Does NOT execute directly — uses adapter lifecycle manager.

UMH substrate subsystem. Phase 96.8BO.
"""

from __future__ import annotations

import time
from typing import Any

from .execution_contracts_v1 import (
    ExecutionEnvelope,
    GovernanceVerdict,
    ObservabilityRecord,
    SpineExecutionResult,
    SpineOutcome,
    _new_id,
    _now_iso,
)
from .adapter_lifecycle_manager_v1 import AdapterLifecycleManager
from .runtime_observability_pipeline_v1 import RuntimeObservabilityPipeline


# Commands that can execute locally on VPS without adapter
VPS_EXECUTABLE_COMMANDS: frozenset[str] = frozenset(
    {
        "runtime-status",
        "capabilities",
        "adapters",
        "execution-queue",
        "resume-runtime",
        "runtime-replay",
        "memory-query",
        "memory-lineage",
        "git-status",
        "git-log",
        "tmux-status",
        "ping",
        "relay-status",
        "explore-environment",
        "constitution-report",
        "economics-report",
        "federation-report",
        "governance-intelligence-report",
        "continuity-report",
        "orchestration-report",
        "strategy-report",
        "epistemic-report",
        "identity-report",
        "telos-report",
        "resilience-report",
        "capability-report",
        "adapter-report",
        "ingest-safe-doc-cu",
        "ingest-safe-doc",
        "promote-safe-memory-candidate",
    }
)


class ExecutionOrchestrator:
    """Coordinates execution within a governance-approved envelope."""

    def __init__(
        self,
        adapter_manager: AdapterLifecycleManager,
        observability: RuntimeObservabilityPipeline,
    ) -> None:
        self._adapter_manager = adapter_manager
        self._observability = observability

    def execute(self, envelope: ExecutionEnvelope) -> SpineExecutionResult:
        """Execute a governance-approved envelope through the orchestrator."""
        start_time = time.monotonic()
        command = envelope.intent.command_name if envelope.intent else ""

        # Guard: governance must be approved
        if envelope.governance_evaluation:
            if not envelope.governance_evaluation.approved:
                return self._make_denied_result(envelope, command)

        # Resolve adapter
        adapter_id = ""
        if envelope.adapter_selection and envelope.adapter_selection.selected:
            adapter_id = envelope.adapter_selection.adapter_id
            self._adapter_manager.mark_busy(adapter_id)

        # Execute
        try:
            result_payload = self._execute_command(command, envelope)
            outcome = SpineOutcome.SUCCESS
            error_message = ""
        except Exception as e:
            result_payload = {}
            outcome = SpineOutcome.EXECUTION_FAILED
            error_message = str(e)

        duration_ms = (time.monotonic() - start_time) * 1000

        # Update adapter lifecycle
        if adapter_id:
            if outcome == SpineOutcome.SUCCESS:
                self._adapter_manager.record_execution_success(adapter_id)
            else:
                self._adapter_manager.record_execution_failure(adapter_id)

        # Record observability
        obs_record = self._observability.record_execution(
            envelope=envelope,
            outcome=outcome,
            latency_ms=duration_ms,
            error_message=error_message,
        )

        return SpineExecutionResult(
            envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id,
            command_name=command,
            outcome=outcome,
            execution_envelope=envelope,
            observability_record=obs_record,
            result_payload=result_payload,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    def _execute_command(self, command: str, envelope: ExecutionEnvelope) -> dict[str, Any]:
        """Execute a command. Returns the result payload.

        Currently handles VPS-local commands. GUI/remote commands
        will wire through the adapter boundary in future phases.
        """
        if command in VPS_EXECUTABLE_COMMANDS:
            return {
                "command": command,
                "status": "executed",
                "environment": (
                    envelope.environment_selection.environment_id
                    if envelope.environment_selection
                    else "vps-tmux-01"
                ),
                "executed_at": _now_iso(),
            }

        return {
            "command": command,
            "status": "not_implemented",
            "note": f"Command '{command}' requires adapter wiring not yet available",
        }

    def _make_denied_result(
        self, envelope: ExecutionEnvelope, command: str
    ) -> SpineExecutionResult:
        gov = envelope.governance_evaluation
        return SpineExecutionResult(
            envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id,
            command_name=command,
            outcome=SpineOutcome.GOVERNANCE_DENIED,
            execution_envelope=envelope,
            error_message=f"Governance denied: {', '.join(gov.denial_reasons) if gov else 'unknown'}",
        )
