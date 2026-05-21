"""Metrics aggregation — computes node and job type performance stats.

Pure computation from feedback records. No side effects, no I/O.
All methods are deterministic given the same input.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.learning.feedback import ExecutionFeedback, FeedbackStore


@dataclass(frozen=True)
class NodeMetrics:
    """Aggregated performance metrics for a single node."""

    node_id: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    avg_duration_ms: float
    success_rate: float
    retry_rate: float
    avg_retries: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "success_rate": round(self.success_rate, 4),
            "retry_rate": round(self.retry_rate, 4),
            "avg_retries": round(self.avg_retries, 2),
        }


@dataclass(frozen=True)
class JobTypeMetrics:
    """Aggregated performance metrics for a job type."""

    task_type: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    avg_duration_ms: float
    failure_rate: float
    avg_retries: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "failure_rate": round(self.failure_rate, 4),
            "avg_retries": round(self.avg_retries, 2),
        }


def compute_node_metrics(feedback: list[ExecutionFeedback]) -> NodeMetrics | None:
    """Compute metrics for a single node from its feedback records."""
    if not feedback:
        return None

    node_id = feedback[0].node_id
    total = len(feedback)
    successes = sum(1 for f in feedback if f.success)
    failures = total - successes
    total_retries = sum(f.retries for f in feedback)
    jobs_with_retries = sum(1 for f in feedback if f.retries > 0)

    durations = [f.duration_ms for f in feedback if f.duration_ms > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return NodeMetrics(
        node_id=node_id,
        total_jobs=total,
        successful_jobs=successes,
        failed_jobs=failures,
        avg_duration_ms=avg_duration,
        success_rate=successes / total if total > 0 else 0.0,
        retry_rate=jobs_with_retries / total if total > 0 else 0.0,
        avg_retries=total_retries / total if total > 0 else 0.0,
    )


def compute_job_type_metrics(feedback: list[ExecutionFeedback]) -> JobTypeMetrics | None:
    """Compute metrics for a single job type from its feedback records."""
    if not feedback:
        return None

    task_type = feedback[0].task_type
    total = len(feedback)
    successes = sum(1 for f in feedback if f.success)
    failures = total - successes
    total_retries = sum(f.retries for f in feedback)

    durations = [f.duration_ms for f in feedback if f.duration_ms > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return JobTypeMetrics(
        task_type=task_type,
        total_jobs=total,
        successful_jobs=successes,
        failed_jobs=failures,
        avg_duration_ms=avg_duration,
        failure_rate=failures / total if total > 0 else 0.0,
        avg_retries=total_retries / total if total > 0 else 0.0,
    )


class MetricsAggregator:
    """Computes metrics from a FeedbackStore. Stateless — recomputes on every call."""

    def node_metrics(self, store: FeedbackStore) -> dict[str, NodeMetrics]:
        """Compute metrics for all nodes."""
        result: dict[str, NodeMetrics] = {}
        for node_id in store.node_ids:
            records = store.get_for_node(node_id)
            metrics = compute_node_metrics(records)
            if metrics is not None:
                result[node_id] = metrics
        return result

    def job_type_metrics(self, store: FeedbackStore) -> dict[str, JobTypeMetrics]:
        """Compute metrics for all job types."""
        result: dict[str, JobTypeMetrics] = {}
        for task_type in store.task_types:
            records = store.get_for_task_type(task_type)
            metrics = compute_job_type_metrics(records)
            if metrics is not None:
                result[task_type] = metrics
        return result

    def node_success_rate(self, store: FeedbackStore, node_id: str) -> float:
        """Get success rate for a specific node. Returns 0.5 if no data."""
        records = store.get_for_node(node_id)
        if not records:
            return 0.5
        return sum(1 for f in records if f.success) / len(records)

    def node_avg_duration(self, store: FeedbackStore, node_id: str) -> float:
        """Get average duration for a specific node. Returns 0.0 if no data."""
        records = store.get_for_node(node_id)
        durations = [f.duration_ms for f in records if f.duration_ms > 0]
        return sum(durations) / len(durations) if durations else 0.0
