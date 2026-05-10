"""Transport abstraction — interface for remote node communication.

Defines the protocol, command model, and result model for executing
commands on remote nodes. Implementations live in separate modules
(ssh_transport.py, etc).

No imports from umh/cells, umh/adapters, subprocess, or shell.
No I/O in this module — pure data models and protocol definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Protocol, runtime_checkable

from umh.core.clock import iso_now as _iso_now
from umh.nodes.registry import DeviceNode


@unique
class TransportStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    AUTH_FAILED = "auth_failed"


@dataclass(frozen=True)
class RemoteCommand:
    """Command to execute on a remote node. command must be list[str]."""

    command: tuple[str, ...]
    cwd: str = ""
    env: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.command:
            raise ValueError("command must be a non-empty sequence of strings")

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": list(self.command),
            "cwd": self.cwd,
            "env": self.env,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }


@dataclass
class RemoteCommandResult:
    """Result of executing a command on a remote node."""

    status: TransportStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.started_at:
            self.started_at = _iso_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata,
        }


@runtime_checkable
class NodeTransport(Protocol):
    """Protocol for remote node transport implementations."""

    def ping(self, node: DeviceNode) -> TransportStatus: ...

    def run_command(self, node: DeviceNode, command: RemoteCommand) -> RemoteCommandResult: ...

    def close(self, node: DeviceNode) -> None: ...
