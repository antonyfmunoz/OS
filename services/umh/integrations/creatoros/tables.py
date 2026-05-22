"""Typed query helpers for CreatorOS database tables.

Single coupling point between UMH and the CreatorOS schema. All SQL lives here;
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

CONTENT_TABLE = "content"
ANALYTICS_TABLE = "analytics"
AUDIENCE_METRICS_TABLE = "audience_metrics"

VALID_CONTENT_STATUSES = frozenset({"draft", "scheduled", "published", "archived"})
VALID_PLATFORMS = frozenset(
    {
        "youtube",
        "instagram",
        "tiktok",
        "twitter",
        "linkedin",
        "spotify",
        "newsletter",
        "blog",
        "other",
    }
)
VALID_CONTENT_TYPES = frozenset(
    {
        "long_form",
        "short_form",
        "article",
        "thread",
        "story",
        "newsletter",
        "podcast",
        "live",
        "other",
    }
)
VALID_AUDIENCE_METRIC_TYPES = frozenset(
    {
        "followers",
        "subscribers",
        "email_list",
        "members",
        "monthly_views",
        "engagement_rate",
    }
)


@dataclass(frozen=True)
class ContentRow:
    """Typed representation of a CreatorOS content table row."""

    id: str
    creator_id: str
    platform: str
    content_type: str
    title: str
    status: str
    published_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class AnalyticsRow:
    """Typed representation of a CreatorOS analytics table row."""

    id: str
    creator_id: str
    content_id: str
    views: int
    likes: int
    comments: int
    shares: int
    updated_at: datetime


@dataclass(frozen=True)
class AudienceMetricRow:
    """Typed representation of a CreatorOS audience_metrics table row."""

    id: str
    creator_id: str
    platform: str
    metric_type: str
    value: int
    recorded_at: datetime


def fetch_creator_ids(conn: Any) -> list[str]:
    """Discover all creator IDs in the CreatorOS database."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM creators ORDER BY id")
        return [str(row[0]) for row in cur.fetchall()]


def fetch_content_since(
    conn: Any,
    creator_id: str,
    since: str,
    limit: int = 100,
) -> list[ContentRow]:
    """Fetch content created after `since` for a specific creator."""
    query = """
        SELECT id, creator_id, platform, content_type, title, status,
               published_at, created_at
        FROM content
        WHERE creator_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (creator_id, since, limit))
        rows = cur.fetchall()

    return [
        ContentRow(
            id=str(row["id"]),
            creator_id=str(row["creator_id"]),
            platform=row["platform"],
            content_type=row["content_type"],
            title=row["title"],
            status=row["status"],
            published_at=row["published_at"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_analytics_since(
    conn: Any,
    creator_id: str,
    since: str,
    limit: int = 100,
) -> list[AnalyticsRow]:
    """Fetch analytics updated after `since` for a specific creator."""
    query = """
        SELECT id, creator_id, content_id, views, likes, comments, shares, updated_at
        FROM analytics
        WHERE creator_id = %s AND updated_at > %s
        ORDER BY updated_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (creator_id, since, limit))
        rows = cur.fetchall()

    return [
        AnalyticsRow(
            id=str(row["id"]),
            creator_id=str(row["creator_id"]),
            content_id=str(row["content_id"]),
            views=int(row["views"]),
            likes=int(row["likes"]),
            comments=int(row["comments"]),
            shares=int(row["shares"]),
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


def fetch_audience_metrics_since(
    conn: Any,
    creator_id: str,
    since: str,
    limit: int = 100,
) -> list[AudienceMetricRow]:
    """Fetch audience metrics recorded after `since` for a specific creator."""
    query = """
        SELECT id, creator_id, platform, metric_type, value, recorded_at
        FROM audience_metrics
        WHERE creator_id = %s AND recorded_at > %s
        ORDER BY recorded_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (creator_id, since, limit))
        rows = cur.fetchall()

    return [
        AudienceMetricRow(
            id=str(row["id"]),
            creator_id=str(row["creator_id"]),
            platform=row["platform"],
            metric_type=row["metric_type"],
            value=int(row["value"]),
            recorded_at=row["recorded_at"],
        )
        for row in rows
    ]


def _require_str(params: dict[str, Any], key: str) -> str:
    """Extract a required non-empty string from params, or raise ValueError."""
    val = params.get(key)
    if not val or not isinstance(val, str) or not val.strip():
        raise ValueError(f"'{key}' is required and must be a non-empty string")
    return val.strip()


def insert_content(conn: Any, params: dict[str, Any]) -> str:
    """Insert a content piece and return its ID."""
    creator_id = _require_str(params, "creator_id")
    platform = _require_str(params, "platform")
    content_type = _require_str(params, "content_type")
    title = _require_str(params, "title")

    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"invalid platform '{platform}', must be one of: {sorted(VALID_PLATFORMS)}"
        )
    if content_type not in VALID_CONTENT_TYPES:
        raise ValueError(
            f"invalid content_type '{content_type}', must be one of: {sorted(VALID_CONTENT_TYPES)}"
        )

    body = params.get("body", "") or ""
    status = params.get("status", "draft") or "draft"
    if status not in VALID_CONTENT_STATUSES:
        raise ValueError(
            f"invalid status '{status}', must be one of: {sorted(VALID_CONTENT_STATUSES)}"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO content (creator_id, platform, content_type, title, body, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (creator_id, platform, content_type, title, body, status),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def update_analytics(conn: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update analytics for a content piece. Returns result dict."""
    creator_id = _require_str(params, "creator_id")
    content_id = _require_str(params, "content_id")

    fields_changed: list[str] = []
    set_clauses: list[str] = []
    values: list[Any] = []

    for field in ("views", "likes", "comments", "shares"):
        if field in params and params[field] is not None:
            val = int(params[field])
            if val < 0:
                raise ValueError(f"'{field}' must be non-negative")
            set_clauses.append(f"{field} = %s")
            values.append(val)
            fields_changed.append(field)

    if not set_clauses:
        raise ValueError(
            "at least one of 'views', 'likes', 'comments', or 'shares' must be provided"
        )

    set_clauses.append("updated_at = NOW()")
    values.extend([content_id, creator_id])
    query = (
        f"UPDATE analytics SET {', '.join(set_clauses)} "
        f"WHERE content_id = %s AND creator_id = %s RETURNING content_id"
    )

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise ValueError(
                f"analytics for content '{content_id}' not found for creator '{creator_id}'"
            )
        return {"content_id": str(row[0]), "updated": True, "fields_changed": fields_changed}


def insert_audience_metric(conn: Any, params: dict[str, Any]) -> str:
    """Insert an audience metric and return its ID."""
    creator_id = _require_str(params, "creator_id")
    platform = _require_str(params, "platform")
    metric_type = _require_str(params, "metric_type")

    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"invalid platform '{platform}', must be one of: {sorted(VALID_PLATFORMS)}"
        )
    if metric_type not in VALID_AUDIENCE_METRIC_TYPES:
        raise ValueError(
            f"invalid metric_type '{metric_type}', must be one of: {sorted(VALID_AUDIENCE_METRIC_TYPES)}"
        )

    value = params.get("value")
    if value is None:
        raise ValueError("'value' is required")
    value = int(value)
    if value < 0:
        raise ValueError("'value' must be non-negative")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO audience_metrics (creator_id, platform, metric_type, value)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (creator_id, platform, metric_type, value),
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
VALID_SOURCE_TABLES = frozenset({CONTENT_TABLE, ANALYTICS_TABLE, AUDIENCE_METRICS_TABLE})


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
    creator_id: str,
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
                (creator_id, trace_id, source_table, source_row_id,
                 outcome_type, severity, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                creator_id,
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
