"""SSH transport — real remote command execution via system SSH binary.

Uses subprocess.run with list args. No shell=True. No manual quoting.
All subprocess usage is confined to this module.

SSH command structure:
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new
      -o ConnectTimeout=<seconds> -p <port> -i <identity_file>
      user@host -- <command args>

No imports from umh/cells, umh/adapters, or umh/environments.
"""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

from umh.core.clock import iso_now as _iso_now, now_ms
from umh.nodes.registry import DeviceNode
from umh.nodes.transport import (
    NodeTransport,
    RemoteCommand,
    RemoteCommandResult,
    TransportStatus,
)

_log = logging.getLogger(__name__)

_DEFAULT_CONNECT_TIMEOUT = 10
_DEFAULT_PORT = 22


class SSHNodeTransport:
    """SSH-based transport using system ssh binary. No shell=True."""

    def __init__(
        self,
        *,
        connect_timeout: int = _DEFAULT_CONNECT_TIMEOUT,
        default_port: int = _DEFAULT_PORT,
    ) -> None:
        self._connect_timeout = connect_timeout
        self._default_port = default_port

    def ping(self, node: DeviceNode) -> TransportStatus:
        host, user, port, identity = self._extract_ssh_params(node)
        if not host or not user:
            return TransportStatus.AUTH_FAILED

        cmd = self._build_ssh_args(host, user, port, identity) + ["--", "echo", "pong"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._connect_timeout,
            )
            if result.returncode == 0:
                return TransportStatus.OK
            if result.returncode == 255:
                if "permission denied" in result.stderr.lower():
                    return TransportStatus.AUTH_FAILED
                return TransportStatus.UNREACHABLE
            return TransportStatus.FAILED
        except subprocess.TimeoutExpired:
            return TransportStatus.TIMEOUT
        except FileNotFoundError:
            _log.error("ssh binary not found")
            return TransportStatus.FAILED
        except Exception as e:
            _log.error("SSH ping error: %s", e)
            return TransportStatus.FAILED

    def run_command(self, node: DeviceNode, command: RemoteCommand) -> RemoteCommandResult:
        host, user, port, identity = self._extract_ssh_params(node)
        if not host or not user:
            return RemoteCommandResult(
                status=TransportStatus.AUTH_FAILED,
                error="missing host or user in node metadata",
            )

        ssh_args = self._build_ssh_args(host, user, port, identity)
        full_cmd = ssh_args + ["--"] + list(command.command)

        started_at = _iso_now()
        start_ms = now_ms()

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=command.timeout_seconds,
            )
            finished_at = _iso_now()
            duration_ms = now_ms() - start_ms

            if result.returncode == 0:
                return RemoteCommandResult(
                    status=TransportStatus.OK,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=0,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                )

            status = TransportStatus.FAILED
            if result.returncode == 255:
                if "permission denied" in result.stderr.lower():
                    status = TransportStatus.AUTH_FAILED
                else:
                    status = TransportStatus.UNREACHABLE

            return RemoteCommandResult(
                status=status,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                error=result.stderr.strip()[:500] if result.stderr else "",
            )

        except subprocess.TimeoutExpired:
            return RemoteCommandResult(
                status=TransportStatus.TIMEOUT,
                started_at=started_at,
                finished_at=_iso_now(),
                duration_ms=now_ms() - start_ms,
                error=f"command timed out after {command.timeout_seconds}s",
            )
        except FileNotFoundError:
            return RemoteCommandResult(
                status=TransportStatus.FAILED,
                started_at=started_at,
                finished_at=_iso_now(),
                duration_ms=now_ms() - start_ms,
                error="ssh binary not found on system",
            )
        except Exception as e:
            return RemoteCommandResult(
                status=TransportStatus.FAILED,
                started_at=started_at,
                finished_at=_iso_now(),
                duration_ms=now_ms() - start_ms,
                error=str(e),
            )

    def close(self, node: DeviceNode) -> None:
        pass

    def _extract_ssh_params(self, node: DeviceNode) -> tuple[str, str, int, str]:
        meta = node.metadata
        host = meta.get("host", "")
        user = meta.get("user", "")
        port = meta.get("port", self._default_port)
        identity = meta.get("identity_file", "")
        return host, user, port, identity

    def _build_ssh_args(self, host: str, user: str, port: int, identity_file: str) -> list[str]:
        args = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"ConnectTimeout={self._connect_timeout}",
            "-p",
            str(port),
        ]
        if identity_file:
            args.extend(["-i", identity_file])
        args.append(f"{user}@{host}")
        return args
