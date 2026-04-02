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

# Load .env so GEMINI_API_KEY is available when model_router is used standalone
# (agent_runtime does this too — safe to call twice, dotenv is idempotent)
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).parent / '.env')
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
    cost_usd: float = 0.0
    latency_ms: int = 0


# ─── Providers ────────────────────────────────────────────────────────────────

class ModelProvider(Enum):
    ANTHROPIC  = 'anthropic'
    PERPLEXITY = 'perplexity'
    OPENAI     = 'openai'
    GROQ       = 'groq'
    OLLAMA     = 'ollama'
    GEMINI     = 'gemini'
    MANUS      = 'manus'
    # Acquired by Meta Dec 2025 for $2B+
    # Future API access via Meta ecosystem
    # Monitor: developers.facebook.com and manus.im for API updates


class TaskType(Enum):
    # Original types
    CONVERSATION    = 'conversation'
    ANALYSIS        = 'analysis'
    WEB_SEARCH      = 'web_search'
    MARKET_INTEL    = 'market_intel'
    FAST_RESPONSE   = 'fast_response'
    LONG_CONTEXT    = 'long_context'
    AUTONOMOUS      = 'autonomous'
    MULTIMODAL      = 'multimodal'
    BROWSER_CONTROL = 'browser_control'
    # Agent execution types (aligned with agent_runtime.TaskType)
    SCORE           = 'score'
    CLASSIFY        = 'classify'
    ANALYZE         = 'analyze'
    GENERATE        = 'generate'
    SUMMARIZE       = 'summarize'
    # Strategic / CEO types
    STRATEGIC       = 'strategic'
    CODE            = 'code'
    RESEARCH        = 'research'
    SELF_IMPROVE    = 'self_improve'
    PLAN            = 'plan'
    COORDINATE      = 'coordinate'


# ─── CC model map ─────────────────────────────────────────────────────────────
# Maps task type → best Claude model when Anthropic credits are available.
# Boris Cherny: use Opus with thinking for strategic tasks.
# Less steering + better tool use = faster overall.

CC_MODEL_MAP: dict[str, str] = {
    TaskType.STRATEGIC.value:    'claude-opus-4-6',
    TaskType.CODE.value:         'claude-opus-4-6',
    TaskType.SELF_IMPROVE.value: 'claude-opus-4-6',
    TaskType.PLAN.value:         'claude-opus-4-6',
    TaskType.ANALYZE.value:      'claude-sonnet-4-6',
    TaskType.ANALYSIS.value:     'claude-sonnet-4-6',
    TaskType.GENERATE.value:     'claude-sonnet-4-6',
    TaskType.RESEARCH.value:     'claude-sonnet-4-6',
    TaskType.COORDINATE.value:   'claude-sonnet-4-6',
    TaskType.LONG_CONTEXT.value: 'claude-sonnet-4-6',
    TaskType.CONVERSATION.value: 'claude-sonnet-4-6',
    TaskType.SCORE.value:        'claude-haiku-4-5-20251001',
    TaskType.CLASSIFY.value:     'claude-haiku-4-5-20251001',
    TaskType.SUMMARIZE.value:    'claude-haiku-4-5-20251001',
    TaskType.FAST_RESPONSE.value: 'claude-haiku-4-5-20251001',
    TaskType.MARKET_INTEL.value: 'claude-sonnet-4-6',
    TaskType.WEB_SEARCH.value:   'claude-sonnet-4-6',
    TaskType.AUTONOMOUS.value:   'claude-opus-4-6',
}


@dataclass
class ModelConfig:
    provider:     ModelProvider
    model_id:     str
    api_key_env:  str
    strengths:    list  # list[TaskType]
    cost_per_1k:  float  # USD per 1k tokens
    available:    bool = False
    base_url:     str = ''


# Provider priority for fallback ordering (lower = preferred)
PROVIDER_PRIORITY: dict = {
    ModelProvider.ANTHROPIC:  0,
    ModelProvider.GEMINI:     1,
    ModelProvider.GROQ:       2,
    ModelProvider.PERPLEXITY: 3,
    ModelProvider.OLLAMA:     4,
    ModelProvider.MANUS:      5,
}

MODEL_REGISTRY: dict[str, ModelConfig] = {

    # PRIMARY: Claude for reasoning
    'claude-haiku': ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id='claude-haiku-4-5-20251001',
        api_key_env='ANTHROPIC_API_KEY',
        strengths=[
            TaskType.CONVERSATION,
            TaskType.ANALYSIS,
            TaskType.FAST_RESPONSE,
        ],
        cost_per_1k=0.00025,
    ),

    'claude-sonnet': ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id='claude-sonnet-4-6',
        api_key_env='ANTHROPIC_API_KEY',
        strengths=[
            TaskType.CONVERSATION,
            TaskType.ANALYSIS,
            TaskType.LONG_CONTEXT,
        ],
        cost_per_1k=0.003,
    ),

    # PERPLEXITY: Real-time web search
    # Best for world pulse, market intel
    'perplexity-sonar': ModelConfig(
        provider=ModelProvider.PERPLEXITY,
        model_id='llama-3.1-sonar-large-128k-online',
        api_key_env='PERPLEXITY_API_KEY',
        strengths=[
            TaskType.WEB_SEARCH,
            TaskType.MARKET_INTEL,
        ],
        cost_per_1k=0.001,
        base_url='https://api.perplexity.ai',
    ),

    # GROQ: Ultra-fast inference
    # Already used for STT via groq_whisper
    'groq-llama': ModelConfig(
        provider=ModelProvider.GROQ,
        model_id='llama-3.3-70b-versatile',
        api_key_env='GROQ_API_KEY',
        strengths=[
            TaskType.FAST_RESPONSE,
            TaskType.CONVERSATION,
        ],
        cost_per_1k=0.00059,
        base_url='https://api.groq.com/openai/v1',
    ),

    # OLLAMA: Local fallback
    'ollama-qwen': ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_id='qwen2.5:3b',
        api_key_env='',
        strengths=[
            TaskType.FAST_RESPONSE,
        ],
        cost_per_1k=0.0,
        base_url='http://localhost:11434',
    ),

    # GEMINI: Multimodal
    'gemini-pro': ModelConfig(
        provider=ModelProvider.GEMINI,
        model_id='gemini-2.5-flash',
        api_key_env='GEMINI_API_KEY',
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
    'manus': ModelConfig(
        provider=ModelProvider.MANUS,
        model_id='manus-agent',
        api_key_env='MANUS_API_KEY',
        strengths=[
            TaskType.AUTONOMOUS,
            TaskType.BROWSER_CONTROL,
        ],
        cost_per_1k=0.0,
        available=True,
        base_url='https://manus.im',
    ),
}


def _ollama_available() -> bool:
    """Returns True only if Ollama HTTP endpoint responds within 2s."""
    try:
        import requests as _req
        resp = _req.get(
            'http://localhost:11434/api/tags',
            timeout=2,
        )
        return resp.status_code == 200
    except Exception:
        return False


class ModelRouter:

    def __init__(self, ctx=None) -> None:
        self.ctx = ctx
        self._check_availability()

    def _check_availability(self) -> None:
        for config in MODEL_REGISTRY.values():
            if not config.api_key_env:
                # Local model (Ollama) — check if actually running
                config.available = (
                    config.provider == ModelProvider.OLLAMA
                    and _ollama_available()
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
            c for c in MODEL_REGISTRY.values()
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
        system: str = '',
        max_tokens: int = 1000,
    ) -> str:
        """Universal model call — routes to correct API by provider."""
        provider = model_config.provider

        if provider == ModelProvider.ANTHROPIC:
            return self._call_anthropic(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.PERPLEXITY:
            return self._call_openai_compatible(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.GROQ:
            return self._call_openai_compatible(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.OLLAMA:
            return self._call_ollama(model_config, prompt, system, max_tokens)
        elif provider == ModelProvider.GEMINI:
            return self._call_gemini(model_config, prompt, system, max_tokens)
        else:
            print(f'[ModelRouter] Unknown provider: {provider}')
            return ''

    def call_with_fallback(
        self,
        task_type: TaskType,
        prompt: str,
        system: str = '',
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
            c for c in MODEL_REGISTRY.values()
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

        print(f'[ModelRouter] All candidates exhausted for {task_type.name}')
        return ''

    def _call_anthropic(
        self, config: ModelConfig, prompt: str, system: str, max_tokens: int,
    ) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv(config.api_key_env))
            kwargs: dict = {
                'model': config.model_id,
                'max_tokens': max_tokens,
                'messages': [{'role': 'user', 'content': prompt}],
            }
            if system:
                kwargs['system'] = system
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            err_str = str(e)
            if 'credit balance is too low' in err_str or 'Your credit balance' in err_str:
                # All Anthropic models share the same account — mark them all unavailable
                print('[ModelRouter] Anthropic credits depleted — marking all Anthropic models unavailable')
                for cfg in MODEL_REGISTRY.values():
                    if cfg.provider == ModelProvider.ANTHROPIC:
                        cfg.available = False
            else:
                print(f'[ModelRouter] Anthropic error: {e}')
            return ''

    def _call_openai_compatible(
        self, config: ModelConfig, prompt: str, system: str, max_tokens: int,
    ) -> str:
        """Works for Perplexity, Groq, OpenAI — all OpenAI-compatible APIs."""
        try:
            from openai import OpenAI
        except ImportError:
            return ''
        try:
            client = OpenAI(
                api_key=os.getenv(config.api_key_env),
                base_url=config.base_url or None,
            )
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': prompt})
            response = client.chat.completions.create(
                model=config.model_id,
                messages=messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ''
        except Exception as e:
            print(f'[ModelRouter] {config.provider.value} error: {e}')
            return ''

    def _call_ollama(
        self, config: ModelConfig, prompt: str, system: str, max_tokens: int,
    ) -> str:
        try:
            import requests
            payload: dict = {
                'model': config.model_id,
                'prompt': prompt,
                'stream': False,
                'options': {'num_predict': max_tokens},
            }
            if system:
                payload['system'] = system
            resp = requests.post(
                f'{config.base_url}/api/generate',
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json().get('response', '')
        except Exception as e:
            print(f'[ModelRouter] Ollama error: {e}')
        return ''

    def _call_gemini(
        self, config: ModelConfig, prompt: str, system: str, max_tokens: int,
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
            return response.text or ''
        except Exception as e:
            print(f'[ModelRouter] Gemini error: {e}')
        return ''

    def get_status(self) -> str:
        lines = ['MODEL REGISTRY:']
        for model_id, config in MODEL_REGISTRY.items():
            status = '✅' if config.available else '❌'
            lines.append(
                f'  {status} {model_id} '
                f'({config.provider.value}) '
                f'${config.cost_per_1k}/1k tokens'
            )
        return '\n'.join(lines)


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

_CEO_AGENT_TYPES = frozenset({
    'ceo', 'lyfe_institute_ceo', 'empyrean_ceo',
    'personal_brand_ceo', 'portfolio_advisor',
})


def call_with_fallback(
    prompt: str,
    system: str | None = None,
    task_type: 'TaskType | str' = 'fast_response',
    trigger_source: str = 'conversational',
    agent_type: str | None = None,
    force_opus: bool = False,
) -> RoutingResult:
    """
    Main routing entry point for all EOS agent calls.

    Quality-ranked fallback chain (current — Anthropic credits depleted):
    1. Gemini 2.5 Flash  (gemini-pro in registry)
    2. Ollama qwen2.5:3b (local, always available)

    When Anthropic credits are restored, priority becomes:
    1. Anthropic (model per CC_MODEL_MAP)
    2. Gemini 2.5 Flash
    3. Ollama

    CEO/strategic agents always use best available model.
    """
    if isinstance(task_type, TaskType):
        task_type_str = task_type.value
    else:
        task_type_str = task_type

    # CEO/strategic agents override economy mode
    if agent_type in _CEO_AGENT_TYPES or force_opus:
        task_type_str = TaskType.STRATEGIC.value

    logger.info(
        '[Router] task=%s agent=%s trigger=%s',
        task_type_str, agent_type, trigger_source,
    )

    router = get_router()
    # Re-check availability on each call (handles credit restoration)
    router._check_availability()

    # Map extended task types to router's strength categories
    _TASK_MAP: dict[str, str] = {
        'strategic':    'analysis',
        'code':         'analysis',
        'research':     'web_search',
        'self_improve': 'analysis',
        'plan':         'analysis',
        'coordinate':   'conversation',
        'score':        'fast_response',
        'classify':     'fast_response',
        'analyze':      'analysis',
        'generate':     'conversation',
        'summarize':    'fast_response',
    }
    router_task_str = _TASK_MAP.get(task_type_str, task_type_str)
    try:
        router_task = TaskType(router_task_str)
    except ValueError:
        router_task = TaskType.FAST_RESPONSE

    # Build ordered candidate list
    candidates = [
        c for c in MODEL_REGISTRY.values()
        if router_task in c.strengths and c.available
    ]
    if not candidates:
        candidates = [c for c in MODEL_REGISTRY.values() if c.available]
    candidates.sort(key=lambda x: PROVIDER_PRIORITY.get(x.provider, 99))

    start = time.time()

    for config in candidates:
        if not config.available:
            continue
        output = router.call(config, prompt, system or '', 2000)
        if output:
            latency_ms = int((time.time() - start) * 1000)
            logger.info(
                '[Router] %s/%s responded (%dms)',
                config.provider.value, config.model_id, latency_ms,
            )
            return RoutingResult(
                output=output,
                provider=config.provider.value,
                model=config.model_id,
                task_type=task_type_str,
                latency_ms=latency_ms,
            )

    latency_ms = int((time.time() - start) * 1000)
    logger.error('[Router] ALL PROVIDERS FAILED')
    return RoutingResult(
        output=(
            '[EOS] All intelligence providers unavailable. '
            'Check API keys and network connectivity.'
        ),
        provider='none',
        model='none',
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
    logger.info('[Router] adversarial_code_review: Codex unavailable, returning input')
    return code_or_plan
