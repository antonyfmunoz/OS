"""Job priority model and scoring — deterministic priority-aware scheduling.

Pure functions: same inputs always produce same outputs.
No side effects, no state mutation, no I/O.

Scoring factors:
  1. Priority weight (CRITICAL > HIGH > NORMAL > LOW > BACKGROUND)
  2. Wait time aging (prevents starvation)
  3. Deadline urgency (bonus as deadline approaches)
  4. Node suitability (resource fit)
  5. Cost penalty (expensive jobs on capable nodes)

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any

from umh.jobs.models import ExecutionJob


@unique
class JobPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


_PRIORITY_WEIGHTS: dict[JobPriority, float] = {
    JobPriority.CRITICAL: 1000.0,
    JobPriority.HIGH: 100.0,
    JobPriority.NORMAL: 10.0,
    JobPriority.LOW: 1.0,
    JobPriority.BACKGROUND: 0.1,
}

_AGING_RATE_PER_SECOND = 0.05
_DEADLINE_URGENCY_MAX = 500.0
_COST_PENALTY_WEIGHT = 0.5
_NODE_FIT_BONUS = 5.0


def get_priority(job: ExecutionJob) -> JobPriority:
    """Extract priority from job metadata, defaulting to NORMAL."""
    raw = job.metadata.get("priority", "normal")
    if isinstance(raw, JobPriority):
        return raw
    try:
        return JobPriority(str(raw).lower())
    except ValueError:
        return JobPriority.NORMAL


def get_deadline(job: ExecutionJob) -> datetime | None:
    """Extract deadline from job metadata, or None if unset."""
    raw = job.metadata.get("deadline")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw
    try:
        dt = datetime.fromisoformat(str(raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def get_estimated_cost(job: ExecutionJob) -> float:
    """Extract estimated cost from job metadata, defaulting to 0."""
    raw = job.metadata.get("estimated_cost", 0.0)
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


@dataclass(frozen=True)
class NodeCapability:
    """Simplified node capability snapshot for scoring."""

    node_id: str
    cpu_cores: float = 4.0
    memory_mb: int = 8192
    current_load: float = 0.0
    gpu: bool = False


@dataclass(frozen=True)
class ScoredJob:
    """A job with its computed score and breakdown."""

    job: ExecutionJob
    score: float
    priority_weight: float
    wait_bonus: float
    urgency_bonus: float
    node_fit: float
    cost_penalty: float


def score_job(
    job: ExecutionJob,
    node: NodeCapability | None = None,
    *,
    now: datetime | None = None,
) -> ScoredJob:
    """Score a job for scheduling. Pure function — no side effects."""
    ref = now or datetime.now(timezone.utc)

    priority = get_priority(job)
    priority_weight = _PRIORITY_WEIGHTS[priority]

    wait_bonus = _compute_wait_bonus(job, ref)
    urgency_bonus = _compute_urgency_bonus(job, ref)
    node_fit = _compute_node_fit(job, node) if node is not None else 0.0
    cost_penalty = _compute_cost_penalty(job, node) if node is not None else 0.0

    total = priority_weight + wait_bonus + urgency_bonus + node_fit - cost_penalty

    return ScoredJob(
        job=job,
        score=total,
        priority_weight=priority_weight,
        wait_bonus=wait_bonus,
        urgency_bonus=urgency_bonus,
        node_fit=node_fit,
        cost_penalty=cost_penalty,
    )


def rank_jobs(
    jobs: list[ExecutionJob],
    node: NodeCapability | None = None,
    *,
    now: datetime | None = None,
) -> list[ScoredJob]:
    """Rank jobs by score, highest first. Deterministic tie-breaking by job_id."""
    ref = now or datetime.now(timezone.utc)
    scored = [score_job(j, node, now=ref) for j in jobs]
    scored.sort(key=lambda s: (-s.score, s.job.job_id))
    return scored


def select_best_job(
    jobs: list[ExecutionJob],
    nodes: list[NodeCapability] | None = None,
    *,
    now: datetime | None = None,
) -> tuple[ExecutionJob, str] | None:
    """Select the best (job, node_id) pair. Returns None if no jobs.

    Evaluates every job against every node (or without nodes if none
    provided) and picks the highest-scoring combination.
    """
    if not jobs:
        return None

    ref = now or datetime.now(timezone.utc)

    best_scored: ScoredJob | None = None
    best_node_id: str = ""

    if nodes:
        for node in nodes:
            for job in jobs:
                scored = score_job(job, node, now=ref)
                if best_scored is None or (
                    scored.score > best_scored.score
                    or (
                        scored.score == best_scored.score
                        and scored.job.job_id < best_scored.job.job_id
                    )
                ):
                    best_scored = scored
                    best_node_id = node.node_id
    else:
        ranked = rank_jobs(jobs, now=ref)
        if ranked:
            best_scored = ranked[0]

    if best_scored is None:
        return None

    return (best_scored.job, best_node_id)


def _compute_wait_bonus(job: ExecutionJob, ref: datetime) -> float:
    """Aging bonus — older jobs gain priority to prevent starvation."""
    timestamp = job.submitted_at or job.created_at
    if not timestamp:
        return 0.0
    try:
        created = datetime.fromisoformat(timestamp)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        wait_seconds = max(0.0, (ref - created).total_seconds())
        return wait_seconds * _AGING_RATE_PER_SECOND
    except (ValueError, TypeError):
        return 0.0


def _compute_urgency_bonus(job: ExecutionJob, ref: datetime) -> float:
    """Deadline urgency — higher score as deadline approaches."""
    deadline = get_deadline(job)
    if deadline is None:
        return 0.0

    remaining = (deadline - ref).total_seconds()
    if remaining <= 0:
        return _DEADLINE_URGENCY_MAX

    if remaining < 60:
        return _DEADLINE_URGENCY_MAX * 0.9
    if remaining < 300:
        return _DEADLINE_URGENCY_MAX * 0.7
    if remaining < 3600:
        return _DEADLINE_URGENCY_MAX * 0.3
    return 0.0


def _compute_node_fit(job: ExecutionJob, node: NodeCapability) -> float:
    """Bonus for node resource suitability."""
    cost = get_estimated_cost(job)

    if cost > 5.0 and node.cpu_cores >= 4:
        return _NODE_FIT_BONUS
    if cost <= 1.0 and node.current_load < 0.5:
        return _NODE_FIT_BONUS * 0.5
    return 0.0


def _compute_cost_penalty(job: ExecutionJob, node: NodeCapability) -> float:
    """Penalty when a heavy job is sent to an underpowered node."""
    cost = get_estimated_cost(job)
    if cost <= 0:
        return 0.0

    if cost > 5.0 and node.cpu_cores < 2:
        return cost * _COST_PENALTY_WEIGHT
    if cost > 5.0 and node.current_load > 0.8:
        return cost * _COST_PENALTY_WEIGHT * 0.5
    return 0.0
