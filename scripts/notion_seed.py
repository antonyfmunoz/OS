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

VENTURES = [
    ('personal_brand', 'Personal Brand'),
    ('lyfe_institute', 'Lyfe Institute'),
    ('empyrean_creative', 'Empyrean Creative'),
]


# ── Portfolio Overview ────────────────────────────

def seed_portfolio() -> None:
    db_id = os.getenv('NOTION_PORTFOLIO_OVERVIEW_DB', '')
    if not db_id:
        print('  ⚠️  NOTION_PORTFOLIO_OVERVIEW_DB not set')
        return
    rows = [
        {
            'name': 'Lyfe Institute',
            'stage': 'Pre-revenue',
            'model': 'B2C Coaching',
            'north_star': '$10K/month net from Initiate Arena',
            'binding': 'Sales — no paying customers yet',
            'proof': '1 customer → $1K MRR → $5K MRR → $10K MRR',
            'focus': 'Initiate Arena outreach and sales calls',
            'health': 0.3,
        },
        {
            'name': 'Personal Brand',
            'stage': 'Pre-revenue',
            'model': 'Content',
            'north_star': 'Primary marketing vehicle for all offers',
            'binding': 'Content volume and consistency',
            'proof': '10K followers → 50K → 100K',
            'focus': 'Content production and distribution',
            'health': 0.25,
        },
        {
            'name': 'Empyrean Creative',
            'stage': 'Pre-revenue',
            'model': 'Agency',
            'north_star': 'AI infrastructure proven internally → productize',
            'binding': 'EOS must work internally before selling externally',
            'proof': 'All EOS services stable + Notion synced',
            'focus': 'Building EOS and AI infrastructure',
            'health': 0.5,
        },
    ]
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
        'name': 'DEX — Executive Assistant',
        'dept': 'Leadership',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': 'DEX',
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
        'agent': 'DEX',
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
        'agent': 'DEX',
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
        'agent': 'DEX',
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

GOALS_BY_VENTURE: dict[str, list[dict]] = {
    'lyfe_institute': [
        {
            'name': '$10K/month net profit from Initiate Arena',
            'type': 'North Star',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '$10,000 MRR net',
            'current': '$0',
            'due': '2026-06-30',
            'progress': 0.0,
            'notes': 'Primary north star. Every decision traces here.',
        },
        {
            'name': 'First paying customer — Initiate Arena',
            'type': 'Key Result',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '1 customer at $750',
            'current': '0',
            'due': '2026-04-30',
            'progress': 0.0,
            'notes': 'Proof of concept. Must happen before scaling.',
        },
        {
            'name': 'Run 20 qualified sales calls',
            'type': 'Key Result',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '20 calls',
            'current': '0',
            'due': '2026-04-15',
            'progress': 0.0,
            'notes': 'Volume needed to find product-market fit.',
        },
    ],
    'personal_brand': [
        {
            'name': 'Establish consistent content output',
            'type': 'Quarterly Goal',
            'status': 'Behind',
            'dept': 'Marketing',
            'target': '5 posts/week across platforms',
            'current': '0',
            'due': '2026-06-30',
            'progress': 0.0,
            'notes': 'Content IS the advertising.',
        },
    ],
    'empyrean_creative': [
        {
            'name': 'EOS fully operational internally',
            'type': 'Quarterly Goal',
            'status': 'At risk',
            'dept': 'Operations',
            'target': 'All 5 EOS services stable + Notion synced',
            'current': '4/5 services up, Notion pending',
            'due': '2026-04-30',
            'progress': 0.6,
            'notes': 'Must prove internally before productizing.',
        },
    ],
}


def seed_goals(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'goals')
    if not db_id:
        print(f'  ⚠️  No Goals DB for {venture_id}')
        return
    goals = GOALS_BY_VENTURE.get(venture_id, [])
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
