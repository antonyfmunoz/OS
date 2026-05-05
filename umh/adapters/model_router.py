"""Multi-provider model router with fallback chain.

Provides task-type-aware model selection and universal call dispatch
across Anthropic, Gemini, Groq, Perplexity, OpenAI, and Ollama.

Standalone — no umh imports. EOS-specific features (CC SDK, Claude CLI,
execution traces) live in the umh/model_router.py compatibility wrapper.

Usage:
    from umh.adapters.model_router import ModelRouter, TaskType, get_router

    router = get_router()
    model = router.route(TaskType.ANALYSIS)
    if model:
        result = router.call(model, prompt="What is trending?")

This is the UMH-owned extraction of the generic routing engine
from umh/model_router.py.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ─── RoutingResult ────────────────────────────────────────────────────────────


@dataclass
class RoutingResult:
    """Return type for model routing calls."""

    output: str
    provider: str
    model: str
    task_type: str
    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


# ─── Providers ────────────────────────────────────────────────────────────────


class ModelProvider(Enum):
    CLAUDE_CLI = "claude_cli"
    CC_SDK = "cc_sdk"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    MANUS = "manus"


class TaskType(Enum):
    CONVERSATION = "conversation"
    ANALYSIS = "analysis"
    WEB_SEARCH = "web_search"
    MARKET_INTEL = "market_intel"
    FAST_RESPONSE = "fast_response"
    LONG_CONTEXT = "long_context"
    AUTONOMOUS = "autonomous"
    MULTIMODAL = "multimodal"
    BROWSER_CONTROL = "browser_control"
    SCORE = "score"
    CLASSIFY = "classify"
    ANALYZE = "analyze"
    GENERATE = "generate"
    SUMMARIZE = "summarize"
    STRATEGIC = "strategic"
    CODE = "code"
    RESEARCH = "research"
    SELF_IMPROVE = "self_improve"
    PLAN = "plan"
    COORDINATE = "coordinate"


# ─── CC model map ─────────────────────────────────────────────────────────────

CC_MODEL_MAP: dict[str, str] = {
    TaskType.STRATEGIC.value: "claude-opus-4-6",
    TaskType.CODE.value: "claude-opus-4-6",
    TaskType.SELF_IMPROVE.value: "claude-opus-4-6",
    TaskType.PLAN.value: "claude-opus-4-6",
    TaskType.ANALYZE.value: "claude-sonnet-4-6",
    TaskType.ANALYSIS.value: "claude-sonnet-4-6",
    TaskType.GENERATE.value: "claude-sonnet-4-6",
    TaskType.RESEARCH.value: "claude-sonnet-4-6",
    TaskType.COORDINATE.value: "claude-sonnet-4-6",
    TaskType.LONG_CONTEXT.value: "claude-sonnet-4-6",
    TaskType.CONVERSATION.value: "claude-sonnet-4-6",
    TaskType.SCORE.value: "claude-haiku-4-5-20251001",
    TaskType.CLASSIFY.value: "claude-haiku-4-5-20251001",
    TaskType.SUMMARIZE.value: "claude-haiku-4-5-20251001",
    TaskType.FAST_RESPONSE.value: "claude-haiku-4-5-20251001",
    TaskType.MARKET_INTEL.value: "claude-sonnet-4-6",
    TaskType.WEB_SEARCH.value: "claude-sonnet-4-6",
    TaskType.AUTONOMOUS.value: "claude-opus-4-6",
}


# ─── Model configuration ─────────────────────────────────────────────────────


@dataclass
class ModelConfig:
    """Configuration for a single model endpoint."""

    provider: ModelProvider
    model_id: str
    api_key_env: str
    strengths: list[TaskType]
    cost_per_1k: float
    available: bool = False
    base_url: str = ""


PROVIDER_PRIORITY: dict[ModelProvider, int] = {
    ModelProvider.CLAUDE_CLI: 0,
    ModelProvider.CC_SDK: 1,
    ModelProvider.GEMINI: 2,
    ModelProvider.GROQ: 3,
    ModelProvider.ANTHROPIC: 4,
    ModelProvider.OPENAI: 5,
    ModelProvider.PERPLEXITY: 6,
    ModelProvider.OLLAMA: 7,
    ModelProvider.MANUS: 8,
}

PROVIDER_PRIORITY_FAST: dict[ModelProvider, int] = {
    ModelProvider.CLAUDE_CLI: 0,
    ModelProvider.GEMINI: 1,
    ModelProvider.GROQ: 2,
    ModelProvider.ANTHROPIC: 3,
    ModelProvider.OPENAI: 4,
    ModelProvider.CC_SDK: 5,
    ModelProvider.PERPLEXITY: 6,
    ModelProvider.OLLAMA: 7,
    ModelProvider.MANUS: 8,
}

FAST_TASK_TYPES = frozenset(
    {"fast_response", "conversation", "score", "classify", "summarize"}
)

HAIKU_TOKEN_CAPS: dict[str, int] = {
    "fast_response": 500,
    "conversation": 800,
    "score": 500,
    "classify": 500,
    "summarize": 800,
}

ESCALATION_QUALITY_THRESHOLD = 0.40

PROVIDER_QUALITY: dict[str, float] = {
    "cc_sdk": 0.85,
    "anthropic": 0.80,
    "gemini": 0.65,
    "groq": 0.55,
    "perplexity": 0.60,
    "ollama": 0.35,
}


# ─── Task type mapping ───────────────────────────────────────────────────────

TASK_TYPE_MAP: dict[str, str] = {
    "strategic": "analysis",
    "code": "analysis",
    "research": "web_search",
    "self_improve": "analysis",
    "plan": "analysis",
    "coordinate": "conversation",
    "score": "fast_response",
    "classify": "fast_response",
    "analyze": "analysis",
    "generate": "conversation",
    "summarize": "fast_response",
}


# ─── Default model registry ──────────────────────────────────────────────────


def build_default_registry() -> dict[str, ModelConfig]:
    """Build the default model registry from environment."""
    return {
        "claude-haiku": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-haiku-4-5-20251001",
            api_key_env="ANTHROPIC_API_KEY",
            strengths=[
                TaskType.CONVERSATION,
                TaskType.ANALYSIS,
                TaskType.FAST_RESPONSE,
            ],
            cost_per_1k=0.00025,
        ),
        "claude-sonnet": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-sonnet-4-6",
            api_key_env="ANTHROPIC_API_KEY",
            strengths=[TaskType.CONVERSATION, TaskType.ANALYSIS, TaskType.LONG_CONTEXT],
            cost_per_1k=0.003,
        ),
        "perplexity-sonar": ModelConfig(
            provider=ModelProvider.PERPLEXITY,
            model_id="sonar-pro",
            api_key_env="PERPLEXITY_API_KEY",
            strengths=[TaskType.WEB_SEARCH, TaskType.MARKET_INTEL],
            cost_per_1k=0.001,
            base_url="https://api.perplexity.ai",
        ),
        "groq-llama": ModelConfig(
            provider=ModelProvider.GROQ,
            model_id="llama-3.3-70b-versatile",
            api_key_env="GROQ_API_KEY",
            strengths=[TaskType.FAST_RESPONSE, TaskType.CONVERSATION],
            cost_per_1k=0.00059,
            base_url="https://api.groq.com/openai/v1",
        ),
        "ollama-qwen": ModelConfig(
            provider=ModelProvider.OLLAMA,
            model_id="qwen2.5:0.5b",
            api_key_env="",
            strengths=[TaskType.FAST_RESPONSE],
            cost_per_1k=0.0,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ),
        "gemini-pro": ModelConfig(
            provider=ModelProvider.GEMINI,
            model_id="gemini-2.5-flash",
            api_key_env="GEMINI_API_KEY",
            strengths=[
                TaskType.MULTIMODAL,
                TaskType.LONG_CONTEXT,
                TaskType.ANALYSIS,
                TaskType.FAST_RESPONSE,
                TaskType.CONVERSATION,
            ],
            cost_per_1k=0.000075,
        ),
        "manus": ModelConfig(
            provider=ModelProvider.MANUS,
            model_id="manus-agent",
            api_key_env="MANUS_API_KEY",
            strengths=[TaskType.AUTONOMOUS, TaskType.BROWSER_CONTROL],
            cost_per_1k=0.0,
            available=False,
            base_url="https://manus.im",
        ),
    }


# ─── Quality estimation ──────────────────────────────────────────────────────


def estimate_quality_score(output: str, provider: str) -> float:
    """Heuristic quality score for a model response."""
    if not output or not output.strip():
        return 0.0

    base = PROVIDER_QUALITY.get(provider, 0.5)
    length = len(output.strip())

    if length < 20:
        return min(base, 0.3)
    if length < 50:
        return min(base, 0.5)

    _refusal = any(
        p in output.lower()
        for p in ["i cannot", "i can't", "i'm sorry", "as an ai", "i don't have"]
    )
    if _refusal:
        return min(base, 0.4)

    return base


def should_escalate(output: str, provider: str) -> bool:
    """Return True if response quality is below escalation threshold."""
    score = estimate_quality_score(output, provider)
    if score < ESCALATION_QUALITY_THRESHOLD:
        logger.warning(
            "[Router] Quality %.2f < %.2f from %s — escalating",
            score,
            ESCALATION_QUALITY_THRESHOLD,
            provider,
        )
        return True
    return False


# ─── Availability checks ─────────────────────────────────────────────────────


def ollama_available() -> bool:
    """Returns True if Ollama HTTP endpoint responds within 2s."""
    try:
        import urllib.request

        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        resp = urllib.request.urlopen(req, timeout=2)
        return resp.status == 200
    except Exception:
        return False


# ─── Provider call implementations ───────────────────────────────────────────


def call_anthropic(
    config: ModelConfig,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, int, int]:
    """Call Anthropic API. Returns (output, input_tokens, output_tokens)."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv(config.api_key_env))
        kwargs: dict[str, Any] = {
            "model": config.model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        in_tok = getattr(response.usage, "input_tokens", 0) if response.usage else 0
        out_tok = getattr(response.usage, "output_tokens", 0) if response.usage else 0
        return response.content[0].text, in_tok, out_tok
    except Exception as e:
        err_str = str(e)
        _fatal = any(
            p in err_str
            for p in [
                "credit balance is too low",
                "Your credit balance",
                "authentication_error",
                "invalid x-api-key",
            ]
        )
        if _fatal:
            logger.warning("[Router] Anthropic unavailable: %s", err_str[:120])
        else:
            logger.warning("[Router] Anthropic error: %s", e)
        return "", 0, 0


def call_openai_compatible(
    config: ModelConfig,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, int, int]:
    """Call OpenAI-compatible API. Returns (output, input_tokens, output_tokens)."""
    try:
        from openai import OpenAI
    except ImportError:
        return "", 0, 0
    try:
        client = OpenAI(
            api_key=os.getenv(config.api_key_env),
            base_url=config.base_url or None,
        )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=config.model_id,
            messages=messages,
            max_tokens=max_tokens,
        )
        in_tok = (
            getattr(response.usage, "prompt_tokens", 0) or 0 if response.usage else 0
        )
        out_tok = (
            getattr(response.usage, "completion_tokens", 0) or 0
            if response.usage
            else 0
        )
        return response.choices[0].message.content or "", in_tok, out_tok
    except Exception as e:
        logger.warning("[Router] %s error: %s", config.provider.value, e)
        return "", 0, 0


def call_ollama(
    config: ModelConfig,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, int, int]:
    """Call Ollama API. Returns (output, input_tokens, output_tokens)."""
    try:
        import urllib.request
        import json

        _sys = system[:1500] if system else ""
        _max_tokens = min(max_tokens, 256)
        payload: dict[str, Any] = {
            "model": config.model_id,
            "prompt": prompt[:2000],
            "stream": False,
            "options": {"num_predict": _max_tokens},
        }
        if _sys:
            payload["system"] = _sys

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{config.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=60)
        elapsed = time.time() - start
        if elapsed > 60:
            logger.warning("[Ollama] Slow response: %.0fs", elapsed)
        data = json.loads(resp.read())
        in_tok = data.get("prompt_eval_count", 0) or 0
        out_tok = data.get("eval_count", 0) or 0
        return data.get("response", ""), in_tok, out_tok
    except Exception as e:
        logger.warning("[Router] Ollama error: %s", e)
        return "", 0, 0


def call_gemini(
    config: ModelConfig,
    prompt: str,
    system: str,
    max_tokens: int,
) -> tuple[str, int, int]:
    """Call Gemini API. Returns (output, input_tokens, output_tokens)."""
    try:
        from google import genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore

        client = genai.Client(api_key=os.getenv(config.api_key_env))
        cfg = genai_types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            system_instruction=system or None,
        )
        response = client.models.generate_content(
            model=config.model_id,
            contents=prompt,
            config=cfg,
        )
        in_tok = (
            getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            if response.usage_metadata
            else 0
        )
        out_tok = (
            getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            if response.usage_metadata
            else 0
        )
        return response.text or "", in_tok, out_tok
    except Exception as e:
        logger.warning("[Router] Gemini error: %s", e)
        return "", 0, 0


# ─── ModelRouter class ────────────────────────────────────────────────────────


class ModelRouter:
    """Multi-provider model router with fallback chain."""

    def __init__(
        self,
        registry: dict[str, ModelConfig] | None = None,
    ) -> None:
        self.registry = registry if registry is not None else build_default_registry()
        self._last_input_tokens: int = 0
        self._last_output_tokens: int = 0
        self.check_availability()

    def check_availability(self) -> None:
        """Probe all registered models for availability."""
        for config in self.registry.values():
            if not config.api_key_env:
                config.available = (
                    config.provider == ModelProvider.OLLAMA and ollama_available()
                )
            elif os.getenv(config.api_key_env):
                config.available = True
            else:
                config.available = False

    def route(
        self,
        task_type: TaskType,
        prefer_fast: bool = False,
        prefer_cheap: bool = False,
    ) -> ModelConfig | None:
        """Select the best available model for the given task type."""
        candidates = [
            c
            for c in self.registry.values()
            if task_type in c.strengths and c.available
        ]

        if not candidates:
            candidates = [c for c in self.registry.values() if c.available]

        if not candidates:
            return None

        if prefer_fast or prefer_cheap:
            candidates.sort(key=lambda x: x.cost_per_1k)
        else:
            candidates.sort(key=lambda x: PROVIDER_PRIORITY.get(x.provider, 99))

        return candidates[0]

    def call(
        self,
        model_config: ModelConfig,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
    ) -> str:
        """Universal model call — routes to correct API by provider."""
        self._last_input_tokens = 0
        self._last_output_tokens = 0
        provider = model_config.provider

        if provider == ModelProvider.ANTHROPIC:
            output, in_t, out_t = call_anthropic(
                model_config, prompt, system, max_tokens
            )
        elif provider in (ModelProvider.PERPLEXITY, ModelProvider.GROQ):
            output, in_t, out_t = call_openai_compatible(
                model_config, prompt, system, max_tokens
            )
        elif provider == ModelProvider.OLLAMA:
            output, in_t, out_t = call_ollama(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.GEMINI:
            output, in_t, out_t = call_gemini(model_config, prompt, system, max_tokens)
        else:
            logger.warning("[Router] Unknown provider: %s", provider)
            return ""

        self._last_input_tokens = in_t
        self._last_output_tokens = out_t

        if not output:
            _fatal_providers = {ModelProvider.ANTHROPIC}
            if provider in _fatal_providers:
                for cfg in self.registry.values():
                    if cfg.provider == provider:
                        cfg.available = False

        return output

    def call_with_fallback(
        self,
        task_type: TaskType,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
    ) -> str:
        """Try models in priority order until one returns a non-empty response."""
        candidates = [
            c
            for c in self.registry.values()
            if task_type in c.strengths and c.available
        ]
        if not candidates:
            candidates = [c for c in self.registry.values() if c.available]

        candidates.sort(key=lambda x: PROVIDER_PRIORITY.get(x.provider, 99))

        for config in candidates:
            if not config.available:
                continue
            result = self.call(config, prompt, system, max_tokens)
            if result:
                return result

        logger.warning("[Router] All candidates exhausted for %s", task_type.name)
        return ""

    def get_status(self) -> str:
        """Return human-readable status of all registered models."""
        lines = ["MODEL REGISTRY:"]
        for model_id, config in self.registry.items():
            status = "available" if config.available else "unavailable"
            lines.append(
                f"  [{status}] {model_id} "
                f"({config.provider.value}) "
                f"${config.cost_per_1k}/1k tokens"
            )
        return "\n".join(lines)


# ─── Module-level singleton ──────────────────────────────────────────────────

_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    """Get the module-level ModelRouter singleton."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def reset_router() -> None:
    """Reset the singleton (for testing)."""
    global _router
    _router = None
