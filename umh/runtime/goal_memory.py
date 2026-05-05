"""Goal memory — append-only record of goal outcomes for long-horizon learning.

Stores GoalRecords capturing outcome, duration, identity alignment, and
reward signals. GoalMemory supports querying by goal type and computing
aggregate statistics for reinforcement scoring.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


_DEFAULT_MAX_RECORDS = 500
_MIN_MAX_RECORDS = 50
_MAX_MAX_RECORDS = 2000


@dataclass(frozen=True)
class GoalRecord:
    """Immutable record of a completed goal attempt."""

    goal_id: str
    goal_type: str
    duration_ticks: int
    completed: bool
    success_rate: float
    identity_alignment: float
    reward: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "duration_ticks": self.duration_ticks,
            "completed": self.completed,
            "success_rate": round(self.success_rate, 4),
            "identity_alignment": round(self.identity_alignment, 4),
            "reward": round(self.reward, 4),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class GoalTypeStats:
    """Aggregate statistics for a goal type."""

    goal_type: str
    count: int
    completion_rate: float
    avg_duration: float
    avg_success_rate: float
    avg_identity_alignment: float
    avg_reward: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "count": self.count,
            "completion_rate": round(self.completion_rate, 4),
            "avg_duration": round(self.avg_duration, 4),
            "avg_success_rate": round(self.avg_success_rate, 4),
            "avg_identity_alignment": round(self.avg_identity_alignment, 4),
            "avg_reward": round(self.avg_reward, 4),
        }


def make_goal_record(
    *,
    goal_id: str,
    goal_type: str,
    duration_ticks: int,
    completed: bool,
    success_rate: float = 0.0,
    identity_alignment: float = 0.5,
    reward: float = 0.0,
    timestamp: str = "",
) -> GoalRecord:
    """Create a GoalRecord with defaults and clamping."""
    return GoalRecord(
        goal_id=goal_id,
        goal_type=goal_type,
        duration_ticks=max(0, duration_ticks),
        completed=completed,
        success_rate=max(0.0, min(1.0, success_rate)),
        identity_alignment=max(0.0, min(1.0, identity_alignment)),
        reward=max(-1.0, min(1.0, reward)),
        timestamp=timestamp or _iso_now(),
    )


class GoalMemory:
    """Append-only store of goal outcome records with type-based querying.

    Records are never mutated or deleted once appended. The store
    caps at max_records by dropping the oldest entries (FIFO eviction).
    Supports meta-goal grouping via type-to-meta mappings.
    """

    def __init__(
        self,
        *,
        max_records: int = _DEFAULT_MAX_RECORDS,
    ) -> None:
        self._records: list[GoalRecord] = []
        self._max_records = max(
            _MIN_MAX_RECORDS,
            min(_MAX_MAX_RECORDS, max_records),
        )
        self._type_to_meta: dict[str, list[str]] = {}

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def max_records(self) -> int:
        return self._max_records

    def append(self, record: GoalRecord) -> None:
        """Append a record. Evicts oldest if at capacity."""
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

    def get_all(self) -> list[GoalRecord]:
        """Return a copy of all records."""
        return list(self._records)

    def query_by_type(self, goal_type: str) -> list[GoalRecord]:
        """Return all records matching the given goal type."""
        return [r for r in self._records if r.goal_type == goal_type]

    def query_by_goal_id(self, goal_id: str) -> list[GoalRecord]:
        """Return all records for a specific goal ID."""
        return [r for r in self._records if r.goal_id == goal_id]

    def get_types(self) -> list[str]:
        """Return sorted list of distinct goal types."""
        return sorted({r.goal_type for r in self._records})

    def compute_stats(self, goal_type: str) -> GoalTypeStats | None:
        """Compute aggregate statistics for a goal type. Returns None if no records."""
        records = self.query_by_type(goal_type)
        if not records:
            return None

        count = len(records)
        completed_count = sum(1 for r in records if r.completed)
        completion_rate = completed_count / count

        avg_duration = sum(r.duration_ticks for r in records) / count
        avg_success = sum(r.success_rate for r in records) / count
        avg_alignment = sum(r.identity_alignment for r in records) / count
        avg_reward = sum(r.reward for r in records) / count

        return GoalTypeStats(
            goal_type=goal_type,
            count=count,
            completion_rate=completion_rate,
            avg_duration=avg_duration,
            avg_success_rate=avg_success,
            avg_identity_alignment=avg_alignment,
            avg_reward=avg_reward,
        )

    def compute_all_stats(self) -> list[GoalTypeStats]:
        """Compute statistics for all known goal types."""
        stats: list[GoalTypeStats] = []
        for goal_type in self.get_types():
            s = self.compute_stats(goal_type)
            if s is not None:
                stats.append(s)
        return stats

    def set_type_meta_mapping(self, goal_type: str, meta_goal_names: list[str]) -> None:
        """Register which meta-goals a goal type belongs to."""
        self._type_to_meta[goal_type] = list(meta_goal_names)

    def get_meta_goals_for_type(self, goal_type: str) -> list[str]:
        """Get meta-goal names for a goal type."""
        return list(self._type_to_meta.get(goal_type, []))

    def query_by_meta_goal(self, meta_goal_name: str) -> list[GoalRecord]:
        """Return all records whose goal_type maps to the given meta-goal."""
        matching_types = {gt for gt, metas in self._type_to_meta.items() if meta_goal_name in metas}
        return [r for r in self._records if r.goal_type in matching_types]

    def compute_grouped_stats(self, meta_goal_name: str) -> list[GoalTypeStats]:
        """Compute per-type statistics for all types under a meta-goal."""
        matching_types = {gt for gt, metas in self._type_to_meta.items() if meta_goal_name in metas}
        result: list[GoalTypeStats] = []
        for gt in sorted(matching_types):
            s = self.compute_stats(gt)
            if s is not None:
                result.append(s)
        return result

    def clear(self) -> None:
        """Clear all records and mappings."""
        self._records.clear()
        self._type_to_meta.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "max_records": self._max_records,
            "types": self.get_types(),
            "type_to_meta": {k: list(v) for k, v in sorted(self._type_to_meta.items())},
            "records": [r.to_dict() for r in self._records],
        }
