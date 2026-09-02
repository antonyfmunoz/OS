"""WebSocket client — connects to the VPS node mesh server.

Handles the full lifecycle: connect → hello → heartbeat loop →
capability execution → signal emission → reconnect on failure.

Architecture: CONTROL PLANE and MEDIA PLANE are hard-separated.
- Control plane (heartbeats, capability dispatch) runs on the main
  asyncio event loop and is NEVER blocked by frame emission.
- Media plane (frame emission) uses a bounded async queue with
  drop-oldest backpressure. A dedicated drain task sends frames
  without blocking the control loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import hashlib
import json
import logging
import os
import platform
import re
import signal
import socket
import subprocess
import struct
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import websockets
import aiohttp

from nodes.windows.umh_node.adapters.broadcast import BroadcastAdapter
from nodes.windows.umh_node.adapters.camera import CameraAdapter
from nodes.windows.umh_node.adapters.clipboard import ClipboardAdapter
from nodes.windows.umh_node.adapters.desktop import DesktopAdapter
from nodes.windows.umh_node.adapters.desktop_stream import DesktopStreamAdapter
from nodes.windows.umh_node.adapters.filesystem import FilesystemAdapter
from nodes.windows.umh_node.adapters.hermes import HermesAdapter
from nodes.windows.umh_node.adapters.shell import ShellAdapter
from nodes.windows.umh_node.config import CapabilityConfig, NodeConfig
from nodes.windows.umh_node.governance import validate_request
from nodes.windows.umh_node.metrics import collect_metrics
from nodes.windows.umh_node.peripheral_scanner import scan_all_peripherals, get_scan_age_s
from nodes.windows.umh_node.workspace import collect_workstation_state, _state_hash
from substrate.execution.durable_remote_transport import (
    DurableRemoteRequest,
    DurableRemoteStore,
    SHELL_LAUNCH_IN_PROGRESS,
    SHELL_LAUNCH_INTENT_PERSISTED,
    SHELL_LAUNCH_RUNNING,
    SHELL_PROCESS_IDENTITY_PERSISTED,
    STATE_ORDER,
    TERMINAL_STATES,
    default_node_root,
    durable_execution_identity,
    sha256_json,
)

logger = logging.getLogger(__name__)

_MEDIA_QUEUE_MAX = 4
_BULK_MEDIA_MAX_FRAME_BYTES = 1024 * 1024
_TRAFFIC_AUTHORITY_CONTROL = "AUTHORITY_CONTROL"
_TRAFFIC_REQUIRED_CONTROL = "REQUIRED_CONTROL"
_TRAFFIC_ORDINARY = "ORDINARY"
_TRAFFIC_BULK_MEDIA = "BULK_MEDIA"
_TRAFFIC_CLASSES = (
    _TRAFFIC_AUTHORITY_CONTROL,
    _TRAFFIC_REQUIRED_CONTROL,
    _TRAFFIC_ORDINARY,
    _TRAFFIC_BULK_MEDIA,
)
_AUTHORITY_SEND_BURST_LIMIT = 8
_WS_SEND_DEADLINE_S = 2.0
_WS_SEND_ABORT_GRACE_S = 0.25
_AUTHORITY_SCHEDULER_OVERHEAD_BOUND_S = 0.25
_WS_SEND_QUEUE_CAPACITY = {
    _TRAFFIC_AUTHORITY_CONTROL: 8,
    _TRAFFIC_REQUIRED_CONTROL: 16,
    _TRAFFIC_ORDINARY: 32,
    _TRAFFIC_BULK_MEDIA: 4,
}
_WS_SEND_PAYLOAD_MAX_BYTES = {
    _TRAFFIC_AUTHORITY_CONTROL: 256 * 1024,
    _TRAFFIC_REQUIRED_CONTROL: 256 * 1024,
    _TRAFFIC_ORDINARY: 256 * 1024,
    _TRAFFIC_BULK_MEDIA: _BULK_MEDIA_MAX_FRAME_BYTES,
}
_WS_SEND_QUEUE_MAX_BYTES = {
    traffic_class: _WS_SEND_QUEUE_CAPACITY[traffic_class]
    * _WS_SEND_PAYLOAD_MAX_BYTES[traffic_class]
    for traffic_class in _TRAFFIC_CLASSES
}
_AUTHORITY_LOWER_CLASS_INTERLEAVES_MAX = (
    _WS_SEND_QUEUE_CAPACITY[_TRAFFIC_AUTHORITY_CONTROL] + _AUTHORITY_SEND_BURST_LIMIT - 1
) // _AUTHORITY_SEND_BURST_LIMIT
# Last accepted authority work may wait for one in-flight frame, seven earlier
# authority frames, and at most one lower-class fairness interleave. Each send
# either completes or invalidates the transport within _WS_SEND_DEADLINE_S.
_AUTHORITY_SERVICE_START_BOUND_S = (
    _WS_SEND_QUEUE_CAPACITY[_TRAFFIC_AUTHORITY_CONTROL] + _AUTHORITY_LOWER_CLASS_INTERLEAVES_MAX
) * _WS_SEND_DEADLINE_S + _AUTHORITY_SCHEDULER_OVERHEAD_BOUND_S
_AUTHORITY_SERVICE_COMPLETE_BOUND_S = _AUTHORITY_SERVICE_START_BOUND_S + _WS_SEND_DEADLINE_S
_AUTHORITY_QUEUE_MAX_WAIT_S = _AUTHORITY_SERVICE_START_BOUND_S
_CONTROL_TIMEOUT_S = 8.0
_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S = 30.0
_CLAIM_AUTHORITY_ENVELOPE_S = _AUTHORITY_SERVICE_COMPLETE_BOUND_S + _CONTROL_TIMEOUT_S
assert _CLAIM_AUTHORITY_ENVELOPE_S < _DURABLE_CLAIM_ACQUIRE_TIMEOUT_S
_DURABLE_CLAIM_RETRY_SLEEP_S = 1.0
_CONNECTION_GENERATION_TEARDOWN_S = 2.0


_SUSPEND_STATE_UNKNOWN = "UNKNOWN"
_SUSPEND_STATE_PROVEN_SUSPENDED = "PROVEN_SUSPENDED"
_SUSPEND_STATE_PROVEN_RESUMED = "PROVEN_RESUMED"
_SUSPEND_STATE_PROVEN_EXITED = "PROVEN_EXITED"
_SUSPEND_STATES = frozenset(
    {
        _SUSPEND_STATE_UNKNOWN,
        _SUSPEND_STATE_PROVEN_SUSPENDED,
        _SUSPEND_STATE_PROVEN_RESUMED,
        _SUSPEND_STATE_PROVEN_EXITED,
    }
)
_RESUME_RESULT_NOT_ATTEMPTED = "NOT_ATTEMPTED"
_RESUME_RESULT_EXPECTED = "EXPECTED"
_RESUME_RESULT_UNEXPECTED = "UNEXPECTED"
_RESUME_RESULT_FAILURE = "FAILURE"
_RESUME_RESULTS = frozenset(
    {
        _RESUME_RESULT_NOT_ATTEMPTED,
        _RESUME_RESULT_EXPECTED,
        _RESUME_RESULT_UNEXPECTED,
        _RESUME_RESULT_FAILURE,
    }
)


@dataclass(frozen=True)
class _SuspendStateEvidence:
    state: str
    process_id: int
    thread_id: int | None
    observation_method: str
    observation_success: bool
    win32_error: int | None
    observed_at: float
    launch_intent_id: str
    logical_execution_id: str
    previous_suspend_count: int | None = None
    resume_result: str = _RESUME_RESULT_NOT_ATTEMPTED

    def __post_init__(self) -> None:
        if self.state not in _SUSPEND_STATES:
            raise ValueError(f"invalid suspend state: {self.state}")
        if self.resume_result not in _RESUME_RESULTS:
            raise ValueError(f"invalid resume result: {self.resume_result}")
        if not self.observation_success and self.state != _SUSPEND_STATE_UNKNOWN:
            raise ValueError("failed observation cannot prove a suspend state")
        if self.process_id <= 0:
            raise ValueError("suspend evidence requires a positive process id")
        if not self.launch_intent_id or not self.logical_execution_id:
            raise ValueError("suspend evidence requires exact launch and execution identity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "observation_method": self.observation_method,
            "observation_success": self.observation_success,
            "win32_error": self.win32_error,
            "observed_at": self.observed_at,
            "launch_intent_id": self.launch_intent_id,
            "logical_execution_id": self.logical_execution_id,
            "previous_suspend_count": self.previous_suspend_count,
            "resume_result": self.resume_result,
        }


class _DurableResumeStateUncertain(RuntimeError):
    def __init__(self, message: str, *, evidence: _SuspendStateEvidence) -> None:
        super().__init__(message)
        self.evidence = evidence


_LOGICAL_EXECUTION_TEARDOWN_S = 2.0
_RESULT_REPLAY_IDLE_POLL_S = 1.0
_RESULT_REPLAY_BATCH = _WS_SEND_QUEUE_CAPACITY[_TRAFFIC_AUTHORITY_CONTROL]
_DURABLE_TRAJECTORY_TOMBSTONE_TTL_S = 300.0
_DURABLE_TRAJECTORY_MAX = 512
_DURABLE_CLAIM_PROOF_STATES = frozenset(
    {
        "CLAIMED",
        "RUNNING",
        "CANCEL_REQUESTED",
        "CANCELLED",
        "EXPIRED",
        "FAILED",
        "SUCCEEDED",
        "RECONCILIATION_REQUIRED",
    }
)
_DURABLE_TIMEOUT_STDOUT_LIMIT = 20000
_DURABLE_TIMEOUT_STDERR_LIMIT = 20000
_DURABLE_TIMEOUT_TOTAL_LIMIT = _DURABLE_TIMEOUT_STDOUT_LIMIT + _DURABLE_TIMEOUT_STDERR_LIMIT
_DURABLE_TIMEOUT_DRAIN_SECONDS = 1.0
_DURABLE_SECRET_SCAN_TAIL_CHARS = 64
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(secret(?:[_-]?key)?\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(credential\s*[:=]\s*)[^\s]+"),
    re.compile(r"op" + r"://[^\s\"')]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)
_SECRET_LINE_PATTERNS = (
    re.compile(r"(?i)authorization\s*:\s*bearer\s+"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*"),
    re.compile(r"(?i)token\s*[:=]\s*"),
    re.compile(r"(?i)password\s*[:=]\s*"),
    re.compile(r"(?i)secret(?:[_-]?key)?\s*[:=]\s*"),
    re.compile(r"(?i)credential\s*[:=]\s*"),
    re.compile(r"op" + r"://"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


class TransportQueueOverload(ConnectionError):
    """A bounded transport queue couldn't truthfully admit a frame."""


class TransportSendDeadlineExceeded(TimeoutError):
    """A send exceeded its finite service bound and invalidated the socket."""


class TransportGenerationTeardownFailed(ConnectionError):
    """A connection generation could not reach bounded task quiescence."""


_connection_generation_context: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "umh_connection_generation",
    default=None,
)


@dataclass(frozen=True)
class _WsSendEntry:
    seq: int
    payload: str | bytes
    future: asyncio.Future[dict[str, Any]]
    traffic_class: str
    payload_bytes: int
    queued_at: float
    generation: int


def _redact_durable_output(text: str) -> str:
    redacted: list[str] = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if any(
            marker in lowered
            for marker in (
                "authorization",
                "api_key",
                "apikey",
                "password",
                "secret",
                "credential",
                "op://",
            )
        ):
            redacted.append("[redacted credential-bearing line]")
            continue
        clean = line
        for pattern in _SECRET_PATTERNS:
            clean = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "[redacted]", clean)
        redacted.append(clean)
    return "\n".join(redacted)


def _tail_with_limit(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    marker = "\n[...durable output truncated...]\n"
    if limit <= len(marker):
        return text[:limit], True
    head_len = (limit - len(marker)) // 2
    tail_len = limit - len(marker) - head_len
    return f"{text[:head_len]}{marker}{text[-tail_len:]}", True


class _BoundedStreamBuffer:
    def __init__(self, limit: int) -> None:
        self._limit = max(0, int(limit))
        self._marker = b"\n[...durable output truncated...]\n"
        available = max(0, self._limit - len(self._marker))
        self._head_limit = available // 2
        self._tail_limit = available - self._head_limit
        self._head = b""
        self._tail = b""
        self.bytes_seen = 0
        self.truncated = False
        self.redacted = False
        self._pending_line = ""
        self._discarding_secret_line = False

    def _append_retained(self, text: str) -> None:
        if not text:
            return
        data = text.encode("utf-8", errors="replace")
        if self._limit <= 0:
            self.truncated = True
            return
        if not self.truncated:
            combined = self._head + data
            if len(combined) <= self._limit:
                self._head = combined
                return
            self.truncated = True
            self._head = combined[: self._head_limit]
            self._tail = combined[-self._tail_limit :] if self._tail_limit else b""
            return
        if self._tail_limit:
            self._tail = (self._tail + data)[-self._tail_limit :]

    def append(self, text: str) -> None:
        if not text:
            return
        self.bytes_seen += len(text.encode("utf-8", errors="replace"))
        self._pending_line += text
        lines = self._pending_line.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            self._pending_line = lines.pop()
        else:
            self._pending_line = ""
        for piece in lines:
            self._append_redacted_piece(piece)
        if len(self._pending_line) > _DURABLE_SECRET_SCAN_TAIL_CHARS:
            safe = self._pending_line[:-_DURABLE_SECRET_SCAN_TAIL_CHARS]
            self._pending_line = self._pending_line[-_DURABLE_SECRET_SCAN_TAIL_CHARS:]
            self._append_redacted_piece(safe)

    def finish(self) -> None:
        if self._pending_line:
            pending = self._pending_line
            self._pending_line = ""
            self._append_redacted_piece(pending)

    def _append_redacted_piece(self, piece: str) -> None:
        ends_line = piece.endswith(("\n", "\r"))
        if self._discarding_secret_line:
            if ends_line:
                self._discarding_secret_line = False
            return
        if any(pattern.search(piece) for pattern in _SECRET_LINE_PATTERNS) or any(
            pattern.search(piece) for pattern in _SECRET_PATTERNS
        ):
            self.redacted = True
            self._append_retained("[redacted credential-bearing line]\n")
            self._discarding_secret_line = not ends_line
            return
        self._append_retained(piece)

    def text(self) -> str:
        self.finish()
        if not self.truncated:
            return self._head.decode("utf-8", errors="ignore")
        return (self._head + self._marker + self._tail).decode("utf-8", errors="ignore")


def _durable_owned_process_tree_pids(root_pid: int) -> list[int]:
    if root_pid <= 0:
        return []
    if sys.platform == "win32":
        script = (
            "$root="
            + str(root_pid)
            + ";"
            + "$procs=Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId;"
            + "$ids=New-Object 'System.Collections.Generic.HashSet[int]';"
            + "[void]$ids.Add([int]$root);"
            + "do{$changed=$false;foreach($p in $procs){"
            + "if($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)){"
            + "[void]$ids.Add([int]$p.ProcessId);$changed=$true}}}while($changed);"
            + "$ids | Sort-Object"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            pids: list[int] = []
            for line in (result.stdout or "").splitlines():
                try:
                    pids.append(int(line.strip()))
                except ValueError:
                    continue
            return sorted(set(pids)) or [root_pid]
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"process tree enumeration failed rc={result.returncode}"
            + (f": {stderr}" if stderr else "")
        )
    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid="],
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result.returncode == 0:
        children_by_parent: dict[int, list[int]] = {}
        for line in (result.stdout or "").splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
                ppid = int(parts[1])
            except ValueError:
                continue
            children_by_parent.setdefault(ppid, []).append(pid)
        owned = {root_pid}
        pending = [root_pid]
        while pending:
            parent = pending.pop()
            for child in children_by_parent.get(parent, []):
                if child not in owned:
                    owned.add(child)
                    pending.append(child)
        return sorted(owned)
    stderr = (result.stderr or result.stdout or "").strip()
    raise RuntimeError(
        f"process tree enumeration failed rc={result.returncode}"
        + (f": {stderr}" if stderr else "")
    )


def _durable_process_identity(
    root_pid: int,
    *,
    command_digest: str,
) -> dict[str, Any]:
    """Capture an OS-backed process identity suitable for PID-reuse fencing."""

    if root_pid <= 0:
        raise ValueError("root_pid must be positive")
    if sys.platform == "win32":
        import psutil

        try:
            process = psutil.Process(root_pid)
            with process.oneshot():
                start_token = str(round(process.create_time() * 10_000_000))
                executable = process.exe()
                parent_pid = process.ppid()
                command_line = process.cmdline()
        except psutil.Error as exc:
            raise OSError(f"psutil process identity failed: {exc}") from exc
        return {
            "pid": root_pid,
            "start_token": start_token,
            "parent_pid": parent_pid,
            "executable": executable,
            "observed_command_digest": hashlib.sha256(
                json.dumps(command_line, ensure_ascii=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "command_digest": command_digest,
            "identity_source": "psutil_process_identity",
        }

    stat_text = (Path(f"/proc/{root_pid}/stat")).read_text(encoding="utf-8")
    close_paren = stat_text.rfind(")")
    if close_paren < 0:
        raise ValueError("malformed /proc stat")
    fields = stat_text[close_paren + 2 :].split()
    if len(fields) <= 19:
        raise ValueError("incomplete /proc stat")
    try:
        executable = os.readlink(f"/proc/{root_pid}/exe")
    except OSError:
        executable = ""
    try:
        command_line = Path(f"/proc/{root_pid}/cmdline").read_bytes()
    except OSError:
        command_line = b""
    return {
        "pid": root_pid,
        "start_token": fields[19],
        "parent_pid": int(fields[1]),
        "executable": executable,
        "observed_command_digest": hashlib.sha256(command_line).hexdigest(),
        "command_digest": command_digest,
        "identity_source": "procfs_starttime",
    }


def _durable_process_identity_matches(
    stored: dict[str, Any],
    *,
    command_digest: str,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Prove that a live PID is still the exact persisted process."""

    try:
        pid = int(stored.get("pid", 0) or 0)
        observed = _durable_process_identity(pid, command_digest=command_digest)
    except (OSError, ValueError) as exc:
        return False, f"process identity unavailable: {type(exc).__name__}: {exc}", None
    if str(stored.get("command_digest", "")) != command_digest:
        return False, "persisted command digest mismatch", observed
    for key in ("pid", "start_token", "executable", "parent_pid", "observed_command_digest"):
        expected = str(stored.get(key, "") or "")
        actual = str(observed.get(key, "") or "")
        if expected and expected != actual:
            return False, f"process identity mismatch for {key}", observed
    if not str(stored.get("start_token", "") or ""):
        return False, "persisted process start token missing", observed
    if not str(stored.get("observed_command_digest", "") or ""):
        return False, "persisted observed command digest missing", observed
    return True, "exact process identity matched", observed


class _WindowsDurableJob:
    """Windows Job Object used as the owned process-tree boundary."""

    def __init__(self, *, containment_id: str) -> None:
        import ctypes
        from ctypes import wintypes

        class _BasicLimit(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _ExtendedLimit(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BasicLimit),
                ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        class _ThreadEntry(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", wintypes.LONG),
                ("tpDeltaPri", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
            ]

        self._ctypes = ctypes
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self._kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        self._kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self._kernel32.SetInformationJobObject.restype = wintypes.BOOL
        self._kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self._kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        self._kernel32.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        self._kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        self._kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self._kernel32.TerminateJobObject.restype = wintypes.BOOL
        self._kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self._kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self._kernel32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        self._kernel32.Thread32First.restype = wintypes.BOOL
        self._kernel32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        self._kernel32.Thread32Next.restype = wintypes.BOOL
        self._kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self._kernel32.OpenThread.restype = wintypes.HANDLE
        self._kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
        self._kernel32.ResumeThread.restype = wintypes.DWORD
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._ThreadEntry = _ThreadEntry
        self._handle = self._kernel32.CreateJobObjectW(None, None)
        self.containment_id = containment_id
        self.closed = False
        if not self._handle:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
        limits = _ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not self._kernel32.SetInformationJobObject(
            self._handle,
            9,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "SetInformationJobObject failed")

    def assign(self, proc: subprocess.Popen[str]) -> None:
        process_handle = getattr(proc, "_handle", None)
        if process_handle is None or not self._kernel32.AssignProcessToJobObject(
            self._handle, self._ctypes.c_void_p(int(process_handle))
        ):
            raise OSError(self._ctypes.get_last_error(), "AssignProcessToJobObject failed")

    def verify_root_membership(self, proc: subprocess.Popen[str]) -> None:
        if int(proc.pid) not in self.pids():
            raise RuntimeError(f"root pid {proc.pid} is not a member of the durable Job Object")

    def pids(self) -> list[int]:
        capacity = 64
        while capacity <= 4096:
            header = 8
            pointer_size = self._ctypes.sizeof(self._ctypes.c_size_t)
            buffer = self._ctypes.create_string_buffer(header + capacity * pointer_size)
            returned = self._ctypes.c_ulong()
            ok = self._kernel32.QueryInformationJobObject(
                self._handle,
                3,
                buffer,
                len(buffer),
                self._ctypes.byref(returned),
            )
            if ok:
                assigned = self._ctypes.c_ulong.from_buffer(buffer, 0).value
                listed = self._ctypes.c_ulong.from_buffer(buffer, 4).value
                if assigned > listed:
                    capacity *= 2
                    continue
                return sorted(
                    int(self._ctypes.c_size_t.from_buffer(buffer, header + i * pointer_size).value)
                    for i in range(listed)
                )
            error = self._ctypes.get_last_error()
            if error != 122:  # ERROR_INSUFFICIENT_BUFFER
                raise OSError(error, "QueryInformationJobObject failed")
            capacity *= 2
        raise RuntimeError("job process enumeration exceeded bounded capacity")

    def _suspend_evidence(
        self,
        proc: subprocess.Popen[str],
        *,
        launch_intent_id: str,
        logical_execution_id: str,
        state: str,
        method: str,
        success: bool,
        thread_id: int | None = None,
        win32_error: int | None = None,
        previous_suspend_count: int | None = None,
        resume_result: str = _RESUME_RESULT_NOT_ATTEMPTED,
    ) -> _SuspendStateEvidence:
        return _SuspendStateEvidence(
            state=state,
            process_id=int(proc.pid),
            thread_id=thread_id,
            observation_method=method,
            observation_success=success,
            win32_error=win32_error,
            observed_at=time.time(),
            launch_intent_id=launch_intent_id,
            logical_execution_id=logical_execution_id,
            previous_suspend_count=previous_suspend_count,
            resume_result=resume_result,
        )

    def resume_suspended_process(
        self,
        proc: subprocess.Popen[str],
        *,
        launch_intent_id: str,
        logical_execution_id: str,
    ) -> _SuspendStateEvidence:
        snapshot = self._kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
        invalid_handle = self._ctypes.c_void_p(-1).value
        if not snapshot or int(snapshot) == invalid_handle:
            error = self._ctypes.get_last_error()
            raise _DurableResumeStateUncertain(
                f"thread snapshot failed: win32={error}",
                evidence=self._suspend_evidence(
                    proc,
                    launch_intent_id=launch_intent_id,
                    logical_execution_id=logical_execution_id,
                    state=_SUSPEND_STATE_UNKNOWN,
                    method="CreateToolhelp32Snapshot",
                    success=False,
                    win32_error=error,
                ),
            )
        try:
            entry = self._ThreadEntry()
            entry.dwSize = self._ctypes.sizeof(entry)
            found = bool(self._kernel32.Thread32First(snapshot, self._ctypes.byref(entry)))
            while found:
                if int(entry.th32OwnerProcessID) == int(proc.pid):
                    thread = self._kernel32.OpenThread(0x0002, False, entry.th32ThreadID)
                    if not thread:
                        error = self._ctypes.get_last_error()
                        raise _DurableResumeStateUncertain(
                            f"OpenThread failed: win32={error}",
                            evidence=self._suspend_evidence(
                                proc,
                                launch_intent_id=launch_intent_id,
                                logical_execution_id=logical_execution_id,
                                state=_SUSPEND_STATE_UNKNOWN,
                                method="OpenThread",
                                success=False,
                                thread_id=int(entry.th32ThreadID),
                                win32_error=error,
                            ),
                        )
                    try:
                        previous_count = self._kernel32.ResumeThread(thread)
                        if previous_count == 0xFFFFFFFF:
                            error = self._ctypes.get_last_error()
                            raise _DurableResumeStateUncertain(
                                "ResumeThread failed with ambiguous thread state",
                                evidence=self._suspend_evidence(
                                    proc,
                                    launch_intent_id=launch_intent_id,
                                    logical_execution_id=logical_execution_id,
                                    state=_SUSPEND_STATE_UNKNOWN,
                                    method="ResumeThread",
                                    success=False,
                                    thread_id=int(entry.th32ThreadID),
                                    win32_error=error,
                                    resume_result=_RESUME_RESULT_FAILURE,
                                ),
                            )
                        if previous_count != 1:
                            state = (
                                _SUSPEND_STATE_PROVEN_SUSPENDED
                                if previous_count > 1
                                else _SUSPEND_STATE_UNKNOWN
                            )
                            raise _DurableResumeStateUncertain(
                                f"unexpected ResumeThread previous suspend count {previous_count} "
                                f"for pid {proc.pid}",
                                evidence=self._suspend_evidence(
                                    proc,
                                    launch_intent_id=launch_intent_id,
                                    logical_execution_id=logical_execution_id,
                                    state=state,
                                    method="ResumeThread",
                                    success=previous_count > 1,
                                    thread_id=int(entry.th32ThreadID),
                                    previous_suspend_count=int(previous_count),
                                    resume_result=_RESUME_RESULT_UNEXPECTED,
                                ),
                            )
                        return self._suspend_evidence(
                            proc,
                            launch_intent_id=launch_intent_id,
                            logical_execution_id=logical_execution_id,
                            state=_SUSPEND_STATE_PROVEN_RESUMED,
                            method="ResumeThread",
                            success=True,
                            thread_id=int(entry.th32ThreadID),
                            previous_suspend_count=1,
                            resume_result=_RESUME_RESULT_EXPECTED,
                        )
                    finally:
                        self._kernel32.CloseHandle(thread)
                found = bool(self._kernel32.Thread32Next(snapshot, self._ctypes.byref(entry)))
        finally:
            self._kernel32.CloseHandle(snapshot)
        raise _DurableResumeStateUncertain(
            f"suspended initial thread not found for pid {proc.pid}",
            evidence=self._suspend_evidence(
                proc,
                launch_intent_id=launch_intent_id,
                logical_execution_id=logical_execution_id,
                state=_SUSPEND_STATE_UNKNOWN,
                method="thread_snapshot_enumeration",
                success=False,
            ),
        )

    def terminate(self) -> None:
        if not self._kernel32.TerminateJobObject(self._handle, 1):
            raise OSError(self._ctypes.get_last_error(), "TerminateJobObject failed")

    def close(self) -> None:
        if not self.closed and self._handle:
            self._kernel32.CloseHandle(self._handle)
            self.closed = True


def _durable_observe_process_after_unexpected_resume(
    proc: subprocess.Popen[str],
    *,
    evidence: _SuspendStateEvidence,
) -> _SuspendStateEvidence:
    if evidence.state == _SUSPEND_STATE_PROVEN_SUSPENDED:
        return evidence
    try:
        returncode = proc.poll()
    except Exception:
        return _SuspendStateEvidence(
            state=_SUSPEND_STATE_UNKNOWN,
            process_id=evidence.process_id,
            thread_id=evidence.thread_id,
            observation_method="process_handle_poll",
            observation_success=False,
            win32_error=None,
            observed_at=time.time(),
            launch_intent_id=evidence.launch_intent_id,
            logical_execution_id=evidence.logical_execution_id,
            previous_suspend_count=evidence.previous_suspend_count,
            resume_result=evidence.resume_result,
        )
    if returncode is not None:
        state = _SUSPEND_STATE_PROVEN_EXITED
    elif (
        evidence.resume_result == _RESUME_RESULT_UNEXPECTED
        and evidence.previous_suspend_count == 0
    ):
        # ResumeThread's zero return proves the thread was not suspended before
        # the call; the process-handle observation independently proves it exists.
        state = _SUSPEND_STATE_PROVEN_RESUMED
    else:
        state = _SUSPEND_STATE_UNKNOWN
    return _SuspendStateEvidence(
        state=state,
        process_id=evidence.process_id,
        thread_id=evidence.thread_id,
        observation_method="process_handle_poll_after_unexpected_resume",
        observation_success=state != _SUSPEND_STATE_UNKNOWN,
        win32_error=None,
        observed_at=time.time(),
        launch_intent_id=evidence.launch_intent_id,
        logical_execution_id=evidence.logical_execution_id,
        previous_suspend_count=evidence.previous_suspend_count,
        resume_result=evidence.resume_result,
    )


def _durable_attach_process_containment(
    proc: subprocess.Popen[str], *, containment_id: str
) -> _WindowsDurableJob | None:
    if sys.platform != "win32":
        return None
    job = _WindowsDurableJob(containment_id=containment_id)
    try:
        job.assign(proc)
        job.verify_root_membership(proc)
    except Exception:
        job.close()
        raise
    return job


def _durable_contained_pids(proc: subprocess.Popen[str]) -> list[int]:
    containment = getattr(proc, "_umh_containment", None)
    if containment is not None:
        return containment.pids()
    return _durable_owned_process_tree_pids(proc.pid)


def _durable_capture_owned_identities(
    proc: subprocess.Popen[str],
    *,
    command_digest: str,
) -> dict[int, dict[str, Any]]:
    identities = dict(getattr(proc, "_umh_owned_process_identities", {}) or {})
    for pid in _durable_contained_pids(proc):
        if pid in identities:
            continue
        identities[pid] = _durable_process_identity(pid, command_digest=command_digest)
    setattr(proc, "_umh_owned_process_identities", identities)
    return identities


def _durable_alive_pids(pids: list[int]) -> list[int]:
    alive: list[int] = []
    for pid in sorted(set(pids)):
        if pid <= 0:
            continue
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and str(pid) in (result.stdout or ""):
                alive.append(pid)
        else:
            try:
                os.kill(pid, 0)
                alive.append(pid)
            except ProcessLookupError:
                continue
            except PermissionError:
                alive.append(pid)
    return alive


def _durable_force_exact_pids(pids: list[int]) -> list[str]:
    lines: list[str] = []
    for pid in sorted(set(pids), reverse=True):
        if pid <= 0:
            continue
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                lines.append(
                    f"exact pid force cleanup pid={pid} rc={result.returncode}: "
                    f"{(result.stdout or result.stderr or '').strip()}"
                )
            except Exception as exc:  # noqa: BLE001
                lines.append(
                    f"exact pid force cleanup failed pid={pid}: {type(exc).__name__}: {exc}"
                )
        else:
            try:
                os.kill(pid, signal.SIGKILL)
                lines.append(f"sent SIGKILL to exact pid {pid}")
            except ProcessLookupError:
                lines.append(f"exact pid already absent {pid}")
            except Exception as exc:  # noqa: BLE001
                lines.append(
                    f"exact pid force cleanup failed pid={pid}: {type(exc).__name__}: {exc}"
                )
    return lines


def _durable_terminate_owned_processes(
    proc: subprocess.Popen[str], exact_owned: list[int]
) -> list[str]:
    """Terminate only through a containment handle on Windows.

    A PID can be reused between identity validation and a later taskkill call.  The
    Job Object handle is the stable ownership boundary for Windows executions.
    """

    containment = getattr(proc, "_umh_containment", None)
    if sys.platform == "win32":
        if containment is None:
            raise RuntimeError("Windows process containment unavailable; refusing PID cleanup")
        containment.terminate()
        return ["terminated owned Windows Job Object"]
    return _durable_force_exact_pids(exact_owned)


def _durable_fail_closed_reader_timeout_cleanup(
    proc: subprocess.Popen[str],
    cleanup: dict[str, Any],
    last_tree_pids: list[int],
) -> dict[str, Any]:
    cleanup.setdefault("enumeration_performed", False)
    cleanup.setdefault("enumeration_complete", False)
    cleanup.setdefault("ownership_validated", False)
    cleanup.setdefault("post_termination_enumeration_complete", False)
    cleanup["cleanup_verified"] = False
    try:
        command_digest = str(
            (getattr(proc, "_umh_process_identity", {}) or {}).get("command_digest", "")
        )
        identities = _durable_capture_owned_identities(proc, command_digest=command_digest)
        last_tree_pids = sorted(set(last_tree_pids + list(identities)))
        cleanup["enumeration_performed"] = True
        cleanup["enumeration_complete"] = True
    except Exception as exc:  # noqa: BLE001
        cleanup["enumeration_performed"] = True
        cleanup["reader_timeout_enumeration_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [{"state": "reader_timeout_descendant_identity_unknown"}]
        return cleanup
    try:
        alive = _durable_alive_pids(last_tree_pids)
    except Exception as exc:  # noqa: BLE001
        cleanup["process_residue"] = [{"state": "reader_timeout_alive_scan_unverified"}]
        cleanup["reader_timeout_alive_scan_error"] = f"{type(exc).__name__}: {exc}"
        return cleanup
    exact_owned: list[int] = []
    for pid in alive:
        stored = dict(identities.get(pid) or {})
        if not stored:
            cleanup["process_residue"] = [
                {"pid": pid, "state": "reader_timeout_ownership_unverified"}
            ]
            return cleanup
        matched, _reason, _observed = _durable_process_identity_matches(
            stored,
            command_digest=str(stored.get("command_digest", "")),
        )
        if matched:
            exact_owned.append(pid)
    cleanup["ownership_validated"] = True
    if getattr(proc, "_umh_containment", None) is None and not any(
        pid != proc.pid for pid in identities
    ):
        cleanup["process_residue"] = [
            {"state": "reader_timeout_descendant_identity_unknown"}
        ]
        return cleanup
    if exact_owned:
        cleanup.setdefault("force_stdout", "")
        cleanup["force_stdout"] = "\n".join(
            str(x)
            for x in [
                cleanup.get("force_stdout", ""),
                *_durable_terminate_owned_processes(proc, exact_owned),
            ]
            if x
        )
        remaining = _durable_alive_pids(exact_owned)
        cleanup["process_residue"] = [{"pid": pid, "state": "still_alive"} for pid in remaining]
        cleanup["post_termination_enumeration_complete"] = True
        cleanup["residue_count"] = len(remaining)
        cleanup["cleanup_verified"] = not remaining
    else:
        cleanup["process_residue"] = []
        cleanup["post_termination_enumeration_complete"] = True
        cleanup["residue_count"] = 0
        cleanup["cleanup_verified"] = True
    return cleanup


def _durable_post_exit_process_cleanup(
    proc: subprocess.Popen[str],
    last_tree_pids: list[int],
) -> dict[str, Any]:
    cleanup: dict[str, Any] = {
        "root_pid": proc.pid,
        "post_exit_process_check": True,
        "enumeration_performed": False,
        "enumeration_complete": False,
        "ownership_validated": False,
        "matched_processes": [],
        "termination_attempted": False,
        "post_termination_enumeration_complete": False,
        "residue_count": None,
        "cleanup_verified": False,
        "forced": False,
        "process_residue": [],
    }
    try:
        command_digest = str(
            (getattr(proc, "_umh_process_identity", {}) or {}).get("command_digest", "")
        )
        identities = _durable_capture_owned_identities(
            proc,
            command_digest=command_digest,
        )
        observed = list(identities)
        cleanup["enumeration_performed"] = True
        cleanup["enumeration_complete"] = True
    except Exception as exc:  # noqa: BLE001
        cleanup["enumeration_performed"] = True
        cleanup["post_exit_process_check_ok"] = False
        cleanup["post_exit_process_check_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [{"state": "post_exit_process_tree_unverified"}]
        return cleanup
    cleanup["post_exit_process_check_ok"] = True
    candidates = sorted({pid for pid in [*last_tree_pids, *observed] if pid != proc.pid})
    try:
        alive = _durable_alive_pids(candidates)
    except Exception as exc:  # noqa: BLE001
        cleanup["post_exit_process_check_ok"] = False
        cleanup["post_exit_alive_scan_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [{"state": "post_exit_alive_scan_unverified"}]
        return cleanup
    exact_owned: list[int] = []
    ownership_mismatches: list[dict[str, Any]] = []
    for pid in alive:
        stored = dict(identities.get(pid) or {})
        if not stored:
            cleanup["post_exit_process_check_ok"] = False
            cleanup["process_residue"] = [
                {"pid": pid, "state": "descendant_ownership_unverified"}
            ]
            return cleanup
        matched, reason, observed_identity = _durable_process_identity_matches(
            stored,
            command_digest=str(stored.get("command_digest", "")),
        )
        if matched:
            exact_owned.append(pid)
            cleanup["matched_processes"].append(observed_identity or stored)
        else:
            ownership_mismatches.append(
                {
                    "pid": pid,
                    "reason": reason,
                    "stored": stored,
                    "observed": observed_identity or {},
                }
            )
    cleanup["ownership_validated"] = True
    if ownership_mismatches:
        cleanup["pid_reuse_or_identity_mismatch"] = ownership_mismatches
    if not exact_owned:
        cleanup["post_termination_enumeration_complete"] = True
        cleanup["residue_count"] = 0
        cleanup["cleanup_verified"] = True
        return cleanup
    cleanup["forced"] = True
    cleanup["termination_attempted"] = True
    cleanup["process_residue_detected_after_exit"] = True
    try:
        cleanup["force_stdout"] = "\n".join(
            _durable_terminate_owned_processes(proc, exact_owned)
        )
    except Exception as exc:  # noqa: BLE001
        cleanup["post_exit_process_check_ok"] = False
        cleanup["force_cleanup_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [
            {"pid": pid, "state": "cleanup_unverified"} for pid in exact_owned
        ]
        return cleanup
    try:
        remaining_alive = _durable_alive_pids(exact_owned)
    except Exception as exc:  # noqa: BLE001
        cleanup["post_exit_process_check_ok"] = False
        cleanup["post_exit_remaining_scan_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [
            {"pid": pid, "state": "remaining_scan_unverified"} for pid in exact_owned
        ]
        return cleanup
    remaining: list[int] = []
    for pid in remaining_alive:
        stored = identities[pid]
        matched, _reason, _observed = _durable_process_identity_matches(
            stored,
            command_digest=str(stored.get("command_digest", "")),
        )
        if matched:
            remaining.append(pid)
    cleanup["post_termination_enumeration_complete"] = True
    cleanup["process_residue"] = [{"pid": pid, "state": "still_alive"} for pid in remaining]
    cleanup["residue_count"] = len(remaining)
    cleanup["cleanup_verified"] = not remaining
    return cleanup


def _durable_positive_no_process_cleanup(**evidence: Any) -> dict[str, Any]:
    """Positive proof for a trajectory whose launch primitive was never invoked."""

    return {
        "enumeration_performed": True,
        "enumeration_complete": True,
        "ownership_validated": True,
        "matched_processes": [],
        "termination_attempted": False,
        "post_termination_enumeration_complete": True,
        "residue_count": 0,
        "cleanup_verified": True,
        "process_residue": [],
        "launch_not_attempted": True,
        "process_created": False,
        "process_side_effect_possible": False,
        **evidence,
    }


class _DurablePipeCollector:
    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self._lock = threading.Lock()
        self._buffers = {
            "stdout": _BoundedStreamBuffer(_DURABLE_TIMEOUT_STDOUT_LIMIT),
            "stderr": _BoundedStreamBuffer(_DURABLE_TIMEOUT_STDERR_LIMIT),
        }
        self._reader_errors: dict[str, str] = {}
        self._threads: list[threading.Thread] = []
        self._streams: list[Any] = []
        for name in ("stdout", "stderr"):
            stream = getattr(proc, name, None)
            if stream is None:
                continue
            self._streams.append(stream)
            thread = threading.Thread(
                target=self._drain_stream,
                args=(name, stream),
                name=f"durable-{name}-drain-{getattr(proc, 'pid', 'unknown')}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def _drain_stream(self, name: str, stream: Any) -> None:
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                if isinstance(chunk, bytes):
                    text = chunk.decode("utf-8", errors="replace")
                else:
                    text = str(chunk)
                with self._lock:
                    self._buffers[name].append(text)
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._reader_errors[name] = f"{type(exc).__name__}: {exc}"

    @property
    def has_readers(self) -> bool:
        return bool(self._threads)

    def snapshot(self, *, join_timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + max(0.0, join_timeout)
        for thread in self._threads:
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(timeout=remaining)
        if any(thread.is_alive() for thread in self._threads):
            for stream in self._streams:
                try:
                    stream.close()
                except Exception:
                    pass
            for thread in self._threads:
                remaining = max(0.0, deadline - time.monotonic())
                thread.join(timeout=remaining)
        reader_timed_out = any(thread.is_alive() for thread in self._threads)
        with self._lock:
            raw_stdout = self._buffers["stdout"].text()
            raw_stderr = self._buffers["stderr"].text()
            stdout = raw_stdout
            stderr = raw_stderr
            stdout, stdout_redaction_truncated = _tail_with_limit(
                stdout,
                _DURABLE_TIMEOUT_STDOUT_LIMIT,
            )
            stderr, stderr_redaction_truncated = _tail_with_limit(
                stderr,
                _DURABLE_TIMEOUT_STDERR_LIMIT,
            )
            stdout_truncated = self._buffers["stdout"].truncated or stdout_redaction_truncated
            stderr_truncated = self._buffers["stderr"].truncated or stderr_redaction_truncated
            stdout_bytes = self._buffers["stdout"].bytes_seen
            stderr_bytes = self._buffers["stderr"].bytes_seen
            redacted = self._buffers["stdout"].redacted or self._buffers["stderr"].redacted
            errors = dict(self._reader_errors)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "output_capture": {
                "attempted": True,
                "concurrent_drain": True,
                "drain_timeout_seconds": join_timeout,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "total_truncated": stdout_truncated or stderr_truncated,
                "stdout_limit_bytes": _DURABLE_TIMEOUT_STDOUT_LIMIT,
                "stderr_limit_bytes": _DURABLE_TIMEOUT_STDERR_LIMIT,
                "total_limit_bytes": _DURABLE_TIMEOUT_TOTAL_LIMIT,
                "stdout_bytes_seen": stdout_bytes,
                "stderr_bytes_seen": stderr_bytes,
                "total_bytes_seen": stdout_bytes + stderr_bytes,
                "redacted": redacted,
                "timed_out": reader_timed_out,
                "reader_errors": errors,
            },
        }


class NodeClient:
    """WebSocket client that connects to the UMH node mesh server.

    Hard separation between control plane and media plane:
    - Control: heartbeats + capability dispatch — always responsive.
    - Media: frame emission via bounded queue — drops old frames on backpressure.
    """

    def __init__(self, config: NodeConfig) -> None:
        self._config = config
        self._ws: Any = None
        self._connected = False
        self._shutdown = asyncio.Event()
        self._msg_id = 0
        self._pending_rpc: dict[Any, asyncio.Future[dict[str, Any]]] = {}
        self._pending_rpc_generations: dict[Any, int] = {}
        self._ws_send_lock: asyncio.Lock | None = None
        self._ws_writer_task: asyncio.Task | None = None
        self._ws_send_queues: dict[str, deque[_WsSendEntry]] = {
            traffic_class: deque() for traffic_class in _TRAFFIC_CLASSES
        }
        self._ws_send_queue_bytes = {traffic_class: 0 for traffic_class in _TRAFFIC_CLASSES}
        self._ws_send_seq = 0
        self._authority_send_burst = 0
        self._ws_generation = 0
        self._active_ws_generation: int | None = None
        self._ws_queue_generation = 0
        self._ws_transport_healthy = False
        self._generation_tasks: dict[int, set[asyncio.Task[Any]]] = {}
        self._generation_task_labels: dict[asyncio.Task[Any], str] = {}
        self._generation_teardown_failed = False

        self._adapters: dict[str, Any] = {}
        self._init_adapters()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_workspace_change: Callable[[dict[str, Any]], None] | None = None
        self._camera_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cam")
        self._capability_semaphore = asyncio.Semaphore(8)
        self._durable_store = DurableRemoteStore(default_node_root())
        self._durable_processes: dict[str, subprocess.Popen[str]] = {}
        self._durable_execution_locks: dict[str, asyncio.Lock] = {}
        self._durable_logical_executions: dict[str, dict[str, Any]] = {}
        self._durable_request_gates: dict[str, dict[str, Any]] = {}
        self._durable_request_trajectories: dict[str, dict[str, Any]] = {}

        # Media plane: bounded frame queue — stream thread pushes, drain task sends
        self._media_queue: deque[str] = deque(maxlen=_MEDIA_QUEUE_MAX)
        self._media_event = asyncio.Event()
        self._media_drain_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    def _init_adapters(self) -> None:
        cap_cfg = self._config.capabilities

        if cap_cfg.get("shell") is None or cap_cfg.get("shell").enabled:
            self._adapters["shell"] = ShellAdapter()
        from nodes.windows.umh_node.adapters.terminal import TerminalAdapter

        self._adapters["terminal"] = TerminalAdapter()
        if cap_cfg.get("filesystem") is None or cap_cfg.get("filesystem").enabled:
            self._adapters["filesystem"] = FilesystemAdapter()
        if cap_cfg.get("desktop") and cap_cfg["desktop"].enabled:
            self._adapters["desktop"] = DesktopAdapter()
        if cap_cfg.get("clipboard") and cap_cfg["clipboard"].enabled:
            self._adapters["clipboard"] = ClipboardAdapter()
        if cap_cfg.get("camera") and cap_cfg["camera"].enabled:
            cam = CameraAdapter()
            cam.set_frame_callback(self._on_camera_frame)
            self._adapters["camera"] = cam
            try:
                result = cam.execute(
                    "camera.stream_start", {"fps": 2, "quality": 70, "resolution": [1280, 720]}
                )
                if result.get("success"):
                    logger.info("camera stream auto-started (2fps, 1280x720, q70)")
                else:
                    logger.debug("camera auto-start returned: %s", result.get("error"))
            except Exception as exc:
                logger.debug("camera auto-start failed: %s", exc)
        try:
            import mss

            with mss.mss() as sct:
                monitor_count = len(sct.monitors) - 1  # index 0 is virtual combined
            for idx in range(1, monitor_count + 1):
                key = f"desktop_stream_{idx - 1}"
                ds = DesktopStreamAdapter(monitor_index=idx)
                ds.set_frame_callback(self._on_camera_frame)
                self._adapters[key] = ds
                ds.start()
            logger.info("desktop stream: %d monitor(s) active", monitor_count)
        except Exception as exc:
            logger.debug("desktop stream adapter unavailable: %s", exc)
        # Hermes: always register if binary exists, no config gate needed
        hermes = HermesAdapter()
        if hermes._available:
            self._adapters["hermes"] = hermes

        # Broadcast: always register — FFmpeg availability checked at runtime
        broadcast_cfg = cap_cfg.get("broadcast")
        if broadcast_cfg is None or broadcast_cfg.enabled:
            self._adapters["broadcast"] = BroadcastAdapter()

    def _on_camera_frame(self, frame_data: dict[str, Any]) -> None:
        """Called from camera stream thread — enqueues frame for async send.

        Sends binary WS frames: [4-byte meta_len][JSON meta][JPEG bytes].
        Saves ~33% bandwidth vs base64 JSON-RPC encoding.
        NEVER blocks on WS send. Uses bounded deque with drop-oldest semantics.
        """
        if not self._connected or self._ws is None or self._loop is None:
            return
        try:
            jpeg_bytes = frame_data.pop("image_jpeg", None)
            if jpeg_bytes is None:
                return
            meta_bytes = json.dumps(frame_data).encode()
            msg = struct.pack(">I", len(meta_bytes)) + meta_bytes + jpeg_bytes
            if len(msg) > _BULK_MEDIA_MAX_FRAME_BYTES:
                logger.debug("media frame dropped: %d bytes exceeds bulk frame bound", len(msg))
                return
            self._media_queue.append(msg)
            self._loop.call_soon_threadsafe(self._media_event.set)
        except Exception as exc:
            logger.debug("frame enqueue failed: %s", exc)

    async def _media_drain_loop(self) -> None:
        """Drain media queue and send frames over WS.

        Runs as a separate task — if WS send is slow, frames drop from
        the bounded queue. Control plane is never affected.
        """
        while True:
            await self._media_event.wait()
            self._media_event.clear()
            while self._media_queue:
                try:
                    msg = self._media_queue.popleft()
                except IndexError:
                    break
                if not self._connected or self._ws is None:
                    self._media_queue.clear()
                    break
                try:
                    await self._send_ws(msg, traffic_class=_TRAFFIC_BULK_MEDIA)
                except Exception as exc:
                    logger.debug("media send failed: %s", exc)
                    self._media_queue.clear()
                    break

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _ensure_ws_writer_state(self) -> None:
        if not hasattr(self, "_ws_send_queues"):
            self._ws_send_queues = {traffic_class: deque() for traffic_class in _TRAFFIC_CLASSES}
        if not hasattr(self, "_ws_send_queue_bytes"):
            self._ws_send_queue_bytes = {
                traffic_class: sum(
                    entry.payload_bytes if isinstance(entry, _WsSendEntry) else 0
                    for entry in self._ws_send_queues[traffic_class]
                )
                for traffic_class in _TRAFFIC_CLASSES
            }
        if not hasattr(self, "_ws_send_seq"):
            self._ws_send_seq = 0
        if not hasattr(self, "_authority_send_burst"):
            self._authority_send_burst = 0
        if not hasattr(self, "_ws_writer_task"):
            self._ws_writer_task = None
        if not hasattr(self, "_ws_generation"):
            self._ws_generation = 0
        if not hasattr(self, "_ws_transport_healthy"):
            self._ws_transport_healthy = getattr(self, "_ws", None) is not None
        if not hasattr(self, "_pending_rpc_generations"):
            self._pending_rpc_generations = {}
        if not hasattr(self, "_active_ws_generation"):
            self._active_ws_generation = self._ws_generation if self._ws is not None else None
        if not hasattr(self, "_ws_queue_generation"):
            self._ws_queue_generation = self._ws_generation
        if not hasattr(self, "_generation_tasks"):
            self._generation_tasks = {}
        if not hasattr(self, "_generation_task_labels"):
            self._generation_task_labels = {}
        if not hasattr(self, "_generation_teardown_failed"):
            self._generation_teardown_failed = False

    def _active_generation(self) -> int:
        self._ensure_ws_writer_state()
        generation = self._active_ws_generation
        if generation is None and self._ws is not None and self._ws_transport_healthy:
            # Compatibility for focused unit fixtures that construct a client
            # without running the connection lifecycle.
            generation = self._ws_generation
        return int(generation or 0)

    def _activate_connection_generation(self, ws: Any) -> int:
        self._ensure_ws_writer_state()
        if self._generation_teardown_failed:
            raise TransportGenerationTeardownFailed("prior websocket generation did not quiesce")
        if self._active_ws_generation is not None:
            raise TransportGenerationTeardownFailed(
                "refusing overlapping websocket connection generations"
            )
        self._ws_generation += 1
        generation = self._ws_generation
        self._active_ws_generation = generation
        self._ws_queue_generation = generation
        self._ws = ws
        self._ws_transport_healthy = True
        self._ws_send_queues = {traffic_class: deque() for traffic_class in _TRAFFIC_CLASSES}
        self._ws_send_queue_bytes = {traffic_class: 0 for traffic_class in _TRAFFIC_CLASSES}
        self._authority_send_burst = 0
        self._ws_writer_task = None
        self._generation_tasks[generation] = set()
        return generation

    async def _run_generation_task(
        self,
        generation: int,
        awaitable: Any,
    ) -> Any:
        token = _connection_generation_context.set(generation)
        try:
            return await awaitable
        finally:
            _connection_generation_context.reset(token)

    def _create_generation_task(
        self,
        awaitable: Any,
        *,
        generation: int,
        label: str,
    ) -> asyncio.Task[Any]:
        self._ensure_ws_writer_state()
        if generation != self._active_generation():
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
            raise ConnectionError("stale websocket transport generation")
        task = asyncio.create_task(self._run_generation_task(generation, awaitable))
        tasks = self._generation_tasks.setdefault(generation, set())
        tasks.add(task)
        self._generation_task_labels[task] = label

        def _complete(done: asyncio.Task[Any]) -> None:
            close = getattr(awaitable, "close", None)
            if callable(close):
                close()
            self._generation_tasks.get(generation, set()).discard(done)
            self._generation_task_labels.pop(done, None)
            if done.cancelled():
                return
            try:
                error = done.exception()
            except asyncio.CancelledError:
                return
            if error is not None:
                logger.debug(
                    "connection generation task failed: generation=%s label=%s error=%s",
                    generation,
                    label,
                    error,
                )

        task.add_done_callback(_complete)
        return task

    async def _teardown_connection_generation(self, generation: int, ws: Any) -> None:
        self._ensure_ws_writer_state()
        if self._active_ws_generation == generation:
            self._active_ws_generation = None
        self._connected = False
        self._ws_transport_healthy = False
        closed = ConnectionError(f"websocket generation {generation} closed")
        self._fail_pending_rpc(closed, generation=generation)
        self._fail_queued_ws_sends(closed, generation=generation)

        current = asyncio.current_task()
        tasks = {
            task
            for task in self._generation_tasks.get(generation, set())
            if task is not current and not task.done()
        }
        for task in tasks:
            task.cancel()
        pending: set[asyncio.Task[Any]] = set()
        if tasks:
            done, pending = await asyncio.wait(
                tasks,
                timeout=_CONNECTION_GENERATION_TEARDOWN_S,
            )
            if done:
                await asyncio.gather(*done, return_exceptions=True)
        if pending:
            self._generation_teardown_failed = True
            transport = getattr(ws, "transport", None)
            abort = getattr(transport, "abort", None)
            if callable(abort):
                abort()
            labels = sorted(self._generation_task_labels.get(task, "unknown") for task in pending)
            raise TransportGenerationTeardownFailed(
                "TRANSPORT_GENERATION_TEARDOWN_FAILED: " + ",".join(labels)
            )

        self._generation_tasks.pop(generation, None)
        self._ws_writer_task = None
        self._media_drain_task = None
        if self._ws_queue_generation == generation:
            self._ws_send_queues = {traffic_class: deque() for traffic_class in _TRAFFIC_CLASSES}
            self._ws_send_queue_bytes = {traffic_class: 0 for traffic_class in _TRAFFIC_CLASSES}
            self._ws_queue_generation = 0

    def _normalize_traffic_class(self, traffic_class: str) -> str:
        if traffic_class in _TRAFFIC_CLASSES:
            return traffic_class
        return _TRAFFIC_ORDINARY

    @staticmethod
    def _ws_payload_bytes(payload: str | bytes) -> int:
        if isinstance(payload, bytes):
            return len(payload)
        return len(payload.encode("utf-8"))

    def _queue_ws_send(
        self,
        payload: str | bytes,
        *,
        traffic_class: str,
        future: asyncio.Future[dict[str, Any]],
        generation: int | None = None,
    ) -> _WsSendEntry:
        self._ensure_ws_writer_state()
        expected_generation = generation or self._active_generation()
        if (
            not expected_generation
            or expected_generation != self._active_generation()
            or self._ws_queue_generation not in {0, expected_generation}
        ):
            raise ConnectionError("stale websocket transport generation")
        if self._ws_queue_generation == 0:
            self._ws_queue_generation = expected_generation
        payload_bytes = self._ws_payload_bytes(payload)
        queue = self._ws_send_queues[traffic_class]
        if payload_bytes > _WS_SEND_PAYLOAD_MAX_BYTES[traffic_class]:
            raise TransportQueueOverload(
                f"{traffic_class} frame exceeds {_WS_SEND_PAYLOAD_MAX_BYTES[traffic_class]} byte bound"
            )
        if (
            len(queue) >= _WS_SEND_QUEUE_CAPACITY[traffic_class]
            or self._ws_send_queue_bytes[traffic_class] + payload_bytes
            > _WS_SEND_QUEUE_MAX_BYTES[traffic_class]
        ):
            raise TransportQueueOverload(
                f"{traffic_class}_OVERLOAD depth={len(queue)} bytes="
                f"{self._ws_send_queue_bytes[traffic_class]}"
            )
        self._ws_send_seq += 1
        entry = _WsSendEntry(
            seq=self._ws_send_seq,
            payload=payload,
            future=future,
            traffic_class=traffic_class,
            payload_bytes=payload_bytes,
            queued_at=time.monotonic(),
            generation=expected_generation,
        )
        queue.append(entry)
        self._ws_send_queue_bytes[traffic_class] += payload_bytes
        return entry

    def _pop_ws_send(self, traffic_class: str) -> _WsSendEntry:
        entry = self._ws_send_queues[traffic_class].popleft()
        self._ws_send_queue_bytes[traffic_class] = max(
            0,
            self._ws_send_queue_bytes[traffic_class] - entry.payload_bytes,
        )
        return entry

    def _dequeue_next_ws_send(self) -> _WsSendEntry | None:
        self._ensure_ws_writer_state()
        authority = self._ws_send_queues[_TRAFFIC_AUTHORITY_CONTROL]
        lower_has_work = any(
            self._ws_send_queues[name]
            for name in (_TRAFFIC_REQUIRED_CONTROL, _TRAFFIC_ORDINARY, _TRAFFIC_BULK_MEDIA)
        )
        if authority and (
            self._authority_send_burst < _AUTHORITY_SEND_BURST_LIMIT or not lower_has_work
        ):
            self._authority_send_burst += 1
            return self._pop_ws_send(_TRAFFIC_AUTHORITY_CONTROL)
        for name in (_TRAFFIC_REQUIRED_CONTROL, _TRAFFIC_ORDINARY, _TRAFFIC_BULK_MEDIA):
            queue = self._ws_send_queues[name]
            if queue:
                self._authority_send_burst = 0
                return self._pop_ws_send(name)
        if authority:
            self._authority_send_burst = 1
            return self._pop_ws_send(_TRAFFIC_AUTHORITY_CONTROL)
        return None

    async def _ws_writer_loop(self, generation: int) -> None:
        while True:
            entry = self._dequeue_next_ws_send()
            if entry is None:
                return
            if entry.future.cancelled():
                continue
            if entry.generation != generation or generation != self._active_generation():
                if not entry.future.done():
                    entry.future.set_exception(
                        ConnectionError("stale websocket transport generation")
                    )
                continue
            if self._ws is None:
                if not entry.future.done():
                    entry.future.set_exception(ConnectionError("node websocket not connected"))
                continue
            queue_wait_s = time.monotonic() - entry.queued_at
            if (
                entry.traffic_class == _TRAFFIC_AUTHORITY_CONTROL
                and queue_wait_s > _AUTHORITY_QUEUE_MAX_WAIT_S
            ):
                exc = TransportSendDeadlineExceeded(
                    "authority frame exceeded bounded queue-wait envelope"
                )
                if not entry.future.done():
                    entry.future.set_exception(exc)
                await self._invalidate_ws_transport(exc, generation=entry.generation)
                self._fail_queued_ws_sends(exc)
                return
            try:
                send_s = await self._send_ws_frame_with_deadline(
                    entry.payload,
                    generation=entry.generation,
                )
            except asyncio.CancelledError:
                if not entry.future.done():
                    entry.future.set_exception(
                        ConnectionError("websocket generation closed during send")
                    )
                raise
            except Exception as exc:
                if not entry.future.done():
                    entry.future.set_exception(exc)
                self._fail_queued_ws_sends(exc)
                return
            else:
                if not entry.future.done():
                    entry.future.set_result(
                        {
                            "seq": entry.seq,
                            "traffic_class": entry.traffic_class,
                            "generation": entry.generation,
                            "queue_wait_ms": round(queue_wait_s * 1000, 3),
                            "send_ms": round(send_s * 1000, 3),
                        }
                    )
                # Let producers and authority enqueuers run before the next
                # scheduling decision; a self-replenishing lower queue must
                # not monopolize the local event loop.
                await asyncio.sleep(0)

    async def _send_ws_frame_with_deadline(
        self,
        payload: str | bytes,
        *,
        generation: int,
    ) -> float:
        ws = self._ws
        if ws is None or generation != self._active_generation() or not self._ws_transport_healthy:
            raise ConnectionError("node websocket transport generation unavailable")
        started = time.monotonic()
        send_task = self._create_generation_task(
            ws.send(payload),
            generation=generation,
            label="websocket-send",
        )
        try:
            done, _pending = await asyncio.wait({send_task}, timeout=_WS_SEND_DEADLINE_S)
        except asyncio.CancelledError:
            await self._invalidate_ws_transport(
                ConnectionError("websocket writer cancelled during send"),
                generation=generation,
            )
            send_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await send_task
            raise
        if send_task in done:
            try:
                await send_task
            except Exception as exc:
                await self._invalidate_ws_transport(exc, generation=generation)
                raise
            return time.monotonic() - started

        exc = TransportSendDeadlineExceeded(
            f"websocket send exceeded {_WS_SEND_DEADLINE_S:.3f}s deadline"
        )
        await self._invalidate_ws_transport(exc, generation=generation)
        try:
            await asyncio.wait_for(
                asyncio.shield(send_task),
                timeout=_WS_SEND_ABORT_GRACE_S,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            send_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await send_task
        except Exception:
            pass
        raise exc

    async def _invalidate_ws_transport(self, exc: Exception, *, generation: int) -> None:
        if generation != self._active_generation():
            return
        self._connected = False
        self._ws_transport_healthy = False
        self._fail_pending_rpc(exc, generation=generation)
        ws = self._ws
        if ws is None:
            return
        transport = getattr(ws, "transport", None)
        abort = getattr(transport, "abort", None)
        if callable(abort):
            abort()
            return
        close = getattr(ws, "close", None)
        if not callable(close):
            return
        try:
            await asyncio.wait_for(
                close(code=1011, reason="bounded websocket send failed"),
                timeout=_WS_SEND_ABORT_GRACE_S,
            )
        except Exception:
            logger.debug("websocket close after send failure did not complete", exc_info=True)

    def _ensure_ws_writer_task(self, *, generation: int | None = None) -> None:
        self._ensure_ws_writer_state()
        expected_generation = generation or self._active_generation()
        if not expected_generation or expected_generation != self._active_generation():
            raise ConnectionError("stale websocket transport generation")
        task = self._ws_writer_task
        if task is None or task.done():
            self._ws_writer_task = self._create_generation_task(
                self._ws_writer_loop(expected_generation),
                generation=expected_generation,
                label="serialized-ws-writer",
            )

    def _fail_queued_ws_sends(
        self,
        exc: Exception,
        *,
        generation: int | None = None,
    ) -> None:
        self._ensure_ws_writer_state()
        for traffic_class, queue in self._ws_send_queues.items():
            retained: deque[_WsSendEntry] = deque()
            while queue:
                entry = queue.popleft()
                if generation is not None and entry.generation != generation:
                    retained.append(entry)
                    continue
                if not entry.future.done():
                    entry.future.set_exception(exc)
                self._ws_send_queue_bytes[traffic_class] = max(
                    0,
                    self._ws_send_queue_bytes[traffic_class] - entry.payload_bytes,
                )
            queue.extend(retained)

    def _fail_pending_rpc(self, exc: Exception, *, generation: int | None = None) -> None:
        self._ensure_ws_writer_state()
        for msg_id, future in list(self._pending_rpc.items()):
            expected_generation = self._pending_rpc_generations.get(msg_id)
            if generation is not None and expected_generation != generation:
                continue
            self._pending_rpc.pop(msg_id, None)
            self._pending_rpc_generations.pop(msg_id, None)
            if not future.done():
                future.set_result({"ok": False, "error": str(exc), "retryable": True})

    async def _stop_ws_writer(self) -> None:
        self._ensure_ws_writer_state()
        self._ws_transport_healthy = False
        self._fail_queued_ws_sends(ConnectionError("node websocket writer stopped"))
        self._fail_pending_rpc(ConnectionError("node websocket writer stopped"))
        task = self._ws_writer_task
        self._ws_writer_task = None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _send_ws(
        self,
        payload: str | bytes,
        *,
        traffic_class: str = _TRAFFIC_REQUIRED_CONTROL,
        generation: int | None = None,
    ) -> dict[str, Any]:
        self._ensure_ws_writer_state()
        context_generation = _connection_generation_context.get()
        expected_generation = generation or context_generation or self._active_generation()
        if (
            self._ws is None
            or not self._ws_transport_healthy
            or not expected_generation
            or expected_generation != self._active_generation()
        ):
            raise ConnectionError("node websocket not connected")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        normalized_class = self._normalize_traffic_class(traffic_class)
        try:
            self._queue_ws_send(
                payload,
                traffic_class=normalized_class,
                future=future,
                generation=expected_generation,
            )
        except TransportQueueOverload as exc:
            if normalized_class in {
                _TRAFFIC_AUTHORITY_CONTROL,
                _TRAFFIC_REQUIRED_CONTROL,
            }:
                await self._invalidate_ws_transport(exc, generation=expected_generation)
                self._fail_queued_ws_sends(exc)
            raise
        self._ensure_ws_writer_task(generation=expected_generation)
        try:
            return await future
        except asyncio.CancelledError:
            future.cancel()
            raise

    def _build_capabilities(self) -> list[dict[str, str]]:
        caps = []
        cap_cfg = self._config.capabilities
        default_risk = "reversible_write"
        default_max = "irreversible_write"

        if "shell" in self._adapters:
            cfg = cap_cfg.get("shell")
            caps.append(
                {
                    "name": "shell",
                    "category": "compute",
                    "risk_class": default_risk,
                    "max_risk_class": cfg.max_risk_class if cfg else default_max,
                }
            )

        if "filesystem" in self._adapters:
            cfg = cap_cfg.get("filesystem")
            caps.append(
                {
                    "name": "filesystem",
                    "category": "compute",
                    "risk_class": "read_only",
                    "max_risk_class": cfg.max_risk_class if cfg else default_max,
                }
            )

        if "desktop" in self._adapters:
            cfg = cap_cfg.get("desktop")
            caps.append(
                {
                    "name": "desktop",
                    "category": "compute",
                    "risk_class": default_risk,
                    "max_risk_class": cfg.max_risk_class if cfg else default_max,
                }
            )

        if "clipboard" in self._adapters:
            cfg = cap_cfg.get("clipboard")
            caps.append(
                {
                    "name": "clipboard",
                    "category": "compute",
                    "risk_class": "read_only",
                    "max_risk_class": cfg.max_risk_class if cfg else "safe_write",
                }
            )

        if "camera" in self._adapters:
            cfg = cap_cfg.get("camera")
            caps.append(
                {
                    "name": "camera",
                    "category": "media",
                    "risk_class": "read_only",
                    "max_risk_class": cfg.max_risk_class if cfg else "read_only",
                }
            )

        if "broadcast" in self._adapters:
            caps.append(
                {
                    "name": "broadcast",
                    "category": "media",
                    "risk_class": "reversible_write",
                    "max_risk_class": "external_communication",
                }
            )

        if "terminal" in self._adapters:
            caps.append(
                {
                    "name": "terminal",
                    "category": "compute",
                    "risk_class": "reversible_write",
                    "max_risk_class": "irreversible_write",
                }
            )

        return caps

    async def run(self) -> None:
        """Main loop — connect with exponential backoff, handle messages."""
        self._loop = asyncio.get_running_loop()
        self._ws_send_lock = asyncio.Lock()
        backoff = 1.0
        max_backoff = self._config.reconnect_max_backoff_s

        while not self._shutdown.is_set():
            try:
                await self._connect_and_serve()
                backoff = 1.0
            except (
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            ) as exc:
                logger.warning("connection lost: %s, reconnecting in %.0fs", exc, backoff)
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            except asyncio.CancelledError:
                break
            except TransportGenerationTeardownFailed:
                self._connected = False
                self._shutdown.set()
                raise
            except Exception as exc:
                logger.error("unexpected error: %s, reconnecting in %.0fs", exc, backoff)
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def stop(self) -> None:
        self._shutdown.set()
        generation = self._active_generation()
        ws = self._ws
        if generation and ws is not None:
            await self._teardown_connection_generation(generation, ws)
        await self._quiesce_logical_executions()
        for name, adapter in list(self._adapters.items()):
            try:
                if name == "camera":
                    adapter.execute("camera.stream_stop", {})
                elif hasattr(adapter, "shutdown"):
                    adapter.shutdown()
                elif hasattr(adapter, "stop"):
                    adapter.stop()
            except Exception as exc:  # noqa: BLE001
                logger.debug("adapter shutdown failed for %s: %s", name, exc)
        self._camera_executor.shutdown(wait=False, cancel_futures=True)
        if ws:
            await ws.close()

    async def _quiesce_logical_executions(self) -> None:
        registry = getattr(self, "_durable_logical_executions", {})
        tasks = {
            entry["task"]
            for entry in registry.values()
            if isinstance(entry.get("task"), asyncio.Task) and not entry["task"].done()
        }
        if not tasks:
            return
        done, pending = await asyncio.wait(tasks, timeout=_LOGICAL_EXECUTION_TEARDOWN_S)
        if done:
            await asyncio.gather(*done, return_exceptions=True)
        for request_id, entry in registry.items():
            task = entry.get("task")
            if task not in pending:
                continue
            entry["state"] = "OUTCOME_UNKNOWN"
            try:
                self._durable_store.mark_reconciliation_required(
                    request_id,
                    reason="node shutdown before logical execution outcome was observed",
                    cleanup={
                        "process_residue": [{"state": "execution_outcome_unresolved"}],
                        "execution_outcome_unknown": True,
                    },
                )
            except (KeyError, ValueError):
                logger.exception(
                    "failed to persist logical execution shutdown state: %s", request_id
                )
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def _connect_and_serve(self) -> None:
        url = self._config.ws_url
        logger.info("connecting to %s", url.split("?")[0])

        # Token travels in the Authorization header, never in the URL.
        async with websockets.connect(
            url,
            ping_interval=120,
            ping_timeout=60,
            max_size=4 * 1024 * 1024,
            additional_headers=self._config.auth_header,
        ) as ws:
            generation = self._activate_connection_generation(ws)
            self._ensure_ws_writer_task(generation=generation)
            try:
                await self._send_hello()
                self._connected = True
                self._media_queue.clear()
                logger.info("connected to VPS mesh server")

                self._create_generation_task(
                    self._heartbeat_loop(),
                    generation=generation,
                    label="heartbeat",
                )
                self._media_drain_task = self._create_generation_task(
                    self._media_drain_loop(),
                    generation=generation,
                    label="media-drain",
                )
                self._create_generation_task(
                    self._workspace_emission_loop(),
                    generation=generation,
                    label="workspace-emission",
                )
                self._create_generation_task(
                    self._terminal_result_replay_loop(generation),
                    generation=generation,
                    label="terminal-result-replay",
                )
                reader = self._create_generation_task(
                    self._read_ws_loop(ws, generation),
                    generation=generation,
                    label="websocket-reader",
                )
                await reader
            finally:
                await self._teardown_connection_generation(generation, ws)
                self._ws = None

    async def _read_ws_loop(self, ws: Any, generation: int) -> None:
        async for raw in ws:
            if generation != self._active_generation():
                raise ConnectionError("stale websocket reader generation")
            await self._handle_message(raw, generation=generation)

    async def _send_hello(self) -> None:
        hostname = self._config.hostname or socket.gethostname()
        loop = asyncio.get_running_loop()
        peripherals = await loop.run_in_executor(None, scan_all_peripherals, True)
        msg = {
            "jsonrpc": "2.0",
            "method": "node.hello",
            "params": {
                "node_id": self._config.node_id,
                "hostname": hostname,
                "os": platform.system().lower(),
                "os_version": platform.version(),
                "capabilities": self._build_capabilities(),
                "peripherals": peripherals,
                "peripheral_scan_age_s": 0,
                "daemon_version": "0.2.0",
                "tailscale_ip": self._get_tailscale_ip(),
            },
            "id": self._next_id(),
        }
        await self._send_ws(json.dumps(msg))
        resp = json.loads(await self._ws.recv())
        result = resp.get("result", {})
        if result.get("accepted"):
            server_interval = result.get("heartbeat_interval_s")
            if server_interval and isinstance(server_interval, (int, float)):
                self._heartbeat_interval = int(server_interval)
            else:
                self._heartbeat_interval = self._config.signals.metrics_interval_s
            logger.info("node.hello accepted, heartbeat every %ds", self._heartbeat_interval)
        else:
            error = resp.get("error", {}).get("message", "unknown")
            raise ConnectionError(f"node.hello rejected: {error}")

    async def rescan_peripherals(self) -> list[dict[str, Any]]:
        """Rescan peripherals and notify the server of changes."""
        loop = asyncio.get_running_loop()
        peripherals = await loop.run_in_executor(
            None,
            scan_all_peripherals,
            True,
        )
        if self._connected and self._ws is not None:
            try:
                await self._send_ws(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "method": "node.peripherals_changed",
                            "params": {
                                "peripherals": peripherals,
                                "scan_age_s": get_scan_age_s(),
                            },
                            "id": self._next_id(),
                        }
                    )
                )
                logger.info("peripherals_changed sent: %d devices", len(peripherals))
            except Exception as exc:
                logger.warning("failed to send peripherals_changed: %s", exc)
        return peripherals

    async def _heartbeat_loop(self) -> None:
        """Control plane heartbeat — runs independently of media plane."""
        interval = getattr(self, "_heartbeat_interval", self._config.signals.metrics_interval_s)
        while True:
            await asyncio.sleep(interval)
            try:
                metrics = collect_metrics()
                msg = {
                    "jsonrpc": "2.0",
                    "method": "node.heartbeat",
                    "params": {"metrics": metrics},
                    "id": self._next_id(),
                }
                await self._send_ws(json.dumps(msg))
            except Exception as exc:
                logger.warning("heartbeat send failed: %s", exc)
                break

    async def _workspace_emission_loop(self) -> None:
        """Emit workstation state to VPS when it changes. Control plane signal."""
        if not self._config.signals.workspace_enabled:
            logger.info("workspace emission disabled by config")
            return

        interval = max(self._config.signals.workspace_debounce_s, 2.0)
        last_hash = ""
        loop = asyncio.get_running_loop()

        while True:
            await asyncio.sleep(interval)
            try:
                state = await loop.run_in_executor(None, collect_workstation_state)
                h = _state_hash(state)
                if h == last_hash:
                    continue
                last_hash = h
                state["device_id"] = self._config.node_id
                await self.emit_signal(
                    content_type="workstation.state",
                    payload=state,
                    signal_class="workstation_state",
                    urgency="LOW",
                )
            except Exception as exc:
                logger.debug("workspace emission failed: %s", exc)

    async def _handle_message(self, raw: str, *, generation: int | None = None) -> None:
        msg = json.loads(raw)
        method = msg.get("method", "")
        expected_generation = generation or self._active_generation()

        if method == "capability.execute":
            self._create_generation_task(
                self._safe_handle_capability(msg),
                generation=expected_generation,
                label="capability-handler",
            )
        elif method == "durable_command.request":
            self._schedule_logical_durable_command(msg)
        elif method == "outcome.notify":
            logger.info("outcome received: %s", msg.get("params", {}).get("summary", ""))
        elif "result" in msg or "error" in msg:
            self._handle_rpc_response(msg, generation=expected_generation)
        else:
            logger.debug("unhandled message method: %s", method)

    def _handle_rpc_response(
        self,
        msg: dict[str, Any],
        *,
        generation: int | None = None,
    ) -> None:
        self._ensure_ws_writer_state()
        msg_id = msg.get("id")
        future = self._pending_rpc.get(msg_id)
        if future is None or future.done():
            return
        expected_generation = self._pending_rpc_generations.get(msg_id)
        response_generation = generation or self._active_generation()
        if expected_generation is None or expected_generation != response_generation:
            logger.warning(
                "ignored RPC response without current websocket generation binding: "
                "id=%s expected=%s current=%s",
                msg_id,
                expected_generation,
                response_generation,
            )
            return
        self._pending_rpc.pop(msg_id, None)
        self._pending_rpc_generations.pop(msg_id, None)
        if "error" in msg:
            future.set_result({"ok": False, "error": msg.get("error")})
            return
        result = msg.get("result", {})
        future.set_result(result if isinstance(result, dict) else {"ok": False, "error": result})

    def _effective_write_class(self, cap_name: str, wire_risk_class: str) -> bool:
        """Decide whether a capability is write-class for verdict purposes.

        Write-class if EITHER the caller-declared wire risk class OR the
        capability's own configured max_risk_class is not read-only. This stops
        a caller from downgrading a write-class capability to "read_only" to
        skip the verdict (fail-closed against risk downgrade).
        """
        from substrate.execution.mesh_verdict import is_write_class

        if is_write_class(wire_risk_class):
            return True
        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        cap_config = self._config.capabilities.get(adapter_key)
        if cap_config is not None and is_write_class(cap_config.max_risk_class):
            return True
        return False

    def _validate_verdict(
        self,
        cap_name: str,
        risk_class: str,
        verdict_token: str,
        *,
        request_id: str = "",
        correlation_id: str = "",
        candidate_sha: str = "",
        effect_class: str = "",
        payload_digest: str = "",
        idempotency_key: str = "",
        cap_params: dict[str, Any] | None = None,
        allow_consequential_write: bool = False,
    ) -> tuple[bool, str]:
        """Validate sync effect or DurableRemote verdict before adapter execution.

        Synchronous capability.execute may only run explicit READ_ONLY work.
        Write-class capability execution is allowed only when the caller is the
        DurableRemote execution path, which has already proven canonical
        request authority and passes allow_consequential_write=True.
        """
        try:
            from substrate.execution.mesh_verdict import (
                CONSEQUENTIAL_WRITE_EFFECT,
                canonical_sync_effect_policy,
                canonical_payload_digest,
                get_verdict_secret,
                is_write_class,
                READ_ONLY_EFFECT,
                verify_verdict,
            )
        except Exception as exc:  # pragma: no cover - defensive import guard
            return False, f"sync effect classifier unavailable: {exc}"

        policy = canonical_sync_effect_policy(cap_name, declared_effect_class=effect_class)
        normalized_effect = policy.declared_effect_class
        authoritative_effect = policy.authoritative_effect_class

        if not allow_consequential_write:
            if not normalized_effect:
                return False, "sync capability requires explicit known effect_class"
            if normalized_effect != authoritative_effect:
                return False, f"sync effect policy mismatch: {policy.reason}"
            if not policy.sync_allowed:
                return False, policy.reason
            if authoritative_effect != READ_ONLY_EFFECT:
                return False, "sync capability execution is restricted to READ_ONLY"
            if is_write_class(risk_class):
                return False, "sync read-only capability requires read_only risk"
            if not request_id or not correlation_id or not idempotency_key:
                return False, "sync capability requires exact operation binding"
            expected_digest = canonical_payload_digest(cap_params or {})
            if not payload_digest or payload_digest != expected_digest:
                return False, "payload digest mismatch"
            return True, "read-only sync capability, no verdict required"

        # DurableRemote has already proven canonical durable request authority.
        # The verdict still binds the consequential operation identity and the
        # UMH-owned policy identity; synchronous receiver policy never
        # authorizes this path.
        if not authoritative_effect:
            return False, "capability has no canonical effect policy"
        if authoritative_effect == READ_ONLY_EFFECT:
            return (
                False,
                "DurableRemote consequential execution requires canonical consequential policy",
            )
        if normalized_effect != CONSEQUENTIAL_WRITE_EFFECT:
            return False, "write-class capability requires CONSEQUENTIAL_WRITE effect binding"
        if not is_write_class(risk_class):
            return (
                False,
                "write-class capability risk_class conflicts with canonical consequential policy",
            )

        if not get_verdict_secret():
            return False, "no mesh verdict secret configured on node (fail-closed)"
        if not verdict_token:
            return False, "write-class capability requires a governance verdict"
        if not request_id or not correlation_id or not idempotency_key:
            return False, "write-class capability requires exact operation binding"
        expected_digest = canonical_payload_digest(cap_params or {})
        if not payload_digest or payload_digest != expected_digest:
            return False, "payload digest mismatch"

        check = verify_verdict(
            verdict_token,
            expected_node_id=self._config.node_id,
            expected_capability=cap_name,
            expected_risk_class=risk_class,
            expected_request_id=request_id,
            expected_correlation_id=correlation_id,
            expected_candidate_sha=candidate_sha,
            expected_effect_class=normalized_effect,
            expected_authoritative_effect_class=authoritative_effect,
            expected_effect_policy=policy.policy_id,
            expected_payload_digest=expected_digest,
            expected_idempotency_key=idempotency_key,
        )
        if not check.valid:
            return False, check.reason
        return True, "verdict valid"

    async def _safe_handle_capability(self, msg: dict[str, Any]) -> None:
        try:
            await self._handle_capability(msg)
        except Exception as exc:
            logger.error("capability handler crashed: %s", exc, exc_info=True)
            msg_id = msg.get("id")
            if msg_id and self._ws:
                try:
                    await self._send_ws(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "result": {"success": False, "error": f"internal error: {exc}"},
                                "id": msg_id,
                            }
                        )
                    )
                except Exception:
                    pass

    async def _safe_handle_durable_command(self, msg: dict[str, Any]) -> None:
        try:
            await self._handle_durable_command(msg)
        except Exception as exc:  # noqa: BLE001
            logger.error("durable command handler crashed: %s", exc, exc_info=True)

    def _schedule_logical_durable_command(self, msg: dict[str, Any]) -> None:
        """Own authorized execution independently from a WebSocket generation."""
        params = msg.get("params", {})
        if not isinstance(params, dict):
            logger.warning("durable delivery rejected: params must be an object")
            return
        try:
            delivered_req = DurableRemoteRequest.from_dict(params)
        except (TypeError, ValueError) as exc:
            logger.warning("durable delivery rejected: malformed request material: %s", exc)
            return
        if not delivered_req.request_id or delivered_req.node_id != self._config.node_id:
            return

        registry = getattr(self, "_durable_logical_executions", None)
        if registry is None:
            registry = {}
            self._durable_logical_executions = registry
        existing = registry.get(delivered_req.request_id)
        if existing is not None:
            if existing.get("identity") != self._durable_request_identity(delivered_req):
                logger.error(
                    "durable logical execution identity mismatch: %s",
                    delivered_req.request_id,
                )
                return
            if delivered_req.lifecycle_state == "CANCEL_REQUESTED":
                if not self._durable_cancel_matches_active_execution(
                    delivered_req,
                    logical=existing,
                ):
                    self._record_rejected_durable_control(
                        delivered_req,
                        reason="cancel execution identity mismatch",
                    )
                    return
                current = self._durable_store.put_request(delivered_req)
                current.lifecycle_state = "CANCEL_REQUESTED"
                current.cancellation_requested_at = delivered_req.cancellation_requested_at
                current.cancellation_deadline_at = delivered_req.cancellation_deadline_at
                self._durable_store.update_request(current, "CANCEL_REQUESTED")
                existing["cancel_requested"] = True
            task = existing.get("task")
            if isinstance(task, asyncio.Task) and not task.done():
                return
            if existing.get("state") in {"STARTED", "OUTCOME_UNKNOWN"}:
                return

        entry: dict[str, Any] = {
            "identity": self._durable_request_identity(delivered_req),
            "state": "NOT_STARTED",
            "task": None,
            "operation_future": None,
            "execution_identity": None,
            "outcome_state": "UNKNOWN",
            "created_at": time.monotonic(),
        }
        registry[delivered_req.request_id] = entry

        async def _run() -> None:
            token = _connection_generation_context.set(None)
            try:
                await self._safe_handle_durable_command(msg)
            finally:
                _connection_generation_context.reset(token)

        task = asyncio.create_task(_run(), context=contextvars.Context())
        entry["task"] = task

        def _completed(done: asyncio.Task[None]) -> None:
            current_entry = registry.get(delivered_req.request_id)
            if current_entry is not entry:
                return
            try:
                failure = done.exception()
            except asyncio.CancelledError as exc:
                failure = exc
            result = self._durable_store.result_for(delivered_req.request_id)
            if result is not None:
                entry["state"] = "TERMINAL_PERSISTED"
                registry.pop(delivered_req.request_id, None)
                return
            current = self._durable_store.get_request(delivered_req.request_id)
            if entry.get("state") in {"STARTED", "OUTCOME_UNKNOWN"} or (
                current is not None and current.lifecycle_state in {"RUNNING", "CANCEL_REQUESTED"}
            ):
                reason = "logical execution observer ended before actual outcome was persisted"
                if failure is not None:
                    reason += f": {type(failure).__name__}: {failure}"
                try:
                    self._durable_store.mark_reconciliation_required(
                        delivered_req.request_id,
                        reason=reason,
                        cleanup={
                            "process_residue": [{"state": "execution_outcome_unresolved"}],
                            "execution_outcome_unknown": True,
                        },
                    )
                except (KeyError, ValueError):
                    logger.exception(
                        "failed to preserve unresolved logical execution: %s",
                        delivered_req.request_id,
                    )
                entry["state"] = "OUTCOME_UNKNOWN"
                return
            registry.pop(delivered_req.request_id, None)

        task.add_done_callback(_completed)

    def _durable_request_identity(self, req: DurableRemoteRequest) -> dict[str, str]:
        return {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "node_id": req.node_id,
            "candidate_sha": req.candidate_sha,
            "idempotency_key": req.idempotency_key,
            "payload_digest": req.payload_digest,
        }

    def _durable_execution_identity(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
    ) -> dict[str, Any]:
        return durable_execution_identity(req, claim_id=claim_id)

    def _durable_cancel_matches_active_execution(
        self,
        delivered_req: DurableRemoteRequest,
        *,
        logical: dict[str, Any] | None = None,
    ) -> bool:
        current = self._durable_store.get_request(delivered_req.request_id)
        if current is None:
            return True
        if self._durable_request_identity(current) != self._durable_request_identity(delivered_req):
            return False
        execution_identity = dict(
            (logical or {}).get("execution_identity")
            or current.process_tree.get("execution_identity")
            or {}
        )
        active_claim_id = str(
            execution_identity.get("claim_id")
            or (logical or {}).get("claim_id")
            or current.claim_id
            or ""
        )
        if not active_claim_id:
            return not delivered_req.claim_id
        if str(delivered_req.claim_id or "") != active_claim_id:
            return False
        if not execution_identity:
            execution_identity = self._durable_execution_identity(
                current,
                claim_id=active_claim_id,
            )
        incoming_identity = self._durable_execution_identity(
            delivered_req,
            claim_id=active_claim_id,
        )
        return incoming_identity == execution_identity

    def _record_rejected_durable_control(
        self,
        delivered_req: DurableRemoteRequest,
        *,
        reason: str,
    ) -> None:
        current = self._durable_store.get_request(delivered_req.request_id)
        if current is None:
            return
        logical = getattr(self, "_durable_logical_executions", {}).get(delivered_req.request_id)
        active_identity = dict((logical or {}).get("execution_identity") or {})
        self._durable_store.record_transport_diagnostic(
            delivered_req.request_id,
            "STALE_OR_FOREIGN_EXECUTION_CONTROL_REJECTED",
            {
                "reason": reason,
                "incoming_claim_id": delivered_req.claim_id,
                "active_claim_id": active_identity.get("claim_id", current.claim_id),
                "execution_id": active_identity.get("execution_id", ""),
            },
        )

    @staticmethod
    def _durable_trajectory_identity_matches(
        trajectory: dict[str, Any], req: DurableRemoteRequest
    ) -> bool:
        identity = dict(trajectory.get("identity") or {})
        for key in (
            "request_id",
            "correlation_id",
            "node_id",
            "candidate_sha",
            "idempotency_key",
            "payload_digest",
        ):
            if str(identity.get(key, "")) != str(getattr(req, key, "")):
                return False
        return True

    def _prune_durable_request_trajectories(self) -> None:
        trajectories = getattr(self, "_durable_request_trajectories", None)
        if not trajectories:
            return
        now = time.monotonic()
        for request_id, trajectory in list(trajectories.items()):
            if trajectory.get("refs", 0) > 0:
                continue
            retain_until = float(trajectory.get("retain_until", 0.0) or 0.0)
            if retain_until and retain_until <= now:
                trajectories.pop(request_id, None)
        if len(trajectories) <= _DURABLE_TRAJECTORY_MAX:
            return
        terminal = [
            (float(trajectory.get("updated_at", 0.0) or 0.0), request_id)
            for request_id, trajectory in trajectories.items()
            if trajectory.get("refs", 0) <= 0
            and trajectory.get("status")
            in {"FAIL_CLOSED", "TERMINAL_OBSERVED", "RECONCILIATION_PENDING"}
        ]
        for _, request_id in sorted(terminal)[
            : max(0, len(trajectories) - _DURABLE_TRAJECTORY_MAX)
        ]:
            trajectories.pop(request_id, None)

    def _durable_request_trajectory(self, req: DurableRemoteRequest) -> dict[str, Any]:
        trajectories = getattr(self, "_durable_request_trajectories", None)
        if trajectories is None:
            trajectories = {}
            self._durable_request_trajectories = trajectories
        self._prune_durable_request_trajectories()
        trajectory = trajectories.get(req.request_id)
        if trajectory is None:
            now = time.monotonic()
            trajectory = {
                "lock": asyncio.Lock(),
                "refs": 0,
                "identity": self._durable_request_identity(req),
                "status": "ACQUIRING",
                "claim_id": "",
                "created_at": now,
                "updated_at": now,
                "retain_until": now + _DURABLE_TRAJECTORY_TOMBSTONE_TTL_S,
            }
            trajectories[req.request_id] = trajectory
        return trajectory

    def _record_durable_request_trajectory(
        self,
        request_id: str,
        *,
        status: str,
        claim_id: str | None = None,
        terminal: bool = False,
    ) -> None:
        trajectories = getattr(self, "_durable_request_trajectories", None)
        if not trajectories:
            return
        trajectory = trajectories.get(request_id)
        if trajectory is None:
            return
        if claim_id:
            trajectory["claim_id"] = claim_id
        trajectory["status"] = status
        trajectory["updated_at"] = time.monotonic()
        if terminal:
            trajectory["retain_until"] = time.monotonic() + _DURABLE_TRAJECTORY_TOMBSTONE_TTL_S

    def _sync_durable_request_trajectory(
        self, trajectory: dict[str, Any], req: DurableRemoteRequest
    ) -> None:
        if req.claim_id and not trajectory.get("claim_id"):
            trajectory["claim_id"] = req.claim_id
        existing_status = str(trajectory.get("status", "") or "")
        if existing_status in {
            "FAIL_CLOSED",
            "RECONCILIATION_PENDING",
        } and req.lifecycle_state not in {"RUNNING", *TERMINAL_STATES}:
            trajectory["updated_at"] = time.monotonic()
            return
        if req.lifecycle_state == "RUNNING":
            trajectory["status"] = "RUNNING_OR_RECONCILING"
        elif req.lifecycle_state in TERMINAL_STATES:
            trajectory["status"] = "TERMINAL_OBSERVED"
            trajectory["retain_until"] = time.monotonic() + _DURABLE_TRAJECTORY_TOMBSTONE_TTL_S
        elif req.lifecycle_state == "RECONCILIATION_REQUIRED":
            trajectory["status"] = "RECONCILIATION_PENDING"
            trajectory["retain_until"] = time.monotonic() + _DURABLE_TRAJECTORY_TOMBSTONE_TTL_S
        elif req.lifecycle_state == "CLAIMED":
            trajectory["status"] = "ACQUIRING"
        trajectory["updated_at"] = time.monotonic()

    async def _with_durable_request_gate(
        self, delivered_req: DurableRemoteRequest, handler: Callable[[dict[str, Any]], Any]
    ) -> None:
        """Coalesce redeliveries of one durable request without becoming authority."""
        request_id = delivered_req.request_id
        trajectory = self._durable_request_trajectory(delivered_req)
        gates = getattr(self, "_durable_request_gates", None)
        if gates is None:
            gates = {}
            self._durable_request_gates = gates
        gate = gates.get(request_id)
        if gate is None:
            gate = {"lock": trajectory["lock"], "refs": 0}
            gates[request_id] = gate
        gate["refs"] += 1
        trajectory["refs"] = int(trajectory.get("refs", 0) or 0) + 1
        lock = trajectory["lock"]
        try:
            async with lock:
                try:
                    await handler(trajectory)
                except asyncio.CancelledError as exc:
                    await self._fail_interrupted_durable_request_trajectory(
                        delivered_req,
                        trajectory=trajectory,
                        exc=exc,
                    )
                    raise
                except Exception as exc:  # noqa: BLE001
                    await self._fail_interrupted_durable_request_trajectory(
                        delivered_req,
                        trajectory=trajectory,
                        exc=exc,
                    )
        finally:
            gate["refs"] -= 1
            trajectory["refs"] = max(0, int(trajectory.get("refs", 0) or 0) - 1)
            if gate["refs"] <= 0 and gates.get(request_id) is gate:
                gates.pop(request_id, None)
            self._prune_durable_request_trajectories()

    async def _fail_interrupted_durable_request_trajectory(
        self,
        delivered_req: DurableRemoteRequest,
        *,
        trajectory: dict[str, Any],
        exc: BaseException,
    ) -> None:
        """Terminalize an interrupted local trajectory without granting authority."""
        current = self._durable_store.get_request(delivered_req.request_id) or delivered_req
        existing = self._durable_store.result_for(delivered_req.request_id)
        if existing:
            self._record_durable_request_trajectory(
                delivered_req.request_id,
                status="TERMINAL_OBSERVED",
                claim_id=str(existing.get("claim_id", "")),
                terminal=True,
            )
            return
        reason = (
            "durable request trajectory interrupted before governed outcome: "
            f"{type(exc).__name__}: {exc}"
        )
        claim_id = str(trajectory.get("claim_id", "") or current.claim_id or "")
        root_pid = current.process_tree.get("root_pid")
        proc = self._durable_processes.get(delivered_req.request_id)
        if current.lifecycle_state == "RUNNING" or root_pid or proc is not None:
            logical = getattr(self, "_durable_logical_executions", {}).get(delivered_req.request_id)
            operation_future = (logical or {}).get("operation_future")
            if (
                (logical or {}).get("state") == "STARTED"
                and operation_future is not None
                and operation_future.done()
                and not operation_future.cancelled()
            ):
                terminal = await self._persist_completed_logical_execution_outcome(
                    current,
                    logical=logical,
                    claim_id=claim_id or current.claim_id,
                )
                if terminal is not None:
                    return
            if (logical or {}).get("state") == "STARTED" and (
                operation_future is None
                or operation_future.cancelled()
                or not operation_future.done()
            ):
                logical["state"] = "OUTCOME_UNKNOWN"
                self._durable_store.mark_reconciliation_required(
                    current.request_id,
                    reason=reason,
                    cleanup={
                        "process_residue": [{"state": "execution_outcome_unresolved"}],
                        "execution_outcome_unknown": True,
                        "request_id": current.request_id,
                        "correlation_id": current.correlation_id,
                        "candidate_sha": current.candidate_sha,
                        "node_id": current.node_id,
                        "claim_id": claim_id or current.claim_id or "unclaimed",
                    },
                )
                self._record_durable_request_trajectory(
                    current.request_id,
                    status="RECONCILIATION_PENDING",
                    claim_id=claim_id,
                    terminal=True,
                )
                return
            if proc is None or proc.poll() is not None:
                self._durable_store.mark_reconciliation_required(
                    current.request_id,
                    reason=reason,
                    cleanup={
                        "process_residue": [
                            {"state": "execution_outcome_unresolved_after_observer_loss"}
                        ],
                        "execution_outcome_unknown": True,
                        "request_id": current.request_id,
                        "correlation_id": current.correlation_id,
                        "candidate_sha": current.candidate_sha,
                        "node_id": current.node_id,
                        "claim_id": claim_id or current.claim_id or "unclaimed",
                    },
                )
                self._record_durable_request_trajectory(
                    current.request_id,
                    status="RECONCILIATION_PENDING",
                    claim_id=claim_id,
                    terminal=True,
                )
                return
            cleanup: dict[str, Any] = {
                "process_residue": [],
                "interrupted_running_failed_closed": True,
                "request_id": current.request_id,
                "correlation_id": current.correlation_id,
                "node_id": current.node_id,
                "candidate_sha": current.candidate_sha,
                "claim_id": claim_id or current.claim_id or "unclaimed",
            }
            if proc is not None and proc.poll() is None:
                cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                cleanup["interrupted_running_failed_closed"] = True
                cleanup.update(
                    {
                        "request_id": current.request_id,
                        "correlation_id": current.correlation_id,
                        "node_id": current.node_id,
                        "candidate_sha": current.candidate_sha,
                        "claim_id": claim_id or current.claim_id or "unclaimed",
                    }
                )
            elif root_pid:
                cleanup["process_residue"] = [
                    {"pid": root_pid, "state": "running_interruption_unverified"}
                ]
            result = {
                "success": False,
                "error": "durable running trajectory interrupted",
                "reason": reason,
            }
            terminal = self._durable_store.publish_result(
                current.request_id,
                claim_id=claim_id or current.claim_id or "unclaimed",
                state="FAILED",
                result=result,
                cleanup=cleanup,
            )
            self._record_durable_request_trajectory(
                current.request_id,
                status="FAIL_CLOSED",
                claim_id=terminal.claim_id,
                terminal=True,
            )
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": terminal.request_id,
                    "claim_id": terminal.claim_id,
                    "state": terminal.lifecycle_state,
                    "result": result,
                    "cleanup": cleanup,
                },
            )
            return
        if claim_id and claim_id != "unclaimed":
            await self._fail_durable_claim_acquisition(
                current,
                claim_id=claim_id,
                reason=reason,
            )
            return
        await self._fail_unresolved_durable_request(current, reason=reason)

    async def _persist_completed_logical_execution_outcome(
        self,
        req: DurableRemoteRequest,
        *,
        logical: dict[str, Any],
        claim_id: str,
    ) -> DurableRemoteRequest | None:
        operation = logical.get("operation_future")
        if operation is None or not operation.done() or operation.cancelled():
            return None
        try:
            observed = operation.result()
        except Exception as exc:  # noqa: BLE001
            result: dict[str, Any] = {
                "success": False,
                "error": f"adapter execution failed: {type(exc).__name__}: {exc}",
            }
        else:
            if isinstance(observed, dict):
                result = dict(observed)
            else:
                result = {
                    "success": False,
                    "error": "adapter returned non-object execution outcome",
                }
        state = "SUCCEEDED" if result.get("success") else "FAILED"
        cleanup = dict(result.get("cleanup") or {"process_residue": []})
        terminal = self._durable_store.publish_result(
            req.request_id,
            claim_id=claim_id,
            state=state,
            result=result,
            cleanup=cleanup,
        )
        logical["state"] = "TERMINAL_PERSISTED"
        logical["outcome_state"] = state
        self._record_durable_request_trajectory(
            req.request_id,
            status="TERMINAL_OBSERVED",
            claim_id=claim_id,
            terminal=True,
        )
        await self._send_durable_event(
            "durable_command.result",
            {
                "request_id": req.request_id,
                "claim_id": claim_id,
                "state": state,
                "result": result,
                "cleanup": cleanup,
            },
        )
        return terminal

    async def _fail_durable_trajectory_identity_mismatch(
        self,
        req: DurableRemoteRequest,
        *,
        trajectory: dict[str, Any],
    ) -> None:
        reason = "durable request trajectory identity mismatch"
        current = self._durable_store.get_request(req.request_id) or req
        if self._durable_store.get_request(req.request_id) is None:
            current = self._durable_store.put_request(req)
        if current.claim_id:
            await self._fail_durable_claim_acquisition(
                current,
                claim_id=current.claim_id,
                reason=reason,
            )
            return
        current.cleanup = {
            "process_residue": [],
            "trajectory_identity_mismatch_failed_closed": True,
            "request_id": current.request_id,
            "correlation_id": current.correlation_id,
            "node_id": current.node_id,
            "candidate_sha": current.candidate_sha,
        }
        self._durable_store.update_request(current, "TRAJECTORY_IDENTITY_MISMATCH")
        await self._fail_unresolved_durable_request(
            current,
            reason=reason,
            no_execution_proven=True,
        )

    def _canonical_terminal_result_payload(self, request_id: str) -> dict[str, Any]:
        delivery = self._durable_store.stage_terminal_result_delivery(request_id)
        result = self._durable_store.result_for(request_id)
        request = self._durable_store.get_request(request_id)
        if result is None or request is None:
            raise ValueError("terminal result delivery material is unavailable")
        if request.lifecycle_state not in TERMINAL_STATES | {"RECONCILIATION_REQUIRED"}:
            raise ValueError("terminal result delivery request is not terminal evidence")
        if result.get("result_digest") != delivery.get("result_digest"):
            raise ValueError("terminal result delivery digest mismatch")
        if delivery.get("delivery_state") == "RECONCILIATION_REQUIRED":
            raise ValueError("terminal result delivery requires governed reconciliation")
        return {
            "request_id": request.request_id,
            "correlation_id": request.correlation_id,
            "candidate_sha": request.candidate_sha,
            "node_id": request.node_id,
            "claim_id": str(result.get("claim_id", "") or ""),
            "state": str(result.get("state", "") or ""),
            "result": dict(result.get("result") or {}),
            "cleanup": dict(result.get("cleanup") or {}),
            "result_id": str(delivery.get("result_id", "") or ""),
            "result_digest": str(delivery.get("result_digest", "") or ""),
            "idempotent_replay": True,
        }

    async def _terminal_result_replay_loop(self, generation: int) -> None:
        """Autonomously deliver due terminal evidence; never execute work."""
        while generation == self._active_generation() and self._connected:
            delivered = await self._replay_due_terminal_results(generation)
            if not delivered:
                await asyncio.sleep(_RESULT_REPLAY_IDLE_POLL_S)
                continue
            await asyncio.sleep(0)

    async def _replay_due_terminal_results(self, generation: int) -> int:
        pending = self._durable_store.pending_terminal_result_deliveries(
            limit=_RESULT_REPLAY_BATCH,
        )
        attempted = 0
        for delivery in pending:
            if generation != self._active_generation() or not self._connected:
                break
            request_id = str(delivery.get("request_id", "") or "")
            if not request_id:
                continue
            payload = self._canonical_terminal_result_payload(request_id)
            attempted += 1
            ack = await self._send_durable_event(
                "durable_command.result",
                payload,
                expect_ack=True,
                generation=generation,
            )
            if not isinstance(ack, dict) or ack.get("ok") is not True:
                if not self._ws_transport_healthy:
                    break
        return attempted

    async def _send_durable_event(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        expect_ack: bool = False,
        timeout_s: float = _CONTROL_TIMEOUT_S,
        generation: int | None = None,
    ) -> dict[str, Any] | None:
        if not self._connected or self._ws is None:
            return {"ok": False, "error": "node websocket not connected"} if expect_ack else None
        self._ensure_ws_writer_state()
        expected_generation = (
            generation or _connection_generation_context.get() or self._active_generation()
        )
        terminal_request_id = ""
        if method == "durable_command.result":
            terminal_request_id = str(payload.get("request_id", "") or "")
            try:
                payload = self._canonical_terminal_result_payload(terminal_request_id)
                self._durable_store.record_terminal_result_delivery_attempt(terminal_request_id)
            except (KeyError, ValueError) as exc:
                persisted_reconciliation_evidence = (
                    terminal_request_id
                    and self._durable_store.has_persisted_rejected_result_evidence(
                        terminal_request_id,
                        claim_id=str(payload.get("claim_id", "") or ""),
                        state=str(payload.get("state", "") or ""),
                        result=dict(payload.get("result") or {}),
                        cleanup=dict(payload.get("cleanup") or {}),
                    )
                )
                if persisted_reconciliation_evidence:
                    self._durable_store.record_transport_diagnostic(
                        terminal_request_id,
                        "RECONCILIATION_RESULT_EVIDENCE_SEND",
                        {"error": str(exc)},
                    )
                else:
                    if terminal_request_id:
                        self._durable_store.record_transport_diagnostic(
                            terminal_request_id,
                            "TERMINAL_RESULT_DELIVERY_REJECTED",
                            {"error": str(exc)},
                        )
                    return {"ok": False, "error": str(exc), "retryable": False}
            else:
                expect_ack = True
        msg_id = self._next_id()
        request_id = str(payload.get("request_id", "") or "")
        future: asyncio.Future[dict[str, Any]] | None = None
        if expect_ack:
            future = asyncio.get_running_loop().create_future()
            self._pending_rpc[msg_id] = future
            self._pending_rpc_generations[msg_id] = expected_generation
        message = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": payload,
                "id": msg_id,
            }
        )
        try:
            if request_id:
                self._durable_store.record_transport_diagnostic(
                    request_id,
                    "NODE_AUTHORITY_SEND_QUEUED",
                    {
                        "method": method,
                        "message_id": msg_id,
                        "traffic_class": _TRAFFIC_AUTHORITY_CONTROL,
                    },
                )
            send_evidence = await self._send_ws(
                message,
                traffic_class=_TRAFFIC_AUTHORITY_CONTROL,
                generation=expected_generation,
            )
            if request_id:
                self._durable_store.record_transport_diagnostic(
                    request_id,
                    "NODE_AUTHORITY_SEND_COMPLETED",
                    {
                        "method": method,
                        "message_id": msg_id,
                        "traffic_class": _TRAFFIC_AUTHORITY_CONTROL,
                        **send_evidence,
                    },
                )
            if not expect_ack or future is None:
                return None
            ack = await asyncio.wait_for(future, timeout=timeout_s)
            if request_id:
                self._durable_store.record_transport_diagnostic(
                    request_id,
                    "NODE_AUTHORITY_ACK_RECEIVED",
                    {"method": method, "message_id": msg_id},
                )
            if method == "durable_command.result" and terminal_request_id:
                try:
                    self._durable_store.mark_terminal_result_delivery_acknowledged(
                        terminal_request_id,
                        ack,
                    )
                except ValueError as exc:
                    self._durable_store.mark_terminal_result_delivery_reconciliation_required(
                        terminal_request_id,
                        reason=str(exc),
                        receipt=ack,
                    )
                    self._durable_store.record_transport_diagnostic(
                        terminal_request_id,
                        "TERMINAL_RESULT_RECEIPT_REJECTED",
                        {"message_id": msg_id, "error": str(exc)},
                    )
                    return {"ok": False, "error": str(exc), "retryable": False}
            return ack
        except (TransportQueueOverload, TransportSendDeadlineExceeded, ConnectionError) as exc:
            self._pending_rpc.pop(msg_id, None)
            self._pending_rpc_generations.pop(msg_id, None)
            if request_id:
                event = (
                    "NODE_AUTHORITY_CONTROL_OVERLOAD"
                    if isinstance(exc, TransportQueueOverload)
                    else "NODE_AUTHORITY_TRANSPORT_UNHEALTHY"
                )
                self._durable_store.record_transport_diagnostic(
                    request_id,
                    event,
                    {
                        "method": method,
                        "message_id": msg_id,
                        "traffic_class": _TRAFFIC_AUTHORITY_CONTROL,
                        "error": str(exc),
                        "generation": expected_generation,
                    },
                )
            if terminal_request_id:
                self._durable_store.record_terminal_result_delivery_attempt(
                    terminal_request_id,
                    error=str(exc),
                )
            return {"ok": False, "error": str(exc), "retryable": True}
        except asyncio.TimeoutError:
            self._pending_rpc.pop(msg_id, None)
            self._pending_rpc_generations.pop(msg_id, None)
            if request_id:
                self._durable_store.record_transport_diagnostic(
                    request_id,
                    "NODE_AUTHORITY_ACK_TIMEOUT",
                    {"method": method, "message_id": msg_id, "timeout_s": timeout_s},
                )
            if terminal_request_id:
                self._durable_store.record_terminal_result_delivery_attempt(
                    terminal_request_id,
                    error=f"{method} acknowledgement timed out",
                )
            return {"ok": False, "error": f"{method} acknowledgement timed out"}
        except BaseException:
            if expect_ack:
                self._pending_rpc.pop(msg_id, None)
                self._pending_rpc_generations.pop(msg_id, None)
            raise

    async def _handle_durable_command(self, msg: dict[str, Any]) -> None:
        params = msg.get("params", {})
        if not isinstance(params, dict):
            logger.warning("durable delivery rejected: params must be an object")
            return
        try:
            delivered_req = DurableRemoteRequest.from_dict(params)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "durable delivery rejected: malformed request material: %s",
                exc,
            )
            return
        if not delivered_req.request_id or delivered_req.node_id != self._config.node_id:
            return
        if delivered_req.lifecycle_state == "CANCEL_REQUESTED":
            if (
                not delivered_req.cancellation_requested_at
                or not delivered_req.cancellation_deadline_at
            ):
                logger.error(
                    "durable cancel missing identity for %s; refusing cancellation ack",
                    delivered_req.request_id,
                )
                return
            logical = getattr(self, "_durable_logical_executions", {}).get(delivered_req.request_id)
            if not self._durable_cancel_matches_active_execution(
                delivered_req,
                logical=logical,
            ):
                self._record_rejected_durable_control(
                    delivered_req,
                    reason="cancel execution identity mismatch",
                )
                return
            current = self._durable_store.put_request(delivered_req)
            current.lifecycle_state = "CANCEL_REQUESTED"
            current.cancellation_requested_at = delivered_req.cancellation_requested_at
            current.cancellation_deadline_at = delivered_req.cancellation_deadline_at
            self._durable_store.update_request(current, "CANCEL_REQUESTED")

        async def _run(trajectory: dict[str, Any]) -> None:
            await self._handle_durable_command_locked(delivered_req, trajectory)

        await self._with_durable_request_gate(delivered_req, _run)

    async def _handle_durable_command_locked(
        self, delivered_req: DurableRemoteRequest, trajectory: dict[str, Any]
    ) -> None:
        if not self._durable_trajectory_identity_matches(trajectory, delivered_req):
            logger.error(
                "durable request identity mismatch for coalesced trajectory: %s",
                delivered_req.request_id,
            )
            await self._fail_durable_trajectory_identity_mismatch(
                delivered_req,
                trajectory=trajectory,
            )
            return
        req = self._durable_store.put_request(delivered_req)
        self._sync_durable_request_trajectory(trajectory, req)
        if delivered_req.lifecycle_state == "CANCEL_REQUESTED":
            if (
                not delivered_req.cancellation_requested_at
                or not delivered_req.cancellation_deadline_at
            ):
                logger.error(
                    "durable cancel missing identity for %s; refusing cancellation ack",
                    delivered_req.request_id,
                )
                return
            req.lifecycle_state = "CANCEL_REQUESTED"
            req.cancellation_requested_at = delivered_req.cancellation_requested_at
            req.cancellation_deadline_at = delivered_req.cancellation_deadline_at
            self._durable_store.update_request(req, "CANCEL_REQUESTED")
            req = self._durable_store.get_request(delivered_req.request_id) or req
            self._sync_durable_request_trajectory(trajectory, req)
        existing = self._durable_store.result_for(req.request_id)
        if existing:
            self._record_durable_request_trajectory(
                req.request_id,
                status="TERMINAL_OBSERVED",
                claim_id=str(existing.get("claim_id", "")),
                terminal=True,
            )
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": req.request_id,
                    "claim_id": existing.get("claim_id", ""),
                    "state": existing.get("state", "FAILED"),
                    "result": existing.get("result", {}),
                    "cleanup": existing.get("cleanup", {}),
                    "idempotent_replay": True,
                },
            )
            return

        launch_state = str(req.process_tree.get("launch_state", "") or "")
        local_process = self._durable_processes.get(req.request_id)
        logical = getattr(self, "_durable_logical_executions", {}).get(req.request_id)
        local_execution_active = bool(
            local_process is not None
            or (
                logical is not None
                and logical.get("state") in {"AUTHORIZED", "STARTED"}
                and isinstance(logical.get("task"), asyncio.Task)
                and not logical["task"].done()
            )
        )
        if launch_state and not local_execution_active:
            if await self._recover_interrupted_shell_launch(req):
                return

        if delivered_req.lifecycle_state == "CANCEL_REQUESTED":
            terminal = await self._cancel_durable_request(
                req,
                claim_id=req.claim_id or f"{self._config.node_id}-{uuid4().hex[:12]}",
                reason="cancel requested by controller",
            )
            if terminal.lifecycle_state != "CANCELLED":
                return
            self._record_durable_request_trajectory(
                req.request_id,
                status="TERMINAL_OBSERVED",
                claim_id=terminal.claim_id,
                terminal=True,
            )
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": req.request_id,
                    "claim_id": terminal.claim_id,
                    "state": terminal.lifecycle_state,
                    "result": {"success": False, "error": "cancel requested by controller"},
                    "cleanup": terminal.cleanup,
                },
            )
            return

        if self._durable_request_expired(req) and req.lifecycle_state in {"QUEUED", "CLAIMED"}:
            await self._fail_unresolved_durable_request(
                req,
                reason="request expired before claim authority",
                no_execution_proven=True,
            )
            return

        trajectory_claim_id = str(trajectory.get("claim_id", "") or "")
        trajectory_status = str(trajectory.get("status", "") or "")
        if (
            trajectory_claim_id
            and trajectory_status in {"FAIL_CLOSED", "RECONCILIATION_PENDING"}
            and req.lifecycle_state not in {"RUNNING", *TERMINAL_STATES}
        ):
            await self._fail_durable_claim_acquisition(
                req,
                claim_id=trajectory_claim_id,
                reason=(
                    "duplicate durable delivery observed existing request trajectory "
                    f"status={trajectory_status}"
                ),
            )
            return

        if req.lifecycle_state == "CLAIMED" and req.claim_id:
            self._record_durable_request_trajectory(
                req.request_id,
                status="ACQUIRING",
                claim_id=req.claim_id,
            )
            if req.process_tree.get("root_pid"):
                await self._fail_durable_claim_acquisition(
                    req,
                    claim_id=req.claim_id,
                    reason="claimed request has root pid before running authority",
                )
                return
            ack = await self._acquire_durable_claim(
                req,
                claim_id=req.claim_id,
                process_tree=req.process_tree,
            )
            if not ack.get("ok"):
                logger.warning(
                    "durable claim unresolved for %s: %s",
                    req.request_id,
                    ack.get("error", "missing acknowledgement"),
                )
                await self._fail_durable_claim_acquisition(
                    req,
                    claim_id=req.claim_id,
                    reason=str(ack.get("error", "missing acknowledgement")),
                    attempts=ack.get("attempts"),
                )
                return
            current = self._durable_store.get_request(req.request_id) or req
            if current.lifecycle_state == "CANCEL_REQUESTED":
                terminal = await self._cancel_durable_request(
                    current,
                    claim_id=req.claim_id,
                    reason="cancel requested by controller",
                )
                if terminal.lifecycle_state != "CANCELLED":
                    return
                await self._send_durable_event(
                    "durable_command.result",
                    {
                        "request_id": current.request_id,
                        "claim_id": terminal.claim_id,
                        "state": terminal.lifecycle_state,
                        "result": {"success": False, "error": "cancel requested by controller"},
                        "cleanup": terminal.cleanup,
                    },
                )
                return
            await self._resolve_proven_durable_claim(
                current,
                claim_id=req.claim_id,
                process_tree=current.process_tree,
                claim_authority=ack,
            )
            return

        if (
            req.lifecycle_state == "RUNNING"
            and req.claim_id
            and self._durable_request_is_shell_backed(req)
            and not req.process_tree.get("root_pid")
        ):
            execution_lock = self._durable_execution_locks.get(req.request_id)
            if execution_lock is not None and execution_lock.locked():
                logger.info(
                    "durable running redelivery for %s observed local pre-start owner; "
                    "suppressing duplicate launch",
                    req.request_id,
                )
                return
            await self._fail_durable_claim_acquisition(
                req,
                claim_id=req.claim_id,
                reason="running without root pid cannot prove process ownership",
            )
            return

        if req.lifecycle_state in {"CLAIMED", "RUNNING"} and req.claim_id:
            self._record_durable_request_trajectory(
                req.request_id,
                status="RUNNING_OR_RECONCILING"
                if req.lifecycle_state == "RUNNING"
                else "ACQUIRING",
                claim_id=req.claim_id,
            )
            ack = await self._send_durable_event(
                "durable_command.claimed",
                {
                    "request_id": req.request_id,
                    "claim_id": req.claim_id,
                    "state": req.lifecycle_state,
                    "process_tree": req.process_tree,
                },
                expect_ack=True,
            )
            if req.lifecycle_state == "RUNNING" and not (ack or {}).get("ok"):
                await self._fail_durable_running_redelivery(
                    req,
                    claim_id=req.claim_id,
                    reason=str((ack or {}).get("error", "missing acknowledgement")),
                )
            return

        if self._durable_request_expired(req):
            await self._fail_unresolved_durable_request(
                req,
                reason="request expired before claim authority",
                no_execution_proven=True,
            )
            return

        if trajectory_claim_id:
            current = self._durable_store.get_request(req.request_id) or req
            if trajectory_status in {
                "FAIL_CLOSED",
                "RECONCILIATION_PENDING",
            }:
                await self._fail_durable_claim_acquisition(
                    current,
                    claim_id=trajectory_claim_id,
                    reason=(
                        "duplicate durable delivery observed existing request trajectory "
                        f"status={trajectory_status}"
                    ),
                )
                return
            if current.claim_id == trajectory_claim_id:
                await self._resolve_proven_durable_claim(
                    current,
                    claim_id=trajectory_claim_id,
                    process_tree=current.process_tree,
                    claim_authority={
                        "lifecycle_state": current.lifecycle_state,
                        "process_tree": current.process_tree,
                    },
                )
                return
            if trajectory_status in {
                "TERMINAL_OBSERVED",
                "RUNNING_OR_RECONCILING",
                "CLAIM_PROVEN",
            }:
                await self._fail_durable_claim_acquisition(
                    current,
                    claim_id=trajectory_claim_id,
                    reason=(
                        "duplicate durable delivery observed existing request trajectory "
                        f"status={trajectory_status}"
                    ),
                )
                return

        claim_id = trajectory_claim_id or f"{self._config.node_id}-{uuid4().hex[:12]}"
        self._record_durable_request_trajectory(
            req.request_id,
            status="ACQUIRING",
            claim_id=claim_id,
        )
        process_tree = {"node_pid": os.getpid(), "claimed_at": time.time()}
        self._durable_store.mark_claimed(
            req.request_id, claim_id=claim_id, process_tree=process_tree
        )
        ack = await self._acquire_durable_claim(
            req,
            claim_id=claim_id,
            process_tree=process_tree,
        )
        if not ack.get("ok"):
            logger.warning(
                "durable claim rejected for %s: %s",
                req.request_id,
                ack.get("error", "missing acknowledgement"),
            )
            await self._fail_durable_claim_acquisition(
                req,
                claim_id=claim_id,
                reason=str(ack.get("error", "missing acknowledgement")),
                attempts=ack.get("attempts"),
            )
            return

        current = self._durable_store.get_request(req.request_id) or req
        if current.lifecycle_state == "CANCEL_REQUESTED":
            terminal = await self._cancel_durable_request(
                current,
                claim_id=claim_id,
                reason="cancel requested by controller",
            )
            if terminal.lifecycle_state != "CANCELLED":
                return
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": current.request_id,
                    "claim_id": terminal.claim_id,
                    "state": terminal.lifecycle_state,
                    "result": {"success": False, "error": "cancel requested by controller"},
                    "cleanup": terminal.cleanup,
                },
            )
            return
        await self._resolve_proven_durable_claim(
            current,
            claim_id=claim_id,
            process_tree=current.process_tree,
            claim_authority=ack,
        )

    async def _resolve_proven_durable_claim(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        process_tree: dict[str, Any],
        claim_authority: dict[str, Any] | None = None,
    ) -> None:
        """Separate monotonic claim proof from current launch eligibility."""
        existing = self._durable_store.result_for(req.request_id)
        if existing:
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": req.request_id,
                    "claim_id": existing.get("claim_id", ""),
                    "state": existing.get("state", "FAILED"),
                    "result": existing.get("result", {}),
                    "cleanup": existing.get("cleanup", {}),
                    "idempotent_replay": True,
                },
            )
            return
        current = self._durable_store.get_request(req.request_id) or req
        authority_state = str((claim_authority or {}).get("lifecycle_state", "") or "")
        authority_process_tree = (claim_authority or {}).get("process_tree")
        current_state = str(current.lifecycle_state)
        effective_state = current_state
        if authority_state and STATE_ORDER.get(authority_state, -1) > STATE_ORDER.get(
            current_state, -1
        ):
            effective_state = authority_state
        effective_process_tree = (
            authority_process_tree
            if isinstance(authority_process_tree, dict) and authority_process_tree
            else current.process_tree
        )
        if current.claim_id != claim_id:
            logger.warning(
                "durable claim refused after proof for %s: state=%s claim=%s",
                req.request_id,
                current.lifecycle_state,
                current.claim_id,
            )
            await self._fail_durable_claim_acquisition(
                current,
                claim_id=claim_id,
                reason=(
                    "claim no longer executable: "
                    f"state={current.lifecycle_state} claim={current.claim_id}"
                ),
            )
            return
        if effective_state == "CANCEL_REQUESTED" or current.lifecycle_state == "CANCEL_REQUESTED":
            terminal = await self._cancel_durable_request(
                current,
                claim_id=claim_id,
                reason="cancel requested by controller",
            )
            if terminal.lifecycle_state != "CANCELLED":
                return
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": current.request_id,
                    "claim_id": terminal.claim_id,
                    "state": terminal.lifecycle_state,
                    "result": {"success": False, "error": "cancel requested by controller"},
                    "cleanup": terminal.cleanup,
                },
            )
            return
        if effective_state == "CLAIMED":
            self._record_durable_request_trajectory(
                current.request_id,
                status="CLAIM_PROVEN",
                claim_id=claim_id,
            )
            await self._execute_accepted_durable_claim(
                current,
                claim_id=claim_id,
                process_tree=current.process_tree or process_tree,
            )
            return
        if effective_state == "RUNNING":
            if self._durable_request_is_shell_backed(current) and not effective_process_tree.get(
                "root_pid"
            ):
                execution_lock = self._durable_execution_locks.get(current.request_id)
                if execution_lock is not None and execution_lock.locked():
                    logger.info(
                        "durable running replay for %s observed local pre-start owner; "
                        "suppressing duplicate launch",
                        current.request_id,
                    )
                    return
                await self._fail_durable_claim_acquisition(
                    current,
                    claim_id=claim_id,
                    reason="running without root pid cannot prove process ownership",
                )
                return
            self._record_durable_request_trajectory(
                current.request_id,
                status="RUNNING_OR_RECONCILING",
                claim_id=claim_id,
            )
            ack = await self._send_durable_event(
                "durable_command.claimed",
                {
                    "request_id": current.request_id,
                    "claim_id": claim_id,
                    "state": effective_state,
                    "process_tree": effective_process_tree,
                },
                expect_ack=True,
            )
            if not (ack or {}).get("ok"):
                await self._fail_durable_running_redelivery(
                    current,
                    claim_id=claim_id,
                    reason=str((ack or {}).get("error", "missing acknowledgement")),
                )
            return
        if effective_state in TERMINAL_STATES:
            self._record_durable_request_trajectory(
                current.request_id,
                status="TERMINAL_OBSERVED",
                claim_id=claim_id,
                terminal=True,
            )
            return
        await self._fail_durable_claim_acquisition(
            current,
            claim_id=claim_id,
            reason=(
                f"claim no longer executable: state={effective_state} claim={current.claim_id}"
            ),
        )

    @staticmethod
    def _durable_request_is_shell_backed(req: DurableRemoteRequest) -> bool:
        cap_name = str(req.capability or "")
        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        return adapter_key == "shell"

    async def _recover_interrupted_shell_launch(
        self,
        req: DurableRemoteRequest,
    ) -> bool:
        """Resolve durable shell launch state without ever relaunching uncertain work."""

        if not self._durable_request_is_shell_backed(req):
            return False
        launch_state = str(req.process_tree.get("launch_state", "") or "")
        if not launch_state:
            return False
        claim_id = str(req.claim_id or "")
        execution_identity = dict(req.process_tree.get("execution_identity") or {})
        expected_identity = self._durable_execution_identity(req, claim_id=claim_id)
        if not claim_id or execution_identity != expected_identity:
            self._durable_store.mark_reconciliation_required(
                req.request_id,
                reason="persisted shell launch identity does not match canonical execution",
                cleanup={
                    "process_residue": [{"state": "shell_execution_identity_mismatch"}],
                    "execution_outcome_unknown": True,
                },
            )
            return True
        if launch_state == SHELL_LAUNCH_INTENT_PERSISTED:
            cleanup = _durable_positive_no_process_cleanup(
                launch_not_attempted=True,
                launch_intent_id=req.process_tree.get("launch_intent_id", ""),
                execution_identity=execution_identity,
            )
            terminal = self._durable_store.publish_result(
                req.request_id,
                claim_id=claim_id,
                state="FAILED",
                result={
                    "success": False,
                    "error": "node stopped after durable launch intent but before launch attempt",
                    "launch_not_attempted": True,
                },
                cleanup=cleanup,
            )
            persisted = self._durable_store.result_for(req.request_id) or {}
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": req.request_id,
                    "claim_id": claim_id,
                    "state": terminal.lifecycle_state,
                    "result": persisted.get("result", {}),
                    "cleanup": cleanup,
                },
            )
            return True
        if launch_state == SHELL_LAUNCH_IN_PROGRESS and not req.process_tree.get("root_pid"):
            self._durable_store.mark_reconciliation_required(
                req.request_id,
                reason="shell launch may have completed before process identity persistence",
                cleanup={
                    "process_residue": [{"state": "shell_launch_outcome_uncertain"}],
                    "execution_outcome_unknown": True,
                    "duplicate_launch_fenced": True,
                    "launch_intent_id": req.process_tree.get("launch_intent_id", ""),
                    "execution_identity": execution_identity,
                },
            )
            return True
        stored_process = dict(req.process_tree.get("process_identity") or {})
        matched, reason, observed = _durable_process_identity_matches(
            stored_process,
            command_digest=req.payload_digest,
        )
        cleanup = {
            "process_residue": [
                {
                    "pid": req.process_tree.get("root_pid"),
                    "state": "observerless_exact_shell_process"
                    if matched
                    else "shell_process_ownership_unverified",
                }
            ],
            "execution_outcome_unknown": True,
            "duplicate_launch_fenced": True,
            "process_identity_match": matched,
            "process_identity_reason": reason,
            "persisted_process_identity": stored_process,
            "observed_process_identity": observed or {},
            "execution_identity": execution_identity,
        }
        if matched and req.lifecycle_state == "CLAIMED":
            self._durable_store.mark_running(
                req.request_id,
                claim_id=claim_id,
                process_tree=req.process_tree,
            )
        self._durable_store.mark_reconciliation_required(
            req.request_id,
            reason=(
                "exact shell process recovered without durable outcome observer"
                if matched
                else reason
            ),
            cleanup=cleanup,
        )
        return True

    async def _execute_accepted_durable_claim(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        process_tree: dict[str, Any],
    ) -> None:
        lock = self._durable_execution_locks.setdefault(req.request_id, asyncio.Lock())
        async with lock:
            self._record_durable_request_trajectory(
                req.request_id,
                status="RUNNING_OR_RECONCILING",
                claim_id=claim_id,
            )
            existing = self._durable_store.result_for(req.request_id)
            if existing:
                self._record_durable_request_trajectory(
                    req.request_id,
                    status="TERMINAL_OBSERVED",
                    claim_id=str(existing.get("claim_id", claim_id)),
                    terminal=True,
                )
                await self._send_durable_event(
                    "durable_command.result",
                    {
                        "request_id": req.request_id,
                        "claim_id": existing.get("claim_id", ""),
                        "state": existing.get("state", "FAILED"),
                        "result": existing.get("result", {}),
                        "cleanup": existing.get("cleanup", {}),
                        "idempotent_replay": True,
                    },
                )
                return
            current = self._durable_store.get_request(req.request_id) or req
            if current.lifecycle_state != "CLAIMED" or current.claim_id != claim_id:
                logger.warning(
                    "durable claim refused execution for %s: state=%s claim=%s",
                    req.request_id,
                    current.lifecycle_state,
                    current.claim_id,
                )
                await self._fail_durable_claim_acquisition(
                    current,
                    claim_id=claim_id,
                    reason=(
                        "claim refused execution: "
                        f"state={current.lifecycle_state} claim={current.claim_id}"
                    ),
                )
                return
            if self._durable_request_expired(current):
                await self._fail_durable_claim_acquisition(
                    current,
                    claim_id=claim_id,
                    reason="request expired before execution authority",
                )
                return
            result = await self._execute_capability_for_durable(
                current,
                claim_id=claim_id,
                process_tree=current.process_tree or process_tree,
            )
            launch_state = str(
                (self._durable_store.get_request(current.request_id) or current).process_tree.get(
                    "launch_state", ""
                )
                or ""
            )
            cleanup = dict(result.get("cleanup") or {})
            if (
                self._durable_request_is_shell_backed(current)
                and launch_state
                in {
                    SHELL_LAUNCH_IN_PROGRESS,
                    SHELL_PROCESS_IDENTITY_PERSISTED,
                    SHELL_LAUNCH_RUNNING,
                }
                and cleanup.get("cleanup_verified") is not True
            ):
                cleanup.setdefault(
                    "process_residue",
                    [{"state": "shell_cleanup_completeness_unverified"}],
                )
                if cleanup.get("process_residue") == []:
                    cleanup["process_residue"] = [
                        {"state": "shell_cleanup_completeness_unverified"}
                    ]
                cleanup["execution_outcome_unknown"] = True
                result["cleanup"] = cleanup
                result["execution_outcome_unresolved"] = True
            if result.get("execution_outcome_unresolved"):
                cleanup = dict(
                    result.get("cleanup")
                    or {
                        "process_residue": [{"state": "shell_launch_outcome_uncertain"}],
                        "execution_outcome_unknown": True,
                    }
                )
                self._durable_store.mark_reconciliation_required(
                    current.request_id,
                    reason=str(result.get("error", "shell execution outcome unresolved")),
                    cleanup=cleanup,
                )
                self._record_durable_request_trajectory(
                    current.request_id,
                    status="RECONCILIATION_PENDING",
                    claim_id=claim_id,
                    terminal=True,
                )
                return
            state = "SUCCEEDED" if result.get("success") else "FAILED"
            cleanup = dict(result.get("cleanup") or {"process_residue": []})
            if not self._durable_request_is_shell_backed(current):
                cleanup = _durable_positive_no_process_cleanup(
                    cleanup_scope="adapter_without_node_process_launch",
                    adapter_cleanup=cleanup,
                )
                result["cleanup"] = cleanup
            logical = getattr(self, "_durable_logical_executions", {}).get(current.request_id)
            if logical is not None:
                logical["outcome_state"] = state
            if result.get("durable_request_missing_after_running"):
                await self._send_durable_event(
                    "durable_command.result",
                    {
                        "request_id": current.request_id,
                        "claim_id": claim_id,
                        "state": state,
                        "result": result,
                        "cleanup": cleanup,
                    },
                )
                return
            self._durable_store.publish_result(
                current.request_id,
                claim_id=claim_id,
                state=state,
                result=result,
                cleanup=cleanup,
            )
            self._record_durable_request_trajectory(
                current.request_id,
                status="TERMINAL_OBSERVED",
                claim_id=claim_id,
                terminal=True,
            )
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": current.request_id,
                    "claim_id": claim_id,
                    "state": state,
                    "result": result,
                    "cleanup": cleanup,
                },
            )

    @staticmethod
    def _durable_request_expired(req: DurableRemoteRequest) -> bool:
        return bool(req.expires_at and time.time() >= req.expires_at)

    async def _fail_unresolved_durable_request(
        self,
        req: DurableRemoteRequest,
        *,
        reason: str,
        no_execution_proven: bool = False,
    ) -> DurableRemoteRequest:
        if no_execution_proven:
            current = self._durable_store.get_request(req.request_id) or req
            cleanup = _durable_positive_no_process_cleanup(
                **dict(current.cleanup or {}),
                failure_before_execution=True,
            )
            terminal = self._durable_store.publish_result(
                current.request_id,
                claim_id=current.claim_id or "unclaimed",
                state="FAILED",
                result={"success": False, "error": reason, "reason": reason},
                cleanup=cleanup,
            )
        else:
            terminal = self._durable_store.fail_unresolved_request(req.request_id, reason=reason)
        self._record_durable_request_trajectory(
            terminal.request_id,
            status="FAIL_CLOSED",
            claim_id=terminal.claim_id or "unclaimed",
            terminal=True,
        )
        published = self._durable_store.result_for(req.request_id) or {}
        await self._send_durable_event(
            "durable_command.result",
            {
                "request_id": terminal.request_id,
                "claim_id": published.get("claim_id", terminal.claim_id or "unclaimed"),
                "state": terminal.lifecycle_state,
                "result": published.get(
                    "result",
                    {
                        "success": False,
                        "error": "durable remote unresolved request failed closed",
                        "reason": reason,
                    },
                ),
                "cleanup": published.get("cleanup", terminal.cleanup or {"process_residue": []}),
            },
        )
        return terminal

    async def _fail_durable_running_redelivery(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        reason: str,
    ) -> DurableRemoteRequest:
        cleanup = {
            "process_residue": [{"state": "running_execution_outcome_unresolved"}],
            "running_redelivery_reconciliation_required": True,
            "execution_outcome_unknown": True,
            "claim_id": claim_id,
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "node_id": req.node_id,
            "candidate_sha": req.candidate_sha,
        }
        root_pid = req.process_tree.get("root_pid")
        if root_pid:
            cleanup["process_residue"] = [
                {"pid": root_pid, "state": "running_redelivery_ack_unresolved"}
            ]
        current = self._durable_store.mark_reconciliation_required(
            req.request_id,
            reason=f"running acknowledgement unresolved: {reason}",
            cleanup=cleanup,
        )
        self._record_durable_request_trajectory(
            req.request_id,
            status="RECONCILIATION_PENDING",
            claim_id=claim_id,
            terminal=True,
        )
        return current

    async def _fail_durable_claim_acquisition(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        reason: str,
        attempts: object | None = None,
    ) -> DurableRemoteRequest:
        """Fail closed when a claimed request cannot prove execution authority."""
        current = self._durable_store.get_request(req.request_id) or req
        launch_state = str(current.process_tree.get("launch_state", "") or "")
        if launch_state in {
            SHELL_LAUNCH_IN_PROGRESS,
            SHELL_PROCESS_IDENTITY_PERSISTED,
            SHELL_LAUNCH_RUNNING,
        }:
            cleanup = {
                "process_residue": [
                    {
                        "pid": current.process_tree.get("root_pid"),
                        "state": "shell_launch_or_execution_outcome_uncertain",
                    }
                ],
                "execution_outcome_unknown": True,
                "duplicate_launch_fenced": True,
                "launch_state": launch_state,
                "execution_identity": current.process_tree.get("execution_identity", {}),
            }
            terminal = self._durable_store.mark_reconciliation_required(
                current.request_id,
                reason=f"{reason}; shell launch cannot be terminalized definitively",
                cleanup=cleanup,
            )
            self._record_durable_request_trajectory(
                current.request_id,
                status="RECONCILIATION_PENDING",
                claim_id=claim_id,
                terminal=True,
            )
            return terminal
        if current.lifecycle_state == "CANCEL_REQUESTED":
            terminal = await self._cancel_durable_request(
                current,
                claim_id=claim_id,
                reason="cancel requested by controller",
            )
            if terminal.lifecycle_state != "CANCELLED":
                return terminal
            self._record_durable_request_trajectory(
                current.request_id,
                status="TERMINAL_OBSERVED",
                claim_id=terminal.claim_id,
                terminal=True,
            )
            await self._send_durable_event(
                "durable_command.result",
                {
                    "request_id": current.request_id,
                    "claim_id": terminal.claim_id,
                    "state": terminal.lifecycle_state,
                    "result": {"success": False, "error": "cancel requested by controller"},
                    "cleanup": terminal.cleanup,
                },
            )
            return terminal
        if current.lifecycle_state in {"SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"}:
            return current

        cleanup = _durable_positive_no_process_cleanup(
            cleanup_scope="claim_failed_before_execution",
            claim_acquisition_failed_closed=True,
            claim_id=claim_id,
            request_id=current.request_id,
            correlation_id=current.correlation_id,
            node_id=current.node_id,
            candidate_sha=current.candidate_sha,
        )
        result: dict[str, Any] = {
            "success": False,
            "error": "durable claim acquisition failed closed",
            "reason": reason,
        }
        if isinstance(attempts, list):
            result["claim_acquisition_attempts"] = attempts
        terminal = self._durable_store.publish_result(
            current.request_id,
            claim_id=claim_id,
            state="FAILED",
            result=result,
            cleanup=cleanup,
        )
        self._record_durable_request_trajectory(
            current.request_id,
            status="FAIL_CLOSED",
            claim_id=claim_id,
            terminal=True,
        )
        await self._send_durable_event(
            "durable_command.result",
            {
                "request_id": terminal.request_id,
                "claim_id": claim_id,
                "state": terminal.lifecycle_state,
                "result": result,
                "cleanup": cleanup,
            },
        )
        return terminal

    async def _acquire_durable_claim(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        process_tree: dict[str, Any],
    ) -> dict[str, Any]:
        """Prove this exact claim was accepted before executing the request."""
        payload = {
            "request_id": req.request_id,
            "claim_id": claim_id,
            "state": "CLAIMED",
            "process_tree": process_tree,
        }
        deadline = time.monotonic() + _DURABLE_CLAIM_ACQUIRE_TIMEOUT_S
        attempts: list[dict[str, Any]] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {
                    "ok": False,
                    "error": "claim acknowledgement unresolved before acquisition deadline",
                    "attempts": attempts,
                    "claim_id": claim_id,
                }
            try:
                ack = await self._send_durable_event(
                    "durable_command.claimed",
                    payload,
                    expect_ack=True,
                    timeout_s=min(_CONTROL_TIMEOUT_S, remaining),
                )
            except Exception as exc:  # noqa: BLE001
                ack = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "retryable": True}
            ack = ack or {"ok": False, "error": "missing acknowledgement"}
            attempts.append(
                {
                    "method": "durable_command.claimed",
                    "ok": bool(ack.get("ok")),
                    "error": str(ack.get("error", "")),
                }
            )
            if ack.get("ok"):
                validated_ack = self._validate_durable_claim_authority(
                    ack,
                    req,
                    claim_id=claim_id,
                    expected_state="CLAIMED",
                    label="claim acknowledgement",
                    allow_monotonic_claim_state=True,
                )
                if validated_ack.get("ok"):
                    return {
                        "ok": True,
                        "attempts": attempts,
                        "claim_id": claim_id,
                        "lifecycle_state": validated_ack.get("lifecycle_state"),
                        "process_tree": validated_ack.get("process_tree", {}),
                    }
                readback = await self._reconcile_durable_claim_state(
                    req,
                    claim_id=claim_id,
                    expected_state="CLAIMED",
                    timeout_s=min(_CONTROL_TIMEOUT_S, max(0.0, deadline - time.monotonic())),
                    allow_monotonic_claim_state=True,
                )
                attempts.append(
                    {
                        "method": "canonical_durable_claim_state",
                        "ok": bool(readback.get("ok")),
                        "error": str(readback.get("error", validated_ack.get("error", ""))),
                    }
                )
                if readback.get("ok"):
                    return {
                        "ok": True,
                        "attempts": attempts,
                        "claim_id": claim_id,
                        "reconciled": True,
                        "lifecycle_state": readback.get("lifecycle_state"),
                        "process_tree": readback.get("process_tree", {}),
                    }
                if not readback.get("retryable"):
                    return {
                        "ok": False,
                        "error": str(
                            readback.get(
                                "error",
                                validated_ack.get("error", "claim authority rejected"),
                            )
                        ),
                        "attempts": attempts,
                        "claim_id": claim_id,
                    }
            error = str(ack.get("error", ""))
            retryable = bool(ack.get("retryable")) or (
                "timed out" in error or "missing acknowledgement" in error
            )
            if retryable:
                readback = await self._reconcile_durable_claim_state(
                    req,
                    claim_id=claim_id,
                    expected_state="CLAIMED",
                    timeout_s=min(_CONTROL_TIMEOUT_S, max(0.0, deadline - time.monotonic())),
                    allow_monotonic_claim_state=True,
                )
                attempts.append(
                    {
                        "method": "canonical_durable_claim_state",
                        "ok": bool(readback.get("ok")),
                        "error": str(readback.get("error", "")),
                    }
                )
                if readback.get("ok"):
                    return {
                        "ok": True,
                        "attempts": attempts,
                        "claim_id": claim_id,
                        "reconciled": True,
                        "lifecycle_state": readback.get("lifecycle_state"),
                        "process_tree": readback.get("process_tree", {}),
                    }
                if not readback.get("retryable"):
                    return {
                        "ok": False,
                        "error": str(readback.get("error", "claim readback rejected")),
                        "attempts": attempts,
                        "claim_id": claim_id,
                    }
            if not retryable:
                return {
                    "ok": False,
                    "error": error or "claim rejected",
                    "attempts": attempts,
                    "claim_id": claim_id,
                }
            await asyncio.sleep(
                min(_DURABLE_CLAIM_RETRY_SLEEP_S, max(0.0, deadline - time.monotonic()))
            )

    async def _reconcile_durable_claim_state(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        expected_state: str,
        timeout_s: float,
        allow_monotonic_claim_state: bool = False,
    ) -> dict[str, Any]:
        """Read back the controller's canonical claim after a lost direct ACK."""
        if timeout_s <= 0:
            return {"ok": False, "error": "claim readback deadline expired", "retryable": False}
        payload = {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "node_id": req.node_id,
            "claim_id": claim_id,
            "state": expected_state,
        }
        try:
            readback = await self._read_canonical_durable_claim_state(
                payload,
                timeout_s=timeout_s,
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "retryable": True}
        readback = readback or {"ok": False, "error": "missing claim readback"}
        if not readback.get("ok") or not readback.get("accepted"):
            readback["ok"] = False
            readback.setdefault("error", "claim readback not accepted")
            error = readback.get("error")
            if isinstance(error, dict) and error.get("code") == -32601:
                readback["retryable"] = True
            elif "unknown method" in str(error):
                readback["retryable"] = True
            readback.setdefault("retryable", False)
            return readback
        validated = self._validate_durable_claim_authority(
            readback,
            req,
            claim_id=claim_id,
            expected_state=expected_state,
            label="claim readback",
            allow_monotonic_claim_state=allow_monotonic_claim_state,
        )
        self._durable_store.record_transport_diagnostic(
            req.request_id,
            (
                "NODE_CLAIM_READBACK_RESPONSE_VALIDATED"
                if validated.get("ok")
                else "NODE_CLAIM_READBACK_VALIDATION_ERROR"
            ),
            {
                "claim_id": claim_id,
                "correlation_id": req.correlation_id,
                "candidate_sha": req.candidate_sha,
                "node_id": req.node_id,
                "readback_id": str(readback.get("_readback_id", "")),
                "ok": bool(validated.get("ok")),
                "error": str(validated.get("error", "")),
            },
        )
        return validated

    def _validate_durable_claim_authority(
        self,
        readback: dict[str, Any],
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        expected_state: str,
        label: str,
        allow_monotonic_claim_state: bool = False,
    ) -> dict[str, Any]:
        if not readback.get("accepted"):
            return {
                "ok": False,
                "accepted": False,
                "error": f"{label} not accepted",
                "retryable": False,
            }
        mismatches: list[str] = []
        expected = {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "candidate_sha": req.candidate_sha,
            "node_id": req.node_id,
            "claim_id": claim_id,
        }
        for key, value in expected.items():
            if str(readback.get(key, "")) != str(value):
                mismatches.append(key)
        observed_state = str(readback.get("lifecycle_state", ""))
        if allow_monotonic_claim_state:
            if observed_state not in _DURABLE_CLAIM_PROOF_STATES:
                mismatches.append("lifecycle_state")
        elif observed_state != expected_state:
            mismatches.append("lifecycle_state")
        if mismatches:
            return {
                "ok": False,
                "accepted": False,
                "error": f"{label} mismatch: " + ",".join(mismatches),
                "retryable": False,
            }
        if str(readback.get("authority_source", "")) != "vps_canonical_durable_store":
            return {
                "ok": False,
                "accepted": False,
                "error": f"{label} authority source is not canonical durable store",
                "retryable": False,
            }
        lease_expires_at = float(readback.get("lease_expires_at", 0.0) or 0.0)
        if lease_expires_at and lease_expires_at <= time.time():
            return {
                "ok": False,
                "accepted": False,
                "error": f"{label} lease expired",
                "retryable": False,
            }
        process_tree = readback.get("process_tree")
        return {
            "ok": True,
            "accepted": True,
            "lifecycle_state": observed_state,
            "process_tree": process_tree if isinstance(process_tree, dict) else {},
        }

    async def _read_canonical_durable_claim_state(
        self,
        payload: dict[str, Any],
        *,
        timeout_s: float,
    ) -> dict[str, Any]:
        """Read VPS canonical durable state outside the WebSocket RPC waiter path."""
        request_id = str(payload.get("request_id", "") or "")
        claim_id = str(payload.get("claim_id", "") or "")
        correlation_id = str(payload.get("correlation_id", "") or "")
        candidate_sha = str(payload.get("candidate_sha", "") or "")
        node_id = str(payload.get("node_id", "") or "")
        readback_id = uuid4().hex
        identity = {
            "request_id": request_id,
            "claim_id": claim_id,
            "correlation_id": correlation_id,
            "candidate_sha": candidate_sha,
            "node_id": node_id,
            "readback_id": readback_id,
        }

        def _record(stage: str, extra: dict[str, Any] | None = None) -> None:
            if request_id:
                self._durable_store.record_transport_diagnostic(
                    request_id,
                    f"NODE_CLAIM_READBACK_{stage}",
                    {**identity, **(extra or {})},
                )

        if timeout_s <= 0:
            _record("TIMEOUT", {"error": "claim readback deadline expired"})
            return {"ok": False, "error": "claim readback deadline expired", "retryable": False}
        if not self._config.vps_host or not self._config.token:
            _record("TRANSPORT_ERROR", {"error": "missing node auth"})
            return {
                "ok": False,
                "error": "canonical claim readback unavailable: missing node auth",
                "retryable": False,
            }
        _record("START", {"timeout_s": timeout_s})

        async def _post() -> dict[str, Any]:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            timeout = aiohttp.ClientTimeout(
                total=timeout_s,
                connect=min(timeout_s, 2.0),
                sock_connect=min(timeout_s, 2.0),
                sock_read=timeout_s,
            )
            trace = aiohttp.TraceConfig()

            async def _headers_sent(
                _session: aiohttp.ClientSession,
                _context: Any,
                _params: Any,
            ) -> None:
                _record("REQUEST_SENT", {"request_bytes": len(body)})

            trace.on_request_headers_sent.append(_headers_sent)
            _record("CONNECT_START")
            try:
                async with aiohttp.ClientSession(
                    timeout=timeout,
                    trace_configs=[trace],
                ) as session:
                    async with session.post(
                        self._config.relay_http_url.rstrip("/") + "/durable-claim-state",
                        data=body,
                        headers={
                            "Authorization": f"Bearer {self._config.token}",
                            "Content-Type": "application/json",
                        },
                    ) as resp:
                        _record("HTTP_STATUS", {"status": int(resp.status)})
                        if not 200 <= resp.status < 300:
                            return {
                                "ok": False,
                                "error": f"canonical claim readback HTTP {resp.status}",
                                "retryable": 500 <= resp.status < 600,
                            }
                        raw = await resp.content.read(64 * 1024 + 1)
                        _record("RESPONSE_RECEIVED", {"response_bytes": len(raw)})
            except asyncio.TimeoutError as exc:
                _record("TIMEOUT", {"error": f"{type(exc).__name__}: {exc}"})
                return {
                    "ok": False,
                    "error": "canonical claim readback timed out",
                    "retryable": True,
                }
            except aiohttp.ClientError as exc:
                _record(
                    "TRANSPORT_ERROR",
                    {"error": f"{type(exc).__name__}: {exc}"},
                )
                return {
                    "ok": False,
                    "error": f"canonical claim readback unavailable: {exc}",
                    "retryable": True,
                }
            except asyncio.CancelledError:
                _record("CANCELLED")
                raise
            if len(raw) > 64 * 1024:
                _record("VALIDATION_ERROR", {"error": "response exceeds 65536 byte bound"})
                return {
                    "ok": False,
                    "error": "canonical claim readback response too large",
                    "retryable": False,
                }
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                _record(
                    "VALIDATION_ERROR",
                    {"error": f"{type(exc).__name__}: {exc}"},
                )
                return {
                    "ok": False,
                    "error": f"canonical claim readback invalid JSON: {exc}",
                    "retryable": False,
                }
            if not isinstance(parsed, dict):
                _record("VALIDATION_ERROR", {"error": "non-object response"})
                return {
                    "ok": False,
                    "error": "canonical claim readback returned non-object",
                    "retryable": False,
                }
            return parsed

        started = time.monotonic()
        try:
            async with asyncio.timeout(timeout_s + 0.1):
                result = await _post()
        except asyncio.TimeoutError:
            result = {
                "ok": False,
                "error": "canonical claim readback bounded wait expired",
                "retryable": True,
            }
            _record("TIMEOUT", {"error": result["error"]})
        result["_readback_id"] = readback_id
        _record(
            "END",
            {
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
                "ok": bool(result.get("ok")),
                "accepted": bool(result.get("accepted")),
                "error": str(result.get("error", "")),
                "retryable": bool(result.get("retryable", False)),
            },
        )
        return result

    async def _announce_durable_running(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        process_tree: dict[str, Any],
    ) -> dict[str, Any]:
        if self._durable_request_is_shell_backed(req):
            current = self._durable_store.get_request(req.request_id) or req
            effective_tree = {**current.process_tree, **process_tree}
            if (
                effective_tree.get("launch_state") != SHELL_PROCESS_IDENTITY_PERSISTED
                or not effective_tree.get("root_pid")
                or not effective_tree.get("process_identity")
                or not effective_tree.get("execution_identity")
                or not effective_tree.get("launch_intent_id")
            ):
                self._durable_store.mark_reconciliation_required(
                    req.request_id,
                    reason="shell RUNNING requires durable exact process identity",
                    cleanup={
                        "process_residue": [{"state": "shell_process_identity_not_persisted"}],
                        "execution_outcome_unknown": True,
                    },
                )
                return {
                    "ok": False,
                    "error": "shell RUNNING requires durable exact process identity",
                }
            process_tree = {
                **effective_tree,
                "launch_state": SHELL_LAUNCH_RUNNING,
            }
        updated = self._durable_store.mark_running(
            req.request_id,
            claim_id=claim_id,
            process_tree=process_tree,
        )
        if updated.lifecycle_state != "RUNNING" or updated.claim_id != claim_id:
            return {
                "ok": False,
                "error": f"running rejected into {updated.lifecycle_state}",
            }
        self._record_durable_request_trajectory(
            req.request_id,
            status="RUNNING_OR_RECONCILING",
            claim_id=claim_id,
        )
        ack = await self._send_durable_event(
            "durable_command.claimed",
            {
                "request_id": req.request_id,
                "claim_id": claim_id,
                "state": "RUNNING",
                "process_tree": process_tree,
            },
            expect_ack=True,
        )
        ack = ack or {"ok": False, "error": "missing acknowledgement"}
        if ack.get("ok"):
            validated_ack = self._validate_durable_claim_authority(
                ack,
                req,
                claim_id=claim_id,
                expected_state="RUNNING",
                label="running acknowledgement",
            )
            if validated_ack.get("ok"):
                return ack
            readback = await self._reconcile_durable_claim_state(
                req,
                claim_id=claim_id,
                expected_state="RUNNING",
                timeout_s=_CONTROL_TIMEOUT_S,
            )
            if readback.get("ok"):
                return {"ok": True, "reconciled": True}
            return {
                "ok": False,
                "error": str(
                    readback.get(
                        "error",
                        validated_ack.get("error", "running acknowledgement rejected"),
                    )
                ),
                "retryable": bool(readback.get("retryable")),
            }
        error = str(ack.get("error", ""))
        retryable = bool(ack.get("retryable")) or (
            "timed out" in error or "missing acknowledgement" in error
        )
        if not retryable:
            return ack
        readback = await self._reconcile_durable_claim_state(
            req,
            claim_id=claim_id,
            expected_state="RUNNING",
            timeout_s=_CONTROL_TIMEOUT_S,
        )
        if readback.get("ok"):
            return {"ok": True, "reconciled": True}
        return readback

    async def _cancel_durable_request(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        reason: str,
    ) -> DurableRemoteRequest:
        if not req.cancellation_requested_at or not req.cancellation_deadline_at:
            raise ValueError(f"cancel identity missing for durable request {req.request_id}")
        logical = getattr(self, "_durable_logical_executions", {}).get(req.request_id)
        if logical is not None and not self._durable_cancel_matches_active_execution(
            req,
            logical=logical,
        ):
            self._record_rejected_durable_control(
                req,
                reason="cancel execution identity mismatch",
            )
            return self._durable_store.get_request(req.request_id) or req
        if logical is not None and logical.get("state") == "STARTED":
            operation = logical.get("operation_future")
            if operation is not None and operation.done() and not operation.cancelled():
                terminal = await self._persist_completed_logical_execution_outcome(
                    req,
                    logical=logical,
                    claim_id=claim_id,
                )
                if terminal is not None:
                    return terminal
            logical["cancel_requested"] = True
            self._durable_store.record_transport_diagnostic(
                req.request_id,
                "CANCEL_REQUESTED_EXECUTION_OUTCOME_PENDING",
                {
                    "claim_id": claim_id,
                    "execution_id": dict(logical.get("execution_identity") or {}).get(
                        "execution_id",
                        "",
                    ),
                },
            )
            return self._durable_store.get_request(req.request_id) or req
        if req.lifecycle_state == "RECONCILIATION_REQUIRED" and bool(
            (req.cleanup or {}).get("execution_outcome_unknown")
        ):
            self._durable_store.record_transport_diagnostic(
                req.request_id,
                "CANCEL_REQUESTED_EXECUTION_OUTCOME_UNRESOLVED",
                {"claim_id": claim_id},
            )
            return self._durable_store.get_request(req.request_id) or req
        launch_state = str(req.process_tree.get("launch_state", "") or "")
        if launch_state == SHELL_LAUNCH_IN_PROGRESS:
            current = self._durable_store.mark_reconciliation_required(
                req.request_id,
                reason="cancel requested while shell launch/execution outcome is uncertain",
                cleanup={
                    "process_residue": [
                        {
                            "pid": req.process_tree.get("root_pid"),
                            "state": "shell_launch_or_execution_outcome_uncertain",
                        }
                    ],
                    "execution_outcome_unknown": True,
                    "duplicate_launch_fenced": True,
                    "launch_state": launch_state,
                    "execution_identity": req.process_tree.get("execution_identity", {}),
                },
            )
            self._record_durable_request_trajectory(
                req.request_id,
                status="RECONCILIATION_PENDING",
                claim_id=claim_id,
                terminal=True,
            )
            return current
        proc = self._durable_processes.get(req.request_id)
        cleanup = _durable_positive_no_process_cleanup(
            cleanup_scope="cancelled_before_process_launch",
            cancel_reason=reason,
            **req.cancellation_identity(claim_id=claim_id),
        )
        if proc is not None and proc.poll() is None:
            cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
            cleanup["cancel_reason"] = reason
            cleanup.update(req.cancellation_identity(claim_id=claim_id))
            if cleanup.get("cleanup_verified") is not True:
                if cleanup.get("process_residue") == []:
                    cleanup["process_residue"] = [
                        {"state": "shell_cleanup_completeness_unverified"}
                    ]
                cleanup["execution_outcome_unknown"] = True
                current = self._durable_store.mark_reconciliation_required(
                    req.request_id,
                    reason="cancel cleanup completeness could not be proven",
                    cleanup=cleanup,
                )
                self._record_durable_request_trajectory(
                    req.request_id,
                    status="RECONCILIATION_PENDING",
                    claim_id=claim_id,
                    terminal=True,
                )
                return current
        elif req.process_tree.get("root_pid") or req.lifecycle_state == "RUNNING":
            cleanup["process_residue"] = [
                {
                    "pid": req.process_tree.get("root_pid"),
                    "state": "running_process_owner_lost_after_restart",
                }
            ]
            cleanup["process_owner_lost_after_restart"] = True
            cleanup["execution_outcome_unknown"] = True
            current = self._durable_store.mark_reconciliation_required(
                req.request_id,
                reason="cancel requested while execution outcome is observerless",
                cleanup=cleanup,
            )
            self._record_durable_request_trajectory(
                req.request_id,
                status="RECONCILIATION_PENDING",
                claim_id=claim_id,
                terminal=True,
            )
            return current
        terminal = self._durable_store.publish_result(
            req.request_id,
            claim_id=claim_id,
            state="CANCELLED",
            result={"success": False, "error": reason},
            cleanup=cleanup,
        )
        self._record_durable_request_trajectory(
            req.request_id,
            status="TERMINAL_OBSERVED",
            claim_id=claim_id,
            terminal=True,
        )
        return terminal

    async def _terminate_durable_process_tree(
        self, proc: subprocess.Popen[str], *, graceful_timeout: float
    ) -> dict[str, Any]:
        pid = proc.pid
        cleanup: dict[str, Any] = {
            "root_pid": pid,
            "graceful_attempted": True,
            "enumeration_performed": False,
            "enumeration_complete": False,
            "ownership_validated": False,
            "matched_processes": [],
            "termination_attempted": False,
            "post_termination_enumeration_complete": False,
            "residue_count": None,
            "cleanup_verified": False,
            "forced": False,
            "process_residue": [],
        }
        containment = getattr(proc, "_umh_containment", None)
        root_identity = dict(getattr(proc, "_umh_process_identity", {}) or {})
        try:
            try:
                command_digest = str(root_identity.get("command_digest", ""))
                identities = _durable_capture_owned_identities(
                    proc,
                    command_digest=command_digest,
                )
                cleanup["enumeration_performed"] = True
                cleanup["enumeration_complete"] = True
                cleanup["matched_processes"] = list(identities.values())
                cleanup["ownership_validated"] = True
            except Exception as exc:  # noqa: BLE001
                identities = dict(
                    getattr(proc, "_umh_owned_process_identities", {}) or {}
                )
                cleanup["enumeration_performed"] = True
                cleanup["enumeration_error"] = f"{type(exc).__name__}: {exc}"
            if sys.platform == "win32":
                if containment is None:
                    matched, reason, observed = _durable_process_identity_matches(
                        root_identity,
                        command_digest=str(root_identity.get("command_digest", "")),
                    )
                    cleanup["ownership_validated"] = matched
                    cleanup["observed_root_identity"] = observed or {}
                    if not matched:
                        cleanup["process_residue"] = [
                            {"pid": pid, "state": "process_ownership_unverified", "reason": reason}
                        ]
                        return cleanup
                    proc.terminate()
                    cleanup["graceful_stdout"] = "terminated exact process handle"
                else:
                    containment.terminate()
                    cleanup["graceful_stdout"] = "terminated owned Windows Job Object"
                cleanup["termination_attempted"] = True
            else:
                try:
                    os.killpg(pid, signal.SIGTERM)
                    cleanup["graceful_stdout"] = f"sent SIGTERM to process group {pid}"
                    cleanup["termination_attempted"] = True
                except ProcessLookupError:
                    cleanup["graceful_stdout"] = "process group already absent"
                except Exception as exc:  # noqa: BLE001
                    cleanup["graceful_stderr"] = f"process group SIGTERM failed: {exc}"
                    proc.terminate()
                    cleanup["termination_attempted"] = True
            try:
                proc.wait(timeout=graceful_timeout)
            except subprocess.TimeoutExpired:
                cleanup["forced"] = True
                if sys.platform == "win32":
                    if containment is not None:
                        containment.terminate()
                        cleanup["force_stdout"] = "force-terminated owned Windows Job Object"
                    else:
                        proc.kill()
                        cleanup["force_stdout"] = "killed exact process handle"
                else:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                        cleanup["force_stdout"] = f"sent SIGKILL to process group {pid}"
                    except ProcessLookupError:
                        cleanup["force_stdout"] = "process group already absent"
                    except Exception as exc:  # noqa: BLE001
                        cleanup["force_stderr"] = f"process group SIGKILL failed: {exc}"
                        proc.kill()
                try:
                    proc.wait(timeout=graceful_timeout)
                except subprocess.TimeoutExpired:
                    cleanup["process_residue"] = [{"pid": pid, "state": "still_alive"}]
        except Exception as exc:  # noqa: BLE001
            cleanup["process_residue"] = [{"pid": pid, "error": f"{type(exc).__name__}: {exc}"}]
            return cleanup
        try:
            observed_pids = _durable_contained_pids(proc)
            cleanup["post_termination_enumeration_complete"] = True
            alive = _durable_alive_pids(observed_pids)
            exact_remaining: list[int] = []
            for remaining_pid in alive:
                stored = dict(identities.get(remaining_pid) or {})
                if not stored:
                    cleanup["process_residue"] = [
                        {"pid": remaining_pid, "state": "descendant_ownership_unverified"}
                    ]
                    return cleanup
                matched, _reason, _observed = _durable_process_identity_matches(
                    stored,
                    command_digest=str(stored.get("command_digest", "")),
                )
                if matched:
                    exact_remaining.append(remaining_pid)
            cleanup["process_residue"] = [
                {"pid": remaining_pid, "state": "still_alive"}
                for remaining_pid in exact_remaining
            ]
            cleanup["residue_count"] = len(exact_remaining)
            cleanup["cleanup_verified"] = bool(
                cleanup["enumeration_complete"]
                and cleanup["ownership_validated"]
                and not exact_remaining
            )
        except Exception as exc:  # noqa: BLE001
            cleanup["post_termination_enumeration_error"] = f"{type(exc).__name__}: {exc}"
            cleanup["process_residue"] = [
                {"state": "post_termination_enumeration_unverified"}
            ]
        return cleanup

    def _capture_timed_out_process_output(
        self,
        proc: subprocess.Popen[str],
        collector: _DurablePipeCollector | None = None,
    ) -> dict[str, Any]:
        if collector is not None and collector.has_readers:
            return collector.snapshot(join_timeout=_DURABLE_TIMEOUT_DRAIN_SECONDS)
        if collector is None:
            collector = _DurablePipeCollector(proc)
        if not collector.has_readers:
            captured: dict[str, Any] = {
                "stdout": "",
                "stderr": "",
                "output_capture": {
                    "attempted": True,
                    "concurrent_drain": False,
                    "drain_timeout_seconds": _DURABLE_TIMEOUT_DRAIN_SECONDS,
                    "stdout_truncated": False,
                    "stderr_truncated": False,
                    "total_truncated": False,
                    "timed_out": False,
                },
            }
            try:
                stdout, stderr = proc.communicate(timeout=_DURABLE_TIMEOUT_DRAIN_SECONDS)
            except subprocess.TimeoutExpired as exc:
                captured["output_capture"]["timed_out"] = True
                stdout = getattr(exc, "output", "") or ""
                stderr = getattr(exc, "stderr", "") or ""
            except Exception as exc:  # noqa: BLE001
                captured["output_capture"]["error"] = f"{type(exc).__name__}: {exc}"
                stdout = ""
                stderr = ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            stdout_text, stdout_truncated = _tail_with_limit(
                _redact_durable_output(str(stdout or "")),
                _DURABLE_TIMEOUT_STDOUT_LIMIT,
            )
            stderr_text, stderr_truncated = _tail_with_limit(
                _redact_durable_output(str(stderr or "")),
                _DURABLE_TIMEOUT_STDERR_LIMIT,
            )
            captured["stdout"] = stdout_text
            captured["stderr"] = stderr_text
            captured["output_capture"]["stdout_truncated"] = stdout_truncated
            captured["output_capture"]["stderr_truncated"] = stderr_truncated
            captured["output_capture"]["total_truncated"] = stdout_truncated or stderr_truncated
            captured["output_capture"]["stdout_limit_bytes"] = _DURABLE_TIMEOUT_STDOUT_LIMIT
            captured["output_capture"]["stderr_limit_bytes"] = _DURABLE_TIMEOUT_STDERR_LIMIT
            captured["output_capture"]["total_limit_bytes"] = _DURABLE_TIMEOUT_TOTAL_LIMIT
            captured["output_capture"]["stdout_bytes_seen"] = len(
                str(stdout or "").encode("utf-8", errors="replace")
            )
            captured["output_capture"]["stderr_bytes_seen"] = len(
                str(stderr or "").encode("utf-8", errors="replace")
            )
            captured["output_capture"]["total_bytes_seen"] = (
                captured["output_capture"]["stdout_bytes_seen"]
                + captured["output_capture"]["stderr_bytes_seen"]
            )
            captured["output_capture"]["redacted"] = str(stdout or "") != _redact_durable_output(
                str(stdout or "")
            ) or str(stderr or "") != _redact_durable_output(str(stderr or ""))
            return captured
        return collector.snapshot(join_timeout=_DURABLE_TIMEOUT_DRAIN_SECONDS)

    async def _execute_capability_for_durable(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        process_tree: dict[str, Any],
    ) -> dict[str, Any]:
        cap_name = req.capability
        cap_params = dict(req.params)
        risk_class = req.risk_class
        verdict_token = str(cap_params.pop("governance_verdict_id", ""))
        verdict_ok, verdict_reason = self._validate_verdict(
            cap_name,
            risk_class,
            verdict_token,
            request_id=req.request_id,
            correlation_id=req.correlation_id,
            candidate_sha=req.candidate_sha,
            effect_class="CONSEQUENTIAL_WRITE",
            payload_digest=req.diagnostics.get("verdict_payload_digest", "")
            if isinstance(req.diagnostics, dict)
            else "",
            idempotency_key=req.idempotency_key,
            cap_params=cap_params,
            allow_consequential_write=True,
        )
        if not verdict_ok:
            return {"success": False, "error": f"node verdict rejected: {verdict_reason}"}
        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        cap_config = self._config.capabilities.get(adapter_key)
        if cap_config is None and adapter_key in self._adapters:
            cap_config = CapabilityConfig()
        allowed, reason = validate_request(cap_name, cap_params, risk_class, cap_config)
        if not allowed:
            return {"success": False, "error": f"node governance denied: {reason}"}
        adapter = self._adapters.get(adapter_key)
        if adapter is None:
            return {"success": False, "error": f"adapter not available: {adapter_key}"}
        timeout = max(1.0, min(float(cap_params.get("timeout", 30)), 300.0))
        logical = getattr(self, "_durable_logical_executions", {}).get(req.request_id)
        if adapter_key == "shell":
            if logical is not None:
                logical["claim_id"] = claim_id
                logical["execution_identity"] = self._durable_execution_identity(
                    req,
                    claim_id=claim_id,
                )
                logical["state"] = "AUTHORIZED"
            return await self._execute_shell_for_durable(
                req,
                cap_name=cap_name,
                cap_params=cap_params,
                claim_id=claim_id,
                process_tree=process_tree,
                timeout=timeout,
            )
        running_ack = await self._announce_durable_running(
            req,
            claim_id=claim_id,
            process_tree=process_tree,
        )
        if not running_ack.get("ok"):
            return {
                "success": False,
                "error": f"running acknowledgement rejected: {running_ack.get('error', '')}",
            }
        current = self._durable_store.get_request(req.request_id)
        if current is None:
            return {
                "success": False,
                "error": "durable request missing before adapter start",
                "durable_request_missing_after_running": True,
                "cleanup": {"process_residue": []},
            }
        if current and current.lifecycle_state == "CANCEL_REQUESTED":
            cleanup = {
                "process_residue": [],
                "cancel_reason": "cancel requested before adapter start",
                **current.cancellation_identity(claim_id=claim_id),
            }
            return {
                "success": False,
                "error": "cancel requested before adapter start",
                "cleanup": cleanup,
            }
        if current and (current.lifecycle_state != "RUNNING" or current.claim_id != claim_id):
            return {
                "success": False,
                "error": f"running state changed before adapter start: {current.lifecycle_state}",
            }
        if current and self._durable_request_expired(current):
            return {
                "success": False,
                "error": "request expired before adapter start",
                "cleanup": {"process_residue": []},
            }
        if logical is not None:
            logical["state"] = "STARTED"
            logical["claim_id"] = claim_id
            logical["execution_identity"] = self._durable_execution_identity(
                req,
                claim_id=claim_id,
            )
            logical["started_at"] = time.monotonic()
        if hasattr(adapter, "execute_async") and callable(adapter.execute_async):
            operation = asyncio.create_task(adapter.execute_async(cap_name, cap_params))
            if logical is not None:
                logical["operation_future"] = operation
            try:
                return await asyncio.wait_for(asyncio.shield(operation), timeout=timeout)
            except asyncio.TimeoutError:
                self._durable_store.record_transport_diagnostic(
                    req.request_id,
                    "EXECUTION_TIMEOUT_OUTCOME_PENDING",
                    {"capability": cap_name, "timeout_s": timeout},
                )
                return await asyncio.shield(operation)
        loop = asyncio.get_event_loop()
        executor = self._camera_executor if adapter_key == "camera" else None
        operation = loop.run_in_executor(executor, adapter.execute, cap_name, cap_params)
        if logical is not None:
            logical["operation_future"] = operation
        try:
            return await asyncio.wait_for(asyncio.shield(operation), timeout=timeout)
        except asyncio.TimeoutError:
            self._durable_store.record_transport_diagnostic(
                req.request_id,
                "EXECUTION_TIMEOUT_OUTCOME_PENDING",
                {"capability": cap_name, "timeout_s": timeout},
            )
            return await asyncio.shield(operation)

    async def _execute_shell_for_durable(
        self,
        req: DurableRemoteRequest,
        *,
        cap_name: str,
        cap_params: dict[str, Any],
        claim_id: str,
        process_tree: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        argv = cap_params.get("argv")
        command = cap_params.get("command", "")
        cwd = cap_params.get("cwd")
        if argv and isinstance(argv, list):
            args: list[str] | str = [str(a) for a in argv]
            use_shell = False
        elif command:
            if cap_name == "shell.powershell" and sys.platform == "win32":
                args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
                use_shell = False
            else:
                args = command
                use_shell = True
        else:
            return {"success": False, "error": "no command or argv provided"}

        proc: subprocess.Popen[str] | None = None
        output_collector: _DurablePipeCollector | None = None
        last_tree_pids: list[int] = []
        try:
            logical = getattr(self, "_durable_logical_executions", {}).get(req.request_id)
            execution_identity = dict(
                (logical or {}).get("execution_identity")
                or self._durable_execution_identity(req, claim_id=claim_id)
            )
            launch_intent_id = sha256_json(
                {
                    "execution_identity": execution_identity,
                    "command_digest": req.payload_digest,
                    "capability": cap_name,
                }
            )
            launch_material = {
                "command_digest": req.payload_digest,
                "root_pid": None,
                "pre_start_containment": True,
                "execution_identity": execution_identity,
                "launch_intent_id": launch_intent_id,
                "launch_not_attempted": True,
            }
            current = self._durable_store.mark_shell_launch_state(
                req.request_id,
                claim_id=claim_id,
                launch_state=SHELL_LAUNCH_INTENT_PERSISTED,
                launch_material=launch_material,
            )
            if current.lifecycle_state != "CLAIMED":
                return {
                    "success": False,
                    "error": f"launch intent rejected into {current.lifecycle_state}",
                    "execution_outcome_unresolved": current.lifecycle_state
                    == "RECONCILIATION_REQUIRED",
                }
            current = self._durable_store.get_request(req.request_id)
            if current and current.lifecycle_state == "CANCEL_REQUESTED":
                cleanup = {
                    "process_residue": [],
                    "cancel_reason": "cancel requested before process start",
                    **current.cancellation_identity(claim_id=claim_id),
                }
                return {
                    "success": False,
                    "error": "cancel requested before process start",
                    "cleanup": cleanup,
                }
            if current is None:
                return {
                    "success": False,
                    "error": "durable request missing before process start",
                    "durable_request_missing_after_running": True,
                    "cleanup": {"process_residue": []},
                }
            if current and (current.lifecycle_state != "CLAIMED" or current.claim_id != claim_id):
                return {
                    "success": False,
                    "error": f"claimed state changed before process start: {current.lifecycle_state}",
                }
            if current and self._durable_request_expired(current):
                return {
                    "success": False,
                    "error": "request expired before process start",
                    "cleanup": {"process_residue": []},
                }

            extra: dict[str, Any] = {}
            if sys.platform == "win32":
                extra["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x00000004
            else:
                extra["start_new_session"] = True
            launch_material["launch_not_attempted"] = False
            launch_material["launch_attempted_at"] = time.time()
            current = self._durable_store.mark_shell_launch_state(
                req.request_id,
                claim_id=claim_id,
                launch_state=SHELL_LAUNCH_IN_PROGRESS,
                launch_material=launch_material,
            )
            if current.lifecycle_state != "CLAIMED":
                return {
                    "success": False,
                    "error": f"launch attempt rejected into {current.lifecycle_state}",
                    "execution_outcome_unresolved": True,
                }
            if logical is not None:
                logical["state"] = "STARTED"
                logical["execution_identity"] = execution_identity
                logical["started_at"] = time.monotonic()
            proc = subprocess.Popen(
                args,
                cwd=cwd,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **extra,
            )
            process_identity = _durable_process_identity(
                proc.pid,
                command_digest=req.payload_digest,
            )
            process_identity.update(
                {
                    "logical_execution_id": execution_identity["logical_execution_id"],
                    "launch_intent_id": launch_intent_id,
                    "parent_identity": {
                        "pid": os.getpid(),
                        "node_id": req.node_id,
                    },
                }
            )
            try:
                containment = _durable_attach_process_containment(
                    proc,
                    containment_id=launch_intent_id,
                )
            except Exception:
                # The Windows child is still suspended here, so terminating its
                # exact process handle cannot race PID reuse or escaped children.
                proc.kill()
                proc.wait(timeout=5)
                raise
            setattr(proc, "_umh_containment", containment)
            output_collector = _DurablePipeCollector(proc)
            self._durable_processes[req.request_id] = proc
            try:
                last_tree_pids = _durable_contained_pids(proc)
            except Exception:
                last_tree_pids = [proc.pid]
            setattr(proc, "_umh_process_identity", dict(process_identity))
            setattr(proc, "_umh_owned_process_identities", {proc.pid: dict(process_identity)})
            containment_material = {
                "kind": "windows_job_object" if containment is not None else "process_group",
                "containment_id": launch_intent_id,
                "complete_tree_boundary": bool(containment is not None or sys.platform != "win32"),
            }
            process_tree = {
                **process_tree,
                **launch_material,
                "root_pid": proc.pid,
                "process_identity": process_identity,
                "process_containment": containment_material,
            }
            current = self._durable_store.mark_shell_launch_state(
                req.request_id,
                claim_id=claim_id,
                launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
                launch_material=process_tree,
            )
            if current.lifecycle_state != "CLAIMED":
                cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                return {
                    "success": False,
                    "error": f"process identity persistence rejected into {current.lifecycle_state}",
                    "cleanup": cleanup,
                    "execution_outcome_unresolved": bool(cleanup.get("process_residue")),
                }
            if containment is not None:
                resume_state = _SUSPEND_STATE_UNKNOWN
                try:
                    resume_evidence = containment.resume_suspended_process(
                        proc,
                        launch_intent_id=launch_intent_id,
                        logical_execution_id=execution_identity["logical_execution_id"],
                    )
                except _DurableResumeStateUncertain as exc:
                    resume_evidence = _durable_observe_process_after_unexpected_resume(
                        proc,
                        evidence=exc.evidence,
                    )
                    resume_state = resume_evidence.state
                    process_tree["suspend_state_evidence"] = resume_evidence.to_dict()
                    self._durable_store.mark_shell_launch_state(
                        req.request_id,
                        claim_id=claim_id,
                        launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
                        launch_material=process_tree,
                    )
                    if resume_state in {
                        _SUSPEND_STATE_PROVEN_RESUMED,
                        _SUSPEND_STATE_PROVEN_EXITED,
                    }:
                        resume_observation = resume_evidence.to_dict()
                    else:
                        cleanup = await self._terminate_durable_process_tree(
                            proc,
                            graceful_timeout=5.0,
                        )
                        cleanup.update(
                            {
                                "resume_previous_suspend_count": (
                                    resume_evidence.previous_suspend_count
                                ),
                                "resume_state_observation": resume_state,
                                "suspend_state_evidence": resume_evidence.to_dict(),
                                "resume_error": str(exc),
                                "duplicate_resume_fenced": True,
                                "duplicate_launch_fenced": True,
                            }
                        )
                        if (
                            resume_state == _SUSPEND_STATE_PROVEN_SUSPENDED
                            and cleanup.get("cleanup_verified") is True
                        ):
                            cleanup["launch_outcome_known"] = True
                            cleanup["process_never_resumed_proven"] = True
                            return {
                                "success": False,
                                "error": str(exc),
                                "cleanup": cleanup,
                            }
                        cleanup["resume_state_uncertain"] = True
                        cleanup["execution_outcome_unknown"] = True
                        return {
                            "success": False,
                            "error": str(exc),
                            "cleanup": cleanup,
                            "execution_outcome_unresolved": True,
                        }
                except Exception as exc:
                    cleanup = await self._terminate_durable_process_tree(
                        proc,
                        graceful_timeout=5.0,
                    )
                    cleanup.update(
                        {
                            "resume_previous_suspend_count": None,
                            "resume_state_observation": _SUSPEND_STATE_UNKNOWN,
                            "resume_error": str(exc),
                            "resume_state_uncertain": True,
                            "execution_outcome_unknown": True,
                            "duplicate_resume_fenced": True,
                            "duplicate_launch_fenced": True,
                        }
                    )
                    return {
                        "success": False,
                        "error": f"ambiguous ResumeThread state: {exc}",
                        "cleanup": cleanup,
                        "execution_outcome_unresolved": True,
                    }
                else:
                    resume_state = resume_evidence.state
                    resume_observation = resume_evidence.to_dict()
                process_tree["resume_observation"] = dict(resume_observation)
                process_tree["suspend_state_evidence"] = dict(resume_observation)
                self._durable_store.mark_shell_launch_state(
                    req.request_id,
                    claim_id=claim_id,
                    launch_state=SHELL_PROCESS_IDENTITY_PERSISTED,
                    launch_material=process_tree,
                )
            if containment is None or resume_state != _SUSPEND_STATE_PROVEN_EXITED:
                running_ack = await self._announce_durable_running(
                    req,
                    claim_id=claim_id,
                    process_tree=process_tree,
                )
                if not running_ack.get("ok"):
                    self._durable_store.record_transport_diagnostic(
                        req.request_id,
                        "RUNNING_ACK_UNRESOLVED_AFTER_PROCESS_IDENTITY",
                        {
                            "claim_id": claim_id,
                            "execution_id": execution_identity["execution_id"],
                            "error": str(running_ack.get("error", "")),
                        },
                    )

            deadline = time.time() + timeout
            while proc.poll() is None:
                try:
                    observed_identities = _durable_capture_owned_identities(
                        proc,
                        command_digest=req.payload_digest,
                    )
                    observed = list(observed_identities)
                    last_tree_pids = sorted(set(last_tree_pids + observed))
                except Exception:
                    last_tree_pids = sorted(set(last_tree_pids + [proc.pid]))
                local = self._durable_store.get_request(req.request_id)
                if local and local.lifecycle_state == "CANCEL_REQUESTED":
                    cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                    captured = self._capture_timed_out_process_output(proc, output_collector)
                    cleanup["cancel_reason"] = "cancel requested during execution"
                    cleanup.update(local.cancellation_identity(claim_id=claim_id))
                    if captured["output_capture"].get("timed_out"):
                        cleanup["reader_timeout_after_termination"] = True
                        cleanup = _durable_fail_closed_reader_timeout_cleanup(
                            proc,
                            cleanup,
                            last_tree_pids,
                        )
                    return {
                        "success": False,
                        "error": "cancel requested during execution",
                        "cleanup": cleanup,
                        **captured,
                    }
                if time.time() >= deadline:
                    cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                    captured = self._capture_timed_out_process_output(proc, output_collector)
                    if captured["output_capture"].get("timed_out"):
                        cleanup["reader_timeout_after_termination"] = True
                        cleanup = _durable_fail_closed_reader_timeout_cleanup(
                            proc,
                            cleanup,
                            last_tree_pids,
                        )
                    return {
                        "success": False,
                        "error": f"{cap_name} timed out after {timeout:.0f}s",
                        "cleanup": cleanup,
                        **captured,
                    }
                await asyncio.sleep(0.5)
            captured = output_collector.snapshot(join_timeout=_DURABLE_TIMEOUT_DRAIN_SECONDS)
            if captured["output_capture"].get("timed_out"):
                cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                cleanup["reader_timeout_after_exit"] = True
                cleanup = _durable_fail_closed_reader_timeout_cleanup(
                    proc,
                    cleanup,
                    last_tree_pids,
                )
                return {
                    "success": False,
                    "error": "durable output readers timed out after process exit",
                    "cleanup": cleanup,
                    **captured,
                }
            cleanup = _durable_post_exit_process_cleanup(proc, last_tree_pids)
            if cleanup.get("post_exit_process_check_ok") is not True or cleanup.get(
                "process_residue"
            ):
                return {
                    "success": False,
                    "error": "durable success process residue unproven",
                    "cleanup": cleanup,
                    **captured,
                }
            return {
                "success": proc.returncode == 0,
                "stdout": captured["stdout"],
                "stderr": captured["stderr"],
                "exit_code": proc.returncode,
                "output_capture": captured["output_capture"],
                "cleanup": cleanup,
            }
        except asyncio.CancelledError:
            cleanup: dict[str, Any] = {
                "process_residue": [],
                "interrupted_running_failed_closed": True,
                "request_id": req.request_id,
                "correlation_id": req.correlation_id,
                "node_id": req.node_id,
                "candidate_sha": req.candidate_sha,
                "claim_id": claim_id,
            }
            captured: dict[str, Any] = {}
            if proc is not None and proc.poll() is None:
                cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                cleanup["interrupted_running_failed_closed"] = True
                cleanup.update(
                    {
                        "request_id": req.request_id,
                        "correlation_id": req.correlation_id,
                        "node_id": req.node_id,
                        "candidate_sha": req.candidate_sha,
                        "claim_id": claim_id,
                    }
                )
                if output_collector is not None:
                    captured = self._capture_timed_out_process_output(proc, output_collector)
                    if captured.get("output_capture", {}).get("timed_out"):
                        cleanup["reader_timeout_after_termination"] = True
                        cleanup = _durable_fail_closed_reader_timeout_cleanup(
                            proc,
                            cleanup,
                            last_tree_pids or [proc.pid],
                        )
            return {
                "success": False,
                "error": "durable shell execution cancelled before terminal result",
                "cleanup": cleanup,
                **captured,
            }
        except Exception as exc:  # noqa: BLE001
            cleanup: dict[str, Any] = {"process_residue": []}
            if proc is not None:
                if proc.poll() is None:
                    cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
                else:
                    cleanup = _durable_post_exit_process_cleanup(
                        proc,
                        last_tree_pids or [proc.pid],
                    )
                if cleanup.get("post_exit_process_check_ok") is not True:
                    cleanup.setdefault(
                        "process_residue", [{"state": "durable_shell_cleanup_unverified"}]
                    )
            return {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "cleanup": cleanup,
            }
        finally:
            self._durable_processes.pop(req.request_id, None)
            if proc is not None:
                containment = getattr(proc, "_umh_containment", None)
                if containment is not None:
                    containment.close()

    async def _handle_capability(self, msg: dict[str, Any]) -> None:
        async with self._capability_semaphore:
            params = msg.get("params", {})
            msg_id = msg.get("id")
            cap_name = params.get("capability_name", "")
            cap_params = params.get("params", {})
            risk_class = params.get("risk_class", "REVERSIBLE_WRITE")
            verdict_token = params.get("governance_verdict_id", "")

            # Node-side verdict validation (fail-closed). A write-class
            # capability must carry a signed governance verdict bound to THIS
            # node and THIS capability. Missing or invalid verdict → reject
            # before touching any adapter. This is the last line of the mesh
            # trust boundary — the node never trusts the orchestrator blindly.
            verdict_ok, verdict_reason = self._validate_verdict(
                cap_name,
                risk_class,
                verdict_token,
                request_id=str(params.get("request_id", "")),
                correlation_id=str(params.get("correlation_id", "")),
                candidate_sha=str(params.get("candidate_sha", "")),
                effect_class=str(params.get("effect_class", "")),
                payload_digest=str(params.get("payload_digest", "")),
                idempotency_key=str(params.get("idempotency_key", "")),
                cap_params=cap_params if isinstance(cap_params, dict) else {},
            )
            if not verdict_ok:
                logger.warning(
                    "capability %s rejected by node verdict gate: %s",
                    cap_name,
                    verdict_reason,
                )
                await self._send_ws(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {
                                "success": False,
                                "error": f"node verdict rejected: {verdict_reason}",
                            },
                            "id": msg_id,
                        }
                    )
                )
                return

            adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
            cap_config = self._config.capabilities.get(adapter_key)
            if cap_config is None and adapter_key in self._adapters:
                cap_config = CapabilityConfig()
            # pass the ORIGINAL dotted name — governance normalizes it and
            # denies unknown operations (adapter_key stays for lookup only)
            allowed, reason = validate_request(cap_name, cap_params, risk_class, cap_config)

            if not allowed:
                logger.warning("capability %s denied: %s", cap_name, reason)
                await self._send_ws(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {
                                "success": False,
                                "error": f"node governance denied: {reason}",
                            },
                            "id": msg_id,
                        }
                    )
                )
                return

            adapter = self._adapters.get(adapter_key)
            if adapter is None:
                await self._send_ws(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "result": {
                                "success": False,
                                "error": f"adapter not available: {adapter_key}",
                            },
                            "id": msg_id,
                        }
                    )
                )
                return

            t0 = time.monotonic()
            _MAX_CAPABILITY_TIMEOUT_S = 300.0
            raw_timeout = params.get("timeout_seconds", _CONTROL_TIMEOUT_S)
            request_timeout = max(1.0, min(float(raw_timeout), _MAX_CAPABILITY_TIMEOUT_S))
            has_async = hasattr(adapter, "execute_async") and callable(adapter.execute_async)

            try:
                if has_async:
                    result = await asyncio.wait_for(
                        adapter.execute_async(cap_name, cap_params),
                        timeout=request_timeout,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    executor = self._camera_executor if adapter_key == "camera" else None
                    if "timeout" not in cap_params and request_timeout > _CONTROL_TIMEOUT_S:
                        cap_params["timeout"] = int(request_timeout)
                    result = await asyncio.wait_for(
                        loop.run_in_executor(executor, adapter.execute, cap_name, cap_params),
                        timeout=request_timeout,
                    )
            except asyncio.TimeoutError:
                effective_timeout = request_timeout
                logger.warning("capability %s timed out after %.0fs", cap_name, effective_timeout)
                result = {"success": False, "error": f"{cap_name} timed out"}
            duration = (time.monotonic() - t0) * 1000

            await self._send_ws(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {
                            "success": result.get("success", False),
                            "result_data": result,
                            "latency_ms": round(duration, 1),
                            "side_effects": [],
                        },
                        "id": msg_id,
                    }
                )
            )

    async def emit_signal(
        self,
        content_type: str,
        payload: dict[str, Any],
        signal_class: str = "event",
        urgency: str = "LOW",
    ) -> None:
        """Emit a signal to the VPS (control plane signals, not media frames)."""
        if not self._connected or self._ws is None:
            return
        msg = {
            "jsonrpc": "2.0",
            "method": "signal.emit",
            "params": {
                "content_type": content_type,
                "payload": payload,
                "urgency": urgency,
                "signal_class": signal_class,
            },
            "id": self._next_id(),
        }
        try:
            await self._send_ws(json.dumps(msg))
        except Exception as exc:
            logger.warning("signal emit failed: %s", exc)

    def _get_tailscale_ip(self) -> str:
        try:
            import subprocess

            from nodes.windows.umh_node.subprocess_utils import no_window_kwargs

            result = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
                **no_window_kwargs(),
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return ""
