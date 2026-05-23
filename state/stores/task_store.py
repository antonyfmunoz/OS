"""TaskStore — canonical write API for the tasks table."""

from state.storage.db import get_conn


class TaskStore:
    def create_task(
        self,
        org_id: str,
        venture_id: str | None,
        description: str,
        assignee_type: str,
        assignee_id: str,
        priority: str,
        due_by: str | None = None,
        assigned_by: str = "ai",
    ) -> str:
        """Insert a new task. Returns task_id (UUID)."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO tasks
                    (org_id, venture_id, description, assignee_type,
                     assignee_id, priority, status, due_by, assigned_by)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s)
                RETURNING id
                """,
                (
                    org_id,
                    venture_id,
                    description,
                    assignee_type,
                    assignee_id,
                    priority,
                    due_by,
                    assigned_by,
                ),
            )
            return str(cur.fetchone()["id"])

    def update_status(
        self,
        org_id: str,
        task_id: str,
        status: str,
        extra_fields: dict | None = None,
    ) -> dict | None:
        """
        Update task status and optional extra columns.
        Returns the RETURNING row as dict, or None if not found.
        """
        sets = ["status = %s", "updated_at = now()"]
        params: list = [status]

        if extra_fields:
            for col, val in extra_fields.items():
                sets.append(f"{col} = %s")
                params.append(val)

        params.extend([task_id, org_id])
        sql = (
            f"UPDATE tasks SET {', '.join(sets)} "
            "WHERE id = %s AND org_id = %s "
            "RETURNING id, description, assignee_id, assignee_type, priority"
        )

        with get_conn(org_id) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return dict(row) if row else None

    def set_notion_page_id(
        self,
        org_id: str,
        task_id: str,
        notion_page_id: str,
    ) -> None:
        """Link a Notion page to a task."""
        with get_conn(org_id) as cur:
            cur.execute(
                "UPDATE tasks SET notion_page_id = %s WHERE id::text = %s AND org_id = %s",
                (notion_page_id, task_id, org_id),
            )
