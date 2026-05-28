"""Relay Execution Transport v1.

VPS-side transport layer that sends execution packets to the Windows
workstation relay via Tailscale SSH and polls for real results.

Transport chain:
  VPS SSH → Windows OpenSSH → wsl -e bash → shared filesystem
  → Windows relay reads inbox → executes → writes outbox
  → VPS polls outbox via SSH → reads result

UMH substrate subsystem.
"""

from __future__ import annotations

import os
import json
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SSH_HOST = os.getenv("EOS_LOCAL_BRIDGE_IP", "")
SSH_USER = os.getenv("EOS_LOCAL_BRIDGE_USER", "")
SSH_KEY = "/root/.ssh/id_ed25519"
SSH_TIMEOUT = 8

RELAY_DIR_WSL = "~/eos_advisor_messages/windows_desktop_relay"
RELAY_INBOX_WSL = f"{RELAY_DIR_WSL}/inbox"
RELAY_OUTBOX_WSL = f"{RELAY_DIR_WSL}/outbox"

TRANSPORT_TIMEOUT_SECONDS = 120
TRANSPORT_POLL_INTERVAL = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [relay-transport] {msg}", flush=True)


def _ssh_cmd(remote_command: str, timeout: int = SSH_TIMEOUT) -> str:
    return (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout={timeout} -o StrictHostKeyChecking=no "
        f"'{SSH_USER}'@{SSH_HOST} "
        f"'wsl -e bash -c \"{remote_command}\"'"
    )


def _run_ssh(remote_command: str, timeout: int = 30) -> tuple[bool, str, str]:
    cmd = _ssh_cmd(remote_command, timeout=SSH_TIMEOUT)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "SSH timeout"
    except OSError as e:
        return False, "", str(e)


@dataclass
class RelayTransportResult:
    """Result of a VPS → Windows relay transport round-trip."""

    status: str = "pending"
    request_id: str = ""
    relay_result: dict[str, Any] = field(default_factory=dict)
    transport_error: str = ""
    ssh_reachable: bool = False
    inbox_written: bool = False
    result_received: bool = False
    elapsed_seconds: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "request_id": self.request_id,
            "relay_result": self.relay_result,
            "transport_error": self.transport_error,
            "ssh_reachable": self.ssh_reachable,
            "inbox_written": self.inbox_written,
            "result_received": self.result_received,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "timestamp": self.timestamp,
        }


def check_ssh_reachable() -> tuple[bool, str]:
    ok, out, err = _run_ssh("echo SSH_OK", timeout=15)
    if ok and "SSH_OK" in out:
        return True, "ssh_ok"
    return False, err or "no_response"


def check_relay_inbox_exists() -> tuple[bool, str]:
    ok, out, err = _run_ssh(f"test -d {RELAY_INBOX_WSL} && echo EXISTS", timeout=15)
    if ok and "EXISTS" in out:
        return True, "inbox_exists"
    return False, err or "inbox_not_found"


def write_request_to_relay(
    request: dict[str, Any],
) -> tuple[bool, str]:
    request_id = request.get("request_id", f"REQ-{uuid.uuid4().hex[:8]}")
    filename = f"{request_id}.json"

    request_json = json.dumps(request, indent=2, default=str)
    escaped = (
        request_json.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
    )

    remote_cmd = (
        f'mkdir -p {RELAY_INBOX_WSL} && echo \\"{escaped}\\" > {RELAY_INBOX_WSL}/{filename}'
    )
    ok, out, err = _run_ssh(remote_cmd, timeout=20)

    if ok:
        _log(f"request written to relay inbox: {filename}")
        return True, request_id
    _log(f"failed to write request: {err}")
    return False, err


def write_request_via_scp(
    request: dict[str, Any],
    local_tmp: Path = Path("/tmp"),
) -> tuple[bool, str]:
    request_id = request.get("request_id", f"REQ-{uuid.uuid4().hex[:8]}")
    filename = f"{request_id}.json"
    local_path = local_tmp / filename

    local_path.write_text(json.dumps(request, indent=2, default=str))

    scp_cmd = (
        f"scp -i {SSH_KEY} -o IdentitiesOnly=yes -o BatchMode=yes "
        f"-o ConnectTimeout={SSH_TIMEOUT} -o StrictHostKeyChecking=no "
        f"{local_path} "
        f"'{SSH_USER}'@{SSH_HOST}:eos_advisor_messages/windows_desktop_relay/inbox/{filename}"
    )
    try:
        result = subprocess.run(
            scp_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        local_path.unlink(missing_ok=True)
        if result.returncode == 0:
            _log(f"scp wrote request to relay inbox: {filename}")
            return True, request_id
        _log(f"scp failed: {result.stderr.strip()}")
        return False, result.stderr.strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        local_path.unlink(missing_ok=True)
        return False, str(e)


def poll_relay_result(
    request_id: str,
    timeout_seconds: int = TRANSPORT_TIMEOUT_SECONDS,
    poll_interval: int = TRANSPORT_POLL_INTERVAL,
) -> dict[str, Any] | None:
    import time

    result_filename = f"{request_id}_result.json"
    result_path = f"{RELAY_OUTBOX_WSL}/{result_filename}"
    deadline = time.time() + timeout_seconds
    poll_count = 0

    _log(f"polling relay outbox for {result_filename} (timeout={timeout_seconds}s)")

    while time.time() < deadline:
        ok, out, err = _run_ssh(
            f"test -f {result_path} && cat {result_path}",
            timeout=15,
        )
        if ok and out:
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                _log(f"result file exists but not valid JSON yet")

        poll_count += 1
        if poll_count % 5 == 0:
            _log(f"  polling... ({poll_count * poll_interval}s elapsed)")
        time.sleep(poll_interval)

    _log(f"timeout after {timeout_seconds}s — no result received")
    return None


def send_and_wait(
    request: dict[str, Any],
    timeout_seconds: int = TRANSPORT_TIMEOUT_SECONDS,
) -> RelayTransportResult:
    import time

    start = time.time()
    result = RelayTransportResult(request_id=request.get("request_id", ""))

    ssh_ok, ssh_reason = check_ssh_reachable()
    result.ssh_reachable = ssh_ok
    if not ssh_ok:
        result.status = "ssh_unreachable"
        result.transport_error = f"SSH failed: {ssh_reason}"
        result.elapsed_seconds = time.time() - start
        _log(f"transport failed: SSH unreachable ({ssh_reason})")
        return result

    written, write_info = write_request_via_scp(request)
    result.inbox_written = written
    if not written:
        result.status = "write_failed"
        result.transport_error = f"inbox write failed: {write_info}"
        result.elapsed_seconds = time.time() - start
        _log(f"transport failed: could not write to inbox ({write_info})")
        return result

    request_id = request.get("request_id", write_info)
    result.request_id = request_id

    relay_result = poll_relay_result(
        request_id,
        timeout_seconds=timeout_seconds,
    )
    result.elapsed_seconds = time.time() - start

    if relay_result is None:
        result.status = "timeout"
        result.transport_error = f"no result within {timeout_seconds}s"
        _log(f"transport timeout: relay did not respond in {timeout_seconds}s")
        return result

    result.status = "completed"
    result.relay_result = relay_result
    result.result_received = True
    _log(
        f"transport completed: adapter_status={relay_result.get('adapter_status')} "
        f"elapsed={result.elapsed_seconds:.1f}s"
    )
    return result


def send_chrome_proof_request(
    url: str = "https://www.google.com",
    timeout_seconds: int = TRANSPORT_TIMEOUT_SECONDS,
) -> RelayTransportResult:
    from execution.environments.windows_desktop_request_builder import (
        build_w0_chrome_proof_request,
    )

    request = build_w0_chrome_proof_request(url=url)
    _log(f"sending chrome_proof request: {request.request_id}")
    return send_and_wait(request.to_dict(), timeout_seconds=timeout_seconds)


def send_ping_request(
    timeout_seconds: int = 30,
) -> RelayTransportResult:
    from execution.environments.windows_desktop_request_builder import (
        build_ping_request,
    )

    request = build_ping_request()
    _log(f"sending ping request: {request.request_id}")
    return send_and_wait(request.to_dict(), timeout_seconds=timeout_seconds)
