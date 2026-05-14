"""
OKR Tracker — tracks Objectives and Key Results per venture.
Weekly check-in cadence. Stored in Neon events table.
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


def set_okr(
    objective: str,
    key_results: list,
    venture_id: str,
    quarter: str = None,
    ctx=None,
) -> bool:
    """
    Set an OKR for a venture.
    key_results: [{"kr": str, "target": float, "unit": str, "current": float}]
    """
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)
        if not quarter:
            month = now.month
            quarter = f'Q{(month - 1) // 3 + 1} {now.year}'

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'okr',
                json.dumps({
                    'objective': objective,
                    'key_results': key_results,
                    'venture_id': venture_id,
                    'quarter': quarter,
                    'created_at': now.isoformat(),
                }),
                'dex_okr',
            ))
        return True
    except Exception as e:
        logger.warning(f'[OKR] set_okr failed: {e}')
        return False


def get_okrs(venture_id: str = None, ctx=None) -> list:
    """Get current quarter OKRs, optionally filtered by venture."""
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)
        current_quarter = f'Q{(now.month - 1) // 3 + 1} {now.year}'

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'okr'
                AND payload_json->>'quarter' = %s
                ORDER BY created_at DESC
            """, (str(ctx.org_id), current_quarter))
            rows = cur.fetchall()

        results = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if venture_id and payload.get('venture_id') != venture_id:
                continue
            payload['event_id'] = str(r['id'])
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[OKR] get_okrs failed: {e}')
        return []


def generate_okr_report(ctx=None) -> str:
    """Generate OKR progress report for all ventures."""
    okrs = get_okrs(ctx=ctx)
    if not okrs:
        return 'No OKRs set for this quarter. Use `!okr set` to add objectives.'

    now = datetime.now(PDT)
    quarter = f'Q{(now.month - 1) // 3 + 1}'
    lines = [f'**🎯 OKR Report — {quarter}:**']
    for okr in okrs:
        venture = okr.get('venture_id', 'Unknown')
        objective = okr.get('objective', '')
        lines.append(f'\n**{venture} — {objective}**')
        for kr in okr.get('key_results', []):
            target = float(kr.get('target', 0))
            current = float(kr.get('current', 0))
            unit = kr.get('unit', '')
            pct = (current / target * 100) if target > 0 else 0
            bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
            lines.append(
                f'• {kr["kr"]}\n'
                f'  [{bar}] {pct:.0f}% ({unit}{current:.0f} / {unit}{target:.0f})'
            )
    return '\n'.join(lines)
