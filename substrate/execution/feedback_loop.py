"""RLHF Feedback Loop — explicit human feedback ingestion and learning cycle.

Builds on substrate/execution/feedback.py (implicit quality scoring from
execution outcomes) by adding explicit human feedback: thumbs up/down,
numeric ratings, outcome labeling. Aggregates this into actionable stats
for routing adjustments and skill effectiveness tracking.

Write path: outcomes table via substrate.state.storage.db.get_conn().
Read path: outcomes + interactions tables with aggregate SQL.

Singleton: get_feedback_loop() returns a process-wide instance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from substrate.state.storage.db import ORG_ID, get_conn

logger = logging.getLogger(__name__)


# ─── Data types ──────────────────────────────────────────────────────────────


class Rating(str, Enum):
    """Human rating scale."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    NUMERIC_1 = "1"
    NUMERIC_2 = "2"
    NUMERIC_3 = "3"
    NUMERIC_4 = "4"
    NUMERIC_5 = "5"


class OutcomeCategory(str, Enum):
    """Categorization of interaction quality."""

    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"
    INCORRECT = "incorrect"
    HARMFUL = "harmful"


# Rating → numeric score for aggregation
_RATING_SCORE: dict[Rating, float] = {
    Rating.THUMBS_UP: 1.0,
    Rating.THUMBS_DOWN: 0.0,
    Rating.NUMERIC_1: 0.2,
    Rating.NUMERIC_2: 0.4,
    Rating.NUMERIC_3: 0.6,
    Rating.NUMERIC_4: 0.8,
    Rating.NUMERIC_5: 1.0,
}

# OutcomeCategory → Neon outcome_type enum value
_CATEGORY_TO_NEON: dict[OutcomeCategory, str] = {
    OutcomeCategory.HELPFUL: "positive",
    OutcomeCategory.UNHELPFUL: "neutral",
    OutcomeCategory.INCORRECT: "negative",
    OutcomeCategory.HARMFUL: "negative",
}


@dataclass
class FeedbackEntry:
    """A single piece of explicit human feedback."""

    interaction_id: str
    rating: Rating
    outcome_type: OutcomeCategory
    notes: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─── FeedbackLoop ────────────────────────────────────────────────────────────


class FeedbackLoop:
    """Ingests explicit human feedback and produces learning signals.

    Write path: outcomes table (same table AgentMemory.log_outcome uses).
    Read path: aggregate queries across outcomes + interactions.
    """

    def record_feedback(self, entry: FeedbackEntry) -> bool:
        """Save feedback to the outcomes table.

        Maps FeedbackEntry to the existing outcomes schema:
        - outcome_type: positive/negative/neutral (Neon enum)
        - outcome_label: the OutcomeCategory value (helpful/unhelpful/etc.)
        - score: numeric score derived from rating
        - notes: human notes + rating info

        Returns True on success, False on failure.
        """
        neon_type = _CATEGORY_TO_NEON[entry.outcome_type]
        score = _RATING_SCORE[entry.rating]
        notes_full = f"[rlhf:{entry.rating.value}] {entry.notes}".strip()

        try:
            with get_conn() as cur:
                # Verify interaction exists (RLS-scoped)
                cur.execute(
                    "SELECT id FROM interactions WHERE id = %s",
                    (entry.interaction_id,),
                )
                if cur.fetchone() is None:
                    logger.warning(
                        "feedback rejected: interaction %s not found",
                        entry.interaction_id,
                    )
                    return False

                cur.execute(
                    """
                    INSERT INTO outcomes
                        (interaction_id, org_id, outcome_type, outcome_label,
                         score, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entry.interaction_id,
                        ORG_ID,
                        neon_type,
                        entry.outcome_type.value,
                        score,
                        notes_full,
                    ),
                )
            logger.info(
                "feedback recorded: interaction=%s rating=%s outcome=%s",
                entry.interaction_id,
                entry.rating.value,
                entry.outcome_type.value,
            )
            return True
        except Exception as exc:
            logger.error("feedback recording failed: %s", exc)
            return False

    def get_feedback_stats(
        self,
        agent: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Aggregate feedback statistics.

        Returns:
            total: count of feedback-tagged outcomes
            positive_rate: fraction of positive outcomes
            by_agent: {agent_label: {total, positive, negative, neutral}}
            by_outcome_type: {outcome_label: count}
        """
        try:
            with get_conn() as cur:
                # Base filter: only RLHF-tagged outcomes (notes starts with [rlhf:)
                agent_filter = ""
                params: list[Any] = [ORG_ID, limit]
                if agent:
                    agent_filter = "AND i.agent_label = %s"
                    params = [ORG_ID, agent, limit]

                # Total + positive rate
                sql = f"""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN o.outcome_type = 'positive' THEN 1 ELSE 0 END)
                            AS positive_count,
                        SUM(CASE WHEN o.outcome_type = 'negative' THEN 1 ELSE 0 END)
                            AS negative_count,
                        SUM(CASE WHEN o.outcome_type = 'neutral' THEN 1 ELSE 0 END)
                            AS neutral_count
                    FROM outcomes o
                    LEFT JOIN interactions i ON i.id = o.interaction_id
                    WHERE o.org_id = %s
                      AND o.notes LIKE '[rlhf:%%'
                      {agent_filter}
                    ORDER BY o.created_at DESC
                    LIMIT %s
                """
                cur.execute(sql, params)
                row = cur.fetchone()
                total = int(row["total"] or 0)
                positive = int(row["positive_count"] or 0)
                negative = int(row["negative_count"] or 0)
                neutral = int(row["neutral_count"] or 0)

                # By agent
                sql_agent = f"""
                    SELECT
                        COALESCE(i.agent_label, 'unknown') AS agent_label,
                        COUNT(*) AS total,
                        SUM(CASE WHEN o.outcome_type = 'positive' THEN 1 ELSE 0 END)
                            AS positive,
                        SUM(CASE WHEN o.outcome_type = 'negative' THEN 1 ELSE 0 END)
                            AS negative,
                        SUM(CASE WHEN o.outcome_type = 'neutral' THEN 1 ELSE 0 END)
                            AS neutral
                    FROM outcomes o
                    LEFT JOIN interactions i ON i.id = o.interaction_id
                    WHERE o.org_id = %s
                      AND o.notes LIKE '[rlhf:%%'
                      {agent_filter}
                    GROUP BY i.agent_label
                    LIMIT %s
                """
                cur.execute(sql_agent, params)
                by_agent: dict[str, dict[str, int]] = {}
                for r in cur.fetchall():
                    by_agent[r["agent_label"]] = {
                        "total": int(r["total"]),
                        "positive": int(r["positive"]),
                        "negative": int(r["negative"]),
                        "neutral": int(r["neutral"]),
                    }

                # By outcome label (helpful/unhelpful/incorrect/harmful)
                sql_label = f"""
                    SELECT
                        o.outcome_label,
                        COUNT(*) AS count
                    FROM outcomes o
                    LEFT JOIN interactions i ON i.id = o.interaction_id
                    WHERE o.org_id = %s
                      AND o.notes LIKE '[rlhf:%%'
                      {agent_filter}
                    GROUP BY o.outcome_label
                    LIMIT %s
                """
                cur.execute(sql_label, params)
                by_outcome_type: dict[str, int] = {}
                for r in cur.fetchall():
                    label = r["outcome_label"] or "unknown"
                    by_outcome_type[label] = int(r["count"])

            return {
                "total": total,
                "positive_rate": round(positive / max(total, 1), 4),
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "by_agent": by_agent,
                "by_outcome_type": by_outcome_type,
            }
        except Exception as exc:
            logger.error("get_feedback_stats failed: %s", exc)
            return {
                "total": 0,
                "positive_rate": 0.0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "by_agent": {},
                "by_outcome_type": {},
                "error": str(exc),
            }

    def skill_effectiveness(
        self,
        agent: str,
        skill: str,
        window_days: int = 30,
    ) -> dict[str, Any]:
        """Track which skills produce positive outcomes for an agent.

        Joins outcomes -> interactions -> skills, filtered by agent_label
        and skill name, within the time window.

        Returns:
            agent, skill, window_days,
            total_interactions, feedback_count, positive_rate,
            avg_score, outcome_distribution
        """
        try:
            with get_conn() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(DISTINCT i.id) AS total_interactions,
                        COUNT(o.id) AS feedback_count,
                        SUM(CASE WHEN o.outcome_type = 'positive' THEN 1 ELSE 0 END)
                            AS positive,
                        SUM(CASE WHEN o.outcome_type = 'negative' THEN 1 ELSE 0 END)
                            AS negative,
                        SUM(CASE WHEN o.outcome_type = 'neutral' THEN 1 ELSE 0 END)
                            AS neutral,
                        AVG(o.score) AS avg_score
                    FROM interactions i
                    LEFT JOIN outcomes o ON o.interaction_id = i.id
                        AND o.notes LIKE '[rlhf:%%'
                    LEFT JOIN skills s ON s.id = i.skill_id
                    WHERE i.agent_label = %s
                      AND s.name = %s
                      AND i.created_at >= NOW() - INTERVAL '%s days'
                      AND i.org_id = %s
                    """,
                    (agent, skill, window_days, ORG_ID),
                )
                row = cur.fetchone()
                total_interactions = int(row["total_interactions"] or 0)
                feedback_count = int(row["feedback_count"] or 0)
                positive = int(row["positive"] or 0)
                negative = int(row["negative"] or 0)
                neutral = int(row["neutral"] or 0)
                avg_score = float(row["avg_score"] or 0.0)

            return {
                "agent": agent,
                "skill": skill,
                "window_days": window_days,
                "total_interactions": total_interactions,
                "feedback_count": feedback_count,
                "positive_rate": round(positive / max(feedback_count, 1), 4),
                "avg_score": round(avg_score, 4),
                "outcome_distribution": {
                    "positive": positive,
                    "negative": negative,
                    "neutral": neutral,
                },
            }
        except Exception as exc:
            logger.error("skill_effectiveness failed: %s", exc)
            return {
                "agent": agent,
                "skill": skill,
                "window_days": window_days,
                "total_interactions": 0,
                "feedback_count": 0,
                "positive_rate": 0.0,
                "avg_score": 0.0,
                "outcome_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "error": str(exc),
            }

    def recommend_routing_adjustment(self) -> list[dict[str, Any]]:
        """Analyze feedback patterns and recommend routing changes.

        Rules (deterministic spine — no LLM):
        1. Agent with < 40% positive rate over 10+ feedbacks -> recommend switch
        2. Skill with avg score < 0.4 over 5+ feedbacks -> recommend disable
        3. Agent with 0 feedback but high interaction count -> recommend monitoring

        Returns list of recommendation dicts with type, agent, rationale, action.
        """
        recommendations: list[dict[str, Any]] = []

        try:
            with get_conn() as cur:
                # Rule 1: agents with poor positive rate
                cur.execute(
                    """
                    SELECT
                        COALESCE(i.agent_label, 'unknown') AS agent_label,
                        COUNT(o.id) AS feedback_count,
                        SUM(CASE WHEN o.outcome_type = 'positive' THEN 1 ELSE 0 END)
                            AS positive,
                        AVG(o.score) AS avg_score
                    FROM outcomes o
                    LEFT JOIN interactions i ON i.id = o.interaction_id
                    WHERE o.org_id = %s
                      AND o.notes LIKE '[rlhf:%%'
                    GROUP BY i.agent_label
                    HAVING COUNT(o.id) >= 10
                    """,
                    (ORG_ID,),
                )
                for row in cur.fetchall():
                    agent = row["agent_label"]
                    fb_count = int(row["feedback_count"])
                    pos = int(row["positive"])
                    pos_rate = pos / max(fb_count, 1)
                    if pos_rate < 0.4:
                        recommendations.append(
                            {
                                "type": "agent_underperforming",
                                "agent": agent,
                                "positive_rate": round(pos_rate, 4),
                                "feedback_count": fb_count,
                                "rationale": (
                                    f"Agent '{agent}' has {pos_rate:.0%} positive rate "
                                    f"over {fb_count} feedbacks — below 40% threshold."
                                ),
                                "action": "consider_model_upgrade_or_retraining",
                            }
                        )

                # Rule 2: skills with poor avg score
                cur.execute(
                    """
                    SELECT
                        s.name AS skill_name,
                        COALESCE(i.agent_label, 'unknown') AS agent_label,
                        COUNT(o.id) AS feedback_count,
                        AVG(o.score) AS avg_score
                    FROM outcomes o
                    LEFT JOIN interactions i ON i.id = o.interaction_id
                    LEFT JOIN skills s ON s.id = i.skill_id
                    WHERE o.org_id = %s
                      AND o.notes LIKE '[rlhf:%%'
                      AND s.name IS NOT NULL
                    GROUP BY s.name, i.agent_label
                    HAVING COUNT(o.id) >= 5
                    """,
                    (ORG_ID,),
                )
                for row in cur.fetchall():
                    skill_name = row["skill_name"]
                    agent = row["agent_label"]
                    avg_s = float(row["avg_score"] or 0)
                    fb_count = int(row["feedback_count"])
                    if avg_s < 0.4:
                        recommendations.append(
                            {
                                "type": "skill_underperforming",
                                "agent": agent,
                                "skill": skill_name,
                                "avg_score": round(avg_s, 4),
                                "feedback_count": fb_count,
                                "rationale": (
                                    f"Skill '{skill_name}' (agent '{agent}') has "
                                    f"avg score {avg_s:.2f} over {fb_count} feedbacks "
                                    f"— below 0.4 threshold."
                                ),
                                "action": "review_skill_or_disable",
                            }
                        )

                # Rule 3: agents with interactions but zero feedback
                cur.execute(
                    """
                    SELECT
                        i.agent_label,
                        COUNT(DISTINCT i.id) AS interaction_count,
                        COUNT(o.id) FILTER (WHERE o.notes LIKE '[rlhf:%%') AS rlhf_count
                    FROM interactions i
                    LEFT JOIN outcomes o ON o.interaction_id = i.id
                    WHERE i.org_id = %s
                      AND i.created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY i.agent_label
                    HAVING COUNT(DISTINCT i.id) >= 20
                       AND COUNT(o.id) FILTER (WHERE o.notes LIKE '[rlhf:%%') = 0
                    """,
                    (ORG_ID,),
                )
                for row in cur.fetchall():
                    agent = row["agent_label"]
                    count = int(row["interaction_count"])
                    recommendations.append(
                        {
                            "type": "no_feedback",
                            "agent": agent,
                            "interaction_count": count,
                            "rationale": (
                                f"Agent '{agent}' has {count} interactions in 30d "
                                f"but zero RLHF feedback — blind spot."
                            ),
                            "action": "request_feedback_collection",
                        }
                    )

        except Exception as exc:
            logger.error("recommend_routing_adjustment failed: %s", exc)
            recommendations.append(
                {
                    "type": "error",
                    "rationale": f"Could not analyze feedback: {exc}",
                    "action": "check_db_connectivity",
                }
            )

        return recommendations


# ─── Singleton ───────────────────────────────────────────────────────────────

_instance: FeedbackLoop | None = None


def get_feedback_loop() -> FeedbackLoop:
    """Return the process-wide FeedbackLoop singleton."""
    global _instance
    if _instance is None:
        _instance = FeedbackLoop()
    return _instance
