"""Sensing adapter port — substrate-layer abstraction for perception registration.

Follows the same pattern as notification.py and channel_port.py:
the workstation runtime registers a concrete registry at boot,
and substrate code queries through these thin functions without
importing from adapters/ directly.

UMH substrate subsystem.
"""

from __future__ import annotations

from typing import Any, Callable

_registry: Any | None = None
_on_signal_fn: Callable[[str, dict[str, object]], None] | None = None


def register_sensing_registry(registry: Any) -> None:
    """Register the concrete SensingAdapterRegistry at boot."""
    global _registry
    _registry = registry


def register_signal_handler(fn: Callable[[str, dict[str, object]], None]) -> None:
    """Register a callback invoked when any sensing adapter emits a signal.

    The callback receives (adapter_id, signal_data).
    """
    global _on_signal_fn
    _on_signal_fn = fn


def get_registry() -> Any | None:
    """Get the registered sensing adapter registry, or None if not registered."""
    return _registry


def emit_sensing_signal(adapter_id: str, signal_data: dict[str, object]) -> bool:
    """Route a sensing signal through the registered handler.

    Returns False if no handler is registered (headless/no-perception mode).
    """
    if _on_signal_fn is not None:
        _on_signal_fn(adapter_id, signal_data)
        return True
    return False


def sensing_health() -> dict[str, Any]:
    """Query health of all registered sensing adapters.

    Returns empty dict when no registry is registered.
    """
    if _registry is not None and hasattr(_registry, "health_all"):
        return {k: v.to_dict() for k, v in _registry.health_all().items()}
    return {}


def sensing_summary() -> dict[str, object]:
    """Quick summary of registered sensing adapters.

    Returns empty summary when no registry is registered.
    """
    if _registry is not None and hasattr(_registry, "summary"):
        return _registry.summary()
    return {"total": 0, "by_state": {}, "families": []}
