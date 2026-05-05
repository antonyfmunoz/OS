"""Phase 16 — Durable Persistence + Replayable Runtime State.

Tests: file persistence, atomic writes, corruption handling,
store rehydration, replay engine, orphan handling, runtime
integration, boundary checks, regression.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

from umh.jobs.lifecycle import transition
from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.persistence import FileJobPersistenceBackend, _dict_to_job
from umh.jobs.store import JobStore
from umh.runtime.bootstrap import RuntimeBootstrap


def _make_job(
    job_id: str = "job_test001",
    task_id: str = "t1",
    node_id: str = "n1",
    status: JobStatus = JobStatus.CREATED,
    command: list[str] | None = None,
    attempts: int = 0,
    max_attempts: int = 1,
) -> ExecutionJob:
    return ExecutionJob(
        job_id=job_id,
        task_id=task_id,
        node_id=node_id,
        status=status,
        command=command,
        attempts=attempts,
        max_attempts=max_attempts,
    )


# ─── Persistence backend tests ──────────────────────────────────────


class TestFileJobPersistenceBackend:
    def test_save_and_load_job(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(command=["echo", "hi"])
        backend.save_job(job)
        loaded = backend.load_job("job_test001")
        assert loaded is not None
        assert loaded.job_id == "job_test001"
        assert loaded.command == ["echo", "hi"]

    def test_load_nonexistent_returns_none(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        assert backend.load_job("nonexistent") is None

    def test_load_all_jobs(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        backend.save_job(_make_job(job_id="j1"))
        backend.save_job(_make_job(job_id="j2"))
        jobs = backend.load_all_jobs()
        assert len(jobs) == 2
        ids = {j.job_id for j in jobs}
        assert ids == {"j1", "j2"}

    def test_delete_job(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        backend.save_job(_make_job())
        assert backend.delete_job("job_test001") is True
        assert backend.load_job("job_test001") is None

    def test_delete_nonexistent(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        assert backend.delete_job("nonexistent") is False

    def test_atomic_write_produces_valid_json(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job()
        backend.save_job(job)
        path = tmp_path / "job_test001.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["job_id"] == "job_test001"

    def test_no_temp_files_left(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        backend.save_job(_make_job())
        files = list(tmp_path.iterdir())
        tmp_files = [f for f in files if f.suffix == ".tmp"]
        assert len(tmp_files) == 0

    def test_corrupted_file_skipped(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        backend.save_job(_make_job(job_id="good"))
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{not valid json!!!")
        jobs = backend.load_all_jobs()
        assert len(jobs) == 1
        assert jobs[0].job_id == "good"

    def test_empty_file_skipped(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        (tmp_path / "empty.json").write_text("")
        jobs = backend.load_all_jobs()
        assert len(jobs) == 0

    def test_overwrite_existing_job(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job()
        backend.save_job(job)
        job.error = "updated"
        backend.save_job(job)
        loaded = backend.load_job("job_test001")
        assert loaded.error == "updated"

    def test_directory_created_if_missing(self):
        with tempfile.TemporaryDirectory() as td:
            new_dir = os.path.join(td, "nested", "jobs")
            backend = FileJobPersistenceBackend(directory=new_dir)
            assert Path(new_dir).exists()

    def test_status_preserved_through_roundtrip(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(status=JobStatus.RUNNING, attempts=2, max_attempts=3)
        # Manually set status since lifecycle isn't involved in this unit test
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        job.started_at = "2026-01-01T00:00:01+00:00"
        backend.save_job(job)
        loaded = backend.load_job("job_test001")
        assert loaded.status == JobStatus.RUNNING
        assert loaded.attempts == 2
        assert loaded.max_attempts == 3


# ─── Store with persistence tests ───────────────────────────────────


class TestStoreWithPersistence:
    def test_store_persists_on_create(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        job = store.create_job("t1", "n1", command=["echo"])
        loaded = backend.load_job(job.job_id)
        assert loaded is not None
        assert loaded.task_id == "t1"

    def test_store_persists_on_transition(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        loaded = backend.load_job(job.job_id)
        assert loaded.status == JobStatus.SUBMITTED

    def test_store_reloads_on_init(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store1 = JobStore(persistence=backend)
        job = store1.create_job("t1", "n1", command=["echo"])
        job_id = job.job_id

        store2 = JobStore(persistence=backend)
        loaded = store2.get_job(job_id)
        assert loaded is not None
        assert loaded.task_id == "t1"

    def test_store_update_persists(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        job = store.create_job("t1", "n1")
        job.metadata["extra"] = "data"
        store.update_job(job)
        loaded = backend.load_job(job.job_id)
        assert loaded.metadata.get("extra") == "data"

    def test_store_delete_persists(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        job = store.create_job("t1", "n1")
        store.delete_job(job.job_id)
        assert backend.load_job(job.job_id) is None
        assert store.get_job(job.job_id) is None

    def test_store_without_persistence_still_works(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        assert store.get_job(job.job_id) is not None

    def test_store_lifecycle_still_enforced(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        job = store.create_job("t1", "n1")
        with pytest.raises(ValueError):
            store.mark_running(job.job_id)


# ─── Replay / bootstrap tests ───────────────────────────────────────


class TestRuntimeBootstrap:
    def test_running_becomes_orphaned(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_run", status=JobStatus.RUNNING, attempts=1)
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        job.started_at = "2026-01-01T00:00:01+00:00"
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_run")
        assert loaded.status == JobStatus.ORPHANED
        assert report.orphaned == 1

    def test_submitted_preserved(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_sub", status=JobStatus.SUBMITTED, attempts=1)
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_sub")
        assert loaded.status == JobStatus.SUBMITTED
        assert report.kept_as_is == 1

    def test_succeeded_untouched(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_done", status=JobStatus.SUCCEEDED)
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        job.finished_at = "2026-01-01T00:00:05+00:00"
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_done")
        assert loaded.status == JobStatus.SUCCEEDED
        assert report.terminal == 1

    def test_cancelled_untouched(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_cancel", status=JobStatus.CANCELLED)
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_cancel")
        assert loaded.status == JobStatus.CANCELLED
        assert report.terminal == 1

    def test_created_preserved(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_new")
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_new")
        assert loaded.status == JobStatus.CREATED
        assert report.kept_as_is == 1

    def test_running_with_retries_becomes_submitted(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(
            job_id="j_retry",
            status=JobStatus.RUNNING,
            attempts=1,
            max_attempts=3,
        )
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        job.started_at = "2026-01-01T00:00:01+00:00"
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_retry")
        assert loaded.status == JobStatus.SUBMITTED
        assert report.orphaned == 1
        assert report.retried == 1

    def test_failed_with_retries_retried(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(
            job_id="j_fail",
            status=JobStatus.FAILED,
            attempts=1,
            max_attempts=3,
        )
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_fail")
        assert loaded.status == JobStatus.SUBMITTED
        assert report.retried == 1

    def test_failed_exhausted_stays_terminal(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(
            job_id="j_exhaust",
            status=JobStatus.FAILED,
            attempts=3,
            max_attempts=3,
        )
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_exhaust")
        assert loaded.status == JobStatus.FAILED
        assert report.terminal == 1

    def test_report_serializes(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)
        d = report.to_dict()
        assert isinstance(d["total_loaded"], int)

    def test_empty_store_bootstrap(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)
        assert report.total_loaded == 0


# ─── Runtime integration tests ──────────────────────────────────────


class TestRuntimeIntegration:
    def test_bootstrap_then_runtime_loop(self, tmp_path):
        from umh.jobs.poller import JobPoller
        from umh.runtime.loop import RuntimeLoop

        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_loop", status=JobStatus.SUBMITTED, attempts=1)
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        bootstrap.rehydrate(store)

        poller = JobPoller()
        loop = RuntimeLoop(job_poller=poller, job_store=store)
        loop.start()
        try:
            result = loop.tick()
            assert "error" not in result
        finally:
            loop.stop()

    def test_persisted_state_survives_store_recreation(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))

        store1 = JobStore(persistence=backend)
        job = store1.create_job("t1", "n1", command=["echo"])
        store1.mark_submitted(job.job_id)
        store1.mark_running(job.job_id)
        store1.mark_succeeded(job.job_id, {"output": "done"})
        job_id = job.job_id

        store2 = JobStore(persistence=backend)
        loaded = store2.get_job(job_id)
        assert loaded is not None
        assert loaded.status == JobStatus.SUCCEEDED
        assert loaded.result == {"output": "done"}

    def test_no_execution_during_replay(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        job = _make_job(job_id="j_noop", status=JobStatus.RUNNING, attempts=1)
        job.submitted_at = "2026-01-01T00:00:00+00:00"
        job.started_at = "2026-01-01T00:00:01+00:00"
        backend.save_job(job)

        store = JobStore(persistence=backend)
        bootstrap = RuntimeBootstrap()
        report = bootstrap.rehydrate(store)

        loaded = store.get_job("j_noop")
        assert loaded.status == JobStatus.ORPHANED
        assert loaded.result is None


# ─── Boundary tests ─────────────────────────────────────────────────


class TestBoundaryInvariants:
    def test_persistence_does_not_import_cells(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.jobs.persistence")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_persistence_does_not_import_environments(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.jobs.persistence")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src

    def test_persistence_does_not_import_subprocess(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.jobs.persistence")
        src = inspect.getsource(mod)
        assert "import subprocess" not in src

    def test_bootstrap_does_not_import_cells(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.runtime.bootstrap")
        src = inspect.getsource(mod)
        assert "from umh.cells" not in src

    def test_bootstrap_does_not_import_environments(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.runtime.bootstrap")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src

    def test_bootstrap_does_not_import_subprocess(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.runtime.bootstrap")
        src = inspect.getsource(mod)
        assert "import subprocess" not in src

    def test_no_shell_true_in_persistence(self):
        import ast
        import importlib
        import inspect

        for name in ["umh.jobs.persistence", "umh.runtime.bootstrap"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "shell":
                    if isinstance(node.value, ast.Constant) and node.value.value is True:
                        raise AssertionError(f"{name} passes shell=True")

    def test_lifecycle_still_enforced_with_persistence(self, tmp_path):
        backend = FileJobPersistenceBackend(directory=str(tmp_path))
        store = JobStore(persistence=backend)
        job = store.create_job("t1", "n1")
        with pytest.raises(ValueError):
            store.mark_running(job.job_id)


# ─── Regression / import tests ───────────────────────────────────────


class TestPhase16Regression:
    def test_import_persistence(self):
        from umh.jobs import FileJobPersistenceBackend, JobPersistenceBackend

        assert FileJobPersistenceBackend is not None

    def test_import_bootstrap(self):
        from umh.runtime import BootstrapReport, RuntimeBootstrap

        assert RuntimeBootstrap is not None

    def test_store_without_persistence_backward_compatible(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        assert store.get_job(job.job_id).status == JobStatus.SUBMITTED

    def test_dict_to_job_roundtrip(self):
        job = _make_job(command=["test"], attempts=2, max_attempts=5)
        d = job.to_dict()
        rebuilt = _dict_to_job(d)
        assert rebuilt.job_id == job.job_id
        assert rebuilt.command == ["test"]
        assert rebuilt.attempts == 2
        assert rebuilt.max_attempts == 5

    def test_phase15_types_still_importable(self):
        from umh.jobs import JobPoller, JobStore

        assert JobPoller is not None
        assert JobStore is not None

    def test_phase14_types_still_importable(self):
        from umh.nodes import SSHNodeTransport, TransportBackedRemoteNodeClient

        assert SSHNodeTransport is not None

    def test_phase13_types_still_importable(self):
        from umh.nodes import FailoverRouter, HeartbeatMonitor, NodeHealthManager

        assert FailoverRouter is not None
