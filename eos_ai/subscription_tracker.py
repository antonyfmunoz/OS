"""
Subscription Tracker — maintains a registry of active
subscriptions, renewal dates, and costs.
"""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def get_subscriptions(ctx=None) -> list[dict]:
    """Get all tracked subscriptions from Neon (most recent per vendor)."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                SELECT payload_json, created_at FROM events
                WHERE org_id = %s
                AND event_type = 'subscription'
                ORDER BY created_at DESC
            """, (str(ctx.org_id),))
            rows = cur.fetchall()

        subs = []
        seen_vendors: set[str] = set()
        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            vendor = payload.get('vendor', '')
            if vendor not in seen_vendors:
                seen_vendors.add(vendor)
                subs.append(payload)
        return subs
    except Exception as e:
        logger.warning(f'[SubTracker] get_subscriptions failed: {e}')
        return []


def add_subscription(
    vendor: str,
    amount: float,
    billing_cycle: str,
    next_renewal: str,
    category: str = 'Software/SaaS',
    notes: str = '',
    ctx=None,
) -> bool:
    """Add or update a subscription record."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute("""
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            """, (
                str(ctx.org_id),
                'subscription',
                json.dumps({
                    'vendor': vendor,
                    'amount': amount,
                    'billing_cycle': billing_cycle,
                    'next_renewal': next_renewal,
                    'category': category,
                    'notes': notes,
                    'added_at': datetime.now(PDT).isoformat(),
                }),
                'dex_subscriptions',
            ))
        return True
    except Exception as e:
        logger.warning(f'[SubTracker] add_subscription failed: {e}')
        return False


def get_upcoming_renewals(days: int = 14, ctx=None) -> list[dict]:
    """Get subscriptions renewing in the next N days."""
    subs = get_subscriptions(ctx)
    now = datetime.now(PDT)
    cutoff = now + timedelta(days=days)
    upcoming = []
    for s in subs:
        renewal = s.get('next_renewal', '')
        if not renewal:
            continue
        try:
            renewal_dt = datetime.fromisoformat(renewal)
            if renewal_dt.tzinfo is None:
                renewal_dt = renewal_dt.replace(tzinfo=PDT)
            else:
                renewal_dt = renewal_dt.astimezone(PDT)
            if now <= renewal_dt <= cutoff:
                s = dict(s)
                s['days_until'] = (renewal_dt.date() - now.date()).days
                upcoming.append(s)
        except Exception:
            continue
    return sorted(upcoming, key=lambda x: x.get('days_until', 99))


def get_monthly_subscription_total(ctx=None) -> float:
    """Calculate total monthly subscription cost."""
    subs = get_subscriptions(ctx)
    total = 0.0
    for s in subs:
        amount = float(s.get('amount', 0))
        cycle = s.get('billing_cycle', 'monthly').lower()
        if cycle == 'annual':
            total += amount / 12
        elif cycle == 'monthly':
            total += amount
        elif cycle == 'weekly':
            total += amount * 4.33
    return total
