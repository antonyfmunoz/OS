"""Tool adapter port — substrate-layer abstraction for shell/filesystem/git tools.

The adapter layer (adapters/tool_adapters/) registers its concrete classes
at startup. Substrate code calls the thin wrappers here, never importing
from adapters/.
"""

from __future__ import annotations

from typing import Any, Optional

_tool_adapter_classes: dict[str, type] = {}


def register_tool_adapter(name: str, cls: type) -> None:
    """Register a tool adapter class by name (tmux, shell, git, filesystem)."""
    _tool_adapter_classes[name] = cls


def get_tool_adapter_class(name: str) -> Optional[type]:
    """Return a tool adapter class by name, or None if not registered."""
    return _tool_adapter_classes.get(name)


def get_all_tool_adapter_classes() -> dict[str, type]:
    """Return all registered tool adapter classes."""
    return dict(_tool_adapter_classes)
