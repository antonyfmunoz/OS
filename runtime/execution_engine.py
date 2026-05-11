"""
ExecutionEngine — formal lifecycle tracking for every task in the system.

Gives every task a visible, auditable lifecycle:
  queued → assigned → in_progress → blocked → completed → outcome_logged

Usage:
    from runtime.execution_engine import ExecutionEngine
    from runtime.context import load_context_from_env

    ctx = load_context_from_env()
    ee = ExecutionEngine(ctx)

    task_id = coordination_engine.assign_task(...)
    ee.start_execution(task_id, agent='sales.icp_qualifier')
    ee.complete_execution(task_id, result='scored: HIGH', outcome_type='reply', outcome_score=1.0)
    trace = ee.get_execution_trace(task_id)
"""

from __future__ import annotations

import os
import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from runtime.context import EOSContext
from runtime.db import get_conn


# ─── Telegram alert helper ────────────────────────────────────────────────────

def _notify(text: str) -> None:
    """Send notification via channel router."""
    try:
        from runtime.channel import get_channel_router

        router = get_channel_router()
        router.notify(text)
    except Exception as e:
        print(f"[ExecutionEngine] Notify failed: {e}")


# ─── ExecutionEngine ──────────────────────────────────────────────────────────

class ExecutionEngine:
    """
    Tracks task lifecycle from creation to outcome.

    All state changes are persisted to Neon tasks + events tables.
    Human-assigned tasks that become blocked trigger Telegram alerts.
    """

    _STUCK_THRESHOLD_MINUTES = 30

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx

    # ─── start_execution ─────────────────────────────────────────────────────

    def start_execution(self, task_id: str, agent: str) -> bool:
        """
        Mark a task as in_progress and record who picked it up.

        Updates:
          tasks.status      = 'in_progress'
          tasks.started_at  = now()
          tasks.assigned_to = agent

        Args:
            task_id: UUID string of the task.
            agent:   Agent label e.g. 'sales.icp_qualifier' or 'human'.

        Returns:
            True if updated, False if task not found.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    UPDATE tasks
                       SET status      = 'in_progress',
                           started_at  = %s,
                           assigned_to = %s,
                           updated_at  = %s
                     WHERE id = %s
                       AND org_id = %s
                    """,
                    (now, agent, now, task_id, self.ctx.org_id),
                )
                updated = cur.rowcount > 0

            self._log_event(task_id, "in_progress", {"agent": agent})
            return updated
        except Exception as e:
            print(f"[ExecutionEngine] start_execution failed: {e}")
            return False

    # ─── block_execution ─────────────────────────────────────────────────────

    def block_execution(self, task_id: str, reason: str) -> bool:
        """
        Mark a task as blocked and log the blocking reason.
        Sends a Telegram alert if the task is assigned to a human.

        Updates:
          tasks.status = 'blocked'

        Args:
            task_id: UUID string of the task.
            reason:  Plain-language description of what's blocking this task.

        Returns:
            True if updated, False if task not found.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            assignee_type = None
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    UPDATE tasks
                       SET status     = 'blocked',
                           updated_at = %s
                     WHERE id = %s
                       AND org_id = %s
                    RETURNING assignee_type, description
                    """,
                    (now, task_id, self.ctx.org_id),
                )
                row = cur.fetchone()
                if row:
                    assignee_type = row["assignee_type"]
                    description   = row["description"]

            self._log_event(task_id, "blocked", {"reason": reason})

            if assignee_type == "human":
                _notify(
                    f"⚠️ TASK BLOCKED\n\n"
                    f"Task: {description[:100] if row else task_id[:8]}\n"
                    f"Reason: {reason}\n"
                    f"Task ID: {task_id[:8]}"
                )

            return row is not None
        except Exception as e:
            print(f"[ExecutionEngine] block_execution failed: {e}")
            return False

    # ─── complete_execution ───────────────────────────────────────────────────

    def complete_execution(
        self,
        task_id: str,
        result: str,
        outcome_type: str | None = None,
        outcome_score: float | None = None,
    ) -> bool:
        """
        Mark a task as completed and optionally log an outcome.

        Updates:
          tasks.status       = 'completed'
          tasks.completed_at = now()
          tasks.result       = result

        If outcome_type is provided, writes a row to the outcomes table
        linked to the task via result_ref.

        Args:
            task_id:       UUID string.
            result:        Plain-language summary of what was produced.
            outcome_type:  Optional — 'reply', 'book', 'qualify', 'content', etc.
            outcome_score: Optional — numeric score (0.0–1.0) for this outcome.

        Returns:
            True if updated, False if task not found.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    UPDATE tasks
                       SET status       = 'completed',
                           completed_at = %s,
                           result       = %s,
                           updated_at   = %s
                     WHERE id = %s
                       AND org_id = %s
                    RETURNING id
                    """,
                    (now, result, now, task_id, self.ctx.org_id),
                )
                updated = cur.fetchone() is not None

                # Log outcome if provided
                if updated and outcome_type:
                    try:
                        cur.execute(
                            """
                            INSERT INTO outcomes
                              (org_id, outcome_label, outcome_score,
                               result_ref, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                self.ctx.org_id,
                                outcome_type,
                                outcome_score,
                                task_id,
                                now,
                            ),
                        )
                    except Exception as oe:
                        print(f"[ExecutionEngine] outcome log failed: {oe}")

            self._log_event(task_id, "completed", {
                "result": result[:200],
                "outcome_type": outcome_type,
            })
            return updated
        except Exception as e:
            print(f"[ExecutionEngine] complete_execution failed: {e}")
            return False

    # ─── get_execution_trace ─────────────────────────────────────────────────

    def get_execution_trace(self, task_id: str) -> list[dict]:
        """
        Return the full lifecycle history for a task.

        Reads from events table filtered by task_id reference in payload,
        plus the current task row for base state.

        Returns:
            List of dicts ordered by timestamp: queued, assigned,
            in_progress, blocked, completed, outcome_logged events.
        """
        trace = []
        try:
            with get_conn(self.ctx.org_id) as cur:
                # Base task row
                cur.execute(
                    """
                    SELECT id, description, status, assignee_type,
                           assigned_to, priority, started_at,
                           completed_at, result, created_at
                      FROM tasks
                     WHERE id = %s AND org_id = %s
                    """,
                    (task_id, self.ctx.org_id),
                )
                task = cur.fetchone()
                if task:
                    trace.append({
                        "event":       "queued",
                        "timestamp":   str(task["created_at"]),
                        "description": task["description"],
                        "assignee":    task["assignee_type"],
                        "priority":    task["priority"],
                    })

                # Events table entries for this task
                try:
                    cur.execute(
                        """
                        SELECT event_type, payload, created_at
                          FROM events
                         WHERE org_id = %s
                           AND payload::text LIKE %s
                         ORDER BY created_at ASC
                        """,
                        (self.ctx.org_id, f'%{task_id}%'),
                    )
                    for row in cur.fetchall():
                        trace.append({
                            "event":     row["event_type"],
                            "timestamp": str(row["created_at"]),
                            "payload":   row["payload"],
                        })
                except Exception:
                    pass  # events table may not exist yet — trace still valid

        except Exception as e:
            print(f"[ExecutionEngine] get_execution_trace failed: {e}")

        return trace

    # ─── get_active_executions ───────────────────────────────────────────────

    def get_active_executions(self) -> list[dict]:
        """
        Return all in_progress tasks with runtime duration.
        Flags tasks stuck longer than _STUCK_THRESHOLD_MINUTES.

        Returns:
            List of dicts: task_id, description, agent, started_at,
            runtime_minutes, stuck (bool).
        """
        executions = []
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, description, assigned_to,
                           started_at, assignee_type, priority
                      FROM tasks
                     WHERE org_id = %s
                       AND status = 'in_progress'
                     ORDER BY started_at ASC
                    """,
                    (self.ctx.org_id,),
                )
                now = datetime.datetime.now(datetime.timezone.utc)
                for row in cur.fetchall():
                    started = row["started_at"]
                    runtime_min = 0
                    if started:
                        if started.tzinfo is None:
                            started = started.replace(tzinfo=datetime.timezone.utc)
                        runtime_min = round((now - started).total_seconds() / 60, 1)

                    executions.append({
                        "task_id":        str(row["id"]),
                        "description":    row["description"][:80],
                        "agent":          row["assigned_to"] or row["assignee_type"],
                        "started_at":     str(started) if started else None,
                        "runtime_minutes": runtime_min,
                        "stuck":          runtime_min > self._STUCK_THRESHOLD_MINUTES,
                    })
        except Exception as e:
            print(f"[ExecutionEngine] get_active_executions failed: {e}")

        return executions

    # ─── _log_event ──────────────────────────────────────────────────────────

    def _log_event(self, task_id: str, event_type: str, payload: dict) -> None:
        """Write a lifecycle event to the events table (best-effort)."""
        try:
            import json
            payload_with_task = {"task_id": task_id, **payload}
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (org_id, event_type, payload)
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (self.ctx.org_id, f"task.{event_type}", json.dumps(payload_with_task)),
                )
        except Exception:
            pass  # event logging is enhancement — never block lifecycle updates
