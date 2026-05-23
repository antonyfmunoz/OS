"""SkillStore — canonical API for the skills table."""

import uuid

from substrate.state.storage.db import get_conn


class SkillStore:

    def get_by_name(
        self,
        org_id: str,
        name: str,
    ) -> dict | None:
        """Fetch a skill by (org_id, name). Returns {id, content, version} or None."""
        with get_conn(org_id) as cur:
            cur.execute(
                "SELECT id, content, version FROM skills WHERE org_id = %s AND name = %s",
                (org_id, name),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {"id": str(row["id"]), "content": row["content"] or "", "version": int(row["version"] or 1)}

    def upsert_skill(
        self,
        org_id: str,
        name: str,
        content: str,
        version: int = 1,
    ) -> None:
        """Insert or update a skill by (org_id, name). ON CONFLICT updates content+version."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO skills (id, org_id, name, content, version)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (org_id, name)
                DO UPDATE SET content = EXCLUDED.content,
                              version = EXCLUDED.version
                """,
                (str(uuid.uuid4()), org_id, name, content, version),
            )

    def update_skill_content(
        self,
        org_id: str,
        skill_id: str,
        content: str,
    ) -> None:
        """Update skill content by id, auto-incrementing version."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE skills
                SET content = %s, version = version + 1, updated_at = NOW()
                WHERE id = %s AND org_id = %s
                """,
                (content, skill_id, org_id),
            )

    def update_skill_content_by_name(
        self,
        org_id: str,
        name: str,
        content: str,
    ) -> None:
        """Update skill content by name, auto-incrementing version."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE skills SET content = %s, version = version + 1
                WHERE org_id = %s AND name = %s
                """,
                (content, org_id, name),
            )
