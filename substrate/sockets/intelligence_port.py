"""Intelligence port — substrate-layer abstraction for model routing and LLM access.

The adapter layer (adapters/models/) registers its concrete implementations at startup.
Substrate code calls the thin wrappers here, never importing from adapters/.

Covers: model_router (get_router, call_with_fallback, MODEL_REGISTRY, etc.),
agent_runtime (AgentRuntime, get_agent_runtime), and CLI adapters (cc_sdk, etc.).
"""

from __future__ import annotations

from typing import Any, Callable, Optional

# ── Model Router ────────────────────────────────────────────────────

_get_router_fn: Optional[Callable] = None
_call_with_fallback_fn: Optional[Callable] = None
_model_registry: Optional[Any] = None
_refresh_provider_health_fn: Optional[Callable] = None
_role_slots: Optional[Any] = None
_ollama_available_fn: Optional[Callable] = None


def register_model_router(
    *,
    get_router: Callable,
    call_with_fallback: Callable,
    model_registry: Any,
    refresh_provider_health: Optional[Callable] = None,
    role_slots: Optional[Any] = None,
    ollama_available: Optional[Callable] = None,
) -> None:
    """Register the concrete model router (called once at startup)."""
    global _get_router_fn, _call_with_fallback_fn, _model_registry
    global _refresh_provider_health_fn, _role_slots, _ollama_available_fn
    _get_router_fn = get_router
    _call_with_fallback_fn = call_with_fallback
    _model_registry = model_registry
    _refresh_provider_health_fn = refresh_provider_health
    _role_slots = role_slots
    _ollama_available_fn = ollama_available


def get_router() -> Any:
    """Return the model router, or None if not registered."""
    if _get_router_fn is not None:
        return _get_router_fn()
    return None


def call_with_fallback(**kwargs: Any) -> Any:
    """Route an LLM call through the registered model router."""
    if _call_with_fallback_fn is not None:
        return _call_with_fallback_fn(**kwargs)
    return None


def get_model_registry() -> Any:
    """Return MODEL_REGISTRY dict, or empty dict if not registered."""
    return _model_registry if _model_registry is not None else {}


def refresh_provider_health() -> None:
    """Refresh provider health checks."""
    if _refresh_provider_health_fn is not None:
        _refresh_provider_health_fn()


def get_role_slots() -> Any:
    """Return ROLE_SLOTS, or None if not registered."""
    return _role_slots


def ollama_available() -> bool:
    """Check if Ollama is available."""
    if _ollama_available_fn is not None:
        return _ollama_available_fn()
    return False


# ── Agent Runtime ───────────────────────────────────────────────────

_agent_runtime_cls: Optional[type] = None
_get_agent_runtime_fn: Optional[Callable] = None


def register_agent_runtime(
    *,
    agent_runtime_cls: type,
    get_agent_runtime: Optional[Callable] = None,
) -> None:
    """Register the concrete AgentRuntime class."""
    global _agent_runtime_cls, _get_agent_runtime_fn
    _agent_runtime_cls = agent_runtime_cls
    _get_agent_runtime_fn = get_agent_runtime


def get_agent_runtime_class() -> Optional[type]:
    """Return the AgentRuntime class, or None if not registered."""
    return _agent_runtime_cls


def get_agent_runtime(*args: Any, **kwargs: Any) -> Any:
    """Get or create an AgentRuntime instance."""
    if _get_agent_runtime_fn is not None:
        return _get_agent_runtime_fn(*args, **kwargs)
    if _agent_runtime_cls is not None:
        return _agent_runtime_cls(*args, **kwargs)
    return None


# ── LLM Adapter ─────────────────────────────────────────────────────

_llm_adapter_cls: Optional[type] = None


def register_llm_adapter(cls: type) -> None:
    """Register the concrete LLMAdapter class."""
    global _llm_adapter_cls
    _llm_adapter_cls = cls


def get_llm_adapter_class() -> Optional[type]:
    """Return LLMAdapter class, or None if not registered."""
    return _llm_adapter_cls


# ── CLI Adapters (cc_sdk, codex, hermes, opencode) ──────────────────

_cli_adapters: dict[str, dict[str, Callable]] = {}


def register_cli_adapter(name: str, *, query_fn: Callable, is_available_fn: Optional[Callable] = None, **extra: Callable) -> None:
    """Register a CLI adapter (cc_sdk, codex, hermes, opencode)."""
    entry: dict[str, Callable] = {"query": query_fn}
    if is_available_fn is not None:
        entry["is_available"] = is_available_fn
    entry.update(extra)
    _cli_adapters[name] = entry


def get_cli_query(name: str) -> Optional[Callable]:
    """Return the query function for a named CLI adapter."""
    entry = _cli_adapters.get(name)
    return entry["query"] if entry else None


def cli_is_available(name: str) -> bool:
    """Check if a named CLI adapter is available."""
    entry = _cli_adapters.get(name)
    if entry and "is_available" in entry:
        return entry["is_available"]()
    return False


def get_cli_extra(name: str, fn_name: str) -> Optional[Callable]:
    """Return an extra function from a CLI adapter (e.g. review_codex_sync)."""
    entry = _cli_adapters.get(name)
    return entry.get(fn_name) if entry else None


# ── Routing Config ──────────────────────────────────────────────────

_routing_config_fn: Optional[Callable] = None


def register_routing_config(load_fn: Callable) -> None:
    """Register the routing config loader."""
    global _routing_config_fn
    _routing_config_fn = load_fn


def load_routing_config() -> Any:
    """Load routing config, or None if not registered."""
    if _routing_config_fn is not None:
        return _routing_config_fn()
    return None
