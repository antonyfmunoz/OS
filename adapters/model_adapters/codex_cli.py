"""
codex_cli — Codex CLI adapter for EOS.

Wraps `codex exec --json` for non-interactive agent execution.
Parses JSONL output stream for agent responses.

Auth: ChatGPT login (`codex login`) or OPENAI_API_KEY / CODEX_API_KEY env var.
Default model: gpt-5.5 (via ChatGPT subscription).

Usage:
    from adapters.model_adapters.codex_cli import query_codex_sync

    result = query_codex_sync("Review this code for bugs")
    if result:
        print(result.output)
"""

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: int = 120


def _resolve_timeout() -> float:
    raw = os.environ.get("CODEX_TIMEOUT_SECONDS")
    if not raw:
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        return float(int(raw))
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


_ERROR_SIGNATURES: tuple[str, ...] = (
    "invalid_request_error",
    "rate_limit",
    "authentication",
    "insufficient_quota",
    "billing",
)


def _is_error_leak(content: str) -> bool:
    lowered = content.lower()
    return any(sig in lowered for sig in _ERROR_SIGNATURES)


@dataclass
class CodexResult:
    output: str
    thread_id: str
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    provider: str = "codex"
    model: str = ""


def _track_result(success: bool) -> None:
    try:
        from state.providers.provider_state import get_system_state
        state = get_system_state()
        if success:
            state.record_provider_success("codex")
        else:
            state.record_provider_failure("codex")
    except Exception:
        pass


def is_available() -> bool:
    return shutil.which("codex") is not None


def query_codex_sync(
    prompt: str,
    model: str | None = None,
    sandbox: str = "read-only",
    cwd: str | None = None,
    timeout: float | None = None,
) -> CodexResult | None:
    """
    Run a Codex agent non-interactively via `codex exec`.

    Args:
        prompt: The task prompt.
        model: Override model (e.g. "o4-mini"). None = Codex default.
        sandbox: Sandbox mode — read-only | workspace-write | danger-full-access.
        cwd: Working directory for the agent.
        timeout: Max seconds. Default from CODEX_TIMEOUT_SECONDS or 120.

    Returns:
        CodexResult on success, None on error.
    """
    if timeout is None:
        timeout = _resolve_timeout()

    if not is_available():
        logger.warning("[codex] CLI not found on PATH")
        return None

    try:
        from state.providers.provider_state import get_system_state
        if not get_system_state().allow_execution():
            logger.info("[codex] blocked by backpressure gate")
            return None
    except Exception:
        pass

    cmd = [
        "codex", "exec",
        "--json",
        "--ephemeral",
        "--sandbox", sandbox,
        "--skip-git-repo-check",
    ]
    if model:
        cmd.extend(["-m", model])
    cmd.append(prompt)

    start_ms = time.monotonic_ns() // 1_000_000

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
        )
    except subprocess.TimeoutExpired:
        logger.warning("[codex] timed out after %ss", timeout)
        _track_result(False)
        return None
    except Exception as e:
        logger.warning("[codex] subprocess error: %s", e)
        _track_result(False)
        return None

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    output_parts: list[str] = []
    thread_id = ""
    model_used = ""
    input_tokens = 0
    output_tokens = 0

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        if event_type == "thread.started":
            thread_id = event.get("thread_id", "")

        elif event_type == "item.completed":
            item = event.get("item", {})
            text = item.get("text", "")
            if text:
                output_parts.append(text)

        elif event_type == "turn.completed":
            usage = event.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

        elif event_type == "error":
            logger.warning("[codex] error event: %s", event.get("message", "")[:200])

        elif event_type == "turn.failed":
            error = event.get("error", {})
            logger.warning("[codex] turn failed: %s", error.get("message", "")[:200])

    output = "\n".join(output_parts).strip()

    if not output:
        logger.warning("[codex] empty response")
        _track_result(False)
        return None

    if _is_error_leak(output):
        logger.warning("[codex] error leak detected: %s", output[:120])
        _track_result(False)
        return None

    _track_result(True)
    return CodexResult(
        output=output,
        thread_id=thread_id,
        latency_ms=elapsed_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider="codex",
        model=model_used,
    )


def review_codex_sync(
    base_branch: str | None = None,
    uncommitted: bool = False,
    cwd: str | None = None,
    timeout: float | None = None,
) -> CodexResult | None:
    """Run Codex code review non-interactively."""
    if timeout is None:
        timeout = _resolve_timeout()

    if not is_available():
        logger.warning("[codex] CLI not found on PATH")
        return None

    cmd = ["codex", "review"]
    if uncommitted:
        cmd.append("--uncommitted")
    if base_branch:
        cmd.extend(["--base", base_branch])

    start_ms = time.monotonic_ns() // 1_000_000

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
        )
    except subprocess.TimeoutExpired:
        logger.warning("[codex] review timed out after %ss", timeout)
        return None
    except Exception as e:
        logger.warning("[codex] review subprocess error: %s", e)
        return None

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms
    output = result.stdout.strip()

    if not output:
        return None

    return CodexResult(
        output=output,
        thread_id="",
        latency_ms=elapsed_ms,
        provider="codex",
    )
