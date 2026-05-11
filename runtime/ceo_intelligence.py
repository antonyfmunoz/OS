"""
CEO Intelligence — real-time business diagnostics.

Gives the CEO agent data-driven awareness of:
- Active constraint (Leads/Sales/Delivery/Profit)
- Offer stage position (I/II/III)
- Funnel metrics vs benchmarks
- Agent performance this week
- CEO daily brief

Reads benchmarks from venture primitives.
Never hardcodes business-specific thresholds.
The harness reads data. The CEO agent reasons.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

CONSTRAINT_LEADS = 'leads'
CONSTRAINT_SALES = 'sales'
CONSTRAINT_DELIVERY = 'delivery'
CONSTRAINT_PROFIT = 'profit'

# Which agents own each constraint system
CONSTRAINT_AGENTS = {
    CONSTRAINT_LEADS: [
        'research_agent',
        'outreach_agent',
        'content_agent',
        'intelligence_agent',
    ],
    CONSTRAINT_SALES: [
        'sales_agent',
    ],
    CONSTRAINT_DELIVERY: [
        'customer_success_agent',
    ],
    CONSTRAINT_PROFIT: [
        'finance_agent',
    ],
    # Always active regardless of constraint
    '_always_active': [
        'operations_agent',
    ],
}

DEFAULT_BENCHMARKS = {
    'b2c_coaching': {
        'dms_per_week': 50,
        'reply_rate_pct': 15,
        'call_rate_pct': 30,
        'close_rate_pct': 20,
        'cac_payback_days': 30,
        'ltv_cac_ratio': 3.0,
    },
    'b2b_saas': {
        'dms_per_week': 20,
        'reply_rate_pct': 10,
        'call_rate_pct': 25,
        'close_rate_pct': 15,
        'cac_payback_days': 90,
        'ltv_cac_ratio': 5.0,
    },
    'content': {
        'dms_per_week': 10,
        'reply_rate_pct': 20,
        'call_rate_pct': 15,
        'close_rate_pct': 10,
        'cac_payback_days': 0,
        'ltv_cac_ratio': 0,
    },
    'default': {
        'dms_per_week': 30,
        'reply_rate_pct': 15,
        'call_rate_pct': 25,
        'close_rate_pct': 20,
        'cac_payback_days': 30,
        'ltv_cac_ratio': 3.0,
    },
}


def _get_benchmarks(venture_id: str) -> dict:
    """
    Get benchmarks from venture primitives.
    Falls back to business model defaults.
    Never hardcodes venture-specific numbers.
    """
    ventures = json.loads(
        os.getenv('VENTURES_JSON', '[]')
    )
    v = next(
        (x for x in ventures
         if x.get('id') == venture_id), {}
    )
    if v.get('benchmarks'):
        return v['benchmarks']
    model = (
        v.get('business_model', 'default')
        .lower()
        .replace(' ', '_')
        .replace('-', '_')
    )
    for key in DEFAULT_BENCHMARKS:
        if key != 'default' and (
            key in model or model in key
        ):
            return DEFAULT_BENCHMARKS[key]
    return DEFAULT_BENCHMARKS['default']


def get_funnel_metrics(
    venture_id: str,
    ctx=None,
    days: int = 7,
) -> dict:
    """
    Read live funnel metrics from Neon.
    Returns current outreach → close funnel state.
    """
    try:
        from runtime.context import (
            load_context_from_env,
        )
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()
        since = datetime.now(PDT) - timedelta(
            days=days
        )

        m: dict = {
            'dms_sent': 0,
            'replies': 0,
            'calls_booked': 0,
            'sales': 0,
            'revenue': 0.0,
            'customers_total': 0,
            'revenue_total': 0.0,
        }

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT COUNT(*) as cnt
                FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'dm_sent','outreach_sent',
                    'message_sent'
                )
                AND created_at >= %s
            ''', (str(ctx.org_id),
                  since.isoformat()))
            row = cur.fetchone()
            m['dms_sent'] = (
                row['cnt'] if row else 0
            )

            cur.execute('''
                SELECT COUNT(*) as cnt
                FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'dm_reply','lead_replied',
                    'reply_received'
                )
                AND created_at >= %s
            ''', (str(ctx.org_id),
                  since.isoformat()))
            row = cur.fetchone()
            m['replies'] = (
                row['cnt'] if row else 0
            )

            cur.execute('''
                SELECT COUNT(*) as cnt
                FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'call_booked',
                    'meeting_scheduled',
                    'calendly_booking'
                )
                AND created_at >= %s
            ''', (str(ctx.org_id),
                  since.isoformat()))
            row = cur.fetchone()
            m['calls_booked'] = (
                row['cnt'] if row else 0
            )

            cur.execute('''
                SELECT COUNT(*) as cnt,
                COALESCE(SUM(
                    (payload_json->>'amount')
                    ::numeric
                ), 0) as total
                FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'sale','payment_received',
                    'revenue'
                )
                AND created_at >= %s
            ''', (str(ctx.org_id),
                  since.isoformat()))
            row = cur.fetchone()
            m['sales'] = (
                row['cnt'] if row else 0
            )
            m['revenue'] = float(
                row['total'] if row else 0
            )

            cur.execute('''
                SELECT COUNT(*) as cnt,
                COALESCE(SUM(
                    (payload_json->>'amount')
                    ::numeric
                ), 0) as total
                FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'sale','payment_received'
                )
            ''', (str(ctx.org_id),))
            row = cur.fetchone()
            m['customers_total'] = (
                row['cnt'] if row else 0
            )
            m['revenue_total'] = float(
                row['total'] if row else 0
            )

        dms = max(m['dms_sent'], 1)
        m['reply_rate'] = round(
            m['replies'] / dms * 100, 1
        )
        m['call_rate'] = round(
            m['calls_booked']
            / max(m['replies'], 1) * 100, 1
        )
        m['close_rate'] = round(
            m['sales']
            / max(m['calls_booked'], 1) * 100, 1
        )
        m['period_days'] = days
        return m

    except Exception as e:
        logger.warning(
            f'[CEOIntel] funnel error: {e}'
        )
        return {
            'dms_sent': 0, 'replies': 0,
            'calls_booked': 0, 'sales': 0,
            'revenue': 0.0, 'reply_rate': 0,
            'call_rate': 0, 'close_rate': 0,
            'customers_total': 0,
            'revenue_total': 0.0,
            'period_days': days,
        }


def diagnose_constraint(
    venture_id: str,
    ctx=None,
) -> dict:
    """
    Identify the one active business constraint.
    Uses More → Better → New logic.
    Reads benchmarks from venture primitives.

    Returns:
    {
      constraint: str,
      confidence: float,
      diagnosis: str,
      recommendation: str,
      phase: 'more|better|new',
      active_agents: list[str],
      idle_agents: list[str],
      metrics: dict,
      benchmarks: dict,
    }
    """
    benchmarks = _get_benchmarks(venture_id)
    metrics = get_funnel_metrics(venture_id, ctx)

    dms = metrics.get('dms_sent', 0)
    reply_rate = metrics.get('reply_rate', 0)
    call_rate = metrics.get('call_rate', 0)
    close_rate = metrics.get('close_rate', 0)
    customers = metrics.get('customers_total', 0)
    revenue = metrics.get('revenue_total', 0.0)

    dm_target = benchmarks.get('dms_per_week', 30)
    reply_target = benchmarks.get(
        'reply_rate_pct', 15
    )
    call_target = benchmarks.get(
        'call_rate_pct', 25
    )
    close_target = benchmarks.get(
        'close_rate_pct', 20
    )

    # Apply More → Better → New
    if dms < dm_target * 0.6:
        constraint = CONSTRAINT_LEADS
        confidence = 0.9
        phase = 'more'
        diagnosis = (
            f'Volume is the problem. '
            f'{dms} DMs sent vs {dm_target} target. '
            f'Not enough data to evaluate anything else.'
        )
        recommendation = (
            f'Do MORE. Get to {dm_target}+ DMs/week '
            f'before changing any other variable.'
        )

    elif (dms >= dm_target * 0.6
          and reply_rate < reply_target * 0.7):
        constraint = CONSTRAINT_LEADS
        confidence = 0.85
        phase = 'better'
        diagnosis = (
            f'Volume at {dms} DMs but reply rate '
            f'{reply_rate}% vs {reply_target}% target. '
            f'Opener or ICP targeting problem.'
        )
        recommendation = (
            'Make it BETTER. Test one variable — '
            'opener angle OR ICP targeting, not both. '
            '70% current best, 20% variation, '
            '10% experiment.'
        )

    elif (reply_rate >= reply_target * 0.7
          and call_rate < call_target * 0.7):
        constraint = CONSTRAINT_SALES
        confidence = 0.85
        phase = 'better'
        diagnosis = (
            f'Reply rate {reply_rate}% acceptable '
            f'but call rate {call_rate}% vs '
            f'{call_target}% target. '
            f'Conversations dying before calls book.'
        )
        recommendation = (
            'Sales Agent: diagnose where '
            'conversations die. Fix that one point. '
            'Pain before pitch on every conversation.'
        )

    elif (call_rate >= call_target * 0.7
          and close_rate < close_target * 0.7
          and metrics.get('calls_booked', 0) > 0):
        constraint = CONSTRAINT_SALES
        confidence = 0.9
        phase = 'better'
        diagnosis = (
            f'Calls happening but close rate '
            f'{close_rate}% vs {close_target}% target. '
            f'Closing or offer proof problem.'
        )
        recommendation = (
            'Sales Agent: apply direct ask on every '
            'call. Diagnose objection pattern. '
            'Does the offer feel like a steal?'
        )

    elif (customers > 0
          and revenue > 0
          and revenue / max(customers, 1) < 800):
        constraint = CONSTRAINT_DELIVERY
        confidence = 0.75
        phase = 'better'
        diagnosis = (
            f'{customers} customers but low LTV. '
            f'Fix delivery before scaling acquisition.'
        )
        recommendation = (
            'CS Agent: why are customers not getting '
            'results or not referring? Fix before '
            'adding more acquisition volume.'
        )

    elif revenue > 2000:
        constraint = CONSTRAINT_PROFIT
        confidence = 0.65
        phase = 'better'
        diagnosis = (
            f'Revenue at ${revenue:,.0f}. '
            f'Evaluate unit economics — does CAC '
            f'recover within 30 days?'
        )
        recommendation = (
            'Finance Agent: calculate CAC, LTV, '
            'payback. Does the self-funding '
            'equation hold?'
        )

    else:
        constraint = CONSTRAINT_LEADS
        confidence = 0.7
        phase = 'more'
        diagnosis = (
            'No sales data yet. '
            'Focus entirely on outreach volume.'
        )
        recommendation = (
            f'Maximize outreach. '
            f'Target {dm_target}+ DMs/week.'
        )

    # Build active/idle agent lists
    all_agents = [
        'research_agent', 'outreach_agent',
        'content_agent', 'sales_agent',
        'customer_success_agent', 'finance_agent',
        'intelligence_agent', 'operations_agent',
    ]
    active = list(
        CONSTRAINT_AGENTS.get(constraint, [])
    )
    # Always keep ops agent active
    always = CONSTRAINT_AGENTS.get(
        '_always_active', []
    )
    for a in always:
        if a not in active:
            active.append(a)

    idle = [a for a in all_agents
            if a not in active]

    return {
        'constraint': constraint,
        'confidence': confidence,
        'diagnosis': diagnosis,
        'recommendation': recommendation,
        'phase': phase,
        'active_agents': active,
        'idle_agents': idle,
        'metrics': metrics,
        'benchmarks': benchmarks,
        'diagnosed_at': datetime.now(
            PDT
        ).isoformat(),
    }


def get_offer_stage(
    venture_id: str,
    ctx=None,
) -> dict:
    """
    Determine current offer stage.
    Stage I: Attraction (first sale)
    Stage II: Upsell/Downsell
    Stage III: Continuity
    Never advances without proof.
    """
    try:
        from runtime.context import (
            load_context_from_env,
        )
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT COUNT(*) as cnt,
                COALESCE(SUM(
                    (payload_json->>'amount')
                    ::numeric
                ), 0) as revenue
                FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'sale','payment_received'
                )
            ''', (str(ctx.org_id),))
            row = cur.fetchone()
            sales = row['cnt'] if row else 0
            revenue = float(
                row['revenue'] if row else 0
            )

        if sales == 0:
            return {
                'stage': 1,
                'label': 'Attraction',
                'proof_met': False,
                'objective': (
                    'Get first paying customer. '
                    'Prove the offer converts.'
                ),
                'advance_when': 'First sale closes.',
            }
        elif revenue < 5000:
            return {
                'stage': 1,
                'label': 'Attraction',
                'proof_met': False,
                'objective': (
                    'Get consistent conversions. '
                    'Validate the offer repeats.'
                ),
                'advance_when': (
                    'Same channel working 3 times '
                    'with same ICP.'
                ),
            }
        elif revenue < 50000:
            return {
                'stage': 2,
                'label': 'Upsell/Downsell',
                'proof_met': True,
                'objective': (
                    'Maximize 30-day customer value. '
                    'Deploy upsell sequence.'
                ),
                'advance_when': (
                    'Upsell converting >20%. '
                    'Revenue >$50K/mo.'
                ),
            }
        else:
            return {
                'stage': 3,
                'label': 'Continuity',
                'proof_met': True,
                'objective': (
                    'Build recurring revenue. '
                    'Deploy continuity offer.'
                ),
                'advance_when': (
                    'MRR >$10K. Retention >80%.'
                ),
            }
    except Exception as e:
        logger.warning(
            f'[CEOIntel] offer_stage: {e}'
        )
        return {
            'stage': 1,
            'label': 'Attraction',
            'proof_met': False,
            'objective': 'Get first sale.',
            'advance_when': 'First sale closes.',
        }


def get_agent_performance(
    ctx=None,
    days: int = 7,
) -> dict:
    """
    Score each agent's task completion this week.
    Below 50% triggers STAR diagnosis flag.
    """
    try:
        from runtime.context import (
            load_context_from_env,
        )
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()
        since = datetime.now(PDT) - timedelta(
            days=days
        )

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT assignee_id,
                COUNT(*) as total,
                SUM(CASE WHEN status =
                    'completed' THEN 1
                    ELSE 0 END) as completed
                FROM tasks
                WHERE org_id = %s
                AND created_at >= %s
                GROUP BY assignee_id
            ''', (str(ctx.org_id),
                  since.isoformat()))
            rows = cur.fetchall()

        performance = {}
        for row in rows:
            agent = row['assignee_id']
            total = row['total'] or 0
            done = row['completed'] or 0
            rate = round(
                done / max(total, 1) * 100, 1
            )
            flag = (
                '🟢' if rate >= 80
                else '🟡' if rate >= 50
                else '🔴'
            )
            needs_star = (
                rate < 50 and total >= 3
            )
            performance[agent] = {
                'assigned': total,
                'completed': done,
                'rate': rate,
                'flag': flag,
                'needs_star': needs_star,
            }

        return performance
    except Exception as e:
        logger.warning(
            f'[CEOIntel] perf: {e}'
        )
        return {}


def generate_ceo_brief(
    venture_id: str,
    venture_name: str,
    ctx=None,
) -> str:
    """
    Generate the CEO's daily intelligence brief.
    Constraint → Phase → Agents → Metrics → Performance.
    This is what the CEO agent reads before
    generating today's objective.
    """
    c = diagnose_constraint(venture_id, ctx)
    o = get_offer_stage(venture_id, ctx)
    p = get_agent_performance(ctx)
    m = c.get('metrics', {})
    b = c.get('benchmarks', {})
    now = datetime.now(PDT).strftime('%B %d %Y')

    def status(actual, target):
        if actual >= target:
            return '✅'
        elif actual >= target * 0.7:
            return '🟡'
        return '🔴'

    lines = [
        f'## {venture_name} — CEO Brief {now}',
        '',
        f'**CONSTRAINT: '
        f'{c["constraint"].upper()}** '
        f'| Phase: {c["phase"].upper()} '
        f'| Confidence: '
        f'{c["confidence"]*100:.0f}%',
        '',
        f'**Diagnosis:** {c["diagnosis"]}',
        f'**Action:** {c["recommendation"]}',
        '',
        f'**Active agents:** '
        f'{", ".join(c["active_agents"])}',
        f'**Idle:** '
        f'{", ".join(c["idle_agents"][:4])}',
        '',
        f'**OFFER STAGE {o["stage"]}: '
        f'{o["label"]}** '
        f'| Proof: '
        f'{"✅" if o["proof_met"] else "❌"}',
        f'Objective: {o["objective"]}',
        f'Advance when: '
        f'{o.get("advance_when", "TBD")}',
    ]

    if m:
        dm_t = b.get('dms_per_week', 30)
        rr_t = b.get('reply_rate_pct', 15)
        cr_t = b.get('call_rate_pct', 25)
        cl_t = b.get('close_rate_pct', 20)

        lines.extend([
            '',
            '**FUNNEL (7d):**',
            f'{status(m.get("dms_sent",0), dm_t)} '
            f'DMs: {m.get("dms_sent",0)} '
            f'(target {dm_t}+)',
            f'{status(m.get("reply_rate",0), rr_t)} '
            f'Reply rate: {m.get("reply_rate",0)}% '
            f'(target {rr_t}%+)',
            f'{status(m.get("call_rate",0), cr_t)} '
            f'Call rate: {m.get("call_rate",0)}% '
            f'(target {cr_t}%+)',
            f'{status(m.get("close_rate",0), cl_t)} '
            f'Close rate: {m.get("close_rate",0)}% '
            f'(target {cl_t}%+)',
            f'Calls booked: '
            f'{m.get("calls_booked", 0)}',
            f'Revenue this week: '
            f'${m.get("revenue", 0):,.0f}',
            f'Total customers: '
            f'{m.get("customers_total", 0)}',
            f'Total revenue: '
            f'${m.get("revenue_total", 0):,.0f}',
        ])

    if p:
        lines.extend(['', '**AGENT PERFORMANCE:**'])
        for agent, data in p.items():
            if data['assigned'] > 0:
                line = (
                    f'{data["flag"]} {agent}: '
                    f'{data["rate"]}% '
                    f'({data["completed"]}/'
                    f'{data["assigned"]})'
                )
                if data['needs_star']:
                    line += ' ← STAR check needed'
                lines.append(line)

    return '\n'.join(lines)
