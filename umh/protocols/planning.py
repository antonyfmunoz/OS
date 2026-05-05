"""Planning protocols — contracts for task decomposition and plan management."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from umh.execution.harness import HarnessPlan, HarnessTask, TaskPlanner

__all__ = ["TaskPlanner", "PlanEvaluator"]


@runtime_checkable
class PlanEvaluator(Protocol):
    """Evaluates a plan before execution — quality gate for plan-mode runs."""

    def evaluate(self, plan: HarnessPlan, task: HarnessTask) -> tuple[bool, str]: ...
