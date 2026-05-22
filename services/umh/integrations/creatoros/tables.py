"""Typed query helpers for CreatorOS database tables.

Single coupling point between UMH and the CreatorOS schema. All SQL lives here;
the rest of the integration imports typed row dataclasses from this module.

Schema source: /opt/OS/data/repos/creatoros/shared/schema.ts
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

POSTS_TABLE = "posts"
PRODUCTS_TABLE = "products"
REVENUE_TABLE = "revenue"
STORIES_TABLE = "stories"

VALID_MEDIA_TYPES = frozenset({"text", "photo", "audio", "video"})
VALID_STORY_MEDIA_TYPES = frozenset({"image", "video"})


@dataclass(frozen=True)
class PostRow:
    """Typed representation of a CreatorOS posts table row."""

    id: int
    user_id: int
    content: str
    media_type: str
    likes: int
    comments: int
    created_at: datetime


@dataclass(frozen=True)
class ProductRow:
    """Typed representation of a CreatorOS products table row."""

    id: int
    user_id: int
    title: str
    description: str
    price: float
    category: str
    rating: float
    review_count: int
    created_at: datetime


@dataclass(frozen=True)
class RevenueRow:
    """Typed representation of a CreatorOS revenue table row."""

    id: int
    user_id: int
    amount: float
    date: datetime
    source: str


@dataclass(frozen=True)
class StoryRow:
    """Typed representation of a CreatorOS stories table row."""

    id: int
    user_id: int
    media_url: str
    media_type: str
    caption: str | None
    view_count: int
    created_at: datetime
    expires_at: datetime | None


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


def fetch_user_ids(conn: Any) -> list[str]:
    """Discover all user IDs in the CreatorOS database.

    Returns list[str] for compatibility with the integration polling layer.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users ORDER BY id")
        return [str(row[0]) for row in cur.fetchall()]


def fetch_posts_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[PostRow]:
    """Fetch posts created after ``since`` for a specific user."""
    query = """
        SELECT id, user_id, content, media_type, likes, comments, created_at
        FROM posts
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        PostRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            content=row["content"] or "",
            media_type=row["media_type"] or "text",
            likes=int(row["likes"] or 0),
            comments=int(row["comments"] or 0),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_products_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[ProductRow]:
    """Fetch products created after ``since`` for a specific user."""
    query = """
        SELECT id, user_id, title, description, price, category,
               rating, review_count, created_at
        FROM products
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        ProductRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            title=row["title"] or "",
            description=row["description"] or "",
            price=float(row["price"] or 0.0),
            category=row["category"] or "",
            rating=float(row["rating"] or 0.0),
            review_count=int(row["review_count"] or 0),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_revenue_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[RevenueRow]:
    """Fetch revenue entries recorded after ``since`` for a specific user."""
    query = """
        SELECT id, user_id, amount, date, source
        FROM revenue
        WHERE user_id = %s AND date > %s
        ORDER BY date ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        RevenueRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            amount=float(row["amount"] or 0.0),
            date=row["date"],
            source=row["source"] or "",
        )
        for row in rows
    ]


def fetch_stories_since(
    conn: Any,
    user_id: int,
    since: str,
    limit: int = 100,
) -> list[StoryRow]:
    """Fetch stories created after ``since`` for a specific user."""
    query = """
        SELECT id, user_id, media_url, media_type, caption,
               view_count, created_at, expires_at
        FROM stories
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        StoryRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            media_url=row["media_url"] or "",
            media_type=row["media_type"] or "image",
            caption=row["caption"],
            view_count=int(row["view_count"] or 0),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Validation helpers
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
    return int(val)


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------


def insert_post(conn: Any, params: dict[str, Any]) -> str:
    """Insert a post and return its ID as string."""
    user_id = _require_int(params, "user_id")
    content = _require_str(params, "content")
    media_type = params.get("media_type", "text") or "text"

    if media_type not in VALID_MEDIA_TYPES:
        raise ValueError(
            f"invalid media_type '{media_type}', must be one of: {sorted(VALID_MEDIA_TYPES)}"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO posts (user_id, content, media_type)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, content, media_type),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def insert_product(conn: Any, params: dict[str, Any]) -> str:
    """Insert a product listing and return its ID as string."""
    user_id = _require_int(params, "user_id")
    title = _require_str(params, "title")
    description = params.get("description", "") or ""
    price = float(params.get("price", 0.0) or 0.0)
    category = params.get("category", "") or ""

    if price < 0:
        raise ValueError("'price' must be non-negative")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (user_id, title, description, price, category)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, title, description, price, category),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def insert_revenue(conn: Any, params: dict[str, Any]) -> str:
    """Insert a revenue entry and return its ID as string."""
    user_id = _require_int(params, "user_id")
    amount = float(params.get("amount", 0.0) or 0.0)
    source = params.get("source", "") or ""

    date_val = params.get("date")
    if date_val and isinstance(date_val, str):
        date_str = date_val
    else:
        date_str = "NOW()"

    with conn.cursor() as cur:
        if date_str == "NOW()":
            cur.execute(
                """
                INSERT INTO revenue (user_id, amount, date, source)
                VALUES (%s, %s, NOW(), %s)
                RETURNING id
                """,
                (user_id, amount, source),
            )
        else:
            cur.execute(
                """
                INSERT INTO revenue (user_id, amount, date, source)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, amount, date_str, source),
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
VALID_SOURCE_TABLES = frozenset({POSTS_TABLE, PRODUCTS_TABLE, REVENUE_TABLE, STORIES_TABLE})


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
    user_id: int,
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
