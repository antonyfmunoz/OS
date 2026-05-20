"""Typed query helpers for EOS database tables.

Single coupling point between UMH and the EOS schema. All SQL lives here;
the rest of the integration imports typed row dicts from this module.

Phase 1: events table reads. Phase 2: events/clients inserts, ventures update.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

EVENTS_TABLE = "events"
CLIENTS_TABLE = "clients"
VENTURES_TABLE = "ventures"

VALID_CLIENT_STATUSES = frozenset({"lead", "prospect", "client", "fulfilled", "churned"})
VALID_VENTURE_STAGES = frozenset({"idea", "pre_revenue", "early", "growth", "scale"})


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


# ---------------------------------------------------------------------------
# Phase 2: write helpers
# ---------------------------------------------------------------------------


def _require_str(params: dict[str, Any], key: str) -> str:
    """Extract a required non-empty string from params, or raise ValueError."""
    val = params.get(key)
    if not val or not isinstance(val, str) or not val.strip():
        raise ValueError(f"'{key}' is required and must be a non-empty string")
    return val.strip()


def insert_event(conn: Any, params: dict[str, Any]) -> str:
    """Insert a domain event and return its ID.

    Required params: org_id (uuid str), event_type (str).
    Optional: payload_json (dict, default {}), handled_by (str).
    """
    org_id = _require_str(params, "org_id")
    event_type = _require_str(params, "event_type")
    payload = params.get("payload_json") or {}
    if not isinstance(payload, dict):
        raise ValueError("'payload_json' must be a dict")
    handled_by = params.get("handled_by")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (org_id, event_type, payload_json, handled_by)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (org_id, event_type, psycopg2.extras.Json(payload), handled_by),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def insert_client(conn: Any, params: dict[str, Any]) -> str:
    """Insert a new client (lead) and return its ID.

    Required params: org_id, venture_id, name, email (all non-empty strings).
    Optional: source (default 'umh'), phone, notes, status (default 'lead').

    No FK constraint on clients.org_id/venture_id (text columns) — validation
    here is the primary defense against invalid references.
    """
    org_id = _require_str(params, "org_id")
    venture_id = _require_str(params, "venture_id")
    name = _require_str(params, "name")
    email = _require_str(params, "email")
    source = params.get("source", "umh") or "umh"
    phone = params.get("phone")
    notes = params.get("notes", "")
    status = params.get("status", "lead") or "lead"

    if status not in VALID_CLIENT_STATUSES:
        raise ValueError(
            f"invalid client status '{status}', must be one of: {sorted(VALID_CLIENT_STATUSES)}"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO clients (org_id, venture_id, name, email, source, phone, notes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (org_id, venture_id, name, email, source, phone, notes, status),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def update_venture(conn: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update a venture's monthly_revenue and/or stage. Returns result dict.

    Required params: org_id (uuid str), venture_id (uuid str).
    Optional: monthly_revenue (str or Decimal), stage (venture_stage enum).
    At least one optional field must be provided.
    """
    org_id = _require_str(params, "org_id")
    venture_id = _require_str(params, "venture_id")

    fields_changed: list[str] = []
    set_clauses: list[str] = []
    values: list[Any] = []

    if "monthly_revenue" in params and params["monthly_revenue"] is not None:
        raw = params["monthly_revenue"]
        try:
            revenue = Decimal(str(raw))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"'monthly_revenue' must be a valid decimal: {exc}") from exc
        if revenue < 0:
            raise ValueError("'monthly_revenue' must be non-negative")
        set_clauses.append("monthly_revenue = %s")
        values.append(str(revenue))
        fields_changed.append("monthly_revenue")

    if "stage" in params and params["stage"] is not None:
        stage = params["stage"]
        if stage not in VALID_VENTURE_STAGES:
            raise ValueError(
                f"invalid venture stage '{stage}', must be one of: {sorted(VALID_VENTURE_STAGES)}"
            )
        set_clauses.append("stage = %s")
        values.append(stage)
        fields_changed.append("stage")

    if not set_clauses:
        raise ValueError("at least one of 'monthly_revenue' or 'stage' must be provided")

    values.extend([venture_id, org_id])
    query = (
        f"UPDATE ventures SET {', '.join(set_clauses)} WHERE id = %s AND org_id = %s RETURNING id"
    )

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise ValueError(f"venture '{venture_id}' not found for org '{org_id}'")
        return {"venture_id": str(row[0]), "updated": True, "fields_changed": fields_changed}
