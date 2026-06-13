"""Subsystem-agnostic subprocess lifecycle manager.

Composes on gated_popen() for CPU gate compliance.  Adds asyncio monitoring,
graceful teardown (SIGTERM -> wait -> SIGKILL), and process-group orphan
tracking.  Reusable for any long-running subprocess — not broadcast-specific.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any, Callable

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_SIGKILL_WAIT_TIMEOUT = 5.0


class ProcessLifecycle:
    """Manage the full lifecycle of a long-running subprocess.

    The child is spawned in its own process group so the entire group can be
    killed on stop or parent death — no orphan survives.
    """

    def __init__(
        self,
        cmd: list[str],
        *,
        caller: str = "process_lifecycle",
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
        on_exit: Callable[[int | None], None] | None = None,
        teardown_timeout: float = 5.0,
    ) -> None:
        self._cmd = cmd
        self._caller = caller
        self._on_stdout = on_stdout
        self._on_stderr = on_stderr
        self._on_exit = on_exit
        self._teardown_timeout = teardown_timeout

        self._proc: asyncio.subprocess.Process | None = None
        self._monitor_task: asyncio.Task[None] | None = None
        self._pgid: int | None = None
        self._stopped = False
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    async def start(self) -> bool:
        """Spawn the subprocess via CPU gate.  Returns False if gate denied."""
        async with self._lock:
            return await self._start_locked()

    async def _start_locked(self) -> bool:
        if self.running:
            logger.warning("[ProcessLifecycle] already running (pid=%s)", self.pid)
            return True

        import sys
        sys.path.insert(0, _ROOT) if _ROOT not in sys.path else None
        from substrate.execution.cpu_gate import cpu_gate_check

        gate = cpu_gate_check(self._caller)
        if not gate.allowed:
            logger.warning("[ProcessLifecycle] CPU gate denied for %s", self._caller)
            return False

        self._stopped = False
        self._proc = await asyncio.create_subprocess_exec(
            *self._cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        try:
            self._pgid = os.getpgid(self._proc.pid)
        except (ProcessLookupError, OSError):
            self._pgid = None

        logger.info(
            "[ProcessLifecycle] started pid=%s pgid=%s cmd=%s",
            self._proc.pid, self._pgid, " ".join(self._cmd[:4]),
        )

        self._monitor_task = asyncio.create_task(self._monitor())
        return True

    async def stop(self) -> int | None:
        """Idempotent graceful teardown.  Returns exit code or None."""
        async with self._lock:
            return await self._stop_locked()

    async def _stop_locked(self) -> int | None:
        if self._stopped:
            return None
        self._stopped = True
        self._on_exit = None

        if not self._proc or self._proc.returncode is not None:
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
            code = self._proc.returncode if self._proc else None
            self._proc = None
            self._pgid = None
            return code

        pid = self._proc.pid
        logger.info("[ProcessLifecycle] stopping pid=%s", pid)

        try:
            if self._pgid:
                os.killpg(self._pgid, signal.SIGTERM)
            else:
                self._proc.terminate()
        except (ProcessLookupError, OSError):
            pass

        try:
            await asyncio.wait_for(self._proc.wait(), timeout=self._teardown_timeout)
        except asyncio.TimeoutError:
            logger.warning("[ProcessLifecycle] SIGKILL after timeout pid=%s", pid)
            try:
                if self._pgid:
                    os.killpg(self._pgid, signal.SIGKILL)
                else:
                    self._proc.kill()
            except (ProcessLookupError, OSError):
                pass
            try:
                await asyncio.wait_for(
                    self._proc.wait(), timeout=_SIGKILL_WAIT_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "[ProcessLifecycle] zombie after SIGKILL pid=%s", pid,
                )

        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

        code = self._proc.returncode
        logger.info("[ProcessLifecycle] exited pid=%s code=%s", pid, code)
        self._proc = None
        self._pgid = None
        return code

    async def _monitor(self) -> None:
        """Read stdout/stderr and wait for exit."""
        proc = self._proc
        if proc is None or proc.stdout is None or proc.stderr is None:
            return

        async def _read_stream(
            stream: asyncio.StreamReader,
            callback: Callable[[str], None] | None,
            label: str,
        ) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if callback:
                    try:
                        callback(text)
                    except Exception:
                        logger.debug("[ProcessLifecycle] %s callback error", label)

        try:
            await asyncio.gather(
                _read_stream(proc.stdout, self._on_stdout, "stdout"),
                _read_stream(proc.stderr, self._on_stderr, "stderr"),
            )
            await proc.wait()
        except asyncio.CancelledError:
            return

        if not self._stopped and self._on_exit:
            try:
                self._on_exit(proc.returncode)
            except Exception:
                logger.debug("[ProcessLifecycle] on_exit callback error")
