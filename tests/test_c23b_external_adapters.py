"""Tests for Campaign 23B external benchmark adapters."""

from __future__ import annotations

import sys
sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.benchmarks.external_adapters import (
    ADAPTER_REGISTRY,
    BenchmarkTask,
    BrowseCompAdapter,
    ExternalBenchmarkResult,
    GAIAAdapter,
    SWEBenchAdapter,
    TaskResult,
    TerminalBenchAdapter,
    WebArenaAdapter,
    get_adapter,
)


class TestBenchmarkTask:
    def test_to_dict(self):
        t = BenchmarkTask(task_id="t1", benchmark_name="swe_bench")
        d = t.to_dict()
        assert d["task_id"] == "t1"
        assert isinstance(d["metadata"], dict)

    def test_defaults(self):
        t = BenchmarkTask()
        assert t.task_id == ""
        assert t.metadata == {}


class TestTaskResult:
    def test_to_dict(self):
        r = TaskResult(task_id="t1", success=True, partial_score=0.9)
        d = r.to_dict()
        assert d["success"] is True
        assert d["partial_score"] == 0.9

    def test_defaults(self):
        r = TaskResult()
        assert r.success is False
        assert r.cost_usd == 0.0


class TestExternalBenchmarkResult:
    def test_to_dict(self):
        r = ExternalBenchmarkResult(benchmark_name="x", tasks_attempted=5, tasks_resolved=3)
        d = r.to_dict()
        assert d["tasks_attempted"] == 5
        assert isinstance(d["results"], list)

    def test_empty(self):
        r = ExternalBenchmarkResult()
        assert r.benchmark_name == ""
        assert r.resolution_rate == 0.0


class TestSWEBenchAdapter:
    def test_loads_5_tasks(self):
        a = SWEBenchAdapter(test_mode=True)
        tasks = a.load_tasks()
        assert len(tasks) == 5
        for t in tasks:
            assert t.benchmark_name == "swe_bench"

    def test_task_ids_unique(self):
        a = SWEBenchAdapter(test_mode=True)
        ids = [t.task_id for t in a.load_tasks()]
        assert len(set(ids)) == 5

    def test_run_task(self):
        a = SWEBenchAdapter(test_mode=True)
        tasks = a.load_tasks()
        r = a.run_task(tasks[0])
        assert isinstance(r, TaskResult)
        assert r.benchmark_name == "swe_bench"

    def test_score_results(self):
        a = SWEBenchAdapter(test_mode=True)
        tasks = a.load_tasks()
        results = [a.run_task(t) for t in tasks]
        score = a.score_results(results)
        assert score.tasks_attempted == 5
        assert score.tasks_resolved == 3
        assert abs(score.resolution_rate - 0.6) < 0.001

    def test_run_all(self):
        a = SWEBenchAdapter(test_mode=True)
        result = a.run_all()
        assert result.tasks_attempted == 5
        assert result.avg_duration > 0
        assert result.avg_cost > 0

    def test_score_empty(self):
        a = SWEBenchAdapter(test_mode=True)
        result = a.score_results([])
        assert result.tasks_attempted == 0
        assert result.resolution_rate == 0.0

    def test_unknown_task(self):
        a = SWEBenchAdapter(test_mode=True)
        t = BenchmarkTask(task_id="nonexist", benchmark_name="swe_bench")
        r = a.run_task(t)
        assert r.success is False
        assert r.partial_score == 0.0


class TestTerminalBenchAdapter:
    def test_loads_5_tasks(self):
        a = TerminalBenchAdapter(test_mode=True)
        assert len(a.load_tasks()) == 5

    def test_run_all(self):
        a = TerminalBenchAdapter(test_mode=True)
        result = a.run_all()
        assert result.tasks_attempted == 5
        assert result.tasks_resolved == 4

    def test_benchmark_name(self):
        a = TerminalBenchAdapter()
        assert a.benchmark_name == "terminal_bench"


class TestWebArenaAdapter:
    def test_loads_5_tasks(self):
        a = WebArenaAdapter(test_mode=True)
        assert len(a.load_tasks()) == 5

    def test_run_all(self):
        a = WebArenaAdapter(test_mode=True)
        result = a.run_all()
        assert result.tasks_attempted == 5
        assert result.tasks_resolved == 3

    def test_benchmark_name(self):
        a = WebArenaAdapter()
        assert a.benchmark_name == "webarena"


class TestGAIAAdapter:
    def test_loads_5_tasks(self):
        a = GAIAAdapter(test_mode=True)
        assert len(a.load_tasks()) == 5

    def test_run_all(self):
        a = GAIAAdapter(test_mode=True)
        result = a.run_all()
        assert result.tasks_attempted == 5
        assert result.tasks_resolved == 3

    def test_benchmark_name(self):
        a = GAIAAdapter()
        assert a.benchmark_name == "gaia"


class TestBrowseCompAdapter:
    def test_loads_5_tasks(self):
        a = BrowseCompAdapter(test_mode=True)
        assert len(a.load_tasks()) == 5

    def test_run_all(self):
        a = BrowseCompAdapter(test_mode=True)
        result = a.run_all()
        assert result.tasks_attempted == 5
        assert result.tasks_resolved == 3

    def test_benchmark_name(self):
        a = BrowseCompAdapter()
        assert a.benchmark_name == "browsecomp"


class TestAdapterRegistry:
    def test_five_adapters(self):
        assert len(ADAPTER_REGISTRY) == 5

    def test_get_adapter(self):
        a = get_adapter("swe_bench")
        assert a is not None
        assert isinstance(a, SWEBenchAdapter)

    def test_get_adapter_unknown(self):
        assert get_adapter("nonexist") is None

    def test_get_adapter_test_mode_default(self):
        a = get_adapter("terminal_bench")
        assert a is not None
        assert a._test_mode is True

    def test_all_adapters_run(self):
        for name in ADAPTER_REGISTRY:
            a = get_adapter(name, test_mode=True)
            result = a.run_all()
            assert result.tasks_attempted == 5
            assert result.benchmark_name == name


class TestScoringMath:
    def test_partial_score_avg(self):
        a = SWEBenchAdapter(test_mode=True)
        result = a.run_all()
        assert 0.0 < result.partial_score_avg < 1.0

    def test_avg_tokens_positive(self):
        a = SWEBenchAdapter(test_mode=True)
        result = a.run_all()
        assert result.avg_tokens > 0

    def test_resolution_rate_matches(self):
        a = SWEBenchAdapter(test_mode=True)
        result = a.run_all()
        expected = result.tasks_resolved / result.tasks_attempted
        assert abs(result.resolution_rate - expected) < 0.001

    def test_result_to_dict_serializable(self):
        import json
        a = SWEBenchAdapter(test_mode=True)
        result = a.run_all()
        s = json.dumps(result.to_dict())
        assert isinstance(s, str)
