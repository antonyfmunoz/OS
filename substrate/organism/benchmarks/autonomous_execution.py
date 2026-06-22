"""Autonomous Execution Benchmark — session depth, recovery, and independence.

Campaign 23B. Category B. Tier 2: Production Benchmark.
Measures how deeply and reliably UMH executes without operator intervention.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    session_id: str = ""
    duration_seconds: float = 0.0
    tasks_attempted: int = 0
    tasks_completed: int = 0
    errors_encountered: int = 0
    errors_recovered: int = 0
    operator_interventions: int = 0
    validation_attempts: int = 0
    validation_passes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomousExecutionResult:
    sessions_evaluated: int = 0
    avg_session_duration_seconds: float = 0.0
    avg_task_depth: float = 0.0
    recovery_rate: float = 0.0
    validation_pass_rate: float = 0.0
    autonomous_completion_rate: float = 0.0
    total_tasks_attempted: int = 0
    total_tasks_completed: int = 0
    total_errors: int = 0
    total_recoveries: int = 0
    total_interventions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomousExecutionBenchmark:
    """Evaluates autonomous execution capability from session records."""

    def evaluate(self, sessions: list[SessionRecord]) -> AutonomousExecutionResult:
        if not sessions:
            return AutonomousExecutionResult()

        count = len(sessions)
        total_duration = sum(s.duration_seconds for s in sessions)
        total_attempted = sum(s.tasks_attempted for s in sessions)
        total_completed = sum(s.tasks_completed for s in sessions)
        total_errors = sum(s.errors_encountered for s in sessions)
        total_recovered = sum(s.errors_recovered for s in sessions)
        total_interventions = sum(s.operator_interventions for s in sessions)
        total_val_attempts = sum(s.validation_attempts for s in sessions)
        total_val_passes = sum(s.validation_passes for s in sessions)

        autonomous_tasks = sum(
            s.tasks_completed
            for s in sessions
            if s.operator_interventions == 0
        )

        return AutonomousExecutionResult(
            sessions_evaluated=count,
            avg_session_duration_seconds=total_duration / count,
            avg_task_depth=total_completed / count,
            recovery_rate=total_recovered / total_errors if total_errors > 0 else 0.0,
            validation_pass_rate=total_val_passes / total_val_attempts if total_val_attempts > 0 else 0.0,
            autonomous_completion_rate=autonomous_tasks / total_attempted if total_attempted > 0 else 0.0,
            total_tasks_attempted=total_attempted,
            total_tasks_completed=total_completed,
            total_errors=total_errors,
            total_recoveries=total_recovered,
            total_interventions=total_interventions,
        )
