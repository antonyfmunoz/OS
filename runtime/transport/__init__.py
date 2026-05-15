"""
runtime.transport → execution.transport shim.

Canonical location: execution/transport/ (§24 migration, 2026-05-14).
This shim delegates all attribute access to the canonical package.
"""

from __future__ import annotations

import importlib
from typing import Any


def __getattr__(name: str) -> Any:
    import execution.transport as _canonical

    try:
        return getattr(_canonical, name)
    except AttributeError:
        pass

    try:
        mod = importlib.import_module(f"execution.transport.{name}")
        return mod
    except ImportError:
        pass

    raise AttributeError(f"module 'runtime.transport' has no attribute {name!r}")
