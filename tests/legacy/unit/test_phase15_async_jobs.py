"""Phase 15 — Asynchronous Distributed Execution Jobs + Remote Job Lifecycle.

Tests: job models, lifecycle state machine, in-memory store, remote client
integration, poller, runtime loop integration, boundary checks, regression.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "/opt/OS")

from umh.jobs.lifecycle import (
    can_transition,
    is_terminal,
    is_terminal_for_job,
    should_retry,
    transition,
)
from umh.jobs.models import ExecutionJob, JobResult, JobStatus, _gen_job_id
from umh.jobs.poller import JobPoller
from umh.jobs.store import JobStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


# ─── Model tests ─────────────────────────────────────────────────────


class TestJobModels:
    def test_command_must_be_list(self):
        with pytest.raises(TypeError):
            ExecutionJob(job_id="j1", task_id="t1", node_id="n1", command="bad")

    def test_command_none_is_valid(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="n1")
        assert job.command is None

    def test_command_list_is_valid(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="n1", command=["echo", "hi"])
        assert job.command == ["echo", "hi"]

    def test_job_serializes(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="n1")
        d = job.to_dict()
        assert d["job_id"] == "j1"
        assert d["status"] == "created"

    def test_result_serializes(self):
        r = JobResult(job_id="j1", status=JobStatus.SUCCEEDED, stdout="ok", exit_code=0)
        d = r.to_dict()
        assert d["status"] == "succeeded"
        assert d["stdout"] == "ok"

    def test_default_values(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="n1")
        assert job.status == JobStatus.CREATED
        assert job.attempts == 0
        assert job.max_attempts == 1
        assert job.timeout_seconds == 60
        assert job.created_at != ""

    def test_gen_job_id_unique(self):
        ids = {_gen_job_id() for _ in range(100)}
        assert len(ids) == 100


# ─── Lifecycle tests ────────────────────────────────────────────────


class TestJobLifecycle:
    def test_created_to_submitted(self):
        assert can_transition(JobStatus.CREATED, JobStatus.SUBMITTED)

    def test_submitted_to_running(self):
        assert can_transition(JobStatus.SUBMITTED, JobStatus.RUNNING)

    def test_running_to_succeeded(self):
        assert can_transition(JobStatus.RUNNING, JobStatus.SUCCEEDED)

    def test_running_to_failed(self):
        assert can_transition(JobStatus.RUNNING, JobStatus.FAILED)

    def test_running_to_timeout(self):
        assert can_transition(JobStatus.RUNNING, JobStatus.TIMEOUT)

    def test_running_to_orphaned(self):
        assert can_transition(JobStatus.RUNNING, JobStatus.ORPHANED)

    def test_invalid_created_to_running(self):
        assert not can_transition(JobStatus.CREATED, JobStatus.RUNNING)

    def test_invalid_succeeded_to_anything(self):
        for s in JobStatus:
            assert not can_transition(JobStatus.SUCCEEDED, s)

    def test_invalid_cancelled_to_anything(self):
        for s in JobStatus:
            assert not can_transition(JobStatus.CANCELLED, s)

    def test_terminal_succeeded(self):
        assert is_terminal(JobStatus.SUCCEEDED)

    def test_terminal_cancelled(self):
        assert is_terminal(JobStatus.CANCELLED)

    def test_not_terminal_running(self):
        assert not is_terminal(JobStatus.RUNNING)

    def test_terminal_for_job_exhausted_retries(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.FAILED,
            attempts=3,
            max_attempts=3,
        )
        assert is_terminal_for_job(job)

    def test_not_terminal_for_job_with_retries(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.FAILED,
            attempts=1,
            max_attempts=3,
        )
        assert not is_terminal_for_job(job)

    def test_should_retry_failed_with_attempts(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.FAILED,
            attempts=1,
            max_attempts=3,
        )
        assert should_retry(job)

    def test_should_not_retry_exhausted(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.FAILED,
            attempts=3,
            max_attempts=3,
        )
        assert not should_retry(job)

    def test_should_not_retry_running(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.RUNNING,
            attempts=1,
            max_attempts=3,
        )
        assert not should_retry(job)

    def test_transition_updates_status(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="n1")
        transition(job, JobStatus.SUBMITTED)
        assert job.status == JobStatus.SUBMITTED
        assert job.attempts == 1

    def test_transition_invalid_raises(self):
        job = ExecutionJob(job_id="j1", task_id="t1", node_id="n1")
        with pytest.raises(ValueError):
            transition(job, JobStatus.RUNNING)

    def test_retry_denied_when_exhausted(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.FAILED,
            attempts=2,
            max_attempts=2,
        )
        with pytest.raises(ValueError, match="Cannot retry"):
            transition(job, JobStatus.SUBMITTED)

    def test_retry_allowed_when_attempts_remain(self):
        job = ExecutionJob(
            job_id="j1",
            task_id="t1",
            node_id="n1",
            status=JobStatus.FAILED,
            attempts=1,
            max_attempts=3,
        )
        transition(job, JobStatus.SUBMITTED)
        assert job.status == JobStatus.SUBMITTED
        assert job.attempts == 2


# ─── Store tests ─────────────────────────────────────────────────────


class TestJobStore:
    def test_create_and_get(self):
        store = JobStore()
        job = store.create_job("t1", "n1", command=["echo", "hi"])
        fetched = store.get_job(job.job_id)
        assert fetched is not None
        assert fetched.task_id == "t1"

    def test_list_by_status(self):
        store = JobStore()
        j1 = store.create_job("t1", "n1")
        j2 = store.create_job("t2", "n1")
        store.mark_submitted(j1.job_id)
        created = store.list_jobs(status=JobStatus.CREATED)
        submitted = store.list_jobs(status=JobStatus.SUBMITTED)
        assert len(created) == 1
        assert len(submitted) == 1

    def test_list_by_node(self):
        store = JobStore()
        store.create_job("t1", "n1")
        store.create_job("t2", "n2")
        n1_jobs = store.list_jobs(node_id="n1")
        assert len(n1_jobs) == 1

    def test_mark_submitted_running_succeeded(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        store.mark_succeeded(job.job_id, {"output": "done"})
        fetched = store.get_job(job.job_id)
        assert fetched.status == JobStatus.SUCCEEDED
        assert fetched.result == {"output": "done"}

    def test_mark_failed(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        store.mark_failed(job.job_id, "something broke")
        fetched = store.get_job(job.job_id)
        assert fetched.status == JobStatus.FAILED
        assert fetched.error == "something broke"

    def test_mark_timeout(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        store.mark_timeout(job.job_id, "took too long")
        fetched = store.get_job(job.job_id)
        assert fetched.status == JobStatus.TIMEOUT

    def test_cancel_job(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        store.cancel_job(job.job_id)
        fetched = store.get_job(job.job_id)
        assert fetched.status == JobStatus.CANCELLED

    def test_invalid_transition_raises(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        with pytest.raises(ValueError):
            store.mark_running(job.job_id)

    def test_missing_job_raises(self):
        store = JobStore()
        with pytest.raises(KeyError):
            store.mark_submitted("nonexistent")


# ─── Remote client async contract tests ──────────────────────────────


class TestRemoteClientJobContract:
    def test_submit_job_with_command(self):
        from umh.nodes.registry import DeviceNode, DeviceType
        from umh.nodes.remote import RemoteExecutionStatus, TransportBackedRemoteNodeClient
        from umh.nodes.ssh_transport import SSHNodeTransport
        from umh.nodes.transport import RemoteCommandResult, TransportStatus

        transport = MagicMock(spec=SSHNodeTransport)
        transport.ping.return_value = TransportStatus.OK
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.OK,
            stdout="done",
            exit_code=0,
        )
        client = TransportBackedRemoteNodeClient(transport)
        node = DeviceNode(
            node_id="n1",
            device_type=DeviceType.VPS,
            metadata={"host": "10.0.0.1", "user": "deploy"},
        )
        record = client.submit_execution(node, {"task_id": "t1", "command": ["echo", "hi"]})
        assert record.status == RemoteExecutionStatus.SUCCEEDED

    def test_submit_job_without_command_fails(self):
        from umh.nodes.registry import DeviceNode, DeviceType
        from umh.nodes.remote import RemoteExecutionStatus, TransportBackedRemoteNodeClient
        from umh.nodes.ssh_transport import SSHNodeTransport
        from umh.nodes.transport import TransportStatus

        transport = MagicMock(spec=SSHNodeTransport)
        transport.ping.return_value = TransportStatus.OK
        client = TransportBackedRemoteNodeClient(transport)
        node = DeviceNode(
            node_id="n1",
            device_type=DeviceType.VPS,
            metadata={"host": "10.0.0.1", "user": "deploy"},
        )
        record = client.submit_execution(node, {"task_id": "t1"})
        assert record.status == RemoteExecutionStatus.FAILED

    def test_poll_returns_known_record(self):
        from umh.nodes.registry import DeviceNode, DeviceType
        from umh.nodes.remote import TransportBackedRemoteNodeClient
        from umh.nodes.ssh_transport import SSHNodeTransport
        from umh.nodes.transport import RemoteCommandResult, TransportStatus

        transport = MagicMock(spec=SSHNodeTransport)
        transport.ping.return_value = TransportStatus.OK
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.OK,
            stdout="done",
            exit_code=0,
        )
        client = TransportBackedRemoteNodeClient(transport)
        node = DeviceNode(
            node_id="n1",
            device_type=DeviceType.VPS,
            metadata={"host": "10.0.0.1", "user": "deploy"},
        )
        client.submit_execution(node, {"task_id": "t1", "command": ["echo"]})
        result = client.fetch_result(node, "t1")
        assert result is not None

    def test_cancel_job_safe(self):
        from umh.nodes.registry import DeviceNode, DeviceType
        from umh.nodes.remote import RemoteExecutionStatus, TransportBackedRemoteNodeClient
        from umh.nodes.ssh_transport import SSHNodeTransport
        from umh.nodes.transport import RemoteCommandResult, TransportStatus

        transport = MagicMock(spec=SSHNodeTransport)
        transport.ping.return_value = TransportStatus.OK
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.OK,
            stdout="done",
            exit_code=0,
        )
        client = TransportBackedRemoteNodeClient(transport)
        node = DeviceNode(
            node_id="n1",
            device_type=DeviceType.VPS,
            metadata={"host": "10.0.0.1", "user": "deploy"},
        )
        client.submit_execution(node, {"task_id": "t1", "command": ["echo"]})
        assert client.cancel(node, "t1") is True


# ─── Poller tests ────────────────────────────────────────────────────


class TestJobPoller:
    def test_poll_once_updates_succeeded(self):
        from umh.nodes.registry import DeviceNode, DeviceType
        from umh.nodes.remote import RemoteExecutionRecord, RemoteExecutionStatus

        store = JobStore()
        job = store.create_job("t1", "n1", command=["echo"])
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)

        record = RemoteExecutionRecord(
            task_id="t1",
            node_id="n1",
            status=RemoteExecutionStatus.SUCCEEDED,
            result={"out": "ok"},
        )
        client = MagicMock()
        client.fetch_result.return_value = record
        node = DeviceNode(node_id="n1", device_type=DeviceType.VPS)

        poller = JobPoller()
        result = poller.poll_once(store, client, {"n1": node})
        assert result["polled"] >= 1

        fetched = store.get_job(job.job_id)
        assert fetched.status == JobStatus.SUCCEEDED

    def test_poll_once_updates_failed(self):
        from umh.nodes.registry import DeviceNode, DeviceType
        from umh.nodes.remote import RemoteExecutionRecord, RemoteExecutionStatus

        store = JobStore()
        job = store.create_job("t1", "n1", command=["bad_cmd"])
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)

        record = RemoteExecutionRecord(
            task_id="t1",
            node_id="n1",
            status=RemoteExecutionStatus.FAILED,
            error="not found",
        )
        client = MagicMock()
        client.fetch_result.return_value = record
        node = DeviceNode(node_id="n1", device_type=DeviceType.VPS)

        poller = JobPoller()
        poller.poll_once(store, client, {"n1": node})
        assert store.get_job(job.job_id).status == JobStatus.FAILED

    def test_timeout_detection(self):
        store = JobStore()
        job = store.create_job("t1", "n1", timeout_seconds=10)
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        job.started_at = _past_iso(30)

        poller = JobPoller()
        timed_out = poller.detect_timeouts(store)
        assert job.job_id in timed_out
        assert store.get_job(job.job_id).status == JobStatus.TIMEOUT

    def test_orphan_detection(self):
        from umh.nodes.health import NodeHealth, NodeHealthState

        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)

        health = NodeHealth(node_id="n1", state=NodeHealthState.OFFLINE)
        poller = JobPoller()
        orphaned = poller.detect_orphans(store, {"n1": health})
        assert job.job_id in orphaned
        assert store.get_job(job.job_id).status == JobStatus.ORPHANED

    def test_retry_eligible(self):
        store = JobStore()
        job = store.create_job("t1", "n1", max_attempts=3)
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        store.mark_failed(job.job_id, "oops")

        poller = JobPoller()
        eligible = poller.retry_eligible(store)
        assert len(eligible) == 1
        assert eligible[0].job_id == job.job_id

    def test_retry_job(self):
        store = JobStore()
        job = store.create_job("t1", "n1", max_attempts=3)
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        store.mark_failed(job.job_id, "oops")

        poller = JobPoller()
        retried = poller.retry_job(store, job.job_id)
        assert retried is not None
        assert retried.status == JobStatus.SUBMITTED
        assert retried.attempts == 2

    def test_poller_does_not_crash_on_unreachable(self):
        from umh.nodes.registry import DeviceNode, DeviceType

        store = JobStore()
        job = store.create_job("t1", "n1", command=["echo"])
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)

        client = MagicMock()
        client.fetch_result.side_effect = ConnectionError("unreachable")
        node = DeviceNode(node_id="n1", device_type=DeviceType.VPS)

        poller = JobPoller()
        result = poller.poll_once(store, client, {"n1": node})
        assert result["errors"] >= 1
        assert store.get_job(job.job_id).status == JobStatus.RUNNING

    def test_orphan_detection_without_health(self):
        store = JobStore()
        job = store.create_job("t1", "n1")
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)

        poller = JobPoller()
        orphaned = poller.detect_orphans(store, health_by_node=None)
        assert orphaned == []


# ─── Runtime loop integration tests ─────────────────────────────────


class TestRuntimeLoopJobIntegration:
    def test_tick_with_job_poller_does_not_crash(self):
        from umh.runtime.loop import RuntimeLoop

        store = JobStore()
        poller = JobPoller()
        loop = RuntimeLoop(job_poller=poller, job_store=store)
        loop.start()
        try:
            result = loop.tick()
            assert "error" not in result
        finally:
            loop.stop()

    def test_tick_without_job_poller_unchanged(self):
        from umh.runtime.loop import RuntimeLoop

        loop = RuntimeLoop()
        loop.start()
        try:
            result = loop.tick()
            assert "error" not in result
            assert "job_updates" not in result
        finally:
            loop.stop()

    def test_tick_detects_timed_out_jobs(self):
        from umh.runtime.loop import RuntimeLoop

        store = JobStore()
        job = store.create_job("t1", "n1", timeout_seconds=5)
        store.mark_submitted(job.job_id)
        store.mark_running(job.job_id)
        job.started_at = _past_iso(30)

        poller = JobPoller()
        loop = RuntimeLoop(job_poller=poller, job_store=store)
        loop.start()
        try:
            result = loop.tick()
            assert result.get("job_updates") is not None
            assert job.job_id in result["job_updates"]["timed_out"]
        finally:
            loop.stop()


# ─── Boundary tests ─────────────────────────────────────────────────


class TestBoundaryInvariants:
    def test_cells_do_not_import_jobs(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.cells.models")
        src = inspect.getsource(mod)
        assert "from umh.jobs" not in src
        assert "import umh.jobs" not in src

    def test_cells_do_not_import_nodes(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.cells.models")
        src = inspect.getsource(mod)
        assert "from umh.nodes" not in src
        assert "import umh.nodes" not in src

    def test_cells_do_not_import_transports(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.cells.models")
        src = inspect.getsource(mod)
        assert "from umh.nodes.transport" not in src
        assert "from umh.nodes.ssh_transport" not in src

    def test_cells_do_not_import_environments(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.cells.models")
        src = inspect.getsource(mod)
        assert "from umh.environments" not in src
        assert "import umh.environments" not in src

    def test_jobs_do_not_import_cells(self):
        import importlib
        import inspect

        for name in ["umh.jobs.models", "umh.jobs.lifecycle", "umh.jobs.store", "umh.jobs.poller"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.cells" not in src, f"{name} imports cells"

    def test_jobs_do_not_import_environments(self):
        import importlib
        import inspect

        for name in ["umh.jobs.models", "umh.jobs.lifecycle", "umh.jobs.store", "umh.jobs.poller"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.environments" not in src, f"{name} imports environments"

    def test_jobs_do_not_import_adapters(self):
        import importlib
        import inspect

        for name in ["umh.jobs.models", "umh.jobs.lifecycle", "umh.jobs.store", "umh.jobs.poller"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.adapters" not in src, f"{name} imports adapters"

    def test_no_shell_true_in_jobs(self):
        import ast
        import importlib
        import inspect

        for name in ["umh.jobs.models", "umh.jobs.lifecycle", "umh.jobs.store", "umh.jobs.poller"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "shell":
                    if isinstance(node.value, ast.Constant) and node.value.value is True:
                        raise AssertionError(f"{name} passes shell=True")

    def test_no_subprocess_in_jobs(self):
        import importlib
        import inspect

        for name in ["umh.jobs.models", "umh.jobs.lifecycle", "umh.jobs.store", "umh.jobs.poller"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "import subprocess" not in src, f"{name} imports subprocess"


# ─── Regression / import tests ───────────────────────────────────────


class TestPhase15Regression:
    def test_import_jobs_package(self):
        from umh.jobs import ExecutionJob, JobPoller, JobStore

        assert ExecutionJob is not None
        assert JobStore is not None
        assert JobPoller is not None

    def test_import_lifecycle(self):
        from umh.jobs import can_transition, is_terminal, should_retry, transition

        assert callable(can_transition)
        assert callable(transition)

    def test_import_models(self):
        from umh.jobs import JobResult, JobStatus

        assert JobStatus.CREATED.value == "created"

    def test_phase14_types_still_importable(self):
        from umh.nodes import SSHNodeTransport, TransportBackedRemoteNodeClient

        assert SSHNodeTransport is not None

    def test_phase13_types_still_importable(self):
        from umh.nodes import FailoverRouter, HeartbeatMonitor, NodeHealthManager

        assert FailoverRouter is not None
