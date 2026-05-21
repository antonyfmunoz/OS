"""Planner — lightweight scheduling decision layer with adaptive learning.

Bridges the priority scoring system with the job store and worker
claim flow. Provides a ranker callback for claim_job() that orders
jobs by priority score instead of FIFO. When adaptive weights are
provided, incorporates learned node performance into scoring.

Pure decision functions — no state mutation, no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from umh.jobs.models import ExecutionJob, JobStatus
from umh.jobs.priority import (
    JobPriority,
    NodeCapability,
    ScoredJob,
    rank_jobs,
    score_job,
    select_best_job,
)
from umh.jobs.store import JobStore
from umh.runtime.strategy import ExecutionStrategy


def make_ranker(
    node: NodeCapability | None = None,
    *,
    now: datetime | None = None,
    weights: Any | None = None,
) -> Any:
    """Create a ranker callback for JobStore.claim_job().

    Returns a callable that accepts a list of ExecutionJobs and returns
    them sorted by priority score (highest first). When weights are
    provided, applies learned node adjustments to scores.
    """
    ref = now or datetime.now(timezone.utc)

    def _rank(jobs: list[ExecutionJob]) -> list[ExecutionJob]:
        scored = rank_jobs(jobs, node, now=ref)
        if weights is not None and node is not None:
            adjustment = weights.get_node_adjustment(node.node_id)
            if adjustment != 0.0:
                adjusted = []
                for s in scored:
                    new_score = s.score + adjustment
                    adjusted.append(
                        ScoredJob(
                            job=s.job,
                            score=new_score,
                            priority_weight=s.priority_weight,
                            wait_bonus=s.wait_bonus,
                            urgency_bonus=s.urgency_bonus,
                            node_fit=s.node_fit,
                            cost_penalty=s.cost_penalty,
                        )
                    )
                adjusted.sort(key=lambda s: (-s.score, s.job.job_id))
                return [s.job for s in adjusted]
        return [s.job for s in scored]

    return _rank


def adaptive_score(
    job: ExecutionJob,
    node: NodeCapability | None = None,
    *,
    weights: Any | None = None,
    now: datetime | None = None,
) -> ScoredJob:
    """Score a job with adaptive weight adjustments. Pure function.

    Applies the base score_job(), then adjusts based on learned
    weights (node bonuses/penalties, weight multipliers).
    """
    ref = now or datetime.now(timezone.utc)
    base = score_job(job, node, now=ref)

    if weights is None:
        return base

    adjusted_priority = base.priority_weight * weights.priority_weight
    adjusted_wait = base.wait_bonus * weights.wait_time_weight
    adjusted_fit = base.node_fit * weights.node_fit_weight
    adjusted_cost = base.cost_penalty * weights.cost_weight

    node_adj = 0.0
    if node is not None:
        node_adj = weights.get_node_adjustment(node.node_id)

    total = (
        adjusted_priority
        + adjusted_wait
        + base.urgency_bonus
        + adjusted_fit
        - adjusted_cost
        + node_adj
    )

    return ScoredJob(
        job=base.job,
        score=total,
        priority_weight=adjusted_priority,
        wait_bonus=adjusted_wait,
        urgency_bonus=base.urgency_bonus,
        node_fit=adjusted_fit,
        cost_penalty=adjusted_cost,
    )


class SchedulingPlanner:
    """Stateless scheduling advisor with optional adaptive learning.

    Evaluates candidate jobs and nodes and returns scheduling
    decisions. Does NOT mutate any state — the caller is
    responsible for acting on recommendations. When weights
    are provided, learned adjustments influence scoring.
    """

    def plan_next(
        self,
        store: JobStore,
        nodes: list[NodeCapability] | None = None,
        *,
        weights: Any | None = None,
        now: datetime | None = None,
    ) -> tuple[ExecutionJob, str] | None:
        """Recommend the best (job, node_id) pair from the store.

        Reads SUBMITTED jobs from the store, scores them against
        available nodes, and returns the best combination.
        Does NOT claim or transition — that's the caller's job.
        """
        ref = now or datetime.now(timezone.utc)
        submitted = store.list_jobs(status=JobStatus.SUBMITTED)
        if not submitted:
            return None

        if weights is None:
            return select_best_job(submitted, nodes, now=ref)

        best_scored: ScoredJob | None = None
        best_node_id: str = ""

        if nodes:
            for node in nodes:
                for job in submitted:
                    scored = adaptive_score(job, node, weights=weights, now=ref)
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
            for job in submitted:
                scored = adaptive_score(job, weights=weights, now=ref)
                if best_scored is None or (
                    scored.score > best_scored.score
                    or (
                        scored.score == best_scored.score
                        and scored.job.job_id < best_scored.job.job_id
                    )
                ):
                    best_scored = scored

        if best_scored is None:
            return None
        return (best_scored.job, best_node_id)

    def score_candidates(
        self,
        jobs: list[ExecutionJob],
        nodes: list[NodeCapability] | None = None,
        *,
        weights: Any | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Score all job/node combinations and return detailed breakdown.

        For observability — lets the caller see WHY the scheduler
        made its decision. Uses adaptive scoring when weights provided.
        """
        ref = now or datetime.now(timezone.utc)
        results: list[dict[str, Any]] = []

        if nodes:
            for node in nodes:
                for job in jobs:
                    scored = adaptive_score(job, node, weights=weights, now=ref)
                    results.append(
                        {
                            "job_id": job.job_id,
                            "node_id": node.node_id,
                            "score": scored.score,
                            "priority_weight": scored.priority_weight,
                            "wait_bonus": scored.wait_bonus,
                            "urgency_bonus": scored.urgency_bonus,
                            "node_fit": scored.node_fit,
                            "cost_penalty": scored.cost_penalty,
                        }
                    )
        else:
            for job in jobs:
                scored = adaptive_score(job, weights=weights, now=ref)
                results.append(
                    {
                        "job_id": job.job_id,
                        "node_id": "",
                        "score": scored.score,
                        "priority_weight": scored.priority_weight,
                        "wait_bonus": scored.wait_bonus,
                        "urgency_bonus": scored.urgency_bonus,
                        "node_fit": scored.node_fit,
                        "cost_penalty": scored.cost_penalty,
                    }
                )

        results.sort(key=lambda r: (-r["score"], r["job_id"]))
        return results

    def plan_batch(
        self,
        store: JobStore,
        nodes: list[NodeCapability] | None = None,
        *,
        weights: Any | None = None,
        strategy: ExecutionStrategy | None = None,
        now: datetime | None = None,
    ) -> list[tuple[ExecutionJob, str]]:
        """Select a batch of (job, node_id) pairs respecting strategy limits.

        Uses strategy.batch_size to cap the result count and
        strategy.priority_bias to adjust scores. Returns an empty
        list when no SUBMITTED jobs exist. Does NOT mutate store.
        """
        ref = now or datetime.now(timezone.utc)
        submitted = store.list_jobs(status=JobStatus.SUBMITTED)
        if not submitted:
            return []

        limit = strategy.batch_size if strategy is not None else _DEFAULT_BATCH_SIZE
        bias = strategy.priority_bias if strategy is not None else 0.0

        scored_pairs: list[tuple[ScoredJob, str]] = []

        if nodes:
            for node in nodes:
                for job in submitted:
                    scored = adaptive_score(job, node, weights=weights, now=ref)
                    if bias != 0.0:
                        scored = ScoredJob(
                            job=scored.job,
                            score=scored.score + bias,
                            priority_weight=scored.priority_weight,
                            wait_bonus=scored.wait_bonus,
                            urgency_bonus=scored.urgency_bonus,
                            node_fit=scored.node_fit,
                            cost_penalty=scored.cost_penalty,
                        )
                    scored_pairs.append((scored, node.node_id))
        else:
            for job in submitted:
                scored = adaptive_score(job, weights=weights, now=ref)
                if bias != 0.0:
                    scored = ScoredJob(
                        job=scored.job,
                        score=scored.score + bias,
                        priority_weight=scored.priority_weight,
                        wait_bonus=scored.wait_bonus,
                        urgency_bonus=scored.urgency_bonus,
                        node_fit=scored.node_fit,
                        cost_penalty=scored.cost_penalty,
                    )
                scored_pairs.append((scored, ""))

        scored_pairs.sort(key=lambda sp: (-sp[0].score, sp[0].job.job_id))

        seen_jobs: set[str] = set()
        result: list[tuple[ExecutionJob, str]] = []
        for scored, node_id in scored_pairs:
            if scored.job.job_id in seen_jobs:
                continue
            seen_jobs.add(scored.job.job_id)
            result.append((scored.job, node_id))
            if len(result) >= limit:
                break

        return result


_DEFAULT_BATCH_SIZE = 5
