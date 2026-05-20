"""Typed query helpers for EOS database tables.

Single coupling point between UMH and the EOS schema. All SQL lives here;
the rest of the integration imports typed row dicts from this module.

Phase 1: events table only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

EVENTS_TABLE = "events"


@dataclass(frozen=True)
class EventRow:
    """Typed representation of an EOS events table row."""

    id: str
    org_id: str
    event_type: str
    payload_json: dict[str, Any]
    handled_by: str | None
    created_at: datetime


def fetch_org_ids(conn: Any) -> list[str]:
    """Discover all organization IDs in the EOS database."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM organizations ORDER BY id")
        return [str(row[0]) for row in cur.fetchall()]


def fetch_events_since(
    conn: Any,
    org_id: str,
    since: str,
    limit: int = 100,
) -> list[EventRow]:
    """Fetch events created after `since` for a specific org, sorted ascending.

    Uses the idx_events_org_created index for efficient polling.
    """
    query = """
        SELECT id, org_id, event_type, payload_json, handled_by, created_at
        FROM events
        WHERE org_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (org_id, since, limit))
        rows = cur.fetchall()

    return [
        EventRow(
            id=str(row["id"]),
            org_id=str(row["org_id"]),
            event_type=row["event_type"],
            payload_json=row["payload_json"] if isinstance(row["payload_json"], dict) else {},
            handled_by=row["handled_by"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def insert_test_event(
    conn: Any,
    org_id: str,
    event_type: str = "umh_test",
    payload: dict[str, Any] | None = None,
) -> str:
    """Insert a test event and return its ID. Used by smoke tests only."""
    payload = payload or {"marker": "[UMH-TEST]"}
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (org_id, event_type, payload_json)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (org_id, event_type, psycopg2.extras.Json(payload)),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])
