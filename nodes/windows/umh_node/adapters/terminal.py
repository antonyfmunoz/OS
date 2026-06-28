"""Terminal adapter — persistent shell sessions via subprocess pipes."""

from __future__ import annotations

import collections
import logging
import subprocess
import threading
import time
from typing import Any, Optional

from nodes.windows.umh_node.subprocess_utils import no_window_kwargs

logger = logging.getLogger(__name__)

# Control-key byte mapping (v1 — extend as needed)
_KEY_MAP: dict[str, bytes] = {
    "C-c": b"\x03",
    "C-d": b"\x04",
    "C-z": b"\x1a",
    "C-l": b"\x0c",
}


class TerminalSession:
    """A single persistent shell process with threaded output capture."""

    __slots__ = (
        "name",
        "process",
        "output_buffer",
        "lock",
        "reader_thread",
        "shell_type",
        "created_at",
        "last_activity",
        "_exit_code",
    )

    def __init__(
        self,
        name: str,
        process: subprocess.Popen,
        reader_thread: threading.Thread,
        shell_type: str,
    ) -> None:
        self.name = name
        self.process = process
        self.output_buffer: collections.deque[str] = collections.deque(maxlen=500)
        self.lock = threading.Lock()
        self.reader_thread = reader_thread
        self.shell_type = shell_type
        self.created_at = time.time()
        self.last_activity = self.created_at
        self._exit_code: Optional[int] = None


class TerminalAdapter:
    """Manages persistent shell sessions (PowerShell / cmd) via subprocess pipes."""

    def __init__(self) -> None:
        self._sessions: dict[str, TerminalSession] = {}
        self._lock = threading.Lock()
        self._max_sessions: int = 8
        self._idle_timeout: float = 1800.0
        self._counter: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        op = operation.split(".", 1)[-1] if "." in operation else operation
        handler = {
            "create": self._op_create,
            "list": self._op_list,
            "capture": self._op_capture,
            "send": self._op_send,
            "send_key": self._op_send_key,
            "destroy": self._op_destroy,
        }.get(op)
        if handler is None:
            return {"success": False, "error": f"unknown terminal operation: {operation}"}
        try:
            return handler(params)
        except Exception as exc:
            logger.error("terminal.%s failed: %s", op, exc, exc_info=True)
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

    def shutdown(self) -> None:
        """Destroy all sessions. Called during daemon shutdown."""
        with self._lock:
            names = list(self._sessions.keys())
        for name in names:
            self._destroy_session(name)
        logger.info("terminal adapter shutdown — all sessions destroyed")

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _op_create(self, params: dict[str, Any]) -> dict[str, Any]:
        shell_type = params.get("shell", "powershell")
        if shell_type not in ("cmd", "powershell"):
            return {"success": False, "error": f"unsupported shell type: {shell_type}"}

        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                return {"success": False, "error": f"session limit reached ({self._max_sessions})"}
            prefix = "ps" if shell_type == "powershell" else "cmd"
            name = params.get("name") or f"{prefix}_{self._counter}"
            self._counter += 1
            if name in self._sessions:
                return {"success": False, "error": f"session '{name}' already exists"}

        if shell_type == "powershell":
            cmd = ["powershell", "-NoLogo", "-NoProfile"]
        else:
            cmd = ["cmd", "/Q"]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                **no_window_kwargs(),
            )
        except Exception as exc:
            return {"success": False, "error": f"failed to spawn {shell_type}: {exc}"}

        # Build session — reader thread starts after construction
        session = TerminalSession(
            name=name,
            process=proc,
            reader_thread=threading.Thread(target=lambda: None, daemon=True),
            shell_type=shell_type,
        )
        reader = threading.Thread(
            target=self._reader_loop,
            args=(session,),
            daemon=True,
            name=f"term-reader-{name}",
        )
        session.reader_thread = reader
        reader.start()

        with self._lock:
            self._sessions[name] = session

        logger.info("terminal session created: %s (%s)", name, shell_type)
        return {"success": True, "session_name": name, "shell_type": shell_type}

    def _op_list(self, params: dict[str, Any]) -> dict[str, Any]:
        self._cleanup_idle()
        with self._lock:
            sessions = []
            for s in self._sessions.values():
                sessions.append({
                    "name": s.name,
                    "shell_type": s.shell_type,
                    "alive": s.process.poll() is None,
                    "lines": len(s.output_buffer),
                })
        return {"success": True, "sessions": sessions}

    def _op_capture(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        session = self._get_session(name)
        if session is None:
            return {"success": False, "error": f"session '{name}' not found"}

        num_lines = params.get("lines", 100)
        session.last_activity = time.time()

        with session.lock:
            buf = list(session.output_buffer)
            tail = buf[-num_lines:] if len(buf) > num_lines else buf

        logger.debug("terminal.capture %s: %d lines", name, len(tail))
        return {
            "success": True,
            "output": "\n".join(tail),
            "alive": session.process.poll() is None,
            "exit_code": session._exit_code,
        }

    def _op_send(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        text = params.get("text", "")
        session = self._get_session(name)
        if session is None:
            return {"success": False, "error": f"session '{name}' not found"}
        if session.process.poll() is not None:
            return {"success": False, "error": f"session '{name}' is dead"}

        try:
            session.process.stdin.write(text.encode("utf-8") + b"\r\n")
            session.process.stdin.flush()
        except Exception as exc:
            return {"success": False, "error": f"stdin write failed: {exc}"}

        session.last_activity = time.time()
        return {"success": True}

    def _op_send_key(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        key = params.get("key", "")
        session = self._get_session(name)
        if session is None:
            return {"success": False, "error": f"session '{name}' not found"}
        if session.process.poll() is not None:
            return {"success": False, "error": f"session '{name}' is dead"}

        raw = _KEY_MAP.get(key)
        if raw is not None:
            try:
                session.process.stdin.write(raw)
                session.process.stdin.flush()
            except Exception as exc:
                return {"success": False, "error": f"stdin write failed: {exc}"}

        # Unmapped keys: silently succeed (v1 limitation)
        return {"success": True}

    def _op_destroy(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        session = self._get_session(name)
        if session is None:
            return {"success": False, "error": f"session '{name}' not found"}
        self._destroy_session(name)
        return {"success": True}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_session(self, name: str) -> Optional[TerminalSession]:
        with self._lock:
            return self._sessions.get(name)

    def _destroy_session(self, name: str) -> None:
        with self._lock:
            session = self._sessions.pop(name, None)
        if session is None:
            return
        try:
            session.process.terminate()
            session.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            session.process.kill()
            session.process.wait(timeout=2)
        except Exception as exc:
            logger.debug("destroy session %s cleanup error: %s", name, exc)
        logger.info("terminal session destroyed: %s", name)

    def _reader_loop(self, session: TerminalSession) -> None:
        """Read stdout line-by-line into the ring buffer. Runs in daemon thread."""
        try:
            for line in iter(session.process.stdout.readline, b""):
                decoded = line.decode("utf-8", errors="replace")
                with session.lock:
                    session.output_buffer.append(decoded.rstrip("\n").rstrip("\r"))
        except Exception as exc:
            logger.debug("reader loop for %s ended: %s", session.name, exc)
        session._exit_code = session.process.wait()

    def _cleanup_idle(self) -> None:
        """Remove dead processes and terminate idle sessions."""
        now = time.time()
        to_remove: list[str] = []
        with self._lock:
            for name, session in self._sessions.items():
                alive = session.process.poll() is None
                if not alive:
                    to_remove.append(name)
                elif now - session.last_activity > self._idle_timeout:
                    to_remove.append(name)
        for name in to_remove:
            self._destroy_session(name)
