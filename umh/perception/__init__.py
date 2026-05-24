"""Perception subsystem — webcam, workspace, metrics, unified routing."""

from __future__ import annotations

__all__ = [
    "PerceptionRouter",
    "WebcamMonitor",
    "WorkspaceTracker",
    "MetricsCollector",
]


def _lazy_import(name: str):  # noqa: ANN202
    if name == "PerceptionRouter":
        from umh.perception.router import PerceptionRouter

        return PerceptionRouter
    if name == "WebcamMonitor":
        from umh.perception.webcam import WebcamMonitor

        return WebcamMonitor
    if name == "WorkspaceTracker":
        from umh.perception.workspace import WorkspaceTracker

        return WorkspaceTracker
    if name == "MetricsCollector":
        from umh.perception.metrics import MetricsCollector

        return MetricsCollector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __getattr__(name: str):  # noqa: ANN202
    return _lazy_import(name)
