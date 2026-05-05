"""Phase 14 — Real Remote Node Transport + SSH Execution v1.

Tests: transport models, SSH transport (mocked subprocess), transport-backed
remote client, remote heartbeat collection, failover/health compatibility,
boundary checks, regression.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/opt/OS")

from umh.nodes.failover import FailoverRouter
from umh.nodes.health import NodeHealthManager, NodeHealthState
from umh.nodes.heartbeat import HeartbeatStatus, NodeHeartbeat
from umh.nodes.registry import DeviceNode, DeviceType
from umh.nodes.remote import (
    MockRemoteNodeClient,
    RemoteExecutionRecord,
    RemoteExecutionStatus,
    RemoteNodeClient,
    TransportBackedRemoteNodeClient,
    collect_remote_heartbeat,
)
from umh.nodes.ssh_transport import SSHNodeTransport
from umh.nodes.transport import (
    NodeTransport,
    RemoteCommand,
    RemoteCommandResult,
    TransportStatus,
)


def _make_node(
    node_id: str = "n1",
    dtype: DeviceType = DeviceType.VPS,
    host: str = "10.0.0.1",
    user: str = "deploy",
    port: int = 22,
    identity_file: str = "",
) -> DeviceNode:
    meta = {"host": host, "user": user, "port": port}
    if identity_file:
        meta["identity_file"] = identity_file
    return DeviceNode(
        node_id=node_id, device_type=dtype, hostname=f"{node_id}.remote", metadata=meta
    )


def _make_node_no_ssh(node_id: str = "bad") -> DeviceNode:
    return DeviceNode(
        node_id=node_id, device_type=DeviceType.VPS, hostname="bad.remote", metadata={}
    )


def _mock_subprocess_ok(stdout: str = "pong\n", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = 0
    result.stdout = stdout
    result.stderr = stderr
    return result


def _mock_subprocess_fail(
    returncode: int = 1, stderr: str = "error", stdout: str = ""
) -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ─── Transport model tests ──────────────────────────────────────────


class TestTransportModels:
    def test_remote_command_requires_non_empty(self):
        with pytest.raises(ValueError):
            RemoteCommand(command=())

    def test_remote_command_serializes(self):
        cmd = RemoteCommand(command=("echo", "hello"), timeout_seconds=10)
        d = cmd.to_dict()
        assert d["command"] == ["echo", "hello"]
        assert d["timeout_seconds"] == 10

    def test_remote_command_result_serializes(self):
        r = RemoteCommandResult(status=TransportStatus.OK, stdout="ok", exit_code=0)
        d = r.to_dict()
        assert d["status"] == "ok"
        assert d["stdout"] == "ok"

    def test_transport_status_values(self):
        assert TransportStatus.OK.value == "ok"
        assert TransportStatus.TIMEOUT.value == "timeout"
        assert TransportStatus.AUTH_FAILED.value == "auth_failed"


# ─── SSH transport tests ────────────────────────────────────────────


class TestSSHTransport:
    def test_builds_ssh_args_without_shell(self):
        transport = SSHNodeTransport()
        args = transport._build_ssh_args("10.0.0.1", "deploy", 22, "")
        assert args[0] == "ssh"
        assert "-o" in args
        assert "BatchMode=yes" in args
        assert "deploy@10.0.0.1" in args
        assert "shell" not in " ".join(args).lower()

    def test_builds_ssh_args_with_identity(self):
        transport = SSHNodeTransport()
        args = transport._build_ssh_args("10.0.0.1", "deploy", 22, "/keys/id_rsa")
        assert "-i" in args
        assert "/keys/id_rsa" in args

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_ping_success(self, mock_run):
        mock_run.return_value = _mock_subprocess_ok()
        transport = SSHNodeTransport()
        node = _make_node()
        status = transport.ping(node)
        assert status == TransportStatus.OK
        call_args = mock_run.call_args[0][0]
        assert isinstance(call_args, list)

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_ping_permission_denied(self, mock_run):
        mock_run.return_value = _mock_subprocess_fail(255, "Permission denied")
        transport = SSHNodeTransport()
        status = transport.ping(_make_node())
        assert status == TransportStatus.AUTH_FAILED

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_ping_unreachable(self, mock_run):
        mock_run.return_value = _mock_subprocess_fail(255, "Connection refused")
        transport = SSHNodeTransport()
        status = transport.ping(_make_node())
        assert status == TransportStatus.UNREACHABLE

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_ping_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ssh", timeout=10)
        transport = SSHNodeTransport()
        status = transport.ping(_make_node())
        assert status == TransportStatus.TIMEOUT

    def test_ping_missing_host_returns_auth_failed(self):
        transport = SSHNodeTransport()
        status = transport.ping(_make_node_no_ssh())
        assert status == TransportStatus.AUTH_FAILED

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_run_command_success(self, mock_run):
        mock_run.return_value = _mock_subprocess_ok("hello world\n")
        transport = SSHNodeTransport()
        cmd = RemoteCommand(command=("echo", "hello world"), timeout_seconds=10)
        result = transport.run_command(_make_node(), cmd)
        assert result.status == TransportStatus.OK
        assert "hello world" in result.stdout
        assert result.exit_code == 0

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_run_command_failure(self, mock_run):
        mock_run.return_value = _mock_subprocess_fail(1, "not found")
        transport = SSHNodeTransport()
        cmd = RemoteCommand(command=("bad_cmd",), timeout_seconds=10)
        result = transport.run_command(_make_node(), cmd)
        assert result.status == TransportStatus.FAILED
        assert result.exit_code == 1

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_run_command_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ssh", timeout=5)
        transport = SSHNodeTransport()
        cmd = RemoteCommand(command=("sleep", "100"), timeout_seconds=5)
        result = transport.run_command(_make_node(), cmd)
        assert result.status == TransportStatus.TIMEOUT
        assert "timed out" in result.error

    def test_run_command_missing_host(self):
        transport = SSHNodeTransport()
        cmd = RemoteCommand(command=("echo", "test"), timeout_seconds=5)
        result = transport.run_command(_make_node_no_ssh(), cmd)
        assert result.status == TransportStatus.AUTH_FAILED

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_run_command_ssh_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("ssh not found")
        transport = SSHNodeTransport()
        cmd = RemoteCommand(command=("echo", "hi"), timeout_seconds=5)
        result = transport.run_command(_make_node(), cmd)
        assert result.status == TransportStatus.FAILED
        assert "not found" in result.error

    def test_ssh_implements_transport_protocol(self):
        transport = SSHNodeTransport()
        assert isinstance(transport, NodeTransport)

    def test_close_is_noop(self):
        transport = SSHNodeTransport()
        transport.close(_make_node())

    @patch("umh.nodes.ssh_transport.subprocess.run")
    def test_no_shell_true_in_subprocess_call(self, mock_run):
        mock_run.return_value = _mock_subprocess_ok()
        transport = SSHNodeTransport()
        cmd = RemoteCommand(command=("echo", "test"), timeout_seconds=5)
        transport.run_command(_make_node(), cmd)
        _, kwargs = mock_run.call_args
        assert "shell" not in kwargs or kwargs.get("shell") is not True


# ─── Transport-backed remote client tests ────────────────────────────


class TestTransportBackedRemoteClient:
    def _make_mock_transport(self, ping_status=TransportStatus.OK, cmd_result=None):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.ping.return_value = ping_status
        if cmd_result is None:
            cmd_result = RemoteCommandResult(status=TransportStatus.OK, stdout="done", exit_code=0)
        transport.run_command.return_value = cmd_result
        return transport

    def test_implements_remote_node_client(self):
        transport = self._make_mock_transport()
        client = TransportBackedRemoteNodeClient(transport)
        assert isinstance(client, RemoteNodeClient)

    def test_ping_delegates_to_transport(self):
        transport = self._make_mock_transport(ping_status=TransportStatus.OK)
        client = TransportBackedRemoteNodeClient(transport)
        assert client.ping(_make_node()) is True

    def test_ping_unreachable(self):
        transport = self._make_mock_transport(ping_status=TransportStatus.UNREACHABLE)
        client = TransportBackedRemoteNodeClient(transport)
        assert client.ping(_make_node()) is False

    def test_submit_with_command_succeeds(self):
        transport = self._make_mock_transport()
        client = TransportBackedRemoteNodeClient(transport)
        record = client.submit_execution(_make_node(), {"task_id": "t1", "command": ["echo", "hi"]})
        assert record.status == RemoteExecutionStatus.SUCCEEDED
        assert record.result["stdout"] == "done"

    def test_submit_without_command_fails(self):
        transport = self._make_mock_transport()
        client = TransportBackedRemoteNodeClient(transport)
        record = client.submit_execution(_make_node(), {"task_id": "t1"})
        assert record.status == RemoteExecutionStatus.FAILED
        assert "no valid command" in record.error

    def test_submit_timeout(self):
        transport = self._make_mock_transport(
            cmd_result=RemoteCommandResult(status=TransportStatus.TIMEOUT, error="timed out")
        )
        client = TransportBackedRemoteNodeClient(transport)
        record = client.submit_execution(
            _make_node(), {"task_id": "t1", "command": ["sleep", "100"]}
        )
        assert record.status == RemoteExecutionStatus.FAILED

    def test_submit_unreachable(self):
        transport = self._make_mock_transport(
            cmd_result=RemoteCommandResult(status=TransportStatus.UNREACHABLE, error="refused")
        )
        client = TransportBackedRemoteNodeClient(transport)
        record = client.submit_execution(_make_node(), {"task_id": "t1", "command": ["echo"]})
        assert record.status == RemoteExecutionStatus.UNREACHABLE

    def test_fetch_result(self):
        transport = self._make_mock_transport()
        client = TransportBackedRemoteNodeClient(transport)
        client.submit_execution(_make_node(), {"task_id": "t1", "command": ["echo"]})
        result = client.fetch_result(_make_node(), "t1")
        assert result is not None
        assert result.task_id == "t1"

    def test_cancel(self):
        transport = self._make_mock_transport()
        client = TransportBackedRemoteNodeClient(transport)
        client.submit_execution(_make_node(), {"task_id": "t1", "command": ["echo"]})
        assert client.cancel(_make_node(), "t1") is True
        result = client.fetch_result(_make_node(), "t1")
        assert result.status == RemoteExecutionStatus.CANCELLED

    def test_invalid_transport_raises(self):
        with pytest.raises(TypeError):
            TransportBackedRemoteNodeClient("not_a_transport")


# ─── Remote heartbeat tests ─────────────────────────────────────────


class TestRemoteHeartbeat:
    def test_success_creates_heartbeat(self):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.OK,
            stdout=json.dumps(
                {
                    "hostname": "vps1",
                    "platform": "Linux",
                    "load_1m": 0.5,
                    "timestamp": 1234567890.0,
                }
            ),
            exit_code=0,
        )
        hb = collect_remote_heartbeat(_make_node(), transport)
        assert hb.status == HeartbeatStatus.OK
        assert hb.telemetry["hostname"] == "vps1"
        assert hb.telemetry["load_1m"] == 0.5

    def test_high_load_returns_degraded(self):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.OK,
            stdout=json.dumps(
                {
                    "hostname": "vps1",
                    "platform": "Linux",
                    "load_1m": 8.5,
                    "timestamp": 1234567890.0,
                }
            ),
            exit_code=0,
        )
        hb = collect_remote_heartbeat(_make_node(), transport)
        assert hb.status == HeartbeatStatus.DEGRADED

    def test_transport_failure_returns_unknown(self):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.UNREACHABLE, error="connection refused"
        )
        hb = collect_remote_heartbeat(_make_node(), transport)
        assert hb.status == HeartbeatStatus.UNKNOWN
        assert "error" in hb.metadata

    def test_transport_timeout_returns_degraded(self):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.TIMEOUT, error="timed out"
        )
        hb = collect_remote_heartbeat(_make_node(), transport)
        assert hb.status == HeartbeatStatus.DEGRADED

    def test_bad_json_returns_degraded(self):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.run_command.return_value = RemoteCommandResult(
            status=TransportStatus.OK, stdout="not json", exit_code=0
        )
        hb = collect_remote_heartbeat(_make_node(), transport)
        assert hb.status == HeartbeatStatus.DEGRADED
        assert "parse" in hb.metadata.get("error", "")

    def test_transport_exception_returns_unknown(self):
        transport = MagicMock(spec=SSHNodeTransport)
        transport.run_command.side_effect = RuntimeError("boom")
        hb = collect_remote_heartbeat(_make_node(), transport)
        assert hb.status == HeartbeatStatus.UNKNOWN
        assert "boom" in hb.metadata.get("error", "")


# ─── Failover/health compatibility tests ─────────────────────────────


class TestFailoverHealthCompatibility:
    def test_unreachable_remote_marked_offline(self):
        health = NodeHealthManager()
        health.mark_failure("vps1", "SSH unreachable")
        h = health.get_health("vps1")
        assert h.state == NodeHealthState.OFFLINE

    def test_healthy_remote_routed_when_local_down(self):
        from umh.nodes.heartbeat import HeartbeatMonitor

        health = NodeHealthManager()
        health.mark_failure("local1", "down")
        health.update_from_heartbeat(
            NodeHeartbeat(
                node_id="vps1",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=HeartbeatStatus.OK,
            )
        )
        router = FailoverRouter(health_manager=health)
        local = DeviceNode(node_id="local1", device_type=DeviceType.LOCAL)
        vps = DeviceNode(node_id="vps1", device_type=DeviceType.VPS)
        chosen = router.choose_initial_node([local, vps])
        assert chosen is not None
        assert chosen.node_id == "vps1"


# ─── Boundary tests ─────────────────────────────────────────────────


class TestBoundaryInvariants:
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

    def test_transport_does_not_import_cells(self):
        import importlib
        import inspect

        for name in ["umh.nodes.transport", "umh.nodes.ssh_transport"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.cells" not in src, f"{name} imports cells"
            assert "import umh.cells" not in src, f"{name} imports cells"

    def test_transport_does_not_import_adapters(self):
        import importlib
        import inspect

        for name in ["umh.nodes.transport", "umh.nodes.ssh_transport"]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.adapters" not in src, f"{name} imports adapters"

    def test_no_shell_true_in_nodes(self):
        import ast
        import importlib
        import inspect

        for name in [
            "umh.nodes.transport",
            "umh.nodes.ssh_transport",
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
            "umh.nodes.registry",
            "umh.nodes.routing",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "shell":
                    if isinstance(node.value, ast.Constant) and node.value.value is True:
                        raise AssertionError(f"{name} passes shell=True in code")

    def test_subprocess_only_in_approved_files(self):
        import importlib
        import inspect

        allowed = {"umh.environments.containers", "umh.nodes.ssh_transport"}
        checked = [
            "umh.nodes.transport",
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
            "umh.nodes.registry",
            "umh.nodes.routing",
            "umh.runtime.loop",
            "umh.runtime.advisor",
        ]
        for name in checked:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "import subprocess" not in src, (
                f"{name} imports subprocess (not in allowed list)"
            )

    def test_ssh_transport_uses_subprocess(self):
        import importlib
        import inspect

        mod = importlib.import_module("umh.nodes.ssh_transport")
        src = inspect.getsource(mod)
        assert "import subprocess" in src

    def test_nodes_do_not_import_runtime(self):
        import importlib
        import inspect

        for name in [
            "umh.nodes.transport",
            "umh.nodes.ssh_transport",
            "umh.nodes.heartbeat",
            "umh.nodes.health",
            "umh.nodes.remote",
            "umh.nodes.failover",
        ]:
            mod = importlib.import_module(name)
            src = inspect.getsource(mod)
            assert "from umh.runtime" not in src, f"{name} imports runtime"
            assert "import umh.runtime" not in src, f"{name} imports runtime"


# ─── Regression / import tests ───────────────────────────────────────


class TestPhase14Regression:
    def test_import_phase14_transport(self):
        from umh.nodes import SSHNodeTransport, TransportBackedRemoteNodeClient

        assert SSHNodeTransport is not None
        assert TransportBackedRemoteNodeClient is not None

    def test_import_transport_models(self):
        from umh.nodes import (
            NodeTransport,
            RemoteCommand,
            RemoteCommandResult,
            TransportStatus,
        )

        assert TransportStatus.OK.value == "ok"

    def test_import_collect_remote_heartbeat(self):
        from umh.nodes import collect_remote_heartbeat

        assert callable(collect_remote_heartbeat)

    def test_phase13_types_still_importable(self):
        from umh.nodes import (
            FailoverPolicy,
            FailoverRouter,
            HeartbeatMonitor,
            MockRemoteNodeClient,
            NodeHealthManager,
        )

        assert FailoverRouter is not None
