"""
Notion Seed — populates initial rows in EOS Notion databases.
Run once after notion_setup.py has created all DBs.
Idempotent in effect (creates rows, does not check for duplicates —
safe to re-run on empty DBs, do not re-run on populated ones).
"""

import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

from adapters.notion.notion_sync import (

    get_db_id,
    HEADERS, _title, _select, _text, _number,
    _date, _checkbox, _create_page,
)


TODAY = datetime.now().strftime('%Y-%m-%d')

def _ventures() -> list:
    """(venture_id, name) tuples from the tenant registry (BIS) at runtime."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.business.business_instance import get_ventures
        return [(v.get('id', ''), v.get('name', v.get('id', '')))
                for v in get_ventures(load_context_from_env()) if v.get('id')]
    except Exception:
        return []


VENTURES = _ventures()


def _ai_name() -> str:
    try:
        from substrate.state.business.business_instance import get_ai_name
        return get_ai_name() or 'Assistant'
    except Exception:
        return 'Assistant'


AI_NAME = _ai_name()


# ── Portfolio Overview ────────────────────────────

def _portfolio_rows() -> list:
    """Portfolio rows from the tenant's ventures + BIS at runtime. Never hardcode
    a tenant's venture names / north-stars / models — that would seed one tenant's
    portfolio into every seat."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.business.business_instance import (
            BusinessInstanceManager, get_ventures, STAGE_NAMES,
        )
        ctx = load_context_from_env()
        bim = BusinessInstanceManager(ctx)
        rows = []
        for v in get_ventures(ctx):
            vid = v.get('id', '')
            if not vid:
                continue
            bis = None
            try:
                bis = bim.get_bis(vid)
            except Exception:
                bis = None
            rows.append({
                'name': (getattr(bis, 'name', '') if bis else '') or v.get('name', vid),
                'stage': (STAGE_NAMES.get(getattr(bis, 'current_stage', 1), '') if bis else '') or 'Validation',
                'model': (getattr(bis, 'business_model', '') if bis else '') or '',
                'north_star': (getattr(bis, 'north_star', '') if bis else '') or '',
                'binding': '',
                'proof': (getattr(bis, 'stage_proof', {}) if bis else {}) and '' or '',
                'focus': '',
                'health': 0.0,
            })
        return rows
    except Exception:
        return []


def seed_portfolio() -> None:
    db_id = os.getenv('NOTION_PORTFOLIO_OVERVIEW_DB', '')
    if not db_id:
        print('  ⚠️  NOTION_PORTFOLIO_OVERVIEW_DB not set')
        return
    rows = _portfolio_rows()
    print('\n── Portfolio Overview ──')
    for r in rows:
        props = {
            'Company': _title(r['name']),
            'Stage': _select(r['stage']),
            'Business Model': _select(r['model']),
            'North Star': _text(r['north_star']),
            'Binding Constraint': _text(r['binding']),
            'Proof to Advance': _text(r['proof']),
            'Current Focus': _text(r['focus']),
            'Status': _select('Active'),
            'Health Score': _number(r['health']),
            'Revenue MRR': _number(0),
            'Active Agents': _number(0),
            'Tasks In Progress': _number(0),
            'Last Updated': _date(TODAY),
        }
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {r["name"]}')


# ── Roles ─────────────────────────────────────────

ROLES = [
    {
        'name': 'Founder',
        'dept': 'Leadership',
        'mode': 'Human Only',
        'authority': 'Strategic',
        'status': 'Active',
        'agent': 'Founder',
        'agent_status': '🟢 Complete',
        'kpi': 'Revenue MRR',
        'kpi_value': '$0 → $10K',
        'responsibilities': (
            'Vision, strategy, capital allocation, final decisions, brand.'
        ),
        'soul_doc': '',
    },
    {
        'name': f'{AI_NAME} — Executive Assistant',
        'dept': 'Leadership',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': AI_NAME,
        'agent_status': '⚪ Idle',
        'kpi': 'Tasks completed',
        'kpi_value': '0',
        'responsibilities': (
            'Calendar, email, task routing, meeting prep, '
            'cross-venture coordination, daily brief.'
        ),
        'soul_doc': f'{_ROOT}/agents/executive_assistant.md',
    },
    {
        'name': 'CEO Agent',
        'dept': 'Leadership',
        'mode': 'AI Only',
        'authority': 'Strategic',
        'status': 'AI-Staffed',
        'agent': 'CEO Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'Revenue growth',
        'kpi_value': '0',
        'responsibilities': (
            'Strategic oversight, delegation to dept agents, '
            'goal setting, org health monitoring.'
        ),
        'soul_doc': f'{_ROOT}/agents/ceo_agent.md',
    },
    {
        'name': 'Sales Agent',
        'dept': 'Sales',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': 'Sales Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'Calls booked / week',
        'kpi_value': '0',
        'responsibilities': (
            'Lead qualification, follow-up sequences, '
            'call booking, pipeline management.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Outreach Agent',
        'dept': 'Sales',
        'mode': 'AI Only',
        'authority': 'Execution',
        'status': 'AI-Staffed',
        'agent': 'Outreach Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'DMs sent / response rate',
        'kpi_value': '0',
        'responsibilities': (
            'Instagram DM outreach, opener personalization, '
            'initial lead engagement.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Research / Intelligence Agent',
        'dept': 'Research',
        'mode': 'AI Only',
        'authority': 'Execution',
        'status': 'AI-Staffed',
        'agent': 'Research Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'ICP signals processed',
        'kpi_value': '0',
        'responsibilities': (
            'ICP analysis, market signals, competitive intelligence, '
            'knowledge base maintenance.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Content Agent',
        'dept': 'Marketing',
        'mode': 'AI Only',
        'authority': 'Execution',
        'status': 'AI-Staffed',
        'agent': 'Content Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'Content pieces published',
        'kpi_value': '0',
        'responsibilities': (
            'Content calendar management, caption drafting, '
            'campaign execution.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Operations Agent',
        'dept': 'Operations',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': 'Operations Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'SOP coverage',
        'kpi_value': '0%',
        'responsibilities': (
            'Process documentation, SOP execution, tool management, '
            'system health monitoring.'
        ),
        'soul_doc': '',
    },
]


def seed_roles(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'roles')
    if not db_id:
        print(f'  ⚠️  No Roles DB for {venture_id}')
        return
    print(f'\n── Roles: {venture_name} ──')
    for r in ROLES:
        props: dict = {
            'Name': _title(r['name']),
            'Department': _select(r['dept']),
            'Mode': _select(r['mode']),
            'Authority Level': _select(r['authority']),
            'Status': _select(r['status']),
            'Agent Assigned': _select(r['agent']),
            'Agent Status': _select(r['agent_status']),
            'Primary KPI': _text(r['kpi']),
            'KPI Value': _text(r['kpi_value']),
            'Responsibilities': _text(r['responsibilities']),
            'Last Active': _date(TODAY),
        }
        if r['soul_doc']:
            props['Soul Doc Path'] = _text(r['soul_doc'])
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {r["name"]}')


# ── Tools ─────────────────────────────────────────

TOOLS = [
    {
        'name': 'Telegram Bot',
        'dept': 'Operations',
        'role': 'Founder mobile control interface',
        'agent': AI_NAME,
        'category': 'Native EOS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Primary founder → EOS command interface',
        'access': 'BOT_TOKEN in .env. services/discord_bot.py',
        'cost': 0,
    },
    {
        'name': 'Discord Bot',
        'dept': 'Operations',
        'role': 'Community management',
        'agent': 'Operations Agent',
        'category': 'Native EOS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Community engagement and moderation',
        'access': 'DISCORD_BOT_TOKEN in .env. 13_Scripts/discord_bot.py',
        'cost': 0,
    },
    {
        'name': 'Instagram (Playwright)',
        'dept': 'Sales',
        'role': 'DM outreach and inbox monitoring',
        'agent': 'Outreach Agent',
        'category': 'Native EOS',
        'integration': 'Browser Agent',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'DM monitor and outreach automation via Playwright',
        'access': 'IG_USERNAME/IG_PASSWORD in .env. 13_Scripts/dm_monitor.py',
        'cost': 0,
    },
    {
        'name': 'Calendly',
        'dept': 'Sales',
        'role': 'Sales call booking',
        'agent': 'Sales Agent',
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Booking page + webhook for call scheduling',
        'access': 'CALENDLY_API_KEY in .env. Flask on os-webhook.',
        'cost': 16,
    },
    {
        'name': 'Apify',
        'dept': 'Research',
        'role': 'Instagram scraping and data collection',
        'agent': 'Research Agent',
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Comment and profile scraping for lead generation',
        'access': 'APIFY_API_TOKEN in .env',
        'cost': 49,
    },
    {
        'name': 'Notion',
        'dept': 'Operations',
        'role': 'EOS UI layer — business operating system',
        'agent': AI_NAME,
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Primary UI for EOS primitives. Synced from Neon.',
        'access': 'NOTION_API_KEY in .env',
        'cost': 16,
    },
    {
        'name': 'Neon (PostgreSQL)',
        'dept': 'Engineering',
        'role': 'Primary EOS database',
        'agent': 'None',
        'category': 'Native EOS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': False,
        'desc': 'All EOS data: orgs, ventures, agents, memory, primitives',
        'access': 'DATABASE_URL in .env',
        'cost': 0,
    },
    {
        'name': 'Claude (Anthropic)',
        'dept': 'Engineering',
        'role': 'Primary LLM for all EOS agents',
        'agent': 'None',
        'category': 'API Integration',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': False,
        'desc': 'Haiku for scoring/classification, Sonnet for generation',
        'access': 'ANTHROPIC_API_KEY in .env',
        'cost': 0,
    },
    {
        'name': 'Google Workspace (GWS)',
        'dept': 'Operations',
        'role': 'Email and calendar integration',
        'agent': AI_NAME,
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Gmail + Google Calendar. OAuth active.',
        'access': 'GWS service account credentials in .env',
        'cost': 6,
    },
]


def seed_tools(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'tools')
    if not db_id:
        print(f'  ⚠️  No Tools DB for {venture_id}')
        return
    print(f'\n── Tools: {venture_name} ──')
    for t in TOOLS:
        props: dict = {
            'Name': _title(t['name']),
            'Department': _select(t['dept']),
            'Primary Role': _text(t['role']),
            'Agent': _select(t['agent']),
            'Category': _select(t['category']),
            'Integration Level': _select(t['integration']),
            'Status': _select(t['status']),
            'AI Operable': _checkbox(t['ai_operable']),
            'Description': _text(t['desc']),
            'Access Method': _text(t['access']),
            'Cost Per Month': _number(t['cost']),
        }
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {t["name"]}')


# ── Goals ─────────────────────────────────────────

def _goals_for(venture_id: str) -> list[dict]:
    """Seed the venture's North Star goal from BIS at runtime. A multi-tenant
    seeder never ships one tenant's OKRs — it seeds the tenant's own north-star
    (from BIS) as the starting goal; the operator authors the rest."""
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.business.business_instance import BusinessInstanceManager
        bis = BusinessInstanceManager(load_context_from_env()).get_bis(venture_id)
        ns = (getattr(bis, 'north_star', '') if bis else '') or ''
        if not ns:
            return []
        return [{
            'name': ns,
            'type': 'North Star',
            'status': 'Not Started',
            'dept': 'Leadership',
            'target': ns,
            'current': '',
            'due': '',
            'progress': 0.0,
            'notes': 'Primary north star. Every decision traces here.',
        }]
    except Exception:
        return []


def seed_goals(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'goals')
    if not db_id:
        print(f'  ⚠️  No Goals DB for {venture_id}')
        return
    goals = _goals_for(venture_id)
    print(f'\n── Goals: {venture_name} ──')
    for g in goals:
        props: dict = {
            'Name': _title(g['name']),
            'Type': _select(g['type']),
            'Status': _select(g['status']),
            'Department': _select(g['dept']),
            'Target': _text(g['target']),
            'Current': _text(g['current']),
            'Due Date': _date(g['due']),
            'Progress': _number(g['progress']),
            'Notes': _text(g['notes']),
        }
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {g["name"][:60]}')


# ── main ──────────────────────────────────────────

def main() -> None:
    print('EOS Notion Seed')
    print('================')

    seed_portfolio()

    for venture_id, venture_name in VENTURES:
        seed_roles(venture_id, venture_name)
        seed_tools(venture_id, venture_name)
        seed_goals(venture_id, venture_name)

    print('\n✅ Seed complete')


if __name__ == '__main__':
    main()
