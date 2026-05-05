"""Remote node execution abstraction — interface boundary for distributed execution.

Defines the protocol for submitting work to remote nodes and tracking
results. Includes MockRemoteNodeClient (testing) and
TransportBackedRemoteNodeClient (real SSH/transport execution).

No imports from umh/cells, umh/adapters, subprocess, or shell.
Transport calls are delegated to NodeTransport implementations.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Protocol, runtime_checkable

from umh.core.clock import iso_now as _iso_now
from umh.nodes.registry import DeviceNode

_log = logging.getLogger(__name__)


@unique
class RemoteExecutionStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNREACHABLE = "unreachable"
    CANCELLED = "cancelled"


@dataclass
class RemoteExecutionRecord:
    """Tracks a single remote execution attempt."""

    task_id: str
    node_id: str
    status: RemoteExecutionStatus = RemoteExecutionStatus.ACCEPTED
    submitted_at: str = ""
    updated_at: str = ""
    result: dict[str, Any] | None = None
    error: str = ""

    def __post_init__(self):
        now = _iso_now()
        if not self.submitted_at:
            self.submitted_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "submitted_at": self.submitted_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
        }


@runtime_checkable
class RemoteNodeClient(Protocol):
    """Protocol for remote node communication."""

    def ping(self, node: DeviceNode) -> bool: ...

    def submit_execution(self, node: DeviceNode, task: dict[str, Any]) -> RemoteExecutionRecord: ...

    def fetch_result(self, node: DeviceNode, task_id: str) -> RemoteExecutionRecord | None: ...

    def cancel(self, node: DeviceNode, task_id: str) -> bool: ...


class MockRemoteNodeClient:
    """Mock implementation for testing. No real network calls."""

    def __init__(self, *, reachable: bool = True) -> None:
        self._lock = threading.Lock()
        self._reachable = reachable
        self._records: dict[str, RemoteExecutionRecord] = {}

    @property
    def reachable(self) -> bool:
        return self._reachable

    def set_reachable(self, reachable: bool) -> None:
        self._reachable = reachable

    def ping(self, node: DeviceNode) -> bool:
        return self._reachable

    def submit_execution(self, node: DeviceNode, task: dict[str, Any]) -> RemoteExecutionRecord:
        if not self._reachable:
            record = RemoteExecutionRecord(
                task_id=task.get("task_id", "unknown"),
                node_id=node.node_id,
                status=RemoteExecutionStatus.UNREACHABLE,
                error="node unreachable",
            )
            return record

        record = RemoteExecutionRecord(
            task_id=task.get("task_id", "unknown"),
            node_id=node.node_id,
            status=RemoteExecutionStatus.ACCEPTED,
        )
        with self._lock:
            self._records[record.task_id] = record
        return record

    def fetch_result(self, node: DeviceNode, task_id: str) -> RemoteExecutionRecord | None:
        if not self._reachable:
            return RemoteExecutionRecord(
                task_id=task_id,
                node_id=node.node_id,
                status=RemoteExecutionStatus.UNREACHABLE,
                error="node unreachable",
            )
        with self._lock:
            return self._records.get(task_id)

    def cancel(self, node: DeviceNode, task_id: str) -> bool:
        if not self._reachable:
            return False
        with self._lock:
            record = self._records.get(task_id)
            if record is None:
                return False
            record.status = RemoteExecutionStatus.CANCELLED
            record.updated_at = _iso_now()
            return True

    def complete_task(self, task_id: str, result: dict[str, Any] | None = None) -> bool:
        """Test helper: mark a submitted task as succeeded."""
        with self._lock:
            record = self._records.get(task_id)
            if record is None:
                return False
            record.status = RemoteExecutionStatus.SUCCEEDED
            record.result = result or {}
            record.updated_at = _iso_now()
            return True

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


class TransportBackedRemoteNodeClient:
    """Remote client backed by a real NodeTransport (SSH, etc).

    Phase 14: synchronous remote execution. Commands execute over
    the transport and return immediately. No async job queue.
    """

    def __init__(self, transport: Any) -> None:
        from umh.nodes.transport import NodeTransport

        if not isinstance(transport, NodeTransport):
            raise TypeError(f"transport must implement NodeTransport, got {type(transport)}")
        self._transport = transport
        self._lock = threading.Lock()
        self._records: dict[str, RemoteExecutionRecord] = {}

    def ping(self, node: DeviceNode) -> bool:
        from umh.nodes.transport import TransportStatus

        status = self._transport.ping(node)
        return status == TransportStatus.OK

    def submit_execution(self, node: DeviceNode, task: dict[str, Any]) -> RemoteExecutionRecord:
        from umh.nodes.transport import RemoteCommand, TransportStatus

        command_list = task.get("command")
        if not command_list or not isinstance(command_list, (list, tuple)):
            return RemoteExecutionRecord(
                task_id=task.get("task_id", "unknown"),
                node_id=node.node_id,
                status=RemoteExecutionStatus.FAILED,
                error="no valid command provided in task",
            )

        cmd = RemoteCommand(
            command=tuple(str(c) for c in command_list),
            cwd=task.get("cwd", ""),
            timeout_seconds=task.get("timeout_seconds", 30),
        )

        result = self._transport.run_command(node, cmd)

        if result.status == TransportStatus.OK:
            record = RemoteExecutionRecord(
                task_id=task.get("task_id", "unknown"),
                node_id=node.node_id,
                status=RemoteExecutionStatus.SUCCEEDED,
                result={"stdout": result.stdout, "stderr": result.stderr, "exit_code": 0},
            )
        elif result.status == TransportStatus.TIMEOUT:
            record = RemoteExecutionRecord(
                task_id=task.get("task_id", "unknown"),
                node_id=node.node_id,
                status=RemoteExecutionStatus.FAILED,
                error=result.error or "timeout",
            )
        elif result.status == TransportStatus.UNREACHABLE:
            record = RemoteExecutionRecord(
                task_id=task.get("task_id", "unknown"),
                node_id=node.node_id,
                status=RemoteExecutionStatus.UNREACHABLE,
                error=result.error or "node unreachable",
            )
        else:
            record = RemoteExecutionRecord(
                task_id=task.get("task_id", "unknown"),
                node_id=node.node_id,
                status=RemoteExecutionStatus.FAILED,
                error=result.error or f"transport status: {result.status.value}",
                result={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                },
            )

        with self._lock:
            self._records[record.task_id] = record
        return record

    def fetch_result(self, node: DeviceNode, task_id: str) -> RemoteExecutionRecord | None:
        with self._lock:
            return self._records.get(task_id)

    def cancel(self, node: DeviceNode, task_id: str) -> bool:
        with self._lock:
            record = self._records.get(task_id)
            if record is None:
                return False
            record.status = RemoteExecutionStatus.CANCELLED
            record.updated_at = _iso_now()
            return True

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


def collect_remote_heartbeat(node: DeviceNode, transport: Any) -> "NodeHeartbeat":
    """Collect a heartbeat from a remote node over transport.

    Runs a lightweight Python command on the remote node to gather
    hostname, platform, and load average. Returns a NodeHeartbeat
    with status OK on success or DEGRADED/UNKNOWN on failure.
    """
    from umh.nodes.heartbeat import HeartbeatStatus, NodeHeartbeat
    from umh.nodes.transport import RemoteCommand, TransportStatus

    probe_script = (
        "import json, os, platform, time; "
        "load = os.getloadavg() if hasattr(os, 'getloadavg') else (0,0,0); "
        "print(json.dumps({"
        "'hostname': platform.node(), "
        "'platform': platform.system(), "
        "'load_1m': load[0], "
        "'timestamp': time.time()"
        "}))"
    )

    cmd = RemoteCommand(
        command=("python3", "-c", probe_script),
        timeout_seconds=15,
    )

    try:
        result = transport.run_command(node, cmd)
    except Exception as e:
        return NodeHeartbeat(
            node_id=node.node_id,
            timestamp=_iso_now(),
            status=HeartbeatStatus.UNKNOWN,
            metadata={"error": str(e), "source": "remote_heartbeat"},
        )

    if result.status != TransportStatus.OK:
        return NodeHeartbeat(
            node_id=node.node_id,
            timestamp=_iso_now(),
            status=HeartbeatStatus.DEGRADED
            if result.status == TransportStatus.TIMEOUT
            else HeartbeatStatus.UNKNOWN,
            metadata={
                "error": result.error or result.status.value,
                "source": "remote_heartbeat",
            },
        )

    try:
        data = json.loads(result.stdout.strip())
        load_1m = float(data.get("load_1m", 0))
        status = HeartbeatStatus.DEGRADED if load_1m > 4.0 else HeartbeatStatus.OK
        return NodeHeartbeat(
            node_id=node.node_id,
            timestamp=_iso_now(),
            status=status,
            telemetry={
                "load_1m": load_1m,
                "hostname": data.get("hostname", ""),
                "platform": data.get("platform", ""),
            },
            metadata={"source": "remote_heartbeat"},
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return NodeHeartbeat(
            node_id=node.node_id,
            timestamp=_iso_now(),
            status=HeartbeatStatus.DEGRADED,
            metadata={
                "error": f"failed to parse remote output: {e}",
                "raw_stdout": result.stdout[:200],
                "source": "remote_heartbeat",
            },
        )
