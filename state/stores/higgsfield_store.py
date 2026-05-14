"""HiggsFieldStore — canonical write API for the higgsfield_jobs table."""

import json

from state.storage.db import get_conn


class HiggsFieldStore:

    def insert_job(
        self,
        request_id: str,
        venture: str,
        model_id: str,
        arguments: dict,
    ) -> None:
        """Insert a new job. ON CONFLICT (request_id) does nothing."""
        with get_conn() as cur:
            cur.execute(
                """
                INSERT INTO higgsfield_jobs
                    (request_id, venture, model_id, arguments, status, submitted_at)
                VALUES (%s, %s, %s, %s::jsonb, 'queued', now())
                ON CONFLICT (request_id) DO NOTHING
                """,
                (request_id, venture, model_id, json.dumps(arguments)),
            )

    def update_status(
        self,
        request_id: str,
        status: str,
        output_url: str | None = None,
        local_path: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update job status and optional result fields."""
        with get_conn() as cur:
            cur.execute(
                """
                UPDATE higgsfield_jobs
                   SET status=%s,
                       output_url=%s,
                       local_path=%s,
                       error=%s,
                       finished_at=now()
                 WHERE request_id=%s
                """,
                (status, output_url, local_path, error, request_id),
            )
