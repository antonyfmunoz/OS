"""
hermes_cli — Hermes Agent CLI adapter for EOS.

Wraps `hermes -z` for headless single-shot execution.
Hermes is model-agnostic (OpenRouter, OpenAI, Ollama, etc.).

Auth: ~/.hermes/.env or env vars (OPENROUTER_API_KEY, OPENAI_API_KEY, etc.).
Configure provider: `hermes model` (interactive) or `hermes config set`.

Usage:
    from adapters.models.hermes_cli import query_hermes_sync

    result = query_hermes_sync("Analyze this codebase structure")
    if result:
        print(result.output)
"""

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: int = 120


def _resolve_timeout() -> float:
    raw = os.environ.get("HERMES_TIMEOUT_SECONDS")
    if not raw:
        return float(DEFAULT_TIMEOUT_SECONDS)
    try:
        return float(int(raw))
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECONDS)


_ERROR_SIGNATURES: tuple[str, ...] = (
    "autherror",
    "no inference provider configured",
    "rate limit",
    "api key",
    "authentication",
    "billing",
    "quota",
)


def _is_error_leak(content: str) -> bool:
    lowered = content.lower()
    return any(sig in lowered for sig in _ERROR_SIGNATURES)


@dataclass
class HermesResult:
    output: str
    latency_ms: int
    provider: str = "hermes"
    model: str = ""


def _track_result(success: bool) -> None:
    try:
        from state.providers.provider_state import get_system_state
        state = get_system_state()
        if success:
            state.record_provider_success("hermes")
        else:
            state.record_provider_failure("hermes")
    except Exception:
        pass


def is_available() -> bool:
    return shutil.which("hermes") is not None


def is_configured() -> bool:
    """Check if Hermes has a provider configured (API key present)."""
    if not is_available():
        return False
    hermes_env = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(hermes_env):
        try:
            with open(hermes_env) as f:
                content = f.read()
            if "API_KEY" in content.upper():
                return True
        except Exception:
            pass
    for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "NOUS_API_KEY"):
        if os.environ.get(key):
            return True
    return False


def query_hermes_sync(
    prompt: str,
    cwd: str | None = None,
    timeout: float | None = None,
) -> HermesResult | None:
    """
    Run Hermes agent headlessly via `hermes -z`.

    The -z flag gives pure headless output: single prompt in,
    final response text out, no banner/spinner/TUI.

    Args:
        prompt: The task prompt.
        cwd: Working directory for the agent.
        timeout: Max seconds. Default from HERMES_TIMEOUT_SECONDS or 120.

    Returns:
        HermesResult on success, None on error.
    """
    if timeout is None:
        timeout = _resolve_timeout()

    if not is_available():
        logger.warning("[hermes] CLI not found on PATH")
        return None

    try:
        from state.providers.provider_state import get_system_state
        if not get_system_state().allow_execution():
            logger.info("[hermes] blocked by backpressure gate")
            return None
    except Exception:
        pass

    cmd = ["hermes", "-z", prompt]
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
        logger.warning("[hermes] timed out after %ss", timeout)
        _track_result(False)
        return None
    except Exception as e:
        logger.warning("[hermes] subprocess error: %s", e)
        _track_result(False)
        return None

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    output = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0 and not output:
        logger.warning("[hermes] exit code %d: %s", result.returncode, stderr[:200])
        _track_result(False)
        return None

    if not output:
        logger.warning("[hermes] empty response. stderr: %s", stderr[:200])
        _track_result(False)
        return None

    if _is_error_leak(output) or _is_error_leak(stderr):
        logger.warning("[hermes] error leak detected: %s", (output or stderr)[:120])
        _track_result(False)
        return None

    _track_result(True)
    return HermesResult(
        output=output,
        latency_ms=elapsed_ms,
        provider="hermes",
    )
