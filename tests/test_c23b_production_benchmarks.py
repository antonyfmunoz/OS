"""Tests for Campaign 23B production benchmarks (B, N, Q, R)."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import json

import pytest

from substrate.organism.benchmarks.autonomous_execution import (
    AutonomousExecutionBenchmark,
    AutonomousExecutionResult,
    SessionRecord,
)
from substrate.organism.benchmarks.outcome_accuracy import (
    OutcomeAccuracyBenchmark,
    OutcomeAccuracyResult,
    OutcomeRecord,
)
from substrate.organism.benchmarks.efficiency import (
    EfficiencyBenchmark,
    EfficiencyResult,
    ProductionCost,
)
from substrate.organism.benchmarks.reliability import (
    ReliabilityBenchmark,
    ReliabilityResult,
    ReliabilityTrial,
    _population_variance,
)


# --- Autonomous Execution (B) ---

class TestAutonomousExecution:
    def test_empty(self):
        b = AutonomousExecutionBenchmark()
        r = b.evaluate([])
        assert r.sessions_evaluated == 0
        assert r.recovery_rate == 0.0

    def test_single_session(self):
        s = SessionRecord(
            session_id="s1", duration_seconds=120.0,
            tasks_attempted=5, tasks_completed=4,
            errors_encountered=2, errors_recovered=1,
            operator_interventions=0,
            validation_attempts=4, validation_passes=3,
        )
        r = AutonomousExecutionBenchmark().evaluate([s])
        assert r.sessions_evaluated == 1
        assert r.avg_session_duration_seconds == 120.0
        assert r.avg_task_depth == 4.0
        assert r.recovery_rate == 0.5
        assert r.validation_pass_rate == 0.75
        assert r.autonomous_completion_rate == 4 / 5

    def test_with_interventions(self):
        sessions = [
            SessionRecord(session_id="s1", tasks_attempted=3, tasks_completed=3, operator_interventions=0),
            SessionRecord(session_id="s2", tasks_attempted=2, tasks_completed=2, operator_interventions=1),
        ]
        r = AutonomousExecutionBenchmark().evaluate(sessions)
        assert r.autonomous_completion_rate == 3 / 5

    def test_no_errors(self):
        s = SessionRecord(session_id="s1", errors_encountered=0, errors_recovered=0)
        r = AutonomousExecutionBenchmark().evaluate([s])
        assert r.recovery_rate == 0.0

    def test_no_validations(self):
        s = SessionRecord(session_id="s1", validation_attempts=0, validation_passes=0)
        r = AutonomousExecutionBenchmark().evaluate([s])
        assert r.validation_pass_rate == 0.0

    def test_perfect_session(self):
        s = SessionRecord(
            session_id="s1", tasks_attempted=10, tasks_completed=10,
            errors_encountered=1, errors_recovered=1,
            operator_interventions=0,
            validation_attempts=10, validation_passes=10,
        )
        r = AutonomousExecutionBenchmark().evaluate([s])
        assert r.autonomous_completion_rate == 1.0
        assert r.recovery_rate == 1.0
        assert r.validation_pass_rate == 1.0

    def test_to_dict(self):
        r = AutonomousExecutionResult(sessions_evaluated=5)
        d = r.to_dict()
        assert d["sessions_evaluated"] == 5


# --- Outcome Accuracy (N) ---

class TestOutcomeAccuracy:
    def test_empty(self):
        r = OutcomeAccuracyBenchmark().evaluate([])
        assert r.productions_evaluated == 0

    def test_full_achievement(self):
        o = OutcomeRecord(
            production_id="p1",
            acceptance_criteria=["a", "b", "c"],
            criteria_met=[True, True, True],
            tests_passed=True,
            deployed=True,
        )
        r = OutcomeAccuracyBenchmark().evaluate([o])
        assert r.intent_achievement_rate == 1.0
        assert r.full_achievement_count == 1
        assert r.deployment_success_rate == 1.0

    def test_partial_achievement(self):
        o = OutcomeRecord(
            acceptance_criteria=["a", "b", "c", "d"],
            criteria_met=[True, True, False, False],
        )
        r = OutcomeAccuracyBenchmark().evaluate([o])
        assert r.intent_achievement_rate == 0.5
        assert r.partial_achievement_count == 1

    def test_zero_achievement(self):
        o = OutcomeRecord(
            acceptance_criteria=["a", "b"],
            criteria_met=[False, False],
        )
        r = OutcomeAccuracyBenchmark().evaluate([o])
        assert r.intent_achievement_rate == 0.0
        assert r.zero_achievement_count == 1

    def test_no_criteria(self):
        o = OutcomeRecord(production_id="p1")
        r = OutcomeAccuracyBenchmark().evaluate([o])
        assert r.intent_achievement_rate == 0.0
        assert r.zero_achievement_count == 1

    def test_multiple_outcomes(self):
        outcomes = [
            OutcomeRecord(acceptance_criteria=["a"], criteria_met=[True], tests_passed=True, deployed=True),
            OutcomeRecord(acceptance_criteria=["a", "b"], criteria_met=[True, False], tests_passed=False, deployed=False),
        ]
        r = OutcomeAccuracyBenchmark().evaluate(outcomes)
        assert r.intent_achievement_rate == 2 / 3
        assert r.deployment_success_rate == 0.5
        assert r.test_pass_rate == 0.5

    def test_to_dict(self):
        r = OutcomeAccuracyResult(productions_evaluated=3)
        d = r.to_dict()
        assert d["productions_evaluated"] == 3


# --- Efficiency (Q) ---

class TestEfficiency:
    def test_empty(self):
        r = EfficiencyBenchmark().evaluate([])
        assert r.productions_evaluated == 0

    def test_single_production(self):
        c = ProductionCost(
            production_id="p1", tokens_consumed=10000,
            api_cost_usd=0.50, human_hours=2.0,
            output_loc=200, capabilities_reused=3,
        )
        r = EfficiencyBenchmark().evaluate([c])
        assert r.avg_cost_per_production == 0.50
        assert r.avg_tokens_per_production == 10000
        assert r.total_loc == 200
        assert r.capability_per_dollar == 3 / 0.50

    def test_cost_per_loc(self):
        c = ProductionCost(api_cost_usd=1.0, output_loc=100)
        r = EfficiencyBenchmark().evaluate([c])
        assert r.avg_cost_per_loc == 0.01

    def test_cost_per_loc_zero_loc(self):
        c = ProductionCost(api_cost_usd=1.0, output_loc=0)
        r = EfficiencyBenchmark().evaluate([c])
        assert r.avg_cost_per_loc == 0.0

    def test_human_hours_saved_ratio(self):
        c = ProductionCost(output_loc=500, human_hours=2.0)
        r = EfficiencyBenchmark().evaluate([c])
        expected = (500 / 50.0) / 2.0
        assert abs(r.human_hours_saved_ratio - expected) < 0.001

    def test_zero_human_hours(self):
        c = ProductionCost(output_loc=100, human_hours=0.0)
        r = EfficiencyBenchmark().evaluate([c])
        assert r.human_hours_saved_ratio == 0.0

    def test_trend_improving(self):
        costs = [
            ProductionCost(api_cost_usd=1.0),
            ProductionCost(api_cost_usd=0.9),
            ProductionCost(api_cost_usd=0.5),
            ProductionCost(api_cost_usd=0.4),
        ]
        r = EfficiencyBenchmark().evaluate(costs)
        assert r.cost_trend == "improving"

    def test_trend_worsening(self):
        costs = [
            ProductionCost(api_cost_usd=0.4),
            ProductionCost(api_cost_usd=0.5),
            ProductionCost(api_cost_usd=0.9),
            ProductionCost(api_cost_usd=1.0),
        ]
        r = EfficiencyBenchmark().evaluate(costs)
        assert r.cost_trend == "worsening"

    def test_trend_stable(self):
        costs = [
            ProductionCost(api_cost_usd=1.0),
            ProductionCost(api_cost_usd=1.0),
            ProductionCost(api_cost_usd=1.0),
            ProductionCost(api_cost_usd=1.0),
        ]
        r = EfficiencyBenchmark().evaluate(costs)
        assert r.cost_trend == "stable"

    def test_trend_single(self):
        r = EfficiencyBenchmark().evaluate([ProductionCost(api_cost_usd=1.0)])
        assert r.cost_trend == "stable"

    def test_zero_cost(self):
        c = ProductionCost(api_cost_usd=0.0, capabilities_reused=5)
        r = EfficiencyBenchmark().evaluate([c])
        assert r.capability_per_dollar == 0.0

    def test_to_dict(self):
        r = EfficiencyResult(productions_evaluated=2, cost_trend="stable")
        d = r.to_dict()
        assert d["cost_trend"] == "stable"


# --- Reliability (R) ---

class TestReliability:
    def test_empty(self):
        r = ReliabilityBenchmark().evaluate([])
        assert r.trials_run == 0

    def test_all_success(self):
        trials = [
            ReliabilityTrial(trial_id=f"t{i}", success=True, duration_seconds=10.0)
            for i in range(5)
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.success_rate == 1.0
        assert r.failure_frequency == 0.0
        assert r.success_variance == 0.0

    def test_all_failure(self):
        trials = [
            ReliabilityTrial(trial_id=f"t{i}", success=False, duration_seconds=5.0)
            for i in range(3)
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.success_rate == 0.0
        assert r.failure_frequency == 1.0
        assert r.success_variance == 0.0

    def test_mixed(self):
        trials = [
            ReliabilityTrial(success=True, duration_seconds=10.0),
            ReliabilityTrial(success=False, duration_seconds=20.0),
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.success_rate == 0.5
        assert r.success_variance == 0.25
        assert r.mean_duration == 15.0

    def test_duration_variance(self):
        trials = [
            ReliabilityTrial(duration_seconds=10.0),
            ReliabilityTrial(duration_seconds=10.0),
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.duration_variance == 0.0

    def test_consistency_score_perfect(self):
        trials = [
            ReliabilityTrial(duration_seconds=10.0),
            ReliabilityTrial(duration_seconds=10.0),
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.consistency_score == 1.0

    def test_consistency_score_clamped(self):
        trials = [
            ReliabilityTrial(duration_seconds=1.0),
            ReliabilityTrial(duration_seconds=100.0),
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert 0.0 <= r.consistency_score <= 1.0

    def test_recovery_rate(self):
        trials = [
            ReliabilityTrial(defect_count=3, recovery_count=2),
            ReliabilityTrial(defect_count=2, recovery_count=2),
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.recovery_success_rate == 4 / 5

    def test_no_defects(self):
        trials = [ReliabilityTrial(defect_count=0, recovery_count=0)]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.recovery_success_rate == 0.0

    def test_mean_defect_count(self):
        trials = [
            ReliabilityTrial(defect_count=2),
            ReliabilityTrial(defect_count=4),
        ]
        r = ReliabilityBenchmark().evaluate(trials)
        assert r.mean_defect_count == 3.0

    def test_to_dict(self):
        r = ReliabilityResult(trials_run=10, consistency_score=0.85)
        d = r.to_dict()
        assert d["consistency_score"] == 0.85


class TestPopulationVariance:
    def test_empty(self):
        assert _population_variance([]) == 0.0

    def test_constant(self):
        assert _population_variance([5.0, 5.0, 5.0]) == 0.0

    def test_known(self):
        v = _population_variance([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert abs(v - 4.0) < 0.001

    def test_single(self):
        assert _population_variance([42.0]) == 0.0


class TestAllJsonSerializable:
    def test_autonomous(self):
        r = AutonomousExecutionBenchmark().evaluate([
            SessionRecord(session_id="s1", tasks_attempted=3, tasks_completed=2)
        ])
        json.dumps(r.to_dict())

    def test_outcome(self):
        r = OutcomeAccuracyBenchmark().evaluate([
            OutcomeRecord(acceptance_criteria=["a"], criteria_met=[True])
        ])
        json.dumps(r.to_dict())

    def test_efficiency(self):
        r = EfficiencyBenchmark().evaluate([
            ProductionCost(api_cost_usd=1.0, output_loc=100)
        ])
        json.dumps(r.to_dict())

    def test_reliability(self):
        r = ReliabilityBenchmark().evaluate([
            ReliabilityTrial(success=True, duration_seconds=10.0)
        ])
        json.dumps(r.to_dict())
