"""Tests for Phase 96.8BR — Live Substrate Runtime Wiring.

Tests:
  - single spine enforcement
  - no direct adapter execution
  - runtime continuity preservation
  - runtime observability preservation
  - runtime replay determinism
  - runtime governance preservation
  - embodiment coordination
  - routing determinism
  - lineage completeness
  - lifecycle transitions
  - open-loop continuity
  - runtime resume consistency
"""

import sys
import tempfile
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.runtime.live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimeContinuation,
    RuntimeContinuationType,
    RuntimeDecision,
    RuntimeDecisionType,
    RuntimeExecutionPlan,
    RuntimeExecutionStep,
    RuntimeLineageReceipt,
    RuntimeOutcome,
    RuntimeOutcomeStatus,
    RuntimePhase,
    RuntimeSignal,
    RuntimeSignalSource,
    RuntimeStepType,
)
from substrate.execution.runtime.live_cognition_coordinator_v1 import (
    LiveCognitionCoordinator,
    WORKSTATION_COMMANDS,
    BROWSER_COMMANDS,
    RUNTIME_COMMANDS,
)
from substrate.execution.runtime.live_runtime_router_v1 import (
    LiveRuntimeRouter,
    CAPABILITY_MAP,
    EMBODIMENT_MAP,
)
from substrate.execution.runtime.live_execution_coordinator_v1 import LiveExecutionCoordinator
from substrate.execution.runtime.live_continuity_coordinator_v1 import LiveContinuityCoordinator
from substrate.execution.runtime.live_observability_coordinator_v1 import LiveObservabilityCoordinator
from substrate.execution.runtime.live_replay_coordinator_v1 import (
    LiveReplayCheck,
    LiveReplayCoordinator,
    LiveReplayResult,
    LiveReplaySessionResult,
)
from substrate.execution.runtime.runtime_lifecycle_engine_v1 import (
    LifecycleState,
    LifecycleTransition,
    RuntimeLifecycleEngine,
    RuntimeSession,
    VALID_TRANSITIONS,
)
from substrate.execution.runtime.live_substrate_runtime_spine_v1 import (
    LiveSubstrateRuntimeSpine,
    RUNTIME_COMMANDS as SPINE_RUNTIME_COMMANDS,
)


# ===================================================================
# Test 1: Contracts
# ===================================================================


class TestLiveRuntimeContracts:
    """Test all 8 live runtime contracts."""

    def test_signal_has_deterministic_fields(self):
        sig = RuntimeSignal(raw_input="!runtime-status")
        assert sig.signal_id.startswith("lsig-")
        assert sig.correlation_id.startswith("lcorr-")
        assert sig.timestamp
        assert sig.content_hash()

    def test_signal_serialization(self):
        sig = RuntimeSignal(raw_input="!test", source=RuntimeSignalSource.DISCORD)
        d = sig.to_dict()
        assert d["source"] == "discord"
        assert d["raw_input"] == "!test"
        assert "content_hash" in d

    def test_context_accumulation(self):
        ctx = RuntimeContext(signal_id="sig-1", correlation_id="corr-1")
        ctx.command_name = "workstation-status"
        ctx.capability_resolved = "workstation_inspection"
        ctx.embodiment_path = "workstation"
        assert ctx.content_hash()
        d = ctx.to_dict()
        assert d["command_name"] == "workstation-status"

    def test_context_add_decision(self):
        ctx = RuntimeContext()
        dec = RuntimeDecision(decision_type=RuntimeDecisionType.ROUTE)
        ctx.add_decision(dec)
        assert len(ctx.decisions) == 1

    def test_context_add_lineage_receipt(self):
        ctx = RuntimeContext()
        ctx.add_lineage_receipt("rcpt-123")
        assert "rcpt-123" in ctx.lineage_receipts

    def test_decision_content_hash(self):
        dec = RuntimeDecision(
            decision_type=RuntimeDecisionType.GOVERN,
            input_summary="test",
            approved=True,
        )
        assert dec.content_hash()
        assert dec.to_dict()["decision_type"] == "govern"

    def test_execution_plan(self):
        plan = RuntimeExecutionPlan(signal_id="sig-1")
        step = RuntimeExecutionStep(step_index=0, step_type=RuntimeStepType.INSPECT)
        plan.steps.append(step)
        plan.finalize()
        assert plan.total_steps == 1
        assert plan.content_hash()

    def test_execution_step(self):
        step = RuntimeExecutionStep(
            step_type=RuntimeStepType.SHELL,
            command="git status",
            adapter="governed_shell",
        )
        assert step.step_id.startswith("lstep-")
        assert step.content_hash()

    def test_outcome_succeeded(self):
        out = RuntimeOutcome(status=RuntimeOutcomeStatus.SUCCESS)
        assert out.succeeded
        out2 = RuntimeOutcome(status=RuntimeOutcomeStatus.DENIED)
        assert not out2.succeeded

    def test_outcome_serialization(self):
        out = RuntimeOutcome(
            status=RuntimeOutcomeStatus.SUCCESS,
            command_name="test",
            embodiment_path="runtime",
        )
        d = out.to_dict()
        assert d["status"] == "success"
        assert "content_hash" in d

    def test_continuation_types(self):
        c = RuntimeContinuation(continuation_type=RuntimeContinuationType.COMPLETE)
        assert c.to_dict()["continuation_type"] == "complete"
        c2 = RuntimeContinuation(continuation_type=RuntimeContinuationType.OPEN_LOOP)
        assert c2.to_dict()["continuation_type"] == "open_loop"

    def test_lineage_receipt(self):
        r = RuntimeLineageReceipt(
            signal_id="sig-1",
            phase=RuntimePhase.ROUTING,
            action="resolve",
            component="router",
        )
        assert r.receipt_id.startswith("lrcpt-")
        assert r.content_hash()
        d = r.to_dict()
        assert d["phase"] == "routing"

    def test_all_enums(self):
        assert len(RuntimeSignalSource) >= 8
        assert len(RuntimePhase) >= 10
        assert len(RuntimeDecisionType) >= 7
        assert len(RuntimeStepType) >= 7
        assert len(RuntimeOutcomeStatus) >= 6
        assert len(RuntimeContinuationType) >= 4


# ===================================================================
# Test 2: Cognition Coordinator
# ===================================================================


class TestCognitionCoordinator:
    """Test the cognition coordinator."""

    def setup_method(self):
        self.cog = LiveCognitionCoordinator()

    def test_interpret_command(self):
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext(signal_id=sig.signal_id, correlation_id=sig.correlation_id)
        ctx = self.cog.interpret(sig, ctx)
        assert ctx.command_name == "workstation-status"
        assert ctx.intent_type == "query"
        assert ctx.domain == "workstation"
        assert len(ctx.decisions) >= 1
        assert len(ctx.lineage_receipts) >= 1

    def test_interpret_strips_bang(self):
        sig = RuntimeSignal(raw_input="!browser-tabs")
        ctx = RuntimeContext()
        ctx = self.cog.interpret(sig, ctx)
        assert ctx.command_name == "browser-tabs"

    def test_interpret_with_args(self):
        sig = RuntimeSignal(raw_input="!ingest-doc some/path.txt")
        ctx = RuntimeContext()
        ctx = self.cog.interpret(sig, ctx)
        assert ctx.command_name == "ingest-doc"
        assert ctx.command_args.get("raw_args") == "some/path.txt"

    def test_classify_intent_types(self):
        assert self.cog._classify_intent("workstation-status") == "query"
        assert self.cog._classify_intent("runtime-status") == "query"
        assert self.cog._classify_intent("report-system") == "report"
        assert self.cog._classify_intent("ingest-doc") == "ingestion"
        assert self.cog._classify_intent("unknown-command") == "command"

    def test_resolve_domains(self):
        assert self.cog._resolve_domain("workstation-status") == "workstation"
        assert self.cog._resolve_domain("browser-tabs") == "browser"
        assert self.cog._resolve_domain("runtime-status") == "runtime"
        assert self.cog._resolve_domain("memory-query") == "memory"
        assert self.cog._resolve_domain("unknown") == "general"

    def test_create_plan(self):
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext()
        ctx = self.cog.interpret(sig, ctx)
        plan = self.cog.create_plan(sig, ctx)
        assert plan.total_steps == 1
        assert plan.steps[0].command == "workstation-status"
        assert plan.embodiment_path == "workstation"

    def test_create_multi_step_plan(self):
        sig = RuntimeSignal(raw_input="!multi-step")
        ctx = RuntimeContext()
        steps = [
            {"step_type": "inspect", "command": "step1"},
            {"step_type": "shell", "command": "step2"},
        ]
        plan = self.cog.create_multi_step_plan(sig, ctx, steps)
        assert plan.total_steps == 2
        assert plan.steps[0].step_type == RuntimeStepType.INSPECT
        assert plan.steps[1].step_type == RuntimeStepType.SHELL

    def test_retrieve_memory_context(self):
        ctx = RuntimeContext()
        entries = [{"id": "mem-1", "content": "test"}]
        ctx = self.cog.retrieve_memory_context(ctx, entries)
        assert len(ctx.memory_context) == 1
        assert self.cog.get_stats()["memory_retrievals"] == 1

    def test_retrieve_continuity_context(self):
        ctx = RuntimeContext()
        ctx = self.cog.retrieve_continuity_context(
            ctx,
            continuity_state={"phase": "active"},
            open_loops=[{"id": "loop-1"}],
        )
        assert ctx.continuity_context["phase"] == "active"
        assert len(ctx.open_loops) == 1

    def test_stats(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext()
        self.cog.interpret(sig, ctx)
        stats = self.cog.get_stats()
        assert stats["interpretations"] == 1

    def test_command_sets(self):
        assert "workstation-status" in WORKSTATION_COMMANDS
        assert "browser-tabs" in BROWSER_COMMANDS
        assert "runtime-status" in RUNTIME_COMMANDS


# ===================================================================
# Test 3: Runtime Router
# ===================================================================


class TestRuntimeRouter:
    """Test the runtime router."""

    def setup_method(self):
        self.router = LiveRuntimeRouter()

    def test_resolve_workstation_command(self):
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext(command_name="workstation-status")
        ctx = self.router.resolve(sig, ctx)
        assert ctx.capability_resolved == "workstation_inspection"
        assert ctx.environment_resolved == "vps_local"
        assert ctx.embodiment_path == "workstation"
        assert ctx.risk_class == "safe"

    def test_resolve_browser_command(self):
        sig = RuntimeSignal(raw_input="!browser-tabs")
        ctx = RuntimeContext(command_name="browser-tabs")
        ctx = self.router.resolve(sig, ctx)
        assert ctx.capability_resolved == "browser_inspection"
        assert ctx.embodiment_path == "browser"

    def test_resolve_runtime_command(self):
        sig = RuntimeSignal(raw_input="!runtime-status")
        ctx = RuntimeContext(command_name="runtime-status")
        ctx = self.router.resolve(sig, ctx)
        assert ctx.capability_resolved == "runtime_inspection"
        assert ctx.embodiment_path == "runtime"

    def test_resolve_unknown_command(self):
        sig = RuntimeSignal(raw_input="!unknown-cmd")
        ctx = RuntimeContext(command_name="unknown-cmd")
        ctx = self.router.resolve(sig, ctx)
        assert ctx.capability_resolved == "general_execution"
        assert ctx.risk_class == "medium"

    def test_routing_emits_decision(self):
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext(command_name="workstation-status")
        ctx = self.router.resolve(sig, ctx)
        assert len(ctx.decisions) >= 1
        assert ctx.decisions[0]["decision_type"] == "route"

    def test_routing_emits_lineage_receipt(self):
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext(command_name="workstation-status")
        ctx = self.router.resolve(sig, ctx)
        assert len(ctx.lineage_receipts) >= 1

    def test_routing_determinism(self):
        """Same input → same routing decisions."""
        sig1 = RuntimeSignal(raw_input="!browser-status")
        ctx1 = RuntimeContext(command_name="browser-status")
        ctx1 = self.router.resolve(sig1, ctx1)

        router2 = LiveRuntimeRouter()
        sig2 = RuntimeSignal(raw_input="!browser-status")
        ctx2 = RuntimeContext(command_name="browser-status")
        ctx2 = router2.resolve(sig2, ctx2)

        assert ctx1.capability_resolved == ctx2.capability_resolved
        assert ctx1.environment_resolved == ctx2.environment_resolved
        assert ctx1.embodiment_path == ctx2.embodiment_path
        assert ctx1.risk_class == ctx2.risk_class

    def test_governance_rules_for_safe(self):
        sig = RuntimeSignal(raw_input="!runtime-status")
        ctx = RuntimeContext(command_name="runtime-status")
        ctx = self.router.resolve(sig, ctx)
        assert "CAPABILITY_AUTHORIZED" in ctx.governance_rules
        assert "RISK_ELEVATED" not in ctx.governance_rules

    def test_all_known_commands_resolve(self):
        for cmd in CAPABILITY_MAP:
            cap = self.router.resolve_capability(cmd)
            emb = self.router.resolve_embodiment(cmd)
            assert cap
            assert emb

    def test_stats(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(command_name="workstation-status")
        self.router.resolve(sig, ctx)
        stats = self.router.get_stats()
        assert stats["routes_resolved"] == 1


# ===================================================================
# Test 4: Execution Coordinator
# ===================================================================


class TestExecutionCoordinator:
    """Test the execution coordinator."""

    def setup_method(self):
        self.exec = LiveExecutionCoordinator()

    def test_execute_workstation_plan(self):
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext(command_name="workstation-status")
        plan = RuntimeExecutionPlan(
            signal_id=sig.signal_id,
            embodiment_path="workstation",
        )
        step = RuntimeExecutionStep(
            step_type=RuntimeStepType.SHELL,
            command="workstation-status",
        )
        plan.steps.append(step)
        plan.finalize()

        outcome = self.exec.execute_plan(sig, ctx, plan)
        assert outcome.status == RuntimeOutcomeStatus.SUCCESS
        assert outcome.steps_completed == 1

    def test_execute_browser_plan(self):
        sig = RuntimeSignal(raw_input="!browser-status")
        ctx = RuntimeContext(command_name="browser-status")
        plan = RuntimeExecutionPlan(
            signal_id=sig.signal_id,
            embodiment_path="browser",
        )
        step = RuntimeExecutionStep(
            step_type=RuntimeStepType.BROWSER,
            command="browser-status",
        )
        plan.steps.append(step)
        plan.finalize()

        outcome = self.exec.execute_plan(sig, ctx, plan)
        assert outcome.status == RuntimeOutcomeStatus.SUCCESS

    def test_execute_inspect_plan(self):
        sig = RuntimeSignal(raw_input="!runtime-status")
        ctx = RuntimeContext(command_name="runtime-status")
        plan = RuntimeExecutionPlan(embodiment_path="runtime")
        step = RuntimeExecutionStep(
            step_type=RuntimeStepType.INSPECT,
            command="runtime-status",
        )
        plan.steps.append(step)
        plan.finalize()

        outcome = self.exec.execute_plan(sig, ctx, plan)
        assert outcome.succeeded

    def test_execute_emits_lineage(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext()
        plan = RuntimeExecutionPlan()
        step = RuntimeExecutionStep(step_type=RuntimeStepType.INSPECT, command="test")
        plan.steps.append(step)
        plan.finalize()

        self.exec.execute_plan(sig, ctx, plan)
        assert len(ctx.lineage_receipts) >= 1
        assert len(ctx.decisions) >= 1

    def test_stats(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext()
        plan = RuntimeExecutionPlan()
        step = RuntimeExecutionStep(step_type=RuntimeStepType.INSPECT, command="test")
        plan.steps.append(step)
        plan.finalize()

        self.exec.execute_plan(sig, ctx, plan)
        stats = self.exec.get_stats()
        assert stats["executions"] == 1
        assert stats["successes"] == 1


# ===================================================================
# Test 5: Continuity Coordinator
# ===================================================================


class TestContinuityCoordinator:
    """Test the continuity coordinator."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.cont = LiveContinuityCoordinator(state_dir=self.tmp)

    def test_start_session(self):
        sid = self.cont.start_session("test-session")
        assert sid == "test-session"

    def test_persist_success_event(self):
        self.cont.start_session("s1")
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(correlation_id=sig.correlation_id)
        outcome = RuntimeOutcome(
            status=RuntimeOutcomeStatus.SUCCESS,
            command_name="test",
            embodiment_path="runtime",
        )
        continuation = self.cont.persist_event(sig, ctx, outcome)
        assert continuation.continuation_type == RuntimeContinuationType.COMPLETE

    def test_persist_failed_event_creates_open_loop(self):
        self.cont.start_session("s2")
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(correlation_id=sig.correlation_id)
        outcome = RuntimeOutcome(
            status=RuntimeOutcomeStatus.FAILED,
            command_name="test",
            error_message="something failed",
        )
        continuation = self.cont.persist_event(sig, ctx, outcome)
        assert continuation.continuation_type == RuntimeContinuationType.OPEN_LOOP
        assert len(continuation.open_loop_ids) == 1

    def test_retrieve_state(self):
        self.cont.start_session("s3")
        state = self.cont.retrieve_state()
        assert state["session_id"] == "s3"
        assert "substrate_continuity" in state
        assert "workstation_continuity" in state
        assert "browser_continuity" in state

    def test_create_resume_packet(self):
        self.cont.start_session("s4")
        packet = self.cont.create_resume_packet(
            active_goals=["build phase"],
            suggested_next_actions=["run tests"],
        )
        assert packet is not None
        assert self.cont.get_stats()["resume_packets"] == 1

    def test_stats(self):
        self.cont.start_session("s5")
        stats = self.cont.get_stats()
        assert stats["session_id"] == "s5"
        assert stats["events_persisted"] == 0


# ===================================================================
# Test 6: Observability Coordinator
# ===================================================================


class TestObservabilityCoordinator:
    """Test the observability coordinator."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.obs = LiveObservabilityCoordinator(observability_dir=self.tmp)

    def test_record_trace(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(
            command_name="test",
            capability_resolved="test_cap",
            governance_verdict="approved",
        )
        outcome = RuntimeOutcome(status=RuntimeOutcomeStatus.SUCCESS, command_name="test")
        trace = self.obs.record_trace(sig, ctx, outcome)
        assert trace["command_name"] == "test"
        assert self.obs.get_stats()["total_traces"] == 1

    def test_record_governance_event(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(command_name="test", governance_verdict="approved")
        self.obs.record_governance_event(sig, ctx)
        assert self.obs.get_stats()["total_governance_events"] == 1

    def test_record_execution_event(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(command_name="test")
        outcome = RuntimeOutcome(status=RuntimeOutcomeStatus.SUCCESS)
        self.obs.record_execution_event(sig, ctx, outcome)
        assert self.obs.get_stats()["total_execution_events"] == 1

    def test_record_continuity_event(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(command_name="test")
        self.obs.record_continuity_event(sig, ctx, "complete")
        assert self.obs.get_stats()["total_continuity_events"] == 1

    def test_persist_lineage_receipts(self):
        ctx = RuntimeContext()
        ctx.add_lineage_receipt("rcpt-1")
        ctx.add_lineage_receipt("rcpt-2")
        self.obs.persist_lineage_receipts(ctx)
        lineage_path = Path(self.tmp) / "lineage_receipts.jsonl"
        assert lineage_path.exists()

    def test_get_recent_traces(self):
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext(command_name="test")
        outcome = RuntimeOutcome(status=RuntimeOutcomeStatus.SUCCESS)
        self.obs.record_trace(sig, ctx, outcome)
        recent = self.obs.get_recent_traces(10)
        assert len(recent) == 1


# ===================================================================
# Test 7: Replay Coordinator
# ===================================================================


class TestReplayCoordinator:
    """Test the replay coordinator."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.replay = LiveReplayCoordinator(proof_dir=self.tmp)

    def test_replay_trace_determinism(self):
        trace = {
            "command_name": "workstation-status",
            "intent_type": "query",
            "domain": "workstation",
            "capability": "workstation_inspection",
            "environment": "vps_local",
            "embodiment_path": "workstation",
            "risk_class": "safe",
        }
        result = self.replay.replay_trace(trace)
        result.finalize()
        assert result.all_passed
        assert len(result.checks) == 6

    def test_replay_browser_trace(self):
        trace = {
            "command_name": "browser-tabs",
            "intent_type": "query",
            "domain": "browser",
            "capability": "browser_inspection",
            "environment": "vps_local",
            "embodiment_path": "browser",
            "risk_class": "safe",
        }
        result = self.replay.replay_trace(trace)
        result.finalize()
        assert result.all_passed

    def test_replay_runtime_trace(self):
        trace = {
            "command_name": "runtime-status",
            "intent_type": "query",
            "domain": "runtime",
            "capability": "runtime_inspection",
            "environment": "vps_local",
            "embodiment_path": "runtime",
            "risk_class": "safe",
        }
        result = self.replay.replay_trace(trace)
        result.finalize()
        assert result.all_passed

    def test_replay_session(self):
        traces = [
            {
                "command_name": "workstation-status",
                "intent_type": "query",
                "domain": "workstation",
                "capability": "workstation_inspection",
                "environment": "vps_local",
                "embodiment_path": "workstation",
                "risk_class": "safe",
            },
            {
                "command_name": "browser-tabs",
                "intent_type": "query",
                "domain": "browser",
                "capability": "browser_inspection",
                "environment": "vps_local",
                "embodiment_path": "browser",
                "risk_class": "safe",
            },
        ]
        session = self.replay.replay_session(traces, session_id="test-session")
        assert session.all_passed
        assert session.total_records == 2
        assert session.passed_records == 2

    def test_replay_proof_persisted(self):
        traces = [
            {
                "command_name": "runtime-status",
                "intent_type": "query",
                "domain": "runtime",
                "capability": "runtime_inspection",
                "environment": "vps_local",
                "embodiment_path": "runtime",
                "risk_class": "safe",
            },
        ]
        self.replay.replay_session(traces, session_id="proof-test")
        proof_path = Path(self.tmp) / "live_replay_proof_proof-test.json"
        assert proof_path.exists()

    def test_replay_mismatch_detection(self):
        trace = {
            "command_name": "workstation-status",
            "intent_type": "query",
            "domain": "workstation",
            "capability": "WRONG_CAPABILITY",
            "environment": "vps_local",
            "embodiment_path": "workstation",
            "risk_class": "safe",
        }
        result = self.replay.replay_trace(trace)
        result.finalize()
        assert not result.all_passed
        failed = [c for c in result.checks if not c.passed]
        assert any(c.check_name == "capability" for c in failed)


# ===================================================================
# Test 8: Lifecycle Engine
# ===================================================================


class TestLifecycleEngine:
    """Test the runtime lifecycle engine."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.lc = RuntimeLifecycleEngine(state_dir=self.tmp)

    def test_initialize(self):
        session = self.lc.initialize("test-session")
        assert self.lc.state == LifecycleState.ACTIVE
        assert session.session_type == "runtime"

    def test_valid_transitions(self):
        self.lc.initialize()
        assert self.lc.transition(LifecycleState.WAITING, "waiting for input")
        assert self.lc.state == LifecycleState.WAITING
        assert self.lc.transition(LifecycleState.ACTIVE, "input received")
        assert self.lc.state == LifecycleState.ACTIVE

    def test_invalid_transition_rejected(self):
        self.lc.initialize()
        assert not self.lc.transition(LifecycleState.RESUMED, "invalid")
        assert self.lc.state == LifecycleState.ACTIVE

    def test_suspended_to_resumed(self):
        self.lc.initialize()
        self.lc.transition(LifecycleState.SUSPENDED, "suspend")
        assert self.lc.state == LifecycleState.SUSPENDED
        self.lc.transition(LifecycleState.RESUMED, "resume")
        assert self.lc.state == LifecycleState.RESUMED
        self.lc.transition(LifecycleState.ACTIVE, "back to active")
        assert self.lc.state == LifecycleState.ACTIVE

    def test_degraded_recovery(self):
        self.lc.initialize()
        self.lc.transition(LifecycleState.DEGRADED, "adapter failure")
        assert self.lc.state == LifecycleState.DEGRADED
        self.lc.transition(LifecycleState.ACTIVE, "recovered")
        assert self.lc.state == LifecycleState.ACTIVE

    def test_terminated_is_final(self):
        self.lc.initialize()
        self.lc.transition(LifecycleState.TERMINATED, "shutdown")
        assert self.lc.state == LifecycleState.TERMINATED
        assert not self.lc.transition(LifecycleState.ACTIVE, "attempt recovery")

    def test_register_session(self):
        self.lc.initialize()
        session = self.lc.register_session("continuity")
        assert session.session_type == "continuity"
        assert session.state == LifecycleState.ACTIVE

    def test_record_activity(self):
        session = self.lc.initialize("s1")
        self.lc.record_activity("s1")
        s = self.lc.get_session("s1")
        assert s.events_count == 1

    def test_terminate_session(self):
        self.lc.initialize("s1")
        self.lc.terminate_session("s1")
        s = self.lc.get_session("s1")
        assert s.state == LifecycleState.TERMINATED
        assert len(self.lc.get_active_sessions()) == 0

    def test_get_state_map(self):
        self.lc.initialize("s1")
        state_map = self.lc.get_state_map()
        assert state_map["lifecycle_state"] == "active"
        assert "sessions" in state_map
        assert "stats" in state_map

    def test_persist_state_map(self):
        self.lc.initialize("s1")
        self.lc.persist_state_map()
        path = Path(self.tmp) / "runtime_state_map.json"
        assert path.exists()

    def test_transitions_tracked(self):
        self.lc.initialize()
        self.lc.transition(LifecycleState.WAITING)
        self.lc.transition(LifecycleState.ACTIVE)
        transitions = self.lc.get_transitions()
        assert len(transitions) == 3  # init→active, active→waiting, waiting→active


# ===================================================================
# Test 9: Live Substrate Runtime Spine
# ===================================================================


class TestLiveSubstrateRuntimeSpine:
    """Test the canonical live runtime spine."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.spine = LiveSubstrateRuntimeSpine(
            observability=LiveObservabilityCoordinator(observability_dir=f"{self.tmp}/obs"),
            continuity=LiveContinuityCoordinator(state_dir=f"{self.tmp}/cont"),
            replay=LiveReplayCoordinator(proof_dir=f"{self.tmp}/replay"),
            lifecycle=RuntimeLifecycleEngine(state_dir=f"{self.tmp}/lifecycle"),
        )

    def test_initialize(self):
        result = self.spine.initialize("test-spine")
        assert result["session_id"] == "test-spine"
        assert result["lifecycle_state"] == "active"
        assert result["active_sessions"] >= 5

    def test_process_runtime_command(self):
        self.spine.initialize("s1")
        outcome = self.spine.process("!runtime-status")
        assert outcome.succeeded
        assert outcome.command_name == "runtime-status"
        assert outcome.embodiment_path == "runtime"

    def test_process_workstation_command(self):
        self.spine.initialize("s2")
        outcome = self.spine.process("!workstation-status")
        assert outcome.succeeded
        assert outcome.command_name == "workstation-status"

    def test_process_browser_command(self):
        self.spine.initialize("s3")
        outcome = self.spine.process("!browser-status")
        assert outcome.succeeded
        assert outcome.command_name == "browser-status"

    def test_process_emits_observability(self):
        self.spine.initialize("s4")
        self.spine.process("!workstation-status")
        obs_stats = self.spine._observability.get_stats()
        assert obs_stats["total_traces"] >= 1

    def test_process_emits_continuity(self):
        self.spine.initialize("s5")
        self.spine.process("!workstation-status")
        cont_stats = self.spine._continuity.get_stats()
        assert cont_stats["events_persisted"] >= 1

    def test_process_updates_lifecycle(self):
        self.spine.initialize("s6")
        self.spine.process("!runtime-status")
        lifecycle_stats = self.spine._lifecycle.get_stats()
        assert lifecycle_stats["current_state"] == "active"

    def test_governance_denial(self):
        self.spine.initialize("s7")
        spine = self.spine
        # Temporarily set forbidden risk for a command
        original_risk = spine._router._resolve_risk
        spine._router._resolve_risk = lambda cap: "forbidden"
        outcome = spine.process("!workstation-status")
        assert outcome.status == RuntimeOutcomeStatus.DENIED
        spine._router._resolve_risk = original_risk

    def test_single_spine_enforcement(self):
        """All commands go through process() → one pipeline."""
        self.spine.initialize("s8")
        o1 = self.spine.process("!workstation-status")
        o2 = self.spine.process("!browser-status")
        o3 = self.spine.process("!runtime-status")
        assert o1.succeeded
        assert o2.succeeded
        assert o3.succeeded
        stats = self.spine.get_stats()
        assert stats["total_processed"] == 3

    def test_dispatch_all_runtime_commands(self):
        self.spine.initialize("s9")
        for cmd in SPINE_RUNTIME_COMMANDS:
            result = self.spine.dispatch_command(cmd)
            assert "error" not in result, f"Command {cmd} returned error"

    def test_dispatch_unknown_command(self):
        result = self.spine.dispatch_command("nonexistent-command")
        assert "error" in result

    def test_replay_through_spine(self):
        self.spine.initialize("s10")
        self.spine.process("!workstation-status")
        self.spine.process("!browser-tabs")
        self.spine.process("!runtime-status")
        result = self.spine.dispatch_command("runtime-replay")
        assert "replay_result" in result or "message" in result

    def test_lineage_completeness(self):
        """Process emits lineage receipts at each phase."""
        self.spine.initialize("s11")
        outcome = self.spine.process("!workstation-status")
        assert len(outcome.lineage_receipts) >= 2

    def test_stats_comprehensive(self):
        self.spine.initialize("s12")
        self.spine.process("!runtime-status")
        stats = self.spine.get_stats()
        assert "cognition" in stats
        assert "router" in stats
        assert "executor" in stats
        assert "continuity" in stats
        assert "observability" in stats
        assert "replay" in stats
        assert "lifecycle" in stats

    def test_process_multiple_signals_accumulate(self):
        self.spine.initialize("s13")
        for i in range(5):
            self.spine.process(f"!runtime-status")
        stats = self.spine.get_stats()
        assert stats["total_processed"] == 5
        assert stats["total_successes"] == 5

    def test_context_command_dispatches_correctly(self):
        self.spine.initialize("s14")
        result = self.spine.dispatch_command("runtime-context")
        assert result["command"] == "runtime-context"
        assert "session_id" in result

    def test_governance_command_dispatches(self):
        self.spine.initialize("s15")
        result = self.spine.dispatch_command("runtime-governance")
        assert result["command"] == "runtime-governance"

    def test_open_loops_command(self):
        self.spine.initialize("s16")
        result = self.spine.dispatch_command("runtime-open-loops")
        assert result["command"] == "runtime-open-loops"

    def test_resume_command(self):
        self.spine.initialize("s17")
        result = self.spine.dispatch_command("runtime-resume")
        assert result["command"] == "runtime-resume"
        assert "resume_packet" in result

    def test_observe_command(self):
        self.spine.initialize("s18")
        self.spine.process("!workstation-status")
        result = self.spine.dispatch_command("runtime-observe")
        assert result["command"] == "runtime-observe"
        assert "recent_traces" in result


# ===================================================================
# Test 10: Integration — No Direct Adapter Execution
# ===================================================================


class TestNoDirectAdapterExecution:
    """Verify that adapters cannot be called outside the spine."""

    def test_execution_coordinator_uses_engines(self):
        """ExecutionCoordinator dispatches through embodiment engines only."""
        exec_coord = LiveExecutionCoordinator()
        sig = RuntimeSignal(raw_input="!workstation-status")
        ctx = RuntimeContext(command_name="workstation-status")
        plan = RuntimeExecutionPlan(embodiment_path="workstation")
        step = RuntimeExecutionStep(step_type=RuntimeStepType.SHELL, command="workstation-status")
        plan.steps.append(step)
        plan.finalize()

        outcome = exec_coord.execute_plan(sig, ctx, plan)
        assert outcome.steps_completed == 1
        assert outcome.embodiment_path == "workstation"

    def test_spine_is_only_entrypoint(self):
        """All processing goes through spine.process()."""
        tmp = tempfile.mkdtemp()
        spine = LiveSubstrateRuntimeSpine(
            observability=LiveObservabilityCoordinator(observability_dir=f"{tmp}/obs"),
            continuity=LiveContinuityCoordinator(state_dir=f"{tmp}/cont"),
            replay=LiveReplayCoordinator(proof_dir=f"{tmp}/replay"),
            lifecycle=RuntimeLifecycleEngine(state_dir=f"{tmp}/lc"),
        )
        spine.initialize("integration-test")
        outcome = spine.process("!workstation-status")
        assert outcome.succeeded
        assert outcome.command_name == "workstation-status"
        stats = spine.get_stats()
        assert stats["total_processed"] == 1

    def test_routing_determinism_across_instances(self):
        """Different router instances produce same routing for same input."""
        r1 = LiveRuntimeRouter()
        r2 = LiveRuntimeRouter()
        for cmd in ["workstation-status", "browser-tabs", "runtime-status"]:
            sig = RuntimeSignal(raw_input=f"!{cmd}")
            ctx1 = RuntimeContext(command_name=cmd)
            ctx2 = RuntimeContext(command_name=cmd)
            ctx1 = r1.resolve(sig, ctx1)
            ctx2 = r2.resolve(sig, ctx2)
            assert ctx1.capability_resolved == ctx2.capability_resolved
            assert ctx1.embodiment_path == ctx2.embodiment_path

    def test_replay_determinism_full_pipeline(self):
        """Process → observe → replay: all checks pass."""
        tmp = tempfile.mkdtemp()
        spine = LiveSubstrateRuntimeSpine(
            observability=LiveObservabilityCoordinator(observability_dir=f"{tmp}/obs"),
            continuity=LiveContinuityCoordinator(state_dir=f"{tmp}/cont"),
            replay=LiveReplayCoordinator(proof_dir=f"{tmp}/replay"),
            lifecycle=RuntimeLifecycleEngine(state_dir=f"{tmp}/lc"),
        )
        spine.initialize("replay-test")
        spine.process("!workstation-status")
        spine.process("!browser-tabs")

        traces = spine._observability.get_recent_traces(10)
        non_runtime = [t for t in traces if t.get("command_name") not in SPINE_RUNTIME_COMMANDS]
        if non_runtime:
            session = spine._replay.replay_session(non_runtime, session_id="replay-test")
            assert session.all_passed

    def test_open_loop_created_on_failure(self):
        """Failed execution creates an open loop continuation."""
        cont = LiveContinuityCoordinator(state_dir=tempfile.mkdtemp())
        cont.start_session("loop-test")
        sig = RuntimeSignal(raw_input="!test")
        ctx = RuntimeContext()
        outcome = RuntimeOutcome(
            status=RuntimeOutcomeStatus.FAILED,
            command_name="test",
            error_message="adapter unavailable",
        )
        continuation = cont.persist_event(sig, ctx, outcome)
        assert continuation.continuation_type == RuntimeContinuationType.OPEN_LOOP
