"""Tests for Phase 96.8AE — Live Local Runtime Execution.

Covers:
  - runtime queue routing
  - supervisor lifecycle
  - worker restart
  - heartbeat timeout
  - runtime replay
  - deterministic dispatch
  - proof generation
  - dispatch idempotency
  - runtime recovery
  - async execution continuity
  - workstation presence transitions
  - end-to-end spine execution
  - ledger stage persistence
  - session registry
"""

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from core.runtime.runtime_heartbeat_v1 import (
    HeartbeatHealth,
    RuntimeHeartbeat,
    evaluate_heartbeat_health,
    read_runtime_heartbeat,
    write_runtime_heartbeat,
)
from core.runtime.runtime_presence_state_v1 import (
    WorkstationPresence,
    WorkstationPresenceState,
    is_execution_capable,
)
from core.runtime.runtime_session_registry_v1 import (
    RuntimeHealth,
    RuntimeMode,
    RuntimeSession,
    RuntimeSessionRegistry,
)
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
from core.runtime.runtime_recovery_v1 import (
    FailureRecord,
    FailureType,
    RecoveryStrategy,
    RuntimeRecoveryEngine,
)
from core.runtime.local_runtime_supervisor_v1 import (
    LocalRuntimeSupervisor,
    SupervisorState,
)
from core.runtime.live_local_runtime_execution_v1 import (
    ExecutionSpineOutcome,
    LiveLocalRuntimeExecution,
    SPINE_FORBIDDEN_ACTIONS,
)
from governance.policy.execution_authority_engine_v1 import (
    AuthorityClass,
    CapabilityAuthority,
    EnvironmentAuthority,
    ExecutionAuthorityEngine,
    RiskClass,
)
from core.execution.workpacket_execution_gate_v1 import (
    WorkPacketExecutionGate,
)
from state.transformation_state_ledger import (
    TransformationStage,
    TransformationStateLedger,
)


# -- Fixtures --


def _make_queue(tmp: Path) -> RuntimeDispatchQueue:
    return RuntimeDispatchQueue(tmp / "queue")


def _make_registry() -> RuntimeSessionRegistry:
    return RuntimeSessionRegistry()


def _make_recovery() -> RuntimeRecoveryEngine:
    return RuntimeRecoveryEngine(max_retries=3)


def _make_ledger(tmp: Path) -> TransformationStateLedger:
    return TransformationStateLedger(tmp / "ledger")


def _make_supervisor(
    tmp: Path,
    ledger: TransformationStateLedger | None = None,
) -> LocalRuntimeSupervisor:
    queue = _make_queue(tmp)
    registry = _make_registry()
    recovery = _make_recovery()
    return LocalRuntimeSupervisor(
        queue=queue,
        registry=registry,
        recovery=recovery,
        ledger=ledger,
        proof_dir=tmp / "proofs",
        worker_id="test-worker",
        environment_id="local_windows_desktop",
    )


def _make_dispatch(
    packet_id: str = "WP-test-001",
    action_type: str = "browser_execution",
) -> DispatchRecord:
    return DispatchRecord(
        dispatch_id="",
        packet_id=packet_id,
        action_type=action_type,
        target_environment="local_windows_desktop",
        target_runtime="test-worker",
        authority_class="supervised_execute",
        governance_trace_id="TRACE-test",
        execution_lineage_id="LINEAGE-test",
        blocked_actions=["wallet_execution"],
        proof_requirements=["dispatch_proof", "execution_proof"],
        timeout_seconds=300,
    )


def _make_spine(tmp: Path) -> LiveLocalRuntimeExecution:
    env_auth = EnvironmentAuthority(
        environment_type="local_windows_desktop",
        can_own_gui=True,
        can_own_local_shell=True,
        can_execute_browser=True,
        max_risk_class=RiskClass.MEDIUM,
    )
    cap_auth = CapabilityAuthority(
        adapter_id="chrome_adapter",
        capabilities=["browser_execution", "chrome_launch"],
        is_configured=True,
        is_mature=True,
    )
    authority = ExecutionAuthorityEngine(
        environment_authorities=[env_auth],
        capability_authorities=[cap_auth],
    )
    ledger = _make_ledger(tmp)
    gate = WorkPacketExecutionGate(
        environment_authorities={"local_windows_desktop": env_auth},
        capability_authorities={"chrome_adapter": cap_auth},
        available_runtimes={"local-worker-01": True},
        ledger=ledger,
        proof_dir=tmp / "gate_proofs",
    )
    queue = _make_queue(tmp)
    registry = _make_registry()
    recovery = _make_recovery()
    supervisor = LocalRuntimeSupervisor(
        queue=queue,
        registry=registry,
        recovery=recovery,
        ledger=ledger,
        proof_dir=tmp / "exec_proofs",
        worker_id="local-worker-01",
        environment_id="local_windows_desktop",
    )
    supervisor.start()
    return LiveLocalRuntimeExecution(
        authority_engine=authority,
        gate=gate,
        queue=queue,
        supervisor=supervisor,
        ledger=ledger,
        proof_dir=tmp / "spine_proofs",
    )


# ========================================================
# Test: Runtime Queue Routing
# ========================================================


class TestRuntimeQueueRouting:
    def test_enqueue_creates_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = _make_queue(Path(tmp))
            dispatch = _make_dispatch()
            result = queue.enqueue(dispatch)
            assert result is not None
            assert result.status == DispatchStatus.QUEUED

    def test_dequeue_returns_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = _make_queue(Path(tmp))
            queue.enqueue(_make_dispatch("WP-1"))
            queue.enqueue(_make_dispatch("WP-2"))
            queued = queue.get_queued()
            assert len(queued) == 2

    def test_claim_transitions_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = _make_queue(Path(tmp))
            dispatch = _make_dispatch()
            queue.enqueue(dispatch)
            claimed = queue.claim(dispatch.packet_id, "worker-1")
            assert claimed
            record = queue.get_record(dispatch.packet_id)
            assert record.status == DispatchStatus.CLAIMED


# ========================================================
# Test: Supervisor Lifecycle
# ========================================================


class TestSupervisorLifecycle:
    def test_start_creates_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            session = sv.start()
            assert session is not None
            assert session.is_active

    def test_stop_ends_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            session = sv.start()
            sv.stop()
            status = sv.get_status()
            assert status.state == SupervisorState.STOPPED

    def test_status_reflects_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            status = sv.get_status()
            assert status.state == SupervisorState.RUNNING
            assert status.presence_state == "active"


# ========================================================
# Test: Worker Restart / Recovery
# ========================================================


class TestWorkerRestart:
    def test_worker_crash_requeues(self):
        engine = _make_recovery()
        failure = FailureRecord(
            failure_id="",
            packet_id="WP-crash",
            dispatch_id="D-1",
            worker_id="w1",
            failure_type=FailureType.WORKER_CRASH,
        )
        decision = engine.evaluate(failure)
        assert decision.strategy == RecoveryStrategy.REQUEUE

    def test_timeout_retries(self):
        engine = _make_recovery()
        failure = FailureRecord(
            failure_id="",
            packet_id="WP-timeout",
            dispatch_id="D-2",
            worker_id="w1",
            failure_type=FailureType.TIMEOUT,
        )
        decision = engine.evaluate(failure)
        assert decision.strategy == RecoveryStrategy.RETRY

    def test_max_retries_abandons(self):
        engine = RuntimeRecoveryEngine(max_retries=1)
        for i in range(3):
            failure = FailureRecord(
                failure_id="",
                packet_id="WP-exhaust",
                dispatch_id=f"D-{i}",
                worker_id="w1",
                failure_type=FailureType.TIMEOUT,
            )
            decision = engine.evaluate(failure)
        assert decision.strategy == RecoveryStrategy.ABANDON


# ========================================================
# Test: Heartbeat Timeout
# ========================================================


class TestHeartbeatTimeout:
    def test_fresh_heartbeat_alive(self):
        hb = RuntimeHeartbeat(worker_id="w1")
        health = evaluate_heartbeat_health(hb)
        assert health == HeartbeatHealth.ALIVE

    def test_stale_heartbeat_degraded(self):
        ts = (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat()
        hb = RuntimeHeartbeat(worker_id="w1", timestamp=ts)
        health = evaluate_heartbeat_health(hb)
        assert health == HeartbeatHealth.DEGRADED

    def test_old_heartbeat_timeout(self):
        ts = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        hb = RuntimeHeartbeat(worker_id="w1", timestamp=ts)
        health = evaluate_heartbeat_health(hb)
        assert health == HeartbeatHealth.TIMEOUT

    def test_empty_heartbeat_dead(self):
        hb = RuntimeHeartbeat(worker_id="w1")
        hb.timestamp = ""
        health = evaluate_heartbeat_health(hb)
        assert health == HeartbeatHealth.DEAD

    def test_heartbeat_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "heartbeat.json"
            hb = RuntimeHeartbeat(
                worker_id="w1",
                session_id="s1",
                capabilities=["execute"],
            )
            assert write_runtime_heartbeat(path, hb)
            loaded = read_runtime_heartbeat(path)
            assert loaded is not None
            assert loaded.worker_id == "w1"


# ========================================================
# Test: Runtime Replay
# ========================================================


class TestRuntimeReplay:
    def test_ledger_trace_reconstructable(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = _make_ledger(Path(tmp))
            sv = _make_supervisor(Path(tmp), ledger=ledger)
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch, trace_id="TRACE-replay-test")
            trace = ledger.get_trace("TRACE-replay-test")
            assert len(trace) >= 7

    def test_replay_proof_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch)
            replay_proofs = [
                p for p in result.proof_artifacts if p.proof_type == ProofArtifactType.REPLAY_PROOF
            ]
            assert len(replay_proofs) == 1
            assert replay_proofs[0].evidence["replayable"] is True


# ========================================================
# Test: Deterministic Dispatch
# ========================================================


class TestDeterministicDispatch:
    def test_same_packet_same_hash(self):
        d1 = _make_dispatch("WP-det-1")
        d2 = DispatchRecord(
            dispatch_id="",
            packet_id="WP-det-1",
            action_type="browser_execution",
            target_environment="local_windows_desktop",
            target_runtime="test-worker",
        )
        assert d1.dispatch_hash == d2.dispatch_hash

    def test_different_packets_different_hash(self):
        d1 = _make_dispatch("WP-A")
        d2 = _make_dispatch("WP-B")
        assert d1.dispatch_hash != d2.dispatch_hash


# ========================================================
# Test: Proof Generation
# ========================================================


class TestProofGeneration:
    def test_execution_generates_all_proof_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch)
            assert result.proof_count >= 7

    def test_proof_types_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch)
            types = {p.proof_type for p in result.proof_artifacts}
            assert ProofArtifactType.DISPATCH_PROOF in types
            assert ProofArtifactType.EXECUTION_PROOF in types
            assert ProofArtifactType.ADAPTER_BOUNDARY_PROOF in types
            assert ProofArtifactType.CHROME_LAUNCH_PROOF in types
            assert ProofArtifactType.HEARTBEAT_PROOF in types
            assert ProofArtifactType.REPLAY_PROOF in types
            assert ProofArtifactType.RUNTIME_ACCEPTANCE_PROOF in types

    def test_proof_persisted_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch)
            proof_files = list((Path(tmp) / "proofs").glob("*.json"))
            assert len(proof_files) >= 1

    def test_result_hash_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch)
            assert result.result_hash
            assert len(result.result_hash) == 64


# ========================================================
# Test: Dispatch Idempotency
# ========================================================


class TestDispatchIdempotency:
    def test_duplicate_packet_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = _make_queue(Path(tmp))
            d1 = _make_dispatch("WP-dup")
            d2 = _make_dispatch("WP-dup")
            assert queue.enqueue(d1) is not None
            assert queue.enqueue(d2) is None

    def test_different_packets_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = _make_queue(Path(tmp))
            assert queue.enqueue(_make_dispatch("WP-A")) is not None
            assert queue.enqueue(_make_dispatch("WP-B")) is not None


# ========================================================
# Test: Runtime Recovery
# ========================================================


class TestRuntimeRecovery:
    def test_connectivity_loss_retries(self):
        engine = _make_recovery()
        failure = FailureRecord(
            failure_id="",
            packet_id="WP-conn",
            dispatch_id="D-1",
            worker_id="w1",
            failure_type=FailureType.CONNECTIVITY_LOSS,
        )
        decision = engine.evaluate(failure)
        assert decision.strategy == RecoveryStrategy.RETRY
        assert decision.retry_after_seconds > 0

    def test_governance_block_escalates(self):
        engine = _make_recovery()
        failure = FailureRecord(
            failure_id="",
            packet_id="WP-gov",
            dispatch_id="D-1",
            worker_id="w1",
            failure_type=FailureType.GOVERNANCE_BLOCK,
        )
        decision = engine.evaluate(failure)
        assert decision.strategy == RecoveryStrategy.ESCALATE
        assert decision.requires_founder

    def test_adapter_failure_retries_then_escalates(self):
        engine = _make_recovery()
        f1 = FailureRecord(
            failure_id="",
            packet_id="WP-adapt",
            dispatch_id="D-1",
            worker_id="w1",
            failure_type=FailureType.ADAPTER_FAILURE,
        )
        d1 = engine.evaluate(f1)
        assert d1.strategy == RecoveryStrategy.RETRY

        f2 = FailureRecord(
            failure_id="",
            packet_id="WP-adapt",
            dispatch_id="D-2",
            worker_id="w1",
            failure_type=FailureType.ADAPTER_FAILURE,
        )
        d2 = engine.evaluate(f2)
        assert d2.strategy == RecoveryStrategy.ESCALATE

    def test_failure_history_tracked(self):
        engine = _make_recovery()
        for i in range(3):
            engine.record_failure(
                FailureRecord(
                    failure_id="",
                    packet_id="WP-hist",
                    dispatch_id=f"D-{i}",
                    worker_id="w1",
                    failure_type=FailureType.TIMEOUT,
                )
            )
        assert engine.get_failure_count("WP-hist") == 3

    def test_supervisor_failure_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            sv._queue.start_processing(dispatch.packet_id)
            result = sv.handle_failure(
                dispatch,
                FailureType.TIMEOUT,
                "connection_timeout",
            )
            assert result.outcome == ExecutionOutcome.FAILURE
            assert len(result.proof_artifacts) >= 1


# ========================================================
# Test: Async Execution Continuity
# ========================================================


class TestAsyncExecutionContinuity:
    def test_session_survives_multiple_packets(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            session = sv.start()
            for i in range(3):
                d = _make_dispatch(f"WP-multi-{i}")
                sv._queue.enqueue(d)
                sv.accept_dispatch(d)
                sv.execute_packet(d)
            assert session.is_active
            assert len(session.completed_packets) == 3

    def test_presence_transitions_during_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            assert sv.presence.current_state == WorkstationPresenceState.ACTIVE
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            sv.execute_packet(dispatch)
            assert sv.presence.current_state == WorkstationPresenceState.ACTIVE
            assert len(sv.presence.history) >= 3

    def test_registry_tracks_all_sessions(self):
        registry = _make_registry()
        s1 = registry.create_session("w1", "env1")
        s2 = registry.create_session("w2", "env2")
        assert registry.session_count == 2
        assert registry.active_count == 2
        registry.stop_session(s1.session_id)
        assert registry.active_count == 1


# ========================================================
# Test: Workstation Presence Transitions
# ========================================================


class TestWorkstationPresenceTransitions:
    def test_valid_transitions(self):
        p = WorkstationPresence()
        assert p.current_state == WorkstationPresenceState.DISCONNECTED
        assert p.transition(WorkstationPresenceState.ACTIVE) is not None
        assert p.transition(WorkstationPresenceState.EXECUTING) is not None
        assert p.transition(WorkstationPresenceState.ACTIVE) is not None

    def test_invalid_transition_returns_none(self):
        p = WorkstationPresence()
        result = p.transition(WorkstationPresenceState.EXECUTING)
        assert result is None
        assert p.current_state == WorkstationPresenceState.DISCONNECTED

    def test_history_tracked(self):
        p = WorkstationPresence()
        p.transition(WorkstationPresenceState.ACTIVE)
        p.transition(WorkstationPresenceState.IDLE)
        p.transition(WorkstationPresenceState.EXECUTING)
        assert len(p.history) == 3

    def test_is_execution_capable(self):
        assert is_execution_capable(WorkstationPresenceState.ACTIVE)
        assert is_execution_capable(WorkstationPresenceState.IDLE)
        assert is_execution_capable(WorkstationPresenceState.EXECUTING)
        assert not is_execution_capable(WorkstationPresenceState.DISCONNECTED)
        assert not is_execution_capable(WorkstationPresenceState.RECOVERING)


# ========================================================
# Test: Session Registry
# ========================================================


class TestSessionRegistry:
    def test_create_and_get_session(self):
        registry = _make_registry()
        session = registry.create_session("w1", "env1")
        found = registry.get_session(session.session_id)
        assert found is not None
        assert found.worker_id == "w1"

    def test_assign_and_complete_packet(self):
        registry = _make_registry()
        session = registry.create_session("w1", "env1")
        registry.assign_packet(session.session_id, "WP-1")
        assert "WP-1" in session.active_packets
        registry.complete_packet(session.session_id, "WP-1")
        assert "WP-1" not in session.active_packets
        assert "WP-1" in session.completed_packets

    def test_fail_packet(self):
        registry = _make_registry()
        session = registry.create_session("w1", "env1")
        registry.assign_packet(session.session_id, "WP-2")
        registry.fail_packet(session.session_id, "WP-2")
        assert "WP-2" in session.failed_packets

    def test_stop_session(self):
        registry = _make_registry()
        session = registry.create_session("w1", "env1")
        assert session.is_active
        registry.stop_session(session.session_id)
        assert not session.is_active

    def test_get_sessions_for_worker(self):
        registry = _make_registry()
        registry.create_session("w1", "env1")
        registry.create_session("w1", "env2")
        registry.create_session("w2", "env3")
        w1_sessions = registry.get_sessions_for_worker("w1")
        assert len(w1_sessions) == 2


# ========================================================
# Test: End-to-End Spine Execution
# ========================================================


class TestEndToEndSpine:
    def test_full_spine_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            spine = _make_spine(Path(tmp))
            result = spine.execute(
                packet_id="WP-spine-001",
                action_type="browser_execution",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="chrome_adapter",
                required_capability="browser_execution",
            )
            assert result.succeeded
            assert result.outcome == ExecutionSpineOutcome.SUCCESS
            assert result.authority_decision is not None
            assert result.gate_result is not None
            assert result.execution_result is not None
            assert result.execution_result.proof_count >= 7

    def test_forbidden_action_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            spine = _make_spine(Path(tmp))
            result = spine.execute(
                packet_id="WP-forbidden",
                action_type="wallet_execution",
            )
            assert not result.succeeded
            assert result.outcome == ExecutionSpineOutcome.GOVERNANCE_BLOCKED

    def test_spine_with_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            spine = _make_spine(Path(tmp))
            result = spine.execute_with_failure(
                packet_id="WP-fail-test",
                action_type="browser_execution",
                failure_type=FailureType.TIMEOUT,
                error_message="connection_timed_out",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
            )
            assert not result.succeeded
            assert result.outcome == ExecutionSpineOutcome.EXECUTION_FAILED
            assert result.execution_result is not None

    def test_spine_proof_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            spine = _make_spine(Path(tmp))
            result = spine.execute(
                packet_id="WP-persist-001",
                action_type="browser_execution",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="chrome_adapter",
                required_capability="browser_execution",
            )
            spine_proofs = list((Path(tmp) / "spine_proofs").glob("*.json"))
            assert len(spine_proofs) >= 1


# ========================================================
# Test: Ledger Stage Persistence
# ========================================================


class TestLedgerStagePersistence:
    def test_execution_records_all_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = _make_ledger(Path(tmp))
            sv = _make_supervisor(Path(tmp), ledger=ledger)
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            result = sv.execute_packet(dispatch, trace_id="TRACE-ledger-test")
            trace = ledger.get_trace("TRACE-ledger-test")
            stages = [r.stage for r in trace]
            assert TransformationStage.WORKPACKET_DISPATCHED in stages
            assert TransformationStage.RUNTIME_ACCEPTED in stages
            assert TransformationStage.RUNTIME_EXECUTING in stages
            assert TransformationStage.ADAPTER_BOUNDARY_ENTERED in stages
            assert TransformationStage.LOCAL_GUI_EXECUTED in stages
            assert TransformationStage.PROOF_CAPTURED in stages
            assert TransformationStage.RUNTIME_COMPLETED in stages

    def test_failure_records_failed_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = _make_ledger(Path(tmp))
            sv = _make_supervisor(Path(tmp), ledger=ledger)
            sv.start()
            dispatch = _make_dispatch()
            sv._queue.enqueue(dispatch)
            sv.accept_dispatch(dispatch)
            sv._queue.start_processing(dispatch.packet_id)
            sv.handle_failure(
                dispatch,
                FailureType.WORKER_CRASH,
                "crash",
                trace_id="TRACE-fail-test",
            )
            trace = ledger.get_trace("TRACE-fail-test")
            stages = [r.stage for r in trace]
            assert TransformationStage.RUNTIME_FAILED in stages

    def test_new_stages_in_valid_transitions(self):
        from state.transformation_state_ledger import VALID_TRANSITIONS

        new_stages = [
            TransformationStage.WORKPACKET_DISPATCHED,
            TransformationStage.RUNTIME_ACCEPTED,
            TransformationStage.RUNTIME_EXECUTING,
            TransformationStage.ADAPTER_BOUNDARY_ENTERED,
            TransformationStage.LOCAL_GUI_EXECUTED,
            TransformationStage.PROOF_CAPTURED,
            TransformationStage.RUNTIME_COMPLETED,
            TransformationStage.RUNTIME_FAILED,
            TransformationStage.RUNTIME_RECOVERED,
        ]
        for stage in new_stages:
            assert stage in VALID_TRANSITIONS, f"{stage} not in VALID_TRANSITIONS"


# ========================================================
# Test: Execution Result Dataclasses
# ========================================================


class TestExecutionResultDataclasses:
    def test_execution_result_to_dict(self):
        result = RuntimeExecutionResult(
            result_id="",
            dispatch_id="D-1",
            packet_id="WP-1",
            worker_id="w1",
            session_id="s1",
            action_type="browser_execution",
            outcome=ExecutionOutcome.SUCCESS,
        )
        d = result.to_dict()
        assert d["outcome"] == "success"
        assert d["succeeded"] is True

    def test_proof_artifact_hash(self):
        proof = ProofArtifact(
            proof_id="",
            proof_type=ProofArtifactType.DISPATCH_PROOF,
            evidence={"key": "value"},
        )
        assert proof.content_hash
        assert len(proof.content_hash) == 64

    def test_result_hash_deterministic(self):
        r1 = RuntimeExecutionResult(
            result_id="R1",
            dispatch_id="D-1",
            packet_id="WP-1",
            worker_id="w1",
            session_id="s1",
            action_type="test",
            outcome=ExecutionOutcome.SUCCESS,
        )
        r2 = RuntimeExecutionResult(
            result_id="R1",
            dispatch_id="D-1",
            packet_id="WP-1",
            worker_id="w1",
            session_id="s1",
            action_type="test",
            outcome=ExecutionOutcome.SUCCESS,
        )
        r1.compute_result_hash()
        r2.compute_result_hash()
        assert r1.result_hash == r2.result_hash

    def test_persist_result_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RuntimeExecutionResult(
                result_id="R-persist",
                dispatch_id="D-1",
                packet_id="WP-1",
                worker_id="w1",
                session_id="s1",
                action_type="test",
                outcome=ExecutionOutcome.SUCCESS,
            )
            path = persist_execution_result(result, Path(tmp))
            assert path.exists()


# ========================================================
# Test: Forbidden Actions
# ========================================================


class TestForbiddenActions:
    def test_supervisor_rejects_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            sv = _make_supervisor(Path(tmp))
            sv.start()
            dispatch = _make_dispatch(action_type="self_govern")
            sv._queue.enqueue(dispatch)
            accepted = sv.accept_dispatch(dispatch)
            assert not accepted

    def test_spine_blocks_forbidden(self):
        for action in SPINE_FORBIDDEN_ACTIONS:
            with tempfile.TemporaryDirectory() as tmp:
                spine = _make_spine(Path(tmp))
                result = spine.execute(
                    packet_id=f"WP-forbidden-{action}",
                    action_type=action,
                )
                assert result.outcome == ExecutionSpineOutcome.GOVERNANCE_BLOCKED
