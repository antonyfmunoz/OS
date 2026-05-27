"""Execution Economy — runtime cost/value tracking and leverage scoring.

Every execution through the organism produces an ExecutionDecisionRecord
that captures: which runtime was selected, what alternatives existed,
the cost estimate, latency, quality score, and leverage score. Over time,
this data enables RuntimeGraph to learn which runtimes perform best for
which task classes.

The economy is deterministic-first: scoring uses weighted formulas with
configurable weights. No LLM calls.

Metrics tracked per runtime per task class:
  - success rate
  - average latency
  - average quality score
  - cost efficiency (value / cost)
  - leverage score (time saved vs manual execution)

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExecutionClass(str, Enum):
    DETERMINISTIC = "deterministic"
    AGENT = "agent"
    ADVISOR_DELEGATION = "advisor_delegation"
    RECURSIVE_IMPROVEMENT = "recursive_improvement"
    EXTERNAL_LEVERAGE = "external_leverage"
    PRODUCTION_IMPACT = "production_impact"


class VerificationResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ExecutionCost:
    compute_cost_usd: float = 0.0
    token_cost_usd: float = 0.0
    wall_clock_ms: int = 0
    is_subscription: bool = False

    @property
    def total_usd(self) -> float:
        if self.is_subscription:
            return 0.0
        return self.compute_cost_usd + self.token_cost_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "compute_cost_usd": round(self.compute_cost_usd, 6),
            "token_cost_usd": round(self.token_cost_usd, 6),
            "total_usd": round(self.total_usd, 6),
            "wall_clock_ms": self.wall_clock_ms,
            "is_subscription": self.is_subscription,
        }


@dataclass
class ExecutionValue:
    quality_score: float = 0.0
    completeness: float = 0.0
    correctness: float = 0.0
    time_saved_minutes: float = 0.0

    @property
    def composite(self) -> float:
        return (
            0.40 * self.quality_score
            + 0.30 * self.completeness
            + 0.30 * self.correctness
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "quality_score": round(self.quality_score, 3),
            "completeness": round(self.completeness, 3),
            "correctness": round(self.correctness, 3),
            "composite": round(self.composite, 3),
            "time_saved_minutes": round(self.time_saved_minutes, 1),
        }


@dataclass
class RuntimeBenchmark:
    runtime_id: str = ""
    task_class: str = ""
    executions: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: int = 0
    total_quality: float = 0.0
    total_cost_usd: float = 0.0
    total_time_saved_min: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.executions == 0:
            return 0.0
        return self.successes / self.executions

    @property
    def avg_latency_ms(self) -> float:
        if self.successes == 0:
            return 0.0
        return self.total_latency_ms / self.successes

    @property
    def avg_quality(self) -> float:
        if self.successes == 0:
            return 0.0
        return self.total_quality / self.successes

    @property
    def cost_efficiency(self) -> float:
        if self.total_cost_usd <= 0:
            return float("inf") if self.total_quality > 0 else 0.0
        return self.total_quality / self.total_cost_usd

    @property
    def leverage_score(self) -> float:
        if self.executions == 0:
            return 0.0
        time_factor = min(self.total_time_saved_min / max(self.executions, 1), 60) / 60
        quality_factor = self.avg_quality
        reliability_factor = self.success_rate
        return (
            0.35 * time_factor
            + 0.35 * quality_factor
            + 0.30 * reliability_factor
        )

    def record(
        self,
        success: bool,
        latency_ms: int = 0,
        quality: float = 0.0,
        cost_usd: float = 0.0,
        time_saved_min: float = 0.0,
    ) -> None:
        self.executions += 1
        if success:
            self.successes += 1
            self.total_latency_ms += latency_ms
            self.total_quality += quality
            self.total_time_saved_min += time_saved_min
        else:
            self.failures += 1
        self.total_cost_usd += cost_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "task_class": self.task_class,
            "executions": self.executions,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_quality": round(self.avg_quality, 3),
            "cost_efficiency": round(self.cost_efficiency, 3)
            if self.cost_efficiency != float("inf")
            else "infinite",
            "leverage_score": round(self.leverage_score, 3),
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_time_saved_min": round(self.total_time_saved_min, 1),
        }


@dataclass
class RuntimePerformanceProfile:
    runtime_id: str = ""
    benchmarks: dict[str, RuntimeBenchmark] = field(default_factory=dict)

    @property
    def overall_leverage(self) -> float:
        if not self.benchmarks:
            return 0.0
        scores = [b.leverage_score for b in self.benchmarks.values()]
        return sum(scores) / len(scores)

    @property
    def total_executions(self) -> int:
        return sum(b.executions for b in self.benchmarks.values())

    def get_benchmark(self, task_class: str) -> RuntimeBenchmark:
        if task_class not in self.benchmarks:
            self.benchmarks[task_class] = RuntimeBenchmark(
                runtime_id=self.runtime_id,
                task_class=task_class,
            )
        return self.benchmarks[task_class]

    def best_task_class(self) -> str:
        if not self.benchmarks:
            return ""
        return max(
            self.benchmarks,
            key=lambda k: self.benchmarks[k].leverage_score,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "overall_leverage": round(self.overall_leverage, 3),
            "total_executions": self.total_executions,
            "best_task_class": self.best_task_class(),
            "benchmarks": {k: v.to_dict() for k, v in self.benchmarks.items()},
        }


@dataclass
class TaskExecutionProfile:
    task_class: str = ""
    best_runtime: str = ""
    best_leverage: float = 0.0
    runtime_rankings: list[tuple[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_class": self.task_class,
            "best_runtime": self.best_runtime,
            "best_leverage": round(self.best_leverage, 3),
            "runtime_rankings": [
                {"runtime_id": r, "leverage": round(s, 3)}
                for r, s in self.runtime_rankings
            ],
        }


@dataclass
class ExecutionDecisionRecord:
    id: str = ""
    runtime_selected: str = ""
    alternatives_considered: list[str] = field(default_factory=list)
    task_class: str = ""
    execution_class: ExecutionClass = ExecutionClass.DETERMINISTIC
    cost: ExecutionCost = field(default_factory=ExecutionCost)
    value: ExecutionValue = field(default_factory=ExecutionValue)
    latency_ms: int = 0
    success: bool = False
    retry_count: int = 0
    confidence: float = 0.0
    verification: VerificationResult = VerificationResult.SKIPPED
    governance_class: str = ""
    human_attention_required: bool = False
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"edr-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    @property
    def leverage_score(self) -> float:
        cost_factor = 1.0 / (1.0 + self.cost.total_usd * 100)
        latency_factor = 1.0 / (1.0 + self.latency_ms / 5000.0)
        quality_factor = self.value.composite
        success_factor = 1.0 if self.success else 0.0
        return (
            0.30 * quality_factor
            + 0.25 * success_factor
            + 0.25 * cost_factor
            + 0.20 * latency_factor
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "runtime_selected": self.runtime_selected,
            "alternatives_considered": self.alternatives_considered,
            "task_class": self.task_class,
            "execution_class": self.execution_class.value,
            "cost": self.cost.to_dict(),
            "value": self.value.to_dict(),
            "latency_ms": self.latency_ms,
            "success": self.success,
            "retry_count": self.retry_count,
            "confidence": round(self.confidence, 3),
            "verification": self.verification.value,
            "governance_class": self.governance_class,
            "human_attention_required": self.human_attention_required,
            "leverage_score": round(self.leverage_score, 3),
            "created_at": self.created_at,
        }


class ExecutionEconomy:
    """Tracks execution economics across all runtimes and task classes.

    Maintains per-runtime performance profiles and per-task-class
    execution profiles. Produces leverage scores that feed back into
    RuntimeGraph scoring for progressively better runtime selection.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, RuntimePerformanceProfile] = {}
        self._records: list[ExecutionDecisionRecord] = []
        self._max_records = 10000

    def record_execution(self, record: ExecutionDecisionRecord) -> None:
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        profile = self._get_profile(record.runtime_selected)
        benchmark = profile.get_benchmark(record.task_class)
        benchmark.record(
            success=record.success,
            latency_ms=record.latency_ms,
            quality=record.value.composite,
            cost_usd=record.cost.total_usd,
            time_saved_min=record.value.time_saved_minutes,
        )

        logger.info(
            "execution recorded: runtime=%s task=%s success=%s leverage=%.3f",
            record.runtime_selected,
            record.task_class,
            record.success,
            record.leverage_score,
        )

    def get_profile(self, runtime_id: str) -> RuntimePerformanceProfile | None:
        return self._profiles.get(runtime_id)

    def task_execution_profile(self, task_class: str) -> TaskExecutionProfile:
        rankings: list[tuple[str, float]] = []
        for profile in self._profiles.values():
            benchmark = profile.benchmarks.get(task_class)
            if benchmark and benchmark.executions > 0:
                rankings.append((profile.runtime_id, benchmark.leverage_score))

        rankings.sort(key=lambda x: x[1], reverse=True)

        return TaskExecutionProfile(
            task_class=task_class,
            best_runtime=rankings[0][0] if rankings else "",
            best_leverage=rankings[0][1] if rankings else 0.0,
            runtime_rankings=rankings,
        )

    def best_runtime_for_task(self, task_class: str) -> str:
        profile = self.task_execution_profile(task_class)
        return profile.best_runtime

    def recent_records(self, limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._records[-limit:]]

    def economy_summary(self) -> dict[str, Any]:
        total_cost = sum(r.cost.total_usd for r in self._records)
        total_time_saved = sum(r.value.time_saved_minutes for r in self._records)
        successes = sum(1 for r in self._records if r.success)
        total = len(self._records)

        return {
            "total_executions": total,
            "success_rate": round(successes / max(total, 1), 3),
            "total_cost_usd": round(total_cost, 4),
            "total_time_saved_minutes": round(total_time_saved, 1),
            "avg_leverage_score": round(
                sum(r.leverage_score for r in self._records) / max(total, 1),
                3,
            ),
            "runtime_profiles": {
                k: v.to_dict() for k, v in self._profiles.items()
            },
        }

    def _get_profile(self, runtime_id: str) -> RuntimePerformanceProfile:
        if runtime_id not in self._profiles:
            self._profiles[runtime_id] = RuntimePerformanceProfile(
                runtime_id=runtime_id,
            )
        return self._profiles[runtime_id]

    def to_dict(self) -> dict[str, Any]:
        return self.economy_summary()
