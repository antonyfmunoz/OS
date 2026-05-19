"""Routing config — maps capability classes to runtime/model_router kwargs.

This is the bridge between Jarvis symbolic labels and the existing
model_router.call_with_fallback() interface. It wraps — never replaces —
the protected model_router.py.

Local-first routing: capabilities marked local_first=True attempt Ollama
before any cloud provider. Cloud fallback only triggers when local is
unavailable or returns an error.
"""

from __future__ import annotations

import os
from typing import Any

from .capabilities import (
    CapabilityClass,
    CapabilityEntry,
    CAPABILITY_REGISTRY,
)


# Maps capability classes to model_router.call_with_fallback() kwargs.
# These are the actual parameters passed at runtime.
_MODEL_ROUTER_MAP: dict[CapabilityClass, dict[str, Any]] = {
    CapabilityClass.BEST_CLOUD_REASONING: {
        "agent_type": "ceo",
        "force_opus": True,
    },
    CapabilityClass.FAST_CLOUD_REASONING: {
        "agent_type": "worker",
    },
    CapabilityClass.CHEAP_CLOUD_REASONING: {
        "agent_type": "worker",
    },
    CapabilityClass.LOCAL_FAST_MODEL: {
        "agent_type": "worker",
        "prefer_local": True,
    },
    CapabilityClass.LOCAL_CODE_MODEL: {
        "agent_type": "worker",
        "prefer_local": True,
    },
    CapabilityClass.LOCAL_EMBEDDING_MODEL: {},
    CapabilityClass.LOCAL_VISION_MODEL: {},
    CapabilityClass.LOCAL_TRANSCRIPTION_MODEL: {},
    CapabilityClass.CLOUD_VISION_MODEL: {
        "agent_type": "worker",
    },
    CapabilityClass.LOCAL_TTS_MODEL: {},
    CapabilityClass.CLOUD_TTS_MODEL: {},
    CapabilityClass.LOCAL_STT_MODEL: {},
}


class RoutingConfig:
    """Resolves capability classes to model_router kwargs and metadata.

    Wraps the static registry with runtime overrides from environment.
    """

    def __init__(
        self,
        registry: dict[CapabilityClass, CapabilityEntry] | None = None,
        router_map: dict[CapabilityClass, dict[str, Any]] | None = None,
    ) -> None:
        self._registry = registry or dict(CAPABILITY_REGISTRY)
        self._router_map = router_map or dict(_MODEL_ROUTER_MAP)
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Check env vars for provider overrides. Format: JARVIS_ROUTE_<CAPABILITY>=provider"""
        for cap in CapabilityClass:
            env_key = f"JARVIS_ROUTE_{cap.name}"
            override = os.environ.get(env_key)
            if override and cap in self._registry:
                entry = self._registry[cap]
                self._registry[cap] = CapabilityEntry(
                    capability_class=entry.capability_class,
                    preferred_provider_symbol=override,
                    fallback_provider_symbols=entry.fallback_provider_symbols,
                    privacy_level=entry.privacy_level,
                    max_cost_hint=entry.max_cost_hint,
                    local_first=entry.local_first,
                    notes=f"Overridden by {env_key}. Original: {entry.preferred_provider_symbol}",
                )

    def resolve(self, capability: CapabilityClass) -> dict[str, Any]:
        """Return model_router.call_with_fallback() kwargs for a capability."""
        return dict(self._router_map.get(capability, {}))

    def entry(self, capability: CapabilityClass) -> CapabilityEntry | None:
        """Return the full routing entry for inspection."""
        return self._registry.get(capability)

    def is_local_first(self, capability: CapabilityClass) -> bool:
        """Whether this capability prefers local execution."""
        entry = self._registry.get(capability)
        return entry.local_first if entry else False

    def describe(self) -> dict[str, dict[str, Any]]:
        """Return the full routing table for the /capabilities endpoint."""
        result: dict[str, dict[str, Any]] = {}
        for cap, entry in self._registry.items():
            result[cap.value] = {
                "preferred_provider": entry.preferred_provider_symbol,
                "fallbacks": entry.fallback_provider_symbols,
                "privacy_level": entry.privacy_level.value,
                "max_cost_hint": entry.max_cost_hint,
                "local_first": entry.local_first,
                "notes": entry.notes,
                "router_kwargs": self._router_map.get(cap, {}),
            }
        return result

    def local_capabilities(self) -> list[str]:
        """List capabilities that can run without any cloud provider."""
        return [cap.value for cap, entry in self._registry.items() if entry.local_first]

    def cloud_capabilities(self) -> list[str]:
        """List capabilities that require a cloud provider."""
        return [cap.value for cap, entry in self._registry.items() if not entry.local_first]


def load_routing_config() -> RoutingConfig:
    """Factory — loads config with env overrides applied."""
    return RoutingConfig()
