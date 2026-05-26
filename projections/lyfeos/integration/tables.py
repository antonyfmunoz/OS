"""Typed query helpers for LyfeOS database tables.

Single coupling point between UMH and the LyfeOS schema. All SQL lives here;
the rest of the integration imports typed row dataclasses from this module.

Schema source: /opt/OS/data/repos/LYFEOS/shared/schema.ts
All IDs are serial (integer). Scope key is user_id (integer).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

QUESTS_TABLE = "quests"
USER_STATS_TABLE = "user_stats"
DAILY_LOGS_TABLE = "user_daily_logs"
VISION_GOALS_TABLE = "vision_goals"

VALID_QUEST_DIFFICULTIES = frozenset({"S", "A", "B", "C", "D"})
VALID_QUEST_CATEGORIES = frozenset({"general", "setup", "rituals", "life pillars"})
VALID_VISION_CATEGORIES = frozenset({"legacy", "10year", "5year", "18month", "90day"})
VALID_MISSION_STATUSES = frozenset({"confirmed", "pending", "completed", "cancelled"})


@dataclass(frozen=True)
class QuestRow:
    """Typed representation of a LyfeOS quests table row."""

    id: int
    user_id: int
    title: str
    description: str
    category: str
    completed: bool
    energy_cost: int
    experience_reward: int
    difficulty: str
    is_ritualized: bool
    ritual_group: str | None
    mission_status: str
    created_at: datetime
    updated_at: datetime | None


@dataclass(frozen=True)
class UserStatsRow:
    """Typed representation of a LyfeOS user_stats table row."""

    id: int
    user_id: int
    energy_points_current: int
    energy_points_max: int
    health_points_current: int
    health_points_max: int
    experience_current: int
    experience_max: int
    level: int
    streak_days: int
    updated_at: datetime


@dataclass(frozen=True)
class DailyLogRow:
    """Typed representation of a LyfeOS user_daily_logs table row."""

    id: int
    user_id: int
    date: str
    mental_state: int
    physical_state: int
    emotional_state: int
    gratitude: str | None
    went_well: str | None
    created_at: datetime


@dataclass(frozen=True)
class VisionGoalRow:
    """Typed representation of a LyfeOS vision_goals table row."""

    id: int
    user_id: int
    category: str
    title: str
    description: str | None
    bonus_xp: int
    completed: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def fetch_user_ids(conn: Any) -> list[str]:
    """Discover all user IDs in the LyfeOS database.

    Returns list[str] for compatibility with the socket protocol layer
    (which uses string user identifiers), even though LyfeOS IDs are integers.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users ORDER BY id")
        return [str(row[0]) for row in cur.fetchall()]


def fetch_quests_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[QuestRow]:
    """Fetch quests created after `since` for a specific user."""
    query = """
        SELECT id, user_id, title, description, category, completed,
               energy_cost, experience_reward, difficulty, is_ritualized,
               ritual_group, mission_status, created_at, updated_at
        FROM quests
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        QuestRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            title=row["title"] or "",
            description=row["description"] or "",
            category=row["category"] or "",
            completed=bool(row["completed"]),
            energy_cost=int(row["energy_cost"] or 0),
            experience_reward=int(row["experience_reward"] or 0),
            difficulty=row["difficulty"] or "D",
            is_ritualized=bool(row["is_ritualized"]),
            ritual_group=row["ritual_group"],
            mission_status=row["mission_status"] or "pending",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


def fetch_stats_for_user(
    conn: Any,
    user_id: int,
) -> UserStatsRow | None:
    """Fetch the single user_stats row for a user. Returns None if not found."""
    query = """
        SELECT id, user_id, energy_points_current, energy_points_max,
               health_points_current, health_points_max,
               experience_current, experience_max,
               level, streak_days, updated_at
        FROM user_stats
        WHERE user_id = %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id,))
        row = cur.fetchone()

    if row is None:
        return None

    return UserStatsRow(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        energy_points_current=int(row["energy_points_current"] or 0),
        energy_points_max=int(row["energy_points_max"] or 0),
        health_points_current=int(row["health_points_current"] or 0),
        health_points_max=int(row["health_points_max"] or 0),
        experience_current=int(row["experience_current"] or 0),
        experience_max=int(row["experience_max"] or 0),
        level=int(row["level"] or 1),
        streak_days=int(row["streak_days"] or 0),
        updated_at=row["updated_at"],
    )


def fetch_daily_logs_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[DailyLogRow]:
    """Fetch daily logs created after `since` for a specific user."""
    query = """
        SELECT id, user_id, date, mental_state, physical_state,
               emotional_state, gratitude, went_well, created_at
        FROM user_daily_logs
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        DailyLogRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            date=str(row["date"]),
            mental_state=int(row["mental_state"] or 0),
            physical_state=int(row["physical_state"] or 0),
            emotional_state=int(row["emotional_state"] or 0),
            gratitude=row["gratitude"],
            went_well=row["went_well"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_vision_goals_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[VisionGoalRow]:
    """Fetch vision goals created after `since` for a specific user."""
    query = """
        SELECT id, user_id, category, title, description,
               bonus_xp, completed, created_at
        FROM vision_goals
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        VisionGoalRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            category=row["category"] or "",
            title=row["title"] or "",
            description=row["description"],
            bonus_xp=int(row["bonus_xp"] or 0),
            completed=bool(row["completed"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def _require_str(params: dict[str, Any], key: str) -> str:
    """Extract a required non-empty string from params, or raise ValueError."""
    val = params.get(key)
    if not val or not isinstance(val, str) or not val.strip():
        raise ValueError(f"'{key}' is required and must be a non-empty string")
    return val.strip()


def _require_int(params: dict[str, Any], key: str) -> int:
    """Extract a required integer from params, or raise ValueError."""
    val = params.get(key)
    if val is None:
        raise ValueError(f"'{key}' is required")
    try:
        return int(val)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' must be an integer, got {type(val).__name__}")


def insert_quest(conn: Any, params: dict[str, Any]) -> str:
    """Insert a quest and return its ID as string."""
    user_id = _require_int(params, "user_id")
    title = _require_str(params, "title")
    description = params.get("description", "") or ""
    category = params.get("category", "general") or "general"
    energy_cost = int(params.get("energy_cost", 0) or 0)
    experience_reward = int(params.get("experience_reward", 0) or 0)
    difficulty = params.get("difficulty", "D") or "D"

    if category not in VALID_QUEST_CATEGORIES:
        raise ValueError(
            f"invalid quest category '{category}', must be one of: {sorted(VALID_QUEST_CATEGORIES)}"
        )
    if difficulty not in VALID_QUEST_DIFFICULTIES:
        raise ValueError(
            f"invalid quest difficulty '{difficulty}', "
            f"must be one of: {sorted(VALID_QUEST_DIFFICULTIES)}"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO quests
                (user_id, title, description, category,
                 energy_cost, experience_reward, difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, title, description, category, energy_cost, experience_reward, difficulty),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def update_quest(conn: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update a quest's completed status and/or mission_status. Returns result dict."""
    user_id = _require_int(params, "user_id")
    quest_id = _require_int(params, "quest_id")

    fields_changed: list[str] = []
    set_clauses: list[str] = []
    values: list[Any] = []

    if "completed" in params and params["completed"] is not None:
        completed = bool(params["completed"])
        set_clauses.append("completed = %s")
        values.append(completed)
        fields_changed.append("completed")
        if completed:
            set_clauses.append("completed_at = NOW()")
            fields_changed.append("completed_at")

    if "mission_status" in params and params["mission_status"] is not None:
        status = params["mission_status"]
        if status not in VALID_MISSION_STATUSES:
            raise ValueError(
                f"invalid mission_status '{status}', "
                f"must be one of: {sorted(VALID_MISSION_STATUSES)}"
            )
        set_clauses.append("mission_status = %s")
        values.append(status)
        fields_changed.append("mission_status")

    if not set_clauses:
        raise ValueError("at least one of 'completed' or 'mission_status' must be provided")

    set_clauses.append("updated_at = NOW()")
    values.extend([quest_id, user_id])
    query = (
        f"UPDATE quests SET {', '.join(set_clauses)} WHERE id = %s AND user_id = %s RETURNING id"
    )

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise ValueError(f"quest '{quest_id}' not found for user '{user_id}'")
        return {
            "quest_id": str(row[0]),
            "updated": True,
            "fields_changed": fields_changed,
        }


def insert_daily_log(conn: Any, params: dict[str, Any]) -> str:
    """Insert a daily log entry and return its ID as string."""
    user_id = _require_int(params, "user_id")
    date = _require_str(params, "date")
    mental_state = int(params.get("mental_state", 5) or 5)
    physical_state = int(params.get("physical_state", 5) or 5)
    emotional_state = int(params.get("emotional_state", 5) or 5)
    gratitude = params.get("gratitude", "") or ""

    for label, val in [
        ("mental_state", mental_state),
        ("physical_state", physical_state),
        ("emotional_state", emotional_state),
    ]:
        if not 1 <= val <= 10:
            raise ValueError(f"'{label}' must be between 1 and 10, got {val}")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_daily_logs
                (user_id, date, mental_state, physical_state,
                 emotional_state, gratitude)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, date, mental_state, physical_state, emotional_state, gratitude),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


# ---------------------------------------------------------------------------
# Outcome writeback helpers
# ---------------------------------------------------------------------------

UMH_OUTCOMES_TABLE = "umh_outcomes"

SEVERITY_LADDER: dict[str, int] = {
    "success": 0,
    "timeout": 1,
    "governance_denied": 2,
    "error": 3,
}

SOURCE_ROW_UPDATE_TYPES = frozenset({"success", "timeout", "governance_denied"})
VALID_SOURCE_TABLES = frozenset(
    {QUESTS_TABLE, USER_STATS_TABLE, DAILY_LOGS_TABLE, VISION_GOALS_TABLE}
)


def outcome_severity(outcome_type: str) -> int:
    """Return numeric severity for an outcome type. Unknown types get max severity."""
    return SEVERITY_LADDER.get(outcome_type, len(SEVERITY_LADDER))


def update_umh_status(
    conn: Any,
    table_name: str,
    row_id: str,
    new_status: str,
) -> bool:
    """Update umh_status on a source row, only if new severity >= current."""
    if table_name not in VALID_SOURCE_TABLES:
        raise ValueError(
            f"invalid source table '{table_name}', must be one of: {sorted(VALID_SOURCE_TABLES)}"
        )

    new_severity = outcome_severity(new_status)

    severity_checks = []
    check_values: list[Any] = []
    for status_val, sev in SEVERITY_LADDER.items():
        if sev < new_severity:
            severity_checks.append("umh_status = %s")
            check_values.append(status_val)

    where_parts = ["umh_status IS NULL"]
    where_parts.extend(severity_checks)

    query = (
        f"UPDATE {table_name} SET umh_status = %s "
        f"WHERE id = %s AND ({' OR '.join(where_parts)}) "
        f"RETURNING id"
    )
    params_list = [new_status, row_id] + check_values

    with conn.cursor() as cur:
        cur.execute(query, params_list)
        row = cur.fetchone()
        conn.commit()
        return row is not None


def insert_umh_outcome(
    conn: Any,
    trace_id: str,
    source_table: str,
    source_row_id: str | None,
    user_id: str,
    outcome_type: str,
    severity: int,
    payload: dict[str, Any],
) -> str:
    """Insert an audit row into umh_outcomes. Returns the new row ID."""
    if source_table not in VALID_SOURCE_TABLES:
        raise ValueError(
            f"invalid source table '{source_table}', must be one of: {sorted(VALID_SOURCE_TABLES)}"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO umh_outcomes
                (user_id, trace_id, source_table, source_row_id,
                 outcome_type, severity, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                trace_id,
                source_table,
                source_row_id,
                outcome_type,
                severity,
                psycopg2.extras.Json(payload),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])
