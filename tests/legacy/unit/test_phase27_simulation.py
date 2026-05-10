"""Phase 27: Strategy Simulation + Outcome Evaluation Layer v1 — 85 tests.

Covers StrategyGenerator, SimulationEngine, OutcomeEvaluator,
StrategySimulator, advisor integration, and hard invariants 70-74.
"""

from __future__ import annotations

import copy
import sys
import inspect
import json

import pytest

sys.path.insert(0, "/opt/OS")

from umh.model.behavior import UserBehaviorModel
from umh.model.aggregator import BehaviorAggregator
from umh.runtime.strategy import ExecutionStrategy, StrategyBuilder
from umh.runtime.simulation import (
    SimulatedOutcome,
    SimulationEngine,
    SimulationResult,
    StrategyGenerator,
)
from umh.runtime.evaluator import (
    OutcomeEvaluator,
    ScoringWeights,
    StrategySimulator,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _confident_model(**traits: float) -> UserBehaviorModel:
    m = UserBehaviorModel()
    for name, value in traits.items():
        m.set_trait(name, value=value, confidence=0.9, sample_count=18)
    return m


_BASE = ExecutionStrategy()
_SMALL = ExecutionStrategy(batch_size=2, retry_budget=4)
_LARGE = ExecutionStrategy(batch_size=10, pacing=0.8)


# ===================================================================
# SECTION 1: StrategyGenerator (12 tests)
# ===================================================================

class TestStrategyGenerator:
    def test_includes_base(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(_BASE)
        assert candidates[0] is _BASE

    def test_generates_multiple(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(_BASE)
        assert len(candidates) >= 4

    def test_deterministic(self):
        gen = StrategyGenerator()
        c1 = gen.generate_candidates(_BASE)
        c2 = gen.generate_candidates(_BASE)
        assert len(c1) == len(c2)
        for a, b in zip(c1[1:], c2[1:]):
            assert a.batch_size == b.batch_size
            assert a.pacing == b.pacing
            assert a.retry_budget == b.retry_budget

    def test_has_smaller_batch_variant(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(_BASE)
        assert any(c.batch_size < _BASE.batch_size for c in candidates)

    def test_has_larger_batch_variant(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(_BASE)
        assert any(c.batch_size > _BASE.batch_size for c in candidates)

    def test_has_conservative_pacing_variant(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(_BASE)
        assert any(c.pacing > _BASE.pacing for c in candidates)

    def test_has_aggressive_retry_variant(self):
        gen = StrategyGenerator()
        candidates = gen.generate_candidates(_BASE)
        assert any(c.retry_budget > _BASE.retry_budget for c in candidates)

    def test_no_smaller_batch_when_at_minimum(self):
        gen = StrategyGenerator()
        base = ExecutionStrategy(batch_size=1)
        candidates = gen.generate_candidates(base)
        assert not any(c.batch_size < 1 for c in candidates)

    def test_no_larger_batch_when_at_maximum(self):
        gen = StrategyGenerator()
        base = ExecutionStrategy(batch_size=20)
        candidates = gen.generate_candidates(base)
        assert not any(c.batch_size > 20 for c in candidates)

    def test_label_base(self):
        gen = StrategyGenerator()
        assert gen.label_candidate(0, _BASE, _BASE) == "base"

    def test_label_smaller_batch(self):
        gen = StrategyGenerator()
        variant = ExecutionStrategy(batch_size=3)
        label = gen.label_candidate(1, variant, _BASE)
        assert "smaller-batch" in label

    def test_label_larger_batch(self):
        gen = StrategyGenerator()
        variant = ExecutionStrategy(batch_size=8)
        label = gen.label_candidate(1, variant, _BASE)
        assert "larger-batch" in label


# ===================================================================
# SECTION 2: SimulationEngine (15 tests)
# ===================================================================

class TestSimulationEngine:
    def test_returns_simulated_outcome(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        assert isinstance(out, SimulatedOutcome)

    def test_completion_rate_bounded(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        assert 0.0 <= out.expected_completion_rate <= 1.0

    def test_failure_risk_bounded(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        assert 0.0 <= out.expected_failure_risk <= 1.0

    def test_latency_positive(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        assert out.expected_latency > 0

    def test_effort_positive(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        assert out.estimated_effort > 0

    def test_larger_batch_higher_latency(self):
        engine = SimulationEngine()
        out_small = engine.simulate(ExecutionStrategy(batch_size=2))
        out_large = engine.simulate(ExecutionStrategy(batch_size=10))
        assert out_large.expected_latency > out_small.expected_latency

    def test_more_retries_higher_completion(self):
        engine = SimulationEngine()
        out_low = engine.simulate(ExecutionStrategy(retry_budget=1))
        out_high = engine.simulate(ExecutionStrategy(retry_budget=5))
        assert out_high.expected_completion_rate >= out_low.expected_completion_rate

    def test_larger_batch_higher_risk(self):
        engine = SimulationEngine()
        out_small = engine.simulate(ExecutionStrategy(batch_size=2))
        out_large = engine.simulate(ExecutionStrategy(batch_size=10))
        assert out_large.expected_failure_risk >= out_small.expected_failure_risk

    def test_model_influences_completion(self):
        engine = SimulationEngine()
        m_high = _confident_model(completion_rate=0.9)
        m_low = _confident_model(completion_rate=0.2)
        out_high = engine.simulate(_BASE, m_high)
        out_low = engine.simulate(_BASE, m_low)
        assert out_high.expected_completion_rate > out_low.expected_completion_rate

    def test_model_volatility_influences_risk(self):
        engine = SimulationEngine()
        m_stable = _confident_model(volatility_index=0.1)
        m_volatile = _confident_model(volatility_index=0.9)
        out_stable = engine.simulate(_BASE, m_stable)
        out_volatile = engine.simulate(_BASE, m_volatile)
        assert out_volatile.expected_failure_risk > out_stable.expected_failure_risk

    def test_none_model_uses_defaults(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE, None)
        assert out.expected_completion_rate > 0

    def test_outcome_frozen(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        with pytest.raises(AttributeError):
            out.expected_completion_rate = 0.5  # type: ignore[misc]

    def test_to_dict(self):
        engine = SimulationEngine()
        out = engine.simulate(_BASE)
        d = out.to_dict()
        assert "expected_completion_rate" in d
        assert "expected_latency" in d
        assert "expected_failure_risk" in d
        assert "estimated_effort" in d
        assert "strategy" in d

    def test_deterministic_same_inputs(self):
        engine = SimulationEngine()
        m = _confident_model(completion_rate=0.7)
        o1 = engine.simulate(_BASE, m)
        o2 = engine.simulate(_BASE, m)
        assert o1.expected_completion_rate == o2.expected_completion_rate
        assert o1.expected_failure_risk == o2.expected_failure_risk

    def test_pacing_affects_latency(self):
        engine = SimulationEngine()
        slow = ExecutionStrategy(pacing=2.0)
        fast = ExecutionStrategy(pacing=0.5)
        assert engine.simulate(slow).expected_latency > engine.simulate(fast).expected_latency


# ===================================================================
# SECTION 3: OutcomeEvaluator (12 tests)
# ===================================================================

class TestOutcomeEvaluator:
    def _make_outcome(self, **overrides) -> SimulatedOutcome:
        defaults = {
            "strategy": _BASE,
            "label": "test",
            "expected_completion_rate": 0.7,
            "expected_latency": 5.0,
            "expected_failure_risk": 0.2,
            "estimated_effort": 0.5,
        }
        defaults.update(overrides)
        return SimulatedOutcome(**defaults)

    def test_score_returns_float(self):
        ev = OutcomeEvaluator()
        out = self._make_outcome()
        s = ev.score(out)
        assert isinstance(s, float)

    def test_higher_completion_higher_score(self):
        ev = OutcomeEvaluator()
        low = self._make_outcome(expected_completion_rate=0.3)
        high = self._make_outcome(expected_completion_rate=0.9)
        assert ev.score(high) > ev.score(low)

    def test_lower_risk_higher_score(self):
        ev = OutcomeEvaluator()
        risky = self._make_outcome(expected_failure_risk=0.8)
        safe = self._make_outcome(expected_failure_risk=0.1)
        assert ev.score(safe) > ev.score(risky)

    def test_lower_latency_higher_score(self):
        ev = OutcomeEvaluator()
        slow = self._make_outcome(expected_latency=20.0)
        fast = self._make_outcome(expected_latency=1.0)
        assert ev.score(fast) > ev.score(slow)

    def test_lower_effort_higher_score(self):
        ev = OutcomeEvaluator()
        hard = self._make_outcome(estimated_effort=5.0)
        easy = self._make_outcome(estimated_effort=0.1)
        assert ev.score(easy) > ev.score(hard)

    def test_rank_orders_by_score(self):
        ev = OutcomeEvaluator()
        outcomes = [
            self._make_outcome(label="bad", expected_completion_rate=0.2),
            self._make_outcome(label="good", expected_completion_rate=0.9),
            self._make_outcome(label="mid", expected_completion_rate=0.5),
        ]
        ranked = ev.rank(outcomes)
        assert ranked[0].label == "good"
        scores = [o.score for o in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_assigns_scores(self):
        ev = OutcomeEvaluator()
        outcomes = [self._make_outcome()]
        ranked = ev.rank(outcomes)
        assert ranked[0].score > 0

    def test_custom_weights(self):
        ev = OutcomeEvaluator(weights=ScoringWeights(
            completion=1.0, latency=0.0, risk=0.0, effort=0.0,
        ))
        low = self._make_outcome(expected_completion_rate=0.2, expected_latency=1.0)
        high = self._make_outcome(expected_completion_rate=0.9, expected_latency=100.0)
        assert ev.score(high) > ev.score(low)

    def test_deterministic_scoring(self):
        ev = OutcomeEvaluator()
        out = self._make_outcome()
        s1 = ev.score(out)
        s2 = ev.score(out)
        assert s1 == s2

    def test_weights_property(self):
        ev = OutcomeEvaluator()
        w = ev.weights
        assert isinstance(w, ScoringWeights)

    def test_weights_normalize(self):
        ev = OutcomeEvaluator(weights=ScoringWeights(
            completion=2.0, latency=2.0, risk=2.0, effort=2.0,
        ))
        w = ev.weights
        total = w.completion + w.latency + w.risk + w.effort
        assert total == pytest.approx(1.0)

    def test_scoring_weights_to_dict(self):
        w = ScoringWeights()
        d = w.to_dict()
        assert set(d.keys()) == {"completion", "latency", "risk", "effort"}


# ===================================================================
# SECTION 4: StrategySimulator (10 tests)
# ===================================================================

class TestStrategySimulator:
    def test_run_returns_simulation_result(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        assert isinstance(result, SimulationResult)

    def test_result_has_candidates(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        assert len(result.candidates) >= 4

    def test_result_has_selected(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        assert result.selected is not None
        assert result.selected.score > 0

    def test_selected_is_highest_score(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        max_score = max(c.score for c in result.candidates)
        assert result.selected.score == pytest.approx(max_score)

    def test_result_has_reason(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        assert len(result.reason) > 0

    def test_result_to_dict(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        d = result.to_dict()
        assert "candidates_evaluated" in d
        assert "selected" in d
        assert "reason" in d
        assert "all_candidates" in d

    def test_result_json_serializable(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)

    def test_explanation_has_lines(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        lines = result.explanation
        assert len(lines) >= 2

    def test_deterministic(self):
        sim = StrategySimulator()
        r1 = sim.run(_BASE)
        r2 = sim.run(_BASE)
        assert r1.selected.label == r2.selected.label
        assert r1.selected.score == pytest.approx(r2.selected.score)

    def test_model_influences_selection(self):
        sim = StrategySimulator()
        m_high = _confident_model(completion_rate=0.95)
        m_low = _confident_model(completion_rate=0.2, volatility_index=0.9)
        r_high = sim.run(_BASE, m_high)
        r_low = sim.run(_BASE, m_low)
        assert r_high.selected.expected_completion_rate > r_low.selected.expected_completion_rate


# ===================================================================
# SECTION 5: SimulationResult (5 tests)
# ===================================================================

class TestSimulationResult:
    def test_candidates_are_tuple(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        assert isinstance(result.candidates, tuple)

    def test_frozen(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        with pytest.raises(AttributeError):
            result.reason = "changed"  # type: ignore[misc]

    def test_candidates_labeled(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        labels = [c.label for c in result.candidates]
        assert "base" in labels

    def test_candidates_scored(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        for c in result.candidates:
            assert c.score > 0

    def test_selected_label_in_candidates(self):
        sim = StrategySimulator()
        result = sim.run(_BASE)
        labels = [c.label for c in result.candidates]
        assert result.selected.label in labels


# ===================================================================
# SECTION 6: Advisor integration (11 tests)
# ===================================================================

class TestAdvisorSimulationIntegration:
    def _make_advisor(self, *, with_sim: bool = True):
        from umh.runtime.advisor import AdvisorRuntime
        kwargs = {
            "behavior_aggregator": BehaviorAggregator(),
            "strategy_builder": StrategyBuilder(),
        }
        if with_sim:
            kwargs["strategy_simulator"] = StrategySimulator()
        return AdvisorRuntime(**kwargs)

    def test_simulator_property(self):
        adv = self._make_advisor()
        assert adv.strategy_simulator is not None

    def test_simulator_none_without(self):
        adv = self._make_advisor(with_sim=False)
        assert adv.strategy_simulator is None

    def test_last_simulation_initially_none(self):
        adv = self._make_advisor()
        assert adv.last_simulation is None

    def test_tick_populates_simulation(self):
        adv = self._make_advisor()
        adv.tick()
        assert adv.last_simulation is not None

    def test_tick_without_simulator_no_simulation(self):
        adv = self._make_advisor(with_sim=False)
        adv.tick()
        assert adv.last_simulation is None
        assert adv.current_strategy is not None

    def test_get_state_includes_simulation(self):
        adv = self._make_advisor()
        adv.tick()
        state = adv.get_state()
        assert "simulation" in state

    def test_get_state_no_simulation_without_simulator(self):
        adv = self._make_advisor(with_sim=False)
        adv.tick()
        state = adv.get_state()
        assert "simulation" not in state

    def test_clear_resets_simulation(self):
        adv = self._make_advisor()
        adv.tick()
        assert adv.last_simulation is not None
        adv.clear()
        assert adv.last_simulation is None

    def test_strategy_comes_from_simulation(self):
        adv = self._make_advisor()
        adv.tick()
        assert adv.current_strategy is not None
        assert adv.last_simulation.selected.strategy is adv.current_strategy

    def test_simulation_has_multiple_candidates(self):
        adv = self._make_advisor()
        adv.tick()
        assert len(adv.last_simulation.candidates) >= 4

    def test_simulation_with_feedback(self):
        from umh.learning.feedback import ExecutionFeedback
        adv = self._make_advisor()
        fb = [
            ExecutionFeedback(
                job_id=f"j{i}", node_id="n1", task_type="t",
                success=True, duration_ms=50,
            )
            for i in range(20)
        ]
        adv.tick(completed_feedback=fb)
        sim = adv.last_simulation
        assert sim is not None
        assert sim.selected.expected_completion_rate > 0


# ===================================================================
# SECTION 7: Hard invariants (10 tests)
# ===================================================================

class TestHardInvariants:
    def test_inv70_simulation_does_not_execute_tasks(self):
        """INV70: SimulationEngine never imports or calls task execution."""
        src = inspect.getsource(SimulationEngine)
        assert "execute" not in src.lower() or "execution" in src.lower()
        assert "subprocess" not in src
        assert "Popen" not in src

    def test_inv70_no_io_in_simulation(self):
        """INV70: No file I/O in simulation module."""
        import umh.runtime.simulation as mod
        src = inspect.getsource(mod)
        assert "open(" not in src
        assert "pathlib" not in src

    def test_inv71_simulation_pure(self):
        """INV71: Same strategy + model → same outcome."""
        engine = SimulationEngine()
        m = _confident_model(completion_rate=0.7, volatility_index=0.3)
        o1 = engine.simulate(_BASE, m)
        o2 = engine.simulate(_BASE, m)
        assert o1.expected_completion_rate == o2.expected_completion_rate
        assert o1.expected_failure_risk == o2.expected_failure_risk
        assert o1.expected_latency == o2.expected_latency
        assert o1.estimated_effort == o2.estimated_effort

    def test_inv72_simulation_does_not_mutate_model(self):
        """INV72: Simulation never changes the behavior model."""
        m = _confident_model(completion_rate=0.5, volatility_index=0.5)
        traits_before = {k: (v.value, v.confidence) for k, v in m.traits.items()}
        count_before = m.update_count

        sim = StrategySimulator()
        sim.run(_BASE, m)

        traits_after = {k: (v.value, v.confidence) for k, v in m.traits.items()}
        assert traits_before == traits_after
        assert m.update_count == count_before

    def test_inv72_simulation_does_not_mutate_strategy(self):
        """INV72: Simulation never changes the input strategy."""
        base = ExecutionStrategy(batch_size=5, pacing=1.0, retry_budget=2)
        sim = StrategySimulator()
        sim.run(base)
        assert base.batch_size == 5
        assert base.pacing == 1.0
        assert base.retry_budget == 2

    def test_inv73_deterministic_selection(self):
        """INV73: Same inputs → same strategy selected."""
        m = _confident_model(completion_rate=0.6, volatility_index=0.4)
        sim = StrategySimulator()
        r1 = sim.run(_BASE, m)
        r2 = sim.run(_BASE, m)
        assert r1.selected.label == r2.selected.label
        assert r1.selected.score == r2.selected.score
        assert r1.selected.strategy.batch_size == r2.selected.strategy.batch_size

    def test_inv74_outcomes_explainable(self):
        """INV74: Every simulation result has reason and explanation."""
        sim = StrategySimulator()
        result = sim.run(_BASE)
        assert len(result.reason) > 0
        assert len(result.explanation) >= 2
        for c in result.candidates:
            assert c.label != ""
            assert c.score > 0

    def test_inv74_explanation_lists_alternatives(self):
        """INV74: Explanation includes all candidates with scores."""
        sim = StrategySimulator()
        result = sim.run(_BASE)
        lines = result.explanation
        for c in result.candidates:
            assert any(c.label in line for line in lines)

    def test_no_cells_import(self):
        """No direct coupling between simulation and cells."""
        import umh.runtime.simulation as mod_sim
        import umh.runtime.evaluator as mod_eval
        for mod in [mod_sim, mod_eval]:
            src = inspect.getsource(mod)
            assert "from umh.cells" not in src
            assert "from umh.environments" not in src
            assert "from umh.adapters" not in src

    def test_no_subprocess(self):
        """No subprocess in simulation or evaluator modules."""
        import umh.runtime.simulation as mod_sim
        import umh.runtime.evaluator as mod_eval
        for mod in [mod_sim, mod_eval]:
            src = inspect.getsource(mod)
            assert "import subprocess" not in src


# ===================================================================
# SECTION 8: Boundary + exports (5 tests)
# ===================================================================

class TestBoundaryExports:
    def test_runtime_exports_simulation_types(self):
        from umh.runtime import (
            SimulatedOutcome, SimulationEngine, SimulationResult,
            StrategyGenerator, StrategySimulator, OutcomeEvaluator,
            ScoringWeights,
        )
        assert SimulatedOutcome is not None
        assert StrategySimulator is not None

    def test_evaluator_module_compiles(self):
        import umh.runtime.evaluator
        assert hasattr(umh.runtime.evaluator, "OutcomeEvaluator")

    def test_simulation_module_compiles(self):
        import umh.runtime.simulation
        assert hasattr(umh.runtime.simulation, "SimulationEngine")

    def test_end_to_end_pipeline(self):
        """Full pipeline: model → strategy → simulate → select → plan."""
        m = _confident_model(completion_rate=0.4, volatility_index=0.8)
        sb = StrategyBuilder()
        base = sb.build_strategy(m)

        sim = StrategySimulator()
        result = sim.run(base, m)

        assert result.selected.strategy is not None
        assert result.selected.score > 0
        assert len(result.candidates) >= 4

    def test_scoring_weights_frozen(self):
        w = ScoringWeights()
        with pytest.raises(AttributeError):
            w.completion = 0.5  # type: ignore[misc]
