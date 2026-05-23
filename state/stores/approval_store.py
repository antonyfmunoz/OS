"""ApprovalStore — canonical write API for the approvals table."""

import json
import uuid
from datetime import datetime, timezone

from state.storage.db import get_conn


class ApprovalStore:
    def create_approval(
        self,
        org_id: str,
        request: dict,
    ) -> str:
        """Insert a pending approval. Returns approval_id (UUID)."""
        approval_id = str(uuid.uuid4())
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO approvals (id, org_id, request_json, status, created_at)
                VALUES (%s, %s, %s, 'pending', NOW())
                """,
                (approval_id, org_id, json.dumps(request)),
            )
        return approval_id

    def approve(
        self,
        org_id: str,
        approval_id: str,
        resolved_by: str,
    ) -> dict | None:
        """Approve a pending request. Returns the request payload or None."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE approvals
                SET status = 'approved',
                    resolved_at = %s,
                    resolved_by = %s
                WHERE id = %s AND org_id = %s
                RETURNING request_json
                """,
                (
                    datetime.now(timezone.utc),
                    resolved_by,
                    approval_id,
                    org_id,
                ),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def reject(
        self,
        org_id: str,
        approval_id: str,
        resolved_by: str,
    ) -> None:
        """Reject a pending request."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE approvals
                SET status = 'rejected',
                    resolved_at = %s,
                    resolved_by = %s
                WHERE id = %s AND org_id = %s
                """,
                (
                    datetime.now(timezone.utc),
                    resolved_by,
                    approval_id,
                    org_id,
                ),
            )
