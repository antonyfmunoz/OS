"""Tests for Phase 96.8BO — Live Substrate Operationalization.

Tests cover:
  - Execution contracts (9 contracts)
  - Environment registry (3 environments)
  - Capability router (command mapping, risk, routing)
  - Adapter lifecycle manager (states, health, selection)
  - Execution queue (enqueue, dequeue, priority, dedup)
  - Governance execution bridge (verdicts, rules)
  - Observability pipeline (recording, metrics)
  - Execution orchestrator (end-to-end execution)
  - Canonical runtime spine (14-step pipeline)
  - Runtime replay engine (determinism verification)

Phase 96.8BO. UMH substrate subsystem.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from execution.runtime.execution_contracts_v1 import (
    AdapterSelection,
    CapabilityDomain,
    CapabilityResolution,
    EnvironmentSelection,
    ExecutionEnvelope,
    ExecutionMode,
    ExecutionSignal,
    GovernanceEvaluation,
    GovernanceVerdict,
    IntentType,
    InterpretedIntent,
    ObservabilityRecord,
    RiskClass,
    SignalSource,
    SpineExecutionResult,
    SpineOutcome,
)
from execution.runtime.environment_registry_v1 import (
    EnvironmentDescriptor,
    EnvironmentRegistry,
    EnvironmentStatus,
    LOCAL_WORKSTATION,
    SANDBOX,
    VPS_TMUX,
)
from execution.runtime.capability_router_v1 import (
    COMMAND_CAPABILITY_MAP,
    COMMAND_RISK_MAP,
    CapabilityRouter,
    FORBIDDEN_COMMANDS,
    SAFE_COMMANDS,
)
from adapters.adapter_engine.adapter_lifecycle_manager_v1 import (
    AdapterHealthRecord,
    AdapterLifecycleManager,
    AdapterState,
)
from execution.runtime.runtime_execution_queue_v1 import (
    QueuePriority,
    RuntimeExecutionQueue,
)
from execution.runtime.governance_execution_bridge_v1 import (
    GovernanceExecutionBridge,
)
from execution.runtime.runtime_observability_pipeline_v1 import (
    RuntimeObservabilityPipeline,
)
from execution.runtime.execution_orchestrator_v1 import ExecutionOrchestrator
from execution.runtime.canonical_runtime_spine_v1 import CanonicalRuntimeSpine
from execution.runtime.runtime_replay_engine_v1 import RuntimeReplayEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="test_96bo_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def env_registry():
    return EnvironmentRegistry.create_default()


@pytest.fixture
def router(env_registry):
    return CapabilityRouter(env_registry)


@pytest.fixture
def adapter_manager():
    mgr = AdapterLifecycleManager()
    mgr.register_adapter(
        "vps-shell-01", "shell_adapter", ["ping", "explore-environment", "relay-status"], "vps_tmux"
    )
    mgr.register_adapter(
        "vps-report-01",
        "report_adapter",
        [
            "constitution-report",
            "economics-report",
            "continuity-report",
            "runtime-status",
            "capabilities",
            "adapters",
            "execution-queue",
        ],
        "vps_tmux",
    )
    mgr.register_adapter(
        "vps-memory-01",
        "memory_adapter",
        ["memory-query", "memory-lineage", "promote-safe-memory-candidate"],
        "vps_tmux",
    )
    mgr.register_adapter(
        "vps-ingest-01",
        "ingestion_adapter",
        ["ingest-safe-doc-cu", "ingest-safe-doc"],
        "vps_tmux",
    )
    mgr.register_adapter(
        "local-gui-01",
        "gui_adapter",
        ["chrome-proof", "chrome-open-google-drive", "open-application-url"],
        "local_windows_desktop",
    )
    return mgr


@pytest.fixture
def spine(tmp_dir, router, adapter_manager, env_registry):
    governance = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
    queue = RuntimeExecutionQueue(queue_dir=tmp_dir / "queue")
    observability = RuntimeObservabilityPipeline(observability_dir=tmp_dir / "obs")
    orchestrator = ExecutionOrchestrator(adapter_manager, observability)

    sp = CanonicalRuntimeSpine(
        capability_router=router,
        adapter_manager=adapter_manager,
        environment_registry=env_registry,
        governance_bridge=governance,
        execution_queue=queue,
        orchestrator=orchestrator,
        observability=observability,
    )
    sp.start_session("test-session-001")
    return sp


# ---------------------------------------------------------------------------
# Test: Execution Contracts
# ---------------------------------------------------------------------------


class TestExecutionContracts:
    def test_signal_creates_with_ids(self):
        sig = ExecutionSignal(raw_command="!ping", source=SignalSource.DISCORD)
        assert sig.signal_id.startswith("sig-")
        assert sig.correlation_id.startswith("corr-")

    def test_signal_content_hash_deterministic(self):
        s1 = ExecutionSignal(raw_command="!ping", source=SignalSource.DISCORD)
        s2 = ExecutionSignal(raw_command="!ping", source=SignalSource.DISCORD)
        assert s1.content_hash() == s2.content_hash()

    def test_intent_deterministic_id(self):
        i1 = InterpretedIntent(signal_id="sig-x", command_name="ping")
        i2 = InterpretedIntent(signal_id="sig-x", command_name="ping")
        assert i1.intent_id == i2.intent_id

    def test_capability_resolution_detects_missing(self):
        res = CapabilityResolution(
            intent_id="i1",
            required_capabilities=["shell_execution", "gui_actuation"],
            available_capabilities=["shell_execution"],
        )
        assert not res.resolved
        assert "gui_actuation" in res.missing_capabilities

    def test_governance_evaluation_approved(self):
        gov = GovernanceEvaluation(
            intent_id="i1", command_name="ping", verdict=GovernanceVerdict.APPROVED
        )
        assert gov.approved

    def test_governance_evaluation_denied(self):
        gov = GovernanceEvaluation(
            intent_id="i1", command_name="bad", verdict=GovernanceVerdict.DENIED
        )
        assert not gov.approved

    def test_envelope_content_hash(self):
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        assert len(env.content_hash()) == 24

    def test_spine_result_succeeded(self):
        r = SpineExecutionResult(command_name="ping", outcome=SpineOutcome.SUCCESS)
        assert r.succeeded

    def test_spine_result_failed(self):
        r = SpineExecutionResult(command_name="bad", outcome=SpineOutcome.GOVERNANCE_DENIED)
        assert not r.succeeded

    def test_observability_record_serializes(self):
        rec = ObservabilityRecord(
            command_name="ping", outcome=SpineOutcome.SUCCESS, latency_ms=42.0
        )
        d = rec.to_dict()
        assert d["command_name"] == "ping"
        assert d["latency_ms"] == 42.0


# ---------------------------------------------------------------------------
# Test: Environment Registry
# ---------------------------------------------------------------------------


class TestEnvironmentRegistry:
    def test_default_has_three_environments(self, env_registry):
        assert len(env_registry.get_available()) == 3

    def test_vps_has_shell(self, env_registry):
        vps = env_registry.get("vps-tmux-01")
        assert vps is not None
        assert vps.has_capability(CapabilityDomain.SHELL_EXECUTION)

    def test_vps_no_gui(self, env_registry):
        vps = env_registry.get("vps-tmux-01")
        assert not vps.can_gui

    def test_local_has_gui(self, env_registry):
        local = env_registry.get("local-workstation-01")
        assert local.can_gui

    def test_sandbox_no_write(self, env_registry):
        sandbox = env_registry.get("sandbox-01")
        assert not sandbox.can_write_filesystem

    def test_update_status(self, env_registry):
        env_registry.update_status("sandbox-01", EnvironmentStatus.OFFLINE)
        sandbox = env_registry.get("sandbox-01")
        assert sandbox.status == EnvironmentStatus.OFFLINE
        assert not sandbox.is_available()

    def test_find_for_gui(self, env_registry):
        gui_envs = env_registry.find_for_gui()
        assert len(gui_envs) == 1
        assert gui_envs[0].environment_id == "local-workstation-01"


# ---------------------------------------------------------------------------
# Test: Capability Router
# ---------------------------------------------------------------------------


class TestCapabilityRouter:
    def test_ping_routes_to_shell(self, router):
        route = router.resolve("ping")
        assert route.capability == CapabilityDomain.SHELL_EXECUTION
        assert route.routable

    def test_constitution_report_routes_to_report(self, router):
        route = router.resolve("constitution-report")
        assert route.capability == CapabilityDomain.REPORT_GENERATION

    def test_chrome_proof_routes_to_gui(self, router):
        route = router.resolve("chrome-proof")
        assert route.capability == CapabilityDomain.GUI_ACTUATION

    def test_forbidden_command_not_routable(self, router):
        route = router.resolve("self-govern")
        assert route.is_forbidden
        assert not route.routable

    def test_unknown_command_no_capability(self, router):
        route = router.resolve("nonexistent-command")
        assert route.capability is None
        assert not route.routable

    def test_safe_commands_classified(self, router):
        assert router.is_safe_command("ping")
        assert router.is_safe_command("runtime-status")
        assert not router.is_safe_command("chrome-proof")

    def test_risk_classification(self, router):
        assert router.get_risk_class("ping") == RiskClass.SAFE
        assert router.get_risk_class("ingest-safe-doc-cu") == RiskClass.MEDIUM

    def test_strip_exclamation(self, router):
        route = router.resolve("!ping")
        assert route.capability == CapabilityDomain.SHELL_EXECUTION


# ---------------------------------------------------------------------------
# Test: Adapter Lifecycle Manager
# ---------------------------------------------------------------------------


class TestAdapterLifecycle:
    def test_register_and_find(self, adapter_manager):
        adapters = adapter_manager.find_for_action("ping")
        assert len(adapters) >= 1

    def test_select_adapter(self, adapter_manager):
        selection = adapter_manager.select_adapter("ping")
        assert selection.selected
        assert selection.adapter_id == "vps-shell-01"

    def test_no_adapter_for_unknown(self, adapter_manager):
        selection = adapter_manager.select_adapter("nonexistent-action")
        assert not selection.selected

    def test_mark_busy_and_available(self, adapter_manager):
        adapter_manager.mark_busy("vps-shell-01")
        a = adapter_manager.get_adapter("vps-shell-01")
        assert a.state == AdapterState.BUSY
        adapter_manager.mark_available("vps-shell-01")
        assert a.state == AdapterState.AVAILABLE

    def test_failure_triggers_degraded(self, adapter_manager):
        for _ in range(3):
            adapter_manager.record_execution_failure("vps-shell-01")
        a = adapter_manager.get_adapter("vps-shell-01")
        assert a.state == AdapterState.DEGRADED

    def test_recovery(self, adapter_manager):
        adapter_manager.mark_offline("vps-shell-01", "test")
        assert adapter_manager.get_adapter("vps-shell-01").state == AdapterState.OFFLINE
        adapter_manager.recover("vps-shell-01")
        assert adapter_manager.get_adapter("vps-shell-01").state == AdapterState.AVAILABLE


# ---------------------------------------------------------------------------
# Test: Execution Queue
# ---------------------------------------------------------------------------


class TestExecutionQueue:
    def test_enqueue_and_dequeue(self, tmp_dir):
        q = RuntimeExecutionQueue(queue_dir=tmp_dir / "q")
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        entry = q.enqueue(env)
        assert entry is not None
        assert q.depth == 1
        dequeued = q.dequeue()
        assert dequeued is not None
        assert dequeued.entry_id == entry.entry_id

    def test_dedup(self, tmp_dir):
        q = RuntimeExecutionQueue(queue_dir=tmp_dir / "q")
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        q.enqueue(env)
        dup = q.enqueue(env)
        assert dup is None
        assert q.depth == 1

    def test_priority_ordering(self, tmp_dir):
        q = RuntimeExecutionQueue(queue_dir=tmp_dir / "q")
        e1 = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        e2 = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s2", command_name="status"),
        )
        q.enqueue(e1, priority=QueuePriority.LOW)
        q.enqueue(e2, priority=QueuePriority.CRITICAL)
        dequeued = q.dequeue()
        assert dequeued.command_name == "status"

    def test_complete_and_fail(self, tmp_dir):
        q = RuntimeExecutionQueue(queue_dir=tmp_dir / "q")
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        entry = q.enqueue(env)
        q.dequeue()
        assert q.complete(entry.entry_id)


# ---------------------------------------------------------------------------
# Test: Governance Execution Bridge
# ---------------------------------------------------------------------------


class TestGovernanceBridge:
    def test_safe_command_auto_approves(self, tmp_dir):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        intent = InterpretedIntent(signal_id="s1", command_name="ping", risk_class=RiskClass.SAFE)
        evaluation = gov.evaluate(intent)
        assert evaluation.approved
        assert "SAFE_AUTO_APPROVE" in evaluation.governance_rules_applied

    def test_forbidden_command_denied(self, tmp_dir):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        intent = InterpretedIntent(
            signal_id="s1", command_name="self-govern", risk_class=RiskClass.FORBIDDEN
        )
        evaluation = gov.evaluate(intent)
        assert evaluation.verdict == GovernanceVerdict.STRUCTURALLY_FORBIDDEN

    def test_high_risk_requires_approval(self, tmp_dir):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        intent = InterpretedIntent(
            signal_id="s1", command_name="unknown", risk_class=RiskClass.HIGH
        )
        evaluation = gov.evaluate(intent)
        assert evaluation.verdict == GovernanceVerdict.REQUIRES_APPROVAL

    def test_medium_risk_approved_with_trace(self, tmp_dir):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        intent = InterpretedIntent(
            signal_id="s1", command_name="ingest-safe-doc-cu", risk_class=RiskClass.MEDIUM
        )
        evaluation = gov.evaluate(intent)
        assert evaluation.approved
        assert "MEDIUM_RISK_GOVERNED_APPROVE" in evaluation.governance_rules_applied

    def test_decisions_persisted(self, tmp_dir):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        intent = InterpretedIntent(signal_id="s1", command_name="ping", risk_class=RiskClass.SAFE)
        gov.evaluate(intent)
        decisions = gov.load_decisions()
        assert len(decisions) >= 1
        assert decisions[0]["verdict"] == "approved"


# ---------------------------------------------------------------------------
# Test: Observability Pipeline
# ---------------------------------------------------------------------------


class TestObservability:
    def test_record_and_retrieve(self, tmp_dir):
        obs = RuntimeObservabilityPipeline(observability_dir=tmp_dir / "obs")
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        record = obs.record_execution(env, SpineOutcome.SUCCESS, latency_ms=42.0)
        assert record.command_name == "ping"
        assert record.latency_ms == 42.0
        recent = obs.get_recent_records()
        assert len(recent) == 1

    def test_metrics_tracked(self, tmp_dir):
        obs = RuntimeObservabilityPipeline(observability_dir=tmp_dir / "obs")
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
        )
        obs.record_execution(env, SpineOutcome.SUCCESS)
        obs.record_execution(env, SpineOutcome.EXECUTION_FAILED)
        stats = obs.get_stats()
        assert stats["total_recorded"] == 2
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1


# ---------------------------------------------------------------------------
# Test: Execution Orchestrator
# ---------------------------------------------------------------------------


class TestOrchestrator:
    def test_execute_safe_command(self, tmp_dir, adapter_manager):
        obs = RuntimeObservabilityPipeline(observability_dir=tmp_dir / "obs")
        orch = ExecutionOrchestrator(adapter_manager, obs)
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="ping"),
            governance_evaluation=GovernanceEvaluation(
                intent_id="i1", command_name="ping", verdict=GovernanceVerdict.APPROVED
            ),
        )
        result = orch.execute(env)
        assert result.succeeded
        assert result.command_name == "ping"

    def test_governance_denied_blocks(self, tmp_dir, adapter_manager):
        obs = RuntimeObservabilityPipeline(observability_dir=tmp_dir / "obs")
        orch = ExecutionOrchestrator(adapter_manager, obs)
        env = ExecutionEnvelope(
            intent=InterpretedIntent(signal_id="s1", command_name="bad"),
            governance_evaluation=GovernanceEvaluation(
                intent_id="i1",
                command_name="bad",
                verdict=GovernanceVerdict.DENIED,
                denial_reasons=["forbidden"],
            ),
        )
        result = orch.execute(env)
        assert not result.succeeded
        assert result.outcome == SpineOutcome.GOVERNANCE_DENIED


# ---------------------------------------------------------------------------
# Test: Canonical Runtime Spine
# ---------------------------------------------------------------------------


class TestCanonicalSpine:
    def test_safe_command_succeeds(self, spine):
        result = spine.execute("!ping")
        assert result.succeeded
        assert result.command_name == "ping"

    def test_report_command_succeeds(self, spine):
        result = spine.execute("!constitution-report")
        assert result.succeeded

    def test_forbidden_command_denied(self, spine):
        result = spine.execute("!self-govern")
        assert not result.succeeded
        assert result.outcome == SpineOutcome.STRUCTURALLY_FORBIDDEN

    def test_unknown_command_fails_capability(self, spine):
        result = spine.execute("!nonexistent-xyz-command")
        assert not result.succeeded
        assert result.outcome == SpineOutcome.CAPABILITY_UNAVAILABLE

    def test_multiple_commands_execute(self, spine):
        commands = ["!ping", "!runtime-status", "!capabilities", "!git-status"]
        for cmd in commands:
            result = spine.execute(cmd)
            assert result.succeeded, f"Failed: {cmd}"

    def test_stats_update_after_execution(self, spine):
        spine.execute("!ping")
        spine.execute("!runtime-status")
        stats = spine.get_stats()
        assert stats["executions_count"] == 2

    def test_correlation_id_propagated(self, spine):
        result = spine.execute("!ping")
        assert result.correlation_id


# ---------------------------------------------------------------------------
# Test: Runtime Replay Engine
# ---------------------------------------------------------------------------


class TestReplayEngine:
    def test_replay_single_record(self, tmp_dir, router):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        replay = RuntimeReplayEngine(router, gov, proof_dir=tmp_dir / "replay")

        record = {
            "record_id": "obs-001",
            "command_name": "ping",
            "risk_class": "safe",
            "governance_verdict": "approved",
            "adapter_id": "",
        }
        result = replay.replay_record(record)
        assert result.checks[1].passed  # risk_class
        assert result.checks[2].passed  # governance_verdict

    def test_replay_session(self, tmp_dir, router):
        gov = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov")
        replay = RuntimeReplayEngine(router, gov, proof_dir=tmp_dir / "replay")

        records = [
            {
                "record_id": "obs-001",
                "command_name": "ping",
                "risk_class": "safe",
                "governance_verdict": "approved",
                "adapter_id": "",
            },
            {
                "record_id": "obs-002",
                "command_name": "constitution-report",
                "risk_class": "low",
                "governance_verdict": "approved",
                "adapter_id": "",
            },
        ]
        session = replay.replay_session(records, session_id="test-replay-001")
        assert session.passed_records >= 1
        assert (tmp_dir / "replay" / "replay_proof_test-replay-001.json").exists()


# ---------------------------------------------------------------------------
# Test: Replay Determinism (End-to-End)
# ---------------------------------------------------------------------------


class TestReplayDeterminism:
    def test_spine_produces_deterministic_routing(self, spine, router):
        result1 = spine.execute("!ping")
        result2 = spine.execute("!constitution-report")

        route1 = router.resolve("ping")
        route2 = router.resolve("constitution-report")

        assert route1.risk_class.value == "safe"
        assert route2.risk_class.value == "low"
        assert route1.capability == CapabilityDomain.SHELL_EXECUTION
        assert route2.capability == CapabilityDomain.REPORT_GENERATION

    def test_governance_deterministic(self, tmp_dir):
        gov1 = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov1")
        gov2 = GovernanceExecutionBridge(decisions_dir=tmp_dir / "gov2")

        intent = InterpretedIntent(signal_id="s1", command_name="ping", risk_class=RiskClass.SAFE)
        e1 = gov1.evaluate(intent)
        e2 = gov2.evaluate(intent)
        assert e1.verdict == e2.verdict
        assert e1.governance_rules_applied == e2.governance_rules_applied


# ---------------------------------------------------------------------------
# Test: Runtime Artifacts
# ---------------------------------------------------------------------------


class TestRuntimeArtifacts:
    def test_all_modules_import(self):
        from execution.runtime.execution_contracts_v1 import ExecutionSignal
        from execution.runtime.environment_registry_v1 import EnvironmentRegistry
        from execution.runtime.capability_router_v1 import CapabilityRouter
        from adapters.adapter_engine.adapter_lifecycle_manager_v1 import AdapterLifecycleManager
        from execution.runtime.runtime_execution_queue_v1 import RuntimeExecutionQueue
        from execution.runtime.governance_execution_bridge_v1 import GovernanceExecutionBridge
        from execution.runtime.runtime_observability_pipeline_v1 import RuntimeObservabilityPipeline
        from execution.runtime.execution_orchestrator_v1 import ExecutionOrchestrator
        from execution.runtime.canonical_runtime_spine_v1 import CanonicalRuntimeSpine
        from execution.runtime.runtime_replay_engine_v1 import RuntimeReplayEngine

        assert True

    def test_command_maps_consistent(self):
        for cmd in SAFE_COMMANDS:
            assert cmd in COMMAND_CAPABILITY_MAP, f"Safe command {cmd} missing from capability map"

    def test_risk_map_covers_capability_map(self):
        for cmd in COMMAND_CAPABILITY_MAP:
            assert cmd in COMMAND_RISK_MAP, f"Command {cmd} missing from risk map"

    def test_forbidden_not_in_safe(self):
        for cmd in FORBIDDEN_COMMANDS:
            assert cmd not in SAFE_COMMANDS, f"Forbidden command {cmd} in safe set"
