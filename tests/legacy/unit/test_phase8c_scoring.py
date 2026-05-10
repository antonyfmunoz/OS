"""Phase 8C — Strategy scoring tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from umh.strategy.history import PerformanceMetrics, StrategyVersion
from umh.strategy.models import Strategy, StrategyStep, StepComplexity
from umh.strategy.scoring import (
    StrategyScore,
    compare_versions,
    score_strategy,
)


class TestStrategyScore:
    def test_to_dict(self):
        s = StrategyScore(efficiency=0.8, reliability=0.9, complexity=0.7, overall=0.82)
        d = s.to_dict()
        assert d["efficiency"] == 0.8
        assert d["reliability"] == 0.9
        assert d["overall"] == 0.82


class TestScoring:
    def _make_version(self, completed=5, failed=0, retried=0, evaluations=5, steps=None):
        if steps is None:
            steps = [StrategyStep(description="test")]
        s = Strategy(goal_id="g1", objective="test", steps=steps)
        perf = PerformanceMetrics(
            tasks_completed=completed,
            tasks_failed=failed,
            tasks_retried=retried,
            evaluations=evaluations,
        )
        return StrategyVersion(strategy=s, performance=perf)

    def test_perfect_score(self):
        v = self._make_version(completed=10, failed=0, evaluations=10)
        score = score_strategy(v)
        assert score.efficiency > 0.8
        assert score.reliability > 0.9
        assert score.overall > 0.7

    def test_zero_evaluations(self):
        v = self._make_version(completed=0, failed=0, evaluations=0)
        score = score_strategy(v)
        assert score.efficiency == 0.5
        assert score.reliability == 0.5

    def test_high_failure_low_reliability(self):
        v = self._make_version(completed=2, failed=8, evaluations=10)
        score = score_strategy(v)
        assert score.reliability < 0.3

    def test_many_retries_lower_efficiency(self):
        v = self._make_version(completed=5, failed=0, retried=5, evaluations=5)
        score = score_strategy(v)
        assert score.efficiency < 1.0

    def test_high_complexity_steps(self):
        steps = [
            StrategyStep(description="a", estimated_complexity=StepComplexity.HIGH),
            StrategyStep(description="b", estimated_complexity=StepComplexity.HIGH),
            StrategyStep(description="c", estimated_complexity=StepComplexity.HIGH),
        ]
        v = self._make_version(steps=steps)
        score = score_strategy(v)
        assert score.complexity < 0.5

    def test_low_complexity_steps(self):
        steps = [
            StrategyStep(description="a", estimated_complexity=StepComplexity.LOW),
        ]
        v = self._make_version(steps=steps)
        score = score_strategy(v)
        assert score.complexity > 0.8

    def test_many_steps_penalty(self):
        steps = [StrategyStep(description=f"s{i}") for i in range(8)]
        v = self._make_version(steps=steps)
        score = score_strategy(v)
        assert score.complexity < 0.5

    def test_scores_in_range(self):
        v = self._make_version(completed=3, failed=2, retried=1, evaluations=5)
        score = score_strategy(v)
        assert 0.0 <= score.efficiency <= 1.0
        assert 0.0 <= score.reliability <= 1.0
        assert 0.0 <= score.complexity <= 1.0
        assert 0.0 <= score.overall <= 1.0

    def test_overall_is_weighted(self):
        v = self._make_version(completed=5, failed=0, evaluations=5)
        score = score_strategy(v)
        expected = score.efficiency * 0.4 + score.reliability * 0.4 + score.complexity * 0.2
        assert abs(score.overall - expected) < 0.001


class TestCompareVersions:
    def test_compare_better(self):
        s = Strategy(goal_id="g1", objective="test", steps=[StrategyStep(description="a")])
        v1 = StrategyVersion(
            strategy=s,
            performance=PerformanceMetrics(tasks_completed=3, tasks_failed=3, evaluations=6),
        )
        v2 = StrategyVersion(
            strategy=s,
            performance=PerformanceMetrics(tasks_completed=9, tasks_failed=1, evaluations=10),
        )
        result = compare_versions(v1, v2)
        assert "better" in result
        assert result["better"] == v2.version_id
        assert "improvement" in result

    def test_compare_same(self):
        s = Strategy(goal_id="g1", objective="test", steps=[StrategyStep(description="a")])
        perf = PerformanceMetrics(tasks_completed=5, tasks_failed=0, evaluations=5)
        v1 = StrategyVersion(strategy=s, performance=perf)
        v2 = StrategyVersion(strategy=s, performance=perf)
        result = compare_versions(v1, v2)
        assert "better" in result
