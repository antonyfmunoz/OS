"""EmbeddingStore — canonical write API for the embeddings table."""

from state.storage.db import get_conn


class EmbeddingStore:

    def upsert_embedding(
        self,
        org_id: str,
        interaction_id: str,
        embedding_json: str,
        content_preview: str,
        embedding_model: str,
    ) -> bool:
        """Delete-then-insert embedding for an interaction. Returns True on success."""
        with get_conn(org_id) as cur:
            cur.execute(
                "DELETE FROM embeddings "
                "WHERE interaction_id = %s AND org_id = %s",
                (interaction_id, org_id),
            )
            cur.execute(
                """
                INSERT INTO embeddings
                    (interaction_id, org_id, embedding,
                     content_preview, embedding_model)
                VALUES (%s, %s, %s::vector, %s, %s)
                """,
                (
                    interaction_id,
                    org_id,
                    embedding_json,
                    content_preview,
                    embedding_model,
                ),
            )
        return True
