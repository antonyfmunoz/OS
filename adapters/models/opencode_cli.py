"""
opencode_cli — OpenCode CLI adapter for EOS.

Wraps `opencode run` for non-interactive agent execution.
OpenCode supports 75+ LLM providers (Anthropic, OpenAI, Gemini, etc.).

Auth: `opencode auth login` or provider-specific env vars.
Configure: opencode.json in project root or ~/.config/opencode/opencode.json.

Usage:
    from adapters.models.opencode_cli import query_opencode_sync

    result = query_opencode_sync("Explain this codebase")
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
    raw = os.environ.get("OPENCODE_TIMEOUT_SECONDS")
    if not raw:
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        return float(int(raw))
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


_ERROR_SIGNATURES: tuple[str, ...] = (
    "authentication",
    "rate limit",
    "api key",
    "unauthorized",
    "billing",
    "no provider",
    "not authenticated",
)


def _is_error_leak(content: str) -> bool:
    lowered = content.lower()
    return any(sig in lowered for sig in _ERROR_SIGNATURES)


@dataclass
class OpenCodeResult:
    output: str
    latency_ms: int
    provider: str = "opencode"
    model: str = ""


def _track_result(success: bool) -> None:
    try:
        from state.providers.provider_state import get_system_state

        state = get_system_state()
        if success:
            state.record_provider_success("opencode")
        else:
            state.record_provider_failure("opencode")
    except Exception:
        pass


def is_available() -> bool:
    return shutil.which("opencode") is not None


def query_opencode_sync(
    prompt: str,
    model: str | None = None,
    output_format: str = "default",
    cwd: str | None = None,
    timeout: float | None = None,
    skip_permissions: bool = False,
) -> OpenCodeResult | None:
    """
    Run OpenCode agent non-interactively via `opencode run`.

    Args:
        prompt: The task prompt.
        model: Override model (e.g. "anthropic/claude-sonnet-4-5"). None = default.
        output_format: "default" or "json".
        cwd: Working directory for the agent.
        timeout: Max seconds. Default from OPENCODE_TIMEOUT_SECONDS or 120.
        skip_permissions: Auto-approve all tool use (dangerous).

    Returns:
        OpenCodeResult on success, None on error.
    """
    if timeout is None:
        timeout = _resolve_timeout()

    if not is_available():
        logger.warning("[opencode] CLI not found on PATH")
        return None

    try:
        from state.providers.provider_state import get_system_state

        if not get_system_state().allow_execution():
            logger.info("[opencode] blocked by backpressure gate")
            return None
    except Exception:
        pass

    cmd = ["opencode", "run"]
    if model:
        cmd.extend(["--model", model])
    if output_format == "json":
        cmd.extend(["--format", "json"])
    if skip_permissions:
        cmd.append("--dangerously-skip-permissions")
    if cwd:
        cmd.extend(["--dir", cwd])
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
        logger.warning("[opencode] timed out after %ss", timeout)
        _track_result(False)
        return None
    except Exception as e:
        logger.warning("[opencode] subprocess error: %s", e)
        _track_result(False)
        return None

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    output = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0 and not output:
        logger.warning("[opencode] exit code %d: %s", result.returncode, stderr[:200])
        _track_result(False)
        return None

    if output_format == "json" and output:
        try:
            parsed = json.loads(output)
            output = parsed.get("response", parsed.get("text", output))
        except json.JSONDecodeError:
            pass

    if not output:
        logger.warning("[opencode] empty response. stderr: %s", stderr[:200])
        _track_result(False)
        return None

    if _is_error_leak(output) or _is_error_leak(stderr):
        logger.warning("[opencode] error leak detected: %s", (output or stderr)[:120])
        _track_result(False)
        return None

    _track_result(True)
    return OpenCodeResult(
        output=output,
        latency_ms=elapsed_ms,
        provider="opencode",
    )
