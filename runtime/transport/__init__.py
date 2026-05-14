"""
runtime.transport — Lazy-import package.

All symbols are available via ``from runtime.transport import X`` or
``from runtime.transport.submodule import Y``. Submodules are loaded
on first access (PEP 562 __getattr__), not at package import time.

Previously this file was 570+ lines of eager imports that pulled in
40 submodules transitively — blocking 151 deferred migration items.
See: data/audits/2026-05-13_triage_manifest.md (Wave 0.5 thread).

Post-orphan-archive (2026-05-14): 148 orphan modules archived.
Only 15 production-reachable modules remain registered here.
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
        _LAZY_MAP[name] = (f"runtime.transport.{submodule}", name)


# ── Core registries ───────────────────────────────────────────────────

_m("nodes", "Node", "NodeRole", "NodeType", "NodeStatus", "NodeRegistry")
_m("station", "StationContract", "StationHeartbeat", "StationEvent", "ControlMode")
_m("actions", "SafeAction", "ActionKind", "ActionResult", "ActionStatus")
_m("rituals", "Ritual", "RitualKind", "RitualState", "RitualRegistry")
_m("storage", "SubstrateStorage", "JSONFileStorage", "NeonStorage", "get_storage")
_m("station_bus", "StationBus", "get_station_bus")
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
_m("ritual_body", "RitualPolicy", "run_close_day_body", "run_open_day_body")

# ── Voice / session ──────────────────────────────────────────────────

_m(
    "voice_session",
    "VoiceSession",
    "VoiceSessionStatus",
    "VoiceSessionRuntime",
    "VoiceTurn",
    "VoiceTurnSource",
    "VoiceSessionStore",
    "get_voice_session_store",
    "set_voice_responder",
    "voice_session_report",
)


# ── PEP 562 lazy loader ─────────────────────────────────────────────

_ALIASES: dict[str, tuple[str, str]] = {}


def __getattr__(name: str) -> Any:
    if name in _LAZY_MAP:
        module_path, attr = _LAZY_MAP[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value

    if name in _ALIASES:
        module_path, attr = _ALIASES[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value

    raise AttributeError(f"module 'runtime.transport' has no attribute {name!r}")


# ── __all__ ──────────────────────────────────────────────────────────

__all__ = list(_LAZY_MAP.keys()) + list(_ALIASES.keys())
