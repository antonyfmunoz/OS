"""Adapter protocols — boundary contracts for external capabilities."""

from __future__ import annotations

from umh.adapters.base import (
    BrowserAdapter,
    FilesystemAdapter,
    LLMAdapter,
    ShellAdapter,
    WorkstationAdapter,
)

__all__ = [
    "BrowserAdapter",
    "FilesystemAdapter",
    "LLMAdapter",
    "ShellAdapter",
    "WorkstationAdapter",
]
