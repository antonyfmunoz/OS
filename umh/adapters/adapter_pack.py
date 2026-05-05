"""Phase 76 MVP adapter pack — initialization and registry wiring.

Creates all MVP adapters, wraps them in an AdapterExecutionBackend,
and registers that backend for each supported environment in the
backend registry.

Usage:
    from umh.adapters.adapter_pack import initialize_adapter_pack
    initialize_adapter_pack()  # registers into global backend registry

    # Or with explicit registry:
    initialize_adapter_pack(registry=my_registry)
"""

from __future__ import annotations

import logging
from typing import Any

from umh.adapters.adapter_backend import AdapterExecutionBackend
from umh.adapters.cli_adapter import CLIAdapter
from umh.adapters.filesystem_adapter import FilesystemAdapter
from umh.adapters.http_adapter import HTTPAdapter
from umh.adapters.simulated_browser import SimulatedBrowserAdapter
from umh.environments.definitions import MVP_ENVIRONMENTS

_log = logging.getLogger(__name__)

_initialized = False


def create_adapter_backend(
    safe_roots: tuple[str, ...] = ("/opt/OS", "/tmp/umh"),
) -> AdapterExecutionBackend:
    """Create an AdapterExecutionBackend with all MVP adapters registered."""
    backend = AdapterExecutionBackend()

    backend.register_adapter(CLIAdapter())
    backend.register_adapter(FilesystemAdapter(safe_roots=safe_roots))
    backend.register_adapter(HTTPAdapter())
    backend.register_adapter(SimulatedBrowserAdapter())

    return backend


def initialize_adapter_pack(
    registry: Any | None = None,
    safe_roots: tuple[str, ...] = ("/opt/OS", "/tmp/umh"),
    force: bool = False,
) -> AdapterExecutionBackend:
    """Create MVP adapter backend and register it for all MVP environments.

    Args:
        registry: Backend registry to register into.  Uses global if None.
        safe_roots: Filesystem safe roots for the filesystem adapter.
        force: Re-initialize even if already done.

    Returns:
        The configured AdapterExecutionBackend.
    """
    global _initialized
    if _initialized and not force:
        _log.debug("Adapter pack already initialized, skipping")
        return _get_current_backend(registry)

    from umh.execution.backend_registry import get_backend_registry

    reg = registry or get_backend_registry()
    backend = create_adapter_backend(safe_roots=safe_roots)

    for env_id, env_def in MVP_ENVIRONMENTS.items():
        if env_def.available:
            reg.register(env_id, backend, name=f"adapter_pack:{env_id}")
            _log.info("Registered adapter_pack backend for environment: %s", env_id)

    _initialized = True
    _log.info(
        "Adapter pack initialized: %d capabilities across %d environments",
        len(backend.registered_capabilities),
        len(MVP_ENVIRONMENTS),
    )

    return backend


def _get_current_backend(registry: Any | None = None) -> AdapterExecutionBackend:
    """Retrieve the current adapter backend from the registry."""
    from umh.execution.backend_registry import get_backend_registry

    reg = registry or get_backend_registry()
    backend = reg.get("local")
    if isinstance(backend, AdapterExecutionBackend):
        return backend
    return create_adapter_backend()


def get_adapter_pack_status() -> dict[str, Any]:
    """Return status of the adapter pack for diagnostics."""
    from umh.execution.backend_registry import get_backend_registry

    reg = get_backend_registry()
    envs = reg.list_environments()

    return {
        "initialized": _initialized,
        "registered_environments": envs,
        "mvp_environments": sorted(MVP_ENVIRONMENTS.keys()),
        "coverage": [e for e in MVP_ENVIRONMENTS if e in envs],
    }
