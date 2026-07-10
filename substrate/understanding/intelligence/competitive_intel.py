"""
Competitive Intelligence — tracks competitor signals
and synthesizes implications for each venture.
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

def _competitors_for(venture: str, ctx=None) -> list[str]:
    """Competitor watch-list for a venture — from the tenant's BIS at runtime.

    NEVER hardcode competitors: a fixed per-slug dict would leak one tenant's
    competitive intel into every seat. Reads BIS.main_competitors; returns []
    when unavailable so callers degrade to signals-only synthesis.
    """
    try:
        from substrate.state.business.business_instance import BusinessInstanceManager
        from substrate.state.context.context import load_context_from_env
        ctx = ctx or load_context_from_env()
        bis = BusinessInstanceManager(ctx).get_bis(venture)
        comps = getattr(bis, 'main_competitors', None) if bis else None
        return [str(c) for c in comps] if comps else []
    except Exception:
        return []


def log_competitor_signal(
    venture: str,
    competitor: str,
    signal: str,
    implication: str = '',
    ctx=None,
) -> bool:
    """Log a competitor signal to Neon."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='competitor_signal',
            payload={
                'venture': venture,
                'competitor': competitor,
                'signal': signal,
                'implication': implication,
                'logged_at': datetime.now(PDT).isoformat(),
            },
            handled_by='competitive_intel',
        )
        return True
    except Exception as e:
        logger.warning(f'[CompetitiveIntel] log failed: {e}')
        return False


def get_recent_signals(venture: str = None, days: int = 7, ctx=None) -> list[dict]:
    """Get recent competitor signals."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.storage.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            if venture:
                cur.execute('''
                    SELECT payload_json, created_at FROM events
                    WHERE org_id = %s
                    AND event_type = 'competitor_signal'
                    AND payload_json->>'venture' = %s
                    AND created_at >= NOW() - INTERVAL '1 day' * %s
                    ORDER BY created_at DESC
                    LIMIT 20
                ''', (str(ctx.org_id), venture, days))
            else:
                cur.execute('''
                    SELECT payload_json, created_at FROM events
                    WHERE org_id = %s
                    AND event_type = 'competitor_signal'
                    AND created_at >= NOW() - INTERVAL '1 day' * %s
                    ORDER BY created_at DESC
                    LIMIT 20
                ''', (str(ctx.org_id), days))
            rows = cur.fetchall()

        results = []
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            results.append(payload)
        return results
    except Exception as e:
        logger.warning(f'[CompetitiveIntel] get_recent_signals failed: {e}')
        return []


def synthesize_competitive_landscape(venture: str, ctx=None) -> str:
    """
    Use LLM to synthesize competitive landscape for a venture.
    Pulls from signals + knowledge files.
    """
    try:
        from substrate.contracts.agent_types import TaskType
        from substrate.sockets.intelligence_port import get_router
        router = get_router()
        model = router.route(TaskType.ANALYSIS) or router.route(TaskType.FAST_RESPONSE)

        signals = get_recent_signals(venture=venture, days=30, ctx=ctx)
        signals_text = '\n'.join(
            f'- {s.get("competitor")}: {s.get("signal", "")[:100]}'
            for s in signals[:10]
        ) if signals else 'No recent signals logged.'

        competitors = _competitors_for(venture, ctx=ctx)

        prompt = f"""Synthesize the competitive landscape for {venture}.

Known competitors/signals to watch: {', '.join(competitors[:5])}

Recent signals logged:
{signals_text}

Provide:
1. Current competitive position (1-2 sentences)
2. Biggest competitive threat right now
3. One opportunity the competition is missing
4. Recommended positioning response

Under 150 words. Direct."""

        return router.call(model, prompt).strip()
    except Exception as e:
        logger.warning(f'[CompetitiveIntel] synthesis failed: {e}')
        return f'Competitive synthesis unavailable: {e}'
