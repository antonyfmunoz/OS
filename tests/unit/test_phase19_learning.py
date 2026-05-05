"""Phase 19 tests — Adaptive Scheduling + Feedback Learning.

Tests cover: execution feedback, metrics aggregation, adaptive weights,
feedback loop integration, determinism, planner adaptation, boundary
invariants, and regression against prior phases.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from umh.jobs.lifecycle import transition
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.priority import NodeCapability, score_job
from umh.jobs.store import JobStore
from umh.learning.feedback import ExecutionFeedback, FeedbackStore
from umh.learning.metrics import (
    JobTypeMetrics,
    MetricsAggregator,
    NodeMetrics,
    compute_job_type_metrics,
    compute_node_metrics,
)
from umh.learning.weights import SchedulerWeights, WeightAdapter
from umh.runtime.planner import SchedulingPlanner, adaptive_score, make_ranker

_REF_TIME = datetime(2026, 1, 1, 0, 10, 0, tzinfo=timezone.utc)


def _make_feedback(
    job_id: str = "j1",
    node_id: str = "n1",
    task_type: str = "default",
    success: bool = True,
    duration_ms: int = 1000,
    retries: int = 0,
) -> ExecutionFeedback:
    return ExecutionFeedback(
        job_id=job_id,
        node_id=node_id,
        task_type=task_type,
        success=success,
        duration_ms=duration_ms,
        retries=retries,
        timestamp="2026-01-01T00:05:00+00:00",
    )


def _make_job(
    job_id: str = "j1",
    priority: str = "normal",
    created_at: str = "2026-01-01T00:00:00+00:00",
) -> ExecutionJob:
    return ExecutionJob(
        job_id=job_id,
        task_id="t1",
        node_id="",
        status=JobStatus.SUBMITTED,
        created_at=created_at,
        submitted_at=created_at,
        attempts=1,
        metadata={"priority": priority},
    )


def _make_node(
    node_id: str = "n1",
    cpu_cores: float = 4.0,
    current_load: float = 0.2,
) -> NodeCapability:
    return NodeCapability(node_id=node_id, cpu_cores=cpu_cores, current_load=current_load)


# ─── Feedback tests ─────────────────────────────────────────────────


class TestExecutionFeedback:
    def test_feedback_creation(self):
        fb = _make_feedback()
        assert fb.job_id == "j1"
        assert fb.node_id == "n1"
        assert fb.success is True
        assert fb.duration_ms == 1000

    def test_feedback_immutable(self):
        fb = _make_feedback()
        with pytest.raises(AttributeError):
            fb.success = False

    def test_feedback_to_dict(self):
        fb = _make_feedback()
        d = fb.to_dict()
        assert d["job_id"] == "j1"
        assert d["success"] is True

    def test_feedback_store_record(self):
        store = FeedbackStore()
        store.record(_make_feedback())
        assert store.total == 1

    def test_feedback_store_by_node(self):
        store = FeedbackStore()
        store.record(_make_feedback(node_id="n1"))
        store.record(_make_feedback(node_id="n2"))
        assert len(store.get_for_node("n1")) == 1
        assert len(store.get_for_node("n2")) == 1

    def test_feedback_store_by_task_type(self):
        store = FeedbackStore()
        store.record(_make_feedback(task_type="deploy"))
        store.record(_make_feedback(task_type="build"))
        assert len(store.get_for_task_type("deploy")) == 1
        assert len(store.get_for_task_type("build")) == 1

    def test_feedback_store_eviction(self):
        store = FeedbackStore(max_records=3)
        for i in range(5):
            store.record(_make_feedback(job_id=f"j{i}"))
        assert store.total == 3

    def test_feedback_store_clear(self):
        store = FeedbackStore()
        store.record(_make_feedback())
        store.clear()
        assert store.total == 0


# ─── Metrics tests ──────────────────────────────────────────────────


class TestMetrics:
    def test_node_metrics_computed(self):
        records = [
            _make_feedback(success=True, duration_ms=100),
            _make_feedback(success=True, duration_ms=200),
            _make_feedback(success=False, duration_ms=300),
        ]
        metrics = compute_node_metrics(records)
        assert metrics is not None
        assert metrics.total_jobs == 3
        assert metrics.successful_jobs == 2
        assert metrics.failed_jobs == 1
        assert metrics.avg_duration_ms == 200.0
        assert abs(metrics.success_rate - 2 / 3) < 0.01

    def test_node_metrics_empty(self):
        assert compute_node_metrics([]) is None

    def test_job_type_metrics_computed(self):
        records = [
            _make_feedback(task_type="build", success=True, duration_ms=500),
            _make_feedback(task_type="build", success=False, duration_ms=1000),
        ]
        metrics = compute_job_type_metrics(records)
        assert metrics is not None
        assert metrics.task_type == "build"
        assert metrics.total_jobs == 2
        assert metrics.failure_rate == 0.5

    def test_aggregator_node_metrics(self):
        store = FeedbackStore()
        store.record(_make_feedback(node_id="n1", success=True))
        store.record(_make_feedback(node_id="n1", success=True))
        store.record(_make_feedback(node_id="n2", success=False))

        agg = MetricsAggregator()
        node_m = agg.node_metrics(store)
        assert "n1" in node_m
        assert "n2" in node_m
        assert node_m["n1"].success_rate == 1.0
        assert node_m["n2"].success_rate == 0.0

    def test_aggregator_success_rate_default(self):
        store = FeedbackStore()
        agg = MetricsAggregator()
        assert agg.node_success_rate(store, "unknown") == 0.5

    def test_retry_rate(self):
        records = [
            _make_feedback(retries=0),
            _make_feedback(retries=2),
            _make_feedback(retries=1),
        ]
        metrics = compute_node_metrics(records)
        assert metrics is not None
        assert abs(metrics.retry_rate - 2 / 3) < 0.01
        assert abs(metrics.avg_retries - 1.0) < 0.01


# ─── Weights tests ──────────────────────────────────────────────────


class TestSchedulerWeights:
    def test_default_weights(self):
        w = SchedulerWeights()
        assert w.priority_weight == 1.0
        assert w.success_bias == 10.0

    def test_reset_weights(self):
        w = SchedulerWeights()
        w.priority_weight = 5.0
        w.node_penalties["n1"] = 10.0
        w.reset()
        assert w.priority_weight == 1.0
        assert len(w.node_penalties) == 0

    def test_node_adjustment(self):
        w = SchedulerWeights()
        w.node_bonuses["n1"] = 10.0
        w.node_penalties["n1"] = 3.0
        assert w.get_node_adjustment("n1") == 7.0

    def test_node_adjustment_unknown(self):
        w = SchedulerWeights()
        assert w.get_node_adjustment("unknown") == 0.0

    def test_weights_to_dict(self):
        w = SchedulerWeights()
        d = w.to_dict()
        assert "priority_weight" in d
        assert "node_penalties" in d

    def test_weight_adapter_boosts_good_node(self):
        store = FeedbackStore()
        for i in range(5):
            store.record(_make_feedback(node_id="fast", success=True, duration_ms=200))

        adapter = WeightAdapter()
        w = adapter.compute_fresh(store)
        assert w.node_bonuses.get("fast", 0) > 0

    def test_weight_adapter_penalizes_bad_node(self):
        store = FeedbackStore()
        for i in range(5):
            store.record(_make_feedback(node_id="flaky", success=False, duration_ms=6000))

        adapter = WeightAdapter()
        w = adapter.compute_fresh(store)
        assert w.node_penalties.get("flaky", 0) > 0

    def test_weight_adapter_deterministic(self):
        store = FeedbackStore()
        for i in range(5):
            store.record(_make_feedback(node_id="n1", success=True, duration_ms=300))
            store.record(_make_feedback(node_id="n2", success=False, duration_ms=4000))

        adapter = WeightAdapter()
        w1 = adapter.compute_fresh(store)
        w2 = adapter.compute_fresh(store)
        assert w1.to_dict() == w2.to_dict()

    def test_weight_adapter_min_samples(self):
        store = FeedbackStore()
        store.record(_make_feedback(node_id="n1", success=False))
        store.record(_make_feedback(node_id="n1", success=False))

        adapter = WeightAdapter()
        w = adapter.compute_fresh(store)
        assert w.node_penalties.get("n1", 0) == 0

    def test_weight_adapter_penalty_cap(self):
        store = FeedbackStore()
        for i in range(100):
            store.record(_make_feedback(node_id="bad", success=False, duration_ms=10000))

        adapter = WeightAdapter()
        w = SchedulerWeights()
        for _ in range(20):
            adapter.adapt(store, w)
        assert w.node_penalties.get("bad", 0) <= 50.0


# ─── Adaptive scoring tests ─────────────────────────────────────────


class TestAdaptiveScoring:
    def test_adaptive_score_without_weights(self):
        job = _make_job()
        base = score_job(job, now=_REF_TIME)
        adapted = adaptive_score(job, now=_REF_TIME)
        assert adapted.score == base.score

    def test_adaptive_score_with_node_bonus(self):
        job = _make_job()
        node = _make_node(node_id="fast")
        w = SchedulerWeights()
        w.node_bonuses["fast"] = 20.0

        base = score_job(job, node, now=_REF_TIME)
        adapted = adaptive_score(job, node, weights=w, now=_REF_TIME)
        assert adapted.score > base.score

    def test_adaptive_score_with_node_penalty(self):
        job = _make_job()
        node = _make_node(node_id="slow")
        w = SchedulerWeights()
        w.node_penalties["slow"] = 15.0

        base = score_job(job, node, now=_REF_TIME)
        adapted = adaptive_score(job, node, weights=w, now=_REF_TIME)
        assert adapted.score < base.score

    def test_adaptive_score_deterministic(self):
        job = _make_job()
        node = _make_node()
        w = SchedulerWeights()
        w.node_bonuses["n1"] = 5.0

        s1 = adaptive_score(job, node, weights=w, now=_REF_TIME)
        s2 = adaptive_score(job, node, weights=w, now=_REF_TIME)
        assert s1.score == s2.score


# ─── Planner integration tests ──────────────────────────────────────


class TestPlannerIntegration:
    def test_planner_with_weights_prefers_good_node(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="", metadata={"priority": "normal"})
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        w = SchedulerWeights()
        w.node_bonuses["fast"] = 20.0
        w.node_penalties["slow"] = 15.0

        fast = _make_node(node_id="fast")
        slow = _make_node(node_id="slow")

        planner = SchedulingPlanner()
        result = planner.plan_next(store, [fast, slow], weights=w, now=_REF_TIME)
        assert result is not None
        assert result[1] == "fast"

    def test_planner_without_weights_backward_compat(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="", metadata={"priority": "normal"})
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        planner = SchedulingPlanner()
        result = planner.plan_next(store, now=_REF_TIME)
        assert result is not None

    def test_score_candidates_with_weights(self):
        jobs = [_make_job(job_id="j1"), _make_job(job_id="j2")]
        nodes = [_make_node(node_id="n1")]
        w = SchedulerWeights()
        w.node_bonuses["n1"] = 10.0

        planner = SchedulingPlanner()
        scores = planner.score_candidates(jobs, nodes, weights=w, now=_REF_TIME)
        assert len(scores) == 2
        assert all(s["score"] > 0 for s in scores)


# ─── Feedback loop integration ──────────────────────────────────────


class TestFeedbackLoop:
    def test_full_feedback_loop(self):
        """End-to-end: record feedback → compute metrics → adapt weights → score changes."""
        fb_store = FeedbackStore()
        for i in range(5):
            fb_store.record(_make_feedback(node_id="reliable", success=True, duration_ms=200))
            fb_store.record(_make_feedback(node_id="unreliable", success=False, duration_ms=8000))

        adapter = WeightAdapter()
        weights = adapter.compute_fresh(fb_store)

        assert weights.node_bonuses.get("reliable", 0) > 0
        assert weights.node_penalties.get("unreliable", 0) > 0

        job = _make_job()
        reliable = _make_node(node_id="reliable")
        unreliable = _make_node(node_id="unreliable")

        s_reliable = adaptive_score(job, reliable, weights=weights, now=_REF_TIME)
        s_unreliable = adaptive_score(job, unreliable, weights=weights, now=_REF_TIME)
        assert s_reliable.score > s_unreliable.score

    def test_faster_node_preferred_after_learning(self):
        fb_store = FeedbackStore()
        for i in range(5):
            fb_store.record(_make_feedback(node_id="fast", success=True, duration_ms=100))
            fb_store.record(_make_feedback(node_id="slow", success=True, duration_ms=8000))

        adapter = WeightAdapter()
        weights = adapter.compute_fresh(fb_store)

        job = _make_job()
        fast = _make_node(node_id="fast")
        slow = _make_node(node_id="slow")

        s_fast = adaptive_score(job, fast, weights=weights, now=_REF_TIME)
        s_slow = adaptive_score(job, slow, weights=weights, now=_REF_TIME)
        assert s_fast.score > s_slow.score

    def test_failing_node_deprioritized(self):
        fb_store = FeedbackStore()
        for i in range(5):
            fb_store.record(_make_feedback(node_id="good", success=True))
            fb_store.record(_make_feedback(node_id="bad", success=False))

        adapter = WeightAdapter()
        weights = adapter.compute_fresh(fb_store)

        job = _make_job()
        good = _make_node(node_id="good")
        bad = _make_node(node_id="bad")

        s_good = adaptive_score(job, good, weights=weights, now=_REF_TIME)
        s_bad = adaptive_score(job, bad, weights=weights, now=_REF_TIME)
        assert s_good.score > s_bad.score

    def test_feedback_does_not_mutate_past_jobs(self):
        job = _make_job()
        original_status = job.status
        original_meta = dict(job.metadata)

        fb_store = FeedbackStore()
        fb_store.record(_make_feedback())
        adapter = WeightAdapter()
        weights = adapter.compute_fresh(fb_store)
        adaptive_score(job, weights=weights, now=_REF_TIME)

        assert job.status == original_status
        assert job.metadata == original_meta

    def test_learning_is_reversible(self):
        fb_store = FeedbackStore()
        for i in range(5):
            fb_store.record(_make_feedback(node_id="n1", success=False))

        adapter = WeightAdapter()
        weights = adapter.compute_fresh(fb_store)
        assert weights.node_penalties.get("n1", 0) > 0

        weights.reset()
        assert weights.node_penalties.get("n1", 0) == 0
        assert weights.priority_weight == 1.0


# ─── Determinism tests ──────────────────────────────────────────────


class TestDeterminism:
    def test_same_feedback_same_weights(self):
        fb_store = FeedbackStore()
        for i in range(5):
            fb_store.record(_make_feedback(node_id="n1", success=True, duration_ms=300))

        adapter = WeightAdapter()
        w1 = adapter.compute_fresh(fb_store)
        w2 = adapter.compute_fresh(fb_store)
        assert w1.to_dict() == w2.to_dict()

    def test_same_weights_same_score(self):
        job = _make_job()
        node = _make_node()
        w = SchedulerWeights()
        w.node_bonuses["n1"] = 5.0

        s1 = adaptive_score(job, node, weights=w, now=_REF_TIME)
        s2 = adaptive_score(job, node, weights=w, now=_REF_TIME)
        assert s1.score == s2.score

    def test_ranker_with_weights_deterministic(self):
        jobs = [
            _make_job(job_id="j1", priority="low"),
            _make_job(job_id="j2", priority="high"),
        ]
        node = _make_node()
        w = SchedulerWeights()
        w.node_bonuses["n1"] = 5.0

        r1 = make_ranker(node, now=_REF_TIME, weights=w)
        r2 = make_ranker(node, now=_REF_TIME, weights=w)
        assert [j.job_id for j in r1(jobs)] == [j.job_id for j in r2(jobs)]


# ─── Boundary invariant tests ───────────────────────────────────────


class TestBoundaryInvariants:
    def test_feedback_does_not_import_cells(self):
        mod = importlib.import_module("umh.learning.feedback")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_metrics_does_not_import_cells(self):
        mod = importlib.import_module("umh.learning.metrics")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_weights_does_not_import_cells(self):
        mod = importlib.import_module("umh.learning.weights")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_no_environments_in_learning(self):
        for modname in [
            "umh.learning.feedback",
            "umh.learning.metrics",
            "umh.learning.weights",
        ]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            assert "from umh.environments" not in src

    def test_no_subprocess_in_learning(self):
        for modname in [
            "umh.learning.feedback",
            "umh.learning.metrics",
            "umh.learning.weights",
        ]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            assert "import subprocess" not in src

    def test_no_shell_true_in_learning(self):
        for modname in [
            "umh.learning.feedback",
            "umh.learning.metrics",
            "umh.learning.weights",
        ]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword):
                    if node.arg == "shell" and isinstance(node.value, ast.Constant):
                        assert node.value.value is not True, f"shell=True in {modname}"

    def test_feedback_recorded_after_completion(self):
        """Feedback requires a completed job's data — can't be created mid-execution."""
        fb = _make_feedback(success=True, duration_ms=500)
        assert fb.duration_ms > 0
        assert fb.timestamp != ""

    def test_scheduler_remains_pure_with_weights(self):
        """Adaptive scoring does not mutate weights."""
        w = SchedulerWeights()
        w.node_bonuses["n1"] = 5.0
        original = w.to_dict()

        job = _make_job()
        node = _make_node()
        adaptive_score(job, node, weights=w, now=_REF_TIME)

        assert w.to_dict() == original


# ─── Regression tests ───────────────────────────────────────────────


class TestRegression:
    def test_make_ranker_without_weights(self):
        jobs = [_make_job(job_id="j1", priority="high"), _make_job(job_id="j2", priority="low")]
        ranker = make_ranker(now=_REF_TIME)
        ranked = ranker(jobs)
        assert ranked[0].job_id == "j1"

    def test_planner_plan_next_without_weights(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="", metadata={"priority": "normal"})
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        planner = SchedulingPlanner()
        result = planner.plan_next(store, now=_REF_TIME)
        assert result is not None

    def test_claim_job_without_ranker(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="")
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)
        claimed = store.claim_job("w1")
        assert claimed is not None

    def test_base_score_job_unchanged(self):
        job = _make_job(priority="high")
        scored = score_job(job, now=_REF_TIME)
        assert scored.priority_weight == 100.0
