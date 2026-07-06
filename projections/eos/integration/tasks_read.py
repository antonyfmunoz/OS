"""EOS `/eos/tasks` read surface — P4S-20 (governed-effect visibility).

The smallest projection-owned accessor proving that EOS tasks created through
governed execution are visible over the substrate. Surfaces `tasks` rows
LEFT JOINed against their originating `agent_actions` row via the
`agent_actions.task_id` FK (shared/schema.ts:395) — the mechanism that ties a
task back to the governed action that produced it.

Composition (all fail-closed, never raises):

1. EOS DB (env-gated) — manifest.load_eos_config(); unset EOS_DATABASE_URL →
   stable "disconnected" envelope. When configured, the connection is opened
   READ-ONLY (set_session readonly) so a write is mechanically impossible, and
   only the SELECT in tables.fetch_recent_tasks_with_action_link runs.

Read-only end to end. This module contains no INSERT/UPDATE/DELETE statement
and imports no executor, no mutation path, no governed_mutation. Follows the
`.claude/rules/projection-read-surfaces.md` six invariants: projection-owned
accessor, env-disabled-safe, side-effect-free, stable flat-plus-one-list shape.

Imports are downward only (projection → substrate/same-package/stdlib).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_PROJECTION_ID = "eos"
_SURFACE = "tasks"


def _envelope(
    connected: bool,
    connection_status: str,
    tasks: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    rows = tasks or []
    return {
        "projection_id": _PROJECTION_ID,
        "surface": _SURFACE,
        "connected": connected,
        "connection_status": connection_status,
        "count": len(rows),
        "tasks": rows,
        "error": error,
    }


def _task_to_dict(row: Any) -> dict[str, Any]:
    """Render one TaskWithActionRow as a flat dict — proves the governed-effect
    link (action_id/action_type/action_status) when it exists, None otherwise."""
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "action_id": row.action_id,
        "action_type": row.action_type,
        "action_status": row.action_status,
    }


def eos_tasks(limit: int = 25) -> dict[str, Any]:
    """Return the most recent EOS tasks, each annotated with its originating
    governed action (if any). Never raises. Env-disabled (EOS_DATABASE_URL
    unset) → stable "disconnected" envelope with zero rows. Read-only end to
    end: the DB session is opened readonly and only the canonical SELECT runs.
    """
    try:
        from projections.eos.integration.manifest import load_eos_config

        config = load_eos_config()
    except Exception as exc:
        logger.debug("EOS config load failed: %s", exc)
        return _envelope(False, "disconnected")

    if not config:
        return _envelope(False, "disconnected")

    try:
        import psycopg2

        from projections.eos.integration.tables import fetch_recent_tasks_with_action_link

        conn = psycopg2.connect(config["database_url"])
        try:
            # Mechanical read-only guarantee: any write in this session errors.
            conn.set_session(readonly=True)
            rows = fetch_recent_tasks_with_action_link(conn, limit=limit)
        finally:
            conn.close()
    except Exception as exc:
        # Never echo the raw driver exception: a psycopg2 OperationalError can
        # embed the DSN (host/user, sometimes password). Stable code only; the
        # detail stays in the debug log.
        logger.debug("EOS tasks read failed: %s", exc)
        return _envelope(False, "unavailable", error="eos_database_unavailable")

    return _envelope(True, "connected", tasks=[_task_to_dict(row) for row in rows])
