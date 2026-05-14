"""Phase 17 tests — Distributed Worker Runtime.

Tests cover: job locking, atomic claiming, worker loop, daemon lifecycle,
distributor control plane, failure handling, heartbeat integration,
boundary invariants, and regression against prior phases.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from umh.jobs.locking import JobLock, JobLockManager
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.store import JobStore
from umh.nodes.daemon import DaemonConfig, DaemonMode, NodeDaemon
from umh.nodes.heartbeat import HeartbeatMonitor
from umh.nodes.worker import ExecutionResult, WorkerLoop, WorkerStats
from umh.runtime.distributor import Distributor


def _make_store(**kwargs) -> JobStore:
    return JobStore(**kwargs)


def _submit_job(store: JobStore, task_id: str = "t1", node_id: str = "") -> ExecutionJob:
    from umh.jobs.lifecycle import transition

    job = store.create_job(task_id=task_id, node_id=node_id, max_attempts=2)
    transition(job, JobStatus.SUBMITTED)
    store.update_job(job)
    return job


def _ok_executor(job: ExecutionJob) -> ExecutionResult:
    return ExecutionResult(success=True, output={"result": "done"})


def _fail_executor(job: ExecutionJob) -> ExecutionResult:
    return ExecutionResult(success=False, error="execution failed")


def _crash_executor(job: ExecutionJob) -> ExecutionResult:
    raise RuntimeError("executor crashed")


# ─── Locking tests ──────────────────────────────────────────────────


class TestJobLocking:
    def test_acquire_lock(self):
        mgr = JobLockManager()
        lock = mgr.acquire_lock("j1", "node_a")
        assert lock is not None
        assert lock.job_id == "j1"
        assert lock.node_id == "node_a"
        assert lock.acquired_at
        assert lock.expires_at

    def test_double_lock_prevented(self):
        mgr = JobLockManager()
        lock1 = mgr.acquire_lock("j1", "node_a")
        lock2 = mgr.acquire_lock("j1", "node_b")
        assert lock1 is not None
        assert lock2 is None

    def test_same_node_double_lock_prevented(self):
        mgr = JobLockManager()
        lock1 = mgr.acquire_lock("j1", "node_a")
        lock2 = mgr.acquire_lock("j1", "node_a")
        assert lock1 is not None
        assert lock2 is None

    def test_lock_expires(self):
        mgr = JobLockManager(lock_ttl_s=10)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        lock1 = mgr.acquire_lock("j1", "node_a", now=now.isoformat())
        assert lock1 is not None

        later = (now + timedelta(seconds=15)).isoformat()
        lock2 = mgr.acquire_lock("j1", "node_b", now=later)
        assert lock2 is not None
        assert lock2.node_id == "node_b"

    def test_release_lock(self):
        mgr = JobLockManager()
        mgr.acquire_lock("j1", "node_a")
        assert mgr.is_locked("j1")
        assert mgr.release_lock("j1")
        assert not mgr.is_locked("j1")

    def test_release_with_wrong_node_fails(self):
        mgr = JobLockManager()
        mgr.acquire_lock("j1", "node_a")
        assert not mgr.release_lock("j1", node_id="node_b")
        assert mgr.is_locked("j1")

    def test_release_nonexistent(self):
        mgr = JobLockManager()
        assert not mgr.release_lock("j_missing")

    def test_is_locked_false_after_expiry(self):
        mgr = JobLockManager(lock_ttl_s=5)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mgr.acquire_lock("j1", "node_a", now=now.isoformat())
        later = (now + timedelta(seconds=10)).isoformat()
        assert not mgr.is_locked("j1", now=later)

    def test_get_owner(self):
        mgr = JobLockManager()
        mgr.acquire_lock("j1", "node_a")
        assert mgr.get_owner("j1") == "node_a"
        assert mgr.get_owner("j_missing") is None

    def test_list_locks(self):
        mgr = JobLockManager()
        mgr.acquire_lock("j1", "node_a")
        mgr.acquire_lock("j2", "node_b")
        locks = mgr.list_locks()
        assert len(locks) == 2
        job_ids = {l.job_id for l in locks}
        assert job_ids == {"j1", "j2"}

    def test_clear_expired(self):
        mgr = JobLockManager(lock_ttl_s=5)
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mgr.acquire_lock("j1", "node_a", now=now.isoformat())
        mgr.acquire_lock("j2", "node_b", now=now.isoformat())
        later = (now + timedelta(seconds=10)).isoformat()
        removed = mgr.clear_expired(now=later)
        assert removed == 2
        assert len(mgr.list_locks()) == 0

    def test_clear_all(self):
        mgr = JobLockManager()
        mgr.acquire_lock("j1", "node_a")
        mgr.acquire_lock("j2", "node_b")
        mgr.clear()
        assert len(mgr.list_locks()) == 0


# ─── Claiming tests ─────────────────────────────────────────────────


class TestJobClaiming:
    def test_claim_job_basic(self):
        lock_mgr = JobLockManager()
        store = _make_store(lock_manager=lock_mgr)
        _submit_job(store, task_id="t1")

        job = store.claim_job("worker_1")
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.node_id == "worker_1"

    def test_claim_job_no_work(self):
        store = _make_store()
        job = store.claim_job("worker_1")
        assert job is None

    def test_claim_prevents_double_execution(self):
        lock_mgr = JobLockManager()
        store = _make_store(lock_manager=lock_mgr)
        _submit_job(store, task_id="t1")

        job1 = store.claim_job("worker_1")
        job2 = store.claim_job("worker_2")
        assert job1 is not None
        assert job2 is None

    def test_claim_without_lock_manager(self):
        store = _make_store()
        _submit_job(store, task_id="t1")
        job = store.claim_job("worker_1")
        assert job is not None
        assert job.status == JobStatus.RUNNING

    def test_claim_oldest_first(self):
        store = _make_store()
        from umh.jobs.lifecycle import transition

        j1 = store.create_job(task_id="first", node_id="")
        transition(j1, JobStatus.SUBMITTED, now="2026-01-01T00:00:01+00:00")
        store.update_job(j1)

        j2 = store.create_job(task_id="second", node_id="")
        transition(j2, JobStatus.SUBMITTED, now="2026-01-01T00:00:02+00:00")
        store.update_job(j2)

        claimed = store.claim_job("w1")
        assert claimed is not None
        assert claimed.task_id == "first"

    def test_claim_skips_non_submitted(self):
        store = _make_store()
        from umh.jobs.lifecycle import transition

        j1 = store.create_job(task_id="t1", node_id="")
        transition(j1, JobStatus.SUBMITTED)
        transition(j1, JobStatus.RUNNING, reason="already running")
        store.update_job(j1)

        claimed = store.claim_job("w1")
        assert claimed is None


# ─── Worker loop tests ───────────────────────────────────────────────


class TestWorkerLoop:
    def test_worker_picks_job(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_ok_executor)
        worker.start()
        job = worker.poll_once()
        assert job is not None
        assert job.status == JobStatus.SUCCEEDED

    def test_worker_no_work(self):
        store = _make_store()
        worker = WorkerLoop("w1", store, executor=_ok_executor)
        worker.start()
        job = worker.poll_once()
        assert job is None
        assert worker.stats.polls == 1

    def test_worker_tracks_stats(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_ok_executor)
        worker.start()
        worker.poll_once()
        assert worker.stats.jobs_claimed == 1
        assert worker.stats.jobs_succeeded == 1
        assert worker.stats.polls == 1

    def test_worker_handles_failed_execution(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_fail_executor)
        worker.start()
        job = worker.poll_once()
        assert job is not None
        assert worker.stats.jobs_failed == 1

        stored = store.get_job(job.job_id)
        assert stored.status == JobStatus.FAILED

    def test_worker_handles_executor_crash(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_crash_executor)
        worker.start()
        job = worker.poll_once()
        assert job is not None
        assert worker.stats.jobs_failed == 1

    def test_worker_no_executor_fails_job(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=None)
        worker.start()
        job = worker.poll_once()
        assert job is not None
        stored = store.get_job(job.job_id)
        assert stored.status == JobStatus.FAILED

    def test_worker_inactive_returns_none(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_ok_executor)
        job = worker.poll_once()
        assert job is None

    def test_worker_stop(self):
        worker = WorkerLoop("w1", _make_store(), executor=_ok_executor)
        worker.start()
        assert worker.active
        worker.stop()
        assert not worker.active

    def test_worker_empty_node_id_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            WorkerLoop("", _make_store())

    def test_worker_releases_lock_after_execution(self):
        lock_mgr = JobLockManager()
        store = _make_store(lock_manager=lock_mgr)
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_ok_executor)
        worker.start()
        job = worker.poll_once()
        assert job is not None
        assert not lock_mgr.is_locked(job.job_id)


# ─── Daemon tests ────────────────────────────────────────────────────


class TestNodeDaemon:
    def test_daemon_starts_and_stops(self):
        store = _make_store()
        config = DaemonConfig(node_id="d1")
        daemon = NodeDaemon(config, store)
        daemon.start()
        assert daemon.active
        daemon.stop()
        assert not daemon.active

    def test_daemon_tick_processes_job(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        config = DaemonConfig(node_id="d1")
        daemon = NodeDaemon(config, store, executor=_ok_executor)
        daemon.start()

        result = daemon.tick()
        assert "job_processed" in result

    def test_daemon_tick_no_work(self):
        store = _make_store()
        config = DaemonConfig(node_id="d1")
        daemon = NodeDaemon(config, store, executor=_ok_executor)
        daemon.start()

        result = daemon.tick()
        assert "job_processed" not in result
        assert result["tick"] == 1

    def test_daemon_heartbeat_emitted(self):
        monitor = HeartbeatMonitor()
        store = _make_store()
        config = DaemonConfig(node_id="d1", heartbeat_interval_s=5.0, poll_interval_s=5.0)
        daemon = NodeDaemon(config, store, heartbeat_monitor=monitor, executor=_ok_executor)
        daemon.start()

        assert daemon.heartbeat_count == 1
        hb = monitor.get_last_heartbeat("d1")
        assert hb is not None
        assert hb.metadata.get("daemon") is True

    def test_daemon_periodic_heartbeat(self):
        monitor = HeartbeatMonitor()
        store = _make_store()
        config = DaemonConfig(node_id="d1", heartbeat_interval_s=10.0, poll_interval_s=5.0)
        daemon = NodeDaemon(config, store, heartbeat_monitor=monitor, executor=_ok_executor)
        daemon.start()
        initial_count = daemon.heartbeat_count

        daemon.run_ticks(2)
        assert daemon.heartbeat_count == initial_count + 1

    def test_daemon_config_empty_node_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            DaemonConfig(node_id="")

    def test_daemon_mode_local(self):
        config = DaemonConfig(node_id="d1", mode=DaemonMode.LOCAL)
        assert config.mode == DaemonMode.LOCAL

    def test_daemon_mode_remote(self):
        config = DaemonConfig(node_id="d1", mode=DaemonMode.REMOTE)
        assert config.mode == DaemonMode.REMOTE

    def test_daemon_inactive_tick(self):
        store = _make_store()
        config = DaemonConfig(node_id="d1")
        daemon = NodeDaemon(config, store)
        result = daemon.tick()
        assert "error" in result


# ─── Distributor tests ───────────────────────────────────────────────


class TestDistributor:
    def test_submit_job(self):
        store = _make_store()
        dist = Distributor(store)
        job = dist.submit_job("t1")
        assert job.status == JobStatus.SUBMITTED
        assert dist.submitted_count == 1

    def test_submit_with_preferred_node(self):
        store = _make_store()
        dist = Distributor(store)
        job = dist.submit_job("t1", preferred_node_id="node_a")
        assert job.metadata.get("preferred_node_id") == "node_a"

    def test_worker_claims_distributed_job(self):
        store = _make_store()
        dist = Distributor(store)
        dist.submit_job("t1")

        worker = WorkerLoop("w1", store, executor=_ok_executor)
        worker.start()
        job = worker.poll_once()
        assert job is not None
        assert job.status == JobStatus.SUCCEEDED

    def test_list_pending(self):
        store = _make_store()
        dist = Distributor(store)
        dist.submit_job("t1")
        dist.submit_job("t2")
        assert len(dist.list_pending()) == 2

    def test_assignment_status(self):
        store = _make_store()
        dist = Distributor(store)
        job = dist.submit_job("t1")
        status = dist.get_assignment_status(job.job_id)
        assert status["status"] == "submitted"
        assert not status["assigned"]

    def test_assignment_status_not_found(self):
        store = _make_store()
        dist = Distributor(store)
        status = dist.get_assignment_status("nonexistent")
        assert status["status"] == "not_found"


# ─── Failure handling tests ──────────────────────────────────────────


class TestFailureHandling:
    def test_worker_death_orphans_job(self):
        """Simulates worker dying: heartbeat goes stale, job gets orphaned."""
        from umh.jobs.poller import JobPoller
        from umh.nodes.health import NodeHealthManager, NodeHealthState

        store = _make_store()
        _submit_job(store, task_id="t1")

        job = store.claim_job("dying_worker")
        assert job is not None
        assert job.status == JobStatus.RUNNING

        health_mgr = NodeHealthManager()
        health_mgr.mark_stale("dying_worker")

        poller = JobPoller()
        health_map = {h.node_id: h for h in health_mgr.list_all()}
        orphaned = poller.detect_orphans(store, health_by_node=health_map)
        assert len(orphaned) == 1

        orphaned_job = store.get_job(job.job_id)
        assert orphaned_job.status == JobStatus.ORPHANED

    def test_expired_lock_allows_reclaim(self):
        lock_mgr = JobLockManager(lock_ttl_s=5)
        store = _make_store(lock_manager=lock_mgr)

        from umh.jobs.lifecycle import transition

        job = store.create_job(task_id="t1", node_id="", max_attempts=3)
        transition(job, JobStatus.SUBMITTED)
        store.update_job(job)

        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        lock = lock_mgr.acquire_lock(job.job_id, "dead_worker", now=now.isoformat())
        assert lock is not None

        later = (now + timedelta(seconds=10)).isoformat()
        assert not lock_mgr.is_locked(job.job_id, now=later)

    def test_job_retried_after_failure(self):
        store = _make_store()
        _submit_job(store, task_id="t1")

        worker = WorkerLoop("w1", store, executor=_fail_executor)
        worker.start()
        job = worker.poll_once()
        assert job is not None

        stored = store.get_job(job.job_id)
        assert stored.status == JobStatus.FAILED

        from umh.jobs.lifecycle import should_retry

        assert should_retry(stored)


# ─── Heartbeat integration tests ────────────────────────────────────


class TestHeartbeatIntegration:
    def test_heartbeat_includes_worker_telemetry(self):
        monitor = HeartbeatMonitor()
        store = _make_store()
        _submit_job(store, task_id="t1")

        config = DaemonConfig(node_id="d1", heartbeat_interval_s=5.0, poll_interval_s=5.0)
        daemon = NodeDaemon(config, store, heartbeat_monitor=monitor, executor=_ok_executor)
        daemon.start()
        daemon.tick()

        hb = monitor.get_last_heartbeat("d1")
        assert hb is not None
        assert "jobs_claimed" in hb.telemetry
        assert "polls" in hb.telemetry

    def test_offline_worker_jobs_orphaned(self):
        from umh.jobs.poller import JobPoller
        from umh.nodes.health import NodeHealthManager

        monitor = HeartbeatMonitor()
        health_mgr = NodeHealthManager()
        store = _make_store()
        _submit_job(store, task_id="t1")

        job = store.claim_job("flaky_node")
        assert job is not None

        health_mgr.mark_stale("flaky_node")

        poller = JobPoller()
        health_map = {h.node_id: h for h in health_mgr.list_all()}
        orphaned = poller.detect_orphans(store, health_by_node=health_map)
        assert job.job_id in orphaned


# ─── Boundary invariant tests ───────────────────────────────────────


class TestBoundaryInvariants:
    def test_locking_does_not_import_cells(self):
        mod = importlib.import_module("umh.jobs.locking")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_worker_does_not_import_cells(self):
        mod = importlib.import_module("umh.nodes.worker")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_daemon_does_not_import_cells(self):
        mod = importlib.import_module("umh.nodes.daemon")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_distributor_does_not_import_cells(self):
        mod = importlib.import_module("umh.runtime.distributor")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_no_subprocess_in_new_modules(self):
        for modname in [
            "umh.jobs.locking",
            "umh.nodes.worker",
            "umh.nodes.daemon",
            "umh.runtime.distributor",
        ]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            assert "import subprocess" not in src
            assert "from subprocess" not in src

    def test_no_shell_true_in_new_modules(self):
        for modname in [
            "umh.jobs.locking",
            "umh.nodes.worker",
            "umh.nodes.daemon",
            "umh.runtime.distributor",
        ]:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword):
                    if node.arg == "shell" and isinstance(node.value, ast.Constant):
                        assert node.value.value is not True, f"shell=True in {modname}"

    def test_worker_does_not_import_environments(self):
        mod = importlib.import_module("umh.nodes.worker")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src

    def test_daemon_does_not_import_environments(self):
        mod = importlib.import_module("umh.nodes.daemon")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src


# ─── Regression tests ───────────────────────────────────────────────


class TestRegression:
    def test_store_works_without_lock_manager(self):
        store = _make_store()
        _submit_job(store, task_id="t1")
        jobs = store.list_jobs(status=JobStatus.SUBMITTED)
        assert len(jobs) == 1

    def test_store_mark_methods_still_work(self):
        store = _make_store()
        job = _submit_job(store, task_id="t1")
        store.mark_running(job.job_id)
        stored = store.get_job(job.job_id)
        assert stored.status == JobStatus.RUNNING

    def test_store_create_job_still_works(self):
        store = _make_store()
        job = store.create_job(task_id="t1", node_id="n1")
        assert job.status == JobStatus.CREATED

    def test_lifecycle_unchanged(self):
        from umh.jobs.lifecycle import can_transition

        assert can_transition(JobStatus.CREATED, JobStatus.SUBMITTED)
        assert can_transition(JobStatus.SUBMITTED, JobStatus.RUNNING)
        assert not can_transition(JobStatus.SUCCEEDED, JobStatus.RUNNING)

    def test_existing_poller_still_works(self):
        from umh.jobs.poller import JobPoller

        store = _make_store()
        poller = JobPoller()
        result = poller.poll_once(store)
        assert result["polled"] == 0
