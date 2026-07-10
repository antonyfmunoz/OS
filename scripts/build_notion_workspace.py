"""
Build EOS Notion Workspace
Mirrors the end game UI structure exactly.
Every section maps to a route in the SaaS UI.

All business copy (portfolio tree, per-company hub content, org chart) lives
in data/umh/instance.json under `notion_seed`. This script is a pure
template: it reads that seed at runtime. No tenant literals are embedded.
Degrades gracefully: if no notion_seed is configured, it seeds nothing.
"""
import os
import sys
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

from notion_client import Client

from substrate.state.business.business_instance import (
    get_notion_seed, get_ai_name, get_founder_name,
)

client = Client(auth=os.getenv('NOTION_API_KEY'))


def _ai_name() -> str:
    try:
        return get_ai_name() or 'Assistant'
    except Exception:
        return 'Assistant'


def _founder_name() -> str:
    try:
        from substrate.state.context.context import load_context_from_env
        return get_founder_name(load_context_from_env(), default='the founder')
    except Exception:
        return 'the founder'


AI_NAME = _ai_name()
FOUNDER_NAME = _founder_name()

# Per-tenant workspace seed content. Empty dict for a fresh tenant.
SEED = get_notion_seed()

# Token map for template placeholders stored in the seed.
_FMT = {'founder_name': FOUNDER_NAME, 'ai_name': AI_NAME}


def _fmt(value: str) -> str:
    """Interpolate {founder_name}/{ai_name} tokens in a seed string.

    Unknown tokens are left intact so an unrelated brace never crashes."""
    if not isinstance(value, str):
        return value
    try:
        return value.format(**_FMT)
    except (KeyError, IndexError, ValueError):
        return value

# ── HELPERS ────────────────────────────────────────────────────────────────

def create_page(parent_id, title, icon='', content_blocks=None):
    try:
        kwargs = {
            'parent': {'page_id': parent_id},
            'properties': {
                'title': [{'type': 'text', 'text': {'content': title}}]
            },
        }
        if icon:
            kwargs['icon'] = {'type': 'emoji', 'emoji': icon}
        if content_blocks:
            kwargs['children'] = content_blocks
        result = client.pages.create(**kwargs)
        print(f'  ✅ {title}: {result["id"]}')
        return result['id']
    except Exception as e:
        print(f'  ❌ {title}: {e}')
        return None


def create_database(parent_id, title, icon='', properties=None):
    try:
        kwargs = {
            'parent': {'type': 'page_id', 'page_id': parent_id},
            'title': [{'type': 'text', 'text': {'content': title}}],
            'properties': properties or {'Name': {'title': {}}},
        }
        if icon:
            kwargs['icon'] = {'type': 'emoji', 'emoji': icon}
        result = client.databases.create(**kwargs)
        print(f'  ✅ DB: {title}: {result["id"]}')
        return result['id']
    except Exception as e:
        print(f'  ❌ DB: {title}: {e}')
        return None


def text_block(content):
    return {
        'object': 'block',
        'type': 'paragraph',
        'paragraph': {
            'rich_text': [{'type': 'text', 'text': {'content': content[:2000]}}]
        }
    }


def heading_block(content, level=2):
    h = f'heading_{level}'
    return {
        'object': 'block',
        'type': h,
        h: {'rich_text': [{'type': 'text', 'text': {'content': content}}]}
    }


def divider_block():
    return {'object': 'block', 'type': 'divider', 'divider': {}}


def callout_block(content, emoji='💡'):
    return {
        'object': 'block',
        'type': 'callout',
        'callout': {
            'rich_text': [{'type': 'text', 'text': {'content': content}}],
            'icon': {'type': 'emoji', 'emoji': emoji}
        }
    }


# ── FIND EOS ROOT PAGE ──────────────────────────────────────────────────────

print('Finding EOS root page...')
results = client.search(
    query='EOS',
    filter={'value': 'page', 'property': 'object'}
)

eos_pages = [
    r for r in results.get('results', [])
    if any(
        t.get('plain_text', '') == 'EOS'
        for t in r.get('properties', {}).get('title', {}).get('title', [])
    )
]

if not eos_pages:
    print('EOS page not found. Share it with the integration first.')
    sys.exit(1)

if not SEED:
    print('No notion_seed configured — nothing to seed.')
    sys.exit(0)

ROOT_ID = eos_pages[0]['id']
print(f'EOS root: {ROOT_ID}')
print()

page_ids = {'root': ROOT_ID}

# Portfolio KPI copy + tree text pulled from the tenant seed.
_PORTFOLIO = (SEED.get('portfolio') or [{}])[0]
_EMPIRE_TREE = _fmt(SEED.get('empire_tree_text', ''))
_ENTITY_TREE = _fmt(SEED.get('entity_structure_text', ''))
_ORG_CHART = _fmt(SEED.get('org_chart_text', ''))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 1: PORTFOLIO VIEW
# Maps to: /home — founder command center
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print('Building Portfolio View (/home)...')
portfolio_id = create_page(
    ROOT_ID,
    f'📊 Portfolio — {FOUNDER_NAME}',
    icon='📊',
    content_blocks=[
        heading_block(f'{FOUNDER_NAME}', 1),
        callout_block(
            'Portfolio intelligence. Capital allocation. Cross-company patterns.',
            '👁️'
        ),
        divider_block(),
        heading_block('Empire Structure', 2),
        text_block(_EMPIRE_TREE),
        divider_block(),
        heading_block(_PORTFOLIO.get('heading', 'Portfolio KPIs'), 2),
        text_block(_fmt(_PORTFOLIO.get('kpis_text', ''))),
        divider_block(),
        heading_block('Capital Allocation', 2),
        text_block(
            'EOS tracks resource allocation across all companies here.\n'
            'Updated by Portfolio Advisor agent.'
        ),
        divider_block(),
        heading_block('Cross-Company Insights', 2),
        text_block(
            'Portfolio Advisor intelligence surfaces here.\n'
            'Patterns, opportunities, and risks across all entities.'
        ),
    ]
)
page_ids['portfolio'] = portfolio_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 2: MORNING BRIEF
# Maps to: /home → Next Best Action panel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print('Building Morning Brief...')
brief_id = create_page(
    ROOT_ID,
    '📋 Morning Brief',
    icon='📋',
    content_blocks=[
        heading_block('Daily Intelligence', 1),
        callout_block(
            f'{AI_NAME} generates this daily at 6am.\n'
            'One thing that matters. First action. Reality check.',
            '🧠'
        ),
        divider_block(),
        heading_block('Latest Brief', 2),
        text_block(f'Awaiting first brief.\n{AI_NAME} will write here automatically.'),
        divider_block(),
        heading_block('Brief Archive', 2),
        text_block('Previous briefs stored below by date.'),
    ]
)
page_ids['morning_brief'] = brief_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 3: COMPANIES
# Maps to: /company
# One hub page per company, each with sub-pages mirroring UI routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Per-company hub content pulled from the tenant seed. Each string field is
# token-interpolated ({founder_name}/{ai_name}) so no tenant literal is inline.
companies = []
for _entry in (SEED.get('entity_structure') or []):
    companies.append({k: (_fmt(v) if isinstance(v, str) else v)
                      for k, v in _entry.items()})

for company in companies:
    print(f'\nBuilding {company["name"]}...')

    note_line = f'\nNote: {company["note"]}' if company.get('note') else ''

    # Company hub page — /company
    company_id = create_page(
        ROOT_ID,
        f'{company["icon"]} {company["name"]}',
        icon=company['icon'],
        content_blocks=[
            heading_block(company['name'], 1),
            callout_block(
                f'Type: {company["type"]}\n'
                f'Stage: {company["stage"]}\n'
                f'Offer: {company["offer"]}\n'
                f'ICP: {company["icp"]}\n'
                f'Channel: {company["channel"]}\n'
                f'Goal: {company["goal"]}'
                + note_line,
                company['icon']
            ),
            divider_block(),
            heading_block('Operating Context', 2),
            text_block(
                f'North Star: {company["north_star"]}\n'
                'Current Constraint: First sale\n'
                'Active Primitives: conversation_first, outreach_before_content'
            ),
        ]
    )
    page_ids[company['venture_id']] = company_id

    if not company_id:
        continue

    # /company → Company Profile
    create_page(
        company_id, '🏷️ Company Profile', icon='🏷️',
        content_blocks=[
            heading_block('Company Profile', 1),
            text_block(
                f'Name: {company["name"]}\n'
                f'Type: {company["type"]}\n'
                f'Stage: {company["stage"]}\n'
                f'Offer: {company["offer"]}\n'
                f'ICP: {company["icp"]}\n'
                f'Channel: {company["channel"]}\n'
                f'Goal: {company["goal"]}\n'
                f'North Star: {company["north_star"]}'
                + note_line
            ),
            divider_block(),
            heading_block('Positioning', 2),
            text_block(
                'ICP Doc: [fill in]\n'
                'Offer Sheet: [fill in]\n'
                'Messaging Doc: [fill in]\n'
                'Competitor Analysis: [fill in]'
            ),
        ]
    )

    # /roles → Roles & Structure
    create_page(
        company_id, '👥 Roles & Structure', icon='👥',
        content_blocks=[
            heading_block('Roles & Structure', 1),
            callout_block(
                'Org structure for this company.\n'
                'Roles define who does what.\n'
                f'{AI_NAME} assigns AI or human to each.',
                '👥'
            ),
            divider_block(),
            heading_block('Current Roles', 2),
            text_block(
                f'Founder — {FOUNDER_NAME} (Human)\n'
                f'Executive Assistant — {AI_NAME} (AI)\n'
                f'CEO — {AI_NAME} (AI)\n'
                'Developer — Claude Code (AI)'
            ),
        ]
    )

    # /workflows → Workflows DB
    create_database(
        company_id, '⚙️ Workflows', icon='⚙️',
        properties={
            'Name': {'title': {}},
            'Status': {'select': {'options': [
                {'name': 'Draft', 'color': 'gray'},
                {'name': 'Active', 'color': 'green'},
                {'name': 'Paused', 'color': 'yellow'},
                {'name': 'Completed', 'color': 'blue'},
            ]}},
            'Department': {'select': {'options': [
                {'name': 'Sales', 'color': 'red'},
                {'name': 'Marketing', 'color': 'pink'},
                {'name': 'Operations', 'color': 'orange'},
                {'name': 'Product', 'color': 'purple'},
            ]}},
            'AI Assisted': {'checkbox': {}},
            'Steps': {'number': {}},
            'Owner': {'rich_text': {}},
            'Last Run': {'date': {}},
        }
    )

    # /tasks → Tasks DB
    create_database(
        company_id, '✅ Tasks', icon='✅',
        properties={
            'Name': {'title': {}},
            'Status': {'select': {'options': [
                {'name': 'Backlog', 'color': 'gray'},
                {'name': 'In Progress', 'color': 'blue'},
                {'name': 'Waiting', 'color': 'yellow'},
                {'name': 'Done', 'color': 'green'},
                {'name': 'Blocked', 'color': 'red'},
            ]}},
            'Priority': {'select': {'options': [
                {'name': 'Critical', 'color': 'red'},
                {'name': 'High', 'color': 'orange'},
                {'name': 'Medium', 'color': 'yellow'},
                {'name': 'Low', 'color': 'gray'},
            ]}},
            'Due Date': {'date': {}},
            'Linked Workflow': {'rich_text': {}},
            'Linked Role': {'rich_text': {}},
            'AI Generated': {'checkbox': {}},
        }
    )

    # /workflows → Pipeline (Sales)
    create_database(
        company_id, '🎯 Pipeline', icon='🎯',
        properties={
            'Name': {'title': {}},
            'Stage': {'select': {'options': [
                {'name': 'New Lead', 'color': 'blue'},
                {'name': 'Contacted', 'color': 'yellow'},
                {'name': 'Conversation Active', 'color': 'orange'},
                {'name': 'Call Booked', 'color': 'purple'},
                {'name': 'Proposal Sent', 'color': 'pink'},
                {'name': 'Closed Won', 'color': 'green'},
                {'name': 'Closed Lost', 'color': 'red'},
            ]}},
            'Channel': {'select': {'options': [
                {'name': 'Instagram DM', 'color': 'pink'},
                {'name': 'LinkedIn', 'color': 'blue'},
                {'name': 'Referral', 'color': 'green'},
                {'name': 'Cold Email', 'color': 'yellow'},
                {'name': 'Other', 'color': 'gray'},
            ]}},
            'Value': {'number': {'format': 'dollar'}},
            'Last Contact': {'date': {}},
            'Notes': {'rich_text': {}},
            'AI Qualified': {'checkbox': {}},
        }
    )

    # KPI Dashboard
    create_page(
        company_id, '📊 KPI Dashboard', icon='📊',
        content_blocks=[
            heading_block('KPI Dashboard', 1),
            callout_block(
                'Stage 1 KPIs — what gets measured gets managed.\n'
                f'{AI_NAME} updates these from conversations.',
                '📊'
            ),
            divider_block(),
            heading_block('Stage 1 Metrics', 2),
            text_block(
                'DMs Sent Today: [log daily]\n'
                'Response Rate: [calculate weekly]\n'
                'Calls Booked: [log per booking]\n'
                'Conversion Rate: [calculate]\n'
                'Revenue: $0 → First sale'
            ),
            divider_block(),
            heading_block('Weekly Tracking', 2),
            text_block(
                f'Tell {AI_NAME} in Discord:\n'
                '"Log 20 DMs sent today"\n'
                '"Booked a call with [name]"\n'
                '"Closed [name] for $750"\n\n'
                f'{AI_NAME} tracks and updates here.'
            ),
        ]
    )

    # /ai → Stage Guidance
    create_page(
        company_id, '🧭 Stage Guidance', icon='🧭',
        content_blocks=[
            heading_block('Stage Guidance', 1),
            callout_block(
                'What applies right now.\nWhat is locked and why.\nWhat unlocks next.',
                '🧭'
            ),
            divider_block(),
            heading_block('Active Primitives ✅', 2),
            text_block(
                '✅ conversation_first\n'
                '✅ outreach_before_content\n'
                '✅ unit_economics\n'
                '✅ pricing_psychology\n'
                '✅ cash_flow_management'
            ),
            divider_block(),
            heading_block('Locked Primitives ❌', 2),
            text_block(
                '❌ offer_optimization\n'
                '   Reason: No demand proof yet\n\n'
                '❌ hire_salesperson\n'
                '   Reason: Sale not proven yet\n\n'
                '❌ paid_advertising\n'
                '   Reason: Offer unproven organically\n\n'
                '❌ content_strategy\n'
                '   Reason: Outreach closes faster\n\n'
                '❌ hire_top_down\n'
                '   Reason: No capital or systems yet'
            ),
            divider_block(),
            heading_block('To Advance to Stage 2', 2),
            text_block(
                'First paying client acquired from consistent channel.\n\n'
                f'When confirmed: tell {AI_NAME} in Discord\n'
                '"I closed my first client"\n'
                f'{AI_NAME} unlocks Stage 2 primitives.'
            ),
        ]
    )

    # /docs → Docs & SOPs
    create_page(
        company_id, '📄 Docs & SOPs', icon='📄',
        content_blocks=[
            heading_block('Docs & SOPs', 1),
            callout_block(
                'Operating documents, SOPs, strategy notes, role notes.\n'
                f'{AI_NAME} generates and maintains these.',
                '📄'
            ),
            divider_block(),
            heading_block('Categories', 2),
            text_block(
                'SOP Notes\n'
                'Strategy Notes\n'
                'Role Notes\n'
                'Company Notes\n'
                'Workflow Notes\n'
                'General'
            ),
        ]
    )

    # War Room
    create_page(
        company_id, '🏆 War Room', icon='🏆',
        content_blocks=[
            heading_block('War Room', 1),
            callout_block(
                'Weekly strategy session.\n'
                f'Every Monday. {AI_NAME} facilitates.\n'
                '30 minutes. One outcome: clarity.',
                '🏆'
            ),
            divider_block(),
            heading_block('Agenda Template', 2),
            text_block(
                '1. REALITY CHECK (5 min)\n'
                '   Numbers only. No narrative.\n\n'
                '2. CONSTRAINT (10 min)\n'
                '   One thing blocking progress.\n\n'
                '3. THIS WEEK\'S ONE THING (10 min)\n'
                '   One move that matters most.\n\n'
                '4. COMMIT (5 min)\n'
                '   What gets done by when.'
            ),
            divider_block(),
            heading_block('War Room Archive', 2),
            text_block(f'{AI_NAME} creates a new entry here each Monday morning.'),
        ]
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 4: EMPIRE STRUCTURE / ORG CHART
# Maps to: /company → org chart view
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print('\nBuilding Empire Structure...')
empire_id = create_page(
    ROOT_ID,
    '🏛️ Empire Structure',
    icon='🏛️',
    content_blocks=[
        heading_block(f'{FOUNDER_NAME}', 1),
        callout_block(
            'The holding company.\n'
            'All subsidiaries report here.\n'
            'Portfolio Advisor serves this level.',
            '🏛️'
        ),
        divider_block(),
        heading_block('Entity Structure', 2),
        text_block(_ENTITY_TREE),
        divider_block(),
        heading_block('Agent Hierarchy', 2),
        text_block(_ORG_CHART),
        divider_block(),
        heading_block('Holding Company Notes', 2),
        text_block(
            'Capital allocation decisions made at portfolio level.\n'
            'Cross-company synergies tracked here.\n'
            'Portfolio Advisor reports weekly.'
        ),
    ]
)
page_ids['empire'] = empire_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 5: AI COPILOT
# Maps to: /ai
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print('\nBuilding AI Copilot (/ai)...')
ai_id = create_page(
    ROOT_ID,
    f'🤖 AI Copilot — {AI_NAME}',
    icon='🤖',
    content_blocks=[
        heading_block(f'AI Copilot — {AI_NAME}', 1),
        callout_block(
            f'Interact with {AI_NAME} through Discord.\n'
            'This page stores AI insights, memory summaries, and decisions.',
            '👁️'
        ),
        divider_block(),
        heading_block(f'How to Talk to {AI_NAME}', 2),
        text_block(
            'Open Discord → #general\n'
            'Type anything naturally.\n'
            f'{AI_NAME} responds in text and voice.\n\n'
            f'{AI_NAME} is always in your voice channel when you join.\n'
            f'Type → {AI_NAME} speaks.'
        ),
        divider_block(),
        heading_block('Memory Summary', 2),
        text_block(
            f'{AI_NAME} memory updated here by agents.\n'
            f'What {AI_NAME} knows. What it has learned.\n'
            'Decisions made. Patterns noticed.'
        ),
        divider_block(),
        heading_block('Pinned Insights', 2),
        text_block(
            f'Important insights pinned here by {AI_NAME} automatically.\n'
            'Awaiting first insight.'
        ),
        divider_block(),
        heading_block('Quick Prompts', 2),
        text_block(
            f'Ask {AI_NAME} in Discord:\n'
            '"What should I focus on today?"\n'
            '"Summarize my pipeline"\n'
            '"What is my next best action?"\n'
            '"Run war room for [company]"\n'
            '"Give me a reality check"\n'
            '"What primitive applies right now?"'
        ),
    ]
)
page_ids['ai_copilot'] = ai_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 6: AGENT ACTIVITY LOG
# Maps to: /home → AI insight panel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print('\nBuilding Agent Activity...')
activity_id = create_page(
    ROOT_ID,
    '⚡ Agent Activity',
    icon='⚡',
    content_blocks=[
        heading_block('Agent Activity', 1),
        callout_block(
            'Every action EOS takes is logged here.\n'
            'Morning briefs. Proactive signals.\n'
            'Pipeline updates. DM analyses.',
            '⚡'
        ),
        divider_block(),
        heading_block('Recent Activity', 2),
        text_block(
            'EOS online.\n'
            'Workspace initialized.\n'
            'Awaiting first agent action.'
        ),
    ]
)
page_ids['activity'] = activity_id


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SAVE ALL PAGE IDs TO .env
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

env_path = f'{_ROOT}/.env'

# Read existing to avoid duplicate keys
with open(env_path, 'r') as f:
    existing = f.read()

env_lines = ['\n# ── Notion Page IDs ──────────────────────']
for key, pid in page_ids.items():
    if pid:
        env_key = f'NOTION_{key.upper()}_ID'
        if env_key not in existing:
            env_lines.append(f'{env_key}={pid}')

with open(env_path, 'a') as f:
    f.write('\n'.join(env_lines) + '\n')

print()
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print('EOS Notion Workspace Complete')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
for key, pid in page_ids.items():
    status = '✅' if pid else '❌'
    print(f'  {status} {key}: {pid}')
print()
print('Open Notion to see your workspace.')
print('Structure mirrors end game UI.')
