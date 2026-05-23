"""
execution.bridge — Lazy-import package.

All symbols are available via ``from substrate.execution.bridge import X`` or
``from substrate.execution.bridge.submodule import Y``. Submodules are loaded
on first access (PEP 562 __getattr__), not at package import time.

Post-orphan-archive (2026-05-14): 148 modules archived. Only 15
production-reachable modules remain (4 registered here for
package-level symbol access).

Migrated from runtime.transport → execution.bridge (2026-05-14, §24).
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

_log = logging.getLogger(__name__)

# ── Symbol → (submodule, attribute) mapping ───────────────────────────

_LAZY_MAP: dict[str, tuple[str, str]] = {}


def _m(submodule: str, *names: str) -> None:
    """Register symbols from a submodule for lazy import."""
    for name in names:
        _LAZY_MAP[name] = (f"substrate.execution.bridge.{submodule}", name)


# ── Production modules with package-level symbol access ──────────────

_m("storage", "SubstrateStorage", "JSONFileStorage", "NeonStorage", "get_storage")
_m("capability_tagging", "tag_request")
_m("station_daemon", "StationDaemon")
_m(
    "station_helpers",
    "propose_play_sound",
    "propose_speak_text",
    "propose_open_url",
    "propose_launch_app",
    "propose_open_scene",
)


# ── PEP 562 lazy loader ─────────────────────────────────────────────


def __getattr__(name: str) -> Any:
    if name in _LAZY_MAP:
        module_path, attr = _LAZY_MAP[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value

    raise AttributeError(f"module 'execution.bridge' has no attribute {name!r}")


# ── __all__ ──────────────────────────────────────────────────────────

__all__ = list(_LAZY_MAP.keys())
