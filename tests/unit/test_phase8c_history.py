"""Phase 8C — Strategy history and versioning tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from umh.strategy.history import (
    PerformanceMetrics,
    StrategyHistory,
    StrategyVersion,
    get_strategy_history,
    record_strategy_version,
    record_task_outcome,
    reset_strategy_history,
)
from umh.strategy.models import Strategy, StrategyStep, StepStatus


class TestPerformanceMetrics:
    def test_defaults(self):
        m = PerformanceMetrics()
        assert m.tasks_completed == 0
        assert m.tasks_failed == 0
        assert m.success_rate == 0.0
        assert m.avg_duration_sec == 0.0

    def test_success_rate(self):
        m = PerformanceMetrics(tasks_completed=7, tasks_failed=3)
        assert abs(m.success_rate - 0.7) < 0.01

    def test_success_rate_zero(self):
        m = PerformanceMetrics()
        assert m.success_rate == 0.0

    def test_avg_duration(self):
        m = PerformanceMetrics(tasks_completed=4, total_duration_sec=100.0)
        assert m.avg_duration_sec == 25.0

    def test_avg_duration_zero(self):
        m = PerformanceMetrics()
        assert m.avg_duration_sec == 0.0

    def test_to_dict(self):
        m = PerformanceMetrics(tasks_completed=5, tasks_failed=1)
        d = m.to_dict()
        assert "success_rate" in d
        assert "avg_duration_sec" in d
        assert d["tasks_completed"] == 5


class TestStrategyVersion:
    def test_auto_ids(self):
        s = Strategy(goal_id="g1", objective="test")
        v = StrategyVersion(strategy=s)
        assert v.version_id.startswith("sv_")
        assert v.created_at != ""
        assert v.is_active is True

    def test_to_dict(self):
        s = Strategy(goal_id="g1", objective="test")
        v = StrategyVersion(strategy=s, version=2)
        d = v.to_dict()
        assert d["version"] == 2
        assert "performance" in d
        assert "strategy" in d


class TestStrategyHistory:
    def test_add_version(self):
        h = StrategyHistory(goal_id="g1")
        s1 = Strategy(goal_id="g1", objective="v1")
        v1 = h.add_version(s1)
        assert v1.version == 1
        assert v1.is_active is True
        assert h.version_count() == 1

    def test_add_deactivates_previous(self):
        h = StrategyHistory(goal_id="g1")
        s1 = Strategy(goal_id="g1", objective="v1")
        s2 = Strategy(goal_id="g1", objective="v2")
        v1 = h.add_version(s1)
        v2 = h.add_version(s2)
        assert v1.is_active is False
        assert v2.is_active is True

    def test_active_version(self):
        h = StrategyHistory(goal_id="g1")
        assert h.active_version() is None
        s = Strategy(goal_id="g1", objective="test")
        h.add_version(s)
        assert h.active_version() is not None

    def test_get_version(self):
        h = StrategyHistory(goal_id="g1")
        s = Strategy(goal_id="g1", objective="test")
        v = h.add_version(s)
        found = h.get_version(v.version_id)
        assert found is not None
        assert found.version_id == v.version_id

    def test_get_version_not_found(self):
        h = StrategyHistory(goal_id="g1")
        assert h.get_version("nonexistent") is None

    def test_latest_version(self):
        h = StrategyHistory(goal_id="g1")
        assert h.latest_version() is None
        s1 = Strategy(goal_id="g1", objective="v1")
        s2 = Strategy(goal_id="g1", objective="v2")
        h.add_version(s1)
        h.add_version(s2)
        latest = h.latest_version()
        assert latest.version == 2

    def test_to_dict(self):
        h = StrategyHistory(goal_id="g1")
        s = Strategy(goal_id="g1", objective="test")
        h.add_version(s)
        d = h.to_dict()
        assert d["goal_id"] == "g1"
        assert d["version_count"] == 1
        assert len(d["versions"]) == 1


class TestHistoryStore:
    def setup_method(self):
        reset_strategy_history()

    def test_get_creates_new(self):
        h = get_strategy_history("g1")
        assert h.goal_id == "g1"
        assert h.version_count() == 0

    def test_record_version(self):
        s = Strategy(goal_id="g1", objective="test")
        v = record_strategy_version("g1", s)
        assert v.version == 1
        h = get_strategy_history("g1")
        assert h.version_count() == 1

    def test_record_task_outcome_completed(self):
        s = Strategy(goal_id="g1", objective="test")
        record_strategy_version("g1", s)
        record_task_outcome("g1", completed=True, duration_sec=10.0)
        h = get_strategy_history("g1")
        active = h.active_version()
        assert active.performance.tasks_completed == 1
        assert active.performance.total_duration_sec == 10.0

    def test_record_task_outcome_failed(self):
        s = Strategy(goal_id="g1", objective="test")
        record_strategy_version("g1", s)
        record_task_outcome("g1", failed=True)
        h = get_strategy_history("g1")
        active = h.active_version()
        assert active.performance.tasks_failed == 1

    def test_record_task_outcome_retried(self):
        s = Strategy(goal_id="g1", objective="test")
        record_strategy_version("g1", s)
        record_task_outcome("g1", retried=True)
        h = get_strategy_history("g1")
        active = h.active_version()
        assert active.performance.tasks_retried == 1

    def test_record_no_active_version(self):
        record_task_outcome("nonexistent", completed=True)

    def test_reset(self):
        s = Strategy(goal_id="g1", objective="test")
        record_strategy_version("g1", s)
        reset_strategy_history()
        h = get_strategy_history("g1")
        assert h.version_count() == 0
