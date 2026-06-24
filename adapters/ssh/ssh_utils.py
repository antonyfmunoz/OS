"""Centralized SSH/SCP utility — single entry point for all remote commands.

All functions use gated_subprocess_run (CPU Gate Law compliant).
StrictHostKeyChecking=accept-new to auto-accept new hosts without prompting.

UMH adapters layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

_SSH_OPTS = [
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "ConnectTimeout=10",
    "-o", "BatchMode=yes",
]


def ssh_run(
    host: str,
    command: str,
    *,
    timeout: int = 30,
    user: str = "root",
) -> tuple[bool, str]:
    """Run command on remote host via SSH.

    Returns (success, stdout_or_error).
    """
    cmd = [
        "ssh",
        *_SSH_OPTS,
        "-o", f"ConnectTimeout={min(timeout, 10)}",
        f"{user}@{host}",
        command,
    ]
    result = gated_subprocess_run(
        cmd,
        caller="ssh_utils.ssh_run",
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result is None:
        return False, "CPU gate blocked SSH command"
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, (result.stderr or result.stdout or "").strip()


def ssh_reachable(host: str, *, timeout: int = 10, user: str = "root") -> bool:
    """Quick connectivity check. Returns True if SSH handshake succeeds."""
    cmd = [
        "ssh",
        *_SSH_OPTS,
        "-o", f"ConnectTimeout={timeout}",
        f"{user}@{host}",
        "echo ok",
    ]
    result = gated_subprocess_run(
        cmd,
        caller="ssh_utils.ssh_reachable",
        capture_output=True,
        text=True,
        timeout=timeout + 5,
    )
    if result is None:
        return False
    return result.returncode == 0


def scp_to(
    host: str,
    local_path: str,
    remote_path: str,
    *,
    user: str = "root",
    timeout: int = 60,
) -> bool:
    """Copy file to remote host via scp. Returns success."""
    cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        local_path,
        f"{user}@{host}:{remote_path}",
    ]
    result = gated_subprocess_run(
        cmd,
        caller="ssh_utils.scp_to",
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result is None:
        return False
    if result.returncode != 0:
        logger.debug("scp_to failed: %s", result.stderr)
    return result.returncode == 0


def scp_dir_to(
    host: str,
    local_dir: str,
    remote_dir: str,
    *,
    user: str = "root",
    timeout: int = 120,
) -> bool:
    """Copy directory tree to remote host via scp -r. Returns success."""
    cmd = [
        "scp",
        "-r",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        local_dir,
        f"{user}@{host}:{remote_dir}",
    ]
    result = gated_subprocess_run(
        cmd,
        caller="ssh_utils.scp_dir_to",
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result is None:
        return False
    if result.returncode != 0:
        logger.debug("scp_dir_to failed: %s", result.stderr)
    return result.returncode == 0
