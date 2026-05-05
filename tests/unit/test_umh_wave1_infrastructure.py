"""Wave 1 validation — UMH infrastructure subsystem tests.

Proves that all Wave 1 subsystems exist, import correctly, and
preserve backward compatibility with Wave 0 code.
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/opt/OS")


class TestCoreClock:
    """core/clock.py is the single source for timing utilities."""

    def test_now_ms_returns_int(self):
        from umh.core.clock import now_ms

        result = now_ms()
        assert isinstance(result, int)
        assert result > 0

    def test_iso_now_returns_string(self):
        from umh.core.clock import iso_now

        result = iso_now()
        assert isinstance(result, str)
        assert "T" in result

    def test_no_local_now_ms_in_run(self):
        """run.py must not define its own _now_ms."""
        import ast

        with open("/opt/OS/umh/run.py") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_now_ms":
                pytest.fail("run.py still defines local _now_ms()")

    def test_no_local_now_ms_in_engine(self):
        """execution/engine.py must not define its own _now_ms."""
        import ast

        with open("/opt/OS/umh/execution/engine.py") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_now_ms":
                pytest.fail("execution/engine.py still defines local _now_ms()")

    def test_no_local_now_ms_in_harness(self):
        """execution/harness.py must not define its own _now_ms."""
        import ast

        with open("/opt/OS/umh/execution/harness.py") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_now_ms":
                pytest.fail("execution/harness.py still defines local _now_ms()")

    def test_no_local_now_ms_in_pipeline(self):
        """execution/pipeline.py must not define its own _now_ms."""
        import ast

        with open("/opt/OS/umh/execution/pipeline.py") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_now_ms":
                pytest.fail("execution/pipeline.py still defines local _now_ms()")


class TestProtocols:
    """All 13 protocol modules import cleanly."""

    def test_signals_protocol(self):
        from umh.protocols.signals import SignalClassifier, SignalFilter

        assert SignalClassifier is not None
        assert SignalFilter is not None

    def test_interpretation_protocol(self):
        from umh.protocols.interpretation import IntentCompiler

        assert IntentCompiler is not None

    def test_execution_protocol(self):
        from umh.protocols.execution import (
            ExecutionBackend,
            ExecutionObserver,
            ExecutionStage,
            CapabilityGate,
            HarnessObserver,
            StepExecutor,
            TaskPlanner,
        )

    def test_capabilities_protocol(self):
        from umh.protocols.capabilities import PersistenceBackend

        assert PersistenceBackend is not None

    def test_adapters_protocol(self):
        from umh.protocols.adapters import (
            BrowserAdapter,
            FilesystemAdapter,
            LLMAdapter,
            ShellAdapter,
            WorkstationAdapter,
        )

    def test_governance_protocol(self):
        from umh.protocols.governance import GovernancePolicy

        assert GovernancePolicy is not None

    def test_persistence_protocol(self):
        from umh.protocols.persistence import GoalPersistence, StrategyPersistence

        assert GoalPersistence is not None
        assert StrategyPersistence is not None

    def test_memory_protocol(self):
        from umh.protocols.memory import EpisodicMemory, MemoryStore

        assert MemoryStore is not None
        assert EpisodicMemory is not None

    def test_outcome_protocol(self):
        from umh.protocols.outcome import EventLogger, OutcomeRecorder

        assert EventLogger is not None
        assert OutcomeRecorder is not None

    def test_planning_protocol(self):
        from umh.protocols.planning import PlanEvaluator, TaskPlanner

        assert PlanEvaluator is not None
        assert TaskPlanner is not None

    def test_world_protocol(self):
        from umh.protocols.world import WorldModelReader, WorldModelWriter

        assert WorldModelReader is not None
        assert WorldModelWriter is not None

    def test_workstation_protocol(self):
        from umh.protocols.workstation import EnvironmentDetector, WorkstationAdapter

        assert EnvironmentDetector is not None
        assert WorkstationAdapter is not None

    def test_security_protocol(self):
        from umh.protocols.security import AccessPolicy, SecretProvider

        assert AccessPolicy is not None
        assert SecretProvider is not None


class TestStorageSubsystem:
    """umh.storage is the canonical location; memory.storage re-exports."""

    def test_canonical_import(self):
        from umh.storage import InMemoryStorage, StorageBackend

        assert StorageBackend is not None
        store = InMemoryStorage()
        store.put("k", "v")
        assert store.get("k") == "v"

    def test_backward_compat_import(self):
        from umh.memory.storage import InMemoryStorage, StorageBackend

        assert StorageBackend is not None
        store = InMemoryStorage()
        store.put("k", "v")
        assert store.get("k") == "v"

    def test_same_classes(self):
        from umh.memory.storage import StorageBackend as A
        from umh.storage import StorageBackend as B

        assert A is B

    def test_get_storage_still_works(self):
        from umh.memory.storage import get_storage

        store = get_storage()
        assert hasattr(store, "get")
        assert hasattr(store, "put")
        assert hasattr(store, "all_keys")


class TestMemoryStore:
    """umh.memory.store provides intelligence-layer memory."""

    def test_remember_recall(self):
        from umh.memory.store import InMemoryStore

        store = InMemoryStore()
        store.remember("fact1", "Python was created by Guido", tags=["python"])
        results = store.recall("python")
        assert len(results) == 1
        assert results[0]["content"] == "Python was created by Guido"

    def test_forget(self):
        from umh.memory.store import InMemoryStore

        store = InMemoryStore()
        store.remember("temp", "temporary data")
        assert store.forget("temp") is True
        assert store.forget("nonexistent") is False
        assert store.recall("temporary") == []

    def test_singleton(self):
        from umh.memory.store import get_memory_store, reset_memory_store

        reset_memory_store()
        s1 = get_memory_store()
        s2 = get_memory_store()
        assert s1 is s2
        reset_memory_store()


class TestEnvironments:
    """umh.environments detects runtime context."""

    def test_detect_returns_info(self):
        from umh.environments.detector import EnvironmentInfo, detect_environment

        env = detect_environment()
        assert isinstance(env, EnvironmentInfo)
        assert env.platform in ("Linux", "Darwin", "Windows")

    def test_to_dict(self):
        from umh.environments.detector import detect_environment

        d = detect_environment().to_dict()
        assert "environment_type" in d
        assert "python_version" in d


class TestWorkstation:
    """umh.workstation models the operator environment."""

    def test_detect_workstation(self):
        from umh.workstation.profile import WorkstationProfile, detect_workstation

        ws = detect_workstation()
        assert isinstance(ws, WorkstationProfile)
        assert ws.has_capability("shell") is True

    def test_boot_sequence(self):
        from umh.workstation.profile import BootSequence

        boot = BootSequence(steps=["a", "b", "c"])
        assert not boot.all_done
        boot.mark_completed("a")
        boot.mark_completed("b")
        boot.mark_completed("c")
        assert boot.all_done
        assert boot.success

    def test_work_mode(self):
        from umh.workstation.profile import WorkMode

        assert WorkMode.FULL.value == "full"
        assert WorkMode.HEADLESS.value == "headless"


class TestSecurity:
    """umh.security provides access control."""

    def test_allow_all_policy(self):
        from umh.security.access import AllowAllPolicy

        policy = AllowAllPolicy()
        allowed, reason = policy.check_access("user", "/data", "read")
        assert allowed is True

    def test_deny_all_policy(self):
        from umh.security.access import DenyAllPolicy

        policy = DenyAllPolicy()
        allowed, reason = policy.check_access("user", "/data", "read")
        assert allowed is False

    def test_check_access_function(self):
        from umh.security.access import check_access, reset_access_policy

        reset_access_policy()
        decision = check_access("admin", "/resource", "write")
        assert decision.allowed is True
        assert decision.principal == "admin"
        reset_access_policy()


class TestNullAdapters:
    """umh.adapters.null centralizes all null implementations."""

    def test_all_null_adapters_importable(self):
        from umh.adapters.null import (
            NullBrowserAdapter,
            NullExecutionBackend,
            NullExecutionObserver,
            NullFilesystemAdapter,
            NullGoalPersistence,
            NullLLMAdapter,
            NullLogger,
            NullShellAdapter,
            NullStrategyPersistence,
            NullWorkstationAdapter,
        )


class TestInterfaceCLI:
    """umh.interfaces.cli is the canonical CLI implementation."""

    def test_main_callable(self):
        from umh.interfaces.cli import main

        assert callable(main)

    def test_help_returns_zero(self):
        from umh.interfaces.cli import main

        assert main(["help"]) == 0

    def test_main_delegates_from_dunder_main(self):
        """__main__.py delegates to interfaces.cli.main."""
        with open("/opt/OS/umh/__main__.py") as fh:
            source = fh.read()
        assert "from umh.interfaces.cli import main" in source


class TestWave0StillPasses:
    """Wave 1 changes must not break Wave 0 guarantees."""

    def test_all_subsystems_still_importable(self):
        import umh.adapters.base
        import umh.adapters.bridge
        import umh.adapters.llm
        import umh.capability.registry
        import umh.capability.router
        import umh.context.builder
        import umh.context.budget
        import umh.context.types
        import umh.decision.trace
        import umh.execution.contract
        import umh.execution.engine
        import umh.execution.harness
        import umh.execution.interfaces
        import umh.execution.pipeline
        import umh.execution.quality
        import umh.execution.stages
        import umh.feedback.dynamics
        import umh.feedback.loop
        import umh.goals.engine
        import umh.goals.interfaces
        import umh.goals.objective
        import umh.goals.state
        import umh.governance.authority
        import umh.governance.capability
        import umh.governance.governor
        import umh.intent.compiler
        import umh.memory.storage
        import umh.primitives.ontological
        import umh.signal.event_bus
        import umh.signal.ingest
        import umh.signal.types
        import umh.strategy.interfaces
        import umh.strategy.memory
        import umh.world.calibration
        import umh.world.dynamics_adapter
        import umh.world.model
        import umh.world.reasoning
        import umh.world.simulation
        import umh.world.state
        import umh.world.substrate
        import umh.world.types

    def test_run_import(self):
        from umh import RunResult, RunTrace, run

        assert callable(run)

    def test_dispatch_prompt(self):
        from umh.execution.engine import dispatch_prompt

        assert callable(dispatch_prompt)
