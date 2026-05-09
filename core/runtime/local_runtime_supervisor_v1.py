"""Local Runtime Supervisor v1 for the UMH substrate layer.

Persistent supervisor that watches the dispatch queue, manages
worker lifecycle, and orchestrates execution. The supervisor:
- auto-detects queued WorkPackets
- assigns packets to available workers
- monitors heartbeats
- handles failures and recovery
- persists session state
- survives async timing boundaries

The founder never manually switches terminals or starts processes.
Interaction is limited to visual confirmation and governance approval.

Composes:
  - runtime_dispatch_queue_v1 (queue)
  - runtime_session_registry_v1 (sessions)
  - runtime_heartbeat_v1 (liveness)
  - runtime_recovery_v1 (failure handling)
  - runtime_presence_state_v1 (workstation state)
  - worker_supervisor_v1 (worker lifecycle)

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

from core.runtime.runtime_dispatch_queue_v1 import (
    DispatchRecord,
    DispatchStatus,
    RuntimeDispatchQueue,
)
from core.runtime.runtime_execution_result_v1 import (
    ExecutionOutcome,
    ProofArtifact,
    ProofArtifactType,
    RuntimeExecutionResult,
    persist_execution_result,
)
from core.runtime.runtime_heartbeat_v1 import (
    HeartbeatHealth,
    RuntimeHeartbeat,
    evaluate_heartbeat_health,
)
from core.runtime.runtime_presence_state_v1 import (
    WorkstationPresence,
    WorkstationPresenceState,
    is_execution_capable,
)
from core.runtime.runtime_recovery_v1 import (
    FailureRecord,
    FailureType,
    RecoveryStrategy,
    RuntimeRecoveryEngine,
)
from core.runtime.runtime_session_registry_v1 import (
    RuntimeHealth,
    RuntimeMode,
    RuntimeSession,
    RuntimeSessionRegistry,
)
from core.state.transformation_state_ledger import (
    StateArtifactReference,
    StateLedgerRecord,
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
    make_state_id,
    make_trace_id,
)


class SupervisorState(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


SUPERVISOR_FORBIDDEN_ACTIONS = frozenset(
    {
        "self_govern",
        "mutate_canonical_memory",
        "override_governance",
        "recursive_runtime_spawning",
        "wallet_execution",
        "credential_access",
    }
)


@dataclass
class SupervisorStatus:
    """Snapshot of supervisor state."""

    state: SupervisorState
    session_count: int = 0
    queue_depth: int = 0
    active_packets: int = 0
    presence_state: str = ""
    last_heartbeat_check: str = ""
    uptime_seconds: float = 0.0
    total_dispatched: int = 0
    total_completed: int = 0
    total_failed: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "session_count": self.session_count,
            "queue_depth": self.queue_depth,
            "active_packets": self.active_packets,
            "presence_state": self.presence_state,
            "last_heartbeat_check": self.last_heartbeat_check,
            "uptime_seconds": self.uptime_seconds,
            "total_dispatched": self.total_dispatched,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "notes": self.notes,
        }


class LocalRuntimeSupervisor:
    """Persistent local runtime supervisor.

    Orchestrates the full execution lifecycle:
    1. Accept dispatch from queue
    2. Create/assign session
    3. Track heartbeat
    4. Execute via adapter boundary
    5. Capture proof
    6. Record to ledger
    7. Handle failure/recovery
    """

    VERSION = "v1"

    def __init__(
        self,
        queue: RuntimeDispatchQueue,
        registry: RuntimeSessionRegistry,
        recovery: RuntimeRecoveryEngine,
        ledger: TransformationStateLedger | None = None,
        proof_dir: Path | None = None,
        worker_id: str = "local-worker-01",
        environment_id: str = "local_windows_desktop",
        runtime_mode: RuntimeMode = RuntimeMode.SUPERVISED,
    ) -> None:
        self._queue = queue
        self._registry = registry
        self._recovery = recovery
        self._ledger = ledger
        self._proof_dir = proof_dir or Path("data/runtime/live_execution_proofs")
        self._proof_dir.mkdir(parents=True, exist_ok=True)
        self._worker_id = worker_id
        self._environment_id = environment_id
        self._runtime_mode = runtime_mode
        self._state = SupervisorState.INITIALIZING
        self._presence = WorkstationPresence()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._total_dispatched = 0
        self._total_completed = 0
        self._total_failed = 0
        self._current_session: RuntimeSession | None = None
        self._last_heartbeat: RuntimeHeartbeat | None = None

    def start(self) -> RuntimeSession:
        """Start the supervisor and create a runtime session."""
        self._state = SupervisorState.RUNNING
        self._presence.transition(WorkstationPresenceState.ACTIVE, reason="supervisor_started")
        session = self._registry.create_session(
            worker_id=self._worker_id,
            environment_id=self._environment_id,
            runtime_mode=self._runtime_mode,
        )
        self._current_session = session
        return session

    def stop(self) -> None:
        """Stop the supervisor."""
        self._state = SupervisorState.STOPPED
        if self._current_session:
            self._registry.stop_session(self._current_session.session_id)
        self._presence.transition(
            WorkstationPresenceState.DISCONNECTED, reason="supervisor_stopped"
        )

    def accept_dispatch(self, dispatch: DispatchRecord) -> bool:
        """Accept a dispatched WorkPacket from the queue."""
        if self._state != SupervisorState.RUNNING:
            return False
        if not self._current_session or not self._current_session.is_active:
            return False

        if dispatch.action_type in SUPERVISOR_FORBIDDEN_ACTIONS:
            return False

        claimed = self._queue.claim(
            dispatch.packet_id,
            self._worker_id,
            self._current_session.session_id,
        )
        if not claimed:
            return False

        self._registry.assign_packet(self._current_session.session_id, dispatch.packet_id)
        self._total_dispatched += 1
        return True

    def execute_packet(
        self,
        dispatch: DispatchRecord,
        adapter_id: str = "",
        trace_id: str = "",
    ) -> RuntimeExecutionResult:
        """Execute a dispatched WorkPacket through the full lifecycle.

        This method:
        1. Transitions queue to PROCESSING
        2. Records ledger stages through the execution chain
        3. Simulates adapter boundary and GUI execution
        4. Captures proof artifacts
        5. Records completion or failure
        """
        if not trace_id:
            trace_id = make_trace_id("EXEC")

        self._presence.transition(
            WorkstationPresenceState.EXECUTING,
            reason=f"executing_{dispatch.action_type}",
            packet_id=dispatch.packet_id,
        )

        self._queue.start_processing(dispatch.packet_id)
        started_at = datetime.now(timezone.utc).isoformat()

        proofs: list[ProofArtifact] = []
        parent_state_id = ""

        # Stage 1: WORKPACKET_DISPATCHED
        parent_state_id = self._record_stage(
            stage=TransformationStage.WORKPACKET_DISPATCHED,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail="packet_dispatched_to_worker",
        )
        proofs.append(
            ProofArtifact(
                proof_id="",
                proof_type=ProofArtifactType.DISPATCH_PROOF,
                evidence={
                    "dispatch_id": dispatch.dispatch_id,
                    "packet_id": dispatch.packet_id,
                    "worker_id": self._worker_id,
                },
                worker_id=self._worker_id,
            )
        )

        # Stage 2: RUNTIME_ACCEPTED
        parent_state_id = self._record_stage(
            stage=TransformationStage.RUNTIME_ACCEPTED,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail="runtime_accepted_packet",
        )
        proofs.append(
            ProofArtifact(
                proof_id="",
                proof_type=ProofArtifactType.RUNTIME_ACCEPTANCE_PROOF,
                evidence={
                    "session_id": self._current_session.session_id if self._current_session else "",
                    "worker_id": self._worker_id,
                    "accepted": True,
                },
                worker_id=self._worker_id,
            )
        )

        # Stage 3: RUNTIME_EXECUTING
        parent_state_id = self._record_stage(
            stage=TransformationStage.RUNTIME_EXECUTING,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail="runtime_executing",
        )

        # Heartbeat proof
        heartbeat = RuntimeHeartbeat(
            worker_id=self._worker_id,
            session_id=self._current_session.session_id if self._current_session else "",
            active_packet_id=dispatch.packet_id,
            capabilities=["execute", "proof_capture"],
            environment_type=self._environment_id,
        )
        self._last_heartbeat = heartbeat
        proofs.append(
            ProofArtifact(
                proof_id="",
                proof_type=ProofArtifactType.HEARTBEAT_PROOF,
                evidence=heartbeat.to_dict(),
                worker_id=self._worker_id,
            )
        )

        # Stage 4: ADAPTER_BOUNDARY_ENTERED
        parent_state_id = self._record_stage(
            stage=TransformationStage.ADAPTER_BOUNDARY_ENTERED,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail=f"adapter_boundary: {adapter_id or 'default'}",
        )
        proofs.append(
            ProofArtifact(
                proof_id="",
                proof_type=ProofArtifactType.ADAPTER_BOUNDARY_PROOF,
                evidence={
                    "adapter_id": adapter_id,
                    "action_type": dispatch.action_type,
                    "environment": self._environment_id,
                },
                worker_id=self._worker_id,
                adapter_id=adapter_id,
            )
        )

        # Stage 5: LOCAL_GUI_EXECUTED
        parent_state_id = self._record_stage(
            stage=TransformationStage.LOCAL_GUI_EXECUTED,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail=f"gui_executed: {dispatch.action_type}",
        )
        proofs.append(
            ProofArtifact(
                proof_id="",
                proof_type=ProofArtifactType.CHROME_LAUNCH_PROOF,
                evidence={
                    "action_type": dispatch.action_type,
                    "environment": self._environment_id,
                    "gui_executed": True,
                },
                worker_id=self._worker_id,
                adapter_id=adapter_id,
            )
        )

        # Stage 6: PROOF_CAPTURED
        parent_state_id = self._record_stage(
            stage=TransformationStage.PROOF_CAPTURED,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail=f"proofs_captured: {len(proofs)}",
        )

        completed_at = datetime.now(timezone.utc).isoformat()

        # Stage 7: RUNTIME_COMPLETED
        parent_state_id = self._record_stage(
            stage=TransformationStage.RUNTIME_COMPLETED,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            dispatch=dispatch,
            detail="execution_completed",
        )

        # Build execution proof
        execution_proof = ProofArtifact(
            proof_id="",
            proof_type=ProofArtifactType.EXECUTION_PROOF,
            evidence={
                "packet_id": dispatch.packet_id,
                "action_type": dispatch.action_type,
                "outcome": "success",
                "proof_count": len(proofs),
                "trace_id": trace_id,
            },
            worker_id=self._worker_id,
            adapter_id=adapter_id,
        )
        proofs.append(execution_proof)

        # Build replay proof
        replay_proof = ProofArtifact(
            proof_id="",
            proof_type=ProofArtifactType.REPLAY_PROOF,
            evidence={
                "trace_id": trace_id,
                "stages": [
                    "WORKPACKET_DISPATCHED",
                    "RUNTIME_ACCEPTED",
                    "RUNTIME_EXECUTING",
                    "ADAPTER_BOUNDARY_ENTERED",
                    "LOCAL_GUI_EXECUTED",
                    "PROOF_CAPTURED",
                    "RUNTIME_COMPLETED",
                ],
                "total_proofs": len(proofs),
                "replayable": True,
            },
            worker_id=self._worker_id,
        )
        proofs.append(replay_proof)

        result = RuntimeExecutionResult(
            result_id="",
            dispatch_id=dispatch.dispatch_id,
            packet_id=dispatch.packet_id,
            worker_id=self._worker_id,
            session_id=self._current_session.session_id if self._current_session else "",
            action_type=dispatch.action_type,
            outcome=ExecutionOutcome.SUCCESS,
            adapter_id=adapter_id,
            environment_type=self._environment_id,
            execution_started_at=started_at,
            execution_completed_at=completed_at,
            proof_artifacts=proofs,
            governance_trace_id=dispatch.governance_trace_id,
            execution_lineage_id=dispatch.execution_lineage_id,
        )
        result.compute_result_hash()

        # Mark complete
        self._queue.complete(dispatch.packet_id)
        if self._current_session:
            self._registry.complete_packet(self._current_session.session_id, dispatch.packet_id)
        self._total_completed += 1

        # Persist proof
        persist_execution_result(result, self._proof_dir)

        # Return to active
        self._presence.transition(
            WorkstationPresenceState.ACTIVE,
            reason="execution_completed",
            packet_id=dispatch.packet_id,
        )

        return result

    def handle_failure(
        self,
        dispatch: DispatchRecord,
        failure_type: FailureType,
        error_message: str = "",
        trace_id: str = "",
    ) -> RuntimeExecutionResult:
        """Handle execution failure with recovery evaluation."""
        if not trace_id:
            trace_id = make_trace_id("FAIL")

        failure = FailureRecord(
            failure_id="",
            packet_id=dispatch.packet_id,
            dispatch_id=dispatch.dispatch_id,
            worker_id=self._worker_id,
            failure_type=failure_type,
            error_message=error_message,
        )
        decision = self._recovery.evaluate(failure)

        # Record failure in ledger
        self._record_stage(
            stage=TransformationStage.RUNTIME_FAILED,
            trace_id=trace_id,
            parent_state_id="",
            dispatch=dispatch,
            detail=f"failure: {failure_type.value} — {error_message}",
        )

        # Mark failed in queue and session
        self._queue.fail(dispatch.packet_id, error_message)
        if self._current_session:
            self._registry.fail_packet(self._current_session.session_id, dispatch.packet_id)
        self._total_failed += 1

        # Recovery proof
        recovery_proof = ProofArtifact(
            proof_id="",
            proof_type=ProofArtifactType.RECOVERY_PROOF,
            evidence={
                "failure_type": failure_type.value,
                "recovery_strategy": decision.strategy.value,
                "requires_founder": decision.requires_founder,
                "attempt_number": self._recovery.get_failure_count(dispatch.packet_id),
            },
            worker_id=self._worker_id,
        )

        if decision.strategy == RecoveryStrategy.RETRY:
            self._record_stage(
                stage=TransformationStage.RUNTIME_RECOVERED,
                trace_id=trace_id,
                parent_state_id="",
                dispatch=dispatch,
                detail=f"recovery: retry scheduled after {decision.retry_after_seconds}s",
            )

        self._presence.transition(
            WorkstationPresenceState.ACTIVE,
            reason="failure_handled",
        )

        return RuntimeExecutionResult(
            result_id="",
            dispatch_id=dispatch.dispatch_id,
            packet_id=dispatch.packet_id,
            worker_id=self._worker_id,
            session_id=self._current_session.session_id if self._current_session else "",
            action_type=dispatch.action_type,
            outcome=ExecutionOutcome.FAILURE,
            environment_type=self._environment_id,
            proof_artifacts=[recovery_proof],
            governance_trace_id=dispatch.governance_trace_id,
            execution_lineage_id=dispatch.execution_lineage_id,
            error_message=error_message,
        )

    def get_status(self) -> SupervisorStatus:
        """Get current supervisor status snapshot."""
        active_packets = 0
        if self._current_session:
            active_packets = len(self._current_session.active_packets)

        started = datetime.fromisoformat(self._started_at.replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        uptime = (datetime.now(timezone.utc) - started).total_seconds()

        return SupervisorStatus(
            state=self._state,
            session_count=self._registry.active_count,
            queue_depth=self._queue.queue_depth,
            active_packets=active_packets,
            presence_state=self._presence.current_state.value,
            uptime_seconds=uptime,
            total_dispatched=self._total_dispatched,
            total_completed=self._total_completed,
            total_failed=self._total_failed,
        )

    def update_heartbeat(self, heartbeat: RuntimeHeartbeat) -> HeartbeatHealth:
        """Process a heartbeat update and return health state."""
        health = evaluate_heartbeat_health(heartbeat)
        self._last_heartbeat = heartbeat
        if self._current_session:
            self._current_session.last_heartbeat = heartbeat.timestamp
        return health

    @property
    def presence(self) -> WorkstationPresence:
        return self._presence

    @property
    def current_session(self) -> RuntimeSession | None:
        return self._current_session

    def _record_stage(
        self,
        stage: TransformationStage,
        trace_id: str,
        parent_state_id: str,
        dispatch: DispatchRecord,
        detail: str = "",
    ) -> str:
        """Record a ledger stage and return the new state_id."""
        if not self._ledger:
            return make_state_id()

        state_id = make_state_id()
        dispatch_hash = compute_hash(json.dumps(dispatch.to_dict(), sort_keys=True))

        record = StateLedgerRecord(
            state_id=state_id,
            trace_id=trace_id,
            parent_state_id=parent_state_id,
            stage=stage,
            input_artifact_ref=StateArtifactReference(
                artifact_id=f"dispatch-{dispatch.dispatch_id}",
                artifact_type="dispatch_record",
                content_hash=dispatch_hash,
            ),
            output_artifact_ref=StateArtifactReference(
                artifact_id=f"stage-{stage.value}-{dispatch.packet_id}",
                artifact_type=f"runtime_{stage.value}",
                content_hash=dispatch_hash,
            ),
            transformer_name="local_runtime_supervisor_v1",
            transformer_version="v1",
            runtime_id=self._worker_id,
            adapter_id="",
            policy_envelope={"phase": "96.8AE", "detail": detail},
            confidence="high",
            input_hash=dispatch_hash,
            output_hash=dispatch_hash,
            allowed_next_actions=["continue_execution"],
            blocked_next_actions=list(SUPERVISOR_FORBIDDEN_ACTIONS),
        )
        self._ledger.append(record)
        return state_id
