"""
Buyback Rate — Dan Martell's framework for valuing
founder time and making delegation decisions.
Buyback Rate = Annual income / 2000 hours / 4
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def calculate_buyback_rate(
    annual_income: float,
    working_hours_per_year: int = 2000,
) -> dict:
    """
    BBR = (annual_income / working_hours) / 4
    Any task someone can do for <= BBR should be delegated.
    """
    hourly_rate = annual_income / working_hours_per_year if working_hours_per_year else 0
    buyback_rate = hourly_rate / 4

    return {
        'annual_income': annual_income,
        'hourly_rate': round(hourly_rate, 2),
        'buyback_rate': round(buyback_rate, 2),
        'interpretation': (
            f'Delegate any task that can be done for '
            f'${buyback_rate:.2f}/hour or less.'
        ),
    }


def store_buyback_rate(annual_income: float, ctx=None) -> bool:
    """Store Buyback Rate in Neon for use across the system."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        rate = calculate_buyback_rate(annual_income)

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''INSERT INTO events (org_id, event_type, payload_json, handled_by)
                   VALUES (%s, %s, %s, %s)''',
                (
                    str(ctx.org_id),
                    'buyback_rate',
                    json.dumps({**rate, 'set_at': datetime.now(PDT).isoformat()}),
                    'dex_buyback',
                ),
            )
        return True
    except Exception as e:
        logger.warning(f'[BuybackRate] store failed: {e}')
        return False


def get_current_buyback_rate(ctx=None) -> dict:
    """Get the most recently set Buyback Rate."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''SELECT payload_json FROM events
                   WHERE org_id = %s AND event_type = 'buyback_rate'
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
        logger.warning(f'[BuybackRate] get failed: {e}')
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
        logger.warning(f'[BuybackRate] log_time_block failed: {e}')
        return False


def get_time_audit_summary(days: int = 7, ctx=None) -> dict:
    """Summarize time and energy data for the week."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        import json as _json
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                f'''SELECT payload_json FROM events
                    WHERE org_id = %s AND event_type = 'time_audit_block'
                    AND created_at >= NOW() - INTERVAL '{int(days)} days'
                    ORDER BY created_at DESC''',
                (str(ctx.org_id),),
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
                payload = _json.loads(payload)
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
        logger.warning(f'[BuybackRate] audit summary failed: {e}')
        return {}
