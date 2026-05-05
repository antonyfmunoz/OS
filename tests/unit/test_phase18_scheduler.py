"""Phase 18 tests — Intelligent Scheduling + Priority + Resource-Aware Execution.

Tests cover: priority model, scoring, fairness/anti-starvation, deadline
handling, cost-aware routing, determinism, planner integration, worker
integration, scheduler extension, boundary invariants, and regression.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from umh.jobs.lifecycle import transition
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.priority import (
    JobPriority,
    NodeCapability,
    ScoredJob,
    get_deadline,
    get_estimated_cost,
    get_priority,
    rank_jobs,
    score_job,
    select_best_job,
)
from umh.jobs.store import JobStore
from umh.runtime.planner import SchedulingPlanner, make_ranker


def _make_job(
    job_id: str = "j1",
    task_id: str = "t1",
    priority: str = "normal",
    created_at: str = "2026-01-01T00:00:00+00:00",
    deadline: str | None = None,
    estimated_cost: float = 0.0,
    status: JobStatus = JobStatus.SUBMITTED,
    attempts: int = 1,
) -> ExecutionJob:
    meta: dict = {"priority": priority}
    if deadline is not None:
        meta["deadline"] = deadline
    if estimated_cost:
        meta["estimated_cost"] = estimated_cost

    job = ExecutionJob(
        job_id=job_id,
        task_id=task_id,
        node_id="",
        status=status,
        created_at=created_at,
        submitted_at=created_at,
        attempts=attempts,
        metadata=meta,
    )
    return job


def _make_node(
    node_id: str = "n1",
    cpu_cores: float = 4.0,
    memory_mb: int = 8192,
    current_load: float = 0.2,
    gpu: bool = False,
) -> NodeCapability:
    return NodeCapability(
        node_id=node_id,
        cpu_cores=cpu_cores,
        memory_mb=memory_mb,
        current_load=current_load,
        gpu=gpu,
    )


_REF_TIME = datetime(2026, 1, 1, 0, 10, 0, tzinfo=timezone.utc)


# ─── Priority model tests ───────────────────────────────────────────


class TestPriorityModel:
    def test_all_priority_levels_exist(self):
        assert len(JobPriority) == 5
        levels = {p.value for p in JobPriority}
        assert levels == {"critical", "high", "normal", "low", "background"}

    def test_get_priority_from_metadata(self):
        job = _make_job(priority="high")
        assert get_priority(job) == JobPriority.HIGH

    def test_get_priority_default_normal(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="")
        assert get_priority(job) == JobPriority.NORMAL

    def test_get_priority_invalid_defaults_normal(self):
        job = _make_job(priority="invalid_value")
        assert get_priority(job) == JobPriority.NORMAL

    def test_get_deadline(self):
        job = _make_job(deadline="2026-01-01T01:00:00+00:00")
        dl = get_deadline(job)
        assert dl is not None
        assert dl.year == 2026

    def test_get_deadline_none(self):
        job = _make_job()
        assert get_deadline(job) is None

    def test_get_estimated_cost(self):
        job = _make_job(estimated_cost=7.5)
        assert get_estimated_cost(job) == 7.5

    def test_get_estimated_cost_default(self):
        job = _make_job()
        assert get_estimated_cost(job) == 0.0


# ─── Scoring tests ──────────────────────────────────────────────────


class TestScoring:
    def test_critical_scores_higher_than_high(self):
        j_crit = _make_job(job_id="jc", priority="critical")
        j_high = _make_job(job_id="jh", priority="high")
        s_crit = score_job(j_crit, now=_REF_TIME)
        s_high = score_job(j_high, now=_REF_TIME)
        assert s_crit.score > s_high.score

    def test_high_scores_higher_than_normal(self):
        j_high = _make_job(job_id="jh", priority="high")
        j_norm = _make_job(job_id="jn", priority="normal")
        s_high = score_job(j_high, now=_REF_TIME)
        s_norm = score_job(j_norm, now=_REF_TIME)
        assert s_high.score > s_norm.score

    def test_normal_scores_higher_than_low(self):
        j_norm = _make_job(job_id="jn", priority="normal")
        j_low = _make_job(job_id="jl", priority="low")
        s_norm = score_job(j_norm, now=_REF_TIME)
        s_low = score_job(j_low, now=_REF_TIME)
        assert s_norm.score > s_low.score

    def test_low_scores_higher_than_background(self):
        j_low = _make_job(job_id="jl", priority="low")
        j_bg = _make_job(job_id="jb", priority="background")
        s_low = score_job(j_low, now=_REF_TIME)
        s_bg = score_job(j_bg, now=_REF_TIME)
        assert s_low.score > s_bg.score

    def test_score_includes_priority_weight(self):
        job = _make_job(priority="critical")
        scored = score_job(job, now=_REF_TIME)
        assert scored.priority_weight == 1000.0

    def test_score_with_node(self):
        job = _make_job(priority="normal")
        node = _make_node()
        scored = score_job(job, node, now=_REF_TIME)
        assert isinstance(scored, ScoredJob)
        assert scored.score > 0

    def test_scored_job_has_breakdown(self):
        job = _make_job(priority="normal")
        scored = score_job(job, now=_REF_TIME)
        assert hasattr(scored, "priority_weight")
        assert hasattr(scored, "wait_bonus")
        assert hasattr(scored, "urgency_bonus")
        assert hasattr(scored, "node_fit")
        assert hasattr(scored, "cost_penalty")


# ─── Fairness / anti-starvation tests ───────────────────────────────


class TestFairness:
    def test_old_low_priority_eventually_beats_new_high(self):
        """An old LOW job must eventually outscore a new HIGH job."""
        old_time = "2026-01-01T00:00:00+00:00"
        new_time = "2026-01-02T00:00:00+00:00"
        future = datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc)

        j_old_low = _make_job(job_id="old", priority="low", created_at=old_time)
        j_new_high = _make_job(job_id="new", priority="high", created_at=new_time)

        s_old = score_job(j_old_low, now=future)
        s_new = score_job(j_new_high, now=future)
        assert s_old.score > s_new.score

    def test_wait_bonus_increases_with_age(self):
        t1 = "2026-01-01T00:00:00+00:00"
        ref1 = datetime(2026, 1, 1, 0, 5, 0, tzinfo=timezone.utc)
        ref2 = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

        job = _make_job(created_at=t1)
        s1 = score_job(job, now=ref1)
        s2 = score_job(job, now=ref2)
        assert s2.wait_bonus > s1.wait_bonus

    def test_background_job_scores_positive(self):
        job = _make_job(priority="background")
        scored = score_job(job, now=_REF_TIME)
        assert scored.score > 0


# ─── Deadline handling tests ────────────────────────────────────────


class TestDeadline:
    def test_near_deadline_increases_score(self):
        near = (_REF_TIME + timedelta(seconds=30)).isoformat()
        far = (_REF_TIME + timedelta(hours=2)).isoformat()

        j_near = _make_job(job_id="jn", priority="normal", deadline=near)
        j_far = _make_job(job_id="jf", priority="normal", deadline=far)

        s_near = score_job(j_near, now=_REF_TIME)
        s_far = score_job(j_far, now=_REF_TIME)
        assert s_near.urgency_bonus > s_far.urgency_bonus
        assert s_near.score > s_far.score

    def test_expired_deadline_gets_max_urgency(self):
        expired = (_REF_TIME - timedelta(minutes=5)).isoformat()
        job = _make_job(deadline=expired)
        scored = score_job(job, now=_REF_TIME)
        assert scored.urgency_bonus == 500.0

    def test_no_deadline_no_urgency(self):
        job = _make_job()
        scored = score_job(job, now=_REF_TIME)
        assert scored.urgency_bonus == 0.0

    def test_urgent_normal_preempts_non_urgent_high(self):
        near = (_REF_TIME + timedelta(seconds=10)).isoformat()
        j_urgent = _make_job(job_id="ju", priority="normal", deadline=near)
        j_high = _make_job(job_id="jh", priority="high")

        s_urgent = score_job(j_urgent, now=_REF_TIME)
        s_high = score_job(j_high, now=_REF_TIME)
        assert s_urgent.score > s_high.score


# ─── Cost-aware routing tests ───────────────────────────────────────


class TestCostAware:
    def test_heavy_job_prefers_powerful_node(self):
        job = _make_job(estimated_cost=10.0)
        strong = _make_node(node_id="strong", cpu_cores=8, current_load=0.2)
        weak = _make_node(node_id="weak", cpu_cores=1, current_load=0.2)

        s_strong = score_job(job, strong, now=_REF_TIME)
        s_weak = score_job(job, weak, now=_REF_TIME)
        assert s_strong.score > s_weak.score

    def test_heavy_job_penalized_on_weak_node(self):
        job = _make_job(estimated_cost=10.0)
        weak = _make_node(node_id="weak", cpu_cores=1)
        scored = score_job(job, weak, now=_REF_TIME)
        assert scored.cost_penalty > 0

    def test_light_job_no_penalty(self):
        job = _make_job(estimated_cost=0.5)
        node = _make_node()
        scored = score_job(job, node, now=_REF_TIME)
        assert scored.cost_penalty == 0.0


# ─── Determinism tests ──────────────────────────────────────────────


class TestDeterminism:
    def test_same_inputs_same_score(self):
        job = _make_job(priority="high")
        node = _make_node()
        s1 = score_job(job, node, now=_REF_TIME)
        s2 = score_job(job, node, now=_REF_TIME)
        assert s1.score == s2.score

    def test_same_inputs_same_ranking(self):
        jobs = [
            _make_job(job_id="j1", priority="high"),
            _make_job(job_id="j2", priority="low"),
            _make_job(job_id="j3", priority="critical"),
        ]
        r1 = rank_jobs(jobs, now=_REF_TIME)
        r2 = rank_jobs(jobs, now=_REF_TIME)
        assert [s.job.job_id for s in r1] == [s.job.job_id for s in r2]

    def test_deterministic_tiebreak_by_job_id(self):
        j1 = _make_job(job_id="aaa", priority="normal")
        j2 = _make_job(job_id="zzz", priority="normal")
        ranked = rank_jobs([j1, j2], now=_REF_TIME)
        assert ranked[0].job.job_id == "aaa"

    def test_select_best_job_deterministic(self):
        jobs = [
            _make_job(job_id="j1", priority="high"),
            _make_job(job_id="j2", priority="critical"),
        ]
        nodes = [_make_node(node_id="n1"), _make_node(node_id="n2")]
        r1 = select_best_job(jobs, nodes, now=_REF_TIME)
        r2 = select_best_job(jobs, nodes, now=_REF_TIME)
        assert r1 is not None and r2 is not None
        assert r1[0].job_id == r2[0].job_id
        assert r1[1] == r2[1]


# ─── Ranking tests ──────────────────────────────────────────────────


class TestRanking:
    def test_rank_jobs_orders_by_score(self):
        jobs = [
            _make_job(job_id="jl", priority="low"),
            _make_job(job_id="jh", priority="high"),
            _make_job(job_id="jc", priority="critical"),
        ]
        ranked = rank_jobs(jobs, now=_REF_TIME)
        assert ranked[0].job.job_id == "jc"
        assert ranked[1].job.job_id == "jh"
        assert ranked[2].job.job_id == "jl"

    def test_select_best_job_returns_highest(self):
        jobs = [
            _make_job(job_id="jl", priority="low"),
            _make_job(job_id="jh", priority="high"),
        ]
        result = select_best_job(jobs, now=_REF_TIME)
        assert result is not None
        assert result[0].job_id == "jh"

    def test_select_best_job_empty_returns_none(self):
        assert select_best_job([], now=_REF_TIME) is None

    def test_select_best_job_with_nodes(self):
        jobs = [_make_job(job_id="j1", priority="normal")]
        nodes = [_make_node(node_id="n1")]
        result = select_best_job(jobs, nodes, now=_REF_TIME)
        assert result is not None
        assert result[1] == "n1"


# ─── Planner tests ──────────────────────────────────────────────────


class TestPlanner:
    def test_make_ranker_orders_by_priority(self):
        jobs = [
            _make_job(job_id="jl", priority="low"),
            _make_job(job_id="jh", priority="high"),
        ]
        ranker = make_ranker(now=_REF_TIME)
        ranked = ranker(jobs)
        assert ranked[0].job_id == "jh"
        assert ranked[1].job_id == "jl"

    def test_make_ranker_with_node(self):
        node = _make_node()
        ranker = make_ranker(node, now=_REF_TIME)
        jobs = [_make_job(job_id="j1", priority="normal")]
        ranked = ranker(jobs)
        assert len(ranked) == 1

    def test_planner_plan_next(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="", metadata={"priority": "critical"})
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        planner = SchedulingPlanner()
        result = planner.plan_next(store, now=_REF_TIME)
        assert result is not None
        assert result[0].job_id == job.job_id

    def test_planner_plan_next_empty(self):
        store = JobStore()
        planner = SchedulingPlanner()
        assert planner.plan_next(store, now=_REF_TIME) is None

    def test_planner_score_candidates(self):
        jobs = [
            _make_job(job_id="j1", priority="high"),
            _make_job(job_id="j2", priority="low"),
        ]
        planner = SchedulingPlanner()
        scores = planner.score_candidates(jobs, now=_REF_TIME)
        assert len(scores) == 2
        assert scores[0]["job_id"] == "j1"
        assert scores[0]["score"] > scores[1]["score"]

    def test_planner_score_with_nodes(self):
        jobs = [_make_job(job_id="j1", priority="normal")]
        nodes = [_make_node(node_id="n1"), _make_node(node_id="n2")]
        planner = SchedulingPlanner()
        scores = planner.score_candidates(jobs, nodes, now=_REF_TIME)
        assert len(scores) == 2


# ─── Worker integration tests ───────────────────────────────────────


class TestWorkerIntegration:
    def test_worker_claims_with_ranker(self):
        from umh.nodes.worker import ExecutionResult as WER, WorkerLoop

        store = JobStore()
        j_low = store.create_job(task_id="low", node_id="", metadata={"priority": "low"})
        transition(j_low, JobStatus.SUBMITTED)
        store.update_job(j_low)

        j_high = store.create_job(task_id="high", node_id="", metadata={"priority": "high"})
        transition(j_high, JobStatus.SUBMITTED)
        store.update_job(j_high)

        ranker = make_ranker(now=_REF_TIME)
        claimed = store.claim_job("w1", ranker=ranker)
        assert claimed is not None
        assert claimed.task_id == "high"

    def test_worker_without_ranker_uses_fifo(self):
        store = JobStore()
        j1 = store.create_job(task_id="first", node_id="")
        transition(j1, JobStatus.SUBMITTED, now="2026-01-01T00:00:01+00:00")
        store.update_job(j1)

        j2 = store.create_job(task_id="second", node_id="")
        transition(j2, JobStatus.SUBMITTED, now="2026-01-01T00:00:02+00:00")
        store.update_job(j2)

        claimed = store.claim_job("w1")
        assert claimed is not None
        assert claimed.task_id == "first"

    def test_no_duplicate_with_priority(self):
        from umh.jobs.locking import JobLockManager

        lock_mgr = JobLockManager()
        store = JobStore(lock_manager=lock_mgr)

        job = store.create_job(task_id="t1", node_id="", metadata={"priority": "high"})
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        ranker = make_ranker(now=_REF_TIME)
        c1 = store.claim_job("w1", ranker=ranker)
        c2 = store.claim_job("w2", ranker=ranker)
        assert c1 is not None
        assert c2 is None


# ─── Scheduler extension tests ──────────────────────────────────────


class TestSchedulerExtension:
    def test_select_node_for_job(self):
        from umh.environments.models import Node, NodeStatus, NodeType
        from umh.environments.scheduler import select_node_for_job

        job = _make_job(priority="normal")
        nodes = [
            Node(node_id="n1", node_type=NodeType.LOCAL, cpu_cores=4, memory_mb=8192),
            Node(node_id="n2", node_type=NodeType.VPS, cpu_cores=2, memory_mb=4096),
        ]
        result = select_node_for_job(job, nodes)
        assert result is not None
        assert result.node_id in ("n1", "n2")

    def test_select_node_for_job_no_available(self):
        from umh.environments.models import Node, NodeStatus, NodeType
        from umh.environments.scheduler import select_node_for_job

        job = _make_job()
        nodes = [
            Node(node_id="n1", node_type=NodeType.LOCAL, status=NodeStatus.OFFLINE),
        ]
        result = select_node_for_job(job, nodes)
        assert result is None

    def test_original_select_node_unchanged(self):
        from umh.environments.models import (
            ExecutionTask,
            Node,
            NodeType,
            ResourceRequirements,
        )
        from umh.environments.scheduler import select_node

        task = ExecutionTask(
            task_id="t1",
            plan_objective_id="p1",
            operation="test",
            resources=ResourceRequirements(cpu_cores=1, memory_mb=256),
        )
        nodes = [
            Node(node_id="n1", node_type=NodeType.LOCAL, cpu_cores=4, memory_mb=8192),
        ]
        result = select_node(task, nodes)
        assert result is not None
        assert result.node_id == "n1"


# ─── Boundary invariant tests ───────────────────────────────────────


class TestBoundaryInvariants:
    def test_priority_does_not_import_cells(self):
        mod = importlib.import_module("umh.jobs.priority")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_planner_does_not_import_cells(self):
        mod = importlib.import_module("umh.runtime.planner")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_priority_does_not_import_environments(self):
        mod = importlib.import_module("umh.jobs.priority")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src

    def test_planner_does_not_import_environments(self):
        mod = importlib.import_module("umh.runtime.planner")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src

    def test_no_subprocess_in_new_modules(self):
        for modname in ["umh.jobs.priority", "umh.runtime.planner"]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            assert "import subprocess" not in src
            assert "from subprocess" not in src

    def test_no_shell_true_in_new_modules(self):
        for modname in ["umh.jobs.priority", "umh.runtime.planner"]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword):
                    if node.arg == "shell" and isinstance(node.value, ast.Constant):
                        assert node.value.value is not True, f"shell=True in {modname}"

    def test_scoring_is_pure(self):
        """Score function must not modify the input job."""
        job = _make_job(priority="high")
        original_meta = dict(job.metadata)
        original_status = job.status
        score_job(job, now=_REF_TIME)
        assert job.metadata == original_meta
        assert job.status == original_status

    def test_priority_does_not_bypass_lifecycle(self):
        """Priority cannot force a transition that lifecycle forbids."""
        job = _make_job(status=JobStatus.SUCCEEDED, attempts=1)
        scored = score_job(job, now=_REF_TIME)
        assert scored.score > 0
        with pytest.raises(ValueError):
            transition(job, JobStatus.RUNNING)


# ─── Regression tests ───────────────────────────────────────────────


class TestRegression:
    def test_claim_job_still_works_without_ranker(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="")
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)
        claimed = store.claim_job("w1")
        assert claimed is not None

    def test_store_mark_methods_unchanged(self):
        store = JobStore()
        job = store.create_job(task_id="t1", node_id="")
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)
        store.mark_running(job.job_id)
        stored = store.get_job(job.job_id)
        assert stored.status == JobStatus.RUNNING

    def test_lifecycle_unchanged(self):
        from umh.jobs.lifecycle import can_transition

        assert can_transition(JobStatus.CREATED, JobStatus.SUBMITTED)
        assert can_transition(JobStatus.SUBMITTED, JobStatus.RUNNING)
        assert not can_transition(JobStatus.SUCCEEDED, JobStatus.RUNNING)

    def test_existing_worker_poll_still_works(self):
        from umh.nodes.worker import ExecutionResult as WER, WorkerLoop

        store = JobStore()
        job = store.create_job(task_id="t1", node_id="")
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        def success_handler(j):
            return WER(success=True)

        worker = WorkerLoop("w1", store, executor=success_handler)
        worker.start()
        result = worker.poll_once()
        assert result is not None
