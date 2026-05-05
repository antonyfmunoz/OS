"""Execution protocols — contracts for dispatch, backends, and observation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from umh.execution.contract import ExecutionRequest, ExecutionResult
from umh.execution.interfaces import ExecutionBackend, ExecutionObserver
from umh.execution.harness import (
    CapabilityGate,
    HarnessObserver,
    StepExecutor,
    TaskPlanner,
)
from umh.execution.stages import ExecutionStage

__all__ = [
    "ExecutionBackend",
    "ExecutionObserver",
    "ExecutionStage",
    "CapabilityGate",
    "HarnessObserver",
    "StepExecutor",
    "TaskPlanner",
]
