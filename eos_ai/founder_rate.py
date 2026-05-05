"""
Founder Rate — Dan Martell's framework for valuing
founder time and making delegation decisions.
Leverage Loop = Annual income / 2000 hours / 4
"""

import json
import logging
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(_Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def calculate_founder_rate(
    annual_income: float,
    working_hours_per_year: int = 2000,
) -> dict:
    """
    FR = (annual_income / working_hours) / 4
    Any task someone can do for <= FR should be delegated.
    """
    hourly_rate = annual_income / working_hours_per_year if working_hours_per_year else 0
    founder_rate = hourly_rate / 4

    return {
        'annual_income': annual_income,
        'hourly_rate': round(hourly_rate, 2),
        'founder_rate': round(founder_rate, 2),
        'interpretation': (
            f'Delegate any task that can be done for '
            f'${founder_rate:.2f}/hour or less.'
        ),
    }


def store_founder_rate(annual_income: float, ctx=None) -> bool:
    """Store Founder Rate in Neon for use across the system."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        rate = calculate_founder_rate(annual_income)

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''INSERT INTO events (org_id, event_type, payload_json, handled_by)
                   VALUES (%s, %s, %s, %s)''',
                (
                    str(ctx.org_id),
                    'founder_rate',
                    json.dumps({**rate, 'set_at': datetime.now(PDT).isoformat()}),
                    'dex_founder_rate',
                ),
            )
        return True
    except Exception as e:
        logger.warning(f'[FounderRate] store failed: {e}')
        return False


def get_current_founder_rate(ctx=None) -> dict:
    """Get the most recently set Founder Rate."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''SELECT payload_json FROM events
                   WHERE org_id = %s AND event_type = 'founder_rate'
                   ORDER BY created_at DESC LIMIT 1''',
                (str(ctx.org_id),),
            )
            row = cur.fetchone()

        if row:
            payload = row['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            return payload
        return {}
    except Exception as e:
        logger.warning(f'[FounderRate] get failed: {e}')
        return {}


def log_time_block(
    activity: str,
    duration_minutes: int,
    energy: int,
    estimated_value: float = 0,
    ctx=None,
) -> bool:
    """
    Log a time block for the Time and Energy Audit.
    energy: -2 (drain) to +2 (gain)
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''INSERT INTO events (org_id, event_type, payload_json, handled_by)
                   VALUES (%s, %s, %s, %s)''',
                (
                    str(ctx.org_id),
                    'time_audit_block',
                    json.dumps({
                        'activity': activity,
                        'duration_minutes': duration_minutes,
                        'energy': energy,
                        'estimated_value': estimated_value,
                        'logged_at': datetime.now(PDT).isoformat(),
                    }),
                    'dex_time_audit',
                ),
            )
        return True
    except Exception as e:
        logger.warning(f'[FounderRate] log_time_block failed: {e}')
        return False


def get_time_audit_summary(days: int = 7, ctx=None) -> dict:
    """Summarize time and energy data for the week."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''SELECT payload_json FROM events
                   WHERE org_id = %s AND event_type = 'time_audit_block'
                   AND created_at >= NOW() - INTERVAL '1 day' * %s
                   ORDER BY created_at DESC''',
                (str(ctx.org_id), int(days)),
            )
            rows = cur.fetchall()

        total_minutes = 0
        energy_weighted = 0
        high_value_minutes = 0
        low_value_minutes = 0
        activities = []

        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            mins = payload.get('duration_minutes', 0)
            energy = payload.get('energy', 0)
            value = payload.get('estimated_value', 0)

            total_minutes += mins
            energy_weighted += energy * mins
            if value > 100:
                high_value_minutes += mins
            else:
                low_value_minutes += mins
            activities.append(payload)

        avg_energy = energy_weighted / total_minutes if total_minutes > 0 else 0

        return {
            'total_hours': round(total_minutes / 60, 1),
            'avg_energy': round(avg_energy, 2),
            'high_value_pct': round(
                high_value_minutes / total_minutes * 100, 1
            ) if total_minutes > 0 else 0,
            'low_value_pct': round(
                low_value_minutes / total_minutes * 100, 1
            ) if total_minutes > 0 else 0,
            'activities': activities,
        }
    except Exception as e:
        logger.warning(f'[FounderRate] audit summary failed: {e}')
        return {}


def add_to_no_list(item: str, reason: str = '', ctx=None) -> bool:
    """Add something to Antony's No List."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'no_list',
                json.dumps({
                    'item': item,
                    'reason': reason,
                    'added_at': datetime.now(PDT).isoformat(),
                }),
                'dex_no_list',
            ))
        return True
    except Exception as e:
        logger.warning(f'[NoList] add failed: {e}')
        return False


def get_no_list(ctx=None) -> list[dict]:
    """Get Antony's No List (deduplicated, newest-first)."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'no_list'
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()
        results = []
        seen: set[str] = set()
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            item = p.get('item', '')
            if item and item not in seen:
                seen.add(item)
                results.append(p)
        return results
    except Exception as e:
        logger.warning(f'[NoList] get failed: {e}')
        return []


def check_against_no_list(text: str, ctx=None) -> list[str]:
    """Return any No List items found in text."""
    no_list = get_no_list(ctx)
    text_lower = text.lower()
    return [
        item['item']
        for item in no_list
        if item.get('item', '').lower() in text_lower
    ]


def detect_delegation_threshold(ctx=None) -> list[dict]:
    """
    Detect tasks Antony is repeatedly handling himself
    that should be delegated. Returns list of violations.
    Looks for dex_task events appearing 3+ times in 30 days.
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                SELECT
                    payload_json->>'task' as task_text,
                    COUNT(*) as occurrence_count
                FROM events
                WHERE org_id = %s
                AND event_type = 'dex_task'
                AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY payload_json->>'task'
                HAVING COUNT(*) >= 3
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (str(ctx.org_id),))
            rows = cur.fetchall()

        return [
            {
                'task': r['task_text'] or '',
                'occurrences': r['occurrence_count'],
                'recommendation': (
                    f'This has appeared {r["occurrence_count"]}x. '
                    'Build a playbook or delegate permanently.'
                ),
            }
            for r in rows
            if r['task_text'] and len(r['task_text']) > 10
        ]
    except Exception as e:
        logger.warning(f'[FounderRate] detect_delegation_threshold failed: {e}')
        return []
