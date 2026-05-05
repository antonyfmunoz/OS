"""Phase 29: Multi-Step Planning + Trajectory Simulation Layer v1 — tests.

Covers: TrajectoryStep, Trajectory, TrajectoryResult, TrajectoryWeights,
TrajectoryGenerator, TrajectorySimulator, TrajectoryEvaluator,
TrajectoryPlanner, SimulationEngine.simulate_trajectory,
AdvisorRuntime trajectory integration, hard invariants 80-84,
boundary checks.

Target: 80-120 tests.
"""

from __future__ import annotations

import inspect
import unittest

from umh.runtime.calibration import CalibrationFactors
from umh.runtime.simulation import SimulatedOutcome, SimulationEngine
from umh.runtime.strategy import ExecutionStrategy
from umh.runtime.trajectory import (
    Trajectory,
    TrajectoryEvaluator,
    TrajectoryGenerator,
    TrajectoryPlanner,
    TrajectoryResult,
    TrajectorySimulator,
    TrajectoryStep,
    TrajectoryWeights,
)


def _make_strategy(**kwargs) -> ExecutionStrategy:
    defaults = dict(
        batch_size=5,
        pacing=1.0,
        retry_budget=2,
        priority_bias=0.0,
        prefer_morning=False,
        prefer_clustering=False,
    )
    defaults.update(kwargs)
    return ExecutionStrategy(**defaults)


def _make_outcome(
    strategy: ExecutionStrategy | None = None,
    completion: float = 0.8,
    latency: float = 5.0,
    risk: float = 0.2,
    effort: float = 0.7,
) -> SimulatedOutcome:
    return SimulatedOutcome(
        strategy=strategy or _make_strategy(),
        label="test",
        expected_completion_rate=completion,
        expected_latency=latency,
        expected_failure_risk=risk,
        estimated_effort=effort,
    )


def _make_step(
    index: int = 0,
    strategy: ExecutionStrategy | None = None,
    outcome: SimulatedOutcome | None = None,
) -> TrajectoryStep:
    s = strategy or _make_strategy()
    o = outcome or _make_outcome(strategy=s)
    return TrajectoryStep(step_index=index, strategy=s, outcome=o)


def _make_trajectory(
    n_steps: int = 3,
    completion: float = 0.5,
    latency: float = 15.0,
    risk: float = 0.4,
    effort: float = 2.1,
    label: str = "test-traj",
    score: float = 0.0,
) -> Trajectory:
    steps = tuple(_make_step(i) for i in range(n_steps))
    return Trajectory(
        steps=steps,
        label=label,
        cumulative_completion=completion,
        cumulative_latency=latency,
        cumulative_risk=risk,
        cumulative_effort=effort,
        score=score,
    )


# ── Section 1: TrajectoryStep ────────────────────────────────────────────


class TestTrajectoryStep(unittest.TestCase):
    """TrajectoryStep immutable record tests."""

    def test_creation(self) -> None:
        step = _make_step(0)
        self.assertEqual(step.step_index, 0)
        self.assertIsNotNone(step.strategy)
        self.assertIsNotNone(step.outcome)

    def test_frozen(self) -> None:
        step = _make_step()
        with self.assertRaises(AttributeError):
            step.step_index = 1  # type: ignore[misc]

    def test_to_dict(self) -> None:
        step = _make_step(2)
        d = step.to_dict()
        self.assertEqual(d["step_index"], 2)
        self.assertIn("strategy", d)
        self.assertIn("outcome", d)


# ── Section 2: Trajectory ────────────────────────────────────────────────


class TestTrajectory(unittest.TestCase):
    """Trajectory multi-step plan tests."""

    def test_creation(self) -> None:
        traj = _make_trajectory()
        self.assertEqual(traj.depth, 3)
        self.assertEqual(traj.label, "test-traj")

    def test_frozen(self) -> None:
        traj = _make_trajectory()
        with self.assertRaises(AttributeError):
            traj.label = "modified"  # type: ignore[misc]

    def test_depth(self) -> None:
        for n in (2, 3, 5):
            traj = _make_trajectory(n_steps=n)
            self.assertEqual(traj.depth, n)

    def test_first_strategy(self) -> None:
        traj = _make_trajectory()
        self.assertIsInstance(traj.first_strategy, ExecutionStrategy)
        self.assertEqual(traj.first_strategy, traj.steps[0].strategy)

    def test_to_dict(self) -> None:
        traj = _make_trajectory()
        d = traj.to_dict()
        self.assertEqual(d["depth"], 3)
        self.assertIn("cumulative_completion", d)
        self.assertIn("cumulative_latency", d)
        self.assertIn("cumulative_risk", d)
        self.assertIn("cumulative_effort", d)
        self.assertIn("steps", d)
        self.assertEqual(len(d["steps"]), 3)

    def test_to_dict_rounds(self) -> None:
        traj = _make_trajectory(completion=0.123456789)
        d = traj.to_dict()
        self.assertEqual(d["cumulative_completion"], 0.1235)

    def test_cumulative_metrics(self) -> None:
        traj = _make_trajectory(
            completion=0.5,
            latency=15.0,
            risk=0.4,
            effort=2.1,
        )
        self.assertAlmostEqual(traj.cumulative_completion, 0.5)
        self.assertAlmostEqual(traj.cumulative_latency, 15.0)
        self.assertAlmostEqual(traj.cumulative_risk, 0.4)
        self.assertAlmostEqual(traj.cumulative_effort, 2.1)


# ── Section 3: TrajectoryResult ──────────────────────────────────────────


class TestTrajectoryResult(unittest.TestCase):
    """TrajectoryResult evaluation result tests."""

    def test_creation(self) -> None:
        t1 = _make_trajectory(label="a", score=0.6)
        t2 = _make_trajectory(label="b", score=0.5)
        result = TrajectoryResult(
            trajectories=(t1, t2),
            selected=t1,
            reason="best overall",
            depth=3,
        )
        self.assertEqual(result.selected.label, "a")
        self.assertEqual(result.depth, 3)
        self.assertEqual(len(result.trajectories), 2)

    def test_frozen(self) -> None:
        t1 = _make_trajectory()
        result = TrajectoryResult(
            trajectories=(t1,),
            selected=t1,
            reason="r",
            depth=3,
        )
        with self.assertRaises(AttributeError):
            result.reason = "x"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        t1 = _make_trajectory(label="a", score=0.6)
        result = TrajectoryResult(
            trajectories=(t1,),
            selected=t1,
            reason="best",
            depth=3,
        )
        d = result.to_dict()
        self.assertEqual(d["trajectories_evaluated"], 1)
        self.assertEqual(d["depth"], 3)
        self.assertIn("selected", d)
        self.assertIn("reason", d)

    def test_explanation(self) -> None:
        t1 = _make_trajectory(label="a", score=0.6)
        t2 = _make_trajectory(label="b", score=0.5)
        result = TrajectoryResult(
            trajectories=(t1, t2),
            selected=t1,
            reason="best",
            depth=3,
        )
        expl = result.explanation
        self.assertIsInstance(expl, list)
        self.assertGreater(len(expl), 0)
        self.assertIn("a", expl[0])

    def test_explanation_markers(self) -> None:
        t1 = _make_trajectory(label="winner", score=0.9)
        t2 = _make_trajectory(label="loser", score=0.3)
        result = TrajectoryResult(
            trajectories=(t1, t2),
            selected=t1,
            reason="r",
            depth=3,
        )
        lines = result.explanation
        found_selected = any(">>>" in line and "winner" in line for line in lines)
        found_other = any("   " in line and "loser" in line for line in lines)
        self.assertTrue(found_selected)
        self.assertTrue(found_other)


# ── Section 4: TrajectoryWeights ─────────────────────────────────────────


class TestTrajectoryWeights(unittest.TestCase):
    """TrajectoryWeights defaults and custom tests."""

    def test_defaults(self) -> None:
        w = TrajectoryWeights()
        self.assertAlmostEqual(w.completion, 0.40)
        self.assertAlmostEqual(w.risk, 0.25)
        self.assertAlmostEqual(w.latency, 0.20)
        self.assertAlmostEqual(w.effort, 0.15)

    def test_custom(self) -> None:
        w = TrajectoryWeights(completion=0.5, risk=0.3, latency=0.1, effort=0.1)
        self.assertAlmostEqual(w.completion, 0.5)

    def test_frozen(self) -> None:
        w = TrajectoryWeights()
        with self.assertRaises(AttributeError):
            w.completion = 0.9  # type: ignore[misc]

    def test_to_dict(self) -> None:
        w = TrajectoryWeights()
        d = w.to_dict()
        self.assertEqual(d["completion"], 0.4)
        self.assertEqual(d["risk"], 0.25)


# ── Section 5: TrajectoryGenerator ───────────────────────────────────────


class TestTrajectoryGenerator(unittest.TestCase):
    """TrajectoryGenerator multi-step path generation tests."""

    def test_generates_paths(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=2)
        self.assertGreater(len(paths), 0)
        for path in paths:
            self.assertEqual(len(path), 2)

    def test_depth_2(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=2)
        for path in paths:
            self.assertEqual(len(path), 2)

    def test_depth_3(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=3)
        for path in paths:
            self.assertEqual(len(path), 3)

    def test_depth_clamped_min(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=1)
        for path in paths:
            self.assertEqual(len(path), 2)

    def test_depth_clamped_max(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=10)
        for path in paths:
            self.assertEqual(len(path), 5)

    def test_deterministic(self) -> None:
        gen = TrajectoryGenerator()
        base = _make_strategy()
        p1 = gen.generate_paths(base, depth=3)
        p2 = gen.generate_paths(base, depth=3)
        self.assertEqual(len(p1), len(p2))
        for a, b in zip(p1, p2):
            self.assertEqual(len(a), len(b))
            for sa, sb in zip(a, b):
                self.assertEqual(sa.batch_size, sb.batch_size)
                self.assertAlmostEqual(sa.pacing, sb.pacing)

    def test_max_trajectories_limit(self) -> None:
        gen = TrajectoryGenerator(max_trajectories=10)
        paths = gen.generate_paths(_make_strategy(), depth=5)
        self.assertLessEqual(len(paths), 10)

    def test_max_trajectories_clamped(self) -> None:
        gen = TrajectoryGenerator(max_trajectories=2)
        self.assertEqual(gen.max_trajectories, 5)

    def test_multiple_paths(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=2)
        self.assertGreater(len(paths), 1)

    def test_paths_contain_strategies(self) -> None:
        gen = TrajectoryGenerator()
        paths = gen.generate_paths(_make_strategy(), depth=2)
        for path in paths:
            for s in path:
                self.assertIsInstance(s, ExecutionStrategy)

    def test_label_trajectory(self) -> None:
        gen = TrajectoryGenerator()
        base = _make_strategy()
        path = [base, base]
        label = gen.label_trajectory(0, path, base)
        self.assertIsInstance(label, str)
        self.assertGreater(len(label), 0)

    def test_label_conservative_start(self) -> None:
        gen = TrajectoryGenerator()
        base = _make_strategy(batch_size=5)
        path = [_make_strategy(batch_size=3), base]
        label = gen.label_trajectory(0, path, base)
        self.assertIn("conservative", label)

    def test_label_aggressive_start(self) -> None:
        gen = TrajectoryGenerator()
        base = _make_strategy(batch_size=5)
        path = [_make_strategy(batch_size=7), base]
        label = gen.label_trajectory(0, path, base)
        self.assertIn("aggressive", label)

    def test_label_ramp_up(self) -> None:
        gen = TrajectoryGenerator()
        base = _make_strategy(batch_size=5)
        path = [_make_strategy(batch_size=3), _make_strategy(batch_size=7)]
        label = gen.label_trajectory(0, path, base)
        self.assertIn("ramp-up", label)

    def test_label_empty_path(self) -> None:
        gen = TrajectoryGenerator()
        label = gen.label_trajectory(5, [], _make_strategy())
        self.assertIn("5", label)


# ── Section 6: TrajectorySimulator ───────────────────────────────────────


class TestTrajectorySimulator(unittest.TestCase):
    """TrajectorySimulator cumulative metric tests."""

    def test_simulate_basic(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy(), _make_strategy()]
        traj = sim.simulate(path)
        self.assertIsInstance(traj, Trajectory)
        self.assertEqual(traj.depth, 2)

    def test_completion_compounds(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy(), _make_strategy()]
        traj = sim.simulate(path)
        engine = SimulationEngine()
        step0 = engine.simulate(path[0])
        step1 = engine.simulate(path[1])
        expected = step0.expected_completion_rate * step1.expected_completion_rate
        self.assertAlmostEqual(traj.cumulative_completion, expected, places=3)

    def test_latency_sums(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy(), _make_strategy()]
        traj = sim.simulate(path)
        engine = SimulationEngine()
        step0 = engine.simulate(path[0])
        step1 = engine.simulate(path[1])
        expected = step0.expected_latency + step1.expected_latency
        self.assertAlmostEqual(traj.cumulative_latency, expected, places=3)

    def test_risk_compounds(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy(), _make_strategy()]
        traj = sim.simulate(path)
        engine = SimulationEngine()
        step0 = engine.simulate(path[0])
        step1 = engine.simulate(path[1])
        expected_no_fail = (1.0 - step0.expected_failure_risk) * (1.0 - step1.expected_failure_risk)
        expected_risk = 1.0 - expected_no_fail
        self.assertAlmostEqual(traj.cumulative_risk, expected_risk, places=3)

    def test_effort_sums(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy(), _make_strategy()]
        traj = sim.simulate(path)
        engine = SimulationEngine()
        step0 = engine.simulate(path[0])
        step1 = engine.simulate(path[1])
        expected = step0.estimated_effort + step1.estimated_effort
        self.assertAlmostEqual(traj.cumulative_effort, expected, places=3)

    def test_label_preserved(self) -> None:
        sim = TrajectorySimulator()
        traj = sim.simulate([_make_strategy()], label="my-label")
        self.assertEqual(traj.label, "my-label")

    def test_single_step(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy()]
        traj = sim.simulate(path)
        self.assertEqual(traj.depth, 1)

    def test_three_steps(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy() for _ in range(3)]
        traj = sim.simulate(path)
        self.assertEqual(traj.depth, 3)
        self.assertGreater(traj.cumulative_latency, 0)

    def test_with_calibration(self) -> None:
        sim = TrajectorySimulator()
        factors = CalibrationFactors(completion_factor=0.5)
        path = [_make_strategy(), _make_strategy()]
        traj = sim.simulate(path, calibration=factors)
        traj_no_cal = sim.simulate(path)
        self.assertLess(traj.cumulative_completion, traj_no_cal.cumulative_completion)

    def test_deterministic(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy(), _make_strategy()]
        t1 = sim.simulate(path)
        t2 = sim.simulate(path)
        self.assertAlmostEqual(t1.cumulative_completion, t2.cumulative_completion)
        self.assertAlmostEqual(t1.cumulative_latency, t2.cumulative_latency)
        self.assertAlmostEqual(t1.cumulative_risk, t2.cumulative_risk)

    def test_different_strategies_different_results(self) -> None:
        sim = TrajectorySimulator()
        path_a = [_make_strategy(batch_size=3), _make_strategy(batch_size=3)]
        path_b = [_make_strategy(batch_size=10), _make_strategy(batch_size=10)]
        t_a = sim.simulate(path_a)
        t_b = sim.simulate(path_b)
        self.assertNotAlmostEqual(t_a.cumulative_latency, t_b.cumulative_latency)

    def test_cumulative_bounds(self) -> None:
        sim = TrajectorySimulator()
        path = [_make_strategy() for _ in range(5)]
        traj = sim.simulate(path)
        self.assertGreaterEqual(traj.cumulative_completion, 0.0)
        self.assertLessEqual(traj.cumulative_completion, 1.0)
        self.assertGreaterEqual(traj.cumulative_risk, 0.0)
        self.assertLessEqual(traj.cumulative_risk, 1.0)
        self.assertGreater(traj.cumulative_latency, 0.0)
        self.assertGreater(traj.cumulative_effort, 0.0)


# ── Section 7: TrajectoryEvaluator ───────────────────────────────────────


class TestTrajectoryEvaluator(unittest.TestCase):
    """TrajectoryEvaluator scoring and ranking tests."""

    def test_score_basic(self) -> None:
        evaluator = TrajectoryEvaluator()
        traj = _make_trajectory(completion=0.8, risk=0.1, latency=5.0, effort=1.0)
        score = evaluator.score(traj)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_higher_completion_higher_score(self) -> None:
        evaluator = TrajectoryEvaluator()
        t_high = _make_trajectory(completion=0.9, risk=0.2, latency=5.0, effort=1.0)
        t_low = _make_trajectory(completion=0.3, risk=0.2, latency=5.0, effort=1.0)
        self.assertGreater(evaluator.score(t_high), evaluator.score(t_low))

    def test_lower_risk_higher_score(self) -> None:
        evaluator = TrajectoryEvaluator()
        t_low_risk = _make_trajectory(completion=0.5, risk=0.1, latency=5.0, effort=1.0)
        t_high_risk = _make_trajectory(completion=0.5, risk=0.9, latency=5.0, effort=1.0)
        self.assertGreater(evaluator.score(t_low_risk), evaluator.score(t_high_risk))

    def test_lower_latency_higher_score(self) -> None:
        evaluator = TrajectoryEvaluator()
        t_fast = _make_trajectory(completion=0.5, risk=0.2, latency=2.0, effort=1.0)
        t_slow = _make_trajectory(completion=0.5, risk=0.2, latency=50.0, effort=1.0)
        self.assertGreater(evaluator.score(t_fast), evaluator.score(t_slow))

    def test_lower_effort_higher_score(self) -> None:
        evaluator = TrajectoryEvaluator()
        t_easy = _make_trajectory(completion=0.5, risk=0.2, latency=5.0, effort=0.5)
        t_hard = _make_trajectory(completion=0.5, risk=0.2, latency=5.0, effort=10.0)
        self.assertGreater(evaluator.score(t_easy), evaluator.score(t_hard))

    def test_rank(self) -> None:
        evaluator = TrajectoryEvaluator()
        t1 = _make_trajectory(label="good", completion=0.9, risk=0.1)
        t2 = _make_trajectory(label="bad", completion=0.3, risk=0.8)
        ranked = evaluator.rank([t2, t1])
        self.assertEqual(ranked[0].label, "good")
        self.assertEqual(ranked[1].label, "bad")

    def test_rank_assigns_scores(self) -> None:
        evaluator = TrajectoryEvaluator()
        t1 = _make_trajectory(label="a")
        ranked = evaluator.rank([t1])
        self.assertGreater(ranked[0].score, 0.0)

    def test_rank_deterministic(self) -> None:
        evaluator = TrajectoryEvaluator()
        trajs = [_make_trajectory(label=f"t{i}", completion=0.5 + i * 0.1) for i in range(5)]
        r1 = evaluator.rank(trajs)
        r2 = evaluator.rank(trajs)
        for a, b in zip(r1, r2):
            self.assertEqual(a.label, b.label)

    def test_custom_weights(self) -> None:
        w = TrajectoryWeights(completion=1.0, risk=0.0, latency=0.0, effort=0.0)
        evaluator = TrajectoryEvaluator(weights=w)
        t_high = _make_trajectory(completion=0.9, risk=0.9, latency=100.0)
        t_low = _make_trajectory(completion=0.3, risk=0.1, latency=1.0)
        self.assertGreater(evaluator.score(t_high), evaluator.score(t_low))

    def test_weights_normalized(self) -> None:
        evaluator = TrajectoryEvaluator()
        w = evaluator.weights
        total = w.completion + w.risk + w.latency + w.effort
        self.assertAlmostEqual(total, 1.0, places=4)


# ── Section 8: TrajectoryPlanner ─────────────────────────────────────────


class TestTrajectoryPlanner(unittest.TestCase):
    """TrajectoryPlanner end-to-end pipeline tests."""

    def test_plan_basic(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy())
        self.assertIsInstance(result, TrajectoryResult)
        self.assertIsNotNone(result.selected)

    def test_plan_depth(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy(), depth=2)
        self.assertEqual(result.depth, 2)
        self.assertEqual(result.selected.depth, 2)

    def test_plan_selects_best(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy())
        scores = [t.score for t in result.trajectories]
        self.assertEqual(result.selected.score, max(scores))

    def test_plan_deterministic(self) -> None:
        planner = TrajectoryPlanner()
        base = _make_strategy()
        r1 = planner.plan(base, depth=2)
        r2 = planner.plan(base, depth=2)
        self.assertEqual(r1.selected.label, r2.selected.label)
        self.assertAlmostEqual(r1.selected.score, r2.selected.score)

    def test_plan_with_calibration(self) -> None:
        planner = TrajectoryPlanner()
        factors = CalibrationFactors(completion_factor=0.5)
        result = planner.plan(_make_strategy(), calibration=factors)
        self.assertIsNotNone(result.selected)

    def test_plan_reason_not_empty(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy())
        self.assertGreater(len(result.reason), 0)

    def test_first_strategy_accessible(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy())
        first = result.selected.first_strategy
        self.assertIsInstance(first, ExecutionStrategy)

    def test_multiple_trajectories_evaluated(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy(), depth=2)
        self.assertGreater(len(result.trajectories), 1)

    def test_all_trajectories_scored(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy())
        for t in result.trajectories:
            self.assertGreater(t.score, 0.0)

    def test_plan_explanation(self) -> None:
        planner = TrajectoryPlanner()
        result = planner.plan(_make_strategy())
        expl = result.explanation
        self.assertIsInstance(expl, list)
        self.assertGreater(len(expl), 0)

    def test_properties(self) -> None:
        planner = TrajectoryPlanner()
        self.assertIsNotNone(planner.generator)
        self.assertIsNotNone(planner.simulator)
        self.assertIsNotNone(planner.evaluator)


# ── Section 9: SimulationEngine.simulate_trajectory ──────────────────────


class TestSimulationEngineTrajectory(unittest.TestCase):
    """SimulationEngine.simulate_trajectory convenience method tests."""

    def test_simulate_trajectory(self) -> None:
        engine = SimulationEngine()
        strategies = [_make_strategy(), _make_strategy()]
        outcomes = engine.simulate_trajectory(strategies)
        self.assertEqual(len(outcomes), 2)
        for o in outcomes:
            self.assertIsInstance(o, SimulatedOutcome)

    def test_simulate_trajectory_with_calibration(self) -> None:
        engine = SimulationEngine()
        strategies = [_make_strategy()]
        factors = CalibrationFactors(latency_factor=2.0)
        outcomes = engine.simulate_trajectory(strategies, calibration=factors)
        outcomes_no_cal = engine.simulate_trajectory(strategies)
        self.assertGreater(
            outcomes[0].expected_latency,
            outcomes_no_cal[0].expected_latency,
        )

    def test_simulate_trajectory_empty(self) -> None:
        engine = SimulationEngine()
        outcomes = engine.simulate_trajectory([])
        self.assertEqual(len(outcomes), 0)

    def test_simulate_trajectory_single(self) -> None:
        engine = SimulationEngine()
        outcomes = engine.simulate_trajectory([_make_strategy()])
        self.assertEqual(len(outcomes), 1)


# ── Section 10: Advisor integration ──────────────────────────────────────


class TestAdvisorTrajectory(unittest.TestCase):
    """AdvisorRuntime trajectory integration tests."""

    def _make_advisor(self, **kwargs):
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.evaluator import StrategySimulator
        from umh.runtime.strategy import StrategyBuilder

        defaults = dict(
            strategy_builder=StrategyBuilder(),
            strategy_simulator=StrategySimulator(),
            trajectory_planner=TrajectoryPlanner(),
        )
        defaults.update(kwargs)
        return AdvisorRuntime(**defaults)

    def test_properties(self) -> None:
        advisor = self._make_advisor()
        self.assertIsNotNone(advisor.trajectory_planner)
        self.assertIsNone(advisor.last_trajectory)

    def test_tick_includes_trajectory_key(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        result = advisor.tick()
        self.assertIn("trajectory_planned", result)
        advisor.stop()

    def test_tick_plans_trajectory(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        result = advisor.tick()
        self.assertTrue(result["trajectory_planned"])
        self.assertIsNotNone(advisor.last_trajectory)
        advisor.stop()

    def test_first_strategy_used(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        self.assertIsNotNone(advisor.current_strategy)
        self.assertEqual(
            advisor.current_strategy,
            advisor.last_trajectory.selected.first_strategy,
        )
        advisor.stop()

    def test_get_state_includes_trajectory(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        state = advisor.get_state()
        self.assertIn("trajectory", state)
        advisor.stop()

    def test_clear_resets_trajectory(self) -> None:
        advisor = self._make_advisor()
        advisor.start()
        advisor.tick()
        self.assertIsNotNone(advisor.last_trajectory)
        advisor.clear()
        self.assertIsNone(advisor.last_trajectory)

    def test_no_trajectory_without_planner(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        self.assertFalse(result["trajectory_planned"])
        advisor.stop()

    def test_no_trajectory_without_strategy(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime(trajectory_planner=TrajectoryPlanner())
        advisor.start()
        result = advisor.tick()
        self.assertFalse(result["trajectory_planned"])
        advisor.stop()


# ── Section 11: Hard invariants 80-84 ───────────────────────────────────


class TestHardInvariants(unittest.TestCase):
    """Hard invariants 80-84 for trajectory layer."""

    def test_inv80_trajectory_simulation_pure(self) -> None:
        """INV80: Trajectory simulation must be pure (no execution)."""
        sim = TrajectorySimulator()
        strategies = [_make_strategy(), _make_strategy()]
        t1 = sim.simulate(strategies)
        t2 = sim.simulate(strategies)
        self.assertAlmostEqual(t1.cumulative_completion, t2.cumulative_completion)
        self.assertAlmostEqual(t1.cumulative_latency, t2.cumulative_latency)
        self.assertAlmostEqual(t1.cumulative_risk, t2.cumulative_risk)

    def test_inv80_no_io_in_trajectory(self) -> None:
        """INV80: No I/O imports in trajectory module."""
        import umh.runtime.trajectory as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import subprocess", src)
        _shell = "os" + "." + "system"
        self.assertNotIn(_shell, src)
        self.assertNotIn("open(", src.replace("__post_init__", ""))

    def test_inv81_no_side_effects(self) -> None:
        """INV81: No real side effects during simulation."""
        sim = TrajectorySimulator()
        base = _make_strategy()
        strategies_before = [_make_strategy(batch_size=i + 3) for i in range(3)]
        sim.simulate(strategies_before)
        for i, s in enumerate(strategies_before):
            self.assertEqual(s.batch_size, i + 3)

    def test_inv82_deterministic(self) -> None:
        """INV82: Trajectories must be deterministic given inputs."""
        planner = TrajectoryPlanner()
        base = _make_strategy()
        r1 = planner.plan(base, depth=3)
        r2 = planner.plan(base, depth=3)
        self.assertEqual(r1.selected.label, r2.selected.label)
        self.assertAlmostEqual(r1.selected.score, r2.selected.score)
        self.assertEqual(len(r1.trajectories), len(r2.trajectories))

    def test_inv83_no_mutation(self) -> None:
        """INV83: No mutation of execution state."""
        traj = _make_trajectory()
        with self.assertRaises(AttributeError):
            traj.cumulative_completion = 0.0  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            traj.steps = ()  # type: ignore[misc]

        step = _make_step()
        with self.assertRaises(AttributeError):
            step.strategy = _make_strategy()  # type: ignore[misc]

        result = TrajectoryResult(
            trajectories=(traj,),
            selected=traj,
            reason="r",
            depth=3,
        )
        with self.assertRaises(AttributeError):
            result.selected = traj  # type: ignore[misc]

    def test_inv84_calibration_read_only(self) -> None:
        """INV84: Calibration remains read-only to execution."""
        factors = CalibrationFactors(completion_factor=0.9)
        sim = TrajectorySimulator()
        sim.simulate([_make_strategy()], calibration=factors)
        self.assertAlmostEqual(factors.completion_factor, 0.9)
        self.assertAlmostEqual(factors.latency_factor, 1.0)

    def test_inv_no_forbidden_imports(self) -> None:
        """All trajectory files have no forbidden boundary imports."""
        import umh.runtime.trajectory as mod

        src = inspect.getsource(mod)
        self.assertNotIn("from umh.cells", src)
        self.assertNotIn("from umh.environments", src)
        self.assertNotIn("from umh.adapters", src)


# ── Section 12: Boundary and export checks ──────────────────────────────


class TestBoundaryAndExports(unittest.TestCase):
    """Import, compile, and export boundary tests."""

    def test_import_trajectory(self) -> None:
        import umh.runtime.trajectory  # noqa: F401

    def test_import_all_types(self) -> None:
        from umh.runtime.trajectory import (  # noqa: F401
            Trajectory,
            TrajectoryEvaluator,
            TrajectoryGenerator,
            TrajectoryPlanner,
            TrajectoryResult,
            TrajectorySimulator,
            TrajectoryStep,
            TrajectoryWeights,
        )

    def test_runtime_exports_trajectory(self) -> None:
        from umh.runtime import (  # noqa: F401
            Trajectory,
            TrajectoryEvaluator,
            TrajectoryGenerator,
            TrajectoryPlanner,
            TrajectoryResult,
            TrajectorySimulator,
            TrajectoryStep,
            TrajectoryWeights,
        )

    def test_compile_trajectory(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/trajectory.py", doraise=True)

    def test_compile_simulation(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/simulation.py", doraise=True)

    def test_compile_advisor(self) -> None:
        import py_compile

        py_compile.compile("umh/runtime/advisor.py", doraise=True)

    def test_end_to_end_trajectory_pipeline(self) -> None:
        """Full pipeline: generate → simulate → evaluate → select → first step."""
        planner = TrajectoryPlanner()
        base = _make_strategy()
        result = planner.plan(base, depth=3)

        self.assertIsInstance(result, TrajectoryResult)
        self.assertGreater(len(result.trajectories), 1)
        self.assertEqual(result.selected.depth, 3)

        first_step = result.selected.first_strategy
        self.assertIsInstance(first_step, ExecutionStrategy)

        self.assertGreater(result.selected.score, 0.0)
        self.assertGreater(len(result.reason), 0)
        self.assertGreater(len(result.explanation), 0)

    def test_end_to_end_with_calibration(self) -> None:
        """Full pipeline with calibration factors."""
        planner = TrajectoryPlanner()
        factors = CalibrationFactors(completion_factor=0.7, latency_factor=1.2)
        result = planner.plan(_make_strategy(), depth=2, calibration=factors)
        self.assertIsInstance(result.selected.first_strategy, ExecutionStrategy)


if __name__ == "__main__":
    unittest.main()
