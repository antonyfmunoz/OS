"""
Event Manager — coordinates conferences, offsites, client dinners,
team events, and speaking engagements. Distinct from calendar events —
these are multi-day or multi-stakeholder events requiring logistics.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def create_event(
    name: str,
    event_type: str,
    date: str,
    location: str = '',
    attendees: list = None,
    budget: float = 0,
    notes: str = '',
    ctx=None,
) -> dict:
    """
    Create an event record with AI-generated logistics checklist.
    event_type: conference|offsite|client_dinner|team_event|speaking|podcast|media
    """
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        from runtime.model_router import get_router, TaskType
        ctx = ctx or load_context_from_env()
        router = get_router()

        checklist_raw = router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Generate a logistics checklist for this event.

Event: {name}
Type: {event_type}
Date: {date}
Location: {location or 'TBD'}
Attendees: {len(attendees or [])}
Budget: ${budget:,.0f}

Return JSON only:
{{"checklist": [{{"item": "task description", "owner": "DEX or Founder", "due": "X days before", "done": false}}]}}""").strip()

        checklist_data = []
        try:
            if '```' in checklist_raw:
                checklist_raw = checklist_raw.split('```')[1].replace('json', '').strip()
            checklist_data = json.loads(checklist_raw).get('checklist', [])
        except Exception:
            pass

        event = {
            'name': name,
            'type': event_type,
            'date': date,
            'location': location,
            'attendees': attendees or [],
            'budget': budget,
            'notes': notes,
            'checklist': checklist_data,
            'status': 'planning',
            'created_at': datetime.now(PDT).isoformat(),
        }

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'managed_event',
                json.dumps(event),
                'dex_events',
            ))

        return event
    except Exception as e:
        logger.warning(f'[EventManager] create_event failed: {e}')
        return {}


def get_events(upcoming_only: bool = True, ctx=None) -> list:
    """Get managed events, ordered by date ascending."""
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'managed_event'
                ORDER BY (payload_json->>'date') ASC
                LIMIT 20
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        results = []
        now_str = datetime.now(PDT).strftime('%Y-%m-%d')
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if upcoming_only and payload.get('date', '') < now_str:
                continue
            payload['event_id'] = str(r['id'])
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[EventManager] get_events failed: {e}')
        return []


def log_speaking_engagement(
    event_name: str,
    organizer: str,
    organizer_email: str,
    date: str,
    topic: str = '',
    format: str = 'talk',
    status: str = 'inquired',
    ctx=None,
) -> bool:
    """
    Log a speaking engagement or podcast appearance.
    format: talk|panel|podcast|interview|workshop|webinar
    status: inquired|confirmed|preparing|completed|declined
    """
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'speaking_engagement',
                json.dumps({
                    'event_name': event_name,
                    'organizer': organizer,
                    'organizer_email': organizer_email,
                    'date': date,
                    'topic': topic,
                    'format': format,
                    'status': status,
                    'logged_at': datetime.now(PDT).isoformat(),
                }),
                'dex_speaking',
            ))
        return True
    except Exception as e:
        logger.warning(f'[EventManager] log_speaking failed: {e}')
        return False


def draft_talking_points(
    topic: str,
    audience: str,
    duration_minutes: int = 30,
    format: str = 'talk',
    ctx=None,
) -> str:
    """Draft talking points for a speaking engagement."""
    try:
        from runtime.context import load_context_from_env
        from runtime.model_router import get_router, TaskType
        ctx = ctx or load_context_from_env()
        router = get_router()

        ventures = getattr(ctx, 'ventures', [])
        venture_context = '\n'.join(
            f'- {v.get("name")}: {v.get("offer", "")}' for v in ventures
        ) if ventures else 'Entrepreneur and founder'

        # Substrate-neutral speaker/brand framing from ctx.
        _speaker = (
            getattr(ctx, 'founder_name', None)
            or getattr(ctx, 'user_name', None)
            or 'the founder'
        )
        _brand_voice = (
            getattr(ctx, 'brand_voice', None)
            or 'direct, structured, founder-operator tone'
        )

        return router.call_with_fallback(TaskType.ANALYSIS, f"""Draft talking points for a speaking engagement.

Speaker: {_speaker}
Ventures: {venture_context}
Topic: {topic}
Audience: {audience}
Format: {format}
Duration: {duration_minutes} minutes

Create:
# Talking Points: {topic}

## Opening hook
## Core message
## Key points (3-5)
## Stories to tell
## Audience takeaways
## Closing
## Q&A prep

Brand voice: {_brand_voice}.""").strip()
    except Exception as e:
        return f'Talking points unavailable: {e}'


def log_pr_media_inquiry(
    outlet: str,
    contact_name: str,
    contact_email: str,
    topic: str,
    deadline: str = '',
    inquiry_type: str = 'interview',
    ctx=None,
) -> bool:
    """
    Log a PR or media inquiry.
    inquiry_type: interview|quote|feature|podcast|press_release
    """
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'pr_media_inquiry',
                json.dumps({
                    'outlet': outlet,
                    'contact_name': contact_name,
                    'contact_email': contact_email,
                    'topic': topic,
                    'deadline': deadline,
                    'type': inquiry_type,
                    'status': 'received',
                    'logged_at': datetime.now(PDT).isoformat(),
                }),
                'dex_pr',
            ))
        return True
    except Exception as e:
        logger.warning(f'[EventManager] log_pr failed: {e}')
        return False
