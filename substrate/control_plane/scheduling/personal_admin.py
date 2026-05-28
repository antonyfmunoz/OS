"""
Personal Admin — important dates, gift research,
and personal appointment management.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
from substrate.self_model import get_handler_prefix as _ghp

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def add_important_date(
    person: str,
    date: str,
    date_type: str,
    notes: str = '',
    ctx=None,
) -> bool:
    """
    Add an important date to the events table.
    date_type: birthday | anniversary | work_anniversary | other
    date format: MM-DD (recurring yearly) or YYYY-MM-DD (one-time)
    """
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()
        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='important_date',
            payload={
                'person': person,
                'date': date,
                'type': date_type,
                'notes': notes,
                'added_at': datetime.now(PDT).isoformat(),
            },
            handled_by=f'{_ghp()}personal',
        )
        return True
    except Exception as e:
        logger.warning(f'[PersonalAdmin] add_important_date failed: {e}')
        return False


def get_upcoming_dates(days: int = 30, ctx=None) -> list[dict]:
    """Get important dates coming up in the next N days, sorted by days_until."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.storage.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'important_date'
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        now = datetime.now(PDT)
        upcoming = []
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            date_str = p.get('date', '')
            if not date_str:
                continue
            try:
                # MM-DD recurring
                if len(date_str) == 5 and '-' in date_str:
                    month, day = date_str.split('-')
                    candidate = now.replace(month=int(month), day=int(day),
                                            hour=0, minute=0, second=0, microsecond=0)
                    if candidate.date() < now.date():
                        candidate = candidate.replace(year=now.year + 1)
                    days_until = (candidate.date() - now.date()).days
                else:
                    target = datetime.fromisoformat(date_str).replace(tzinfo=PDT)
                    days_until = (target.date() - now.date()).days

                if 0 <= days_until <= days:
                    p['days_until'] = days_until
                    upcoming.append(p)
            except Exception:
                continue

        return sorted(upcoming, key=lambda x: x.get('days_until', 99))
    except Exception as e:
        logger.warning(f'[PersonalAdmin] get_upcoming_dates failed: {e}')
        return []


def research_gift(
    person: str,
    occasion: str,
    budget: float = 100,
    context: str = '',
) -> str:
    """
    Research gift ideas for a person and occasion.
    Returns formatted list of 5 specific gift suggestions.
    """
    try:
        from substrate.contracts.agent_types import TaskType
        from adapters.models.model_router import get_router
        from substrate.understanding.intelligence.person_recognition import build_intelligence_profile
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        try:
            profile = build_intelligence_profile(name=person)
            person_context = profile.notes or context or 'No specific context available'
        except Exception:
            person_context = context or 'No specific context available'

        return router.call(model, f"""Research gift ideas.

Person: {person}
Occasion: {occasion}
Budget: ${budget}
What I know about them: {person_context}

Suggest 5 specific, thoughtful gift ideas.
For each: name, why it fits, approximate price, where to get it.
Prioritize personalized over generic.
Match the budget closely.

Format as a numbered list.""").strip()
    except Exception as e:
        return f'Gift research unavailable: {e}'
