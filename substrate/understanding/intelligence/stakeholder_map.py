"""
Stakeholder Map — tracks key stakeholders per venture,
their status, influence, and what they need.
"""

import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def add_stakeholder(
    name: str,
    venture: str,
    role: str,
    influence: str = 'medium',
    status: str = 'active',
    notes: str = '',
    email: str = '',
    ctx=None,
) -> bool:
    """
    Add or update a stakeholder entry.
    influence: high/medium/low
    status: active/inactive/prospect/client/partner/investor
    """
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='stakeholder',
            payload={
                'name': name,
                'venture': venture,
                'role': role,
                'influence': influence,
                'status': status,
                'notes': notes,
                'email': email,
                'added_at': datetime.now(PDT).isoformat(),
            },
            handled_by='dex_stakeholders',
        )
        return True
    except Exception as e:
        logger.warning(f'[StakeholderMap] add failed: {e}')
        return False


def get_stakeholders(venture: str = None, ctx=None) -> list[dict]:
    """Get all stakeholders, optionally filtered by venture."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.storage.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            if venture:
                cur.execute('''
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'stakeholder'
                    AND payload_json->>'venture' = %s
                    ORDER BY created_at DESC
                ''', (str(ctx.org_id), venture))
            else:
                cur.execute('''
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'stakeholder'
                    ORDER BY created_at DESC
                ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        seen: set = set()
        stakeholders: list[dict] = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            key = f'{payload.get("name")}_{payload.get("venture")}'
            if key not in seen:
                seen.add(key)
                stakeholders.append(payload)
        return stakeholders
    except Exception as e:
        logger.warning(f'[StakeholderMap] get failed: {e}')
        return []


def generate_stakeholder_brief(venture: str, ctx=None) -> str:
    """Generate a stakeholder map brief for a venture."""
    try:
        from adapters.models.model_router import get_router, TaskType
        from substrate.understanding.intelligence.person_recognition import score_relationship_health
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE) or router.route(TaskType.ANALYSIS)

        stakeholders = get_stakeholders(venture=venture, ctx=ctx)

        if not stakeholders:
            return (
                f'No stakeholders mapped for {venture} yet. '
                f'Use !add_stakeholder to add them.'
            )

        stakeholder_data = []
        for s in stakeholders[:10]:
            health = score_relationship_health(
                name=s.get('name', ''),
                email=s.get('email', ''),
                ctx=ctx,
            )
            stakeholder_data.append({
                **s,
                'health_status': health.get('status', 'Unknown'),
                'days_since': health.get('days_since_contact', 999),
            })

        stakeholder_text = '\n'.join(
            f'- {s["name"]} ({s["role"]}, {s["influence"]} influence, '
            f'{s["status"]}): health={s["health_status"]}, '
            f'last contact {s["days_since"]}d ago'
            for s in stakeholder_data
        )

        return router.call(model, f"""Summarize the stakeholder map
for {venture}.

Stakeholders:
{stakeholder_text}

Provide:
1. Relationship summary (2 sentences)
2. Who needs attention most urgently
3. Who is an untapped opportunity
4. One action to strengthen the most important relationship

Under 100 words.""").strip()

    except Exception as e:
        logger.warning(f'[StakeholderMap] generate_stakeholder_brief failed: {e}')
        return f'Stakeholder brief unavailable: {e}'


def add_board_member(
    name: str,
    email: str,
    venture_id: str,
    role: str = 'advisor',
    notes: str = '',
    ctx=None,
) -> bool:
    """Add a board member or advisor via add_stakeholder."""
    return add_stakeholder(
        name=name,
        venture=venture_id,
        role=role,
        influence='high',
        status='active',
        notes=notes,
        email=email,
        ctx=ctx,
    )


def get_board_members(venture_id: str = None, ctx=None) -> list:
    """Get all board members and advisors (high-influence stakeholders)."""
    stakeholders = get_stakeholders(venture=venture_id, ctx=ctx)
    return [
        s for s in stakeholders
        if s.get('role', '').lower() in
        ('advisor', 'board member', 'investor', 'mentor')
        or s.get('influence') == 'high'
    ]


def generate_board_update_brief(venture_id: str, ctx=None) -> str:
    """Generate a concise board/advisor update for a venture."""
    import json as _j
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.storage.db import get_conn
        from adapters.models.model_router import get_router, TaskType
        ctx = ctx or load_context_from_env()
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        ventures = getattr(ctx, 'ventures', [])
        venture = next(
            (v for v in ventures if v['id'] == venture_id),
            {'name': venture_id}
        )

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type IN ('decision', 'pipeline_entry',
                    'meeting_scheduled', 'revenue')
                AND created_at >= NOW() - INTERVAL '30 days'
                ORDER BY created_at DESC
                LIMIT 15
            """, (str(ctx.org_id),))
            rows = cur.fetchall()

        activity = []
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = _j.loads(p)
            activity.append(str(p)[:100])

        return router.call(model, f"""Draft a board/advisor update
for {venture.get('name', venture_id)}.

Venture context:
- Stage: {venture.get('stage', 'unknown')}
- Offer: {venture.get('offer', 'unknown')}
- North star: {venture.get('north_star', 'unknown')}
- Binding constraint: {venture.get('binding_constraint', 'unknown')}

Recent activity (last 30 days):
{chr(10).join(activity[:10])}

Format as a concise board update under 200 words:
- Headline (one sentence on current state)
- Progress this month
- Key challenges
- What we need from advisors/board
- Next 30 days focus

Direct, no fluff.""").strip()
    except Exception as e:
        logger.warning(f'[StakeholderMap] generate_board_update_brief failed: {e}')
        return f'Board brief unavailable: {e}'
