"""Live Local Runtime Execution v1 for the UMH substrate layer.

The complete governed execution spine:
  Discord intent → Control Plane → Governance → WorkPacket
  → Local Runtime Supervisor → Local Worker Runtime
  → Adapter Boundary → Real Local GUI Execution
  → Proof → Trace → Replay

This module is the single entry point for dispatching governed
work to the local runtime. It composes all prior substrate layers
into an operational execution loop.

UMH substrate subsystem. Phase 96.8AE.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from core.execution.workpacket_execution_gate_v1 import (
    ExecutionGateResult,
    GateVerdict,
    RuntimeExecutionRequest,
    WorkPacketExecutionGate,
)
from governance.policy.execution_authority_engine_v1 import (
    AuthorityClass,
    AuthorityDecision,
    ExecutionAuthorityEngine,
    ExecutionAuthorityRequest,
)
from core.runtime.local_runtime_supervisor_v1 import (
    LocalRuntimeSupervisor,
    SupervisorState,
)
from core.runtime.runtime_dispatch_queue_v1 import (
    DispatchRecord,
    RuntimeDispatchQueue,
)
from core.runtime.runtime_execution_result_v1 import (
    ExecutionOutcome,
    RuntimeExecutionResult,
)
from core.runtime.node_sync_gate_v1 import (
    NodeSyncGate,
    NodeSyncGateResult,
    SyncDecision,
)
from core.runtime.runtime_recovery_v1 import (
    FailureType,
    RuntimeRecoveryEngine,
)
from core.runtime.runtime_session_registry_v1 import (
    RuntimeMode,
    RuntimeSessionRegistry,
)
from state.transformation_state_ledger import (
    TransformationStateLedger,
    make_trace_id,
)


class ExecutionSpineOutcome(str, Enum):
    SUCCESS = "success"
    AUTHORITY_DENIED = "authority_denied"
    GATE_DENIED = "gate_denied"
    NODE_SYNC_DENIED = "node_sync_denied"
    SUPERVISOR_UNAVAILABLE = "supervisor_unavailable"
    EXECUTION_FAILED = "execution_failed"
    GOVERNANCE_BLOCKED = "governance_blocked"


SPINE_FORBIDDEN_ACTIONS = frozenset(
    {
        "wallet_execution",
        "financial_execution",
        "credential_access",
        "recursive_runtime_spawning",
        "canonical_mutation_without_governance",
        "self_govern",
    }
)


@dataclass
class ExecutionSpineResult:
    """Complete result of an end-to-end governed execution."""

    spine_id: str
    packet_id: str
    action_type: str
    outcome: ExecutionSpineOutcome
    authority_decision: AuthorityDecision | None = None
    gate_result: ExecutionGateResult | None = None
    sync_gate_result: NodeSyncGateResult | None = None
    execution_result: RuntimeExecutionResult | None = None
    trace_id: str = ""
    timestamp: str = ""
    denial_reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.spine_id:
            self.spine_id = f"SPINE-{uuid.uuid4().hex[:8]}"

    @property
    def succeeded(self) -> bool:
        return self.outcome == ExecutionSpineOutcome.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "spine_id": self.spine_id,
            "packet_id": self.packet_id,
            "action_type": self.action_type,
            "outcome": self.outcome.value,
            "succeeded": self.succeeded,
            "authority_decision": (
                self.authority_decision.to_dict() if self.authority_decision else None
            ),
            "gate_result": self.gate_result.to_dict() if self.gate_result else None,
            "sync_gate_result": (
                self.sync_gate_result.to_dict() if self.sync_gate_result else None
            ),
            "execution_result": (
                self.execution_result.to_dict() if self.execution_result else None
            ),
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "denial_reasons": self.denial_reasons,
            "notes": self.notes,
        }


class LiveLocalRuntimeExecution:
    """End-to-end governed execution from intent to proof.

    Flow:
    1. Authority evaluation (can this action execute?)
    2. Gate validation (is the environment ready?)
    3. Dispatch to queue
    4. Supervisor accepts and executes
    5. Proof artifacts generated
    6. Ledger trace persisted
    7. Result returned
    """

    VERSION = "v1"

    def __init__(
        self,
        authority_engine: ExecutionAuthorityEngine,
        gate: WorkPacketExecutionGate,
        queue: RuntimeDispatchQueue,
        supervisor: LocalRuntimeSupervisor,
        ledger: TransformationStateLedger | None = None,
        proof_dir: Path | None = None,
        sync_gate: NodeSyncGate | None = None,
    ) -> None:
        self._authority = authority_engine
        self._gate = gate
        self._queue = queue
        self._supervisor = supervisor
        self._ledger = ledger
        self._sync_gate = sync_gate
        self._proof_dir = proof_dir or Path("data/runtime/live_execution_proofs")
        self._proof_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        packet_id: str,
        action_type: str,
        action_description: str = "",
        target_environment: str = "local_windows_desktop",
        target_runtime: str = "local-worker-01",
        required_adapter_id: str = "",
        required_capability: str = "",
        blocked_actions: list[str] | None = None,
        proof_requirements: list[str] | None = None,
        timeout_seconds: int = 300,
        confidence: float = 0.9,
        trace_id: str = "",
    ) -> ExecutionSpineResult:
        """Execute a governed action through the full spine."""
        if not trace_id:
            trace_id = make_trace_id("SPINE")

        _blocked = blocked_actions or list(SPINE_FORBIDDEN_ACTIONS)
        _proofs = proof_requirements or [
            "dispatch_proof",
            "execution_proof",
            "adapter_boundary_proof",
        ]

        # Structural pre-check
        if action_type in SPINE_FORBIDDEN_ACTIONS:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.GOVERNANCE_BLOCKED,
                trace_id=trace_id,
                denial_reasons=[f"structurally_forbidden: {action_type}"],
            )

        # Step 1: Authority evaluation
        auth_request = ExecutionAuthorityRequest(
            request_id=f"auth-{packet_id}",
            action_type=action_type,
            action_description=action_description or f"Execute {action_type}",
            required_environment_type=target_environment,
            required_adapter_id=required_adapter_id,
            confidence=confidence,
            proof_requirements=_proofs,
        )
        auth_decision = self._authority.evaluate(auth_request)

        if auth_decision.authority_class == AuthorityClass.DENY:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.AUTHORITY_DENIED,
                authority_decision=auth_decision,
                trace_id=trace_id,
                denial_reasons=auth_decision.denial_reasons,
            )

        # Step 2: Gate validation
        governance_trace_id = trace_id
        execution_lineage_id = f"lineage-{trace_id}"

        gate_result = self._gate.validate(
            packet_id=packet_id,
            action_type=action_type,
            authority_decision=auth_decision,
            target_environment=target_environment,
            target_runtime=target_runtime,
            required_adapter_id=required_adapter_id,
            required_capability=required_capability,
            blocked_actions=_blocked,
            proof_requirements=_proofs,
            timeout_seconds=timeout_seconds,
            governance_trace_id=governance_trace_id,
            execution_lineage_id=execution_lineage_id,
            trace_id=trace_id,
        )

        if gate_result.verdict == GateVerdict.DENY:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.GATE_DENIED,
                authority_decision=auth_decision,
                gate_result=gate_result,
                trace_id=trace_id,
                denial_reasons=gate_result.denial_reasons,
            )

        # Step 2b: Node sync gate (if configured)
        sync_gate_result: NodeSyncGateResult | None = None
        if self._sync_gate:
            sync_gate_result = self._sync_gate.validate(
                requested_command=action_type,
                requested_capability=action_type,
                trace_id=trace_id,
            )
            if not sync_gate_result.passed:
                return ExecutionSpineResult(
                    spine_id="",
                    packet_id=packet_id,
                    action_type=action_type,
                    outcome=ExecutionSpineOutcome.NODE_SYNC_DENIED,
                    authority_decision=auth_decision,
                    gate_result=gate_result,
                    sync_gate_result=sync_gate_result,
                    trace_id=trace_id,
                    denial_reasons=sync_gate_result.denial_reasons,
                )

        # Step 3: Dispatch to queue
        dispatch = DispatchRecord(
            dispatch_id="",
            packet_id=packet_id,
            action_type=action_type,
            target_environment=target_environment,
            target_runtime=target_runtime,
            authority_class=auth_decision.authority_class.value,
            governance_trace_id=governance_trace_id,
            execution_lineage_id=execution_lineage_id,
            blocked_actions=_blocked,
            proof_requirements=_proofs,
            timeout_seconds=timeout_seconds,
        )

        enqueued = self._queue.enqueue(dispatch)
        if not enqueued:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.EXECUTION_FAILED,
                authority_decision=auth_decision,
                gate_result=gate_result,
                trace_id=trace_id,
                denial_reasons=["dispatch_queue_rejected_duplicate"],
            )

        # Step 4: Supervisor accepts
        accepted = self._supervisor.accept_dispatch(dispatch)
        if not accepted:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.SUPERVISOR_UNAVAILABLE,
                authority_decision=auth_decision,
                gate_result=gate_result,
                trace_id=trace_id,
                denial_reasons=["supervisor_unavailable_or_stopped"],
            )

        # Step 5: Execute
        exec_result = self._supervisor.execute_packet(
            dispatch=dispatch,
            adapter_id=required_adapter_id or "default_adapter",
            trace_id=trace_id,
        )

        # Step 6: Persist spine result
        spine_result = ExecutionSpineResult(
            spine_id="",
            packet_id=packet_id,
            action_type=action_type,
            outcome=(
                ExecutionSpineOutcome.SUCCESS
                if exec_result.succeeded
                else ExecutionSpineOutcome.EXECUTION_FAILED
            ),
            authority_decision=auth_decision,
            gate_result=gate_result,
            sync_gate_result=sync_gate_result,
            execution_result=exec_result,
            trace_id=trace_id,
        )

        # Persist spine proof
        proof_path = self._proof_dir / f"{spine_result.spine_id}.json"
        proof_path.write_text(json.dumps(spine_result.to_dict(), indent=2, default=str))

        return spine_result

    def execute_with_failure(
        self,
        packet_id: str,
        action_type: str,
        failure_type: FailureType,
        error_message: str = "",
        target_environment: str = "local_windows_desktop",
        target_runtime: str = "local-worker-01",
        blocked_actions: list[str] | None = None,
        proof_requirements: list[str] | None = None,
        timeout_seconds: int = 300,
        confidence: float = 0.9,
        trace_id: str = "",
    ) -> ExecutionSpineResult:
        """Execute through authority and gate, then simulate failure for recovery testing."""
        if not trace_id:
            trace_id = make_trace_id("FAIL-SPINE")

        _blocked = blocked_actions or list(SPINE_FORBIDDEN_ACTIONS)
        _proofs = proof_requirements or ["dispatch_proof", "recovery_proof"]

        auth_request = ExecutionAuthorityRequest(
            request_id=f"auth-fail-{packet_id}",
            action_type=action_type,
            action_description=f"Execute {action_type} (failure test)",
            required_environment_type=target_environment,
            confidence=confidence,
            proof_requirements=_proofs,
        )
        auth_decision = self._authority.evaluate(auth_request)

        if auth_decision.authority_class == AuthorityClass.DENY:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.AUTHORITY_DENIED,
                authority_decision=auth_decision,
                trace_id=trace_id,
                denial_reasons=auth_decision.denial_reasons,
            )

        gate_result = self._gate.validate(
            packet_id=packet_id,
            action_type=action_type,
            authority_decision=auth_decision,
            target_environment=target_environment,
            target_runtime=target_runtime,
            blocked_actions=_blocked,
            proof_requirements=_proofs,
            timeout_seconds=timeout_seconds,
            governance_trace_id=trace_id,
            execution_lineage_id=f"lineage-{trace_id}",
            trace_id=trace_id,
        )

        if gate_result.verdict == GateVerdict.DENY:
            return ExecutionSpineResult(
                spine_id="",
                packet_id=packet_id,
                action_type=action_type,
                outcome=ExecutionSpineOutcome.GATE_DENIED,
                authority_decision=auth_decision,
                gate_result=gate_result,
                trace_id=trace_id,
                denial_reasons=gate_result.denial_reasons,
            )

        dispatch = DispatchRecord(
            dispatch_id="",
            packet_id=packet_id,
            action_type=action_type,
            target_environment=target_environment,
            target_runtime=target_runtime,
            authority_class=auth_decision.authority_class.value,
            governance_trace_id=trace_id,
            execution_lineage_id=f"lineage-{trace_id}",
            blocked_actions=_blocked,
            proof_requirements=_proofs,
            timeout_seconds=timeout_seconds,
        )

        self._queue.enqueue(dispatch)
        self._supervisor.accept_dispatch(dispatch)
        self._queue.start_processing(dispatch.packet_id)

        fail_result = self._supervisor.handle_failure(
            dispatch=dispatch,
            failure_type=failure_type,
            error_message=error_message,
            trace_id=trace_id,
        )

        return ExecutionSpineResult(
            spine_id="",
            packet_id=packet_id,
            action_type=action_type,
            outcome=ExecutionSpineOutcome.EXECUTION_FAILED,
            authority_decision=auth_decision,
            gate_result=gate_result,
            execution_result=fail_result,
            trace_id=trace_id,
            denial_reasons=[error_message] if error_message else [],
        )
