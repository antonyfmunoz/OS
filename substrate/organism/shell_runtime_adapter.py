"""Shell runtime adapter — safe subprocess execution surface.

Runs sandboxed shell commands with blocked-command filtering, timeout
enforcement, allowed-path checks, and output capture.

Phase 13.2. Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import time
from typing import Any

from substrate.organism.runtime_adapter import (
    RuntimeAdapter,
    RuntimeInjectRequest,
    RuntimeStartRequest,
    RuntimeStartResult,
)
from substrate.organism.runtime_session import (
    RuntimeEvent,
    RuntimeEventType,
    persist_event,
)

logger = logging.getLogger(__name__)

BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+-R\s+777\b", re.IGNORECASE),
    re.compile(r"\bchown\s+-R\b", re.IGNORECASE),
    re.compile(r"\bcurl\b.*\|\s*sh\b", re.IGNORECASE),
    re.compile(r"\bwget\b.*\|\s*sh\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+publish\b", re.IGNORECASE),
    re.compile(r"\bdeploy\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+restart\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+stop\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+rm\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\b", re.IGNORECASE),
    re.compile(r"\bgh\s+pr\s+merge\b", re.IGNORECASE),
    re.compile(r"\.env\b", re.IGNORECASE),
    re.compile(r"\bsecrets?\b", re.IGNORECASE),
    re.compile(r"\bcredential", re.IGNORECASE),
    re.compile(r"\bdns\b", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+--force\b", re.IGNORECASE),
]

SAFE_PROOF_COMMANDS: set[str] = {
    "pwd",
    "ls",
    "git status --short",
    "git log --oneline -5",
    "git branch --show-current",
    "echo hello",
    "date",
    "whoami",
    "cat /etc/hostname",
}


def is_command_blocked(command: str) -> tuple[bool, str]:
    for pat in BLOCKED_PATTERNS:
        if pat.search(command):
            return True, f"blocked by pattern: {pat.pattern}"
    return False, ""


_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"postgres://[^\s]+:[^\s]+@"),
    re.compile(r"(token|password|secret|api.key)\s*[:=]\s*\S+", re.IGNORECASE),
]

_STRIPPED_ENV_PATTERNS: list[str] = [
    "ANTHROPIC_", "GROQ_", "GEMINI_", "OPENAI_", "GITHUB_TOKEN",
    "NEON_", "_API_KEY", "_TOKEN", "_SECRET", "CLERK_",
    "UMH_OPERATOR_TOKEN",
]


def _redact_secrets(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def _sandbox_env() -> dict[str, str]:
    safe_keys = {"PATH", "HOME", "TERM", "LANG", "LC_ALL", "USER", "SHELL", "TMPDIR"}
    env: dict[str, str] = {}
    for k, v in os.environ.items():
        if k in safe_keys:
            env[k] = v
            continue
        skip = False
        for pat in _STRIPPED_ENV_PATTERNS:
            if pat in k.upper():
                skip = True
                break
        if not skip:
            env[k] = v
    env["TERM"] = "dumb"
    return env


def is_path_allowed(cwd: str, allowed_paths: list[str], blocked_paths: list[str], sandbox_required: bool = True) -> tuple[bool, str]:
    real_cwd = os.path.realpath(os.path.abspath(cwd))
    if ".." in cwd.split(os.sep):
        return False, f"cwd contains '..' components: {cwd}"
    for bp in blocked_paths:
        real_bp = os.path.realpath(os.path.abspath(bp))
        if real_cwd == real_bp or real_cwd.startswith(real_bp + os.sep):
            return False, f"cwd {real_cwd} is inside blocked path {real_bp}"
    if allowed_paths:
        for ap in allowed_paths:
            real_ap = os.path.realpath(os.path.abspath(ap))
            if real_cwd == real_ap or real_cwd.startswith(real_ap + os.sep):
                return True, ""
        return False, f"cwd {real_cwd} not inside any allowed path"
    if sandbox_required:
        return False, "sandbox_required=True but no allowed_paths specified"
    return True, ""


class ShellRuntimeAdapter(RuntimeAdapter):
    adapter_id = "shell-adapter-v1"
    runtime_type = "shell"

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._outputs: dict[str, str] = {}
        self._start_times: dict[str, float] = {}

    def is_available(self) -> bool:
        return True

    def availability_detail(self) -> dict[str, Any]:
        return {
            "available": True,
            "adapter_id": self.adapter_id,
            "runtime_type": self.runtime_type,
            "blocked_patterns_count": len(BLOCKED_PATTERNS),
        }

    def prepare(self, request: RuntimeStartRequest) -> dict[str, Any]:
        blocked, reason = is_command_blocked(request.command)
        if blocked:
            return {"ready": False, "reason": reason, "blocked": True}
        if request.sandbox_required and not request.cwd:
            return {"ready": False, "reason": "sandbox cwd required but not provided"}
        if request.cwd:
            path_ok, path_reason = is_path_allowed(
                request.cwd, request.allowed_paths, request.blocked_paths,
                sandbox_required=request.sandbox_required,
            )
            if not path_ok:
                return {"ready": False, "reason": path_reason}
            if not os.path.isdir(request.cwd):
                return {"ready": False, "reason": f"cwd does not exist: {request.cwd}"}
        return {"ready": True, "command": request.command, "cwd": request.cwd}

    def start(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        prep = self.prepare(request)
        if not prep.get("ready"):
            return RuntimeStartResult(
                session_id=request.session_id,
                started=False,
                error=prep.get("reason", "preparation failed"),
            )

        persist_event(RuntimeEvent.create(
            session_id=request.session_id,
            event_type=RuntimeEventType.RUNTIME_STARTING,
            message=f"starting shell: {_redact_secrets(request.command[:120])}",
        ))

        try:
            proc = subprocess.Popen(
                request.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=request.cwd or None,
                text=True,
                env=_sandbox_env(),
                start_new_session=True,
            )
            self._processes[request.session_id] = proc
            self._outputs[request.session_id] = ""
            self._start_times[request.session_id] = time.time()

            persist_event(RuntimeEvent.create(
                session_id=request.session_id,
                event_type=RuntimeEventType.RUNTIME_STARTED,
                message=f"pid={proc.pid}",
            ))

            try:
                stdout, _ = proc.communicate(timeout=request.timeout_seconds)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                stdout, _ = proc.communicate(timeout=5)
                stdout = (stdout or "") + "\n[TIMEOUT — process killed]"

            output = stdout or ""
            if len(output) > request.max_output_bytes:
                output = output[: request.max_output_bytes] + "\n[OUTPUT TRUNCATED]"

            self._outputs[request.session_id] = output

            seq = 0
            for line in output.split("\n"):
                if line.strip():
                    seq += 1
                    persist_event(RuntimeEvent.create(
                        session_id=request.session_id,
                        event_type=RuntimeEventType.STDOUT,
                        message=_redact_secrets(line),
                        stream="stdout",
                        sequence=seq,
                    ))

            event_type = RuntimeEventType.COMPLETED if proc.returncode == 0 else RuntimeEventType.FAILED
            persist_event(RuntimeEvent.create(
                session_id=request.session_id,
                event_type=event_type,
                message=f"exit_code={proc.returncode}",
            ))

            return RuntimeStartResult(
                session_id=request.session_id,
                started=True,
                pid=proc.pid,
                status="completed" if proc.returncode == 0 else "failed",
                output=output,
                metadata={"exit_code": proc.returncode},
            )
        except Exception as exc:
            logger.exception("shell adapter start failed for session %s", request.session_id)
            sanitized = f"shell start failed: {type(exc).__name__}"
            persist_event(RuntimeEvent.create(
                session_id=request.session_id,
                event_type=RuntimeEventType.FAILED,
                message=sanitized,
                severity="error",
            ))
            return RuntimeStartResult(
                session_id=request.session_id,
                started=False,
                error=sanitized,
            )

    def inject(self, request: RuntimeInjectRequest) -> dict[str, Any]:
        proc = self._processes.get(request.session_id)
        if not proc or proc.poll() is not None:
            return {"injected": False, "reason": "process not running"}
        if proc.stdin:
            try:
                msg = request.message
                if request.requires_enter and not msg.endswith("\n"):
                    msg += "\n"
                proc.stdin.write(msg)
                proc.stdin.flush()
                persist_event(RuntimeEvent.create(
                    session_id=request.session_id,
                    event_type=RuntimeEventType.PROMPT_INJECTED,
                    message=f"injected {len(msg)} bytes",
                ))
                return {"injected": True}
            except Exception as exc:
                return {"injected": False, "reason": str(exc)}
        return {"injected": False, "reason": "no stdin pipe"}

    def stop(self, session_id: str, reason: str = "") -> dict[str, Any]:
        proc = self._processes.get(session_id)
        if not proc:
            return {"stopped": False, "reason": "no process found"}
        if proc.poll() is not None:
            return {"stopped": True, "reason": "already terminated", "exit_code": proc.returncode}

        persist_event(RuntimeEvent.create(
            session_id=session_id,
            event_type=RuntimeEventType.STOP_REQUESTED,
            message=reason or "operator requested stop",
        ))

        try:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                proc.wait(timeout=3)
        except Exception as exc:
            logger.exception("stop failed for session %s", session_id)
            return {"stopped": False, "reason": f"stop failed: {type(exc).__name__}"}

        persist_event(RuntimeEvent.create(
            session_id=session_id,
            event_type=RuntimeEventType.STOPPED,
            message=f"exit_code={proc.returncode}, reason={reason}",
        ))
        return {"stopped": True, "exit_code": proc.returncode, "reason": reason}

    def status(self, session_id: str) -> dict[str, Any]:
        proc = self._processes.get(session_id)
        if not proc:
            return {"status": "unknown", "reason": "no process tracked"}
        poll = proc.poll()
        if poll is None:
            elapsed = time.time() - self._start_times.get(session_id, 0)
            return {"status": "running", "pid": proc.pid, "elapsed_seconds": round(elapsed, 1)}
        return {"status": "terminated", "exit_code": poll, "pid": proc.pid}

    def collect_output(self, session_id: str) -> str:
        return self._outputs.get(session_id, "")

    def collect_artifacts(self, session_id: str) -> list[str]:
        return []

    def validate(self, session_id: str) -> dict[str, Any]:
        output = self._outputs.get(session_id, "")
        proc = self._processes.get(session_id)
        exit_code = proc.returncode if proc else None
        return {
            "valid": exit_code == 0 if exit_code is not None else False,
            "exit_code": exit_code,
            "output_bytes": len(output),
            "has_output": bool(output.strip()),
        }

    def cleanup(self, session_id: str) -> dict[str, Any]:
        proc = self._processes.pop(session_id, None)
        self._outputs.pop(session_id, None)
        self._start_times.pop(session_id, None)
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3)
            return {"cleaned": True, "killed": True}
        return {"cleaned": True, "killed": False}
