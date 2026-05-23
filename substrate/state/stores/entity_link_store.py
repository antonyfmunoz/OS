"""EntityLinkStore — canonical write API for the entity_links table."""

import json

from substrate.state.storage.db import get_conn


class EntityLinkStore:

    def insert_link(
        self,
        org_id: str,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        relationship: str,
        metadata: dict | None = None,
    ) -> str:
        """Insert a directed entity link. Returns link id (UUID)."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO entity_links
                    (org_id, from_type, from_id, to_type, to_id,
                     relationship, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    org_id,
                    from_type, from_id,
                    to_type, to_id,
                    relationship,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            return str(cur.fetchone()["id"])
