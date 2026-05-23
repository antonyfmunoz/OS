"""AgentRegistryStore — canonical write API for the agents table."""

import uuid

from state.storage.db import get_conn


class AgentRegistryStore:
    def register_agent(
        self,
        org_id: str,
        name: str,
        agent_type: str = "ai_agent",
        department: str = "",
    ) -> None:
        """Upsert an agent registration. Reactivates if previously deactivated."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO agents
                    (id, org_id, name, type, department, is_active)
                VALUES (%s, %s, %s, %s, %s, true)
                ON CONFLICT (org_id, name)
                DO UPDATE SET is_active = true
                """,
                (str(uuid.uuid4()), org_id, name, agent_type, department),
            )
