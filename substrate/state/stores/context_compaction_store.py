"""ContextCompactionStore — canonical write API for the context_compactions table."""

import json

from substrate.state.storage.db import get_conn


class ContextCompactionStore:
    def insert_compaction(
        self,
        org_id: str,
        session_id: str,
        generation: int,
        brief: dict,
        messages_compressed: int,
        tokens_before: int,
    ) -> str:
        """Insert a context compaction record. Returns id (UUID)."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO context_compactions
                    (org_id, session_id, generation, brief_json,
                     messages_compressed, tokens_before)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    org_id,
                    session_id,
                    generation,
                    json.dumps(brief),
                    messages_compressed,
                    tokens_before,
                ),
            )
            return str(cur.fetchone()["id"])
