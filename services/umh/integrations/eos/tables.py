"""Typed query helpers for EOS database tables.

Single coupling point between UMH and the EOS schema. All SQL lives here;
the rest of the integration imports typed row dicts from this module.

Real EntrepreneurOS tables (Drizzle ORM pgTable definitions):
  crm_contacts — leads/prospects/customers (text PK, user_id text)
  crm_deals    — pipeline deals (text PK, value decimal, stage enum)
  crm_activities — CRM interaction log (text PK, type enum)
  tasks        — agent task management (text PK, status enum)
  agents       — AI agent roster (text PK, role_level enum)
  agent_actions — governed agent actions (text PK, status enum)
  agent_metrics — daily agent performance metrics (text PK)
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

CRM_CONTACTS_TABLE = "crm_contacts"
CRM_DEALS_TABLE = "crm_deals"
CRM_ACTIVITIES_TABLE = "crm_activities"
TASKS_TABLE = "tasks"
AGENT_ACTIONS_TABLE = "agent_actions"

VALID_CONTACT_STATUSES = frozenset({"lead", "prospect", "customer", "churned"})
VALID_DEAL_STAGES = frozenset(
    {"discovery", "proposal", "negotiation", "closed-won", "closed-lost"}
)
VALID_ACTIVITY_TYPES = frozenset({"email", "call", "meeting", "task", "note"})
VALID_TASK_STATUSES = frozenset({"todo", "in-progress", "done"})
VALID_TASK_PRIORITIES = frozenset({"low", "medium", "high", "urgent"})
VALID_ACTION_STATUSES = frozenset(
    {"pending", "approved", "executing", "completed", "failed", "rejected"}
)


@dataclass(frozen=True)
class CrmContactRow:
    """Typed representation of an EOS crm_contacts table row."""

    id: str
    user_id: str
    name: str
    email: str
    status: str
    company: str | None
    title: str | None
    created_at: datetime


@dataclass(frozen=True)
class CrmDealRow:
    """Typed representation of an EOS crm_deals table row."""

    id: str
    user_id: str
    title: str
    company: str
    value: str
    stage: str
    probability: int
    contact_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class CrmActivityRow:
    """Typed representation of an EOS crm_activities table row."""

    id: str
    user_id: str
    type: str
    subject: str
    date: datetime
    related_to_type: str
    related_to_id: str
    completed: bool
    created_at: datetime


@dataclass(frozen=True)
class TaskRow:
    """Typed representation of an EOS tasks table row."""

    id: str
    title: str
    description: str
    status: str
    priority: str
    agent_id: str | None
    task_type: str
    created_at: datetime


@dataclass(frozen=True)
class AgentActionRow:
    """Typed representation of an EOS agent_actions table row."""

    id: str
    agent_id: str
    user_id: str
    action_type: str
    action_name: str
    status: str
    requires_approval: bool
    priority: str
    created_at: datetime


def fetch_user_ids(conn: Any) -> list[str]:
    """Discover all user IDs in the EOS database."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users ORDER BY id")
        return [str(row[0]) for row in cur.fetchall()]


def fetch_contacts_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[CrmContactRow]:
    """Fetch CRM contacts created after `since` for a specific user."""
    query = """
        SELECT id, user_id, name, email, status, company, title, created_at
        FROM crm_contacts
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        CrmContactRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            name=row["name"],
            email=row["email"],
            status=row["status"] or "lead",
            company=row["company"],
            title=row["title"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_deals_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[CrmDealRow]:
    """Fetch CRM deals created after `since` for a specific user."""
    query = """
        SELECT id, user_id, title, company, value, stage, probability,
               contact_id, created_at
        FROM crm_deals
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        CrmDealRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row["title"],
            company=row["company"],
            value=str(row["value"]),
            stage=row["stage"] or "discovery",
            probability=int(row["probability"] or 50),
            contact_id=row["contact_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_activities_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[CrmActivityRow]:
    """Fetch CRM activities created after `since` for a specific user."""
    query = """
        SELECT id, user_id, type, subject, date, related_to_type,
               related_to_id, completed, created_at
        FROM crm_activities
        WHERE user_id = %s AND created_at > %s
        ORDER BY created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (user_id, since, limit))
        rows = cur.fetchall()

    return [
        CrmActivityRow(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            type=row["type"],
            subject=row["subject"],
            date=row["date"],
            related_to_type=row["related_to_type"],
            related_to_id=str(row["related_to_id"]),
            completed=bool(row["completed"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def fetch_tasks_since(
    conn: Any,
    user_id: str,
    since: str,
    limit: int = 100,
) -> list[TaskRow]:
    """Fetch tasks created after `since` assigned to agents owned by user."""
    query = """
        SELECT t.id, t.title, t.description, t.status, t.priority,
               t.agent_id, t.task_type, t.created_at
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        WHERE a.id IN (SELECT id FROM agents)
              AND t.created_at > %s
        ORDER BY t.created_at ASC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (since, limit))
        rows = cur.fetchall()

    return [
        TaskRow(
            id=str(row["id"]),
            title=row["title"],
            description=row["description"] or "",
            status=row["status"] or "todo",
            priority=row["priority"] or "medium",
            agent_id=row["agent_id"],
            task_type=row["task_type"] or "standard",
            created_at=row["created_at"],
        )
        for row in rows
    ]


def _require_str(params: dict[str, Any], key: str) -> str:
    """Extract a required non-empty string from params, or raise ValueError."""
    val = params.get(key)
    if not val or not isinstance(val, str) or not val.strip():
        raise ValueError(f"'{key}' is required and must be a non-empty string")
    return val.strip()


def insert_contact(conn: Any, params: dict[str, Any]) -> str:
    """Insert a CRM contact and return its ID.

    Required params: user_id, name, email (all text).
    Optional: phone, company, title, status (default 'lead'), notes, avatar.
    """
    user_id = _require_str(params, "user_id")
    name = _require_str(params, "name")
    email = _require_str(params, "email")
    status = params.get("status", "lead") or "lead"
    if status not in VALID_CONTACT_STATUSES:
        raise ValueError(
            f"invalid contact status '{status}', must be one of: {sorted(VALID_CONTACT_STATUSES)}"
        )

    phone = params.get("phone")
    company = params.get("company")
    title = params.get("title")
    notes = params.get("notes")

    import uuid

    contact_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO crm_contacts (id, user_id, name, email, status, phone, company, title, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (contact_id, user_id, name, email, status, phone, company, title, notes),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def insert_deal(conn: Any, params: dict[str, Any]) -> str:
    """Insert a CRM deal and return its ID.

    Required params: user_id, title, company, value, contact_id.
    Optional: stage (default 'discovery'), probability (default 50),
              assigned_agent_id, notes.
    """
    user_id = _require_str(params, "user_id")
    title = _require_str(params, "title")
    company = _require_str(params, "company")
    contact_id = _require_str(params, "contact_id")

    raw_value = params.get("value")
    if raw_value is None:
        raise ValueError("'value' is required")
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"'value' must be a valid decimal: {exc}") from exc
    if value < 0:
        raise ValueError("'value' must be non-negative")

    stage = params.get("stage", "discovery") or "discovery"
    if stage not in VALID_DEAL_STAGES:
        raise ValueError(
            f"invalid deal stage '{stage}', must be one of: {sorted(VALID_DEAL_STAGES)}"
        )

    probability = int(params.get("probability", 50) or 50)
    if not 0 <= probability <= 100:
        raise ValueError("'probability' must be between 0 and 100")

    assigned_agent_id = params.get("assigned_agent_id")
    notes = params.get("notes")

    import uuid

    deal_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO crm_deals
                (id, user_id, title, company, value, stage, probability,
                 contact_id, assigned_agent_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                deal_id, user_id, title, company, str(value), stage, probability,
                contact_id, assigned_agent_id, notes,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row[0])


def update_deal_stage(conn: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Update a deal's stage and/or probability. Returns result dict.

    Required params: user_id, deal_id.
    Optional: stage, probability. At least one must be provided.
    """
    user_id = _require_str(params, "user_id")
    deal_id = _require_str(params, "deal_id")

    fields_changed: list[str] = []
    set_clauses: list[str] = []
    values: list[Any] = []

    if "stage" in params and params["stage"] is not None:
        stage = params["stage"]
        if stage not in VALID_DEAL_STAGES:
            raise ValueError(
                f"invalid deal stage '{stage}', must be one of: {sorted(VALID_DEAL_STAGES)}"
            )
        set_clauses.append("stage = %s")
        values.append(stage)
        fields_changed.append("stage")

    if "probability" in params and params["probability"] is not None:
        prob = int(params["probability"])
        if not 0 <= prob <= 100:
            raise ValueError("'probability' must be between 0 and 100")
        set_clauses.append("probability = %s")
        values.append(prob)
        fields_changed.append("probability")

    if not set_clauses:
        raise ValueError("at least one of 'stage' or 'probability' must be provided")

    set_clauses.append("updated_at = NOW()")
    values.extend([deal_id, user_id])
    query = (
        f"UPDATE crm_deals SET {', '.join(set_clauses)} "
        f"WHERE id = %s AND user_id = %s RETURNING id"
    )

    with conn.cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
        conn.commit()
        if row is None:
            raise ValueError(f"deal '{deal_id}' not found for user '{user_id}'")
        return {"deal_id": str(row[0]), "updated": True, "fields_changed": fields_changed}


def insert_activity(conn: Any, params: dict[str, Any]) -> str:
    """Insert a CRM activity and return its ID.

    Required params: user_id, type, subject, date, related_to_type, related_to_id.
    Optional: completed (default false), notes, created_by_agent_id.
    """
    user_id = _require_str(params, "user_id")
    activity_type = _require_str(params, "type")
    subject = _require_str(params, "subject")
    related_to_type = _require_str(params, "related_to_type")
    related_to_id = _require_str(params, "related_to_id")

    if activity_type not in VALID_ACTIVITY_TYPES:
        raise ValueError(
            f"invalid activity type '{activity_type}', must be one of: {sorted(VALID_ACTIVITY_TYPES)}"
        )
    if related_to_type not in ("contact", "deal"):
        raise ValueError("'related_to_type' must be 'contact' or 'deal'")

    date_str = params.get("date")
    if not date_str:
        raise ValueError("'date' is required")

    completed = bool(params.get("completed", False))
    notes = params.get("notes")
    created_by_agent_id = params.get("created_by_agent_id")

    import uuid

    activity_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO crm_activities
                (id, user_id, type, subject, date, related_to_type,
                 related_to_id, completed, notes, created_by_agent_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                activity_id, user_id, activity_type, subject, date_str,
                related_to_type, related_to_id, completed, notes, created_by_agent_id,
            ),
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
    {CRM_CONTACTS_TABLE, CRM_DEALS_TABLE, CRM_ACTIVITIES_TABLE, TASKS_TABLE, AGENT_ACTIONS_TABLE}
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
