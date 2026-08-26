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
import urllib.error
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
from uuid import uuid4

import websockets

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
    STATE_ORDER,
    TERMINAL_STATES,
    default_node_root,
)

logger = logging.getLogger(__name__)

_MEDIA_QUEUE_MAX = 4
_CONTROL_TIMEOUT_S = 8.0
_DURABLE_CLAIM_ACQUIRE_TIMEOUT_S = 30.0
_DURABLE_CLAIM_RETRY_SLEEP_S = 1.0
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
_DURABLE_TIMEOUT_TOTAL_LIMIT = (
    _DURABLE_TIMEOUT_STDOUT_LIMIT + _DURABLE_TIMEOUT_STDERR_LIMIT
)
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
                lines.append(f"exact pid force cleanup failed pid={pid}: {type(exc).__name__}: {exc}")
        else:
            try:
                os.kill(pid, signal.SIGKILL)
                lines.append(f"sent SIGKILL to exact pid {pid}")
            except ProcessLookupError:
                lines.append(f"exact pid already absent {pid}")
            except Exception as exc:  # noqa: BLE001
                lines.append(f"exact pid force cleanup failed pid={pid}: {type(exc).__name__}: {exc}")
    return lines


def _durable_fail_closed_reader_timeout_cleanup(
    proc: subprocess.Popen[str],
    cleanup: dict[str, Any],
    last_tree_pids: list[int],
) -> dict[str, Any]:
    try:
        last_tree_pids = sorted(set(last_tree_pids + _durable_owned_process_tree_pids(proc.pid)))
    except Exception:
        last_tree_pids = sorted(set(last_tree_pids + [proc.pid]))
    alive = _durable_alive_pids(last_tree_pids)
    if alive:
        cleanup.setdefault("force_stdout", "")
        cleanup["force_stdout"] = "\n".join(
            str(x)
            for x in [
                cleanup.get("force_stdout", ""),
                *_durable_force_exact_pids(alive),
            ]
            if x
        )
        remaining = _durable_alive_pids(alive)
        cleanup["process_residue"] = [
            {"pid": pid, "state": "still_alive"} for pid in remaining
        ]
    elif not any(pid != proc.pid for pid in last_tree_pids):
        cleanup["process_residue"] = [
            {"state": "reader_timeout_descendant_identity_unknown"}
        ]
    else:
        cleanup["process_residue"] = []
    return cleanup


def _durable_post_exit_process_cleanup(
    proc: subprocess.Popen[str],
    last_tree_pids: list[int],
) -> dict[str, Any]:
    cleanup: dict[str, Any] = {
        "root_pid": proc.pid,
        "post_exit_process_check": True,
        "forced": False,
        "process_residue": [],
    }
    try:
        observed = _durable_owned_process_tree_pids(proc.pid)
    except Exception as exc:  # noqa: BLE001
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
    if not alive:
        return cleanup
    cleanup["forced"] = True
    cleanup["process_residue_detected_after_exit"] = True
    try:
        cleanup["force_stdout"] = "\n".join(_durable_force_exact_pids(alive))
    except Exception as exc:  # noqa: BLE001
        cleanup["post_exit_process_check_ok"] = False
        cleanup["force_cleanup_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [{"pid": pid, "state": "cleanup_unverified"} for pid in alive]
        return cleanup
    try:
        remaining = _durable_alive_pids(alive)
    except Exception as exc:  # noqa: BLE001
        cleanup["post_exit_process_check_ok"] = False
        cleanup["post_exit_remaining_scan_error"] = f"{type(exc).__name__}: {exc}"
        cleanup["process_residue"] = [{"pid": pid, "state": "remaining_scan_unverified"} for pid in alive]
        return cleanup
    cleanup["process_residue"] = [{"pid": pid, "state": "still_alive"} for pid in remaining]
    return cleanup


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
        self._ws_send_lock: asyncio.Lock | None = None

        self._adapters: dict[str, Any] = {}
        self._init_adapters()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_workspace_change: Callable[[dict[str, Any]], None] | None = None
        self._camera_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cam")
        self._capability_semaphore = asyncio.Semaphore(8)
        self._durable_store = DurableRemoteStore(default_node_root())
        self._durable_processes: dict[str, subprocess.Popen[str]] = {}
        self._durable_execution_locks: dict[str, asyncio.Lock] = {}
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
                    await self._send_ws(msg)
                except Exception as exc:
                    logger.debug("media send failed: %s", exc)
                    self._media_queue.clear()
                    break

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def _send_ws(self, payload: str | bytes) -> None:
        if self._ws is None:
            raise ConnectionError("node websocket not connected")
        send_lock = self._ws_send_lock
        if send_lock is None:
            await self._ws.send(payload)
            return
        async with send_lock:
            await self._ws.send(payload)

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
            except Exception as exc:
                logger.error("unexpected error: %s, reconnecting in %.0fs", exc, backoff)
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def stop(self) -> None:
        self._shutdown.set()
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
        if self._media_drain_task:
            self._media_drain_task.cancel()
            self._media_drain_task = None
        self._camera_executor.shutdown(wait=False, cancel_futures=True)
        if self._ws:
            await self._ws.close()

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
            self._ws = ws
            await self._send_hello()
            self._connected = True
            self._media_queue.clear()
            logger.info("connected to VPS mesh server")

            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._media_drain_task = asyncio.create_task(self._media_drain_loop())
            workspace_task = asyncio.create_task(self._workspace_emission_loop())
            try:
                async for raw in ws:
                    await self._handle_message(raw)
            finally:
                heartbeat_task.cancel()
                workspace_task.cancel()
                if self._media_drain_task:
                    self._media_drain_task.cancel()
                    self._media_drain_task = None
                self._connected = False

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

    async def _handle_message(self, raw: str) -> None:
        msg = json.loads(raw)
        method = msg.get("method", "")

        if method == "capability.execute":
            asyncio.create_task(self._safe_handle_capability(msg))
        elif method == "durable_command.request":
            asyncio.create_task(self._safe_handle_durable_command(msg))
        elif method == "outcome.notify":
            logger.info("outcome received: %s", msg.get("params", {}).get("summary", ""))
        elif "result" in msg or "error" in msg:
            self._handle_rpc_response(msg)
        else:
            logger.debug("unhandled message method: %s", method)

    def _handle_rpc_response(self, msg: dict[str, Any]) -> None:
        msg_id = msg.get("id")
        future = self._pending_rpc.pop(msg_id, None)
        if future is None or future.done():
            return
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
            return False, "DurableRemote consequential execution requires canonical consequential policy"
        if normalized_effect != CONSEQUENTIAL_WRITE_EFFECT:
            return False, "write-class capability requires CONSEQUENTIAL_WRITE effect binding"
        if not is_write_class(risk_class):
            return False, "write-class capability risk_class conflicts with canonical consequential policy"

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

    def _durable_request_identity(self, req: DurableRemoteRequest) -> dict[str, str]:
        return {
            "request_id": req.request_id,
            "correlation_id": req.correlation_id,
            "node_id": req.node_id,
            "candidate_sha": req.candidate_sha,
            "idempotency_key": req.idempotency_key,
            "payload_digest": req.payload_digest,
        }

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
        for _, request_id in sorted(terminal)[: max(0, len(trajectories) - _DURABLE_TRAJECTORY_MAX)]:
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
        if (
            existing_status in {"FAIL_CLOSED", "RECONCILIATION_PENDING"}
            and req.lifecycle_state not in {"RUNNING", *TERMINAL_STATES}
        ):
            trajectory["updated_at"] = time.monotonic()
            return
        if req.lifecycle_state == "RUNNING":
            trajectory["status"] = "RUNNING_OR_RECONCILING"
        elif req.lifecycle_state in TERMINAL_STATES:
            trajectory["status"] = "TERMINAL_OBSERVED"
            trajectory["retain_until"] = (
                time.monotonic() + _DURABLE_TRAJECTORY_TOMBSTONE_TTL_S
            )
        elif req.lifecycle_state == "RECONCILIATION_REQUIRED":
            trajectory["status"] = "RECONCILIATION_PENDING"
            trajectory["retain_until"] = (
                time.monotonic() + _DURABLE_TRAJECTORY_TOMBSTONE_TTL_S
            )
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
        await self._fail_unresolved_durable_request(current, reason=reason)

    async def _send_durable_event(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        expect_ack: bool = False,
        timeout_s: float = _CONTROL_TIMEOUT_S,
    ) -> dict[str, Any] | None:
        if not self._connected or self._ws is None:
            return {"ok": False, "error": "node websocket not connected"} if expect_ack else None
        msg_id = self._next_id()
        future: asyncio.Future[dict[str, Any]] | None = None
        if expect_ack:
            future = asyncio.get_running_loop().create_future()
            self._pending_rpc[msg_id] = future
        message = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": payload,
                "id": msg_id,
            }
        )
        try:
            await self._send_ws(message)
            if not expect_ack or future is None:
                return None
            return await asyncio.wait_for(future, timeout=timeout_s)
        except asyncio.TimeoutError:
            self._pending_rpc.pop(msg_id, None)
            return {"ok": False, "error": f"{method} acknowledgement timed out"}
        except BaseException:
            if expect_ack:
                self._pending_rpc.pop(msg_id, None)
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
            self._durable_store.put_request(delivered_req)
            self._durable_store.update_request(delivered_req, "CANCEL_REQUESTED")

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
            self._durable_store.update_request(delivered_req, "CANCEL_REQUESTED")
            req = self._durable_store.get_request(delivered_req.request_id) or delivered_req
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

        if delivered_req.lifecycle_state == "CANCEL_REQUESTED":
            terminal = await self._cancel_durable_request(
                req,
                claim_id=req.claim_id or f"{self._config.node_id}-{uuid4().hex[:12]}",
                reason="cancel requested by controller",
            )
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
        self._durable_store.mark_claimed(req.request_id, claim_id=claim_id, process_tree=process_tree)
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
            if (
                self._durable_request_is_shell_backed(current)
                and not effective_process_tree.get("root_pid")
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
                "claim no longer executable: "
                f"state={effective_state} claim={current.claim_id}"
            ),
        )

    @staticmethod
    def _durable_request_is_shell_backed(req: DurableRemoteRequest) -> bool:
        cap_name = str(req.capability or "")
        adapter_key = cap_name.split(".")[0] if "." in cap_name else cap_name
        return adapter_key == "shell"

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
            state = "SUCCEEDED" if result.get("success") else "FAILED"
            cleanup = dict(result.get("cleanup") or {"process_residue": []})
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
    ) -> DurableRemoteRequest:
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
            "process_residue": [],
            "running_redelivery_failed_closed": True,
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
        result: dict[str, Any] = {
            "success": False,
            "error": "durable running acknowledgement failed closed",
            "reason": reason,
        }
        try:
            self._durable_store.publish_result(
                req.request_id,
                claim_id=claim_id,
                state="FAILED",
                result=result,
                cleanup=cleanup,
            )
        except KeyError:
            result["durable_request_missing_after_running"] = True
        self._record_durable_request_trajectory(
            req.request_id,
            status="FAIL_CLOSED",
            claim_id=claim_id,
            terminal=True,
        )
        await self._send_durable_event(
            "durable_command.result",
            {
                "request_id": req.request_id,
                "claim_id": claim_id,
                "state": "FAILED",
                "result": result,
                "cleanup": cleanup,
            },
        )
        return self._durable_store.get_request(req.request_id) or req

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
        if current.lifecycle_state == "CANCEL_REQUESTED":
            terminal = await self._cancel_durable_request(
                current,
                claim_id=claim_id,
                reason="cancel requested by controller",
            )
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

        cleanup = {
            "process_residue": [],
            "claim_acquisition_failed_closed": True,
            "claim_id": claim_id,
            "request_id": current.request_id,
            "correlation_id": current.correlation_id,
            "node_id": current.node_id,
            "candidate_sha": current.candidate_sha,
        }
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
                        "error": str(
                            readback.get("error", validated_ack.get("error", ""))
                        ),
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
        return self._validate_durable_claim_authority(
            readback,
            req,
            claim_id=claim_id,
            expected_state=expected_state,
            label="claim readback",
            allow_monotonic_claim_state=allow_monotonic_claim_state,
        )

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
        if timeout_s <= 0:
            return {"ok": False, "error": "claim readback deadline expired", "retryable": False}
        if not self._config.vps_host or not self._config.token:
            return {
                "ok": False,
                "error": "canonical claim readback unavailable: missing node auth",
                "retryable": False,
            }

        def _post() -> dict[str, Any]:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            req = urllib.request.Request(
                self._config.relay_http_url.rstrip("/") + "/durable-claim-state",
                data=body,
                headers={
                    "Authorization": f"Bearer {self._config.token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=max(0.1, timeout_s)) as resp:
                    raw = resp.read(64 * 1024)
            except urllib.error.HTTPError as exc:
                return {
                    "ok": False,
                    "error": f"canonical claim readback HTTP {exc.code}",
                    "retryable": 500 <= exc.code < 600,
                }
            except (OSError, TimeoutError) as exc:
                return {
                    "ok": False,
                    "error": f"canonical claim readback unavailable: {exc}",
                    "retryable": True,
                }
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                return {
                    "ok": False,
                    "error": f"canonical claim readback invalid JSON: {exc}",
                    "retryable": False,
                }
            if not isinstance(parsed, dict):
                return {
                    "ok": False,
                    "error": "canonical claim readback returned non-object",
                    "retryable": False,
                }
            return parsed

        return await asyncio.to_thread(_post)

    async def _announce_durable_running(
        self,
        req: DurableRemoteRequest,
        *,
        claim_id: str,
        process_tree: dict[str, Any],
    ) -> dict[str, Any]:
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
        proc = self._durable_processes.get(req.request_id)
        cleanup = {
            "process_residue": [],
            "cancel_reason": reason,
            **req.cancellation_identity(claim_id=claim_id),
        }
        if proc is not None and proc.poll() is None:
            cleanup = await self._terminate_durable_process_tree(proc, graceful_timeout=5.0)
            cleanup["cancel_reason"] = reason
            cleanup.update(req.cancellation_identity(claim_id=claim_id))
        elif req.process_tree.get("root_pid"):
            cleanup["process_residue"] = [
                {
                    "pid": req.process_tree.get("root_pid"),
                    "state": "running_process_owner_lost_after_restart",
                }
            ]
            cleanup["process_owner_lost_after_restart"] = True
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
            "forced": False,
            "process_residue": [],
        }
        try:
            if sys.platform == "win32":
                first = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T"],
                    capture_output=True,
                    text=True,
                    timeout=max(1.0, graceful_timeout),
                )
                cleanup["graceful_exit_code"] = first.returncode
                cleanup["graceful_stdout"] = first.stdout[-2000:]
                cleanup["graceful_stderr"] = first.stderr[-2000:]
            else:
                try:
                    os.killpg(pid, signal.SIGTERM)
                    cleanup["graceful_stdout"] = f"sent SIGTERM to process group {pid}"
                except ProcessLookupError:
                    cleanup["graceful_stdout"] = "process group already absent"
                except Exception as exc:  # noqa: BLE001
                    cleanup["graceful_stderr"] = f"process group SIGTERM failed: {exc}"
                    proc.terminate()
            try:
                proc.wait(timeout=graceful_timeout)
            except subprocess.TimeoutExpired:
                cleanup["forced"] = True
                if sys.platform == "win32":
                    forced = subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True,
                        text=True,
                        timeout=max(1.0, graceful_timeout),
                    )
                    cleanup["force_exit_code"] = forced.returncode
                    cleanup["force_stdout"] = forced.stdout[-2000:]
                    cleanup["force_stderr"] = forced.stderr[-2000:]
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
            captured["output_capture"]["redacted"] = (
                str(stdout or "") != _redact_durable_output(str(stdout or ""))
                or str(stderr or "") != _redact_durable_output(str(stderr or ""))
            )
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
        if adapter_key == "shell":
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
        try:
            if hasattr(adapter, "execute_async") and callable(adapter.execute_async):
                return await asyncio.wait_for(adapter.execute_async(cap_name, cap_params), timeout=timeout)
            loop = asyncio.get_event_loop()
            executor = self._camera_executor if adapter_key == "camera" else None
            return await asyncio.wait_for(
                loop.run_in_executor(executor, adapter.execute, cap_name, cap_params),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return {"success": False, "error": f"{cap_name} timed out after {timeout:.0f}s"}

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
            pre_start_tree = dict(process_tree)
            pre_start_tree.update(
                {
                    "command_digest": req.payload_digest,
                    "root_pid": None,
                    "pre_start_containment": True,
                }
            )
            running_ack = await self._announce_durable_running(
                req,
                claim_id=claim_id,
                process_tree=pre_start_tree,
            )
            if not running_ack.get("ok"):
                return {
                    "success": False,
                    "error": f"running acknowledgement rejected: {running_ack.get('error', '')}",
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
            if current and (current.lifecycle_state != "RUNNING" or current.claim_id != claim_id):
                return {
                    "success": False,
                    "error": f"running state changed before process start: {current.lifecycle_state}",
                }
            if current and self._durable_request_expired(current):
                return {
                    "success": False,
                    "error": "request expired before process start",
                    "cleanup": {"process_residue": []},
                }

            extra: dict[str, Any] = {}
            if sys.platform == "win32":
                extra["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                extra["start_new_session"] = True
            proc = subprocess.Popen(
                args,
                cwd=cwd,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **extra,
            )
            output_collector = _DurablePipeCollector(proc)
            self._durable_processes[req.request_id] = proc
            try:
                last_tree_pids = _durable_owned_process_tree_pids(proc.pid)
            except Exception:
                last_tree_pids = [proc.pid]
            process_tree = dict(process_tree)
            process_tree.update({"root_pid": proc.pid, "command_digest": req.payload_digest})
            self._durable_store.mark_running(
                req.request_id,
                claim_id=claim_id,
                process_tree=process_tree,
            )
            await self._send_durable_event(
                "durable_command.claimed",
                {
                    "request_id": req.request_id,
                    "claim_id": claim_id,
                    "state": "RUNNING",
                    "process_tree": process_tree,
                },
            )

            deadline = time.time() + timeout
            while proc.poll() is None:
                try:
                    observed = _durable_owned_process_tree_pids(proc.pid)
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
            if (
                cleanup.get("post_exit_process_check_ok") is not True
                or cleanup.get("process_residue")
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
                    cleanup.setdefault("process_residue", [{"state": "durable_shell_cleanup_unverified"}])
            return {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "cleanup": cleanup,
            }
        finally:
            self._durable_processes.pop(req.request_id, None)

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
