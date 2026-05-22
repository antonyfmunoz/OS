"""Typed query helpers for LyfeOS database tables.

Single coupling point between UMH and the LyfeOS schema. All SQL lives here;
the rest of the integration imports typed row dataclasses from this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

HABIT_LOGS_TABLE = "habit_logs"
GOALS_TABLE = "goals"
HEALTH_METRICS_TABLE = "health_metrics"

VALID_GOAL_STATUSES = frozenset({"active", "paused", "completed", "abandoned"})
VALID_METRIC_TYPES = frozenset(
    {
        "weight",
        "body_fat",
        "sleep_hours",
        "steps",
        "hrv",
        "resting_hr",
        "blood_pressure",
        "custom",
    }
)


@dataclass(frozen=True)
class HabitLogRow:
    """Typed representation of a LyfeOS habit_logs table row."""

    id: str
    user_id: str
    habit_name: str
    completed: bool
    notes: str
    logged_at: datetime


@dataclass(frozen=True)
class GoalRow:
    """Typed representation of a LyfeOS goals table row."""

    id: str
    user_id: str
    title: str
    progress_pct: int
    status: str
    updated_at: datetime


@dataclass(frozen=True)
class HealthMetricRow:
    """Typed representation of a LyfeOS health_metrics table row."""

    id: str
    user_id: str
    metric_type: str
    value: float
    unit: str
    logged_at: datetime


def fetch_user_ids(conn: Any) -> list[str]:
    """Discover all user IDs in the LyfeOS database."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users ORDER BY id")
        return [str(row[0]) for row in cur.fetchall()]


def fetch_habit_logs_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[HabitLogRow]:
    """Fetch habit logs created after `since` for a specific user."""
    query = """
        SELECT id, user_id, habit_name, completed, notes, logged_at
        FROM habit_logs
        WHERE user_id = %s AND logged_at > %s
        ORDER BY logged_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        HabitLogRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            habit_name=row["habit_name"],
            completed=bool(row["completed"]),
            notes=row["notes"] or "",
            logged_at=row["logged_at"],
        )
        for row in rows
    ]


def fetch_goals_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[GoalRow]:
    """Fetch goals updated after `since` for a specific user."""
    query = """
        SELECT id, user_id, title, progress_pct, status, updated_at
        FROM goals
        WHERE user_id = %s AND updated_at > %s
        ORDER BY updated_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        GoalRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row["title"],
            progress_pct=int(row["progress_pct"]),
            status=row["status"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


def fetch_health_metrics_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[HealthMetricRow]:
    """Fetch health metrics logged after `since` for a specific user."""
    query = """
        SELECT id, user_id, metric_type, value, unit, logged_at
        FROM health_metrics
        WHERE user_id = %s AND logged_at > %s
        ORDER BY logged_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        HealthMetricRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            metric_type=row["metric_type"],
            value=float(row["value"]),
            unit=row["unit"] or "",
            logged_at=row["logged_at"],
        )
        for row in rows
    ]


def _require_str(params: dict[str, Any], key: str) -> str:
    """Extract a required non-empty string from params, or raise ValueError."""
    val = params.get(key)
    if not val or not isinstance(val, str) or not val.strip():
        raise ValueError(f"'{key}' is required and must be a non-empty string")
    return val.strip()


def insert_habit_log(conn: Any, params: dict[str, Any]) -> str:
    """Insert a habit log and return its ID."""
    user_id = _require_str(params, "user_id")
    habit_name = _require_str(params, "habit_name")
    completed = bool(params.get("completed", True))
    notes = params.get("notes", "") or ""

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO habit_logs (user_id, habit_name, completed, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, habit_name, completed, notes),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def update_goal(conn: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update a goal's progress and/or status. Returns result dict."""
    user_id = _require_str(params, "user_id")
    goal_id = _require_str(params, "goal_id")

    fields_changed: list[str] = []
    set_clauses: list[str] = []
    values: list[Any] = []

    if "progress_pct" in params and params["progress_pct"] is not None:
        pct = int(params["progress_pct"])
        if not 0 <= pct <= 100:
            raise ValueError("'progress_pct' must be between 0 and 100")
        set_clauses.append("progress_pct = %s")
        values.append(pct)
        fields_changed.append("progress_pct")

    if "status" in params and params["status"] is not None:
        status = params["status"]
        if status not in VALID_GOAL_STATUSES:
            raise ValueError(
                f"invalid goal status '{status}', must be one of: {sorted(VALID_GOAL_STATUSES)}"
            )
        set_clauses.append("status = %s")
        values.append(status)
        fields_changed.append("status")

    if "notes" in params and params["notes"] is not None:
        set_clauses.append("notes = %s")
        values.append(params["notes"])
        fields_changed.append("notes")

    if not set_clauses:
        raise ValueError("at least one of 'progress_pct', 'status', or 'notes' must be provided")

    set_clauses.append("updated_at = NOW()")
    values.extend([goal_id, user_id])
    query = f"UPDATE goals SET {', '.join(set_clauses)} WHERE id = %s AND user_id = %s RETURNING id"

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise ValueError(f"goal '{goal_id}' not found for user '{user_id}'")
        return {"goal_id": str(row[0]), "updated": True, "fields_changed": fields_changed}


def insert_health_metric(conn: Any, params: dict[str, Any]) -> str:
    """Insert a health metric and return its ID."""
    user_id = _require_str(params, "user_id")
    metric_type = _require_str(params, "metric_type")

    if metric_type not in VALID_METRIC_TYPES:
        raise ValueError(
            f"invalid metric_type '{metric_type}', must be one of: {sorted(VALID_METRIC_TYPES)}"
        )

    value = params.get("value")
    if value is None:
        raise ValueError("'value' is required")
    value = float(value)

    unit = params.get("unit", "") or ""
    notes = params.get("notes", "") or ""

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO health_metrics (user_id, metric_type, value, unit, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, metric_type, value, unit, notes),
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
VALID_SOURCE_TABLES = frozenset({HABIT_LOGS_TABLE, GOALS_TABLE, HEALTH_METRICS_TABLE})


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
                (user_id, trace_id, source_table, source_row_id, outcome_type, severity, payload)
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
