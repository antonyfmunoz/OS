"""GoalStore — canonical write API for the goals and goal_outcomes tables."""

import json

from substrate.state.storage.db import get_conn


class GoalStore:
    def upsert_goal(
        self,
        org_id: str,
        goal_id: str,
        title: str,
        description: str,
        state: str,
        priority: str,
        expected_impact: float,
        estimated_cost: float,
        confidence: float,
        dependency_unlock: float,
        venture_id: str,
        blocked_by: list,
        score: float,
        rank: int,
        score_explanation: dict,
        performance: dict,
        created_at: str,
        updated_at: str,
    ) -> None:
        """Full upsert of a goal (18 columns). ON CONFLICT updates all mutable fields."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO goals (
                    id, org_id, title, description, state,
                    priority, expected_impact, estimated_cost,
                    confidence, dependency_unlock, venture_id,
                    blocked_by, score, rank, score_explanation,
                    performance, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    state = EXCLUDED.state,
                    priority = EXCLUDED.priority,
                    expected_impact = EXCLUDED.expected_impact,
                    estimated_cost = EXCLUDED.estimated_cost,
                    confidence = EXCLUDED.confidence,
                    dependency_unlock = EXCLUDED.dependency_unlock,
                    venture_id = EXCLUDED.venture_id,
                    blocked_by = EXCLUDED.blocked_by,
                    score = EXCLUDED.score,
                    rank = EXCLUDED.rank,
                    score_explanation = EXCLUDED.score_explanation,
                    performance = EXCLUDED.performance,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    goal_id,
                    org_id,
                    title,
                    description,
                    state,
                    priority,
                    expected_impact,
                    estimated_cost,
                    confidence,
                    dependency_unlock,
                    venture_id,
                    json.dumps(blocked_by),
                    score,
                    rank,
                    json.dumps(score_explanation),
                    json.dumps(performance),
                    created_at,
                    updated_at,
                ),
            )

    def batch_update_rankings(
        self,
        org_id: str,
        goals: list[dict],
    ) -> None:
        """Batch update goal rankings in one transaction. Each dict must have 'id' plus ranking fields."""
        with get_conn(org_id) as cur:
            for g in goals:
                cur.execute(
                    """
                    UPDATE goals SET
                        state = %s, score = %s, rank = %s,
                        score_explanation = %s, dependency_unlock = %s,
                        performance = %s, horizons = %s,
                        updated_at = %s,
                        opportunity_cost_adjustment = %s,
                        swap_pressure_cycles = %s,
                        stability_bonus = %s,
                        horizon_adjustments = %s,
                        failure_streak = %s,
                        priority_decay_multiplier = %s
                    WHERE id = %s AND org_id = %s
                    """,
                    (
                        g["state"],
                        g["score"],
                        g["rank"],
                        json.dumps(g["score_explanation"]),
                        g["dependency_unlock"],
                        json.dumps(g["performance"]),
                        json.dumps(g["horizons"]),
                        g["updated_at"],
                        g["opportunity_cost_adjustment"],
                        g["swap_pressure_cycles"],
                        g["stability_bonus"],
                        json.dumps(g["horizon_adjustments"]),
                        g["failure_streak"],
                        g["priority_decay_multiplier"],
                        g["id"],
                        org_id,
                    ),
                )

    def update_performance(
        self,
        org_id: str,
        goal_id: str,
        performance: dict,
        horizons: dict,
        failure_streak: int,
        priority_decay_multiplier: float,
        updated_at: str,
    ) -> None:
        """Update a goal's performance profile after an outcome."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE goals SET
                    performance = %s, horizons = %s,
                    failure_streak = %s, priority_decay_multiplier = %s,
                    updated_at = %s
                WHERE id = %s AND org_id = %s
                """,
                (
                    json.dumps(performance),
                    json.dumps(horizons),
                    failure_streak,
                    priority_decay_multiplier,
                    updated_at,
                    goal_id,
                    org_id,
                ),
            )

    def insert_outcome(
        self,
        org_id: str,
        goal_id: str,
        outcome_type: str,
        task_type: str,
        execution_time: float,
        impact_delta: float,
        metadata: dict,
    ) -> None:
        """Insert a goal outcome record."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO goal_outcomes
                    (org_id, goal_id, outcome_type, task_type,
                     execution_time, impact_delta, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    org_id,
                    goal_id,
                    outcome_type,
                    task_type,
                    execution_time,
                    impact_delta,
                    json.dumps(metadata),
                ),
            )
