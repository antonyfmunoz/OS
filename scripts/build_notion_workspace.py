"""
Build EOS Notion Workspace
Mirrors the end game UI structure exactly.
Every section maps to a route in the SaaS UI.
"""
import sys
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))

from notion_client import Client
import os

client = Client(auth=os.getenv('NOTION_API_KEY'))

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

ROOT_ID = eos_pages[0]['id']
print(f'EOS root: {ROOT_ID}')
print()

page_ids = {'root': ROOT_ID}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECTION 1: PORTFOLIO VIEW
# Maps to: /home — founder command center
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print('Building Portfolio View (/home)...')
portfolio_id = create_page(
    ROOT_ID,
    '📊 Portfolio — Munoz Holdings',
    icon='📊',
    content_blocks=[
        heading_block('Munoz Holdings', 1),
        callout_block(
            'Portfolio intelligence. Capital allocation. Cross-company patterns.',
            '👁️'
        ),
        divider_block(),
        heading_block('Empire Structure', 2),
        text_block(
            'Munoz Holdings (Holding Company)\n'
            '├── Empyrean Creative  [B2B AI Services]\n'
            '│   └── Lyfe Institute  [Coaching — incubated under Empyrean]\n'
            '│       Offer: Initiate Arena $750\n'
            '│       Channel: Instagram DMs\n'
            '└── Personal Brand — Antony  [Content Business]\n'
            '    Revenue: Sponsors, Affiliates, Ads, Donations\n'
            '    Goal: grow audience, promote Empyrean + Lyfe'
        ),
        divider_block(),
        heading_block('Portfolio KPIs', 2),
        text_block(
            'Total Revenue: $0\n'
            'Active Companies: 3\n'
            'Stage: All Stage 1 — Validation\n'
            'North Star: $10K/month net (Initiate Arena) → $100K/month'
        ),
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
            'DEX generates this daily at 6am.\n'
            'One thing that matters. First action. Reality check.',
            '🧠'
        ),
        divider_block(),
        heading_block('Latest Brief', 2),
        text_block('Awaiting first brief.\nDEX will write here automatically.'),
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

companies = [
    {
        'name': 'Empyrean Creative',
        'icon': '⚡',
        'type': 'B2B Agency',
        'stage': '1 — Validation',
        'offer': 'AI services for businesses',
        'icp': 'Business owners who need AI',
        'channel': 'TBD — outreach',
        'goal': 'Land first retainer client',
        'north_star': '$100K/month',
        'venture_id': 'empyrean_creative',
        'note': None,
    },
    {
        'name': 'Lyfe Institute',
        'icon': '🏢',
        'type': 'Coaching Program',
        'stage': '1 — Validation',
        'offer': 'Initiate Arena $750',
        'icp': 'Men 18-28 feeling directionless',
        'channel': 'Instagram DMs',
        'goal': 'First paying client',
        'north_star': '$10K/month net → $100K/month',
        'venture_id': 'lyfe_institute',
        'note': 'Incubated under Empyrean Creative. Spins out once offer is proven.',
    },
    {
        'name': 'Personal Brand — Antony',
        'icon': '👤',
        'type': 'Content Business',
        'stage': '1 — Audience Building',
        'offer': 'Sponsors, Affiliates, Ads, Donations',
        'icp': 'Entrepreneurs and founders',
        'channel': 'Instagram + Content',
        'goal': 'Grow audience, promote Empyrean + Lyfe',
        'north_star': 'Profitable content business',
        'venture_id': 'personal_brand',
        'note': None,
    },
]

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
                'DEX assigns AI or human to each.',
                '👥'
            ),
            divider_block(),
            heading_block('Current Roles', 2),
            text_block(
                'Founder — Antony (Human)\n'
                'Executive Assistant — DEX (AI)\n'
                'CEO — DEX (AI)\n'
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
                'DEX updates these from conversations.',
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
                'Tell DEX in Discord:\n'
                '"Log 20 DMs sent today"\n'
                '"Booked a call with [name]"\n'
                '"Closed [name] for $750"\n\n'
                'DEX tracks and updates here.'
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
                'When confirmed: tell DEX in Discord\n'
                '"I closed my first client"\n'
                'DEX unlocks Stage 2 primitives.'
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
                'DEX generates and maintains these.',
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
                'Every Monday. DEX facilitates.\n'
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
            text_block('DEX creates a new entry here each Monday morning.'),
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
        heading_block('Munoz Holdings', 1),
        callout_block(
            'The holding company.\n'
            'All subsidiaries report here.\n'
            'Portfolio Advisor serves this level.',
            '🏛️'
        ),
        divider_block(),
        heading_block('Entity Structure', 2),
        text_block(
            'MUNOZ HOLDINGS\n'
            '├── EMPYREAN CREATIVE\n'
            '│   Type: B2B Agency\n'
            '│   Stage: 1 — Validation\n'
            '│   Focus: AI services for businesses\n'
            '│   │\n'
            '│   └── LYFE INSTITUTE (incubated)\n'
            '│       Type: Coaching Program\n'
            '│       Stage: 1 — Validation\n'
            '│       Offer: Initiate Arena $750\n'
            '│       Channel: Instagram DMs\n'
            '│       Status: Spinning up\n'
            '│\n'
            '└── PERSONAL BRAND — ANTONY\n'
            '    Type: Content Business\n'
            '    Stage: 1 — Audience Building\n'
            '    Revenue: Sponsors, Affiliates, Ads, Donations\n'
            '    Goal: Promote Empyrean + Lyfe'
        ),
        divider_block(),
        heading_block('Agent Hierarchy', 2),
        text_block(
            'ANTONY (Founder)\n'
            '├── DEX (Executive Assistant — Discord)\n'
            '│   ├── Portfolio Advisor\n'
            '│   ├── Empyrean CEO\n'
            '│   │   └── Empyrean Dev Agent\n'
            '│   └── Lyfe Institute CEO\n'
            '│       └── Lyfe Dev Agent\n'
            '└── Claude Code (Platform Dev)'
        ),
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
    '🤖 AI Copilot — DEX',
    icon='🤖',
    content_blocks=[
        heading_block('AI Copilot — DEX', 1),
        callout_block(
            'Interact with DEX through Discord.\n'
            'This page stores AI insights, memory summaries, and decisions.',
            '👁️'
        ),
        divider_block(),
        heading_block('How to Talk to DEX', 2),
        text_block(
            'Open Discord → #general\n'
            'Type anything naturally.\n'
            'DEX responds in text and voice.\n\n'
            'DEX is always in your voice channel when you join.\n'
            'Type → DEX speaks.'
        ),
        divider_block(),
        heading_block('Memory Summary', 2),
        text_block(
            'DEX memory updated here by agents.\n'
            'What DEX knows. What it has learned.\n'
            'Decisions made. Patterns noticed.'
        ),
        divider_block(),
        heading_block('Pinned Insights', 2),
        text_block(
            'Important insights pinned here by DEX automatically.\n'
            'Awaiting first insight.'
        ),
        divider_block(),
        heading_block('Quick Prompts', 2),
        text_block(
            'Ask DEX in Discord:\n'
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

env_path = f'{_ROOT}/eos_ai/.env'

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
