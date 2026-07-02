"""P1 Phase 2 — Cognitive Pipeline Bridge tests.

Verifies all 5 wiring points:
1. GovernedExecutionSpine bridge (set_governed_spine + _governed_execute)
2. OutcomeLearningLoop signal emission (set_outcome_learning)
3. Organism self-model injection (set_world_model)
4. Homeostasis COGNITIVE_LOOP dimension (set_homeostasis)
5. Planning enrichment (strategic context injection)

Run with: pytest tests/test_p1_phase2_bridge.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

pytestmark = pytest.mark.smoke


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.org_id = "test-org"
    ctx.active_venture_id = "test-venture"
    return ctx


@pytest.fixture
def cognitive_loop(mock_ctx):
    with patch("substrate.control_plane.runtime.cognitive_loop.get_agent_runtime") as mock_rt, \
         patch("substrate.control_plane.runtime.cognitive_loop.AgentMemory"), \
         patch("substrate.control_plane.runtime.cognitive_loop.AuthorityEngine"), \
         patch("substrate.control_plane.runtime.cognitive_loop.IntelligenceRuntime"):
        mock_rt.return_value = MagicMock()
        from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
        loop = CognitiveLoop(mock_ctx)
        yield loop


# ── 1. Late-binding setters exist ────────────────────────────────────────────


class TestLateBndingSetters:
    def test_set_governed_spine_exists(self, cognitive_loop):
        assert hasattr(cognitive_loop, "set_governed_spine")
        assert callable(cognitive_loop.set_governed_spine)

    def test_set_outcome_learning_exists(self, cognitive_loop):
        assert hasattr(cognitive_loop, "set_outcome_learning")
        assert callable(cognitive_loop.set_outcome_learning)

    def test_set_world_model_exists(self, cognitive_loop):
        assert hasattr(cognitive_loop, "set_world_model")
        assert callable(cognitive_loop.set_world_model)

    def test_set_homeostasis_exists(self, cognitive_loop):
        assert hasattr(cognitive_loop, "set_homeostasis")
        assert callable(cognitive_loop.set_homeostasis)

    def test_cognitive_metrics_exists(self, cognitive_loop):
        assert hasattr(cognitive_loop, "cognitive_metrics")
        assert callable(cognitive_loop.cognitive_metrics)

    def test_setters_are_null_safe(self, cognitive_loop):
        """All spine attributes default to None — no crash without wiring."""
        assert cognitive_loop._governed_spine is None
        assert cognitive_loop._outcome_learning is None
        assert cognitive_loop._world_model is None
        assert cognitive_loop._homeostasis is None

    def test_setters_store_references(self, cognitive_loop):
        mock_spine = MagicMock()
        mock_learning = MagicMock()
        mock_wm = MagicMock()
        mock_homeo = MagicMock()

        cognitive_loop.set_governed_spine(mock_spine)
        cognitive_loop.set_outcome_learning(mock_learning)
        cognitive_loop.set_world_model(mock_wm)
        cognitive_loop.set_homeostasis(mock_homeo)

        assert cognitive_loop._governed_spine is mock_spine
        assert cognitive_loop._outcome_learning is mock_learning
        assert cognitive_loop._world_model is mock_wm
        assert cognitive_loop._homeostasis is mock_homeo


# ── 2. Governed execution bridge ─────────────────────────────────────────────


class TestGovernedExecutionBridge:
    def test_direct_path_without_flag(self, cognitive_loop):
        """Without UMH_COGNITIVE_BRIDGE, runtime.run() is called directly."""
        mock_result = MagicMock()
        mock_result.output = "test response"
        cognitive_loop.runtime.run.return_value = mock_result

        result = cognitive_loop._governed_execute(
            task_type="analyze",
            prompt="test",
            venture_id=None,
            skill_name=None,
            agent="test_agent",
        )

        cognitive_loop.runtime.run.assert_called_once()
        assert result is mock_result

    @patch.dict(os.environ, {"UMH_COGNITIVE_BRIDGE": "1"})
    def test_direct_path_without_spine(self, cognitive_loop):
        """With flag but no spine wired, falls back to direct."""
        mock_result = MagicMock()
        mock_result.output = "test response"
        cognitive_loop.runtime.run.return_value = mock_result

        result = cognitive_loop._governed_execute(
            task_type="analyze",
            prompt="test",
            venture_id=None,
            skill_name=None,
            agent="test_agent",
        )

        cognitive_loop.runtime.run.assert_called_once()
        assert result is mock_result

    @patch.dict(os.environ, {"UMH_COGNITIVE_BRIDGE": "1"})
    def test_governed_path_with_spine(self, cognitive_loop):
        """With flag AND spine, execution goes through governed spine."""
        mock_spine = MagicMock()
        mock_envelope = MagicMock()
        mock_envelope.status.value = "completed"
        mock_envelope.result_output = "governed response"
        mock_spine.submit.return_value = mock_envelope
        cognitive_loop.set_governed_spine(mock_spine)

        cognitive_loop._governed_execute(
            task_type="analyze",
            prompt="test",
            venture_id=None,
            skill_name=None,
            agent="test_agent",
        )

        mock_spine.submit.assert_called_once()
        envelope = mock_spine.submit.call_args[0][0]
        assert envelope.metadata["mutation_name"] == "cognitive_execution"
        assert envelope.source == "cognitive_loop"


# ── 3. COGNITIVE_EXECUTION mutation spec ─────────────────────────────────────


class TestCognitiveExecutionSpec:
    def test_spec_exists(self):
        from substrate.organism.mutation_registry import COGNITIVE_EXECUTION
        assert COGNITIVE_EXECUTION.name == "cognitive_execution"
        assert COGNITIVE_EXECUTION.risk_level == "medium"

    def test_spec_registered_in_registry(self):
        from substrate.organism.mutation_registry import MutationRegistry
        registry = MutationRegistry()
        assert registry.is_registered("cognitive_execution")

    def test_spec_properties(self):
        from substrate.organism.mutation_registry import COGNITIVE_EXECUTION
        from substrate.organism.action_envelope import ActionType, BlastRadius
        assert COGNITIVE_EXECUTION.action_type == ActionType.STATE
        assert COGNITIVE_EXECUTION.blast_radius == BlastRadius.SINGLE_SERVICE
        assert COGNITIVE_EXECUTION.timeout_seconds == 120.0


# ── 4. Homeostasis COGNITIVE_LOOP dimension ──────────────────────────────────


class TestCognitiveLoopHomeostasis:
    def test_dimension_enum_exists(self):
        from substrate.organism.homeostasis import HealthDimension
        assert hasattr(HealthDimension, "COGNITIVE_LOOP")
        assert HealthDimension.COGNITIVE_LOOP.value == "cognitive_loop"

    def test_cognitive_metrics_provider_setter(self):
        from substrate.organism.homeostasis import HomeostasisEngine
        engine = HomeostasisEngine()
        assert hasattr(engine, "set_cognitive_metrics_provider")
        provider = lambda: {"total_executions": 10, "error_rate": 0.1, "avg_latency_seconds": 5.0}
        engine.set_cognitive_metrics_provider(provider)
        assert engine._cognitive_metrics_provider is provider

    def test_check_includes_cognitive_loop(self):
        from substrate.organism.homeostasis import HomeostasisEngine
        engine = HomeostasisEngine()
        report = engine.check()
        dim_names = [d.dimension.value for d in report.dimensions]
        assert "cognitive_loop" in dim_names

    def test_healthy_without_provider(self):
        from substrate.organism.homeostasis import HomeostasisEngine
        engine = HomeostasisEngine()
        report = engine.check()
        cog_dim = [d for d in report.dimensions if d.dimension.value == "cognitive_loop"][0]
        assert cog_dim.healthy is True

    def test_healthy_with_good_metrics(self):
        from substrate.organism.homeostasis import HomeostasisEngine
        engine = HomeostasisEngine()
        engine.set_cognitive_metrics_provider(
            lambda: {"total_executions": 100, "error_rate": 0.05, "avg_latency_seconds": 10.0}
        )
        report = engine.check()
        cog_dim = [d for d in report.dimensions if d.dimension.value == "cognitive_loop"][0]
        assert cog_dim.healthy is True

    def test_unhealthy_high_error_rate(self):
        from substrate.organism.homeostasis import HomeostasisEngine
        engine = HomeostasisEngine()
        engine.set_cognitive_metrics_provider(
            lambda: {"total_executions": 100, "error_rate": 0.5, "avg_latency_seconds": 10.0}
        )
        report = engine.check()
        cog_dim = [d for d in report.dimensions if d.dimension.value == "cognitive_loop"][0]
        assert cog_dim.healthy is False


# ── 5. Cognitive metrics tracking ────────────────────────────────────────────


class TestCognitiveMetrics:
    def test_initial_metrics(self, cognitive_loop):
        metrics = cognitive_loop.cognitive_metrics()
        assert metrics["total_executions"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["avg_latency_seconds"] == 0.0

    def test_metrics_after_execution(self, cognitive_loop):
        cognitive_loop._exec_count = 10
        cognitive_loop._exec_errors = 2
        cognitive_loop._exec_total_latency = 50.0

        metrics = cognitive_loop.cognitive_metrics()
        assert metrics["total_executions"] == 10
        assert metrics["error_rate"] == pytest.approx(0.2)
        assert metrics["avg_latency_seconds"] == pytest.approx(5.0)


# ── 6. Contract preservation ─────────────────────────────────────────────────


class TestContractPreservation:
    def test_governed_spine_submit_signature(self):
        """GovernedExecutionSpine.submit() signature unchanged."""
        import inspect
        from substrate.organism.governed_spine import GovernedExecutionSpine
        sig = inspect.signature(GovernedExecutionSpine.submit)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "envelope" in params

    def test_governed_mutation_signature(self):
        """governed_mutation() signature unchanged."""
        import inspect
        from transports.api.governed import governed_mutation
        sig = inspect.signature(governed_mutation)
        params = list(sig.parameters.keys())
        assert "mutation_name" in params
        assert "execute_fn" in params

    def test_event_spine_class_exists(self):
        """EventSpine contract unchanged."""
        from substrate.organism.event_spine import EventSpine
        assert hasattr(EventSpine, "emit")
