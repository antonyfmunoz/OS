"""UMH Execution Backend Registry — environment-aware backend selection.

Maps environment names to execution backends.  The governance gate uses
this to select the correct backend before delegating to the canonical
execution engine.

MVP behaviour:
  - "local" and "null" environments always available (NullExecutionBackend)
  - Unknown environments are rejected unless a fallback policy is set
  - register() / get() / select_backend() are the public surface

Usage:
    registry = get_backend_registry()
    registry.register("local", NullExecutionBackend())
    result = registry.select_backend("local")
    backend = result["backend"]
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from umh.execution.interfaces import ExecutionBackend, NullExecutionBackend

_log = logging.getLogger(__name__)


class ExecutionBackendRegistry:
    """Registry of named execution backends keyed by environment."""

    def __init__(self) -> None:
        self._backends: dict[str, tuple[str, ExecutionBackend]] = {}
        self._lock = threading.Lock()
        self._discover_defaults()

    def _discover_defaults(self) -> None:
        null = NullExecutionBackend()
        self._backends["null"] = ("null", null)
        self._backends["local"] = ("null", null)
        self._backends["test"] = ("null", null)

    def register(
        self,
        environment: str,
        backend: ExecutionBackend,
        name: str = "",
    ) -> None:
        """Register a backend for an environment.

        Args:
            environment: Environment name (e.g. "local", "sandbox").
            backend: An object satisfying the ExecutionBackend protocol.
            name: Human-readable name.  Defaults to the class name.
        """
        if not environment:
            raise ValueError("Environment name must not be empty")
        resolved_name = name or type(backend).__name__
        with self._lock:
            self._backends[environment] = (resolved_name, backend)
        _log.info("Registered backend %s for environment %s", resolved_name, environment)

    def get(self, environment: str) -> ExecutionBackend | None:
        """Return the backend for an environment, or None."""
        entry = self._backends.get(environment)
        return entry[1] if entry else None

    def has(self, environment: str) -> bool:
        return environment in self._backends

    def list_environments(self) -> list[str]:
        """Return all registered environment names."""
        return list(self._backends.keys())

    def select_backend(
        self,
        environment: str,
        capability: str | None = None,
    ) -> dict[str, Any]:
        """Select a backend for the given environment.

        Returns:
            {"name": str, "backend": ExecutionBackend, "environment": str}

        Raises:
            ValueError: If the environment has no registered backend.
        """
        entry = self._backends.get(environment)
        if entry is None:
            raise ValueError(
                f"No backend registered for environment '{environment}'. "
                f"Available: {', '.join(self._backends.keys())}"
            )
        backend_name, backend = entry
        if capability and hasattr(backend, "can_handle") and not backend.can_handle(capability):
            _log.warning(
                "Backend %s for env %s cannot handle capability %s — proceeding anyway",
                backend_name,
                environment,
                capability,
            )
        return {
            "name": backend_name,
            "backend": backend,
            "environment": environment,
        }

    def discover_default_backends(self) -> list[str]:
        """Re-discover and return list of default environment names.

        Called at init.  Can be called again to refresh after adapter
        registration.
        """
        self._discover_defaults()
        return list(self._backends.keys())

    def reset(self) -> None:
        """Clear all backends and re-discover defaults."""
        with self._lock:
            self._backends.clear()
            self._discover_defaults()


_registry: ExecutionBackendRegistry | None = None
_registry_lock = threading.Lock()


def get_backend_registry() -> ExecutionBackendRegistry:
    """Return the process-global backend registry (lazy-initialized)."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ExecutionBackendRegistry()
    return _registry


def reset_backend_registry(registry: ExecutionBackendRegistry | None = None) -> None:
    """Replace the global registry (useful for tests)."""
    global _registry
    with _registry_lock:
        _registry = registry
