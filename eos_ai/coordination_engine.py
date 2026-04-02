"""
CoordinationEngine — event-driven task coordination for AI agents and humans.

Manages task assignment, tracking, and CEO-level delegation across the EOS
system. Agents and human team members share the same task queue.

Table: tasks
    (id UUID, org_id UUID, venture_id UUID, description TEXT,
     assignee_type TEXT, assignee_id TEXT, priority TEXT,
     status TEXT, due_by TIMESTAMPTZ, assigned_by TEXT,
     result TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / "services" / ".env")

from eos_ai.context import EOSContext
from eos_ai.db import get_conn, resolve_venture
from eos_ai.event_bus import EventBus
from eos_ai.authority_engine import AuthorityEngine

_TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
_TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _send_telegram(text: str) -> None:
    if not _TELEGRAM_BOT_TOKEN or not _TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{_TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": _TELEGRAM_CHAT_ID, "text": text[:4096]},
            timeout=10,
        )
    except Exception:
        pass


class CoordinationEngine:

    def __init__(self, ctx: EOSContext):
        self.ctx       = ctx
        self.event_bus = EventBus()
        self.authority = AuthorityEngine(ctx)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id         UUID        NOT NULL,
                    venture_id     UUID,
                    description    TEXT        NOT NULL,
                    assignee_type  TEXT        NOT NULL
                                               CHECK (assignee_type IN ('agent', 'human')),
                    assignee_id    TEXT        NOT NULL,
                    priority       TEXT        NOT NULL DEFAULT 'normal'
                                               CHECK (priority IN
                                                   ('critical', 'high', 'normal', 'low')),
                    status         TEXT        NOT NULL DEFAULT 'pending'
                                               CHECK (status IN
                                                   ('pending', 'in_progress',
                                                    'completed', 'blocked')),
                    due_by         TIMESTAMPTZ,
                    assigned_by    TEXT        NOT NULL DEFAULT 'ai',
                    result         TEXT,
                    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_assignee
                ON tasks (org_id, assignee_id, status)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks (org_id, status)
            """)

    # ─── Assign ───────────────────────────────────────────────────────────────

    def assign_task(
        self,
        task_description: str,
        assignee_type: str,
        assignee_id: str,
        venture_id: str | None = None,
        priority: str = "normal",
        due_by: str | None = None,
        assigned_by: str = "ai",
    ) -> str:
        """
        Create and assign a task to an agent or human.
        - agent: published to event bus immediately.
        - human: Telegram notification sent.
        Returns task_id (UUID string).
        """
        venture_uuid = resolve_venture(venture_id) if venture_id else None

        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                INSERT INTO tasks
                    (org_id, venture_id, description, assignee_type,
                     assignee_id, priority, status, due_by, assigned_by)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
                RETURNING id
                """,
                (
                    self.ctx.org_id,
                    venture_uuid,
                    task_description,
                    assignee_type,
                    assignee_id,
                    priority,
                    due_by,
                    assigned_by,
                ),
            )
            task_id = str(cur.fetchone()["id"])

        if assignee_type == "agent":
            self.event_bus.publish_async("agent_task_assigned", {
                "task_id":     task_id,
                "assignee_id": assignee_id,
                "description": task_description,
                "priority":    priority,
                "venture_id":  venture_id,
            })
            # Lifecycle tracking: mark in_progress immediately for agent tasks
            try:
                from eos_ai.execution_engine import ExecutionEngine
                ExecutionEngine(self.ctx).start_execution(task_id, assignee_id)
            except Exception as _ee_err:
                print(f"[CoordEngine] ExecutionEngine.start_execution failed: {_ee_err}")
        else:
            _send_telegram(
                f"TASK ASSIGNED ({priority.upper()})\n\n"
                f"{task_description}\n\n"
                f"Due: {due_by or 'no deadline'}\n"
                f"Task ID: {task_id[:8]}...\n\n"
                f"Reply /done {task_id[:8]} when complete."
            )
            try:
                from eos_ai.gws_connector import GWSConnector
                gws = GWSConnector()
                gws.create_task(
                    title=task_description[:100],
                    notes=(
                        f"EOS Task ID: {task_id}\n"
                        f"Priority: {priority}\n"
                        f"Venture: {venture_id or 'general'}"
                    ),
                    due=due_by,
                )
            except Exception as e:
                print(f"[CoordEngine] GWS task creation failed: {e}")

        return task_id

    # ─── Queue ────────────────────────────────────────────────────────────────

    def get_task_queue(
        self,
        assignee_id: str | None = None,
        status: str = "pending",
    ) -> list[dict]:
        """
        Return tasks filtered by assignee and status.
        Sorted by priority (critical → high → normal → low), then created_at.
        """
        priority_order = (
            "CASE priority "
            "WHEN 'critical' THEN 0 "
            "WHEN 'high'     THEN 1 "
            "WHEN 'normal'   THEN 2 "
            "WHEN 'low'      THEN 3 "
            "END ASC"
        )
        with get_conn(self.ctx.org_id) as cur:
            if assignee_id:
                cur.execute(
                    f"""
                    SELECT id, venture_id, description, assignee_type,
                           assignee_id, priority, status, due_by,
                           assigned_by, result, created_at
                    FROM tasks
                    WHERE org_id = %s AND assignee_id = %s AND status = %s
                    ORDER BY {priority_order}, created_at ASC
                    """,
                    (self.ctx.org_id, assignee_id, status),
                )
            else:
                cur.execute(
                    f"""
                    SELECT id, venture_id, description, assignee_type,
                           assignee_id, priority, status, due_by,
                           assigned_by, result, created_at
                    FROM tasks
                    WHERE org_id = %s AND status = %s
                    ORDER BY {priority_order}, created_at ASC
                    """,
                    (self.ctx.org_id, status),
                )
            rows = cur.fetchall()

        def _ts(v):
            return v.isoformat() if v and hasattr(v, "isoformat") else None

        return [
            {
                "id":            str(r["id"]),
                "description":   r["description"],
                "assignee_type": r["assignee_type"],
                "assignee_id":   r["assignee_id"],
                "priority":      r["priority"],
                "status":        r["status"],
                "due_by":        _ts(r["due_by"]),
                "assigned_by":   r["assigned_by"],
                "result":        r["result"],
                "created_at":    _ts(r["created_at"]),
            }
            for r in rows
        ]

    # ─── Complete ─────────────────────────────────────────────────────────────

    def complete_task(
        self,
        task_id: str,
        result: str | None = None,
    ) -> dict:
        """
        Mark a task completed in Neon. Logs to events table.
        Accepts full UUID or first 8 chars.
        Returns updated task dict.
        """
        with get_conn(self.ctx.org_id) as cur:
            # Support short IDs
            if len(task_id) < 36:
                cur.execute(
                    """
                    SELECT id FROM tasks
                    WHERE org_id = %s AND CAST(id AS TEXT) LIKE %s
                    LIMIT 1
                    """,
                    (self.ctx.org_id, task_id + "%"),
                )
                row = cur.fetchone()
                if row:
                    task_id = str(row["id"])

            cur.execute(
                """
                UPDATE tasks
                SET status = 'completed', result = %s, updated_at = now()
                WHERE id = %s AND org_id = %s
                RETURNING id, description, assignee_id, priority
                """,
                (result, task_id, self.ctx.org_id),
            )
            row = cur.fetchone()

        if not row:
            return {"error": f"task {task_id} not found"}

        try:
            from eos_ai.memory import AgentMemory
            AgentMemory().log_event(
                org_id=self.ctx.org_id,
                event_type="task_completed",
                payload={
                    "task_id":     task_id,
                    "description": (row["description"] or "")[:200],
                    "assignee":    row["assignee_id"],
                    "priority":    row["priority"],
                    "result":      (result or "")[:200],
                },
            )
        except Exception:
            pass

        return {
            "status":      "completed",
            "task_id":     task_id,
            "description": row["description"],
        }

    # ─── CEO delegation ───────────────────────────────────────────────────────

    def ceo_delegate(
        self,
        company_objective: str,
        venture_id: str,
    ) -> dict:
        """
        CEO Agent breaks down a company objective into specific tasks
        and assigns each one. Returns a delegation summary.
        """
        from eos_ai.cognitive_loop import CognitiveLoop
        from eos_ai.agent_runtime import TaskType

        loop   = CognitiveLoop(self.ctx)
        result = loop.run(
            input=(
                f"Break this objective into specific, executable tasks:\n\n"
                f"OBJECTIVE: {company_objective}\n\n"
                f"For each task specify:\n"
                f"- description: what exactly needs to be done (one sentence)\n"
                f"- executor: 'human', 'research_agent', 'sales_agent', "
                f"'content_agent', or 'ai'\n"
                f"- priority: critical / high / normal / low\n"
                f"- estimated_time: brief estimate (e.g. '30 min', '2 hours')\n\n"
                f"Return as a JSON array:\n"
                f'[{{"description": "...", "executor": "...", '
                f'"priority": "...", "estimated_time": "..."}}]\n\n'
                f"Return ONLY the JSON array. No markdown, no explanation."
            ),
            agent="ceo_agent",
            task_type=TaskType.ANALYZE,
            venture_id=venture_id,
        )

        tasks_raw: list[dict] = []
        if result.output:
            try:
                raw = result.output.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    raw   = parts[1] if len(parts) > 1 else raw
                    if raw.startswith("json"):
                        raw = raw[4:]
                parsed = json.loads(raw.strip(), strict=False)
                tasks_raw = parsed if isinstance(parsed, list) else []
            except Exception:
                tasks_raw = []

        tasks_created: list[dict] = []
        ai_tasks:      int = 0
        human_tasks:   int = 0

        for t in tasks_raw:
            if not isinstance(t, dict):
                continue
            desc     = (t.get("description") or "").strip()
            executor = (t.get("executor") or "ai").strip().lower()
            priority = (t.get("priority") or "normal").lower()
            if priority not in ("critical", "high", "normal", "low"):
                priority = "normal"
            if not desc:
                continue

            if executor == "human":
                assignee_type = "human"
                assignee_id   = self.ctx.user_id
                human_tasks  += 1
            else:
                assignee_type = "agent"
                assignee_id   = executor if executor != "ai" else "default_agent"
                ai_tasks     += 1

            task_id = self.assign_task(
                task_description=desc,
                assignee_type=assignee_type,
                assignee_id=assignee_id,
                venture_id=venture_id,
                priority=priority,
                assigned_by="ceo_agent",
            )
            tasks_created.append({
                "task_id":        task_id,
                "description":    desc,
                "executor":       executor,
                "priority":       priority,
                "estimated_time": t.get("estimated_time", ""),
            })

        return {
            "objective":     company_objective,
            "tasks_created": tasks_created,
            "total":         len(tasks_created),
            "ai_tasks":      ai_tasks,
            "human_tasks":   human_tasks,
        }
