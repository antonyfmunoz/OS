"""Codex production adapter for governed model execution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time

from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelExecutorReadiness,
    ModelInvocation,
    ModelTerminalResult,
    ModelWorkPacketInput,
)
from substrate.execution.attempts.model_executor_selection import selected_codex_model
from substrate.execution.cpu_gate import gated_popen, gated_subprocess_run

_ERROR_SIGNATURES = (
    "auth",
    "login",
    "permission denied",
    "rate limit",
    "quota",
    "billing",
    "invalid_request",
)
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


def _resolve_codex() -> str:
    return shutil.which("codex") or ""


def _sanitize(text: str) -> str:
    redacted = []
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
        else:
            clean = line
            for pattern in _SECRET_PATTERNS:
                clean = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + "[redacted]", clean)
            redacted.append(clean)
    return "\n".join(redacted)


def _object_field(event: dict, key: str, line_no: int, errors: list[str]) -> dict:
    raw = event.get(key, {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        errors.append(f"line {line_no}: {key} is not an object")
        return {}
    return raw


def _classify_failure(*, timed_out: bool, returncode: int | None, stderr: str, stdout: str) -> str:
    if timed_out:
        return "external_transient"
    joined = f"{stderr}\n{stdout}".lower()
    if any(sig in joined for sig in _ERROR_SIGNATURES):
        return "owner_auth_or_provider"
    if returncode in (130, -2, -15):
        return "cancelled"
    if returncode not in (None, 0):
        return "adapter_or_worker"
    return "malformed_output"


def _argv_digest(argv: list[str]) -> str:
    payload = json.dumps(argv, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _explicit_model_argument(argv: list[str], expected_model: str) -> bool:
    for i, arg in enumerate(argv):
        if arg in ("-m", "--model") and i + 1 < len(argv) and argv[i + 1] == expected_model:
            return True
        if arg.startswith("--model=") and arg.split("=", 1)[1] == expected_model:
            return True
    return False


def _decode_timeout_stream(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _taskkill_tree(pid: int, *, force: bool) -> subprocess.CompletedProcess[str]:
    cmd = ["taskkill", "/PID", str(pid), "/T"]
    if force:
        cmd.append("/F")
    result = gated_subprocess_run(
        cmd,
        caller="codex_executor_timeout_cleanup",
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result or subprocess.CompletedProcess(
        cmd,
        127,
        "",
        "cleanup command blocked by CPU gate or unavailable",
    )


def _run_codex_process_tree(
    cmd: list[str],
    *,
    caller: str,
    timeout: float,
    **kwargs: object,
) -> subprocess.CompletedProcess[str] | None:
    """Run Codex with an owned timeout.

    On Windows, a direct subprocess timeout can hit the ``codex.cmd`` wrapper
    while a descendant still owns inherited stdio handles.
    The caller then waits past its own deadline until an outer transport kills
    the whole tree. Wave 2 needs the model-executor timeout to win first, so the
    Windows path owns the process tree explicitly.
    """

    if os.name != "nt":
        return gated_subprocess_run(cmd, caller=caller, timeout=timeout, **kwargs)

    popen_kwargs = dict(kwargs)
    input_text = popen_kwargs.pop("input", None)
    if input_text is not None:
        popen_kwargs.setdefault("stdin", subprocess.PIPE)
    if popen_kwargs.pop("capture_output", False):
        popen_kwargs.setdefault("stdout", subprocess.PIPE)
        popen_kwargs.setdefault("stderr", subprocess.PIPE)
    popen_kwargs.setdefault("text", True)
    creationflags = int(popen_kwargs.pop("creationflags", 0) or 0)
    creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    popen_kwargs["creationflags"] = creationflags

    proc = gated_popen(cmd, caller=caller, **popen_kwargs)
    if proc is None:
        return None
    try:
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_timeout_stream(getattr(exc, "output", ""))
        stderr = _decode_timeout_stream(getattr(exc, "stderr", ""))
        cleanup_lines: list[str] = []
        try:
            graceful = _taskkill_tree(proc.pid, force=False)
            cleanup_lines.append(graceful.stdout or graceful.stderr or "")
        except Exception as cleanup_exc:  # noqa: BLE001
            cleanup_lines.append(f"graceful tree termination failed: {cleanup_exc}")
        try:
            more_out, more_err = proc.communicate(timeout=5)
            stdout = stdout or _decode_timeout_stream(more_out)
            stderr = "\n".join(x for x in [stderr, _decode_timeout_stream(more_err)] if x)
        except subprocess.TimeoutExpired:
            try:
                forced = _taskkill_tree(proc.pid, force=True)
                cleanup_lines.append(forced.stdout or forced.stderr or "")
            except Exception as cleanup_exc:  # noqa: BLE001
                cleanup_lines.append(f"forced tree termination failed: {cleanup_exc}")
            try:
                more_out, more_err = proc.communicate(timeout=5)
                stdout = stdout or _decode_timeout_stream(more_out)
                stderr = "\n".join(x for x in [stderr, _decode_timeout_stream(more_err)] if x)
            except subprocess.TimeoutExpired:
                cleanup_lines.append("process tree stdio did not close after forced termination")
        cleanup = "\n".join(line.strip() for line in cleanup_lines if line.strip())
        if cleanup:
            stderr = "\n".join(x for x in [stderr, cleanup] if x)
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout, output=stdout, stderr=stderr)


def _parse_jsonl(stdout: str) -> tuple[str, dict[str, int], str, list[str], dict[str, object]]:
    parts: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = ""
    errors: list[str] = []
    terminal_events = 0
    failed_events = 0
    error_events = 0
    terminal_status = "missing"
    usage_present = False
    event_types: list[str] = []
    for n, line in enumerate((stdout or "").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {n}: malformed json")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {n}: json event is not an object")
            continue
        typ = str(event.get("type", ""))
        event_types.append(typ)
        if typ == "item.completed":
            item = _object_field(event, "item", n, errors)
            text = item.get("text", "")
            if text and not isinstance(text, str):
                errors.append(f"line {n}: item.text is not a string")
                continue
            if text:
                parts.append(_sanitize(text))
        elif typ == "turn.completed":
            terminal_events += 1
            terminal_status = "completed"
            raw = _object_field(event, "usage", n, errors)
            usage_present = "usage" in event and isinstance(raw, dict)
            try:
                usage["input_tokens"] = int(raw.get("input_tokens", 0) or 0)
                usage["output_tokens"] = int(raw.get("output_tokens", 0) or 0)
            except (TypeError, ValueError):
                errors.append(f"line {n}: usage token counts are not integers")
            model = str(event.get("model") or model)
        elif typ == "turn.failed":
            failed_events += 1
            terminal_status = "failed"
            errors.append(f"line {n}: turn.failed event")
        elif typ == "error":
            error_events += 1
            terminal_status = "error"
            errors.append(f"line {n}: error event")
        elif typ == "agent_message":
            msg = _object_field(event, "message", n, errors)
            text = msg.get("content", "")
            if text and not isinstance(text, str):
                errors.append(f"line {n}: message.content is not a string")
                continue
            if text:
                parts.append(_sanitize(text))
    if terminal_events == 0:
        errors.append("missing terminal turn.completed event")
    elif terminal_events > 1:
        errors.append("multiple terminal turn.completed events")
    meta = {
        "event_types": event_types,
        "terminal_status": terminal_status,
        "usage_present": usage_present,
        "terminal_completed_count": terminal_events,
        "turn_failed_count": failed_events,
        "error_event_count": error_events,
        "trusted_model_resolved": model,
        "trusted_model_resolution_source": "turn.completed.model" if model else "",
        "model_resolution_observable": bool(model),
    }
    return "\n".join(parts).strip(), usage, model, errors, meta


class CodexModelExecutor:
    def __init__(self, *, model: str | None = None, sandbox: str = "danger-full-access") -> None:
        # UMH's outer bwrap sandbox is the authoritative write/credential/process
        # boundary. Codex's nested workspace-write sandbox makes .git read-only,
        # which prevents legitimate attempt commits (`.git/index.lock`).
        self.model = model or selected_codex_model()
        self.sandbox = sandbox
        self.identity = ModelExecutorIdentity(
            provider="codex",
            model=self.model,
            version=self._version(),
            adapter=type(self).__name__,
        )

    def _version(self) -> str:
        cli = _resolve_codex()
        if not cli:
            return ""
        try:
            r = gated_subprocess_run([cli, "--version"], caller="codex_executor", timeout=10)
        except Exception:
            return ""
        return (r.stdout or r.stderr or "").strip() if r else ""

    def readiness(self, *, env: dict[str, str] | None = None) -> ModelExecutorReadiness:
        cli = _resolve_codex()
        if not cli:
            return ModelExecutorReadiness(False, self.identity, "codex CLI not found", False)
        try:
            status = gated_subprocess_run(
                [cli, "login", "status"],
                caller="codex_executor_readiness",
                timeout=20,
                capture_output=True,
                text=True,
                env=env,
            )
        except Exception as exc:  # noqa: BLE001
            return ModelExecutorReadiness(False, self.identity, f"codex status failed: {exc}", False)
        if status is None:
            return ModelExecutorReadiness(False, self.identity, "blocked by CPU gate", False)
        out = f"{status.stdout or ''}\n{status.stderr or ''}".lower()
        ok = status.returncode == 0 and ("not logged" not in out and "login" not in out)
        return ModelExecutorReadiness(
            ok=ok,
            authenticated=ok,
            identity=self.identity,
            reason="" if ok else _sanitize(out)[-300:],
        )

    def build_invocation(self, packet: ModelWorkPacketInput) -> ModelInvocation:
        cli = _resolve_codex()
        if not cli:
            return ModelInvocation(argv=[])

        return ModelInvocation(
            argv=[
            cli,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox,
            "--cd",
            packet.worktree_path,
            "-m",
            self.model,
            "-",
            ],
            stdin=packet.prompt,
            cwd=packet.worktree_path,
        )

    def collect_result(
        self, packet: ModelWorkPacketInput, completed: object | None, *, duration_seconds: float
    ) -> ModelTerminalResult:
        if completed is None:
            return ModelTerminalResult(
                ok=False,
                status="failed",
                retry_class="host_backpressure",
                identity=self.identity,
                proof_binding=packet.proof_binding,
                duration_seconds=duration_seconds,
            )
        proc = completed
        invocation = self.build_invocation(packet)
        argv = invocation.argv
        parsed, usage, model_seen, parse_errors, parse_meta = _parse_jsonl(
            getattr(proc, "stdout", "") or ""
        )
        explicit_model_argument_present = _explicit_model_argument(argv, self.model)
        if not explicit_model_argument_present:
            parse_errors.append("missing exact explicit Codex model argument")
        if model_seen and model_seen != self.model:
            parse_errors.append(
                f"trusted terminal model identity mismatch: expected {self.model!r}, got {model_seen!r}"
            )
        stdout = parsed or _sanitize(getattr(proc, "stdout", "") or "")
        stderr = _sanitize(getattr(proc, "stderr", "") or "")
        if parse_errors:
            stderr = "\n".join([stderr, *parse_errors]).strip()
        returncode = getattr(proc, "returncode", None)
        usage_present = bool(parse_meta.get("usage_present"))
        if not usage_present:
            parse_errors.append("missing terminal usage metadata")
            stderr = "\n".join([stderr, "missing terminal usage metadata"]).strip()
        invocation_accepted = (
            returncode == 0
            and parse_meta.get("terminal_status") == "completed"
            and not parse_meta.get("turn_failed_count")
            and not parse_meta.get("error_event_count")
        )
        execution_identity = {
            "provider_requested": "codex",
            "provider_adapter": type(self).__name__,
            "model_requested": self.model,
            "model_selector_source": "explicit_argument",
            "executable_path": argv[0] if argv else "",
            "executable_version": self.identity.version,
            "invocation_argv_digest": _argv_digest(argv) if argv else "",
            "explicit_model_argument_present": explicit_model_argument_present,
            "user_config_ignored": "--ignore-user-config" in argv,
            "invocation_accepted": invocation_accepted,
            "terminal_status": str(parse_meta.get("terminal_status") or ""),
            "trusted_model_resolved": str(parse_meta.get("trusted_model_resolved") or ""),
            "trusted_model_resolution_source": str(
                parse_meta.get("trusted_model_resolution_source") or ""
            ),
            "model_resolution_observable": bool(parse_meta.get("model_resolution_observable")),
            "output_content_present": bool(parsed.strip()),
            "usage_present": usage_present,
            "credential_isolation_verified": False,
            "workspace_integrity_verified": False,
            "event_types": list(parse_meta.get("event_types") or []),
        }
        terminal = ModelTerminalResult(
            ok=returncode == 0 and bool(parsed.strip()) and not parse_errors,
            status="succeeded"
            if returncode == 0 and bool(parsed.strip()) and not parse_errors
            else "failed",
            stdout=stdout,
            stderr=stderr,
            summary=stdout[-500:],
            exit_code=returncode,
            duration_seconds=duration_seconds,
            retry_class="not_retryable",
            usage=usage,
            cost={"amount_usd": None, "status": "unavailable"},
            identity=ModelExecutorIdentity(
                provider="codex",
                model=self.model,
                version=self.identity.version,
                adapter=type(self).__name__,
            ),
            execution_identity=execution_identity,
            proof_binding=packet.proof_binding,
        )
        if not terminal.ok:
            terminal.retry_class = _classify_failure(
                timed_out=False, returncode=returncode, stderr=stderr, stdout=stdout
            )
        return terminal

    def invoke(self, packet: ModelWorkPacketInput, *, env: dict[str, str]) -> ModelTerminalResult:
        invocation = self.build_invocation(packet)
        if not invocation.argv:
            return ModelTerminalResult(
                ok=False,
                status="failed",
                summary="codex CLI not found",
                retry_class="owner_auth_or_provider",
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )
        start = time.monotonic()
        timed_out = False
        stdout = ""
        stderr = ""
        try:
            proc = _run_codex_process_tree(
                invocation.argv,
                caller="wave2_model_executor_codex",
                timeout=packet.timeout_seconds,
                cwd=invocation.cwd,
                env=env,
                input=invocation.stdin,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            proc = None
            timed_out = True
            stdout = _sanitize(_decode_timeout_stream(getattr(exc, "output", "")))
            stderr = _sanitize(_decode_timeout_stream(getattr(exc, "stderr", "")) or str(exc))
        duration = time.monotonic() - start
        if proc is None:
            return ModelTerminalResult(
                ok=False,
                status="failed",
                stdout=stdout if timed_out else "",
                stderr=stderr if timed_out else "",
                timed_out=timed_out,
                duration_seconds=duration,
                retry_class="external_transient" if timed_out else "host_backpressure",
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )
        return self.collect_result(packet, proc, duration_seconds=duration)


__all__ = ["CodexModelExecutor"]
