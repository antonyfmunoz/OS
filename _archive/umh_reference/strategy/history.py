"""UMH Strategy History — versioned strategy tracking per goal.

Tracks all strategy versions for a goal along with performance metrics.
Strategies are IMMUTABLE — new versions are always appended, never modified.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from umh.core.clock import iso_now as _iso_now
from umh.strategy.models import Strategy


@dataclass
class PerformanceMetrics:
    """Aggregated performance data for a strategy version."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0
    total_duration_sec: float = 0.0
    evaluations: int = 0

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total

    @property
    def avg_duration_sec(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return self.total_duration_sec / self.tasks_completed

    def to_dict(self) -> dict:
        return {
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_retried": self.tasks_retried,
            "total_duration_sec": self.total_duration_sec,
            "evaluations": self.evaluations,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_sec": round(self.avg_duration_sec, 2),
        }


@dataclass
class StrategyVersion:
    """A single versioned strategy with its performance metrics."""

    strategy: Strategy
    version: int = 1
    version_id: str = ""
    created_at: str = ""
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    is_active: bool = True
    replaced_by: str = ""

    def __post_init__(self) -> None:
        if not self.version_id:
            self.version_id = f"sv_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = _iso_now()

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "version": self.version,
            "strategy_id": self.strategy.id,
            "created_at": self.created_at,
            "performance": self.performance.to_dict(),
            "is_active": self.is_active,
            "replaced_by": self.replaced_by,
            "strategy": self.strategy.to_dict(),
        }


@dataclass
class StrategyHistory:
    """Complete version history for a goal's strategies."""

    goal_id: str
    versions: list[StrategyVersion] = field(default_factory=list)

    def add_version(self, strategy: Strategy) -> StrategyVersion:
        """Add a new strategy version. Deactivates the previous active version."""
        version_num = len(self.versions) + 1
        for v in self.versions:
            if v.is_active:
                v.is_active = False

        sv = StrategyVersion(
            strategy=strategy,
            version=version_num,
        )
        self.versions.append(sv)
        return sv

    def active_version(self) -> StrategyVersion | None:
        """Return the currently active version, or None."""
        for v in reversed(self.versions):
            if v.is_active:
                return v
        return None

    def get_version(self, version_id: str) -> StrategyVersion | None:
        """Return a specific version by ID."""
        for v in self.versions:
            if v.version_id == version_id:
                return v
        return None

    def latest_version(self) -> StrategyVersion | None:
        """Return the most recent version."""
        if not self.versions:
            return None
        return self.versions[-1]

    def version_count(self) -> int:
        return len(self.versions)

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "version_count": self.version_count(),
            "versions": [v.to_dict() for v in self.versions],
        }


# -- History Store -----------------------------------------------------

_histories: dict[str, StrategyHistory] = {}
_history_lock = threading.Lock()


def get_strategy_history(goal_id: str) -> StrategyHistory:
    """Return history for a goal, creating if needed."""
    with _history_lock:
        if goal_id not in _histories:
            _histories[goal_id] = StrategyHistory(goal_id=goal_id)
        return _histories[goal_id]


def record_strategy_version(goal_id: str, strategy: Strategy) -> StrategyVersion:
    """Record a new strategy version for a goal."""
    history = get_strategy_history(goal_id)
    return history.add_version(strategy)


def record_task_outcome(
    goal_id: str,
    completed: bool = False,
    failed: bool = False,
    retried: bool = False,
    duration_sec: float = 0.0,
) -> None:
    """Record a task outcome against the active strategy version."""
    history = get_strategy_history(goal_id)
    active = history.active_version()
    if active is None:
        return
    if completed:
        active.performance.tasks_completed += 1
        active.performance.total_duration_sec += duration_sec
    if failed:
        active.performance.tasks_failed += 1
    if retried:
        active.performance.tasks_retried += 1
    active.performance.evaluations += 1


def reset_strategy_history() -> None:
    """Clear all history (for testing)."""
    with _history_lock:
        _histories.clear()
