"""Codex production adapter for governed model execution."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelExecutorReadiness,
    ModelInvocation,
    ModelTerminalResult,
    ModelWorkPacketInput,
)

_DEFAULT_MODEL = "gpt-5.5"
_ERROR_SIGNATURES = (
    "auth",
    "login",
    "permission denied",
    "rate limit",
    "quota",
    "billing",
    "invalid_request",
)


def _resolve_codex() -> str:
    return shutil.which("codex") or ""


def _sanitize(text: str) -> str:
    redacted = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if "token" in lowered or "api_key" in lowered or "authorization" in lowered:
            redacted.append("[redacted credential-bearing line]")
        else:
            redacted.append(line)
    return "\n".join(redacted)


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


def _parse_jsonl(stdout: str) -> tuple[str, dict[str, int], str]:
    parts: list[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = ""
    for line in (stdout or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        typ = str(event.get("type", ""))
        if typ == "item.completed":
            item = event.get("item", {}) or {}
            text = item.get("text", "")
            if text:
                parts.append(str(text))
        elif typ == "turn.completed":
            raw = event.get("usage", {}) or {}
            usage["input_tokens"] = int(raw.get("input_tokens", 0) or 0)
            usage["output_tokens"] = int(raw.get("output_tokens", 0) or 0)
            model = str(event.get("model") or model)
        elif typ == "agent_message":
            msg = event.get("message", {}) or {}
            text = msg.get("content", "")
            if isinstance(text, str) and text:
                parts.append(text)
    return "\n".join(parts).strip(), usage, model


class CodexModelExecutor:
    def __init__(self, *, model: str | None = None, sandbox: str = "workspace-write") -> None:
        self.model = model or os.environ.get("UMH_CODEX_MODEL", _DEFAULT_MODEL)
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

    def readiness(self) -> ModelExecutorReadiness:
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
        parsed, usage, model_seen = _parse_jsonl(getattr(proc, "stdout", "") or "")
        stdout = parsed or _sanitize(getattr(proc, "stdout", "") or "")
        stderr = _sanitize(getattr(proc, "stderr", "") or "")
        returncode = getattr(proc, "returncode", None)
        terminal = ModelTerminalResult(
            ok=returncode == 0 and bool(parsed.strip()),
            status="succeeded" if returncode == 0 and bool(parsed.strip()) else "failed",
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
                model=model_seen or self.model,
                version=self.identity.version,
                adapter=type(self).__name__,
            ),
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
        try:
            proc = gated_subprocess_run(
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
            stderr = _sanitize(str(exc))
        duration = time.monotonic() - start
        if proc is None:
            return ModelTerminalResult(
                ok=False,
                status="failed",
                stderr=stderr if timed_out else "",
                timed_out=timed_out,
                duration_seconds=duration,
                retry_class="external_transient" if timed_out else "host_backpressure",
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )
        return self.collect_result(packet, proc, duration_seconds=duration)


__all__ = ["CodexModelExecutor"]
