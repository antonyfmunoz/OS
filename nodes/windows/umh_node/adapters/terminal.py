"""Terminal adapter — persistent shell sessions via subprocess pipes."""

from __future__ import annotations

import collections
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Optional

if sys.platform == "win32":
    from nodes.windows.umh_node.subprocess_utils import no_window_kwargs

logger = logging.getLogger(__name__)

# Control-key byte mapping (v1 — extend as needed)
_KEY_MAP: dict[str, bytes] = {
    "C-c": b"\x03",
    "C-d": b"\x04",
    "C-z": b"\x1a",
    "C-l": b"\x0c",
}

# Shell registry: id → (display label, command builder, auto-detect function)
_SHELL_DEFS: dict[str, dict[str, Any]] = {
    "powershell": {
        "label": "PowerShell",
        "cmd": ["powershell", "-NoLogo", "-NoProfile"],
        "detect": lambda: shutil.which("powershell") is not None,
        "os": "windows",
        "prefix": "ps",
    },
    "pwsh": {
        "label": "PowerShell Core",
        "cmd": ["pwsh", "-NoLogo", "-NoProfile"],
        "detect": lambda: shutil.which("pwsh") is not None,
        "os": "windows",
        "prefix": "pwsh",
    },
    "cmd": {
        "label": "cmd",
        "cmd": ["cmd", "/Q"],
        "detect": lambda: sys.platform == "win32",
        "os": "windows",
        "prefix": "cmd",
    },
    "git-bash": {
        "label": "Git Bash",
        "cmd": lambda: [_find_git_bash(), "--login", "-i"] if _find_git_bash() else None,
        "detect": lambda: _find_git_bash() is not None,
        "os": "windows",
        "prefix": "gb",
    },
    "wsl": {
        "label": "WSL (Ubuntu)",
        "cmd": ["wsl", "--exec", "bash", "--login"],
        "detect": lambda: shutil.which("wsl") is not None,
        "os": "windows",
        "prefix": "wsl",
    },
    "bash": {
        "label": "Bash",
        "cmd": ["bash", "--login"],
        "detect": lambda: shutil.which("bash") is not None and sys.platform != "win32",
        "os": "linux",
        "prefix": "bash",
    },
    "zsh": {
        "label": "Zsh",
        "cmd": ["zsh", "--login"],
        "detect": lambda: shutil.which("zsh") is not None and sys.platform != "win32",
        "os": "linux",
        "prefix": "zsh",
    },
    "sh": {
        "label": "sh",
        "cmd": ["sh"],
        "detect": lambda: shutil.which("sh") is not None and sys.platform != "win32",
        "os": "posix",
        "prefix": "sh",
    },
    "python": {
        "label": "Python REPL",
        "cmd": ["python3", "-u"] if sys.platform != "win32" else ["python", "-u"],
        "detect": lambda: shutil.which("python3" if sys.platform != "win32" else "python") is not None,
        "os": "any",
        "prefix": "py",
    },
}


def _find_git_bash() -> Optional[str]:
    """Locate git-bash.exe on Windows."""
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Git", "bin", "bash.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "bin", "bash.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return shutil.which("bash")


def discover_available_shells() -> list[dict[str, str]]:
    """Return list of shells available on this node."""
    available = []
    for shell_id, defn in _SHELL_DEFS.items():
        try:
            if defn["detect"]():
                available.append({"id": shell_id, "label": defn["label"], "os": defn["os"]})
        except Exception:
            pass
    return available


_MUX_DEFS: dict[str, dict[str, Any]] = {
    "tmux": {
        "label": "tmux",
        "detect_native": lambda: shutil.which("tmux") is not None,
        "detect_wsl": lambda: sys.platform == "win32" and shutil.which("wsl") is not None and _wsl_has("tmux"),
    },
    "screen": {
        "label": "GNU Screen",
        "detect_native": lambda: shutil.which("screen") is not None,
        "detect_wsl": lambda: sys.platform == "win32" and shutil.which("wsl") is not None and _wsl_has("screen"),
    },
}


def _wsl_has(binary: str) -> bool:
    """Check if a binary exists inside the default WSL distro."""
    try:
        r = subprocess.run(
            ["wsl", "--exec", "which", binary],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and r.stdout.strip() != ""
    except Exception:
        return False


def discover_available_multiplexers() -> list[dict[str, str]]:
    """Return list of terminal multiplexers available on this node."""
    available = []
    for mux_id, defn in _MUX_DEFS.items():
        try:
            if defn["detect_native"]():
                available.append({"id": mux_id, "label": defn["label"], "via": "native"})
            elif defn["detect_wsl"]():
                available.append({"id": mux_id, "label": defn["label"], "via": "wsl"})
        except Exception:
            pass
    return available


def discover_capabilities() -> dict[str, Any]:
    """Full terminal capability report for this node."""
    return {
        "platform": sys.platform,
        "shells": discover_available_shells(),
        "multiplexers": discover_available_multiplexers(),
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
    """Manages persistent shell sessions across all available shell types."""

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
            "shells": self._op_shells,
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
        defn = _SHELL_DEFS.get(shell_type)
        if defn is None:
            return {"success": False, "error": f"unknown shell type: {shell_type}. available: {list(_SHELL_DEFS.keys())}"}
        if not defn["detect"]():
            return {"success": False, "error": f"shell '{shell_type}' not available on this node"}

        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                return {"success": False, "error": f"session limit reached ({self._max_sessions})"}
            prefix = defn["prefix"]
            name = params.get("name") or f"{prefix}_{self._counter}"
            self._counter += 1
            if name in self._sessions:
                return {"success": False, "error": f"session '{name}' already exists"}

        cmd_spec = defn["cmd"]
        cmd = cmd_spec() if callable(cmd_spec) else list(cmd_spec)
        if cmd is None:
            return {"success": False, "error": f"shell '{shell_type}' command not found"}

        popen_kwargs: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
        }
        if sys.platform == "win32":
            popen_kwargs.update(no_window_kwargs())

        try:
            proc = subprocess.Popen(cmd, **popen_kwargs)
        except Exception as exc:
            return {"success": False, "error": f"failed to spawn {shell_type}: {exc}"}

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

    def _op_shells(self, params: dict[str, Any]) -> dict[str, Any]:
        caps = discover_capabilities()
        return {"success": True, "shells": caps["shells"], "multiplexers": caps["multiplexers"], "platform": caps["platform"]}

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
