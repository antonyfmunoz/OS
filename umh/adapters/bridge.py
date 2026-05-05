"""Platform adapter bridge — centralized optional dependency discovery.

Every UMH subsystem that needs a platform-specific adapter (goals persistence,
strategy persistence, storage, execution backend, etc.) discovers it through
this single module. The umh import path appears here and nowhere else
inside UMH.

Usage::

    from umh.adapters.bridge import discover_platform_adapter

    adapter = discover_platform_adapter(
        "umh.adapters.umh_storage",
        "get_umh_storage",
    )
    if adapter is None:
        # fall back to null/in-memory implementation
        ...
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


def discover_platform_adapter(
    module_path: str,
    factory_name: str,
) -> Any | None:
    """Try to import a platform adapter factory and call it.

    Returns the adapter instance if available, None otherwise.
    Swallows ImportError and any exception from the factory itself
    so UMH always remains standalone-capable.
    """
    try:
        import importlib

        mod = importlib.import_module(module_path)
        factory = getattr(mod, factory_name)
        return factory()
    except ImportError:
        _log.debug("Platform adapter %s not available (ImportError)", module_path)
        return None
    except Exception as exc:
        _log.debug("Platform adapter %s.%s failed: %s", module_path, factory_name, exc)
        return None
