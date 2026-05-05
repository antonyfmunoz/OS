"""Phase 26: Behavior-Aware Planning + Strategy Layer v1 — 80 tests.

Covers ExecutionStrategy, StrategyBuilder, planner integration,
advisor integration, explainability, and hard invariants 65-69.
"""

from __future__ import annotations

import sys
import inspect
import json

import pytest

sys.path.insert(0, "/opt/OS")

from umh.model.aggregator import BehaviorAggregator
from umh.model.behavior import UserBehaviorModel
from umh.model.traits import TraitValue
from umh.runtime.strategy import (
    ExecutionStrategy,
    StrategyAdjustment,
    StrategyBuilder,
    _DEFAULT_BATCH_SIZE,
    _MAX_BATCH_SIZE,
    _MIN_BATCH_SIZE,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _model_with(**trait_overrides: tuple[float, float, int]) -> UserBehaviorModel:
    """Build a UserBehaviorModel with specific trait (value, confidence, sample_count)."""
    m = UserBehaviorModel()
    for name, (value, confidence, count) in trait_overrides.items():
        m.set_trait(name, value=value, confidence=confidence, sample_count=count)
    return m


def _confident_model(**traits: float) -> UserBehaviorModel:
    """Build a model where every provided trait has high confidence."""
    m = UserBehaviorModel()
    for name, value in traits.items():
        m.set_trait(name, value=value, confidence=0.9, sample_count=18)
    return m


# ===================================================================
# SECTION 1: ExecutionStrategy (12 tests)
# ===================================================================

class TestExecutionStrategy:
    def test_defaults(self):
        s = ExecutionStrategy()
        assert s.batch_size == _DEFAULT_BATCH_SIZE
        assert s.pacing == 1.0
        assert s.retry_budget == 2
        assert s.priority_bias == 0.0
        assert s.prefer_morning is False
        assert s.prefer_clustering is False
        assert s.adjustments == ()

    def test_frozen(self):
        s = ExecutionStrategy()
        with pytest.raises(AttributeError):
            s.batch_size = 10  # type: ignore[misc]

    def test_to_dict(self):
        s = ExecutionStrategy(batch_size=3, pacing=1.5)
        d = s.to_dict()
        assert d["batch_size"] == 3
        assert d["pacing"] == 1.5
        assert "adjustments" in d

    def test_to_dict_with_adjustments(self):
        adj = StrategyAdjustment(
            trait_name="completion_rate",
            trait_value=0.3,
            trait_confidence=0.8,
            adjustment="batch_size -2",
            reason="Low completion rate",
        )
        s = ExecutionStrategy(adjustments=(adj,))
        d = s.to_dict()
        assert len(d["adjustments"]) == 1
        assert d["adjustments"][0]["trait_name"] == "completion_rate"

    def test_explanation_property(self):
        adj1 = StrategyAdjustment(
            trait_name="t1", trait_value=0.3, trait_confidence=0.8,
            adjustment="x", reason="reason A",
        )
        adj2 = StrategyAdjustment(
            trait_name="t2", trait_value=0.9, trait_confidence=0.7,
            adjustment="y", reason="reason B",
        )
        s = ExecutionStrategy(adjustments=(adj1, adj2))
        assert s.explanation == ["reason A", "reason B"]

    def test_explanation_empty_when_no_adjustments(self):
        s = ExecutionStrategy()
        assert s.explanation == []

    def test_json_serializable(self):
        adj = StrategyAdjustment(
            trait_name="t", trait_value=0.5, trait_confidence=0.5,
            adjustment="x", reason="r",
        )
        s = ExecutionStrategy(adjustments=(adj,))
        json_str = json.dumps(s.to_dict())
        assert isinstance(json_str, str)


class TestStrategyAdjustment:
    def test_frozen(self):
        adj = StrategyAdjustment(
            trait_name="t", trait_value=0.5, trait_confidence=0.5,
            adjustment="x", reason="r",
        )
        with pytest.raises(AttributeError):
            adj.reason = "changed"  # type: ignore[misc]

    def test_to_dict(self):
        adj = StrategyAdjustment(
            trait_name="completion_rate", trait_value=0.3456789,
            trait_confidence=0.8765432, adjustment="batch -2",
            reason="low completion",
        )
        d = adj.to_dict()
        assert d["trait_value"] == 0.3457
        assert d["trait_confidence"] == 0.8765
        assert d["adjustment"] == "batch -2"

    def test_to_dict_has_all_fields(self):
        adj = StrategyAdjustment(
            trait_name="t", trait_value=0.5, trait_confidence=0.5,
            adjustment="x", reason="r",
        )
        d = adj.to_dict()
        assert set(d.keys()) == {"trait_name", "trait_value", "trait_confidence", "adjustment", "reason"}

    def test_reason_captures_trait_info(self):
        adj = StrategyAdjustment(
            trait_name="latency_score", trait_value=0.2,
            trait_confidence=0.8, adjustment="pacing *1.5",
            reason="Slow responses (20%) — increase time buffers",
        )
        assert "20%" in adj.reason
        assert "latency_score" == adj.trait_name

    def test_adjustment_describes_change(self):
        adj = StrategyAdjustment(
            trait_name="t", trait_value=0.5, trait_confidence=0.5,
            adjustment="batch_size -2, retry_budget +1",
            reason="r",
        )
        assert "batch_size" in adj.adjustment
        assert "retry_budget" in adj.adjustment


# ===================================================================
# SECTION 2: StrategyBuilder — trait rules (25 tests)
# ===================================================================

class TestStrategyBuilderBasic:
    def test_none_model_returns_defaults(self):
        sb = StrategyBuilder()
        s = sb.build_strategy(None)
        assert s.batch_size == _DEFAULT_BATCH_SIZE
        assert s.adjustments == ()

    def test_fresh_model_returns_defaults(self):
        sb = StrategyBuilder()
        s = sb.build_strategy(UserBehaviorModel())
        assert s.batch_size == _DEFAULT_BATCH_SIZE
        assert len(s.adjustments) == 0

    def test_confidence_threshold_default(self):
        sb = StrategyBuilder()
        assert sb.confidence_threshold == 0.2

    def test_confidence_threshold_custom(self):
        sb = StrategyBuilder(confidence_threshold=0.5)
        assert sb.confidence_threshold == 0.5

    def test_confidence_threshold_clamped(self):
        sb = StrategyBuilder(confidence_threshold=2.0)
        assert sb.confidence_threshold == 1.0


class TestCompletionRateRule:
    def test_low_completion_reduces_batch(self):
        m = _confident_model(completion_rate=0.3)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size < _DEFAULT_BATCH_SIZE

    def test_low_completion_increases_retries(self):
        m = _confident_model(completion_rate=0.3)
        s = StrategyBuilder().build_strategy(m)
        assert s.retry_budget > 2

    def test_high_completion_increases_batch(self):
        m = _confident_model(completion_rate=0.9)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size > _DEFAULT_BATCH_SIZE

    def test_medium_completion_no_change(self):
        m = _confident_model(completion_rate=0.6)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size == _DEFAULT_BATCH_SIZE


class TestConsistencyScoreRule:
    def test_high_consistency_enables_clustering(self):
        m = _confident_model(consistency_score=0.8)
        s = StrategyBuilder().build_strategy(m)
        assert s.prefer_clustering is True

    def test_high_consistency_increases_batch(self):
        m = _confident_model(consistency_score=0.8)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size > _DEFAULT_BATCH_SIZE

    def test_low_consistency_slows_pacing(self):
        m = _confident_model(consistency_score=0.2)
        s = StrategyBuilder().build_strategy(m)
        assert s.pacing > 1.0


class TestLatencyScoreRule:
    def test_slow_latency_increases_pacing(self):
        m = _confident_model(latency_score=0.2)
        s = StrategyBuilder().build_strategy(m)
        assert s.pacing > 1.0

    def test_fast_latency_decreases_pacing(self):
        m = _confident_model(latency_score=0.9)
        s = StrategyBuilder().build_strategy(m)
        assert s.pacing < 1.0


class TestTimePreferenceRule:
    def test_morning_preference(self):
        m = _confident_model(time_preference=0.8)
        s = StrategyBuilder().build_strategy(m)
        assert s.prefer_morning is True

    def test_no_morning_preference(self):
        m = _confident_model(time_preference=0.3)
        s = StrategyBuilder().build_strategy(m)
        assert s.prefer_morning is False


class TestPatternStabilityRule:
    def test_stable_patterns_add_priority_bias(self):
        m = _confident_model(pattern_stability=0.7)
        s = StrategyBuilder().build_strategy(m)
        assert s.priority_bias > 0.0


class TestVolatilityRule:
    def test_high_volatility_reduces_batch(self):
        m = _confident_model(volatility_index=0.8)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size < _DEFAULT_BATCH_SIZE

    def test_high_volatility_increases_retries(self):
        m = _confident_model(volatility_index=0.8)
        s = StrategyBuilder().build_strategy(m)
        assert s.retry_budget > 2


class TestBatchSizeBounds:
    def test_batch_size_minimum(self):
        m = _confident_model(completion_rate=0.0, volatility_index=0.99)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size >= _MIN_BATCH_SIZE

    def test_batch_size_maximum(self):
        m = _confident_model(
            completion_rate=0.99,
            consistency_score=0.99,
        )
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size <= _MAX_BATCH_SIZE


class TestLowConfidenceSkipped:
    def test_low_confidence_trait_ignored(self):
        m = UserBehaviorModel()
        m.set_trait("completion_rate", value=0.1, confidence=0.1, sample_count=2)
        s = StrategyBuilder().build_strategy(m)
        assert s.batch_size == _DEFAULT_BATCH_SIZE
        assert len(s.adjustments) == 0

    def test_custom_threshold_skips_more(self):
        m = UserBehaviorModel()
        m.set_trait("completion_rate", value=0.1, confidence=0.4, sample_count=8)
        s = StrategyBuilder(confidence_threshold=0.5).build_strategy(m)
        assert len(s.adjustments) == 0

    def test_custom_threshold_passes_more(self):
        m = UserBehaviorModel()
        m.set_trait("completion_rate", value=0.1, confidence=0.15, sample_count=3)
        s = StrategyBuilder(confidence_threshold=0.1).build_strategy(m)
        assert len(s.adjustments) > 0


# ===================================================================
# SECTION 3: Planner integration (10 tests)
# ===================================================================

class TestPlannerBatchIntegration:
    def _make_store_with_n(self, n: int):
        from umh.jobs.store import JobStore
        store = JobStore()
        for i in range(n):
            job = store.create_job(task_id=f"t{i}", node_id="n1")
            store.mark_submitted(job.job_id)
        return store

    def test_plan_batch_default_limit(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(10)
        planner = SchedulingPlanner()
        batch = planner.plan_batch(store)
        assert len(batch) == _DEFAULT_BATCH_SIZE

    def test_plan_batch_strategy_limits(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(10)
        planner = SchedulingPlanner()
        strategy = ExecutionStrategy(batch_size=3)
        batch = planner.plan_batch(store, strategy=strategy)
        assert len(batch) == 3

    def test_plan_batch_empty_store(self):
        from umh.runtime.planner import SchedulingPlanner
        from umh.jobs.store import JobStore
        planner = SchedulingPlanner()
        batch = planner.plan_batch(JobStore())
        assert batch == []

    def test_plan_batch_no_duplicate_jobs(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(5)
        planner = SchedulingPlanner()
        batch = planner.plan_batch(store)
        job_ids = [j.job_id for j, _ in batch]
        assert len(job_ids) == len(set(job_ids))

    def test_plan_batch_respects_strategy_batch_size(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(20)
        planner = SchedulingPlanner()
        for size in [1, 3, 7, 10]:
            strategy = ExecutionStrategy(batch_size=size)
            batch = planner.plan_batch(store, strategy=strategy)
            assert len(batch) == size

    def test_plan_batch_applies_priority_bias(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(3)
        planner = SchedulingPlanner()
        strategy = ExecutionStrategy(priority_bias=0.5)
        batch = planner.plan_batch(store, strategy=strategy)
        assert len(batch) == 3

    def test_plan_batch_fewer_jobs_than_batch_size(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(2)
        planner = SchedulingPlanner()
        strategy = ExecutionStrategy(batch_size=10)
        batch = planner.plan_batch(store, strategy=strategy)
        assert len(batch) == 2

    def test_plan_batch_returns_tuples(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(1)
        planner = SchedulingPlanner()
        batch = planner.plan_batch(store)
        assert len(batch) == 1
        job, node_id = batch[0]
        assert isinstance(job.job_id, str)
        assert isinstance(node_id, str)

    def test_plan_batch_does_not_mutate_store(self):
        from umh.runtime.planner import SchedulingPlanner
        from umh.jobs.models import JobStatus
        store = self._make_store_with_n(5)
        planner = SchedulingPlanner()
        planner.plan_batch(store, strategy=ExecutionStrategy(batch_size=2))
        remaining = store.list_jobs(status=JobStatus.SUBMITTED)
        assert len(remaining) == 5

    def test_existing_plan_next_still_works(self):
        from umh.runtime.planner import SchedulingPlanner
        store = self._make_store_with_n(3)
        planner = SchedulingPlanner()
        result = planner.plan_next(store)
        assert result is not None


# ===================================================================
# SECTION 4: Advisor integration (12 tests)
# ===================================================================

class TestAdvisorStrategyIntegration:
    def _make_advisor(self, *, with_strategy: bool = True, with_aggregator: bool = True):
        from umh.runtime.advisor import AdvisorRuntime
        kwargs = {}
        if with_aggregator:
            kwargs["behavior_aggregator"] = BehaviorAggregator()
        if with_strategy:
            kwargs["strategy_builder"] = StrategyBuilder()
        return AdvisorRuntime(**kwargs)

    def test_strategy_builder_property(self):
        adv = self._make_advisor()
        assert adv.strategy_builder is not None

    def test_strategy_builder_none_without(self):
        adv = self._make_advisor(with_strategy=False)
        assert adv.strategy_builder is None

    def test_current_strategy_initially_none(self):
        adv = self._make_advisor()
        assert adv.current_strategy is None

    def test_tick_rebuilds_strategy(self):
        adv = self._make_advisor()
        result = adv.tick()
        assert result["strategy_rebuilt"] is True
        assert adv.current_strategy is not None

    def test_tick_without_builder_skips_strategy(self):
        adv = self._make_advisor(with_strategy=False)
        result = adv.tick()
        assert result["strategy_rebuilt"] is False
        assert adv.current_strategy is None

    def test_tick_without_aggregator_still_rebuilds(self):
        from umh.runtime.advisor import AdvisorRuntime
        adv = AdvisorRuntime(strategy_builder=StrategyBuilder())
        result = adv.tick()
        assert result["strategy_rebuilt"] is True
        assert adv.current_strategy is not None
        assert adv.current_strategy.batch_size == _DEFAULT_BATCH_SIZE

    def test_get_state_includes_strategy(self):
        adv = self._make_advisor()
        adv.tick()
        state = adv.get_state()
        assert "strategy" in state
        assert "batch_size" in state["strategy"]

    def test_get_state_no_strategy_when_none(self):
        adv = self._make_advisor(with_strategy=False)
        state = adv.get_state()
        assert "strategy" not in state

    def test_clear_resets_strategy(self):
        adv = self._make_advisor()
        adv.tick()
        assert adv.current_strategy is not None
        adv.clear()
        assert adv.current_strategy is None

    def test_strategy_reflects_model_traits(self):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.learning.feedback import ExecutionFeedback
        adv = AdvisorRuntime(
            behavior_aggregator=BehaviorAggregator(),
            strategy_builder=StrategyBuilder(),
        )
        fb = [
            ExecutionFeedback(
                job_id=f"j{i}", node_id="n1", task_type="t",
                success=True, duration_ms=10,
                timestamp=f"2026-04-30T{h:02d}:00:00+00:00",
            )
            for i, h in enumerate([6, 7, 8, 9, 10, 6, 7, 8, 9, 10,
                                    6, 7, 8, 9, 10, 6, 7, 8, 9, 10])
        ]
        adv.tick(completed_feedback=fb)
        strategy = adv.current_strategy
        assert strategy is not None
        assert strategy.prefer_morning is True

    def test_strategy_explanation_in_state(self):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.learning.feedback import ExecutionFeedback
        adv = AdvisorRuntime(
            behavior_aggregator=BehaviorAggregator(),
            strategy_builder=StrategyBuilder(),
        )
        fb = [
            ExecutionFeedback(
                job_id=f"j{i}", node_id="n1", task_type="t",
                success=False, duration_ms=5000,
            )
            for i in range(20)
        ]
        adv.tick(completed_feedback=fb)
        state = adv.get_state()
        strategy_dict = state.get("strategy", {})
        adjustments = strategy_dict.get("adjustments", [])
        assert len(adjustments) > 0
        assert all("reason" in a for a in adjustments)

    def test_multiple_ticks_update_strategy(self):
        adv = self._make_advisor()
        adv.tick()
        s1 = adv.current_strategy
        adv.tick()
        s2 = adv.current_strategy
        assert s2 is not None
        assert s1 is not s2


# ===================================================================
# SECTION 5: Explainability (6 tests)
# ===================================================================

class TestExplainability:
    def test_every_adjustment_has_reason(self):
        m = _confident_model(
            completion_rate=0.3, latency_score=0.2,
            consistency_score=0.2, volatility_index=0.9,
        )
        s = StrategyBuilder().build_strategy(m)
        for adj in s.adjustments:
            assert adj.reason != ""
            assert adj.trait_name != ""
            assert adj.adjustment != ""

    def test_every_adjustment_has_trait_value(self):
        m = _confident_model(completion_rate=0.3, time_preference=0.9)
        s = StrategyBuilder().build_strategy(m)
        for adj in s.adjustments:
            assert 0.0 <= adj.trait_value <= 1.0

    def test_adjustment_count_matches_active_rules(self):
        m = _confident_model(completion_rate=0.3)
        s = StrategyBuilder().build_strategy(m)
        assert len(s.adjustments) == 1
        assert s.adjustments[0].trait_name == "completion_rate"

    def test_multiple_adjustments_for_multiple_traits(self):
        m = _confident_model(
            completion_rate=0.3, latency_score=0.2,
            time_preference=0.9, pattern_stability=0.8,
        )
        s = StrategyBuilder().build_strategy(m)
        trait_names = [a.trait_name for a in s.adjustments]
        assert "completion_rate" in trait_names
        assert "latency_score" in trait_names
        assert "time_preference" in trait_names
        assert "pattern_stability" in trait_names

    def test_no_adjustments_when_all_neutral(self):
        m = _confident_model(
            completion_rate=0.6, consistency_score=0.5,
            latency_score=0.5, time_preference=0.5,
        )
        s = StrategyBuilder().build_strategy(m)
        assert len(s.adjustments) == 0

    def test_explanation_strings_are_human_readable(self):
        m = _confident_model(completion_rate=0.3)
        s = StrategyBuilder().build_strategy(m)
        for reason in s.explanation:
            assert len(reason) > 10
            assert "%" in reason or "rate" in reason.lower()


# ===================================================================
# SECTION 6: Hard invariants (10 tests)
# ===================================================================

class TestHardInvariants:
    def test_inv65_model_read_only_during_planning(self):
        """INV65: Strategy builder never mutates the behavior model."""
        m = _confident_model(completion_rate=0.3, latency_score=0.2)
        before = {k: (v.value, v.confidence) for k, v in m.traits.items()}
        StrategyBuilder().build_strategy(m)
        after = {k: (v.value, v.confidence) for k, v in m.traits.items()}
        assert before == after

    def test_inv65_model_update_count_unchanged(self):
        """INV65: build_strategy doesn't increment model update count."""
        m = _confident_model(completion_rate=0.3)
        count_before = m.update_count
        StrategyBuilder().build_strategy(m)
        assert m.update_count == count_before

    def test_inv66_deterministic_same_inputs(self):
        """INV66: Same model → same strategy, always."""
        m = _confident_model(
            completion_rate=0.3, latency_score=0.2,
            consistency_score=0.8, time_preference=0.9,
        )
        sb = StrategyBuilder()
        s1 = sb.build_strategy(m)
        s2 = sb.build_strategy(m)
        assert s1.batch_size == s2.batch_size
        assert s1.pacing == s2.pacing
        assert s1.retry_budget == s2.retry_budget
        assert s1.priority_bias == s2.priority_bias
        assert s1.prefer_morning == s2.prefer_morning
        assert s1.prefer_clustering == s2.prefer_clustering
        assert len(s1.adjustments) == len(s2.adjustments)

    def test_inv67_strategy_does_not_mutate_execution_state(self):
        """INV67: ExecutionStrategy is frozen — immutable."""
        s = ExecutionStrategy(batch_size=3)
        with pytest.raises(AttributeError):
            s.batch_size = 10  # type: ignore[misc]
        with pytest.raises(AttributeError):
            s.pacing = 2.0  # type: ignore[misc]

    def test_inv67_adjustment_is_frozen(self):
        """INV67: StrategyAdjustment is frozen — immutable."""
        adj = StrategyAdjustment(
            trait_name="t", trait_value=0.5, trait_confidence=0.5,
            adjustment="x", reason="r",
        )
        with pytest.raises(AttributeError):
            adj.reason = "changed"  # type: ignore[misc]

    def test_inv68_no_hidden_heuristics(self):
        """INV68: Every strategy field change produces an adjustment record."""
        m = _confident_model(
            completion_rate=0.3, latency_score=0.2,
            consistency_score=0.2, time_preference=0.9,
            pattern_stability=0.8, volatility_index=0.9,
        )
        s = StrategyBuilder().build_strategy(m)
        trait_names_adjusted = {a.trait_name for a in s.adjustments}
        if s.batch_size != _DEFAULT_BATCH_SIZE:
            assert len(trait_names_adjusted) > 0
        if s.pacing != 1.0:
            assert any("pacing" in a.adjustment for a in s.adjustments)
        if s.prefer_morning:
            assert "time_preference" in trait_names_adjusted
        if s.prefer_clustering:
            assert "consistency_score" in trait_names_adjusted
        if s.priority_bias != 0.0:
            assert "pattern_stability" in trait_names_adjusted

    def test_inv69_no_cells_import(self):
        """INV69: Strategy module has no direct coupling to cells."""
        src = inspect.getsource(sys.modules["umh.runtime.strategy"])
        assert "from umh.cells" not in src
        assert "import umh.cells" not in src

    def test_inv69_no_environments_import(self):
        """INV69: Strategy module has no direct coupling to environments."""
        src = inspect.getsource(sys.modules["umh.runtime.strategy"])
        assert "from umh.environments" not in src

    def test_inv69_no_adapters_import(self):
        """INV69: Strategy module has no direct coupling to adapters."""
        src = inspect.getsource(sys.modules["umh.runtime.strategy"])
        assert "from umh.adapters" not in src

    def test_inv69_no_subprocess(self):
        """INV69: Strategy module does not use subprocess."""
        src = inspect.getsource(sys.modules["umh.runtime.strategy"])
        assert "import subprocess" not in src


# ===================================================================
# SECTION 7: Boundary + exports (5 tests)
# ===================================================================

class TestBoundaryExports:
    def test_runtime_exports_strategy_types(self):
        from umh.runtime import ExecutionStrategy, StrategyAdjustment, StrategyBuilder
        assert ExecutionStrategy is not None
        assert StrategyAdjustment is not None
        assert StrategyBuilder is not None

    def test_planner_still_exports(self):
        from umh.runtime.planner import SchedulingPlanner, adaptive_score, make_ranker
        assert SchedulingPlanner is not None

    def test_strategy_module_compiles(self):
        import umh.runtime.strategy
        assert hasattr(umh.runtime.strategy, "ExecutionStrategy")

    def test_planner_imports_strategy(self):
        from umh.runtime.planner import ExecutionStrategy as ES
        assert ES is not None

    def test_combined_build_flow(self):
        """End-to-end: model → strategy → plan_batch."""
        from umh.jobs.store import JobStore
        from umh.runtime.planner import SchedulingPlanner

        m = _confident_model(completion_rate=0.3, volatility_index=0.9)
        sb = StrategyBuilder()
        strategy = sb.build_strategy(m)

        store = JobStore()
        for i in range(10):
            job = store.create_job(task_id=f"t{i}", node_id="n1")
            store.mark_submitted(job.job_id)

        planner = SchedulingPlanner()
        batch = planner.plan_batch(store, strategy=strategy)
        assert len(batch) == strategy.batch_size
        assert strategy.batch_size < _DEFAULT_BATCH_SIZE
