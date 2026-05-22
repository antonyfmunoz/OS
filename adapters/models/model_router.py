"""
ModelRouter — standalone multi-model router for EOS.

Provides task-type-aware model selection and universal call dispatch
across Anthropic, Perplexity, Groq, Gemini, and Ollama.

Complements ModelPreferences (which handles business-context routing).
Used directly by WorldPulse and other modules that need a simple
"give me the best model for this task" API.

Usage:
    from execution.runtime.model_router import get_router, TaskType

    router = get_router()
    print(router.get_status())

    model = router.route(TaskType.MARKET_INTEL)
    if model:
        result = router.call(model, prompt='What is trending in AI?')
        print(result)
"""

import json
import os
import re
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from adapters.models.cc_sdk import query_cc_sync, CCResult
from adapters.models.codex_cli import query_codex_sync, CodexResult
from adapters.models.hermes_cli import query_hermes_sync, HermesResult
from adapters.models.opencode_cli import query_opencode_sync, OpenCodeResult

# Load .env so GEMINI_API_KEY is available when model_router is used standalone
# (agent_runtime does this too — safe to call twice, dotenv is idempotent)
try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

from state.providers.provider_state import get_system_state

logger = logging.getLogger(__name__)

# ─── Fix-forever error recording ─────────────────────────────────────────────

_ERROR_LOG_PATH = (
    Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or "/opt/OS")
    / "logs"
    / "model_router_errors.jsonl"
)


def _record_error(component: str, error: str, context: dict | None = None) -> None:
    """Append error to JSONL log for pattern detection and permanent fixing."""
    try:
        _ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "error": str(error)[:500],
            "context": {k: str(v)[:200] for k, v in (context or {}).items()},
        }
        with _ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ─── Deterministic fallback for model router ─────────────────────────────────

_ROUTER_INTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(schedule|book|calendar|meeting|call)\b", re.I), "calendar_action"),
    (re.compile(r"\b(send|draft|email|compose)\b", re.I), "email_action"),
    (re.compile(r"\b(check|status|update|progress)\b", re.I), "status_check"),
    (re.compile(r"\b(analyze|review|assess|evaluate)\b", re.I), "analysis"),
    (re.compile(r"\b(create|build|write|generate)\b", re.I), "content_creation"),
    (re.compile(r"\b(fix|debug|error|broken|issue)\b", re.I), "troubleshoot"),
    (re.compile(r"\b(hey|hi|hello|morning|gm|yo|sup)\b", re.I), "greeting"),
]

_ROUTER_INTENT_FALLBACKS: dict[str, str] = {
    "calendar_action": "I've noted your calendar request. AI providers are temporarily unavailable — I'll process this once they reconnect.",
    "email_action": "I've captured your email request. I'll draft and send once AI is back online.",
    "status_check": "Operating in reduced mode — AI providers temporarily unavailable. Core systems remain functional.",
    "analysis": "Analysis queued. Full analytical capabilities require AI, which is temporarily offline.",
    "content_creation": "Content generation requires AI, which is temporarily unavailable. Request logged.",
    "troubleshoot": "Issue logged for investigation. Diagnostic capabilities limited while AI is offline.",
    "greeting": "Hey! Operating in reduced mode — AI providers temporarily offline. Core functions still work.",
}

_ROUTER_DEFAULT_FALLBACK = (
    "All intelligence providers are temporarily unavailable. "
    "Request has been logged. Core functions (CRM, calendar, email) remain operational."
)


def _deterministic_router_response(prompt: str) -> str:
    """Intent-aware fallback when all LLM providers fail."""
    prompt_lower = prompt.lower()
    for pattern, intent in _ROUTER_INTENT_PATTERNS:
        if pattern.search(prompt_lower):
            return _ROUTER_INTENT_FALLBACKS[intent]
    return _ROUTER_DEFAULT_FALLBACK


# ─── Circuit Breaker ─────────────────────────────────────────────────────────
# Prevents CPU death spiral when all providers are down.
# After consecutive all-providers-failed results, enforces exponential backoff
# before allowing the next attempt (30s, 60s, 120s, 240s, cap 300s).

_circuit_consecutive_failures: int = 0
_circuit_last_failure_time: float = 0.0
_CIRCUIT_BASE_DELAY: float = 30.0
_CIRCUIT_MAX_DELAY: float = 300.0


def _circuit_check() -> str | None:
    """Return an early-exit message if the circuit breaker is open, else None."""
    global _circuit_consecutive_failures, _circuit_last_failure_time
    if _circuit_consecutive_failures < 2:
        return None
    delay = min(
        _CIRCUIT_BASE_DELAY * (2 ** (_circuit_consecutive_failures - 2)),
        _CIRCUIT_MAX_DELAY,
    )
    elapsed = time.time() - _circuit_last_failure_time
    if elapsed < delay:
        remaining = int(delay - elapsed)
        logger.warning(
            "[Router] Circuit breaker OPEN — %d consecutive failures, retry in %ds",
            _circuit_consecutive_failures,
            remaining,
        )
        return f"[EOS] All providers down — circuit breaker open, retrying in {remaining}s."
    return None


def _circuit_record_failure() -> None:
    global _circuit_consecutive_failures, _circuit_last_failure_time
    _circuit_consecutive_failures += 1
    _circuit_last_failure_time = time.time()
    _record_error(
        "circuit_breaker",
        "all providers failed",
        {
            "consecutive_failures": str(_circuit_consecutive_failures),
        },
    )
    try:
        from state.providers.provider_state import get_system_state

        get_system_state().record_all_providers_failed()
    except Exception:
        pass


def _circuit_record_success() -> None:
    global _circuit_consecutive_failures, _circuit_last_failure_time
    _circuit_consecutive_failures = 0
    _circuit_last_failure_time = 0.0


def _track_provider_result(provider_name: str, success: bool) -> None:
    """Feed per-provider result into global SystemProviderState."""
    if not success:
        _record_error(
            "provider_empty",
            f"{provider_name} returned empty",
            {
                "provider": provider_name,
            },
        )
    try:
        from state.providers.provider_state import get_system_state

        state = get_system_state()
        if success:
            state.record_provider_success(provider_name)
        else:
            state.record_provider_failure(provider_name)
    except Exception as _track_err:
        _record_error(
            "provider_state_tracking",
            _track_err,
            {
                "provider": provider_name,
            },
        )


# ─── RoutingResult ────────────────────────────────────────────────────────────


@dataclass
class RoutingResult:
    """Return type for module-level call_with_fallback()."""

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
    CLAUDE_CLI = "claude_cli"  # persistent tmux Claude Code session (substrate)
    CC_SDK = "cc_sdk"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    CODEX = "codex"
    HERMES = "hermes"
    OPENCODE = "opencode"
    MANUS = "manus"
    # Acquired by Meta Dec 2025 for $2B+
    # Future API access via Meta ecosystem
    # Monitor: developers.facebook.com and manus.im for API updates


class TaskType(Enum):
    # Original types
    CONVERSATION = "conversation"
    ANALYSIS = "analysis"
    WEB_SEARCH = "web_search"
    MARKET_INTEL = "market_intel"
    FAST_RESPONSE = "fast_response"
    LONG_CONTEXT = "long_context"
    AUTONOMOUS = "autonomous"
    MULTIMODAL = "multimodal"
    BROWSER_CONTROL = "browser_control"
    # Agent execution types (aligned with agent_runtime.TaskType)
    SCORE = "score"
    CLASSIFY = "classify"
    ANALYZE = "analyze"
    GENERATE = "generate"
    SUMMARIZE = "summarize"
    # Strategic / CEO types
    STRATEGIC = "strategic"
    CODE = "code"
    RESEARCH = "research"
    SELF_IMPROVE = "self_improve"
    PLAN = "plan"
    COORDINATE = "coordinate"


# ─── CC model map ─────────────────────────────────────────────────────────────
# Maps task type → best Claude model when Anthropic credits are available.
# Boris Cherny: use Opus with thinking for strategic tasks.
# Less steering + better tool use = faster overall.

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


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_id: str
    api_key_env: str
    strengths: list  # list[TaskType]
    cost_per_1k: float  # USD per 1k tokens
    available: bool = False
    base_url: str = ""


# Provider priority for fallback ordering (lower = preferred)
# Default priority — used for analyze/generate/code/strategic tasks
# Claude CLI (persistent tmux session) first for conversational continuity →
# CC SDK (Opus) for quality → Gemini (cheap, fast) → Groq (fast inference)
# → Anthropic (401 until credits restored) → Perplexity (search tasks)
# → Ollama (free local catch-all)
PROVIDER_PRIORITY: dict = {
    ModelProvider.CLAUDE_CLI: 0,
    ModelProvider.CC_SDK: 1,
    ModelProvider.GEMINI: 2,
    ModelProvider.GROQ: 3,
    ModelProvider.ANTHROPIC: 4,
    ModelProvider.PERPLEXITY: 5,
    ModelProvider.OLLAMA: 6,
    ModelProvider.CODEX: 7,
    ModelProvider.HERMES: 8,
    ModelProvider.OPENCODE: 9,
    ModelProvider.MANUS: 10,
}

# Fast-path priority — used for fast_response/conversation tasks
# Claude CLI session first so Discord/pseudo-live keeps a single stateful
# brain → Gemini Flash (fast + cheap) → Groq (ultra-fast) → Anthropic (Haiku)
# → CC SDK reserved for escalation only → Ollama local catch-all
PROVIDER_PRIORITY_FAST: dict = {
    ModelProvider.CLAUDE_CLI: 0,
    ModelProvider.GEMINI: 1,
    ModelProvider.GROQ: 2,
    ModelProvider.ANTHROPIC: 3,
    ModelProvider.CC_SDK: 4,
    ModelProvider.PERPLEXITY: 5,
    ModelProvider.OLLAMA: 6,
    ModelProvider.CODEX: 7,
    ModelProvider.HERMES: 8,
    ModelProvider.OPENCODE: 9,
    ModelProvider.MANUS: 10,
}

# Task types that use the fast-path priority
_FAST_TASK_TYPES = frozenset({"fast_response", "conversation", "score", "classify", "summarize"})

# Token caps for Haiku on cheap tasks (protect $5 budget)
_HAIKU_TOKEN_CAPS: dict[str, int] = {
    "fast_response": 500,
    "conversation": 800,
    "score": 500,
    "classify": 500,
    "summarize": 800,
}

# Escalation threshold — if quality_score below this, retry with cc_sdk
# Lowered from 0.65: Haiku is a fast/cheap model, not a reasoning model.
# Only escalate on actual failures (empty, refusals, ultra-short), not
# on Haiku being Haiku.
_ESCALATION_QUALITY_THRESHOLD = 0.40

# Quality thresholds per provider (0.0–1.0, for model_preferences gating)
PROVIDER_QUALITY: dict = {
    "cc_sdk": 0.85,  # Opus 4.6 via Agent SDK — highest quality
    "anthropic": 0.80,  # Direct Anthropic SDK
    "gemini": 0.65,  # Gemini 2.5 Flash
    "groq": 0.55,  # Llama 3.3 70B
    "perplexity": 0.60,  # Sonar (search-augmented)
    "ollama": 0.35,  # Local qwen2.5:0.5b — emergency fallback only, low quality
    "codex": 0.80,  # GPT-5.5 via Codex CLI — strong coding, adversarial review
    "hermes": 0.70,  # Model-agnostic via Hermes Agent — depends on configured provider
    "opencode": 0.75,  # Multi-provider via OpenCode — depends on configured model
}

MODEL_REGISTRY: dict[str, ModelConfig] = {
    # PRIMARY: Claude for reasoning
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
        strengths=[
            TaskType.CONVERSATION,
            TaskType.ANALYSIS,
            TaskType.LONG_CONTEXT,
        ],
        cost_per_1k=0.003,
    ),
    # PERPLEXITY: Real-time web search
    # Best for world pulse, market intel
    "perplexity-sonar": ModelConfig(
        provider=ModelProvider.PERPLEXITY,
        model_id="sonar-pro",
        api_key_env="PERPLEXITY_API_KEY",
        strengths=[
            TaskType.WEB_SEARCH,
            TaskType.MARKET_INTEL,
        ],
        cost_per_1k=0.001,
        base_url="https://api.perplexity.ai",
    ),
    # GROQ: Ultra-fast inference
    # Already used for STT via groq_whisper
    "groq-llama": ModelConfig(
        provider=ModelProvider.GROQ,
        model_id="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
        strengths=[
            TaskType.FAST_RESPONSE,
            TaskType.CONVERSATION,
        ],
        cost_per_1k=0.00059,
        base_url="https://api.groq.com/openai/v1",
    ),
    # OLLAMA: Local emergency fallback only.
    # Hardware reality: 2 vCPU / 8 GB VPS with no GPU.
    # qwen2.5:0.5b (~400 MB) is the only model that loads fast enough to be useful.
    # Larger models (1.5b/3b/4b/7b) are too slow on CPU-only — multi-minute responses
    # defeat the purpose of a "fallback that responds when clouds are down".
    # Strengths intentionally minimal — Ollama is last-resort, not primary.
    # base_url from env so Docker containers can reach host Ollama via gateway IP.
    "ollama-qwen": ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_id="qwen2.5:0.5b",
        api_key_env="",
        strengths=[
            TaskType.FAST_RESPONSE,
        ],
        cost_per_1k=0.0,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    ),
    # GEMINI: Multimodal
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
    # MANUS: Fully autonomous agent — acquired by Meta Dec 2025 for $2B+
    # API access TBD post-acquisition. Monitor manus.im and developers.facebook.com
    # Available via browser (ManusAgent) even without native API key
    # CLI AGENTS: availability checked by binary presence, not API key
    "codex-agent": ModelConfig(
        provider=ModelProvider.CODEX,
        model_id="gpt-5.5",
        api_key_env="",
        strengths=[TaskType.CODE, TaskType.ANALYZE],
        cost_per_1k=0.0,
    ),
    "hermes-agent": ModelConfig(
        provider=ModelProvider.HERMES,
        model_id="hermes-default",
        api_key_env="",
        strengths=[TaskType.CODE, TaskType.AUTONOMOUS],
        cost_per_1k=0.0,
    ),
    "opencode-agent": ModelConfig(
        provider=ModelProvider.OPENCODE,
        model_id="opencode-default",
        api_key_env="",
        strengths=[TaskType.CODE, TaskType.ANALYZE],
        cost_per_1k=0.0,
    ),
    "manus": ModelConfig(
        provider=ModelProvider.MANUS,
        model_id="manus-agent",
        api_key_env="MANUS_API_KEY",
        strengths=[
            TaskType.AUTONOMOUS,
            TaskType.BROWSER_CONTROL,
        ],
        cost_per_1k=0.0,
        available=False,
        base_url="https://manus.im",
    ),
}


def _estimate_quality_score(output: str, provider: str) -> float:
    """
    Heuristic quality score for a model response.

    Uses response length, structure, and provider baseline to estimate
    whether the output is worth returning or should escalate.
    """
    if not output or not output.strip():
        return 0.0

    base = PROVIDER_QUALITY.get(provider, 0.5)
    length = len(output.strip())

    # Very short responses from weak providers are suspect
    if length < 20:
        return min(base, 0.3)
    if length < 50:
        return min(base, 0.5)

    # Refusal / error patterns
    _refusal = any(
        p in output.lower()
        for p in ["i cannot", "i can't", "i'm sorry", "as an ai", "i don't have"]
    )
    if _refusal:
        return min(base, 0.4)

    return base


def _should_escalate(output: str, provider: str) -> bool:
    """Return True if the response quality is below escalation threshold."""
    score = _estimate_quality_score(output, provider)
    if score < _ESCALATION_QUALITY_THRESHOLD:
        logger.warning(
            "[Router] Quality %.2f < %.2f from %s — escalating to cc_sdk",
            score,
            _ESCALATION_QUALITY_THRESHOLD,
            provider,
        )
        return True
    return False


def _ollama_available() -> bool:
    """Returns True only if Ollama HTTP endpoint responds within 2s."""
    try:
        import requests as _req

        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        resp = _req.get(
            f"{base}/api/tags",
            timeout=2,
        )
        return resp.status_code == 200
    except Exception:
        return False


class ModelRouter:
    def __init__(self, ctx=None) -> None:
        self.ctx = ctx
        self._last_input_tokens: int = 0
        self._last_output_tokens: int = 0
        self._check_availability()

    def _check_availability(self) -> None:
        # cc_sdk available if claude CLI is installed (import succeeded at module level)
        self._cc_sdk_available = query_cc_sync is not None

        from adapters.models.codex_cli import is_available as _codex_avail
        from adapters.models.hermes_cli import is_available as _hermes_avail
        from adapters.models.opencode_cli import is_available as _opencode_avail

        _cli_checks = {
            ModelProvider.OLLAMA: _ollama_available,
            ModelProvider.CODEX: _codex_avail,
            ModelProvider.HERMES: _hermes_avail,
            ModelProvider.OPENCODE: _opencode_avail,
        }

        for config in MODEL_REGISTRY.values():
            if config.provider in _cli_checks:
                config.available = _cli_checks[config.provider]()
            elif not config.api_key_env:
                config.available = False
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
        """
        Select the best available model for the given task type.

        Falls back to any available model if no specialist is found.
        Default priority: Claude first, then by cost.
        """
        # Models that handle this task type
        candidates = [
            c for c in MODEL_REGISTRY.values() if task_type in c.strengths and c.available
        ]

        if not candidates:
            # Fall back to any available model
            candidates = [c for c in MODEL_REGISTRY.values() if c.available]

        if not candidates:
            return None

        if prefer_fast or prefer_cheap:
            candidates.sort(key=lambda x: x.cost_per_1k)
        else:
            # Default: provider priority (Anthropic → Gemini → Groq → Perplexity → Ollama)
            candidates.sort(key=lambda x: PROVIDER_PRIORITY.get(x.provider, 99))

        return candidates[0]

    def call(
        self,
        model_config: ModelConfig,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        """Universal model call — routes to correct API by provider.

        Args:
            images: Optional list of (image_bytes, mime_type) tuples for vision tasks.
                    Only Gemini and Anthropic support images; other providers ignore them.
        """
        self._last_input_tokens = 0
        self._last_output_tokens = 0
        provider = model_config.provider

        if provider == ModelProvider.ANTHROPIC:
            result = self._call_anthropic(model_config, prompt, system, max_tokens, images)
        elif provider == ModelProvider.PERPLEXITY:
            result = self._call_openai_compatible(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.GROQ:
            result = self._call_openai_compatible(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.OLLAMA:
            result = self._call_ollama(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.GEMINI:
            result = self._call_gemini(model_config, prompt, system, max_tokens, images)
        elif provider == ModelProvider.CODEX:
            result = self._call_codex(prompt, system, max_tokens)
        elif provider == ModelProvider.HERMES:
            result = self._call_hermes(prompt, system)
        elif provider == ModelProvider.OPENCODE:
            result = self._call_opencode(prompt, system)
        else:
            logger.warning("[ModelRouter] Unknown provider: %s", provider)
            return ""

        _track_provider_result(provider.value, bool(result))
        return result

    def call_with_fallback(
        self,
        task_type: TaskType,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        """
        Try models in priority order until one returns a non-empty response.

        Use this instead of route() + call() when you need automatic fallback.
        Marks models unavailable after confirmed failures so routing improves
        over the session.
        """
        # Build candidate list for this task type
        candidates = [
            c for c in MODEL_REGISTRY.values() if task_type in c.strengths and c.available
        ]
        if not candidates:
            candidates = [c for c in MODEL_REGISTRY.values() if c.available]

        # If images provided, prefer vision-capable providers
        if images:
            vision_providers = {ModelProvider.GEMINI, ModelProvider.ANTHROPIC}
            vision_candidates = [c for c in candidates if c.provider in vision_providers]
            if vision_candidates:
                candidates = vision_candidates

        candidates.sort(key=lambda x: PROVIDER_PRIORITY.get(x.provider, 99))

        for config in candidates:
            if not config.available:
                continue
            result = self.call(config, prompt, system, max_tokens, images)
            if result:
                return result

        logger.warning("[ModelRouter] All candidates exhausted for %s", task_type.name)
        return ""

    def _call_anthropic(
        self,
        config: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        try:
            import anthropic
            import base64

            client = anthropic.Anthropic(api_key=os.getenv(config.api_key_env))

            # Build content blocks — text + optional images
            if images:
                content: list[dict] = []
                for img_bytes, mime_type in images:
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64.b64encode(img_bytes).decode(),
                            },
                        }
                    )
                content.append({"type": "text", "text": prompt})
                messages = [{"role": "user", "content": content}]
            else:
                messages = [{"role": "user", "content": prompt}]

            kwargs: dict = {
                "model": config.model_id,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            response = client.messages.create(**kwargs)
            if hasattr(response, "usage") and response.usage:
                self._last_input_tokens = getattr(response.usage, "input_tokens", 0)
                self._last_output_tokens = getattr(response.usage, "output_tokens", 0)
            return response.content[0].text
        except Exception as e:
            err_str = str(e)
            _fatal = (
                "credit balance is too low" in err_str
                or "Your credit balance" in err_str
                or "authentication_error" in err_str
                or "invalid x-api-key" in err_str
            )
            _record_error(
                "anthropic",
                e,
                {
                    "model": config.model_id,
                    "fatal": str(_fatal),
                },
            )
            if _fatal:
                logger.warning(
                    "[ModelRouter] Anthropic unavailable — marking all models down: %s",
                    err_str[:120],
                )
                for cfg in MODEL_REGISTRY.values():
                    if cfg.provider == ModelProvider.ANTHROPIC:
                        cfg.available = False
            else:
                logger.warning("[ModelRouter] Anthropic error: %s", e)
            return ""

    def _call_openai_compatible(
        self,
        config: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
    ) -> str:
        """Works for Perplexity, Groq, OpenAI — all OpenAI-compatible APIs."""
        try:
            from openai import OpenAI
        except ImportError:
            return ""
        try:
            client = OpenAI(
                api_key=os.getenv(config.api_key_env),
                base_url=config.base_url or None,
            )
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=config.model_id,
                messages=messages,
                max_tokens=max_tokens,
            )
            if hasattr(response, "usage") and response.usage:
                self._last_input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                self._last_output_tokens = getattr(response.usage, "completion_tokens", 0) or 0
            return response.choices[0].message.content or ""
        except Exception as e:
            _record_error(
                config.provider.value,
                e,
                {
                    "model": config.model_id,
                },
            )
            logger.warning("[ModelRouter] %s error: %s", config.provider.value, e)
            return ""

    def _call_ollama(
        self,
        config: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
    ) -> str:
        try:
            import requests

            # qwen2.5:0.5b on 2-vCPU CPU: keep prompts small, cap output tokens.
            # Anything larger than ~2k input takes >60s on this hardware.
            _sys = system[:1500] if system else ""
            _max_tokens = min(max_tokens, 256)
            payload: dict = {
                "model": config.model_id,
                "prompt": prompt[:2000],
                "stream": False,
                "options": {"num_predict": _max_tokens},
            }
            if _sys:
                payload["system"] = _sys
            start = time.time()
            resp = requests.post(
                f"{config.base_url}/api/generate",
                json=payload,
                timeout=60,
            )
            elapsed = time.time() - start
            if elapsed > 60:
                logger.warning(
                    "[Ollama] Slow response: %.0fs for %s (%d chars)",
                    elapsed,
                    config.model_id,
                    len(resp.text) if resp.status_code == 200 else 0,
                )
            if resp.status_code == 200:
                data = resp.json()
                self._last_input_tokens = data.get("prompt_eval_count", 0) or 0
                self._last_output_tokens = data.get("eval_count", 0) or 0
                return data.get("response", "")
        except Exception as e:
            _record_error(
                "ollama",
                e,
                {
                    "model": config.model_id,
                },
            )
            logger.warning("[ModelRouter] Ollama error: %s", e)
        return ""

    def _call_gemini(
        self,
        config: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        try:
            import base64
            from google import genai  # type: ignore
            from google.genai import types as genai_types  # type: ignore

            client = genai.Client(api_key=os.getenv(config.api_key_env))

            # Build contents — text + optional inline images
            if images:
                parts: list[dict] = []
                for img_bytes, mime_type in images:
                    parts.append(
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(img_bytes).decode(),
                            }
                        }
                    )
                parts.append({"text": prompt})
                contents = parts
            else:
                contents = prompt

            cfg = genai_types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                system_instruction=system or None,
            )
            response = client.models.generate_content(
                model=config.model_id,
                contents=contents,
                config=cfg,
            )
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                self._last_input_tokens = (
                    getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                )
                self._last_output_tokens = (
                    getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                )
            return response.text or ""
        except Exception as e:
            _record_error(
                "gemini",
                e,
                {
                    "model": config.model_id,
                },
            )
            logger.warning("[ModelRouter] Gemini error: %s", e)
        return ""

    def _call_codex(self, prompt: str, system: str, max_tokens: int) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        result = query_codex_sync(full_prompt)
        if result:
            self._last_input_tokens = result.input_tokens
            self._last_output_tokens = result.output_tokens
            return result.output
        return ""

    def _call_hermes(self, prompt: str, system: str) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        result = query_hermes_sync(full_prompt)
        if result:
            return result.output
        return ""

    def _call_opencode(self, prompt: str, system: str) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        result = query_opencode_sync(full_prompt)
        if result:
            return result.output
        return ""

    def get_status(self) -> str:
        lines = ["MODEL REGISTRY:"]
        for model_id, config in MODEL_REGISTRY.items():
            status = "✅" if config.available else "❌"
            lines.append(
                f"  {status} {model_id} ({config.provider.value}) ${config.cost_per_1k}/1k tokens"
            )
        return "\n".join(lines)


# Global singleton
_router: ModelRouter | None = None


def get_router(ctx=None) -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter(ctx)
    return _router


# ─── Module-level API ─────────────────────────────────────────────────────────
# call_with_fallback() is the single entry point for all EOS agent calls.
# Returns RoutingResult with provider, model, latency, and output.
#
# CEO/strategic agents pass agent_type='ceo' or force_opus=True to ensure
# they always use the best available model regardless of economy mode.

# CEO/strategic agents — pattern-based, not name-based.
# Any agent ending in "_ceo" or explicitly strategic gets best-available model.
# No venture-specific names in the substrate.
_CEO_AGENT_KEYWORDS = ("_ceo", "portfolio_advisor", "strategic")


def _claude_cli_backend_enabled() -> bool:
    """Whether to attempt the Claude CLI tmux session as backend #0.

    Default ON. Set EOS_ROUTER_CLAUDE_CLI_ENABLED=0 to disable (e.g. on
    machines without tmux/claude CLI, or when running unit tests that
    should exercise only the provider chain).
    """
    raw = (os.getenv("EOS_ROUTER_CLAUDE_CLI_ENABLED") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def _is_ceo_agent(agent_type: str | None) -> bool:
    """Return True if agent_type matches a CEO/strategic pattern."""
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
    images: list[tuple[bytes, str]] | None = None,
) -> RoutingResult:
    """
    Main routing entry point for all EOS agent calls.

    Task-aware routing:
      fast_response/conversation → Haiku first (fast, cheap)
        escalates to Opus if quality_score < 0.65
      analyze/generate/code/strategic → Opus first (free via Max)
        falls back to Haiku if cc_sdk fails

    CEO/strategic agents always use best available model.

    Args:
        raw_input: The original user message before cognitive loop augmentation.
                   Used by the Claude CLI (tmux) backend which already has full
                   context via CLAUDE.md — sending the augmented prompt would
                   redundantly paste system context into the tmux pane and exceed
                   the 8000-char send limit.
        images: Optional list of (image_bytes, mime_type) tuples for vision tasks.
                Routes to Gemini or Anthropic (vision-capable providers).
                Claude CLI and cc_sdk backends skip images (text-only).
    """
    if isinstance(task_type, TaskType):
        task_type_str = task_type.value
    else:
        task_type_str = task_type

    # Circuit breaker: short-circuit when all providers are known-down
    breaker_msg = _circuit_check()
    if breaker_msg:
        return RoutingResult(
            output=breaker_msg,
            provider="none",
            model="circuit_breaker",
            task_type=task_type_str,
        )

    # CEO/strategic agents override economy mode
    is_ceo = _is_ceo_agent(agent_type) or force_opus
    if is_ceo:
        task_type_str = TaskType.STRATEGIC.value

    # Vision: images present → force multimodal task type (skip CLI/cc_sdk text-only paths)
    if images:
        task_type_str = TaskType.MULTIMODAL.value

    # Determine if this is a fast-path task
    is_fast = task_type_str in _FAST_TASK_TYPES and not is_ceo

    logger.info(
        "[Router] task=%s agent=%s trigger=%s fast=%s",
        task_type_str,
        agent_type,
        trigger_source,
        is_fast,
    )

    router = get_router()
    # Re-check availability on each call (handles credit restoration)
    router._check_availability()

    # ── Map extended task types to router's strength categories ──
    _TASK_MAP: dict[str, str] = {
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
    router_task_str = _TASK_MAP.get(task_type_str, task_type_str)
    try:
        router_task = TaskType(router_task_str)
    except ValueError:
        router_task = TaskType.FAST_RESPONSE

    # ── Select priority table based on task type ──
    priority = PROVIDER_PRIORITY_FAST if is_fast else PROVIDER_PRIORITY

    start = time.time()

    # ── Capability routing: detect if a specialized tool should handle this ──
    try:
        from execution.runtime.capability_router import (
            detect_capability,
            route_capability,
            _LLM_ONLY_CAPABILITIES,
        )

        _cap = detect_capability(prompt, task_type_str, context={"agent_type": agent_type})
        if _cap not in _LLM_ONLY_CAPABILITIES:
            _cap_result = route_capability(
                prompt,
                task_type=task_type_str,
                context={"agent_type": agent_type},
                system=system,
            )
            if _cap_result:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] capability_router handled via %s (%dms)",
                    _cap_result.provider_id,
                    latency_ms,
                )
                return RoutingResult(
                    output=_cap_result.output,
                    provider=_cap_result.provider_id,
                    model=f"cap:{_cap_result.capability}",
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                )
    except Exception as _cap_exc:
        _record_error(
            "capability_router",
            _cap_exc,
            {
                "task_type": task_type_str,
            },
        )
        logger.debug("[Router] capability_router skipped: %s", _cap_exc)

    # ── Backend #0: Claude CLI persistent tmux session ──
    # Shared first backend for all routed calls (fast + heavy paths). This is
    # the router's single seam for "Claude Code CLI first"; if it returns any
    # bounded failure (tmux missing, cli missing, session missing, empty reply,
    # ask exception) we fall through to the existing provider chain unchanged.
    # Never raises — respond_via_claude_session is a safe-degrade adapter.
    cli_enabled = _claude_cli_backend_enabled()
    logger.info(
        "[Router] claude_cli backend gate: enabled=%s priority_index=%s path=%s",
        cli_enabled,
        priority.get(ModelProvider.CLAUDE_CLI, "missing"),
        "fast" if is_fast else "heavy",
    )
    if cli_enabled:
        try:
            from execution.transport.claude_responder import (
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

            # ── Discord Channel Mode Routing v1 override ──
            # If the caller (Discord ingress) has bound a mode context on this
            # thread, use its target/session instead of the env defaults. The
            # shared router is unchanged; only the Claude CLI session name
            # differs between builder vs product modes, which keeps builder
            # and product contexts isolated without forking the pipeline.
            mode_label = None
            try:
                from execution.transport.discord_mode_routing import (
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
            except Exception as _mode_exc:  # noqa: BLE001 — never poison router
                _record_error("mode_context", _mode_exc, {})
                logger.warning("[Router] mode_context lookup failed: %s", _mode_exc)
            # Use raw_input for the tmux session — the CC session already
            # has full context via CLAUDE.md and soul docs. Sending the
            # augmented prompt redundantly pastes system context into the
            # pane and often exceeds the 8000-char send limit.
            cli_text = raw_input if raw_input else prompt
            logger.info(
                "[Router] claude_cli attempt: target=%s session=%s mode=%s raw=%s chars=%d",
                cli_target,
                cli_session,
                mode_label or "none",
                bool(raw_input),
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
                # Estimate tokens from character count (CC sessions don't
                # expose exact token counts — chars/4 is a reasonable proxy)
                est_tokens = max(1, len(reply_text) // 4)
                logger.info(
                    "[Router] claude_cli/%s responded (%dms, ~%d tok, primary)",
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
                "[Router] claude_cli unavailable (reason=%s detail=%s) — falling through",
                cli_res.get("reason"),
                (cli_res.get("detail") or "")[:200],
            )
        except Exception as exc:  # noqa: BLE001 — boundary: never raise
            _record_error(
                "claude_cli",
                exc,
                {
                    "task_type": task_type_str,
                },
            )
            logger.warning("[Router] claude_cli backend error: %s", exc)
    else:
        logger.info("[Router] claude_cli backend disabled via env — skipping")

    if is_fast:
        # ── FAST PATH: Haiku first, escalate to cc_sdk if quality low ──

        # 1. Try Anthropic (Haiku) first
        haiku_cap = _HAIKU_TOKEN_CAPS.get(task_type_str, 800)
        candidates = [
            c
            for c in MODEL_REGISTRY.values()
            if c.provider == ModelProvider.ANTHROPIC and c.available
        ]
        # Prefer Haiku (cheapest Anthropic model)
        candidates.sort(key=lambda x: x.cost_per_1k)

        for config in candidates:
            output = router.call(config, prompt, system or "", haiku_cap, images)
            if output:
                # Check quality — escalate if too low
                if _should_escalate(output, config.provider.value):
                    break  # fall through to cc_sdk escalation
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] %s/%s responded (%dms, fast path)",
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                )
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

        # 2. Escalate to cc_sdk (Opus — no token cap on escalation)
        if router._cc_sdk_available and get_system_state().allow_execution():
            cc_result = query_cc_sync(
                prompt=prompt,
                system=system or "",
                task_type=task_type_str,
                agent_id=agent_type or "eos_default",
                max_budget_usd=0.10,
            )
            if cc_result and cc_result.output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] cc_sdk/%s responded (%dms, escalated)",
                    cc_result.model,
                    latency_ms,
                )
                _stamp_trace("cc_sdk", cc_result.model, latency_ms, "ok_escalated")
                return RoutingResult(
                    output=cc_result.output,
                    provider="cc_sdk",
                    model=cc_result.model,
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                )

        # 3. Fall through to remaining providers (gemini, ollama)
        remaining = [
            c
            for c in MODEL_REGISTRY.values()
            if c.available and c.provider not in (ModelProvider.ANTHROPIC, ModelProvider.CC_SDK)
        ]
        remaining.sort(key=lambda x: priority.get(x.provider, 99))

        for config in remaining:
            output = router.call(config, prompt, system or "", 2000, images)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] %s/%s responded (%dms, fast fallback)",
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                )
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
        # ── HEAVY PATH: cc_sdk (Opus) first, then registry fallback ──

        # 1. Try cc_sdk first (Opus 4.6 via Agent SDK — free via Max)
        if router._cc_sdk_available and get_system_state().allow_execution():
            cc_result = query_cc_sync(
                prompt=prompt,
                system=system or "",
                task_type=task_type_str,
                agent_id=agent_type or "eos_default",
                max_budget_usd=0.10,
            )
            if cc_result and cc_result.output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] cc_sdk/%s responded (%dms)",
                    cc_result.model,
                    latency_ms,
                )
                _stamp_trace("cc_sdk", cc_result.model, latency_ms, "ok")
                return RoutingResult(
                    output=cc_result.output,
                    provider="cc_sdk",
                    model=cc_result.model,
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                )
            logger.info("[Router] cc_sdk failed, falling back to registry providers")

        # 2. Registry-based fallback — strength-matched first, then any available
        strength_matched = [
            c for c in MODEL_REGISTRY.values() if router_task in c.strengths and c.available
        ]
        strength_matched.sort(key=lambda x: priority.get(x.provider, 99))
        _tried_providers: set = set()

        for config in strength_matched:
            if not config.available:
                continue
            _tried_providers.add(config.provider)
            output = router.call(config, prompt, system or "", 2000, images)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] %s/%s responded (%dms)",
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                )
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

        # 3. All strength-matched failed — try remaining available providers
        remaining = [
            c for c in MODEL_REGISTRY.values() if c.available and c.provider not in _tried_providers
        ]
        remaining.sort(key=lambda x: priority.get(x.provider, 99))

        for config in remaining:
            if not config.available:
                continue
            output = router.call(config, prompt, system or "", 2000, images)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] %s/%s responded (%dms, heavy remaining)",
                    config.provider.value,
                    config.model_id,
                    latency_ms,
                )
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
    _circuit_record_failure()
    logger.error(
        "[Router] ALL PROVIDERS FAILED (consecutive: %d)",
        _circuit_consecutive_failures,
    )
    _stamp_trace("none", "none", latency_ms, "all_failed")
    return RoutingResult(
        output=_deterministic_router_response(prompt),
        provider="deterministic",
        model="fallback",
        task_type=task_type_str,
        latency_ms=latency_ms,
    )


def _stamp_trace(provider: str, model: str, latency_ms: int, result: str) -> None:
    """Stamp execution trace with router outcome. Never raises."""
    if "fail" not in result:
        _circuit_record_success()
    try:
        from execution.transport.execution_trace import get_current_trace, finalize_trace

        trace = get_current_trace()
        if trace is not None:
            finalize_trace(
                trace,
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                result=result,
            )
    except Exception as _trace_err:
        _record_error(
            "stamp_trace",
            _trace_err,
            {
                "provider": provider,
                "model": model,
            },
        )


def adversarial_code_review(
    code_or_plan: str,
    context: str | None = None,
) -> str:
    """
    Adversarial code review via Codex CLI.

    Pattern: CC writes → Codex reviews adversarially → CC synthesizes.
    Falls back to returning input unchanged if Codex is unavailable.
    """
    from adapters.models.codex_cli import is_available as codex_available

    if not codex_available():
        logger.info("[Router] adversarial_code_review: Codex CLI not available, returning input")
        return code_or_plan

    review_prompt = (
        "Review the following code/plan for bugs, security issues, edge cases, "
        "and design problems. Be adversarial — assume something is wrong and find it.\n\n"
    )
    if context:
        review_prompt += f"Context: {context}\n\n"
    review_prompt += f"```\n{code_or_plan}\n```"

    result = query_codex_sync(review_prompt, sandbox="read-only", timeout=90)
    if result and result.output:
        logger.info("[Router] adversarial_code_review: Codex returned %d chars", len(result.output))
        return result.output

    logger.info("[Router] adversarial_code_review: Codex returned empty, returning input")
    return code_or_plan
