"""
cc_sdk — Claude Code Agent SDK wrapper for EOS.

New provider for model_router. Uses claude-agent-sdk to run queries
through Claude Code's subprocess transport (local CLI).

This is NOT a replacement for model_router — it is a provider that
model_router can call, alongside Gemini, Ollama, etc.

Usage:
    from eos_ai.cc_sdk import query_cc_sync

    result = query_cc_sync("Analyze this business situation")
    if result:
        print(result.output)
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── Task type → effort mapping ─────────────────────────────────────────────

EFFORT_MAP: dict[str, str] = {
    "analyze": "high",
    "fast_response": "low",
    "generate": "medium",
    "code": "high",
}

# ─── Session persistence per agent ──────────────────────────────────────────

_agent_sessions: dict[str, str] = {}


# ─── Result dataclass ───────────────────────────────────────────────────────


@dataclass
class CCResult:
    """Return type for cc_sdk queries."""

    output: str
    session_id: str
    latency_ms: int
    provider: str = "cc_sdk"
    model: str = ""


# ─── Core async query ───────────────────────────────────────────────────────


def _is_nested_cc_session() -> bool:
    """Return True if we're already inside a Claude Code session."""
    return bool(os.environ.get("CLAUDE_CODE_SESSION"))


async def query_cc(
    prompt: str,
    system: str = "",
    task_type: str = "analyze",
    session_id: str | None = None,
    max_budget_usd: float = 0.10,
    agent_id: str | None = None,
    timeout: float = 30.0,
) -> CCResult | None:
    """
    Query Claude Code via the Agent SDK.

    Args:
        prompt: The user prompt to send.
        system: Optional system prompt.
        task_type: One of analyze, fast_response, generate, code.
        session_id: Explicit session ID. If None, uses persisted
                    session for agent_id (if provided).
        max_budget_usd: Hard budget cap per call. Default $0.10.
        agent_id: Agent identifier for session persistence.
        timeout: Max seconds to wait for response. Default 30.

    Returns:
        CCResult on success, None on any error.
    """
    if _is_nested_cc_session():
        logger.info("[CC SDK] Nested session detected, skipping")
        return None

    # Lower budget for fast tasks
    if task_type == "fast_response":
        max_budget_usd = min(max_budget_usd, 0.05)

    try:
        from claude_agent_sdk import (
            ClaudeAgentOptions,
            ResultMessage,
            AssistantMessage,
            TextBlock,
            query,
        )
    except ImportError:
        logger.error("claude-agent-sdk not installed")
        return None

    # Resolve session: explicit > persisted > None
    resolved_session = session_id
    if resolved_session is None and agent_id:
        resolved_session = _agent_sessions.get(agent_id)

    # Build options
    effort = EFFORT_MAP.get(task_type, "medium")

    # Set initialize timeout in parent process env (SDK reads os.environ, not child env)
    os.environ.setdefault("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "120000")

    options = ClaudeAgentOptions(
        system_prompt=system or None,
        max_budget_usd=max_budget_usd,
        permission_mode="auto",
        max_turns=1,
        cli_path="/usr/bin/claude",
        setting_sources=[],
    )

    # Resume prior session if available
    if resolved_session:
        options.resume = resolved_session

    start_ms = time.monotonic_ns() // 1_000_000
    output_parts: list[str] = []
    result_session_id = resolved_session or ""
    model_used = ""

    async def _stream() -> None:
        nonlocal model_used, result_session_id
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    model_used = getattr(message, "model", "")
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            output_parts.append(block.text)
                elif isinstance(message, ResultMessage):
                    if message.session_id:
                        result_session_id = message.session_id
                    if message.result:
                        output_parts.append(message.result)
        except Exception as e:
            # The SDK raises when CLI exits with non-zero code (e.g., exit
            # code 1 from MCP server shutdown).  The error arrives via the
            # stream *after* valid messages have already been yielded, so
            # output_parts will normally contain the real response.  Catch
            # here so the outer code sees collected output instead of an
            # empty failure.
            logger.debug("cc_sdk _stream: caught %s (output_parts=%d)", e, len(output_parts))

    try:
        await asyncio.wait_for(_stream(), timeout=timeout)

    except asyncio.TimeoutError:
        if output_parts:
            logger.warning("cc_sdk: timed out after %ss but partial output available", timeout)
        else:
            logger.warning("cc_sdk: timed out after %ss with no output", timeout)
            return None

    except Exception as e:
        # Fallback: if something outside _stream raises, still check output.
        if output_parts:
            logger.debug("cc_sdk: outer error after response — %s", e)
        else:
            err_str = str(e).lower()
            stderr_detail = getattr(e, "stderr", None) or ""
            if "rate" in err_str or "429" in err_str:
                logger.warning("cc_sdk: rate limited — %s %s", e, stderr_detail)
            elif "auth" in err_str or "401" in err_str or "key" in err_str:
                logger.warning("cc_sdk: auth error — %s %s", e, stderr_detail)
            elif "timeout" in err_str or "timed out" in err_str:
                logger.warning("cc_sdk: timeout — %s %s", e, stderr_detail)
            else:
                logger.warning("cc_sdk: query failed — %s %s", e, stderr_detail)
            return None

    elapsed_ms = (time.monotonic_ns() // 1_000_000) - start_ms

    # Persist session for this agent
    if agent_id and result_session_id:
        _agent_sessions[agent_id] = result_session_id

    output = "\n".join(output_parts).strip()
    if not output:
        logger.warning("cc_sdk: empty response")
        return None

    return CCResult(
        output=output,
        session_id=result_session_id,
        latency_ms=elapsed_ms,
        provider="cc_sdk",
        model=model_used,
    )


# ─── Sync wrapper for model_router compatibility ────────────────────────────


def query_cc_sync(
    prompt: str,
    system: str = "",
    task_type: str = "analyze",
    session_id: str | None = None,
    max_budget_usd: float = 0.10,
    agent_id: str | None = None,
    timeout: float = 30.0,
) -> CCResult | None:
    """
    Synchronous wrapper around query_cc().

    Safe to call from model_router and other sync code.
    Creates a new event loop if none is running.
    """
    if _is_nested_cc_session():
        logger.info("[CC SDK] Nested session detected, skipping")
        return None

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    coro = query_cc(
        prompt=prompt,
        system=system,
        task_type=task_type,
        session_id=session_id,
        max_budget_usd=max_budget_usd,
        agent_id=agent_id,
        timeout=timeout,
    )

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=timeout + 5)
    else:
        return asyncio.run(coro)
