"""
Delegation Tracker — tracks tasks routed to CEO agents
or other parties. Follows up if not completed.
"""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def log_delegation(
    task: str,
    delegated_to: str,
    due_hours: int = 24,
    ctx=None,
) -> bool:
    """Log a delegated task for follow-up tracking."""
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)
        due_at = (now + timedelta(hours=due_hours)).isoformat()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'delegation',
                json.dumps({
                    'task': task,
                    'delegated_to': delegated_to,
                    'status': 'pending',
                    'delegated_at': now.isoformat(),
                    'due_at': due_at,
                }),
                'dex_delegation',
            ))
        return True
    except Exception as e:
        logger.warning(f'[Delegation] log_delegation failed: {e}')
        return False


def get_overdue_delegations(ctx=None) -> list[dict]:
    """Get delegated tasks that are overdue."""
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                SELECT id, payload_json, created_at FROM events
                WHERE org_id = %s
                AND event_type = 'delegation'
                AND payload_json->>'status' = 'pending'
                AND (payload_json->>'due_at')::timestamp < NOW()
                ORDER BY created_at ASC
                LIMIT 10
            """, (str(ctx.org_id),))
            rows = cur.fetchall()

        results = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            payload['event_id'] = str(r['id'])
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[Delegation] get_overdue_delegations failed: {e}')
        return []


def mark_delegation_complete(event_id: str, ctx=None) -> bool:
    """Mark a delegation as completed."""
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                UPDATE events
                SET payload_json = payload_json || '{"status": "completed"}'::jsonb
                WHERE id = %s AND org_id = %s
            """, (event_id, str(ctx.org_id)))
        return True
    except Exception as e:
        logger.warning(f'[Delegation] mark_complete failed: {e}')
        return False
