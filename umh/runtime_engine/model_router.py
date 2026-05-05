"""Model router — compatibility wrapper over umh.adapters.model_router.

Generic routing engine lives in UMH. This file adds EOS-specific features:
  - Claude CLI tmux backend (Backend #0)
  - CC SDK integration
  - Discord mode routing
  - Execution trace stamping
  - CEO agent keyword detection
  - adversarial_code_review stub

All generic types (ModelProvider, TaskType, ModelConfig, RoutingResult,
ModelRouter, etc.) are re-exported from UMH.

Usage unchanged:
    from umh.runtime_engine.model_router import call_with_fallback, TaskType, get_router
"""

import logging
import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

from umh.adapters.model_router import (  # noqa: E402, F401
    CC_MODEL_MAP,
    ESCALATION_QUALITY_THRESHOLD,
    FAST_TASK_TYPES,
    HAIKU_TOKEN_CAPS,
    ModelConfig,
    ModelProvider,
    ModelRouter,
    PROVIDER_PRIORITY,
    PROVIDER_PRIORITY_FAST,
    PROVIDER_QUALITY,
    RoutingResult,
    TASK_TYPE_MAP,
    TaskType,
    build_default_registry,
    estimate_quality_score,
    get_router,
    ollama_available,
    reset_router,
    should_escalate,
)

from umh.runtime_engine.cc_sdk import query_cc_sync, CCResult  # noqa: E402

logger = logging.getLogger(__name__)

# Re-export the registry from UMH singleton
MODEL_REGISTRY = get_router().registry

# Backward compat aliases
_FAST_TASK_TYPES = FAST_TASK_TYPES
_HAIKU_TOKEN_CAPS = HAIKU_TOKEN_CAPS
_ESCALATION_QUALITY_THRESHOLD = ESCALATION_QUALITY_THRESHOLD
_estimate_quality_score = estimate_quality_score
_should_escalate = should_escalate
_ollama_available = ollama_available

# ─── EOS-specific routing ─────────────────────────────────────────────────────

_CEO_AGENT_KEYWORDS = ("_ceo", "portfolio_advisor", "strategic")


def _claude_cli_backend_enabled() -> bool:
    raw = (os.getenv("EOS_ROUTER_CLAUDE_CLI_ENABLED") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def _is_ceo_agent(agent_type: str | None) -> bool:
    if not agent_type:
        return False
    agent_lower = agent_type.lower()
    return any(kw in agent_lower for kw in _CEO_AGENT_KEYWORDS)


def call_with_fallback(
    prompt: str,
    system: str | None = None,
    task_type: "TaskType | str" = "fast_response",
    trigger_source: str = "conversational",
    agent_type: str | None = None,
    force_opus: bool = False,
    raw_input: str | None = None,
    max_tokens: int = 1024,
) -> RoutingResult:
    """Main routing entry point for all EOS agent calls.

    Adds Claude CLI tmux backend, CC SDK escalation, execution trace
    stamping, and CEO agent overrides on top of the UMH generic router.
    """
    if isinstance(task_type, TaskType):
        task_type_str = task_type.value
    else:
        task_type_str = task_type

    is_ceo = _is_ceo_agent(agent_type) or force_opus
    if is_ceo:
        task_type_str = TaskType.STRATEGIC.value

    is_fast = task_type_str in FAST_TASK_TYPES and not is_ceo

    logger.info(
        "[Router] task=%s agent=%s trigger=%s fast=%s",
        task_type_str,
        agent_type,
        trigger_source,
        is_fast,
    )

    router = get_router()
    router.check_availability()

    router_task_str = TASK_TYPE_MAP.get(task_type_str, task_type_str)
    try:
        router_task = TaskType(router_task_str)
    except ValueError:
        router_task = TaskType.FAST_RESPONSE

    priority = PROVIDER_PRIORITY_FAST if is_fast else PROVIDER_PRIORITY

    start = time.time()

    # ── Backend #0: Claude CLI persistent tmux session ──
    # Only for conversational triggers — execution engine needs stateless CC SDK
    cli_enabled = _claude_cli_backend_enabled() and trigger_source == "conversational"
    logger.info(
        "[Router] claude_cli backend gate: enabled=%s path=%s trigger=%s",
        cli_enabled,
        "fast" if is_fast else "heavy",
        trigger_source,
    )
    if cli_enabled:
        try:
            from umh.substrate.claude_responder import (
                DEFAULT_SESSION_NAME,
                DEFAULT_TARGET,
                respond_via_claude_session,
            )

            cli_target = (
                os.getenv("EOS_ROUTER_CLAUDE_CLI_TARGET") or DEFAULT_TARGET
            ).strip().lower() or DEFAULT_TARGET
            cli_session = (
                os.getenv("EOS_ROUTER_CLAUDE_CLI_SESSION") or DEFAULT_SESSION_NAME
            ).strip() or DEFAULT_SESSION_NAME

            mode_label = None
            try:
                from umh.substrate.discord_mode_routing import (
                    current_mode_context,
                )

                _mctx = current_mode_context()
                if _mctx:
                    mode_label = _mctx.get("mode")
                    _mt = (_mctx.get("target") or "").strip().lower()
                    if _mt:
                        cli_target = _mt
                    _ms = (_mctx.get("session_name") or "").strip()
                    if _ms:
                        cli_session = _ms
            except Exception as _mode_exc:
                logger.warning("[Router] mode_context lookup failed: %s", _mode_exc)

            cli_text = raw_input if raw_input else prompt
            logger.info(
                "[Router] claude_cli attempt: target=%s session=%s mode=%s chars=%d",
                cli_target,
                cli_session,
                mode_label or "none",
                len(cli_text),
            )
            cli_res = respond_via_claude_session(
                cli_text,
                target=cli_target,
                session_name=cli_session,
            )
            if cli_res.get("ok") and cli_res.get("reply"):
                latency_ms = int((time.time() - start) * 1000)
                reply_text = cli_res["reply"]
                est_tokens = max(1, len(reply_text) // 4)
                logger.info(
                    "[Router] claude_cli/%s responded (%dms, ~%d tok)",
                    cli_session,
                    latency_ms,
                    est_tokens,
                )
                _stamp_trace("claude_cli", f"tmux:{cli_session}", latency_ms, "ok")
                return RoutingResult(
                    output=reply_text,
                    provider="claude_cli",
                    model=f"tmux:{cli_session}",
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                    tokens_used=est_tokens,
                    output_tokens=est_tokens,
                )
            logger.info(
                "[Router] claude_cli unavailable (reason=%s) — falling through",
                cli_res.get("reason"),
            )
        except Exception as exc:
            logger.warning("[Router] claude_cli backend error: %s", exc)
    else:
        logger.info("[Router] claude_cli backend disabled — skipping")

    if is_fast:
        # ── FAST PATH: Haiku first, escalate to cc_sdk if quality low ──
        haiku_cap = HAIKU_TOKEN_CAPS.get(task_type_str, 800)
        effective_max = min(haiku_cap, max_tokens)
        candidates = [
            c
            for c in router.registry.values()
            if c.provider == ModelProvider.ANTHROPIC and c.available
        ]
        candidates.sort(key=lambda x: x.cost_per_1k)

        for config in candidates:
            output = router.call(config, prompt, system or "", effective_max)
            if output:
                if should_escalate(output, config.provider.value):
                    break
                latency_ms = int((time.time() - start) * 1000)
                _stamp_trace(config.provider.value, config.model_id, latency_ms, "ok")
                return RoutingResult(
                    output=output,
                    provider=config.provider.value,
                    model=config.model_id,
                    task_type=task_type_str,
                    input_tokens=router._last_input_tokens,
                    output_tokens=router._last_output_tokens,
                    tokens_used=router._last_input_tokens + router._last_output_tokens,
                    latency_ms=latency_ms,
                )

        # Escalate to cc_sdk
        if query_cc_sync is not None:
            cc_result = query_cc_sync(
                prompt=prompt,
                system=system or "",
                task_type=task_type_str,
                agent_id=agent_type or "eos_default",
                max_budget_usd=0.10,
            )
            if cc_result and cc_result.output:
                latency_ms = int((time.time() - start) * 1000)
                _stamp_trace("cc_sdk", cc_result.model, latency_ms, "ok_escalated")
                return RoutingResult(
                    output=cc_result.output,
                    provider="cc_sdk",
                    model=cc_result.model,
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                )

        # Remaining providers
        remaining = [
            c
            for c in router.registry.values()
            if c.available and c.provider not in (ModelProvider.ANTHROPIC, ModelProvider.CC_SDK)
        ]
        remaining.sort(key=lambda x: priority.get(x.provider, 99))

        for config in remaining:
            output = router.call(config, prompt, system or "", max_tokens)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                _stamp_trace(
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                    "ok_fast_fallback",
                )
                return RoutingResult(
                    output=output,
                    provider=config.provider.value,
                    model=config.model_id,
                    task_type=task_type_str,
                    input_tokens=router._last_input_tokens,
                    output_tokens=router._last_output_tokens,
                    tokens_used=router._last_input_tokens + router._last_output_tokens,
                    latency_ms=latency_ms,
                )

    else:
        # ── HEAVY PATH: cc_sdk first, then registry fallback ──
        if query_cc_sync is not None:
            cc_result = query_cc_sync(
                prompt=prompt,
                system=system or "",
                task_type=task_type_str,
                agent_id=agent_type or "eos_default",
                max_budget_usd=0.10,
            )
            if cc_result and cc_result.output:
                latency_ms = int((time.time() - start) * 1000)
                _stamp_trace("cc_sdk", cc_result.model, latency_ms, "ok")
                return RoutingResult(
                    output=cc_result.output,
                    provider="cc_sdk",
                    model=cc_result.model,
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                )
            logger.info("[Router] cc_sdk failed, falling back to registry providers")

        strength_matched = [
            c for c in router.registry.values() if router_task in c.strengths and c.available
        ]
        strength_matched.sort(key=lambda x: priority.get(x.provider, 99))
        _tried_providers: set = set()

        for config in strength_matched:
            if not config.available:
                continue
            _tried_providers.add(config.provider)
            output = router.call(config, prompt, system or "", max_tokens)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                _stamp_trace(
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                    "ok_heavy_fallback",
                )
                return RoutingResult(
                    output=output,
                    provider=config.provider.value,
                    model=config.model_id,
                    task_type=task_type_str,
                    input_tokens=router._last_input_tokens,
                    output_tokens=router._last_output_tokens,
                    tokens_used=router._last_input_tokens + router._last_output_tokens,
                    latency_ms=latency_ms,
                )

        remaining = [
            c
            for c in router.registry.values()
            if c.available and c.provider not in _tried_providers
        ]
        remaining.sort(key=lambda x: priority.get(x.provider, 99))

        for config in remaining:
            if not config.available:
                continue
            output = router.call(config, prompt, system or "", max_tokens)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                _stamp_trace(
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                    "ok_heavy_remaining",
                )
                return RoutingResult(
                    output=output,
                    provider=config.provider.value,
                    model=config.model_id,
                    task_type=task_type_str,
                    input_tokens=router._last_input_tokens,
                    output_tokens=router._last_output_tokens,
                    tokens_used=router._last_input_tokens + router._last_output_tokens,
                    latency_ms=latency_ms,
                )

    latency_ms = int((time.time() - start) * 1000)
    logger.error("[Router] ALL PROVIDERS FAILED")
    _stamp_trace("none", "none", latency_ms, "all_failed")
    return RoutingResult(
        output=(
            "[EOS] All intelligence providers unavailable. Check API keys and network connectivity."
        ),
        provider="none",
        model="none",
        task_type=task_type_str,
        latency_ms=latency_ms,
    )


def _stamp_trace(provider: str, model: str, latency_ms: int, result: str) -> None:
    """Stamp execution trace with router outcome. Never raises."""
    try:
        from umh.substrate.execution_trace import get_current_trace, finalize_trace

        trace = get_current_trace()
        if trace is not None:
            finalize_trace(
                trace,
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                result=result,
            )
    except Exception:
        pass


def adversarial_code_review(
    code_or_plan: str,
    context: str | None = None,
) -> str:
    """Adversarial review stub — returns input unchanged."""
    logger.info("[Router] adversarial_code_review: Codex unavailable, returning input")
    return code_or_plan
