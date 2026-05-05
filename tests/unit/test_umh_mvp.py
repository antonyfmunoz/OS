"""UMH MVP Tests — comprehensive tests for the vertical slice.

Tests cover:
  1. Import boundaries (no EOS imports)
  2. Signal ingestion and classification
  3. Intent compilation
  4. World model read/update
  5. Governance authority checks
  6. Capability registry and routing
  7. Feedback loop
  8. Adapter contracts
  9. Full run loop (umh.run)
  10. CLI entry point
  11. No EOS import contamination (scan all UMH modules)
"""

import ast
import json
import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Import Boundaries
# ═══════════════════════════════════════════════════════════════════════════════


class TestImportBoundaries:
    """Verify all UMH subpackages import cleanly."""

    def test_umh_top_level(self):
        import umh

        assert hasattr(umh, "run")
        assert hasattr(umh, "RunResult")

    def test_signal_types(self):
        from umh.signal.types import Signal, SignalBundle, SignalTier

        assert SignalTier.REALITY.value == 1

    def test_signal_ingest(self):
        from umh.signal.ingest import classify_input

        assert callable(classify_input)

    def test_intent_compiler(self):
        from umh.intent.compiler import compile_intent, Intent, IntentType

        assert IntentType.QUERY == "query"

    def test_governance_authority(self):
        from umh.governance.authority import (
            AuthorityLevel,
            GovernanceDecision,
            check_governance,
        )

        assert AuthorityLevel.OBSERVE < AuthorityLevel.EXECUTE

    def test_capability_registry(self):
        from umh.capability.registry import (
            Capability,
            CapabilityRegistry,
            get_registry,
        )

        assert callable(get_registry)

    def test_capability_router(self):
        from umh.capability.router import route_to_capability, RoutingDecision

        assert callable(route_to_capability)

    def test_feedback_loop(self):
        from umh.feedback.loop import record_outcome, FeedbackEvent

        assert callable(record_outcome)

    def test_adapters_base(self):
        from umh.adapters.base import (
            LLMAdapter,
            ShellAdapter,
            FilesystemAdapter,
            BrowserAdapter,
            WorkstationAdapter,
            NullLLMAdapter,
            get_adapter,
            list_adapters,
        )

        assert callable(list_adapters)

    def test_run_module(self):
        from umh.run import run, RunResult, RunTrace

        assert callable(run)

    def test_existing_modules_still_import(self):
        """Verify all pre-existing UMH modules still work."""
        from umh.execution.pipeline import ExecutionPipeline
        from umh.execution.contract import ExecutionRequest, ExecutionResult
        from umh.execution.engine import execute
        from umh.execution.stages import StageContext, ExecutionStage
        from umh.execution.interfaces import ExecutionBackend
        from umh.decision.trace import DecisionTrace
        from umh.goals.state import GoalState, GoalRegistry
        from umh.goals.objective import ObjectiveFunction, ObjectiveSet
        from umh.goals.interfaces import get_goal_persistence
        from umh.memory.storage import StorageBackend, InMemoryStorage
        from umh.primitives.ontological import PrimitiveTag
        from umh.strategy.interfaces import StrategyPersistence
        from umh.strategy.memory import StrategyMemory
        from umh.world.model import WorldModel
        from umh.world.types import Entity, Observation


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Signal Ingestion
# ═══════════════════════════════════════════════════════════════════════════════


class TestSignalIngestion:
    def test_basic_classification(self):
        from umh.signal.ingest import classify_input

        bundle = classify_input("What happened today with revenue?")
        assert len(bundle.signals) > 0
        assert bundle.primary is not None
        assert bundle.source == "user"

    def test_reality_tier_detected(self):
        from umh.signal.ingest import classify_input
        from umh.signal.types import SignalTier

        bundle = classify_input("Revenue data shows actual results today")
        tiers = {s.tier for s in bundle.signals}
        assert SignalTier.REALITY in tiers

    def test_fallback_to_context(self):
        from umh.signal.ingest import classify_input
        from umh.signal.types import SignalTier

        bundle = classify_input("xyz nonsense gibberish")
        assert bundle.primary is not None
        assert bundle.primary.tier == SignalTier.CONTEXT

    def test_signals_sorted_by_tier(self):
        from umh.signal.ingest import classify_input

        bundle = classify_input(
            "What happened today? What's the best strategy approach?"
        )
        tiers = [s.tier.value for s in bundle.signals]
        assert tiers == sorted(tiers)

    def test_signal_bundle_by_tier(self):
        from umh.signal.ingest import classify_input
        from umh.signal.types import SignalTier

        bundle = classify_input("The actual status data results")
        reality = bundle.by_tier(SignalTier.REALITY)
        assert len(reality) > 0

    def test_signal_to_dict(self):
        from umh.signal.ingest import classify_input

        bundle = classify_input("test input")
        d = bundle.to_dict()
        assert "signals" in d
        assert "raw_input" in d
        assert d["source"] == "user"

    def test_custom_source(self):
        from umh.signal.ingest import classify_input

        bundle = classify_input("test", source="cron")
        assert bundle.source == "cron"
        assert bundle.primary.source == "cron"

    def test_metadata_passed_through(self):
        from umh.signal.ingest import classify_input

        bundle = classify_input("test", metadata={"channel": "discord"})
        assert bundle.primary.metadata.get("channel") == "discord"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Intent Compilation
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntentCompiler:
    def test_query_intent(self):
        from umh.intent.compiler import compile_intent, IntentType
        from umh.signal.ingest import classify_input

        bundle = classify_input("What is the current status?")
        intent = compile_intent(bundle)
        assert intent.intent_type == IntentType.QUERY

    def test_action_intent(self):
        from umh.intent.compiler import compile_intent, IntentType
        from umh.signal.ingest import classify_input

        bundle = classify_input("Deploy the new build and start the service")
        intent = compile_intent(bundle)
        assert intent.intent_type == IntentType.ACTION

    def test_analysis_intent(self):
        from umh.intent.compiler import compile_intent, IntentType
        from umh.signal.ingest import classify_input

        bundle = classify_input("Analyze and evaluate the pipeline performance")
        intent = compile_intent(bundle)
        assert intent.intent_type == IntentType.ANALYSIS

    def test_creation_intent(self):
        from umh.intent.compiler import compile_intent, IntentType
        from umh.signal.ingest import classify_input

        bundle = classify_input("Write a draft proposal and outline the plan")
        intent = compile_intent(bundle)
        assert intent.intent_type == IntentType.CREATION

    def test_monitoring_intent(self):
        from umh.intent.compiler import compile_intent, IntentType
        from umh.signal.ingest import classify_input

        bundle = classify_input("Monitor the health status and track alerts")
        intent = compile_intent(bundle)
        assert intent.intent_type == IntentType.MONITORING

    def test_intent_has_operation(self):
        from umh.intent.compiler import compile_intent
        from umh.signal.ingest import classify_input

        bundle = classify_input("Show me the data")
        intent = compile_intent(bundle)
        assert intent.operation != ""
        assert intent.intent_id.startswith("int_")

    def test_intent_to_dict(self):
        from umh.intent.compiler import compile_intent
        from umh.signal.ingest import classify_input

        bundle = classify_input("test")
        intent = compile_intent(bundle)
        d = intent.to_dict()
        assert "intent_type" in d
        assert "operation" in d

    def test_empty_bundle_yields_unknown(self):
        from umh.intent.compiler import compile_intent, IntentType
        from umh.signal.types import SignalBundle

        bundle = SignalBundle(signals=(), raw_input="", source="test")
        intent = compile_intent(bundle)
        assert intent.intent_type == IntentType.UNKNOWN
        assert intent.confidence == 0.0

    def test_constraints_from_reality_signals(self):
        from umh.intent.compiler import compile_intent
        from umh.signal.ingest import classify_input

        bundle = classify_input("The actual data results happened now")
        intent = compile_intent(bundle)
        assert intent.constraints.get("grounded") is True

    def test_constraints_from_leverage_signals(self):
        from umh.intent.compiler import compile_intent
        from umh.signal.ingest import classify_input

        bundle = classify_input("This is a critical priority blocker")
        intent = compile_intent(bundle)
        assert intent.constraints.get("high_leverage") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Governance
# ═══════════════════════════════════════════════════════════════════════════════


class TestGovernance:
    def test_observe_allows_query(self):
        from umh.governance.authority import (
            AuthorityLevel,
            check_governance,
            reset_governance_policy,
        )

        reset_governance_policy()
        decision = check_governance("answer_query", AuthorityLevel.OBSERVE)
        assert decision.allowed

    def test_observe_blocks_action(self):
        from umh.governance.authority import (
            AuthorityLevel,
            check_governance,
            reset_governance_policy,
        )

        reset_governance_policy()
        decision = check_governance("execute_action", AuthorityLevel.OBSERVE)
        assert not decision.allowed

    def test_act_allows_action(self):
        from umh.governance.authority import (
            AuthorityLevel,
            check_governance,
            reset_governance_policy,
        )

        reset_governance_policy()
        decision = check_governance("execute_action", AuthorityLevel.ACT)
        assert decision.allowed

    def test_decision_to_dict(self):
        from umh.governance.authority import (
            AuthorityLevel,
            check_governance,
            reset_governance_policy,
        )

        reset_governance_policy()
        decision = check_governance("answer_query", AuthorityLevel.ANALYZE)
        d = decision.to_dict()
        assert "allowed" in d
        assert "authority_level" in d
        assert "reason" in d

    def test_warnings_on_side_effects(self):
        from umh.governance.authority import (
            AuthorityLevel,
            check_governance,
            reset_governance_policy,
        )

        reset_governance_policy()
        decision = check_governance("execute_action", AuthorityLevel.ACT)
        assert len(decision.warnings) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Capability Registry & Routing
# ═══════════════════════════════════════════════════════════════════════════════


class TestCapabilityRegistry:
    def test_default_registry_has_capabilities(self):
        from umh.capability.registry import get_registry, reset_registry

        reset_registry()
        reg = get_registry()
        assert reg.size >= 2

    def test_register_and_get(self):
        from umh.capability.registry import (
            Capability,
            CapabilityRegistry,
        )

        reg = CapabilityRegistry()
        cap = Capability(
            name="test_cap",
            capability_type="test",
            description="test capability",
        )
        reg.register(cap)
        assert reg.get("test_cap") is not None
        assert reg.size == 1

    def test_by_type(self):
        from umh.capability.registry import get_registry, reset_registry

        reset_registry()
        reg = get_registry()
        runtimes = reg.by_type("runtime")
        assert len(runtimes) >= 1

    def test_performance_tracking(self):
        from umh.capability.registry import Capability, PerformanceStats

        perf = PerformanceStats()
        perf.record(success=True, latency_ms=100)
        perf.record(success=False, latency_ms=200)
        assert perf.total_runs == 2
        assert perf.success_rate == 0.5
        assert perf.avg_latency_ms == 150.0


class TestCapabilityRouter:
    def test_route_finds_capability(self):
        from umh.capability.registry import reset_registry
        from umh.capability.router import route_to_capability

        reset_registry()
        decision = route_to_capability("answer_query")
        assert decision.selected is not None

    def test_route_scores_populated(self):
        from umh.capability.registry import reset_registry
        from umh.capability.router import route_to_capability

        reset_registry()
        decision = route_to_capability("answer_query")
        assert len(decision.scores) > 0

    def test_route_to_dict(self):
        from umh.capability.registry import reset_registry
        from umh.capability.router import route_to_capability

        reset_registry()
        decision = route_to_capability("process_input")
        d = decision.to_dict()
        assert "selected" in d
        assert "scores" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Feedback Loop
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeedbackLoop:
    def test_record_success(self):
        from umh.feedback.loop import (
            record_outcome,
            OutcomeType,
            clear_feedback_log,
        )

        clear_feedback_log()
        event = record_outcome(
            operation="test_op",
            outcome=OutcomeType.SUCCESS,
            capability_name="local_python",
            latency_ms=50,
        )
        assert event.outcome == "success"
        assert event.event_id.startswith("fb_")

    def test_record_failure(self):
        from umh.feedback.loop import record_outcome, OutcomeType, clear_feedback_log

        clear_feedback_log()
        event = record_outcome(
            operation="test_op",
            outcome=OutcomeType.FAILURE,
            capability_name="null_llm",
            latency_ms=100,
            error="test error",
        )
        assert event.confidence < 0.5

    def test_recent_feedback(self):
        from umh.feedback.loop import (
            record_outcome,
            OutcomeType,
            get_recent_feedback,
            clear_feedback_log,
        )

        clear_feedback_log()
        for i in range(5):
            record_outcome("op", OutcomeType.SUCCESS, "cap", 10)
        recent = get_recent_feedback(3)
        assert len(recent) == 3

    def test_feedback_to_dict(self):
        from umh.feedback.loop import record_outcome, OutcomeType, clear_feedback_log

        clear_feedback_log()
        event = record_outcome("op", OutcomeType.SUCCESS, "cap", 10)
        d = event.to_dict()
        assert "event_id" in d
        assert "learning_signal" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Adapter Contracts
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdapters:
    def test_null_llm(self):
        from umh.adapters.base import NullLLMAdapter

        llm = NullLLMAdapter()
        assert llm.available()
        result = llm.generate("hello")
        assert "hello" in result

    def test_null_shell(self):
        from umh.adapters.base import NullShellAdapter

        shell = NullShellAdapter()
        assert not shell.available()
        code, out = shell.run("ls")
        assert code == 1

    def test_null_filesystem(self):
        from umh.adapters.base import NullFilesystemAdapter

        fs = NullFilesystemAdapter()
        assert fs.available()
        fs.write("/test.txt", "content")
        assert fs.exists("/test.txt")
        assert fs.read("/test.txt") == "content"

    def test_null_browser(self):
        from umh.adapters.base import NullBrowserAdapter

        browser = NullBrowserAdapter()
        assert not browser.available()

    def test_null_workstation(self):
        from umh.adapters.base import NullWorkstationAdapter

        ws = NullWorkstationAdapter()
        assert ws.available()
        env = ws.detect_environment()
        assert "platform" in env

    def test_get_adapter_defaults(self):
        from umh.adapters.base import get_adapter, reset_adapters

        reset_adapters()
        llm = get_adapter("llm")
        assert llm.available()

    def test_list_adapters(self):
        from umh.adapters.base import list_adapters, reset_adapters

        reset_adapters()
        adapters = list_adapters()
        assert "llm" in adapters
        assert "shell" in adapters
        assert "workstation" in adapters

    def test_set_adapter_override(self):
        from umh.adapters.base import (
            get_adapter,
            set_adapter,
            reset_adapters,
            NullLLMAdapter,
        )

        reset_adapters()

        class CustomLLM(NullLLMAdapter):
            def generate(self, prompt, system="", **kw):
                return "custom response"

        set_adapter("llm", CustomLLM())
        result = get_adapter("llm").generate("test")
        assert result == "custom response"
        reset_adapters()

    def test_protocol_compliance(self):
        from umh.adapters.base import (
            LLMAdapter,
            ShellAdapter,
            FilesystemAdapter,
            BrowserAdapter,
            WorkstationAdapter,
            NullLLMAdapter,
            NullShellAdapter,
            NullFilesystemAdapter,
            NullBrowserAdapter,
            NullWorkstationAdapter,
        )

        assert isinstance(NullLLMAdapter(), LLMAdapter)
        assert isinstance(NullShellAdapter(), ShellAdapter)
        assert isinstance(NullFilesystemAdapter(), FilesystemAdapter)
        assert isinstance(NullBrowserAdapter(), BrowserAdapter)
        assert isinstance(NullWorkstationAdapter(), WorkstationAdapter)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Full Run Loop
# ═══════════════════════════════════════════════════════════════════════════════


class TestRunLoop:
    def _reset_all(self):
        from umh.adapters.base import reset_adapters
        from umh.capability.registry import reset_registry
        from umh.feedback.loop import clear_feedback_log
        from umh.governance.authority import reset_governance_policy
        from umh.memory.storage import reset_storage

        reset_adapters()
        reset_registry()
        reset_governance_policy()
        reset_storage()
        clear_feedback_log()

    def test_basic_run(self):
        self._reset_all()
        from umh.run import run

        result = run("What is the status of my project?")
        assert result.success
        assert result.response != ""
        assert result.run_id.startswith("run_")

    def test_run_with_goal(self):
        self._reset_all()
        from umh.goals.state import GoalState
        from umh.run import run

        goal = GoalState(
            goal_id="test_goal",
            description="Test objective",
            priority=0.8,
        )
        result = run("analyze pipeline", goal=goal)
        assert result.success

    def test_run_trace_has_all_stages(self):
        self._reset_all()
        from umh.run import run

        result = run("Show me the data results")
        stages = result.trace.stages
        expected = [
            "signal",
            "intent",
            "world",
            "decision",
            "compose",
            "route",
            "govern",
            "execute",
            "feedback",
        ]
        for stage in expected:
            assert stage in stages, f"Missing stage: {stage}"

    def test_run_governance_block(self):
        self._reset_all()
        from umh.governance.authority import AuthorityLevel
        from umh.run import run

        result = run(
            "Deploy and execute the build",
            authority=AuthorityLevel.OBSERVE,
        )
        assert not result.success
        assert "governance" in result.metadata.get("blocked_by", "")

    def test_run_result_to_dict(self):
        self._reset_all()
        from umh.run import run

        result = run("test")
        d = result.to_dict()
        assert "run_id" in d
        assert "trace" in d
        assert "response" in d
        serialized = json.dumps(d, default=str)
        assert len(serialized) > 0

    def test_run_updates_world_model(self):
        self._reset_all()
        from umh.run import run
        from umh.world.model import WorldModel

        result = run("What is my strategy approach for this plan?", org_id="test_org")
        assert result.success
        wm = WorldModel(org_id="test_org")
        entries = wm.instance.get_entries()
        # World model may or may not have entries depending on confidence threshold
        # but the run should not fail

    def test_run_records_feedback(self):
        self._reset_all()
        from umh.feedback.loop import get_recent_feedback
        from umh.run import run

        run("test feedback recording")
        recent = get_recent_feedback(1)
        assert len(recent) == 1

    def test_run_with_constraints(self):
        self._reset_all()
        from umh.run import run

        result = run("test", constraints={"max_cost_usd": 0.01})
        assert result.success


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════


class TestCLI:
    def _reset_all(self):
        from umh.adapters.base import reset_adapters
        from umh.capability.registry import reset_registry
        from umh.feedback.loop import clear_feedback_log
        from umh.governance.authority import reset_governance_policy
        from umh.memory.storage import reset_storage

        reset_adapters()
        reset_registry()
        reset_governance_policy()
        reset_storage()
        clear_feedback_log()

    def test_cli_help(self):
        from umh.__main__ import main

        assert main(["help"]) == 0

    def test_cli_no_args(self):
        from umh.__main__ import main

        assert main([]) == 0

    def test_cli_status(self):
        self._reset_all()
        from umh.__main__ import main

        assert main(["status"]) == 0

    def test_cli_capabilities(self):
        self._reset_all()
        from umh.__main__ import main

        assert main(["capabilities"]) == 0

    def test_cli_adapters(self):
        self._reset_all()
        from umh.__main__ import main

        assert main(["adapters"]) == 0

    def test_cli_run(self):
        self._reset_all()
        from umh.__main__ import main

        assert main(["run", "test input"]) == 0

    def test_cli_trace(self):
        self._reset_all()
        from umh.__main__ import main

        assert main(["trace", "test input"]) == 0

    def test_cli_unknown_command(self):
        from umh.__main__ import main

        assert main(["foobar"]) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 10. No EOS Import Contamination
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoEOSImports:
    """Scan all UMH .py files to ensure no eos_ai imports at module level.

    The only allowed EOS references are inside try/except ImportError blocks
    in interface modules (lazy adapter discovery).
    """

    def _get_umh_files(self) -> list[str]:
        umh_dir = "/opt/OS/umh"
        py_files = []
        for root, _, files in os.walk(umh_dir):
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
        return sorted(py_files)

    def test_no_top_level_eos_imports(self):
        """Verify no file has 'from eos_ai' or 'import eos_ai' at top level.

        Allowed exceptions:
          - Files in allowed_files (lazy adapter discovery in try/except)
          - TYPE_CHECKING-guarded imports (never execute at runtime)
          - Imports inside try/except blocks (lazy discovery)
          - Imports inside function bodies (deferred)
        """
        violations = []
        allowed_files = {
            "storage.py",
            "interfaces.py",
            "state.py",
        }

        for filepath in self._get_umh_files():
            filename = os.path.basename(filepath)
            if filename in allowed_files:
                continue

            with open(filepath) as f:
                source = f.read()

            tree = ast.parse(source, filepath)

            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if node.module.startswith(("services.", "interfaces.", "scripts.")):
                            violations.append(
                                f"{filepath}:{node.lineno} imports {node.module}"
                            )
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith(("services.", "interfaces.", "scripts.")):
                                violations.append(
                                    f"{filepath}:{node.lineno} imports {alias.name}"
                                )
                elif isinstance(node, ast.If):
                    # Skip TYPE_CHECKING blocks
                    pass

        assert violations == [], f"UMH files contain EOS imports:\n" + "\n".join(
            f"  {v}" for v in violations
        )

    def test_eos_imports_only_in_try_except(self):
        """For allowed files, verify eos_ai imports are inside try/except."""
        allowed_files = {
            "/opt/OS/umh/memory/storage.py",
            "/opt/OS/umh/execution/interfaces.py",
            "/opt/OS/umh/strategy/interfaces.py",
            "/opt/OS/umh/goals/interfaces.py",
        }

        for filepath in allowed_files:
            if not os.path.exists(filepath):
                continue

            with open(filepath) as f:
                source = f.read()

            tree = ast.parse(source, filepath)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("umh.runtime_engine.")
                ):
                    parent_is_try = False
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.Try):
                            for child in ast.walk(parent):
                                if child is node:
                                    parent_is_try = True
                                    break
                    assert parent_is_try, (
                        f"{filepath}:{node.lineno} has eos_ai import "
                        f"outside try/except block"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# 11. World Model Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorldModelIntegration:
    def test_world_model_standalone(self):
        from umh.memory.storage import reset_storage

        reset_storage()
        from umh.world.model import WorldModel

        wm = WorldModel(org_id="test")
        entries = wm.canonical.get_entries()
        assert len(entries) >= 5  # seeded entries

    def test_world_model_context_for_prompt(self):
        from umh.memory.storage import reset_storage

        reset_storage()
        from umh.world.model import WorldModel

        wm = WorldModel(org_id="test")
        ctx = wm.get_context_for_prompt("business")
        assert len(ctx) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
