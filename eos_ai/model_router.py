"""
ModelRouter — standalone multi-model router for EOS.

Provides task-type-aware model selection and universal call dispatch
across Anthropic, Perplexity, Groq, Gemini, and Ollama.

Complements ModelPreferences (which handles business-context routing).
Used directly by WorldPulse and other modules that need a simple
"give me the best model for this task" API.

Usage:
    from eos_ai.model_router import get_router, TaskType

    router = get_router()
    print(router.get_status())

    model = router.route(TaskType.MARKET_INTEL)
    if model:
        result = router.call(model, prompt='What is trending in AI?')
        print(result)
"""

import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from eos_ai.cc_sdk import query_cc_sync, CCResult

# Load .env so GEMINI_API_KEY is available when model_router is used standalone
# (agent_runtime does this too — safe to call twice, dotenv is idempotent)
try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

logger = logging.getLogger(__name__)


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
    CC_SDK = "cc_sdk"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    GEMINI = "gemini"
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
# CC SDK (Opus) for quality → Gemini (cheap, fast) → Groq (fast inference)
# → Anthropic (401 until credits restored) → Perplexity (search tasks)
# → Ollama (free local catch-all)
PROVIDER_PRIORITY: dict = {
    ModelProvider.CC_SDK: 0,
    ModelProvider.GEMINI: 1,
    ModelProvider.GROQ: 2,
    ModelProvider.ANTHROPIC: 3,
    ModelProvider.PERPLEXITY: 4,
    ModelProvider.OLLAMA: 5,
    ModelProvider.MANUS: 6,
}

# Fast-path priority — used for fast_response/conversation tasks
# Gemini Flash first (fast + cheap) → Groq (ultra-fast) → Anthropic (Haiku)
# → CC SDK reserved for escalation only → Ollama local catch-all
PROVIDER_PRIORITY_FAST: dict = {
    ModelProvider.GEMINI: 0,
    ModelProvider.GROQ: 1,
    ModelProvider.ANTHROPIC: 2,
    ModelProvider.CC_SDK: 3,
    ModelProvider.PERPLEXITY: 4,
    ModelProvider.OLLAMA: 5,
    ModelProvider.MANUS: 6,
}

# Task types that use the fast-path priority
_FAST_TASK_TYPES = frozenset(
    {"fast_response", "conversation", "score", "classify", "summarize"}
)

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
    "ollama": 0.45,  # Local gemma3:4b — significant upgrade from qwen2.5:0.5b
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
    # OLLAMA: Local fallback
    # gemma3:4b — 3.3 GiB. Fits with os-bot stopped (5.2 GiB available).
    # base_url from env so Docker containers can reach host Ollama via gateway IP.
    "ollama-gemma": ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_id="gemma3:4b",
        api_key_env="",
        strengths=[
            TaskType.FAST_RESPONSE,
            TaskType.CONVERSATION,
            TaskType.ANALYSIS,
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
    "manus": ModelConfig(
        provider=ModelProvider.MANUS,
        model_id="manus-agent",
        api_key_env="MANUS_API_KEY",
        strengths=[
            TaskType.AUTONOMOUS,
            TaskType.BROWSER_CONTROL,
        ],
        cost_per_1k=0.0,
        available=True,
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
        for config in MODEL_REGISTRY.values():
            if not config.api_key_env:
                # Local model (Ollama) — check if actually running
                config.available = (
                    config.provider == ModelProvider.OLLAMA and _ollama_available()
                )
            elif config.provider == ModelProvider.MANUS:
                # Manus accessible via browser even without native API key
                config.available = True
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
            c
            for c in MODEL_REGISTRY.values()
            if task_type in c.strengths and c.available
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
    ) -> str:
        """Universal model call — routes to correct API by provider."""
        self._last_input_tokens = 0
        self._last_output_tokens = 0
        provider = model_config.provider

        if provider == ModelProvider.ANTHROPIC:
            return self._call_anthropic(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.PERPLEXITY:
            return self._call_openai_compatible(
                model_config, prompt, system, max_tokens
            )
        elif provider == ModelProvider.GROQ:
            return self._call_openai_compatible(
                model_config, prompt, system, max_tokens
            )
        elif provider == ModelProvider.OLLAMA:
            return self._call_ollama(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.GEMINI:
            return self._call_gemini(model_config, prompt, system, max_tokens)
        else:
            print(f"[ModelRouter] Unknown provider: {provider}")
            return ""

    def call_with_fallback(
        self,
        task_type: TaskType,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
    ) -> str:
        """
        Try models in priority order until one returns a non-empty response.

        Use this instead of route() + call() when you need automatic fallback.
        Marks models unavailable after confirmed failures so routing improves
        over the session.
        """
        # Build candidate list for this task type
        candidates = [
            c
            for c in MODEL_REGISTRY.values()
            if task_type in c.strengths and c.available
        ]
        if not candidates:
            candidates = [c for c in MODEL_REGISTRY.values() if c.available]

        candidates.sort(key=lambda x: PROVIDER_PRIORITY.get(x.provider, 99))

        for config in candidates:
            if not config.available:
                continue
            result = self.call(config, prompt, system, max_tokens)
            if result:
                return result
            # Call returned '' — provider may have just marked itself unavailable
            # Loop continues to next candidate automatically

        print(f"[ModelRouter] All candidates exhausted for {task_type.name}")
        return ""

    def _call_anthropic(
        self,
        config: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
    ) -> str:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.getenv(config.api_key_env))
            kwargs: dict = {
                "model": config.model_id,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
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
            if (
                "credit balance is too low" in err_str
                or "Your credit balance" in err_str
            ):
                # All Anthropic models share the same account — mark them all unavailable
                print(
                    "[ModelRouter] Anthropic credits depleted — marking all Anthropic models unavailable"
                )
                for cfg in MODEL_REGISTRY.values():
                    if cfg.provider == ModelProvider.ANTHROPIC:
                        cfg.available = False
            else:
                print(f"[ModelRouter] Anthropic error: {e}")
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
            print(f"[ModelRouter] {config.provider.value} error: {e}")
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

            # gemma3:4b handles ~8k context comfortably
            _sys = system[:6000] if system else ""
            payload: dict = {
                "model": config.model_id,
                "prompt": prompt[:8000],
                "stream": False,
                "options": {"num_predict": max_tokens},
            }
            if _sys:
                payload["system"] = _sys
            start = time.time()
            resp = requests.post(
                f"{config.base_url}/api/generate",
                json=payload,
                timeout=300,
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
            print(f"[ModelRouter] Ollama error: {e}")
        return ""

    def _call_gemini(
        self,
        config: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
    ) -> str:
        try:
            from google import genai  # type: ignore
            from google.genai import types as genai_types  # type: ignore

            client = genai.Client(api_key=os.getenv(config.api_key_env))
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
                self._last_input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                self._last_output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            return response.text or ""
        except Exception as e:
            print(f"[ModelRouter] Gemini error: {e}")
        return ""

    def get_status(self) -> str:
        lines = ["MODEL REGISTRY:"]
        for model_id, config in MODEL_REGISTRY.items():
            status = "✅" if config.available else "❌"
            lines.append(
                f"  {status} {model_id} "
                f"({config.provider.value}) "
                f"${config.cost_per_1k}/1k tokens"
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
) -> RoutingResult:
    """
    Main routing entry point for all EOS agent calls.

    Task-aware routing:
      fast_response/conversation → Haiku first (fast, cheap)
        escalates to Opus if quality_score < 0.65
      analyze/generate/code/strategic → Opus first (free via Max)
        falls back to Haiku if cc_sdk fails

    CEO/strategic agents always use best available model.
    """
    if isinstance(task_type, TaskType):
        task_type_str = task_type.value
    else:
        task_type_str = task_type

    # CEO/strategic agents override economy mode
    is_ceo = _is_ceo_agent(agent_type) or force_opus
    if is_ceo:
        task_type_str = TaskType.STRATEGIC.value

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
            output = router.call(config, prompt, system or "", haiku_cap)
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
        if router._cc_sdk_available:
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
            if c.available
            and c.provider not in (ModelProvider.ANTHROPIC, ModelProvider.CC_SDK)
        ]
        remaining.sort(key=lambda x: priority.get(x.provider, 99))

        for config in remaining:
            output = router.call(config, prompt, system or "", 2000)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] %s/%s responded (%dms, fast fallback)",
                    config.provider.value,
                    config.model_id,
                    latency_ms,
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
        if router._cc_sdk_available:
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
                return RoutingResult(
                    output=cc_result.output,
                    provider="cc_sdk",
                    model=cc_result.model,
                    task_type=task_type_str,
                    latency_ms=latency_ms,
                )
            logger.info("[Router] cc_sdk failed, falling back to registry providers")

        # 2. Registry-based fallback (Haiku → Gemini → Ollama)
        candidates = [
            c
            for c in MODEL_REGISTRY.values()
            if router_task in c.strengths and c.available
        ]
        if not candidates:
            candidates = [c for c in MODEL_REGISTRY.values() if c.available]
        candidates.sort(key=lambda x: priority.get(x.provider, 99))

        for config in candidates:
            if not config.available:
                continue
            output = router.call(config, prompt, system or "", 2000)
            if output:
                latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "[Router] %s/%s responded (%dms)",
                    config.provider.value,
                    config.model_id,
                    latency_ms,
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
    return RoutingResult(
        output=(
            "[EOS] All intelligence providers unavailable. "
            "Check API keys and network connectivity."
        ),
        provider="none",
        model="none",
        task_type=task_type_str,
        latency_ms=latency_ms,
    )


def adversarial_code_review(
    code_or_plan: str,
    context: str | None = None,
) -> str:
    """
    Adversarial review stub.

    Full pattern (when Codex is available):
      CC writes → Codex reviews adversarially → CC synthesizes

    Currently: Codex subprocess is unstable. Returns input unchanged.
    Restore when Codex exec is stable or Anthropic credits available.
    """
    logger.info("[Router] adversarial_code_review: Codex unavailable, returning input")
    return code_or_plan
