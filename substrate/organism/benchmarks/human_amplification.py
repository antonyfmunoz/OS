"""Human Amplification Benchmark — does the operator become more capable?

Campaign 23B. Category S. Tier 5: Strategic Metric.
Measures capability expansion, not just speed improvement. Compression = less work.
Amplification = more capability. Could a non-technical founder build software through UMH?

Deterministic. No LLM calls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class SkillLevel:
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"
    ALL = frozenset({"novice", "intermediate", "expert"})


class TaskComplexity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    ALL = frozenset({"low", "medium", "high", "extreme"})
    RANK = {"low": 1, "medium": 2, "high": 3, "extreme": 4}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AmplificationRecord:
    """A single task attempt and whether UMH amplified the operator."""

    record_id: str = ""
    operator_skill_level: str = ""  # SkillLevel
    task_complexity: str = ""  # TaskComplexity
    task_completed: bool = False
    quality_score: float = 0.0  # 0.0-1.0
    would_need_specialist_without: bool = False  # operator couldn't do this alone

    def complexity_rank(self) -> int:
        """Return the numeric rank of this record's complexity (0 if unknown)."""
        return TaskComplexity.RANK.get(self.task_complexity, 0)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AmplificationResult:
    """Complete human amplification benchmark result."""

    records_evaluated: int = 0
    capability_expansion_rate: float = 0.0  # specialist tasks completed / total specialist
    quality_by_skill_level: dict[str, float] = field(default_factory=dict)
    completion_by_skill_level: dict[str, float] = field(default_factory=dict)
    complexity_ceiling_with_umh: int = 0  # highest complexity completed (1-4)
    complexity_ceiling_without: int = 0  # highest complexity possible without UMH
    amplification_ratio: float = 0.0  # ceiling_with / max(ceiling_without, 1)
    specialist_tasks_completed: int = 0
    total_specialist_tasks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

class HumanAmplificationBenchmark:
    """Measures whether UMH expands operator capability beyond their baseline."""

    def evaluate(self, records: list[AmplificationRecord]) -> AmplificationResult:
        """Evaluate amplification records into capability-expansion metrics."""
        if not records:
            return AmplificationResult()

        # Specialist task capability expansion.
        specialist = [r for r in records if r.would_need_specialist_without]
        total_specialist = len(specialist)
        specialist_completed = sum(1 for r in specialist if r.task_completed)
        expansion_rate = (
            specialist_completed / total_specialist if total_specialist > 0 else 0.0
        )

        # Quality and completion grouped by skill level.
        quality_by_skill: dict[str, float] = {}
        completion_by_skill: dict[str, float] = {}
        for level in sorted(SkillLevel.ALL):
            group = [r for r in records if r.operator_skill_level == level]
            if not group:
                continue
            quality_by_skill[level] = round(
                sum(r.quality_score for r in group) / len(group), 4
            )
            completion_by_skill[level] = round(
                sum(1 for r in group if r.task_completed) / len(group), 4
            )

        # Complexity ceilings.
        ceiling_with = 0
        ceiling_without = 0
        for r in records:
            if not r.task_completed:
                continue
            rank = r.complexity_rank()
            ceiling_with = max(ceiling_with, rank)
            # Without UMH: only tasks that did NOT require a specialist count.
            if not r.would_need_specialist_without:
                ceiling_without = max(ceiling_without, rank)

        amplification_ratio = round(ceiling_with / max(ceiling_without, 1), 4)

        return AmplificationResult(
            records_evaluated=len(records),
            capability_expansion_rate=round(expansion_rate, 4),
            quality_by_skill_level=quality_by_skill,
            completion_by_skill_level=completion_by_skill,
            complexity_ceiling_with_umh=ceiling_with,
            complexity_ceiling_without=ceiling_without,
            amplification_ratio=amplification_ratio,
            specialist_tasks_completed=specialist_completed,
            total_specialist_tasks=total_specialist,
        )
