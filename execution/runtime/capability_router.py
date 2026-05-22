"""
capability_router — Intent-driven tool selection for EOS.

Routes tasks to the best available tool/agent/service based on what the
task actually requires, not just which LLM should think about it.

Every capability has a ranked provider chain. The system detects intent
from prompt context and routes to the best provider, with automatic
fallback. If no specialized tool applies, falls through to the existing
LLM routing in model_router.call_with_fallback().

Principle: no redundancy. Each tool earns its slot by being THE BEST
at one specific capability. Fallback chains exist for resilience only.

Usage:
    from execution.runtime.capability_router import route_capability

    result = route_capability("review the auth module for security issues")
    # → automatically routes to codex review (best at adversarial review)
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ─── Capability Enum ───────────────────────────────────────────────────────
# Every discrete JOB the system can perform. Not LLM task types — actual work.


class Capability(Enum):
    CODE_REVIEW = "code_review"
    CODE_WRITE = "code_write"
    CODE_EXECUTE = "code_execute"

    WEB_SCRAPE = "web_scrape"
    WEB_SEARCH = "web_search"
    WEB_RESEARCH = "web_research"
    BROWSER_AUTOMATE = "browser_automate"

    CONTENT_WRITE = "content_write"
    DESIGN_TEMPLATE = "design_template"
    IMAGE_EDIT = "image_edit"
    VECTOR_DESIGN = "vector_design"
    VIDEO_GENERATE = "video_generate"
    VIDEO_EDIT = "video_edit"

    DATA_QUERY = "data_query"
    SOCIAL_SCRAPE = "social_scrape"
    TRANSCRIBE = "transcribe"

    EMAIL_SEND = "email_send"
    SOCIAL_POST = "social_post"
    MESSAGE_SEND = "message_send"

    PAYMENT_PROCESS = "payment_process"
    CALENDAR_MANAGE = "calendar_manage"
    DOCUMENT_MANAGE = "document_manage"

    SHELL_EXECUTE = "shell_execute"
    FILE_OPERATE = "file_operate"
    DEPLOY = "deploy"

    AUTONOMOUS_TASK = "autonomous_task"

    # LLM-only (no specialized tool — falls through to model_router)
    REASON = "reason"
    FAST_RESPOND = "fast_respond"


# Capabilities that don't need specialized tools — just LLM thinking
_LLM_ONLY_CAPABILITIES = frozenset({Capability.REASON, Capability.FAST_RESPOND})


# ─── Provider Entry ────────────────────────────────────────────────────────


@dataclass
class ProviderEntry:
    """A single provider in a capability's fallback chain."""

    provider_id: str
    is_available: Callable[[], bool]
    invoke: Callable[..., Any]
    priority: int = 0


@dataclass
class CapabilityResult:
    """Return type for capability routing."""

    output: str
    provider_id: str
    capability: str
    latency_ms: int = 0
    metadata: dict = field(default_factory=dict)


# ─── Provider State Tracking ──────────────────────────────────────────────


def _track(provider_id: str, success: bool) -> None:
    try:
        from state.providers.provider_state import get_system_state
        state = get_system_state()
        if success:
            state.record_provider_success(provider_id)
        else:
            state.record_provider_failure(provider_id)
    except Exception:
        pass


# ─── Lazy Provider Loaders ────────────────────────────────────────────────
# Deferred imports to avoid circular dependencies and import-time failures.
# Each returns (is_available_fn, invoke_fn).


def _codex_review_provider() -> ProviderEntry:
    from adapters.model_adapters.codex_cli import is_available, review_codex_sync
    return ProviderEntry(
        provider_id="codex_review",
        is_available=is_available,
        invoke=lambda prompt, **kw: review_codex_sync(
            uncommitted=True,
            cwd=kw.get("cwd"),
            timeout=kw.get("timeout", 90),
        ),
        priority=0,
    )


def _codex_exec_provider() -> ProviderEntry:
    from adapters.model_adapters.codex_cli import is_available, query_codex_sync
    return ProviderEntry(
        provider_id="codex_exec",
        is_available=is_available,
        invoke=lambda prompt, **kw: query_codex_sync(prompt, timeout=kw.get("timeout", 120)),
        priority=1,
    )


def _cc_sdk_provider() -> ProviderEntry:
    from adapters.model_adapters.cc_sdk import query_cc_sync

    def _available() -> bool:
        return query_cc_sync is not None

    return ProviderEntry(
        provider_id="cc_sdk",
        is_available=_available,
        invoke=lambda prompt, **kw: query_cc_sync(
            prompt,
            task_type=kw.get("task_type", "analyze"),
            agent_id=kw.get("agent_id", "capability_router"),
        ),
        priority=1,
    )


def _hermes_provider() -> ProviderEntry:
    from adapters.model_adapters.hermes_cli import is_available, query_hermes_sync
    return ProviderEntry(
        provider_id="hermes",
        is_available=is_available,
        invoke=lambda prompt, **kw: query_hermes_sync(prompt, timeout=kw.get("timeout", 120)),
        priority=2,
    )


def _opencode_provider() -> ProviderEntry:
    from adapters.model_adapters.opencode_cli import is_available, query_opencode_sync
    return ProviderEntry(
        provider_id="opencode",
        is_available=is_available,
        invoke=lambda prompt, **kw: query_opencode_sync(prompt, timeout=kw.get("timeout", 120)),
        priority=2,
    )


def _perplexity_provider() -> ProviderEntry:
    import os

    def _available() -> bool:
        return bool(os.environ.get("PERPLEXITY_API_KEY"))

    def _invoke(prompt: str, **kw: Any) -> CapabilityResult | None:
        from execution.runtime.model_router import get_router, ModelProvider, MODEL_REGISTRY
        router = get_router()
        configs = [c for c in MODEL_REGISTRY.values() if c.provider == ModelProvider.PERPLEXITY and c.available]
        if not configs:
            return None
        output = router.call(configs[0], prompt, kw.get("system", ""), 2000)
        if output:
            return CapabilityResult(output=output, provider_id="perplexity", capability="web_research")
        return None

    return ProviderEntry(
        provider_id="perplexity",
        is_available=_available,
        invoke=_invoke,
        priority=0,
    )


def _gemini_provider() -> ProviderEntry:
    import os

    def _available() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))

    def _invoke(prompt: str, **kw: Any) -> CapabilityResult | None:
        from execution.runtime.model_router import get_router, ModelProvider, MODEL_REGISTRY
        router = get_router()
        configs = [c for c in MODEL_REGISTRY.values() if c.provider == ModelProvider.GEMINI and c.available]
        if not configs:
            return None
        output = router.call(configs[0], prompt, kw.get("system", ""), 2000, kw.get("images"))
        if output:
            return CapabilityResult(output=output, provider_id="gemini", capability=kw.get("cap", "reason"))
        return None

    return ProviderEntry(
        provider_id="gemini",
        is_available=_available,
        invoke=_invoke,
        priority=1,
    )


# ─── Capability Chains ────────────────────────────────────────────────────
# Each capability maps to an ordered list of providers.
# Built lazily on first access to avoid import-time side effects.

_chains_cache: dict[Capability, list[ProviderEntry]] | None = None


def _build_chains() -> dict[Capability, list[ProviderEntry]]:
    return {
        # ── Code ──
        Capability.CODE_REVIEW: [
            _codex_review_provider(),
            _cc_sdk_provider(),
            _opencode_provider(),
        ],
        Capability.CODE_WRITE: [
            _cc_sdk_provider(),
            _codex_exec_provider(),
            _opencode_provider(),
        ],
        Capability.CODE_EXECUTE: [
            _cc_sdk_provider(),
            _codex_exec_provider(),
        ],

        # ── Web ──
        Capability.WEB_RESEARCH: [
            _perplexity_provider(),
            _hermes_provider(),
        ],

        # ── Autonomous ──
        Capability.AUTONOMOUS_TASK: [
            _hermes_provider(),
            _cc_sdk_provider(),
            _opencode_provider(),
        ],
    }


def _get_chains() -> dict[Capability, list[ProviderEntry]]:
    global _chains_cache
    if _chains_cache is None:
        _chains_cache = _build_chains()
    return _chains_cache


# ─── Intent Detection ─────────────────────────────────────────────────────
# Pattern matching rules evaluated in order. First match wins.
# Each rule: (compiled_regex, Capability)

_INTENT_PATTERNS: list[tuple[re.Pattern, Capability]] = [
    # Code review — adversarial analysis, bug hunting, security audit
    (re.compile(
        r"review\s+(this\s+)?(code|changes|diff|pr|pull\s*request|commit)"
        r"|check\s+(this\s+)?(code|changes)\s+(before|for)"
        r"|find\s+(bugs|issues|vulnerabilities|security)"
        r"|code\s+review"
        r"|security\s+(audit|review|scan)"
        r"|audit\s+(this|the)\s+(code|module|function)",
        re.IGNORECASE,
    ), Capability.CODE_REVIEW),

    # Code write — implementing, writing, building code
    (re.compile(
        r"(write|implement|build|create|add)\s+(a\s+|the\s+|this\s+)?(function|method|class|module|endpoint|api|component|feature|handler|service|middleware)"
        r"|implement\s+the\b"
        r"|build\s+the\s+(api|endpoint|module|service|backend|frontend)"
        r"|code\s+(this|the|a)\b",
        re.IGNORECASE,
    ), Capability.CODE_WRITE),

    # Shell execute — running scripts, commands, migrations
    (re.compile(
        r"run\s+(this\s+|the\s+|a\s+)?(script|command|migration|test)"
        r"|execute\s+(this\s+|the\s+|a\s+)?(script|command|migration|query)"
        r"|bash\s+-c\b"
        r"|shell\s+(command|exec)",
        re.IGNORECASE,
    ), Capability.SHELL_EXECUTE),

    # Social scraping (before generic web_scrape — "scrape instagram" is social, not generic)
    (re.compile(
        r"scrape\s+(instagram|twitter|tiktok|linkedin|reddit|youtube)"
        r"|get\s+(instagram|twitter|tiktok)\s+(followers|posts|comments|data)"
        r"|get\s+(data|info|posts|followers|comments)\s+(from|on)\s+(instagram|twitter|tiktok|linkedin|reddit|youtube)"
        r"|monitor\s+(instagram|twitter|tiktok|social)",
        re.IGNORECASE,
    ), Capability.SOCIAL_SCRAPE),

    # Web scrape — extracting data from specific URLs
    (re.compile(
        r"\bscrape\b"
        r"|extract\s+(data|content|info)\s+from\s+(https?://|(this|the|that|a)\s+(url|page|site|link))"
        r"|crawl\s+(this|the|https?://)"
        r"|get\s+(the\s+)?(html|content|data)\s+(from|of)\s+",
        re.IGNORECASE,
    ), Capability.WEB_SCRAPE),

    # Web search — finding information via search engines
    (re.compile(
        r"search\s+(for|the\s+web)"
        r"|look\s+up\b"
        r"|find\s+(information|articles|results)\s+(about|on|for)"
        r"|google\s+"
        r"|what\s+are\s+the\s+latest",
        re.IGNORECASE,
    ), Capability.WEB_SEARCH),

    # Web research — synthesized investigation with citations
    (re.compile(
        r"\bresearch\b"
        r"|investigate\b"
        r"|what\s+do\s+we\s+know\s+about"
        r"|deep\s+dive\s+(into|on)"
        r"|comprehensive\s+(analysis|overview)\s+of"
        r"|market\s+(research|analysis|intel)",
        re.IGNORECASE,
    ), Capability.WEB_RESEARCH),

    # Browser automation — interactive browser control
    (re.compile(
        r"open\s+(the\s+)?browser"
        r"|navigate\s+to\b"
        r"|click\s+(on|the|through)\b"
        r"|fill\s+(out|in)\s+(the\s+)?form"
        r"|log\s*in\s+to\b"
        r"|browser\s+automat"
        r"|automate\s+(the\s+)?(login|signup|checkout|flow|form|page)"
        r"|automate\s+(this\s+)?(ui|web|browser)",
        re.IGNORECASE,
    ), Capability.BROWSER_AUTOMATE),

    # Transcribe — audio/video to text
    (re.compile(
        r"\btranscri(be|ption)\b"
        r"|convert\s+(this\s+)?(audio|video|recording)\s+to\s+text"
        r"|speech.to.text"
        r"|whisper\b",
        re.IGNORECASE,
    ), Capability.TRANSCRIBE),

    # Design / image generation
    (re.compile(
        r"(make|create|generate|design)\s+(me\s+)?(a\s+)?(thumbnail|graphic|image|banner|logo|poster|flyer)"
        r"|social\s+(media\s+)?(graphic|image|post\s+image)"
        r"|brand\s+template",
        re.IGNORECASE,
    ), Capability.DESIGN_TEMPLATE),

    # Image editing
    (re.compile(
        r"edit\s+(this\s+)?(image|photo|picture)"
        r"|photoshop\b"
        r"|remove\s+(the\s+)?background"
        r"|resize\s+(the\s+)?(image|photo)"
        r"|crop\s+(the\s+)?(image|photo)",
        re.IGNORECASE,
    ), Capability.IMAGE_EDIT),

    # Vector design
    (re.compile(
        r"(create|design)\s+(a\s+)?(vector|svg|logo|icon)"
        r"|illustrator\b"
        r"|scalable\s+graphic",
        re.IGNORECASE,
    ), Capability.VECTOR_DESIGN),

    # Video generation (programmatic)
    (re.compile(
        r"(generate|create|make)\s+(a\s+)?video"
        r"|remotion\b"
        r"|render\s+(a\s+)?video"
        r"|programmatic\s+video",
        re.IGNORECASE,
    ), Capability.VIDEO_GENERATE),

    # Video editing
    (re.compile(
        r"edit\s+(this\s+)?video"
        r"|davinci\s+resolve\b"
        r"|color\s+grad(e|ing)"
        r"|add\s+(subtitles|captions)\s+to\s+(the\s+)?video",
        re.IGNORECASE,
    ), Capability.VIDEO_EDIT),

    # Email
    (re.compile(
        r"send\s+(an?\s+)?email"
        r"|draft\s+(an?\s+)?email"
        r"|compose\s+(an?\s+)?email"
        r"|email\s+(this|them|him|her)\b",
        re.IGNORECASE,
    ), Capability.EMAIL_SEND),

    # Social posting
    (re.compile(
        r"post\s+(to|on)\s+(instagram|twitter|x|tiktok|linkedin|facebook|youtube|reddit)"
        r"|publish\s+(to|on)\b"
        r"|schedule\s+(a\s+)?post",
        re.IGNORECASE,
    ), Capability.SOCIAL_POST),

    # Calendar
    (re.compile(
        r"schedule\s+(a\s+)?(meeting|call|event)"
        r"|check\s+(my\s+)?calendar"
        r"|book\s+(a\s+)?(meeting|time|slot)"
        r"|calendly\b",
        re.IGNORECASE,
    ), Capability.CALENDAR_MANAGE),

    # Payment
    (re.compile(
        r"(process|create|send)\s+(a\s+)?(payment|invoice|charge)"
        r"|charge\s+(the\s+)?(customer|client|user|card|account)"
        r"|stripe\b"
        r"|checkout\s+(link|page|session)",
        re.IGNORECASE,
    ), Capability.PAYMENT_PROCESS),

    # Data query
    (re.compile(
        r"query\s+(the\s+)?(database|db|postgres|neon)"
        r"|run\s+(a\s+)?sql\b"
        r"|select\s+.*\s+from\s+",
        re.IGNORECASE,
    ), Capability.DATA_QUERY),

    # Deploy
    (re.compile(
        r"\bdeploy\b"
        r"|push\s+to\s+(production|staging|prod)"
        r"|ship\s+(this|it)\b"
        r"|release\s+(this|the|v\d)",
        re.IGNORECASE,
    ), Capability.DEPLOY),

    # Autonomous multi-step
    (re.compile(
        r"autonom(ous|ously)\b"
        r"|run\s+this\s+overnight"
        r"|handle\s+this\s+(end.to.end|completely|fully)"
        r"|do\s+everything\s+(needed|required)",
        re.IGNORECASE,
    ), Capability.AUTONOMOUS_TASK),
]

# Task type → Capability fallback mapping (when no pattern matches)
_TASK_TYPE_MAP: dict[str, Capability] = {
    "code": Capability.CODE_WRITE,
    "strategic": Capability.REASON,
    "fast_response": Capability.FAST_RESPOND,
    "conversation": Capability.FAST_RESPOND,
    "score": Capability.FAST_RESPOND,
    "classify": Capability.FAST_RESPOND,
    "summarize": Capability.FAST_RESPOND,
    "analyze": Capability.REASON,
    "generate": Capability.CONTENT_WRITE,
    "research": Capability.WEB_RESEARCH,
    "web_search": Capability.WEB_SEARCH,
    "market_intel": Capability.WEB_RESEARCH,
    "self_improve": Capability.REASON,
    "plan": Capability.REASON,
    "coordinate": Capability.REASON,
    "autonomous": Capability.AUTONOMOUS_TASK,
    "multimodal": Capability.REASON,
    "browser_control": Capability.BROWSER_AUTOMATE,
}


def detect_capability(
    prompt: str,
    task_type: str | None = None,
    context: dict | None = None,
) -> Capability:
    """Infer the required capability from prompt content and context.

    Uses pattern matching first (fast, deterministic).
    Falls back to task_type mapping for ambiguous cases.
    Defaults to REASON for anything unrecognized.
    """
    prompt_lower = prompt.lower().strip()

    for pattern, capability in _INTENT_PATTERNS:
        if pattern.search(prompt_lower):
            logger.info("[CapRouter] detected %s from prompt pattern", capability.value)
            return capability

    if task_type:
        mapped = _TASK_TYPE_MAP.get(task_type)
        if mapped:
            logger.debug("[CapRouter] mapped task_type=%s → %s", task_type, mapped.value)
            return mapped

    return Capability.REASON


# ─── Dispatch ──────────────────────────────────────────────────────────────


def _normalize_result(raw: Any, provider_id: str, capability: Capability) -> CapabilityResult | None:
    """Convert adapter-specific result types to CapabilityResult."""
    if raw is None:
        return None

    if isinstance(raw, CapabilityResult):
        return raw

    output = getattr(raw, "output", None) or (raw if isinstance(raw, str) else None)
    if not output:
        return None

    latency = getattr(raw, "latency_ms", 0)
    return CapabilityResult(
        output=output,
        provider_id=provider_id,
        capability=capability.value,
        latency_ms=latency,
    )


def route_capability(
    prompt: str,
    task_type: str | None = None,
    context: dict | None = None,
    system: str | None = None,
    **kwargs: Any,
) -> CapabilityResult | None:
    """Main entry point. Detects capability, walks the provider chain,
    returns first successful result. Returns None if no specialized
    provider handles it (caller should fall back to LLM routing).
    """
    cap = detect_capability(prompt, task_type, context)

    if cap in _LLM_ONLY_CAPABILITIES:
        return None

    chains = _get_chains()
    chain = chains.get(cap)
    if not chain:
        logger.debug("[CapRouter] no chain for %s, falling through", cap.value)
        return None

    start_ms = time.monotonic_ns() // 1_000_000

    for entry in chain:
        try:
            if not entry.is_available():
                logger.debug("[CapRouter] %s unavailable, skipping", entry.provider_id)
                continue
        except Exception:
            continue

        try:
            logger.info("[CapRouter] trying %s for %s", entry.provider_id, cap.value)
            raw = entry.invoke(prompt, system=system or "", **kwargs)
            result = _normalize_result(raw, entry.provider_id, cap)
            if result:
                elapsed = (time.monotonic_ns() // 1_000_000) - start_ms
                result.latency_ms = result.latency_ms or elapsed
                _track(entry.provider_id, True)
                logger.info(
                    "[CapRouter] %s handled %s (%dms, %d chars)",
                    entry.provider_id, cap.value, result.latency_ms, len(result.output),
                )
                return result
            logger.info("[CapRouter] %s returned empty for %s", entry.provider_id, cap.value)
        except Exception as e:
            logger.warning("[CapRouter] %s failed for %s: %s", entry.provider_id, cap.value, e)
            _track(entry.provider_id, False)
            continue

    logger.info("[CapRouter] all providers exhausted for %s, falling through", cap.value)
    return None
