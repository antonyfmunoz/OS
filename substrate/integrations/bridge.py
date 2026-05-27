"""UMH Bridge — connects UMH model routing to runtime/model_router.py.

This is the integration point between the symbolic capability layer
and the existing UMH model routing infrastructure. It wraps
call_with_fallback() without modifying it.
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.contracts.routing_contracts import CapabilityClass

def _load_routing():
    from adapters.models.routing.config import RoutingConfig, load_routing_config
    return RoutingConfig, load_routing_config


class CapabilityBridge:
    """Bridges symbolic capability requests to runtime/model_router.

    Usage:
        bridge = CapabilityBridge()
        result = bridge.route(
            CapabilityClass.BEST_CLOUD_REASONING,
            system_prompt="You are a strategic advisor.",
            user_prompt="Analyze this market opportunity.",
        )
    """

    def __init__(self, config: Any | None = None) -> None:
        if config is None:
            _, load_routing_config = _load_routing()
            config = load_routing_config()
        self._config = config
        self._model_router = None

    def _get_router(self) -> Any:
        """Lazy-load model_router to avoid circular imports."""
        if self._model_router is None:
            try:
                from adapters.models.model_router import call_with_fallback

                self._model_router = call_with_fallback
            except ImportError:
                self._model_router = self._stub_router
        return self._model_router

    def route(
        self,
        capability: CapabilityClass,
        system_prompt: str = "",
        user_prompt: str = "",
        **extra_kwargs: Any,
    ) -> str | None:
        """Route a request through the capability layer to model_router."""
        router_kwargs = self._config.resolve(capability)
        router_kwargs.update(extra_kwargs)

        router = self._get_router()
        return router(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **router_kwargs,
        )

    def describe(self) -> dict[str, Any]:
        """Describe the full routing table."""
        return self._config.describe()

    def is_available(self) -> bool:
        """Check if the model router is importable."""
        try:
            from adapters.models.model_router import call_with_fallback

            return True
        except ImportError:
            return False

    @staticmethod
    def _stub_router(
        system_prompt: str = "",
        user_prompt: str = "",
        **kwargs: Any,
    ) -> str:
        """Fallback when model_router is not available."""
        return f"[stub] Would route: {user_prompt[:100]}"
