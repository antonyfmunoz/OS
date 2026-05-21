"""Workstation protocols — contracts for local environment detection and control."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from umh.adapters.base import WorkstationAdapter

__all__ = ["WorkstationAdapter", "EnvironmentDetector"]


@runtime_checkable
class EnvironmentDetector(Protocol):
    """Detects the current execution environment (local, container, cloud, etc.)."""

    def detect(self) -> dict[str, Any]: ...

    def environment_name(self) -> str: ...
