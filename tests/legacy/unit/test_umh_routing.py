"""Tests for UMH multi-dimensional capability routing.

Covers:
  1. Capability registration — llm_generation registered when adapter available
  2. Router scoring — LLM selected for NL generation, local_python for deterministic
  3. Operation profiles — each operation has correct generation/determinism weights
  4. Fallback chain — correct ordering when LLM unavailable
  5. Compose layer — system prompt for LLM, flat prompt for runtime
  6. End-to-end routing — full pipeline routes correctly by input type
  7. No EOS imports in modified files
"""

import ast
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, "/opt/OS")


def _reset_all():
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


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Capability Registration
# ═══════════════════════════════════════════════════════════════════════════════


class TestLLMCapabilityRegistration:
    def test_llm_generation_registered_when_ollama_available(self):
        _reset_all()
        from umh.capability.registry import get_registry

        reg = get_registry()
        cap = reg.get("llm_generation")
        assert cap is not None
        assert cap.capability_type == "llm"
        assert cap.available

    def test_llm_generation_has_metadata(self):
        _reset_all()
        from umh.capability.registry import get_registry

        cap = get_registry().get("llm_generation")
        assert cap is not None
        assert "generation_quality" in cap.metadata
        assert "determinism" in cap.metadata
        assert "adapter" in cap.metadata
        assert "model" in cap.metadata
        assert cap.metadata["generation_quality"] > 0.5
        assert cap.metadata["determinism"] < 0.5

    def test_local_python_has_scoring_metadata(self):
        _reset_all()
        from umh.capability.registry import get_registry

        cap = get_registry().get("local_python")
        assert cap is not None
        assert cap.metadata["determinism"] == 1.0
        assert cap.metadata["generation_quality"] == 0.0

    def test_null_llm_still_registered(self):
        _reset_all()
        from umh.capability.registry import get_registry

        cap = get_registry().get("null_llm")
        assert cap is not None
        assert cap.quality_score == 0.1

    def test_three_capabilities_registered(self):
        _reset_all()
        from umh.capability.registry import get_registry

        reg = get_registry()
        assert reg.size >= 3

    def test_llm_generation_not_registered_without_adapter(self):
        from umh.capability.registry import CapabilityRegistry, reset_registry

        reset_registry()

        with patch.dict(os.environ, {"UMH_OLLAMA_HOST": "http://127.0.0.1:59999"}):
            os.environ.pop("UMH_LLM_URL", None)
            from umh.capability import registry as reg_mod

            old = reg_mod._REGISTRY
            reg_mod._REGISTRY = None
            r = reg_mod.get_registry()
            assert r.get("llm_generation") is None
            assert r.size == 2
            reg_mod._REGISTRY = old

        reset_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Router Scoring
# ═══════════════════════════════════════════════════════════════════════════════


class TestRouterScoring:
    def test_llm_wins_for_answer_query(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("answer_query")
        assert d.selected is not None
        assert d.selected.name == "llm_generation"

    def test_llm_wins_for_create_artifact(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("create_artifact")
        assert d.selected is not None
        assert d.selected.name == "llm_generation"

    def test_llm_wins_for_run_analysis(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("run_analysis")
        assert d.selected is not None
        assert d.selected.name == "llm_generation"

    def test_llm_wins_for_process_input(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("process_input")
        assert d.selected is not None
        assert d.selected.name == "llm_generation"

    def test_local_python_wins_for_execute_action(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("execute_action")
        assert d.selected is not None
        assert d.selected.name == "local_python"

    def test_local_python_wins_for_check_status(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("check_status")
        assert d.selected is not None
        assert d.selected.name == "local_python"

    def test_scores_are_populated(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("answer_query")
        assert "llm_generation" in d.scores
        assert "local_python" in d.scores
        assert "null_llm" in d.scores

    def test_llm_score_higher_than_local_python_for_query(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("answer_query")
        assert d.scores["llm_generation"] > d.scores["local_python"]

    def test_local_python_score_higher_than_llm_for_action(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("execute_action")
        assert d.scores["local_python"] > d.scores["llm_generation"]

    def test_routing_decision_serializable(self):
        _reset_all()
        import json
        from umh.capability.router import route_to_capability

        d = route_to_capability("answer_query")
        serialized = json.dumps(d.to_dict(), default=str)
        assert len(serialized) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Fallback Chain
# ═══════════════════════════════════════════════════════════════════════════════


class TestFallbackChain:
    def test_fallback_chain_for_query(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("answer_query")
        fallback_names = [c.name for c in d.fallback_chain]
        assert "local_python" in fallback_names
        assert "null_llm" in fallback_names

    def test_fallback_chain_for_action(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("execute_action")
        assert d.selected.name == "local_python"
        fallback_names = [c.name for c in d.fallback_chain]
        assert "llm_generation" in fallback_names

    def test_fallback_when_no_capabilities(self):
        from umh.capability.registry import (
            CapabilityRegistry,
            set_registry,
            reset_registry,
        )
        from umh.capability.router import route_to_capability

        set_registry(CapabilityRegistry())
        d = route_to_capability("answer_query")
        assert d.selected is None
        assert len(d.fallback_chain) == 0
        reset_registry()

    def test_budget_constraint_penalizes_expensive(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("answer_query", constraints={"max_cost_usd": 0.0001})
        assert (
            d.scores["llm_generation"]
            < route_to_capability("answer_query").scores["llm_generation"]
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Compose Layer
# ═══════════════════════════════════════════════════════════════════════════════


class TestComposeLayer:
    def test_llm_compose_produces_system_prompt(self):
        from umh.goals.state import GoalState
        from umh.intent.compiler import compile_intent
        from umh.run import _compose_prompt
        from umh.signal.ingest import classify_input

        bundle = classify_input("What should I focus on?")
        intent = compile_intent(bundle)
        goal = GoalState(goal_id="g1", description="Grow revenue", priority=0.9)

        prompt, system = _compose_prompt(
            "What should I focus on?", intent, "Some context", goal, uses_llm=True
        )
        assert prompt == "What should I focus on?"
        assert "Grow revenue" in system
        assert "Some context" in system
        assert intent.operation in system

    def test_runtime_compose_flat_prompt(self):
        from umh.goals.state import GoalState
        from umh.intent.compiler import compile_intent
        from umh.run import _compose_prompt
        from umh.signal.ingest import classify_input

        bundle = classify_input("Calculate something")
        intent = compile_intent(bundle)
        goal = GoalState(goal_id="g1", description="Test", priority=0.5)

        prompt, system = _compose_prompt(
            "Calculate something", intent, "Some context", goal, uses_llm=False
        )
        assert "Calculate something" in prompt
        assert "[Objective: Test]" in prompt
        assert system == ""

    def test_llm_compose_without_goal(self):
        from umh.goals.state import GoalState
        from umh.intent.compiler import compile_intent
        from umh.run import _compose_prompt
        from umh.signal.ingest import classify_input

        bundle = classify_input("Tell me a joke")
        intent = compile_intent(bundle)
        goal = GoalState(goal_id="none", description="", priority=0.0, active=False)

        prompt, system = _compose_prompt(
            "Tell me a joke", intent, "", goal, uses_llm=True
        )
        assert prompt == "Tell me a joke"
        assert "objective" not in system.lower()

    def test_llm_compose_includes_constraints(self):
        from umh.goals.state import GoalState
        from umh.intent.compiler import compile_intent
        from umh.run import _compose_prompt
        from umh.signal.ingest import classify_input

        bundle = classify_input("What happened today with critical priority data?")
        intent = compile_intent(bundle)
        goal = GoalState(goal_id="g1", description="", priority=0.0)

        prompt, system = _compose_prompt(
            "What happened?", intent, "", goal, uses_llm=True
        )
        if intent.constraints:
            assert "Constraints:" in system


# ═══════════════════════════════════════════════════════════════════════════════
# 5. End-to-End Routing
# ═══════════════════════════════════════════════════════════════════════════════


class TestEndToEndRouting:
    def test_nl_query_routes_to_llm(self):
        _reset_all()
        from umh.run import run

        result = run("What should I focus on today?")
        assert result.success
        assert result.capability_used == "llm_generation"
        assert result.trace.stages["compose"]["target"] == "llm"
        assert result.trace.stages["compose"]["has_system_prompt"]

    def test_action_routes_to_local_python(self):
        _reset_all()
        from umh.governance.authority import AuthorityLevel
        from umh.run import run

        result = run("Execute the deployment", authority=AuthorityLevel.ACT)
        assert result.success
        assert result.capability_used == "local_python"
        assert result.trace.stages["compose"]["target"] == "runtime"

    def test_status_check_routes_to_local_python(self):
        _reset_all()
        from umh.run import run

        result = run("Check the health status and track alerts")
        assert result.success
        assert result.capability_used == "local_python"

    def test_creation_routes_to_llm(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("create_artifact")
        assert d.selected is not None
        assert d.selected.name == "llm_generation"
        assert d.scores["llm_generation"] > d.scores["local_python"]

    def test_analysis_routes_to_llm(self):
        _reset_all()
        from umh.capability.router import route_to_capability

        d = route_to_capability("run_analysis")
        assert d.selected is not None
        assert d.selected.name == "llm_generation"
        assert d.scores["llm_generation"] > d.scores["local_python"]

    def test_llm_failure_captured_in_trace(self):
        _reset_all()
        from umh.adapters.base import set_adapter
        from umh.adapters.llm import OllamaLLMAdapter
        from umh.run import run

        set_adapter("llm", OllamaLLMAdapter(host="http://127.0.0.1:59999"))
        result = run("What should I focus on?")
        assert not result.success
        assert result.trace.stages["execute"]["error"] is not None
        from umh.adapters.base import reset_adapters

        reset_adapters()

    def test_trace_has_all_nine_stages(self):
        _reset_all()
        from umh.run import run

        result = run("Tell me about the project")
        expected = [
            "signal",
            "intent",
            "world",
            "decision",
            "route",
            "compose",
            "govern",
            "execute",
            "feedback",
        ]
        for stage in expected:
            assert stage in result.trace.stages, f"Missing stage: {stage}"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. No EOS Imports
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoEOSImportsInModifiedFiles:
    def test_router_no_eos_imports(self):
        filepath = "/opt/OS/umh/capability/router.py"
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filepath)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.runtime_engine."), (
                    f"router.py has EOS import: {node.module}"
                )

    def test_registry_no_top_level_eos_imports(self):
        filepath = "/opt/OS/umh/capability/registry.py"
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filepath)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.runtime_engine."), (
                    f"registry.py has top-level EOS import: {node.module}"
                )

    def test_run_module_no_eos_imports(self):
        filepath = "/opt/OS/umh/run.py"
        with open(filepath) as f:
            source = f.read()
        tree = ast.parse(source, filepath)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("umh.runtime_engine."), (
                    f"run.py has EOS import: {node.module}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Registry Convergence (Wave 2B)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegistryConvergence:
    """Tests for features absorbed from legacy core.capabilities."""

    def test_effective_quality_baseline(self):
        from umh.capability.registry import Capability

        cap = Capability(name="test", capability_type="llm", quality_score=0.9)
        assert cap.effective_quality() == 0.9

    def test_effective_quality_adapts(self):
        from umh.capability.registry import Capability

        cap = Capability(name="test", capability_type="llm", quality_score=0.9)
        for _ in range(20):
            cap.performance.record(success=True, latency_ms=100)
        # After 20 runs at 100% success, effective should be close to 1.0
        assert cap.effective_quality() > 0.95

    def test_effective_quality_degrades(self):
        from umh.capability.registry import Capability

        cap = Capability(name="test", capability_type="llm", quality_score=0.9)
        for _ in range(20):
            cap.performance.record(success=False, latency_ms=100)
        # After 20 failures, effective should be near 0.0
        assert cap.effective_quality() < 0.1

    def test_cost_efficiency(self):
        from umh.capability.registry import PerformanceStats

        stats = PerformanceStats()
        stats.record(success=True, latency_ms=100, cost=0.10)
        stats.record(success=True, latency_ms=100, cost=0.10)
        stats.record(success=False, latency_ms=100, cost=0.10)
        assert abs(stats.cost_efficiency - 0.15) < 0.001  # $0.30 / 2 successes

    def test_cost_efficiency_no_successes(self):
        from umh.capability.registry import PerformanceStats

        stats = PerformanceStats()
        stats.record(success=False, latency_ms=100, cost=0.10)
        assert stats.cost_efficiency == float("inf")

    def test_supports_task(self):
        from umh.capability.registry import Capability

        cap = Capability(
            name="test",
            capability_type="llm",
            tags=("reasoning", "analysis", "generation"),
        )
        assert cap.supports_task("reasoning")
        assert cap.supports_task("analysis")
        assert not cap.supports_task("unknown_task")

    def test_weaknesses_field(self):
        from umh.capability.registry import Capability

        cap = Capability(
            name="test",
            capability_type="llm",
            weaknesses=("cost", "latency"),
        )
        assert "cost" in cap.weaknesses
        d = cap.to_dict()
        assert d["weaknesses"] == ["cost", "latency"]

    def test_latency_score_field(self):
        from umh.capability.registry import Capability

        cap = Capability(name="test", capability_type="llm", latency_score=0.3)
        assert cap.latency_score == 0.3
        d = cap.to_dict()
        assert d["latency_score"] == 0.3

    def test_record_outcome_via_registry(self):
        from umh.capability.registry import Capability, CapabilityRegistry

        reg = CapabilityRegistry()
        reg.register(Capability(name="cap1", capability_type="llm"))
        reg.record_outcome("cap1", success=True, latency_ms=50, cost=0.01)
        reg.record_outcome("cap1", success=False, latency_ms=200, cost=0.01)

        cap = reg.get("cap1")
        assert cap.performance.total_runs == 2
        assert cap.performance.successes == 1
        assert abs(cap.performance.total_cost - 0.02) < 0.0001

    def test_record_outcome_unknown_cap(self):
        from umh.capability.registry import CapabilityRegistry

        reg = CapabilityRegistry()
        reg.record_outcome("nonexistent", success=True, latency_ms=10)

    def test_persistence_backend_protocol(self):
        from umh.capability.registry import (
            PersistenceBackend,
            NullPersistence,
            PerformanceStats,
        )

        assert isinstance(NullPersistence(), PersistenceBackend)

    def test_custom_persistence(self):
        from umh.capability.registry import (
            Capability,
            CapabilityRegistry,
            PerformanceStats,
        )

        saved = {}

        class MemPersistence:
            def save(self, name, stats):
                saved[name] = stats.to_dict()

            def load(self, name):
                if name in saved:
                    d = saved[name]
                    return PerformanceStats(
                        total_runs=d["total_runs"],
                        successes=d["successes"],
                        total_latency_ms=int(d["avg_latency_ms"] * d["total_runs"]),
                        total_cost=d["total_cost"],
                    )
                return None

        reg = CapabilityRegistry(persistence=MemPersistence())
        reg.register(Capability(name="test", capability_type="llm"))
        reg.record_outcome("test", success=True, latency_ms=100, cost=0.05)
        assert "test" in saved
        assert saved["test"]["total_runs"] == 1

    def test_to_dict_includes_new_fields(self):
        from umh.capability.registry import Capability

        cap = Capability(
            name="full",
            capability_type="llm",
            description="test cap",
            latency_score=0.4,
            weaknesses=("slow",),
        )
        d = cap.to_dict()
        assert "effective_quality" in d
        assert "cost_efficiency" in d["performance"]
        assert "total_cost" in d["performance"]
        assert "weaknesses" in d
        assert "latency_score" in d

    def test_default_registry_has_tags(self):
        _reset_all()
        from umh.capability.registry import get_registry

        reg = get_registry()
        lp = reg.get("local_python")
        assert lp is not None
        assert "compute" in lp.tags
        assert "execution" in lp.tags
        assert lp.supports_task("computation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
